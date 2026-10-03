"""
Test Suite: SAS Field Lineage Parser

This file contains tests for the lineage parser.
Run with: python test_lineage.py
"""

import unittest
from lineage_parser import SASLineageParser, FieldLineage, DatasetLineage


class TestCommentRemoval(unittest.TestCase):
    """Test comment removal functionality."""
    
    def setUp(self):
        self.parser = SASLineageParser()
    
    def test_star_comment(self):
        """Test * style comment removal."""
        code = "DATA test; * This is a comment; SET input; RUN;"
        result = self.parser._remove_comments(code)
        self.assertNotIn('This is a comment', result)
        self.assertIn('DATA test', result)
    
    def test_block_comment(self):
        """Test /* */ style comment removal."""
        code = "DATA test; /* This is a comment */ SET input; RUN;"
        result = self.parser._remove_comments(code)
        self.assertNotIn('This is a comment', result)
        self.assertIn('DATA test', result)
    
    def test_multiline_block_comment(self):
        """Test multiline /* */ comment removal."""
        code = """DATA test; 
        /* This is a 
           multiline comment */ 
        SET input; RUN;"""
        result = self.parser._remove_comments(code)
        self.assertNotIn('multiline comment', result)


class TestStatementSplitting(unittest.TestCase):
    """Test statement splitting functionality."""
    
    def setUp(self):
        self.parser = SASLineageParser()
    
    def test_simple_split(self):
        """Test splitting simple statements."""
        code = "DATA test; SET input; RUN;"
        statements = self.parser._split_statements(code)
        self.assertEqual(len(statements), 3)
        self.assertIn('DATA test', statements[0])
    
    def test_multiline_split(self):
        """Test splitting multiline code."""
        code = """DATA test;
        SET input;
        x = y;
        RUN;"""
        statements = self.parser._split_statements(code)
        self.assertGreaterEqual(len(statements), 3)


class TestFieldExtraction(unittest.TestCase):
    """Test field extraction from expressions."""
    
    def setUp(self):
        self.parser = SASLineageParser()
    
    def test_simple_expression(self):
        """Test extracting fields from simple expression."""
        expr = "price * quantity"
        fields = self.parser._extract_fields_from_expression(expr)
        self.assertIn('price', fields)
        self.assertIn('quantity', fields)
        self.assertEqual(len(fields), 2)
    
    def test_function_call(self):
        """Test that function names are not extracted as fields."""
        expr = "SUM(price, quantity)"
        fields = self.parser._extract_fields_from_expression(expr)
        self.assertNotIn('sum', fields)
        # Note: Due to regex limitations, fields inside functions may not be extracted
        # This is a known limitation
    
    def test_string_literal(self):
        """Test that string literals are ignored."""
        expr = "'Hello World'"
        fields = self.parser._extract_fields_from_expression(expr)
        self.assertEqual(len(fields), 0)
    
    def test_keyword_filtering(self):
        """Test that keywords are filtered out."""
        expr = "IF age THEN category"
        fields = self.parser._extract_fields_from_expression(expr)
        self.assertNotIn('if', fields)
        self.assertNotIn('then', fields)
        self.assertIn('age', fields)
        self.assertIn('category', fields)


class TestDataStatementParsing(unittest.TestCase):
    """Test DATA statement parsing."""
    
    def setUp(self):
        self.parser = SASLineageParser()
    
    def test_simple_data_statement(self):
        """Test parsing simple DATA statement."""
        self.parser._parse_statement("DATA customer_summary")
        self.assertEqual(self.parser.current_dataset, 'customer_summary')
        self.assertIn('customer_summary', self.parser.dataset_lineages)


class TestSetStatementParsing(unittest.TestCase):
    """Test SET statement parsing."""
    
    def setUp(self):
        self.parser = SASLineageParser()
        self.parser._parse_statement("DATA output")
    
    def test_simple_set_statement(self):
        """Test parsing simple SET statement."""
        self.parser._parse_statement("SET input_data")
        lineage = self.parser.dataset_lineages['output']
        self.assertIn('input_data', lineage.source_datasets)
    
    def test_multiple_datasets(self):
        """Test SET with multiple datasets."""
        self.parser._parse_statement("SET data1 data2")
        lineage = self.parser.dataset_lineages['output']
        self.assertIn('data1', lineage.source_datasets)
        self.assertIn('data2', lineage.source_datasets)


