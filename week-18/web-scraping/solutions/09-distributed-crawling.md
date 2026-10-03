# Distributed Crawling - Scaling to Billions of Pages

## Overview

Distributed crawling enables horizontal scaling by distributing work across multiple machines. This guide covers architectures, coordination, and implementation strategies for large-scale web crawling.

## Why Distribute?

### Single Machine Limits

**Throughput:** ~1000 pages/second (optimized)
**Bottlenecks:**
- Network bandwidth (1-10 Gbps)
- CPU (parsing, compression)
- Memory (URL frontier, caches)
- Connection limits (65K ports)

### Distributed Benefits

- **10-100x throughput** with 10-100 machines
- **Fault tolerance** - survive machine failures
- **Geographic distribution** - crawl from multiple locations
- **Specialization** - different machines for different tasks

## Architecture Patterns

### 1. Master-Worker (Centralized)

```
                    ┌──────────────┐
                    │    Master    │
                    │  (Scheduler) │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Worker 1 │    │ Worker 2 │    │ Worker N │
    │(Fetcher) │    │(Fetcher) │    │(Fetcher) │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
                  ┌─────────────┐
                  │   Storage   │
                  └─────────────┘
```

**Pros:**
- Simple to implement
- Centralized control
- Easy to monitor

**Cons:**
- Master is bottleneck
- Master is single point of failure
- Coordination overhead

### 2. Decentralized (Peer-to-Peer)

```
┌──────────┐        ┌──────────┐        ┌──────────┐
│ Worker 1 │◄──────►│ Worker 2 │◄──────►│ Worker 3 │
│(Frontier)│        │(Frontier)│        │(Frontier)│
└──────────┘        └──────────┘        └──────────┘
     ▲                   ▲                   ▲
     └───────────────────┼───────────────────┘
                         │
                  ┌──────────────┐
                  │  Shared URL  │
                  │   Frontier   │
                  │   (Redis)    │
                  └──────────────┘
```

**Pros:**
- No single point of failure
- Scales horizontally
- Lower coordination overhead

**Cons:**
- More complex
- Harder to monitor
- Synchronization challenges

### 3. Hybrid (Recommended)

```
       ┌──────────────────────────────────┐
       │   Coordinator (Lightweight)      │
       │   - Health monitoring            │
       │   - Load balancing               │
       │   - Configuration distribution   │
       └──────────────┬───────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │Worker 1 │   │Worker 2 │   │Worker N │
   │Self-    │   │Self-    │   │Self-    │
   │managed  │   │managed  │   │managed  │
   └────┬────┘   └────┬────┘   └────┬────┘
        │             │             │
        └─────────────┼─────────────┘
                      ▼
              ┌──────────────┐
              │ Shared State │
              │   (Redis)    │
              └──────────────┘
```

**Pros:**
- Combines benefits of both
- Coordinator only for monitoring
- Workers are autonomous
- Survives coordinator failure

## URL Partitioning Strategies

### Strategy 1: Domain-Based Partitioning

```python
import hashlib

def assign_url_to_worker(url, num_workers):
    """
    Assign URL to worker based on domain hash
    """
    domain = urlparse(url).netloc
    hash_value = int(hashlib.md5(domain.encode()).hexdigest(), 16)
    worker_id = hash_value % num_workers
    return worker_id

# Benefit: All URLs from same domain go to same worker
# - Easier to enforce politeness policies
# - Better connection reuse
```

### Strategy 2: URL Hash Partitioning

```python
def assign_url_to_worker_random(url, num_workers):
    """
    Assign URL randomly based on full URL hash
    """
    hash_value = int(hashlib.md5(url.encode()).hexdigest(), 16)
    worker_id = hash_value % num_workers
    return worker_id

# Benefit: Better load balancing
# Drawback: Same domain might be split across workers
```

### Strategy 3: Consistent Hashing

```python
import bisect

class ConsistentHash:
    """
    Consistent hashing for minimal remapping when workers change
    """
    def __init__(self, num_workers, num_virtual_nodes=150):
        self.num_workers = num_workers
        self.num_virtual_nodes = num_virtual_nodes
        self.ring = []
        self._build_ring()
    
    def _build_ring(self):
        """Build hash ring with virtual nodes"""
        for worker_id in range(self.num_workers):
            for i in range(self.num_virtual_nodes):
                # Create virtual nodes
                key = f"worker-{worker_id}-vnode-{i}"
                hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
                self.ring.append((hash_value, worker_id))
        
        # Sort ring by hash value
        self.ring.sort()
    
    def get_worker(self, url):
        """Get worker for URL using consistent hashing"""
        url_hash = int(hashlib.md5(url.encode()).hexdigest(), 16)
        
        # Binary search for position in ring
        idx = bisect.bisect(self.ring, (url_hash, 0))
        if idx == len(self.ring):
            idx = 0
        
        return self.ring[idx][1]

# Benefit: When worker is added/removed, only ~1/N URLs need remapping
```

