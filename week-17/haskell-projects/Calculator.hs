-- Simple Calculator in Haskell - Template
-- This template guides you through building a calculator with a parser and evaluator
<<<<<<< HEAD
=======
--
-- LEARNING OBJECTIVES:
-- 1. Define algebraic data types (ADTs) to model expressions
-- 2. Use pattern matching for recursive evaluation
-- 3. Implement recursive descent parser from scratch
-- 4. Handle errors gracefully with Either type
-- 5. Understand operator precedence in parsing
--
-- ESTIMATED TIME: 4-6 hours for beginners, 2-3 hours for intermediate
>>>>>>> main

module Main where

import Data.Char (isDigit, isSpace)

{- |
<<<<<<< HEAD
TODO 1: Define the expression data type

Guidelines:
- Represent numbers as integers
- Represent binary operations (addition, subtraction, etc.)
- Consider recursive structure for nested expressions

Example structure:
  data Expr = Num Int
            | Add Expr Expr
            | Sub Expr Expr
            | Mul Expr Expr
            | Div Expr Expr
-}
data Expr = Num Int
          -- TODO: Add more constructors
=======
TODO 1: Define the expression data type (Algebraic Data Type - ADT)

CONCEPT: Algebraic Data Types
An ADT is a composite type that represents different variants of data.
In our case, a mathematical expression can be:
- A number (like 5, 42, -3)
- An addition of two expressions (like e1 + e2)
- A subtraction of two expressions (like e1 - e2)
- A multiplication of two expressions (like e1 * e2)
- A division of two expressions (like e1 / e2)

GUIDELINES:
1. Use the `data` keyword to define a new type named `Expr`
2. Each variant is called a "constructor" (Num, Add, Sub, etc.)
3. Constructors can hold values - e.g., Num holds an Int
4. Constructors for binary operations (Add, Sub, Mul, Div) should hold two Expr values
5. This creates a recursive structure: expressions can contain other expressions
6. The `deriving (Show, Eq)` clause automatically generates functions to:
   - Show: Convert Expr to String for printing
   - Eq: Compare two Expr values for equality

STRUCTURE TO IMPLEMENT:
- Num: Holds a single integer value
  Example: Num 42 represents the number 42
- Add: Holds two expressions to add
  Example: Add (Num 2) (Num 3) represents 2 + 3
- Sub: Holds two expressions to subtract
  Example: Sub (Num 5) (Num 2) represents 5 - 2
- Mul: Holds two expressions to multiply
  Example: Mul (Num 3) (Num 4) represents 3 * 4
- Div: Holds two expressions to divide
  Example: Div (Num 10) (Num 2) represents 10 / 2

WHY RECURSIVE?
This allows representing nested expressions like: (2 + 3) * 4
  Mul (Add (Num 2) (Num 3)) (Num 4)

EXAMPLE USAGE:
  expr1 = Num 5                              -- represents: 5
  expr2 = Add (Num 2) (Num 3)               -- represents: 2 + 3
  expr3 = Mul (Num 4) (Add (Num 1) (Num 2)) -- represents: 4 * (1 + 2)
-}
data Expr = Num Int
          -- TODO: Add more constructors for Add, Sub, Mul, Div
          -- Each should take two Expr parameters
>>>>>>> main
  deriving (Show, Eq)

{- |
TODO 2: Implement the eval function

<<<<<<< HEAD
Guidelines:
- Pattern match on expression constructors
- Recursively evaluate sub-expressions
- Apply the appropriate operation
- Handle division by zero (return Maybe Int or Either String Int)

Example:
  eval (Num 5) = 5
  eval (Add (Num 2) (Num 3)) = 5
-}
eval :: Expr -> Int
eval (Num n) = n
-- TODO: Implement evaluation for other operations
eval _ = 0

{- |
TODO 3: Implement the parse function

Guidelines:
- Parse a string into an Expr
- Handle operator precedence (* and / before + and -)
- Handle parentheses
- Skip whitespace
- Use recursive descent parsing or parser combinators

Suggested approach:
1. Start with parseNumber
2. Add parseFactor (numbers and parentheses)
3. Add parseTerm (multiplication and division)
4. Add parseExpr (addition and subtraction)
-}

-- Parse a number from the input
parseNumber :: String -> Maybe (Int, String)
parseNumber s = Nothing  -- TODO: Implement

