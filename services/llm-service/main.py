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
    ResponseGenerationRequest, ResponseGenerationResponse,
    BanditStrategyRequest, BanditStrategyResponse
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
        # Configure safety settings to be more permissive for language learning content
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        self.model = genai.GenerativeModel('gemini-2.5-pro', safety_settings=safety_settings)
        print(f"✓ Google Gemini LLM service initialized with gemini-2.5-pro")

    def _extract_text_from_response(self, response) -> str:
        """Safely extract text from Gemini response, handling different response structures."""
        try:
            # Try the simple text accessor first
            return response.text
        except (ValueError, AttributeError) as e:
            # Fall back to parts accessor
            try:
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    finish_reason = candidate.finish_reason if hasattr(candidate, 'finish_reason') else None

                    # finish_reason: 1=STOP (normal), 2=MAX_TOKENS, 3=SAFETY, 4=RECITATION, 5=OTHER
                    if finish_reason == 3:  # SAFETY
                        print(f"Warning: Response blocked by safety filters")
                        if hasattr(candidate, 'safety_ratings'):
                            print(f"Safety ratings: {candidate.safety_ratings}")
                        return "[Content blocked by safety filters]"

                    # Debug: print candidate structure
                    print(f"Debug: finish_reason={finish_reason}, candidate={candidate}")

                    if candidate.content:
                        # Check if parts exist and have length (protobuf RepeatedComposite may be empty)
                        if hasattr(candidate.content, 'parts') and len(candidate.content.parts) > 0:
                            text_parts = []
                            for part in candidate.content.parts:
                                if hasattr(part, 'text'):
                                    text_parts.append(part.text)
                            result = "".join(text_parts)
                            if result:
                                return result
                        # Try direct text access on content
                        if hasattr(candidate.content, 'text'):
                            return candidate.content.text

                    print(f"Warning: Could not extract text. finish_reason={finish_reason}, parts_len={len(candidate.content.parts) if (candidate.content and hasattr(candidate.content, 'parts')) else 0}")
            except Exception as ex:
                print(f"Error extracting from parts: {ex}")
                import traceback
                print(traceback.format_exc())
            # Last resort - return empty string
            return ""
    
    async def generate_conversation_response(self, user_message: str, context: List[dict], language: str) -> str:
        """Generate conversation response for language learning"""
        
        # Build context from previous messages
        context_str = ""
        if context:
            context_str = "\n".join([
                f"User: {msg.get('user', '')}\nAssistant: {msg.get('assistant', '')}" 
                for msg in context[-5:]  # Last 5 exchanges
            ])
        
        # Check if user is requesting practice
        is_practice_request = any(keyword in user_message.lower() for keyword in [
            'practice', 'sentence', 'try', 'learn', 'teach me', 'generate'
        ])

        if is_practice_request:
            # Generate single practice sentence with few-shot examples
            if language == "Malayalam":
                examples = """Example 1:
{"type": "practice", "sentence": "എനിക്ക് വെള്ളം വേണം", "romanized": "Enikku vellam venam", "translation": "I want water"}

Example 2:
{"type": "practice", "sentence": "നിങ്ങളുടെ പേര് എന്താണ്?", "romanized": "Ningalude peru enthanu?", "translation": "What is your name?"}

Example 3:
{"type": "practice", "sentence": "ഇത് വളരെ നല്ലതാണ്", "romanized": "Ithu valare nallathanu", "translation": "This is very good"}

Example 4:
{"type": "practice", "sentence": "ഞാൻ മലയാളം പഠിക്കുന്നു", "romanized": "Njan Malayalam padikkunnu", "translation": "I am learning Malayalam"}"""
            elif language == "Tamil":
                examples = """Example 1:
{"type": "practice", "sentence": "எனக்கு தண்ணீர் வேண்டும்", "romanized": "Enakku thanneer vendum", "translation": "I want water"}

Example 2:
{"type": "practice", "sentence": "உங்கள் பெயர் என்ன?", "romanized": "Ungal peyar enna?", "translation": "What is your name?"}

Example 3:
{"type": "practice", "sentence": "இது மிகவும் நல்லது", "romanized": "Idhu migavum nalladhu", "translation": "This is very good"}"""
            elif language == "Hindi":
                examples = """Example 1:
{"type": "practice", "sentence": "मुझे पानी चाहिए", "romanized": "Mujhe paani chahiye", "translation": "I want water"}

Example 2:
{"type": "practice", "sentence": "आपका नाम क्या है?", "romanized": "Aapka naam kya hai?", "translation": "What is your name?"}

Example 3:
{"type": "practice", "sentence": "यह बहुत अच्छा है", "romanized": "Yeh bahut accha hai", "translation": "This is very good"}"""
            else:
                examples = """Example 1:
{"type": "practice", "sentence": "I want water", "romanized": "I want water", "translation": "I want water"}"""

            prompt = f"""You are generating practice sentences for {language} language learners.

CRITICAL RULES:
1. Sentence MUST be in {language} script (NOT English/Latin alphabet)
2. Follow the EXACT JSON format from examples below
3. Return ONLY valid JSON with no markdown, no code blocks, no explanations

Here are correct examples for {language}:

{examples}

Now generate ONE NEW practice sentence in {language} following the EXACT same format as above:"""
        else:
            # Regular conversation
            prompt = f"""You are a friendly language learning assistant helping users practice {language}.

Previous conversation:
{context_str}

Current user message: {user_message}

Respond conversationally and supportively. If appropriate, offer to provide practice sentences."""

        try:
            import re
            import json as json_module

            # Try up to 3 times for practice requests
            max_retries = 3 if is_practice_request else 1

            for attempt in range(max_retries):
                response = self.model.generate_content(prompt)
                extracted_text = self._extract_text_from_response(response)

                if not extracted_text:
                    print(f"Warning: Empty response from Gemini (attempt {attempt + 1})")
                    continue

                # Clean JSON if it has markdown code blocks or extra text
                if is_practice_request:
                    # Remove markdown code blocks
                    cleaned = extracted_text.strip()
                    if cleaned.startswith('```'):
                        cleaned = cleaned.split('\n', 1)[1] if '\n' in cleaned else cleaned[3:]
                    if cleaned.endswith('```'):
                        cleaned = cleaned.rsplit('\n', 1)[0] if '\n' in cleaned else cleaned[:-3]
                    cleaned = cleaned.strip()

                    # Find JSON object
                    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                    if json_match:
                        cleaned = json_match.group(0)

                    # Validate the response
                    try:
                        parsed = json_module.loads(cleaned)
                        sentence = parsed.get('sentence', '')

                        print(f"DEBUG: language='{language}', sentence='{sentence}'")

                        # Check if sentence contains non-Latin script for non-English languages
                        validation_passed = True
                        if language != "English":
                            # Malayalam Unicode range: 0D00-0D7F
                            # Tamil Unicode range: 0B80-0BFF
                            # Hindi/Devanagari Unicode range: 0900-097F
                            has_native_script = bool(re.search(r'[\u0900-\u097F\u0B80-\u0BFF\u0D00-\u0D7F]', sentence))

                            if not has_native_script:
                                print(f"Validation FAILED (attempt {attempt + 1}/{max_retries}): No {language} script detected in '{sentence}'")
                                validation_passed = False
                                if attempt < max_retries - 1:
                                    prompt = f"{prompt}\n\nPREVIOUS ATTEMPT WAS WRONG - it used English letters. You MUST use {language} script!"
                                    continue
                                else:
                                    print(f"All retries exhausted. Failing request.")
                                    return "I'm having trouble generating a Malayalam sentence. Please try again."

                        if validation_passed:
                            print(f"Validation PASSED: '{sentence}'")
                            return cleaned
                    except json_module.JSONDecodeError as e:
                        print(f"JSON decode error (attempt {attempt + 1}): {e}")
                        if attempt < max_retries - 1:
                            continue

                    return cleaned

                return extracted_text

            # If all retries failed
            print(f"Warning: All {max_retries} attempts failed for practice request")
            return "I'm having trouble generating a response right now. Please try again."
        except Exception as e:
            print(f"Error in generate_conversation_response: {type(e).__name__}: {str(e)}")
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
            response = self.model.generate_content(prompt)
            result = self._extract_text_from_response(response).strip()
            # Clean up the response
            result = result.split('\n')[0].strip()
            return result if result else text
        except Exception as e:
            print(f"Transliteration error: {e}")
            return text
    
    async def generate_practice_sentence(
        self, 
        language: str, 
        difficulty: str = "beginner", 
        topic: Optional[str] = None,
        target_phonemes: Optional[List[str]] = None,
        pronunciation_profile: Optional[dict] = None
    ) -> dict:
        """Generate practice sentence for pronunciation with profiling support"""
        
        topic_context = f" related to {topic}" if topic else ""
        
        # Build phoneme context
        phoneme_context = ""
        if target_phonemes:
            phoneme_list = ", ".join(target_phonemes)
            phoneme_context = f"\n\nIMPORTANT: Include words with these target sounds/phonemes: {phoneme_list}"
        
        # Build user context
        user_context = ""
        if pronunciation_profile:
            overall_acc = pronunciation_profile.get("overall_accuracy", 0.5)
            recent_acc = pronunciation_profile.get("recent_accuracy", 0.5)
            user_context = f"""
            
User pronunciation context:
- Overall accuracy: {overall_acc:.1%}
- Recent accuracy: {recent_acc:.1%}
- Adjust sentence complexity accordingly"""
        
        prompt = f"""Generate a {difficulty} level sentence in {language}{topic_context} for pronunciation practice.

Requirements:
- Appropriate for {difficulty} level learners
- Clear pronunciation focus
- Culturally appropriate
- Single sentence only{phoneme_context}{user_context}

Respond with just the sentence in {language}."""

        try:
            response = self.model.generate_content(prompt)
            sentence = self._extract_text_from_response(response).strip()

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
            response = self.model.generate_content(prompt)
            return self._extract_text_from_response(response)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Response generation error: {str(e)}")

    async def analyze_bandit_strategy(self, prompt: str) -> str:
        """Analyze user context and recommend bandit strategy"""
        try:
            response = self.model.generate_content(prompt)
            return self._extract_text_from_response(response).strip()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Strategy analysis error: {str(e)}")

