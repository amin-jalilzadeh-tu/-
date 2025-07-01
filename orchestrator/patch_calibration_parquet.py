"""
Patch for orchestrator to use parquet files directly for calibration
Apply this before running calibration
"""

import sys
from pathlib import Path

# Add cal directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cal.unified_calibration_parquet import patch_unified_calibration

# Apply the patch
patch_unified_calibration()

print("Calibration system patched to use parquet files directly")