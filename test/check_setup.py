# test/check_setup.py - Diagnostic script to check setup

import sys
import os
from pathlib import Path
import json

print("IDF Modification Test Suite - Setup Diagnostic")
print("=" * 60)

# Check Python version
print(f"\nPython version: {sys.version}")
print(f"Python executable: {sys.executable}")

# Check current directory
current_dir = Path.cwd()
print(f"\nCurrent directory: {current_dir}")

# Check script location
script_dir = Path(__file__).parent
project_root = script_dir.parent
print(f"Script directory: {script_dir}")
print(f"Project root: {project_root}")

# Check if required directories exist
print("\nChecking project structure:")
required_dirs = [
    project_root / "idf_modification",
    project_root / "parserr",
    project_root / "epw",
    project_root / "orchestrator"
]

all_dirs_exist = True
for dir_path in required_dirs:
    exists = dir_path.exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {dir_path.relative_to(project_root) if exists else dir_path}")
    if not exists:
        all_dirs_exist = False

# Check for required files
print("\nChecking required files:")
required_files = [
    project_root / "idf_modification" / "modification_engine.py",
    project_root / "idf_modification" / "base_modifier.py",
    project_root / "parserr" / "idf_parser.py",
    project_root / "epw" / "run_epw_sims.py"
]

all_files_exist = True
for file_path in required_files:
    exists = file_path.exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {file_path.relative_to(project_root) if exists else file_path}")
    if not exists:
        all_files_exist = False

# Check imports
print("\nChecking imports:")
sys.path.insert(0, str(project_root))

import_status = {}
modules_to_check = [
    ("eppy", "eppy.modeleditor"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("scipy", "scipy.stats"),
    ("idf_modification", "idf_modification.modification_engine"),
    ("parserr", "parserr.idf_parser")
]

for module_name, import_path in modules_to_check:
    try:
        __import__(import_path)
        import_status[module_name] = True
        print(f"  ✓ {module_name}")
    except ImportError as e:
        import_status[module_name] = False
        print(f"  ✗ {module_name}: {e}")

# Check test configuration
print("\nChecking test configuration:")
config_path = script_dir / "test_config.json"
if config_path.exists():
    print(f"  ✓ test_config.json found")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"    Test name: {config.get('test_name', 'Not specified')}")
        
        # Check paths in config
        if 'paths' in config:
            print("\n  Checking paths in config:")
            for path_name, path_value in config['paths'].items():
                if path_name == 'output_dir':
                    print(f"    {path_name}: {path_value} (will be created)")
                else:
                    path_obj = Path(path_value)
                    exists = path_obj.exists()
                    status = "✓" if exists else "✗"
                    print(f"    {status} {path_name}: {path_value}")
    except json.JSONDecodeError as e:
        print(f"  ✗ Error reading test_config.json: {e}")
else:
    print(f"  ✗ test_config.json not found")

# Check test output directory
print("\nChecking test output:")
output_dir = script_dir / "test_output"
if output_dir.exists():
    print(f"  ✓ test_output directory exists")
    # Count files
    num_files = len(list(output_dir.glob("*")))
    print(f"    Contains {num_files} files/folders")
else:
    print(f"  - test_output directory will be created on first run")

# Summary
print("\n" + "=" * 60)
print("SUMMARY:")

issues = []
if not all_dirs_exist:
    issues.append("Some required directories are missing")
if not all_files_exist:
    issues.append("Some required files are missing")
if not import_status.get("eppy", False):
    issues.append("eppy is not installed (run: pip install eppy)")
if not import_status.get("pandas", False):
    issues.append("pandas is not installed (run: pip install pandas)")
if not import_status.get("idf_modification", False):
    issues.append("Cannot import idf_modification module")
if not import_status.get("parserr", False):
    issues.append("Cannot import parserr module")

if issues:
    print("Issues found:")
    for issue in issues:
        print(f"  - {issue}")
    print("\nPlease fix these issues before running tests.")
else:
    print("✓ All checks passed! You're ready to run tests.")
    print("\nNext steps:")
    print("  1. Run: python main_test.py")
    print("  2. Or use the interactive menu: python run_test.py")

print("\n" + "=" * 60)