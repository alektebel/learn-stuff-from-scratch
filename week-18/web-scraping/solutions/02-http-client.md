# HTTP Client - Robust Request Handling

## Overview

The HTTP client is the foundation of any web scraper. It must be fast, reliable, and handle the complexities of real-world web servers.

## Requirements

A production HTTP client needs:
- **Connection pooling** - Reuse TCP connections
- **Keep-alive** - Maintain persistent connections
- **Timeout handling** - Don't wait forever
- **Retry logic** - Handle transient failures
- **Redirect following** - Handle 301/302 properly
- **Compression** - Handle gzip, deflate, brotli
- **TLS/SSL** - HTTPS support
- **Custom headers** - User-Agent, cookies, etc.
- **Rate limiting** - Respect server limits

## Implementation Strategies

### 1. Python: aiohttp (Async, Production)

```python
import aiohttp
import asyncio
from typing import Optional, Dict
import logging

class HTTPClient:
    """
    Production-grade async HTTP client
    """
    def __init__(
        self,
        max_connections=100,
        max_per_host=10,
        timeout_total=60,
        timeout_connect=10,
        user_agent='MyBot/1.0 (+https://example.com/bot)'
    ):
        # Connection pooling configuration
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,        # Total connections
            limit_per_host=max_per_host,  # Per domain
            ttl_dns_cache=300,            # Cache DNS for 5 min
            enable_cleanup_closed=True,   # Clean up closed connections
            force_close=False,            # Use keep-alive
        )
        
        # Timeout configuration
        self.timeout = aiohttp.ClientTimeout(
            total=timeout_total,
            connect=timeout_connect,
            sock_read=30
        )
        
        # Default headers
        self.headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout,
            headers=self.headers,
            cookie_jar=aiohttp.CookieJar()  # Handle cookies automatically
        )
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def fetch(
        self,
        url: str,
        method: str = 'GET',
        headers: Optional[Dict] = None,
        max_retries: int = 3,
        **kwargs
    ) -> Dict:
        """
        Fetch URL with retry logic
        """
        merged_headers = {**self.headers, **(headers or {})}
        
        for attempt in range(max_retries):
            try:
                async with self.session.request(
                    method,
                    url,
                    headers=merged_headers,
                    allow_redirects=True,
                    max_redirects=10,
                    **kwargs
                ) as response:
                    # Read content
                    content = await response.read()
                    
                    return {
                        'url': str(response.url),  # Final URL after redirects
                        'status': response.status,
                        'headers': dict(response.headers),
                        'content': content,
                        'encoding': response.get_encoding(),
                        'error': None
                    }
            
            except asyncio.TimeoutError:
                logging.warning(f"Timeout on {url}, attempt {attempt+1}/{max_retries}")
                if attempt == max_retries - 1:
                    return {'url': url, 'error': 'timeout'}
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            except aiohttp.ClientError as e:
                logging.warning(f"Client error on {url}: {e}, attempt {attempt+1}/{max_retries}")
                if attempt == max_retries - 1:
                    return {'url': url, 'error': str(e)}
                await asyncio.sleep(2 ** attempt)
            
            except Exception as e:
                logging.error(f"Unexpected error on {url}: {e}")
                return {'url': url, 'error': f'unexpected: {str(e)}'}
    
    async def fetch_many(self, urls: list) -> list:
        """
        Fetch multiple URLs concurrently
        """
        tasks = [self.fetch(url) for url in urls]
        return await asyncio.gather(*tasks)

# Usage
async def main():
    async with HTTPClient(max_connections=100) as client:
        # Single request
        result = await client.fetch('https://example.com')
        print(f"Status: {result['status']}")
        
        # Multiple concurrent requests
        urls = ['https://example.com/page1', 'https://example.com/page2', ...]
        results = await client.fetch_many(urls)
        
        for result in results:
            if result['error']:
                print(f"Error: {result['error']}")
            else:
                print(f"Success: {result['status']}")

asyncio.run(main())
```

### 2. Python: requests (Simple, Sync)

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class SimpleHTTPClient:
    """
    Simple synchronous client for prototyping
    """
    def __init__(self):
        self.session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # Wait 1, 2, 4 seconds
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=100
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Default headers
        self.session.headers.update({
            'User-Agent': 'MyBot/1.0 (+https://example.com/bot)'
        })
    
    def fetch(self, url, timeout=(10, 30)):
        """
        Fetch URL with automatic retries
        timeout: (connect_timeout, read_timeout)
        """
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return {
                'url': response.url,
                'status': response.status_code,
                'headers': dict(response.headers),
                'content': response.content,
                'encoding': response.encoding,
                'error': None
            }
        except requests.exceptions.RequestException as e:
            return {'url': url, 'error': str(e)}

