# Modification Tracking System

## Overview

The modification tracking system records every change made to IDF files, enabling analysis, validation, and reproducibility. It maintains a complete audit trail from base IDF to final variants.

## Tracking Architecture

### Data Flow
```
Modification Request
    ↓
Parameter Change
    ↓
Validation Check
    ↓
Change Recording
    ↓
Multiple Output Formats
```

## Tracking Data Structure

### 1. Modification Record Schema

```python
ModificationRecord = {
    # Identification
    "modification_id": "uuid",
    "timestamp": "2025-01-07T10:30:45.123456",
    "job_id": "e0e23b56-96a2-44b9-9936-76c15af196fb",
    
    # Building Information
    "building_id": "4136733",
    "variant_id": "variant_0",
    "base_idf_path": "original_idfs/building_4136733.idf",
    "variant_idf_path": "modified_idfs/building_4136733_variant_0.idf",
    
    # Modification Details
    "category": "hvac",
    "modifier_class": "HVACModifier",
    "strategy": "high_efficiency",
    
    # Object Information
    "object_type": "COIL:COOLING:DX:SINGLESPEED",
    "object_name": "Main Cooling Coil 1",
    "object_id": "obj_12345",
    
    # Field Changes
    "field_name": "Gross Rated COP",
    "field_index": 13,
    "original_value": "3.5",
    "new_value": "4.5",
    "value_type": "float",
    "units": "W/W",
    
    # Analysis Data
    "change_type": "multiplier",
    "change_factor": 1.286,
    "change_percentage": 28.57,
    
    # Validation
    "validation_status": "valid",
    "validation_message": "Within acceptable range",
    "constraints_checked": ["min_max", "efficiency_limit"],
    
    # Context
    "zone_name": "Zone 1",
    "zone_area": 150.5,
    "modification_rule": "cooling_cop_multiplier",
    "parent_modifications": ["mod_123", "mod_124"]
}
```

### 2. Aggregated Tracking Formats

#### Wide Format (modifications_detail_wide_*.parquet)
```
| building_id | variant_id | hvac_cooling_cop | hvac_heating_eff | envelope_wall_r | ... |
|-------------|------------|------------------|------------------|-----------------|-----|
| 4136733     | variant_0  | 4.5             | 0.95            | 30.0           | ... |
| 4136733     | variant_1  | 5.0             | 0.95            | 35.0           | ... |
```

#### Long Format (parameter_changes_*.parquet)
```
| building_id | variant_id | parameter       | original | new  | change_pct |
|-------------|------------|-----------------|----------|------|------------|
| 4136733     | variant_0  | cooling_cop     | 3.5      | 4.5  | 28.57     |
| 4136733     | variant_0  | heating_eff     | 0.82     | 0.95 | 15.85     |
```

#### Summary Format (modifications_summary_*.parquet)
```
| building_id | variant_id | total_changes | categories_modified | energy_impact_est |
|-------------|------------|---------------|--------------------|--------------------|
| 4136733     | variant_0  | 25            | hvac,envelope      | -15.3%            |
| 4136733     | variant_1  | 32            | all                | -22.7%            |
```

## Output Formats

### 1. JSON Report (modification_report_*.json)

Complete hierarchical report of all modifications:

```json
{
  "metadata": {
    "timestamp": "2025-01-07T10:30:45",
    "job_id": "e0e23b56-96a2-44b9-9936-76c15af196fb",
    "total_buildings": 5,
    "total_variants": 25,
    "total_modifications": 625
  },
  "buildings": {
    "4136733": {
      "variants": {
        "variant_0": {
          "strategy": "high_efficiency",
          "total_changes": 25,
          "categories": {
            "hvac": {
              "changes": 10,
              "objects_modified": [
                {
                  "object_type": "COIL:COOLING:DX:SINGLESPEED",
                  "object_name": "Main Cooling Coil 1",
                  "modifications": [
                    {
                      "field": "Gross Rated COP",
                      "original": "3.5",
                      "new": "4.5",
                      "change_pct": 28.57
                    }
                  ]
                }
              ]
            }
          }
        }
      }
    }
  }
}
```

### 2. Parquet Files

High-performance columnar format for analysis:

```python
# Read modification data
import pandas as pd

# Wide format - one row per variant
wide_df = pd.read_parquet('modifications_detail_wide_*.parquet')

# Long format - one row per parameter change  
changes_df = pd.read_parquet('parameter_changes_*.parquet')

# Summary - aggregated statistics
summary_df = pd.read_parquet('modifications_summary_*.parquet')
```

### 3. CSV Export

Human-readable format:

```csv
building_id,variant_id,category,parameter,original,new,change_pct,units
4136733,variant_0,hvac,cooling_cop,3.5,4.5,28.57,W/W
4136733,variant_0,hvac,heating_efficiency,0.82,0.95,15.85,fraction
```