class TestAssignmentParsing(unittest.TestCase):
    """Test assignment statement parsing."""
    
    def setUp(self):
        self.parser = SASLineageParser()
        self.parser._parse_statement("DATA output")
        self.parser._parse_statement("SET input")
    
    def test_simple_assignment(self):
        """Test parsing simple assignment."""
        self.parser._parse_statement("x = y")
        lineage = self.parser.dataset_lineages['output']
        self.assertIn('x', lineage.fields)
        field = lineage.fields['x']
        self.assertIn('y', field.source_fields)
    
    def test_calculated_field(self):
        """Test parsing calculated field."""
        self.parser._parse_statement("total = price * quantity")
        lineage = self.parser.dataset_lineages['output']
        self.assertIn('total', lineage.fields)
        field = lineage.fields['total']
        self.assertIn('price', field.source_fields)
        self.assertIn('quantity', field.source_fields)


class TestFullFileParsing(unittest.TestCase):
    """Test parsing complete SAS files."""
    
    def test_simple_data_step(self):
        """Test parsing simple_data_step.sas."""
        parser = SASLineageParser()
        lineages = parser.parse_file('../test_data/simple_data_step.sas')
        
        # Check dataset lineage
        self.assertIn('customer_summary', lineages)
        lineage = lineages['customer_summary']
        self.assertIn('customer_data', lineage.source_datasets)
        
        # Check field lineages
        self.assertIn('customer_id', lineage.fields)
        self.assertIn('total_revenue', lineage.fields)
        
        # Check specific field dependencies
        total_revenue = lineage.fields.get('total_revenue')
        if total_revenue:
            self.assertIn('price', total_revenue.source_fields)
            self.assertIn('quantity', total_revenue.source_fields)
    
    def test_multiple_datasets(self):
        """Test parsing multiple_datasets.sas."""
        parser = SASLineageParser()
        lineages = parser.parse_file('../test_data/multiple_datasets.sas')
        
        # Should have multiple datasets
        self.assertGreater(len(lineages), 1)
        
        # Check dataset flow
        if 'cleaned_customers' in lineages:
            self.assertIn('raw_customers', lineages['cleaned_customers'].source_datasets)


class TestReportGeneration(unittest.TestCase):
    """Test report generation."""
    
    def test_generate_report(self):
        """Test generating lineage report."""
        parser = SASLineageParser()
        parser.parse_file('../test_data/simple_data_step.sas')
        
        report = parser.generate_report()
        
        # Check report contains key sections
        self.assertIn('DATASET LINEAGE', report)
        self.assertIn('FIELD LINEAGE', report)
        self.assertIn('customer_summary', report)


class TestJSONExport(unittest.TestCase):
    """Test JSON export functionality."""
    
    def test_export_to_json(self):
        """Test exporting lineage to JSON."""
        parser = SASLineageParser()
        parser.parse_file('../test_data/simple_data_step.sas')
        
        json_data = parser.export_to_json()
        
        # Check structure
        self.assertIsInstance(json_data, dict)
        self.assertIn('customer_summary', json_data)
        
        # Check dataset structure
        dataset = json_data['customer_summary']
        self.assertIn('dataset_name', dataset)
        self.assertIn('source_datasets', dataset)
        self.assertIn('fields', dataset)
        
        # Check fields structure
        self.assertIsInstance(dataset['fields'], dict)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestCommentRemoval))
    suite.addTests(loader.loadTestsFromTestCase(TestStatementSplitting))
    suite.addTests(loader.loadTestsFromTestCase(TestFieldExtraction))
    suite.addTests(loader.loadTestsFromTestCase(TestDataStatementParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestSetStatementParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestAssignmentParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestFullFileParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestReportGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestJSONExport))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
