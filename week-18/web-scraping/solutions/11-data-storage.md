# Data Storage - Efficient Storage for Crawled Data

## Overview

Efficient data storage is critical for web crawling at scale. This guide covers storage architectures, database selection, compression strategies, deduplication, and archival policies for handling billions of web pages.

## Storage Architecture

### Data Flow

```
┌──────────────┐
│   Crawler    │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│        Storage Pipeline              │
│                                      │
│  ┌──────────┐  ┌──────────────┐   │
│  │Validation│─►│ Compression  │   │
│  └──────────┘  └──────┬───────┘   │
│                       │             │
│                       ▼             │
│  ┌──────────┐  ┌──────────────┐   │
│  │  Dedup   │◄─┤  Hash Index  │   │
│  └────┬─────┘  └──────────────┘   │
│       │                             │
└───────┼─────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│         Storage Layer                   │
│  ┌──────────┐  ┌──────────┐  ┌──────┐ │
│  │   Hot    │  │   Warm   │  │ Cold │ │
│  │ (SSD)    │─►│  (HDD)   │─►│ (S3) │ │
│  │ 7 days   │  │ 30 days  │  │ 1yr+ │ │
│  └──────────┘  └──────────┘  └──────┘ │
└─────────────────────────────────────────┘
```

### Storage Tiers

**Hot Storage (Recent Data)**
- Last 7 days of crawls
- High IOPS required
- SSD/NVMe storage
- Frequent access for processing

**Warm Storage (Recent History)**
- 7-30 days old
- Moderate access
- HDD/slower SSD
- Available for comparison

**Cold Storage (Archives)**
- 30+ days old
- Rare access
- Object storage (S3, GCS)
- High compression

## Database Selection

### 1. Document Store (MongoDB)

**Use Case:** Structured data extraction, flexible schemas

```python
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from typing import Dict, List, Optional
import hashlib
from datetime import datetime

class MongoStorage:
    """
    MongoDB storage for crawled data
    
    Stores documents with flexible schema.
    Supports efficient querying and indexing.
    """
    
    def __init__(self, connection_string: str, database: str):
        self.client = MongoClient(connection_string)
        self.db = self.client[database]
        
        # Collections
        self.pages = self.db.pages
        self.metadata = self.db.metadata
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create indexes for efficient querying"""
        # URL index (unique)
        self.pages.create_index('url', unique=True)
        
        # Content hash for deduplication
        self.pages.create_index('content_hash')
        
        # Timestamp for time-based queries
        self.pages.create_index('crawled_at')
        
        # Domain for grouping
        self.pages.create_index('domain')
        
        # Compound index for common queries
        self.pages.create_index([
            ('domain', 1),
            ('crawled_at', -1)
        ])
    
    def save_page(
        self,
        url: str,
        content: str,
        metadata: Dict,
        extracted_data: Optional[Dict] = None
    ) -> bool:
        """
        Save crawled page
        
        Returns True if new, False if duplicate
        """
        # Calculate content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check for duplicates
        existing = self.pages.find_one({
            'url': url,
            'content_hash': content_hash
        })
        
        if existing:
            # Update last_seen timestamp
            self.pages.update_one(
                {'_id': existing['_id']},
                {'$set': {'last_seen': datetime.utcnow()}}
            )
            return False
        
        # Save new page
        document = {
            'url': url,
            'content': content,
            'content_hash': content_hash,
            'metadata': metadata,
            'extracted_data': extracted_data or {},
            'crawled_at': datetime.utcnow(),
            'last_seen': datetime.utcnow()
        }
        
        self.pages.replace_one(
            {'url': url},
            document,
            upsert=True
        )
        return True
    
    def bulk_save(self, pages: List[Dict]) -> Dict[str, int]:
        """
        Bulk save pages efficiently
        
        Returns counts of inserted, updated, duplicates
        """
        operations = []
        stats = {'inserted': 0, 'updated': 0, 'duplicates': 0}
        
        for page in pages:
            content_hash = hashlib.sha256(
                page['content'].encode()
            ).hexdigest()
            
            document = {
                'url': page['url'],
                'content': page['content'],
                'content_hash': content_hash,
                'metadata': page.get('metadata', {}),
                'extracted_data': page.get('extracted_data', {}),
                'crawled_at': datetime.utcnow(),
                'last_seen': datetime.utcnow()
            }
            
            operations.append(
                UpdateOne(
                    {'url': page['url']},
                    {'$set': document},
                    upsert=True
                )
            )
        
        try:
            result = self.pages.bulk_write(operations, ordered=False)
            stats['inserted'] = result.upserted_count
            stats['updated'] = result.modified_count
        except BulkWriteError as e:
            # Handle partial success
            stats['inserted'] = e.details['nInserted']
            stats['updated'] = e.details['nModified']
        
        return stats
    
    def get_page(self, url: str) -> Optional[Dict]:
        """Retrieve page by URL"""
        return self.pages.find_one({'url': url})
    
    def query_pages(
        self,
        domain: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query pages with filters"""
        query = {}
        
        if domain:
            query['domain'] = domain
        
        if since:
            query['crawled_at'] = {'$gte': since}
        
        return list(self.pages.find(query).limit(limit))


# Usage example
storage = MongoStorage(
    connection_string='mongodb://localhost:27017',
    database='web_crawler'
)

# Save single page
storage.save_page(
    url='http://example.com/page1',
    content='<html>...</html>',
    metadata={'status': 200, 'content_type': 'text/html'},
    extracted_data={'title': 'Example Page', 'links': ['...']}
)

# Bulk save
pages = [
    {
        'url': 'http://example.com/page2',
        'content': '<html>...</html>',
        'metadata': {'status': 200}
    },
    # ... more pages
]
stats = storage.bulk_save(pages)
print(f"Inserted: {stats['inserted']}, Updated: {stats['updated']}")
```

