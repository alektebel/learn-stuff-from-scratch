# URL Frontier - Queue and Prioritization Guide

## Overview

The URL Frontier (also called URL queue or URL frontier) is the core data structure that manages which URLs to crawl next. It must handle deduplication, prioritization, politeness policies, and efficient distribution in a scalable manner.

## Architecture

### Basic Structure

```
┌─────────────────────────────────────────────────┐
│              URL Frontier                       │
│                                                 │
│  ┌──────────────┐         ┌─────────────────┐ │
│  │   Priority   │         │  Duplicate      │ │
│  │    Queues    │◄────────┤  Detection      │ │
│  │  (Per-Host)  │         │ (Bloom Filter)  │ │
│  └──────┬───────┘         └─────────────────┘ │
│         │                                      │
│         │                                      │
│         ▼                                      │
│  ┌──────────────┐         ┌─────────────────┐ │
│  │  Politeness  │         │     Storage     │ │
│  │   Manager    │◄────────┤   (Redis/DB)    │ │
│  │ (Rate Limit) │         └─────────────────┘ │
│  └──────┬───────┘                             │
│         │                                      │
│         ▼                                      │
│  ┌──────────────┐                             │
│  │   Get Next   │                             │
│  │     URL      │                             │
│  └──────────────┘                             │
└─────────────────────────────────────────────────┘
```

## Core Components

### 1. URL Normalization

URLs must be normalized to avoid duplicates:

```python
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import re

class URLNormalizer:
    """Normalize URLs for deduplication"""
    
    @staticmethod
    def normalize(url: str) -> str:
        """
        Normalize URL to canonical form
        
        Steps:
        1. Convert scheme and host to lowercase
        2. Remove default ports (80, 443)
        3. Normalize path (resolve .., remove //)
        4. Sort query parameters
        5. Remove fragment
        6. Remove tracking parameters
        7. Normalize percent encoding
        """
        parsed = urlparse(url)
        
        # 1. Lowercase scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # 2. Remove default ports
        if scheme == 'http' and netloc.endswith(':80'):
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc.endswith(':443'):
            netloc = netloc[:-4]
        
        # 3. Normalize path
        path = URLNormalizer._normalize_path(parsed.path or '/')
        
        # 4. Sort query parameters
        query = URLNormalizer._normalize_query(parsed.query)
        
        # 5. Fragment is removed (set to '')
        
        # Reconstruct URL
        return urlunparse((scheme, netloc, path, '', query, ''))
    
    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize URL path"""
        # Remove duplicate slashes
        path = re.sub(r'/+', '/', path)
        
        # Resolve . and ..
        parts = []
        for part in path.split('/'):
            if part == '..':
                if parts:
                    parts.pop()
            elif part and part != '.':
                parts.append(part)
        
        # Reconstruct path
        result = '/' + '/'.join(parts)
        
        # Preserve trailing slash if original had it
        if path.endswith('/') and not result.endswith('/'):
            result += '/'
        
        return result
    
    @staticmethod
    def _normalize_query(query: str) -> str:
        """Normalize query string"""
        if not query:
            return ''
        
        # Parse query parameters
        params = parse_qs(query, keep_blank_values=True)
        
        # Remove common tracking parameters
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'mc_eid', 'mc_cid', '_ga', 'ref', 'source'
        }
        params = {k: v for k, v in params.items() if k not in tracking_params}
        
        if not params:
            return ''
        
        # Sort parameters by key, then by value
        sorted_params = []
        for key in sorted(params.keys()):
            for value in sorted(params[key]):
                sorted_params.append((key, value))
        
        return urlencode(sorted_params)
    
    @staticmethod
    def get_domain(url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc.lower()
```

### 2. Duplicate Detection with Bloom Filter

