# Smart Validation System Guide

## Table of Contents
1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Getting Started](#getting-started)
4. [Data Format Requirements](#data-format-requirements)
5. [Configuration Options](#configuration-options)
6. [How It Works](#how-it-works)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)
9. [Migration from Old System](#migration-from-old-system)

---

## Overview

The Smart Validation System is an intelligent, configuration-driven validation framework for EnergyPlus simulations. It automatically handles:

- **Variable mapping** - Fuzzy/semantic matching between real and simulated variables
- **Unit conversion** - Automatic conversion between different unit systems
- **Date parsing** - Flexible handling of various date formats
- **Zone aggregation** - Automatic aggregation from zone to building level
- **Frequency alignment** - Automatic alignment of different time frequencies

### Philosophy

> **"The validation system should adapt to your data, not the other way around."**

Instead of forcing you to format your data in specific ways, the smart validation system intelligently understands and processes various data formats, units, and structures.

---

## Key Features

### 🚀 Automatic Everything
- **Zero configuration required** - Works with just a data file path
- **Intelligent variable matching** - Uses semantic understanding to map variables
- **Smart unit detection** - Detects and converts units automatically
- **Flexible date parsing** - Handles any reasonable date format

### 📊 Comprehensive Validation
- **Multiple metrics** - CVRMSE, NMBE, MBE, R²
- **Configurable thresholds** - Global and per-variable thresholds
- **Multi-building support** - Validate multiple buildings in one run
- **Partial validation** - Continues even if some variables are missing

### 🔍 Transparent Process
- **Detailed logging** - See exactly what decisions were made
- **Progress tracking** - Know which step is running
- **Clear error messages** - Understand what went wrong
- **Recommendations** - Get suggestions for improvements

### 📈 Flexible Data Handling
- **Any frequency** - Hourly, daily, monthly data
- **Any structure** - Long format, wide format, with or without zones
- **Any units** - kWh, J, MJ, °C, °F, etc.
- **Missing data** - Handles gaps and NaN values gracefully

---

## Getting Started

### Installation

1. **Copy the required files** to your validation directory:
   ```
   validation/
   ├── smart_validation_wrapper.py    # Main validation logic
   ├── validation_config_simple.py    # Configuration helper
   └── metrics.py                     # Metric calculations
   ```

2. **Update your orchestrator.py** with the new validation section (see [Migration](#migration-from-old-system))

3. **Create measured data** in CSV format (see [Data Format Requirements](#data-format-requirements))

4. **Run validation** with minimal configuration:
   ```json
   {
     "validation": {
       "perform_validation": true,
       "config": {
         "real_data_path": "measured_data.csv"
       }
     }
   }
   ```

### Quick Example

**Step 1: Create measured data** (`measured_data.csv`):
```csv
building_id,DateTime,Variable,Value,Units
4136737,2013-01-01,Total Electricity,45000,kWh
4136737,2013-01-01,Heating Energy,120000,kWh
4136737,2013-01-01,Indoor Temperature,21.5,C
```

**Step 2: Add to configuration** (`combined.json`):
```json
{
  "main_config": {
    "validation": {
      "perform_validation": true,
      "config": {
        "real_data_path": "measured_data.csv"
      }
    }
  }
}
```

**Step 3: Run the workflow** - The validation will automatically:
- Find matching simulation variables
- Convert units if needed
- Calculate validation metrics
- Generate reports

---

## Data Format Requirements

### Minimum Required Columns

Your measured data must have these columns (case-insensitive):

| Column | Description | Example |
|--------|-------------|---------|
| `building_id` | Building identifier | 4136737 |
| `DateTime` | Date/time of measurement | 2013-01-01 |
| `Variable` | What was measured | Total Electricity |
| `Value` | Measured value | 45000 |
| `Units` | Units of measurement | kWh |

### Optional Columns

| Column | Description | When to Use |
|--------|-------------|-------------|
| `Zone` | Zone identifier | For zone-level data |
| `Quality` | Data quality flag | To mark questionable data |

### Supported Date Formats

The system automatically detects these formats:
- `2013-01-01` (YYYY-MM-DD)
- `2013-01-01 14:00:00` (YYYY-MM-DD HH:MM:SS)
- `01/31/2013` (MM/DD/YYYY)
- `31/01/2013` (DD/MM/YYYY)
- `2013/01/31` (YYYY/MM/DD)
- And many more...

### Supported Units

**Energy:**
- kWh, MWh, J, kJ, MJ, GJ, BTU, MMBTU, therm

**Power:**
- W, kW, MW, hp, BTU/h

**Temperature:**
- °C, °F, K, °R

### Data Structure Options

#### Option 1: Simple Daily Data
```csv
building_id,DateTime,Variable,Value,Units
4136737,2013-01-01,Total Electricity,45000,kWh
4136737,2013-01-02,Total Electricity,47000,kWh
```

#### Option 2: Hourly with Zones
```csv
building_id,DateTime,Variable,Zone,Value,Units
4136737,2013-01-01 01:00:00,Zone Temperature,Zone1,21.5,C
4136737,2013-01-01 01:00:00,Zone Temperature,Zone2,22.0,C
```

#### Option 3: Mixed Units and Formats
```csv
building_id,DateTime,Variable,Value,Units
4136737,01/01/2013,Electricity,45000,kWh
4136737,2013-01-01,Heating,432000000,J
4136737,2013/01/01,Indoor Temp,70,F
```

---

## Configuration Options

### Minimal Configuration

```json
{
  "validation": {
    "perform_validation": true,
    "config": {
      "real_data_path": "measured_data.csv"
    }
  }
}
```

### Full Configuration Options

```json
{
  "validation": {
    "perform_validation": true,
    "config": {
      "real_data_path": "path/to/measured_data.csv",
      
      "variables_to_validate": [
        "Electricity",      // Partial names work
        "Heating Energy",   // Will match variations
        "Cooling",         
        "Temperature"
      ],
      
      "aggregation": {
        "target_frequency": "daily",  // "hourly", "daily", "monthly"
        "methods": {
          "energy": "sum",
          "temperature": "mean",
          "power": "mean"
        }
      },
      
      "thresholds": {
        "default": {
          "cvrmse": 30.0,
          "nmbe": 10.0
        },
        "by_variable": {
          "Temperature": {  // Matches any temperature variable
            "cvrmse": 20.0,
            "nmbe": 5.0
          }
        }
      },
      
      "logging": {
        "level": "INFO",  // "DEBUG" for more details
        "show_mappings": true,
        "show_aggregations": true,
        "show_unit_conversions": true
      }
    }
  }
}
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `real_data_path` | string | Required | Path to measured data file |
| `variables_to_validate` | array | [] (all) | Filter variables to validate |
| `aggregation.target_frequency` | string | "daily" | Target time frequency |
| `aggregation.methods` | object | See above | How to aggregate each variable type |
| `thresholds.default.cvrmse` | number | 30.0 | Default CVRMSE threshold (%) |
| `thresholds.default.nmbe` | number | 10.0 | Default NMBE threshold (%) |
| `thresholds.by_variable` | object | {} | Variable-specific thresholds |
| `logging.level` | string | "INFO" | Logging detail level |
| `logging.show_mappings` | boolean | true | Show variable mapping details |
| `logging.show_aggregations` | boolean | true | Show aggregation details |
| `logging.show_unit_conversions` | boolean | true | Show unit conversion details |

---

## How It Works

### Step-by-Step Process

#### Step 1: Discovery
The system first discovers what data the parser produced:

```
Step 1/6: Discovering available simulation data...
  - Found hvac_2013: 701,895 hourly records, 28 variables
  - Found zones_daily: 6,935 daily records, 7 variables
  
  Available simulation variables:
    * Zone Air System Sensible Heating Energy
    * Zone Air System Sensible Cooling Energy
    * Zone Mean Air Temperature
    ... and 25 more
```

#### Step 2: Load Real Data
Loads and parses your measured data:

```
Step 2/6: Loading real/measured data...
  - Reading from: measured_data.csv
  - Loaded 1,095 rows
  - Successfully parsed dates with format: %Y-%m-%d
  - Found 2 buildings: [4136737, 4136738]
  - Found 4 variables: [Total Electricity, Heating Energy, Cooling Energy, Indoor Temperature]
  - Date range: 2013-01-01 to 2013-12-31
```

#### Step 3: Load Simulation Data
Loads appropriate simulation data based on target frequency:

```
Step 3/6: Loading simulation data...
  - Target frequency: daily
  - Loading hvac_daily (1,095 records)
  - Total simulation records loaded: 1,095
```

#### Step 4: Frequency Alignment
Aligns data to the same time frequency:

```
Step 4/6: Aligning data frequencies...
  - Real data frequency: daily
  - Sim data frequency: hourly
  - Target frequency: daily
  - Aggregating hourly simulation data to daily...
    * Zone Air System Sensible Heating Energy: 8,760 hourly → daily (sum)
    * Zone Mean Air Temperature: 8,760 hourly → daily (mean)
```

#### Step 5: Variable Mapping
Creates intelligent mappings between variables:

```
Step 5/6: Creating variable mappings...
  Real variables to map:
    - Total Electricity
    - Heating Energy
    - Indoor Temperature
    
  ✓ Exact match: Heating Energy
  ≈ Semantic match: Indoor Temperature → Zone Mean Air Temperature (confidence: 0.85)
  ✗ Could not map: Total Electricity (no facility-level electricity data)
  
  Mapping summary: 2 successful mappings
```

#### Step 6: Validation
Validates each mapped variable:

```
Step 6/6: Validating data...

  Validating: Heating Energy ↔ Zone Air System Sensible Heating Energy
  Converting Heating Energy: J → kWh
  Aggregating 5 zones for building 4136737
    - Method: sum
    - Zones: [Zone1, Zone2, Zone3, Zone4, Zone5]
    
    - Building 4136737: PASS
      CVRMSE: 12.3% (threshold: 30.0%)
      NMBE: -2.1% (threshold: ±10.0%)
```

### Variable Matching Algorithm

The system uses a three-tier approach:

1. **Exact Match** - Checks if variable names match exactly
2. **Semantic Match** - Uses patterns and keywords to find related variables
3. **Fuzzy Match** - Falls back to string similarity if needed

Example semantic patterns:
```python
'electricity': ['electricity.*facility', 'total.*electric', 'power']
'heating': ['heating.*energy', 'sensible.*heating', 'water.*heater']
'cooling': ['cooling.*energy', 'sensible.*cooling']
'temperature': ['zone.*temperature', 'indoor.*temp', 'mean.*temp']
```

### Unit Conversion

Automatic conversion between common units:

| From | To | Method |
|------|----|--------|
| kWh | J | × 3,600,000 |
| MJ | J | × 1,000,000 |
| °F | °C | (F - 32) × 5/9 |
| kW | W | × 1,000 |

### Zone Aggregation

When simulation has zone-level data but measured data is building-level:

| Variable Type | Aggregation Method |
|---------------|-------------------|
| Energy | Sum all zones |
| Temperature | Mean of all zones |
| Power | Sum for total, mean for density |

---

## Examples

### Example 1: Basic Validation

**Configuration:**
```json
{
  "validation": {
    "perform_validation": true,
    "config": {
      "real_data_path": "measured_data.csv"
    }
  }
}
```

**Output:**
```
SMART VALIDATION SUMMARY
========================================
Mappings created: 4
  - Exact matches: 1
  - Semantic matches: 3
  - Fuzzy matches: 0

Validations performed: 8
Validations passed: 6
Pass rate: 75.0%

Buildings validated: 2
Variables validated: 4
```

### Example 2: Debug Mode

**Configuration:**
```json
{
  "validation": {
    "perform_validation": true,
    "config": {
      "real_data_path": "measured_data.csv",
      "variables_to_validate": ["Heating"],
      "logging": {
        "level": "DEBUG",
        "show_mappings": true,
        "show_aggregations": true,
        "show_unit_conversions": true
      }
    }
  }
}
```

**Output includes detailed debugging:**
```
[DEBUG] Parsing datetime values...
[DEBUG] Trying format: %Y-%m-%d %H:%M:%S
[DEBUG] Trying format: %Y-%m-%d
[DEBUG] Successfully parsed with format: %Y-%m-%d
[DEBUG] Checking semantic match for 'heating energy'
[DEBUG] Pattern match: heating.*energy → True
[DEBUG] Confidence calculation: jaccard=0.75, key_score=0.60
[DEBUG] Final confidence: 0.69
```

### Example 3: Custom Thresholds

**Configuration:**
```json
{
  "validation": {
    "perform_validation": true,
    "config": {
      "real_data_path": "measured_data.csv",
      "thresholds": {
        "default": {
          "cvrmse": 25.0,
          "nmbe": 8.0
        },
        "by_variable": {
          "Temperature": {
            "cvrmse": 15.0,
            "nmbe": 3.0
          }
        }
      }
    }
  }
}
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: "No simulation data found!"

**Cause:** Parser didn't produce expected output files

**Solution:** 
1. Check if parsing was enabled in configuration
2. Verify simulation completed successfully
3. Check `parsed_data/sql_results/timeseries/` directory

#### Issue: "No common dates found between datasets"

**Cause:** Date ranges don't overlap

**Solution:**
1. Check date ranges in both datasets
2. Ensure year is correct (not default 2013)
3. Verify date parsing worked correctly

#### Issue: High CVRMSE values (>1000%)

**Cause:** Unit mismatch not detected

**Solution:**
1. Check unit columns in both datasets
2. Explicitly specify units in measured data
3. Look for unit conversion warnings in log

#### Issue: "Could not map X variables"

**Cause:** Variable names too different

**Solution:**
1. Use more standard variable names
2. Add specific variables to `variables_to_validate`
3. Check available simulation variables in log

### Debug Mode

Enable debug mode for detailed troubleshooting:

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

This shows:
- All date parsing attempts
- Variable matching confidence scores
- Detailed aggregation steps
- Unit conversion calculations

---

## Migration from Old System

### Files to Delete

Remove these files from your `validation/` directory:
- ❌ `enhanced_validation.py`
- ❌ `validation_data_loader.py`
- ❌ `data_alignment.py`
- ❌ `compare_sims_with_measured.py`
- ❌ `validate_results_custom.py`
- ❌ `main_validation.py`
- ❌ `validation_config.py`
- ❌ All complex JSON configuration files

### Files to Keep

Keep only:
- ✅ `smart_validation_wrapper.py` (new)
- ✅ `validation_config_simple.py` (new)
- ✅ `metrics.py` (existing)
- ✅ `visualize.py` (optional)

### Update Orchestrator

Replace the entire validation section (around line 650-900) with:

```python
# Smart Validation
check_canceled()
validation_cfg = main_config.get("validation", {})

if validation_cfg.get("perform_validation", False):
    with step_timer(logger, "validation"):
        logger.info("[INFO] Running smart validation...")
        
        val_config = validation_cfg.get("config", {})
        real_data_path = val_config.get("real_data_path", "measured_data.csv")
        
        if not os.path.isabs(real_data_path):
            real_data_path = patch_if_relative(real_data_path)
        
        if not os.path.isfile(real_data_path):
            logger.error(f"[ERROR] Real data file not found: {real_data_path}")
        else:
            try:
                from smart_validation_wrapper import run_smart_validation
                
                results = run_smart_validation(
                    parsed_data_path=os.path.join(job_output_dir, "parsed_data"),
                    real_data_path=real_data_path,
                    config=val_config,
                    output_path=os.path.join(job_output_dir, "validation_results")
                )
                
                if results and 'summary' in results:
                    summary = results['summary']
                    logger.info(f"[INFO] Validation complete:")
                    logger.info(f"  - Pass rate: {summary.get('pass_rate', 0):.1f}%")
                    
            except Exception as e:
                logger.error(f"[ERROR] Smart validation failed: {str(e)}")
```

### Update Configuration

Old configuration:
```json
{
  "validation": {
    "perform_validation": true,
    "config": {
      "real_data_csv": "data/measured.csv",
      "sim_data_csv": "results/simulated.csv",
      "bldg_ranges": {"0": [0, 1, 2]},
      "variables_to_compare": [...],
      "threshold_cv_rmse": 30.0,
      ...
    }
  }
}
```

New configuration:
```json
{
  "validation": {
    "perform_validation": true,
    "config": {
      "real_data_path": "data/measured.csv"
    }
  }
}
```

---

## Best Practices

### 1. Data Quality
- **Include units** in your measured data
- **Use consistent date formats** within a file
- **Remove outliers** before validation
- **Document data sources** in comments

### 2. Variable Naming
- **Use descriptive names** like "Total Electricity" not "Elec"
- **Be consistent** across time periods
- **Include units in names** when possible: "Heating Energy (kWh)"

### 3. Configuration
- **Start simple** - Use minimal configuration first
- **Add complexity gradually** - Only add options you need
- **Use debug mode** when troubleshooting
- **Save working configs** as templates

### 4. Interpretation
- **CVRMSE < 30%** - Generally acceptable for monthly data
- **NMBE < ±10%** - Indicates low systematic bias
- **Check both metrics** - Good CVRMSE with bad NMBE indicates bias
- **Consider context** - Hourly data typically has higher CVRMSE

---

## Advanced Topics

### Custom Variable Patterns

Add new patterns for specialized variables:

```python
# In smart_validation_wrapper.py
self.variable_patterns['custom'] = {
    'patterns': [
        r'custom.*pattern',
        r'special.*variable'
    ],
    'keywords': ['custom', 'special']
}
```

### Custom Unit Conversions

Add new unit conversions:

```python
# In smart_validation_wrapper.py
self.unit_conversions[('custom_unit', 'J')] = 12345.67
self.unit_conversions[('°Custom', '°C')] = lambda x: (x - 100) * 0.5
```

### Integration with Calibration

The validation results are automatically saved for use in calibration:

```python
# Results saved to:
job_output_dir/validation_results/
├── validation_results.csv         # Detailed results
├── validation_results.parquet     # For use by calibration
├── variable_mappings.csv          # How variables were mapped
└── validation_summary.json        # Complete summary
```

---

## Appendix

### Output Files

| File | Description | Use Case |
|------|-------------|----------|
| `validation_results.csv` | Detailed validation metrics | Analysis, reporting |
| `validation_results.parquet` | Same data in Parquet format | Integration with other tools |
| `variable_mappings.csv` | How variables were mapped | Debugging, documentation |
| `validation_summary.json` | Complete results with metadata | Programmatic access |

### Metrics Explained

**CVRMSE (Coefficient of Variation of RMSE)**
- Measures prediction accuracy
- Lower is better
- Formula: `CVRMSE = (RMSE / mean(observed)) × 100%`

**NMBE (Normalized Mean Bias Error)**
- Measures systematic bias
- Should be close to 0
- Formula: `NMBE = (sum(predicted - observed) / (n × mean(observed))) × 100%`

**MBE (Mean Bias Error)**
- Raw bias measurement
- Positive = over-prediction
- Formula: `MBE = (sum(predicted - observed) / sum(observed)) × 100%`

### Support

For issues or questions:
1. Check the troubleshooting section
2. Enable debug logging
3. Review the example configurations
4. Check that your data format matches requirements

---

*Last updated: 2024*