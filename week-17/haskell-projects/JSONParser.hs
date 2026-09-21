-- JSON Parser in Haskell - Template
-- Build a complete JSON parser from scratch to understand recursive data structures
--
-- LEARNING OBJECTIVES:
-- 1. Model nested data structures with algebraic data types
-- 2. Parse strings with escape sequences and Unicode
-- 3. Handle recursive parsing for nested objects and arrays
-- 4. Work with multiple data types (strings, numbers, booleans, null)
-- 5. Pretty-print structured data
--
-- ESTIMATED TIME: 6-8 hours for beginners, 3-4 hours for intermediate

module JSONParser where

import Data.Char (isDigit, isSpace, ord, chr)
import Data.List (intercalate)
import Numeric (readHex)

{- |
TODO 1: Define the JSON value data type

CONCEPT: JSON Data Structure
JSON supports the following value types:
- Null: represents absence of value
- Boolean: true or false
- Number: integers and floating-point numbers
- String: text enclosed in quotes with escape sequences
- Array: ordered list of values [1, 2, 3]
- Object: key-value pairs {"name": "John", "age": 30}

GUIDELINES:
Define an algebraic data type called JSONValue with constructors for each JSON type.

STRUCTURE TO IMPLEMENT:
- JSONNull: Represents JSON null
  Example: null in JSON

- JSONBool Bool: Represents JSON boolean
  Example: true or false
  Storage: Haskell Bool value

- JSONNumber Double: Represents JSON number
  Example: 42, 3.14, -17, 2.5e10
  Note: Use Double to support both integers and floating-point

- JSONString String: Represents JSON string
  Example: "hello", "world\n", "Unicode: \u0041"
  Storage: Haskell String (already unescaped)

- JSONArray [JSONValue]: Represents JSON array
  Example: [1, "hello", true, null]
  Storage: List of JSONValue (recursively defined!)

- JSONObject [(String, JSONValue)]: Represents JSON object
  Example: {"name": "John", "age": 30}
  Storage: Association list of (key, value) pairs
  Note: Keys are always strings in JSON

WHY RECURSIVE?
JSONArray and JSONObject contain JSONValue, which can be arrays or objects themselves.
This allows representing deeply nested structures like:
  {"users": [{"name": "Alice", "scores": [95, 87, 92]}]}

DERIVING CLAUSES:
- Show: For printing JSON values
- Eq: For comparing JSON values

EXAMPLES OF REPRESENTATION:
  JSONNull                                    -- null
  JSONBool True                               -- true
  JSONNumber 42.0                             -- 42
  JSONString "hello"                          -- "hello"
  JSONArray [JSONNumber 1, JSONNumber 2]      -- [1, 2]
  JSONObject [("name", JSONString "Alice")]   -- {"name": "Alice"}
-}
data JSONValue 
  = JSONNull
  | JSONBool Bool
  | JSONNumber Double
  | JSONString String
  | JSONArray [JSONValue]
  | JSONObject [(String, JSONValue)]
  deriving (Show, Eq)

{- |
TODO 2: Implement JSON string parsing

CONCEPT: String Parsing with Escape Sequences
JSON strings are enclosed in double quotes and support escape sequences:
- \" → " (quotation mark)
- \\ → \ (backslash)
- \/ → / (forward slash)
- \b → backspace
- \f → form feed
- \n → newline
- \r → carriage return
- \t → tab
- \uXXXX → Unicode character (4 hex digits)

PARSING STRATEGY:
1. Expect opening " character
2. Parse characters until closing " is found
3. Handle escape sequences when encountering \
4. Accumulate characters into a string
5. Return the parsed string and remaining input
-}

-- Helper: Skip whitespace
skipSpace :: String -> String
skipSpace = dropWhile isSpace
-- TODO: This is already implemented for you

