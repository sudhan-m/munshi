# ASR Service

Speech recognition service using Whisper models for multi-language support.

## Features

- Multi-language ASR (English, Tamil, Malayalam)
- GPU optimization for fast inference
- Model caching for efficient memory usage
- RESTful API interface

## Supported Languages

- **English**: openai/whisper-large-v2
- **Tamil**: vasista22/whisper-tamil-large-v2  
- **Malayalam**: thennal/whisper-medium-ml

## API Endpoints

### POST /transcribe
Transcribe audio file to text.

**Parameters:**
- `audio` (file): Audio file to transcribe
- `language` (form): Language for transcription

**Response:**
```json
{
  "success": true,
  "transcription": "transcribed text",
  "language": "English",
  "model_used": "openai/whisper-large-v2"
}
```

### GET /supported-languages
Get list of supported languages and models.

### GET /health
Health check endpoint.

## GPU Requirements

This service is designed to run on GPU pods for optimal performance. It will fallback to CPU if GPU is not available.

## Environment Variables

- `ASR_SERVICE_PORT`: Service port (default: 8004)