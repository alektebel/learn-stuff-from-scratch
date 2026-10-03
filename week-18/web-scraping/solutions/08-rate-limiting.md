# Rate Limiting - Distributed Politeness and Throttling

## Overview

Rate limiting is critical for ethical web scraping. It prevents server overload, respects robots.txt directives, adapts to server responses, and ensures sustainable long-term crawling.

## Why Rate Limit?

### Ethical Reasons
- **Respect servers** - Don't overwhelm target websites
- **Prevent blocking** - Avoid IP bans and CAPTCHAs
- **Legal compliance** - Many ToS require rate limiting
- **Good citizenship** - Be a polite crawler

### Technical Reasons
- **Avoid timeouts** - Overloaded servers respond slowly
- **Better quality** - Slower = fewer errors
- **Resource efficiency** - Don't waste bandwidth on errors
- **Sustainable crawling** - Long-term access preservation

## Rate Limiting Algorithms

### 1. Token Bucket Algorithm

**Concept:** Tokens accumulate in a bucket at a fixed rate. Each request consumes a token. When empty, requests must wait.

```
         Rate: 10 tokens/sec
              │
              ▼
    ┌───────────────────┐
    │   Token Bucket    │  Capacity: 100
    │   ████████░░░░    │  Current: 60 tokens
    └───────────────────┘
              │
              ▼
         Requests consume tokens
```

**Properties:**
- Allows bursts up to bucket capacity
- Smooths out traffic over time
- Simple to implement
- Good for bursty patterns

**Implementation:**

```python
import time
import asyncio
from typing import Optional

class TokenBucket:
    """
    Token bucket rate limiter
    
    Tokens accumulate at a fixed rate (tokens_per_second).
    Each request consumes one token.
    Allows bursts up to max_tokens.
    """
    
    def __init__(
        self,
        tokens_per_second: float,
        max_tokens: int
    ):
        self.rate = tokens_per_second
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens (wait if necessary)
        """
        async with self.lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                
                # Add tokens based on elapsed time
                self.tokens = min(
                    self.max_tokens,
                    self.tokens + elapsed * self.rate
                )
                self.last_update = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                
                # Calculate wait time
                deficit = tokens - self.tokens
                wait_time = deficit / self.rate
                await asyncio.sleep(wait_time)
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without waiting
        Returns True if successful, False otherwise
        """
        now = time.monotonic()
        elapsed = now - self.last_update
        
        self.tokens = min(
            self.max_tokens,
            self.tokens + elapsed * self.rate
        )
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


# Usage example
async def rate_limited_requests():
    limiter = TokenBucket(
        tokens_per_second=10,  # 10 requests/sec
        max_tokens=50          # Allow burst of 50
    )
    
    urls = ['http://example.com/page1', 'http://example.com/page2']
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            await limiter.acquire()  # Wait for token
            async with session.get(url) as response:
                print(f"Fetched {url}")
```

### 2. Leaky Bucket Algorithm

**Concept:** Requests enter a queue (bucket) and are processed at a constant rate. Queue has maximum size.

```
    Requests arrive
         │││
         vvv
    ┌──────────┐
    │  Queue   │  Max size: 100
    │  ██████  │  Current: 40
    └────┬─────┘
         │
         ├─► Processed at constant rate
         │   (e.g., 10 requests/sec)
         ▼
```

**Properties:**
- Perfectly smooth output rate
- Rejects requests when queue full
- More predictable load on server
- Good for strict rate limits

**Implementation:**

