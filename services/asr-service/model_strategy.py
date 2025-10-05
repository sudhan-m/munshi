"""
Production model configuration.
"""

import os
import logging

logger = logging.getLogger(__name__)

class ProductionStrategy:
    """Production model configuration strategy."""
    
    def __init__(self):
        self.environment = "production"
        self.gpu_support = os.getenv("GPU_SUPPORT", "cuda").lower()
        
    def get_recommended_model_size(self, language):
        """Always use large models for production quality."""
        return "large"
            
    def log_strategy_info(self):
        """Log production strategy information."""
        logger.info(f"Environment: {self.environment}")
        logger.info(f"GPU Support: {self.gpu_support}")
        logger.info("Using production-quality large models")

# Global instance
model_strategy = ProductionStrategy()