# Usage
client = SimpleHTTPClient()
result = client.fetch('https://example.com')
```

### 3. C: libcurl (Maximum Performance)

```c
#include <curl/curl.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char* data;
    size_t size;
} MemoryStruct;

// Callback for writing response data
static size_t write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t realsize = size * nmemb;
    MemoryStruct* mem = (MemoryStruct*)userp;
    
    char* ptr = realloc(mem->data, mem->size + realsize + 1);
    if (!ptr) {
        fprintf(stderr, "Out of memory\\n");
        return 0;
    }
    
    mem->data = ptr;
    memcpy(&(mem->data[mem->size]), contents, realsize);
    mem->size += realsize;
    mem->data[mem->size] = 0;
    
    return realsize;
}

// Fetch single URL
CURLcode fetch_url(const char* url, MemoryStruct* response) {
    CURL* curl = curl_easy_init();
    if (!curl) return CURLE_FAILED_INIT;
    
    response->data = malloc(1);
    response->size = 0;
    
    // Configure request
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void*)response);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "MyBot/1.0");
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);  // Follow redirects
    curl_easy_setopt(curl, CURLOPT_MAXREDIRS, 10L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 60L);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 10L);
    curl_easy_setopt(curl, CURLOPT_ACCEPT_ENCODING, "gzip");  // Auto decompress
    
    // Perform request
    CURLcode res = curl_easy_perform(curl);
    
    curl_easy_cleanup(curl);
    return res;
}

// Multi-handle for concurrent requests
void fetch_multiple_urls(char** urls, int num_urls) {
    CURLM* multi_handle = curl_multi_init();
    CURL* easy_handles[num_urls];
    MemoryStruct responses[num_urls];
    
    // Add all URLs to multi handle
    for (int i = 0; i < num_urls; i++) {
        easy_handles[i] = curl_easy_init();
        responses[i].data = malloc(1);
        responses[i].size = 0;
        
        curl_easy_setopt(easy_handles[i], CURLOPT_URL, urls[i]);
        curl_easy_setopt(easy_handles[i], CURLOPT_WRITEFUNCTION, write_callback);
        curl_easy_setopt(easy_handles[i], CURLOPT_WRITEDATA, &responses[i]);
        curl_easy_setopt(easy_handles[i], CURLOPT_USERAGENT, "MyBot/1.0");
        
        curl_multi_add_handle(multi_handle, easy_handles[i]);
    }
    
    // Perform all requests concurrently
    int still_running;
    curl_multi_perform(multi_handle, &still_running);
    
    while (still_running) {
        CURLMcode mc = curl_multi_wait(multi_handle, NULL, 0, 1000, NULL);
        if (mc != CURLM_OK) {
            fprintf(stderr, "curl_multi_wait() failed: %s\\n", curl_multi_strerror(mc));
            break;
        }
        curl_multi_perform(multi_handle, &still_running);
    }
    
    // Cleanup
    for (int i = 0; i < num_urls; i++) {
        curl_multi_remove_handle(multi_handle, easy_handles[i]);
        curl_easy_cleanup(easy_handles[i]);
        
        // Process response
        printf("URL %s: %zu bytes\\n", urls[i], responses[i].size);
        free(responses[i].data);
    }
    
    curl_multi_cleanup(multi_handle);
}
```

## Advanced Features

### Session Management

```python
class SessionManager:
    """
    Manage cookies and session state across requests
    """
    async def login(self, username, password):
        """Login and maintain session"""
        async with self.session.post(
            'https://example.com/login',
            data={'username': username, 'password': password}
        ) as response:
            if response.status == 200:
                # Cookies automatically saved in session
                return True
            return False
    
    async def fetch_authenticated(self, url):
        """Fetch with session cookies"""
        return await self.fetch(url)
```

### Custom Headers and User-Agent Rotation

```python
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
]

import random

async def fetch_with_random_ua(self, url):
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    return await self.fetch(url, headers=headers)
```

### Handling Compression

Most modern clients handle this automatically, but understand the options:

```python
# aiohttp handles automatically with:
# 'Accept-Encoding': 'gzip, deflate, br'

# Manual decompression if needed:
import gzip
import brotli

def decompress_response(content, encoding):
    if encoding == 'gzip':
        return gzip.decompress(content)
    elif encoding == 'br':
        return brotli.decompress(content)
    elif encoding == 'deflate':
        return zlib.decompress(content)
    else:
        return content