```python
import asyncio
from collections import deque
from typing import Callable, Any, Optional

class LeakyBucket:
    """
    Leaky bucket rate limiter
    
    Processes requests at a constant rate.
    Queues overflow requests up to capacity.
    """
    
    def __init__(
        self,
        rate: float,  # requests per second
        capacity: int  # max queue size
    ):
        self.rate = rate
        self.capacity = capacity
        self.queue = deque()
        self.running = False
        self.lock = asyncio.Lock()
    
    async def submit(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Submit a function to be executed with rate limiting
        """
        async with self.lock:
            if len(self.queue) >= self.capacity:
                raise Exception("Queue full - request rejected")
            
            future = asyncio.Future()
            self.queue.append((func, args, kwargs, future))
            
            if not self.running:
                asyncio.create_task(self._process_queue())
            
            return await future
    
    async def _process_queue(self):
        """
        Process queued requests at constant rate
        """
        self.running = True
        interval = 1.0 / self.rate
        
        while self.queue:
            func, args, kwargs, future = self.queue.popleft()
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
            
            # Wait before processing next request
            if self.queue:
                await asyncio.sleep(interval)
        
        self.running = False


# Usage example
async def fetch_url(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def main():
    limiter = LeakyBucket(rate=10, capacity=100)
    
    urls = ['http://example.com/page1', 'http://example.com/page2']
    
    tasks = [limiter.submit(fetch_url, url) for url in urls]
    results = await asyncio.gather(*tasks)
```

### 3. Sliding Window Algorithm

**Concept:** Track requests in a time window. Limit based on recent request count.

```
Time:  [-------|-------|-------|-------]
       t-3min  t-2min  t-1min    now
Counts:   15      23      18      12  = 68 total in last 3 min
Limit: 100 requests per 3 minutes
Remaining: 32
```

**Implementation:**

```python
import time
from collections import deque
from typing import Optional

class SlidingWindowLimiter:
    """
    Sliding window rate limiter
    
    Tracks requests in a time window.
    Allows up to max_requests in window_seconds.
    """
    
    def __init__(
        self,
        max_requests: int,
        window_seconds: float
    ):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """
        Acquire permission to make a request
        """
        async with self.lock:
            now = time.monotonic()
            
            # Remove old requests outside window
            while self.requests and self.requests[0] <= now - self.window:
                self.requests.popleft()
            
            # Check if we can make request
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return
            
            # Wait until oldest request expires
            wait_time = self.requests[0] + self.window - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            # Retry
            await self.acquire()
    
    def get_remaining(self) -> int:
        """
        Get remaining requests in current window
        """
        now = time.monotonic()
        
        # Remove old requests
        while self.requests and self.requests[0] <= now - self.window:
            self.requests.popleft()
        
        return self.max_requests - len(self.requests)


# Usage example
async def crawl_with_sliding_window():
    limiter = SlidingWindowLimiter(
        max_requests=100,
        window_seconds=60  # 100 requests per minute
    )
    
    urls = ['http://example.com/page1', 'http://example.com/page2']
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            await limiter.acquire()
            print(f"Remaining: {limiter.get_remaining()}")
            async with session.get(url) as response:
                print(f"Fetched {url}")
```

## Distributed Rate Limiting with Redis

### Why Distributed?

When running multiple crawler instances:
- Each instance needs to respect global rate limit
- Must coordinate across machines
- Need centralized state

### Redis-Based Token Bucket