```python
import mmh3  # MurmurHash3
from bitarray import bitarray
import math

class BloomFilter:
    """Space-efficient probabilistic data structure for duplicate detection"""
    
    def __init__(self, expected_elements: int, false_positive_rate: float = 0.01):
        """
        Args:
            expected_elements: Number of expected URLs
            false_positive_rate: Acceptable false positive rate (0.01 = 1%)
        """
        # Calculate optimal size and number of hash functions
        self.size = self._optimal_size(expected_elements, false_positive_rate)
        self.hash_count = self._optimal_hash_count(self.size, expected_elements)
        
        # Initialize bit array
        self.bit_array = bitarray(self.size)
        self.bit_array.setall(0)
        
        self.element_count = 0
    
    def _optimal_size(self, n: int, p: float) -> int:
        """Calculate optimal bit array size"""
        return int(-n * math.log(p) / (math.log(2) ** 2))
    
    def _optimal_hash_count(self, m: int, n: int) -> int:
        """Calculate optimal number of hash functions"""
        return max(1, int((m / n) * math.log(2)))
    
    def add(self, item: str) -> bool:
        """
        Add item to bloom filter
        
        Returns:
            True if item was not present (probably)
            False if item was already present (definitely)
        """
        was_new = False
        
        for seed in range(self.hash_count):
            # Generate hash
            hash_value = mmh3.hash(item, seed) % self.size
            
            # Check if bit is already set
            if not self.bit_array[hash_value]:
                was_new = True
                self.bit_array[hash_value] = 1
        
        if was_new:
            self.element_count += 1
        
        return was_new
    
    def contains(self, item: str) -> bool:
        """
        Check if item might be in the set
        
        Returns:
            True if item might be present (could be false positive)
            False if item is definitely not present
        """
        for seed in range(self.hash_count):
            hash_value = mmh3.hash(item, seed) % self.size
            if not self.bit_array[hash_value]:
                return False
        return True
    
    def __len__(self) -> int:
        """Return approximate number of elements"""
        return self.element_count


class DistributedBloomFilter:
    """Redis-backed distributed bloom filter"""
    
    def __init__(self, redis_client, key_prefix: str, size: int, hash_count: int):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.size = size
        self.hash_count = hash_count
    
    def add(self, item: str) -> bool:
        """Add item using Redis SETBIT"""
        was_new = False
        pipe = self.redis.pipeline()
        
        for seed in range(self.hash_count):
            hash_value = mmh3.hash(item, seed) % self.size
            key = f"{self.key_prefix}:{hash_value // 10000}"  # Shard across keys
            bit = hash_value % 10000
            
            # Check and set bit atomically
            pipe.getbit(key, bit)
            pipe.setbit(key, bit, 1)
        
        results = pipe.execute()
        
        # Check if any bit was 0 (new)
        for i in range(0, len(results), 2):
            if results[i] == 0:
                was_new = True
        
        return was_new
    
    def contains(self, item: str) -> bool:
        """Check if item exists"""
        pipe = self.redis.pipeline()
        
        for seed in range(self.hash_count):
            hash_value = mmh3.hash(item, seed) % self.size
            key = f"{self.key_prefix}:{hash_value // 10000}"
            bit = hash_value % 10000
            pipe.getbit(key, bit)
        
        results = pipe.execute()
        return all(results)
```

### 3. Priority Queue Structure

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import heapq
from enum import IntEnum

class Priority(IntEnum):
    """URL priority levels"""
    CRITICAL = 0   # Highest priority
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4  # Lowest priority

@dataclass(order=True)
class QueuedURL:
    """Represents a URL in the frontier"""
    priority: int
    score: float = field(compare=True)
    url: str = field(compare=False)
    depth: int = field(compare=False, default=0)
    discovered_time: datetime = field(compare=False, default_factory=datetime.now)
    retry_count: int = field(compare=False, default=0)
    metadata: dict = field(compare=False, default_factory=dict)
    
    def __post_init__(self):
        # Invert score for max heap behavior
        self.score = -self.score

