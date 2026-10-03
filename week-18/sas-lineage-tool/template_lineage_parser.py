"""
Template: SAS Field Lineage Parser

GOAL: Build a tool to parse SAS programs and extract field lineage information.

GUIDELINES:
1. Parse SAS code to identify datasets and field transformations
2. Track where fields come from (source datasets)
3. Track how fields are created/transformed (assignments, calculations)
4. Track where fields go (output datasets)
5. Generate a lineage report showing field dependencies

YOUR TASKS:
- Implement SAS code tokenization
- Parse DATA steps and extract field information
- Build field dependency graph
- Generate lineage reports
"""

import re
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class FieldLineage:
    """
    Represents the lineage of a single field.
    
    Attributes:
        field_name: Name of the target field
        source_fields: Set of source fields this field depends on
        transformation: Description of how the field is created
        dataset: The dataset this field belongs to
    """
    field_name: str
    source_fields: Set[str] = field(default_factory=set)
    transformation: str = ""
    dataset: str = ""
    
    def __str__(self):
        sources = ", ".join(sorted(self.source_fields)) if self.source_fields else "none"
        return f"{self.dataset}.{self.field_name} <- [{sources}] ({self.transformation})"


@dataclass
class DatasetLineage:
    """
    Represents the lineage of a dataset.
    
    Attributes:
        dataset_name: Name of the output dataset
        source_datasets: List of input datasets
        fields: Dictionary of field lineages in this dataset
    """
    dataset_name: str
    source_datasets: List[str] = field(default_factory=list)
    fields: Dict[str, FieldLineage] = field(default_factory=dict)
    
    def add_field(self, field_lineage: FieldLineage):
        """Add a field lineage to this dataset."""
        self.fields[field_lineage.field_name] = field_lineage


