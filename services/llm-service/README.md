# LLM Service

Language model service using Anthropic Claude API for conversation generation, transliteration, and response generation.

## Features

- Conversation generation for language learning
- Text transliteration (Tamil/Malayalam to English romanization)
- Practice sentence generation
- Contextual response generation
- Multi-endpoint architecture for different LLM tasks

## API Endpoints

### POST /conversation
Generate conversation response for language learning.

**Request:**
```json
{
  "user_message": "I want to learn Malayalam",
  "context": [{"user": "Hello", "assistant": "Hi! How can I help you today?"}],
  "language": "Malayalam"
}
```

### POST /transliterate
Transliterate text to romanized format.

**Request:**
```json
{
  "text": "എനിക്ക് മലയാളം ഇഷ്ടമാണ്",
  "source_language": "Malayalam"
}
```

### POST /generate-sentence
Generate practice sentence for pronunciation.

**Request:**
```json
{
  "language": "Tamil",
  "difficulty": "beginner",
  "topic": "greetings"
}
```

### POST /generate-response
Generate response based on pronunciation evaluation.

**Request:**
```json
{
  "accuracy": 85.5,
  "errors": [...],
  "user_context": {"language": "Tamil", "level": "beginner"}
}
```

### GET /health
Health check endpoint.

## Environment Variables

- `ANTHROPIC_API_KEY`: Anthropic API key (required)
- `LLM_SERVICE_PORT`: Service port (default: 8005)

## Model Used

- **Claude 3 Sonnet**: claude-3-sonnet-20240229