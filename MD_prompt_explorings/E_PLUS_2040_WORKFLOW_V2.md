# EnergyPlus 2040 Simulation and Analysis Workflow - Version 2

## Overview
This document provides a comprehensive overview of the EnergyPlus 2040 simulation and analysis pipeline based on actual implementation analysis. The system is a sophisticated, modular framework designed for large-scale building energy simulation workflows with advanced analytics capabilities.

## System Architecture

### Main Orchestrator
- **Entry Point**: `orchestrator.py` (thin wrapper)
- **Core Logic**: `orchestrator/main.py` - coordinates all workflow steps
- **Design Pattern**: Modular pipeline with separate step modules
- **Configuration**: Hierarchical JSON-based configuration system

### Workflow Steps (Sequential)
1. Job environment setup
2. Configuration loading and merging
3. IDF creation and simulations
4. Parsing to Parquet format
5. Timeseries aggregation
6. IDF modification
7. Validation
8. Sensitivity analysis
9. Surrogate modeling
10. Calibration

---

## 1. IDF Creation System

### Purpose
Generate EnergyPlus Input Data Files (IDF) for building simulations using modular components

### Implementation Details
**Main Module**: `orchestrator/idf_creation_step.py`
- **Core Function**: `run_idf_creation()` - orchestrates multi-building IDF generation
- **IDF Generator**: `idf_creation.py` using geomeppy library
- **Database Support**: Can load buildings from database with filters

### IDF Object Components (`/idf_objects/`)
| Component | Purpose | Files |
|-----------|---------|-------|
| DHW | Domestic hot water systems | `dhw_*.idf` |
| Elec | Lighting systems | `elec_*.idf` |
| HVAC | Heating/cooling systems | `hvac_*.idf` |
| eequip | Electric equipment | `eequip_*.idf` |
| fenez | Fenestration (windows) | `fenez_*.idf` |
| geomz | Building geometry | `geomz_*.idf` |
| ventilation | Ventilation systems | `ventilation_*.idf` |
| shading | Window/geometric shading | `shading_*.idf` |
| tempground | Ground temperatures | `tempground_*.idf` |
| setzone | Zone sizing | `setzone_*.idf` |

### Configuration Parameters
```json
{
  "scenario": "scenario1",
  "calibration_stage": "pre_calibration",
  "strategy": "B",
  "run_simulations": true,
  "output_definitions": ["Zone Air Temperature", "Electricity:Facility"]
}
```

### Key Paths
- IDF Objects: `/mnt/d/Documents/daily/E_Plus_2040_py/idf_objects`
- Documentation: `/mnt/d/Documents/daily/E_Plus_2040_py/MD_prompt_explorings/idf_creation`
- Implementation: `/mnt/d/Documents/daily/E_Plus_2040_py/orchestrator/idf_creation_step.py`

---

## 2. Simulation System

### Purpose
Execute EnergyPlus simulations with parallel processing support

### Implementation Details
**Main Module**: `orchestrator/simulation_step.py`
- **Parallel Execution**: Configurable worker count
- **Variant Support**: Handles both base and modified buildings
- **Output**: SQL database files for each simulation

### Features
- Automatic weather file assignment
- Progress tracking
- Error handling and retry logic
- Memory management for large batches

### Key Paths
- Weather Files: `/mnt/d/Documents/daily/E_Plus_2040_py/epw`
- Implementation: `/mnt/d/Documents/daily/E_Plus_2040_py/orchestrator/simulation_step.py`

---

## 3. Parsing System

### Purpose
Extract and structure simulation results into efficient data formats

### Implementation Details
**Main Module**: `orchestrator/parsing_step.py`
- **Core Class**: `CombinedAnalyzer` - handles IDF and SQL parsing
- **Output Format**: Parquet files for efficient storage and querying

### Parse Types
1. **IDF Parsing**: Extract building metadata and parameters
2. **SQL Parsing**: Extract time series simulation results
3. **SQL Static**: Extract schedules and static data

### Data Organization
- Base buildings: `timeseries/base_all_daily.parquet`
- Variant comparisons: `comparisons/` directory
- Metadata: `parsed_data/metadata.parquet`

### Key Paths
- Parser Library: `/mnt/d/Documents/daily/E_Plus_2040_py/parserr`
- Documentation: `/mnt/d/Documents/daily/E_Plus_2040_py/MD_prompt_explorings/idf_parsing`
- Implementation: `/mnt/d/Documents/daily/E_Plus_2040_py/orchestrator/parsing_step.py`

---

## 4. Smart Validation System

### Purpose
Intelligent comparison of simulation results with measured/real data

### Implementation Details
**Main Module**: `validation/smart_validation_wrapper.py`
- **Intelligent Mapping**: Automatic variable name matching
- **Unit Conversion**: Automatic handling of different unit systems
- **Flexible Formats**: Adapts to various data structures

### Key Features
1. **Variable Mapping Strategies**:
   - Exact matching
   - Semantic pattern matching
   - Fuzzy string matching

