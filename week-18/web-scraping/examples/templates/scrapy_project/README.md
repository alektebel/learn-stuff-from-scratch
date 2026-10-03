# Scrapy Project Template

This template provides a production-ready Scrapy crawler setup with best practices.

## What is Scrapy?

Scrapy is a powerful, production-ready web scraping framework that handles:
- Request scheduling and concurrency
- robots.txt compliance
- Connection pooling
- Automatic retries
- Response caching
- Data pipelines
- Middleware system

## Project Structure

```
scrapy_project/
├── README.md              # This file
├── scrapy.cfg             # Deploy configuration
├── crawler/               # Project module
│   ├── __init__.py
│   ├── settings.py        # Project settings
│   ├── items.py           # Data models
│   ├── pipelines.py       # Data processing
│   ├── middlewares.py     # Custom middleware
│   └── spiders/           # Spider definitions
│       ├── __init__.py
│       └── example.py     # Example spider
└── requirements.txt       # Dependencies
```

## Installation

```bash
# Install Scrapy
pip install -r requirements.txt

# Or create new Scrapy project
scrapy startproject crawler
```

## Usage

### Run a Spider

```bash
# Run the example spider
scrapy crawl example -o output.json

# Run with custom settings
scrapy crawl example -s CONCURRENT_REQUESTS=16 -o output.json

# Run with logging
scrapy crawl example -L INFO
```

### Create New Spider

```bash
scrapy genspider myspider example.com
```

## Spider Example

The included example spider (`crawler/spiders/example.py`) demonstrates:

- ✅ Basic crawling with `CrawlSpider`
- ✅ Link extraction with rules
- ✅ Data extraction with CSS selectors
- ✅ Item pipeline integration
- ✅ Error handling

## Configuration

Key settings in `settings.py`:

```python
# Concurrency
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# Delays
DOWNLOAD_DELAY = 1  # Politeness delay
RANDOMIZE_DOWNLOAD_DELAY = True

# User Agent
USER_AGENT = 'MyBot/1.0'

# Obey robots.txt
ROBOTSTXT_OBEY = True

# AutoThrottle (adaptive delays)
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_TARGET_CONCURRENCY = 4.0
```

## Data Pipeline

The pipeline (`pipelines.py`) processes scraped items:

1. **ValidationPipeline** - Validate required fields
2. **CleaningPipeline** - Clean and normalize data
3. **DuplicatesPipeline** - Remove duplicates
4. **StoragePipeline** - Save to database/file

## Middleware

Custom middleware (`middlewares.py`) for:

- User agent rotation
- Proxy rotation
- Request/response logging
- Error handling

## Advanced Features

### 1. Distributed Crawling

Use Scrapy-Redis for distributed crawling:

```bash
pip install scrapy-redis
```

Configure in `settings.py`:
```python
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
```

### 2. JavaScript Rendering

Use Scrapy-Playwright for JavaScript:

```bash
pip install scrapy-playwright
```

Configure in `settings.py`:
```python
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
```

### 3. AutoThrottle

Automatically adjust delays based on load:

```python
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
```

## Best Practices

1. **Always respect robots.txt**: Keep `ROBOTSTXT_OBEY = True`
2. **Use delays**: Set `DOWNLOAD_DELAY` to be polite
3. **Identify your bot**: Use descriptive `USER_AGENT`
4. **Handle errors**: Implement error callbacks
5. **Validate data**: Use Item Loaders for cleaning
6. **Monitor crawls**: Use Scrapy stats and logging

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY crawler/ crawler/
COPY scrapy.cfg .

CMD ["scrapy", "crawl", "example"]
```

### Scrapyd Deployment

```bash
# Install Scrapyd
pip install scrapyd scrapyd-client

# Deploy
scrapyd-deploy
```

## Monitoring

### Scrapy Stats

Access stats in spider:
```python
def closed(self, reason):
    stats = self.crawler.stats.get_stats()
    print(f"Pages: {stats.get('item_scraped_count', 0)}")
    print(f"Errors: {stats.get('spider_exceptions/KeyError', 0)}")
```

### Integration with Prometheus

Use `scrapy-prometheus-exporter`:
```bash
pip install scrapy-prometheus-exporter
```

## Testing

```bash
# Test spider
scrapy check example

# Test with mock server
scrapy crawl example -s HTTPCACHE_ENABLED=True
```

## Common Issues

### 1. Rate Limiting (HTTP 429)
- Increase `DOWNLOAD_DELAY`
- Enable `AUTOTHROTTLE_ENABLED`
- Reduce `CONCURRENT_REQUESTS_PER_DOMAIN`

### 2. Memory Issues
- Enable `MEMUSAGE_ENABLED = True`
- Set `MEMUSAGE_LIMIT_MB = 500`
- Reduce `CONCURRENT_REQUESTS`

### 3. JavaScript Content Missing
- Use Scrapy-Playwright or Scrapy-Selenium
- Or find API endpoints (check Network tab)

## Resources

- [Scrapy Documentation](https://docs.scrapy.org/)
- [Scrapy Tutorial](https://docs.scrapy.org/en/latest/intro/tutorial.html)
- [Best Practices](https://docs.scrapy.org/en/latest/topics/practices.html)
- [Scrapy-Redis](https://github.com/rmax/scrapy-redis)

## Next Steps

1. Customize `settings.py` for your needs
2. Create spiders in `spiders/` directory
3. Define items in `items.py`
4. Implement pipelines in `pipelines.py`
5. Add middleware as needed
6. Deploy with Scrapyd or Docker

## License

Educational use only. Respect robots.txt and Terms of Service.