class SASLineageParser:
    """
    Parses SAS code and extracts field lineage information.
    
    TODO: Implement the SAS lineage parser
    """
    
    def __init__(self):
        """
        Initialize the parser.
        
        TODO:
        1. Initialize storage for dataset lineages
        2. Set up SAS keyword patterns
        3. Initialize current context tracking
        """
        self.dataset_lineages: Dict[str, DatasetLineage] = {}
        self.current_dataset: Optional[str] = None
        
        # TODO: Define SAS keywords to recognize
        # Hint: DATA, SET, MERGE, RUN, IF, THEN, ELSE, etc.
        self.keywords = set([])
        
    def parse_file(self, filepath: str) -> Dict[str, DatasetLineage]:
        """
        Parse a SAS file and extract lineage information.
        
        Args:
            filepath: Path to the SAS file
            
        Returns:
            Dictionary mapping dataset names to their lineage
            
        TODO:
        1. Read the SAS file
        2. Remove comments
        3. Split into statements
        4. Parse each statement
        5. Return lineage information
        """
        # TODO: Implement file reading
        with open(filepath, 'r') as f:
            content = f.read()
        
        # TODO: Remove SAS comments (* ... *) and (/* ... */)
        # Hint: Use regex or string processing
        content = self._remove_comments(content)
        
        # TODO: Split into statements (typically separated by semicolons)
        statements = self._split_statements(content)
        
        # TODO: Parse each statement
        for stmt in statements:
            self._parse_statement(stmt)
        
        return self.dataset_lineages
    
    def _remove_comments(self, content: str) -> str:
        """
        Remove SAS comments from the code.
        
        SAS has two comment styles:
        - * comment text;
        - /* comment text */
        
        Args:
            content: SAS code with comments
            
        Returns:
            SAS code without comments
            
        TODO:
        1. Remove * style comments (from * to ;)
        2. Remove /* */ style comments
        3. Preserve code structure (newlines, etc.)
        """
        # TODO: Implement comment removal
        pass
    
    def _split_statements(self, content: str) -> List[str]:
        """
        Split SAS code into individual statements.
        
        SAS statements are typically separated by semicolons.
        
        Args:
            content: SAS code without comments
            
        Returns:
            List of individual statements
            
        TODO:
        1. Split on semicolons
        2. Clean up whitespace
        3. Filter out empty statements
        """
        # TODO: Implement statement splitting
        pass
    
    def _parse_statement(self, statement: str):
        """
        Parse a single SAS statement.
        
        Args:
            statement: A single SAS statement
            
        TODO:
        1. Identify statement type (DATA, SET, assignment, etc.)
        2. Call appropriate handler method
        3. Update lineage information
        
        HINT: Check first keyword to determine statement type
        """
        # TODO: Normalize statement (strip whitespace, convert to uppercase for keywords)
        stmt = statement.strip()
        if not stmt:
            return
        
        # TODO: Identify and handle different statement types
        # - DATA statement: Creates new dataset
        # - SET statement: Reads input dataset
        # - MERGE statement: Merges datasets
        # - Assignment statement: Creates/transforms fields
        # - RUN statement: Ends DATA step
        
        # Hint: Use string methods or regex to identify statement type
        pass
    
    def _parse_data_statement(self, statement: str):
        """
        Parse a DATA statement to identify output dataset.
        
        Example: DATA customer_summary;
        
        Args:
            statement: DATA statement
            
        TODO:
        1. Extract dataset name after DATA keyword
        2. Create new DatasetLineage object
        3. Set as current dataset
        """
        # TODO: Implement DATA statement parsing
        pass
    
    def _parse_set_statement(self, statement: str):
        """
        Parse a SET statement to identify input dataset(s).
        
        Example: SET customer_data;
        Example: SET customer_data transactions;
        
        Args:
            statement: SET statement
            
        TODO:
        1. Extract dataset name(s) after SET keyword
        2. Add to current dataset's source_datasets
        3. Handle multiple datasets
        """
        # TODO: Implement SET statement parsing
        pass
    
    def _parse_merge_statement(self, statement: str):
        """
        Parse a MERGE statement to identify input datasets.
        
        Example: MERGE customers (IN=a) transactions (IN=b);
        
        Args:
            statement: MERGE statement
            
        TODO:
        1. Extract all dataset names
        2. Handle dataset options like (IN=a)
        3. Add to current dataset's source_datasets
        """
        # TODO: Implement MERGE statement parsing
        pass
    
    def _parse_assignment(self, statement: str):
        """
        Parse an assignment statement to extract field lineage.
        
        Examples:
        - customer_id = id;
        - total = price * quantity;
        - full_name = CATX(' ', first_name, last_name);
        
        Args:
            statement: Assignment statement (contains =)
            
        TODO:
        1. Split on = to get target field and expression
        2. Extract source fields from expression
        3. Create FieldLineage object
        4. Add to current dataset
        """
        # TODO: Implement assignment parsing
        pass
    
    def _extract_fields_from_expression(self, expression: str) -> Set[str]:
        """
        Extract field names from an expression.
        
        Examples:
        - "price * quantity" -> {"price", "quantity"}
        - "CATX(' ', first_name, last_name)" -> {"first_name", "last_name"}
        - "100" -> {} (no fields, just a constant)
        
        Args:
            expression: Right-hand side of an assignment
            
        Returns:
            Set of field names used in the expression
            
        TODO:
        1. Remove SAS functions (they look like FUNC(...))
        2. Remove string literals (in quotes)
        3. Remove numbers
        4. Extract remaining identifiers (field names)
        5. Filter out SAS keywords
        
        HINT: Use regex to find identifiers
        """
        # TODO: Implement field extraction from expressions
        pass
    
    def _is_keyword(self, word: str) -> bool:
        """
        Check if a word is a SAS keyword.
        
        Args:
            word: Word to check
            
        Returns:
            True if word is a SAS keyword
            
        TODO: Compare against self.keywords set
        """
        # TODO: Implement keyword check
        pass
    
    def generate_report(self) -> str:
        """
        Generate a human-readable lineage report.
        
        Returns:
            Formatted lineage report
            
        TODO:
        1. Iterate through all dataset lineages
        2. Format dataset-level lineage
        3. Format field-level lineage
        4. Create hierarchical report
        """
        # TODO: Implement report generation
        report = []
        report.append("=" * 80)
        report.append("SAS FIELD LINEAGE REPORT")
        report.append("=" * 80)
        report.append("")
        
        # TODO: Add dataset lineages
        for dataset_name, lineage in self.dataset_lineages.items():
            # TODO: Format dataset section
            pass
        
        return "\n".join(report)
    
    def export_to_json(self) -> Dict:
        """
        Export lineage information to JSON-serializable format.
        
        Returns:
            Dictionary that can be serialized to JSON
            
        TODO:
        1. Convert DatasetLineage objects to dictionaries
        2. Convert FieldLineage objects to dictionaries
        3. Handle sets (convert to lists)
        """
        # TODO: Implement JSON export
        pass


def main():
    """
    Main function to demonstrate the lineage parser.
    
    TODO:
    1. Parse command line arguments
    2. Create parser instance
    3. Parse SAS file
    4. Generate and print report
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python template_lineage_parser.py <sas_file>")
        print("\nExample:")
        print("  python template_lineage_parser.py test_data/simple_data_step.sas")
        sys.exit(1)
    
    # TODO: Get filepath from command line
    filepath = sys.argv[1]
    
    # TODO: Create parser and parse file
    parser = SASLineageParser()
    lineages = parser.parse_file(filepath)
    
    # TODO: Generate and print report
    report = parser.generate_report()
    print(report)
    
    # TODO (Optional): Export to JSON file
    # import json
    # with open('lineage.json', 'w') as f:
    #     json.dump(parser.export_to_json(), f, indent=2)


if __name__ == "__main__":
    main()


# ============================================================================
# IMPLEMENTATION GUIDE
# ============================================================================
"""
Step-by-Step Implementation Guide:

