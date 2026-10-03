# SAS Field Lineage Parser - Solution

This directory contains the complete implementation of the SAS field lineage parser.

## Features

✅ **Implemented Features:**
- Parse SAS DATA steps
- Extract dataset input/output relationships
- Track field assignments and dependencies
- Identify direct, derived, and constant field lineages
- Handle SET and MERGE statements
- Generate human-readable lineage reports
- Export lineage to JSON format
- Remove SAS comments (both `*` and `/* */` styles)

## Files

- `lineage_parser.py` - Complete implementation
- `examples.py` - Usage examples and demonstrations
- `test_lineage.py` - Test suite for the parser
- `README.md` - This file

## Installation

No external dependencies required! Uses only Python standard library.

```bash
# Python 3.8+ required
python3 --version
```

## Usage

### Basic Usage

```bash
python lineage_parser.py <sas_file>
```

### Example

```bash
python lineage_parser.py ../test_data/simple_data_step.sas
```

### Output Example

```
================================================================================
SAS FIELD LINEAGE REPORT
================================================================================

DATASET LINEAGE:
--------------------------------------------------------------------------------
  customer_data → customer_summary

FIELD LINEAGE:
--------------------------------------------------------------------------------

Dataset: customer_summary
  ----------------------------------------------------------------------------
  age_group ← [age] (derived)
  age_years ← [age] (direct copy)
  customer_id ← [id] (direct copy)
  full_name ← [first_name, last_name] (derived)
  total_revenue ← [price, quantity] (derived)

================================================================================
```

### Export to JSON

```bash
python lineage_parser.py ../test_data/simple_data_step.sas --json
```

This creates a JSON file with detailed lineage information.

## How It Works

### 1. Comment Removal
Removes both SAS comment styles:
- `* comment text;`
- `/* comment text */`

### 2. Statement Parsing
Splits SAS code into individual statements (separated by semicolons).

### 3. Statement Classification
Identifies statement types:
- **DATA statements**: Define output datasets
- **SET/MERGE statements**: Define input datasets
- **Assignment statements**: Define field transformations

### 4. Field Extraction
Extracts field names from expressions by:
- Removing string literals
- Removing function calls
- Filtering out keywords
- Identifying variable names

### 5. Lineage Building
Creates a graph of dependencies:
- Dataset → Dataset relationships
- Field → Field relationships
- Transformation types (direct, derived, constant)

## Examples

### Example 1: Simple DATA Step

```sas
DATA customer_summary;
    SET customer_data;
    customer_id = id;
    total_revenue = price * quantity;
RUN;
```

**Lineage:**
- `customer_data` → `customer_summary`
- `customer_data.id` → `customer_summary.customer_id` (direct)
- `customer_data.price, quantity` → `customer_summary.total_revenue` (derived)

### Example 2: MERGE Operation

```sas
DATA combined;
    MERGE customers (IN=a) transactions (IN=b);
    BY customer_id;
    total = amount * 1.1;
RUN;
```

**Lineage:**
- `customers, transactions` → `combined`
- `amount` → `total` (derived)

### Example 3: Complex Transformation

```sas
DATA result;
    SET input_data;
    IF age < 18 THEN category = 'Youth';
    ELSE category = 'Adult';
    full_name = CATX(' ', first_name, last_name);
RUN;
```

**Lineage:**
- `input_data` → `result`
- `age` → `category` (derived)
- `first_name, last_name` → `full_name` (derived)

## Testing

Run the test suite:

```bash
python test_lineage.py
```

This tests the parser against all example files in `test_data/`.

## Limitations

This implementation handles common SAS patterns but has limitations:

### Supported
✅ Basic DATA steps
✅ SET and MERGE statements
✅ Simple assignments and calculations
✅ Common SAS functions
✅ Both comment styles

### Not Fully Supported
⚠️ PROC SQL (basic support only)
⚠️ Macro variables and macro processing
⚠️ Array processing (limited)
⚠️ DO loops with complex logic
⚠️ RETAIN and LAG functions (advanced state)
⚠️ BY-group processing details
⚠️ Dataset options (IN=, WHERE=, etc.)

### Future Enhancements
- Full PROC SQL support
- Macro variable expansion
- Array processing
- Cross-file lineage
- Lineage visualization (graphviz)
- Interactive web UI
- Database storage for large codebases

## Architecture

### Classes

1. **FieldLineage**: Represents a single field's lineage
   - Source fields
   - Transformation type
   - Target dataset

2. **DatasetLineage**: Represents a dataset's lineage
   - Source datasets
   - Field lineages
   - Dataset name

3. **SASLineageParser**: Main parser class
   - Parse files
   - Extract lineage
   - Generate reports

### Data Flow

```
SAS File
    ↓
Comment Removal
    ↓
Statement Splitting
    ↓
Statement Parsing
    ↓
Lineage Extraction
    ↓
Report Generation
```

## Advanced Usage

### Programmatic Usage

```python
from lineage_parser import SASLineageParser

# Create parser
parser = SASLineageParser()

# Parse file
lineages = parser.parse_file('my_program.sas')

# Access lineage data
for dataset_name, lineage in lineages.items():
    print(f"Dataset: {dataset_name}")
    print(f"Sources: {lineage.source_datasets}")
    for field_name, field_lineage in lineage.fields.items():
        print(f"  {field_name} depends on: {field_lineage.source_fields}")
```

### JSON Export

```python
import json
from lineage_parser import SASLineageParser

parser = SASLineageParser()
parser.parse_file('my_program.sas')

# Export to JSON
lineage_json = parser.export_to_json()

# Save to file
with open('lineage.json', 'w') as f:
    json.dump(lineage_json, f, indent=2)
```

### Integration with Other Tools

The JSON export can be used to:
- Import into data catalog systems
- Generate documentation
- Build lineage visualizations
- Perform impact analysis
- Track data quality

## Performance

The parser is designed for clarity over performance. For large codebases:

- **Small files (<1000 lines)**: < 1 second
- **Medium files (1000-10000 lines)**: 1-10 seconds
- **Large files (>10000 lines)**: 10+ seconds

For production use with large codebases:
- Parse files in parallel
- Cache parsed results
- Use incremental parsing
- Store lineage in a database

## Troubleshooting

### Issue: Parser doesn't recognize fields

**Cause**: Field names might be confused with keywords/functions

**Solution**: Check `self.keywords` and `self.functions` sets in the parser

### Issue: Comments not removed properly

**Cause**: Nested or unusual comment syntax

**Solution**: Review `_remove_comments()` method, may need enhanced regex

### Issue: Assignment not parsed

**Cause**: Complex expression or statement format

**Solution**: Add debug logging to see what's being parsed

### Debug Mode

Add this to see what's being parsed:

```python
def _parse_statement(self, statement: str):
    print(f"DEBUG: Parsing statement: {statement[:50]}...")
    # ... rest of the method
```

## Contributing

If you extend this implementation:
1. Add test cases for new features
2. Update the README with new capabilities
3. Maintain backward compatibility
4. Document limitations clearly

## License

This is educational code. Use freely for learning and teaching.

## Learn More

- [SAS Documentation](https://documentation.sas.com/)
- [Data Lineage Concepts](https://www.collibra.com/us/en/blog/data-lineage-best-practices)
- [OpenLineage Standard](https://openlineage.io/)
- [Apache Atlas](https://atlas.apache.org/)
