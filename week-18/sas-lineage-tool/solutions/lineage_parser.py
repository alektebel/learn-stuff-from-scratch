"""
Complete Solution: SAS Field Lineage Parser

This is a complete implementation of a SAS field lineage parser.
It demonstrates parsing SAS code and extracting field-level data lineage.
"""

import re
import json
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict


@dataclass
class FieldLineage:
    """Represents the lineage of a single field."""
    field_name: str
    source_fields: Set[str] = field(default_factory=set)
    transformation: str = ""
    dataset: str = ""
    
    def __str__(self):
        sources = ", ".join(sorted(self.source_fields)) if self.source_fields else "none"
        return f"{self.dataset}.{self.field_name} <- [{sources}] ({self.transformation})"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'field_name': self.field_name,
            'source_fields': list(self.source_fields),
            'transformation': self.transformation,
            'dataset': self.dataset
        }


@dataclass
class DatasetLineage:
    """Represents the lineage of a dataset."""
    dataset_name: str
    source_datasets: List[str] = field(default_factory=list)
    fields: Dict[str, FieldLineage] = field(default_factory=dict)
    
    def add_field(self, field_lineage: FieldLineage):
        """Add a field lineage to this dataset."""
        self.fields[field_lineage.field_name] = field_lineage
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'dataset_name': self.dataset_name,
            'source_datasets': self.source_datasets,
            'fields': {name: fl.to_dict() for name, fl in self.fields.items()}
        }