STEP 1: Setup and Basic Structure (30 minutes)
----------------------------------------------
1. Review the dataclasses (FieldLineage, DatasetLineage)
2. Initialize the SASLineageParser class
3. Define SAS keywords (DATA, SET, RUN, IF, THEN, etc.)
4. Test: Create parser instance and verify initialization

STEP 2: Comment Removal (30 minutes)
-------------------------------------
1. Implement _remove_comments() method
   - Use regex to find and remove (* ... *) comments
   - Use regex to find and remove /* ... */ comments
   - Handle nested comments if needed
2. Test with sample SAS code containing comments

STEP 3: Statement Splitting (20 minutes)
-----------------------------------------
1. Implement _split_statements() method
   - Split on semicolons
   - Strip whitespace from each statement
   - Filter out empty statements
2. Test with multi-statement SAS code

STEP 4: DATA Statement Parsing (30 minutes)
--------------------------------------------
1. Implement _parse_data_statement()
   - Extract dataset name using regex or string methods
   - Create DatasetLineage object
   - Store in self.dataset_lineages
   - Set self.current_dataset
2. Test: Parse "DATA customer_summary;" statement

STEP 5: SET Statement Parsing (30 minutes)
-------------------------------------------
1. Implement _parse_set_statement()
   - Extract dataset name(s) after SET keyword
   - Add to current dataset's source_datasets
   - Handle multiple datasets (space-separated)
2. Test: Parse "SET customer_data;" statement

STEP 6: Field Extraction from Expressions (1 hour)
---------------------------------------------------
1. Implement _extract_fields_from_expression()
   - Use regex to find all identifiers (words)
   - Remove SAS functions (pattern: WORD(...))
   - Remove string literals (in quotes)
   - Remove numbers
   - Filter out keywords
2. Test with various expressions:
   - "price * quantity"
   - "CATX(' ', first_name, last_name)"
   - "age + 10"

STEP 7: Assignment Parsing (1 hour)
------------------------------------
1. Implement _parse_assignment()
   - Split statement on '=' to get target and expression
   - Extract target field name
   - Call _extract_fields_from_expression() for source fields
   - Create FieldLineage object
   - Add to current dataset
2. Test: Parse "total = price * quantity;" statement

STEP 8: Statement Router (30 minutes)
--------------------------------------
1. Implement _parse_statement()
   - Identify statement type by checking keywords
   - Call appropriate handler method
   - Handle RUN statement (ends DATA step)
2. Test with various statement types

STEP 9: Report Generation (45 minutes)
---------------------------------------
1. Implement generate_report()
   - Format dataset lineages
   - Format field lineages with indentation
   - Create hierarchical structure
2. Test: Generate report for parsed lineage

STEP 10: Main Function and Testing (30 minutes)
------------------------------------------------
1. Implement main() function
   - Parse command line arguments
   - Create parser and parse file
   - Generate and print report
2. Test with all test data files:
   - simple_data_step.sas
   - complex_transform.sas
   - multiple_datasets.sas

STEP 11: Advanced Features (Optional, 1-2 hours)
-------------------------------------------------
1. Implement MERGE statement parsing
2. Add JSON export functionality
3. Handle PROC SQL statements
4. Add visualization of lineage graph

TOTAL ESTIMATED TIME: 6-8 hours for core features

TESTING STRATEGY:
-----------------
1. Unit test each method independently
2. Test with increasingly complex SAS code
3. Verify lineage correctness manually
4. Compare with solution implementation

COMMON PITFALLS:
----------------
1. SAS is case-insensitive - normalize to uppercase for comparison
2. Field names can contain underscores - don't split on them
3. SAS functions look like fields but aren't - filter them out
4. Comments can contain semicolons - remove comments first
5. Multiple statements can be on one line - handle carefully

DEBUGGING TIPS:
---------------
1. Print intermediate results (tokens, statements, lineages)
2. Start with simple_data_step.sas - it's the easiest
3. Use the solution as a reference when stuck
4. Test each method independently before integration
5. Add logging to track parser state

NEXT STEPS AFTER COMPLETION:
-----------------------------
1. Add support for PROC SQL
2. Handle SAS macros
3. Parse multiple files and link them
4. Build a web UI for lineage exploration
5. Integrate with data catalog systems
"""
