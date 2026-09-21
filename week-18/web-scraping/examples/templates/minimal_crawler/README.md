# Minimal Crawler Template

This is a minimal starting point for building your own web crawler. It includes only the essential components.

## Structure

```
minimal_crawler/
├── README.md          # This file
├── crawler.py         # Main crawler logic
├── config.py          # Configuration
└── requirements.txt   # Dependencies
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python crawler.py https://example.com
```

## Customization

Edit `crawler.py` to add your own parsing logic in the `parse_page()` method:

```python
def parse_page(self, html, url):
    """
    Parse page and extract data
    
    Modify this method to extract the data you need
    """
    soup = BeautifulSoup(html, 'lxml')
    
    # Your custom extraction logic here
    data = {
        'title': soup.find('h1').get_text() if soup.find('h1') else '',
        # Add more fields...
    }
    
    return data
```

## Configuration

Edit `config.py` to adjust crawler behavior:

```python
# Maximum crawl depth
MAX_DEPTH = 3

# Delay between requests (seconds)
POLITENESS_DELAY = 1.0

# User agent string
USER_AGENT = 'MyBot/1.0 (+http://example.com/bot)'

# Maximum pages to crawl
MAX_PAGES = 1000
```

## Features

- ✅ Basic URL crawling
- ✅ robots.txt compliance
- ✅ Deduplication
- ✅ Politeness delays
- ✅ Simple data extraction

## Next Steps

To add more features:

1. **Async crawling**: See `../async_crawler.py`
2. **Better storage**: Add database integration
3. **More parsers**: Handle different content types
4. **Monitoring**: Add logging and metrics
5. **Distribution**: Use Redis for URL queue

## Resources

- Parent directory `../` has more advanced examples
- Solution guides in `../../solutions/`
