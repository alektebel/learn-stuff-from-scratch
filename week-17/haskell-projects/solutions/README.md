# Solutions

<<<<<<< HEAD
This directory contains complete implementations of Haskell projects.

## Files

- **Calculator.hs** - Complete calculator with parser and evaluator

## Building and Running

```bash
# Using GHC
ghc -o calculator Calculator.hs
./calculator

# Or using runhaskell
runhaskell Calculator.hs

# Interactive (GHCi)
ghci Calculator.hs
> calculate "2 + 3 * 4"
```

## Calculator Implementation

The solution demonstrates:

1. **Algebraic Data Types**: Expr type representing mathematical expressions
2. **Pattern Matching**: Evaluating expressions recursively
3. **Recursive Descent Parsing**: Building expressions from strings
4. **Error Handling**: Using Either for parse and evaluation errors
5. **Operator Precedence**: Correct handling of * / before + -

### Expression Type

=======
This directory contains complete, working implementations of all Haskell projects.

**⚠️ IMPORTANT**: Try to implement the projects yourself first! These solutions are here for:
- **Reference** when you're stuck
- **Verification** of your approach
- **Learning** alternative implementations
- **Comparison** with your own solution

## Philosophy

The best way to learn is by doing. Use these solutions wisely:
1. ✅ Attempt the project yourself first
2. ✅ Get stuck and struggle (this is where learning happens!)
3. ✅ Try to debug and fix issues on your own
4. ✅ Consult hints and guidelines in the template
5. ✅ Only then peek at solutions for specific functions
6. ✅ Understand the solution, don't just copy it
7. ✅ Implement it yourself after understanding

## Files

### 1. Calculator.hs
**Complete calculator with parser and evaluator**

A mathematical expression parser and evaluator demonstrating:
- **Algebraic Data Types**: Expression representation
- **Pattern Matching**: Recursive evaluation
- **Recursive Descent Parsing**: Building AST from strings
- **Error Handling**: Either monad for errors
- **Operator Precedence**: Correct * / before + -

**Complexity**: Beginner  
**Lines**: ~130  
**Key Concepts**: ADTs, Pattern Matching, Parsing, Recursion

#### Features:
- ✅ Integer arithmetic: +, -, *, /
- ✅ Operator precedence (PEMDAS without exponents)
- ✅ Parentheses for grouping
- ✅ Division by zero detection
- ✅ Clear error messages
- ✅ Whitespace handling

#### Architecture:
```
String → Parser → Expr → Evaluator → Int
         (parse)        (eval)
```

Two-phase design:
1. **Parsing**: Converts string to expression tree
2. **Evaluation**: Walks tree and computes result

#### Expression Type:
>>>>>>> main
```haskell
data Expr = Num Int
          | Add Expr Expr
          | Sub Expr Expr
          | Mul Expr Expr
          | Div Expr Expr
```

<<<<<<< HEAD
### Usage Examples

=======
#### Usage Examples:
>>>>>>> main
```haskell
calculate "2 + 3"          -- Right 5
calculate "10 - 4"         -- Right 6
calculate "5 * 6"          -- Right 30
calculate "20 / 4"         -- Right 5
calculate "2 + 3 * 4"      -- Right 14 (respects precedence)
calculate "(2 + 3) * 4"    -- Right 20
calculate "10 / 0"         -- Left "Division by zero"
<<<<<<< HEAD
```

## Learning Points

- **Functional Programming**: Pure functions, immutability
- **Type Safety**: Compile-time guarantees
- **Algebraic Data Types**: Modeling problems with types
- **Pattern Matching**: Elegant case analysis
- **Recursion**: Natural solution for recursive structures
- **Monads**: Either monad for error handling
- **Parsing**: Building parsers from scratch

## Features

1. **Correct Operator Precedence**
   - Multiplication and division before addition and subtraction
   - Parentheses for grouping

2. **Error Handling**
   - Parse errors for invalid syntax
   - Division by zero detection
   - Clear error messages

3. **Clean Separation**
   - Parsing phase: String → Expr
   - Evaluation phase: Expr → Int

## Extensions to Explore

