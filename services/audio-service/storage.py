"""
File storage management for audio files.

This module handles saving, retrieving, and managing audio files in the
service volume with proper organization and cleanup.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Tuple
import aiofiles
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError


class AudioStorage:
    """Manages audio file storage operations."""
    
    def __init__(self, base_path: str = "/app/audio_storage"):
        self.base_path = Path(base_path)
        self.recordings_path = self.base_path / "recordings"
        self.responses_path = self.base_path / "responses"
        
        # Create directories if they don't exist
        self.recordings_path.mkdir(parents=True, exist_ok=True)
        self.responses_path.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, user_id: str, original_filename: str) -> str:
        """Generate unique filename for storage."""
        file_extension = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())
        return f"{user_id}_{unique_id}{file_extension}"
    
    async def save_audio_file(self, file_content: bytes, user_id: str, 
                            original_filename: str) -> Tuple[str, dict]:
        """
        Save uploaded audio file to storage.
        
        Args:
            file_content: Raw file content
            user_id: ID of the user uploading
            original_filename: Original name of the file
            
        Returns:
            Tuple of (file_path, metadata_dict)
        """
        filename = self._generate_filename(user_id, original_filename)
        file_path = self.recordings_path / filename
        
        # Save file to disk
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        # Extract audio metadata
        metadata = await self._extract_audio_metadata(file_path)
        
        return str(file_path), metadata
    
    async def create_response_audio(self, original_file_path: str, user_id: str) -> str:
        """
        Create response audio file (currently copies the original).
        
        In the future, this could process the audio through AI models,
        add effects, or generate actual responses.
        
        Args:
            original_file_path: Path to original recording
            user_id: ID of the user
            
        Returns:
            Path to response audio file
        """
        original_path = Path(original_file_path)
        response_filename = f"{user_id}_response_{original_path.name}"
        response_path = self.responses_path / response_filename
        
        # For now, just copy the original file as response
        shutil.copy2(original_file_path, response_path)
        
        return str(response_path)
    
    async def _extract_audio_metadata(self, file_path: Path) -> dict:
        """Extract metadata from audio file."""
        try:
            audio = AudioSegment.from_file(str(file_path))
            return {
                "duration": len(audio) / 1000.0,  # Convert to seconds
                "channels": audio.channels,
                "frame_rate": audio.frame_rate,
                "sample_width": audio.sample_width,
                "format": file_path.suffix[1:].lower()
            }
        except CouldntDecodeError:
            return {
                "duration": None,
                "channels": None,
                "frame_rate": None,
                "sample_width": None,
                "format": file_path.suffix[1:].lower()
            }
    
    async def get_file_info(self, file_path: str) -> Optional[dict]:
        """Get information about a stored file."""
        path = Path(file_path)
        if not path.exists():
            return None
        
        stat = path.stat()
        return {
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "exists": True
        }
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage."""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def get_file_url(self, file_path: str) -> str:
        """Generate URL for file access."""
        # Convert absolute path to relative path for API endpoint
        path = Path(file_path)
        if path.is_relative_to(self.recordings_path):
            return f"/audio/recordings/{path.name}"
        elif path.is_relative_to(self.responses_path):
            return f"/audio/responses/{path.name}"
        else:
            return f"/audio/file/{path.name}"