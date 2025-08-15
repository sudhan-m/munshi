"""
Conversation Service - Main orchestrator for language learning conversations.

This service handles:
- User conversation management
- Orchestration between ASR, LLM, and Evaluator services
- Chat history and context management
- RAG preparation for future integration
- User learning profile management
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import os
import httpx
import uvicorn
from datetime import datetime, timedelta

from database import connect_to_mongo, close_mongo_connection, get_conversations_collection, get_users_collection
from models import (
    ChatMessage, ConversationRequest, ConversationResponse,
    PronunciationEvaluationRequest, PronunciationEvaluationResponse,
    UserProfile, ConversationSession
)

app = FastAPI(
    title="Munshi Conversation Service",
    description="Main orchestrator for language learning conversations",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
ASR_SERVICE_URL = os.getenv("ASR_SERVICE_URL", "http://localhost:8004")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8005")
EVALUATOR_SERVICE_URL = os.getenv("EVALUATOR_SERVICE_URL", "http://localhost:8006")
AUDIO_SERVICE_URL = os.getenv("AUDIO_SERVICE_URL", "http://localhost:8003")

class ConversationOrchestrator:
    """Main orchestrator for conversation flow"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.http_client.aclose()
    
    async def get_or_create_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get or create user learning profile"""
        collection = get_users_collection()
        
        user = await collection.find_one({"user_id": user_id})
        if user:
            return user
        
        # Create new user profile
        new_user = {
            "user_id": user_id,
            "preferred_language": "English",
            "skill_level": "beginner",
            "learning_goals": [],
            "session_count": 0,
            "total_practice_time": 0,
            "best_accuracy": 0.0,
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        
        await collection.insert_one(new_user)
        return new_user
    
    async def get_conversation_context(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation context for user"""
        collection = get_conversations_collection()
        
        cursor = collection.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit * 2)  # Get more to account for pairs
        
        messages = []
        async for doc in cursor:
            if doc.get("role") == "user":
                messages.append({"user": doc.get("content", "")})
            elif doc.get("role") == "assistant":
                if messages and "assistant" not in messages[-1]:
                    messages[-1]["assistant"] = doc.get("content", "")
                else:
                    messages.append({"assistant": doc.get("content", "")})
        
        return messages[:limit]
    
    async def save_conversation_message(self, user_id: str, role: str, content: str, metadata: Dict = None):
        """Save conversation message to database"""
        collection = get_conversations_collection()
        
        message = {
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {}
        }
        
        await collection.insert_one(message)
    
    async def handle_text_conversation(self, user_id: str, message: str) -> str:
        """Handle text-based conversation"""
        try:
            # Get user profile and context
            user_profile = await self.get_or_create_user_profile(user_id)
            context = await self.get_conversation_context(user_id)
            
            # Call LLM service for conversation
            response = await self.http_client.post(
                f"{LLM_SERVICE_URL}/conversation",
                json={
                    "user_message": message,
                    "context": context,
                    "language": user_profile.get("preferred_language", "English")
                }
            )
            
            if response.status_code == 200:
                llm_response = response.json()
                if llm_response.get("success"):
                    assistant_message = llm_response.get("response", "I'm sorry, I couldn't process that.")
                    
                    # Save both messages
                    await self.save_conversation_message(user_id, "user", message)
                    await self.save_conversation_message(user_id, "assistant", assistant_message)
                    
                    # Update user activity
                    users_collection = get_users_collection()
                    await users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {"last_active": datetime.utcnow()}}
                    )
                    
                    return assistant_message
                else:
                    return "I'm having trouble processing your message. Please try again."
            else:
                return "I'm currently experiencing technical difficulties. Please try again later."
                
        except Exception as e:
            print(f"Error in text conversation: {e}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again."
    
    async def handle_pronunciation_evaluation(
        self, 
        user_id: str, 
        audio_file_id: str, 
        intended_text: str, 
        language: str
    ) -> Dict[str, Any]:
        """Handle pronunciation evaluation workflow"""
        try:
            # Step 1: Get transcription from ASR service
            audio_response = await self.http_client.get(f"{AUDIO_SERVICE_URL}/audio/play/{audio_file_id}")
            if audio_response.status_code != 200:
                return {"success": False, "error": "Could not retrieve audio file"}
            
            # For now, we'll assume we get the audio file path - in production, 
            # we'd need to handle the actual audio file transfer
            with open(f"temp_audio_{audio_file_id}.wav", "wb") as f:
                f.write(audio_response.content)
            
            # Step 2: Transcribe audio
            with open(f"temp_audio_{audio_file_id}.wav", "rb") as audio_file:
                asr_response = await self.http_client.post(
                    f"{ASR_SERVICE_URL}/transcribe",
                    files={"audio": audio_file},
                    data={"language": language}
                )
            
            if asr_response.status_code != 200:
                return {"success": False, "error": "Transcription failed"}
            
            asr_result = asr_response.json()
            if not asr_result.get("success"):
                return {"success": False, "error": "Transcription was not successful"}
            
            actual_transcription = asr_result.get("transcription", "")
            
            # Step 3: Get transliterations from LLM service
            intended_romanized = intended_text  # Default for English
            actual_romanized = actual_transcription  # Default for English
            
            if language in ["Tamil", "Malayalam"]:
                # Get intended transliteration
                intended_response = await self.http_client.post(
                    f"{LLM_SERVICE_URL}/transliterate",
                    json={"text": intended_text, "source_language": language}
                )
                
                if intended_response.status_code == 200:
                    intended_result = intended_response.json()
                    if intended_result.get("success"):
                        intended_romanized = intended_result.get("romanized_text", intended_text)
                
                # Get actual transliteration
                actual_response = await self.http_client.post(
                    f"{LLM_SERVICE_URL}/transliterate",
                    json={"text": actual_transcription, "source_language": language}
                )
                
                if actual_response.status_code == 200:
                    actual_result = actual_response.json()
                    if actual_result.get("success"):
                        actual_romanized = actual_result.get("romanized_text", actual_transcription)
            
            # Step 4: Evaluate pronunciation
            eval_response = await self.http_client.post(
                f"{EVALUATOR_SERVICE_URL}/evaluate",
                json={
                    "intended_text": intended_text,
                    "actual_text": actual_transcription,
                    "intended_romanized": intended_romanized,
                    "actual_romanized": actual_romanized,
                    "language": language
                }
            )
            
            if eval_response.status_code != 200:
                return {"success": False, "error": "Evaluation failed"}
            
            eval_result = eval_response.json()
            if not eval_result.get("success"):
                return {"success": False, "error": "Evaluation was not successful"}
            
            # Step 5: Generate response using LLM
            accuracy = eval_result["results"]["metrics"]["accuracy_percentage"]
            errors = eval_result["results"]["pronunciation_errors"]
            user_profile = await self.get_or_create_user_profile(user_id)
            
            response_response = await self.http_client.post(
                f"{LLM_SERVICE_URL}/generate-response",
                json={
                    "accuracy": accuracy,
                    "errors": errors,
                    "user_context": {
                        "language": language,
                        "level": user_profile.get("skill_level", "beginner")
                    }
                }
            )
            
            llm_response_text = "Great job practicing!"
            if response_response.status_code == 200:
                response_result = response_response.json()
                if response_result.get("success"):
                    llm_response_text = response_result.get("response", llm_response_text)
            
            # Step 6: Update user profile with results
            users_collection = get_users_collection()
            await users_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "last_active": datetime.utcnow(),
                        "best_accuracy": max(user_profile.get("best_accuracy", 0), accuracy)
                    },
                    "$inc": {"session_count": 1}
                }
            )
            
            # Step 7: Save evaluation to conversation history
            await self.save_conversation_message(
                user_id, 
                "evaluation", 
                f"Pronunciation practice: {accuracy}% accuracy",
                {
                    "evaluation_results": eval_result["results"],
                    "intended_text": intended_text,
                    "language": language
                }
            )
            
            await self.save_conversation_message(
                user_id,
                "assistant", 
                llm_response_text,
                {"type": "evaluation_response"}
            )
            
            # Clean up temp file
            try:
                os.unlink(f"temp_audio_{audio_file_id}.wav")
            except:
                pass
            
            return {
                "success": True,
                "evaluation_results": eval_result["results"],
                "llm_response": llm_response_text
            }
            
        except Exception as e:
            print(f"Error in pronunciation evaluation: {e}")
            return {"success": False, "error": f"Evaluation error: {str(e)}"}

