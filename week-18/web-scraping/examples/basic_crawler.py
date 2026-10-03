#!/usr/bin/env python3
"""Basic single-threaded web crawler with politeness features.

This is a complete, production-ready web crawler that demonstrates
best practices for respectful web crawling.

Features:
- robots.txt compliance
- URL normalization and deduplication
- BeautifulSoup HTML parsing
- Link extraction
- Politeness delays
- JSON output
- Command-line interface
- Error handling
- Progress logging

Usage:
    python basic_crawler.py <start_url> [options]

Example:
    python basic_crawler.py https://example.com --max-pages 100 --delay 1.0
"""

import argparse
import json
import logging
import time
import sys
from collections import deque
from typing import Set, Dict, List, Optional
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

from utils.url_normalizer import URLNormalizer
from utils.robots_parser import RobotsParser


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BasicCrawler:
    """Single-threaded web crawler with politeness features.
    
    This crawler implements best practices for respectful web crawling,
    including robots.txt checking, rate limiting, and proper error handling.
    """
    
    def __init__(self,
                 start_url: str,
                 max_pages: int = 100,
                 delay: float = 1.0,
                 same_domain_only: bool = True,
                 user_agent: str = "BasicCrawler/1.0",
                 timeout: int = 10,
                 max_retries: int = 3):
        """Initialize the crawler.
        
        Args:
            start_url: URL to start crawling from
            max_pages: Maximum number of pages to crawl
            delay: Delay between requests in seconds
            same_domain_only: Only crawl URLs from the same domain
            user_agent: User agent string
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.start_url = start_url
        self.max_pages = max_pages
        self.delay = delay
        self.same_domain_only = same_domain_only
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize components
        self.url_normalizer = URLNormalizer()
        self.robots_parser = RobotsParser(user_agent=user_agent)
        
        # State tracking
        self.visited: Set[str] = set()
        self.queue: deque = deque()
        self.results: List[Dict] = []
        self.errors: List[Dict] = []
        
        # Statistics
        self.stats = {
            'pages_crawled': 0,
            'pages_failed': 0,
            'urls_discovered': 0,
            'urls_filtered': 0,
            'robots_blocked': 0,
            'start_time': None,
            'end_time': None,
        }
        
        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for crawling.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            
            # Must have http or https scheme
            if parsed.scheme not in ('http', 'https'):
                return False
            
            # Must have a netloc
            if not parsed.netloc:
                return False
            
            # Check same domain if required
            if self.same_domain_only:
                if not self.url_normalizer.is_same_domain(url, self.start_url):
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Invalid URL {url}: {e}")
            return False
    
    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract and normalize links from HTML.
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of normalized URLs
        """
        links = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all anchor tags
            for anchor in soup.find_all('a', href=True):
                href = anchor['href']
                
                # Resolve relative URLs
                absolute_url = urljoin(base_url, href)
                
                # Normalize URL
                normalized_url = self.url_normalizer.normalize(absolute_url)
                
                # Validate and add
                if self._is_valid_url(normalized_url):
                    links.append(normalized_url)
                else:
                    self.stats['urls_filtered'] += 1
            
            self.stats['urls_discovered'] += len(links)
            
        except Exception as e:
            logger.error(f"Error extracting links from {base_url}: {e}")
        
        return links
    
    def _fetch_page(self, url: str) -> Optional[Dict]:
        """Fetch a page and extract information.
        
        Args:
            url: URL to fetch
            
        Returns:
            Dictionary with page data, or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                # Make request
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract metadata
                title = soup.find('title')
                title_text = title.get_text(strip=True) if title else ''
                
                # Extract meta description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                description = meta_desc['content'] if meta_desc and meta_desc.get('content') else ''
                
                # Count links
                links = self._extract_links(response.text, url)
                
                return {
                    'url': url,
                    'final_url': response.url,
                    'status_code': response.status_code,
                    'title': title_text,
                    'description': description,
                    'content_type': response.headers.get('Content-Type', ''),
                    'content_length': len(response.text),
                    'num_links': len(links),
                    'links': links[:50],  # Store first 50 links
                    'timestamp': time.time(),
                }
                
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed for {url}: {e}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    # Final attempt failed
                    self.errors.append({
                        'url': url,
                        'error': str(e),
                        'timestamp': time.time(),
                    })
                    return None
            
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                self.errors.append({
                    'url': url,
                    'error': str(e),
                    'timestamp': time.time(),
                })
                return None
        
        return None
    
    def crawl(self) -> Dict:
        """Start the crawling process.
        
        Returns:
            Dictionary with crawl results and statistics
        """
        logger.info(f"Starting crawl from {self.start_url}")
        logger.info(f"Configuration: max_pages={self.max_pages}, delay={self.delay}s, same_domain_only={self.same_domain_only}")
        
        self.stats['start_time'] = time.time()
        
        # Normalize and add start URL
        start_url_normalized = self.url_normalizer.normalize(self.start_url)
        self.queue.append(start_url_normalized)
        
        # Check robots.txt for start URL
        if not self.robots_parser.can_fetch(start_url_normalized):
            logger.error(f"Start URL blocked by robots.txt: {start_url_normalized}")
            return self._get_results()
        
        # Get crawl delay from robots.txt
        robots_delay = self.robots_parser.get_crawl_delay(start_url_normalized)
        if robots_delay:
            logger.info(f"Using crawl delay from robots.txt: {robots_delay}s")
            self.delay = max(self.delay, robots_delay)
        
        # Main crawl loop
        last_request_time = 0
        
        while self.queue and self.stats['pages_crawled'] < self.max_pages:
            # Get next URL
            url = self.queue.popleft()
            
            # Skip if already visited
            if url in self.visited:
                continue
            
            # Mark as visited
            self.visited.add(url)
            
            # Check robots.txt
            if not self.robots_parser.can_fetch(url, fetch_if_needed=True):
                logger.debug(f"Skipping URL blocked by robots.txt: {url}")
                self.stats['robots_blocked'] += 1
                continue
            
            # Enforce politeness delay
            elapsed = time.time() - last_request_time
            if elapsed < self.delay:
                sleep_time = self.delay - elapsed
                logger.debug(f"Sleeping {sleep_time:.2f}s for politeness")
                time.sleep(sleep_time)
            
            # Fetch page
            logger.info(f"Crawling [{self.stats['pages_crawled'] + 1}/{self.max_pages}]: {url}")
            
            page_data = self._fetch_page(url)
            last_request_time = time.time()
            
            if page_data:
                # Success
                self.results.append(page_data)
                self.stats['pages_crawled'] += 1
                
                # Add discovered links to queue
                for link in page_data.get('links', []):
                    if link not in self.visited:
                        self.queue.append(link)
                
                # Progress update
                if self.stats['pages_crawled'] % 10 == 0:
                    self._log_progress()
            else:
                # Failed
                self.stats['pages_failed'] += 1
        
        # Finalize
        self.stats['end_time'] = time.time()
        self._log_progress()
        
        logger.info("Crawl complete!")
        
        return self._get_results()
    
    def _log_progress(self) -> None:
        """Log current progress statistics."""
        elapsed = time.time() - self.stats['start_time']
        rate = self.stats['pages_crawled'] / elapsed if elapsed > 0 else 0
        
        logger.info(
            f"Progress: {self.stats['pages_crawled']} crawled, "
            f"{self.stats['pages_failed']} failed, "
            f"{len(self.queue)} queued, "
            f"{len(self.visited)} visited, "
            f"{rate:.2f} pages/sec"
        )
    
    def _get_results(self) -> Dict:
        """Get final results dictionary.
        
        Returns:
            Dictionary with results and statistics
        """
        duration = (self.stats['end_time'] or time.time()) - self.stats['start_time']
        
        return {
            'start_url': self.start_url,
            'configuration': {
                'max_pages': self.max_pages,
                'delay': self.delay,
                'same_domain_only': self.same_domain_only,
                'user_agent': self.user_agent,
            },
            'statistics': {
                **self.stats,
                'duration': duration,
                'pages_per_second': self.stats['pages_crawled'] / duration if duration > 0 else 0,
            },
            'results': self.results,
            'errors': self.errors,
        }
    
    def save_results(self, filename: str) -> None:
        """Save results to JSON file.
        
        Args:
            filename: Output filename
        """
        results = self._get_results()
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {filename}")


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Basic web crawler with politeness features',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Crawl example.com with default settings
  %(prog)s https://example.com
  
  # Crawl up to 50 pages with 2 second delay
  %(prog)s https://example.com --max-pages 50 --delay 2.0
  
  # Allow cross-domain crawling
  %(prog)s https://example.com --allow-cross-domain
  
  # Save results to custom file
  %(prog)s https://example.com --output my_results.json
        """
    )
    
    parser.add_argument(
        'start_url',
        help='URL to start crawling from'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=100,
        help='Maximum number of pages to crawl (default: 100)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )
    parser.add_argument(
        '--allow-cross-domain',
        action='store_true',
        help='Allow crawling URLs from different domains'
    )
    parser.add_argument(
        '--user-agent',
        default='BasicCrawler/1.0',
        help='User agent string (default: BasicCrawler/1.0)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Request timeout in seconds (default: 10)'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum number of retries for failed requests (default: 3)'
    )
    parser.add_argument(
        '--output',
        default='crawl_results.json',
        help='Output JSON file (default: crawl_results.json)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run crawler
    crawler = BasicCrawler(
        start_url=args.start_url,
        max_pages=args.max_pages,
        delay=args.delay,
        same_domain_only=not args.allow_cross_domain,
        user_agent=args.user_agent,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )
    
    try:
        results = crawler.crawl()
        crawler.save_results(args.output)
        
        # Print summary
        print("\n" + "=" * 60)
        print("CRAWL SUMMARY")
        print("=" * 60)
        print(f"Pages crawled: {results['statistics']['pages_crawled']}")
        print(f"Pages failed: {results['statistics']['pages_failed']}")
        print(f"URLs discovered: {results['statistics']['urls_discovered']}")
        print(f"URLs filtered: {results['statistics']['urls_filtered']}")
        print(f"Blocked by robots.txt: {results['statistics']['robots_blocked']}")
        print(f"Duration: {results['statistics']['duration']:.2f}s")
        print(f"Rate: {results['statistics']['pages_per_second']:.2f} pages/sec")
        print(f"Results saved to: {args.output}")
        print("=" * 60)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.info("\nCrawl interrupted by user")
        crawler.save_results(args.output)
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Crawl failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
