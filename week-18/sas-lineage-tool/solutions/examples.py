"""
Examples: SAS Field Lineage Parser

This file demonstrates various usage patterns of the lineage parser.
"""

from lineage_parser import SASLineageParser
import json
from pathlib import Path


def example1_basic_usage():
    """Example 1: Basic usage - parse and print report."""
    print("=" * 80)
    print("EXAMPLE 1: Basic Usage")
    print("=" * 80)
    
    parser = SASLineageParser()
    lineages = parser.parse_file('../test_data/simple_data_step.sas')
    
    report = parser.generate_report()
    print(report)


def example2_programmatic_access():
    """Example 2: Access lineage data programmatically."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Programmatic Access")
    print("=" * 80)
    
    parser = SASLineageParser()
    lineages = parser.parse_file('../test_data/simple_data_step.sas')
    
    # Access dataset lineages
    for dataset_name, lineage in lineages.items():
        print(f"\nDataset: {dataset_name}")
        print(f"  Sources: {lineage.source_datasets}")
        print(f"  Number of fields: {len(lineage.fields)}")
        
        # Access field lineages
        for field_name, field_lineage in lineage.fields.items():
            sources = ", ".join(sorted(field_lineage.source_fields)) if field_lineage.source_fields else "none"
            print(f"    {field_name}: sources=[{sources}], type={field_lineage.transformation}")


def example3_json_export():
    """Example 3: Export lineage to JSON."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: JSON Export")
    print("=" * 80)
    
    parser = SASLineageParser()
    parser.parse_file('../test_data/simple_data_step.sas')
    
    # Export to JSON
    lineage_json = parser.export_to_json()
    
    # Pretty print
    print(json.dumps(lineage_json, indent=2))


def example4_multiple_datasets():
    """Example 4: Parse file with multiple datasets."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Multiple Datasets")
    print("=" * 80)
    
    parser = SASLineageParser()
    lineages = parser.parse_file('../test_data/multiple_datasets.sas')
    
    report = parser.generate_report()
    print(report)


def example5_complex_transform():
    """Example 5: Parse complex transformations."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Complex Transformations")
    print("=" * 80)
    
    parser = SASLineageParser()
    lineages = parser.parse_file('../test_data/complex_transform.sas')
    
    report = parser.generate_report()
    print(report)


def example6_impact_analysis():
    """Example 6: Impact analysis - find where a field is used."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Impact Analysis")
    print("=" * 80)
    
    parser = SASLineageParser()
    lineages = parser.parse_file('../test_data/simple_data_step.sas')
    
    # Find all fields that depend on 'price'
    source_field = 'price'
    print(f"\nFields that depend on '{source_field}':")
    print("-" * 80)
    
    for dataset_name, lineage in lineages.items():
        for field_name, field_lineage in lineage.fields.items():
            if source_field in field_lineage.source_fields:
                print(f"  {dataset_name}.{field_name}")


def example7_lineage_chain():
    """Example 7: Trace lineage chain across multiple datasets."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Lineage Chain")
    print("=" * 80)
    
    parser = SASLineageParser()
    lineages = parser.parse_file('../test_data/multiple_datasets.sas')
    
    # Build dataset dependency graph
    print("\nDataset Dependency Chain:")
    print("-" * 80)
    
    def print_chain(dataset, level=0):
        """Recursively print dataset dependencies."""
        indent = "  " * level
        print(f"{indent}{dataset}")
        
        if dataset in lineages:
            lineage = lineages[dataset]
            for source in lineage.source_datasets:
                print_chain(source, level + 1)
    
    # Start from final output dataset
    for dataset_name in lineages.keys():
        # Find datasets that aren't used as sources (likely final outputs)
        is_output = True
        for other_lineage in lineages.values():
            if dataset_name in other_lineage.source_datasets:
                is_output = False
                break
        
        if is_output:
            print(f"\nOutput: {dataset_name}")
            print_chain(dataset_name)


def example8_field_statistics():
    """Example 8: Generate statistics about the lineage."""
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Lineage Statistics")
    print("=" * 80)
    
    parser = SASLineageParser()
    lineages = parser.parse_file('../test_data/complex_transform.sas')
    
    # Calculate statistics
    total_datasets = len(lineages)
    total_fields = sum(len(lineage.fields) for lineage in lineages.values())
    
    transformation_types = {}
    for lineage in lineages.values():
        for field_lineage in lineage.fields.values():
            trans_type = field_lineage.transformation
            transformation_types[trans_type] = transformation_types.get(trans_type, 0) + 1
    
    print(f"\nLineage Statistics:")
    print("-" * 80)
    print(f"Total datasets: {total_datasets}")
    print(f"Total fields: {total_fields}")
    print(f"\nTransformation types:")
    for trans_type, count in sorted(transformation_types.items()):
        print(f"  {trans_type}: {count}")


def main():
    """Run all examples."""
    examples = [
        example1_basic_usage,
        example2_programmatic_access,
        example3_json_export,
        example4_multiple_datasets,
        example5_complex_transform,
        example6_impact_analysis,
        example7_lineage_chain,
        example8_field_statistics,
    ]
    
    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\nError in {example_func.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
