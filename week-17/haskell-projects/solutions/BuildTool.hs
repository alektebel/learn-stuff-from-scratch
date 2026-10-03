-- Build Tool in Haskell - Solution Template
-- This is a reference implementation showing the structure
--
-- NOTE: This is a template showing what the solution should contain.
-- The actual detailed implementation would be filled in by students
-- or provided as a complete reference solution.

module BuildTool where

import System.Directory
import System.Process
import System.FilePath
import Data.Time
import Data.Maybe
import Data.List
import qualified Data.Map as Map
import qualified Data.Set as Set
import Control.Monad
import Control.Exception

-- Data structures
data Target = Target
  { targetName    :: String
  , targetDeps    :: [String]
  , targetCommand :: Maybe String
  , targetPhony   :: Bool
  } deriving (Show, Eq)

data BuildConfig = BuildConfig
  { buildTargets :: Map.Map String Target
  , buildDefault :: Maybe String
  } deriving (Show, Eq)

type BuildResult = Either String [String]

-- Parse a single target from lines
parseTarget :: [String] -> Maybe (Target, [String])
parseTarget [] = Nothing
parseTarget (line:rest) = 
  -- Implementation would:
  -- 1. Split line on ':'
  -- 2. Extract target name and dependencies
  -- 3. Look for command line (starting with tab)
  -- 4. Create Target record
  Nothing  -- Placeholder

-- Parse phony declarations
parsePhony :: String -> [String]
parsePhony line = 
  -- Implementation would check for ".PHONY:" prefix
  -- and extract target names
  []  -- Placeholder

-- Parse complete buildfile
parseBuildFile :: String -> Either String BuildConfig
parseBuildFile content = 
  -- Implementation would:
  -- 1. Split into lines
  -- 2. Remove comments and empty lines
  -- 3. Parse .PHONY declarations
  -- 4. Parse all targets
  -- 5. Build BuildConfig
  Left "Solution not yet implemented"

-- Build dependency graph
buildDepGraph :: BuildConfig -> Map.Map String [String]
buildDepGraph config = 
  -- Implementation would convert BuildConfig to dependency graph
  Map.empty  -- Placeholder

-- Detect cycles in dependency graph
detectCycles :: Map.Map String [String] -> Maybe String
detectCycles graph = 
  -- Implementation would use DFS to find cycles
  Nothing  -- Placeholder

-- Topological sort
topologicalSort :: Map.Map String [String] -> Either String [String]
topologicalSort graph = 
  -- Implementation would use Kahn's algorithm or DFS-based approach
  Left "Not implemented"

-- Get file modification time
getFileTime :: FilePath -> IO (Maybe UTCTime)
getFileTime path = do
  result <- try (getModificationTime path) :: IO (Either SomeException UTCTime)
  case result of
    Left _ -> return Nothing
    Right time -> return (Just time)

-- Check if target needs rebuilding
needsRebuild :: Target -> BuildConfig -> IO Bool
needsRebuild target config = 
  -- Implementation would:
  -- 1. Check if phony -> always rebuild
  -- 2. Check if target exists -> rebuild if not
  -- 3. Compare timestamps with dependencies
  return True  -- Placeholder (always rebuild)

-- Execute a shell command
executeCommand :: String -> IO (Either String String)
executeCommand command = do
  (exitCode, stdout, stderr) <- readProcessWithExitCode "sh" ["-c", command] ""
  case exitCode of
    ExitSuccess -> return $ Right stdout
    ExitFailure code -> return $ Left $ 
      "Command failed (exit code " ++ show code ++ "): " ++ stderr