- More operators (modulo, exponentiation)
- Floating-point numbers
- Variables and assignment
- Functions (sin, cos, sqrt, etc.)
- Using parser combinator libraries (Parsec, Megaparsec)
- Pretty-printing expressions
- Simplification and optimization

## Haskell Concepts Demonstrated

- Data types and constructors
- Recursive functions
- Maybe and Either types
- List processing
- String manipulation
- Type inference
- Pure functions
- Immutability

## Resources

- "Learn You a Haskell for Great Good!" by Miran Lipovača
- "Programming in Haskell" by Graham Hutton
- Real World Haskell
- Haskell Wiki: https://wiki.haskell.org/
=======
calculate "2 +"            -- Left "Parse error"
```

### 2. JSONParser.hs
**Complete JSON parser from scratch**

A full JSON parser implementing:
- **Recursive Data Structures**: Nested objects and arrays
- **String Parsing**: Escape sequences and Unicode
- **Multiple Data Types**: Null, bool, number, string, array, object
- **Pretty Printing**: Human-readable JSON output

**Complexity**: Intermediate  
**Lines**: ~300  
**Key Concepts**: Recursive parsing, Unicode handling, String processing

#### Features:
- ✅ All JSON types: null, boolean, number, string, array, object
- ✅ String escapes: \n, \t, \", \\, Unicode \uXXXX
- ✅ Nested structures (arbitrary depth)
- ✅ Number formats: integers, floats, scientific notation
- ✅ Pretty-printing with indentation
- ✅ Round-trip: parse → toJSON → parse

#### JSON Value Type:
```haskell
data JSONValue 
  = JSONNull
  | JSONBool Bool
  | JSONNumber Double
  | JSONString String
  | JSONArray [JSONValue]
  | JSONObject [(String, JSONValue)]
```

#### Usage Examples:
```haskell
parse "null"                          -- Right JSONNull
parse "42"                            -- Right (JSONNumber 42.0)
parse "[1, 2, 3]"                     -- Right (JSONArray [..])
parse "{\"name\": \"Alice\"}"         -- Right (JSONObject [..])
parse "{\"users\": [{\"age\": 30}]}"  -- Nested structures
```

### 3. WebScraper.hs
**Web scraper with HTML parsing**

A web scraping tool demonstrating:
- **IO Monad**: HTTP requests and side effects
- **HTML Parsing**: Using TagSoup library
- **Concurrent Operations**: Parallel page scraping
- **Error Handling**: Network and parse errors

**Complexity**: Intermediate  
**Lines**: ~250  
**Key Concepts**: IO monad, External libraries, Concurrency

#### Features:
- ✅ HTTP fetching with http-conduit
- ✅ HTML parsing with TagSoup
- ✅ Link extraction from pages
- ✅ Metadata extraction
- ✅ Concurrent multi-page scraping
- ✅ Pattern-based filtering
- ✅ Error recovery

#### Usage Examples:
```haskell
-- Scrape single page
result <- scrapePage "https://example.com"

-- Get external links only
links <- getExternalLinks "https://example.com"

-- Find specific links
matches <- findLinks "github" "https://example.com"

-- Scrape multiple pages concurrently
results <- scrapePages ["url1", "url2", "url3"]
```

### 4. BuildTool.hs
**Build system similar to Make**

A dependency-based build tool showing:
- **Graph Algorithms**: Topological sorting, cycle detection
- **File System**: Timestamps, path operations
- **Process Execution**: Running shell commands
- **Configuration Parsing**: Buildfile parsing

**Complexity**: Advanced  
**Lines**: ~400  
**Key Concepts**: Graphs, System programming, Algorithms

#### Features:
- ✅ Dependency tracking
- ✅ Topological build ordering
- ✅ Incremental builds (timestamp-based)
- ✅ Phony targets
- ✅ Cycle detection
- ✅ Parallel builds (optional)
- ✅ Makefile-like syntax

#### Buildfile Format:
```makefile
.PHONY: clean test

app: main.o utils.o
	gcc -o app main.o utils.o

main.o: main.c
	gcc -c main.c

