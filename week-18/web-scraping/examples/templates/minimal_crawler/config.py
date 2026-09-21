"""
Configuration file for minimal crawler

Modify these settings to customize crawler behavior
"""

# Maximum crawl depth (how many links deep to follow)
MAX_DEPTH = 3

# Delay between requests in seconds (be polite!)
POLITENESS_DELAY = 1.0

# User agent string (identify your bot)
# IMPORTANT: Change this to identify your crawler
USER_AGENT = 'MyBot/1.0 (+http://example.com/bot-info)'

# Maximum number of pages to crawl
MAX_PAGES = 1000

# Request timeout in seconds
REQUEST_TIMEOUT = 10

# Output file for results
OUTPUT_FILE = 'results.json'
