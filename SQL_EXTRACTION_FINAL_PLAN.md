# SQL Data Extraction - Final Plan

## Correct Understanding

### Base Buildings (parsed_data/)
- **Primary simulation results** that users work with directly
- Contains both timeseries AND static data
- Used for:
  - Direct analysis and reporting
  - Energy modeling results
  - Building performance assessment
  - Input to other processes (when no modifications needed)
  - ALSO used as baseline for comparison

### Modified Buildings (parsed_modified_results/)
- Created by tweaking parameters from base buildings
- Used specifically for:
  - Sensitivity analysis
  - Surrogate model training
  - Calibration studies
  - Parameter optimization
  - Tracking what changes lead to what outcomes

## Final Data Structure

```
parsed_data/                          # BASE BUILDINGS - PRIMARY DATA
├── timeseries/                      # Existing timeseries structure
│   ├── base_all_daily.parquet     
│   ├── base_all_monthly.parquet    
│   └── base_all_yearly.parquet     
├── static/                          # NEW: All non-timeseries data
│   ├── building_geometry.parquet    # Areas, volumes, zones
│   ├── envelope_properties.parquet  # WWR, surfaces, orientations
│   ├── construction_materials.parquet # U-values, thermal properties
│   ├── internal_loads.parquet       # Occupancy, lighting, equipment
│   ├── annual_energy.parquet        # Annual consumption by end-use
│   ├── peak_demands.parquet         # Peak loads and demands
│   ├── equipment_sizing.parquet     # HVAC capacities
│   ├── comfort_metrics.parquet      # Unmet hours, thermal comfort
│   └── simulation_quality.parquet   # Errors, warnings, quality score
├── idf_data/                        # Existing IDF extracted data
├── metadata/                        # Existing metadata
└── analysis_ready/                  # Combined datasets for analysis
    ├── building_summary.parquet     # All static data joined
    └── energy_summary.parquet       # Annual energy + peaks

parsed_modified_results/              # VARIANT BUILDINGS - MODIFICATIONS
├── timeseries/                      # Variant timeseries
│   └── variants_all_daily.parquet  
├── static/                          # Same structure as base
│   ├── annual_energy.parquet        # But only changing metrics
│   ├── peak_demands.parquet         
│   ├── equipment_sizing.parquet     
│   └── comfort_metrics.parquet      
├── comparisons/                     # Direct comparisons to base
│   ├── by_variable/                
│   │   └── var_{variable}_{freq}_b{building_id}.parquet
│   └── summary/
│       ├── energy_impacts.parquet   # Energy changes vs base
│       ├── comfort_impacts.parquet  # Comfort changes vs base
│       └── sizing_impacts.parquet   # Equipment size changes
├── modifications/                   # What was changed
│   ├── parameter_log.parquet       # Parameters modified
│   ├── modification_mapping.json   # Base->variant relationships
│   └── sensitivity_matrix.parquet  # Parameter vs outcome matrix
└── metadata/
```

## What to Extract from SQL

### 1. **Static Data for ALL Buildings** (Base + Variants)
These don't change with modifications, so extract once from base:
- Building geometry (areas, volumes)
- Envelope properties (calculated once from base)
- Construction materials (unless specifically modified)
- Design internal loads (unless specifically modified)

### 2. **Performance Data for ALL Buildings** (Base + Variants)
These change with modifications, so extract for each:
- Annual energy by end-use
- Peak demands
- Equipment sizing (can change with modifications)
- Comfort metrics
- Simulation quality

### 3. **Comparison Data** (Variants Only)
Calculate differences from base:
- Energy savings/increases
- Comfort improvements/degradation
- Equipment size changes
- Cost impacts

## SQL Tables to Extract

### Priority 1 - Essential Data
```python
essential_extractions = {
    'TabularData': {
        'purpose': 'Annual summaries, end-use breakdown',
        'extract_for': 'all buildings',
        'tables': ['End Uses', 'Comfort Summary', 'Peak Demands']
    },
    'Zones': {
        'purpose': 'Building geometry',
        'extract_for': 'base only',
        'data': ['Area', 'Volume', 'CeilingHeight']
    },
    'ComponentSizes': {
        'purpose': 'Equipment capacities',
        'extract_for': 'all buildings',
        'data': ['Cooling/Heating capacity', 'Fan flows']
    },
    'Errors': {
        'purpose': 'Quality control',
        'extract_for': 'all buildings'
    }
}
```

### Priority 2 - Enhanced Features
```python
enhanced_extractions = {
    'Surfaces': {
        'purpose': 'Calculate WWR, envelope areas',
        'extract_for': 'base only'
    },
    'Constructions/Materials': {
        'purpose': 'Thermal properties',
        'extract_for': 'base only (unless modified)'
    },
    'NominalPeople/Lighting': {
        'purpose': 'Internal load densities',
        'extract_for': 'base only (unless modified)'
    }
}
```

## Integration Points

### 1. **For Direct Analysis** (using base data)
```python
# Load complete building data
geometry = pd.read_parquet('parsed_data/static/building_geometry.parquet')
annual_energy = pd.read_parquet('parsed_data/static/annual_energy.parquet')
timeseries = pd.read_parquet('parsed_data/timeseries/base_all_daily.parquet')

# Analyze building performance
eui = annual_energy['total_energy_kwh'] / geometry['total_floor_area_m2']
```

### 2. **For Sensitivity Analysis** (using base + variants)
```python
# Load base performance
base_energy = pd.read_parquet('parsed_data/static/annual_energy.parquet')

# Load variant performance  
variant_energy = pd.read_parquet('parsed_modified_results/static/annual_energy.parquet')

# Load modification log
mods = pd.read_parquet('parsed_modified_results/modifications/parameter_log.parquet')

# Analyze sensitivity
sensitivity = analyze_parameter_impacts(base_energy, variant_energy, mods)
```

### 3. **For Surrogate Modeling** (using all data)
```python
# Combine static features
features = pd.merge(
    pd.read_parquet('parsed_data/static/building_geometry.parquet'),
    pd.read_parquet('parsed_data/static/envelope_properties.parquet')
)

# Add modification parameters for variants
if is_variant:
    mods = pd.read_parquet('parsed_modified_results/modifications/parameter_log.parquet')
    features = pd.merge(features, mods)

# Target variables from performance
targets = pd.read_parquet('parsed_data/static/annual_energy.parquet')
```

## Key Benefits

1. **Base data is complete**: Users can analyze buildings without needing variants
2. **Clear separation**: Base vs modified data is organized but accessible
3. **Efficient storage**: Static data extracted once, not duplicated
4. **Modification tracking**: Clear record of what changed and impacts
5. **Analysis ready**: Data organized for common use cases

## Implementation Notes

1. **Extract static building characteristics only from base** (geometry, envelope)
2. **Extract performance metrics from all buildings** (energy, comfort, sizing)
3. **Calculate comparison metrics for variants** (vs their base building)
4. **Store efficiently**: Don't duplicate unchanging data
5. **Track relationships**: Maintain base->variant mappings