## Work Distribution

### Push Model (Master pushes tasks to workers)

```python
# Master side
class TaskDistributor:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.worker_queues = {}  # worker_id -> queue_key
    
    async def distribute_urls(self, urls):
        """Distribute URLs to worker queues"""
        hasher = ConsistentHash(num_workers=10)
        
        # Group URLs by worker
        worker_urls = {}
        for url in urls:
            worker_id = hasher.get_worker(url)
            if worker_id not in worker_urls:
                worker_urls[worker_id] = []
            worker_urls[worker_id].append(url)
        
        # Push to worker queues
        for worker_id, worker_url_list in worker_urls.items():
            queue_key = f"worker:{worker_id}:queue"
            self.redis.lpush(queue_key, *worker_url_list)

# Worker side
class Worker:
    def __init__(self, worker_id, redis_client):
        self.worker_id = worker_id
        self.redis = redis_client
        self.queue_key = f"worker:{worker_id}:queue"
    
    async def run(self):
        """Process URLs from queue"""
        while True:
            # Pop URL from queue
            url = self.redis.rpop(self.queue_key)
            if not url:
                await asyncio.sleep(1)
                continue
            
            # Process URL
            await self.fetch_and_parse(url.decode())
```

### Pull Model (Workers pull tasks from shared queue)

```python
# Shared queue (simpler, better load balancing)
class SharedQueue:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.queue_key = "global:url_queue"
    
    def add_urls(self, urls):
        """Add URLs to shared queue"""
        if urls:
            self.redis.lpush(self.queue_key, *urls)
    
    def get_next_url(self, timeout=10):
        """Get next URL (blocking)"""
        result = self.redis.brpop(self.queue_key, timeout=timeout)
        if result:
            _, url = result
            return url.decode()
        return None

# Worker pulls from shared queue
class Worker:
    def __init__(self, worker_id, queue):
        self.worker_id = worker_id
        self.queue = queue
    
    async def run(self):
        """Pull and process URLs"""
        while True:
            url = self.queue.get_next_url()
            if url:
                await self.fetch_and_parse(url)
```

## Coordination with Redis

### URL Frontier in Redis

```python
class DistributedFrontier:
    """
    Distributed URL frontier using Redis
    """
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def add_url(self, url, priority=5):
        """Add URL to frontier"""
        # Check if already seen (using Bloom filter)
        if self._is_seen(url):
            return False
        
        # Mark as seen
        self._mark_seen(url)
        
        # Add to priority queue
        domain = urlparse(url).netloc
        queue_key = f"queue:{domain}:p{priority}"
        self.redis.lpush(queue_key, url)
        
        # Track domain
        self.redis.sadd("domains", domain)
        
        return True
    
    def _is_seen(self, url):
        """Check if URL already seen"""
        # Use Redis Bloom filter (RedisBloom module)
        return self.redis.bf().exists("seen_urls", url)
    
    def _mark_seen(self, url):
        """Mark URL as seen"""
        self.redis.bf().add("seen_urls", url)
    
    def get_next_url(self):
        """Get next URL respecting politeness"""
        # Get domains ready to crawl
        current_time = time.time()
        
        # Lua script for atomic operation
        script = """
        local domains = redis.call('SMEMBERS', 'domains')
        local current_time = tonumber(ARGV[1])
        
        for _, domain in ipairs(domains) do
            local last_crawl = tonumber(redis.call('GET', 'last_crawl:' .. domain) or 0)
            local min_delay = tonumber(redis.call('GET', 'delay:' .. domain) or 1)
            
            if current_time - last_crawl >= min_delay then
                -- Try to get URL from this domain (high to low priority)
                for priority = 10, 0, -1 do
                    local queue_key = 'queue:' .. domain .. ':p' .. priority
                    local url = redis.call('RPOP', queue_key)
                    
                    if url then
                        redis.call('SET', 'last_crawl:' .. domain, current_time)
                        return url
                    end
                end
            end
        end
        
        return nil
        """
        
        url = self.redis.eval(script, 0, current_time)
        return url.decode() if url else None
```

