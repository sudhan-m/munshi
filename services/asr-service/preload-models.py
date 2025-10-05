#!/usr/bin/env python3
"""
Model pre-loading script for ASR service.
Downloads and caches models to reduce cold start time.
"""

import os
import sys
import asyncio
import logging
from model_cache import ExternalModelCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def preload_models():
    """Pre-load production models to cache."""
    cache = ExternalModelCache()
    
    # Production models to preload
    languages_to_preload = ["English", "Tamil", "Malayalam"]
    
    logger.info(f"Pre-loading {len(languages_to_preload)} production models...")
    
    for language in languages_to_preload:
        try:
            logger.info(f"Pre-loading {language} production model")
            model, processor = await cache.get_model(language, False)  # Always use production models
            
            if model and processor:
                logger.info(f"✅ {language} model pre-loaded successfully")
                # Clear from memory but keep in cache
                del model, processor
            else:
                logger.warning(f"⚠️  Failed to pre-load {language} model")
                
        except Exception as e:
            logger.error(f"❌ Error pre-loading {language} model: {e}")
    
    # Log cache status
    cache_info = cache.get_cache_info()
    total_cached_mb = sum(model["size_mb"] for model in cache_info["cached_models"])
    logger.info(f"Pre-loading complete. Total cached: {total_cached_mb:.1f}MB")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(preload_models())
        if success:
            logger.info("🎉 Model pre-loading completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Model pre-loading failed")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Model pre-loading interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during pre-loading: {e}")
        sys.exit(1)