### 2. Time-Series Database (InfluxDB)

**Use Case:** Time-series analytics, crawl metrics

```python
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
from typing import Dict, List

class TimeSeriesStorage:
    """
    InfluxDB storage for time-series data
    
    Stores crawl metrics, performance data, and trends.
    Efficient for time-based queries and aggregations.
    """
    
    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str
    ):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
        self.bucket = bucket
        self.org = org
    
    def record_crawl(
        self,
        url: str,
        domain: str,
        status_code: int,
        response_time: float,
        content_size: int,
        timestamp: Optional[datetime] = None
    ):
        """Record crawl metrics"""
        point = (
            Point("crawl")
            .tag("domain", domain)
            .tag("status", str(status_code))
            .field("response_time", response_time)
            .field("content_size", content_size)
            .field("url", url)
        )
        
        if timestamp:
            point = point.time(timestamp)
        
        self.write_api.write(bucket=self.bucket, record=point)
    
    def record_error(
        self,
        url: str,
        domain: str,
        error_type: str,
        error_message: str
    ):
        """Record crawl error"""
        point = (
            Point("error")
            .tag("domain", domain)
            .tag("error_type", error_type)
            .field("url", url)
            .field("message", error_message)
        )
        
        self.write_api.write(bucket=self.bucket, record=point)
    
    def get_domain_stats(
        self,
        domain: str,
        hours: int = 24
    ) -> Dict:
        """Get statistics for domain over time period"""
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r._measurement == "crawl")
            |> filter(fn: (r) => r.domain == "{domain}")
            |> group(columns: ["status"])
            |> count()
        '''
        
        result = self.query_api.query(query=query, org=self.org)
        
        stats = {}
        for table in result:
            for record in table.records:
                status = record.values.get('status')
                count = record.values.get('_value')
                stats[status] = count
        
        return stats
    
    def get_performance_trend(
        self,
        domain: str,
        hours: int = 24,
        window: str = "1h"
    ) -> List[Dict]:
        """Get performance trend (avg response time)"""
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -{hours}h)
            |> filter(fn: (r) => r._measurement == "crawl")
            |> filter(fn: (r) => r.domain == "{domain}")
            |> filter(fn: (r) => r._field == "response_time")
            |> aggregateWindow(every: {window}, fn: mean)
        '''
        
        result = self.query_api.query(query=query, org=self.org)
        
        trend = []
        for table in result:
            for record in table.records:
                trend.append({
                    'time': record.values.get('_time'),
                    'response_time': record.values.get('_value')
                })
        
        return trend


# Usage example
ts_storage = TimeSeriesStorage(
    url='http://localhost:8086',
    token='my-token',
    org='my-org',
    bucket='web_crawler'
)

# Record crawl
ts_storage.record_crawl(
    url='http://example.com/page1',
    domain='example.com',
    status_code=200,
    response_time=0.523,
    content_size=15234
)

# Get stats
stats = ts_storage.get_domain_stats('example.com', hours=24)
print(f"Status codes: {stats}")

# Get performance trend
trend = ts_storage.get_performance_trend('example.com', hours=24)
```

