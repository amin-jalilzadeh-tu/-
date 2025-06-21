# Enhanced Sensitivity Analysis - Implementation Summary

## What We've Built

We've created a comprehensive enhanced sensitivity analysis module that significantly extends the capabilities of your existing system. This module serves as a critical bridge between your scenario generation/simulation phase and the modification/calibration phase.

## Key Components Added

### 1. **Enhanced Sensitivity Analyzer** (`enhanced_sensitivity_analyzer.py`)
- **EnhancedSensitivityAnalyzer** class that orchestrates the entire analysis
- Building-specific analysis capabilities
- System-level parameter grouping
- Multi-objective optimization support
- Validation integration
- Automated recommendations generation

### 2. **Visualization Module** (`sensitivity_visualization.py`)
- **SensitivityVisualizer** class for comprehensive visualizations
- Interactive Plotly dashboards
- Static matplotlib plots (tornado, heatmaps, etc.)
- Automated HTML report generation
- Conflict analysis visualizations

### 3. **Updated Main Calibration** (`updated_main_cal.py`)
- Integrated workflow that connects sensitivity → surrogate → calibration
- Automatic parameter selection based on sensitivity results
- Enhanced configuration management
- Workflow summary generation

### 4. **Configuration Examples** (`enhanced_combined_config_example.json`)
- Complete configuration structure for all new features
- Preset configurations for common use cases
- Integration with existing orchestrator configuration

## How It Works

### Data Flow

```
Scenarios + Simulation Results
           ↓
   Enhanced Sensitivity Analysis
           ↓
    ┌──────┴──────┬─────────┬──────────┐
    │             │         │          │
Building-    System-    Multi-    Validation
Specific     Level      Objective  Integration
    │             │         │          │
    └──────┬──────┴─────────┴──────────┘
           ↓
     Recommendations
           ↓
    ┌──────┴──────┬──────────┐
    │             │          │
Modification  Surrogate  Calibration
Priorities    Features   Parameters
```

### Key Features

1. **Building-Specific Analysis**
   - Groups buildings by function, age, or custom criteria
   - Identifies building-specific vs. universal parameters
   - Weights by validation performance

2. **System-Level Analysis**
   - Groups parameters by building system
   - Calculates system impact scores
   - Identifies system interactions

3. **Multi-Objective Support**
   - Handles multiple target variables simultaneously
   - Identifies conflicting parameters
   - Creates weighted composite scores

4. **Time Slice Analysis**
   - Focus on specific time periods (peak hours, seasons)
   - Predefined slices (peak cooling, winter mornings, etc.)
   - Custom time filtering

5. **Adaptive Analysis**
   - Morris screening for large parameter sets
   - Detailed Sobol analysis on top parameters
   - Computational efficiency optimization

6. **Comprehensive Visualization**
   - Interactive dashboards
   - Parameter importance charts
   - Building comparison matrices
   - Conflict analysis plots
   - Automated HTML reports

7. **Actionable Recommendations**
   - Modification priorities
   - Calibration focus areas
   - Dead parameter identification
   - System-level priorities

## Integration Points

### 1. With Validation Module
```python
# Automatically loads validation results
# Weights sensitivity by building performance
# Focuses on failed buildings
```

### 2. With Surrogate Module
```python
# Provides ranked parameter list
# Enables feature selection
# Reduces dimensionality
```

### 3. With Calibration Module
```python
# Identifies top parameters
# Highlights conflicting parameters
# Provides parameter bounds
```

### 4. With Modification Module
```python
# Prioritizes parameters for modification
# Identifies dead parameters to fix
# Suggests system-level strategies
```

## Usage in Your Workflow

### 1. After Simulation
```bash
# Run enhanced sensitivity analysis
python orchestrator.py --config combined.json
# (with sensitivity.perform_sensitivity = true)
```

### 2. Review Results
- Check `sensitivity_analysis/report/sensitivity_report.html`
- Review `sensitivity_analysis/recommendations.json`
- Examine building-specific patterns

### 3. Use for Next Steps
- Top parameters → Surrogate features
- Non-conflicting parameters → Calibration
- High-impact parameters → Modification
- Dead parameters → Fix at nominal values

## Configuration Options

### Quick Analysis
```json
{
  "sensitivity": {
    "perform_sensitivity": true,
    "method": "correlation",
    "visualization": {
      "generate_plots": false
    }
  }
}
```

### Comprehensive Analysis
```json
{
  "sensitivity": {
    "perform_sensitivity": true,
    "method": "correlation",
    "building_specific": {"perform": true},
    "validation_integration": {"use_validation_weights": true},
    "parameter_grouping": {"group_by_system": true},
    "multi_objective": {"composite_score": true},
    "visualization": {"generate_plots": true},
    "adaptive_analysis": {"screening_first": true}
  }
}
```

### Peak Load Focus
```json
{
  "sensitivity": {
    "time_slice_config": {
      "method": "predefined",
      "predefined_slice": "peak_cooling_months"
    },
    "target_variable": ["Cooling", "Electricity"]
  }
}
```

## Benefits

1. **Better Understanding**: Know which parameters truly matter for your buildings
2. **Efficiency**: Focus computational resources on important parameters
3. **Building-Specific Insights**: Tailor strategies to building types
4. **Conflict Resolution**: Identify and handle multi-objective trade-offs
5. **Automated Workflow**: Seamless integration with existing modules
6. **Actionable Output**: Clear recommendations for next steps
7. **Comprehensive Documentation**: HTML reports for stakeholders

## Future Enhancements

The module is designed to support your planned automated pipeline:

1. **Automated Iteration**
   - Track sensitivity changes across modification rounds
   - Identify convergence patterns
   - Suggest when to stop iterating

2. **Building Selection**
   - Automatically select buildings for modification based on sensitivity
   - Focus on high-impact opportunities
   - Track improvement potential

3. **Progressive Refinement**
   - Start with coarse analysis
   - Refine based on initial results
   - Zoom in on critical parameters

## Files Modified/Added

1. **New Files**:
   - `cal/enhanced_sensitivity_analyzer.py`
   - `cal/sensitivity_visualization.py`
   - `cal/updated_main_cal.py`
   - Configuration examples

2. **Updated Files**:
   - `cal/unified_sensitivity.py` (enhanced with new features)
   - `cal/time_slice_utils.py` (already existed, enhanced)

3. **No Changes Required**:
   - `orchestrator.py` (works with new config)
   - Existing validation, surrogate, calibration modules

## Next Steps

1. **Test the Module**: Run with your actual data
2. **Review Reports**: Check the HTML output and recommendations
3. **Integrate Results**: Use rankings in surrogate/calibration
4. **Iterate**: Re-run after modifications to track changes
5. **Customize**: Adjust configuration based on your specific needs

The enhanced sensitivity analysis module is now a powerful tool in your building energy optimization workflow, providing deep insights and actionable recommendations for improving building performance.