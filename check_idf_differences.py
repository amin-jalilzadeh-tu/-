
# Manual test for IDF modifications
import os
from pathlib import Path

# Find a sample IDF file
modified_dir = Path(r"D:\Documents\daily\E_Plus_2040_py\output\ec9b5acf-12c0-4abc-940e-bc29a1106d52\modified_idfs")

# Look for building directories
for building_dir in modified_dir.glob("building_*"):
    print(f"\nChecking {building_dir.name}:")
    
    # Get all IDF files
    idf_files = list(building_dir.glob("*.idf"))
    
    if len(idf_files) >= 2:
        # Compare first two files
        file1 = idf_files[0]
        file2 = idf_files[1]
        
        print(f"  Comparing {file1.name} vs {file2.name}")
        
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()
            
        # Find differences
        differences = 0
        for i, (line1, line2) in enumerate(zip(lines1, lines2)):
            if line1 != line2:
                differences += 1
                if differences <= 5:  # Show first 5 differences
                    print(f"    Line {i}:")
                    print(f"      File1: {line1.strip()}")
                    print(f"      File2: {line2.strip()}")
        
        print(f"  Total differences: {differences} lines")
        
        if differences == 0:
            print("  ⚠️ FILES ARE IDENTICAL - Modifications not applied!")
