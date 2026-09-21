-- Simple Calculator in Haskell - Complete Solution

module Main where

import Data.Char (isDigit, isSpace)

-- Expression data type
data Expr = Num Int
          | Add Expr Expr
          | Sub Expr Expr
          | Mul Expr Expr
          | Div Expr Expr
  deriving (Show, Eq)

-- Evaluate an expression
eval :: Expr -> Either String Int
eval (Num n) = Right n
eval (Add e1 e2) = do
  v1 <- eval e1
  v2 <- eval e2
  return (v1 + v2)
eval (Sub e1 e2) = do
  v1 <- eval e1
  v2 <- eval e2
  return (v1 - v2)
eval (Mul e1 e2) = do
  v1 <- eval e1
  v2 <- eval e2
  return (v1 * v2)
eval (Div e1 e2) = do
  v1 <- eval e1
  v2 <- eval e2
  if v2 == 0
    then Left "Division by zero"
    else Right (v1 `div` v2)

-- Skip whitespace
skipSpace :: String -> String
skipSpace = dropWhile isSpace

-- Parse a number
parseNumber :: String -> Maybe (Int, String)
parseNumber s =
  let s' = skipSpace s
      (digits, rest) = span isDigit s'
  in if null digits
     then Nothing
     else Just (read digits, rest)

-- Parse a factor (number or parenthesized expression)
parseFactor :: String -> Maybe (Expr, String)
parseFactor s =
  let s' = skipSpace s
  in case s' of
    ('(':rest) -> case parseExpr rest of
      Just (expr, ')':rest') -> Just (expr, rest')
      _ -> Nothing
    _ -> case parseNumber s' of
      Just (n, rest) -> Just (Num n, rest)
      Nothing -> Nothing

-- Parse a term (handles * and /)
parseTerm :: String -> Maybe (Expr, String)
parseTerm s = case parseFactor s of
  Nothing -> Nothing
  Just (expr, rest) -> parseTerm' expr rest
  where
    parseTerm' left s' =
      let s'' = skipSpace s'
      in case s'' of
        ('*':rest) -> case parseFactor rest of
          Just (right, rest') -> parseTerm' (Mul left right) rest'
          Nothing -> Nothing
        ('/':rest) -> case parseFactor rest of
          Just (right, rest') -> parseTerm' (Div left right) rest'
          Nothing -> Nothing
        _ -> Just (left, s'')

-- Parse an expression (handles + and -)
parseExpr :: String -> Maybe (Expr, String)
parseExpr s = case parseTerm s of
  Nothing -> Nothing
  Just (expr, rest) -> parseExpr' expr rest
  where
    parseExpr' left s' =
      let s'' = skipSpace s'
      in case s'' of
        ('+':rest) -> case parseTerm rest of
          Just (right, rest') -> parseExpr' (Add left right) rest'
          Nothing -> Nothing
        ('-':rest) -> case parseTerm rest of
          Just (right, rest') -> parseExpr' (Sub left right) rest'
          Nothing -> Nothing
        _ -> Just (left, s'')

-- Main parse function
parse :: String -> Either String Expr
parse s = case parseExpr s of
  Just (expr, rest) -> 
    if all isSpace rest
      then Right expr
      else Left "Unexpected characters after expression"
  Nothing -> Left "Parse error"

-- Calculate: parse and evaluate
calculate :: String -> Either String Int
calculate input = do
  expr <- parse input
  eval expr

-- Main function
main :: IO ()
main = do
  putStrLn "Simple Calculator - Complete Solution\n"
  
  let tests = 
        [ "2 + 3"
        , "10 - 4"
        , "5 * 6"
        , "20 / 4"
        , "2 + 3 * 4"
        , "(2 + 3) * 4"
        , "100 / (5 + 5)"
        , "15 - 3 * 2 + 7"
        ]
  
  putStrLn "Test cases:"
  mapM_ testCase tests
  where
    testCase expr = putStrLn $ expr ++ " = " ++ formatResult (calculate expr)
    formatResult (Right n) = show n
    formatResult (Left err) = "Error: " ++ err
