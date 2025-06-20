# EnergyPlus Validation System Usage Guide

## Overview

The updated validation system provides flexible, configuration-driven validation of EnergyPlus simulation results against measured data. Key improvements include:

- **Automatic unit conversion** - No more manual unit conversions
- **Variable name mapping** - Use your own naming conventions
- **Flexible data formats** - Support for CSV and Parquet, wide and long formats
- **Smart data alignment** - Handles different date formats and missing data
- **Zone aggregation** - Automatically aggregates zone-level data to building level
- **Enhanced error reporting** - Clear messages about what went wrong

## Quick Start

### 1. Prepare Your Real Data

Create a CSV or Parquet file following the format specification. The simplest format is:

```csv
BuildingID,VariableName,01/01,01/02,01/03,...,12/31
4136737,Total_Electricity_kWh,45.2,47.8,46.3,...,45.1
4136737,Heating_Energy_kWh,120.5,125.3,118.7,...,122.3
```

### 2. Create a Validation Configuration

Save this as `validation_config.json`:

```json
{
  "real_data": {
    "path": "measured_data.csv",
    "format": "auto"
  },
  "units": {
    "energy": "kWh"
  },
  "variable_mappings": {
    "Total_Electricity_kWh": "Electricity:Facility [J](Daily)",
    "Heating_Energy_kWh": "Heating:EnergyTransfer [J](Daily)"
  },
  "variables_to_compare": [
    "Electricity:Facility [J](Daily)",
    "Heating:EnergyTransfer [J](Daily)"
  ]
}
```

### 3. Run Validation

The validation will run automatically as part of the orchestrator workflow if enabled in `main_config.json`:

```json
{
  "validation": {
    "perform_validation": true,
    "use_parsed_data": true,
    "config": {
      "real_data": {
        "path": "measured_data.csv"
      }
    }
  }
}
```

## Common Issues and Solutions

### Issue 1: Unit Mismatch

**Symptom**: CVRMSE values > 1000%

**Solution**: Specify units in configuration:
```json
{
  "units": {
    "energy": "kWh",  // Your data is in kWh
    "power": "kW",    // Your data is in kW
    "temperature": "F" // Your data is in Fahrenheit
  }
}
```

### Issue 2: Variable Name Mismatch

**Symptom**: "No simulation data found for variables"

**Solution**: Add variable mappings:
```json
{
  "variable_mappings": {
    "Your_Variable_Name": "EnergyPlus:Variable:Name [J](Daily)"
  }
}
```

### Issue 3: Date Format Issues

**Symptom**: "No common dates found between datasets"

**Solution**: Specify date formats:
```json
{
  "real_data": {
    "date_parsing": {
      "formats": ["%m/%d/%Y", "%Y-%m-%d"]
    }
  }
}
```

### Issue 4: Building ID Mismatch

**Symptom**: "No real data for building X"

**Solution**: Add building mappings:
```json
{
  "building_mappings": {
    "RealBuildingID": ["SimBuildingID1", "SimBuildingID2"]
  }
}
```

## Advanced Features

### Variable-Specific Thresholds

Set different pass/fail criteria for different variables:

```json
{
  "thresholds": {
    "cvrmse": 30.0,  // Default
    "nmbe": 10.0,    // Default
    "by_variable": {
      "Zone Mean Air Temperature [C](Hourly)": {
        "cvrmse": 20.0,  // Stricter for temperature
        "nmbe": 5.0
      }
    }
  }
}
```

### Zone-Level Data

If your real data has zone-level detail:

```csv
BuildingID,Zone,VariableName,DateTime,Value
4136737,Zone1,Zone Air Temperature,2020-01-01,21.5
4136737,Zone2,Zone Air Temperature,2020-01-01,20.8
```

The system will automatically aggregate to building level based on the variable type.

### Time-Based Analysis

Enable advanced analyses:

```json
{
  "analysis_options": {
    "peak_analysis": {
      "perform": true,
      "n_peaks": 10
    },
    "seasonal_analysis": true,
    "weekday_weekend": true
  }
}
```

## Output Files

After validation, you'll find these files in `output/<job_id>/validation_results/`:

- `validation_summary.parquet` - Overall results for each building/variable
- `detailed_metrics.parquet` - Detailed metrics including seasonal breakdowns
- `failed_validations.parquet` - Details of failed validations
- `unit_conversion_warnings.parquet` - Potential unit issues detected
- `validation_metadata.json` - Configuration and summary statistics

## Best Practices

1. **Always specify units** - Even if you think they match
2. **Use consistent date formats** - Pick one format and stick to it
3. **Check the warnings** - Unit conversion warnings often indicate configuration issues
4. **Start simple** - Get basic validation working before enabling advanced features
5. **Document your data** - Include a README with your data explaining units and any processing

## Migration from Old System

If you have existing validation workflows:

1. **CSV files still work** - No need to change your data format
2. **Add units to config** - This is the most important change
3. **Map variable names** - If they don't match EnergyPlus exactly
4. **Check results** - Values should be much more reasonable with proper unit conversion

## Troubleshooting

Enable debug logging to see detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Common debug checks:
- Are units being converted? Look for "Converting X from Y to Z"
- Are dates parsing? Look for "Successfully parsed dates using format"
- Are variables mapping? Look for "Mapped variable names"

## Example: Complete Configuration

Here's a complete example for a building with electricity data in kWh and temperature in Fahrenheit:

```json
{
  "real_data": {
    "path": "building_measured_2020.csv",
    "format": "wide",
    "encoding": "utf-8",
    "id_column": "BuildingID",
    "date_parsing": {
      "formats": ["%m/%d", "%m/%d/%Y"],
      "output_format": "%m/%d"
    }
  },
  
  "units": {
    "energy": "kWh",
    "temperature": "F"
  },
  
  "variable_mappings": {
    "Total_Elec_Consumption": "Electricity:Facility [J](Daily)",
    "HVAC_Heating": "Heating:EnergyTransfer [J](Daily)",
    "HVAC_Cooling": "Cooling:EnergyTransfer [J](Daily)",
    "Indoor_Temp_Avg": "Zone Mean Air Temperature [C](Hourly)"
  },
  
  "building_mappings": {
    "BldgA": "4136737",
    "BldgB": "4136738"
  },
  
  "variables_to_compare": [
    "Electricity:Facility [J](Daily)",
    "Heating:EnergyTransfer [J](Daily)",
    "Cooling:EnergyTransfer [J](Daily)",
    "Zone Mean Air Temperature [C](Hourly)"
  ],
  
  "data_frequency": "daily",
  
  "thresholds": {
    "cvrmse": 25.0,
    "nmbe": 10.0
  },
  
  "aggregation": {
    "zones_to_building": true
  },
  
  "analysis_options": {
    "peak_analysis": {
      "perform": true,
      "n_peaks": 10
    }
  }
}