### 3. Object Storage (S3)

**Use Case:** Raw HTML storage, cold archives

```python
import boto3
from botocore.exceptions import ClientError
import gzip
import hashlib
from typing import Optional, Dict
from datetime import datetime, timedelta

class S3Storage:
    """
    S3 storage for raw crawled content
    
    Stores compressed HTML with efficient organization.
    Supports lifecycle policies for archival.
    """
    
    def __init__(
        self,
        bucket_name: str,
        region: str = 'us-east-1',
        compress: bool = True
    ):
        self.s3 = boto3.client('s3', region_name=region)
        self.bucket = bucket_name
        self.compress = compress
    
    def _get_key(self, url: str, timestamp: datetime) -> str:
        """
        Generate S3 key with hierarchical structure
        
        Format: domain/YYYY/MM/DD/hash.html.gz
        """
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Hash URL for filename
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Date-based hierarchy
        date_path = timestamp.strftime('%Y/%m/%d')
        
        ext = '.html.gz' if self.compress else '.html'
        
        return f"{domain}/{date_path}/{url_hash}{ext}"
    
    def save_content(
        self,
        url: str,
        content: str,
        metadata: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Save content to S3
        
        Returns S3 key
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        key = self._get_key(url, timestamp)
        
        # Compress content
        if self.compress:
            content_bytes = gzip.compress(content.encode('utf-8'))
            content_type = 'application/gzip'
        else:
            content_bytes = content.encode('utf-8')
            content_type = 'text/html'
        
        # Prepare metadata
        s3_metadata = {
            'url': url,
            'timestamp': timestamp.isoformat(),
            **(metadata or {})
        }
        
        # Upload to S3
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content_bytes,
                ContentType=content_type,
                Metadata=s3_metadata,
                StorageClass='STANDARD_IA'  # Infrequent access
            )
            return key
        except ClientError as e:
            print(f"Failed to upload {url}: {e}")
            raise
    
    def get_content(self, key: str) -> str:
        """Retrieve content from S3"""
        try:
            response = self.s3.get_object(
                Bucket=self.bucket,
                Key=key
            )
            
            content_bytes = response['Body'].read()
            
            # Decompress if needed
            if key.endswith('.gz'):
                content_bytes = gzip.decompress(content_bytes)
            
            return content_bytes.decode('utf-8')
        except ClientError as e:
            print(f"Failed to retrieve {key}: {e}")
            raise
    
    def setup_lifecycle_policy(self):
        """
        Setup lifecycle policy for automatic archival
        
        - Move to GLACIER after 30 days
        - Move to DEEP_ARCHIVE after 90 days
        - Delete after 1 year (optional)
        """
        lifecycle_policy = {
            'Rules': [
                {
                    'Id': 'ArchiveOldCrawls',
                    'Status': 'Enabled',
                    'Prefix': '',
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'GLACIER'
                        },
                        {
                            'Days': 90,
                            'StorageClass': 'DEEP_ARCHIVE'
                        }
                    ]
                }
            ]
        }
        
        try:
            self.s3.put_bucket_lifecycle_configuration(
                Bucket=self.bucket,
                LifecycleConfiguration=lifecycle_policy
            )
            print(f"Lifecycle policy applied to {self.bucket}")
        except ClientError as e:
            print(f"Failed to set lifecycle policy: {e}")


# Usage example
s3_storage = S3Storage(
    bucket_name='web-crawler-data',
    region='us-east-1',
    compress=True
)

# Save content
key = s3_storage.save_content(
    url='http://example.com/page1',
    content='<html>...</html>',
    metadata={'status': 200, 'content_type': 'text/html'}
)
print(f"Saved to S3: {key}")

# Setup lifecycle
s3_storage.setup_lifecycle_policy()
```

