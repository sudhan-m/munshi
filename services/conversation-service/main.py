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

from database import connect_to_mongo, close_mongo_connection, get_conversations_collection, get_users_collection, get_pronunciation_profiles_collection
from models import (
    ChatMessage, ConversationRequest, ConversationResponse,
    PronunciationEvaluationRequest, PronunciationEvaluationResponse,
    UserProfile, ConversationSession, PronunciationProfile
)
from pronunciation_profiler import PronunciationProfileManager

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
        self.pronunciation_manager = PronunciationProfileManager(LLM_SERVICE_URL)
    
    async def close(self):
        await self.http_client.aclose()
        await self.pronunciation_manager.close()
    
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
    
    async def get_or_create_pronunciation_profile(self, user_id: str, language: str) -> Dict[str, Any]:
        """Get or create pronunciation profile for user and language"""
        collection = get_pronunciation_profiles_collection()
        
        profile = await collection.find_one({"user_id": user_id, "language": language})
        if profile:
            # Convert MongoDB document to dict and remove _id
            profile.pop("_id", None)
            # Reconstruct bandits from stored state
            profile = self._reconstruct_profile_bandits(profile)
            return profile
        
        # Create new pronunciation profile
        new_profile = self.pronunciation_manager.create_profile(user_id, language)
        
        # Serialize for MongoDB storage
        serialized_profile = self._serialize_profile_for_storage(new_profile)
        await collection.insert_one(serialized_profile)
        
        return new_profile
    
    async def save_pronunciation_profile(self, profile: Dict[str, Any]):
        """Save pronunciation profile to database"""
        collection = get_pronunciation_profiles_collection()
        
        # Serialize for storage
        serialized_profile = self._serialize_profile_for_storage(profile)
        
        await collection.update_one(
            {"user_id": profile["user_id"], "language": profile["language"]},
            {"$set": serialized_profile},
            upsert=True
        )
    
    def _serialize_profile_for_storage(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Convert profile with bandits to MongoDB-serializable format"""
        serialized = profile.copy()
        
        # Convert bandit objects to serializable state
        if "weakness_bandit" in profile:
            bandit = profile["weakness_bandit"]
            serialized["weakness_bandit_state"] = {
                phoneme: {
                    "successes": conf.successes,
                    "failures": conf.failures,
                    "attempts": conf.attempts,
                    "last_updated": conf.last_updated.isoformat() if conf.last_updated else None
                }
                for phoneme, conf in bandit.confidences.items()
            }
            del serialized["weakness_bandit"]
        
        if "strength_bandit" in profile:
            bandit = profile["strength_bandit"]
            serialized["strength_bandit_state"] = {
                phoneme: {
                    "successes": conf.successes,
                    "failures": conf.failures,
                    "attempts": conf.attempts,
                    "last_updated": conf.last_updated.isoformat() if conf.last_updated else None
                }
                for phoneme, conf in bandit.confidences.items()
            }
            del serialized["strength_bandit"]
        
        # Convert datetime objects to ISO strings
        if "created_at" in serialized:
            serialized["created_at"] = serialized["created_at"].isoformat()
        if "last_updated" in serialized:
            serialized["last_updated"] = serialized["last_updated"].isoformat()
        
        return serialized
    
    def _reconstruct_profile_bandits(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Reconstruct bandit objects from stored state"""
        from pronunciation_profiler import ThompsonSamplingBandit, PhonemeConfidence
        from phoneme_mappings import LANGUAGE_PHONEMES
        
        language = profile["language"]
        phonemes = LANGUAGE_PHONEMES.get(language, [])
        
        # Reconstruct weakness bandit
        weakness_bandit = ThompsonSamplingBandit(phonemes)
        if "weakness_bandit_state" in profile:
            for phoneme, state in profile["weakness_bandit_state"].items():
                if phoneme in weakness_bandit.confidences:
                    conf = weakness_bandit.confidences[phoneme]
                    conf.successes = state.get("successes", 1)
                    conf.failures = state.get("failures", 1)
                    conf.attempts = state.get("attempts", 0)
                    if state.get("last_updated"):
                        conf.last_updated = datetime.fromisoformat(state["last_updated"])
        profile["weakness_bandit"] = weakness_bandit
        
        # Reconstruct strength bandit
        strength_bandit = ThompsonSamplingBandit(phonemes)
        if "strength_bandit_state" in profile:
            for phoneme, state in profile["strength_bandit_state"].items():
                if phoneme in strength_bandit.confidences:
                    conf = strength_bandit.confidences[phoneme]
                    conf.successes = state.get("successes", 1)
                    conf.failures = state.get("failures", 1)
                    conf.attempts = state.get("attempts", 0)
                    if state.get("last_updated"):
                        conf.last_updated = datetime.fromisoformat(state["last_updated"])
        profile["strength_bandit"] = strength_bandit
        
        # Convert datetime strings back to datetime objects
        if isinstance(profile.get("created_at"), str):
            profile["created_at"] = datetime.fromisoformat(profile["created_at"])
        if isinstance(profile.get("last_updated"), str):
            profile["last_updated"] = datetime.fromisoformat(profile["last_updated"])
        
        return profile
    
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
        """Handle pronunciation evaluation workflow with profiling integration"""
        try:
            # Get or create pronunciation profile
            pronunciation_profile = await self.get_or_create_pronunciation_profile(user_id, language)
            
            # Get conversation context for mood detection
            conversation_context = await self.get_conversation_context(user_id, limit=5)
            context_text = " ".join([
                f"{msg.get('user', '')} {msg.get('assistant', '')}" 
                for msg in conversation_context
            ])
            # Step 1: Get transcription from ASR service
            audio_response = await self.http_client.get(f"{AUDIO_SERVICE_URL}/audio/play/{audio_file_id}")
            if audio_response.status_code != 200:
                return {"success": False, "error": "Could not retrieve audio file"}
            
            # Create temporary file with proper cleanup
            temp_file_path = f"temp_audio_{audio_file_id}.wav"
            try:
                # Write audio content to temporary file
                with open(temp_file_path, "wb") as f:
                    f.write(audio_response.content)
                
                # Step 2: Transcribe audio
                with open(temp_file_path, "rb") as audio_file:
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
                
                # Step 7: Update pronunciation profile with evaluation results
                character_errors = eval_result["results"].get("character_mispronunciations", [])
                updated_profile = self.pronunciation_manager.update_profile_with_evaluation(
                    pronunciation_profile,
                    character_errors,
                    accuracy,
                    intended_text,
                    actual_transcription,
                    language
                )
                
                # Save updated profile to database
                await self.save_pronunciation_profile(updated_profile)
                
                # Check if profile needs compaction
                if await self.pronunciation_manager.should_compact_profile(updated_profile):
                    compacted_profile = await self.pronunciation_manager.compact_profile_with_llm(updated_profile)
                    await self.save_pronunciation_profile(compacted_profile)
                
                # Step 8: Save evaluation to conversation history
                await self.save_conversation_message(
                    user_id, 
                    "evaluation", 
                    f"Pronunciation practice: {accuracy}% accuracy",
                    {
                        "evaluation_results": eval_result["results"],
                        "intended_text": intended_text,
                        "language": language,
                        "character_errors": character_errors
                    }
                )
                
                await self.save_conversation_message(
                    user_id,
                    "assistant", 
                    llm_response_text,
                    {"type": "evaluation_response"}
                )
                
                return {
                    "success": True,
                    "evaluation_results": eval_result["results"],
                    "llm_response": llm_response_text,
                    "pronunciation_insights": {
                        "target_phonemes": await self.pronunciation_manager.suggest_target_phonemes(
                            updated_profile, context_text, count=3
                        ),
                        "overall_accuracy": updated_profile["metadata"]["overall_accuracy"]
                    }
                }
            
            finally:
                # Ensure temporary file is always cleaned up
                try:
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                except Exception as cleanup_error:
                    print(f"Warning: Could not clean up temporary file {temp_file_path}: {cleanup_error}")
            
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
    """Generate practice sentence for user with pronunciation profiling."""
    try:
        # Get pronunciation profile and conversation context
        pronunciation_profile = await orchestrator.get_or_create_pronunciation_profile(user_id, language)
        conversation_context = await orchestrator.get_conversation_context(user_id, limit=5)
        context_text = " ".join([
            f"{msg.get('user', '')} {msg.get('assistant', '')}" 
            for msg in conversation_context
        ])
        
        # Get target phonemes based on bandit strategy
        target_phonemes = await orchestrator.pronunciation_manager.suggest_target_phonemes(
            pronunciation_profile, context_text, count=5
        )
        
        response = await orchestrator.http_client.post(
            f"{LLM_SERVICE_URL}/generate-sentence",
            json={
                "language": language,
                "difficulty": difficulty,
                "topic": topic,
                "target_phonemes": target_phonemes,
                "pronunciation_profile": {
                    "overall_accuracy": pronunciation_profile["metadata"]["overall_accuracy"],
                    "recent_accuracy": orchestrator.pronunciation_manager._calculate_recent_accuracy(
                        pronunciation_profile.get("recent_attempts", [])
                    )
                }
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

@app.get("/user/{user_id}/pronunciation-profile/{language}")
async def get_pronunciation_profile(user_id: str, language: str):
    """Get user's pronunciation profile insights."""
    try:
        pronunciation_profile = await orchestrator.get_or_create_pronunciation_profile(user_id, language)
        
        # Get conversation context for recommendations
        conversation_context = await orchestrator.get_conversation_context(user_id, limit=5)
        context_text = " ".join([
            f"{msg.get('user', '')} {msg.get('assistant', '')}" 
            for msg in conversation_context
        ])
        
        # Get recommendations
        target_phonemes = await orchestrator.pronunciation_manager.suggest_target_phonemes(
            pronunciation_profile, context_text, count=5
        )
        
        # Get weak and strong phonemes for insights
        weakness_bandit = pronunciation_profile["weakness_bandit"]
        strength_bandit = pronunciation_profile["strength_bandit"]
        
        weak_phonemes = weakness_bandit.get_phoneme_ranking(ascending=True)[:5]
        strong_phonemes = strength_bandit.get_phoneme_ranking(ascending=False)[:5]
        
        return {
            "user_id": user_id,
            "language": language,
            "overall_accuracy": pronunciation_profile["metadata"]["overall_accuracy"],
            "total_attempts": pronunciation_profile["metadata"]["total_attempts"],
            "recent_accuracy": orchestrator.pronunciation_manager._calculate_recent_accuracy(
                pronunciation_profile.get("recent_attempts", [])
            ),
            "recommended_phonemes": target_phonemes,
            "weakest_phonemes": [{"phoneme": p, "confidence": c} for p, c in weak_phonemes],
            "strongest_phonemes": [{"phoneme": p, "confidence": c} for p, c in strong_phonemes],
            "session_duration_minutes": orchestrator.pronunciation_manager._get_session_duration(pronunciation_profile),
            "last_updated": pronunciation_profile["last_updated"].isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching pronunciation profile: {str(e)}"
        )

if __name__ == "__main__":
    port_env = os.getenv("CONVERSATION_SERVICE_PORT", "8007")
    # Handle Kubernetes service environment variable format (tcp://host:port)
    if port_env.startswith("tcp://"):
        port = int(port_env.split(":")[-1])
    else:
        port = int(port_env)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )