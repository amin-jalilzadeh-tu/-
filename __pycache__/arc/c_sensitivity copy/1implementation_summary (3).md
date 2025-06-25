# Multi-Level Sensitivity Analysis Implementation Summary

## What Was Implemented

### 1. **Core Components**

#### A. **RelationshipManager** (`relationship_manager.py`)
- Loads and manages zone mappings and equipment assignments
- Detects modification scope (building/zone/equipment)
- Provides zone weights for aggregation
- Creates modification hierarchy

#### B. **EnhancedModificationSensitivityAnalyzer** (`enhanced_modification_sensitivity_analyzer.py`)
- Extends base analyzer with multi-level capabilities
- Calculates zone-level and building-level deltas
- Performs four types of sensitivity analysis:
  - Zone-to-Zone
  - Zone-to-Building
  - Equipment-to-Zone
  - Building-to-Building

#### C. **Updated Sensitivity Step** (`sensitivity_step.py`)
- Routes between standard and multi-level analysis
- Handles zone data aggregation
- Generates multi-level visualizations
- Exports for surrogate/calibration

### 2. **Key Features**

#### Automatic Scope Detection
```python
# Automatically determines if a modification affects:
- Building level: "ALL_ZONES" or building-wide parameters
- Zone level: Specific zone names in object
- Equipment level: Equipment names from assignments
```

#### Smart Aggregation
```python
# Energy variables: Sum across zones
building_heating = sum(zone_heating for all zones)

# Temperature variables: Weighted average
building_temp = weighted_avg(zone_temps, weights=zone_volumes)
```

#### Multi-Level Relationships
```
Equipment → Zone → Building
   ↓         ↓        ↓
Local    Regional  Global
Impact    Impact   Impact
```

### 3. **Data Requirements**

The system uses your existing data structure:
- `relationships/zone_mappings.parquet` - IDF to SQL zone names
- `relationships/equipment_assignments.parquet` - Equipment to zone mapping
- `sql_results/timeseries/aggregated/daily/*_daily.parquet` - Zone-level results
- `modifications_detail_*.parquet` - What changed

### 4. **Configuration**

Enable with one flag:
```json
{
  "sensitivity": {
    "analysis_type": "modification_based",
    "modification_analysis": {
      "multi_level_analysis": true
    }
  }
}
```

### 5. **Outputs**

#### Reports
- `multi_level_sensitivity_report.json` - Comprehensive analysis
- `sensitivity_by_level_and_category.csv` - Summary statistics
- `multi_level_sensitivity_detailed.parquet` - All relationships

#### Visualizations
- Sensitivity by analysis level
- Zone impact heatmap
- Cross-level relationships
- Top parameters by level

#### Export Files
- `surrogate_parameters_multilevel.csv` - For surrogate modeling
- `calibration_parameters_multilevel.csv` - For calibration
- `zone_calibration_parameters.csv` - Zone-specific calibration

## How It Works

### 1. **Modification Loading**
```python
# Load modifications and detect scope
modifications = analyzer.load_modification_tracking_with_scope()
# Each modification now has:
# - scope: 'building', 'zone', or 'equipment'
# - affected_zones: List of impacted zones
```

### 2. **Zone-Level Analysis**
```python
# Calculate deltas for each zone
zone_deltas = analyzer.calculate_zone_level_deltas(output_variables)
# Results include zone-specific changes in energy, temperature, etc.
```

### 3. **Aggregation**
```python
# Aggregate zones to building level
building_deltas = analyzer.aggregate_zones_to_building(zone_deltas)
# Energy: summed, Temperature: averaged
```

### 4. **Multi-Level Sensitivity**
```python
# Calculate sensitivity at all levels
results = analyzer.calculate_multi_level_sensitivity()
# Includes zone→zone, zone→building, equipment→zone relationships
```

## Integration Points

### With Modification Step
- Uses modification tracking to identify what changed
- Leverages scope information for targeted analysis

### With Parsing Step
- Requires zone-level parsing enabled
- Uses relationship data from parsing

### With Surrogate Modeling
- Exports parameters with scope information
- Enables zone-specific surrogate models

### With Calibration
- Provides zone-level calibration targets
- Identifies which zones need calibration

## Benefits

### 1. **Targeted Insights**
- Know which zones drive building performance
- Identify high-impact equipment
- Understand cross-level effects

### 2. **Better Calibration**
- Focus on zones that matter
- Calibrate at appropriate level
- Maintain zone-building consistency

### 3. **Efficient Retrofits**
- Target zones with highest sensitivity
- Prioritize equipment replacements
- Predict building-wide impacts

### 4. **Model Understanding**
- See how changes propagate
- Identify critical zones
- Understand system interactions

## Example Insights

### Critical Zone Identification
```
Zone "Core_Office" contributes 45% to building cooling sensitivity
→ Prioritize this zone for cooling improvements
```

### Equipment Impact
```
"WaterHeater_Zone1" has elasticity of 0.8 for zone temperature
→ 1% efficiency increase → 0.8% zone temperature change
```

### Cross-Level Amplification
```
Zone infiltration changes amplified 1.5x at building level
→ Small zone improvements yield larger building benefits
```

## Next Steps

### 1. **Run the Analysis**
- Ensure all prerequisites are met
- Enable multi_level_analysis in config
- Run the workflow

### 2. **Review Results**
- Check sensitivity_results/multi_level_sensitivity_report.json
- Review visualizations for insights
- Identify critical zones and equipment

### 3. **Apply Insights**
- Use for targeted calibration
- Inform retrofit decisions
- Simplify model where appropriate

### 4. **Extend as Needed**
- Add custom zone weights
- Create equipment groups
- Implement time-varying analysis

## Troubleshooting

### If Zone Data Missing
1. Check parsing configuration includes zone outputs
2. Verify SQL results have Zone column
3. Ensure relationships were parsed

### If All Sensitivities Zero
1. Check modifications actually changed values
2. Verify output variables are affected
3. Ensure proper aggregation method

### If Equipment Not Detected
1. Check equipment_assignments.parquet exists
2. Verify equipment names match
3. Review scope detection logic

## Conclusion

This implementation provides a comprehensive multi-level sensitivity analysis system that:
- Automatically handles your complex data structure
- Provides insights at building, zone, and equipment levels
- Integrates seamlessly with your existing workflow
- Enhances calibration and surrogate modeling

The system is designed to be robust, handling missing data gracefully while providing maximum insights when full data is available.