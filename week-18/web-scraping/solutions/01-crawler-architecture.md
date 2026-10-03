# Crawler Architecture - System Design Guide

## Overview

A production web crawler is a distributed system with multiple cooperating components. This guide covers the high-level architecture, design patterns, and implementation strategies for building a scalable crawler.

## Architecture Patterns

### 1. Monolithic Architecture (Simple Start)

**Structure:**
```
┌─────────────────────────────────────┐
│       Single Process Crawler        │
│                                     │
│  ┌──────────┐    ┌──────────────┐ │
│  │   HTTP   │    │  URL Queue   │ │
│  │  Client  │◄───┤  (in-memory) │ │
│  └────┬─────┘    └──────────────┘ │
│       │                            │
│       ▼                            │
│  ┌──────────┐    ┌──────────────┐ │
│  │  Parser  │───►│   Storage    │ │
│  └──────────┘    └──────────────┘ │
└─────────────────────────────────────┘
```

**Pros:**
- Simple to develop and debug
- No coordination overhead
- Good for small-scale crawls (< 1M pages)

**Cons:**
- Single point of failure
- Limited by single machine resources
- No horizontal scalability

**When to use:** Learning, prototyping, small crawls

### 2. Microservices Architecture (Production Scale)

**Structure:**
```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Scheduler  │◄───┤  URL Manager │───►│ Worker Pool  │
│  (Master)    │    │   (Frontier) │    │ (Fetchers)   │
└──────┬───────┘    └──────────────┘    └──────┬───────┘
       │                                        │
       │            ┌──────────────┐           │
       └───────────►│   Message    │◄──────────┘
                    │    Queue     │
                    │ (RabbitMQ/   │
                    │   Kafka)     │
                    └──────┬───────┘
                           │
       ┌───────────────────┴────────────────┐
       │                                    │
       ▼                                    ▼
┌──────────────┐                    ┌──────────────┐
│   Parsers    │                    │   Storage    │
│  (Workers)   │───────────────────►│   Cluster    │
└──────────────┘                    └──────────────┘
```

**Components:**

1. **Scheduler (Master)**
   - Coordinates crawl jobs
   - Monitors worker health
   - Handles failures and retries
   - Manages crawl priorities

2. **URL Manager (Frontier)**
   - Stores URLs to crawl
   - Implements politeness policies
   - Deduplicates URLs
   - Prioritizes crawls

3. **Worker Pool (Fetchers)**
   - Makes HTTP requests
   - Handles redirects and errors
   - Respects rate limits
   - Returns HTML content

4. **Parsers**
   - Extract data from HTML
   - Extract new URLs
   - Process JavaScript if needed
   - Validate data quality

5. **Message Queue**
   - Distributes work to workers
   - Ensures at-least-once delivery
   - Handles backpressure
   - Provides ordering guarantees

6. **Storage Cluster**
   - Stores crawled content
   - Stores metadata
   - Handles high write throughput
   - Provides query capabilities

**Pros:**
- Horizontal scalability
- Fault tolerance
- Component isolation
- Easy to upgrade components

**Cons:**
- Complex to operate
- Network overhead
- Coordination complexity
- More failure modes

**When to use:** Large-scale production crawls

## Core Components Deep Dive

### URL Frontier Design

The URL frontier is the heart of the crawler. It manages which URLs to crawl next.

**Requirements:**
- Fast URL addition (millions per second)
- Fast URL retrieval
- Duplicate detection
- Priority management
- Politeness (per-domain rate limiting)
- Persistence (survive crashes)

**Implementation Strategy:**

