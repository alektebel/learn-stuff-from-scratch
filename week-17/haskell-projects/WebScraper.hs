-- Web Scraper in Haskell - Template
-- Build a web scraper to fetch and extract data from web pages
--
-- LEARNING OBJECTIVES:
-- 1. Work with IO monad for side effects (HTTP requests)
-- 2. Parse HTML and extract structured data
-- 3. Handle errors in IO operations
-- 4. Use external libraries (HTTP, HTML parsing)
-- 5. Concurrent requests with async
-- 6. Data extraction with selectors
--
-- ESTIMATED TIME: 6-8 hours for beginners, 4-5 hours for intermediate
--
-- REQUIRED LIBRARIES:
-- Install with: cabal install http-conduit tagsoup text
-- Or add to your .cabal file:
--   build-depends: base, http-conduit, tagsoup, text, async, bytestring

module WebScraper where

import Network.HTTP.Conduit (simpleHttp)
import qualified Data.ByteString.Lazy.Char8 as L
import Text.HTML.TagSoup
import Data.Maybe (mapMaybe, listToMaybe)
import Control.Exception (try, SomeException)

{- |
TODO 1: Define data structures for scraped data

CONCEPT: Modeling Extracted Data
When scraping, we extract specific pieces of information from web pages.
Define data structures to hold the extracted data.

GUIDELINES:
Create types that represent the data you want to extract.
For example, if scraping articles, you might have:
- Title
- Author
- Date
- Content
- URL

For this project, we'll scrape web page data in a generic way.
-}

{- |
Generic link data structure

FIELDS:
- linkText: The text content of the link
- linkHref: The URL the link points to

EXAMPLE:
  Link "Google" "https://google.com"

DERIVING:
- Show: For displaying links
- Eq: For comparing links
-}
data Link = Link
  { linkText :: String
  , linkHref :: String
  } deriving (Show, Eq)

{- |
Generic page data structure

FIELDS:
- pageTitle: The <title> of the page
- pageLinks: All links found on the page
- pageMetadata: Key-value pairs from meta tags

EXAMPLE:
  PageData 
    { pageTitle = "Example Page"
    , pageLinks = [Link "Google" "https://google.com"]
    , pageMetadata = [("description", "An example page")]
    }
-}
data PageData = PageData
  { pageTitle :: String
  , pageLinks :: [Link]
  , pageMetadata :: [(String, String)]
  } deriving (Show, Eq)

{- |
Result type for scraping operations

WHY USE RESULT?
Scraping can fail for various reasons:
- Network errors (connection timeout, DNS failure)
- HTTP errors (404, 500)
- Parsing errors (malformed HTML)

Using Either allows us to handle errors gracefully.

LEFT: Error message (String)
RIGHT: Successful result
-}
type ScraperResult a = Either String a

{- |
TODO 2: Implement HTTP fetching

CONCEPT: Making HTTP Requests in Haskell
To scrape web pages, we first need to fetch them over HTTP.
The IO monad handles side effects like network requests.

APPROACH:
Use the http-conduit library (already imported as simpleHttp)
-}

{- |
Fetch a web page from a URL

PURPOSE: Download HTML content from a URL

APPROACH:
1. Use simpleHttp from http-conduit library
   - simpleHttp :: String -> IO ByteString
2. Convert ByteString to String for easier processing
   - Use L.unpack or similar
3. Handle exceptions:
   - Network might be down
   - URL might be invalid
   - Server might return error
4. Wrap in try to catch exceptions
   - try :: IO a -> IO (Either SomeException a)

RETURN TYPE: IO (ScraperResult String)
- Returns IO because network operations are side effects
- ScraperResult (Either String String) for error handling
- String is the HTML content on success

IMPLEMENTATION STEPS:
1. Use try to catch exceptions:
   result <- try (simpleHttp url) :: IO (Either SomeException ByteString)
2. Handle the result:
   - If Left exception: Return Left with error message
   - If Right bytes: Convert to String and return Right

EXAMPLES:
  fetchPage "https://example.com" 
  → IO (Right "<html>...</html>")
  
  fetchPage "https://invalid-url-xyz.com"
  → IO (Left "Network error: ...")

ERROR HANDLING:
- Catch all exceptions and convert to error messages
- Use show to convert exception to String
- Prefix with descriptive message like "Failed to fetch: "

HINTS:
- try :: Exception e => IO a -> IO (Either e a)
- simpleHttp :: String -> IO ByteString
- L.unpack :: ByteString -> String
- case for pattern matching on Either
-}
fetchPage :: String -> IO (ScraperResult String)
fetchPage url = undefined  -- TODO: Implement