class SASLineageParser:
    """Parses SAS code and extracts field lineage information."""
    
    def __init__(self):
        """Initialize the parser."""
        self.dataset_lineages: Dict[str, DatasetLineage] = {}
        self.current_dataset: Optional[str] = None
        
        # SAS keywords (not exhaustive, but covers common cases)
        self.keywords = {
            'DATA', 'SET', 'MERGE', 'RUN', 'IF', 'THEN', 'ELSE', 'DO', 'END',
            'BY', 'WHERE', 'KEEP', 'DROP', 'RENAME', 'LENGTH', 'FORMAT',
            'INPUT', 'OUTPUT', 'DELETE', 'RETAIN', 'ARRAY', 'TO', 'AND', 'OR',
            'IN', 'NOT', 'EQ', 'NE', 'GT', 'LT', 'GE', 'LE', 'PROC', 'QUIT'
        }
        
        # SAS functions (common ones to filter out)
        self.functions = {
            'SUM', 'MEAN', 'MIN', 'MAX', 'ROUND', 'FLOOR', 'CEIL',
            'UPCASE', 'LOWCASE', 'TRIM', 'STRIP', 'SUBSTR', 'SCAN',
            'CATX', 'CAT', 'CATS', 'CATT', 'COMPRESS',
            'TODAY', 'DATE', 'YEAR', 'MONTH', 'DAY', 'DATEPART', 'TIMEPART',
            'INPUT', 'PUT', 'LAG', 'DIF', 'INTCK', 'INTNX',
            'COUNT', 'COUNTW', 'FIND', 'INDEX', 'LENGTH'
        }
        
    def parse_file(self, filepath: str) -> Dict[str, DatasetLineage]:
        """Parse a SAS file and extract lineage information."""
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Remove comments
        content = self._remove_comments(content)
        
        # Split into statements
        statements = self._split_statements(content)
        
        # Parse each statement
        for stmt in statements:
            self._parse_statement(stmt)
        
        return self.dataset_lineages
    
    def _remove_comments(self, content: str) -> str:
        """Remove SAS comments from the code."""
        # Remove /* */ style comments first (including multiline)
        content = re.sub(r'/\*.*?\*/', ' ', content, flags=re.DOTALL)
        
        # Remove * style comments (only at start of statement after whitespace/newline)
        # Match: start of line (^) or semicolon, then whitespace, then *, then everything until ;
        content = re.sub(r'(^|;)\s*\*[^;]*;', r'\1 ', content, flags=re.MULTILINE)
        
        return content
    
    def _split_statements(self, content: str) -> List[str]:
        """Split SAS code into individual statements."""
        # Split on semicolons
        statements = content.split(';')
        
        # Clean up whitespace and filter empty statements
        statements = [stmt.strip() for stmt in statements if stmt.strip()]
        
        return statements
    
    def _parse_statement(self, statement: str):
        """Parse a single SAS statement."""
        stmt = statement.strip()
        if not stmt:
            return
        
        # Normalize for keyword matching (but keep original for field names)
        stmt_upper = stmt.upper()
        
        # Identify statement type by first keyword
        if stmt_upper.startswith('DATA '):
            self._parse_data_statement(stmt)
        elif stmt_upper.startswith('SET '):
            self._parse_set_statement(stmt)
        elif stmt_upper.startswith('MERGE '):
            self._parse_merge_statement(stmt)
        elif stmt_upper.startswith('RUN'):
            # End of DATA step
            self.current_dataset = None
        elif stmt_upper.startswith('IF ') and 'THEN' in stmt_upper:
            # Handle IF-THEN assignment: IF condition THEN assignment
            self._parse_conditional_assignment(stmt)
        elif stmt_upper.startswith('ELSE IF ') and 'THEN' in stmt_upper:
            # Handle ELSE IF-THEN assignment
            self._parse_conditional_assignment(stmt)
        elif stmt_upper.startswith('ELSE ') and '=' in stmt:
            # Handle ELSE assignment
            self._parse_conditional_assignment(stmt)
        elif '=' in stmt and self.current_dataset:
            # Regular assignment statement (only parse if we're in a DATA step)
            # Skip if it looks like a conditional (contains IF, THEN, ELSE at start)
            if not any(stmt_upper.startswith(kw) for kw in ['IF ', 'THEN ', 'ELSE ']):
                self._parse_assignment(stmt)
        # Ignore other statements (KEEP, DROP, etc.) for basic lineage
    
    def _parse_data_statement(self, statement: str):
        """Parse a DATA statement to identify output dataset."""
        # Extract dataset name: DATA <dataset_name>
        match = re.search(r'DATA\s+(\w+)', statement, re.IGNORECASE)
        if match:
            dataset_name = match.group(1).lower()
            self.current_dataset = dataset_name
            
            # Create new dataset lineage if it doesn't exist
            if dataset_name not in self.dataset_lineages:
                self.dataset_lineages[dataset_name] = DatasetLineage(dataset_name=dataset_name)
    
    def _parse_set_statement(self, statement: str):
        """Parse a SET statement to identify input dataset(s)."""
        if not self.current_dataset:
            return
        
        # Extract dataset names: SET <dataset1> <dataset2> ...
        # Remove the SET keyword and any dataset options like (IN=a)
        stmt = re.sub(r'\([^)]*\)', '', statement)  # Remove options
        match = re.search(r'SET\s+([\w\s]+)', stmt, re.IGNORECASE)
        if match:
            datasets_str = match.group(1).strip()
            # Split on whitespace to get multiple datasets
            datasets = [ds.lower() for ds in datasets_str.split() if ds]
            
            # Add to current dataset's sources
            current_lineage = self.dataset_lineages[self.current_dataset]
            for ds in datasets:
                if ds not in current_lineage.source_datasets:
                    current_lineage.source_datasets.append(ds)
    
    def _parse_merge_statement(self, statement: str):
        """Parse a MERGE statement to identify input datasets."""
        if not self.current_dataset:
            return
        
        # Extract dataset names: MERGE <dataset1> (IN=a) <dataset2> (IN=b)
        # Remove dataset options
        stmt = re.sub(r'\([^)]*\)', '', statement)
        match = re.search(r'MERGE\s+([\w\s]+)', stmt, re.IGNORECASE)
        if match:
            datasets_str = match.group(1).strip()
            datasets = [ds.lower() for ds in datasets_str.split() if ds]
            
            # Add to current dataset's sources
            current_lineage = self.dataset_lineages[self.current_dataset]
            for ds in datasets:
                if ds not in current_lineage.source_datasets:
                    current_lineage.source_datasets.append(ds)
    
    def _parse_assignment(self, statement: str):
        """Parse an assignment statement to extract field lineage."""
        if not self.current_dataset:
            return
        
        # Split on = to get target field and expression
        parts = statement.split('=', 1)
        if len(parts) != 2:
            return
        
        target_field = parts[0].strip().lower()
        # Filter out non-identifier characters from target field name
        target_field = re.sub(r'[^a-zA-Z0-9_]', '', target_field)
        if not target_field:
            return
        
        expression = parts[1].strip()
        
        # Extract source fields from expression
        source_fields = self._extract_fields_from_expression(expression)
        
        # Determine transformation type
        if not source_fields:
            trans_type = "constant"
        elif len(source_fields) == 1 and expression.lower().strip() == list(source_fields)[0]:
            trans_type = "direct copy"
        else:
            trans_type = "derived"
        
        # Create field lineage
        field_lineage = FieldLineage(
            field_name=target_field,
            source_fields=source_fields,
            transformation=trans_type,
            dataset=self.current_dataset
        )
        
        # Add to current dataset
        current_lineage = self.dataset_lineages[self.current_dataset]
        current_lineage.add_field(field_lineage)
    
    def _parse_conditional_assignment(self, statement: str):
        """Parse conditional assignment (IF-THEN, ELSE IF, ELSE)."""
        if not self.current_dataset:
            return
        
        # Extract the THEN part or ELSE part
        stmt_upper = statement.upper()
        
        # For IF ... THEN assignment or ELSE IF ... THEN assignment
        if 'THEN' in stmt_upper:
            parts = statement.split('THEN', 1)
            if len(parts) == 2:
                condition = parts[0].strip()
                assignment = parts[1].strip()
                
                # Parse the assignment part
                if '=' in assignment:
                    self._parse_conditional_assignment_with_condition(assignment, condition)
        # For ELSE assignment
        elif stmt_upper.startswith('ELSE ') and '=' in statement:
            assignment = statement[4:].strip()  # Remove 'ELSE'
            self._parse_conditional_assignment_with_condition(assignment, "ELSE")
    
    def _parse_conditional_assignment_with_condition(self, assignment: str, condition: str):
        """Parse assignment with its condition to extract field lineage."""
        if not self.current_dataset:
            return
        
        # Split assignment on =
        parts = assignment.split('=', 1)
        if len(parts) != 2:
            return
        
        target_field = parts[0].strip().lower()
        target_field = re.sub(r'[^a-zA-Z0-9_]', '', target_field)
        if not target_field:
            return
        
        expression = parts[1].strip()
        
        # Extract source fields from both condition and expression
        source_fields = self._extract_fields_from_expression(condition)
        source_fields.update(self._extract_fields_from_expression(expression))
        
        # Create field lineage
        field_lineage = FieldLineage(
            field_name=target_field,
            source_fields=source_fields,
            transformation="conditional",
            dataset=self.current_dataset
        )
        
        # Add or update field in current dataset
        current_lineage = self.dataset_lineages[self.current_dataset]
        # If field already exists, merge source fields
        if target_field in current_lineage.fields:
            existing = current_lineage.fields[target_field]
            existing.source_fields.update(source_fields)
        else:
            current_lineage.add_field(field_lineage)
    
    def _extract_fields_from_expression(self, expression: str) -> Set[str]:
        """Extract field names from an expression."""
        # First, extract fields from within function calls before removing them
        # Find all function calls and extract their arguments
        func_pattern = r'\w+\s*\(([^)]*)\)'
        func_matches = re.findall(func_pattern, expression)
        
        # Recursively process function arguments
        fields = set()
        for args in func_matches:
            fields.update(self._extract_fields_from_expression(args))
        
        # Remove string literals (single and double quotes)
        expr = re.sub(r"'[^']*'", '', expression)
        expr = re.sub(r'"[^"]*"', '', expr)
        
        # Remove function calls (now that we've extracted fields from them)
        expr = re.sub(func_pattern, '', expr)
        
        # Find all identifiers (words that could be field names)
        # Identifiers can contain letters, numbers, and underscores
        identifiers = re.findall(r'\b[a-zA-Z_]\w*\b', expr)
        
        # Filter out keywords and functions
        for ident in identifiers:
            if not self._is_keyword(ident) and not self._is_function(ident):
                fields.add(ident.lower())
        
        return fields
    
    def _is_keyword(self, word: str) -> bool:
        """Check if a word is a SAS keyword."""
        return word.upper() in self.keywords
    
    def _is_function(self, word: str) -> bool:
        """Check if a word is a SAS function."""
        return word.upper() in self.functions
    
    def generate_report(self) -> str:
        """Generate a human-readable lineage report."""
        report = []
        report.append("=" * 80)
        report.append("SAS FIELD LINEAGE REPORT")
        report.append("=" * 80)
        report.append("")
        
        if not self.dataset_lineages:
            report.append("No lineage information found.")
            return "\n".join(report)
        
        # Dataset-level lineage
        report.append("DATASET LINEAGE:")
        report.append("-" * 80)
        for dataset_name, lineage in self.dataset_lineages.items():
            if lineage.source_datasets:
                sources = ", ".join(lineage.source_datasets)
                report.append(f"  {sources} → {dataset_name}")
            else:
                report.append(f"  (no inputs) → {dataset_name}")
        report.append("")
        
        # Field-level lineage
        report.append("FIELD LINEAGE:")
        report.append("-" * 80)
        for dataset_name, lineage in self.dataset_lineages.items():
            if lineage.fields:
                report.append(f"\nDataset: {dataset_name}")
                report.append("  " + "-" * 76)
                for field_name, field_lineage in sorted(lineage.fields.items()):
                    if field_lineage.source_fields:
                        sources = ", ".join(sorted(field_lineage.source_fields))
                        report.append(f"  {field_name} ← [{sources}] ({field_lineage.transformation})")
                    else:
                        report.append(f"  {field_name} ← [constant] ({field_lineage.transformation})")
        
        report.append("")
        report.append("=" * 80)
        return "\n".join(report)
    
    def export_to_json(self) -> Dict:
        """Export lineage information to JSON-serializable format."""
        return {
            dataset_name: lineage.to_dict()
            for dataset_name, lineage in self.dataset_lineages.items()
        }


def main():
    """Main function to demonstrate the lineage parser."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python lineage_parser.py <sas_file>")
        print("\nExample:")
        print("  python lineage_parser.py ../test_data/simple_data_step.sas")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    # Create parser and parse file
    parser = SASLineageParser()
    try:
        lineages = parser.parse_file(filepath)
        
        # Generate and print report
        report = parser.generate_report()
        print(report)
        
        # Optionally export to JSON
        if '--json' in sys.argv:
            json_output = parser.export_to_json()
            output_file = filepath.replace('.sas', '_lineage.json')
            with open(output_file, 'w') as f:
                json.dump(json_output, f, indent=2)
            print(f"\nJSON lineage exported to: {output_file}")
    
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
