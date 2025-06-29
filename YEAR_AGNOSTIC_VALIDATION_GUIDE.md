# Year-Agnostic Validation Configuration Guide

## Problem
When simulation data and measured data are from different years (e.g., simulation from 2013-2014, measured data from 2020), the validation fails with "No overlapping dates" errors.

## Solution
Enable year-agnostic matching in your validation configuration. This feature matches dates by month-day only, ignoring the year.

## Configuration

### 1. For Single-Stage Validation

Add `year_agnostic_matching: true` to your validation config:

```json
{
  "validation": {
    "perform_validation": true,
    "config": {
      "real_data_path": "data/test_validation_data/measured_data_parsed_format_daily_4136733.csv",
      "year_agnostic_matching": true,  // <-- ADD THIS
      "variables_to_validate": ["Electricity", "Heating", "Cooling", "Temperature"],
      "aggregation": {
        "target_frequency": "monthly"
      },
      "thresholds": {
        "default": {
          "cvrmse": 30.0,
          "nmbe": 10.0
        }
      }
    }
  }
}
```

### 2. For Multi-Stage Validation (Baseline + Modified)

Add to each stage's configuration:

```json
{
  "validation": {
    "perform_validation": true,
    "stages": {
      "baseline": {
        "enabled": true,
        "run_after": "parsing",
        "config": {
          "real_data_path": "data/test_validation_data/measured_data_parsed_format_daily_4136733.csv",
          "year_agnostic_matching": true,  // <-- ADD THIS
          "variables_to_validate": ["Electricity", "Heating", "Cooling", "Temperature"],
          "aggregation": {
            "target_frequency": "monthly"
          }
        }
      },
      "modified": {
        "enabled": true,
        "run_after": "modification_parsing",
        "config": {
          "real_data_path": "data/test_validation_data/measured_data_parsed_format_daily_4136733.csv",
          "year_agnostic_matching": true,  // <-- ADD THIS
          "variables_to_validate": ["Electricity", "Heating", "Cooling", "Temperature"],
          "validate_variants": true
        }
      }
    }
  }
}
```

## How It Works

When `year_agnostic_matching` is enabled:

1. **Normal Matching**: `2013-01-15` only matches with `2013-01-15`
2. **Year-Agnostic**: `2013-01-15` matches with `2020-01-15` (same month-day)

The validation creates a "MatchKey" using only month-day (MM-DD) format for alignment.

## Example Usage

### In main_config.json:
```json
{
  "job_id": "your-job-id",
  "building_id": "4136733",
  "validation": {
    "perform_validation": true,
    "config": {
      "real_data_path": "data/measured_data.csv",
      "year_agnostic_matching": true,
      "aggregation": {
        "target_frequency": "monthly"
      }
    }
  }
}
```

### Direct API Call:
```python
from validation.smart_validation_wrapper import run_smart_validation

results = run_smart_validation(
    parsed_data_path="output/job_id/parsed_data",
    real_data_path="data/measured_data.csv",
    config={
        "year_agnostic_matching": True,
        "target_frequency": "monthly",
        "variables_to_validate": ["Electricity", "Heating", "Cooling"]
    },
    output_path="output/job_id/validation_results"
)
```

## Important Notes

1. **Data Coverage**: Ensure your measured data covers the same months as your simulation data
2. **Seasonal Patterns**: Year-agnostic matching assumes similar weather patterns across years
3. **Validation Accuracy**: Results may be less accurate if weather conditions differ significantly between years

## Troubleshooting

If you still see "No overlapping dates" errors after enabling year-agnostic matching:

1. Check that measured and simulated data have matching months (e.g., both have January data)
2. Verify date formats are correctly parsed
3. Ensure the configuration is properly nested in your JSON file
4. Check logs for "year_agnostic_matching" confirmation

## Files Modified to Support This Feature

- `/mnt/d/Documents/daily/E_Plus_2040_py/validation/smart_validation_wrapper.py`
  - Added year-agnostic matching logic (lines 1406-1421)
  - Added config parameter (line 51)
- `/mnt/d/Documents/daily/E_Plus_2040_py/parserr/aggregation_utils.py`
  - Fixed date pattern detection (line 206)