2. **Automatic Processing**:
   - Unit conversions (J↔kWh, °C↔°F)
   - Date parsing flexibility
   - Zone to building aggregation
   - Frequency alignment (hourly→daily→monthly)

3. **Validation Metrics**:
   - CVRMSE (Coefficient of Variation of RMSE)
   - NMBE (Normalized Mean Bias Error)
   - MBE (Mean Bias Error)
   - Peak analysis
   - Ramp rate analysis

### Configuration
```json
{
  "validation": {
    "perform_validation": true,
    "config": {
      "real_data_path": "measured_data.csv",
      "variables_to_validate": ["Electricity", "Heating", "Temperature"],
      "aggregation": {
        "target_frequency": "daily",
        "methods": {
          "energy": "sum",
          "temperature": "mean"
        }
      },
      "thresholds": {
        "default": {"cvrmse": 30.0, "nmbe": 10.0}
      }
    }
  }
}
```

### Key Path
- Validation System: `/mnt/d/Documents/daily/E_Plus_2040_py/validation`

---

## 5. Modification System

### Purpose
Engine for creating building variants through parameter modifications

### Implementation Details
**Main Module**: `orchestrator/modification_step.py`
- **Core Engine**: `ModificationEngine` class
- **Tracking**: Complete audit trail of all changes

### Modification Strategies
1. **Scenarios**: Predefined modification packages
2. **Random**: Statistical parameter variations
3. **Targeted**: Specific parameter adjustments
4. **Progressive**: Increasing modification intensity

### Output Formats
- JSON: Detailed modification records
- Parquet: Wide/long format for analysis
- CSV/HTML/Markdown: Human-readable reports

### Use Cases
1. **Calibration Support**: Generate parameter variations
2. **Scenario Analysis**: Create alternative designs
3. **Sensitivity Analysis**: Systematic parameter perturbation
4. **Optimization**: Iterative improvements

### Key Paths
- Modification System: `/mnt/d/Documents/daily/E_Plus_2040_py/idf_modification_system`
- Implementation: `/mnt/d/Documents/daily/E_Plus_2040_py/orchestrator/modification_step.py`

---

## 6. Advanced Sensitivity Analysis

### Purpose
Identify parameters that most influence building performance

### Implementation Details
**Main Module**: `orchestrator/sensitivity_step.py`
- **Dual Approach**: Traditional methods + modification-based analysis
- **Multi-level**: Building, zone, and equipment level analysis

### Analysis Methods
1. **Traditional Methods**:
   - Sobol indices
   - Morris screening
   - FAST (Fourier Amplitude Sensitivity Test)

2. **Advanced Features**:
   - Time slicing analysis
   - Uncertainty quantification
   - Threshold detection
   - Regional sensitivity
   - Temporal pattern analysis

### Integration Points
- **Surrogate Modeling**: Exports top N influential parameters
- **Calibration**: Provides parameter ranges and recommendations
- **Visualization**: Interactive sensitivity plots

### Key Paths
- Implementation: `/mnt/d/Documents/daily/E_Plus_2040_py/orchestrator/sensitivity_step.py`
- Sensitivity System: `/mnt/d/Documents/daily/E_Plus_2040_py/c_sensitivity`

---

## 7. Surrogate Modeling System

### Purpose
Create fast approximation models for optimization and exploration

### Implementation Details
**Main Module**: `orchestrator/surrogate_step.py`
- **Dual Pipeline Support**: Integrated (new) and legacy approaches
- **AutoML Integration**: Multiple framework support

### Key Features
1. **Integrated Pipeline** (Recommended):
   - Direct Parquet data usage
   - Automatic feature engineering
   - Sensitivity-based feature selection
   - Multi-target support

2. **Model Types Supported**:
   - Random Forest
   - XGBoost
   - Neural Networks
   - AutoML (H2O, TPOT, AutoSklearn)

3. **Validation & Reporting**:
   - Cross-validation
   - Feature importance
   - Model performance metrics
   - Pipeline visualization

### Key Paths
- Implementation: `/mnt/d/Documents/daily/E_Plus_2040_py/orchestrator/surrogate_step.py`
- Surrogate System: `/mnt/d/Documents/daily/E_Plus_2040_py/c_surrogate`

---

## 8. Calibration System

### Purpose
Optimize simulation parameters to match measured data

### Implementation Details
**Main Module**: `orchestrator/calibration_step.py`
- **Direct Integration**: Uses parsed Parquet data
- **Multi-objective**: Supports multiple optimization targets

### Optimization Methods
1. **Population-based**:
   - PSO (Particle Swarm Optimization)
   - DE (Differential Evolution)
   - NSGA-II (Multi-objective)

2. **Gradient-based**:
   - CMA-ES (Covariance Matrix Adaptation)
   - Hybrid methods

3. **Key Features**:
   - Real-time convergence tracking
   - Constraint handling
   - Parallel evaluation support
   - Surrogate model integration

### Calibration Workflow
```
Load Data → Define Objectives → Set Constraints → 
Optimize → Validate → Update Parameters → Iterate
```

