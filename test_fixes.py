#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script to verify all fixes are working"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project to path
BASE_DIR = Path(r"D:\Documents\daily\E_Plus_2040_py")
sys.path.insert(0, str(BASE_DIR))

print("="*60)
print("TESTING WORKFLOW FIXES")
print("="*60)

# Test 1: Import modules
print("\n1. Testing imports...")
try:
    from idf_modification.modification_tracker import ModificationTracker
    from idf_modification.modification_engine import ModificationEngine
    from c_sensitivity.sensitivity_analyzer import SensitivityAnalyzer
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    exit(1)

# Test 2: ModificationTracker methods
print("\n2. Testing ModificationTracker...")
tracker = ModificationTracker()

methods_needed = ['start_session', 'log_modification', 'track_modification', 'get_modifications']
all_good = True
for method in methods_needed:
    if hasattr(tracker, method):
        print(f"  ✓ Method '{method}' exists")
    else:
        print(f"  ✗ Method '{method}' missing")
        all_good = False

if all_good:
    # Test start_session
    try:
        tracker.start_session("test_session", "building_123", "/path/to/idf")
        print("  ✓ start_session() works correctly")
    except Exception as e:
        print(f"  ✗ start_session() failed: {e}")

# Test 3: ModificationEngine
print("\n3. Testing ModificationEngine...")
project_dir = BASE_DIR / "output" / "3252a6f1-32c2-488d-a5a3-5641b7d02738"

# Test with config dict
config_path = BASE_DIR / "combined.json"
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    engine = ModificationEngine(str(project_dir), config)
    print("  ✓ ModificationEngine created with config dict")
    
    # Check if tracker has start_session
    if hasattr(engine.tracker, 'start_session'):
        print("  ✓ Engine's tracker has start_session method")
    else:
        print("  ✗ Engine's tracker missing start_session method")
        
except Exception as e:
    print(f"  ✗ ModificationEngine with config failed: {e}")

# Test with string (legacy)
try:
    engine2 = ModificationEngine(str(project_dir), "test_session_123")
    print("  ✓ ModificationEngine created with session_id string (legacy)")
except Exception as e:
    print(f"  ✗ ModificationEngine (legacy) failed: {e}")

# Test 4: Sensitivity Analyzer
print("\n4. Testing SensitivityAnalyzer...")
try:
    analyzer = SensitivityAnalyzer(str(project_dir))
    print("  ✓ SensitivityAnalyzer created")
    
    # Don't run analysis yet, just check it exists
    if hasattr(analyzer, 'run_analysis'):
        print("  ✓ run_analysis method exists")
except Exception as e:
    print(f"  ✗ SensitivityAnalyzer failed: {e}")

# Test 5: Config file
print("\n5. Checking configuration...")
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"  ✓ Buildings configured: {len(config.get('buildings', []))}")
    print(f"  ✓ Modifications enabled: {config.get('modifications', {}).get('enable_modifications', False)}")
    print(f"  ✓ Scenarios defined: {len(config.get('modifications', {}).get('scenarios', {}))}")
except Exception as e:
    print(f"  ✗ Config check failed: {e}")

print("\n" + "="*60)
print("TESTING COMPLETE")
print("="*60)
print("\nIf all tests pass, run your main workflow!")