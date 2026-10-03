# SAS Field Lineage Tool from Scratch

This directory contains a from-scratch implementation of a SAS field lineage analysis tool in Python.

## Goal

Build a tool to analyze SAS programs and extract field lineage information - understanding where data fields come from, how they're transformed, and where they're used. This is crucial for:
- Impact analysis (what happens if I change this field?)
- Data governance and compliance
- Understanding data flows in legacy systems
- Documentation and knowledge transfer
- Migration to modern platforms

## What is Field Lineage?

Field lineage tracks the journey of data fields through transformations:
- **Source**: Where does the data originate? (input datasets, tables)
- **Transformations**: How is the data modified? (calculations, merges, filters)
- **Target**: Where does the data end up? (output datasets, reports)

For example, if a SAS program reads `customer.age` and creates `customer_segment.age_group`, the lineage shows:
```
customer.age → [IF age < 18 THEN age_group='Youth'] → customer_segment.age_group
```

## Learning Path

### Phase 1: SAS Code Parser (Beginner)
1. **Lexical Analysis**
   - Tokenize SAS code (keywords, identifiers, operators)
   - Handle SAS-specific syntax (DATA steps, PROC steps)
   - Parse comments and macro variables

2. **Basic Statement Recognition**
   - Identify DATA steps (data transformations)
   - Identify INPUT/SET statements (data sources)
   - Identify assignment statements (field creation)
   - Identify OUTPUT statements (data targets)

### Phase 2: Lineage Extraction (Intermediate)
3. **Field Dependency Analysis**
   - Extract field definitions from assignments
   - Track field usage in expressions
   - Handle SAS functions and operations
   - Build dependency graphs

4. **Dataset Flow Tracking**
   - Track dataset inputs (SET, MERGE, UPDATE)
   - Track dataset outputs (DATA statement, OUTPUT)
   - Handle multiple inputs/outputs
   - Track PROC SQL queries

### Phase 3: Advanced Features (Advanced)
5. **Cross-Program Analysis**
   - Link multiple SAS programs
   - Track fields across program boundaries
   - Handle include files and macros
   - Build end-to-end lineage

6. **Visualization and Reporting**
   - Generate lineage diagrams
   - Create impact analysis reports
   - Export to standard formats (CSV, JSON)
   - Interactive lineage exploration

### Phase 4: Production-Ready Tool (Hero Level)
7. **Complete SAS Lineage System**
   - Parse entire SAS codebases
   - Handle complex SAS features (macros, arrays, DO loops)
   - Database integration for lineage storage
   - Web UI for lineage exploration
   - API for programmatic access
   - Integration with data catalogs

## Project Structure

```
sas-lineage-tool/
├── README.md (this file)
├── template_lineage_parser.py      # Template with TODOs
├── test_data/
│   ├── simple_data_step.sas        # Example 1: Basic DATA step
│   ├── complex_transform.sas       # Example 2: Complex transformations
│   ├── proc_sql.sas                # Example 3: PROC SQL
│   └── multiple_datasets.sas       # Example 4: Multiple inputs/outputs
└── solutions/
    ├── README.md                    # Solution documentation
    ├── lineage_parser.py            # Complete implementation
    ├── examples.py                  # Usage examples
    └── test_lineage.py              # Test suite
```

## Key Concepts

### SAS Program Structure

A typical SAS program has:
1. **DATA Steps**: Data transformations
   ```sas
   DATA output_dataset;
       SET input_dataset;
       new_field = old_field * 2;
   RUN;
   ```

2. **PROC Steps**: Procedures for analysis/reporting
   ```sas
   PROC SQL;
       CREATE TABLE output AS
       SELECT field1, field2
       FROM input;
   QUIT;
   ```

### Lineage Types

1. **Direct Lineage**: Field copied directly
   ```sas
   new_field = old_field;
   ```

2. **Derived Lineage**: Field calculated from others
   ```sas
   total = price * quantity;
   ```

3. **Conditional Lineage**: Field depends on conditions
   ```sas
   IF age < 18 THEN category = 'Youth';
   ```

## Getting Started

### Prerequisites
- Python 3.8+
- Basic understanding of SAS syntax
- Familiarity with parsing and ASTs (helpful but not required)

### Step 1: Understand SAS Basics
Read a few example SAS programs in `test_data/` to understand:
- How DATA steps work
- How fields are created and used
- How datasets flow through programs

### Step 2: Implement the Parser
Work through `template_lineage_parser.py`:
1. Start with simple tokenization
2. Parse basic DATA steps
3. Extract field assignments
4. Build lineage relationships
5. Handle more complex features incrementally

### Step 3: Test Your Implementation
```bash
python template_lineage_parser.py test_data/simple_data_step.sas
```

### Step 4: Compare with Solution
After implementing, check `solutions/lineage_parser.py` to see a complete implementation.

## Testing Your Implementation

