-- Web Scraper in Haskell - Solution Template
-- This is a reference implementation showing the structure
--
-- NOTE: This is a template showing what the solution should contain.
-- The actual detailed implementation would be filled in by students
-- or provided as a complete reference solution.

module WebScraper where

import Network.HTTP.Conduit (simpleHttp)
import qualified Data.ByteString.Lazy.Char8 as L
import Text.HTML.TagSoup
import Data.Maybe (mapMaybe, listToMaybe)
import Data.List (isInfixOf, isPrefixOf, nub)
import Control.Exception (try, SomeException)
import Control.Concurrent.Async (mapConcurrently)  -- For concurrent scraping

-- Data structures
data Link = Link
  { linkText :: String
  , linkHref :: String
  } deriving (Show, Eq)

data PageData = PageData
  { pageTitle :: String
  , pageLinks :: [Link]
  , pageMetadata :: [(String, String)]
  } deriving (Show, Eq)

type ScraperResult a = Either String a

-- Fetch a web page
fetchPage :: String -> IO (ScraperResult String)
fetchPage url = do
  result <- try (simpleHttp url) :: IO (Either SomeException L.ByteString)
  case result of
    Left exc -> return $ Left $ "Failed to fetch: " ++ show exc
    Right bytes -> return $ Right $ L.unpack bytes

-- Extract links from HTML
extractLinks :: String -> [Link]
extractLinks html = 
  let tags = parseTags html
      linkTags = [tag | tag@(TagOpen "a" _) <- tags]
      -- Implementation would extract href and text for each link
  in []  -- Placeholder

-- Extract page title
extractTitle :: String -> String
extractTitle html = 
  let tags = parseTags html
      -- Implementation would find <title> tag and extract inner text
  in ""  -- Placeholder

-- Extract metadata from meta tags
extractMetadata :: String -> [(String, String)]
extractMetadata html = 
  let tags = parseTags html
      -- Implementation would find all <meta> tags and extract name/content
  in []  -- Placeholder

-- Scrape a complete page
scrapePage :: String -> IO (ScraperResult PageData)
scrapePage url = do
  htmlResult <- fetchPage url
  case htmlResult of
    Left err -> return $ Left err
    Right html -> 
      let title = extractTitle html
          links = extractLinks html
          metadata = extractMetadata html
          pageData = PageData title links metadata
      in return $ Right pageData

-- Get only external links
getExternalLinks :: String -> IO (ScraperResult [Link])
getExternalLinks url = do
  result <- scrapePage url
  return $ case result of
    Left err -> Left err
    Right pageData -> 
      Right $ filter isExternal (pageLinks pageData)
  where
    isExternal link = 
      "http://" `isPrefixOf` linkHref link ||
      "https://" `isPrefixOf` linkHref link

-- Find links matching a pattern
findLinks :: String -> String -> IO (ScraperResult [Link])
findLinks pattern url = do
  result <- scrapePage url
  return $ case result of
    Left err -> Left err
    Right pageData -> 
      Right $ filter (matchesPattern pattern) (pageLinks pageData)
  where
    matchesPattern pat link =
      pat `isInfixOf` linkText link ||
      pat `isInfixOf` linkHref link

-- Scrape multiple pages concurrently
scrapePages :: [String] -> IO [ScraperResult PageData]
scrapePages urls = 
  -- Full implementation would use: mapConcurrently scrapePage urls
  -- This shows the correct approach:
  mapConcurrently scrapePage urls

-- Scrape and extract all unique links
scrapeAllLinks :: [String] -> IO [Link]
scrapeAllLinks urls = do
  results <- scrapePages urls
  let successfulPages = [page | Right page <- results]
      allLinks = concatMap pageLinks successfulPages
      uniqueLinks = nub allLinks
  return uniqueLinks

-- Simplified selector matching
selectElements :: String -> String -> [[Tag String]]
selectElements selector html = 
  let tags = parseTags html
      -- Implementation would match based on selector type
  in []  -- Placeholder

-- Testing function
testSinglePage :: IO ()
testSinglePage = do
  putStrLn "Testing single page scraping (placeholder)..."
  putStrLn "Full implementation would fetch and parse actual web pages"

-- Main function
main :: IO ()
main = do
  putStrLn "=== Web Scraper - Solution Template ==="
  putStrLn ""
  putStrLn "Complete implementation would include:"
  putStrLn "- Full HTTP fetching with error handling"
  putStrLn "- Comprehensive HTML parsing with TagSoup"
  putStrLn "- Link, title, and metadata extraction"
  putStrLn "- Concurrent multi-page scraping"
  putStrLn "- Pattern matching and filtering"
  putStrLn "- CSS-like selector support"
  putStrLn ""
  putStrLn "Example usage:"
  putStrLn "  result <- scrapePage \"https://example.com\""
  putStrLn "  links <- getExternalLinks \"https://example.com\""
  putStrLn "  matches <- findLinks \"github\" \"https://example.com\""

{-
SOLUTION NOTES:

This template shows the structure of the complete solution.
A full implementation would include:

1. Robust HTTP fetching with error handling
2. Complete HTML parsing using TagSoup:
   - Extract links with href and text content
   - Find title tag and extract inner text
   - Extract meta tags (name/property and content)
3. Concurrent scraping with async library
4. Pattern-based filtering and searching
5. CSS-like selector support (simplified)
6. Proper error handling throughout
7. Rate limiting (for ethical scraping)
8. User agent handling

The implementation would be approximately 250-300 lines
with proper error handling and real-world considerations.

ETHICAL CONSIDERATIONS:
- Always check robots.txt
- Implement rate limiting
- Respect website ToS
- Don't overwhelm servers
- Cache when appropriate
-}