```python
import redis.asyncio as redis
import time
import asyncio
from typing import Optional

class RedisTokenBucket:
    """
    Distributed token bucket using Redis
    
    Multiple crawler instances can share rate limits.
    Uses Redis for atomic operations and state.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        key: str,
        tokens_per_second: float,
        max_tokens: int
    ):
        self.redis = redis_client
        self.key = f"ratelimit:{key}"
        self.rate = tokens_per_second
        self.max_tokens = max_tokens
    
    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens (distributed)
        """
        while True:
            now = time.time()
            
            # Lua script for atomic token bucket update
            lua_script = """
            local key = KEYS[1]
            local rate = tonumber(ARGV[1])
            local max_tokens = tonumber(ARGV[2])
            local tokens_requested = tonumber(ARGV[3])
            local now = tonumber(ARGV[4])
            
            local bucket = redis.call('HMGET', key, 'tokens', 'last_update')
            local current_tokens = tonumber(bucket[1]) or max_tokens
            local last_update = tonumber(bucket[2]) or now
            
            -- Add tokens based on elapsed time
            local elapsed = now - last_update
            current_tokens = math.min(max_tokens, current_tokens + elapsed * rate)
            
            -- Check if we have enough tokens
            if current_tokens >= tokens_requested then
                current_tokens = current_tokens - tokens_requested
                redis.call('HMSET', key, 'tokens', current_tokens, 'last_update', now)
                redis.call('EXPIRE', key, 300)
                return 1
            else
                redis.call('HMSET', key, 'tokens', current_tokens, 'last_update', now)
                redis.call('EXPIRE', key, 300)
                return 0
            end
            """
            
            result = await self.redis.eval(
                lua_script,
                1,
                self.key,
                self.rate,
                self.max_tokens,
                tokens,
                now
            )
            
            if result == 1:
                return
            
            # Calculate wait time
            bucket = await self.redis.hmget(self.key, 'tokens')
            current_tokens = float(bucket[0]) if bucket[0] else 0
            deficit = tokens - current_tokens
            wait_time = deficit / self.rate
            await asyncio.sleep(wait_time)


class RedisRateLimitManager:
    """
    Manage multiple rate limiters for different domains
    """
    
    def __init__(self, redis_url: str = "redis://localhost"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.limiters = {}
    
    def get_limiter(
        self,
        domain: str,
        requests_per_second: float = 1.0
    ) -> RedisTokenBucket:
        """
        Get or create rate limiter for domain
        """
        if domain not in self.limiters:
            self.limiters[domain] = RedisTokenBucket(
                redis_client=self.redis,
                key=domain,
                tokens_per_second=requests_per_second,
                max_tokens=int(requests_per_second * 10)
            )
        return self.limiters[domain]
    
    async def close(self):
        await self.redis.close()


# Usage example
async def distributed_crawling():
    manager = RedisRateLimitManager("redis://localhost:6379")
    
    urls = [
        'http://example.com/page1',
        'http://example.com/page2',
        'http://other.com/page1'
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            domain = urllib.parse.urlparse(url).netloc
            limiter = manager.get_limiter(domain, requests_per_second=2)
            
            await limiter.acquire()
            async with session.get(url) as response:
                print(f"Fetched {url}")
    
    await manager.close()
```

## Per-Domain Rate Limiting

### Domain-Aware Limiter

```python
from urllib.parse import urlparse
from typing import Dict
import asyncio

class PerDomainRateLimiter:
    """
    Separate rate limits per domain
    
    Ensures politeness per website.
    Allows parallel crawling of multiple domains.
    """
    
    def __init__(
        self,
        default_rate: float = 1.0,  # requests/sec
        domain_rates: Optional[Dict[str, float]] = None
    ):
        self.default_rate = default_rate
        self.domain_rates = domain_rates or {}
        self.limiters: Dict[str, TokenBucket] = {}
        self.lock = asyncio.Lock()
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        return urlparse(url).netloc
    
    async def _get_limiter(self, domain: str) -> TokenBucket:
        """Get or create limiter for domain"""
        if domain not in self.limiters:
            async with self.lock:
                if domain not in self.limiters:
                    rate = self.domain_rates.get(domain, self.default_rate)
                    self.limiters[domain] = TokenBucket(
                        tokens_per_second=rate,
                        max_tokens=int(rate * 10)
                    )
        return self.limiters[domain]
    
    async def acquire(self, url: str) -> None:
        """Acquire permission for URL"""
        domain = self._get_domain(url)
        limiter = await self._get_limiter(domain)
        await limiter.acquire()
    
    def set_domain_rate(self, domain: str, rate: float):
        """Update rate for specific domain"""
        self.domain_rates[domain] = rate
        if domain in self.limiters:
            # Update existing limiter
            self.limiters[domain].rate = rate


# Usage example
async def crawl_multiple_domains():
    limiter = PerDomainRateLimiter(
        default_rate=1.0,
        domain_rates={
            'example.com': 2.0,      # 2 req/sec
            'slowserver.com': 0.5,   # 1 req per 2 sec
        }
    )
    
    urls = [
        'http://example.com/page1',
        'http://example.com/page2',
        'http://slowserver.com/page1',
        'http://other.com/page1'
    ]
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for url in urls:
            async def fetch(url):
                await limiter.acquire(url)
                async with session.get(url) as response:
                    return await response.text()
            tasks.append(fetch(url))
        
        results = await asyncio.gather(*tasks)
```

## Adaptive Rate Limiting

### Response-Based Adaptation

