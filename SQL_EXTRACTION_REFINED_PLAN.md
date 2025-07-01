# Refined SQL Data Extraction Plan - Base & Variant Workflow

## Understanding the Two-Stage Process

### Stage 1: Base Buildings
- Created from initial IDF generation
- Serve as reference baseline
- Used for:
  - Initial analysis without modifications
  - Baseline for variant comparisons
  - Identifying targets for modification (best/worst performers)

### Stage 2: Variant Buildings  
- Created by modifying base IDFs with targeted parameters
- Multiple variants per base building
- Used for:
  - Sensitivity analysis
  - Surrogate model training
  - Calibration studies
  - Performance optimization

## Refined Data Structure

```
parsed_data/                          # BASE BUILDINGS ONLY
├── timeseries/
│   ├── base_all_daily.parquet      # All base buildings timeseries
│   ├── base_all_monthly.parquet    
│   └── base_all_yearly.parquet     
├── building_characteristics/         # Static data (doesn't change with variants)
│   ├── geometry.parquet             # Floor areas, volumes, zone counts
│   ├── envelope.parquet            # Window areas, WWR, surface areas
│   ├── constructions.parquet       # U-values, materials, thermal mass
│   └── design_loads.parquet        # Occupancy, lighting, equipment densities
├── performance_analysis/            # Base performance metrics
│   ├── annual_summary.parquet      # Energy by end-use, peaks, costs
│   ├── comfort_metrics.parquet     # Unmet hours, thermal comfort
│   ├── equipment_sizing.parquet    # HVAC capacities, design loads
│   └── performance_ranking.parquet  # Identify best/worst performers
├── quality_control/
│   ├── simulation_errors.parquet   # Warnings, convergence issues
│   └── data_completeness.parquet   # Missing variables, data gaps
└── metadata/
    ├── parsing_summary.json
    ├── building_registry.parquet
    └── extraction_config.json

parsed_modified_results/              # VARIANT BUILDINGS
├── timeseries/
│   ├── variants_all_daily.parquet  # All variants timeseries
│   └── variants_all_monthly.parquet
├── comparisons/                     # Base vs Variant comparisons
│   ├── by_variable/                # Energy, comfort, etc.
│   │   └── var_{variable}_{freq}_b{building_id}.parquet
│   └── by_building/                # All changes for each building
│       └── building_{id}_all_variants.parquet
├── variant_performance/            # Variant-specific metrics
│   ├── annual_summary.parquet     # Same structure as base
│   ├── equipment_sizing.parquet   # How equipment changed
│   └── improvement_metrics.parquet # % improvements over base
├── sensitivity_analysis/           # Analysis-ready datasets
│   ├── parameter_impacts.parquet  # Parameter vs outcome relationships
│   ├── sensitivity_indices.parquet # Sensitivity metrics
│   └── optimization_targets.parquet # Best variants per metric
└── metadata/
    ├── modification_log.parquet   # What parameters were changed
    ├── variant_mapping.parquet    # Base → variant relationships
    └── analysis_summary.json
```

## Enhanced SQL Extraction Components

### 1. **Building Profiling (Base Only)**
Extract comprehensive building profile for targeting:
```python
building_profile = {
    # Performance indicators
    'eui_kwh_m2': total_energy / floor_area,
    'peak_w_m2': peak_demand / floor_area,
    'gas_intensity_kwh_m2': gas_consumption / floor_area,
    
    # Comfort indicators  
    'unmet_hours_percent': unmet_hours / 8760 * 100,
    'comfort_score': calculate_comfort_score(),
    
    # System efficiency
    'hvac_cop': cooling_delivered / cooling_energy,
    'heating_efficiency': heating_delivered / heating_energy,
    
    # Cost metrics
    'energy_cost_per_m2': total_cost / floor_area,
    'demand_charges': peak_demand * demand_rate,
    
    # Targeting score (for modification selection)
    'improvement_potential': calculate_improvement_potential()
}
```

### 2. **Variant Impact Analysis**
Track what changed and its impact:
```python
variant_impact = {
    # Parameter changes
    'modified_parameters': ['wall_insulation', 'window_uvalue'],
    'parameter_values': {'wall_insulation': 0.15, 'window_uvalue': 1.2},
    
    # Performance changes
    'energy_change_percent': (variant_energy - base_energy) / base_energy * 100,
    'peak_change_percent': (variant_peak - base_peak) / base_peak * 100,
    'comfort_change': variant_unmet - base_unmet,
    
    # Equipment impacts
    'cooling_capacity_change': variant_cooling - base_cooling,
    'heating_capacity_change': variant_heating - base_heating,
    
    # Cost impacts
    'annual_cost_savings': base_cost - variant_cost,
    'simple_payback': upgrade_cost / annual_savings
}
```

### 3. **Validation & Targeting Metrics**
Help identify which buildings/variants to focus on:
```python
targeting_metrics = {
    # For base buildings (which to modify)
    'high_energy_users': buildings.nlargest(10, 'eui_kwh_m2'),
    'poor_comfort': buildings[buildings['unmet_hours'] > 300],
    'oversized_systems': buildings[buildings['sizing_factor'] > 1.5],
    
    # For variants (which modifications work)
    'best_energy_savers': variants.nlargest(10, 'energy_savings'),
    'best_comfort_improvers': variants.nlargest(10, 'comfort_improvement'),
    'most_cost_effective': variants.nsmallest(10, 'payback_years'),
    
    # Validation flags
    'anomalies': identify_anomalous_results(),
    'failed_variants': variants[variants['has_errors'] == True]
}
```

## SQL Table Extraction Priority

### Phase 1: Essential for Analysis
1. **TabularData** - Annual summaries for quick metrics
2. **Zones** - Building geometry and areas
3. **ComponentSizes** - Equipment sizing
4. **Errors** - Quality control

### Phase 2: Enhanced Features
5. **Surfaces** - Detailed envelope analysis
6. **Constructions/Materials** - Thermal properties
7. **NominalPeople/Lighting** - Internal loads
8. **Schedules** - Operating patterns

### Phase 3: Advanced Analysis
9. **SystemSizes/ZoneSizes** - Detailed HVAC analysis
10. **Additional tables** - As needed for specific studies

## Integration with Existing Processes

### 1. **Sensitivity Analysis**
```python
# Use base + variant data
sensitivity_data = {
    'base_performance': base_annual_summary,
    'variant_performances': variant_annual_summary,
    'parameter_values': modification_log,
    'sensitivity_indices': calculate_sensitivity()
}
```

### 2. **Surrogate Modeling**
```python
# Combine static + performance data
surrogate_features = {
    **building_characteristics,  # Geometry, envelope
    **design_loads,              # Internal gains
    **equipment_sizing,          # System sizes
    'climate_zone': climate_data
}
surrogate_targets = {
    'annual_energy': annual_summary['total_kwh'],
    'peak_demand': annual_summary['peak_kw'],
    'unmet_hours': comfort_metrics['unmet_total']
}
```

### 3. **Calibration**
```python
# Compare simulated vs measured
calibration_data = {
    'simulated': base_timeseries,
    'measured': utility_data,
    'static_params': building_characteristics,
    'tunable_params': identify_calibration_parameters()
}
```

## Benefits of This Structure

1. **Clear Separation**: Base vs variant data is clearly separated
2. **Analysis-Ready**: Data organized by use case (sensitivity, surrogate, calibration)
3. **Performance Tracking**: Easy to see improvements from base to variants
4. **Targeting Support**: Identifies which buildings need modification
5. **Quality Control**: Tracks simulation quality and anomalies
6. **Scalable**: Works for single building or portfolio analysis

## Implementation Notes

1. **Extract Once, Use Many**: Building characteristics extracted once from base
2. **Incremental Updates**: Can add variants without re-processing base
3. **Comparison Focus**: Structure optimized for base vs variant comparisons
4. **Memory Efficient**: Parquet format with appropriate partitioning
5. **Metadata Rich**: Comprehensive tracking of what was extracted and why