## Compression Strategies

### 1. Gzip Compression

```python
import gzip
import zlib
from typing import Tuple

class GzipCompressor:
    """
    Gzip compression for HTML content
    
    Fast compression with good ratio (~70% reduction)
    """
    
    def compress(self, content: str, level: int = 6) -> bytes:
        """
        Compress content
        
        level: 1-9 (1=fastest, 9=best compression)
        """
        return gzip.compress(
            content.encode('utf-8'),
            compresslevel=level
        )
    
    def decompress(self, data: bytes) -> str:
        """Decompress content"""
        return gzip.decompress(data).decode('utf-8')
    
    def compress_ratio(self, content: str) -> Tuple[int, int, float]:
        """
        Calculate compression ratio
        
        Returns: (original_size, compressed_size, ratio)
        """
        original = len(content.encode('utf-8'))
        compressed = len(self.compress(content))
        ratio = compressed / original
        
        return original, compressed, ratio


# Benchmark different levels
compressor = GzipCompressor()
html = "<html>" + "x" * 100000 + "</html>"

for level in [1, 6, 9]:
    import time
    start = time.time()
    compressed = compressor.compress(html, level=level)
    elapsed = time.time() - start
    
    orig, comp, ratio = compressor.compress_ratio(html)
    print(f"Level {level}: {ratio:.2%} size, {elapsed*1000:.2f}ms")
```

### 2. Zstandard (Better Compression)

```python
import zstandard as zstd
from typing import Optional

class ZstdCompressor:
    """
    Zstandard compression
    
    Better compression ratio and speed than gzip
    Especially good for similar content (HTML)
    """
    
    def __init__(self, level: int = 3, use_dict: bool = False):
        self.level = level
        self.compressor = zstd.ZstdCompressor(level=level)
        self.decompressor = zstd.ZstdDecompressor()
        self.dict_data = None
        
        if use_dict:
            self._train_dictionary()
    
    def _train_dictionary(self, samples: Optional[list] = None):
        """
        Train compression dictionary on sample data
        
        Dictionary improves compression for similar content
        """
        if samples is None:
            # Use sample HTML pages
            samples = [
                b'<html><head><title>Sample</title></head><body>',
                b'<html><body><div class="content">',
                # Add more samples...
            ]
        
        # Train dictionary
        self.dict_data = zstd.train_dictionary(
            dict_size=112640,  # 110KB
            samples=samples
        )
        
        # Update compressor/decompressor
        self.compressor = zstd.ZstdCompressor(
            level=self.level,
            dict_data=self.dict_data
        )
        self.decompressor = zstd.ZstdDecompressor(
            dict_data=self.dict_data
        )
    
    def compress(self, content: str) -> bytes:
        """Compress content"""
        return self.compressor.compress(content.encode('utf-8'))
    
    def decompress(self, data: bytes) -> str:
        """Decompress content"""
        return self.decompressor.decompress(data).decode('utf-8')


# Usage example
compressor = ZstdCompressor(level=3, use_dict=True)

html = "<html><body>Sample content</body></html>"
compressed = compressor.compress(html)
decompressed = compressor.decompress(compressed)

print(f"Original: {len(html)} bytes")
print(f"Compressed: {len(compressed)} bytes")
print(f"Ratio: {len(compressed)/len(html):.2%}")
```

