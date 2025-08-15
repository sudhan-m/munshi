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
    def analyze_character_mispronunciations(
        intended_romanized: str,
        actual_romanized: str
    ) -> List[Dict[str, Any]]:
        """Analyze character-level pronunciation errors"""
        # Remove spaces for character comparison
        intended_chars = ''.join(intended_romanized.split())
        actual_chars = ''.join(actual_romanized.split())
        
        sm = difflib.SequenceMatcher(None, intended_chars, actual_chars)
        errors = []
        
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'replace':
                expected_char = intended_chars[i1:i2]
                actual_char = actual_chars[j1:j2]
                errors.append({
                    "type": "mispronounced_character",
                    "expected": expected_char,
                    "actual": actual_char,
                    "position": i1
                })
            elif tag == 'delete':
                missing_char = intended_chars[i1:i2]
                errors.append({
                    "type": "missing_character",
                    "expected": missing_char,
                    "actual": "",
                    "position": i1
                })
            elif tag == 'insert':
                extra_char = actual_chars[j1:j2]
                errors.append({
                    "type": "extra_character",
                    "expected": "",
                    "actual": extra_char,
                    "position": i1
                })
        
        return errors
    
    @staticmethod
    def calculate_accuracy_score(intended_words: List[str], actual_words: List[str]) -> float:
        """Calculate pronunciation accuracy percentage"""
        sm = difflib.SequenceMatcher(None, intended_words, actual_words)
        return sm.ratio() * 100
    
    
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
            
            # Analyze character-level pronunciation errors
            character_errors = self.analyze_character_mispronunciations(
                intended_romanized, actual_romanized
            )
            
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
                    "character_mispronunciations": character_errors,
                    "metadata": {
                        "language": language,
                        "total_words_expected": len(intended_words),
                        "total_words_spoken": len(actual_words),
                        "total_character_errors": len(character_errors)
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