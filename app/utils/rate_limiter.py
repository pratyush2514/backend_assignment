"""
Rate limiting middleware for API endpoints
"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter
    Production: Use Redis for distributed rate limiting
    """
    
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Storage: {client_id: [(timestamp, count)]}
        self.minute_tracker: Dict[str, list] = defaultdict(list)
        self.hour_tracker: Dict[str, list] = defaultdict(list)
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request"""
        # Try to get user_id from request state (if authenticated)
        if hasattr(request.state, "user_id"):
            return str(request.state.user_id)
        
        # Fallback to IP address
        client_ip = request.client.host if request.client else "unknown"
        return client_ip
    
    def _cleanup_old_entries(self, tracker: Dict[str, list], window_seconds: int):
        """Remove entries older than window"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        for client_id in list(tracker.keys()):
            tracker[client_id] = [
                (ts, count) for ts, count in tracker[client_id]
                if ts > cutoff_time
            ]
            
            # Remove empty entries
            if not tracker[client_id]:
                del tracker[client_id]
    
    async def check_rate_limit(self, request: Request) -> None:
        """
        Check if request exceeds rate limits
        
        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Cleanup old entries
        self._cleanup_old_entries(self.minute_tracker, 60)
        self._cleanup_old_entries(self.hour_tracker, 3600)
        
        # Check minute limit
        minute_requests = sum(count for _, count in self.minute_tracker[client_id])
        if minute_requests >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded (minute): {client_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Limit: {self.requests_per_minute} requests per minute",
                    "retry_after": 60
                }
            )
        
        # Check hour limit
        hour_requests = sum(count for _, count in self.hour_tracker[client_id])
        if hour_requests >= self.requests_per_hour:
            logger.warning(f"Rate limit exceeded (hour): {client_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Limit: {self.requests_per_hour} requests per hour",
                    "retry_after": 3600
                }
            )
        
        # Record this request
        self.minute_tracker[client_id].append((current_time, 1))
        self.hour_tracker[client_id].append((current_time, 1))
        
        logger.debug(f"Rate limit check passed: {client_id} (minute: {minute_requests+1}, hour: {hour_requests+1})")


# Global instance
from app.config import settings
rate_limiter = RateLimiter(
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    requests_per_hour=settings.RATE_LIMIT_PER_HOUR
)