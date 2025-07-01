# SQL Data Extraction Recommendations

## Current State Analysis

### What's Currently Extracted

1. **Timeseries Data (sql_analyzer.py)**
   - Energy meters (electricity, gas, district cooling/heating)
   - Weather data (temperature, humidity, solar radiation)
   - Zone conditions (temperatures, humidity)
   - Surface heat transfer
   - Equipment energy use
   - Lighting energy and daylighting
   - HVAC operation
   - Ventilation and infiltration rates
   - Shading device operation

2. **Static Data (sql_table_extractor.py - partially implemented)**
   - ComponentSizes
   - SystemSizes
   - ZoneSizes
   - Zones geometry
   - Surfaces
   - Constructions
   - Materials
   - Schedules
   - Errors

### Key Gaps Identified

The SQL files contain extensive pre-calculated summaries in the `TabularData` table that are not being fully utilized. This table alone contains over 11,000 rows of valuable performance metrics.

## Recommended Additional Extractions

### 1. Annual Performance Summaries
Extract from `TabularData` table:
- **End Uses**: Detailed energy consumption by end use (heating, cooling, lighting, equipment, fans, pumps)
- **End Uses By Subcategory**: More granular breakdown (e.g., "Interior Equipment:General")
- **Site and Source Energy**: Total energy metrics with site-to-source conversion factors
- **Utility Use Per Area**: Energy intensity metrics (MJ/m²)
- **Peak Demands**: Maximum power demands by end use

### 2. Comfort and Operational Metrics
- **Comfort and Setpoint Not Met Summary**: Hours when temperature setpoints were not maintained
- **Unmet Degree-Hours**: Quantification of comfort violations
- **CO2 Level Hours**: Indoor air quality metrics
- **Heat Index/Humidex Hours**: Thermal stress indicators

### 3. Equipment Performance Data
- **Component Sizes**: Actual vs design capacities
- **Coil Performance**: Efficiency ratings (SEER, COP, EER)
- **Fan Performance**: Power and efficiency metrics
- **Water Heater Performance**: Recovery rates and standby losses

### 4. Building Characteristics Summary
- **Envelope Summary**: Wall/window areas by orientation, U-values
- **Window-Wall Ratios**: By zone and orientation
- **Lighting Power Densities**: By zone and space type
- **Internal Loads**: People, equipment, lighting densities

### 5. HVAC System Details
- **Zone Sizing Results**: Design loads and airflows
- **System Sizing Results**: Central plant capacities
- **Outdoor Air Summary**: Ventilation rates and compliance
- **Airflow Balance**: Supply/return/exhaust flows

### 6. Quality Assurance Data
- **Simulation Errors and Warnings**: Categorized by severity
- **Initialization Summary**: Model setup verification
- **Convergence Information**: Numerical stability metrics

## Implementation Recommendations

### 1. Enhanced TabularData Extraction
```python
def extract_tabular_summaries(self) -> Dict[str, pd.DataFrame]:
    """Extract all valuable summary tables from TabularData"""
    
    # Define high-value reports to extract
    target_reports = {
        'end_uses': ['End Uses', 'End Uses By Subcategory'],
        'energy_summary': ['Site and Source Energy', 'Utility Use Per Conditioned Floor Area'],
        'comfort': ['Comfort and Setpoint Not Met Summary', 'Unmet Degree-Hours'],
        'equipment': ['Equipment Summary', 'Coil Sizing Summary'],
        'envelope': ['Envelope Summary', 'Window-Wall Ratio']
    }
    
    # Extract each report category
    summaries = {}
    for category, table_names in target_reports.items():
        category_data = self._extract_tabular_category(table_names)
        if not category_data.empty:
            summaries[category] = category_data
    
    return summaries
```

### 2. Structured Output Format
Organize extracted data into logical categories:
```
parsed_data/
├── building_xxx/
│   ├── timeseries/           # Existing hourly data
│   ├── annual_summary/       # New: Annual performance metrics
│   │   ├── energy_end_uses.csv
│   │   ├── peak_demands.csv
│   │   └── energy_intensity.csv
│   ├── comfort_metrics/      # New: Comfort and IAQ
│   │   ├── unmet_hours.csv
│   │   └── thermal_stress.csv
│   ├── equipment_sizing/     # New: Equipment details
│   │   ├── component_sizes.csv
│   │   └── system_performance.csv
│   └── building_characteristics/  # New: Static properties
│       ├── envelope_summary.csv
│       ├── internal_loads.csv
│       └── construction_details.csv
```

### 3. Data Validation
Add validation to ensure critical summaries are present:
```python
def validate_extraction(self, extracted_data: Dict) -> List[str]:
    """Validate that essential data was extracted"""
    
    required_summaries = [
        'energy_end_uses',
        'site_source_energy',
        'envelope_properties'
    ]
    
    missing = []
    for summary in required_summaries:
        if summary not in extracted_data or extracted_data[summary].empty:
            missing.append(summary)
    
    return missing
```

### 4. Integration with Existing Workflow
Enhance the current SQL analyzer to include summary extraction:
```python
def analyze_sql_file(self, sql_path: Path) -> Dict:
    """Complete SQL analysis including timeseries and summaries"""
    
    results = {
        'timeseries': self.extract_timeseries_data(),
        'summaries': self.extract_tabular_summaries(),
        'sizing': self.extract_sizing_data(),
        'characteristics': self.extract_building_characteristics(),
        'metadata': self.extract_simulation_metadata()
    }
    
    return results
```

## Benefits of Enhanced Extraction

1. **Reduced Post-Processing**: Pre-calculated summaries eliminate need for custom aggregations
2. **Validation Ready**: Annual totals can validate timeseries aggregations
3. **Calibration Support**: More parameters available for calibration targets
4. **Complete Building Profile**: Full characterization for surrogate modeling
5. **Quality Assurance**: Error and warning tracking for simulation reliability

## Priority Implementation Order

1. **High Priority**: Energy end uses, site/source totals, comfort metrics
2. **Medium Priority**: Equipment sizing, envelope characteristics
3. **Low Priority**: Detailed HVAC performance, initialization summaries

This enhanced extraction will provide a complete picture of building performance and characteristics, supporting all downstream analysis workflows.