### Compression Comparison

| Algorithm | Ratio | Speed | CPU | Best For |
|-----------|-------|-------|-----|----------|
| Gzip (6) | 70% | Fast | Low | General purpose |
| Gzip (9) | 65% | Slow | High | Maximum compression |
| Zstd (3) | 65% | Very fast | Low | Real-time compression |
| Zstd+Dict | 55% | Very fast | Low | Similar content |
| Brotli | 60% | Slow | High | Web delivery |

## Data Deduplication

### Content-Based Deduplication

```python
import hashlib
from typing import Optional, Set, Dict
import redis
import asyncio

class ContentDeduplicator:
    """
    Content-based deduplication using hashing
    
    Detects duplicate content even with different URLs.
    Uses Bloom filter for memory efficiency.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.local_hashes: Set[str] = set()
    
    def _hash_content(self, content: str) -> str:
        """Hash content for deduplication"""
        # Use SHA256 for collision resistance
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _normalize_content(self, content: str) -> str:
        """
        Normalize content before hashing
        
        Remove dynamic elements that change frequently
        """
        import re
        
        # Remove timestamps
        content = re.sub(r'\d{4}-\d{2}-\d{2}', '', content)
        
        # Remove common dynamic elements
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
    
    async def is_duplicate(self, content: str, url: str) -> bool:
        """
        Check if content is duplicate
        
        Returns True if duplicate found
        """
        # Normalize content
        normalized = self._normalize_content(content)
        content_hash = self._hash_content(normalized)
        
        # Check local cache first
        if content_hash in self.local_hashes:
            return True
        
        # Check Redis (distributed)
        if self.redis:
            exists = await self.redis.sismember('content_hashes', content_hash)
            if exists:
                return True
            
            # Add to Redis
            await self.redis.sadd('content_hashes', content_hash)
        
        # Add to local cache
        self.local_hashes.add(content_hash)
        
        return False
    
    async def mark_seen(self, content: str, url: str) -> str:
        """
        Mark content as seen
        
        Returns content hash
        """
        normalized = self._normalize_content(content)
        content_hash = self._hash_content(normalized)
        
        # Store in Redis with URL mapping
        if self.redis:
            await self.redis.hset(
                f'content_hash:{content_hash}',
                'url', url
            )
            await self.redis.sadd('content_hashes', content_hash)
        
        self.local_hashes.add(content_hash)
        
        return content_hash


# Usage example
deduplicator = ContentDeduplicator(
    redis_client=redis.from_url('redis://localhost:6379')
)

content1 = "<html><body>Same content</body></html>"
content2 = "<html><body>Same content</body></html>"

is_dup = await deduplicator.is_duplicate(content1, 'http://example.com/1')
print(f"First page duplicate: {is_dup}")  # False

is_dup = await deduplicator.is_duplicate(content2, 'http://example.com/2')
print(f"Second page duplicate: {is_dup}")  # True
```

### Near-Duplicate Detection (SimHash)