{- |
TODO 3: Implement HTML parsing with TagSoup

CONCEPT: HTML Parsing with TagSoup
TagSoup is a library that parses HTML into a list of tags.
It's very lenient and handles malformed HTML gracefully.

TAG TYPES:
- TagOpen "tag" [("attr", "value"), ...]: Opening tag
- TagClose "tag": Closing tag
- TagText "text": Text content between tags
- TagComment "comment": HTML comments

EXAMPLE:
  parseTags "<a href='example.com'>Click</a>"
  → [ TagOpen "a" [("href","example.com")]
    , TagText "Click"
    , TagClose "a"
    ]
-}

{- |
Extract all links from HTML

PURPOSE: Find all <a> tags and extract href and text

APPROACH:
1. Parse HTML into tags using parseTags
   - parseTags :: String -> [Tag String]
2. Filter for anchor tags (TagOpen "a" attrs)
3. For each anchor:
   a. Extract href attribute
   b. Find following text content
   c. Create Link record
4. Return list of Links

FINDING HREF:
Use fromAttrib function from TagSoup:
  fromAttrib "href" tag
This extracts the href attribute value from a tag.

FINDING TEXT:
After an opening <a> tag, find the next TagText.
Use functions like:
  - innerText :: [Tag String] -> String (gets text inside tags)
  - Or manually find next TagText

FILTERING:
Use list comprehension or map/filter/mapMaybe

IMPLEMENTATION HINT:
  let tags = parseTags html
      links = [...]  -- Extract links from tags
  in links

EXAMPLE:
  extractLinks "<a href='google.com'>Google</a><a href='yahoo.com'>Yahoo</a>"
  → [Link "Google" "google.com", Link "Yahoo" "yahoo.com"]

EDGE CASES:
- Links without href attribute (skip them or use empty string)
- Links without text content (use empty string)
- Nested tags inside <a> (extract inner text)

TAGSOUP UTILITIES:
- parseTags :: String -> [Tag String]
- fromAttrib :: String -> Tag String -> String
- innerText :: [Tag String] -> String
- partitions :: (Tag String -> Bool) -> [Tag String] -> [[Tag String]]
-}
extractLinks :: String -> [Link]
extractLinks html = []  -- TODO: Implement

{- |
Extract page title from HTML

PURPOSE: Find the <title> tag and extract its content

APPROACH:
1. Parse HTML into tags
2. Find the <title> tag
3. Extract text between <title> and </title>
4. Return title or empty string if not found

IMPLEMENTATION:
Use TagSoup functions:
  - parseTags to get tag list
  - Find TagOpen "title" []
  - Get next TagText
  - Extract the text content

HELPER FUNCTIONS:
  - sections :: (Tag String -> Bool) -> [Tag String] -> [[Tag String]]
    Groups tags by a predicate
  - innerText :: [Tag String] -> String
    Extracts text content from tag sequence

EXAMPLE:
  extractTitle "<html><head><title>My Page</title></head></html>"
  → "My Page"
  
  extractTitle "<html><head></head></html>"
  → ""

IMPLEMENTATION TIP:
  let tags = parseTags html
      titleSection = sections (~== TagOpen "title" []) tags
  in case titleSection of
    (t:_) -> innerText t
    [] -> ""

WHERE ~== is TagSoup's tag equality operator that ignores attributes.
-}
extractTitle :: String -> String
extractTitle html = ""  -- TODO: Implement

