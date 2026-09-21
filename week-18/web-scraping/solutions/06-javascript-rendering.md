# JavaScript Rendering - Headless Browser Automation

## Overview

Modern websites increasingly rely on JavaScript to render content. Traditional HTML parsers cannot execute JavaScript, so headless browsers are necessary for scraping Single Page Applications (SPAs) and dynamically loaded content.

## When JavaScript Rendering is Needed

### ✅ Need JavaScript:
- **SPAs** (React, Vue, Angular apps)
- **Infinite scroll** (content loads as you scroll)
- **Dynamic content** (AJAX-loaded data)
- **Protected content** (requires user interaction)
- **Complex interactions** (forms, dropdowns, modals)

### ❌ Don't Need JavaScript:
- **Static HTML** (content in initial response)
- **Server-side rendered** pages
- **API endpoints** (use API directly instead)
- **Simple forms** (can submit via HTTP POST)

**Decision Tree:**
```python
def needs_javascript(url):
    """Heuristic to detect if JavaScript is needed"""
    
    # Fetch HTML without JavaScript
    html = fetch_static(url)
    
    # Check for SPA indicators
    if '<div id="root"></div>' in html or '<div id="app"></div>' in html:
        return True
    
    # Check for heavy framework usage
    if 'react' in html.lower() or 'vue' in html.lower() or 'angular' in html.lower():
        return True
    
    # Check for dynamic loading scripts
    if 'fetch(' in html or 'XMLHttpRequest' in html:
        return True
    
    # Check content length
    content_length = len(extract_text(html))
    if content_length < 100:  # Too little content
        return True
    
    return False
```

## Headless Browser Options

### Comparison

| Browser | Speed | Memory | Features | Use Case |
|---------|-------|--------|----------|----------|
| **Playwright** | Fast | Medium | Modern, Multi-browser | Production (recommended) |
| **Selenium** | Slow | High | Mature, Wide support | Legacy compatibility |
| **Puppeteer** | Fast | Medium | Chrome-only | Node.js projects |
| **Splash** | Medium | Medium | HTTP API, Lua scripts | Distributed systems |

## Implementation: Playwright (Recommended)

### Basic Setup

```python
from playwright.async_api import async_playwright
import asyncio

class JavaScriptRenderer:
    """
    Render JavaScript-heavy pages using Playwright
    """
    def __init__(self, headless=True, max_contexts=5):
        self.playwright = None
        self.browser = None
        self.headless = headless
        self.max_contexts = max_contexts
        self.contexts = []
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        )
        
        return self
    
    async def __aexit__(self, *args):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def render(self, url, wait_for=None, timeout=30000):
        """
        Render page and return HTML
        
        wait_for: CSS selector to wait for before returning
        timeout: Maximum wait time in milliseconds
        """
        # Create new context (isolated browser session)
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        try:
            page = await context.new_page()
            
            # Navigate to URL
            await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            
            # Wait for specific element if provided
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout)
            else:
                # Wait for network to be idle
                await page.wait_for_load_state('networkidle', timeout=timeout)
            
            # Get rendered HTML
            html = await page.content()
            
            return {
                'url': page.url,  # Final URL after redirects
                'html': html,
                'title': await page.title(),
                'error': None
            }
        
        except Exception as e:
            return {
                'url': url,
                'error': str(e)
            }
        
        finally:
            await context.close()
    
    async def render_with_interaction(self, url, actions):
        """
        Render page and perform interactions
        
        actions: List of interactions to perform
        Example:
        [
            {'action': 'click', 'selector': 'button#load-more'},
            {'action': 'scroll', 'amount': 1000},
            {'action': 'wait', 'ms': 2000},
            {'action': 'type', 'selector': 'input#search', 'text': 'query'}
        ]
        """
        context = await self.browser.new_context()
        
        try:
            page = await context.new_page()
            await page.goto(url, wait_until='networkidle')
            
            # Perform actions
            for action_spec in actions:
                action = action_spec['action']
                
                if action == 'click':
                    await page.click(action_spec['selector'])
                    await page.wait_for_load_state('networkidle')
                
                elif action == 'scroll':
                    await page.evaluate(f"window.scrollBy(0, {action_spec['amount']})")
                    await asyncio.sleep(0.5)  # Let content load
                
                elif action == 'wait':
                    await asyncio.sleep(action_spec['ms'] / 1000)
                
                elif action == 'type':
                    await page.type(action_spec['selector'], action_spec['text'])
                
                elif action == 'select':
                    await page.select_option(action_spec['selector'], action_spec['value'])
            
            # Get final HTML
            html = await page.content()
            
            return {
                'url': page.url,
                'html': html,
                'error': None
            }
        
        except Exception as e:
            return {'url': url, 'error': str(e)}
        
        finally:
            await context.close()

# Usage
async def main():
    async with JavaScriptRenderer() as renderer:
        # Simple rendering
        result = await renderer.render('https://example.com')
        print(result['html'])
        
        # Wait for specific element
        result = await renderer.render(
            'https://example.com',
            wait_for='div.content-loaded'
        )
        
        # Render with interactions
        result = await renderer.render_with_interaction(
            'https://example.com/infinite-scroll',
            [
                {'action': 'scroll', 'amount': 1000},
                {'action': 'wait', 'ms': 2000},
                {'action': 'scroll', 'amount': 1000},
                {'action': 'wait', 'ms': 2000}
            ]
        )

asyncio.run(main())
```

