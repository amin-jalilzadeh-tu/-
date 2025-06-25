# Multi-Level Sensitivity Analysis Guide

## Overview

The enhanced sensitivity analysis system now supports **multi-level analysis** that understands the hierarchical nature of building energy models:

```
Building
    ├── Zone 1
    │   ├── Equipment A
    │   ├── Equipment B
    │   └── Zone Parameters
    ├── Zone 2
    │   ├── Equipment C
    │   └── Zone Parameters
    └── Building-wide Parameters
```

## Key Features

### 1. **Automatic Scope Detection**
The system automatically determines whether a modification affects:
- **Building Level**: Changes to all zones (e.g., global setpoints)
- **Zone Level**: Changes to specific zones (e.g., zone lighting)
- **Equipment Level**: Changes to specific equipment (e.g., water heater efficiency)

### 2. **Multi-Level Sensitivity Relationships**
Analyzes five types of relationships:

| Level | Source | Target | Example |
|-------|--------|--------|---------|
| Building-to-Building | Building parameter | Building output | HVAC efficiency → Total energy |
| Zone-to-Zone | Zone parameter | Same zone output | Zone lighting → Zone electricity |
| Zone-to-Building | Zone parameter | Building output | Zone infiltration → Total heating |
| Equipment-to-Zone | Equipment parameter | Zone output | Water heater → Zone temperature |
| Cross-Level | Any level | Different level | Equipment → Building total |

### 3. **Smart Aggregation**
- **Energy Variables**: Summed across zones
- **Temperature Variables**: Averaged (optionally weighted by zone volume)
- **Flow Variables**: Summed or averaged based on context

### 4. **Zone and Equipment Tracking**
- Tracks which zones are affected by each modification
- Maps equipment to their assigned zones
- Handles IDF → SQL zone name variations

## Data Flow

```
1. Modification Tracking
   ├── Load modifications with scope detection
   ├── Create modification hierarchy
   └── Identify affected zones/equipment

2. Results Loading
   ├── Load zone-level results (base & modified)
   ├── Load building-level results
   └── Map zones between IDF and SQL

3. Delta Calculation
   ├── Calculate zone-level deltas
   ├── Aggregate to building level
   └── Track cross-level impacts

4. Sensitivity Analysis
   ├── Zone-to-Zone sensitivity
   ├── Zone-to-Building sensitivity
   ├── Equipment-to-Zone sensitivity
   └── Building-to-Building sensitivity

5. Reporting
   ├── Multi-level summary
   ├── Zone-specific insights
   ├── Equipment impact analysis
   └── Cross-level relationships
```

## Configuration

### Enable Multi-Level Analysis

```json
{
  "sensitivity": {
    "analysis_type": "modification_based",
    "modification_analysis": {
      "multi_level_analysis": true,
      "zone_options": {
        "weight_method": "volume"  // or "equal", "area"
      }
    }
  }
}
```

### Output Variables

Include both zone-level and building-level variables:

```json
"output_variables": [
  "Heating:EnergyTransfer [J](Hourly)",        // Building
  "Zone Air Temperature [C](Hourly)",          // Zone
  "Zone Air System Sensible Heating Energy"    // Zone
]
```

## Interpreting Results

### 1. **Sensitivity Score Components**
```
Sensitivity Score = |Correlation| × (1 + |Elasticity|)
```
- **Correlation**: Direction and strength of relationship
- **Elasticity**: Responsiveness (% output change / % input change)

### 2. **Confidence Levels**
- **High**: p-value < 0.01 (very significant)
- **Medium**: p-value < 0.05 (significant)
- **Low**: p-value < 0.1 (marginally significant)

### 3. **Level-Specific Insights**

#### Zone-to-Zone
- Direct impact within a zone
- Highest confidence
- Use for zone-specific optimization

#### Zone-to-Building
- How zone changes affect total building
- Shows zone importance
- Identifies critical zones

#### Equipment-to-Zone
- Equipment's local impact
- Important for equipment sizing
- Helps prioritize retrofits

## Example Results Interpretation

### High Impact Zone
```json
{
  "zone": "Zone1_Core",
  "avg_impact": 2.45,
  "parameters": ["infiltration", "lighting"],
  "contribution_to_building": "35%"
}
```
**Meaning**: This zone contributes 35% to building energy sensitivity

### Cross-Level Amplification
```json
{
  "level": "zone-to-building",
  "parameter": "hvac_zone_params",
  "elasticity": 1.8
}
```
**Meaning**: 1% change in zone HVAC → 1.8% change in building energy

### Equipment Cascade
```json
{
  "equipment": "WaterHeater_Zone1",
  "zone_impact": 0.7,
  "building_impact": 0.2
}
```
**Meaning**: Equipment strongly affects its zone but has diluted building impact

## Use Cases

### 1. **Targeted Retrofits**
Identify which zones/equipment have highest impact for cost-effective upgrades

### 2. **Zonal Control Optimization**
Understand which zones deserve individual control vs. can share setpoints

### 3. **Equipment Prioritization**
Rank equipment by their building-wide impact for replacement schedules

### 4. **Model Simplification**
Identify zones/equipment with negligible impact that could be simplified

## Troubleshooting

### Missing Zone Data
- Check if parsing included zone-level outputs
- Verify zone name mappings exist
- Ensure SQL results have Zone column

### Low Equipment Sensitivity
- Equipment may have minimal impact
- Check if equipment is properly assigned to zones
- Verify equipment parameters were modified

### Unexpected Aggregation
- Review weight_method setting
- Check zone geometry data for area/volume
- Verify aggregation method matches variable type

## Best Practices

1. **Include Zone Variables**: Always include zone-level outputs for complete analysis
2. **Sufficient Samples**: Modify multiple buildings for statistical significance
3. **Review Scope**: Check modification scope detection is correct
4. **Validate Mappings**: Ensure zone name mappings are accurate
5. **Appropriate Aggregation**: Use sum for energy, mean for temperature
6. **Cross-Level Validation**: Verify zone sums match building totals

## Advanced Features

### Custom Zone Weights
```python
# In configuration
"zone_weights": {
  "Zone1_Core": 1.5,    # Higher importance
  "Storage": 0.5        # Lower importance
}
```

### Equipment Groups
```python
# Group similar equipment
"equipment_groups": {
  "HVAC_Equipment": ["VAV_*", "AHU_*"],
  "Water_Heating": ["WaterHeater_*", "Boiler_*"]
}
```

### Zone Clustering
Automatically group similar zones for analysis:
- By function (perimeter vs. core)
- By size (large vs. small)
- By exposure (north vs. south)

## Integration with Calibration

The multi-level results enhance calibration by:
1. **Zone-Specific Calibration**: Calibrate problem zones individually
2. **Parameter Prioritization**: Focus on high-impact parameters first
3. **Cross-Level Constraints**: Ensure zone changes sum correctly

## Future Enhancements

1. **Time-Varying Sensitivity**: How sensitivity changes seasonally
2. **Occupancy-Weighted Analysis**: Weight by zone occupancy
3. **System Interaction Effects**: HVAC-Envelope interactions
4. **Uncertainty Propagation**: From zone to building level