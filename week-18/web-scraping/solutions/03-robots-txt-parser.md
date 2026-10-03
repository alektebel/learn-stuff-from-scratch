# Robots.txt Parser - Implementation Guide

## Overview

The robots.txt file is a standard used by websites to communicate with web crawlers. It specifies which parts of the site should and shouldn't be crawled. Respecting robots.txt is both a legal requirement in many jurisdictions and an ethical obligation.

## Robots.txt Specification (RFC 9309)

### Basic Structure

```
User-agent: *
Disallow: /private/
Disallow: /tmp/
Allow: /public/

User-agent: Googlebot
Disallow: /no-google/

Crawl-delay: 10
Sitemap: https://example.com/sitemap.xml
```

### Key Directives

1. **User-agent**: Specifies which crawler the rules apply to
2. **Disallow**: Paths that should not be crawled
3. **Allow**: Paths that can be crawled (overrides Disallow)
4. **Crawl-delay**: Minimum delay between requests (seconds)
5. **Sitemap**: Location of XML sitemap

## Implementation Architecture

### Component Design

```
┌─────────────────────────────────────────┐
│         Robots.txt Parser               │
│                                         │
│  ┌─────────────┐    ┌───────────────┐ │
│  │   Fetcher   │───►│    Parser     │ │
│  │ (HTTP GET)  │    │ (Rule Engine) │ │
│  └─────────────┘    └───────┬───────┘ │
│                              │          │
│                              ▼          │
│  ┌─────────────┐    ┌───────────────┐ │
│  │    Cache    │◄───│  Rule Matcher │ │
│  │  (Redis)    │    │  (Per-Agent)  │ │
│  └─────────────┘    └───────────────┘ │
└─────────────────────────────────────────┘
```

## Core Data Structures

### Python Implementation

