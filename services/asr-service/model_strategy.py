"""
Environment-based model loading strategy for Cloud Run optimization.
"""

import os
import logging
from enum import Enum
from typing import Dict, Tuple
from cloudrun_config import cloudrun_config

logger = logging.getLogger(__name__)

class ModelTier(Enum):
    """Model tiers based on accuracy vs speed/memory tradeoffs"""
    TINY = "tiny"       # Fastest, least accurate, minimal memory
    BASE = "base"       # Balanced accuracy and speed
    SMALL = "small"     # Better accuracy, more memory
    MEDIUM = "medium"   # High accuracy, high memory
    LARGE = "large"     # Best accuracy, highest memory

class ModelStrategy:
    """Dynamic model selection based on environment and requirements"""
    
    def __init__(self):
        self.environment = self._detect_environment()
        self.strategy_config = self._load_strategy_config()
        
    def _detect_environment(self) -> str:
        """Detect the current deployment environment"""
        if os.getenv("CLOUD_RUN_MODE", "false").lower() == "true":
            return "cloudrun"
        elif os.getenv("K8S_POD_NAME"):
            return "kubernetes"
        elif os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            return "lambda"
        elif os.getenv("ENVIRONMENT") == "production":
            return "production"
        elif os.getenv("ENVIRONMENT") == "staging":
            return "staging"
        else:
            return "development"
    
    def _load_strategy_config(self) -> Dict:
        """Load model strategy configuration based on environment"""
        
        # Cloud Run optimized configuration
        cloudrun_config_dict = {
            "default_tier": ModelTier.TINY,
            "memory_thresholds": {
                ModelTier.TINY: 1.0,    # 1GB
                ModelTier.BASE: 2.0,    # 2GB
                ModelTier.SMALL: 4.0,   # 4GB
                ModelTier.MEDIUM: 8.0,  # 8GB
                ModelTier.LARGE: 16.0   # 16GB
            },
            "language_priorities": {
                "English": [ModelTier.TINY, ModelTier.BASE],
                "Tamil": [ModelTier.TINY, ModelTier.BASE],
                "Malayalam": [ModelTier.TINY, ModelTier.BASE]
            },
            "fallback_models": {
                ModelTier.TINY: "openai/whisper-tiny",
                ModelTier.BASE: "openai/whisper-base"
            }
        }
        
        # Environment-specific configurations
        configs = {
            "cloudrun": cloudrun_config_dict,
            "kubernetes": {
                "default_tier": ModelTier.BASE,
                "memory_thresholds": {
                    ModelTier.TINY: 2.0,
                    ModelTier.BASE: 4.0,
                    ModelTier.SMALL: 8.0,
                    ModelTier.MEDIUM: 16.0,
                    ModelTier.LARGE: 32.0
                },
                "language_priorities": {
                    "English": [ModelTier.BASE, ModelTier.SMALL],
                    "Tamil": [ModelTier.BASE, ModelTier.SMALL],
                    "Malayalam": [ModelTier.BASE, ModelTier.SMALL]
                }
            },
            "production": {
                "default_tier": ModelTier.SMALL,
                "memory_thresholds": {
                    ModelTier.TINY: 4.0,
                    ModelTier.BASE: 8.0,
                    ModelTier.SMALL: 16.0,
                    ModelTier.MEDIUM: 32.0,
                    ModelTier.LARGE: 64.0
                }
            },
            "development": {
                "default_tier": ModelTier.BASE,
                "memory_thresholds": {
                    ModelTier.TINY: 2.0,
                    ModelTier.BASE: 4.0,
                    ModelTier.SMALL: 8.0,
                    ModelTier.MEDIUM: 16.0,
                    ModelTier.LARGE: 32.0
                }
            }
        }
        
        return configs.get(self.environment, configs["development"])
    
    def select_model_for_language(self, language: str) -> Tuple[str, ModelTier]:
        """Select optimal model for given language and current environment"""
        
        # Get available memory in GB
        memory_gb = cloudrun_config.memory_limit / (1024**3)
        
        # Get language-specific priorities or use default
        priorities = self.strategy_config.get("language_priorities", {}).get(
            language, 
            [self.strategy_config["default_tier"]]
        )
        
        # Find the best model tier that fits in available memory
        selected_tier = None
        for tier in priorities:
            required_memory = self.strategy_config["memory_thresholds"][tier]
            if memory_gb >= required_memory:
                selected_tier = tier
                break
        
        # Fallback to smallest model if nothing fits
        if selected_tier is None:
            selected_tier = ModelTier.TINY
        
        # Get model name for the selected tier
        model_name = self._get_model_name(language, selected_tier)
        
        logger.info(f"Selected {selected_tier.value} model for {language}: {model_name} "
                   f"(available memory: {memory_gb:.1f}GB)")
        
        return model_name, selected_tier
    
    def _get_model_name(self, language: str, tier: ModelTier) -> str:
        """Get HuggingFace model name for language and tier"""
        
        # Model mapping based on language and tier
        model_map = {
            ("English", ModelTier.TINY): "openai/whisper-tiny.en",
            ("English", ModelTier.BASE): "openai/whisper-base.en", 
            ("English", ModelTier.SMALL): "openai/whisper-small.en",
            ("English", ModelTier.MEDIUM): "openai/whisper-medium.en",
            ("English", ModelTier.LARGE): "openai/whisper-large-v2",
            
            # For non-English, use multilingual models
            ("Tamil", ModelTier.TINY): "openai/whisper-tiny",
            ("Tamil", ModelTier.BASE): "openai/whisper-base",
            ("Tamil", ModelTier.SMALL): "openai/whisper-small", 
            ("Tamil", ModelTier.MEDIUM): "vasista22/whisper-tamil-medium",
            ("Tamil", ModelTier.LARGE): "vasista22/whisper-tamil-large-v2",
            
            ("Malayalam", ModelTier.TINY): "openai/whisper-tiny",
            ("Malayalam", ModelTier.BASE): "openai/whisper-base",
            ("Malayalam", ModelTier.SMALL): "openai/whisper-small",
            ("Malayalam", ModelTier.MEDIUM): "thennal/whisper-medium-ml",
            ("Malayalam", ModelTier.LARGE): "openai/whisper-large-v2",
        }
        
        # Get model name or fallback
        model_name = model_map.get((language, tier))
        if model_name is None:
            # Fallback to base multilingual model
            fallback = self.strategy_config.get("fallback_models", {}).get(
                tier, "openai/whisper-tiny"
            )
            logger.warning(f"No specific model for {language}/{tier.value}, using fallback: {fallback}")
            return fallback
            
        return model_name
    
    def get_inference_config(self, tier: ModelTier) -> Dict:
        """Get inference configuration based on model tier and environment"""
        
        # Cloud Run optimized inference settings
        if self.environment == "cloudrun":
            configs = {
                ModelTier.TINY: {
                    "max_length": 224,
                    "num_beams": 1,  # Greedy search for speed
                    "do_sample": False,
                    "temperature": 0.0
                },
                ModelTier.BASE: {
                    "max_length": 448,
                    "num_beams": 1,  # Still prioritize speed
                    "do_sample": False,
                    "temperature": 0.0
                }
            }
        else:
            # Higher quality settings for other environments
            configs = {
                ModelTier.TINY: {
                    "max_length": 448,
                    "num_beams": 3,
                    "do_sample": False,
                    "temperature": 0.0
                },
                ModelTier.BASE: {
                    "max_length": 448,
                    "num_beams": 5,
                    "do_sample": False,
                    "temperature": 0.0
                }
            }
        
        return configs.get(tier, configs[ModelTier.TINY])
    
    def log_strategy_info(self):
        """Log current strategy configuration"""
        logger.info(f"Model Strategy Environment: {self.environment}")
        logger.info(f"Default Tier: {self.strategy_config['default_tier'].value}")
        memory_gb = cloudrun_config.memory_limit / (1024**3)
        logger.info(f"Available Memory: {memory_gb:.1f}GB")

# Global strategy instance
model_strategy = ModelStrategy()