```python
import asyncio
from typing import Optional
from enum import Enum

class ServerHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"

class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that responds to server signals
    
    Increases rate when server is healthy.
    Decreases rate on errors or slow responses.
    """
    
    def __init__(
        self,
        initial_rate: float = 1.0,
        min_rate: float = 0.1,
        max_rate: float = 10.0,
        increase_factor: float = 1.1,
        decrease_factor: float = 0.5
    ):
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.increase_factor = increase_factor
        self.decrease_factor = decrease_factor
        
        self.limiter = TokenBucket(
            tokens_per_second=initial_rate,
            max_tokens=int(initial_rate * 10)
        )
        
        self.success_count = 0
        self.error_count = 0
        self.response_times = []
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to make request"""
        await self.limiter.acquire()
    
    async def report_success(self, response_time: float):
        """Report successful request"""
        async with self.lock:
            self.success_count += 1
            self.response_times.append(response_time)
            
            # Keep last 100 response times
            if len(self.response_times) > 100:
                self.response_times.pop(0)
            
            # Increase rate after consecutive successes
            if self.success_count >= 10:
                await self._increase_rate()
                self.success_count = 0
                self.error_count = 0
    
    async def report_error(self, error_type: str):
        """Report failed request"""
        async with self.lock:
            self.error_count += 1
            
            # Decrease rate on errors
            if self.error_count >= 3:
                await self._decrease_rate()
                self.success_count = 0
                self.error_count = 0
    
    async def _increase_rate(self):
        """Increase rate (server can handle more)"""
        new_rate = min(
            self.max_rate,
            self.current_rate * self.increase_factor
        )
        if new_rate != self.current_rate:
            self.current_rate = new_rate
            self.limiter.rate = new_rate
            print(f"Increased rate to {new_rate:.2f} req/sec")
    
    async def _decrease_rate(self):
        """Decrease rate (server struggling)"""
        new_rate = max(
            self.min_rate,
            self.current_rate * self.decrease_factor
        )
        if new_rate != self.current_rate:
            self.current_rate = new_rate
            self.limiter.rate = new_rate
            print(f"Decreased rate to {new_rate:.2f} req/sec")
    
    def get_health(self) -> ServerHealth:
        """Assess server health"""
        if not self.response_times:
            return ServerHealth.HEALTHY
        
        avg_response_time = sum(self.response_times) / len(self.response_times)
        
        if avg_response_time < 1.0:
            return ServerHealth.HEALTHY
        elif avg_response_time < 5.0:
            return ServerHealth.DEGRADED
        else:
            return ServerHealth.OVERLOADED


# Usage example
async def adaptive_crawling():
    limiter = AdaptiveRateLimiter(
        initial_rate=1.0,
        min_rate=0.1,
        max_rate=5.0
    )
    
    urls = ['http://example.com/page{}'.format(i) for i in range(100)]
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            await limiter.acquire()
            
            start_time = time.time()
            try:
                async with session.get(url) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        await limiter.report_success(response_time)
                        print(f"Success: {url} ({response_time:.2f}s)")
                    elif response.status == 429:  # Too many requests
                        await limiter.report_error("rate_limit")
                        print(f"Rate limited: {url}")
                    else:
                        await limiter.report_error("http_error")
                        print(f"Error {response.status}: {url}")
                        
            except asyncio.TimeoutError:
                await limiter.report_error("timeout")
                print(f"Timeout: {url}")
            except Exception as e:
                await limiter.report_error("exception")
                print(f"Exception: {url} - {e}")
            
            print(f"Current rate: {limiter.current_rate:.2f} req/sec, "
                  f"Health: {limiter.get_health().value}")
```

## Respect robots.txt Crawl-Delay

### robots.txt Integration