```python
from dataclasses import dataclass
from typing import List, Set, Optional
import re
from urllib.parse import urlparse
from datetime import datetime, timedelta

@dataclass
class RobotRule:
    """Represents a single robots.txt rule"""
    path: str
    allow: bool  # True for Allow, False for Disallow
    
    def matches(self, url_path: str) -> bool:
        """Check if this rule matches the given path"""
        # Convert robots.txt pattern to regex
        pattern = self._pattern_to_regex(self.path)
        return bool(re.match(pattern, url_path))
    
    def _pattern_to_regex(self, pattern: str) -> str:
        """Convert robots.txt pattern to regex"""
        # Escape special regex characters except * and $
        escaped = re.escape(pattern)
        # Replace escaped wildcards back
        escaped = escaped.replace(r'\*', '.*')
        escaped = escaped.replace(r'\$', '$')
        # Ensure pattern matches from start
        if not escaped.startswith('^'):
            escaped = '^' + escaped
        return escaped

@dataclass
class RobotRuleset:
    """Collection of rules for a specific user-agent"""
    user_agent: str
    rules: List[RobotRule]
    crawl_delay: Optional[float] = None
    sitemaps: List[str] = None
    
    def __post_init__(self):
        if self.sitemaps is None:
            self.sitemaps = []
        # Sort rules by specificity (longer paths first)
        self.rules.sort(key=lambda r: len(r.path), reverse=True)
    
    def is_allowed(self, url_path: str) -> bool:
        """Check if URL path is allowed to be crawled"""
        # Empty path is always allowed
        if not url_path:
            url_path = '/'
        
        # Check rules in order (most specific first)
        for rule in self.rules:
            if rule.matches(url_path):
                return rule.allow
        
        # If no rule matches, allow by default
        return True

class RobotsParser:
    """Parser for robots.txt files"""
    
    def __init__(self, cache_ttl: int = 86400):
        """
        Args:
            cache_ttl: Time-to-live for cached robots.txt in seconds (default 24h)
        """
        self.cache_ttl = cache_ttl
        self._cache = {}  # In production, use Redis
    
    def parse(self, content: str) -> dict[str, RobotRuleset]:
        """
        Parse robots.txt content
        
        Returns:
            Dict mapping user-agent to RobotRuleset
        """
        rulesets = {}
        current_agents = []
        current_rules = []
        crawl_delay = None
        sitemaps = []
        
        for line in content.split('\n'):
            # Remove comments and whitespace
            line = line.split('#')[0].strip()
            if not line:
                continue
            
            # Parse directive
            if ':' not in line:
                continue
            
            directive, value = line.split(':', 1)
            directive = directive.strip().lower()
            value = value.strip()
            
            if directive == 'user-agent':
                # Save previous ruleset if exists
                if current_agents:
                    self._save_ruleset(
                        rulesets, current_agents, current_rules,
                        crawl_delay, sitemaps
                    )
                # Start new ruleset
                current_agents = [value.lower()]
                current_rules = []
                crawl_delay = None
            
            elif directive == 'disallow':
                if current_agents:
                    current_rules.append(RobotRule(value, allow=False))
            
            elif directive == 'allow':
                if current_agents:
                    current_rules.append(RobotRule(value, allow=True))
            
            elif directive == 'crawl-delay':
                try:
                    crawl_delay = float(value)
                except ValueError:
                    pass
            
            elif directive == 'sitemap':
                sitemaps.append(value)
        
        # Save final ruleset
        if current_agents:
            self._save_ruleset(
                rulesets, current_agents, current_rules,
                crawl_delay, sitemaps
            )
        
        # Add default ruleset if not present
        if '*' not in rulesets:
            rulesets['*'] = RobotRuleset('*', [], sitemaps=sitemaps)
        
        return rulesets
    
    def _save_ruleset(self, rulesets, agents, rules, crawl_delay, sitemaps):
        """Helper to save a ruleset for multiple agents"""
        for agent in agents:
            rulesets[agent] = RobotRuleset(
                user_agent=agent,
                rules=rules.copy(),
                crawl_delay=crawl_delay,
                sitemaps=sitemaps.copy()
            )
    
    def is_allowed(self, url: str, user_agent: str = '*') -> bool:
        """
        Check if URL is allowed to be crawled
        
        Args:
            url: Full URL to check
            user_agent: User agent string
        
        Returns:
            True if allowed, False otherwise
        """
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Get robots.txt for domain
        robots_url = f"{base_url}/robots.txt"
        rulesets = self._get_robots(robots_url)
        
        if not rulesets:
            # If no robots.txt or error, allow by default
            return True
        
        # Find applicable ruleset
        # First try specific user agent, then wildcard
        user_agent_lower = user_agent.lower()
        ruleset = rulesets.get(user_agent_lower) or rulesets.get('*')
        
        if not ruleset:
            return True
        
        # Check if path is allowed
        return ruleset.is_allowed(parsed.path or '/')
    
    def get_crawl_delay(self, url: str, user_agent: str = '*') -> Optional[float]:
        """Get crawl delay for domain and user agent"""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{base_url}/robots.txt"
        
        rulesets = self._get_robots(robots_url)
        if not rulesets:
            return None
        
        user_agent_lower = user_agent.lower()
        ruleset = rulesets.get(user_agent_lower) or rulesets.get('*')
        
        return ruleset.crawl_delay if ruleset else None
    
    def get_sitemaps(self, url: str) -> List[str]:
        """Get sitemap URLs for domain"""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{base_url}/robots.txt"
        
        rulesets = self._get_robots(robots_url)
        if not rulesets:
            return []
        
        # Sitemaps are typically same for all user agents
        # Return from wildcard or first ruleset
        ruleset = rulesets.get('*') or next(iter(rulesets.values()))
        return ruleset.sitemaps if ruleset else []
    
    def _get_robots(self, robots_url: str) -> Optional[dict]:
        """Fetch and parse robots.txt with caching"""
        # Check cache
        if robots_url in self._cache:
            cached_time, rulesets = self._cache[robots_url]
            if datetime.now() - cached_time < timedelta(seconds=self.cache_ttl):
                return rulesets
        
        # Fetch robots.txt
        try:
            content = self._fetch_robots(robots_url)
            if content is None:
                return None
            
            rulesets = self.parse(content)
            self._cache[robots_url] = (datetime.now(), rulesets)
            return rulesets
        
        except Exception as e:
            # Log error, but allow crawling by default
            print(f"Error fetching robots.txt: {e}")
            return None
    
    def _fetch_robots(self, robots_url: str) -> Optional[str]:
        """Fetch robots.txt content (implement with HTTP client)"""
        # This should be implemented with actual HTTP client
        # For now, placeholder
        import requests
        try:
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                return response.text
            return None
        except:
            return None
```

