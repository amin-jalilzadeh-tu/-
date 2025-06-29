# EnergyPlus Analyzer v3.1 - Quick Reference Guide

## 🚀 Quick Start

```python
from energyplus_analyzer_main import EnergyPlusAnalyzer

# Create analyzer with output validation
analyzer = EnergyPlusAnalyzer("my_project")
analyzer.analyze_project(idf_sql_pairs, validate_outputs=True)
```

## 📊 Output Categories

The system now tracks these output types:
- **Variables**: `OUTPUT:VARIABLE` definitions
- **Meters**: `OUTPUT:METER` definitions  
- **Tables**: `OUTPUT:TABLE:SUMMARYREPORTS`, `OUTPUT:TABLE:MONTHLY`
- **Control**: `OUTPUT:SQLITE`, `OUTPUTCONTROL:TABLE:STYLE`

## 🔍 Key Functions

### Check Output Coverage
```python
# Get coverage summary
coverage = analyzer.data_manager.get_output_coverage_summary()
print(f"Average coverage: {coverage['average_coverage']:.1f}%")

# Load validation details
validation_df = analyzer.data_manager.load_output_validation_results()
```

### Analyze Output Consistency
```python
# Compare across buildings
comparison = analyzer.compare_output_configurations()
print(f"Consistency: {comparison['consistency_score']:.1f}%")
```

### Optimize Outputs
```python
# Get suggestions
suggestions = analyzer.suggest_output_optimization(target_size_mb=100)

# Generate output sets
minimal = analyzer.generate_minimal_output_set()
comprehensive = analyzer.generate_comprehensive_output_set()
```

### Load Output Data
```python
# Load output definitions
variables = analyzer.load_category_data('outputs_variables')
meters = analyzer.load_category_data('outputs_meters')

# Get specific building outputs
config = analyzer.get_output_configuration(building_id)
```

## 📁 Key Files

### Input Data
- `idf_data/outputs/outputs_variables.parquet` - Variable definitions
- `idf_data/outputs/outputs_meters.parquet` - Meter definitions

### Validation Results
- `metadata/output_validation.parquet` - Validation summary
- `sql_results/output_validation/missing_outputs.parquet` - Missing outputs detail

### Analysis Results
- `analysis_ready/output_analysis/output_frequency_matrix.parquet`
- `analysis_ready/extraction_statistics.parquet`

## 🎯 Common Tasks

### Find Missing Outputs
```python
missing = pd.read_parquet('project/sql_results/output_validation/missing_outputs.parquet')
missing_by_var = missing.groupby('variable').size().sort_values(ascending=False)
print("Most commonly missing:", missing_by_var.head())
```

### Check Data Quality
```python
sql_analyzer = analyzer.sql_analyzers[building_id]
quality = sql_analyzer.analyze_output_data_quality()
print(f"Data completeness by category:")
for cat, info in quality['category_quality'].items():
    print(f"  {cat}: {info['completeness']:.1f}%")
```

### Standardize Outputs Across Buildings
```python
# Find common outputs
comparison = analyzer.compare_output_configurations()
common_outputs = comparison['common_variables']

# Identify outliers
for bid, unique in comparison['unique_variables'].items():
    print(f"Building {bid} has {len(unique)} unique outputs")
```

## 📈 Output Metrics in Building Registry

The building registry now includes:
- `output_variables` - Count of OUTPUT:VARIABLE definitions
- `output_meters` - Count of OUTPUT:METER definitions
- `output_coverage` - Percentage of outputs with data

## 🛠️ Troubleshooting

### No Output Data Found
1. Check if outputs are defined in IDF: `analyzer.get_output_configuration(building_id)`
2. Verify SQL has data: `sql_analyzer.get_available_outputs()`
3. Check validation results: `validation_df[validation_df['building_id'] == building_id]`

### Low Output Coverage
1. Review missing outputs: `missing_outputs.parquet`
2. Check reporting frequency mismatches
3. Verify simulation completed successfully

### Large Output Files
1. Use optimization suggestions: `analyzer.suggest_output_optimization()`
2. Remove surface-level outputs for large models
3. Reduce reporting frequency for non-critical variables

## 💡 Best Practices

1. **Always validate outputs** after simulations
2. **Standardize outputs** across similar buildings
3. **Use minimal sets** for large-scale analyses
4. **Document** your output configuration
5. **Monitor coverage** in building metrics

## 📝 Example: Complete Workflow

```python
# 1. Setup
analyzer = EnergyPlusAnalyzer("energy_project_v31")

# 2. Analyze with validation
analyzer.analyze_project(
    [("building1.idf", "building1.sql")],
    validate_outputs=True
)

# 3. Check results
coverage = analyzer.data_manager.get_output_coverage_summary()
if coverage['buildings_with_issues'] > 0:
    print("⚠️ Some buildings have missing outputs")
    
# 4. Optimize for next run
if coverage['average_coverage'] < 95:
    suggestions = analyzer.suggest_output_optimization()
    # Apply suggestions to IDF files...

# 5. Close
analyzer.close()
```

## 🔗 Related Documentation
- See `README.md` in project directory for full structure
- Run `sample_output_analysis.py` for more examples
- Check `output_documentation.json` for variable descriptions