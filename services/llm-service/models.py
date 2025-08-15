"""
LLM Service data models.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ConversationRequest(BaseModel):
    """
    Request model for conversation generation.
    
    Attributes:
        user_message: User's input message
        context: Previous conversation context
        language: Target language for learning
    """
    user_message: str
    context: List[Dict[str, str]] = []
    language: str

class ConversationResponse(BaseModel):
    """
    Response model for conversation generation.
    
    Attributes:
        success: Whether generation was successful
        response: Generated response text
        error: Error message if generation failed
    """
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None

class TransliterationRequest(BaseModel):
    """
    Request model for text transliteration.
    
    Attributes:
        text: Text to transliterate
        source_language: Source language (Tamil, Malayalam, English)
    """
    text: str
    source_language: str

class TransliterationResponse(BaseModel):
    """
    Response model for text transliteration.
    
    Attributes:
        success: Whether transliteration was successful
        original_text: Original input text
        romanized_text: Romanized output text
        source_language: Source language used
        error: Error message if transliteration failed
    """
    success: bool
    original_text: Optional[str] = None
    romanized_text: Optional[str] = None
    source_language: Optional[str] = None
    error: Optional[str] = None

class SentenceGenerationRequest(BaseModel):
    """
    Request model for practice sentence generation.
    
    Attributes:
        language: Target language for sentence
        difficulty: Difficulty level (beginner, intermediate, advanced)
        topic: Optional topic focus
        target_phonemes: Phonemes to focus on based on pronunciation profiling
        pronunciation_profile: User's pronunciation profile context
    """
    language: str
    difficulty: str = "beginner"
    topic: Optional[str] = None
    target_phonemes: Optional[List[str]] = None
    pronunciation_profile: Optional[Dict[str, Any]] = None

class SentenceGenerationResponse(BaseModel):
    """
    Response model for practice sentence generation.
    
    Attributes:
        success: Whether generation was successful
        sentence_data: Generated sentence data with original, romanized, and combined formats
        error: Error message if generation failed
    """
    success: bool
    sentence_data: Optional[Dict[str, str]] = None
    error: Optional[str] = None

class ResponseGenerationRequest(BaseModel):
    """
    Request model for evaluation response generation.
    
    Attributes:
        accuracy: Pronunciation accuracy percentage
        errors: List of pronunciation errors
        user_context: User learning context
    """
    accuracy: float
    errors: List[Dict[str, Any]]
    user_context: Dict[str, Any]

class ResponseGenerationResponse(BaseModel):
    """
    Response model for evaluation response generation.
    
    Attributes:
        success: Whether generation was successful
        response: Generated response text
        error: Error message if generation failed
    """
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None

class BanditStrategyRequest(BaseModel):
    """
    Request model for bandit strategy analysis.
    
    Attributes:
        prompt: Analysis prompt for LLM
    """
    prompt: str

class BanditStrategyResponse(BaseModel):
    """
    Response model for bandit strategy analysis.
    
    Attributes:
        success: Whether analysis was successful
        strategy: Recommended strategy (CHALLENGE or ENCOURAGE)
        error: Error message if analysis failed
    """
    success: bool
    strategy: Optional[str] = None
    error: Optional[str] = None