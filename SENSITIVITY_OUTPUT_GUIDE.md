# Sensitivity Analysis Output Guide

## Overview
The sensitivity analysis generates multiple output files in the `sensitivity_results` directory. Each file serves a specific purpose for different use cases.

## File Descriptions

### 1. Core Analysis Results

#### `modification_sensitivity_report_peak_months_cooling.json`
- **Purpose:** Main sensitivity analysis report with time slicing
- **Contains:** 
  - Top sensitive parameters with scores
  - Metadata about the analysis
  - Time slice information (cooling months)
  - Parameter breakdown by category
- **Use case:** Understanding which parameters most affect energy consumption during peak cooling months

#### `modification_sensitivity_results_peak_months_cooling.parquet`
- **Purpose:** Complete tabular results in efficient binary format
- **Contains:** All 41 parameters with:
  - Sensitivity scores
  - Elasticity values
  - Parameter changes
  - Statistical significance
- **Use case:** Further analysis in Python/pandas, data visualization

### 2. Summary Files

#### `sensitivity_summary.json`
- **Purpose:** High-level overview of the analysis
- **Contains:**
  - Analysis completion status
  - Top 5 most sensitive parameters
  - Parameter distribution by category
  - Statistical summary (mean, std, range)
- **Use case:** Quick overview, executive summaries

#### `time_slice_sensitivity_summary.json`
- **Purpose:** Summary specific to time-sliced analysis
- **Contains:**
  - Time slice configuration
  - Period-specific sensitivity results
  - Seasonal analysis details
- **Use case:** Understanding seasonal variations in parameter sensitivity

### 3. Export Files for Other Tools

#### `top_sensitive_parameters.csv`
- **Purpose:** Simple CSV with most important parameters
- **Contains:** Top 10 parameters ranked by sensitivity
- **Use case:** Import into Excel, quick reference

#### `sensitive_parameters_for_surrogate.json`
- **Purpose:** Detailed parameter info for surrogate model development
- **Contains:**
  - Parameter ranges
  - Categories and types
  - Sensitivity scores
- **Use case:** Building reduced-order models, ML training

#### `sensitivity_for_surrogate.parquet`
- **Purpose:** Training data for surrogate models
- **Contains:** Parameter-output relationships
- **Use case:** Machine learning model development

### 4. Calibration Files

#### `calibration_parameters.csv`
- **Purpose:** Parameters suitable for model calibration
- **Contains:** Most influential parameters for calibration
- **Use case:** Model tuning, parameter estimation

#### `calibration_parameters.json`
- **Purpose:** Detailed calibration configuration
- **Contains:**
  - Parameter bounds
  - Initial values
  - Calibration priorities
- **Use case:** Automated calibration workflows

### 5. Visualization Files

#### `sensitivity_report.html`
- **Purpose:** Web-viewable report
- **Status:** Currently has issues (mostly empty)
- **Use case:** Sharing results via web browser

#### `visualizations/top_parameters_comparison.png`
- **Purpose:** Bar chart of top sensitive parameters
- **Contains:** Visual comparison of sensitivity scores
- **Use case:** Presentations, reports

### 6. Legacy/Compatibility Files

#### `modification_sensitivity_report.json`
- **Purpose:** Non-time-sliced version of the report
- **Contains:** Full-year sensitivity analysis
- **Use case:** Comparing with time-sliced results

#### `important_parameters.json`
- **Purpose:** Alternative format for parameter importance
- **Contains:** Extended parameter metadata
- **Use case:** Backward compatibility

## How to Use These Files

### For Quick Overview:
1. Start with `sensitivity_summary.json`
2. Look at `visualizations/top_parameters_comparison.png`
3. Check top parameters in `top_sensitive_parameters.csv`

### For Detailed Analysis:
1. Load `modification_sensitivity_results_peak_months_cooling.parquet` in Python
2. Use the full report `modification_sensitivity_report_peak_months_cooling.json`
3. Compare seasonal vs annual in time slice summary

### For Model Development:
1. Use `sensitive_parameters_for_surrogate.json` for parameter selection
2. Load `sensitivity_for_surrogate.parquet` for training data
3. Apply calibration parameters from calibration files

### For Reporting:
1. Use the PNG visualization for presentations
2. Import CSV files into Excel for custom charts
3. Reference the JSON summaries for key findings

## Key Findings from This Analysis

Based on the output files:

1. **Most Sensitive Parameters:**
   - Window shading control setpoints (score: 10.0)
   - Ventilation outdoor air flow (score: 10.0)
   - Window geometry multipliers (scores: 1.8-2.8)

2. **Parameter Categories Analyzed:**
   - 9 categories total
   - 41 unique parameters
   - Focus on cooling season (June-August)

3. **Data Quality:**
   - All core analyses completed successfully
   - Time slicing applied correctly
   - Results statistically significant

The outputs provide comprehensive sensitivity information suitable for various downstream applications including optimization, calibration, and surrogate modeling.