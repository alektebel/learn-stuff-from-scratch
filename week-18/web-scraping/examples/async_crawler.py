#!/usr/bin/env python3
"""Production-ready asynchronous web crawler.

This is a high-performance, production-ready async web crawler that demonstrates
advanced techniques for large-scale web crawling.

Features:
- asyncio and aiohttp for concurrent requests
- Connection pooling
- Bloom filter for memory-efficient deduplication
- Per-domain rate limiting
- Priority queue for intelligent crawling
- Retry logic with exponential backoff
- Configurable concurrency
- Progress statistics
- Graceful shutdown
- Command-line interface

Usage:
    python async_crawler.py <start_url> [options]

Example:
    python async_crawler.py https://example.com --max-pages 1000 --concurrency 10
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from typing import Set, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import heapq

import aiohttp
from bs4 import BeautifulSoup

from utils.url_normalizer import URLNormalizer
from utils.bloom_filter import BloomFilter
from utils.rate_limiter import DomainRateLimiter


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass(order=True)
class CrawlTask:
    """A crawl task with priority."""
    priority: int
    url: str = field(compare=False)
    depth: int = field(compare=False, default=0)
    retry_count: int = field(compare=False, default=0)


@dataclass
class PageResult:
    """Result from crawling a page."""
    url: str
    final_url: str
    status_code: int
    title: str
    description: str
    content_type: str
    content_length: int
    num_links: int
    links: List[str]
    depth: int
    timestamp: float
    fetch_time: float


class AsyncCrawler:
    """High-performance asynchronous web crawler.
    
    This crawler uses asyncio and aiohttp for concurrent requests,
    with advanced features like Bloom filters, per-domain rate limiting,
    and priority-based crawling.
    """
    
    def __init__(self,
                 start_url: str,
                 max_pages: int = 1000,
                 max_depth: int = 3,
                 concurrency: int = 10,
                 requests_per_second: float = 2.0,
                 same_domain_only: bool = True,
                 user_agent: str = "AsyncCrawler/1.0",
                 timeout: int = 10,
                 max_retries: int = 3,
                 bloom_filter_size: int = 100000):
        """Initialize the async crawler.
        
        Args:
            start_url: URL to start crawling from
            max_pages: Maximum number of pages to crawl
            max_depth: Maximum link depth to crawl
            concurrency: Maximum number of concurrent requests
            requests_per_second: Rate limit per domain
            same_domain_only: Only crawl URLs from the same domain
            user_agent: User agent string
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            bloom_filter_size: Expected number of unique URLs
        """
        self.start_url = start_url
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.concurrency = concurrency
        self.requests_per_second = requests_per_second
        self.same_domain_only = same_domain_only
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize components
        self.url_normalizer = URLNormalizer()
        self.bloom_filter = BloomFilter(expected_elements=bloom_filter_size)
        self.rate_limiter = DomainRateLimiter(requests_per_second=requests_per_second)
        
        # State tracking
        self.priority_queue: List[CrawlTask] = []
        self.results: List[PageResult] = []
        self.errors: List[Dict] = []
        
        # Statistics
        self.stats = {
            'pages_crawled': 0,
            'pages_failed': 0,
            'urls_discovered': 0,
            'urls_filtered': 0,
            'urls_duplicate': 0,
            'bytes_downloaded': 0,
            'start_time': None,
            'end_time': None,
        }
        
        # Per-domain statistics
        self.domain_stats = defaultdict(lambda: {
            'requests': 0,
            'bytes': 0,
            'errors': 0,
        })
        
        # Async components
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore: Optional[asyncio.Semaphore] = None
        
        # Shutdown flag
        self.shutdown_requested = False
    
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
            
        except Exception:
            return False
    
    def _extract_links(self, html: str, base_url: str, current_depth: int) -> List[Tuple[str, int]]:
        """Extract and normalize links from HTML.
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
            current_depth: Current crawl depth
            
        Returns:
            List of (url, priority) tuples
        """
        links = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all anchor tags
            for anchor in soup.find_all('a', href=True):
                href = anchor['href']
                
                # Normalize URL
                normalized_url = self.url_normalizer.normalize(href, base_url)
                
                # Validate
                if not self._is_valid_url(normalized_url):
                    self.stats['urls_filtered'] += 1
                    continue
                
                # Check if already seen (Bloom filter)
                if normalized_url in self.bloom_filter:
                    self.stats['urls_duplicate'] += 1
                    continue
                
                # Add to Bloom filter
                self.bloom_filter.add(normalized_url)
                
                # Calculate priority (lower = higher priority)
                # Prioritize by depth (shallower = higher priority)
                priority = current_depth + 1
                
                links.append((normalized_url, priority))
                self.stats['urls_discovered'] += 1
            
        except Exception as e:
            logger.error(f"Error extracting links from {base_url}: {e}")
        
        return links
    
    async def _fetch_page(self, task: CrawlTask) -> Optional[PageResult]:
        """Fetch a page and extract information.
        
        Args:
            task: Crawl task to execute
            
        Returns:
            PageResult or None if failed
        """
        url = task.url
        domain = self.url_normalizer.get_domain(url)
        
        # Apply rate limiting
        await self.rate_limiter.acquire_async(domain)
        
        start_time = time.time()
        
        try:
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                allow_redirects=True
            ) as response:
                # Check status
                response.raise_for_status()
                
                # Read content
                html = await response.text()
                fetch_time = time.time() - start_time
                
                # Update statistics
                content_length = len(html)
                self.stats['bytes_downloaded'] += content_length
                self.domain_stats[domain]['requests'] += 1
                self.domain_stats[domain]['bytes'] += content_length
                
                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract metadata
                title = soup.find('title')
                title_text = title.get_text(strip=True) if title else ''
                
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                description = meta_desc['content'] if meta_desc and meta_desc.get('content') else ''
                
                # Extract links
                links_with_priority = self._extract_links(html, str(response.url), task.depth)
                links = [link for link, _ in links_with_priority]
                
                # Add links to queue if not at max depth
                if task.depth < self.max_depth:
                    for link, priority in links_with_priority:
                        new_task = CrawlTask(
                            priority=priority,
                            url=link,
                            depth=task.depth + 1
                        )
                        heapq.heappush(self.priority_queue, new_task)
                
                return PageResult(
                    url=url,
                    final_url=str(response.url),
                    status_code=response.status,
                    title=title_text,
                    description=description,
                    content_type=response.headers.get('Content-Type', ''),
                    content_length=content_length,
                    num_links=len(links),
                    links=links[:50],  # Store first 50 links
                    depth=task.depth,
                    timestamp=time.time(),
                    fetch_time=fetch_time,
                )
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {url}")
            self._record_error(url, "Timeout", domain)
            return None
            
        except aiohttp.ClientError as e:
            logger.warning(f"Client error fetching {url}: {e}")
            self._record_error(url, str(e), domain)
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            self._record_error(url, str(e), domain)
            return None
    
    def _record_error(self, url: str, error: str, domain: str) -> None:
        """Record a fetch error.
        
        Args:
            url: URL that failed
            error: Error message
            domain: Domain of the URL
        """
        self.errors.append({
            'url': url,
            'error': error,
            'timestamp': time.time(),
        })
        self.stats['pages_failed'] += 1
        self.domain_stats[domain]['errors'] += 1
    
    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes crawl tasks.
        
        Args:
            worker_id: ID of this worker
        """
        logger.debug(f"Worker {worker_id} started")
        
        while not self.shutdown_requested:
            # Check if we've reached max pages
            if self.stats['pages_crawled'] >= self.max_pages:
                break
            
            # Get next task
            if not self.priority_queue:
                # No more tasks - wait briefly to allow other workers to add tasks
                await asyncio.sleep(0.5)
                # If still no tasks after multiple attempts, exit
                if not self.priority_queue:
                    break
                continue
            
            try:
                task = heapq.heappop(self.priority_queue)
            except IndexError:
                # Race condition - queue became empty
                continue
            
            # Process task
            async with self.semaphore:
                result = await self._fetch_page(task)
                
                if result:
                    self.results.append(result)
                    self.stats['pages_crawled'] += 1
                    
                    # Log progress
                    if self.stats['pages_crawled'] % 10 == 0:
                        self._log_progress()
                
                elif task.retry_count < self.max_retries:
                    # Retry with exponential backoff
                    retry_delay = 2 ** task.retry_count
                    await asyncio.sleep(retry_delay)
                    
                    task.retry_count += 1
                    task.priority += 10  # Lower priority for retries
                    heapq.heappush(self.priority_queue, task)
        
        logger.debug(f"Worker {worker_id} finished")
    
    def _log_progress(self) -> None:
        """Log current progress statistics."""
        elapsed = time.time() - self.stats['start_time']
        rate = self.stats['pages_crawled'] / elapsed if elapsed > 0 else 0
        
        logger.info(
            f"Progress: {self.stats['pages_crawled']}/{self.max_pages} crawled, "
            f"{self.stats['pages_failed']} failed, "
            f"{len(self.priority_queue)} queued, "
            f"{self.stats['bytes_downloaded'] / 1024 / 1024:.2f} MB, "
            f"{rate:.2f} pages/sec"
        )
    
    async def crawl(self) -> Dict:
        """Start the crawling process.
        
        Returns:
            Dictionary with crawl results and statistics
        """
        logger.info(f"Starting async crawl from {self.start_url}")
        logger.info(
            f"Configuration: max_pages={self.max_pages}, "
            f"max_depth={self.max_depth}, "
            f"concurrency={self.concurrency}, "
            f"rate={self.requests_per_second} req/sec"
        )
        
        self.stats['start_time'] = time.time()
        
        # Create session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.concurrency * 2,  # Connection pool size
            limit_per_host=self.concurrency,
            ttl_dns_cache=300,
        )
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.user_agent},
        )
        
        # Create semaphore for concurrency control
        self.semaphore = asyncio.Semaphore(self.concurrency)
        
        try:
            # Add start URL to queue
            start_url_normalized = self.url_normalizer.normalize(self.start_url)
            self.bloom_filter.add(start_url_normalized)
            
            start_task = CrawlTask(priority=0, url=start_url_normalized, depth=0)
            heapq.heappush(self.priority_queue, start_task)
            
            # Create workers
            workers = [
                asyncio.create_task(self._worker(i))
                for i in range(self.concurrency)
            ]
            
            # Wait for workers to complete
            await asyncio.gather(*workers, return_exceptions=True)
            
        finally:
            # Cleanup
            await self.session.close()
            self.stats['end_time'] = time.time()
        
        self._log_progress()
        logger.info("Crawl complete!")
        
        return self._get_results()
    
    def _get_results(self) -> Dict:
        """Get final results dictionary.
        
        Returns:
            Dictionary with results and statistics
        """
        duration = (self.stats['end_time'] or time.time()) - self.stats['start_time']
        
        # Convert results to dictionaries
        results_dict = [asdict(result) for result in self.results]
        
        # Calculate domain statistics
        domain_stats_list = [
            {
                'domain': domain,
                **stats
            }
            for domain, stats in self.domain_stats.items()
        ]
        
        return {
            'start_url': self.start_url,
            'configuration': {
                'max_pages': self.max_pages,
                'max_depth': self.max_depth,
                'concurrency': self.concurrency,
                'requests_per_second': self.requests_per_second,
                'same_domain_only': self.same_domain_only,
                'user_agent': self.user_agent,
            },
            'statistics': {
                **self.stats,
                'duration': duration,
                'pages_per_second': self.stats['pages_crawled'] / duration if duration > 0 else 0,
                'avg_fetch_time': sum(r.fetch_time for r in self.results) / len(self.results) if self.results else 0,
                'bloom_filter': self.bloom_filter.stats(),
            },
            'domain_statistics': domain_stats_list,
            'results': results_dict,
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


async def async_main(args):
    """Async main function."""
    crawler = AsyncCrawler(
        start_url=args.start_url,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        concurrency=args.concurrency,
        requests_per_second=args.rate,
        same_domain_only=not args.allow_cross_domain,
        user_agent=args.user_agent,
        timeout=args.timeout,
        max_retries=args.max_retries,
        bloom_filter_size=args.bloom_size,
    )
    
    try:
        results = await crawler.crawl()
        crawler.save_results(args.output)
        
        # Print summary
        print("\n" + "=" * 60)
        print("ASYNC CRAWL SUMMARY")
        print("=" * 60)
        print(f"Pages crawled: {results['statistics']['pages_crawled']}")
        print(f"Pages failed: {results['statistics']['pages_failed']}")
        print(f"URLs discovered: {results['statistics']['urls_discovered']}")
        print(f"URLs filtered: {results['statistics']['urls_filtered']}")
        print(f"URLs duplicate: {results['statistics']['urls_duplicate']}")
        print(f"Data downloaded: {results['statistics']['bytes_downloaded'] / 1024 / 1024:.2f} MB")
        print(f"Duration: {results['statistics']['duration']:.2f}s")
        print(f"Rate: {results['statistics']['pages_per_second']:.2f} pages/sec")
        print(f"Avg fetch time: {results['statistics']['avg_fetch_time']:.3f}s")
        print(f"\nBloom filter stats:")
        print(f"  Elements: {results['statistics']['bloom_filter']['elements_added']}")
        print(f"  FP rate: {results['statistics']['bloom_filter']['current_fp_rate']:.6f}")
        print(f"  Capacity used: {results['statistics']['bloom_filter']['capacity_used']:.1%}")
        print(f"\nResults saved to: {args.output}")
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nCrawl interrupted by user")
        crawler.shutdown_requested = True
        crawler.save_results(args.output)
        return 1


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Production-ready async web crawler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Crawl with 10 concurrent workers
  %(prog)s https://example.com --concurrency 10
  
  # Crawl up to depth 5 with 1000 max pages
  %(prog)s https://example.com --max-pages 1000 --max-depth 5
  
  # High-speed crawling with 20 workers and 5 req/sec per domain
  %(prog)s https://example.com --concurrency 20 --rate 5.0
  
  # Save results to custom file
  %(prog)s https://example.com --output my_async_results.json
        """
    )
    
    parser.add_argument(
        'start_url',
        help='URL to start crawling from'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=1000,
        help='Maximum number of pages to crawl (default: 1000)'
    )
    parser.add_argument(
        '--max-depth',
        type=int,
        default=3,
        help='Maximum link depth to crawl (default: 3)'
    )
    parser.add_argument(
        '--concurrency',
        type=int,
        default=10,
        help='Maximum number of concurrent requests (default: 10)'
    )
    parser.add_argument(
        '--rate',
        type=float,
        default=2.0,
        help='Requests per second per domain (default: 2.0)'
    )
    parser.add_argument(
        '--allow-cross-domain',
        action='store_true',
        help='Allow crawling URLs from different domains'
    )
    parser.add_argument(
        '--user-agent',
        default='AsyncCrawler/1.0',
        help='User agent string (default: AsyncCrawler/1.0)'
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
        '--bloom-size',
        type=int,
        default=100000,
        help='Expected number of unique URLs (default: 100000)'
    )
    parser.add_argument(
        '--output',
        default='async_crawl_results.json',
        help='Output JSON file (default: async_crawl_results.json)'
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
    
    # Run async main
    try:
        exit_code = asyncio.run(async_main(args))
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Crawl failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
