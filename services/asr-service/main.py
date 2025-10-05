"""
ASR Service for Whisper-based speech recognition - Cloud Run Optimized.

This service handles:
- Speech-to-text transcription using Whisper models
- Multi-language support (English, Tamil, Malayalam) 
- Cloud Run optimized for cost efficiency and cold starts
- Lazy model loading and memory optimization
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import torch
import gc
import tempfile
import os
import asyncio
import time
from transformers import WhisperForConditionalGeneration, WhisperProcessor
import librosa
from typing import Optional, Dict, Any
import uvicorn
import logging

from models import TranscriptionRequest, TranscriptionResponse
# Production optimized imports
from cloudrun_config import cloudrun_config, MemoryMonitor
from model_strategy import model_strategy
from model_cache import ExternalModelCache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Production configuration
GPU_SUPPORT = os.getenv("GPU_SUPPORT", "cuda").lower()  # Default to GPU for production
MODEL_CACHE_SIZE = int(os.getenv("MODEL_CACHE_SIZE", "3"))  # Cache multiple models

# Set PyTorch threading for optimal performance
torch.set_num_threads(cloudrun_config.get_optimal_torch_threads())
logger.info(f"Set PyTorch threads to {cloudrun_config.get_optimal_torch_threads()}")

# Log system info
cloudrun_config.log_system_info()
model_strategy.log_strategy_info()

def detect_device():
    """Detect the best available device based on environment and hardware"""
    if GPU_SUPPORT == "cpu":
        return "cpu"
    elif GPU_SUPPORT == "cuda" and torch.cuda.is_available():
        return "cuda"
    elif GPU_SUPPORT == "metal" and torch.backends.mps.is_available():
        return "mps"
    elif GPU_SUPPORT == "auto":
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    else:
        # Fallback to CPU if specified GPU type not available
        print(f"Warning: {GPU_SUPPORT} GPU not available, falling back to CPU")
        return "cpu"

DEVICE = detect_device()
print(f"ASR Service using device: {DEVICE} (GPU_SUPPORT={GPU_SUPPORT})")

# Production model configurations
MODEL_CONFIGS = {
    "English": "openai/whisper-large-v2",
    "Tamil": "vasista22/whisper-tamil-large-v2", 
    "Malayalam": "thennal/whisper-medium-ml"
}
logger.info("Using production models for optimal quality")

LANG_CODES = {
    "English": "en",
    "Tamil": "ta", 
    "Malayalam": "ml"
}

app = FastAPI(
    title="Munshi ASR Service",
    description="Speech recognition service using Whisper models",
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

class WhisperASR:
    """Production Whisper ASR with external model cache"""
    
    def __init__(self):
        self.current_model = {"language": None, "model": None, "processor": None}
        self.load_lock = asyncio.Lock()  # Prevent concurrent model loading
        self.model_load_time = None
        self.model_cache = ExternalModelCache()
    
    async def load_model(self, language_choice: str):
        """Production model loading with async lock"""
        async with self.load_lock:
            # Return cached model if available
            if (self.current_model["language"] == language_choice and 
                self.current_model["model"] is not None):
                logger.info(f"Using cached model for {language_choice}")
                return self.current_model["model"], self.current_model["processor"]
            
            # Clear previous model to free memory
            await self._clear_current_model()
            
            start_time = time.time()
            
            try:
                # Use external model cache for loading
                model, processor = await self.model_cache.get_model(language_choice, False)
                
                if model is None or processor is None:
                    raise Exception("Model loading from cache failed")
                
                # Move model to correct device
                model = model.to(DEVICE)
                
                self.current_model = {
                    "language": language_choice,
                    "model": model,
                    "processor": processor
                }
                
                self.model_load_time = time.time() - start_time
                logger.info(f"✓ Model loaded successfully for {language_choice} in {self.model_load_time:.2f}s")
                return model, processor
                
            except Exception as e:
                logger.error(f"✗ Error loading model for {language_choice}: {e}")
                
                # Final fallback to tiny model
                try:
                    logger.info("Attempting final fallback to whisper-tiny...")
                    model, processor = await self.model_cache.get_model("fallback", True)
                    
                    if model and processor:
                        model = model.to("cpu")  # Force CPU for fallback
                        
                        self.current_model = {
                            "language": language_choice,
                            "model": model,
                            "processor": processor
                        }
                        
                        self.model_load_time = time.time() - start_time
                        logger.info(f"✓ Fallback to tiny model for {language_choice} in {self.model_load_time:.2f}s")
                        return model, processor
                    else:
                        raise Exception("Fallback model loading failed")
                        
                except Exception as final_error:
                    logger.error(f"✗ All fallback attempts failed: {final_error}")
                    raise HTTPException(status_code=500, detail=f"Model loading failed: {final_error}")
    
    async def _clear_current_model(self):
        """Clear current model and free memory"""
        if self.current_model["model"] is not None:
            logger.info("Clearing previous model to free memory")
            MemoryMonitor.log_memory_status()
            
            del self.current_model["model"]
            del self.current_model["processor"]
            gc.collect()
            if DEVICE == "cuda":
                torch.cuda.empty_cache()
            self.current_model = {"language": None, "model": None, "processor": None}
            
            # Log memory status after cleanup
            MemoryMonitor.log_memory_status()
    
    async def transcribe(self, audio_path: str, language_choice: str) -> str:
        """Cloud Run optimized transcription using Whisper"""
        model, processor = await self.load_model(language_choice)
        lang_code = LANG_CODES.get(language_choice, "en")
        
        start_time = time.time()
        
        # Load audio with error handling
        try:
            audio, sr = librosa.load(audio_path, sr=16000)
        except Exception as e:
            logger.error(f"Error loading audio: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid audio file: {e}")
        
        # Process audio
        input_features = processor(audio, sampling_rate=16000, return_tensors="pt").input_features
        input_features = input_features.to(DEVICE, dtype=next(model.parameters()).dtype)
        
        # Production optimized inference settings
        max_length = 448  # Full length for quality
        num_beams = 5  # Beam search for quality
        do_sample = False  # Deterministic output
        temperature = 0.0
        
        # Generate transcription
        with torch.no_grad():
            try:
                forced_decoder_ids = processor.get_decoder_prompt_ids(language=lang_code, task="transcribe")
                predicted_ids = model.generate(
                    input_features,
                    forced_decoder_ids=forced_decoder_ids,
                    max_length=max_length,
                    num_beams=num_beams,
                    temperature=temperature,
                    do_sample=do_sample
                )
            except Exception as decode_error:
                logger.warning(f"Language-specific decoding failed: {decode_error}, using generic")
                predicted_ids = model.generate(
                    input_features,
                    max_length=max_length,
                    num_beams=num_beams,
                    temperature=temperature,
                    do_sample=do_sample
                )
        
        transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        
        inference_time = time.time() - start_time
        logger.info(f"Transcription completed in {inference_time:.2f}s")
        
        return transcription.strip()

# Initialize ASR
asr = WhisperASR()

@app.get("/health")
async def health_check():
    """Cloud Run health check endpoint."""
    memory_status = MemoryMonitor.get_memory_usage()
    
    return {
        "status": "healthy", 
        "service": "asr-service-production", 
        "device": DEVICE,
        "gpu_support": GPU_SUPPORT,
        "cuda_available": torch.cuda.is_available(),
        "mps_available": torch.backends.mps.is_available() if hasattr(torch.backends, 'mps') else False,
        "model_cache_size": MODEL_CACHE_SIZE,
        "current_model": asr.current_model["language"] if asr.current_model["model"] else None,
        "model_load_time": asr.model_load_time,
        "model_configs": MODEL_CONFIGS,
        "memory_status": {
            "used_mb": round(memory_status["used_mb"], 1),
            "available_mb": round(memory_status["available_mb"], 1),
            "percentage": round(memory_status["percentage"], 1)
        },
        "max_audio_size_mb": round(cloudrun_config.get_max_audio_size() / (1024**2), 1)
    }

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form(...)
):
    """
    Production audio transcription endpoint.
    
    Args:
        audio: Audio file to transcribe
        language: Language for transcription (English, Tamil, Malayalam)
        
    Returns:
        TranscriptionResponse with transcribed text
    """
    request_start = time.time()
    
    if language not in MODEL_CONFIGS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported language: {language}. Supported: {list(MODEL_CONFIGS.keys())}"
        )
    
    # Validate file type and size
    allowed_types = ["audio/wav", "audio/mpeg", "audio/mp3", "audio/ogg", "audio/webm", "audio/m4a"]
    if audio.content_type and audio.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {audio.content_type}"
        )
    
    # Dynamic file size limit based on available memory
    max_size = cloudrun_config.get_max_audio_size()
    
    temp_file_path = None
    try:
        # Read and validate file size
        content = await audio.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"Audio file too large: {len(content)/1024/1024:.1f}MB. Max: {max_size/1024/1024:.1f}MB"
            )
        
        # Check memory pressure before processing
        if MemoryMonitor.check_memory_pressure():
            logger.warning("High memory usage detected, forcing garbage collection")
            gc.collect()
            if MemoryMonitor.check_memory_pressure():
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily overloaded. Please try again in a moment."
                )
        
        # Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav", prefix="asr_") as temp_file:
            temp_file.write(content)
            temp_file.flush()
            temp_file_path = temp_file.name
            
            logger.info(f"Processing audio: {len(content)} bytes, language: {language}")
            
            # Transcribe
            transcription = await asr.transcribe(temp_file_path, language)
            
            # Clean up temp file
            os.unlink(temp_file_path)
            temp_file_path = None
            
            total_time = time.time() - request_start
            logger.info(f"Request completed in {total_time:.2f}s")
            
            # Log final memory status
            MemoryMonitor.log_memory_status()
            
            return TranscriptionResponse(
                success=True,
                transcription=transcription,
                language=language,
                model_used=MODEL_CONFIGS[language]
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        if temp_file_path:
            try:
                os.unlink(temp_file_path)
            except:
                pass
        raise
        
    except Exception as e:
        # Clean up temp file if it exists
        if temp_file_path:
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
        logger.error(f"Transcription error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error during transcription: {str(e)}"
        )

@app.get("/supported-languages")
async def get_supported_languages():
    """Get list of supported languages."""
    return {
        "languages": list(MODEL_CONFIGS.keys()),
        "models": MODEL_CONFIGS
    }

@app.get("/cache-info")
async def get_cache_info():
    """Get model cache information."""
    return asr.model_cache.get_cache_info()

@app.post("/clear-cache")
async def clear_cache(model_id: Optional[str] = None):
    """Clear model cache."""
    try:
        asr.model_cache.clear_cache(model_id)
        # Also clear in-memory cache
        await asr._clear_current_model()
        return {"success": True, "message": f"Cache cleared for {model_id or 'all models'}"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {e}")

if __name__ == "__main__":
    # Production server configuration
    port = int(os.getenv("PORT", os.getenv("ASR_SERVICE_PORT", 8004)))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        access_log=True,
        log_level="info"
    )