class URLQueue:
    """Priority queue for a single host/domain"""
    
    def __init__(self, domain: str, politeness_delay: float = 1.0):
        self.domain = domain
        self.politeness_delay = politeness_delay
        self.queue: List[QueuedURL] = []
        self.last_fetch_time: Optional[datetime] = None
    
    def add(self, queued_url: QueuedURL):
        """Add URL to queue"""
        heapq.heappush(self.queue, queued_url)
    
    def get_next(self) -> Optional[QueuedURL]:
        """Get next URL if politeness delay satisfied"""
        if not self.queue:
            return None
        
        # Check politeness delay
        if self.last_fetch_time:
            elapsed = (datetime.now() - self.last_fetch_time).total_seconds()
            if elapsed < self.politeness_delay:
                return None
        
        url = heapq.heappop(self.queue)
        self.last_fetch_time = datetime.now()
        return url
    
    def peek(self) -> Optional[QueuedURL]:
        """Peek at next URL without removing"""
        return self.queue[0] if self.queue else None
    
    def __len__(self) -> int:
        return len(self.queue)
    
    def is_ready(self) -> bool:
        """Check if queue is ready for next fetch"""
        if not self.queue:
            return False
        
        if self.last_fetch_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_fetch_time).total_seconds()
        return elapsed >= self.politeness_delay
```

### 4. URL Frontier Manager

```python
import asyncio
from collections import defaultdict

class URLFrontier:
    """Main URL frontier managing multiple per-domain queues"""
    
    def __init__(
        self,
        normalizer: URLNormalizer,
        bloom_filter: BloomFilter,
        default_politeness_delay: float = 1.0
    ):
        self.normalizer = normalizer
        self.bloom_filter = bloom_filter
        self.default_politeness_delay = default_politeness_delay
        
        # Per-domain queues
        self.domain_queues: Dict[str, URLQueue] = {}
        
        # Heap of (ready_time, domain) for politeness scheduling
        self.ready_queue: List[tuple] = []
        
        # Statistics
        self.stats = {
            'added': 0,
            'duplicates': 0,
            'fetched': 0
        }
    
    def add_url(
        self,
        url: str,
        priority: Priority = Priority.NORMAL,
        score: float = 0.0,
        depth: int = 0,
        metadata: dict = None
    ) -> bool:
        """
        Add URL to frontier
        
        Returns:
            True if added, False if duplicate
        """
        # Normalize URL
        normalized = self.normalizer.normalize(url)
        
        # Check for duplicates
        if self.bloom_filter.contains(normalized):
            self.stats['duplicates'] += 1
            return False
        
        # Add to bloom filter
        self.bloom_filter.add(normalized)
        
        # Extract domain
        domain = self.normalizer.get_domain(normalized)
        
        # Get or create domain queue
        if domain not in self.domain_queues:
            self.domain_queues[domain] = URLQueue(
                domain,
                politeness_delay=self.default_politeness_delay
            )
        
        # Create queued URL
        queued_url = QueuedURL(
            priority=priority,
            score=score,
            url=normalized,
            depth=depth,
            metadata=metadata or {}
        )
        
        # Add to domain queue
        self.domain_queues[domain].add(queued_url)
        self.stats['added'] += 1
        
        return True
    
    def add_urls(self, urls: List[tuple]) -> int:
        """
        Bulk add URLs
        
        Args:
            urls: List of (url, priority, score, depth, metadata) tuples
        
        Returns:
            Number of URLs added
        """
        added = 0
        for url_data in urls:
            url = url_data[0]
            priority = url_data[1] if len(url_data) > 1 else Priority.NORMAL
            score = url_data[2] if len(url_data) > 2 else 0.0
            depth = url_data[3] if len(url_data) > 3 else 0
            metadata = url_data[4] if len(url_data) > 4 else None
            
            if self.add_url(url, priority, score, depth, metadata):
                added += 1
        
        return added
    
    async def get_next_url(self, timeout: float = 1.0) -> Optional[QueuedURL]:
        """
        Get next URL to fetch, respecting politeness delays
        
        Args:
            timeout: Maximum time to wait for a URL
        
        Returns:
            QueuedURL or None if timeout
        """
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            # Find ready domains
            ready_domains = [
                domain for domain, queue in self.domain_queues.items()
                if queue.is_ready()
            ]
            
            if not ready_domains:
                # No domains ready, wait a bit
                await asyncio.sleep(0.1)
                continue
            
            # Get domain with highest priority URL
            best_domain = None
            best_url = None
            
            for domain in ready_domains:
                url = self.domain_queues[domain].peek()
                if url and (best_url is None or url < best_url):
                    best_domain = domain
                    best_url = url
            
            if best_domain:
                url = self.domain_queues[best_domain].get_next()
                if url:
                    self.stats['fetched'] += 1
                    return url
            
            await asyncio.sleep(0.1)
        
        return None
    
    def get_stats(self) -> dict:
        """Get frontier statistics"""
        return {
            **self.stats,
            'pending': sum(len(q) for q in self.domain_queues.values()),
            'domains': len(self.domain_queues)
        }
