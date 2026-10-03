# Web Scraping Examples

This directory contains production-quality, runnable examples demonstrating best practices for web scraping and crawling.

## Contents

### Main Crawlers

1. **`basic_crawler.py`** - Single-threaded web crawler
   - Perfect for learning and small-scale scraping
   - robots.txt compliance
   - URL normalization and deduplication
   - Politeness delays
   - Error handling and retry logic
   - JSON output

2. **`async_crawler.py`** - High-performance async crawler
   - Production-ready concurrent crawler
   - asyncio and aiohttp
   - Bloom filter deduplication
   - Per-domain rate limiting
   - Priority queue
   - Connection pooling
   - Configurable concurrency

### Utility Modules (`utils/`)

- **`url_normalizer.py`** - URL canonicalization utilities
- **`rate_limiter.py`** - Token bucket rate limiter
- **`bloom_filter.py`** - Space-efficient deduplication
- **`robots_parser.py`** - robots.txt parser and checker

## Directory Structure

```
examples/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── basic_crawler.py               # Simple single-threaded crawler
├── async_crawler.py               # High-performance async crawler
└── utils/                         # Shared utility modules
    ├── __init__.py
    ├── url_normalizer.py
    ├── rate_limiter.py
    ├── bloom_filter.py
    └── robots_parser.py
```

## Installation

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Crawler

Simple crawl with default settings:
```bash
python basic_crawler.py https://example.com
```

Crawl up to 50 pages with 2-second delay:
```bash
python basic_crawler.py https://example.com --max-pages 50 --delay 2.0
```

Allow cross-domain crawling:
```bash
python basic_crawler.py https://example.com --allow-cross-domain
```

Custom output file:
```bash
python basic_crawler.py https://example.com --output my_results.json
```

All options:
```bash
python basic_crawler.py --help
```

### Async Crawler

High-speed crawl with 10 concurrent workers:
```bash
python async_crawler.py https://example.com --concurrency 10
```

Crawl to depth 5 with 1000 max pages:
```bash
python async_crawler.py https://example.com --max-pages 1000 --max-depth 5
```

High-performance crawling (20 workers, 5 req/sec per domain):
```bash
python async_crawler.py https://example.com --concurrency 20 --rate 5.0
```

All options:
```bash
python async_crawler.py --help
```

## Output Format

Both crawlers produce JSON output with the following structure:

```json
{
  "start_url": "https://example.com",
  "configuration": {
    "max_pages": 100,
    "delay": 1.0,
    "same_domain_only": true,
    "user_agent": "BasicCrawler/1.0"
  },
  "statistics": {
    "pages_crawled": 95,
    "pages_failed": 5,
    "urls_discovered": 450,
    "duration": 120.5,
    "pages_per_second": 0.79
  },
  "results": [
    {
      "url": "https://example.com/page1",
      "status_code": 200,
      "title": "Page Title",
      "description": "Meta description",
      "content_length": 15420,
      "num_links": 25,
      "links": ["..."],
      "timestamp": 1704123456.789
    }
  ],
  "errors": [
    {
      "url": "https://example.com/broken",
      "error": "404 Not Found",
      "timestamp": 1704123456.789
    }
  ]
}
```

## Architecture Overview

### Basic Crawler (`basic_crawler.py`)

```
┌─────────────────────────────────────┐
│       BasicCrawler                  │
├─────────────────────────────────────┤
│ • Single-threaded                   │
│ • Queue-based processing            │
│ • requests library                  │
│ • robots.txt checking               │
│ • Politeness delays                 │
└─────────────────────────────────────┘
         │
         ├─> URLNormalizer (dedup)
         ├─> RobotsParser (compliance)
         └─> BeautifulSoup (parsing)
```

### Async Crawler (`async_crawler.py`)

```
┌─────────────────────────────────────┐
│       AsyncCrawler                  │
├─────────────────────────────────────┤
│ • Multi-worker asyncio              │
│ • Priority queue                    │
│ • aiohttp (async HTTP)              │
│ • Connection pooling                │
│ • Per-domain rate limiting          │
└─────────────────────────────────────┘
         │
         ├─> BloomFilter (dedup)
         ├─> DomainRateLimiter (rate control)
         ├─> URLNormalizer (normalization)
         └─> BeautifulSoup (parsing)
```

