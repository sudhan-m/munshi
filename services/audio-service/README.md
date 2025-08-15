# Audio Service

Audio recording and playback service for the Munshi language learning platform.

## Features

- **Audio Recording**: Upload and store audio files with metadata
- **MongoDB Integration**: Store audio metadata in MongoDB
- **File Storage**: Persistent volume storage for audio files
- **Response Generation**: Create response audio (currently mirrors input)
- **RESTful API**: FastAPI-based endpoints for all operations
- **Audio Processing**: Basic audio metadata extraction using pydub

## Endpoints

### Recording Management
- `POST /audio/record` - Upload audio recording
- `GET /audio/recordings/{user_id}` - Get user's recordings
- `GET /audio/recording/{recording_id}` - Get recording metadata
- `DELETE /audio/recording/{recording_id}` - Delete recording

### Audio Playback
- `GET /audio/play/{recording_id}` - Stream original audio
- `GET /audio/response/{recording_id}` - Stream response audio

### Health Check
- `GET /health` - Service health status

## Configuration

Environment variables:
- `MONGODB_URL` - MongoDB connection string (default: `mongodb://localhost:27017`)
- `MONGO_DB_NAME` - Database name (default: `munshi_audio`)
- `AUDIO_SERVICE_PORT` - Service port (default: `8003`)

## File Storage

Audio files are stored in persistent volumes:
- `/app/audio_storage/recordings/` - Original recordings
- `/app/audio_storage/responses/` - Response audio files

## Data Models

### AudioMetadata (MongoDB)
- `user_id` - User identifier
- `original_filename` - Original file name
- `file_path` - Storage path
- `file_size` - File size in bytes
- `duration` - Audio duration in seconds
- `format` - Audio format
- `response_file_path` - Path to response audio
- `created_at` - Creation timestamp
- `metadata` - Additional audio metadata

## API Usage Examples

### Upload Audio
```bash
curl -X POST "http://localhost:8003/audio/record" \
  -F "file=@recording.wav" \
  -F "user_id=user123"
```

### Get User Recordings
```bash
curl "http://localhost:8003/audio/recordings/user123"
```

### Play Audio
```bash
curl "http://localhost:8003/audio/play/recording_id" --output audio.wav
```

## Integration with Munshi Platform

The audio service integrates with the existing Munshi architecture:
- Uses MongoDB for metadata storage (separate from auth PostgreSQL)
- Follows the microservice pattern with dedicated endpoints
- Integrates with Kubernetes/Helm deployment
- Compatible with existing NGINX ingress routing

## Future Enhancements

- AI-powered response generation
- Audio format conversion
- Speech-to-text integration
- Language detection
- Audio quality analysis
- Real-time audio streaming