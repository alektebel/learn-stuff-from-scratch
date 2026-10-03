# HTML Parser - Efficient Parsing and Extraction

## Overview

HTML parsing is the core of web scraping - converting raw HTML into structured data you can work with. Efficient parsing can be the difference between 10 pages/second and 1000 pages/second.

## HTML Parsing Fundamentals

### What is HTML Parsing?

```html
<!-- Input: Raw HTML -->
<html>
  <head><title>Example</title></head>
  <body>
    <div class="content">
      <h1>Hello World</h1>
      <p>This is <a href="/link">a link</a></p>
    </div>
  </body>
</html>

<!-- Output: DOM Tree -->
Document
├── html
    ├── head
    │   └── title
    │       └── "Example"
    └── body
        └── div (class="content")
            ├── h1
            │   └── "Hello World"
            └── p
                ├── "This is "
                ├── a (href="/link")
                │   └── "a link"
                └── ""
```

### HTML5 Parsing Algorithm

HTML5 defines a precise parsing algorithm that handles malformed HTML gracefully:

1. **Tokenization:** Convert character stream to tokens
2. **Tree Construction:** Build DOM tree from tokens
3. **Error Recovery:** Handle malformed HTML

## Parser Performance Comparison

### Python Parsers

| Parser | Speed | Memory | Tolerance | Use Case |
|--------|-------|---------|-----------|----------|
| **BeautifulSoup4 + html.parser** | Slow | High | Medium | Development, prototyping |
| **BeautifulSoup4 + lxml** | Fast | Medium | High | Production (balanced) |
| **lxml** (direct) | Very Fast | Low | High | Production (performance) |
| **html5lib** | Slow | High | Very High | Standards compliance |
| **selectolax** | Fastest | Very Low | Medium | Production (speed-critical) |

### Benchmark (1000 pages, 50KB each)

```
Parser                    Time        Memory      Lines of Code
================================================================
BeautifulSoup4+html.parser  45s      800MB       Simple (5 lines)
BeautifulSoup4+lxml        12s      400MB       Simple (5 lines)
lxml (direct)              5s       200MB       Medium (15 lines)
selectolax                 2s       100MB       Medium (15 lines)
Custom C parser            0.5s     50MB        Complex (500 lines)
```

## Implementation Strategies

### 1. BeautifulSoup4 (Beginner-Friendly)

**Pros:**
- Simple API
- Handles broken HTML well
- Multiple backends (html.parser, lxml, html5lib)
- Great documentation

**Cons:**
- Slower than alternatives
- Higher memory usage

```python
from bs4 import BeautifulSoup
import requests

def extract_with_beautifulsoup(html):
    """
    Simple and readable, but slower
    """
    soup = BeautifulSoup(html, 'lxml')  # Use lxml for speed
    
    # Extract title
    title = soup.find('title')
    title_text = title.get_text() if title else None
    
    # Extract all links
    links = []
    for a_tag in soup.find_all('a', href=True):
        links.append({
            'url': a_tag['href'],
            'text': a_tag.get_text(strip=True)
        })
    
    # Extract specific content with CSS selectors
    articles = []
    for article in soup.select('article.post'):
        articles.append({
            'title': article.select_one('h2.title').get_text(strip=True),
            'content': article.select_one('div.content').get_text(strip=True),
            'date': article.select_one('time')['datetime']
        })
    
    return {
        'title': title_text,
        'links': links,
        'articles': articles
    }
```

### 2. lxml (Production)

**Pros:**
- Very fast (C-based)
- XPath and CSS selectors
- Low memory usage
- Robust

**Cons:**
- More verbose API
- Need to handle errors manually

```python
from lxml import html as lxml_html
from lxml import etree

def extract_with_lxml(html_text):
    """
    Fast and efficient, production-ready
    """
    try:
        tree = lxml_html.fromstring(html_text)
    except etree.ParserError:
        return None
    
    # Extract title using XPath
    title_elements = tree.xpath('//title/text()')
    title = title_elements[0] if title_elements else None
    
    # Extract links using XPath
    links = []
    for a in tree.xpath('//a[@href]'):
        links.append({
            'url': a.get('href'),
            'text': a.text_content().strip()
        })
    
    # Extract articles using CSS selectors (via cssselect)
    articles = []
    for article in tree.cssselect('article.post'):
        title_elem = article.cssselect('h2.title')
        content_elem = article.cssselect('div.content')
        date_elem = article.cssselect('time')
        
        articles.append({
            'title': title_elem[0].text_content().strip() if title_elem else None,
            'content': content_elem[0].text_content().strip() if content_elem else None,
            'date': date_elem[0].get('datetime') if date_elem else None
        })
    
    return {
        'title': title,
        'links': links,
        'articles': articles
    }
```

