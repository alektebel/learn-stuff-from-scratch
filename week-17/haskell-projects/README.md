# Haskell Projects

<<<<<<< HEAD
This directory contains various projects to learn Haskell from scratch.

## Goal
Learn Haskell by implementing real-world projects to understand:
- Functional programming paradigms
- Type systems and type inference
- Monads and functors
- Lazy evaluation
- Pure functions and immutability

## Project Ideas
1. **Simple Calculator** - Parser and evaluator
2. **JSON Parser** - Parsing and data structures
3. **Web Scraper** - HTTP requests and HTML parsing
4. **Build Tool** - File system operations and dependency management
5. **Compiler** - Lexing, parsing, and code generation
6. **Database** - Data storage and query language
7. **Web Framework** - HTTP server and routing

## Learning Path
Start with simpler projects and progressively build more complex systems.
=======
This directory contains various projects to learn Haskell from scratch. Each project comes with verbose implementation guidelines that explain **what** to implement and **how** to approach it, without providing the actual implementation code.

## Goal
Learn Haskell by implementing real-world projects to understand:
- **Functional Programming Paradigms**: Pure functions, immutability, higher-order functions
- **Type Systems and Type Inference**: Algebraic data types, type classes, parametric polymorphism
- **Monads and Functors**: Abstractions for computational context
- **Lazy Evaluation**: Evaluation strategies and infinite data structures
- **Pure Functions and Immutability**: Side-effect free programming

## Philosophy

These projects follow the "learn by doing" approach:
- ✅ **Verbose Guidelines**: Each TODO comment includes detailed explanations
- ✅ **No Direct Solutions**: Guidelines explain concepts without giving away the code
- ✅ **Progressive Complexity**: Start simple, add features incrementally
- ✅ **Real-World Relevance**: Projects mirror actual software systems
- ✅ **Conceptual Focus**: Understand Haskell idioms and patterns

## Projects Overview

### 1. **Simple Calculator** 
**Complexity**: Beginner  
**File**: `Calculator.hs`  
**Focus**: Parsing, algebraic data types, pattern matching

Build a mathematical expression parser and evaluator that handles operator precedence and parentheses.

**Key Learning Points**:
- Defining algebraic data types (ADTs) to represent expressions
- Pattern matching for recursive evaluation
- Recursive descent parsing without libraries
- Error handling with Maybe and Either types
- Operator precedence implementation

**What You'll Build**: A calculator that can parse and evaluate expressions like `"2 + 3 * 4"` or `"(10 - 2) / 4"`.

### 2. **JSON Parser**
**Complexity**: Intermediate  
**File**: `JSONParser.hs`  
**Focus**: Recursive data structures, parsing, Unicode handling

Implement a JSON parser from scratch that can handle objects, arrays, strings, numbers, booleans, and null values.

**Key Learning Points**:
- Recursive data structures for nested JSON
- String parsing with escape sequences
- Number parsing (integers and floats)
- Parser combinators approach
- Unicode support in strings
- Pretty-printing JSON

**What You'll Build**: A parser that converts JSON strings into Haskell data structures and back.

### 3. **Web Scraper**
**Complexity**: Intermediate  
**File**: `WebScraper.hs`  
**Focus**: IO monad, HTTP, HTML parsing, monadic operations

Build a web scraper that fetches web pages and extracts structured data from HTML.

**Key Learning Points**:
- Working with the IO monad
- HTTP requests (using libraries like http-conduit)
- HTML parsing and traversal
- CSS selectors or XPath-like queries
- Handling errors in IO operations
- Concurrent requests with async

**What You'll Build**: A scraper that can extract specific information from web pages based on selectors.

### 4. **Build Tool**
**Complexity**: Advanced  
**File**: `BuildTool.hs`  
**Focus**: File system operations, dependency graphs, incremental builds

Create a build tool similar to Make that manages dependencies and rebuilds only what's necessary.

**Key Learning Points**:
- File system operations in IO
- Dependency graph construction
- Topological sorting for build order
- Timestamp-based change detection
- Parallel build execution
- Configuration file parsing

**What You'll Build**: A tool that reads build specifications and executes build commands in the correct order.

## Learning Path

### Phase 1: Foundations (Start Here)
1. **Simple Calculator** - Master the basics of Haskell syntax, types, and parsing

### Phase 2: Data Handling
2. **JSON Parser** - Dive deeper into recursive structures and string processing

### Phase 3: Real-World Integration  
3. **Web Scraper** - Learn to work with IO, external libraries, and side effects

### Phase 4: System Programming
4. **Build Tool** - Combine everything to build a complex, practical tool

## Getting Started

### Prerequisites
- GHC (Glasgow Haskell Compiler) installed
- Basic understanding of functional programming concepts
- Familiarity with recursion and pattern matching

### Installation