{- |
Parse a single escaped character

APPROACH:
After encountering \, the next character determines the escape:
- 'n' → '\n'
- 't' → '\t'
- 'r' → '\r'
- 'b' → '\b' (backspace, chr 8)
- 'f' → '\f' (form feed, chr 12)
- '"' → '"'
- '\\' → '\\'
- '/' → '/'
- 'u' → Parse 4 hex digits and convert to Unicode character

FOR UNICODE (\uXXXX):
1. Take next 4 characters
2. Verify they are all hex digits (0-9, a-f, A-F)
3. Use readHex to convert to integer
4. Use chr to convert integer to character

RETURN TYPE: Maybe (Char, String)
- Just (char, remaining): Successfully parsed escape sequence
- Nothing: Invalid escape sequence

EXAMPLES:
  parseEscape "n rest" → Just ('\n', " rest")
  parseEscape "u0041 rest" → Just ('A', " rest")
  parseEscape "x invalid" → Nothing

HINT: Use pattern matching on the first character after \
-}
parseEscape :: String -> Maybe (Char, String)
parseEscape s = Nothing  -- TODO: Implement

{- |
Parse characters inside a JSON string

APPROACH:
Accumulate characters until reaching the closing quote or an error.

ALGORITHM:
1. If current char is '"', return accumulated string (done)
2. If current char is '\', parse escape sequence:
   a. If successful, add escaped char to accumulator and continue
   b. If failed, return Nothing (invalid escape)
3. If current char is any other character:
   a. Add it to accumulator and continue
4. If string ends without closing quote, return Nothing

PARAMETERS:
- acc: Accumulated characters so far (start with empty string)
- s: Remaining input string

RETURN TYPE: Maybe (String, String)
- Just (parsed_string, remaining): Successfully parsed
- Nothing: Parse error (invalid escape or unclosed string)

IMPLEMENTATION TIP:
Use a helper function with an accumulator parameter that builds the string
as you traverse the input.

EXAMPLES:
  parseStringChars "" "hello\" rest" → Just ("hello", " rest")
  parseStringChars "" "hi\\nworld\" x" → Just ("hi\nworld", " x")
  parseStringChars "" "unclosed → Nothing
-}
parseStringChars :: String -> String -> Maybe (String, String)
parseStringChars acc s = Nothing  -- TODO: Implement

{- |
Main JSON string parser

APPROACH:
1. Skip leading whitespace
2. Verify first character is '"'
3. Call parseStringChars to parse the content
4. Return parsed string wrapped in JSONString

RETURN TYPE: Maybe (JSONValue, String)

EXAMPLES:
  parseString "\"hello\"" → Just (JSONString "hello", "")
  parseString "\"hello\" rest" → Just (JSONString "hello", " rest")
  parseString "\"line1\\nline2\"" → Just (JSONString "line1\nline2", "")
  parseString "no quotes" → Nothing
-}
parseString :: String -> Maybe (JSONValue, String)
parseString s = Nothing  -- TODO: Implement

{- |
TODO 3: Implement JSON number parsing

CONCEPT: Number Formats
JSON numbers can be:
- Integers: 42, -17, 0
- Floating-point: 3.14, -0.5, 2.718
- Scientific notation: 1e10, 2.5e-3, 1E+5

GRAMMAR:
number = [minus] int [frac] [exp]
- minus: optional '-'
- int: digit or (digit1-9 digits)
- frac: '.' digits
- exp: ('e' | 'E') ['+' | '-'] digits

PARSING STRATEGY:
1. Check for optional minus sign
2. Parse integer part (at least one digit required)
3. Check for optional decimal point and fractional part
4. Check for optional exponent (e or E) with optional sign and digits
5. Combine all parts and use read to convert to Double
6. Wrap in JSONNumber

EDGE CASES:
- Leading zeros not allowed except for "0" itself
- Must have at least one digit
- Exponent must have at least one digit

EXAMPLES:
  parseNumber "42" → Just (JSONNumber 42.0, "")
  parseNumber "-3.14" → Just (JSONNumber (-3.14), "")
  parseNumber "2.5e10 rest" → Just (JSONNumber 2.5e10, " rest")
  parseNumber "0.5" → Just (JSONNumber 0.5, "")
  parseNumber "00" → Nothing (leading zero not allowed)

IMPLEMENTATION TIP:
Build the number string character by character, then use read to convert:
1. Collect all valid number characters into a string
2. Verify the format is valid
3. Use read :: String -> Double to parse
4. Return JSONNumber with the parsed value
-}
parseNumber :: String -> Maybe (JSONValue, String)
parseNumber s = Nothing  -- TODO: Implement