### 3. selectolax (Maximum Speed)

**Pros:**
- Fastest Python parser
- Very low memory usage
- Simple API

**Cons:**
- Less mature than lxml
- Fewer features

```python
from selectolax.parser import HTMLParser

def extract_with_selectolax(html_text):
    """
    Fastest option for simple extraction
    """
    tree = HTMLParser(html_text)
    
    # Extract title
    title_node = tree.css_first('title')
    title = title_node.text() if title_node else None
    
    # Extract links
    links = []
    for a in tree.css('a[href]'):
        links.append({
            'url': a.attributes.get('href'),
            'text': a.text(strip=True)
        })
    
    # Extract articles
    articles = []
    for article in tree.css('article.post'):
        title_node = article.css_first('h2.title')
        content_node = article.css_first('div.content')
        date_node = article.css_first('time')
        
        articles.append({
            'title': title_node.text(strip=True) if title_node else None,
            'content': content_node.text(strip=True) if content_node else None,
            'date': date_node.attributes.get('datetime') if date_node else None
        })
    
    return {
        'title': title,
        'links': links,
        'articles': articles
    }
```

### 4. Custom C Parser (Maximum Control)

For ultimate performance, implement a custom parser in C:

```c
// High-performance HTML parser using gumbo-parser
#include <gumbo.h>
#include <string.h>

typedef struct {
    char** urls;
    int url_count;
    int url_capacity;
} URLList;

void extract_links(GumboNode* node, URLList* urls) {
    if (node->type != GUMBO_NODE_ELEMENT) {
        return;
    }
    
    // Check if this is an <a> tag
    if (node->v.element.tag == GUMBO_TAG_A) {
        GumboAttribute* href = gumbo_get_attribute(&node->v.element.attributes, "href");
        if (href) {
            // Add to URL list
            if (urls->url_count >= urls->url_capacity) {
                urls->url_capacity *= 2;
                urls->urls = realloc(urls->urls, urls->url_capacity * sizeof(char*));
            }
            urls->urls[urls->url_count++] = strdup(href->value);
        }
    }
    
    // Recursively process children
    GumboVector* children = &node->v.element.children;
    for (unsigned int i = 0; i < children->length; i++) {
        extract_links((GumboNode*)children->data[i], urls);
    }
}

URLList* parse_html_for_links(const char* html, size_t length) {
    // Parse HTML
    GumboOutput* output = gumbo_parse_with_options(
        &kGumboDefaultOptions,
        html,
        length
    );
    
    // Initialize URL list
    URLList* urls = malloc(sizeof(URLList));
    urls->url_count = 0;
    urls->url_capacity = 100;
    urls->urls = malloc(urls->url_capacity * sizeof(char*));
    
    // Extract links
    extract_links(output->root, urls);
    
    // Cleanup
    gumbo_destroy_output(&kGumboDefaultOptions, output);
    
    return urls;
}
```

## Selector Strategies

### CSS Selectors vs XPath

**CSS Selectors:**
- Simpler syntax
- Faster for simple queries
- More readable
- Limited functionality

**XPath:**
- More powerful
- Can navigate up the tree (parent, sibling)
- Can use text matching
- More complex syntax

```python
# CSS Selector examples
soup.select('div.content > p')           # Direct children
soup.select('article.post h2')           # Descendants
soup.select('a[href^="http"]')           # Attribute starts with
soup.select('li:nth-child(2)')           # Nth child

# XPath examples
tree.xpath('//div[@class="content"]/p')  # Direct children
tree.xpath('//article[@class="post"]//h2')  # Descendants
tree.xpath('//a[starts-with(@href, "http")]')  # Attribute starts with
tree.xpath('//p[contains(text(), "example")]')  # Text contains
tree.xpath('//a[@href]/parent::div')     # Parent of matching element
```

### Choosing the Right Selector

```python
# Bad: Too general (slow, inaccurate)
links = soup.find_all('a')

# Better: More specific
links = soup.select('div.content a[href^="http"]')

# Best: Most specific, fastest
links = soup.select('#main-content article.post div.body a.external-link')
```

## Optimization Techniques

### 1. Parse Once, Extract Multiple Times