# Initialize LLM service
llm_service = LLMService()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "llm-service",
        "provider": "Google Gemini",
        "model": "gemini-2.5-pro",
        "api_key_configured": bool(GOOGLE_API_KEY)
    }

@app.post("/conversation", response_model=ConversationResponse)
async def generate_conversation(request: ConversationRequest):
    """Generate conversation response for language learning."""
    try:
        print(f"Received conversation request: {request.user_message[:50]}...")
        response_text = await llm_service.generate_conversation_response(
            request.user_message,
            request.context,
            request.language
        )
        print(f"Generated response: {response_text[:100] if response_text else 'EMPTY'}")
        return ConversationResponse(success=True, response=response_text)
    except Exception as e:
        print(f"Exception in conversation endpoint: {type(e).__name__}: {str(e)}")
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
    """Generate practice sentence for pronunciation with profiling support."""
    try:
        sentence_data = await llm_service.generate_practice_sentence(
            request.language,
            request.difficulty,
            request.topic,
            request.target_phonemes,
            request.pronunciation_profile
        )
        return SentenceGenerationResponse(success=True, sentence_data=sentence_data)
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"Error in generate_practice_sentence: {error_msg}")
        print(traceback.format_exc())
        return SentenceGenerationResponse(success=False, error=error_msg)

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

@app.post("/analyze-strategy", response_model=BanditStrategyResponse)
async def analyze_bandit_strategy(request: BanditStrategyRequest):
    """Analyze user context and recommend bandit strategy."""
    try:
        strategy_text = await llm_service.analyze_bandit_strategy(request.prompt)
        return BanditStrategyResponse(success=True, strategy=strategy_text)
    except Exception as e:
        return BanditStrategyResponse(success=False, error=str(e))

if __name__ == "__main__":
    port_env = os.getenv("LLM_SERVICE_PORT", "8005")
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