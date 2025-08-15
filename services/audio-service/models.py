"""
Audio service data models.

This module defines MongoDB models and Pydantic schemas for audio recording,
metadata storage, and API request/response structures.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class AudioMetadata(BaseModel):
    """
    MongoDB model for audio recording metadata.
    
    Stores information about recorded audio files including user data,
    timestamps, file paths, and response metadata.
    
    Attributes:
        id: MongoDB ObjectId as string
        user_id: ID of the user who created the recording
        original_filename: Original name of the uploaded file
        file_path: Path to stored audio file in volume
        file_size: Size of audio file in bytes
        duration: Duration of audio in seconds
        format: Audio format (wav, mp3, etc.)
        response_file_path: Path to response audio file
        created_at: Recording timestamp
        metadata: Additional metadata dict
    """
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    original_filename: str
    file_path: str
    file_size: int
    duration: Optional[float] = None
    format: str
    response_file_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = {}

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class AudioUploadResponse(BaseModel):
    """
    Response model for successful audio upload.
    
    Attributes:
        id: Audio record ID
        message: Success message
        file_path: Path to stored file
        response_file_path: Path to response audio file
        created_at: Timestamp when recording was created
        duration: Duration of audio in seconds
        metadata: Audio metadata
    """
    id: str
    message: str
    file_path: str
    response_file_path: str
    created_at: datetime
    duration: Optional[float] = None
    metadata: Dict[str, Any]


class AudioListResponse(BaseModel):
    """
    Response model for audio listing.
    
    Attributes:
        recordings: List of audio recordings
        total: Total number of recordings
    """
    recordings: list[AudioMetadata]
    total: int


class AudioPlaybackResponse(BaseModel):
    """
    Response model for audio playback requests.
    
    Attributes:
        id: Audio record ID
        file_path: Path to audio file
        metadata: Audio metadata
    """
    id: str
    file_path: str
    metadata: Dict[str, Any]