{- |
TODO 4: Implement parsing for null and boolean values

CONCEPT: Keyword Parsing
JSON has three keyword literals:
- null: represents absence of value
- true: boolean true
- false: boolean false

PARSING STRATEGY:
Simple pattern matching on the beginning of the string.
-}

{- |
Parse JSON null

APPROACH:
1. Skip leading whitespace
2. Check if input starts with "null"
3. If yes, consume "null" and return JSONNull
4. If no, return Nothing

RETURN TYPE: Maybe (JSONValue, String)

EXAMPLES:
  parseNull "null" → Just (JSONNull, "")
  parseNull "null rest" → Just (JSONNull, " rest")
  parseNull "nul" → Nothing
  parseNull "nullable" → Nothing (must be exact word)

HINT: Use a helper that checks if a string starts with a prefix
-}
parseNull :: String -> Maybe (JSONValue, String)
parseNull s = Nothing  -- TODO: Implement

{- |
Parse JSON boolean

APPROACH:
1. Skip leading whitespace
2. Check if input starts with "true" or "false"
3. Consume the matched keyword
4. Return appropriate JSONBool value

RETURN TYPE: Maybe (JSONValue, String)

EXAMPLES:
  parseBool "true" → Just (JSONBool True, "")
  parseBool "false rest" → Just (JSONBool False, " rest")
  parseBool "truth" → Nothing (must be exact word)

IMPLEMENTATION TIP:
Try matching "true" first, then "false"
-}
parseBool :: String -> Maybe (JSONValue, String)
parseBool s = Nothing  -- TODO: Implement

{- |
TODO 5: Implement JSON array parsing

CONCEPT: Array Structure
JSON arrays are ordered lists of values enclosed in brackets:
  [value1, value2, value3, ...]

Arrays can be:
- Empty: []
- Single element: [42]
- Multiple elements: [1, "hello", true, null]
- Nested: [[1, 2], [3, 4]]
- Mixed types: [1, "hello", {"key": "value"}]

PARSING STRATEGY:
1. Skip whitespace and expect '['
2. Check if next character is ']' (empty array)
3. If not empty:
   a. Parse first value using parseValue
   b. Look for comma
   c. If comma found, parse next value and repeat
   d. If no comma, expect ']'
4. Return JSONArray with list of parsed values

HANDLING COMMAS:
Arrays are comma-separated: [1, 2, 3]
- After each value except the last, expect a comma
- After the last value, expect ']'

WHITESPACE:
JSON allows arbitrary whitespace around tokens:
  [ 1 , 2 , 3 ]  is equivalent to [1,2,3]

EXAMPLES:
  parseArray "[]" → Just (JSONArray [], "")
  parseArray "[1]" → Just (JSONArray [JSONNumber 1], "")
  parseArray "[1, 2, 3]" → Just (JSONArray [JSONNumber 1, ...], "")
  parseArray "[1, [2, 3]]" → Nested arrays

IMPLEMENTATION TIP:
Use a helper function to parse array elements recursively:
- parseArrayElements: Accumulates parsed values
- After each value, check for comma (more values) or ']' (done)
-}
parseArray :: String -> Maybe (JSONValue, String)
parseArray s = Nothing  -- TODO: Implement

