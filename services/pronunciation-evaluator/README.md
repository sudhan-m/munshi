# Pronunciation Evaluator Service

Service for evaluating pronunciation accuracy and providing detailed feedback on speech performance.

## Features

- Pronunciation accuracy calculation
- Word-level error analysis
- Detailed pronunciation scoring
- Motivational feedback generation
- Multi-language support

## API Endpoints

### POST /evaluate
Evaluate pronunciation accuracy between intended and actual speech.

**Request:**
```json
{
  "intended_text": "Hello, how are you?",
  "actual_text": "Hello, how are you?",
  "intended_romanized": "Hello, how are you?",
  "actual_romanized": "Hello, how are you?",
  "language": "English"
}
```

**Response:**
```json
{
  "success": true,
  "results": {
    "target": {
      "text": "Hello, how are you?",
      "romanized": "Hello, how are you?"
    },
    "transcription": {
      "text": "Hello, how are you?",
      "romanized": "Hello, how are you?"
    },
    "metrics": {
      "accuracy_percentage": 100.0,
      "word_error_rate": 0.0,
      "character_error_rate": 0.0
    },
    "pronunciation_errors": [],
    "feedback": {
      "message": "🎉 Outstanding! Perfect pronunciation!",
      "total_errors": 0
    },
    "metadata": {
      "language": "English",
      "total_words_expected": 4,
      "total_words_spoken": 4
    }
  }
}
```

### GET /health
Health check endpoint.

## Evaluation Metrics

- **Accuracy Percentage**: Overall similarity between intended and actual speech
- **Word Error Rate (WER)**: Percentage of words that were incorrect
- **Character Error Rate (CER)**: Percentage of characters that were incorrect

## Error Types

- **Mispronounced**: Words pronounced differently than expected
- **Missing**: Words that were expected but not spoken
- **Extra**: Words that were spoken but not expected

## Environment Variables

- `EVALUATOR_SERVICE_PORT`: Service port (default: 8006)