```python
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from typing import Dict, Optional
import asyncio

class RobotsRateLimiter:
    """
    Rate limiter that respects robots.txt crawl-delay
    
    Fetches and parses robots.txt.
    Applies crawl-delay per domain.
    Falls back to default rate if not specified.
    """
    
    def __init__(
        self,
        default_delay: float = 1.0,
        user_agent: str = "MyBot"
    ):
        self.default_delay = default_delay
        self.user_agent = user_agent
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.limiters: Dict[str, TokenBucket] = {}
        self.lock = asyncio.Lock()
    
    async def _fetch_robots(self, domain: str) -> Optional[RobotFileParser]:
        """Fetch and parse robots.txt"""
        robots_url = f"http://{domain}/robots.txt"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        parser = RobotFileParser()
                        parser.parse(content.splitlines())
                        return parser
        except Exception as e:
            print(f"Failed to fetch robots.txt for {domain}: {e}")
        
        return None
    
    async def _get_crawl_delay(self, domain: str) -> float:
        """Get crawl-delay from robots.txt"""
        if domain not in self.robots_cache:
            async with self.lock:
                if domain not in self.robots_cache:
                    parser = await self._fetch_robots(domain)
                    self.robots_cache[domain] = parser
        
        parser = self.robots_cache[domain]
        if parser:
            # Try to get crawl-delay
            delay = parser.crawl_delay(self.user_agent)
            if delay:
                return float(delay)
        
        return self.default_delay
    
    async def acquire(self, url: str) -> bool:
        """
        Acquire permission to crawl URL
        Returns False if disallowed by robots.txt
        """
        domain = urlparse(url).netloc
        
        # Check robots.txt permission
        if domain in self.robots_cache:
            parser = self.robots_cache[domain]
            if parser and not parser.can_fetch(self.user_agent, url):
                return False
        
        # Get or create rate limiter
        if domain not in self.limiters:
            delay = await self._get_crawl_delay(domain)
            rate = 1.0 / delay if delay > 0 else 1.0
            self.limiters[domain] = TokenBucket(
                tokens_per_second=rate,
                max_tokens=max(1, int(rate * 5))
            )
        
        await self.limiters[domain].acquire()
        return True


# Usage example
async def crawl_with_robots():
    limiter = RobotsRateLimiter(
        default_delay=1.0,
        user_agent="MyBot/1.0"
    )
    
    urls = [
        'http://example.com/page1',
        'http://example.com/page2',
        'http://example.com/admin'  # Might be disallowed
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            if await limiter.acquire(url):
                async with session.get(url) as response:
                    print(f"Fetched {url}")
            else:
                print(f"Disallowed by robots.txt: {url}")
```

## Best Practices

### 1. Layer Multiple Limiters

```python
class MultiLayerRateLimiter:
    """
    Multiple rate limiting layers
    
    - Global limit (total requests/sec)
    - Per-domain limit (politeness)
    - Per-IP limit (avoid bans)
    """
    
    def __init__(self):
        # Global rate limit
        self.global_limiter = TokenBucket(
            tokens_per_second=100,  # 100 req/sec total
            max_tokens=500
        )
        
        # Per-domain limiters
        self.domain_limiter = PerDomainRateLimiter(
            default_rate=2.0
        )
        
        # Per-IP limiter (if using proxies)
        self.ip_limiter = PerDomainRateLimiter(
            default_rate=10.0
        )
    
    async def acquire(self, url: str, proxy_ip: Optional[str] = None):
        """Acquire all required permissions"""
        # Global limit first
        await self.global_limiter.acquire()
        
        # Domain limit
        await self.domain_limiter.acquire(url)
        
        # IP limit (if using proxies)
        if proxy_ip:
            await self.ip_limiter.acquire(f"proxy_{proxy_ip}")
```

### 2. Monitor and Adjust

```python
import prometheus_client as prom

class MonitoredRateLimiter:
    """Rate limiter with metrics"""
    
    def __init__(self):
        self.limiter = TokenBucket(
            tokens_per_second=10,
            max_tokens=100
        )
        
        # Metrics
        self.requests_total = prom.Counter(
            'rate_limiter_requests_total',
            'Total requests'
        )
        self.requests_delayed = prom.Counter(
            'rate_limiter_delayed_total',
            'Requests delayed by rate limiter'
        )
        self.delay_seconds = prom.Histogram(
            'rate_limiter_delay_seconds',
            'Time spent waiting for rate limiter'
        )
    
    async def acquire(self):
        """Acquire with metrics"""
        self.requests_total.inc()
        
        start = time.time()
        if not self.limiter.try_acquire():
            self.requests_delayed.inc()
            await self.limiter.acquire()
        
        delay = time.time() - start
        if delay > 0:
            self.delay_seconds.observe(delay)
```

