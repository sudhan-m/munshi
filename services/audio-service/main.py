"""
Audio recording and playback service for the Munshi language learning platform.

This service handles:
- Audio file upload and storage
- Metadata storage in MongoDB
- Audio playback and download
- Response audio generation (currently mirrors input)
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
from datetime import datetime
import uuid

from database import connect_to_mongo, close_mongo_connection, get_audio_collection
from storage import AudioStorage
from models import AudioMetadata, AudioUploadResponse, AudioListResponse, AudioPlaybackResponse

app = FastAPI(
    title="Munshi Audio Service",
    description="Audio recording and playback service for language learning",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize storage
audio_storage = AudioStorage()


@app.on_event("startup")
async def startup_event():
    """Initialize database connections on startup."""
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown."""
    await close_mongo_connection()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "audio-service"}


@app.post("/audio/record", response_model=AudioUploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    """
    Upload and store audio recording.
    
    Args:
        file: Audio file upload
        user_id: ID of the user making the recording
        
    Returns:
        AudioUploadResponse with file paths and metadata
    """
    return await _process_audio_upload(file, user_id)


@app.post("/audio/upload", response_model=AudioUploadResponse)  
async def upload_audio_legacy(
    audio: UploadFile = File(...),  # Legacy frontend sends 'audio' parameter
    user_id: str = Form(default="demo_user")  # Default user for legacy requests
):
    """
    Legacy upload endpoint for backwards compatibility.
    
    Args:
        audio: Audio file upload (legacy parameter name)
        user_id: ID of the user making the recording
        
    Returns:
        AudioUploadResponse with file paths and metadata
    """
    return await _process_audio_upload(audio, user_id)


async def _process_audio_upload(file: UploadFile, user_id: str):
    """
    Internal function to process audio upload.
    
    Args:
        file: Audio file upload
        user_id: ID of the user making the recording
        
    Returns:
        AudioUploadResponse with file paths and metadata
    """
    # Validate file type - allow any for webm from browser
    allowed_types = ["audio/wav", "audio/mpeg", "audio/mp3", "audio/ogg", "audio/webm"]
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {file.content_type}"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Save original audio file
        file_path, audio_metadata = await audio_storage.save_audio_file(
            file_content, user_id, file.filename
        )
        
        # Create response audio (currently same as original)
        response_file_path = await audio_storage.create_response_audio(
            file_path, user_id
        )
        
        # Create metadata record
        metadata_record = AudioMetadata(
            user_id=user_id,
            original_filename=file.filename,
            file_path=file_path,
            file_size=len(file_content),
            duration=audio_metadata.get("duration"),
            format=audio_metadata.get("format", "unknown"),
            response_file_path=response_file_path,
            metadata=audio_metadata
        )
        
        # Save to MongoDB
        collection = get_audio_collection()
        result = await collection.insert_one(metadata_record.model_dump(by_alias=True, exclude={"id"}))
        
        return AudioUploadResponse(
            id=str(result.inserted_id),
            message="Audio recorded and processed successfully",
            file_path=audio_storage.get_file_url(file_path),
            response_file_path=audio_storage.get_file_url(response_file_path),
            created_at=metadata_record.created_at,
            duration=metadata_record.duration,
            metadata=audio_metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")


@app.get("/audio/recordings/{user_id}", response_model=AudioListResponse)
async def get_user_recordings(user_id: str, limit: int = 10, offset: int = 0):
    """
    Get list of audio recordings for a user.
    
    Args:
        user_id: ID of the user
        limit: Maximum number of recordings to return
        offset: Number of recordings to skip
        
    Returns:
        AudioListResponse with recordings list and total count
    """
    try:
        collection = get_audio_collection()
        
        # Get total count
        total = await collection.count_documents({"user_id": user_id})
        
        # Get recordings with pagination
        cursor = collection.find(
            {"user_id": user_id}
        ).sort("created_at", -1).skip(offset).limit(limit)
        
        recordings = []
        async for doc in cursor:
            recordings.append(AudioMetadata(**doc))
        
        return AudioListResponse(recordings=recordings, total=total)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recordings: {str(e)}")


@app.get("/audio/recording/{recording_id}", response_model=AudioPlaybackResponse)
async def get_recording(recording_id: str):
    """
    Get metadata for a specific recording.
    
    Args:
        recording_id: ID of the recording
        
    Returns:
        AudioPlaybackResponse with recording metadata
    """
    try:
        from bson import ObjectId
        from bson.errors import InvalidId
        collection = get_audio_collection()
        
        # Validate ObjectId format
        try:
            object_id = ObjectId(recording_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid recording ID format")
        
        doc = await collection.find_one({"_id": object_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        # Convert ObjectId to string for Pydantic model
        doc["_id"] = str(doc["_id"])
        metadata = AudioMetadata(**doc)
        
        return AudioPlaybackResponse(
            id=str(metadata.id),
            file_path=audio_storage.get_file_url(metadata.file_path),
            metadata=metadata.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recording: {str(e)}")


@app.get("/audio/play/{recording_id}")
async def play_original_audio(recording_id: str):
    """
    Stream original audio file for playback.
    
    Args:
        recording_id: ID of the recording
        
    Returns:
        FileResponse with audio file
    """
    try:
        from bson import ObjectId
        from bson.errors import InvalidId
        collection = get_audio_collection()
        
        # Validate ObjectId format
        try:
            object_id = ObjectId(recording_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid recording ID format")
        
        doc = await collection.find_one({"_id": object_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        # Convert ObjectId to string for Pydantic model
        doc["_id"] = str(doc["_id"])
        metadata = AudioMetadata(**doc)
        file_info = await audio_storage.get_file_info(metadata.file_path)
        
        if not file_info or not file_info["exists"]:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(
            path=metadata.file_path,
            media_type="audio/mpeg",
            filename=metadata.original_filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error playing audio: {str(e)}")


@app.get("/audio/response/{recording_id}")
async def play_response_audio(recording_id: str):
    """
    Stream response audio file for playback.
    
    Args:
        recording_id: ID of the recording
        
    Returns:
        FileResponse with response audio file
    """
    try:
        from bson import ObjectId
        from bson.errors import InvalidId
        collection = get_audio_collection()
        
        # Validate ObjectId format
        try:
            object_id = ObjectId(recording_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid recording ID format")
        
        doc = await collection.find_one({"_id": object_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        # Convert ObjectId to string for Pydantic model
        doc["_id"] = str(doc["_id"])
        metadata = AudioMetadata(**doc)
        
        if not metadata.response_file_path:
            raise HTTPException(status_code=404, detail="Response audio not available")
        
        file_info = await audio_storage.get_file_info(metadata.response_file_path)
        if not file_info or not file_info["exists"]:
            raise HTTPException(status_code=404, detail="Response audio file not found")
        
        return FileResponse(
            path=metadata.response_file_path,
            media_type="audio/mpeg",
            filename=f"response_{metadata.original_filename}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error playing response audio: {str(e)}")


@app.delete("/audio/recording/{recording_id}")
async def delete_recording(recording_id: str):
    """
    Delete an audio recording and its files.
    
    Args:
        recording_id: ID of the recording to delete
        
    Returns:
        Success message
    """
    try:
        from bson import ObjectId
        from bson.errors import InvalidId
        collection = get_audio_collection()
        
        # Validate ObjectId format
        try:
            object_id = ObjectId(recording_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Invalid recording ID format")
        
        # Get recording metadata
        doc = await collection.find_one({"_id": object_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Recording not found")
        
        # Convert ObjectId to string for Pydantic model
        doc["_id"] = str(doc["_id"])
        metadata = AudioMetadata(**doc)
        
        # Delete files from storage
        await audio_storage.delete_file(metadata.file_path)
        if metadata.response_file_path:
            await audio_storage.delete_file(metadata.response_file_path)
        
        # Delete from database
        await collection.delete_one({"_id": object_id})
        
        return {"message": "Recording deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting recording: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("AUDIO_SERVICE_PORT", 8003)),
        reload=True
    )