```

## URL Scoring Strategies

### PageRank-based Scoring

```python
class URLScorer:
    """Calculate scores for URL prioritization"""
    
    @staticmethod
    def calculate_score(
        url: str,
        depth: int,
        parent_score: float = 0.0,
        inlink_count: int = 0,
        freshness: float = 1.0
    ) -> float:
        """
        Calculate URL score for prioritization
        
        Factors:
        - Depth: Prefer shallower URLs
        - Parent score: Inherit from parent page
        - Inlinks: Popular pages get higher priority
        - Freshness: Prefer recently discovered URLs
        """
        # Base score from depth (exponential decay)
        depth_score = 100 * (0.8 ** depth)
        
        # Parent score contribution (dampened)
        inherited_score = parent_score * 0.5
        
        # Inlink score (logarithmic)
        inlink_score = math.log(inlink_count + 1) * 10
        
        # Freshness boost (decays over time)
        freshness_score = freshness * 20
        
        # Combined score
        return depth_score + inherited_score + inlink_score + freshness_score
    
    @staticmethod
    def domain_reputation(domain: str, reputation_db: dict) -> float:
        """Get domain reputation score"""
        return reputation_db.get(domain, 0.5)
    
    @staticmethod
    def url_features(url: str) -> dict:
        """Extract features for ML-based scoring"""
        parsed = urlparse(url)
        
        return {
            'depth': url.count('/'),
            'has_query': bool(parsed.query),
            'path_length': len(parsed.path),
            'has_file_extension': '.' in parsed.path.split('/')[-1],
            'is_https': parsed.scheme == 'https',
        }
```

## Distributed Frontier with Redis

```python
import redis
import json
from typing import Optional

class DistributedURLFrontier:
    """Redis-backed distributed URL frontier"""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        cluster_id: str,
        bloom_filter: DistributedBloomFilter
    ):
        self.redis = redis_client
        self.cluster_id = cluster_id
        self.bloom_filter = bloom_filter
        
        # Redis keys
        self.priority_key = f"frontier:{cluster_id}:priority"
        self.domain_key_prefix = f"frontier:{cluster_id}:domain"
        self.stats_key = f"frontier:{cluster_id}:stats"
    
    def add_url(self, url: str, priority: int, score: float, metadata: dict = None) -> bool:
        """Add URL to distributed frontier"""
        # Normalize
        normalized = URLNormalizer.normalize(url)
        
        # Check bloom filter
        if not self.bloom_filter.add(normalized):
            return False  # Duplicate
        
        # Extract domain
        domain = URLNormalizer.get_domain(normalized)
        
        # Create URL data
        url_data = {
            'url': normalized,
            'priority': priority,
            'score': score,
            'metadata': metadata or {},
            'added_time': datetime.now().isoformat()
        }
        
        # Add to domain-specific queue
        domain_key = f"{self.domain_key_prefix}:{domain}"
        self.redis.zadd(domain_key, {json.dumps(url_data): score})
        
        # Update domain in priority queue
        self.redis.zadd(self.priority_key, {domain: priority})
        
        # Increment stats
        self.redis.hincrby(self.stats_key, 'added', 1)
        
        return True
    
    def get_next_url(self, worker_id: str) -> Optional[dict]:
        """Get next URL for worker"""
        # Get highest priority domain
        domains = self.redis.zrange(self.priority_key, 0, 0)
        if not domains:
            return None
        
        domain = domains[0].decode('utf-8')
        
        # Check politeness (use worker-specific last fetch time)
        politeness_key = f"{self.domain_key_prefix}:{domain}:last_fetch:{worker_id}"
        last_fetch = self.redis.get(politeness_key)
        
        if last_fetch:
            elapsed = time.time() - float(last_fetch)
            if elapsed < 1.0:  # Politeness delay
                return None
        
        # Get URL from domain queue
        domain_key = f"{self.domain_key_prefix}:{domain}"
        urls = self.redis.zpopmax(domain_key, 1)
        
        if not urls:
            # Domain queue empty, remove from priority queue
            self.redis.zrem(self.priority_key, domain)
            return None
        
        # Update last fetch time
        self.redis.set(politeness_key, time.time(), ex=10)
        
        # Parse URL data
        url_json, score = urls[0]
        url_data = json.loads(url_json)
        
        # Increment stats
        self.redis.hincrby(self.stats_key, 'fetched', 1)
        
        return url_data
