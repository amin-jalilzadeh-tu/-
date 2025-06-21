#!/usr/bin/env python
"""Quick script to run modified IDF simulations"""

import os
import subprocess
from pathlib import Path

# Configuration
ENERGYPLUS_EXE = r"C:\EnergyPlusV9-5-0\energyplus.exe"  # UPDATE THIS
EPW_FILE = r"D:\Documents\daily\E_Plus_2040_py\data\weather\2020.epw"  # UPDATE THIS
MODIFIED_IDFS_DIR = r"D:\Documents\daily\E_Plus_2040_py\output\ec9b5acf-12c0-4abc-940e-bc29a1106d52\modified_idfs\building_4136733\20250621_111645"
OUTPUT_DIR = r"D:\Documents\daily\E_Plus_2040_py\output\ec9b5acf-12c0-4abc-940e-bc29a1106d52\Sim_Results_Modified"

def run_simulations():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    idf_files = list(Path(MODIFIED_IDFS_DIR).glob("*.idf"))
    print(f"Found {len(idf_files)} IDF files to simulate")
    
    for i, idf in enumerate(idf_files):
        print(f"\n[{i+1}/{len(idf_files)}] {idf.name}")
        
        sim_dir = os.path.join(OUTPUT_DIR, idf.stem)
        os.makedirs(sim_dir, exist_ok=True)
        
        cmd = [ENERGYPLUS_EXE, "-w", EPW_FILE, "-d", sim_dir, str(idf)]
        
        try:
            subprocess.run(cmd, check=True)
            print("  ✓ Success")
        except:
            print("  ✗ Failed")

if __name__ == "__main__":
    run_simulations()