```

## Error Handling

### Comprehensive Error Handling

```python
from aiohttp import ClientError, ClientConnectionError, ClientTimeout

async def fetch_with_full_error_handling(self, url):
    try:
        return await self.fetch(url)
    
    except ClientConnectionError as e:
        # Network errors (DNS, connection refused, etc.)
        return {'url': url, 'error': 'connection_error', 'details': str(e)}
    
    except ClientTimeout as e:
        # Timeout errors
        return {'url': url, 'error': 'timeout', 'details': str(e)}
    
    except ClientError as e:
        # Other client errors
        return {'url': url, 'error': 'client_error', 'details': str(e)}
    
    except Exception as e:
        # Unexpected errors
        return {'url': url, 'error': 'unexpected', 'details': str(e)}
```

### Circuit Breaker Pattern

```python
from datetime import datetime, timedelta

class CircuitBreaker:
    """
    Stop trying to fetch from failing domains
    """
    def __init__(self, failure_threshold=5, timeout=300):
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout)
        self.failures = {}  # domain -> (count, last_failure_time)
    
    def is_open(self, domain):
        """Check if circuit is open (domain is failing)"""
        if domain not in self.failures:
            return False
        
        count, last_failure = self.failures[domain]
        
        # Reset if timeout passed
        if datetime.now() - last_failure > self.timeout:
            del self.failures[domain]
            return False
        
        return count >= self.failure_threshold
    
    def record_failure(self, domain):
        """Record a failure for domain"""
        if domain in self.failures:
            count, _ = self.failures[domain]
            self.failures[domain] = (count + 1, datetime.now())
        else:
            self.failures[domain] = (1, datetime.now())
    
    def record_success(self, domain):
        """Record success, reset failures"""
        if domain in self.failures:
            del self.failures[domain]

# Usage
circuit_breaker = CircuitBreaker()

async def fetch_with_circuit_breaker(url):
    domain = urlparse(url).netloc
    
    if circuit_breaker.is_open(domain):
        return {'url': url, 'error': 'circuit_breaker_open'}
    
    result = await client.fetch(url)
    
    if result['error']:
        circuit_breaker.record_failure(domain)
    else:
        circuit_breaker.record_success(domain)
    
    return result
```

## Performance Optimization

### Connection Pooling Best Practices

```python
# Good: Reuse session
async with HTTPClient() as client:
    for url in urls:
        result = await client.fetch(url)  # Reuses connections

# Bad: Create new session each time
for url in urls:
    async with HTTPClient() as client:
        result = await client.fetch(url)  # New connections every time
```

### DNS Caching

```python
# aiohttp caches DNS automatically
connector = aiohttp.TCPConnector(
    ttl_dns_cache=300,  # Cache for 5 minutes
)

# For custom DNS resolution:
import aiodns

resolver = aiodns.DNSResolver()
connector = aiohttp.TCPConnector(resolver=resolver)
```

### Keep-Alive Tuning

```python
connector = aiohttp.TCPConnector(
    force_close=False,  # Enable keep-alive
    keepalive_timeout=30,  # Keep connections alive for 30s
)
```

## Monitoring and Metrics

```python
from prometheus_client import Counter, Histogram

http_requests_total = Counter('http_requests_total', 'Total HTTP requests', ['status'])
http_request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

async def fetch_with_metrics(url):
    start = time.time()
    result = await client.fetch(url)
    duration = time.time() - start
    
    http_request_duration.observe(duration)
    http_requests_total.labels(status=result.get('status', 'error')).inc()
    
    return result
```

## Testing

```python
import pytest
from aiohttp import web

@pytest.fixture
async def mock_server(aiohttp_server):
    """Create mock HTTP server for testing"""
    async def handler(request):
        return web.Response(text='Hello World')
    
    app = web.Application()
    app.router.add_get('/', handler)
    server = await aiohttp_server(app)
    return server

async def test_fetch(mock_server):
    url = str(mock_server.make_url('/'))
    async with HTTPClient() as client:
        result = await client.fetch(url)
        assert result['status'] == 200
        assert b'Hello World' in result['content']
```

## Next Steps

- Study `03-robots-txt-parser.md` for compliance
- Study `04-url-frontier.md` for URL management
- Study `08-rate-limiting.md` for politeness
- Study `09-distributed-crawling.md` for scaling

## Further Reading

- aiohttp documentation
- libcurl documentation
- HTTP/1.1 RFC 7230-7235
- HTTP/2 RFC 7540
- "High Performance Browser Networking" by Ilya Grigorik
