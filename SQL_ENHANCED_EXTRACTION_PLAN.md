# Enhanced SQL Data Extraction Plan for E_Plus_2040

## Current State Analysis

### What We Currently Extract (Timeseries Only)
The system currently focuses on **timeseries data** extraction from SQL files:
- Energy meters (electricity, gas, cooling/heating)
- Weather data 
- Zone conditions (temperatures, humidity)
- Equipment performance
- Building envelope heat transfer
- HVAC operation
- Ventilation and infiltration

### What We Have But Don't Use
The `sql_table_extractor.py` module exists and can extract:
- **TabularData** - Pre-calculated annual summaries
- **ComponentSizes** - Equipment sizing information
- **Zones** - Building geometry data
- **Surfaces** - Envelope characteristics
- **Constructions/Materials** - Thermal properties
- **Schedules** - Operating patterns
- **Errors** - Simulation quality metrics
- **NominalPeople/Lighting** - Internal loads

### Gap: Integration
While extraction code exists, it's not integrated into the main parsing pipeline.

## Additional Valuable Data to Extract

### 1. **Building Characteristics (High Priority)**
Extract once per building (not per variant):
```python
building_characteristics = {
    # From Zones table
    'total_floor_area_m2': zones_df['Area'].sum(),
    'total_volume_m3': zones_df['Volume'].sum(), 
    'num_zones': len(zones_df),
    'avg_ceiling_height_m': zones_df['CeilingHeight'].mean(),
    
    # From Surfaces table
    'total_envelope_area_m2': surfaces_df[surfaces_df['ClassName'].isin(['Wall:Exterior', 'Roof'])]['Area'].sum(),
    'total_window_area_m2': surfaces_df[surfaces_df['ClassName'] == 'Window']['Area'].sum(),
    'window_wall_ratio': total_window_area / total_wall_area,
    
    # By orientation
    'window_area_north_m2': north_windows['Area'].sum(),
    'window_area_south_m2': south_windows['Area'].sum(),
    'window_area_east_m2': east_windows['Area'].sum(),
    'window_area_west_m2': west_windows['Area'].sum(),
    
    # From Constructions/Materials
    'avg_wall_uvalue': wall_constructions['Uvalue'].mean(),
    'avg_window_uvalue': window_constructions['Uvalue'].mean(),
    'thermal_mass_indicator': calculate_thermal_mass()
}
```

### 2. **Annual Performance Summaries (High Priority)**
Extract from TabularData for each building/variant:
```python
annual_summaries = {
    # Energy by end-use
    'annual_heating_kwh': extract_from_tabular('Heating', 'Electricity [kWh]'),
    'annual_cooling_kwh': extract_from_tabular('Cooling', 'Electricity [kWh]'),
    'annual_lighting_kwh': extract_from_tabular('Lighting', 'Electricity [kWh]'),
    'annual_equipment_kwh': extract_from_tabular('Equipment', 'Electricity [kWh]'),
    
    # Peak demands
    'peak_electricity_kw': extract_from_tabular('Peak Demand', 'Electricity [kW]'),
    'peak_gas_kw': extract_from_tabular('Peak Demand', 'Gas [kW]'),
    
    # Comfort metrics
    'unmet_heating_hours': extract_from_tabular('Time Not Comfortable', 'During Heating'),
    'unmet_cooling_hours': extract_from_tabular('Time Not Comfortable', 'During Cooling'),
    
    # Costs (if available)
    'annual_electricity_cost': extract_from_tabular('Electricity', 'Cost [$]'),
    'annual_gas_cost': extract_from_tabular('Gas', 'Cost [$]')
}
```

### 3. **Equipment Characteristics (High Priority)**
Extract from ComponentSizes for each building/variant:
```python
equipment_data = {
    # HVAC capacities
    'total_cooling_capacity_kw': cooling_equipment['Value'].sum() / 1000,
    'total_heating_capacity_kw': heating_equipment['Value'].sum() / 1000,
    
    # By equipment type
    'dx_cooling_capacity_kw': dx_coils['Value'].sum() / 1000,
    'boiler_capacity_kw': boilers['Value'].sum() / 1000,
    
    # Fan/pump sizing
    'total_fan_flow_m3s': fans['Value'].sum(),
    'total_pump_flow_m3s': pumps['Value'].sum(),
    
    # Zone loads
    'design_cooling_load_kw': zone_cooling_loads['Value'].sum() / 1000,
    'design_heating_load_kw': zone_heating_loads['Value'].sum() / 1000
}
```

