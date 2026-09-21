"""URL normalization utilities for web crawling.

This module provides utilities to normalize URLs for deduplication and comparison.
"""

from urllib.parse import urlparse, urlunparse, urljoin, parse_qs, urlencode
from typing import Optional


class URLNormalizer:
    """Normalizes URLs to a canonical form for deduplication."""
    
    def __init__(self, 
                 remove_fragment: bool = True,
                 sort_query: bool = True,
                 remove_default_port: bool = True,
                 lowercase_scheme_host: bool = True):
        """Initialize URL normalizer with configuration.
        
        Args:
            remove_fragment: Remove URL fragments (#section)
            sort_query: Sort query parameters alphabetically
            remove_default_port: Remove default ports (80 for http, 443 for https)
            lowercase_scheme_host: Lowercase scheme and hostname
        """
        self.remove_fragment = remove_fragment
        self.sort_query = sort_query
        self.remove_default_port = remove_default_port
        self.lowercase_scheme_host = lowercase_scheme_host
    
    def normalize(self, url: str, base_url: Optional[str] = None) -> str:
        """Normalize a URL to canonical form.
        
        Args:
            url: URL to normalize
            base_url: Optional base URL for resolving relative URLs
            
        Returns:
            Normalized URL string
        """
        # Resolve relative URLs
        if base_url:
            url = urljoin(base_url, url)
        
        parsed = urlparse(url)
        
        # Normalize scheme and hostname
        scheme = parsed.scheme.lower() if self.lowercase_scheme_host else parsed.scheme
        netloc = parsed.netloc.lower() if self.lowercase_scheme_host else parsed.netloc
        
        # Remove default ports
        if self.remove_default_port:
            if scheme == 'http' and netloc.endswith(':80'):
                netloc = netloc[:-3]
            elif scheme == 'https' and netloc.endswith(':443'):
                netloc = netloc[:-4]
        
        # Normalize path (remove /. and trailing slash on non-root paths)
        path = parsed.path
        if path and path != '/':
            # Remove trailing slash
            path = path.rstrip('/')
        if not path:
            path = '/'
        
        # Sort query parameters
        query = parsed.query
        if self.sort_query and query:
            params = parse_qs(query, keep_blank_values=True)
            # Sort by key and flatten
            sorted_params = sorted(params.items())
            query = urlencode(sorted_params, doseq=True)
        
        # Remove fragment if configured
        fragment = '' if self.remove_fragment else parsed.fragment
        
        # Reconstruct URL
        normalized = urlunparse((scheme, netloc, path, parsed.params, query, fragment))
        
        return normalized
    
    def is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain.
        
        Args:
            url1: First URL
            url2: Second URL
            
        Returns:
            True if same domain, False otherwise
        """
        domain1 = urlparse(url1).netloc.lower()
        domain2 = urlparse(url2).netloc.lower()
        return domain1 == domain2
    
    def get_domain(self, url: str) -> str:
        """Extract domain from URL.
        
        Args:
            url: URL to extract domain from
            
        Returns:
            Domain string (scheme + netloc)
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
