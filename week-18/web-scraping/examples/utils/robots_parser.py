"""robots.txt parser for respectful web crawling.

This module provides utilities to parse and check robots.txt files.
"""

import urllib.robotparser
from typing import Optional
import logging
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class RobotsParser:
    """Parser and checker for robots.txt files.
    
    Handles fetching, parsing, and checking robots.txt compliance.
    """
    
    def __init__(self, user_agent: str = "*"):
        """Initialize robots parser.
        
        Args:
            user_agent: User agent string to check rules for
        """
        self.user_agent = user_agent
        self._parsers = {}  # Cache parsers by domain
    
    def _get_robots_url(self, url: str) -> str:
        """Get robots.txt URL for a given URL.
        
        Args:
            url: URL to get robots.txt for
            
        Returns:
            robots.txt URL
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    def _get_parser(self, domain: str) -> urllib.robotparser.RobotFileParser:
        """Get or create parser for a domain.
        
        Args:
            domain: Domain to get parser for
            
        Returns:
            RobotFileParser instance
        """
        if domain not in self._parsers:
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(self._get_robots_url(domain))
            self._parsers[domain] = parser
        
        return self._parsers[domain]
    
    def fetch_and_parse(self, url: str) -> bool:
        """Fetch and parse robots.txt for a URL's domain.
        
        Args:
            url: URL to fetch robots.txt for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            
            parser = self._get_parser(domain)
            parser.read()
            
            logger.info(f"Successfully fetched robots.txt for {domain}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {url}: {e}")
            # If we can't fetch robots.txt, we should still allow crawling
            # but log the error
            return False
    
    def can_fetch(self, url: str, fetch_if_needed: bool = True) -> bool:
        """Check if URL can be fetched according to robots.txt.
        
        Args:
            url: URL to check
            fetch_if_needed: Fetch robots.txt if not already cached
            
        Returns:
            True if URL can be fetched, False otherwise
        """
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            
            parser = self._get_parser(domain)
            
            # Fetch robots.txt if not already done
            if fetch_if_needed and parser.mtime() == 0:
                try:
                    parser.read()
                except Exception as e:
                    logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
                    # Allow crawling if robots.txt is unavailable
                    return True
            
            # Check if we can fetch
            can_fetch = parser.can_fetch(self.user_agent, url)
            
            if not can_fetch:
                logger.debug(f"Blocked by robots.txt: {url}")
            
            return can_fetch
            
        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            # Default to allowing if there's an error
            return True
    
    def get_crawl_delay(self, url: str) -> Optional[float]:
        """Get crawl delay for a URL from robots.txt.
        
        Args:
            url: URL to check
            
        Returns:
            Crawl delay in seconds, or None if not specified
        """
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            
            parser = self._get_parser(domain)
            
            # Fetch robots.txt if not already done
            if parser.mtime() == 0:
                try:
                    parser.read()
                except Exception:
                    return None
            
            delay = parser.crawl_delay(self.user_agent)
            return float(delay) if delay is not None else None
            
        except Exception as e:
            logger.error(f"Error getting crawl delay for {url}: {e}")
            return None
    
    def clear_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._parsers.clear()