clean:
	rm -f *.o app
```

#### Usage Examples:
```bash
# Build default target
./build-tool

# Build specific target
./build-tool app

# Build with custom buildfile
./build-tool -f my-build.txt test
```

## Building and Running

### Using GHC (Compile first, then run)
```bash
# Navigate to solutions directory
cd haskell-projects/solutions/

# Compile a project
ghc -o calculator Calculator.hs

# Run the compiled program
./calculator

# For projects with dependencies (like WebScraper)
ghc -o scraper WebScraper.hs -package http-conduit -package tagsoup
```

### Using runhaskell (Interpret directly)
```bash
# Run without compilation
runhaskell Calculator.hs

# Faster for testing and development
runhaskell JSONParser.hs
```

### Using GHCi (Interactive)
```bash
# Load a module
ghci Calculator.hs

# Test functions interactively
> calculate "2 + 3 * 4"
Right 14

> eval (Add (Num 2) (Num 3))
Right 5

> parse "10 / 2"
Right (Div (Num 10) (Num 2))

# Reload after changes
> :reload

# Get type information
> :type calculate
calculate :: String -> Either String Int

# Exit
> :quit
```

## Solution Structure

Each solution follows consistent patterns:

### 1. Module Declaration
```haskell
module Main where
-- or
module ModuleName where
```

### 2. Imports
```haskell
import Data.Char (isDigit, isSpace)
import Data.Maybe (mapMaybe)
-- etc.
```

### 3. Data Type Definitions
```haskell
data Expr = Num Int | Add Expr Expr | ...
```

### 4. Core Functions
```haskell
parse :: String -> Either String Expr
eval :: Expr -> Either String Int
```

### 5. Helper Functions
```haskell
skipSpace :: String -> String
parseNumber :: String -> Maybe (Int, String)
```

### 6. Main Function
```haskell
main :: IO ()
main = do
  -- Test cases and examples
```

## Learning from Solutions

### How to Study a Solution

1. **Read Top-Down**:
   - Start with data types
   - Understand the main functions
   - Then dive into helpers

2. **Trace Execution**:
   - Pick a simple example
   - Follow it through each function
   - Draw diagrams if needed

3. **Identify Patterns**:
   - How are errors handled?
   - How is recursion used?
   - What helper functions exist?

4. **Compare with Your Code**:
   - What's different?
   - Which approach is clearer?
   - What can you learn?

5. **Modify and Experiment**:
   - Change the code
   - Break it intentionally
   - Fix it again
   - Add features

### Key Patterns in Solutions

#### Pattern 1: Maybe for Optional Results
```haskell
parseNumber :: String -> Maybe (Int, String)
-- Returns Nothing on failure, Just (value, rest) on success
```

#### Pattern 2: Either for Error Messages
```haskell
calculate :: String -> Either String Int
-- Returns Left "error" on failure, Right value on success
```

#### Pattern 3: Recursive Descent Parsing
```haskell
parseExpr s = case parseTerm s of
  Just (expr, rest) -> parseExpr' expr rest
  Nothing -> Nothing
  where parseExpr' left rest = ...
```

#### Pattern 4: Accumulator Pattern
```haskell
processItems acc [] = acc
processItems acc (x:xs) = processItems (acc + process x) xs
```

#### Pattern 5: do-notation for Sequencing
```haskell
calculate input = do
  expr <- parse input    -- Either monad
  eval expr              -- Chains operations
```

## Testing Solutions

### Manual Testing
```bash
# Run the main function
runhaskell Calculator.hs

# Or in GHCi
ghci Calculator.hs
> main
```

### Interactive Testing
```bash
ghci Calculator.hs
> calculate "2 + 3"
Right 5
> calculate "invalid"
Left "Parse error"
```

### Creating Test Suites
```haskell
import Test.HUnit  -- or QuickCheck

tests = TestList
  [ "addition" ~: calculate "2+3" ~?= Right 5
  , "precedence" ~: calculate "2+3*4" ~?= Right 14
  , "error" ~: calculate "2+" ~?= Left "Parse error"
  ]