{- |
Extract metadata from <meta> tags

PURPOSE: Extract key-value pairs from meta tags
Meta tags provide metadata about the HTML document.

META TAG FORMAT:
  <meta name="description" content="A description of the page">
  <meta property="og:title" content="Social Media Title">

APPROACH:
1. Parse HTML into tags
2. Find all TagOpen "meta" attrs
3. For each meta tag:
   a. Get "name" or "property" attribute (key)
   b. Get "content" attribute (value)
   c. Create (key, value) pair
4. Return list of pairs

IMPLEMENTATION:
Filter tags for meta tags, then extract attributes:
  let tags = parseTags html
      metaTags = [tag | tag@(TagOpen "meta" _) <- tags]
      metadata = map extractMetaPair metaTags
  in metadata

HELPER FUNCTION:
  extractMetaPair :: Tag String -> (String, String)
  extractMetaPair tag = 
    let key = fromAttrib "name" tag `orElse` fromAttrib "property" tag
        value = fromAttrib "content" tag
    in (key, value)

WHERE orElse means: use first attribute if present, otherwise use second.

EXAMPLE:
  extractMetadata "<meta name='description' content='Hello'>"
  → [("description", "Hello")]

EDGE CASES:
- Meta tags without name/property (skip or use empty key)
- Meta tags without content (use empty value)
-}
extractMetadata :: String -> [(String, String)]
extractMetadata html = []  -- TODO: Implement

{- |
TODO 4: Implement complete page scraping

CONCEPT: Combining Extraction Functions
Combine fetching and parsing into a complete scraping function.
-}

{- |
Scrape a complete web page

PURPOSE: Fetch and parse a web page into PageData

APPROACH:
1. Fetch the page HTML using fetchPage
2. If fetch succeeds:
   a. Extract title using extractTitle
   b. Extract links using extractLinks
   c. Extract metadata using extractMetadata
   d. Combine into PageData
3. If fetch fails, propagate error

IMPLEMENTATION WITH DO-NOTATION:
  scrapePage url = do
    htmlResult <- fetchPage url
    case htmlResult of
      Left err -> return (Left err)
      Right html -> 
        let title = extractTitle html
            links = extractLinks html
            metadata = extractMetadata html
            pageData = PageData title links metadata
        in return (Right pageData)

ALTERNATIVE (Using Either as a Functor):
  scrapePage url = do
    htmlResult <- fetchPage url
    return $ case htmlResult of
      Left err -> Left err
      Right html -> Right $ PageData
        (extractTitle html)
        (extractLinks html)
        (extractMetadata html)

RETURN TYPE: IO (ScraperResult PageData)

EXAMPLE:
  scrapePage "https://example.com"
  → IO (Right PageData { pageTitle = "Example", ... })
-}
scrapePage :: String -> IO (ScraperResult PageData)
scrapePage url = undefined  -- TODO: Implement

{- |
TODO 5: Implement filtered scraping

CONCEPT: Selective Data Extraction
Sometimes we only want specific data, not everything.
Implement functions to extract specific information.
-}

