"""
Automated patcher for orchestrator.py to fix the data type issue
"""

import os
import shutil
from datetime import datetime

def apply_orchestrator_fix(orchestrator_path="orchestrator.py"):
    """Apply the data type fix to orchestrator.py"""
    
    print("Applying Data Type Fix to Orchestrator")
    print("="*60)
    
    # Check if file exists
    if not os.path.exists(orchestrator_path):
        print(f"Error: {orchestrator_path} not found!")
        return False
    
    # Read the file
    with open(orchestrator_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already fixed
    if "df_map['ogc_fid_str']" in content:
        print("✓ File already contains the fix!")
        return True
    
    # Create backup
    backup_path = f"{orchestrator_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(orchestrator_path, backup_path)
    print(f"✓ Created backup: {backup_path}")
    
    # Find the section to fix
    # Look for the problematic line
    search_pattern = "orig_building = df_map[df_map['ogc_fid'] == building_id]"
    
    if search_pattern not in content:
        print("Warning: Could not find the exact pattern to fix.")
        print("Looking for alternative patterns...")
        
        # Try alternative patterns
        if "df_map[df_map['ogc_fid'] ==" in content:
            print("Found similar pattern. Manual fix may be needed.")
            print("\nPlease add this line after loading df_map:")
            print("    df_map['ogc_fid_str'] = df_map['ogc_fid'].astype(str)")
            print("\nAnd change comparisons from:")
            print("    df_map[df_map['ogc_fid'] == building_id]")
            print("To:")
            print("    df_map[df_map['ogc_fid_str'] == building_id]")
            return False
    
    # Apply the fix
    # First, add the string conversion after df_map is loaded
    load_pattern = "df_map = pd.read_csv(idf_map_csv)"
    if load_pattern in content:
        # Find all occurrences
        lines = content.split('\n')
        new_lines = []
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # Add the fix after loading df_map
            if load_pattern in line and "logger.info" in lines[i+1] and "Loaded IDF mapping" in lines[i+1]:
                new_lines.append(lines[i+1])  # Add the logger line
                new_lines.append("")  # Empty line
                new_lines.append("                            # CRITICAL FIX: Convert ogc_fid to string for comparison")
                new_lines.append("                            df_map['ogc_fid_str'] = df_map['ogc_fid'].astype(str)")
                i += 1  # Skip the logger line since we already added it
                continue
        
        # Now fix the comparison
        content = '\n'.join(new_lines)
        content = content.replace(
            "orig_building = df_map[df_map['ogc_fid'] == building_id]",
            "# FIXED: Compare using string column\n                                            orig_building = df_map[df_map['ogc_fid_str'] == building_id]"
        )
        
        # Fix the debug line too
        content = content.replace(
            "logger.warning(f\"[WARN] Available IDs: {df_map['ogc_fid'].unique()[:5]}...\")",
            "logger.debug(f\"[DEBUG] Available IDs: {df_map['ogc_fid_str'].unique()[:5].tolist()}...\")"
        )
        
        # Add string conversion for building_data
        content = content.replace(
            "building_data['original_ogc_fid'] = building_id  # Keep original ID",
            """building_data['original_ogc_fid'] = building_id  # Keep original ID
                                                
                                                # Ensure ogc_fid is string for consistency
                                                building_data['ogc_fid'] = str(building_data['ogc_fid'])"""
        )
        
        # Write the fixed content
        with open(orchestrator_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✓ Applied the fix successfully!")
        print("\nChanges made:")
        print("1. Added: df_map['ogc_fid_str'] = df_map['ogc_fid'].astype(str)")
        print("2. Changed comparison to use 'ogc_fid_str' column")
        print("3. Added string conversion for building_data['ogc_fid']")
        print("4. Fixed debug logging")
        
        return True
    else:
        print("Error: Could not find the expected code structure.")
        print("Please apply the fix manually.")
        return False

def verify_fix(orchestrator_path="orchestrator.py"):
    """Verify that the fix was applied correctly"""
    
    print("\nVerifying Fix")
    print("-"*40)
    
    with open(orchestrator_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "String conversion added": "df_map['ogc_fid_str'] = df_map['ogc_fid'].astype(str)" in content,
        "Comparison uses string column": "df_map[df_map['ogc_fid_str'] == building_id]" in content,
        "Building data conversion": "building_data['ogc_fid'] = str(building_data['ogc_fid'])" in content
    }
    
    all_good = True
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check}")
        if not result:
            all_good = False
    
    return all_good

if __name__ == "__main__":
    import sys
    
    # Get orchestrator path from command line or use default
    orchestrator_path = sys.argv[1] if len(sys.argv) > 1 else "orchestrator.py"
    
    print(f"Target file: {orchestrator_path}")
    print()
    
    # Apply the fix
    success = apply_orchestrator_fix(orchestrator_path)
    
    if success:
        # Verify the fix
        if verify_fix(orchestrator_path):
            print("\n✅ Fix applied and verified successfully!")
            print("\nYou can now run your orchestrator normally.")
        else:
            print("\n⚠ Fix was applied but verification shows issues.")
            print("Please check the file manually.")
    else:
        print("\n❌ Could not apply fix automatically.")
        print("Please apply the changes manually as shown above.")
    
    input("\nPress Enter to exit...")