-- Build a single target
buildTarget :: Target -> BuildConfig -> IO (Either String ())
buildTarget target config = do
  rebuild <- needsRebuild target config
  if not rebuild
    then do
      putStrLn $ "Target '" ++ targetName target ++ "' is up-to-date"
      return $ Right ()
    else case targetCommand target of
      Nothing -> do
        -- No command (might be phony or file dependency)
        return $ Right ()
      Just cmd -> do
        putStrLn $ "Building '" ++ targetName target ++ "'..."
        result <- executeCommand cmd
        case result of
          Left err -> return $ Left err
          Right output -> do
            unless (null output) $ putStrLn output
            return $ Right ()

-- Build multiple targets in order
buildTargets :: [String] -> BuildConfig -> IO BuildResult
buildTargets targetNames config = 
  -- Implementation would:
  -- 1. Build dependency graph
  -- 2. Check for cycles
  -- 3. Topological sort
  -- 4. Build each target in order
  return $ Left "Not implemented"

-- Build default target
buildDefault :: BuildConfig -> IO BuildResult
buildDefault config = 
  case buildDefault config of
    Nothing -> return $ Left "No default target specified"
    Just target -> buildTargets [target] config

-- Parse command-line arguments
parseArgs :: [String] -> Either String (FilePath, [String])
parseArgs [] = Right ("Buildfile", [])
parseArgs ("-f":file:rest) = Right (file, rest)
parseArgs targets = Right ("Buildfile", targets)

-- Main entry point
main :: IO ()
main = do
  putStrLn "=== Build Tool - Solution Template ==="
  putStrLn ""
  putStrLn "Complete implementation would include:"
  putStrLn "- Buildfile parsing (Makefile-like syntax)"
  putStrLn "- Dependency graph construction"
  putStrLn "- Cycle detection"
  putStrLn "- Topological sorting for build order"
  putStrLn "- Timestamp-based incremental builds"
  putStrLn "- Command execution"
  putStrLn "- Error handling and reporting"
  putStrLn ""
  putStrLn "Example buildfile format:"
  putStrLn ".PHONY: clean test"
  putStrLn ""
  putStrLn "app: main.o utils.o"
  putStrLn "\tgcc -o app main.o utils.o"
  putStrLn ""
  putStrLn "main.o: main.c"
  putStrLn "\tgcc -c main.c"
  putStrLn ""
  putStrLn "clean:"
  putStrLn "\trm -f *.o app"
  putStrLn ""
  putStrLn "Usage:"
  putStrLn "  build-tool          # Build default target"
  putStrLn "  build-tool app      # Build specific target"
  putStrLn "  build-tool -f file  # Use custom buildfile"

{-
SOLUTION NOTES:

This template shows the structure of the complete solution.
A full implementation would include:

1. Complete buildfile parsing:
   - Target and dependency extraction
   - Command line parsing (tab-indented)
   - .PHONY declarations
   - Comment and whitespace handling

2. Dependency graph operations:
   - Graph construction from BuildConfig
   - Cycle detection with DFS
   - Topological sorting (Kahn's or DFS-based)

3. Timestamp-based builds:
   - File modification time checking
   - Comparison logic for incremental builds
   - Phony target handling

4. Command execution:
   - Shell command invocation
   - Output and error capture
   - Exit code handling

5. Build orchestration:
   - Target resolution
   - Build order determination
   - Sequential execution
   - Error propagation

6. CLI interface:
   - Argument parsing
   - Buildfile loading
   - Progress reporting
   - Error display

The implementation would be approximately 400-500 lines
with comprehensive error handling, edge case coverage,
and potentially parallel build support.

EXAMPLE BUILDFILE:
# Build configuration
.PHONY: clean test all

all: app

app: main.o utils.o
	gcc -o app main.o utils.o

main.o: main.c
	gcc -c main.c

utils.o: utils.c
	gcc -c utils.c

test: app
	./app --test

clean:
	rm -f *.o app

ADVANCED FEATURES (Extensions):
- Parallel builds with async
- Pattern rules (%.o: %.c)
- Variables and substitution
- Automatic dependency detection
- Build caching
- Progress indicators
- Color output
-}
