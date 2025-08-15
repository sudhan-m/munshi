"""
Conversation Service data models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    """
    Model for chat messages.
    
    Attributes:
        role: Message role (user, assistant, system)
        content: Message content
        timestamp: Message timestamp
        metadata: Additional metadata
    """
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}

class ConversationRequest(BaseModel):
    """
    Request model for conversation.
    
    Attributes:
        user_id: ID of the user
        message: User's message
        language: Target language for learning
    """
    user_id: str
    message: str
    language: str = "English"

class ConversationResponse(BaseModel):
    """
    Response model for conversation.
    
    Attributes:
        success: Whether conversation was successful
        response: Assistant's response
        timestamp: Response timestamp
        error: Error message if conversation failed
    """
    success: bool
    response: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None

class PronunciationEvaluationRequest(BaseModel):
    """
    Request model for pronunciation evaluation.
    
    Attributes:
        user_id: ID of the user
        audio_file_id: ID of the uploaded audio file
        intended_text: Text that user was supposed to pronounce
        language: Language being evaluated
    """
    user_id: str
    audio_file_id: str
    intended_text: str
    language: str

class PronunciationEvaluationResponse(BaseModel):
    """
    Response model for pronunciation evaluation.
    
    Attributes:
        success: Whether evaluation was successful
        evaluation_results: Detailed evaluation results from evaluator service
        llm_response: Generated response from LLM
        error: Error message if evaluation failed
    """
    success: bool
    evaluation_results: Optional[Dict[str, Any]] = None
    llm_response: Optional[str] = None
    error: Optional[str] = None

class UserProfile(BaseModel):
    """
    Model for user learning profile.
    
    Attributes:
        user_id: User identifier
        preferred_language: User's preferred language to learn
        skill_level: Current skill level (beginner, intermediate, advanced)
        learning_goals: List of learning goals
        session_count: Total number of practice sessions
        total_practice_time: Total practice time in minutes
        best_accuracy: Best pronunciation accuracy achieved
        created_at: Profile creation timestamp
        last_active: Last activity timestamp
    """
    user_id: str
    preferred_language: str = "English"
    skill_level: str = "beginner"
    learning_goals: List[str] = []
    session_count: int = 0
    total_practice_time: int = 0
    best_accuracy: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)

class ConversationSession(BaseModel):
    """
    Model for conversation session.
    
    Attributes:
        session_id: Session identifier
        user_id: User identifier
        messages: List of messages in the session
        started_at: Session start timestamp
        last_activity: Last activity timestamp
        language: Language being practiced
        session_type: Type of session (chat, pronunciation, etc.)
    """
    session_id: str
    user_id: str
    messages: List[ChatMessage] = []
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    language: str = "English"
    session_type: str = "chat"

class PronunciationProfile(BaseModel):
    """
    Model for user pronunciation profile using Thompson Sampling bandits.
    
    Attributes:
        user_id: User identifier
        language: Language for this profile
        phoneme_confidences: Mapping of phonemes to confidence scores
        weakness_bandit_state: State of weakness bandit (alpha, beta values)
        strength_bandit_state: State of strength bandit (alpha, beta values)
        recent_attempts: Recent pronunciation attempts
        session_history: Historical session data
        metadata: Profile metadata including accuracy and compaction info
        created_at: Profile creation timestamp
        last_updated: Last update timestamp
    """
    user_id: str
    language: str
    phoneme_confidences: Dict[str, Dict[str, Any]] = {}
    weakness_bandit_state: Dict[str, Dict[str, int]] = {}
    strength_bandit_state: Dict[str, Dict[str, int]] = {}
    recent_attempts: List[Dict[str, Any]] = []
    session_history: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {
        "total_attempts": 0,
        "overall_accuracy": 0.0,
        "last_compaction": None
    }
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)