main = runTestTT tests
```

## Common Haskell Idioms Used

### 1. Pattern Matching
```haskell
eval (Num n) = Right n
eval (Add e1 e2) = ...
```

### 2. Guards
```haskell
needsRebuild target
  | targetPhony target = True
  | not (fileExists target) = True
  | otherwise = False
```

### 3. List Comprehensions
```haskell
links = [Link text href | tag <- tags, isLink tag]
```

### 4. Map and Filter
```haskell
let numbers = map read ["1", "2", "3"] :: [Int]
    evens = filter even numbers
```

### 5. Fold
```haskell
sum = foldl (+) 0 [1,2,3,4,5]
```

### 6. Function Composition
```haskell
process = filter valid . map transform . parse
```

## Performance Considerations

The solutions prioritize **clarity over performance**:

### Optimizations NOT Used:
- ❌ Strict evaluation (bang patterns)
- ❌ Unboxed types
- ❌ Custom parsing libraries (attoparsec)
- ❌ ByteString instead of String
- ❌ Space leak prevention

### Why?
- **Educational focus**: Easier to understand
- **Standard library**: Uses common functions
- **Correctness first**: Performance can come later

### When You Need Performance:
1. Profile first: Use GHC profiler
2. ByteString: For large text processing
3. Vector: For array operations
4. Strict evaluation: Prevent space leaks
5. Specialized libraries: attoparsec, etc.

## Troubleshooting

### Common Issues

**"Module not found"**
```bash
# Install missing packages
cabal update
cabal install <package-name>
```

**"Parse error"**
- Check indentation (Haskell is whitespace-sensitive)
- Ensure proper alignment in do-blocks and where clauses

**"Type mismatch"**
- Read error message carefully
- Check function signatures
- Use :type in GHCi to inspect types

**"Non-exhaustive patterns"**
- Add catch-all pattern: `_ -> ...`
- Or handle all constructors explicitly

## Next Steps

After studying these solutions:

1. **Implement Yourself**: Don't just read, code!
2. **Add Features**: Extend the projects
3. **Refactor**: Make the code better
4. **Test**: Write comprehensive tests
5. **Optimize**: Profile and improve performance
6. **Share**: Help others learn

## Extensions to Try

### Calculator
- [ ] Floating-point numbers
- [ ] More operators (%, ^)
- [ ] Variables and assignment
- [ ] Functions (sin, cos, sqrt)
- [ ] REPL (Read-Eval-Print Loop)

### JSON Parser
- [ ] Better error messages with position
- [ ] Streaming parser for large files
- [ ] JSON Schema validation
- [ ] JSON path queries
- [ ] Benchmarking against Aeson

### Web Scraper
- [ ] Rate limiting
- [ ] Robot.txt checking
- [ ] Cookie handling
- [ ] User agent spoofing
- [ ] Data persistence (database)

### Build Tool
- [ ] Parallel builds
- [ ] Pattern rules (%.o: %.c)
- [ ] Variables in buildfiles
- [ ] Automatic dependency detection
- [ ] Build caching

## Resources

### Official Documentation
- **Haskell.org**: https://www.haskell.org/
- **Hackage**: https://hackage.haskell.org/ (package repository)
- **Hoogle**: https://hoogle.haskell.org/ (function search)

### Books
- **"Learn You a Haskell"**: Beginner-friendly introduction
- **"Programming in Haskell"**: Comprehensive textbook
- **"Real World Haskell"**: Practical applications
- **"Haskell Programming from First Principles"**: In-depth learning

### Online Resources
- **Haskell Wiki**: https://wiki.haskell.org/
- **School of Haskell**: Interactive tutorials
- **r/haskell**: Reddit community
- **#haskell** on IRC: Real-time help

### Practice
- **Exercism.io**: Haskell track with mentoring
- **Project Euler**: Mathematical problems
- **Advent of Code**: Annual programming challenges
- **99 Haskell Problems**: Classic exercises

## Contributing

Found a bug or improvement in the solutions?
- Open an issue
- Submit a pull request
- Suggest better approaches

## License

These educational implementations are provided as learning resources.
Feel free to use, modify, and share.
>>>>>>> main