```python
# Bad: Parse multiple times
def extract_titles(html):
    soup = BeautifulSoup(html, 'lxml')  # Parse
    return soup.find_all('h1')

def extract_links(html):
    soup = BeautifulSoup(html, 'lxml')  # Parse again!
    return soup.find_all('a')

# Good: Parse once
def extract_all(html):
    soup = BeautifulSoup(html, 'lxml')  # Parse once
    return {
        'titles': soup.find_all('h1'),
        'links': soup.find_all('a')
    }
```

### 2. Limit Parsing Scope

```python
# Bad: Parse entire page
soup = BeautifulSoup(html, 'lxml')
content = soup.find('div', id='main-content')

# Good: Parse only the section you need
# (if you can isolate it in the HTML string first)
main_content_html = extract_section(html, '<div id="main-content">', '</div>')
soup = BeautifulSoup(main_content_html, 'lxml')
```

### 3. Use Generators for Large Documents

```python
def extract_links_generator(html):
    """
    Yield links one at a time instead of building a list
    Memory efficient for large documents
    """
    soup = BeautifulSoup(html, 'lxml')
    for a_tag in soup.find_all('a', href=True):
        yield {
            'url': a_tag['href'],
            'text': a_tag.get_text(strip=True)
        }

# Usage
for link in extract_links_generator(html):
    process(link)  # Process immediately, don't store all
```

### 4. Compile Complex Selectors

```python
import re

# Bad: Compile regex every time
def extract_emails(text):
    for match in re.finditer(r'[\w\.-]+@[\w\.-]+\.\w+', text):
        yield match.group()

# Good: Compile once
EMAIL_REGEX = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')

def extract_emails(text):
    for match in EMAIL_REGEX.finditer(text):
        yield match.group()
```

### 5. Avoid Text Processing in Loops

```python
# Bad: Multiple calls to strip(), lower() in loop
for a in soup.find_all('a'):
    text = a.get_text().strip().lower()  # Multiple operations
    if 'keyword' in text:
        process(a)

# Good: Minimize operations
for a in soup.find_all('a'):
    text = a.get_text()  # Get once
    if 'keyword' in text.lower():  # Only lower if needed
        process(a)
```

## Handling Malformed HTML

Real-world HTML is often broken. Good parsers handle this gracefully.

```python
def safe_parse(html_text):
    """
    Robust parsing with fallbacks
    """
    # Try lxml first (fast, usually works)
    try:
        from lxml import html as lxml_html
        return lxml_html.fromstring(html_text)
    except Exception as e:
        logging.warning(f"lxml parsing failed: {e}")
    
    # Fallback to BeautifulSoup + lxml
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html_text, 'lxml')
    except Exception as e:
        logging.warning(f"BeautifulSoup+lxml failed: {e}")
    
    # Last resort: html.parser (most tolerant)
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html_text, 'html.parser')
    except Exception as e:
        logging.error(f"All parsing failed: {e}")
        return None
```

## Encoding Detection

HTML encoding can be tricky:

```python
import chardet
from bs4 import UnicodeDammit

def detect_and_decode(raw_bytes, declared_encoding=None):
    """
    Reliably decode HTML bytes to string
    """
    # Try declared encoding first (from HTTP headers or meta tag)
    if declared_encoding:
        try:
            return raw_bytes.decode(declared_encoding)
        except (UnicodeDecodeError, LookupError):
            pass
    
    # Use BeautifulSoup's UnicodeDammit (tries multiple encodings)
    dammit = UnicodeDammit(raw_bytes)
    if dammit.unicode_markup:
        return dammit.unicode_markup
    
    # Fallback to chardet
    detected = chardet.detect(raw_bytes)
    if detected['confidence'] > 0.7:
        try:
            return raw_bytes.decode(detected['encoding'])
        except (UnicodeDecodeError, LookupError):
            pass
    
    # Last resort: Latin-1 (never fails, might be wrong)
    return raw_bytes.decode('latin-1', errors='replace')
```

## Data Extraction Patterns

### Pattern 1: List of Items

```python
def extract_product_list(html):
    """
    Extract structured data from product listing
    """
    soup = BeautifulSoup(html, 'lxml')
    products = []
    
    for item in soup.select('div.product-item'):
        try:
            product = {
                'name': item.select_one('h3.product-name').get_text(strip=True),
                'price': parse_price(item.select_one('span.price').get_text()),
                'url': item.select_one('a.product-link')['href'],
                'image': item.select_one('img.product-image')['src'],
                'rating': float(item.select_one('span.rating')['data-rating']),
                'reviews': int(item.select_one('span.review-count').get_text().split()[0])
            }
            products.append(product)
        except (AttributeError, KeyError, ValueError) as e:
            # Log but continue processing other items
            logging.warning(f"Failed to parse product: {e}")
            continue
    
    return products
```

