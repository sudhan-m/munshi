"""
Cloud Run specific configuration and utilities for ASR Service.
"""

import os
import psutil
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class CloudRunConfig:
    """Cloud Run optimized configuration"""
    
    def __init__(self):
        self.cloud_run_mode = os.getenv("CLOUD_RUN_MODE", "false").lower() == "true"
        self.memory_limit = self._get_memory_limit()
        self.cpu_count = self._get_cpu_count()
        self.container_concurrency = int(os.getenv("CONTAINER_CONCURRENCY", "1"))
        
    def _get_memory_limit(self) -> int:
        """Get memory limit in bytes"""
        try:
            # Try to get from cgroups (Cloud Run container)
            with open("/sys/fs/cgroup/memory/memory.limit_in_bytes", "r") as f:
                limit = int(f.read().strip())
                # Convert to reasonable limit if it's the system max
                if limit > 100 * 1024**3:  # > 100GB means no limit set
                    return 4 * 1024**3  # Default to 4GB
                return limit
        except (FileNotFoundError, ValueError):
            # Fallback to available memory
            return psutil.virtual_memory().available
    
    def _get_cpu_count(self) -> int:
        """Get available CPU count"""
        try:
            # Cloud Run typically allocates 1-2 CPUs
            return min(psutil.cpu_count(), 2)
        except:
            return 1
    
    def get_optimal_torch_threads(self) -> int:
        """Get optimal PyTorch thread count for Cloud Run"""
        # Conservative threading for Cloud Run
        return min(self.cpu_count, 2)
    
    def should_use_tiny_model(self) -> bool:
        """Determine if we should use tiny models based on available resources"""
        memory_gb = self.memory_limit / (1024**3)
        return self.cloud_run_mode or memory_gb < 3
    
    def get_max_audio_size(self) -> int:
        """Get maximum audio file size based on available memory"""
        memory_gb = self.memory_limit / (1024**3)
        if memory_gb >= 4:
            return 10 * 1024 * 1024  # 10MB
        elif memory_gb >= 2:
            return 5 * 1024 * 1024   # 5MB
        else:
            return 2 * 1024 * 1024   # 2MB
    
    def log_system_info(self):
        """Log system information for debugging"""
        logger.info(f"Cloud Run Mode: {self.cloud_run_mode}")
        logger.info(f"Memory Limit: {self.memory_limit / (1024**3):.1f}GB")
        logger.info(f"CPU Count: {self.cpu_count}")
        logger.info(f"Container Concurrency: {self.container_concurrency}")
        logger.info(f"Max Audio Size: {self.get_max_audio_size() / (1024**2):.1f}MB")

class MemoryMonitor:
    """Monitor memory usage in Cloud Run"""
    
    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        """Get current memory usage statistics"""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available, 
            "used": memory.used,
            "percentage": memory.percent,
            "used_mb": memory.used / (1024**2),
            "available_mb": memory.available / (1024**2)
        }
    
    @staticmethod
    def check_memory_pressure() -> bool:
        """Check if memory usage is high"""
        memory = psutil.virtual_memory()
        return memory.percent > 80  # High memory usage threshold
    
    @staticmethod
    def log_memory_status():
        """Log current memory status"""
        usage = MemoryMonitor.get_memory_usage()
        logger.info(f"Memory: {usage['used_mb']:.1f}MB used, {usage['available_mb']:.1f}MB available ({usage['percentage']:.1f}%)")

# Global config instance
cloudrun_config = CloudRunConfig()