### 4. HTML Report

Interactive web report with:
- Summary statistics
- Modification visualizations
- Sortable/filterable tables
- Parameter change distributions

## Tracking Implementation

### 1. ModificationTracker Class

```python
class ModificationTracker:
    def __init__(self):
        self.modifications = []
        self.summary_stats = defaultdict(int)
        
    def track_modification(self, 
                          building_id: str,
                          variant_id: str,
                          category: str,
                          modification_details: dict):
        """Record a single modification"""
        
        record = {
            'timestamp': datetime.now().isoformat(),
            'building_id': building_id,
            'variant_id': variant_id,
            'category': category,
            **modification_details
        }
        
        # Validate before tracking
        if self.validate_modification(record):
            self.modifications.append(record)
            self.update_summary_stats(record)
            
    def export_tracking_data(self, output_dir: Path):
        """Export tracking data in multiple formats"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON report
        self.export_json_report(
            output_dir / f'modification_report_{timestamp}.json'
        )
        
        # Parquet files
        self.export_parquet_files(output_dir, timestamp)
        
        # CSV summary
        self.export_csv_summary(
            output_dir / f'modifications_summary_{timestamp}.csv'
        )
        
        # HTML report
        self.generate_html_report(
            output_dir / f'modification_report_{timestamp}.html'
        )
```

### 2. Real-time Tracking

```python
def track_field_modification(self, 
                           obj_before: dict,
                           obj_after: dict,
                           field_index: int,
                           field_name: str):
    """Track individual field changes"""
    
    original_value = obj_before['fields'][field_index]
    new_value = obj_after['fields'][field_index]
    
    if original_value != new_value:
        change_record = {
            'object_type': obj_before['object_type'],
            'object_name': obj_before.get('name', 'unnamed'),
            'field_name': field_name,
            'field_index': field_index,
            'original_value': original_value,
            'new_value': new_value,
            'change_percentage': self.calculate_change_percentage(
                original_value, new_value
            )
        }
        
        self.current_modifications.append(change_record)
```

## Analysis Capabilities

### 1. Change Impact Analysis

```python
def analyze_modification_impact(tracking_data):
    """Analyze the impact of modifications"""
    
    impact_analysis = {
        'parameter_sensitivity': {},
        'category_impact': {},
        'correlation_matrix': {}
    }
    
    # Parameter sensitivity
    for param in tracking_data['parameters']:
        impact_analysis['parameter_sensitivity'][param] = {
            'mean_change': np.mean(param['changes']),
            'impact_on_energy': correlation_with_energy(param),
            'frequency': len(param['changes'])
        }
    
    return impact_analysis
```

### 2. Modification Patterns

```python
def identify_modification_patterns(tracking_df):
    """Identify common modification patterns"""
    
    patterns = {
        'common_combinations': find_parameter_combinations(tracking_df),
        'category_sequences': analyze_category_order(tracking_df),
        'value_distributions': calculate_value_distributions(tracking_df)
    }
    
    return patterns
```

### 3. Validation Summary

```python
def generate_validation_summary(tracking_data):
    """Summarize validation results"""
    
    summary = {
        'total_modifications': len(tracking_data),
        'valid_modifications': sum(1 for m in tracking_data 
                                 if m['validation_status'] == 'valid'),
        'validation_issues': defaultdict(list)
    }
    
    for mod in tracking_data:
        if mod['validation_status'] != 'valid':
            summary['validation_issues'][mod['validation_message']].append(
                f"{mod['building_id']}:{mod['object_name']}"
            )
    
    return summary
```

## Integration with Other Systems

### 1. Calibration System
```python
# Tracking data helps calibration understand which parameters changed
calibration_params = tracking_df[
    tracking_df['category'].isin(['hvac', 'envelope'])
]['parameter'].unique()
```

### 2. Sensitivity Analysis
```python
# Use tracking to identify parameters for sensitivity analysis
sensitive_params = tracking_df.groupby('parameter')['change_pct'].std()
high_variation_params = sensitive_params[sensitive_params > 10].index
```

### 3. Reporting System
```python
# Generate automated reports from tracking data
report_generator.create_modification_report(
    tracking_data=tracking_df,
    include_visualizations=True,
    format='pdf'
)
```

## Best Practices

1. **Comprehensive Tracking**: Record every change, no matter how small
2. **Immediate Validation**: Validate changes as they're made
3. **Multiple Formats**: Export in formats suitable for different uses
4. **Hierarchical Organization**: Maintain building/variant/category structure
5. **Performance Optimization**: Use efficient storage formats (Parquet)
6. **Metadata Preservation**: Keep all context about modifications
7. **Change Justification**: Record why modifications were made