### Pattern 2: Hierarchical Data

```python
def extract_article_with_comments(html):
    """
    Extract article and nested comments
    """
    soup = BeautifulSoup(html, 'lxml')
    
    article = {
        'title': soup.select_one('h1.article-title').get_text(strip=True),
        'author': soup.select_one('span.author').get_text(strip=True),
        'date': soup.select_one('time')['datetime'],
        'content': soup.select_one('div.article-content').get_text(strip=True),
        'comments': []
    }
    
    def extract_comment(comment_elem, depth=0):
        """Recursively extract nested comments"""
        comment = {
            'author': comment_elem.select_one('span.comment-author').get_text(strip=True),
            'text': comment_elem.select_one('div.comment-text').get_text(strip=True),
            'date': comment_elem.select_one('time')['datetime'],
            'depth': depth,
            'replies': []
        }
        
        # Extract replies
        replies = comment_elem.select('div.comment-reply > div.comment')
        for reply_elem in replies:
            comment['replies'].append(extract_comment(reply_elem, depth + 1))
        
        return comment
    
    # Extract top-level comments
    for comment_elem in soup.select('div#comments > div.comment'):
        article['comments'].append(extract_comment(comment_elem))
    
    return article
```

### Pattern 3: Table Data

```python
def extract_table_data(html):
    """
    Extract data from HTML table
    """
    soup = BeautifulSoup(html, 'lxml')
    table = soup.select_one('table.data-table')
    
    # Extract headers
    headers = [th.get_text(strip=True) for th in table.select('thead th')]
    
    # Extract rows
    rows = []
    for tr in table.select('tbody tr'):
        cells = [td.get_text(strip=True) for td in tr.select('td')]
        row_dict = dict(zip(headers, cells))
        rows.append(row_dict)
    
    return rows
```

## Memory Management

### Streaming Parser for Large Documents

```python
from lxml import etree

def stream_parse_large_html(file_path):
    """
    Parse very large HTML files without loading entire DOM
    """
    context = etree.iterparse(file_path, events=('start', 'end'), html=True)
    
    current_article = {}
    in_article = False
    
    for event, elem in context:
        if event == 'start' and elem.tag == 'article':
            in_article = True
            current_article = {}
        
        elif in_article:
            if elem.tag == 'h1' and event == 'end':
                current_article['title'] = elem.text
            elif elem.tag == 'div' and elem.get('class') == 'content' and event == 'end':
                current_article['content'] = elem.text
        
        if event == 'end' and elem.tag == 'article':
            in_article = False
            yield current_article
            current_article = {}
        
        # Clear element to free memory
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
```

## Testing Parsers

```python
import pytest

def test_extract_links():
    html = '''
    <html>
        <body>
            <a href="http://example.com">Example</a>
            <a href="/relative">Relative</a>
            <a>No href</a>
        </body>
    </html>
    '''
    
    result = extract_links(html)
    
    assert len(result) == 2
    assert result[0]['url'] == 'http://example.com'
    assert result[0]['text'] == 'Example'
    assert result[1]['url'] == '/relative'

def test_extract_malformed_html():
    """Test handling of broken HTML"""
    html = '<html><div><p>Unclosed tags'
    
    result = extract_text(html)
    
    assert result is not None
    assert 'Unclosed tags' in result

def test_extract_missing_elements():
    """Test handling of missing expected elements"""
    html = '<html><body></body></html>'
    
    result = extract_article(html)
    
    # Should return structure with None values, not crash
    assert result['title'] is None
    assert result['content'] is None
```

## Conclusion

**Key Takeaways:**

1. **Choose the right parser for your needs:**
   - BeautifulSoup4: Development, complex HTML
   - lxml: Production, speed + robustness
   - selectolax: Maximum speed, simple extraction

2. **Optimize parsing:**
   - Parse once, extract multiple times
   - Use specific selectors
   - Handle errors gracefully

3. **Handle real-world HTML:**
   - Expect malformed HTML
   - Detect encoding correctly
   - Provide fallbacks

4. **Memory efficiency:**
   - Use generators for large datasets
   - Stream parse huge files
   - Clear parsed elements

**Next Steps:**
- Study `01-crawler-architecture.md` for overall system
- Study `06-javascript-rendering.md` for dynamic content
- Study `10-cuda-acceleration.md` for GPU parsing

## Further Reading

- HTML5 Parsing Algorithm Specification
- lxml documentation and tutorials
- BeautifulSoup4 documentation
- "Web Scraping with Python" by Ryan Mitchell