## Advanced Features

### 1. Pattern Matching

Robots.txt supports wildcards:
- `*` matches any sequence of characters
- `$` matches end of URL

```python
def test_pattern_matching():
    rule = RobotRule("/admin/*", allow=False)
    
    assert rule.matches("/admin/")
    assert rule.matches("/admin/users")
    assert not rule.matches("/admin")  # No trailing content
    
    rule_end = RobotRule("/*.pdf$", allow=False)
    assert rule_end.matches("/document.pdf")
    assert not rule_end.matches("/document.pdf/page1")
```

### 2. Sitemap Integration

```python
class SitemapParser:
    """Parse XML sitemaps referenced in robots.txt"""
    
    def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Parse sitemap and return list of URLs"""
        import xml.etree.ElementTree as ET
        
        try:
            content = self._fetch(sitemap_url)
            root = ET.fromstring(content)
            
            # Handle sitemap index
            if 'sitemapindex' in root.tag:
                return self._parse_sitemap_index(root)
            
            # Handle regular sitemap
            urls = []
            for url_elem in root.findall('.//{*}url'):
                loc = url_elem.find('{*}loc')
                if loc is not None and loc.text:
                    urls.append(loc.text)
            
            return urls
        
        except Exception as e:
            print(f"Error parsing sitemap: {e}")
            return []
    
    def _parse_sitemap_index(self, root) -> List[str]:
        """Parse sitemap index (contains links to other sitemaps)"""
        sitemaps = []
        for sitemap in root.findall('.//{*}sitemap'):
            loc = sitemap.find('{*}loc')
            if loc is not None and loc.text:
                # Recursively parse child sitemaps
                sitemaps.extend(self.parse_sitemap(loc.text))
        return sitemaps
```

### 3. Distributed Caching with Redis

```python
import redis
import json

class RedisRobotsCache:
    """Redis-backed cache for robots.txt"""
    
    def __init__(self, redis_client: redis.Redis, ttl: int = 86400):
        self.redis = redis_client
        self.ttl = ttl
    
    def get(self, robots_url: str) -> Optional[dict]:
        """Get cached robots.txt rulesets"""
        key = f"robots:{robots_url}"
        cached = self.redis.get(key)
        
        if cached:
            data = json.loads(cached)
            # Reconstruct rulesets from JSON
            rulesets = {}
            for agent, ruleset_data in data.items():
                rules = [
                    RobotRule(r['path'], r['allow'])
                    for r in ruleset_data['rules']
                ]
                rulesets[agent] = RobotRuleset(
                    user_agent=agent,
                    rules=rules,
                    crawl_delay=ruleset_data.get('crawl_delay'),
                    sitemaps=ruleset_data.get('sitemaps', [])
                )
            return rulesets
        
        return None
    
    def set(self, robots_url: str, rulesets: dict):
        """Cache robots.txt rulesets"""
        key = f"robots:{robots_url}"
        
        # Serialize rulesets to JSON
        data = {}
        for agent, ruleset in rulesets.items():
            data[agent] = {
                'rules': [
                    {'path': r.path, 'allow': r.allow}
                    for r in ruleset.rules
                ],
                'crawl_delay': ruleset.crawl_delay,
                'sitemaps': ruleset.sitemaps
            }
        
        self.redis.setex(key, self.ttl, json.dumps(data))
```

## Testing Strategy

### Unit Tests

