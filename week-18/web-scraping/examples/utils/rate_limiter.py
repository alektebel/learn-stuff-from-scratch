"""Token bucket rate limiter for controlling request rates.

This module implements a token bucket algorithm for rate limiting.
"""

import time
import asyncio
from typing import Optional
from collections import defaultdict


class TokenBucketRateLimiter:
    """Token bucket rate limiter for controlling request rates.
    
    This implements the token bucket algorithm where tokens are added
    at a fixed rate and requests consume tokens. If no tokens are
    available, requests must wait.
    """
    
    def __init__(self, rate: float, capacity: Optional[int] = None):
        """Initialize rate limiter.
        
        Args:
            rate: Number of requests per second
            capacity: Maximum burst size (defaults to rate)
        """
        self.rate = rate
        self.capacity = capacity or int(rate)
        self.tokens = float(self.capacity)
        self.last_update = time.monotonic()
        self._lock = None  # Initialized lazily in async methods
    
    def _add_tokens(self) -> None:
        """Add tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
    
    def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens (blocking).
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            Time waited in seconds
        """
        self._add_tokens()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return 0.0
        
        # Calculate wait time
        tokens_needed = tokens - self.tokens
        wait_time = tokens_needed / self.rate
        time.sleep(wait_time)
        
        self._add_tokens()
        self.tokens -= tokens
        return wait_time
    
    async def acquire_async(self, tokens: int = 1) -> float:
        """Acquire tokens (async).
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            Time waited in seconds
        """
        if self._lock is None:
            self._lock = asyncio.Lock()
        
        async with self._lock:
            self._add_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0
            
            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.rate
            await asyncio.sleep(wait_time)
            
            self._add_tokens()
            self.tokens -= tokens
            return wait_time


class DomainRateLimiter:
    """Per-domain rate limiter using token bucket algorithm.
    
    Maintains separate rate limiters for each domain.
    """
    
    def __init__(self, requests_per_second: float = 1.0, burst: Optional[int] = None):
        """Initialize domain rate limiter.
        
        Args:
            requests_per_second: Requests per second per domain
            burst: Maximum burst size (defaults to requests_per_second)
        """
        self.requests_per_second = requests_per_second
        self.burst = burst
        self.limiters = defaultdict(lambda: TokenBucketRateLimiter(
            rate=self.requests_per_second,
            capacity=self.burst
        ))
    
    def acquire(self, domain: str, tokens: int = 1) -> float:
        """Acquire tokens for a domain (blocking).
        
        Args:
            domain: Domain identifier
            tokens: Number of tokens to acquire
            
        Returns:
            Time waited in seconds
        """
        return self.limiters[domain].acquire(tokens)
    
    async def acquire_async(self, domain: str, tokens: int = 1) -> float:
        """Acquire tokens for a domain (async).
        
        Args:
            domain: Domain identifier
            tokens: Number of tokens to acquire
            
        Returns:
            Time waited in seconds
        """
        return await self.limiters[domain].acquire_async(tokens)