## Advanced Techniques

### 1. Infinite Scroll Handling

```python
async def scrape_infinite_scroll(url, max_scrolls=10):
    """
    Handle infinite scroll pages
    """
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(url)
    
    items = []
    prev_height = 0
    scroll_count = 0
    
    while scroll_count < max_scrolls:
        # Extract items currently visible
        new_items = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.item')).map(el => ({
                title: el.querySelector('h2')?.textContent,
                url: el.querySelector('a')?.href
            }));
        }''')
        items.extend(new_items)
        
        # Scroll to bottom
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(2)  # Wait for content to load
        
        # Check if new content loaded
        new_height = await page.evaluate('document.body.scrollHeight')
        
        # Also check if new items appeared
        new_item_count = await page.evaluate('document.querySelectorAll(".item").length')
        
        if new_height == prev_height and new_item_count == len(items):
            break  # No more content (height unchanged and no new items)
        
        prev_height = new_height
        scroll_count += 1
    
    await context.close()
    return items
```

### 2. Handling Dynamic Content Loading

```python
async def wait_for_dynamic_content(page, selector, timeout=30000):
    """
    Wait for dynamically loaded content
    """
    try:
        # Wait for element to appear
        await page.wait_for_selector(selector, state='visible', timeout=timeout)
        
        # Wait for element to be stable (no more DOM changes)
        await page.wait_for_function(
            f'''() => {{
                const el = document.querySelector('{selector}');
                return el && el.textContent.length > 0;
            }}''',
            timeout=timeout
        )
        
        return True
    except Exception:
        return False
```

### 3. Handling Modals and Popups

```python
async def handle_cookie_consent(page):
    """
    Automatically handle cookie consent modals
    """
    # Common selectors for accept buttons
    accept_selectors = [
        'button:has-text("Accept")',
        'button:has-text("I agree")',
        'button:has-text("OK")',
        '#accept-cookies',
        '.cookie-accept',
        'button[id*="accept"]',
        'button[class*="accept"]'
    ]
    
    for selector in accept_selectors:
        try:
            await page.click(selector, timeout=2000)
            print(f"Clicked cookie consent: {selector}")
            return
        except Exception:
            continue
```

### 4. Screenshot and PDF Generation

```python
async def capture_page(url, output_path):
    """
    Capture screenshot and PDF of rendered page
    """
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(url, wait_until='networkidle')
    
    # Screenshot
    await page.screenshot(
        path=f'{output_path}.png',
        full_page=True  # Capture entire page, not just viewport
    )
    
    # PDF
    await page.pdf(
        path=f'{output_path}.pdf',
        format='A4',
        print_background=True
    )
    
    await context.close()
```

## Browser Pool Management

### Why Pool Browsers?

Browser instances are expensive:
- **Memory:** 100-500MB per browser
- **Startup:** 1-3 seconds to launch
- **CPU:** Rendering is CPU-intensive

Solution: Reuse browser instances with a pool.

```python
import asyncio
from collections import deque

class BrowserPool:
    """
    Pool of browser contexts for efficient reuse
    """
    def __init__(self, size=5):
        self.size = size
        self.browser = None
        self.available = deque()
        self.in_use = set()
        self.lock = asyncio.Lock()
    
    async def initialize(self, playwright):
        """Initialize browser and create contexts"""
        self.browser = await playwright.chromium.launch(headless=True)
        
        for _ in range(self.size):
            context = await self._create_context()
            self.available.append(context)
    
    async def _create_context(self):
        """Create new browser context"""
        return await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0...'
        )
    
    async def acquire(self):
        """Get a context from pool"""
        async with self.lock:
            if self.available:
                context = self.available.popleft()
            else:
                # Pool exhausted, create new context
                context = await self._create_context()
            
            self.in_use.add(context)
            return context
    
    async def release(self, context):
        """Return context to pool"""
        async with self.lock:
            self.in_use.remove(context)
            
            # Clear context state
            await context.clear_cookies()
            pages = context.pages
            for page in pages:
                await page.close()
            
            # Return to pool
            self.available.append(context)
    
    async def close(self):
        """Close all contexts and browser"""
        for context in self.available:
            await context.close()
        for context in self.in_use:
            await context.close()
        
        if self.browser:
            await self.browser.close()

# Usage
async def scrape_with_pool(urls):
    async with async_playwright() as p:
        pool = BrowserPool(size=5)
        await pool.initialize(p)
        
        async def scrape_one(url):
            context = await pool.acquire()
            try:
                page = await context.new_page()
                await page.goto(url)
                html = await page.content()
                return html
            finally:
                await pool.release(context)
        
        # Process URLs concurrently
        results = await asyncio.gather(*[scrape_one(url) for url in urls])
        
        await pool.close()
        return results
```

