"""
Redis cache utility for quiz caching
"""
import redis
import json
import logging
import hashlib
from typing import Optional, Any
from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service for quiz generation"""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {str(e)}. Caching disabled.")
            self.redis_client = None
    
    def generate_cache_key(
        self,
        chapter_id: str,
        difficulty: str,
        num_mcq: int,
        num_short: int,
        num_numerical: int
    ) -> str:
        """
        Generate deterministic cache key for quiz parameters
        
        Args:
            chapter_id: Chapter UUID
            difficulty: Quiz difficulty
            num_mcq: Number of MCQ questions
            num_short: Number of short questions
            num_numerical: Number of numerical questions
            
        Returns:
            Cache key string
        """
        key_string = f"quiz:{chapter_id}:{difficulty}:{num_mcq}:{num_short}:{num_numerical}"
        return key_string
    
    def generate_variant_hash(
        self,
        chapter_id: str,
        difficulty: str,
        num_mcq: int,
        num_short: int,
        num_numerical: int
    ) -> str:
        """
        Generate variant hash for database storage
        
        Same parameters → same hash (for deduplication)
        """
        key_string = f"{chapter_id}|{difficulty}|{num_mcq}|{num_short}|{num_numerical}"
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                logger.info(f"Cache hit: {key}")
                return json.loads(value)
            logger.info(f"Cache miss: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = None
    ) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default from settings)
            
        Returns:
            Success status
        """
        if not self.redis_client:
            return False
        
        try:
            ttl = ttl or settings.DEFAULT_QUIZ_CACHE_TTL
            serialized = json.dumps(value)
            self.redis_client.setex(key, ttl, serialized)
            logger.info(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(key)
            logger.info(f"Cache delete: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False
    
    def clear_chapter_cache(self, chapter_id: str) -> bool:
        """Clear all cached quizzes for a chapter"""
        if not self.redis_client:
            return False
        
        try:
            pattern = f"quiz:{chapter_id}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries for chapter {chapter_id}")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
            return False


# Global instance
cache_service = CacheService()