```

## Testing Strategy

```python
import pytest

class TestURLFrontier:
    def test_url_normalization(self):
        normalizer = URLNormalizer()
        
        assert normalizer.normalize("http://EXAMPLE.COM/path") == \
               normalizer.normalize("http://example.com/path")
        
        assert normalizer.normalize("http://example.com:80/path") == \
               "http://example.com/path"
        
        assert normalizer.normalize("http://example.com/a//b") == \
               "http://example.com/a/b"
    
    def test_duplicate_detection(self):
        bloom = BloomFilter(expected_elements=1000)
        
        assert bloom.add("http://example.com/page1")
        assert not bloom.add("http://example.com/page1")  # Duplicate
    
    def test_priority_ordering(self):
        frontier = URLFrontier(URLNormalizer(), BloomFilter(1000))
        
        frontier.add_url("http://example.com/low", Priority.LOW, score=1.0)
        frontier.add_url("http://example.com/high", Priority.HIGH, score=100.0)
        
        url = asyncio.run(frontier.get_next_url())
        assert url.priority == Priority.HIGH
    
    def test_politeness_delay(self):
        frontier = URLFrontier(
            URLNormalizer(),
            BloomFilter(1000),
            default_politeness_delay=1.0
        )
        
        frontier.add_url("http://example.com/1", Priority.NORMAL)
        frontier.add_url("http://example.com/2", Priority.NORMAL)
        
        # First URL should be available immediately
        url1 = asyncio.run(frontier.get_next_url(timeout=0.1))
        assert url1 is not None
        
        # Second URL should wait for politeness delay
        url2 = asyncio.run(frontier.get_next_url(timeout=0.1))
        assert url2 is None  # Not ready yet
```

## Performance Optimization

### 1. Memory Efficiency
- Use Bloom filters for duplicate detection (probabilistic)
- Shard large frontiers across multiple Redis instances
- Compress URL metadata

### 2. Throughput
- Batch operations where possible
- Use Redis pipelining
- Parallel queue operations per domain

### 3. Scalability
- Partition URLs by domain hash
- Use consistent hashing for distribution
- Worker-local caching of domain queues

## Best Practices

1. **Always normalize URLs** before adding to frontier
2. **Use politeness delays** per domain to avoid overwhelming servers
3. **Implement retry logic** with exponential backoff
4. **Monitor queue sizes** and adjust priorities dynamically
5. **Persist frontier state** for crash recovery
6. **Use distributed locks** for coordination in multi-worker setup

## References

- "Mercator: A Scalable, Extensible Web Crawler" - Paper on URL frontier design
- Redis documentation on sorted sets and pipelining
- Bloom filter theory and optimal parameters