```python
class URLFrontier:
    """
    Multi-queue URL frontier with politeness and priorities
    """
    def __init__(self, redis_client, bloom_filter_size=1e9):
        self.redis = redis_client
        self.bloom_filter = BloomFilter(size=bloom_filter_size, error_rate=0.001)
        
    def add_url(self, url, priority=5, depth=0):
        """
        Add URL to frontier if not seen before
        
        Steps:
        1. Normalize URL
        2. Check if seen (Bloom filter + Redis)
        3. Extract domain
        4. Add to domain-specific queue
        5. Update domain metadata
        """
        # Normalize URL
        normalized = self.normalize_url(url)
        
        # Fast duplicate check with Bloom filter
        if normalized in self.bloom_filter:
            # Might be duplicate, check Redis
            if self.redis.sismember('seen_urls', normalized):
                return False  # Duplicate
        
        # Add to Bloom filter
        self.bloom_filter.add(normalized)
        self.redis.sadd('seen_urls', normalized)
        
        # Extract domain
        domain = urlparse(normalized).netloc
        
        # Add to domain-specific queue with priority
        queue_key = f"queue:{domain}:priority:{priority}"
        self.redis.lpush(queue_key, normalized)
        
        # Update domain metadata
        self.redis.hset(f"domain:{domain}", mapping={
            'url_count': self.redis.hincrby(f"domain:{domain}", 'url_count', 1),
            'last_crawl': time.time()
        })
        
        return True
    
    def get_next_url(self):
        """
        Get next URL to crawl respecting politeness
        
        Steps:
        1. Select domain ready to crawl (respecting delays)
        2. Get highest priority URL from that domain
        3. Update domain last_crawl time
        4. Return URL
        """
        # Find domains ready to crawl
        current_time = time.time()
        ready_domains = []
        
        for domain in self.get_all_domains():
            last_crawl = float(self.redis.hget(f"domain:{domain}", 'last_crawl') or 0)
            min_delay = float(self.redis.hget(f"domain:{domain}", 'min_delay') or 1.0)
            
            if current_time - last_crawl >= min_delay:
                ready_domains.append(domain)
        
        if not ready_domains:
            return None  # No domains ready
        
        # Select domain (round-robin or weighted)
        domain = random.choice(ready_domains)
        
        # Get highest priority URL for this domain
        for priority in range(10, -1, -1):  # 10 to 0
            queue_key = f"queue:{domain}:priority:{priority}"
            url = self.redis.rpop(queue_key)
            if url:
                # Update last crawl time
                self.redis.hset(f"domain:{domain}", 'last_crawl', current_time)
                return url.decode('utf-8')
        
        return None
```

**Key Design Decisions:**

1. **Bloom Filter for Seen URLs**
   - Memory efficient: 1 billion URLs in ~1.2GB
   - Fast lookup: O(k) where k is number of hash functions
   - False positive rate: Tunable (0.1% recommended)
   - Backup with Redis for false positive handling

2. **Per-Domain Queues**
   - Enables politeness policies
   - Prevents one domain from dominating
   - Allows per-domain priorities

3. **Priority Levels**
   - Multiple queues per domain by priority
   - High priority: Homepage, important pages
   - Low priority: Deep pages, assets

4. **Persistence with Redis**
   - Survive process restarts
   - Enable distributed access
   - Fast operations (in-memory)

### Fetch/Parse Pipeline

**Async Pipeline Pattern:**

```python
import asyncio
import aiohttp
from typing import AsyncIterator

class CrawlPipeline:
    """
    Async pipeline for fetching and parsing pages
    """
    def __init__(self, max_concurrency=100):
        self.max_concurrency = max_concurrency
        self.session = None
        self.semaphore = asyncio.Semaphore(max_concurrency)
    
    async def __aenter__(self):
        # Configure connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrency,
            limit_per_host=10,  # Max per domain
            ttl_dns_cache=300,  # Cache DNS
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=60,
            connect=10,
            sock_read=30
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def fetch(self, url: str) -> dict:
        """
        Fetch single URL with error handling
        """
        async with self.semaphore:  # Limit concurrency
            try:
                async with self.session.get(url) as response:
                    content = await response.read()
                    return {
                        'url': url,
                        'status': response.status,
                        'headers': dict(response.headers),
                        'content': content,
                        'error': None
                    }
            except asyncio.TimeoutError:
                return {'url': url, 'error': 'timeout'}
            except aiohttp.ClientError as e:
                return {'url': url, 'error': str(e)}
    
    async def parse(self, response: dict) -> dict:
        """
        Parse HTML and extract data
        """
        if response.get('error') or response.get('status') != 200:
            return {'extracted_urls': [], 'data': None, 'error': response.get('error')}
        
        try:
            # Parse HTML (detailed in 05-html-parser.md)
            html = response['content'].decode('utf-8', errors='ignore')
            
            # Extract links
            links = self.extract_links(html, response['url'])
            
            # Extract data
            data = self.extract_data(html)
            
            return {
                'extracted_urls': links,
                'data': data,
                'error': None
            }
        except Exception as e:
            return {'extracted_urls': [], 'data': None, 'error': str(e)}
    
    async def crawl_many(self, urls: list) -> AsyncIterator[dict]:
        """
        Crawl multiple URLs concurrently
        """
        # Create fetch tasks
        fetch_tasks = [self.fetch(url) for url in urls]
        
        # Fetch with limited concurrency
        for coro in asyncio.as_completed(fetch_tasks):
            response = await coro
            
            # Parse immediately
            result = await self.parse(response)
            
            yield result
```