# Initialize orchestrator
orchestrator = ConversationOrchestrator()

@app.on_event("startup")
async def startup_event():
    """Initialize database connections on startup."""
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown."""
    await close_mongo_connection()
    await orchestrator.close()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "conversation-service"}

@app.post("/chat", response_model=ConversationResponse)
async def chat_with_user(request: ConversationRequest):
    """
    Handle user conversation - main entry point for text-based interaction.
    
    Args:
        request: Conversation request with user message and context
        
    Returns:
        ConversationResponse with assistant response
    """
    try:
        response_text = await orchestrator.handle_text_conversation(
            request.user_id,
            request.message
        )
        
        return ConversationResponse(
            success=True,
            response=response_text,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing conversation: {str(e)}"
        )

@app.post("/evaluate-pronunciation", response_model=PronunciationEvaluationResponse)
async def evaluate_pronunciation(request: PronunciationEvaluationRequest):
    """
    Handle pronunciation evaluation workflow.
    
    Args:
        request: Pronunciation evaluation request
        
    Returns:
        PronunciationEvaluationResponse with evaluation results and LLM response
    """
    try:
        result = await orchestrator.handle_pronunciation_evaluation(
            request.user_id,
            request.audio_file_id,
            request.intended_text,
            request.language
        )
        
        if result["success"]:
            return PronunciationEvaluationResponse(
                success=True,
                evaluation_results=result["evaluation_results"],
                llm_response=result["llm_response"]
            )
        else:
            return PronunciationEvaluationResponse(
                success=False,
                error=result["error"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing pronunciation evaluation: {str(e)}"
        )

@app.get("/user/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Get user learning profile."""
    try:
        profile = await orchestrator.get_or_create_user_profile(user_id)
        # Remove MongoDB _id for JSON serialization
        profile.pop("_id", None)
        return profile
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching user profile: {str(e)}"
        )