```python
from simhash import Simhash
from typing import List, Tuple

class NearDuplicateDetector:
    """
    Near-duplicate detection using SimHash
    
    Detects pages that are very similar (e.g., 95% same).
    Efficient for finding copied content with minor changes.
    """
    
    def __init__(self, threshold: int = 3):
        """
        threshold: Maximum hamming distance for duplicates
        (3 = ~94% similarity for 64-bit hash)
        """
        self.threshold = threshold
        self.hashes: Dict[int, str] = {}  # hash -> url
    
    def _extract_features(self, content: str) -> List[str]:
        """
        Extract features for SimHash
        
        Uses word shingles (n-grams)
        """
        import re
        
        # Extract words
        words = re.findall(r'\w+', content.lower())
        
        # Create 3-word shingles
        shingles = []
        for i in range(len(words) - 2):
            shingle = ' '.join(words[i:i+3])
            shingles.append(shingle)
        
        return shingles
    
    def compute_hash(self, content: str) -> int:
        """Compute SimHash for content"""
        features = self._extract_features(content)
        return Simhash(features).value
    
    def is_near_duplicate(
        self,
        content: str,
        url: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if content is near-duplicate
        
        Returns: (is_duplicate, original_url)
        """
        hash_value = self.compute_hash(content)
        
        # Check against existing hashes
        for existing_hash, existing_url in self.hashes.items():
            # Calculate hamming distance
            distance = bin(hash_value ^ existing_hash).count('1')
            
            if distance <= self.threshold:
                return True, existing_url
        
        # Not a duplicate, store hash
        self.hashes[hash_value] = url
        return False, None
    
    def get_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate similarity between two contents
        
        Returns: 0.0-1.0 (1.0 = identical)
        """
        hash1 = self.compute_hash(content1)
        hash2 = self.compute_hash(content2)
        
        distance = bin(hash1 ^ hash2).count('1')
        similarity = 1 - (distance / 64.0)  # 64-bit hash
        
        return similarity


# Usage example
detector = NearDuplicateDetector(threshold=3)

html1 = "<html><body>Original content here</body></html>"
html2 = "<html><body>Original content here with minor change</body></html>"

is_dup, orig_url = detector.is_near_duplicate(html1, 'http://example.com/1')
print(f"First page duplicate: {is_dup}")

is_dup, orig_url = detector.is_near_duplicate(html2, 'http://example.com/2')
print(f"Second page duplicate: {is_dup}")  # Likely True

similarity = detector.get_similarity(html1, html2)
print(f"Similarity: {similarity:.2%}")
```

## Incremental Crawling

### Change Detection