### Distributed Locking

```python
import redis
from redis.lock import Lock

class DistributedLock:
    """
    Distributed lock for coordination
    """
    def __init__(self, redis_client, name, timeout=10):
        self.lock = Lock(redis_client, name, timeout=timeout)
    
    def __enter__(self):
        self.lock.acquire()
        return self
    
    def __exit__(self, *args):
        self.lock.release()

# Usage: Ensure only one worker processes a domain at a time
with DistributedLock(redis, f"lock:domain:{domain}"):
    # Critical section - only one worker can be here
    url = frontier.get_next_url_for_domain(domain)
    result = fetch(url)
```

## Load Balancing

### Work Stealing

```python
class WorkStealingWorker:
    """
    Worker that steals work from others when idle
    """
    def __init__(self, worker_id, redis_client, num_workers):
        self.worker_id = worker_id
        self.redis = redis_client
        self.num_workers = num_workers
        self.local_queue = f"worker:{worker_id}:queue"
    
    async def run(self):
        while True:
            # Try local queue first
            url = self.redis.rpop(self.local_queue)
            
            if url:
                await self.process(url.decode())
            else:
                # Local queue empty, try stealing
                stolen = await self.steal_work()
                if stolen:
                    await self.process(stolen)
                else:
                    await asyncio.sleep(1)
    
    async def steal_work(self):
        """Steal work from another worker"""
        # Try stealing from other workers in random order
        other_workers = [i for i in range(self.num_workers) if i != self.worker_id]
        random.shuffle(other_workers)
        
        for other_id in other_workers:
            # Try to steal from other's queue
            other_queue = f"worker:{other_id}:queue"
            
            # Atomically move item from other's queue to ours
            url = self.redis.rpoplpush(other_queue, self.local_queue)
            if url:
                return url.decode()
        
        return None
```

### Dynamic Load Balancing

```python
class LoadBalancer:
    """
    Monitor workers and rebalance load
    """
    def __init__(self, redis_client, num_workers):
        self.redis = redis_client
        self.num_workers = num_workers
    
    async def balance(self):
        """Periodically rebalance load"""
        while True:
            await asyncio.sleep(60)  # Balance every minute
            
            # Get queue sizes
            queue_sizes = []
            for i in range(self.num_workers):
                size = self.redis.llen(f"worker:{i}:queue")
                queue_sizes.append((i, size))
            
            # Sort by queue size
            queue_sizes.sort(key=lambda x: x[1])
            
            # Move work from busiest to least busy
            least_busy = queue_sizes[0][0]
            most_busy = queue_sizes[-1][0]
            
            if queue_sizes[-1][1] > queue_sizes[0][1] * 2:
                # Imbalanced, move some work
                # Calculate how many to move to balance more evenly
                avg_size = sum(size for _, size in queue_sizes) / len(queue_sizes)
                
                # Move from busiest to those below average
                for worker_id, size in reversed(queue_sizes):
                    if size > avg_size * 1.2:  # More than 20% above average
                        num_to_move = int((size - avg_size) / 2)
                        
                        # Find least busy worker to move to
                        for target_id, target_size in queue_sizes:
                            if target_size < avg_size * 0.8:  # Below average
                                for _ in range(num_to_move):
                                    self.redis.rpoplpush(
                                        f"worker:{worker_id}:queue",
                                        f"worker:{target_id}:queue"
                                    )
                                break
```

## Failure Handling

### Worker Health Monitoring

```python
class HealthMonitor:
    """
    Monitor worker health with heartbeats
    """
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def worker_heartbeat(self, worker_id):
        """Worker reports it's alive"""
        key = f"heartbeat:{worker_id}"
        self.redis.setex(key, 30, "alive")  # Expire in 30 seconds
    
    def get_alive_workers(self):
        """Get list of alive workers"""
        alive = []
        for i in range(100):  # Assuming max 100 workers
            key = f"heartbeat:{i}"
            if self.redis.exists(key):
                alive.append(i)
        return alive
    
    async def monitor(self):
        """Continuously monitor worker health"""
        while True:
            alive = self.get_alive_workers()
            print(f"Alive workers: {alive}")
            
            # Detect dead workers
            # Reassign their work
            # ...
            
            await asyncio.sleep(10)

# Worker side
class Worker:
    async def run(self):
        while True:
            # Send heartbeat
            health_monitor.worker_heartbeat(self.worker_id)
            
            # Do work
            await self.process_urls()
            
            await asyncio.sleep(5)
```