@app.get("/user/{user_id}/conversations")
async def get_user_conversations(user_id: str, limit: int = 20):
    """Get user conversation history."""
    try:
        collection = get_conversations_collection()
        
        cursor = collection.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit)
        
        conversations = []
        async for doc in cursor:
            doc.pop("_id", None)  # Remove MongoDB _id
            conversations.append(doc)
        
        return {"conversations": conversations}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching conversations: {str(e)}"
        )

@app.post("/user/{user_id}/generate-sentence")
async def generate_practice_sentence(user_id: str, language: str, difficulty: str = "beginner", topic: str = None):
    """Generate practice sentence for user."""
    try:
        response = await orchestrator.http_client.post(
            f"{LLM_SERVICE_URL}/generate-sentence",
            json={
                "language": language,
                "difficulty": difficulty,
                "topic": topic
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                # Save the generated sentence to conversation history
                await orchestrator.save_conversation_message(
                    user_id,
                    "assistant",
                    f"Here's a practice sentence: {result['sentence_data']['original']}",
                    {"type": "practice_sentence", "sentence_data": result["sentence_data"]}
                )
                return result
            else:
                raise HTTPException(status_code=500, detail=result.get("error", "Sentence generation failed"))
        else:
            raise HTTPException(status_code=500, detail="LLM service unavailable")
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating sentence: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("CONVERSATION_SERVICE_PORT", 8007)),
        reload=True
    )