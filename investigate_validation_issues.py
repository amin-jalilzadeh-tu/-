#!/usr/bin/env python3
"""
Investigate validation issues:
1. Why no parquet files are generated in modified validation
2. Fix baseline validation data format issues
"""

import pandas as pd
import json
from pathlib import Path

def investigate_issues():
    """Main investigation function"""
    
    job_id = "b139a061-d967-47a5-b850-ff8bd3d351ae"
    base_path = Path(f"/mnt/d/Documents/daily/E_Plus_2040_py/output/{job_id}")
    
    print("="*60)
    print("VALIDATION ISSUES INVESTIGATION")
    print("="*60)
    
    # Issue 1: Check validation output structure
    print("\n1. CHECKING VALIDATION OUTPUT STRUCTURE:")
    validation_path = base_path / "validation_results"
    
    print(f"\nValidation results directory: {validation_path}")
    print(f"Exists: {validation_path.exists()}")
    
    if validation_path.exists():
        # Check baseline directory
        baseline_path = validation_path / "baseline"
        print(f"\nBaseline directory: {baseline_path}")
        print(f"Exists: {baseline_path.exists()}")
        if baseline_path.exists():
            files = list(baseline_path.glob("*"))
            print(f"Files: {[f.name for f in files]}")
            
        # Check modified directory
        modified_path = validation_path / "modified"
        print(f"\nModified directory: {modified_path}")
        print(f"Exists: {modified_path.exists()}")
        if modified_path.exists():
            files = list(modified_path.glob("*"))
            print(f"Files: {[f.name for f in files]}")
    
    # Issue 2: Check baseline data format
    print("\n\n2. CHECKING BASELINE DATA FORMAT:")
    
    # Check daily data
    daily_path = base_path / "parsed_data/timeseries/base_all_daily.parquet"
    if daily_path.exists():
        print(f"\nReading baseline daily data: {daily_path}")
        df = pd.read_parquet(daily_path)
        print(f"Shape: {df.shape}")
        print(f"Columns ({len(df.columns)}): {list(df.columns[:10])}...")
        
        # Check if it's wide format
        date_cols = [col for col in df.columns if col not in ['building_id', 'variant_id', 'VariableName', 'category', 'Zone', 'Units']]
        print(f"\nDate columns found: {len(date_cols)}")
        print(f"First few date columns: {date_cols[:5]}")
        
        # Show sample data
        print("\nSample data:")
        print(df.iloc[:3, :8])
        
        # Test conversion
        print("\n\nTesting wide-to-long conversion:")
        metadata_cols = ['building_id', 'variant_id', 'VariableName', 'category', 'Zone', 'Units']
        id_vars = [col for col in metadata_cols if col in df.columns]
        
        # Convert one row as test
        test_row = df.iloc[[0]]
        df_long = test_row.melt(
            id_vars=id_vars,
            value_vars=date_cols[:5],  # Just first 5 dates for testing
            var_name='DateTime',
            value_name='Value'
        )
        
        print(f"\nConverted shape: {df_long.shape}")
        print("\nConverted data:")
        print(df_long)
        
    # Issue 3: Check comparison files
    print("\n\n3. CHECKING COMPARISON FILES:")
    comparison_path = base_path / "parsed_modified_results/comparisons"
    if comparison_path.exists():
        files = list(comparison_path.glob("*.parquet"))
        print(f"\nFound {len(files)} comparison files")
        if files:
            # Check one file
            sample_file = files[0]
            print(f"\nSample file: {sample_file.name}")
            df = pd.read_parquet(sample_file)
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            print("\nSample data:")
            print(df.head(3))
            
            # Check for variant columns
            variant_cols = [col for col in df.columns if col.startswith('variant_')]
            print(f"\nVariant columns: {variant_cols[:5]}...")
    
    # Issue 4: Check validation summaries
    print("\n\n4. CHECKING VALIDATION SUMMARIES:")
    
    # Baseline summary
    baseline_summary_path = validation_path / "baseline/validation_summary.json"
    if baseline_summary_path.exists():
        with open(baseline_summary_path) as f:
            summary = json.load(f)
        
        print("\nBaseline validation summary:")
        print(f"- Status: {summary.get('summary', {}).get('status', 'Unknown')}")
        print(f"- Mappings: {len(summary.get('mappings', []))}")
        print(f"- Validation results: {len(summary.get('validation_results', []))}")
        
        if summary.get('discovery', {}).get('timeseries'):
            print("\nTimeseries data discovered:")
            for name, info in summary['discovery']['timeseries'].items():
                print(f"  - {name}: {info.get('format', 'unknown')} format, {info.get('frequency')} frequency")
    
    # Modified summary
    modified_summary_path = validation_path / "modified/validation_summary.json"
    if modified_summary_path.exists():
        with open(modified_summary_path) as f:
            summary = json.load(f)
        
        print("\n\nModified validation summary:")
        if 'base_results' in summary:
            print("- Base results found")
            print(f"  - Mappings: {len(summary['base_results'].get('mappings', []))}")
            print(f"  - Validations: {len(summary['base_results'].get('validation_results', []))}")
        
        if 'variant_results' in summary:
            print(f"- Variant results: {len(summary['variant_results'])} variants")
            
        # Check why parquet files weren't saved
        print("\n\nChecking why parquet files weren't saved:")
        print("The validation wrapper should save parquet files when:")
        print("1. output_path is provided")
        print("2. validation_results exist in the results")
        print("\nCurrent situation:")
        print(f"- Base validation_results: {len(summary.get('base_results', {}).get('validation_results', []))}")
        for variant_id, variant_data in summary.get('variant_results', {}).items():
            print(f"- {variant_id} validation_results: {len(variant_data.get('validation_results', []))}")

if __name__ == "__main__":
    investigate_issues()