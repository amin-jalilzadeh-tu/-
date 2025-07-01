# Static SQL Data Extraction - Configuration

## Overview
The static SQL data extraction is now fully integrated into the existing parsing workflow. It extracts pre-calculated summaries, sizing data, and building characteristics from EnergyPlus SQL files.

## Configuration

### Enable/Disable Static Extraction
In your parsing configuration, you can control static extraction using the `parse_types` setting:

```json
{
  "parsing": {
    "parse_types": {
      "idf": true,
      "sql": true,
      "sql_static": true  // Set to false to disable static extraction
    }
  }
}
```

**Default:** Static extraction is enabled by default (`sql_static: true`)

## What Gets Extracted

When enabled, the following data is automatically extracted during SQL parsing:

### 1. Performance Summaries (`performance_summaries/`)
- Energy end uses by fuel type
- Site and source energy totals
- Comfort metrics and unmet hours
- Energy intensity (per floor area)
- Peak demands (when available)

### 2. Sizing Results (`sizing_results/`)
- Zone sizing (design loads, airflows)
- System sizing (capacities)
- Component sizing (equipment sizes)

### 3. Building Characteristics (`building_characteristics/`)
- Zone properties with window-wall ratios
- Construction layer details
- Equipment nominal loads (all types)
- Infiltration and ventilation rates

### 4. Metadata (`metadata/`)
- Simulation information
- Environment periods
- Errors and warnings

## Integration Details

### Code Changes Made:

1. **Moved `sql_static_extractor.py` to `parserr/` directory**
   - Now part of the parsing module

2. **Updated `sql_analyzer_main.py`**
   - Added import for SQLStaticExtractor
   - Added `extract_static_data` parameter
   - Integrated extraction after timeseries

3. **Updated `parsing_step.py`**
   - Added `sql_static` to default parse_types
   - Passes configuration to SQL analyzer
   - Works for both base and modified results

## File Locations

Static data is saved alongside existing parsed data:

```
parsed_data/
├── timeseries/                    # Existing timeseries
├── performance_summaries/         # NEW: Annual summaries
├── sizing_results/                # NEW: Design data
├── building_characteristics/      # NEW: Static properties
└── metadata/                      # Enhanced with new files

parsed_modified_results/
└── (same structure as above)
```

## Usage Examples

### Access Energy End Uses
```python
import pandas as pd

# Load end use data
end_uses = pd.read_parquet("parsed_data/performance_summaries/energy_end_uses.parquet")

# Filter for a specific building
building_data = end_uses[end_uses['building_id'] == '4136733']

# Get heating electricity use
heating_elec = building_data[building_data['RowName'] == 'Heating']['Electricity'].values[0]
```

### Access Zone Sizing
```python
# Load zone sizing data
zone_sizes = pd.read_parquet("parsed_data/sizing_results/zone_sizing.parquet")

# Get cooling design loads
cooling_loads = zone_sizes[zone_sizes['LoadType'] == 'Cooling'][['ZoneName', 'CalcDesLoad']]
```

### Access Building Properties
```python
# Load zone properties
zones = pd.read_parquet("parsed_data/building_characteristics/zone_properties.parquet")

# Calculate average window-wall ratio
avg_wwr = zones['window_wall_ratio'].mean()
```

## Performance Notes

- Static extraction adds ~2-5 seconds per SQL file
- Data is appended if files already exist (no duplicates)
- Extraction failures are logged but don't stop the main workflow
- Missing tables are handled gracefully

## Troubleshooting

If static extraction fails:
1. Check the log for specific error messages
2. Verify SQL file is valid and complete
3. Set `sql_static: false` to skip if needed
4. Static extraction failures don't affect timeseries extraction

The integration is designed to be transparent - existing workflows continue to work unchanged, with additional data available when needed.