```python
from typing import Optional, Dict
from datetime import datetime, timedelta
import hashlib

class IncrementalCrawler:
    """
    Incremental crawling with change detection
    
    Only stores/processes changed content.
    Reduces storage and processing costs.
    """
    
    def __init__(self, storage):
        self.storage = storage  # Can be MongoDB, S3, etc.
        self.etag_cache: Dict[str, str] = {}
        self.last_modified_cache: Dict[str, datetime] = {}
    
    async def should_recrawl(
        self,
        url: str,
        min_interval: timedelta = timedelta(hours=24)
    ) -> bool:
        """
        Determine if URL should be recrawled
        
        Based on last crawl time and change frequency
        """
        # Get last crawl info
        page = self.storage.get_page(url)
        
        if not page:
            return True  # Never crawled
        
        last_crawl = page.get('crawled_at')
        if not last_crawl:
            return True
        
        # Check minimum interval
        if datetime.utcnow() - last_crawl < min_interval:
            return False
        
        # Check change frequency
        change_freq = page.get('change_frequency', 'daily')
        intervals = {
            'always': timedelta(hours=1),
            'hourly': timedelta(hours=1),
            'daily': timedelta(days=1),
            'weekly': timedelta(weeks=1),
            'monthly': timedelta(days=30),
            'yearly': timedelta(days=365)
        }
        
        required_interval = intervals.get(change_freq, timedelta(days=1))
        return datetime.utcnow() - last_crawl >= required_interval
    
    async def fetch_if_modified(
        self,
        url: str,
        session
    ) -> Optional[Dict]:
        """
        Fetch only if modified (using HTTP headers)
        
        Uses ETag and Last-Modified headers
        """
        headers = {}
        
        # Add conditional request headers
        if url in self.etag_cache:
            headers['If-None-Match'] = self.etag_cache[url]
        
        if url in self.last_modified_cache:
            last_mod = self.last_modified_cache[url]
            headers['If-Modified-Since'] = last_mod.strftime(
                '%a, %d %b %Y %H:%M:%S GMT'
            )
        
        async with session.get(url, headers=headers) as response:
            if response.status == 304:
                # Not modified
                return None
            
            if response.status == 200:
                content = await response.text()
                
                # Cache headers for next time
                if 'ETag' in response.headers:
                    self.etag_cache[url] = response.headers['ETag']
                
                if 'Last-Modified' in response.headers:
                    last_mod = response.headers['Last-Modified']
                    # Parse and cache...
                
                return {
                    'url': url,
                    'content': content,
                    'status': response.status,
                    'headers': dict(response.headers)
                }
        
        return None
    
    def detect_content_change(
        self,
        url: str,
        new_content: str
    ) -> bool:
        """
        Detect if content has meaningfully changed
        
        Ignores minor changes like timestamps, ads, etc.
        """
        # Get previous version
        page = self.storage.get_page(url)
        if not page:
            return True  # New content
        
        old_content = page.get('content', '')
        
        # Calculate similarity
        detector = NearDuplicateDetector()
        similarity = detector.get_similarity(old_content, new_content)
        
        # Threshold: 95% similar = no meaningful change
        return similarity < 0.95


# Usage example
async def incremental_crawl():
    storage = MongoStorage('mongodb://localhost', 'crawler')
    crawler = IncrementalCrawler(storage)
    
    urls = ['http://example.com/page1', 'http://example.com/page2']
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            # Check if should recrawl
            if not await crawler.should_recrawl(url):
                print(f"Skipping {url} (too soon)")
                continue
            
            # Fetch if modified
            result = await crawler.fetch_if_modified(url, session)
            
            if result:
                # Check for meaningful changes
                if crawler.detect_content_change(url, result['content']):
                    storage.save_page(url, result['content'], result)
                    print(f"Saved changed content: {url}")
                else:
                    print(f"No meaningful change: {url}")
            else:
                print(f"Not modified: {url}")
```

## Archival Policies

### Retention Policy Implementation

```python
from datetime import datetime, timedelta
from typing import Dict, List
import asyncio

class RetentionPolicy:
    """
    Automated retention and archival policies
    
    - Keep recent versions (hot storage)
    - Archive old versions (cold storage)
    - Delete ancient data (compliance)
    """
    
    def __init__(
        self,
        hot_storage,
        cold_storage,
        hot_retention_days: int = 7,
        warm_retention_days: int = 30,
        cold_retention_days: int = 365
    ):
        self.hot = hot_storage
        self.cold = cold_storage
        self.hot_retention = timedelta(days=hot_retention_days)
        self.warm_retention = timedelta(days=warm_retention_days)
        self.cold_retention = timedelta(days=cold_retention_days)
    
    async def enforce_policy(self):
        """Run retention policy enforcement"""
        now = datetime.utcnow()
        
        # Find old pages in hot storage
        cutoff = now - self.hot_retention
        old_pages = self.hot.query_pages(since=None, limit=1000)
        
        archived = 0
        deleted = 0
        
        for page in old_pages:
            age = now - page['crawled_at']
            
            if age > self.cold_retention:
                # Delete very old pages
                await self._delete_page(page)
                deleted += 1
            elif age > self.warm_retention:
                # Move to cold storage
                await self._archive_page(page)
                archived += 1
        
        print(f"Archived: {archived}, Deleted: {deleted}")
    
    async def _archive_page(self, page: Dict):
        """Move page to cold storage"""
        # Save to cold storage (S3)
        key = self.cold.save_content(
            url=page['url'],
            content=page['content'],
            metadata=page['metadata'],
            timestamp=page['crawled_at']
        )
        
        # Update hot storage with S3 reference
        self.hot.pages.update_one(
            {'_id': page['_id']},
            {
                '$set': {
                    'archived': True,
                    'archive_key': key
                },
                '$unset': {
                    'content': ''  # Remove content from hot storage
                }
            }
        )
    
    async def _delete_page(self, page: Dict):
        """Delete old page"""
        # Delete from hot storage
        self.hot.pages.delete_one({'_id': page['_id']})
        
        # Delete from cold storage if archived
        if page.get('archived') and page.get('archive_key'):
            # S3 lifecycle will handle deletion
            pass


# Schedule retention policy
async def run_retention_job():
    """Run retention policy daily"""
    mongo = MongoStorage('mongodb://localhost', 'crawler')
    s3 = S3Storage('web-crawler-archive')
    
    policy = RetentionPolicy(
        hot_storage=mongo,
        cold_storage=s3,
        hot_retention_days=7,
        warm_retention_days=30,
        cold_retention_days=365
    )
    
    while True:
        try:
            await policy.enforce_policy()
        except Exception as e:
            print(f"Retention policy failed: {e}")
        
        # Run daily
        await asyncio.sleep(86400)
```

