"""
Model cache management for external storage.
Downloads models from GCS to local cache on-demand.
"""

import os
import json
import hashlib
import tempfile
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from google.cloud import storage
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

logger = logging.getLogger(__name__)

class ExternalModelCache:
    """Manages model caching with external storage (GCS) backend."""
    
    def __init__(self, bucket_name: str = None, cache_dir: str = None):
        self.bucket_name = bucket_name or os.getenv("MODEL_STORAGE_BUCKET", "munshi-models")
        self.cache_dir = Path(cache_dir or os.getenv("MODEL_CACHE_DIR", "/tmp/model_cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.manifest_cache = {}
        
        # Production model configurations
        self.model_configs = {
            "English": "openai/whisper-large-v2",
            "Tamil": "vasista22/whisper-tamil-large-v2", 
            "Malayalam": "thennal/whisper-medium-ml"
        }
        
    def _get_storage_client(self):
        """Lazy initialization of GCS client."""
        if self.client is None:
            try:
                self.client = storage.Client()
                logger.info(f"Connected to GCS bucket: {self.bucket_name}")
            except Exception as e:
                logger.warning(f"Failed to connect to GCS: {e}")
                self.client = False  # Mark as failed
        return self.client
        
    def _get_model_hash(self, model_id: str) -> str:
        """Generate hash for model identification."""
        return hashlib.md5(model_id.encode()).hexdigest()[:8]
        
    def _get_local_model_path(self, model_id: str) -> Path:
        """Get local cache path for model."""
        model_hash = self._get_model_hash(model_id)
        return self.cache_dir / f"model_{model_hash}"
        
    def _get_gcs_model_path(self, model_id: str) -> str:
        """Get GCS path for model."""
        model_hash = self._get_model_hash(model_id)
        return f"models/{model_hash}"
        
    def _model_exists_locally(self, model_id: str) -> bool:
        """Check if model exists in local cache."""
        model_path = self._get_local_model_path(model_id)
        return (model_path / "pytorch_model.bin").exists() and (model_path / "config.json").exists()
        
    def _model_exists_gcs(self, model_id: str) -> bool:
        """Check if model exists in GCS."""
        client = self._get_storage_client()
        if not client:
            return False
            
        try:
            bucket = client.bucket(self.bucket_name)
            gcs_path = self._get_gcs_model_path(model_id)
            blob = bucket.blob(f"{gcs_path}/manifest.json")
            return blob.exists()
        except Exception as e:
            logger.warning(f"Error checking GCS model existence: {e}")
            return False
            
    def _download_from_gcs(self, model_id: str) -> bool:
        """Download model from GCS to local cache."""
        client = self._get_storage_client()
        if not client:
            return False
            
        try:
            bucket = client.bucket(self.bucket_name)
            gcs_path = self._get_gcs_model_path(model_id)
            local_path = self._get_local_model_path(model_id)
            local_path.mkdir(parents=True, exist_ok=True)
            
            # Download manifest first
            manifest_blob = bucket.blob(f"{gcs_path}/manifest.json")
            manifest_data = json.loads(manifest_blob.download_as_text())
            
            logger.info(f"Downloading model {model_id} from GCS...")
            
            # Download all files listed in manifest
            for file_name in manifest_data["files"]:
                blob = bucket.blob(f"{gcs_path}/{file_name}")
                local_file = local_path / file_name
                blob.download_to_filename(str(local_file))
                
            logger.info(f"✓ Model {model_id} downloaded to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading model from GCS: {e}")
            return False
            
    def _download_from_huggingface(self, model_id: str) -> bool:
        """Download model from HuggingFace and cache locally."""
        try:
            local_path = self._get_local_model_path(model_id)
            local_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading model {model_id} from HuggingFace...")
            
            # Download model and processor
            model = WhisperForConditionalGeneration.from_pretrained(
                model_id,
                cache_dir=str(local_path),
                local_files_only=False
            )
            processor = WhisperProcessor.from_pretrained(
                model_id,
                cache_dir=str(local_path),
                local_files_only=False
            )
            
            # Save to our cache structure
            model.save_pretrained(str(local_path))
            processor.save_pretrained(str(local_path))
            
            logger.info(f"✓ Model {model_id} downloaded and cached")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading model from HuggingFace: {e}")
            return False
            
    def _upload_to_gcs(self, model_id: str) -> bool:
        """Upload model from local cache to GCS."""
        client = self._get_storage_client()
        if not client:
            return False
            
        try:
            bucket = client.bucket(self.bucket_name)
            local_path = self._get_local_model_path(model_id)
            gcs_path = self._get_gcs_model_path(model_id)
            
            if not local_path.exists():
                return False
                
            logger.info(f"Uploading model {model_id} to GCS...")
            
            # Create manifest of files to upload
            files_to_upload = []
            for file_path in local_path.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(local_path)
                    files_to_upload.append(str(rel_path))
                    
                    # Upload file
                    blob = bucket.blob(f"{gcs_path}/{rel_path}")
                    blob.upload_from_filename(str(file_path))
            
            # Upload manifest
            from datetime import datetime
            manifest = {
                "model_id": model_id,
                "files": files_to_upload,
                "upload_time": str(datetime.now())
            }
            manifest_blob = bucket.blob(f"{gcs_path}/manifest.json")
            manifest_blob.upload_from_string(json.dumps(manifest))
            
            logger.info(f"✓ Model {model_id} uploaded to GCS")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading model to GCS: {e}")
            return False
    
    async def get_model(self, language: str, fallback_mode: bool = False) -> Tuple[Optional[object], Optional[object]]:
        """
        Get model and processor, downloading if necessary.
        
        Args:
            language: Language choice (English, Tamil, Malayalam)
            fallback_mode: Ignored - always use production models
            
        Returns:
            Tuple of (model, processor) or (None, None) if failed
        """
        # Use production model for language
        model_id = self.model_configs.get(language)
        if not model_id:
            logger.error(f"Unsupported language: {language}")
            return None, None
            
        logger.info(f"Requesting production model: {model_id}")
        
        # Try loading from local cache first
        if self._model_exists_locally(model_id):
            try:
                local_path = self._get_local_model_path(model_id)
                model = WhisperForConditionalGeneration.from_pretrained(str(local_path))
                processor = WhisperProcessor.from_pretrained(str(local_path))
                logger.info(f"✓ Loaded model from local cache: {model_id}")
                return model, processor
            except Exception as e:
                logger.warning(f"Failed to load from local cache: {e}")
        
        # Try downloading from GCS
        if self._model_exists_gcs(model_id):
            if self._download_from_gcs(model_id):
                try:
                    local_path = self._get_local_model_path(model_id)
                    model = WhisperForConditionalGeneration.from_pretrained(str(local_path))
                    processor = WhisperProcessor.from_pretrained(str(local_path))
                    logger.info(f"✓ Loaded model from GCS: {model_id}")
                    return model, processor
                except Exception as e:
                    logger.warning(f"Failed to load from GCS download: {e}")
        
        # Fallback: Download from HuggingFace
        if self._download_from_huggingface(model_id):
            try:
                local_path = self._get_local_model_path(model_id)
                model = WhisperForConditionalGeneration.from_pretrained(str(local_path))
                processor = WhisperProcessor.from_pretrained(str(local_path))
                
                # Optionally upload to GCS for future use
                self._upload_to_gcs(model_id)
                
                logger.info(f"✓ Loaded model from HuggingFace: {model_id}")
                return model, processor
            except Exception as e:
                logger.error(f"Failed to load from HuggingFace download: {e}")
        
        logger.error(f"All model loading attempts failed for {model_id}")
        return None, None
        
    def clear_cache(self, model_id: str = None):
        """Clear local model cache."""
        if model_id:
            model_path = self._get_local_model_path(model_id)
            if model_path.exists():
                import shutil
                shutil.rmtree(model_path)
                logger.info(f"Cleared cache for model: {model_id}")
        else:
            import shutil
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Cleared entire model cache")
            
    def get_cache_info(self) -> Dict:
        """Get information about cached models."""
        info = {
            "cache_dir": str(self.cache_dir),
            "bucket_name": self.bucket_name,
            "cached_models": []
        }
        
        for model_dir in self.cache_dir.iterdir():
            if model_dir.is_dir():
                size = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
                info["cached_models"].append({
                    "path": str(model_dir),
                    "size_mb": round(size / 1024 / 1024, 1)
                })
                
        return info