### Key Paths
- Calibration System: `/mnt/d/Documents/daily/E_Plus_2040_py/cal`
- Implementation: `/mnt/d/Documents/daily/E_Plus_2040_py/orchestrator/calibration_step.py`

---

## Process Control Strategies

### A. Human-Based Process
**Configuration Example**:
```json
{
  "orchestration": {
    "strategy": "human-based",
    "mode": "simple",
    "buildings": ["building_1", "building_2"],
    "modifications": {
      "type": "targeted",
      "parameters": ["window_u_value", "wall_insulation"]
    },
    "iterations": 5
  }
}
```

**Characteristics**:
- Manual building selection
- User-defined parameter constraints
- Direct control over process flow
- Explicit iteration management

### B. Performance-Based Process
**Configuration Example**:
```json
{
  "orchestration": {
    "strategy": "performance-based",
    "mode": "full",
    "selection": {
      "method": "validation_failure",
      "fallback": "worst_performers",
      "count": 10
    },
    "convergence": {
      "max_iterations": 20,
      "improvement_threshold": 0.01,
      "no_improvement_limit": 3
    }
  }
}
```

**Characteristics**:
- Automatic building selection based on performance
- Adaptive modification intensity
- Convergence-based termination
- Learning from previous iterations

---

## Data Flow Architecture

### Input Layer
```
┌─────────────────┐  ┌──────────────┐  ┌─────────────┐
│ Building Data   │  │ Config Files │  │ Weather Data│
│ (CSV/Database)  │  │    (JSON)    │  │   (EPW)     │
└────────┬────────┘  └──────┬───────┘  └──────┬──────┘
         └───────────────────┴──────────────────┘
                             │
```

### Processing Layer
```
                    ┌─────────────────┐
                    │ IDF Creation    │
                    └────────┬────────┘
                             │
                    ┌─────────────────┐
                    │ EnergyPlus Sim  │
                    └────────┬────────┘
                             │
                    ┌─────────────────┐
                    │ Parsing System  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Modification   │ │   Validation    │ │   Sensitivity   │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┴───────────────────┘
                             │
                    ┌─────────────────┐
                    │Surrogate/Calib. │
                    └─────────────────┘
```

### Output Layer
```
┌─────────────────┐  ┌──────────────┐  ┌─────────────┐
│ Optimized Params│  │   Reports    │  │  Visualiz.  │
│   (JSON/CSV)    │  │ (HTML/MD/PDF)│  │  (PNG/HTML) │
└─────────────────┘  └──────────────┘  └─────────────┘
```

---

## Configuration System

### Hierarchical Structure
1. **Base Configuration**: `combined.json` - system defaults
2. **User Configuration**: `user_configs/{job_id}/` - job-specific
3. **Excel Overrides**: Material properties and schedules
4. **Runtime Parameters**: Command-line and API inputs

### Key Configuration Sections
```json
{
  "idf_creation": { /* Building generation settings */ },
  "parsing": { /* Data extraction settings */ },
  "modification": { /* Parameter variation settings */ },
  "sensitivity": { /* Analysis methods and parameters */ },
  "surrogate": { /* Model training configuration */ },
  "calibration": { /* Optimization settings */ },
  "validation": { /* Comparison settings */ },
  "orchestration": { /* Workflow control */ }
}
```

---

## Advanced Features

### 1. **Intelligent Defaults**
- Automatic unit detection and conversion
- Smart variable name matching
- Adaptive aggregation methods
- Context-aware thresholds

### 2. **Scalability Features**
- Parallel processing at multiple levels
- Chunked data processing
- Memory-efficient Parquet storage
- Distributed computing support

### 3. **Tracking & Auditing**
- Complete modification history
- Performance metrics logging
- Convergence tracking
- Version control integration

### 4. **Extensibility**
- Plugin architecture for custom steps
- Configurable output formats
- Custom validation metrics
- User-defined modification strategies

---

## Best Practices

### 1. **Workflow Design**
- Start with validation to establish baseline
- Use sensitivity analysis to focus efforts
- Build surrogate models for rapid iteration
- Apply calibration for final optimization

### 2. **Performance Optimization**
- Use Parquet format for large datasets
- Enable parallel processing
- Leverage surrogate models for exploration
- Cache intermediate results

### 3. **Quality Assurance**
- Always validate against measured data
- Track uncertainty through the pipeline
- Document all assumptions
- Version control configurations

---

## Future Enhancements

1. **Cloud Integration**
   - Distributed simulation support
   - Cloud storage backends
   - Containerized deployments

2. **Machine Learning**
   - Advanced feature engineering
   - Automated hyperparameter tuning
   - Ensemble modeling

3. **User Interface**
   - Web-based dashboard
   - Real-time monitoring
   - Interactive visualizations

4. **Integration**
   - BIM model import
   - IoT data streams
   - External optimization services

---

## Conclusion

The EnergyPlus 2040 system represents a comprehensive, production-ready framework for building energy simulation and optimization. Its modular architecture, intelligent defaults, and extensive configuration options make it suitable for both research and commercial applications. The system's emphasis on automation, tracking, and validation ensures reliable, reproducible results across diverse building portfolios and use cases.