{- |
TODO 6: Implement JSON object parsing

CONCEPT: Object Structure
JSON objects are collections of key-value pairs:
  {"key1": value1, "key2": value2, ...}

Rules:
- Keys must be strings (quoted)
- Key and value separated by ':'
- Pairs separated by ','
- Can be empty: {}

PARSING STRATEGY:
1. Skip whitespace and expect '{'
2. Check if next character is '}' (empty object)
3. If not empty:
   a. Parse key (must be a string)
   b. Skip whitespace and expect ':'
   c. Parse value using parseValue
   d. Add (key, value) pair to list
   e. Check for comma:
      - If comma: parse next pair and repeat
      - If no comma: expect '}'
4. Return JSONObject with list of pairs

KEY EXTRACTION:
When parsing a key, you'll get JSONString from parseString.
Extract the actual string value from it.

EXAMPLES:
  parseObject "{}" → Just (JSONObject [], "")
  parseObject "{\"name\": \"Alice\"}" → Just (JSONObject [("name", JSONString "Alice")], "")
  parseObject "{\"a\": 1, \"b\": 2}" → Multiple pairs
  parseObject "{\"nested\": {\"x\": 1}}" → Nested object

IMPLEMENTATION TIP:
Similar structure to parseArray, but:
- Parse key (string), then ':', then value
- Store as (key, value) tuple
- Use helper function to accumulate pairs
-}
parseObject :: String -> Maybe (JSONValue, String)
parseObject s = Nothing  -- TODO: Implement

