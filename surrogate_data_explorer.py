import os
import pandas as pd
from pathlib import Path
import glob
import json
from datetime import datetime

def deep_diagnostic_exploration(root_path):
    """Deep diagnostic exploration to find root issues with surrogate model inputs"""
    
    root = Path(root_path)
    print(f"=== SURROGATE MODEL DEEP DIAGNOSTICS ===")
    print(f"Root Path: {root}")
    print(f"Diagnostic Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # ISSUE 1: Missing Simulation Outputs
    print("\n🔍 INVESTIGATING MISSING SIMULATION OUTPUTS")
    print("-" * 50)
    
    # Check all possible output locations
    output_locations = [
        'parsed_data/outputs',
        'parsed_modified_results/outputs',
        'parsed_data/results',
        'parsed_modified_results/results',
        'simulation_results',
        'outputs',
        'results'
    ]
    
    print("Searching for output files in all possible locations:")
    found_outputs = {}
    
    for location in output_locations:
        path = root / location
        if path.exists():
            # Look for any parquet, csv, or json files
            parquet_files = list(path.rglob('*.parquet'))
            csv_files = list(path.rglob('*.csv'))
            json_files = list(path.rglob('*.json'))
            
            if parquet_files or csv_files or json_files:
                found_outputs[location] = {
                    'parquet': len(parquet_files),
                    'csv': len(csv_files),
                    'json': len(json_files),
                    'samples': parquet_files[:2] + csv_files[:2]
                }
                print(f"\n  ✓ {location}:")
                print(f"    - {len(parquet_files)} parquet files")
                print(f"    - {len(csv_files)} csv files")
                print(f"    - {len(json_files)} json files")
                
                # Show sample files
                for f in found_outputs[location]['samples'][:3]:
                    print(f"    • {f.relative_to(root)}")
    
    if not found_outputs:
        print("\n  ❌ NO OUTPUT FILES FOUND IN ANY LOCATION!")
        print("\n  Possible reasons:")
        print("    1. Simulations may have failed")
        print("    2. Parsing step may have been skipped")
        print("    3. Output files may be in a different format")
    
    # ISSUE 2: Check Simulation Status
    print("\n\n🔍 CHECKING SIMULATION STATUS")
    print("-" * 50)
    
    # Look for simulation logs or status files
    sim_patterns = [
        '**/simulation_*.log',
        '**/eplusout.err',
        '**/eplusout.end',
        '**/simulation_status.json',
        '**/job_status.json'
    ]
    
    for pattern in sim_patterns:
        files = list(root.glob(pattern))
        if files:
            print(f"\nFound {len(files)} {pattern} files:")
            for f in files[:3]:
                print(f"  • {f.relative_to(root)}")
                
                # Check for errors in .err files
                if f.suffix == '.err':
                    with open(f, 'r') as file:
                        content = file.read()
                        if 'Fatal' in content or 'Severe' in content:
                            print(f"    ⚠️ Contains errors!")
    
    # Check building registry for simulation status
    reg_path = root / 'parsed_data' / 'metadata' / 'building_registry.parquet'
    if reg_path.exists():
        df = pd.read_parquet(reg_path)
        print(f"\nBuilding Registry Status:")
        if 'status' in df.columns:
            status_counts = df['status'].value_counts()
            for status, count in status_counts.items():
                print(f"  • {status}: {count} buildings")
    
    # ISSUE 3: Sensitivity Analysis Deep Dive
    print("\n\n🔍 SENSITIVITY ANALYSIS INVESTIGATION")
    print("-" * 50)
    
    sens_path = root / 'sensitivity_results' / 'sensitivity_for_surrogate.parquet'
    if sens_path.exists():
        df = pd.read_parquet(sens_path)
        print(f"Total parameters analyzed: {len(df)}")
        
        # Check sensitivity score distribution
        if 'sensitivity_score' in df.columns:
            print(f"\nSensitivity Score Statistics:")
            print(f"  • Min: {df['sensitivity_score'].min():.6f}")
            print(f"  • Max: {df['sensitivity_score'].max():.6f}")
            print(f"  • Mean: {df['sensitivity_score'].mean():.6f}")
            print(f"  • Std: {df['sensitivity_score'].std():.6f}")
            print(f"  • 75th percentile: {df['sensitivity_score'].quantile(0.75):.6f}")
            
            # Show all parameters with scores
            print(f"\nAll {len(df)} parameters with scores:")
            for idx, row in df.iterrows():
                param_desc = f"{row.get('category', 'N/A')} - {row.get('parameter', 'N/A')}"
                score = row.get('sensitivity_score', 0)
                print(f"  {idx+1}. {param_desc}: {score:.6f}")
        
        # Check why so few parameters
        print(f"\nWhy only {len(df)} parameters?")
        print("  Checking modification vs sensitivity mismatch...")
    
    # ISSUE 4: Modification to Output Linkage
    print("\n\n🔍 MODIFICATION TO OUTPUT LINKAGE")
    print("-" * 50)
    
    # Load modifications
    mod_files = list(glob.glob(str(root / 'modified_idfs' / 'modifications_detail_*.parquet')))
    if mod_files:
        mod_df = pd.read_parquet(mod_files[0])
        print(f"Total modifications: {len(mod_df)}")
        print(f"Unique parameters: {mod_df['category'].nunique()} categories")
        
        # Group by category
        print("\nModifications by category:")
        category_counts = mod_df['category'].value_counts()
        for cat, count in category_counts.items():
            print(f"  • {cat}: {count} modifications")
        
        # Check variant distribution
        if 'variant_id' in mod_df.columns:
            variant_counts = mod_df['variant_id'].value_counts()
            print(f"\nVariants created: {len(variant_counts)}")
            print(f"  • Min modifications per variant: {variant_counts.min()}")
            print(f"  • Max modifications per variant: {variant_counts.max()}")
    
    # ISSUE 5: Check Parsing Configuration
    print("\n\n🔍 PARSING CONFIGURATION CHECK")
    print("-" * 50)
    
    # Look for parsing config or results
    parsing_locations = [
        'parsed_data/metadata/parse_config.json',
        'config/parsing_config.json',
        'parsing_results.json'
    ]
    
    for loc in parsing_locations:
        path = root / loc
        if path.exists():
            print(f"\nFound parsing config: {loc}")
            with open(path, 'r') as f:
                config = json.load(f)
                print(f"  Config keys: {list(config.keys())}")
    
    # ISSUE 6: Check for Raw Simulation Results
    print("\n\n🔍 RAW SIMULATION RESULTS")
    print("-" * 50)
    
    # Look for EnergyPlus output files
    ep_patterns = [
        '**/*.sql',  # EnergyPlus SQLite outputs
        '**/eplusout.csv',
        '**/eplusout.eso',
        '**/eplusssz.csv'
    ]
    
    for pattern in ep_patterns:
        files = list(root.glob(pattern))
        if files:
            print(f"\nFound {len(files)} {pattern.split('/')[-1]} files")
            for f in files[:5]:
                size_mb = f.stat().st_size / 1024 / 1024
                print(f"  • {f.relative_to(root)} ({size_mb:.2f} MB)")
    
    # ISSUE 7: Pipeline Status Check
    print("\n\n🔍 PIPELINE EXECUTION STATUS")
    print("-" * 50)
    
    # Check which steps were executed
    step_indicators = {
        'IDF Creation': root / 'modified_idfs',
        'Simulations': list(root.glob('**/*.sql')),
        'Parsing': root / 'parsed_data',
        'Modification': root / 'modified_idfs' / 'modifications_detail_*.parquet',
        'Sensitivity': root / 'sensitivity_results',
        'Validation': root / 'validation_results'
    }
    
    print("Pipeline step execution status:")
    for step, indicator in step_indicators.items():
        if isinstance(indicator, Path):
            exists = indicator.exists()
        elif isinstance(indicator, list):
            exists = len(indicator) > 0
        else:
            exists = len(list(glob.glob(str(indicator)))) > 0
        
        status = "✓ Executed" if exists else "❌ Not executed"
        print(f"  {status} - {step}")
    
    # ISSUE 8: Recommendations
    print("\n\n💡 DIAGNOSTIC SUMMARY & RECOMMENDATIONS")
    print("-" * 50)
    
    issues_found = []
    
    if not found_outputs:
        issues_found.append({
            'issue': 'No simulation outputs found',
            'severity': 'CRITICAL',
            'recommendation': 'Check if parsing step was executed. Look for .sql files and run parsing if needed.'
        })
    
    if sens_path.exists():
        df = pd.read_parquet(sens_path)
        if len(df) < 20:
            issues_found.append({
                'issue': f'Only {len(df)} parameters in sensitivity analysis',
                'severity': 'HIGH',
                'recommendation': 'Sensitivity analysis may have filtered too aggressively or failed partially.'
            })
    
    print(f"\nFound {len(issues_found)} critical issues:\n")
    for i, issue in enumerate(issues_found, 1):
        print(f"{i}. [{issue['severity']}] {issue['issue']}")
        print(f"   → {issue['recommendation']}\n")
    
    # Final check - are SQL files present but not parsed?
    sql_files = list(root.glob('**/*.sql'))
    if sql_files and not found_outputs:
        print("\n⚠️ CRITICAL FINDING:")
        print(f"  Found {len(sql_files)} SQL simulation result files but no parsed outputs!")
        print("  This suggests the PARSING STEP was not executed.")
        print("\n  Next steps:")
        print("  1. Run the parsing step to convert SQL files to parquet")
        print("  2. Ensure 'perform_parsing': true in configuration")
        print("  3. Re-run surrogate modeling after parsing completes")


# Run the diagnostics
if __name__ == "__main__":
    root_path = r"D:\Documents\daily\E_Plus_2040_py\output\f89bc1a7-176a-4f2e-9012-b626392ae859"
    deep_diagnostic_exploration(root_path)











    