"""
LLM Service using Google Gemini API.

This service handles:
- Conversation generation for language learning
- Text transliteration (Tamil/Malayalam to English)
- Response generation based on user context
- Sentence generation for pronunciation practice
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import google.generativeai as genai
from typing import List, Optional
import uvicorn

from models import (
    ConversationRequest, ConversationResponse,
    TransliterationRequest, TransliterationResponse,
    SentenceGenerationRequest, SentenceGenerationResponse,
    ResponseGenerationRequest, ResponseGenerationResponse
)

app = FastAPI(
    title="Munshi LLM Service",
    description="Language learning service using Google Gemini API",
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

# Initialize Google Gemini client
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")

genai.configure(api_key=GOOGLE_API_KEY)

class LLMService:
    """LLM service wrapper for Google Gemini API"""
    
    def __init__(self):
        # Use the correct model name for the API version
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        print(f"✓ Google Gemini LLM service initialized")
    
    async def generate_conversation_response(self, user_message: str, context: List[dict], language: str) -> str:
        """Generate conversation response for language learning"""
        
        # Build context from previous messages
        context_str = ""
        if context:
            context_str = "\n".join([
                f"User: {msg.get('user', '')}\nAssistant: {msg.get('assistant', '')}" 
                for msg in context[-5:]  # Last 5 exchanges
            ])
        
        prompt = f"""You are a friendly language learning assistant helping users practice {language}. 
        
Previous conversation:
{context_str}

Current user message: {user_message}

Respond helpfully and encourage language practice. If the user wants to practice pronunciation:
1. Provide a sentence in {language} appropriate for their level
2. If applicable, provide romanized version for Tamil/Malayalam
3. Be encouraging and supportive

Keep responses conversational and engaging."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=500,
                    temperature=0.7,
                )
            )
            return response.text
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM generation error: {str(e)}")
    
    async def transliterate_text(self, text: str, source_language: str) -> str:
        """Transliterate text to romanized format"""
        
        if source_language == "English":
            return text
        
        if source_language == "Tamil":
            prompt = f"""Convert this Tamil text to natural romanized English (Thanglish) as Tamil people type on smartphones:

Tamil: {text}
Thanglish:"""
        elif source_language == "Malayalam":
            prompt = f"""Convert this Malayalam text to natural romanized English (Manglish) as Malayalam people type on smartphones:

Malayalam: {text}
Manglish:"""
        else:
            return text
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=200,
                    temperature=0.3,
                )
            )
            result = response.text.strip()
            # Clean up the response
            result = result.split('\n')[0].strip()
            return result if result else text
        except Exception as e:
            print(f"Transliteration error: {e}")
            return text
    
    async def generate_practice_sentence(self, language: str, difficulty: str = "beginner", topic: Optional[str] = None) -> dict:
        """Generate practice sentence for pronunciation"""
        
        topic_context = f" related to {topic}" if topic else ""
        
        prompt = f"""Generate a {difficulty} level sentence in {language}{topic_context} for pronunciation practice.

Requirements:
- Appropriate for {difficulty} level learners
- Clear pronunciation focus
- Culturally appropriate
- Single sentence only

Respond with just the sentence in {language}."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=100,
                    temperature=0.8,
                )
            )
            sentence = response.text.strip()
            
            # Get romanized version if needed
            romanized = await self.transliterate_text(sentence, language)
            
            return {
                "original": sentence,
                "romanized": romanized,
                "combined": f"{sentence}\n\n🔤 {romanized}" if romanized != sentence else sentence
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Sentence generation error: {str(e)}")
    
    async def generate_response_to_evaluation(self, accuracy: float, errors: List[dict], user_context: dict) -> str:
        """Generate encouraging response based on pronunciation evaluation"""
        
        error_summary = f"\nErrors found: {len(errors)}" if errors else "\nNo errors - perfect pronunciation!"
        context_str = f"User is learning {user_context.get('language', 'a language')} at {user_context.get('level', 'beginner')} level."
        
        prompt = f"""You are a supportive language learning coach. A student just completed a pronunciation exercise.

{context_str}

Results:
- Accuracy: {accuracy}%{error_summary}

Generate an encouraging response that:
1. Acknowledges their effort
2. Celebrates success or motivates improvement
3. Offers specific next steps
4. Keeps them motivated to continue

Be warm, supportive, and specific to their performance."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=300,
                    temperature=0.7,
                )
            )
            return response.text
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Response generation error: {str(e)}")

# Initialize LLM service
llm_service = LLMService()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "llm-service",
        "provider": "Google Gemini",
        "model": "gemini-1.5-flash",
        "api_key_configured": bool(GOOGLE_API_KEY)
    }

@app.post("/conversation", response_model=ConversationResponse)
async def generate_conversation(request: ConversationRequest):
    """Generate conversation response for language learning."""
    try:
        response_text = await llm_service.generate_conversation_response(
            request.user_message, 
            request.context, 
            request.language
        )
        return ConversationResponse(success=True, response=response_text)
    except Exception as e:
        return ConversationResponse(success=False, error=str(e))

@app.post("/transliterate", response_model=TransliterationResponse)
async def transliterate_text(request: TransliterationRequest):
    """Transliterate text to romanized format."""
    try:
        romanized = await llm_service.transliterate_text(
            request.text, 
            request.source_language
        )
        return TransliterationResponse(
            success=True, 
            original_text=request.text,
            romanized_text=romanized,
            source_language=request.source_language
        )
    except Exception as e:
        return TransliterationResponse(success=False, error=str(e))

@app.post("/generate-sentence", response_model=SentenceGenerationResponse)
async def generate_practice_sentence(request: SentenceGenerationRequest):
    """Generate practice sentence for pronunciation."""
    try:
        sentence_data = await llm_service.generate_practice_sentence(
            request.language,
            request.difficulty,
            request.topic
        )
        return SentenceGenerationResponse(success=True, sentence_data=sentence_data)
    except Exception as e:
        return SentenceGenerationResponse(success=False, error=str(e))

@app.post("/generate-response", response_model=ResponseGenerationResponse)
async def generate_evaluation_response(request: ResponseGenerationRequest):
    """Generate response based on pronunciation evaluation."""
    try:
        response_text = await llm_service.generate_response_to_evaluation(
            request.accuracy,
            request.errors,
            request.user_context
        )
        return ResponseGenerationResponse(success=True, response=response_text)
    except Exception as e:
        return ResponseGenerationResponse(success=False, error=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("LLM_SERVICE_PORT", 8005)),
        reload=True
    )