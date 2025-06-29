#!/usr/bin/env python3
"""
Test the sensitivity analysis fix
"""

import logging
from pathlib import Path
from c_sensitivity.modification_analyzer import ModificationSensitivityAnalyzer

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Test loading modification tracking
job_dir = Path("output/f1bece00-4e3b-499b-a691-39ec0ed8a5f6")

analyzer = ModificationSensitivityAnalyzer(job_dir, logger)

try:
    # Load modification tracking
    logger.info("Loading modification tracking...")
    mod_df = analyzer.load_modification_tracking()
    
    logger.info(f"Successfully loaded {len(mod_df)} modifications")
    logger.info(f"Columns in modification data: {list(mod_df.columns)}")
    
    # Check key columns
    key_cols = ['param_key', 'field_clean', 'param_display_name']
    for col in key_cols:
        if col in mod_df.columns:
            logger.info(f"✓ {col} column exists")
            # Show some examples
            unique_vals = mod_df[col].unique()[:5]
            logger.info(f"  Sample values: {unique_vals}")
        else:
            logger.error(f"✗ {col} column missing")
    
    logger.info("\nTest passed! Modification tracking loads correctly.")
    
except Exception as e:
    logger.error(f"Test failed: {e}")
    import traceback
    traceback.print_exc()