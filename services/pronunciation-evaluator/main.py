"""
Pronunciation Evaluator Service.

This service handles:
- Pronunciation accuracy calculation
- Word-level error analysis
- Pronunciation scoring and feedback
- Detailed evaluation metrics
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import difflib
import string
import jiwer
from typing import List, Dict, Any
import uvicorn

from models import (
    EvaluationRequest, EvaluationResponse,
    PronunciationError, PronunciationMetrics,
    PronunciationResults
)

app = FastAPI(
    title="Munshi Pronunciation Evaluator",
    description="Pronunciation evaluation and scoring service",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PronunciationEvaluator:
    """Pronunciation evaluation logic"""
    
    @staticmethod
    def normalize_text_for_comparison(text: str) -> str:
        """Remove punctuation and normalize text for fair comparison"""
        text = text.translate(str.maketrans('', '', string.punctuation))
        text = ' '.join(text.split())
        return text.lower()
    
    @staticmethod
    def analyze_pronunciation_errors(
        intended_words: List[str], 
        actual_words: List[str],
        intended_romanized: List[str],
        actual_romanized: List[str]
    ) -> List[Dict[str, Any]]:
        """Analyze word-level pronunciation errors"""
        sm = difflib.SequenceMatcher(None, intended_words, actual_words)
        errors = []
        
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'replace':
                for idx in range(max(i2-i1, j2-j1)):
                    expected_word = intended_words[i1 + idx] if (i1 + idx) < i2 else ""
                    actual_word = actual_words[j1 + idx] if (j1 + idx) < j2 else ""
                    expected_roman = intended_romanized[i1 + idx] if (i1 + idx) < len(intended_romanized) and (i1 + idx) < i2 else ""
                    actual_roman = actual_romanized[j1 + idx] if (j1 + idx) < len(actual_romanized) and (j1 + idx) < j2 else ""
                    
                    if expected_word and actual_word and expected_word != actual_word:
                        errors.append({
                            "type": "mispronounced",
                            "expected_word": expected_word,
                            "expected_romanized": expected_roman,
                            "actual_word": actual_word,
                            "actual_romanized": actual_roman
                        })
            
            elif tag == 'delete':
                for idx in range(i2-i1):
                    expected_word = intended_words[i1 + idx]
                    expected_roman = intended_romanized[i1 + idx] if (i1 + idx) < len(intended_romanized) else ""
                    errors.append({
                        "type": "missing",
                        "expected_word": expected_word,
                        "expected_romanized": expected_roman,
                        "actual_word": "(Not spoken)",
                        "actual_romanized": ""
                    })
            
            elif tag == 'insert':
                for idx in range(j2-j1):
                    actual_word = actual_words[j1 + idx]
                    actual_roman = actual_romanized[j1 + idx] if (j1 + idx) < len(actual_romanized) else ""
                    errors.append({
                        "type": "extra",
                        "expected_word": "(Not expected)",
                        "expected_romanized": "",
                        "actual_word": actual_word,
                        "actual_romanized": actual_roman
                    })
        
        return errors
    
    @staticmethod
    def calculate_accuracy_score(intended_words: List[str], actual_words: List[str]) -> float:
        """Calculate pronunciation accuracy percentage"""
        sm = difflib.SequenceMatcher(None, intended_words, actual_words)
        return sm.ratio() * 100
    
    @staticmethod
    def get_feedback_message(accuracy: float) -> str:
        """Generate motivational feedback message"""
        if accuracy >= 95:
            return "🎉 Outstanding! Perfect pronunciation!"
        elif accuracy >= 85:
            return "🌟 Excellent! Very natural sounding!"
        elif accuracy >= 70:
            return "👍 Good job! Your pronunciation is improving!"
        elif accuracy >= 50:
            return "📚 Getting there! Focus on the highlighted sounds!"
        else:
            return "💪 Keep practicing! Every attempt makes you better!"
    
    def evaluate_pronunciation(
        self,
        intended_text: str,
        actual_text: str,
        intended_romanized: str,
        actual_romanized: str,
        language: str
    ) -> Dict[str, Any]:
        """Main evaluation function"""
        try:
            if not intended_text.strip() or not actual_text.strip():
                return {
                    "success": False,
                    "error": "Missing intended or actual text",
                    "results": None
                }
            
            # Normalize for comparison
            intended_normalized = self.normalize_text_for_comparison(intended_text)
            actual_normalized = self.normalize_text_for_comparison(actual_text)
            intended_romanized_normalized = self.normalize_text_for_comparison(intended_romanized)
            actual_romanized_normalized = self.normalize_text_for_comparison(actual_romanized)
            
            # Split into words
            intended_words = intended_normalized.split()
            actual_words = actual_normalized.split()
            intended_romanized_words = intended_romanized_normalized.split()
            actual_romanized_words = actual_romanized_normalized.split()
            
            # Calculate metrics
            accuracy = self.calculate_accuracy_score(intended_words, actual_words)
            
            # Calculate WER and CER
            try:
                wer_val = jiwer.wer(intended_text, actual_text)
                cer_val = jiwer.cer(intended_text, actual_text)
            except:
                wer_val = 0.0
                cer_val = 0.0
            
            # Analyze errors
            pronunciation_errors = self.analyze_pronunciation_errors(
                intended_words, actual_words,
                intended_romanized_words, actual_romanized_words
            )
            
            # Generate feedback
            feedback_message = self.get_feedback_message(accuracy)
            
            results = {
                "success": True,
                "error": None,
                "results": {
                    "target": {
                        "text": intended_text,
                        "romanized": intended_romanized
                    },
                    "transcription": {
                        "text": actual_text,
                        "romanized": actual_romanized
                    },
                    "metrics": {
                        "accuracy_percentage": round(accuracy, 1),
                        "word_error_rate": round(wer_val * 100, 1),
                        "character_error_rate": round(cer_val * 100, 1)
                    },
                    "pronunciation_errors": pronunciation_errors,
                    "feedback": {
                        "message": feedback_message,
                        "total_errors": len(pronunciation_errors)
                    },
                    "metadata": {
                        "language": language,
                        "total_words_expected": len(intended_words),
                        "total_words_spoken": len(actual_words)
                    }
                }
            }
            
            return results
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Evaluation error: {str(e)}",
                "results": None
            }

# Initialize evaluator
evaluator = PronunciationEvaluator()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "pronunciation-evaluator"}

@app.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_pronunciation(request: EvaluationRequest):
    """
    Evaluate pronunciation accuracy and provide detailed feedback.
    
    Args:
        request: Evaluation request with intended and actual text
        
    Returns:
        EvaluationResponse with detailed evaluation results
    """
    try:
        result = evaluator.evaluate_pronunciation(
            request.intended_text,
            request.actual_text,
            request.intended_romanized,
            request.actual_romanized,
            request.language
        )
        
        if result["success"]:
            return EvaluationResponse(
                success=True,
                results=PronunciationResults(**result["results"])
            )
        else:
            return EvaluationResponse(
                success=False,
                error=result["error"]
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error during pronunciation evaluation: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("EVALUATOR_SERVICE_PORT", 8006)),
        reload=True
    )