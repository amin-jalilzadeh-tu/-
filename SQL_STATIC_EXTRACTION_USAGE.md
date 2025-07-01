# SQL Static Data Extraction - Usage Guide

## Overview
The new static data extraction complements your existing timeseries extraction by extracting all the pre-calculated summaries and static data from EnergyPlus SQL files.

## What's New

### New Data Categories Extracted:
1. **Performance Summaries** (`performance_summaries/`)
   - `energy_end_uses.parquet` - Annual energy by end use
   - `site_source_summary.parquet` - Site vs source energy totals
   - `comfort_metrics.parquet` - Unmet hours and comfort violations
   - `energy_intensity.parquet` - Energy per floor area metrics
   - `peak_demands.parquet` - Peak power demands

2. **Sizing Results** (`sizing_results/`)
   - `zone_sizing.parquet` - Zone design loads and airflows
   - `system_sizing.parquet` - System capacities
   - `component_sizing.parquet` - Equipment design sizes

3. **Building Characteristics** (`building_characteristics/`)
   - `zone_properties.parquet` - Enhanced zone data with WWR
   - `construction_details.parquet` - Layer-by-layer construction
   - `equipment_*_nominal.parquet` - All equipment types
   - `infiltration_nominal.parquet` - Design infiltration
   - `ventilation_nominal.parquet` - Design ventilation

4. **Metadata** (`metadata/`)
   - `simulation_info.parquet` - EnergyPlus version, settings
   - `environment_periods.parquet` - Simulation periods
   - `simulation_errors.parquet` - Warnings and errors

## Integration Options

### Option 1: Standalone Extraction
```python
from sql_static_extractor import extract_static_data_for_building

# Extract for a single building
extract_static_data_for_building(
    sql_path="path/to/simulation.sql",
    output_dir="path/to/parsed_data",
    building_id="4136733",
    variant_id="base"  # or "variant_0", "variant_1", etc.
)
```

### Option 2: Batch Extraction
```python
from integrate_static_extraction import extract_static_data_for_all_buildings

# Extract for all buildings in a project
results = extract_static_data_for_all_buildings(
    base_dir="/path/to/E_Plus_2040_py",
    user_config_id="your-config-id",
    year="2020",
    max_workers=4
)
```

### Option 3: Integration with Existing Workflow
Add to your existing SQL parsing code:

```python
# In your existing parse_sql.py or similar
from sql_static_extractor import SQLStaticExtractor

# After your timeseries extraction
sql_analyzer = EnhancedSQLAnalyzer(sql_path, data_manager)
timeseries_data = sql_analyzer.extract_timeseries()

# Add static extraction
static_extractor = SQLStaticExtractor(
    sql_path,
    output_dir,
    building_id,
    variant_id
)
static_extractor.extract_all()
static_extractor.close()
```

## Minimal Code Change Required

The simplest integration requires adding just 5 lines to your existing workflow:

```python
# Your existing code remains unchanged
# Just add after timeseries extraction:
from sql_static_extractor import SQLStaticExtractor

static = SQLStaticExtractor(sql_path, output_dir, building_id, variant_id)
static.extract_all()
static.close()
```

## Output Structure
```
parsed_data/
├── timeseries/                    # Existing (unchanged)
├── idf_data/                      # Existing (unchanged)
├── metadata/                      # Existing + new files
├── performance_summaries/         # NEW
├── sizing_results/                # NEW
├── building_characteristics/      # NEW
└── detailed_reports/              # NEW (future use)
```

## Key Benefits
1. **No changes to existing code** - Just additions
2. **Pre-calculated summaries** - No need to aggregate timeseries
3. **Validation data** - Annual totals to verify timeseries
4. **Complete building profile** - All static properties in one place
5. **Calibration ready** - More parameters for calibration targets

## Example: Accessing the New Data
```python
import pandas as pd

# Get annual energy by end use
end_uses = pd.read_parquet("parsed_data/performance_summaries/energy_end_uses.parquet")
heating_energy = end_uses[end_uses['RowName'] == 'Heating']['Electricity'].values[0]

# Get zone design loads
zone_sizes = pd.read_parquet("parsed_data/sizing_results/zone_sizing.parquet")
peak_cooling_loads = zone_sizes[zone_sizes['LoadType'] == 'Cooling']['CalcDesLoad']

# Get window-wall ratios
zone_props = pd.read_parquet("parsed_data/building_characteristics/zone_properties.parquet")
avg_wwr = zone_props['window_wall_ratio'].mean()
```

## Notes
- The extractor handles missing tables gracefully
- Existing files are updated (not overwritten) when re-running
- All data includes building_id and variant_id for easy filtering
- Compatible with both base and modified simulation results