**Pipeline Stages:**

1. **URL Selection** (Frontier)
   - Select URLs respecting politeness
   - Batch URLs for efficiency

2. **DNS Resolution**
   - Cache DNS results
   - Parallel resolution
   - Handle DNS failures

3. **HTTP Fetch**
   - Connection pooling
   - Keep-alive connections
   - Retry on transient errors
   - Follow redirects

4. **Content Processing**
   - Decompress (gzip, brotli)
   - Detect encoding
   - Handle partial content

5. **Parsing**
   - Extract links
   - Extract data
   - Validate structure

6. **Storage**
   - Save raw HTML
   - Save extracted data
   - Update metadata

## Distributed Coordination

### Master-Worker Pattern

**Master Responsibilities:**
- Track crawl progress
- Assign URLs to workers
- Handle worker failures
- Aggregate statistics
- Implement crawl policies

**Worker Responsibilities:**
- Fetch assigned URLs
- Parse content
- Report results to master
- Handle local errors

**Communication Pattern:**

```python
# Master side (pseudocode)
class CrawlMaster:
    def __init__(self):
        self.frontier = URLFrontier()
        self.workers = WorkerPool()
        self.task_queue = Queue()
        self.result_queue = Queue()
    
    async def schedule_tasks(self):
        """Continuously assign tasks to workers"""
        while True:
            # Get batch of URLs from frontier
            urls = self.frontier.get_batch(size=1000)
            
            if not urls:
                await asyncio.sleep(1)
                continue
            
            # Create tasks
            tasks = [{'url': url, 'id': generate_id()} for url in urls]
            
            # Send to queue
            for task in tasks:
                await self.task_queue.put(task)
    
    async def handle_results(self):
        """Process results from workers"""
        while True:
            result = await self.result_queue.get()
            
            # Add extracted URLs to frontier
            for url in result.get('extracted_urls', []):
                self.frontier.add_url(url)
            
            # Save data
            await self.save_result(result)
            
            # Update statistics
            self.update_stats(result)

# Worker side (pseudocode)
class CrawlWorker:
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.pipeline = CrawlPipeline()
    
    async def run(self):
        """Main worker loop"""
        async with self.pipeline:
            while True:
                # Get task from queue
                task = await self.task_queue.get()
                
                # Execute crawl
                result = await self.pipeline.fetch(task['url'])
                parsed = await self.pipeline.parse(result)
                
                # Report result
                await self.result_queue.put({
                    'task_id': task['id'],
                    'worker_id': self.worker_id,
                    'url': task['url'],
                    **parsed
                })
                
                # Acknowledge task
                self.task_queue.task_done()
```

### Work Distribution Strategies

**1. Central Queue (Simple)**
- Master maintains URL queue
- Workers pull URLs from queue
- Pros: Simple, good load balancing
- Cons: Queue can be bottleneck

**2. Consistent Hashing (Scalable)**
- URLs partitioned by domain hash
- Each worker responsible for hash range
- Pros: No central coordination, scalable
- Cons: Load imbalance if hash distribution poor

**3. Work Stealing (Optimal)**
- Workers have local queues
- Idle workers steal from busy workers
- Pros: Excellent load balancing
- Cons: More complex coordination