### Task Recovery

```python
class TaskTracker:
    """
    Track in-flight tasks for recovery
    """
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def start_task(self, task_id, worker_id, url):
        """Mark task as started"""
        self.redis.hset(f"task:{task_id}", mapping={
            'worker_id': worker_id,
            'url': url,
            'started_at': time.time(),
            'status': 'in_progress'
        })
        
        # Add to worker's active tasks
        self.redis.sadd(f"worker:{worker_id}:active", task_id)
    
    def complete_task(self, task_id, worker_id):
        """Mark task as completed"""
        self.redis.hset(f"task:{task_id}", 'status', 'completed')
        self.redis.srem(f"worker:{worker_id}:active", task_id)
    
    def recover_failed_tasks(self, dead_worker_id):
        """Recover tasks from dead worker"""
        # Get tasks that were assigned to dead worker
        task_ids = self.redis.smembers(f"worker:{dead_worker_id}:active")
        
        recovered = []
        for task_id in task_ids:
            task = self.redis.hgetall(f"task:{task_id}")
            if task.get(b'status') == b'in_progress':
                # Requeue URL
                url = task[b'url'].decode()
                recovered.append(url)
        
        return recovered
```

## Monitoring and Metrics

### Distributed Metrics Collection

```python
from prometheus_client import Counter, Gauge, Histogram

class DistributedMetrics:
    """
    Collect metrics from distributed workers
    """
    def __init__(self):
        self.pages_fetched = Counter(
            'pages_fetched_total',
            'Total pages fetched',
            ['worker_id', 'status']
        )
        
        self.queue_size = Gauge(
            'queue_size',
            'URLs in queue',
            ['worker_id']
        )
        
        self.fetch_duration = Histogram(
            'fetch_duration_seconds',
            'Fetch duration',
            ['worker_id']
        )
    
    def record_fetch(self, worker_id, status, duration):
        self.pages_fetched.labels(worker_id=worker_id, status=status).inc()
        self.fetch_duration.labels(worker_id=worker_id).observe(duration)

# Each worker reports metrics
metrics = DistributedMetrics()

async def fetch_with_metrics(url, worker_id):
    start = time.time()
    result = await fetch(url)
    duration = time.time() - start
    
    metrics.record_fetch(
        worker_id=worker_id,
        status=result['status'],
        duration=duration
    )
```

## Testing Distributed Systems

### Chaos Testing

```python
import random

class ChaosMonkey:
    """
    Randomly kill workers to test fault tolerance
    """
    def __init__(self, workers):
        self.workers = workers
    
    async def cause_chaos(self):
        while True:
            await asyncio.sleep(random.randint(60, 300))
            
            # Kill random worker
            worker = random.choice(self.workers)
            print(f"💥 Killing worker {worker.worker_id}")
            await worker.stop()
            
            # System should recover...
```

## Performance Targets

### Small Cluster (5 workers)
- **Throughput:** 1,000-5,000 pages/second
- **Coordination overhead:** <5%
- **Recovery time:** <30 seconds

### Medium Cluster (50 workers)
- **Throughput:** 10,000-50,000 pages/second
- **Coordination overhead:** <2%
- **Recovery time:** <60 seconds

### Large Cluster (500 workers)
- **Throughput:** 100,000+ pages/second
- **Coordination overhead:** <1%
- **Recovery time:** <120 seconds

## Conclusion

**Key Takeaways:**

1. **Choose the right architecture:**
   - Master-worker: Simple, good for small scale
   - Decentralized: Scales better, more complex
   - Hybrid: Best of both worlds

2. **Partition intelligently:**
   - Domain-based for politeness
   - Consistent hashing for flexibility

3. **Handle failures:**
   - Heartbeat monitoring
   - Task recovery
   - Automatic reassignment

4. **Monitor everything:**
   - Worker health
   - Queue sizes
   - Throughput metrics

**Next Steps:**
- Study `01-crawler-architecture.md` for overall design
- Study `08-rate-limiting.md` for politeness at scale
- Study `11-data-storage.md` for distributed storage
- Study `12-monitoring.md` for observability

## Further Reading

- "UbiCrawler: A Scalable Fully Distributed Web Crawler" (Boldi et al.)
- "Mercator: A Scalable, Extensible Web Crawler" (Heydon & Najork)
- Redis documentation (distributed data structures)
- "Designing Data-Intensive Applications" by Martin Kleppmann
