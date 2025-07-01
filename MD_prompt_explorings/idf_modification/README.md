# IDF Modification Documentation Index

This directory contains comprehensive documentation for the IDF modification system in the E_Plus_2040_py project. The modification system is a powerful engine for creating building variants, enabling calibration, sensitivity analysis, and scenario development.

## Documentation Structure

### Core System Documentation

1. **[Modification_System_Overview.md](Modification_System_Overview.md)**
   - System architecture and components
   - ModificationEngine and workflow integration
   - Configuration schema and options

2. **[Modification_Strategies.md](Modification_Strategies.md)**
   - Strategy types (scenarios, sampling, optimization)
   - Predefined scenarios (baseline, code_minimum, high_performance, etc.)
   - Custom strategy development

3. **[Parameter_Registry.md](Parameter_Registry.md)**
   - Complete list of modifiable parameters
   - Parameter definitions and constraints
   - Units, ranges, and validation rules

### Category-Specific Modifiers

4. **[HVAC_Modification.md](HVAC_Modification.md)**
   - HVAC system modifications (ZONEHVAC:IDEALLOADSAIRSYSTEM, COIL:COOLING, etc.)
   - Efficiency improvements, capacity changes
   - Setpoint optimization strategies

5. **[Envelope_Modification.md](Envelope_Modification.md)**
   - Materials and constructions (MATERIAL, CONSTRUCTION)
   - Window properties (U-value, SHGC)
   - Insulation and thermal mass optimization

6. **[Internal_Loads_Modification.md](Internal_Loads_Modification.md)**
   - Lighting modifications (LIGHTS)
   - Equipment modifications (ELECTRICEQUIPMENT)
   - Occupancy and schedule adjustments

7. **[Ventilation_Infiltration_Modification.md](Ventilation_Infiltration_Modification.md)**
   - Air change rates (ZONEINFILTRATION, ZONEVENTILATION)
   - Flow rate adjustments
   - Heat recovery modifications

8. **[Other_Modifications.md](Other_Modifications.md)**
   - DHW systems (WATERHEATER:MIXED)
   - Shading devices (SHADING:BUILDING:DETAILED)
   - Site location and ground temperature
   - Geometry modifications

### System Features

9. **[Modification_Tracking.md](Modification_Tracking.md)**
   - Tracking system design
   - Output formats (JSON, Parquet, CSV, HTML)
   - Variant identification and naming

10. **[Rules_and_Validation.md](Rules_and_Validation.md)**
    - Dependency rules between parameters
    - Efficiency rules and constraints
    - Comfort rules and standards compliance
    - Cross-parameter validation

11. **[Integration_Guide.md](Integration_Guide.md)**
    - Integration with orchestrator workflow
    - Connection to parsing system
    - Use in calibration and sensitivity analysis

12. **[Advanced_Features.md](Advanced_Features.md)**
    - Scenario generator capabilities
    - Statistical sampling methods
    - Zone-specific modifications
    - Multi-building batch processing

## Quick Start Example

```python
# Configure modification
config = {
    "modification": {
        "modification_strategy": {
            "type": "scenarios",
            "scenarios": ["high_performance_envelope", "efficient_hvac"],
            "num_variants": 2
        },
        "categories_to_modify": {
            "hvac": {
                "enabled": true,
                "strategy": "high_efficiency"
            },
            "materials": {
                "enabled": true,
                "strategy": "super_insulation"
            }
        }
    }
}

# Run modification
results = run_modification(
    modification_cfg=config['modification'],
    job_output_dir=output_dir,
    job_idf_dir=idf_dir,
    logger=logger
)
```

## Key Concepts

- **Base IDF**: Original building model file
- **Variant**: Modified version of the base IDF
- **Modifier**: Category-specific class that applies modifications
- **Strategy**: Method for selecting and applying parameter changes
- **Tracking**: System for recording all modifications made

## File Organization

```
modified_idfs/
├── building_4136733_variant_0.idf       # Modified IDF files
├── building_4136733_variant_1.idf
├── modification_report_*.json           # Detailed modification report
├── modifications_detail_wide_*.parquet  # Wide format modification data
├── modifications_summary_*.parquet      # Summary of modifications
└── parameter_changes_*.parquet          # Parameter change tracking
```

## Related Systems

- **IDF Creation**: Generates base IDF files (`/idf_creation`)
- **IDF Parsing**: Extracts data from IDF files (`/parserr`)
- **Calibration**: Uses modifications to match measured data (`/cal`)
- **Sensitivity Analysis**: Analyzes parameter impacts (`/c_sensitivity`)
- **Surrogate Modeling**: Fast approximation models (`/c_surrogate`)