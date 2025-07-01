# E_Plus_2040_py - Files to Delete Report

Generated: 2025-01-07

## Executive Summary

This report identifies files in the E_Plus_2040_py project that can be safely deleted as they are not part of the core workflow. The analysis covers all directories and categorizes files by type and purpose.

## Files Already Deleted (per git status)

The following files have already been deleted and this action should be maintained:

### Test Scripts (79 files)
- All `test_*.py` files in root directory
- Debug scripts (`debug_*.py`)
- Analysis scripts (`analyze_*.py`, `check_*.py`, `verify_*.py`)
- Fix/patch scripts (`fix_*.py`, `apply_*.py`)
- Standalone runners and utilities

### Documentation (29 files)
- Old workflow documentation (`*_SUMMARY.md`, `*_GUIDE.md`, etc.)
- Process flow diagrams and reports
- SQL extraction plans and analyses
- Validation and sensitivity reports

### Generated Outputs (11 files)
- CSV exports (`*.csv`)
- PNG images (`*.png`)
- Text outputs (`*.txt`)
- JSON test results

### Other (8 files)
- Jupyter notebooks (`*.ipynb`)
- Shell scripts (`*.sh`)
- Archive files (`*.rar`)
- Executable (`curl.exe`)
- Patch files (`*.patch`)

## Additional Files to Delete

### 1. Root Directory Cleanup

#### Potential Obsolete Files
- `main_modifi.py` - Old modification system (superseded by orchestrator/modification_step.py)
- `orchestrator.py` - Old wrapper (main orchestrator is now in orchestrator/main.py)
- `combined copy.json` - Duplicate configuration file

### 2. MD_prompt_explorings/ Directory
**DELETE ENTIRE DIRECTORY** - Contains 30+ documentation exploration files not used in workflow

### 3. orchestrator/ Directory
- `patch_calibration_parquet.py` - Applied patch file

### 4. parserr/ Directory
- `parserr.rar` - Archive file
- `sql_enhanced_extractor.py` - Superseded version

### 5. cal/ Directory
- `main cal.py` - Temporary file with space in name
- `implementation_calibration_summary.md` - Documentation
- `implementation_summary_Sensitivity_Analysis.md` - Documentation
- `enhanced_config_examples_Calibration.json` - Example config

### 6. idf_objects/ Directory
- `ventilation/schedules copy.py` - Duplicate file
- `fenez/materials_lookup0.py` - Old version
- `fenez/4.md` - Random markdown file
- `fenez/database_handler.cpython-39.pyc` - Misplaced compiled file
- `HVAC/hvac_lookup2.py` - Old version
- `HVAC/hvac_lookup3.py` - Old version
- `DHW/dhw.tex` - LaTeX documentation
- `HVAC/hvac.tex` - LaTeX documentation
- `Elec/light.tex` - LaTeX documentation
- `ventilation/vent.tex` - LaTeX documentation

### 7. validation/ Directory
- `smart_validation_wrapper.py.bak` - Backup file
- `Archieve 2/example-validation-config.json` - Example config
- `archieve/` - Empty directory

### 8. c_sensitivity/ Directory
- `advanced_config_example.json` - Example config

### 9. c_surrogate/ Directory
- `0 enhanced_config_examples_Surrogate.json` - Example config
- `0 ml_vs_automl_comparison.md` - Documentation
- `0 surrogate_quick_reference.md` - Documentation

### 10. System Files to Clean
- **All `__pycache__/` directories** - Python cache directories
- **All `.pyc` files** - Compiled Python files
- **Empty directories**: `logs/`, `user_configs/`

## Core Files to KEEP

These files are essential to the workflow and must NOT be deleted:

### Entry Points
- `app.py` - Flask API application
- `job_manager.py` - Job management system
- `run_job.sh` - Job execution script

### Core Modules
- `database_handler.py` - Database operations
- `idf_creation.py` - IDF creation logic
- `splitter.py` - Configuration splitter
- `cleanup_old_jobs.py` - Job cleanup
- `excel_overrides.py` - Excel overrides
- `user_config_overrides.py` - User overrides
- `zip_and_mail.py` - Results packaging

### Configuration
- `combined.json` - Main configuration
- `requirements_base.txt` - Python dependencies
- `requirements_dev.txt` - Development dependencies
- `docker-compose.yml` - Docker configuration
- `Dockerfile` - Docker image definition

### Documentation
- `CLAUDE.md` - Project instructions
- `E_PLUS_2040_WORKFLOW.md` - Workflow documentation
- `E_PLUS_2040_WORKFLOW_V2.md` - Updated workflow
- `Stef_UI_L1.md` - UI documentation
- `Stef_UI_L2.md` - UI documentation

### All Subdirectory Core Files
- `orchestrator/*.py` (except patches)
- `cal/*.py` (except test files)
- `parserr/*.py` (main parsers)
- `c_sensitivity/*.py`
- `c_surrogate/*.py`
- `idf_modification/*.py`
- `validation/*.py`
- All main `.py` files in idf_objects subdirectories

## Deletion Commands

To delete all identified files, use these commands:

```bash
# Delete MD_prompt_explorings directory
rm -rf MD_prompt_explorings/

# Delete all __pycache__ directories
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Delete all .pyc files
find . -name "*.pyc" -delete

# Delete specific files
rm -f "main_modifi.py"
rm -f "orchestrator.py"
rm -f "combined copy.json"
rm -f "orchestrator/patch_calibration_parquet.py"
rm -f "parserr/parserr.rar"
rm -f "parserr/sql_enhanced_extractor.py"
rm -f "cal/main cal.py"
rm -f "cal/implementation_calibration_summary.md"
rm -f "cal/implementation_summary_Sensitivity_Analysis.md"
rm -f "cal/enhanced_config_examples_Calibration.json"
rm -f "idf_objects/ventilation/schedules copy.py"
rm -f "idf_objects/fenez/materials_lookup0.py"
rm -f "idf_objects/fenez/4.md"
rm -f "idf_objects/fenez/database_handler.cpython-39.pyc"
rm -f "idf_objects/HVAC/hvac_lookup2.py"
rm -f "idf_objects/HVAC/hvac_lookup3.py"
rm -f "idf_objects/DHW/dhw.tex"
rm -f "idf_objects/HVAC/hvac.tex"
rm -f "idf_objects/Elec/light.tex"
rm -f "idf_objects/ventilation/vent.tex"
rm -f "validation/smart_validation_wrapper.py.bak"
rm -f "validation/Archieve 2/example-validation-config.json"
rm -rf "validation/archieve/"
rm -f "c_sensitivity/advanced_config_example.json"
rm -f "c_surrogate/0 enhanced_config_examples_Surrogate.json"
rm -f "c_surrogate/0 ml_vs_automl_comparison.md"
rm -f "c_surrogate/0 surrogate_quick_reference.md"

# Remove empty directories
rmdir logs/ 2>/dev/null
rmdir user_configs/ 2>/dev/null
```

## Summary

- **Already deleted**: 127 files (mostly test scripts and documentation)
- **Additional to delete**: ~50 files plus entire MD_prompt_explorings directory
- **Python cache cleanup**: All `__pycache__` directories and `.pyc` files
- **Total space saved**: Significant, especially from removing compiled Python files

The cleanup will leave only the essential files needed for the E_Plus_2040_py workflow to function properly.