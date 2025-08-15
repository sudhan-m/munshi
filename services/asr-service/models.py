"""
ASR Service data models.
"""

from pydantic import BaseModel
from typing import Optional

class TranscriptionRequest(BaseModel):
    """
    Request model for transcription.
    
    Attributes:
        language: Language for transcription (English, Tamil, Malayalam)
    """
    language: str

class TranscriptionResponse(BaseModel):
    """
    Response model for transcription.
    
    Attributes:
        success: Whether transcription was successful
        transcription: Transcribed text
        language: Language used for transcription
        model_used: Whisper model used
        error: Error message if transcription failed
    """
    success: bool
    transcription: Optional[str] = None
    language: Optional[str] = None
    model_used: Optional[str] = None
    error: Optional[str] = None