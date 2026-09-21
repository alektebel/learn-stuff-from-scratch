-- Build Tool in Haskell - Template
-- Create a build system similar to Make that handles dependencies and incremental builds
--
-- LEARNING OBJECTIVES:
-- 1. Work with file system operations in IO
-- 2. Model and traverse dependency graphs
-- 3. Implement topological sorting
-- 4. Handle timestamps for incremental builds
-- 5. Execute external commands
-- 6. Parse configuration files
-- 7. Implement parallel build execution
--
-- ESTIMATED TIME: 8-12 hours for beginners, 5-7 hours for intermediate
--
-- REQUIRED LIBRARIES:
-- Install with: cabal install directory process filepath time containers
-- Or add to your .cabal file

module BuildTool where

import System.Directory
import System.Process
import System.FilePath
import System.IO
import Data.Time
import Data.Maybe
import Data.List
import qualified Data.Map as Map
import qualified Data.Set as Set
import Control.Monad
import Control.Exception

{- |
TODO 1: Define data structures for build configuration

CONCEPT: Build System Architecture
A build system needs to track:
- Targets: What to build (e.g., "myapp.exe", "test.o")
- Dependencies: What each target depends on
- Commands: How to build each target
- Timestamps: When files were last modified
-}

{- |
Build target definition

FIELDS:
- targetName: Name of the target (e.g., "app", "test.o")
- targetDeps: List of dependencies (files or other targets)
- targetCommand: Command to build this target (optional, might be phony)
- targetPhony: Whether this is a phony target (doesn't produce a file)

EXAMPLE:
  Target "app" ["main.o", "utils.o"] (Just "gcc -o app main.o utils.o") False

PHONY TARGETS:
Some targets don't produce files (e.g., "clean", "test").
These are called phony targets.

DERIVING:
- Show: For debugging
- Eq: For comparisons
-}
data Target = Target
  { targetName    :: String
  , targetDeps    :: [String]
  , targetCommand :: Maybe String
  , targetPhony   :: Bool
  } deriving (Show, Eq)

{- |
Build configuration (entire build file)

FIELDS:
- buildTargets: Map from target name to Target
- buildDefault: Default target to build (if no target specified)

EXAMPLE:
  BuildConfig 
    { buildTargets = Map.fromList [("app", Target ...)]
    , buildDefault = Just "app"
    }
-}
data BuildConfig = BuildConfig
  { buildTargets :: Map.Map String Target
  , buildDefault :: Maybe String
  } deriving (Show, Eq)

{- |
Build result type

LEFT: Error message
RIGHT: Success with list of targets that were built
-}
type BuildResult = Either String [String]

{- |
TODO 2: Implement buildfile parsing

CONCEPT: Configuration File Format
We'll use a simple format similar to Make:

target: dependency1 dependency2
	command to build target

another-target: dependency
	command

RULES:
- Target line: "target: dep1 dep2 dep3"
- Command line: starts with tab, contains shell command
- Empty lines are ignored
- Lines starting with # are comments
- Phony targets: ".PHONY: target1 target2"
-}

{- |
Parse a single target definition from lines

APPROACH:
1. First line format: "target: dep1 dep2 dep3"
   - Split on ':'
   - Left side is target name (trimmed)
   - Right side is space-separated dependencies
2. Following lines (starting with tab) are commands
   - Usually just one command line
   - Can have multiple for complex builds

RETURN: Maybe (Target, remaining lines)
- Just (target, rest): Successfully parsed a target
- Nothing: Failed to parse (invalid format)

PARSING STEPS:
1. Take first line, split on ':'
2. Extract target name (before :)
3. Extract dependencies (after :, split on spaces)
4. Look at next lines starting with tab
5. First tab line is the command
6. Create Target record

EXAMPLE INPUT:
  ["app: main.o utils.o", "\tgcc -o app main.o utils.o", "next-target: ..."]
  
EXAMPLE OUTPUT:
  Just (Target "app" ["main.o", "utils.o"] (Just "gcc ...") False, ["next-target: ..."])

HINTS:
- Use span to split on newlines
- Use break to find the ':' in target line
- Use words to split dependencies
- Use stripPrefix to check for tab
- Handle edge cases: no command, empty dependencies
-}
parseTarget :: [String] -> Maybe (Target, [String])
parseTarget [] = Nothing
parseTarget (line:rest) = undefined  -- TODO: Implement

{- |
Parse phony target declarations

FORMAT: .PHONY: target1 target2 target3

PURPOSE: Mark targets that don't produce files

APPROACH:
1. Check if line starts with ".PHONY:"
2. Extract target names after ":"
3. Return list of phony target names

RETURN: [String] - List of phony target names

EXAMPLE:
  parsePhony ".PHONY: clean test all"
  → ["clean", "test", "all"]
  
  parsePhony "app: main.c"
  → []

IMPLEMENTATION:
  if ".PHONY:" `isPrefixOf` line
    then parse targets after :
    else return []
-}
parsePhony :: String -> [String]
parsePhony line = []  -- TODO: Implement

{- |
Parse complete buildfile

APPROACH:
1. Read file contents
2. Split into lines
3. Remove comments (lines starting with #)
4. Remove empty lines
5. Parse .PHONY declarations
6. Parse target definitions
7. Build BuildConfig

ALGORITHM:
1. Filter lines:
   - Remove empty lines: filter (not . null)
   - Remove comments: filter (not . ("#" `isPrefixOf`))
2. Collect phony targets:
   - Find all .PHONY lines
   - Parse them with parsePhony
   - Combine into a Set
3. Parse targets:
   - Use parseTarget repeatedly
   - Mark phony targets based on Set from step 2
   - Build Map from target name to Target
4. Find default target (first non-phony target)

RETURN: Either String BuildConfig
- Left error: Parse error with message
- Right config: Successfully parsed configuration

EXAMPLE FILE:
  # Build configuration
  .PHONY: clean test
  
  app: main.o utils.o
    gcc -o app main.o utils.o
  
  clean:
    rm -f *.o app

RESULT:
  Right $ BuildConfig
    { buildTargets = Map with "app" and "clean" targets
    , buildDefault = Just "app"
    }

ERROR CASES:
- Invalid target format
- Missing dependencies
- Duplicate target names
-}
parseBuildFile :: String -> Either String BuildConfig
parseBuildFile content = Left "Not implemented"  -- TODO: Implement

{- |
TODO 3: Implement dependency graph operations

CONCEPT: Dependency Graphs
Build systems need to understand dependency relationships:
- A depends on B: B must be built before A
- Cycles are errors: A depends on B depends on A
- Topological sort: Find valid build order

GRAPH REPRESENTATION:
We'll use Map.Map String [String] where:
- Key: Target name
- Value: List of dependencies
-}

{- |
Build dependency graph from BuildConfig

APPROACH:
Convert BuildConfig to a dependency graph (Map).

ALGORITHM:
For each target in buildTargets:
  - Add entry: target name -> list of dependencies
  - Only include dependencies that are also targets
  - File dependencies (not targets) are leaf nodes

RETURN: Map.Map String [String]

EXAMPLE:
  BuildConfig with targets:
    app -> [main.o, utils.o]
    main.o -> [main.c]
    utils.o -> [utils.c]
  
  Dependency graph:
    Map.fromList 
      [ ("app", ["main.o", "utils.o"])
      , ("main.o", ["main.c"])
      , ("utils.o", ["utils.c"])
      ]

NOTE: main.c and utils.c are files, not targets,
so they don't have entries in the map.
-}
buildDepGraph :: BuildConfig -> Map.Map String [String]
buildDepGraph config = Map.empty  -- TODO: Implement

{- |
Detect cycles in dependency graph

PURPOSE: Cycles make builds impossible (circular dependencies)

APPROACH: Use depth-first search (DFS)
1. Track visited nodes
2. Track nodes in current path
3. If we visit a node already in path → cycle found

ALGORITHM:
  detectCycle graph = dfs Set.empty Set.empty (Map.keys graph)
  where
    dfs visited path [] = Nothing  -- No cycle
    dfs visited path (node:rest)
      | node `Set.member` path = Just cycle_description
      | node `Set.member` visited = dfs visited path rest
      | otherwise = 
          case graph Map.! node of
            deps -> 
              case dfs visited (Set.insert node path) deps of
                Just cycle -> Just cycle
                Nothing -> dfs (Set.insert node visited) path rest

RETURN: Maybe String
- Nothing: No cycles detected
- Just cycle_desc: Cycle found with description

EXAMPLE:
  Graph: A -> [B], B -> [C], C -> [A]
  Result: Just "Cycle detected: A -> B -> C -> A"

HINTS:
- Use Set for efficient membership testing
- Track path separately from visited
- Return cycle path when detected
-}
detectCycles :: Map.Map String [String] -> Maybe String
detectCycles graph = Nothing  -- TODO: Implement

{- |
Topological sort of dependency graph

PURPOSE: Find valid build order (dependencies before dependents)

CONCEPT:
Topological sort orders nodes such that for every edge A -> B,
A comes before B in the ordering.

ALGORITHM (Kahn's algorithm):
1. Find all nodes with no dependencies (in-degree = 0)
2. Add them to result and remove from graph
3. Repeat until graph is empty
4. If graph not empty after process → cycle exists

ALTERNATIVE (DFS-based):
1. Do post-order DFS traversal
2. Add nodes to result when finishing their DFS
3. Reverse the result

RETURN: Either String [String]
- Left error: Cycle detected or other error
- Right order: Valid build order

EXAMPLE:
  Graph: app -> [main.o, utils.o], main.o -> [], utils.o -> []
  Result: Right ["main.o", "utils.o", "app"]
    (or ["utils.o", "main.o", "app"] - both valid)

IMPLEMENTATION HINTS:
- Calculate in-degrees for all nodes
- Use queue for nodes with in-degree 0
- Remove edges as you process nodes
- Check for cycles (remaining nodes after processing)
-}
topologicalSort :: Map.Map String [String] -> Either String [String]
topologicalSort graph = Left "Not implemented"  -- TODO: Implement

{- |
TODO 4: Implement timestamp-based build decisions

CONCEPT: Incremental Builds
Only rebuild targets if:
1. Target file doesn't exist, OR
2. Any dependency is newer than target

This avoids rebuilding everything every time.
-}

{- |
Get file modification time

PURPOSE: Find when a file was last modified

APPROACH:
1. Use getModificationTime from System.Directory
2. Handle case where file doesn't exist
3. Return Maybe UTCTime

RETURN: IO (Maybe UTCTime)
- Just time: File exists, modification time
- Nothing: File doesn't exist

EXAMPLE:
  getFileTime "main.o" → IO (Just 2024-01-15 10:30:00)
  getFileTime "nonexistent" → IO Nothing

IMPLEMENTATION:
Use try to catch exceptions:
  result <- try (getModificationTime path) :: IO (Either SomeException UTCTime)
  case result of
    Left _ -> return Nothing
    Right time -> return (Just time)
-}
getFileTime :: FilePath -> IO (Maybe UTCTime)
getFileTime path = undefined  -- TODO: Implement

{- |
Check if target needs rebuilding

PURPOSE: Determine if we should rebuild a target

DECISION LOGIC:
1. If target is phony → always build
2. If target file doesn't exist → build
3. If any dependency is newer than target → build
4. Otherwise → skip (target is up-to-date)

APPROACH:
1. Get target modification time
2. Get modification times of all dependencies
3. Compare times
4. Return True if rebuild needed, False otherwise

PARAMETERS:
- target: The Target to check
- config: BuildConfig (to lookup dependencies)

RETURN: IO Bool
- True: Needs rebuild
- False: Up-to-date, skip

EXAMPLES:
  needsRebuild (Target "app" ["main.o"] ...) config
  
  Scenarios:
  1. app doesn't exist → True
  2. main.o newer than app → True
  3. app newer than main.o → False
  4. Phony target → True

IMPLEMENTATION STEPS:
1. Check if target is phony → return True
2. Get target file time
3. If target doesn't exist → return True
4. Get dependency times
5. If any dependency newer → return True
6. Otherwise → return False

HINTS:
- Use getFileTime for each file
- Compare UTCTime with (>), (<)
- Handle missing files appropriately
-}
needsRebuild :: Target -> BuildConfig -> IO Bool
needsRebuild target config = undefined  -- TODO: Implement

{- |
TODO 5: Implement command execution

CONCEPT: Running Build Commands
Once we know what to build, we need to execute the commands.
-}

{- |
Execute a shell command

PURPOSE: Run a build command and capture output/errors

APPROACH:
1. Use System.Process to run command
2. Capture stdout and stderr
3. Check exit code
4. Return result

RETURN: IO (Either String String)
- Left error: Command failed with error message
- Right output: Command succeeded with output

IMPLEMENTATION:
Use readProcessWithExitCode:
  (exitCode, stdout, stderr) <- readProcessWithExitCode "sh" ["-c", command] ""
  case exitCode of
    ExitSuccess -> return (Right stdout)
    ExitFailure code -> return (Left $ "Command failed with code " ++ show code ++ ": " ++ stderr)

PARAMETERS:
- command: Shell command to execute

EXAMPLE:
  executeCommand "gcc -o app main.o"
  → IO (Right "") on success
  → IO (Left "error message") on failure

NOTES:
- Use "sh -c" to run shell commands
- Capture both stdout and stderr
- Include error details in failure message
-}
executeCommand :: String -> IO (Either String String)
executeCommand command = undefined  -- TODO: Implement

{- |
Build a single target

PURPOSE: Build one target if needed

APPROACH:
1. Check if rebuild is needed (needsRebuild)
2. If not needed:
   a. Print "Target 'X' is up-to-date"
   b. Return success
3. If needed:
   a. Print "Building 'X'..."
   b. Execute build command (if exists)
   c. Handle success/failure
   d. Return result

PARAMETERS:
- target: Target to build
- config: BuildConfig

RETURN: IO (Either String ())
- Left error: Build failed
- Right (): Build succeeded (or skipped)

EXAMPLES:
  buildTarget (Target "app" [...] (Just "gcc ...") False) config
  
  Output:
    Building 'app'...
    [gcc output]
    Success
  
  OR
    Target 'app' is up-to-date

IMPLEMENTATION STEPS:
1. Call needsRebuild
2. If False:
   - Print up-to-date message
   - Return Right ()
3. If True and command exists:
   - Print building message
   - Call executeCommand
   - Check result
   - Return success or propagate error
4. If True but no command:
   - Print warning
   - Return success (might be phony or file dependency)

ERROR HANDLING:
- Command execution failures
- Missing commands for targets that need them
-}
buildTarget :: Target -> BuildConfig -> IO (Either String ())
buildTarget target config = undefined  -- TODO: Implement

{- |
TODO 6: Implement complete build system

CONCEPT: Orchestrating the Build
Combine all pieces to build targets in correct order.
-}

{- |
Build multiple targets in topological order

PURPOSE: Build a list of targets respecting dependencies

APPROACH:
1. Create dependency graph
2. Check for cycles
3. Topologically sort targets
4. Build each target in order
5. Stop on first error or continue to end

PARAMETERS:
- targetNames: Names of targets to build
- config: BuildConfig

RETURN: IO BuildResult
- Left error: Build failed or cycle detected
- Right builtTargets: List of targets that were built

ALGORITHM:
1. Lookup all targets from targetNames
2. Build dependency graph for these targets
3. Detect cycles → return error if found
4. Topological sort → get build order
5. For each target in order:
   a. Build the target
   b. If fails, return error
   c. If succeeds, continue
6. Return list of successfully built targets

EXAMPLE:
  buildTargets ["app"] config
  
  Steps:
  1. app depends on [main.o, utils.o]
  2. Order: [main.o, utils.o, app]
  3. Build main.o → success
  4. Build utils.o → success
  5. Build app → success
  6. Return Right ["main.o", "utils.o", "app"]

ERROR CASES:
- Unknown target name
- Circular dependencies
- Build command failures
-}
buildTargets :: [String] -> BuildConfig -> IO BuildResult
buildTargets targetNames config = undefined  -- TODO: Implement

{- |
Build the default target

PURPOSE: Build default target when no target specified

APPROACH:
1. Check if buildDefault is set
2. If set, build that target
3. If not set, return error

RETURN: IO BuildResult
-}
buildDefault :: BuildConfig -> IO BuildResult
buildDefault config = undefined  -- TODO: Implement

{- |
TODO 7: Implement main interface

CONCEPT: Command-Line Interface
Provide user-friendly interface to the build tool.
-}

{- |
Parse command-line arguments

PURPOSE: Understand what user wants to build

APPROACH:
Parse arguments like:
- build-tool: Build default target
- build-tool target1: Build target1
- build-tool target1 target2: Build multiple targets
- build-tool -f buildfile.txt target: Use custom buildfile

RETURN: Either String (FilePath, [String])
- Left error: Invalid arguments
- Right (buildfile, targets): Parsed successfully
  - buildfile: Path to buildfile
  - targets: List of target names (empty = default)

EXAMPLES:
  [] → Right ("Buildfile", [])
  ["app"] → Right ("Buildfile", ["app"])
  ["-f", "custom.build", "test"] → Right ("custom.build", ["test"])

IMPLEMENTATION:
Pattern match on argument list:
  parseArgs [] = Right ("Buildfile", [])
  parseArgs ("-f":file:rest) = Right (file, rest)
  parseArgs targets = Right ("Buildfile", targets)
-}
parseArgs :: [String] -> Either String (FilePath, [String])
parseArgs args = undefined  -- TODO: Implement

{- |
Main entry point

PURPOSE: Read buildfile and execute build

APPROACH:
1. Parse command-line arguments
2. Read buildfile
3. Parse buildfile
4. Build requested targets (or default)
5. Report results

IMPLEMENTATION:
  main = do
    args <- getArgs
    case parseArgs args of
      Left err -> error message
      Right (buildfile, targets) -> do
        content <- readFile buildfile
        case parseBuildFile content of
          Left err -> error message
          Right config -> do
            result <- if null targets
                      then buildDefault config
                      else buildTargets targets config
            case result of
              Left err -> error message
              Right built -> success message

OUTPUT FORMAT:
  === Build Tool ===
  Reading: Buildfile
  Building targets: [app]
  
  Building 'main.o'...
  [command output]
  
  Building 'utils.o'...
  [command output]
  
  Building 'app'...
  [command output]
  
  === Build succeeded ===
  Built: main.o, utils.o, app
-}
main :: IO ()
main = do
  putStrLn "=== Build Tool ==="
  -- TODO: Implement main logic

{- |
=============================================================================
COMPREHENSIVE IMPLEMENTATION GUIDE
=============================================================================

OVERVIEW:
This build tool project is the most complex in this series. It combines
file system operations, graph algorithms, process execution, and configuration
parsing. Take your time and implement incrementally.

PREREQUISITES:
- Strong understanding of IO monad
- Familiarity with Map and Set data structures
- Basic graph algorithm knowledge
- Comfort with file system operations

LIBRARY INSTALLATION:
  cabal update
  cabal install directory process filepath time containers

STEP-BY-STEP IMPLEMENTATION ROADMAP:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1: DATA STRUCTURES (1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1.1: Review Target and BuildConfig types
  □ Already defined for you
  □ Understand each field's purpose
  □ Think about how they relate to Make

Step 1.2: Create test data
  □ Manually create sample Target values
  □ Create sample BuildConfig in GHCi
  □ Verify Show instances work

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2: PARSING (3-4 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 2.1: Implement parsePhony (TODO 2)
  □ Simple string parsing
  □ Test with .PHONY declarations
  □ Handle edge cases

Step 2.2: Implement parseTarget (TODO 2)
  □ Parse target line (name and dependencies)
  □ Parse command line (starts with tab)
  □ Create Target record
  □ Test with simple examples

Step 2.3: Implement parseBuildFile (TODO 2)
  □ Split into lines
  □ Filter comments and empty lines
  □ Parse .PHONY declarations
  □ Parse all targets
  □ Build BuildConfig
  □ Test with sample buildfile

Step 2.4: Create test buildfile
  □ Write simple buildfile
  □ Test parsing thoroughly
  □ Add complex cases (multiple dependencies, phony targets)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3: DEPENDENCY GRAPH (2-3 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 3.1: Implement buildDepGraph (TODO 3)
  □ Convert BuildConfig to Map
  □ Test with sample configs
  □ Verify graph structure

Step 3.2: Implement detectCycles (TODO 3)
  □ DFS-based cycle detection
  □ Test with acyclic graph → Nothing
  □ Test with cyclic graph → Just error

Step 3.3: Implement topologicalSort (TODO 3)
  □ Choose algorithm (Kahn's or DFS)
  □ Implement carefully
  □ Test with various graphs
  □ Verify correct ordering

DEBUGGING TIPS:
- Print intermediate steps
- Test with small graphs first
- Draw graphs on paper
- Verify with known correct orderings

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 4: TIMESTAMP CHECKING (1-2 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 4.1: Implement getFileTime (TODO 4)
  □ Use getModificationTime
  □ Handle missing files
  □ Test with real files

Step 4.2: Implement needsRebuild (TODO 4)
  □ Check target existence
  □ Compare timestamps
  □ Handle phony targets
  □ Test various scenarios

Step 4.3: Test incremental builds
  □ Create test files
  □ Modify dependencies
  □ Verify rebuild decisions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 5: COMMAND EXECUTION (1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 5.1: Implement executeCommand (TODO 5)
  □ Use readProcessWithExitCode
  □ Capture output
  □ Handle errors
  □ Test with simple commands

Step 5.2: Implement buildTarget (TODO 5)
  □ Check if rebuild needed
  □ Execute command if needed
  □ Print appropriate messages
  □ Test with real build commands

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 6: BUILD ORCHESTRATION (2 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 6.1: Implement buildTargets (TODO 6)
  □ Build dependency graph
  □ Check for cycles
  □ Topologically sort
  □ Build each target in order
  □ Collect results

Step 6.2: Implement buildDefault (TODO 6)
  □ Simple wrapper around buildTargets
  □ Use buildDefault from config

Step 6.3: Test complete builds
  □ Create real buildfile
  □ Test building various targets
  □ Verify correct order
  □ Test incremental rebuilds

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 7: CLI INTERFACE (1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 7.1: Implement parseArgs (TODO 7)
  □ Parse command-line arguments
  □ Handle -f flag
  □ Test with various inputs

Step 7.2: Implement main (TODO 7)
  □ Tie everything together
  □ Read buildfile
  □ Parse configuration
  □ Execute build
  □ Print results

Step 7.3: End-to-end testing
  □ Compile build tool
  □ Create test project with buildfile
  □ Run build tool
  □ Verify everything works

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY HASKELL CONCEPTS DEMONSTRATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ADVANCED IO:
   - File system operations
   - Process execution
   - Exception handling

2. DATA STRUCTURES:
   - Maps for configuration
   - Sets for cycle detection
   - Graphs for dependencies

3. ALGORITHMS:
   - DFS for cycle detection
   - Topological sorting
   - Graph traversal

4. PARSING:
   - Configuration file parsing
   - String manipulation
   - Error handling

5. SYSTEM PROGRAMMING:
   - Command execution
   - File timestamps
   - Path manipulation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXTENSIONS FOR FURTHER LEARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. PARALLEL BUILDS:
   - Build independent targets concurrently
   - Use async library
   - Respect dependency constraints

2. PATTERN RULES:
   - %.o: %.c pattern
   - Automatic target generation
   - Similar to Make's pattern rules

3. VARIABLES:
   - CC = gcc
   - CFLAGS = -O2 -Wall
   - Variable substitution

4. AUTOMATIC DEPENDENCIES:
   - Parse #include directives
   - Generate dependency files
   - Auto-update on header changes

5. CACHING:
   - Cache build results
   - Content-based hashing
   - Like ccache

6. PROGRESS DISPLAY:
   - Show build progress
   - [1/10] Building main.o
   - Color output

7. WATCH MODE:
   - Watch files for changes
   - Rebuild automatically
   - Like nodemon or watchexec

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE BUILDFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Sample buildfile for C project
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TESTING STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Unit tests:
   - Test each function independently
   - Use QuickCheck for property testing
   - Test edge cases

2. Integration tests:
   - Create test projects
   - Run full builds
   - Verify results

3. Test scenarios:
   - Fresh build (no files exist)
   - Incremental build (some files exist)
   - No-op build (everything up-to-date)
   - Build after modifying dependency
   - Parallel builds
   - Error handling (missing files, bad commands)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESOURCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Documentation:
- System.Directory: File operations
- System.Process: Running commands
- Data.Map: Map data structure
- Data.Graph: Graph algorithms

Papers:
- "Build Systems à la Carte" (Mokhov et al.)
- Discusses different build system architectures

Build Systems:
- GNU Make: Classic build system
- Shake: Haskell build system
- Bazel: Google's build system
- Buck: Facebook's build system

Books:
- "Real World Haskell" - System programming chapters
- "Parallel and Concurrent Programming in Haskell"

-}