### 4. **Internal Loads (Medium Priority)**
Extract from NominalPeople/Lighting/Equipment:
```python
internal_loads = {
    'occupancy_density_ppm2': total_people / total_floor_area,
    'lighting_power_density_wm2': total_lighting_power / total_floor_area,
    'equipment_power_density_wm2': total_equipment_power / total_floor_area,
    'total_internal_gains_wm2': (lighting_lpd + equipment_epd + people_gains_per_m2)
}
```

### 5. **Simulation Quality Metrics (Medium Priority)**
Extract from Errors table:
```python
quality_metrics = {
    'total_warnings': warnings_count,
    'total_severe_errors': severe_errors_count,
    'convergence_issues': convergence_error_count,
    'has_fatal_errors': fatal_count > 0,
    'simulation_quality_score': calculate_quality_score()
}
```

## Proposed Data Structure (Simplified)

Instead of many subfolders, organize by data type and access pattern:

```
parsed_data/
├── timeseries/                   # Existing structure (kept as-is)
│   ├── base_all_daily.parquet   
│   ├── base_all_monthly.parquet 
│   └── base_all_yearly.parquet  
├── comparisons/                  # Variant comparisons (kept as-is)
│   └── var_{variable}_{freq}_b{building_id}.parquet
├── building_static/              # NEW: Static building characteristics
│   ├── building_characteristics.parquet  # All buildings' geometry, envelope
│   ├── construction_properties.parquet   # Materials, U-values
│   └── internal_loads_design.parquet    # Design occupancy, lighting, equipment
├── performance_summaries/        # NEW: Annual summaries  
│   ├── base_annual_summary.parquet       # Base buildings' annual metrics
│   └── variant_annual_summary.parquet    # Variant buildings' annual metrics
├── equipment_sizing/             # NEW: Equipment data
│   ├── base_equipment_sizes.parquet      # Base buildings' equipment
│   └── variant_equipment_sizes.parquet   # Variant buildings' equipment
└── metadata/                     # Enhanced metadata
    ├── parsing_summary.json
    ├── building_registry.parquet 
    ├── simulation_quality.parquet        # NEW: Quality metrics
    └── extraction_manifest.json          # NEW: What was extracted

```

## Implementation Plan

### Phase 1: Integrate Existing Extractor
1. Add `SQLTableExtractor` to `sql_analyzer_main.py`
2. Call extraction methods after timeseries extraction
3. Store results in new structure

### Phase 2: Add Derived Metrics
1. Calculate window-to-wall ratios
2. Compute thermal mass indicators
3. Generate performance intensities (kWh/m²)

### Phase 3: Enhanced Features
1. Create feature engineering pipeline
2. Add validation against timeseries aggregates
3. Generate comparison metrics for variants

## Benefits

1. **Surrogate Model Features**: Rich building characteristics without processing IDF files
2. **Quick Validation**: Annual summaries validate timeseries aggregations
3. **Cost Analysis**: Equipment sizing enables cost estimation
4. **Performance Benchmarking**: Compare against standards using intensity metrics
5. **Quality Control**: Identify unreliable simulations from errors

## Example Usage

```python
# Load building characteristics
building_chars = pd.read_parquet('parsed_data/building_static/building_characteristics.parquet')

# Get specific building's annual performance
annual_perf = pd.read_parquet('parsed_data/performance_summaries/base_annual_summary.parquet')
building_energy = annual_perf[annual_perf['building_id'] == '4136733']

# Compare base vs variants
base_equip = pd.read_parquet('parsed_data/equipment_sizing/base_equipment_sizes.parquet')
variant_equip = pd.read_parquet('parsed_data/equipment_sizing/variant_equipment_sizes.parquet')

# Quality check
quality = pd.read_parquet('parsed_data/metadata/simulation_quality.parquet')
reliable_buildings = quality[quality['has_fatal_errors'] == False]['building_id']
```

## Next Steps

1. Modify `sql_analyzer_main.py` to integrate `SQLTableExtractor`
2. Update `sql_data_manager.py` to handle non-timeseries data storage
3. Create aggregation functions for derived metrics
4. Add extraction configuration to allow selective extraction
5. Update documentation with new data availability