-- Parse a factor (number or parenthesized expression)
parseFactor :: String -> Maybe (Expr, String)
parseFactor s = Nothing  -- TODO: Implement

-- Parse a term (multiplication and division)
parseTerm :: String -> Maybe (Expr, String)
parseTerm s = Nothing  -- TODO: Implement

-- Parse an expression (addition and subtraction)
parseExpr :: String -> Maybe (Expr, String)
parseExpr s = Nothing  -- TODO: Implement

-- Main parse function
parse :: String -> Maybe Expr
parse s = case parseExpr s of
  Just (expr, "") -> Just expr
  _ -> Nothing

{- |
TODO 4: Implement the calculator function

Guidelines:
- Combine parse and eval
- Handle parsing errors gracefully
- Return the result or an error message
-}
calculate :: String -> Either String Int
calculate input = Left "Not implemented"  -- TODO: Implement
=======
CONCEPT: Pattern Matching and Recursion
Pattern matching allows you to handle different cases based on the structure of data.
For evaluation, we need to:
1. Match each constructor of Expr
2. Recursively evaluate sub-expressions
3. Apply the appropriate mathematical operation
4. Handle error cases (like division by zero)

FUNCTION SIGNATURE:
  eval :: Expr -> Either String Int
  
UNDERSTANDING Either:
- Either String Int means the function returns one of two things:
  - Left String: An error message (String)
  - Right Int: A successful result (Int)
- This is Haskell's way of handling errors without exceptions

IMPLEMENTATION APPROACH:
1. For Num n: This is the base case. Simply return Right n
   No computation needed, just wrap the number in Right.

2. For Add e1 e2: 
   - Recursively evaluate e1 to get its value
   - Recursively evaluate e2 to get its value
   - If both succeed, add them and return Right (v1 + v2)
   - If either fails, propagate the error
   TIP: Use the Either monad with do-notation to handle errors automatically

3. For Sub e1 e2:
   Similar to Add, but subtract v2 from v1

4. For Mul e1 e2:
   Similar to Add, but multiply v1 and v2

5. For Div e1 e2:
   - Evaluate both expressions like Add
   - Check if v2 is 0 before dividing
   - If v2 == 0, return Left "Division by zero"
   - Otherwise, return Right (v1 `div` v2)

MONADIC PATTERN (RECOMMENDED):
Use do-notation to chain operations:
  eval (Add e1 e2) = do
    v1 <- eval e1        -- If e1 fails, entire function fails
    v2 <- eval e2        -- If e2 fails, entire function fails
    return (v1 + v2)     -- Both succeeded, return sum

ALTERNATIVE PATTERN (Manual):
Handle errors explicitly:
  eval (Add e1 e2) = case eval e1 of
    Left err -> Left err
    Right v1 -> case eval e2 of
      Left err -> Left err
      Right v2 -> Right (v1 + v2)

TESTING YOUR EVAL:
  eval (Num 5) should return Right 5
  eval (Add (Num 2) (Num 3)) should return Right 5
  eval (Mul (Num 4) (Num 3)) should return Right 12
  eval (Div (Num 10) (Num 0)) should return Left "Division by zero"

EDGE CASES TO CONSIDER:
- Division by zero
- Large numbers (though Int handles most cases)
- Negative results from subtraction
-}
eval :: Expr -> Either String Int
eval (Num n) = Right n
-- TODO: Implement evaluation for Add, Sub, Mul, Div operations
-- Remember: 
-- - Use pattern matching for each constructor
-- - Recursively evaluate sub-expressions
-- - Check for division by zero in the Div case
-- - Use Either to return errors or results
eval _ = Left "Not implemented"

{- |
TODO 3: Implement the parsing functions

CONCEPT: Recursive Descent Parsing
Parsing converts a string like "2 + 3 * 4" into an Expr data structure.
We use recursive descent parsing, which mirrors the grammar structure.

GRAMMAR HIERARCHY (by precedence, lowest to highest):
1. Expression (Expr): Handles + and - (lowest precedence)
2. Term: Handles * and / (higher precedence than +/-)
3. Factor: Handles numbers and parentheses (highest precedence)

WHY THIS HIERARCHY?
To ensure "2 + 3 * 4" is parsed as "2 + (3 * 4)" not "(2 + 3) * 4"
This respects mathematical operator precedence rules.

PARSING STRATEGY:
Each parsing function returns Maybe (Expr, String):
- Nothing: Parse failed
- Just (expr, remaining): Parse succeeded
  - expr: The parsed expression
  - remaining: The rest of the string not yet parsed

IMPORTANT: Always skip whitespace before parsing!
-}