```bash
# Install GHC and Cabal (Haskell's build tool)
# On macOS:
brew install ghc cabal-install

# On Ubuntu/Debian:
sudo apt-get install ghc cabal-install

# On Windows:
# Download and install Haskell Platform from https://www.haskell.org/platform/
```

### Running a Project

```bash
# Navigate to the haskell-projects directory
cd haskell-projects

# Run with runhaskell (no compilation needed)
runhaskell Calculator.hs

# Or compile first, then run
ghc -o calculator Calculator.hs
./calculator

# Interactive development with GHCi
ghci Calculator.hs
> -- Test functions interactively
```

## Project Structure

Each project file contains:
- **Module declaration** and imports
- **Data type definitions** with TODOs and guidelines
- **Function templates** with detailed implementation hints
- **Implementation guide** section explaining the overall approach
- **Learning points** highlighting key Haskell concepts
- **Test cases** to verify your implementation

## Implementation Guidelines Format

Each TODO in the project files follows this structure:

```haskell
{- |
TODO N: Brief description of what to implement

Guidelines:
- Detailed explanation of the concept
- Approach suggestions (not actual code)
- Edge cases to consider
- Relevant Haskell idioms

Example:
  Pseudocode or example usage showing expected behavior
-}
```

## Tips for Success

1. **Read Before Coding**: Understand the entire file structure before starting
2. **Implement Incrementally**: Complete one TODO at a time, test after each
3. **Use GHCi**: Test functions interactively as you write them
4. **Type-Driven Development**: Let the type system guide your implementation
5. **Consult Documentation**: Use Hoogle (https://hoogle.haskell.org/) to search for functions
6. **Check Solutions**: When stuck, peek at `solutions/` folder for reference
7. **Understand, Don't Copy**: Make sure you understand why the solution works

## Core Haskell Concepts Covered

### Type System
- Algebraic data types (sum and product types)
- Type classes (Eq, Show, Functor, Monad, etc.)
- Parametric polymorphism
- Type inference

### Functional Programming
- Pure functions
- Higher-order functions
- Currying and partial application
- Function composition
- Immutability

### Pattern Matching
- Destructuring data types
- Guards and case expressions
- Wildcard patterns
- As-patterns

### Monads and Effects
- Maybe monad for optional values
- Either monad for error handling
- IO monad for side effects
- List monad for non-determinism

### Parsing
- Recursive descent parsing
- Parser combinators
- Lexical analysis
- Error reporting

## Common Patterns You'll Learn

1. **Recursive Data Structures**: Trees, lists, nested structures
2. **Fold Patterns**: Reducing structures to values
3. **Map Patterns**: Transforming structure contents
4. **Builder Patterns**: Constructing complex values incrementally
5. **Monadic Patterns**: Chaining computations with context

## Resources

### Books
- "Learn You a Haskell for Great Good!" by Miran Lipovača (Beginner-friendly)
- "Programming in Haskell" by Graham Hutton (Comprehensive)
- "Haskell Programming from First Principles" by Christopher Allen & Julie Moronuki
- "Real World Haskell" by Bryan O'Sullivan, Don Stewart, and John Goerzen

### Online Resources
- Haskell Wiki: https://wiki.haskell.org/
- Hoogle (function search): https://hoogle.haskell.org/
- Hackage (package repository): https://hackage.haskell.org/
- r/haskell on Reddit
- #haskell on IRC

### Practice
- Exercism.io Haskell track
- Project Euler (solve with Haskell)
- Advent of Code (annual programming challenges)

## Next Steps After Completion

Once you've completed these projects, consider:
- Contributing to open-source Haskell projects
- Building your own Haskell applications
- Exploring advanced topics: GADTs, Type Families, Template Haskell
- Learning category theory for deeper understanding
- Trying other functional languages (OCaml, F#, Elm, PureScript)

## Notes

- These implementations prioritize **learning** over production-readiness
- Focus on understanding **why** things work, not just **how**
- Solutions are available in `solutions/` folder for reference
- Don't hesitate to consult external resources when stuck
- The best way to learn is by **implementing yourself first**

## Video Courses & Resources

**Functional Programming**:
- [FP 101x - Introduction to Functional Programming - TU Delft](https://ocw.tudelft.nl/courses/introduction-to-functional-programming/)
- [Functional Programming & Theoretical CS Courses](https://github.com/Developer-Y/cs-video-courses#theoretical-cs-and-programming-languages)

**Additional Resources**:
- [Learn You a Haskell for Great Good](http://learnyouahaskell.com/)
- [Real World Haskell](http://book.realworldhaskell.org/)
>>>>>>> main

## Sources

- Hutton, **Programming in Haskell** — the textbook.
- Hutton & Meijer, **"Monadic Parser Combinators"**, 1996 — the payoff in `JSONParser.hs`.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-17--patterns-light-haskell)
