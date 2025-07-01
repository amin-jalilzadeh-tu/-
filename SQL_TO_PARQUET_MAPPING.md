# SQL to Parquet Mapping Analysis

## Current Parquet Structure

### 1. **Timeseries Data** (`timeseries/`)
**Structure:** Wide format with dates as columns
- Columns: `building_id`, `variant_id`, `VariableName`, `category`, `Zone`, `Units`, then date columns
- Files: `base_all_daily.parquet`, `base_all_monthly.parquet`, etc.
- **Current SQL Source:** ReportData + ReportDataDictionary tables

### 2. **IDF Category Data** (`idf_data/by_category/`)
**Structure:** Long format with object properties
- Common columns: `building_id`, `object_type`, `object_name`, `zone_name`, + category-specific fields
- Files organized by category: `equipment.parquet`, `lighting.parquet`, `hvac_systems.parquet`, etc.
- **Current SQL Source:** Parsed from IDF files, not SQL

### 3. **Building Snapshots** (`idf_data/by_building/`)
**Structure:** Summary of all objects per building
- Columns: `building_id`, `category`, `output_file`, `object_type`, `object_name`, `parameters`, `zone_name`
- **Current SQL Source:** Parsed from IDF files, not SQL

### 4. **Metadata** (`metadata/`)
**Structure:** Registry and validation information
- `building_registry.parquet`: Building info and status
- `schedules.parquet`: Schedule definitions
- **Current SQL Source:** Schedules table (partial)

### 5. **Comparisons** (`comparisons/`)
**Structure:** Wide format comparing base vs variants
- Columns: `timestamp`, `building_id`, `Zone`, `variable_name`, `base_value`, `variant_X_value`...
- One file per variable per aggregation level
- **Current SQL Source:** Processed from timeseries data

## Mapping Unextracted SQL Data to Existing Structures

### Data That Fits Existing Structures

#### 1. **Additional Timeseries → `timeseries/` folder**
From **ReportExtendedData** table:
- Peak values with timestamps
- Min/max occurrences
- Can add new files: `peak_values_daily.parquet`, `peak_occurrences.parquet`

#### 2. **Equipment/Loads Data → `idf_data/by_category/` folder**
From SQL tables:
- **NominalElectricEquipment** → `equipment_electric_nominal.parquet`
- **NominalGasEquipment** → `equipment_gas_nominal.parquet`
- **NominalInfiltration** → `infiltration_nominal.parquet`
- **NominalVentilation** → `ventilation_nominal.parquet`

Structure matches existing category files with columns like:
- `building_id`, `object_name`, `zone_name`, `design_level`, `schedule_index`, etc.

#### 3. **Additional Metadata → `metadata/` folder**
- **Simulations** table → `simulation_info.parquet`
- **Errors** table → `simulation_errors.parquet`
- **EnvironmentPeriods** → `environment_periods.parquet`

## New Parquet Structures Needed

### 1. **Performance Summaries** (`performance_summaries/`)
For **TabularData** table content:

```
performance_summaries/
├── energy_end_uses.parquet
│   └── Columns: building_id, variant_id, end_use, fuel_type, annual_value, units
├── peak_demands.parquet
│   └── Columns: building_id, variant_id, end_use, peak_value, peak_datetime, units
├── comfort_metrics.parquet
│   └── Columns: building_id, variant_id, metric_name, value, units
├── energy_intensity.parquet
│   └── Columns: building_id, variant_id, metric, value, units
└── site_source_summary.parquet
    └── Columns: building_id, variant_id, energy_type, site_value, source_value, units
```

### 2. **Sizing Results** (`sizing_results/`)
For sizing-related tables:

```
sizing_results/
├── zone_sizing.parquet
│   └── From ZoneSizes: building_id, zone_name, load_type, design_load, design_flow, peak_conditions
├── system_sizing.parquet
│   └── From SystemSizes: building_id, system_name, load_type, design_capacity, design_flow
└── component_sizing.parquet
    └── From ComponentSizes: building_id, component_type, component_name, parameter, value, units
```

### 3. **Building Characteristics** (`building_characteristics/`)
Aggregated static properties:

```
building_characteristics/
├── envelope_summary.parquet
│   └── Columns: building_id, surface_type, orientation, area, u_value, construction
├── construction_details.parquet
│   └── From ConstructionLayers: building_id, construction_name, layer_order, material_name
├── zone_properties.parquet
│   └── Enhanced from Zones: building_id, zone_name, volume, area, ceiling_height, multiplier
└── internal_loads_summary.parquet
    └── Aggregated: building_id, zone_name, load_type, design_density, units
```

### 4. **Detailed Reports** (`detailed_reports/`)
For complex TabularData reports:

```
detailed_reports/
├── hvac_performance.parquet
│   └── Equipment efficiency, runtime, part-load data
├── envelope_performance.parquet
│   └── Surface heat transfer, window performance
├── outdoor_air_summary.parquet
│   └── Ventilation rates, outdoor air fractions
└── annual_summaries.parquet
    └── All other TabularData reports in normalized form
```

## Implementation Strategy

### Phase 1: Extend Existing Structures
1. Add nominal equipment/loads files to `idf_data/by_category/`
2. Add simulation metadata to `metadata/`
3. Add peak data to `timeseries/`

### Phase 2: Create New Summary Structures
1. Create `performance_summaries/` for TabularData extraction
2. Create `sizing_results/` for sizing tables
3. Create `building_characteristics/` for aggregated properties

### Phase 3: Advanced Extractions
1. Create `detailed_reports/` for complex analyses
2. Add cross-building comparison capabilities
3. Implement data validation between sources

## Benefits of This Structure

1. **Consistency**: Follows existing patterns where possible
2. **Discoverability**: Logical grouping by data type
3. **Performance**: Optimized column formats for each use case
4. **Flexibility**: Easy to add new categories as needed
5. **Integration**: Works with existing parsing workflows

## Example Code Structure

```python
# For performance summaries
def extract_to_performance_summaries(sql_path, output_dir):
    # Extract end uses
    end_uses_df = extract_end_uses_from_tabular(sql_path)
    end_uses_df.to_parquet(output_dir / 'performance_summaries' / 'energy_end_uses.parquet')
    
    # Extract comfort metrics
    comfort_df = extract_comfort_metrics_from_tabular(sql_path)
    comfort_df.to_parquet(output_dir / 'performance_summaries' / 'comfort_metrics.parquet')
    
    # etc...
```