```python
import pytest

class TestRobotsParser:
    def test_basic_disallow(self):
        content = """
        User-agent: *
        Disallow: /private/
        """
        parser = RobotsParser()
        rulesets = parser.parse(content)
        
        assert not rulesets['*'].is_allowed('/private/file.html')
        assert rulesets['*'].is_allowed('/public/file.html')
    
    def test_allow_overrides_disallow(self):
        content = """
        User-agent: *
        Disallow: /private/
        Allow: /private/public/
        """
        parser = RobotsParser()
        rulesets = parser.parse(content)
        
        assert rulesets['*'].is_allowed('/private/public/file.html')
        assert not rulesets['*'].is_allowed('/private/secret.html')
    
    def test_wildcards(self):
        content = """
        User-agent: *
        Disallow: /*.pdf$
        """
        parser = RobotsParser()
        rulesets = parser.parse(content)
        
        assert not rulesets['*'].is_allowed('/document.pdf')
        assert rulesets['*'].is_allowed('/document.pdf/view')
    
    def test_specific_user_agent(self):
        content = """
        User-agent: Googlebot
        Disallow: /no-google/
        
        User-agent: *
        Disallow: /private/
        """
        parser = RobotsParser()
        rulesets = parser.parse(content)
        
        assert not rulesets['googlebot'].is_allowed('/no-google/page')
        assert rulesets['googlebot'].is_allowed('/private/page')
        assert not rulesets['*'].is_allowed('/private/page')
    
    def test_crawl_delay(self):
        content = """
        User-agent: *
        Crawl-delay: 10
        """
        parser = RobotsParser()
        rulesets = parser.parse(content)
        
        assert rulesets['*'].crawl_delay == 10.0
```

## Performance Considerations

### 1. Caching Strategy
- Cache parsed robots.txt for 24 hours (configurable)
- Use Redis for distributed caching
- Handle cache misses gracefully (allow by default)

### 2. Fetching Optimization
- Parallel robots.txt fetching for multiple domains
- Connection pooling for HTTP requests
- Timeout after 10 seconds
- Retry with exponential backoff

### 3. Rule Matching Performance
- Pre-compile regex patterns
- Sort rules by specificity
- Use trie data structure for large rulesets

## Error Handling

```python
class RobotsError(Exception):
    """Base exception for robots.txt errors"""
    pass

class RobotsFetchError(RobotsError):
    """Error fetching robots.txt"""
    pass

class RobotsParseError(RobotsError):
    """Error parsing robots.txt"""
    pass

def safe_check_robots(url: str, parser: RobotsParser) -> bool:
    """Safely check robots.txt, defaulting to allow on error"""
    try:
        return parser.is_allowed(url)
    except RobotsFetchError:
        # If we can't fetch robots.txt, allow by default
        return True
    except RobotsParseError:
        # If we can't parse robots.txt, allow by default
        return True
    except Exception as e:
        # Unexpected error, log and allow
        print(f"Unexpected error checking robots.txt: {e}")
        return True
```

## Integration with Crawler

```python
class RobotsMiddleware:
    """Middleware to check robots.txt before fetching"""
    
    def __init__(self, parser: RobotsParser, user_agent: str):
        self.parser = parser
        self.user_agent = user_agent
    
    async def process_request(self, url: str):
        """Check if request is allowed"""
        if not self.parser.is_allowed(url, self.user_agent):
            raise RobotsDisallowedError(f"URL blocked by robots.txt: {url}")
        
        # Apply crawl delay if specified
        delay = self.parser.get_crawl_delay(url, self.user_agent)
        if delay:
            await asyncio.sleep(delay)
```

## Best Practices

1. **Always Respect robots.txt**
   - Check before every request
   - Honor crawl delays
   - Use appropriate user agent

2. **Handle Errors Gracefully**
   - Default to allowing if robots.txt unavailable
   - Log errors for investigation
   - Don't let robots.txt errors stop crawling

3. **Cache Aggressively**
   - Robots.txt rarely changes
   - 24-hour TTL is reasonable
   - Use distributed cache (Redis)

4. **Be Transparent**
   - Use descriptive user agent
   - Provide contact information
   - Respect special directives

## Legal Considerations

- Robots.txt is not legally binding everywhere
- Some jurisdictions consider violating it illegal (CFAA in US)
- Always check Terms of Service
- Use robots.txt as minimum compliance level

## References

- RFC 9309: Robots Exclusion Protocol
- Google's robots.txt specification
- Archive.org robots.txt test suite
