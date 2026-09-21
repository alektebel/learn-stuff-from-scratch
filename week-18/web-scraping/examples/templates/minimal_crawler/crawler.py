"""
Minimal Web Crawler Template

A simple, extensible web crawler that you can customize for your needs.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import time
from typing import Set, List, Dict
import json
from collections import deque

from config import *


class MinimalCrawler:
    """Simple web crawler"""
    
    def __init__(self):
        self.visited: Set[str] = set()
        self.to_visit: deque = deque()
        self.results: List[Dict] = []
        self.robots_parsers: Dict[str, RobotFileParser] = {}
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        if base_url not in self.robots_parsers:
            rp = RobotFileParser()
            rp.set_url(f"{base_url}/robots.txt")
            try:
                rp.read()
            except:
                pass  # If robots.txt doesn't exist, allow crawling
            self.robots_parsers[base_url] = rp
        
        return self.robots_parsers[base_url].can_fetch(USER_AGENT, url)
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication"""
        parsed = urlparse(url)
        # Remove fragment
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}{'?' + parsed.query if parsed.query else ''}"
    
    def fetch_page(self, url: str) -> str:
        """Fetch page content"""
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    
    def parse_page(self, html: str, url: str) -> Dict:
        """
        Parse page and extract data
        
        CUSTOMIZE THIS METHOD for your use case
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract title
        title = soup.find('title')
        title_text = title.get_text(strip=True) if title else ''
        
        # Extract main heading
        h1 = soup.find('h1')
        heading = h1.get_text(strip=True) if h1 else ''
        
        # Extract all text
        text = soup.get_text(separator=' ', strip=True)
        
        # Extract metadata
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '') if meta_desc else ''
        
        return {
            'url': url,
            'title': title_text,
            'heading': heading,
            'description': description,
            'text_length': len(text)
        }
    
    def extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract links from page"""
        soup = BeautifulSoup(html, 'lxml')
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            
            # Only keep HTTP(S) links
            if full_url.startswith(('http://', 'https://')):
                normalized = self.normalize_url(full_url)
                links.append(normalized)
        
        return links
    
    def crawl(self, start_url: str, max_depth: int = MAX_DEPTH):
        """
        Crawl starting from start_url
        
        Args:
            start_url: URL to start crawling from
            max_depth: Maximum depth to crawl
        """
        # Add start URL
        self.to_visit.append((start_url, 0))  # (url, depth)
        
        print(f"Starting crawl from: {start_url}")
        print(f"Max depth: {max_depth}, Max pages: {MAX_PAGES}")
        print("-" * 60)
        
        while self.to_visit and len(self.visited) < MAX_PAGES:
            url, depth = self.to_visit.popleft()
            
            # Skip if already visited
            if url in self.visited:
                continue
            
            # Skip if depth exceeded
            if depth > max_depth:
                continue
            
            # Skip if not allowed by robots.txt
            if not self.can_fetch(url):
                print(f"[SKIP] Blocked by robots.txt: {url}")
                continue
            
            try:
                print(f"[{len(self.visited)+1}] Crawling (depth={depth}): {url}")
                
                # Fetch page
                html = self.fetch_page(url)
                
                # Mark as visited
                self.visited.add(url)
                
                # Parse page
                data = self.parse_page(html, url)
                self.results.append(data)
                
                # Extract links if not at max depth
                if depth < max_depth:
                    links = self.extract_links(html, url)
                    for link in links:
                        if link not in self.visited:
                            self.to_visit.append((link, depth + 1))
                
                # Politeness delay
                time.sleep(POLITENESS_DELAY)
                
            except Exception as e:
                print(f"[ERROR] Failed to crawl {url}: {e}")
                continue
        
        print("-" * 60)
        print(f"Crawl complete! Visited {len(self.visited)} pages")
    
    def save_results(self, filename: str = 'results.json'):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to: {filename}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python crawler.py <start_url> [max_depth]")
        print("Example: python crawler.py https://example.com 2")
        sys.exit(1)
    
    start_url = sys.argv[1]
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else MAX_DEPTH
    
    crawler = MinimalCrawler()
    crawler.crawl(start_url, max_depth)
    crawler.save_results()


if __name__ == '__main__':
    main()