## Best Practices

### 1. Partitioning Strategy

```python
# Partition by domain and date
partition_key = f"{domain}/{year}/{month}/{day}"

# MongoDB sharding key
shard_key = {'domain': 1, 'crawled_at': 1}

# S3 prefix structure
s3_key = f"{domain}/{year}/{month}/{day}/{hash}.html.gz"
```

### 2. Index Strategy

```python
# Essential indexes for MongoDB
indexes = [
    {'keys': [('url', 1)], 'unique': True},
    {'keys': [('content_hash', 1)]},
    {'keys': [('domain', 1), ('crawled_at', -1)]},
    {'keys': [('crawled_at', 1)], 'expireAfterSeconds': 2592000}  # TTL
]
```

### 3. Batch Processing

```python
# Batch inserts for efficiency
batch_size = 1000
pages = []

for page in crawled_pages:
    pages.append(page)
    
    if len(pages) >= batch_size:
        storage.bulk_save(pages)
        pages = []

# Don't forget remaining
if pages:
    storage.bulk_save(pages)
```

### 4. Monitoring Storage

```python
import prometheus_client as prom

storage_size = prom.Gauge('storage_size_bytes', 'Total storage size')
storage_documents = prom.Gauge('storage_documents_total', 'Total documents')
storage_rate = prom.Counter('storage_writes_total', 'Total writes')

# Update metrics
storage_size.set(get_storage_size())
storage_documents.set(storage.pages.count_documents({}))
storage_rate.inc()
```

## Performance Considerations

### Storage Comparison

| Storage | Writes/sec | Reads/sec | Cost/TB/month | Best For |
|---------|-----------|-----------|---------------|----------|
| MongoDB | 10,000 | 50,000 | $200-500 | Structured data |
| PostgreSQL | 5,000 | 30,000 | $150-400 | ACID requirements |
| InfluxDB | 100,000 | 100,000 | $300-600 | Time-series |
| S3 Standard | 3,500 | 5,500 | $23 | Archival |
| S3 Glacier | N/A | N/A | $4 | Long-term |

### Compression Ratios (HTML)

| Algorithm | Compression | Speed | CPU Usage |
|-----------|-------------|-------|-----------|
| None | 0% | - | None |
| Gzip-6 | 70% | 50 MB/s | Low |
| Zstd-3 | 65% | 400 MB/s | Low |
| Zstd+Dict | 55% | 350 MB/s | Low |

## References

- [MongoDB Best Practices](https://docs.mongodb.com/manual/administration/production-notes/)
- [InfluxDB Schema Design](https://docs.influxdata.com/influxdb/v2.0/write-data/best-practices/)
- [S3 Performance Optimization](https://docs.aws.amazon.com/AmazonS3/latest/userguide/optimizing-performance.html)
- [SimHash Paper](http://www.wwwconference.org/www2007/papers/paper215.pdf)
- [Zstandard Compression](https://facebook.github.io/zstd/)