{- |
Get only external links (starting with http:// or https://)

PURPOSE: Filter links to only include external URLs

APPROACH:
1. Scrape the page normally
2. Filter pageLinks to only include external links
3. An external link's href starts with "http://" or "https://"

IMPLEMENTATION:
  getExternalLinks url = do
    result <- scrapePage url
    return $ case result of
      Left err -> Left err
      Right pageData -> Right $ filter isExternal (pageLinks pageData)
    where
      isExternal link = 
        "http://" `isPrefixOf` linkHref link ||
        "https://" `isPrefixOf` linkHref link

RETURN TYPE: IO (ScraperResult [Link])

EXAMPLE:
  getExternalLinks "https://example.com"
  → IO (Right [Link "Google" "https://google.com", ...])
-}
getExternalLinks :: String -> IO (ScraperResult [Link])
getExternalLinks url = undefined  -- TODO: Implement

{- |
Find links matching a pattern

PURPOSE: Extract links whose text or href matches a pattern

APPROACH:
1. Scrape the page
2. Filter links based on pattern matching
3. Pattern can match either link text or href

PARAMETERS:
- pattern: String to search for
- url: URL to scrape

IMPLEMENTATION:
Use isInfixOf to check if pattern is contained in text or href:
  import Data.List (isInfixOf)
  
  matchesPattern pattern link =
    pattern `isInfixOf` linkText link ||
    pattern `isInfixOf` linkHref link

RETURN TYPE: IO (ScraperResult [Link])

EXAMPLE:
  findLinks "github" "https://example.com"
  → IO (Right [Link "GitHub" "https://github.com/...", ...])
-}
findLinks :: String -> String -> IO (ScraperResult [Link])
findLinks pattern url = undefined  -- TODO: Implement

{- |
TODO 6: Implement concurrent scraping

CONCEPT: Scraping Multiple Pages Concurrently
When scraping many pages, doing them one by one is slow.
Use Haskell's async library to scrape multiple pages concurrently.

LIBRARY:
  import Control.Concurrent.Async (mapConcurrently, async, wait)
-}

{- |
Scrape multiple pages concurrently

PURPOSE: Scrape a list of URLs in parallel

APPROACH:
1. Use mapConcurrently to run scrapePage on each URL
2. Each scrape runs in its own thread
3. Collect all results
4. Return list of results

IMPLEMENTATION:
  import Control.Concurrent.Async (mapConcurrently)
  
  scrapePages urls = do
    results <- mapConcurrently scrapePage urls
    return results

RETURN TYPE: IO [ScraperResult PageData]
Returns a list of results, one for each URL.
Some may be errors (Left) and some successes (Right).

EXAMPLE:
  scrapePages ["https://example.com", "https://google.com"]
  → IO [Right PageData {...}, Right PageData {...}]

BENEFITS:
- Much faster than sequential scraping
- Handles many URLs efficiently
- Each request runs independently

NOTES:
- Be respectful of target servers (don't DOS them)
- Consider rate limiting for production use
- Some servers may block concurrent requests
-}
scrapePages :: [String] -> IO [ScraperResult PageData]
scrapePages urls = undefined  -- TODO: Implement

{- |
Scrape and extract all unique links from multiple pages

PURPOSE: Collect all unique links from multiple pages

APPROACH:
1. Scrape all pages concurrently
2. Extract links from successful results
3. Remove duplicates
4. Return unique list of links

IMPLEMENTATION:
  scrapeAllLinks urls = do
    results <- scrapePages urls
    let successfulPages = [page | Right page <- results]
        allLinks = concatMap pageLinks successfulPages
        uniqueLinks = nub allLinks  -- nub removes duplicates
    return uniqueLinks

IMPORT:
  import Data.List (nub)

RETURN TYPE: IO [Link]

EXAMPLE:
  scrapeAllLinks ["https://example.com", "https://test.com"]
  → IO [Link "Google" "https://google.com", Link "Yahoo" "...", ...]
-}
scrapeAllLinks :: [String] -> IO [Link]
scrapeAllLinks urls = undefined  -- TODO: Implement

{- |
TODO 7: Implement structured data extraction

CONCEPT: Extracting Specific Structures
Often we want to extract specific patterns from pages,
like all articles, products, or user profiles.
-}

{- |
Extract items matching a CSS-like selector pattern

PURPOSE: Find HTML elements matching a selector

NOTE: This is a simplified selector implementation.
Real CSS selectors are more complex. This handles basic cases:
- Tag name: "div"
- Class: ".className"
- ID: "#idName"

APPROACH:
1. Parse selector to understand what to find
2. Filter tags based on selector
3. Extract relevant data from matched tags

FOR TAG SELECTOR:
  Find all TagOpen with matching tag name

FOR CLASS SELECTOR (.className):
  Find tags with class attribute containing className

FOR ID SELECTOR (#idName):
  Find tag with id attribute equal to idName

IMPLEMENTATION HINT:
  selectElements selector html =
    let tags = parseTags html
    in case selector of
      ('.':className) -> findByClass className tags
      ('#':idName) -> findById idName tags
      tagName -> findByTag tagName tags

WHERE:
  findByClass :: String -> [Tag String] -> [[Tag String]]
  findByTag :: String -> [Tag String] -> [[Tag String]]
  findById :: String -> [Tag String] -> [[Tag String]]

RETURN: List of tag sequences matching selector

EXAMPLE:
  selectElements "a" html → All <a> tags
  selectElements ".article" html → All tags with class "article"
  selectElements "#main" html → Tag with id "main"

NOTE: For production use, consider libraries like:
- scalpel
- taggy-lens
- xml-conduit with html-conduit
-}
selectElements :: String -> String -> [[Tag String]]
selectElements selector html = []  -- TODO: Implement

{- |
TESTING FUNCTIONS
-}

-- Test scraping a single page
testSinglePage :: IO ()
testSinglePage = do
  putStrLn "Testing single page scraping...\n"
  result <- scrapePage "https://example.com"
  case result of
    Left err -> putStrLn $ "Error: " ++ err
    Right pageData -> do
      putStrLn $ "Title: " ++ pageTitle pageData
      putStrLn $ "Links found: " ++ show (length (pageLinks pageData))
      putStrLn $ "Metadata entries: " ++ show (length (pageMetadata pageData))
      putStrLn "\nFirst 5 links:"
      mapM_ (putStrLn . show) (take 5 $ pageLinks pageData)

-- Test concurrent scraping
testConcurrent :: IO ()
testConcurrent = do
  putStrLn "\nTesting concurrent scraping...\n"
  let urls = ["https://example.com", "https://example.org", "https://example.net"]
  results <- scrapePages urls
  putStrLn $ "Scraped " ++ show (length results) ++ " pages"
  let successful = length [r | Right _ <- results]
  putStrLn $ "Successful: " ++ show successful
  let failed = length [r | Left _ <- results]
  putStrLn $ "Failed: " ++ show failed

-- Main function
main :: IO ()
main = do
  putStrLn "=== Web Scraper Tests ===\n"
  testSinglePage
  -- Uncomment to test concurrent scraping
  -- testConcurrent

{- |
=============================================================================
COMPREHENSIVE IMPLEMENTATION GUIDE
=============================================================================

OVERVIEW:
This web scraper project teaches you how to work with IO, external libraries,
and real-world data extraction in Haskell. You'll learn to handle side effects,
parse HTML, and work with concurrent operations.

PREREQUISITES:
- Understanding of IO monad
- Basic knowledge of do-notation
- Familiarity with Either for error handling
- Comfortable with list processing

LIBRARY INSTALLATION:
Before starting, install required packages:
  cabal update
  cabal install http-conduit tagsoup text async bytestring

Or create a .cabal file with dependencies.

STEP-BY-STEP IMPLEMENTATION ROADMAP:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1: UNDERSTANDING DATA STRUCTURES (30 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1.1: Review Link and PageData types
  □ Understand what data we're extracting
  □ These are already defined for you
  □ Think about what other fields might be useful

Step 1.2: Understand ScraperResult
  □ It's just a type alias for Either String a
  □ Used consistently for error handling
  □ Left String = error message
  □ Right a = successful result

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2: HTTP FETCHING (1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 2.1: Understand simpleHttp
  □ Already imported from Network.HTTP.Conduit
  □ Type: simpleHttp :: String -> IO ByteString
  □ Fetches URL and returns content
  □ Can throw exceptions!

Step 2.2: Implement fetchPage (TODO 2)
  □ Use try to catch exceptions
  □ Convert ByteString to String
  □ Return Either String String
  □ Test with:
    - Valid URL: "https://example.com"
    - Invalid URL: "https://xyz-invalid-xyz.com"

Step 2.3: Test in GHCi
  > fetchPage "https://example.com"
  Should return IO (Right "<html>...")

DEBUGGING TIPS:
- If you get connection errors, check internet connection
- Some URLs might require user agent headers (advanced)
- Use shorter URLs for testing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3: HTML PARSING BASICS (2 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 3.1: Learn TagSoup basics
  □ Read TagSoup documentation
  □ Test parseTags in GHCi:
    > parseTags "<a href='test'>Link</a>"
  □ Understand Tag types:
    - TagOpen String [(String, String)]
    - TagClose String
    - TagText String

Step 3.2: Implement extractLinks (TODO 3)
  □ Parse HTML with parseTags
  □ Find all TagOpen "a" attrs
  □ Extract href with fromAttrib
  □ Find following text
  □ Create Link records
  □ Test with simple HTML strings

Step 3.3: Implement extractTitle (TODO 3)
  □ Use parseTags
  □ Find title tag
  □ Extract inner text
  □ Test with: "<title>My Title</title>"

Step 3.4: Implement extractMetadata (TODO 3)
  □ Find all meta tags
  □ Extract name/property and content attributes
  □ Create key-value pairs
  □ Test with meta tag examples

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 4: COMPLETE PAGE SCRAPING (1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 4.1: Implement scrapePage (TODO 4)
  □ Call fetchPage
  □ On success, call extraction functions
  □ Combine into PageData
  □ Handle errors properly

Step 4.2: Test complete scraping
  □ Try with real URLs:
    - https://example.com
    - https://github.com
  □ Verify all data extracted correctly

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 5: FILTERED SCRAPING (1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 5.1: Implement getExternalLinks (TODO 5)
  □ Scrape page normally
  □ Filter for http:// or https:// links
  □ Return filtered list

Step 5.2: Implement findLinks (TODO 5)
  □ Scrape page
  □ Filter by pattern matching
  □ Use isInfixOf for substring matching

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 6: CONCURRENT SCRAPING (1-2 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 6.1: Learn async basics
  □ Read async documentation
  □ Understand mapConcurrently

Step 6.2: Implement scrapePages (TODO 6)
  □ Use mapConcurrently scrapePage urls
  □ Test with multiple URLs
  □ Observe speed improvement

Step 6.3: Implement scrapeAllLinks (TODO 6)
  □ Call scrapePages
  □ Extract and combine all links
  □ Remove duplicates with nub

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 7: ADVANCED SELECTORS (Optional, 2+ hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 7.1: Implement basic selectElements (TODO 7)
  □ Handle tag selectors
  □ Handle class selectors
  □ Handle ID selectors
  □ This is challenging! Take your time.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY HASKELL CONCEPTS DEMONSTRATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. IO MONAD:
   - Managing side effects
   - Sequencing IO operations
   - Combining IO with pure functions

2. ERROR HANDLING:
   - Either for error reporting
   - Exception handling with try
   - Propagating errors through IO

3. EXTERNAL LIBRARIES:
   - http-conduit for HTTP
   - TagSoup for HTML parsing
   - async for concurrency

4. CONCURRENCY:
   - Parallel execution
   - Thread management
   - Collecting concurrent results

5. DATA EXTRACTION:
   - Pattern matching on tags
   - Filtering and transforming data
   - Building structured output

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMON PITFALLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. NOT HANDLING EXCEPTIONS:
   Problem: Program crashes on network errors
   Solution: Always use try to catch exceptions

2. FORGETTING TO SKIP WHITESPACE:
   Problem: Links have extra whitespace
   Solution: Trim strings after extraction

3. EXCESSIVE CONCURRENT REQUESTS:
   Problem: Target server blocks you
   Solution: Limit concurrency or add delays

4. RELATIVE URLs:
   Problem: Links like "/about" not complete
   Solution: Convert relative to absolute URLs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXTENSIONS FOR FURTHER LEARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. RATE LIMITING:
   - Limit requests per second
   - Avoid overwhelming servers
   - Use Control.Concurrent.threadDelay

2. USER AGENTS:
   - Set custom user agent headers
   - Required by some websites
   - Use http-conduit's full API

3. COOKIE HANDLING:
   - Maintain session cookies
   - Handle login/authentication
   - Use CookieJar from http-client

4. JAVASCRIPT RENDERING:
   - Some pages require JavaScript
   - Use external tools like Selenium
   - Or headless browsers

5. DATA PERSISTENCE:
   - Save scraped data to database
   - Export to JSON/CSV
   - Cache fetched pages

6. ROBOTS.TXT:
   - Check robots.txt before scraping
   - Respect crawl delays
   - Be a good internet citizen

7. BETTER SELECTORS:
   - Full CSS selector support
   - XPath support
   - Use scalpel or lens libraries

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETHICAL CONSIDERATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Web scraping can be controversial. Follow these guidelines:

1. RESPECT ROBOTS.TXT:
   - Check /robots.txt on target site
   - Honor crawl delays
   - Respect disallowed paths

2. RATE LIMITING:
   - Don't overwhelm servers
   - Add delays between requests
   - Limit concurrent connections

3. TERMS OF SERVICE:
   - Read and follow site ToS
   - Some sites prohibit scraping
   - Get permission when needed

4. ATTRIBUTION:
   - Credit data sources
   - Don't claim scraped data as your own
   - Follow licensing requirements

5. PRIVACY:
   - Don't scrape personal information
   - Follow GDPR and privacy laws
   - Respect user privacy

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESOURCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Libraries:
- http-conduit: HTTP client
- tagsoup: HTML parsing
- scalpel: High-level scraping
- async: Concurrent operations

Documentation:
- TagSoup tutorial: https://wiki.haskell.org/TagSoup
- http-conduit guide: Hackage documentation
- async examples: Hackage documentation

Books:
- "Parallel and Concurrent Programming in Haskell"
- "Real World Haskell" - Chapter 24 (Parsing)

-}
