"""
Pronunciation Evaluator Service data models.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class PronunciationError(BaseModel):
    """
    Model for pronunciation error analysis.
    
    Attributes:
        type: Type of error (mispronounced, missing, extra)
        expected_word: The expected word
        expected_romanized: Romanized version of expected word
        actual_word: The actual word spoken
        actual_romanized: Romanized version of actual word
    """
    type: str
    expected_word: str
    expected_romanized: str
    actual_word: str
    actual_romanized: str

class PronunciationTarget(BaseModel):
    """
    Model for target pronunciation text.
    
    Attributes:
        text: Target text in original language
        romanized: Romanized version of target text
    """
    text: str
    romanized: str

class PronunciationTranscription(BaseModel):
    """
    Model for pronunciation transcription results.
    
    Attributes:
        text: Transcribed text
        romanized: Romanized version of transcribed text
    """
    text: str
    romanized: str

class PronunciationMetrics(BaseModel):
    """
    Model for pronunciation evaluation metrics.
    
    Attributes:
        accuracy_percentage: Overall accuracy percentage
        word_error_rate: Word error rate percentage
        character_error_rate: Character error rate percentage
    """
    accuracy_percentage: float
    word_error_rate: float
    character_error_rate: float

class PronunciationFeedback(BaseModel):
    """
    Model for pronunciation feedback.
    
    Attributes:
        message: Motivational feedback message
        total_errors: Total number of errors found
    """
    message: str
    total_errors: int

class PronunciationMetadata(BaseModel):
    """
    Model for pronunciation evaluation metadata.
    
    Attributes:
        language: Language being evaluated
        total_words_expected: Number of words expected
        total_words_spoken: Number of words actually spoken
    """
    language: str
    total_words_expected: int
    total_words_spoken: int

class PronunciationResults(BaseModel):
    """
    Model for complete pronunciation evaluation results.
    
    Attributes:
        target: Target pronunciation information
        transcription: Actual transcription results
        metrics: Evaluation metrics
        pronunciation_errors: List of pronunciation errors
        feedback: User feedback
        metadata: Evaluation metadata
    """
    target: PronunciationTarget
    transcription: PronunciationTranscription
    metrics: PronunciationMetrics
    pronunciation_errors: List[PronunciationError]
    feedback: PronunciationFeedback
    metadata: PronunciationMetadata

class EvaluationRequest(BaseModel):
    """
    Request model for pronunciation evaluation.
    
    Attributes:
        intended_text: Text that user was supposed to pronounce
        actual_text: Text that was actually transcribed
        intended_romanized: Romanized version of intended text
        actual_romanized: Romanized version of actual text
        language: Language being evaluated
    """
    intended_text: str
    actual_text: str
    intended_romanized: str
    actual_romanized: str
    language: str

class EvaluationResponse(BaseModel):
    """
    Response model for pronunciation evaluation.
    
    Attributes:
        success: Whether evaluation was successful
        results: Evaluation results if successful
        error: Error message if evaluation failed
    """
    success: bool
    results: Optional[PronunciationResults] = None
    error: Optional[str] = None