{- |
TODO 7: Implement the main parseValue function

CONCEPT: Unified Value Parser
This is the main entry point that delegates to specific parsers.

APPROACH:
Try each parser in sequence until one succeeds:
1. Try parseNull
2. Try parseBool
3. Try parseNumber
4. Try parseString
5. Try parseArray
6. Try parseObject

If all fail, return Nothing.

WHY THIS ORDER?
- Keywords (null, true, false) should be checked before numbers
  (otherwise "null" might be mistaken for invalid number)
- Strings, arrays, objects have distinct starting characters
  (", [, { respectively)

IMPLEMENTATION TIP:
You can try parsers in sequence using pattern matching:
  case parseNull s of
    Just result -> Just result
    Nothing -> case parseBool s of
      Just result -> Just result
      Nothing -> ...

Or use a helper function that tries a list of parsers.

EXAMPLES:
  parseValue "null" → Just (JSONNull, "")
  parseValue "42" → Just (JSONNumber 42, "")
  parseValue "[1,2]" → Just (JSONArray [...], "")
  parseValue "{\"key\": \"val\"}" → Just (JSONObject [...], "")
-}
parseValue :: String -> Maybe (JSONValue, String)
parseValue s = Nothing  -- TODO: Implement

{- |
TODO 8: Implement the main parse function

PURPOSE: Public API for parsing JSON

APPROACH:
1. Call parseValue on the input
2. Check that entire input was consumed (or only whitespace remains)
3. Return Either String JSONValue:
   - Left "error message": Parse failed
   - Right value: Parse succeeded

VALIDATION:
After parsing, remaining string should be empty or contain only whitespace.

EXAMPLES:
  parse "null" → Right JSONNull
  parse "42" → Right (JSONNumber 42)
  parse "42 invalid" → Left "Unexpected characters after JSON value"
  parse "invalid" → Left "Parse error"
-}
parse :: String -> Either String JSONValue
parse s = Left "Not implemented"  -- TODO: Implement

{- |
TODO 9: Implement pretty-printing

CONCEPT: Converting JSON values back to strings
Pretty-printing produces human-readable JSON output with indentation.

GUIDELINES:
Implement two functions:
1. toJSON: Simple, compact representation (no indentation)
2. prettyJSON: Formatted with indentation and newlines
-}

{- |
Convert JSONValue to compact JSON string (no indentation)

APPROACH:
Pattern match on each constructor:
- JSONNull → "null"
- JSONBool True → "true"
- JSONBool False → "false"
- JSONNumber n → show n
- JSONString s → "\"" ++ escapeString s ++ "\""
- JSONArray vs → "[" ++ (comma-separated values) ++ "]"
- JSONObject ps → "{" ++ (comma-separated "key":value pairs) ++ "}"

FOR STRINGS:
Need to escape special characters:
- '\n' → "\\n"
- '\t' → "\\t"
- '"' → "\\\""
- '\\' → "\\\\"
etc.

EXAMPLES:
  toJSON JSONNull → "null"
  toJSON (JSONNumber 42) → "42.0"
  toJSON (JSONArray [JSONNumber 1, JSONNumber 2]) → "[1.0,2.0]"
-}
toJSON :: JSONValue -> String
toJSON v = undefined  -- TODO: Implement

{- |
Convert JSONValue to pretty-printed JSON string with indentation

APPROACH:
Similar to toJSON, but add indentation and newlines:
- Track current indentation level
- Add newlines after opening braces/brackets
- Indent each line appropriately
- Add newlines before closing braces/brackets

PARAMETERS:
- indent: Current indentation level (number of spaces)
- value: JSONValue to print

FOR ARRAYS:
[
  value1,
  value2,
  value3
]

FOR OBJECTS:
{
  "key1": value1,
  "key2": value2
}

EXAMPLES:
  prettyJSON 0 (JSONObject [("name", JSONString "Alice")])
  →
  {
    "name": "Alice"
  }
-}
prettyJSON :: Int -> JSONValue -> String
prettyJSON indent v = undefined  -- TODO: Implement

{- |
MAIN FUNCTION FOR TESTING
-}
main :: IO ()
main = do
  putStrLn "JSON Parser - Test Cases\n"
  
  let testCases = 
        [ "null"
        , "true"
        , "false"
        , "42"
        , "3.14"
        , "\"hello\""
        , "\"hello\\nworld\""
        , "\"Unicode: \\u0041\""
        , "[]"
        , "[1, 2, 3]"
        , "[1, \"hello\", true]"
        , "{}"
        , "{\"name\": \"Alice\"}"
        , "{\"name\": \"Alice\", \"age\": 30}"
        , "{\"users\": [{\"name\": \"Alice\"}, {\"name\": \"Bob\"}]}"
        ]
  
  mapM_ testParse testCases
  where
    testParse input = do
      putStrLn $ "Input:  " ++ input
      case parse input of
        Right value -> do
          putStrLn $ "Parsed: " ++ show value
          putStrLn $ "JSON:   " ++ toJSON value
        Left err -> putStrLn $ "Error:  " ++ err
      putStrLn ""

{- |
=============================================================================
COMPREHENSIVE IMPLEMENTATION GUIDE
=============================================================================

OVERVIEW:
This JSON parser project teaches advanced Haskell concepts through building
a real-world parser. You'll work with recursive data structures, string
processing, and data transformation.

STEP-BY-STEP IMPLEMENTATION ROADMAP:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1: DATA MODELING (30 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1.1: Complete the JSONValue type (TODO 1)
  □ Add constructors for all JSON types
  □ Understand recursive nature of Array and Object
  □ Test creating values in GHCi:
    - JSONNull
    - JSONBool True
    - JSONNumber 42.0
    - JSONString "hello"
    - JSONArray [JSONNull, JSONBool False]
    - JSONObject [("key", JSONString "value")]

Step 1.2: Understand the structure
  □ Draw a tree diagram for nested JSON
  □ See how arrays and objects can contain any JSONValue
  □ Realize this allows arbitrary nesting depth

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2: STRING PARSING (2-3 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 2.1: Implement parseEscape (TODO 2)
  □ Handle basic escapes: \n, \t, \r, \\, \"
  □ Handle Unicode escapes: \uXXXX
  □ Test: parseEscape "n" should give '\n'
  □ Test: parseEscape "u0041" should give 'A'

Step 2.2: Implement parseStringChars (TODO 2)
  □ Use accumulator pattern
  □ Handle regular characters
  □ Handle escape sequences (call parseEscape)
  □ Stop at closing quote
  □ Test with various strings

Step 2.3: Implement parseString (TODO 2)
  □ Check for opening quote
  □ Call parseStringChars
  □ Wrap result in JSONString
  □ Test thoroughly with escapes and Unicode

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3: SIMPLE VALUES (1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 3.1: Implement parseNull (TODO 4)
  □ Check for "null" keyword
  □ Return JSONNull
  □ Test: parseNull "null" and parseNull "null rest"

Step 3.2: Implement parseBool (TODO 4)
  □ Check for "true" or "false"
  □ Return appropriate JSONBool
  □ Test both true and false

Step 3.3: Implement parseNumber (TODO 3)
  □ Handle optional minus sign
  □ Parse integer part
  □ Handle optional decimal part
  □ Handle optional exponent
  □ Use read to convert to Double
  □ Test various number formats

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 4: ARRAYS (1-2 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 4.1: Plan array parsing strategy
  □ Understand recursive nature
  □ Handle empty arrays
  □ Handle comma-separated values

Step 4.2: Implement parseArray (TODO 5)
  □ Check for opening '['
  □ Handle empty array case
  □ Parse first value
  □ Create helper to parse remaining values:
    - Check for comma
    - Parse next value
    - Recurse
  □ Check for closing ']'

Step 4.3: Test arrays
  □ Empty: []
  □ Single element: [1]
  □ Multiple: [1, 2, 3]
  □ Nested: [[1, 2], [3, 4]]
  □ Mixed: [1, "hello", true]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 5: OBJECTS (1-2 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 5.1: Plan object parsing strategy
  □ Understand key-value structure
  □ Handle empty objects
  □ Parse key (must be string)
  □ Parse colon separator
  □ Parse value
  □ Handle comma-separated pairs

Step 5.2: Implement parseObject (TODO 6)
  □ Check for opening '{'
  □ Handle empty object case
  □ Parse first key-value pair
  □ Create helper to parse remaining pairs
  □ Check for closing '}'

Step 5.3: Test objects
  □ Empty: {}
  □ Single pair: {"key": "value"}
  □ Multiple: {"a": 1, "b": 2}
  □ Nested: {"obj": {"x": 1}}
  □ Complex: {"array": [1, 2], "nested": {"key": "val"}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 6: INTEGRATION (30 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 6.1: Implement parseValue (TODO 7)
  □ Try each parser in sequence
  □ Return first successful parse
  □ Test with all value types

Step 6.2: Implement parse (TODO 8)
  □ Call parseValue
  □ Validate entire input consumed
  □ Return Either with error or success

Step 6.3: Test complete parsing
  □ Run all test cases in main
  □ Verify successful parsing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 7: PRETTY-PRINTING (1-2 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 7.1: Implement toJSON (TODO 9)
  □ Handle each constructor
  □ Implement string escaping
  □ Test round-trip: parse then toJSON

Step 7.2: Implement prettyJSON (TODO 9)
  □ Add indentation tracking
  □ Insert newlines appropriately
  □ Indent nested structures
  □ Test with complex nested JSON

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY HASKELL CONCEPTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Recursive Data Structures
2. String Processing
3. Maybe Monad for parsing
4. Pattern Matching
5. List Processing
6. Accumulator Pattern
7. Helper Functions
8. Type Safety

EXTENSIONS:
- Better error messages with position tracking
- Support for comments
- Streaming parser for large files
- Pretty-printer with customizable indentation
- JSON path queries (like $.users[0].name)
- JSON schema validation
- Performance optimization

-}