## Key Features Explained

### URL Normalization

Converts URLs to canonical form to avoid duplicates:
```python
# These are treated as the same:
http://example.com/path/
http://example.com/path
http://EXAMPLE.COM/path
```

### Bloom Filter Deduplication

Space-efficient probabilistic data structure for tracking visited URLs:
- Memory usage: ~1.2 MB for 100,000 URLs (vs ~8 MB for a set)
- False positive rate: < 1%
- No false negatives

### Rate Limiting

Token bucket algorithm ensures respectful crawling:
```python
# 2 requests per second per domain
rate_limiter = DomainRateLimiter(requests_per_second=2.0)
```

### robots.txt Compliance

Automatic checking and enforcement:
```python
# Checks robots.txt before each request
if robots_parser.can_fetch(url):
    # Proceed with crawl
```

## Best Practices Demonstrated

1. **Politeness**
   - Respects robots.txt
   - Rate limiting per domain
   - Configurable delays
   - Proper User-Agent

2. **Robustness**
   - Retry logic with exponential backoff
   - Timeout handling
   - Error logging
   - Graceful degradation

3. **Efficiency**
   - Connection pooling (async)
   - Bloom filter deduplication
   - Concurrent requests (async)
   - Priority-based crawling

4. **Maintainability**
   - Modular design
   - Type hints
   - Comprehensive logging
   - Configuration via CLI

## Performance Comparison

| Metric | Basic Crawler | Async Crawler |
|--------|---------------|---------------|
| Concurrency | 1 | 10+ (configurable) |
| Typical Speed | 0.5-1 page/sec | 5-20 pages/sec |
| Memory Usage | Low | Medium |
| Complexity | Low | Medium |
| Best For | Learning, small sites | Production, large sites |

## Extending the Crawlers

### Add Custom Data Extraction

```python
# In _fetch_page method, add:
# Extract specific data
price = soup.find('span', class_='price')
if price:
    result['price'] = price.get_text(strip=True)
```

### Add Database Storage

```python
# Replace JSON output with database:
import sqlite3

def save_to_db(self, result):
    conn = sqlite3.connect('crawl.db')
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pages VALUES (?, ?, ?, ?)",
        (result['url'], result['title'], result['content'], result['timestamp'])
    )
    conn.commit()
```

### Add JavaScript Rendering

```python
# Use playwright for dynamic content:
from playwright.async_api import async_playwright

async def fetch_with_js(self, url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        content = await page.content()
        await browser.close()
        return content
```

## Common Issues and Solutions

### Issue: Too many connection errors

**Solution**: Reduce concurrency or increase rate limit delay
```bash
python async_crawler.py URL --concurrency 5 --rate 1.0
```

### Issue: Memory usage too high

**Solution**: Increase Bloom filter false positive rate or reduce max pages
```bash
python async_crawler.py URL --max-pages 1000 --bloom-size 50000
```

### Issue: Getting blocked by websites

**Solution**: Increase delays, reduce concurrency, add custom User-Agent
```bash
python basic_crawler.py URL --delay 3.0 --user-agent "Mozilla/5.0..."
```

### Issue: Need to crawl JavaScript-heavy sites

**Solution**: Use playwright or selenium instead of requests/aiohttp (see extensions above)

## Testing

Run the crawlers on safe test sites:

```bash
# Example.com (safe for testing)
python basic_crawler.py https://example.com --max-pages 10

# Your own test server
python async_crawler.py http://localhost:8000 --concurrency 5
```

## Legal and Ethical Considerations

⚠️ **Important**: Always follow these guidelines:

1. **Check robots.txt** - Both crawlers do this automatically
2. **Respect rate limits** - Use appropriate delays
3. **Check Terms of Service** - Some sites prohibit scraping
4. **Don't overload servers** - Use reasonable concurrency
5. **Identify yourself** - Use a descriptive User-Agent
6. **Handle personal data carefully** - Follow privacy laws (GDPR, etc.)

## Further Reading

- [Web Scraping Best Practices](https://www.promptcloud.com/blog/web-scraping-best-practices/)
- [robots.txt Specification](https://www.robotstxt.org/)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [aiohttp Documentation](https://docs.aiohttp.org/)