## Memory Optimization

### 1. Disable Images and Unnecessary Resources

```python
async def create_lightweight_context(browser):
    """
    Context that blocks images, fonts, and other heavy resources
    """
    context = await browser.new_context()
    
    # Block resource types
    await context.route('**/*', lambda route: (
        route.abort() if route.request.resource_type in ['image', 'font', 'media']
        else route.continue_()
    ))
    
    return context
```

### 2. Close Pages Immediately

```python
async def render_and_extract(url):
    context = await browser.new_context()
    page = await context.new_page()
    
    await page.goto(url)
    data = await page.evaluate('...')  # Extract data
    
    # Close immediately after extraction
    await page.close()
    await context.close()
    
    return data
```

### 3. Set Memory Limits

```python
browser = await playwright.chromium.launch(
    headless=True,
    args=[
        '--disable-dev-shm-usage',  # Use /tmp instead of /dev/shm
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-extensions',
        '--no-sandbox',
        '--memory-pressure-off',  # Disable memory pressure checks
    ]
)
```

## Detecting JavaScript Requirement

### Automatic Detection

```python
async def compare_static_vs_rendered(url):
    """
    Compare static HTML vs JavaScript-rendered HTML
    """
    # Fetch static HTML
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            static_html = await response.text()
    
    # Render with JavaScript
    async with JavaScriptRenderer() as renderer:
        result = await renderer.render(url)
        rendered_html = result['html']
    
    # Compare content
    static_text = extract_text(static_html)
    rendered_text = extract_text(rendered_html)
    
    # If rendered has significantly more content, JavaScript is needed
    if len(rendered_text) > len(static_text) * 1.5:
        return True, f"Rendered: {len(rendered_text)} chars, Static: {len(static_text)} chars"
    
    return False, "Static HTML sufficient"
```

## Testing

```python
import pytest

@pytest.mark.asyncio
async def test_render_basic():
    async with JavaScriptRenderer() as renderer:
        result = await renderer.render('https://example.com')
        assert result['error'] is None
        assert '<html' in result['html']

@pytest.mark.asyncio
async def test_render_spa():
    async with JavaScriptRenderer() as renderer:
        result = await renderer.render(
            'https://example.com/spa',
            wait_for='#app-loaded'
        )
        assert result['error'] is None
        assert 'app-loaded' in result['html']
```

## Performance Benchmarks

### Typical Performance

| Task | Static HTML | JavaScript Rendering | Slowdown |
|------|------------|---------------------|----------|
| Simple page | 50ms | 2000ms | 40x |
| Complex SPA | N/A | 5000ms | ∞ |
| With images | 200ms | 8000ms | 40x |

**Conclusion:** Only use JavaScript rendering when necessary!

## Hybrid Approach

```python
class SmartCrawler:
    """
    Automatically choose static vs JavaScript rendering
    """
    def __init__(self):
        self.static_client = HTTPClient()
        self.js_renderer = None
        self.js_needed_cache = {}  # url -> bool
    
    async def fetch(self, url):
        # Check cache
        if url in self.js_needed_cache:
            if self.js_needed_cache[url]:
                return await self._fetch_with_js(url)
            else:
                return await self._fetch_static(url)
        
        # Try static first
        static_result = await self._fetch_static(url)
        
        # Check if sufficient
        if self._has_sufficient_content(static_result['html']):
            self.js_needed_cache[url] = False
            return static_result
        
        # Fall back to JavaScript
        self.js_needed_cache[url] = True
        return await self._fetch_with_js(url)
```

## Next Steps

- Study `01-crawler-architecture.md` for system design
- Study `05-html-parser.md` for extracting data
- Study `07-captcha-bypass.md` for anti-detection
- Study `12-monitoring.md` for debugging browser issues

## Further Reading

- Playwright documentation
- Puppeteer documentation
- "Web Scraping with Python" by Ryan Mitchell (Chapter on JavaScript)
- Chrome DevTools Protocol documentation