-- Helper function to skip leading whitespace
-- ALREADY IMPLEMENTED FOR YOU: This is a simple utility function
-- You'll use this in your parsing functions
skipSpace :: String -> String
skipSpace = dropWhile isSpace

{- |
TODO 3.1: Implement parseNumber

PURPOSE: Extract a number from the beginning of a string

APPROACH:
1. Skip leading whitespace using skipSpace
2. Use span isDigit to separate digits from the rest
   - span splits a string at the first non-digit
   - Example: span isDigit "123abc" = ("123", "abc")
3. If no digits found, return Nothing
4. Otherwise, use read to convert string to Int
5. Return Just (number, remaining_string)

EXAMPLES:
  parseNumber "42" -> Just (42, "")
  parseNumber "123 + 45" -> Just (123, " + 45")
  parseNumber "  789" -> Just (789, "")
  parseNumber "abc" -> Nothing

ERROR CASES:
- Empty string after skipping whitespace -> Nothing
- No digits at the start -> Nothing

HINT: The structure should be:
  let s' = skipSpace s
      (digits, rest) = span isDigit s'
  in if null digits then Nothing else Just (read digits, rest)
-}
parseNumber :: String -> Maybe (Int, String)
parseNumber s = Nothing  -- TODO: Implement

{- |
TODO 3.2: Implement parseFactor

PURPOSE: Parse a factor - either a number or a parenthesized expression

A factor is the highest precedence element:
- A number: 42
- A parenthesized expression: (2 + 3)

APPROACH:
1. Skip leading whitespace
2. Check the first character:
   a. If it's '(', parse a parenthesized expression:
      - Recursively call parseExpr on the contents
      - Verify the closing ')'
      - Return the parsed expression
   b. Otherwise, try to parse a number using parseNumber

EXAMPLES:
  parseFactor "42" -> Just (Num 42, "")
  parseFactor "(2 + 3)" -> Just (Add (Num 2) (Num 3), "")
  parseFactor "  (10)" -> Just (Num 10, "")

PARENTHESIS HANDLING:
  case s' of
    ('(':rest) -> 
      - Call parseExpr on rest
      - Check if result is Just (expr, ')':rest')
      - If yes, return Just (expr, rest')
      - If no, return Nothing (mismatched parentheses)
    _ -> 
      - Call parseNumber to try parsing a number

ERROR CASES:
- Mismatched parentheses: "(2 + 3" or "2 + 3)"
- Neither a number nor parenthesized expr
-}
parseFactor :: String -> Maybe (Expr, String)
parseFactor s = Nothing  -- TODO: Implement

{- |
TODO 3.3: Implement parseTerm

PURPOSE: Parse multiplication and division with left-to-right associativity

A term handles * and / operations:
- "3 * 4" should be parsed as Mul (Num 3) (Num 4)
- "12 / 3 * 2" should be parsed as Mul (Div (Num 12) (Num 3)) (Num 2)

LEFT-ASSOCIATIVITY:
Operations of the same precedence are evaluated left-to-right:
  12 / 3 / 2 = (12 / 3) / 2 = 4 / 2 = 2
  NOT 12 / (3 / 2)

APPROACH:
1. Parse the first factor using parseFactor
2. If successful, enter a helper function parseTerm' that:
   a. Skips whitespace
   b. Checks if the next character is '*' or '/'
   c. If '*': 
      - Parse the next factor
      - Create Mul left right
      - Recursively call parseTerm' with the new expression as left
   d. If '/':
      - Parse the next factor
      - Create Div left right
      - Recursively call parseTerm' with the new expression as left
   e. Otherwise: No more * or /, return current expression

STRUCTURE:
  parseTerm s = case parseFactor s of
    Nothing -> Nothing
    Just (expr, rest) -> parseTerm' expr rest
    where
      parseTerm' left s' = 
        let s'' = skipSpace s'
        in case s'' of
          ('*':rest) -> ... (parse factor, recursively call parseTerm')
          ('/':rest) -> ... (parse factor, recursively call parseTerm')
          _ -> Just (left, s'')

EXAMPLES:
  parseTerm "3 * 4" -> Just (Mul (Num 3) (Num 4), "")
  parseTerm "12 / 3 * 2" -> Just (Mul (Div (Num 12) (Num 3)) (Num 2), "")
  parseTerm "5" -> Just (Num 5, "")

WHY HELPER FUNCTION?
parseTerm' accumulates operations from left to right, maintaining left-associativity.
-}
parseTerm :: String -> Maybe (Expr, String)
parseTerm s = Nothing  -- TODO: Implement

{- |
TODO 3.4: Implement parseExpr

PURPOSE: Parse addition and subtraction with left-to-right associativity

Similar to parseTerm, but handles + and - instead of * and /.
This is the lowest precedence level, so it calls parseTerm for higher-precedence operations.

APPROACH:
1. Parse the first term using parseTerm (not parseFactor!)
2. Use a helper function parseExpr' similar to parseTerm':
   a. Skip whitespace
   b. Check if the next character is '+' or '-'
   c. If '+':
      - Parse the next term (not factor!)
      - Create Add left right
      - Recursively call parseExpr' with new expression as left
   d. If '-':
      - Parse the next term (not factor!)
      - Create Sub left right
      - Recursively call parseExpr' with new expression as left
   e. Otherwise: No more + or -, return current expression

STRUCTURE: (Very similar to parseTerm)
  parseExpr s = case parseTerm s of
    Nothing -> Nothing
    Just (expr, rest) -> parseExpr' expr rest
    where
      parseExpr' left s' = ... (similar to parseTerm')

EXAMPLES:
  parseExpr "2 + 3" -> Just (Add (Num 2) (Num 3), "")
  parseExpr "10 - 3 + 2" -> Just (Add (Sub (Num 10) (Num 3)) (Num 2), "")
  parseExpr "2 + 3 * 4" -> Just (Add (Num 2) (Mul (Num 3) (Num 4)), "")
    Notice: 3 * 4 is handled by parseTerm, maintaining correct precedence

WHY CALL parseTerm NOT parseFactor?
Because terms can contain * and /, which have higher precedence than + and -.
Calling parseTerm ensures "2 + 3 * 4" parses correctly as "2 + (3 * 4)".
-}
parseExpr :: String -> Maybe (Expr, String)
parseExpr s = Nothing  -- TODO: Implement

{- |
TODO 4: Implement the main parse function and calculate function

PURPOSE: Provide a clean interface for parsing and calculation
-}

{- |
Main parse function that validates the entire input

REQUIREMENTS:
1. Call parseExpr to parse the input string
2. Verify that the entire string was consumed (or only whitespace remains)
3. Return Either String Expr:
   - Left "error message": If parsing fails or extra characters remain
   - Right expr: If parsing succeeds completely

APPROACH:
  parse s = case parseExpr s of
    Just (expr, rest) -> 
      - Check if rest is empty or contains only whitespace
      - Use all isSpace rest to check
      - If yes, return Right expr
      - If no, return Left "Unexpected characters after expression"
    Nothing -> 
      - Return Left "Parse error"

EXAMPLES:
  parse "2 + 3" -> Right (Add (Num 2) (Num 3))
  parse "2 + 3   " -> Right (Add (Num 2) (Num 3))  (trailing space is ok)
  parse "2 + 3 x" -> Left "Unexpected characters after expression"
  parse "2 +" -> Left "Parse error"

WHY CHECK FOR REMAINING CHARACTERS?
To catch errors like "2 + 3 xyz" where "xyz" is not a valid part of the expression.
-}
parse :: String -> Either String Expr
parse s = case parseExpr s of
  Just (expr, rest) | all isSpace rest -> Right expr
  Just _ -> Left "Unexpected characters after expression"
  Nothing -> Left "Parse error"

{- |
Calculate: The main entry point combining parsing and evaluation

PURPOSE: Parse a string and evaluate it in one function call

APPROACH:
This function should combine parse and eval using the Either monad.

IMPLEMENTATION:
1. Call parse on the input string
   - If it fails, the error is automatically propagated
2. Call eval on the parsed expression
   - If it fails, the error is automatically propagated
3. Return the final result or error

USING DO-NOTATION:
  calculate input = do
    expr <- parse input    -- Parse the string
    eval expr              -- Evaluate the expression

This automatically handles both parse and eval errors!

WHY DOES THIS WORK?
The Either monad chains operations. If any step fails (returns Left),
the entire chain stops and returns that error.

EXAMPLES:
  calculate "2 + 3" -> Right 5
  calculate "10 / 0" -> Left "Division by zero"
  calculate "2 +" -> Left "Parse error"
  calculate "(2 + 3) * 4" -> Right 20

ALTERNATIVE (Without do-notation):
  calculate input = case parse input of
    Left err -> Left err
    Right expr -> eval expr
-}
calculate :: String -> Either String Int
calculate input = Left "Not implemented"  -- TODO: Implement using do-notation

>>>>>>> main

-- Main function for testing
main :: IO ()
main = do
  putStrLn "Simple Calculator - Enter expressions (or 'quit' to exit)"
  
  -- Test cases
  let tests = ["2 + 3", "10 - 4", "5 * 6", "20 / 4", "2 + 3 * 4", "(2 + 3) * 4"]
  
  putStrLn "\nTest cases:"
  mapM_ (\t -> putStrLn $ t ++ " = " ++ show (calculate t)) tests

{- |
<<<<<<< HEAD
IMPLEMENTATION GUIDE:

Step 1: Define the Expr data type
        Include all operators you want to support

Step 2: Implement eval function
        Start with simple cases, add complexity gradually

Step 3: Implement parseNumber
        Extract digits from the beginning of the string

Step 4: Implement parseFactor
        Handle numbers and parentheses

Step 5: Implement parseTerm
        Handle * and / with correct precedence

Step 6: Implement parseExpr
        Handle + and - with correct precedence

Step 7: Test thoroughly
        Test with various expressions
        Test error cases (division by zero, parse errors)

Learning Points:
- Algebraic data types
- Pattern matching
- Recursive data structures
- Parsing techniques
- Maybe/Either for error handling
=======
=============================================================================
COMPREHENSIVE IMPLEMENTATION GUIDE
=============================================================================

OVERVIEW:
This calculator project teaches you fundamental Haskell concepts through
building a practical tool. You'll implement a complete expression parser
and evaluator from scratch.

STEP-BY-STEP IMPLEMENTATION ROADMAP:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1: DATA MODELING (30 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1.1: Complete the Expr data type (TODO 1)
  □ Add constructors for Add, Sub, Mul, Div
  □ Each constructor should take two Expr parameters
  □ Test in GHCi:
    - Create: Num 5
    - Create: Add (Num 2) (Num 3)
    - Use :type to check types

Step 1.2: Understand the type structure
  □ Realize that Expr is recursive (contains Expr)
  □ Understand how this represents nested expressions
  □ Draw a tree diagram for: Add (Mul (Num 2) (Num 3)) (Num 4)

LEARNING CHECKPOINT:
Can you represent "2 * (3 + 4)" as an Expr value? Write it out.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2: EVALUATION (45 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 2.1: Implement eval for Add (TODO 2)
  □ Use do-notation with Either monad
  □ Pattern: v1 <- eval e1; v2 <- eval e2; return (v1 + v2)
  □ Test: eval (Add (Num 2) (Num 3)) should give Right 5

Step 2.2: Implement eval for Sub
  □ Follow the same pattern as Add, but subtract
  □ Test: eval (Sub (Num 10) (Num 4)) should give Right 6

Step 2.3: Implement eval for Mul
  □ Follow the same pattern, but multiply
  □ Test: eval (Mul (Num 3) (Num 4)) should give Right 12

Step 2.4: Implement eval for Div with error handling
  □ Use the same pattern for evaluation
  □ Add a check: if v2 == 0 then Left "Division by zero" else ...
  □ Test both success and error cases:
    - eval (Div (Num 10) (Num 2)) should give Right 5
    - eval (Div (Num 10) (Num 0)) should give Left "Division by zero"

Step 2.5: Test nested expressions
  □ eval (Add (Num 2) (Mul (Num 3) (Num 4)))
  □ eval (Div (Add (Num 10) (Num 5)) (Sub (Num 10) (Num 7)))

LEARNING CHECKPOINT:
Understand how the Either monad automatically propagates errors.
What happens if you evaluate Div (Add (Num 1) (Div (Num 1) (Num 0))) (Num 2)?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3: PARSING FOUNDATION (1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 3.1: Implement skipSpace helper
  □ Use dropWhile isSpace
  □ Test: skipSpace "  hello" should give "hello"

Step 3.2: Implement parseNumber (TODO 3.1)
  □ Skip leading space
  □ Use span isDigit to extract digits
  □ Check if digits is empty
  □ Use read to convert string to Int
  □ Return Just (number, rest) or Nothing
  □ Test cases:
    - parseNumber "42" → Just (42, "")
    - parseNumber "123abc" → Just (123, "abc")
    - parseNumber "xyz" → Nothing

DEBUGGING TIP:
If parseNumber isn't working, test each step separately in GHCi:
  > let s = "42abc"
  > span isDigit s
  > read "42" :: Int

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 4: FACTOR PARSING (45 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 4.1: Implement parseFactor for numbers (TODO 3.2)
  □ Skip whitespace
  □ Try parseNumber
  □ If successful, wrap in Num constructor
  □ Test: parseFactor "42" → Just (Num 42, "")

Step 4.2: Add parenthesis support to parseFactor
  □ Check if first character is '('
  □ If yes, call parseExpr recursively on the rest
  □ Verify closing ')' exists
  □ Test: parseFactor "(2)" → Just (Num 2, "")
  □ Test: parseFactor "(2 + 3)" → Just (Add (Num 2) (Num 3), "")

COMMON PITFALL:
Make sure to skip whitespace BEFORE checking for '('.
Otherwise "  (2)" won't parse correctly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 5: TERM PARSING - MULTIPLICATION AND DIVISION (1.5 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 5.1: Understand the pattern
  □ parseTerm should handle left-associative * and /
  □ Example: "2 * 3 * 4" should parse as Mul (Mul (Num 2) (Num 3)) (Num 4)
  □ This requires a helper function that accumulates from left to right

Step 5.2: Implement parseTerm structure (TODO 3.3)
  □ Parse first factor
  □ If successful, call helper function parseTerm'
  □ parseTerm' accumulates operations:
    a. Skip whitespace
    b. Check for '*' or '/'
    c. If found, parse next factor and recurse
    d. If not found, return current expression

Step 5.3: Test parseTerm thoroughly
  □ "3 * 4" → Just (Mul (Num 3) (Num 4), "")
  □ "12 / 3" → Just (Div (Num 12) (Num 3), "")
  □ "2 * 3 * 4" → Just (Mul (Mul (Num 2) (Num 3)) (Num 4), "")
  □ "5" → Just (Num 5, "")
  □ "2 * (3 + 4)" → Should parse, but + isn't handled yet (will be in parseExpr)

VISUALIZATION:
For "2 * 3 / 4":
  1. Parse 2 → left = Num 2
  2. See *, parse 3 → left = Mul (Num 2) (Num 3)
  3. See /, parse 4 → left = Div (Mul (Num 2) (Num 3)) (Num 4)
  4. No more operators → return left

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 6: EXPRESSION PARSING - ADDITION AND SUBTRACTION (1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 6.1: Implement parseExpr (TODO 3.4)
  □ Structure is identical to parseTerm
  □ But parse terms (not factors) and handle + and - (not * and /)
  □ This ensures correct precedence: * and / bind tighter than + and -

Step 6.2: Test precedence
  □ "2 + 3 * 4" → Add (Num 2) (Mul (Num 3) (Num 4))
    NOT Mul (Add (Num 2) (Num 3)) (Num 4)
  □ "2 * 3 + 4" → Add (Mul (Num 2) (Num 3)) (Num 4)

Step 6.3: Test complex expressions
  □ "2 + 3 - 4 + 5"
  □ "(2 + 3) * (4 + 5)"
  □ "10 / (2 + 3)"

UNDERSTANDING PRECEDENCE:
  parseExpr calls parseTerm
  parseTerm calls parseFactor
  parseFactor can call parseExpr (for parentheses)
  
This creates the correct precedence hierarchy!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 7: INTEGRATION (30 minutes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 7.1: Implement parse function (TODO 4)
  □ Call parseExpr
  □ Check that entire input was consumed
  □ Return Either String Expr

Step 7.2: Implement calculate function (TODO 4)
  □ Use do-notation to chain parse and eval
  □ Test all the provided test cases

Step 7.3: Run main
  □ Compile: ghc -o calculator Calculator.hs
  □ Run: ./calculator
  □ Verify all test cases pass

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TESTING STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test each function individually in GHCi before combining:
  
1. Test Expr construction:
   > :load Calculator.hs
   > Num 5
   > Add (Num 2) (Num 3)

2. Test eval:
   > eval (Num 5)
   > eval (Add (Num 2) (Num 3))
   > eval (Div (Num 10) (Num 0))

3. Test parseNumber:
   > parseNumber "42"
   > parseNumber "123abc"

4. Test parseFactor:
   > parseFactor "42"
   > parseFactor "(2 + 3)"

5. Test parseTerm:
   > parseTerm "3 * 4"
   > parseTerm "12 / 3 * 2"

6. Test parseExpr:
   > parseExpr "2 + 3"
   > parseExpr "2 + 3 * 4"

7. Test calculate:
   > calculate "2 + 3"
   > calculate "2 + 3 * 4"
   > calculate "(2 + 3) * 4"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY HASKELL CONCEPTS DEMONSTRATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ALGEBRAIC DATA TYPES (ADTs):
   - data Expr = Num Int | Add Expr Expr | ...
   - Sum types (multiple constructors) and product types (multiple fields)
   - Recursive types (Expr contains Expr)

2. PATTERN MATCHING:
   - eval (Num n) = ...
   - eval (Add e1 e2) = ...
   - Exhaustive checking by compiler

3. MAYBE TYPE:
   - Represents optional values
   - Nothing for failure, Just value for success
   - Avoids null pointer errors

4. EITHER TYPE:
   - Represents success or failure with error messages
   - Left error for failure, Right value for success
   - Used for better error reporting than Maybe

5. MONADIC COMPOSITION:
   - do-notation for chaining operations
   - Automatic error propagation
   - Clean, readable code

6. PURE FUNCTIONS:
   - No side effects
   - Same input always produces same output
   - Easy to test and reason about

7. RECURSION:
   - Recursive data structures (Expr)
   - Recursive functions (eval, parseTerm')
   - Natural fit for tree-like structures

8. TYPE INFERENCE:
   - Compiler infers types automatically
   - Strong type safety without verbose annotations
   - Catches errors at compile time

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMON MISTAKES AND HOW TO AVOID THEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. FORGETTING TO SKIP WHITESPACE:
   Problem: "2 + 3" fails to parse
   Solution: Always call skipSpace before checking characters

2. INCORRECT PRECEDENCE:
   Problem: "2 + 3 * 4" evaluates as (2 + 3) * 4 = 20 instead of 14
   Solution: Ensure parseExpr calls parseTerm, not parseFactor

3. NOT HANDLING REMAINING INPUT:
   Problem: "2 + 3 xyz" parses successfully
   Solution: Check that remaining string is empty in parse function

4. PATTERN MATCH ERRORS:
   Problem: Non-exhaustive patterns warning
   Solution: Handle all constructors in eval and parsers

5. READING ERRORS:
   Problem: read "abc" :: Int crashes
   Solution: Check that string contains only digits before calling read

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXTENSIONS FOR FURTHER LEARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After completing the basic calculator, try these extensions:

1. Add more operators:
   - Modulo (%)
   - Exponentiation (^)
   - Unary minus (-)

2. Support floating-point numbers:
   - Change Int to Double
   - Update parseNumber to handle decimals

3. Add variables:
   - data Expr = ... | Var String
   - Pass an environment to eval: eval :: Expr -> Map String Int -> Either String Int

4. Add functions:
   - sqrt, sin, cos, abs, etc.
   - data Expr = ... | Call String Expr

5. Better error messages:
   - Track position in input string
   - Show what was expected vs. what was found

6. Use parser combinator library:
   - Learn Parsec or Megaparsec
   - Compare to your hand-written parser

7. Add REPL (Read-Eval-Print Loop):
   - Read expressions from stdin
   - Store variables between evaluations
   - Add commands like :help, :quit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEARNING RESOURCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Books:
  - "Learn You a Haskell" - Chapters 2-8 (basics, types, functions)
  - "Programming in Haskell" by Graham Hutton - Chapter 13 (parsing)
  - "Real World Haskell" - Chapter 16 (parsers)

Online:
  - Haskell Wiki: https://wiki.haskell.org/Parsing
  - School of Haskell tutorials
  - Hoogle for function search: https://hoogle.haskell.org/

Practice:
  - Exercism.io Haskell track
  - 99 Haskell Problems
  - Project Euler in Haskell

>>>>>>> main
-}