```bash
# Test basic parsing
python template_lineage_parser.py test_data/simple_data_step.sas

# Test complex features
python template_lineage_parser.py test_data/complex_transform.sas

# Run test suite (solution)
cd solutions/
python test_lineage.py
```

## Example Output

For a SAS program:
```sas
DATA customer_summary;
    SET customer_data;
    age_years = age;
    revenue_total = price * quantity;
RUN;
```

The lineage tool should output:
```
Dataset Lineage:
  customer_data → customer_summary

Field Lineage:
  customer_data.age → customer_summary.age_years (direct)
  customer_data.price → customer_summary.revenue_total (derived)
  customer_data.quantity → customer_summary.revenue_total (derived)
```

## Features to Implement

### Core Features (Must Have)
- [x] Parse DATA steps
- [x] Extract field assignments
- [x] Track dataset inputs/outputs
- [x] Build field dependency graph
- [x] Generate lineage report

### Advanced Features (Nice to Have)
- [ ] Handle PROC SQL
- [ ] Support macro variables
- [ ] Parse multiple files
- [ ] Visualize lineage as graph
- [ ] Impact analysis queries

### Production Features (Hero Level)
- [ ] Handle all SAS statements
- [ ] Incremental parsing for large codebases
- [ ] Database storage for lineage
- [ ] Web UI for exploration
- [ ] Integration with data catalogs

## Resources

### SAS Language References
- [SAS Documentation](https://documentation.sas.com/)
- [SAS Language Reference](https://go.documentation.sas.com/doc/en/pgmsascdc/9.4_3.5/lrdict/titlepage.htm)
- [DATA Step Programming](https://support.sas.com/edu/schedules.html?id=1654)

### Lineage Concepts
- [Data Lineage Best Practices](https://www.collibra.com/us/en/blog/data-lineage-best-practices)
- [Apache Atlas - Data Lineage](https://atlas.apache.org/)
- [OpenLineage Standard](https://openlineage.io/)

### Parsing Techniques
- [Abstract Syntax Trees](https://en.wikipedia.org/wiki/Abstract_syntax_tree)
- [Python AST Module](https://docs.python.org/3/library/ast.html)
- [Building a Parser](https://craftinginterpreters.com/)

## Real-World Applications

This tool is useful for:

1. **Legacy System Migration**
   - Understand SAS code before migrating to Python/Spark
   - Map SAS fields to new data models
   - Validate migration completeness

2. **Impact Analysis**
   - "If I change this source field, what breaks?"
   - "Which reports use this calculation?"
   - "Where does this field come from?"

3. **Compliance and Governance**
   - Document data transformations for audits
   - Track PII/sensitive data flows
   - Ensure data quality controls

4. **Knowledge Transfer**
   - Document legacy systems
   - Onboard new team members
   - Understand undocumented code

## Common Challenges

### Challenge 1: SAS Syntax Complexity
SAS has complex syntax with many edge cases. Start simple:
- Begin with basic DATA steps
- Add complexity incrementally
- Handle common patterns first

### Challenge 2: Implicit Behaviors
SAS has implicit behaviors (e.g., automatic variable retention). Document assumptions:
- What features are supported?
- What edge cases are handled?
- What is out of scope?

### Challenge 3: Macro Variables
SAS macros can generate code dynamically. Start without macros:
- Parse the expanded code first
- Add macro support later
- Document macro limitations

## Implementation Tips

1. **Start Small**: Parse a single simple DATA step first
2. **Incremental Development**: Add features one at a time
3. **Test Continuously**: Test after each feature addition
4. **Use Examples**: Work from real SAS code examples
5. **Document Assumptions**: Be clear about what's supported
6. **Handle Errors Gracefully**: Invalid SAS code shouldn't crash

## Next Steps

After completing this project:

1. **Extend the Tool**
   - Add support for more SAS features
   - Improve visualization
   - Add impact analysis queries

2. **Integrate with Other Tools**
   - Export to data catalog systems
   - Generate documentation automatically
   - Build a lineage database

3. **Apply to Real Projects**
   - Analyze real SAS codebases
   - Use for migration projects
   - Support compliance initiatives

## Note

This implementation is educational and demonstrates core lineage concepts. Production lineage tools require handling the full SAS language specification, which is extensive. This project focuses on the most common and important patterns.

## Video Courses & Resources

**Database Systems & Data Engineering**:
- [Database Systems Courses](https://github.com/Developer-Y/cs-video-courses#database-systems)
- [Software Engineering Courses](https://github.com/Developer-Y/cs-video-courses#software-engineering)

**Compilers & Parsing**:
- [Theoretical CS and Programming Languages](https://github.com/Developer-Y/cs-video-courses#theoretical-cs-and-programming-languages)

## Sources

- Cheney, Chiticariu & Tan, **"Provenance in Databases"**, FnTDB 2009 — lineage is provenance with the algebra removed, which is how to read this directory after week 6.
- The **SAS Language Reference**, for the DATA step semantics being parsed.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-18--the-tail)
