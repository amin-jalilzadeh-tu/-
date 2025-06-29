# test/view_results.py - View test results

import json
from pathlib import Path
import sys

def view_latest_results():
    """View the latest test results"""
    test_output = Path("test_output")
    
    # Find latest results file
    result_files = list(test_output.glob("test_results_*.json"))
    if not result_files:
        print("No test results found!")
        return
    
    latest_result = max(result_files, key=lambda x: x.stat().st_mtime)
    print(f"Loading results from: {latest_result}")
    print("=" * 60)
    
    with open(latest_result, 'r') as f:
        results = json.load(f)
    
    print(f"\nTest: {results['test_name']}")
    print(f"Started: {results['start_time']}")
    print(f"Completed: {results.get('end_time', 'Not completed')}")
    
    print("\n" + "=" * 60)
    print("SCENARIOS RUN:")
    print("=" * 60)
    
    for scenario_name, scenario_data in results['scenarios'].items():
        print(f"\n{scenario_name.upper()}:")
        print(f"  Description: {scenario_data['description']}")
        print(f"  Time: {scenario_data['elapsed_time']:.1f}s")
        
        if scenario_data['modification_results']:
            mod_results = scenario_data['modification_results']
            print(f"  Modifications: {len(mod_results['modifications'])}")
            print(f"  Success: {mod_results['success']}")
            
            # Show modification details
            if mod_results['modifications']:
                print("\n  Modified parameters:")
                by_category = {}
                for mod in mod_results['modifications']:
                    cat = mod.get('category', 'unknown')
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append(mod)
                
                for cat, mods in by_category.items():
                    print(f"    {cat}: {len(mods)} modifications")
                    for mod in mods[:3]:  # Show first 3
                        print(f"      - {mod['parameter']}: {mod['original_value']} → {mod['new_value']}")
                    if len(mods) > 3:
                        print(f"      ... and {len(mods) - 3} more")
        
        if scenario_data['simulation_results']:
            sim_results = scenario_data['simulation_results']
            print(f"\n  Simulation: {'Success' if sim_results['success'] else 'Failed'}")
            if sim_results['results'].get('csv_files'):
                print(f"  Output files: {len(sim_results['results']['csv_files'])} CSV files")
    
    # Try to show energy comparison if available
    if 'comparisons' in results and results['comparisons']:
        print("\n" + "=" * 60)
        print("ENERGY COMPARISON:")
        print("=" * 60)
        print("\n(Note: CSV comparison had parsing errors - showing available data)")
        
        for scenario, comparison in results['comparisons'].items():
            if comparison:
                print(f"\n{scenario}:")
                for file_data in comparison.values():
                    for meter, values in file_data.items():
                        if 'pct_change' in values and values['pct_change'] != 0:
                            print(f"  {meter}: {values['pct_change']:.1f}% change")
    
    # Alternative: Look for SQL files which might have summary data
    print("\n" + "=" * 60)
    print("ALTERNATIVE RESULTS:")
    print("=" * 60)
    
    sim_results_dir = Path("simulation_results")
    if sim_results_dir.exists():
        for scenario_dir in sim_results_dir.iterdir():
            if scenario_dir.is_dir():
                sql_files = list(scenario_dir.glob("*.sql"))
                err_files = list(scenario_dir.glob("*.err"))
                
                print(f"\n{scenario_dir.name}:")
                if sql_files:
                    print(f"  ✓ SQL output found (contains detailed results)")
                if err_files:
                    # Check for errors
                    for err_file in err_files:
                        with open(err_file, 'r') as f:
                            content = f.read()
                        if "** Fatal  **" in content:
                            print(f"  ✗ Fatal errors in simulation")
                        elif "** Severe  **" in content:
                            print(f"  ⚠ Severe warnings in simulation")
                        else:
                            print(f"  ✓ No severe errors")
    
    # Show summary file location
    summary_files = list(test_output.glob("test_summary_*.txt"))
    if summary_files:
        latest_summary = max(summary_files, key=lambda x: x.stat().st_mtime)
        print(f"\nHuman-readable summary available at:")
        print(f"  {latest_summary}")
        
        # Show a preview
        print("\nSummary preview:")
        print("-" * 40)
        with open(latest_summary, 'r') as f:
            lines = f.readlines()
            for line in lines[:20]:  # First 20 lines
                print(line.rstrip())
            if len(lines) > 20:
                print("... (see full file for more)")

if __name__ == "__main__":
    view_latest_results()