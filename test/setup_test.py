# test/setup_test.py - Setup script for test environment

import os
import sys
from pathlib import Path
import shutil

def setup_test_environment():
    """Setup the test environment with proper directory structure"""
    
    print("Setting up test environment...")
    
    # Get current directory
    test_dir = Path(__file__).parent
    project_root = test_dir.parent
    
    # Create necessary directories
    directories = [
        'output',
        'logs',
        'simulation_results',
        'test_output',
        'test_output/modified_idfs',
        'test_output/reports'
    ]
    
    for dir_name in directories:
        dir_path = test_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")
    
    # Create __init__.py files for proper imports
    init_files = [
        test_dir / '__init__.py',
        project_root / '__init__.py'
    ]
    
    for init_file in init_files:
        if not init_file.exists():
            init_file.touch()
            print(f"Created: {init_file}")
    
    # Check for required dependencies
    print("\nChecking dependencies...")
    required_modules = [
        'eppy',
        'pandas',
        'numpy',
        'scipy'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module} installed")
        except ImportError:
            print(f"✗ {module} missing")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\nPlease install missing modules:")
        print(f"pip install {' '.join(missing_modules)}")
    
    # Check paths in config
    print("\nChecking paths...")
    paths_to_check = {
        'IDD file': r"D:\Documents\daily\E_Plus_2040_py\EnergyPlus\Energy+.idd",
        'EPW file': r"D:\Documents\daily\E_Plus_2040_py\data\weather\2020.epw",
        'Test IDF': r"D:\Documents\daily\E_Plus_2040_py\output\b0fb6596-3303-4494-bc5f-5741a4db5e11\output_IDFs\building_4136733.idf"
    }
    
    all_paths_exist = True
    for name, path in paths_to_check.items():
        if Path(path).exists():
            print(f"✓ {name}: {path}")
        else:
            print(f"✗ {name} not found: {path}")
            all_paths_exist = False
    
    if not all_paths_exist:
        print("\nPlease update paths in test_config.json")
    
    # Create a simple test script
    simple_test = test_dir / 'run_simple_test.py'
    with open(simple_test, 'w') as f:
        f.write("""#!/usr/bin/env python
# Simple test script to verify setup

import sys
from pathlib import Path

# Add test directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run
from modifier import StandaloneModifier
from run_simulation import StandaloneSimulator

print("Testing modifier import... OK")
print("Testing simulator import... OK")

# Try to load config
import json
config_path = Path(__file__).parent / 'test_config.json'
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
    print(f"Config loaded: {config['test_name']}")
else:
    print("test_config.json not found!")

print("\\nSetup verification complete!")
print("Run 'python main_test.py' to start tests")
""")
    
    print(f"\nCreated simple test script: {simple_test}")
    
    print("\nSetup complete!")
    print("\nTo run tests:")
    print("1. cd to the test directory")
    print("2. python main_test.py")
    print("\nOr run specific scenarios:")
    print("python main_test.py --scenarios efficient_hvac efficient_lighting")

if __name__ == "__main__":
    setup_test_environment()