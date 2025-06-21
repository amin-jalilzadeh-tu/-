#!/usr/bin/env python
"""Run simulations for modified IDF files"""

import os
import sys
import subprocess
from pathlib import Path
import json

# Configuration
PROJECT_ROOT = r"D:\Documents\daily\E_Plus_2040_py"
OUTPUT_DIR = r"D:\Documents\daily\E_Plus_2040_py\output\ec9b5acf-12c0-4abc-940e-bc29a1106d52"
ENERGYPLUS_EXE = r"path\to\energyplus.exe"  # UPDATE THIS

sys.path.insert(0, PROJECT_ROOT)

def run_modified_simulations():
    """Run simulations for all modified IDF files"""
    
    modified_dir = Path(OUTPUT_DIR) / "modified_idfs"
    sim_output_dir = Path(OUTPUT_DIR) / "Sim_Results_Modified"
    sim_output_dir.mkdir(exist_ok=True)
    
    # Find all IDF files
    idf_files = []
    for building_dir in modified_dir.glob("building_*"):
        idf_files.extend(building_dir.glob("*.idf"))
    
    print(f"Found {len(idf_files)} IDF files to simulate")
    
    # Load config for EPW file
    with open(os.path.join(PROJECT_ROOT, "combined.json"), 'r') as f:
        config = json.load(f)
    
    # Get EPW file (you may need to adjust this based on your config)
    epw_file = "path/to/weather.epw"  # UPDATE THIS
    
    # Run simulations
    for i, idf_file in enumerate(idf_files):
        print(f"\nSimulating {i+1}/{len(idf_files)}: {idf_file.name}")
        
        # Create output directory for this simulation
        output_name = idf_file.stem
        sim_dir = sim_output_dir / output_name
        sim_dir.mkdir(exist_ok=True)
        
        # Run EnergyPlus
        cmd = [
            ENERGYPLUS_EXE,
            "-w", epw_file,
            "-d", str(sim_dir),
            str(idf_file)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✓ Success")
            else:
                print(f"  ✗ Failed: {result.stderr}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("\nSimulation batch complete!")

if __name__ == "__main__":
    run_modified_simulations()