## Fault Tolerance

### Failure Scenarios and Solutions

**1. Worker Crashes**
- **Detection:** Heartbeat monitoring (missed 3 heartbeats = dead)
- **Recovery:** Reassign tasks from dead worker
- **Prevention:** Process supervision (systemd, supervisor)

**2. Master Crashes**
- **Detection:** Workers can't connect to master
- **Recovery:** Master election (using Zookeeper, etcd, Consul)
- **Prevention:** Master should be stateless, state in Redis/DB

**3. Network Partitions**
- **Detection:** Timeouts on communication
- **Recovery:** Retry logic, exponential backoff
- **Prevention:** Multiple network paths, redundancy

**4. Data Loss**
- **Detection:** Checksums, validation
- **Recovery:** Replay from logs/queue
- **Prevention:** Durable queues, replication

### Idempotency

All operations should be idempotent:
- URL addition: Check if exists before adding
- Data storage: Use upsert operations
- Task processing: Task IDs prevent duplicate work

```python
# Example: Idempotent URL processing
def process_url_idempotent(url, task_id):
    # Check if already processed
    if redis.exists(f"processed:{task_id}"):
        return  # Already done
    
    # Do work
    result = crawl_and_parse(url)
    
    # Save result and mark as processed atomically
    with redis.pipeline() as pipe:
        pipe.set(f"result:{task_id}", result)
        pipe.set(f"processed:{task_id}", "1", ex=86400)  # 24h TTL
        pipe.execute()
```

## Scalability Considerations

### Horizontal Scaling

**Add more workers:**
- Increase fetch throughput linearly
- Up to bottlenecks (DNS, frontier, storage)

**Scale frontier:**
- Shard URL queue by domain
- Use distributed data structure (Redis Cluster)

**Scale storage:**
- Shard by URL hash or domain
- Use distributed storage (Cassandra, ScyllaDB)

### Vertical Scaling

**Optimize single worker:**
- Increase concurrency (async/await)
- Use connection pooling
- Profile and optimize hot paths

**Optimize frontier:**
- More memory for Bloom filters
- Faster Redis (more RAM, SSD)

### Performance Targets

**Small Crawl (1 worker):**
- 10-50 pages/second
- 100 concurrent connections
- 1GB memory

**Medium Crawl (10 workers):**
- 100-500 pages/second
- 1000 concurrent connections
- 10GB total memory

**Large Crawl (100+ workers):**
- 1000-10000 pages/second
- 10000+ concurrent connections
- 100GB+ total memory

## Monitoring and Observability

### Key Metrics

**Throughput:**
- Pages fetched per second
- Bytes downloaded per second
- URLs added to frontier per second

**Latency:**
- DNS resolution time
- Connection time
- Download time
- Parse time

**Errors:**
- HTTP errors (by status code)
- Timeouts
- Parse errors
- Network errors

**Resource Usage:**
- CPU utilization
- Memory usage
- Network bandwidth
- Disk I/O

### Instrumentation Example

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
pages_fetched = Counter('crawler_pages_fetched_total', 'Total pages fetched')
fetch_duration = Histogram('crawler_fetch_duration_seconds', 'Fetch duration')
active_workers = Gauge('crawler_active_workers', 'Number of active workers')
frontier_size = Gauge('crawler_frontier_size', 'URLs in frontier')

# Instrument code
async def fetch_with_metrics(url):
    with fetch_duration.time():
        result = await fetch(url)
    
    pages_fetched.inc()
    return result
```

## Next Steps

1. Implement `02-http-client.md` for robust HTTP handling
2. Implement `04-url-frontier.md` for URL management
3. Implement `08-rate-limiting.md` for politeness
4. Implement `09-distributed-crawling.md` for scaling

## References

- "Mercator: A Scalable, Extensible Web Crawler" (Heydon & Najork, 1999)
- "UbiCrawler: A Scalable Fully Distributed Web Crawler" (Boldi et al., 2004)
- Scrapy Architecture: https://docs.scrapy.org/en/latest/topics/architecture.html
- Apache Nutch: https://nutch.apache.org/