### 3. Graceful Degradation

```python
class FaultTolerantRateLimiter:
    """
    Rate limiter with fallback
    
    If Redis fails, fall back to local rate limiting.
    """
    
    def __init__(self, redis_url: str):
        try:
            self.distributed = RedisRateLimitManager(redis_url)
            self.use_distributed = True
        except Exception as e:
            print(f"Redis unavailable, using local limiting: {e}")
            self.local = PerDomainRateLimiter()
            self.use_distributed = False
    
    async def acquire(self, url: str):
        """Acquire with fallback"""
        try:
            if self.use_distributed:
                domain = urlparse(url).netloc
                limiter = self.distributed.get_limiter(domain)
                await limiter.acquire()
            else:
                await self.local.acquire(url)
        except Exception as e:
            # Fall back to local if distributed fails
            if self.use_distributed:
                print(f"Distributed limiting failed, falling back: {e}")
                self.use_distributed = False
                await self.local.acquire(url)
            else:
                raise
```

## Testing Rate Limiters

```python
import pytest
import time

@pytest.mark.asyncio
async def test_token_bucket_rate():
    """Test token bucket enforces rate"""
    limiter = TokenBucket(tokens_per_second=10, max_tokens=10)
    
    # Should allow 10 requests immediately
    start = time.time()
    for _ in range(10):
        await limiter.acquire()
    elapsed = time.time() - start
    assert elapsed < 0.1  # Should be nearly instant
    
    # Next 10 should take ~1 second
    start = time.time()
    for _ in range(10):
        await limiter.acquire()
    elapsed = time.time() - start
    assert 0.9 < elapsed < 1.2  # ~1 second with some margin

@pytest.mark.asyncio
async def test_per_domain_isolation():
    """Test domains are rate limited independently"""
    limiter = PerDomainRateLimiter(default_rate=10)
    
    # Requests to different domains should not interfere
    start = time.time()
    await asyncio.gather(
        *[limiter.acquire('http://domain1.com/') for _ in range(10)],
        *[limiter.acquire('http://domain2.com/') for _ in range(10)]
    )
    elapsed = time.time() - start
    
    # Should complete in ~1 second (parallel), not 2 seconds (sequential)
    assert elapsed < 1.5

@pytest.mark.asyncio
async def test_adaptive_decrease_on_errors():
    """Test adaptive limiter decreases on errors"""
    limiter = AdaptiveRateLimiter(initial_rate=10.0)
    initial_rate = limiter.current_rate
    
    # Report multiple errors
    for _ in range(3):
        await limiter.report_error("timeout")
    
    # Rate should decrease
    assert limiter.current_rate < initial_rate

@pytest.mark.asyncio
async def test_adaptive_increase_on_success():
    """Test adaptive limiter increases on success"""
    limiter = AdaptiveRateLimiter(initial_rate=1.0)
    initial_rate = limiter.current_rate
    
    # Report multiple successes
    for _ in range(10):
        await limiter.report_success(0.5)
    
    # Rate should increase
    assert limiter.current_rate > initial_rate
```

## Performance Considerations

### Token Bucket vs Leaky Bucket

| Aspect | Token Bucket | Leaky Bucket |
|--------|-------------|--------------|
| Burst handling | Allows bursts | Smooth output |
| Memory | O(1) | O(queue size) |
| Latency | Lower (no queue) | Higher (queuing) |
| Server load | Variable | Constant |
| Best for | Flexible rate limiting | Strict rate limiting |

### Distributed vs Local

| Aspect | Distributed (Redis) | Local |
|--------|-------------------|-------|
| Coordination | Across instances | Per instance |
| Latency | Higher (network) | Lower (in-memory) |
| Complexity | Higher | Lower |
| Fault tolerance | Requires Redis | Self-contained |
| Best for | Multi-instance | Single instance |

## References

- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Leaky Bucket Algorithm](https://en.wikipedia.org/wiki/Leaky_bucket)
- [Redis Rate Limiting Patterns](https://redis.io/docs/reference/patterns/rate-limiter/)
- [robots.txt Specification](https://www.robotstxt.org/)
- [Adaptive Rate Limiting Paper](https://research.google/pubs/pub36640/)
