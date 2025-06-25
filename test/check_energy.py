# test/check_energy.py - Manually check energy consumption from simulation results

import sys
from pathlib import Path
import pandas as pd

def check_energy_consumption():
    """Manually check energy consumption from EnergyPlus outputs"""
    sim_dir = Path("simulation_results")
    
    if not sim_dir.exists():
        print("No simulation results directory found!")
        return
    
    print("Energy Consumption Summary")
    print("=" * 60)
    
    results = {}
    
    # Check each scenario directory
    for scenario_dir in sorted(sim_dir.iterdir()):
        if not scenario_dir.is_dir():
            continue
            
        scenario_name = scenario_dir.name.split('_', 1)[1] if '_' in scenario_dir.name else scenario_dir.name
        print(f"\nScenario: {scenario_name}")
        print("-" * 40)
        
        # Look for Table output (easiest to parse)
        table_files = list(scenario_dir.glob("*Table.csv"))
        meter_files = list(scenario_dir.glob("*Meter.csv"))
        
        scenario_energy = {}
        
        # Try to read meter files with different approaches
        for meter_file in meter_files:
            print(f"  Checking: {meter_file.name}")
            
            try:
                # Try to read just the last line which often has totals
                with open(meter_file, 'r') as f:
                    lines = f.readlines()
                
                # Find the data section
                data_start = 0
                for i, line in enumerate(lines):
                    if 'Date/Time' in line or 'DateTime' in line:
                        data_start = i
                        break
                
                if data_start > 0 and data_start < len(lines) - 1:
                    # Get header and last line
                    header = lines[data_start].strip().split(',')
                    
                    # Find some data lines (skip empty ones at the end)
                    data_lines = []
                    for line in reversed(lines[data_start+1:]):
                        if line.strip() and not line.startswith('Program'):
                            data_lines.append(line.strip().split(','))
                            if len(data_lines) >= 10:  # Get last 10 data lines
                                break
                    
                    if data_lines and header:
                        # Sum up energy columns
                        for col_idx, col_name in enumerate(header[1:], 1):  # Skip date column
                            if '[J]' in col_name or 'Energy' in col_name:
                                try:
                                    # Sum the values from data lines
                                    total = sum(float(line[col_idx]) for line in data_lines if len(line) > col_idx and line[col_idx])
                                    
                                    # Extract clean name
                                    clean_name = col_name.replace('[J](Hourly)', '').replace('[J](Daily)', '').strip()
                                    scenario_energy[clean_name] = total
                                    
                                    # Convert to kWh for readability
                                    kwh = total / 3600000  # J to kWh
                                    print(f"    {clean_name}: {kwh:,.1f} kWh")
                                    
                                except (ValueError, IndexError):
                                    pass
                
            except Exception as e:
                print(f"    Error reading {meter_file.name}: {e}")
        
        results[scenario_name] = scenario_energy
    
    # Compare results
    if 'baseline' in results and len(results) > 1:
        print("\n" + "=" * 60)
        print("ENERGY SAVINGS COMPARISON:")
        print("=" * 60)
        
        baseline = results['baseline']
        
        for scenario_name, scenario_data in results.items():
            if scenario_name == 'baseline':
                continue
                
            print(f"\n{scenario_name} vs baseline:")
            
            # Compare common meters
            for meter_name in baseline:
                if meter_name in scenario_data:
                    base_val = baseline[meter_name]
                    scen_val = scenario_data[meter_name]
                    
                    if base_val > 0:
                        pct_change = ((scen_val - base_val) / base_val) * 100
                        kwh_change = (scen_val - base_val) / 3600000
                        
                        print(f"  {meter_name}:")
                        print(f"    Change: {pct_change:+.1f}% ({kwh_change:+,.1f} kWh)")
    
    # Look for HTML summary reports
    print("\n" + "=" * 60)
    print("HTML SUMMARY REPORTS:")
    print("=" * 60)
    
    for scenario_dir in sim_dir.iterdir():
        if scenario_dir.is_dir():
            html_files = list(scenario_dir.glob("*.html"))
            if html_files:
                scenario_name = scenario_dir.name.split('_', 1)[1] if '_' in scenario_dir.name else scenario_dir.name
                print(f"\n{scenario_name}:")
                for html in html_files:
                    print(f"  Open in browser: {html.absolute()}")

if __name__ == "__main__":
    check_energy_consumption()