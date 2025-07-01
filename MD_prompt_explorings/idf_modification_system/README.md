# IDF Modification System Overview

## Introduction

The IDF Modification System is a comprehensive framework for systematically modifying EnergyPlus Input Data Files (IDFs) to explore building performance improvements, conduct sensitivity analyses, and optimize building designs. The system provides a modular, extensible architecture for applying various energy conservation measures (ECMs) and design modifications to building models.

## System Architecture

### Core Components

1. **Orchestrator** (`orchestrator/main.py`, `orchestrator/modification_step.py`)
   - Manages the overall workflow
   - Coordinates between different steps
   - Handles configuration and job management

2. **Modification Engine** (`idf_modification/modification_engine.py`)
   - Central controller for all modifications
   - Loads and manages modifier instances
   - Applies modifications based on configuration

3. **Base Modifier** (`idf_modification/base_modifier.py`)
   - Abstract base class for all modifiers
   - Provides common functionality
   - Defines the modifier interface

4. **Category-Specific Modifiers** (`idf_modification/modifiers/`)
   - Implement specific modification logic
   - Handle parameter definitions and constraints
   - Apply domain-specific strategies

## Modification Categories

### 1. **HVAC Systems** ([Details](hvac_modifications.md))
- Cooling/heating equipment efficiency
- Fan and pump performance
- Control strategies
- Heat recovery systems

### 2. **Lighting** ([Details](lighting_modifications.md))
- LED retrofits
- Occupancy sensors
- Daylight harvesting
- Task tuning

### 3. **Domestic Hot Water (DHW)** ([Details](dhw_modifications.md))
- Water heater efficiency
- Low-flow fixtures
- Heat pump conversions
- Standby loss reduction

### 4. **Building Envelope** ([Details](materials_and_fenestration_modifications.md))
- Insulation upgrades
- Window performance
- Thermal mass
- Cool roofs

### 5. **Plug Loads & Equipment** ([Details](equipment_modifications.md))
- Efficient equipment
- Energy Star standards
- Plug load reduction

### 6. **Air Infiltration** ([Details](infiltration_modifications.md))
- Air sealing
- Tight construction standards
- Passive House levels

### 7. **Ventilation** ([Details](ventilation_modifications.md))
- Demand-controlled ventilation
- Heat recovery ventilation
- Natural ventilation strategies

### 8. **Schedules** ([Details](schedules_modifications.md))
- Occupancy patterns
- Temperature setbacks
- Equipment scheduling

### 9. **Shading** ([Details](shading_modifications.md))
- Dynamic shading controls
- Automated blinds
- Fixed overhangs

### 10. **Geometry** ([Details](geometry_modifications.md))
- Window-to-wall ratio
- Zone volumes
- Surface properties

### 11. **Simulation Control** ([Details](simulation_control_modifications.md))
- Timestep settings
- Convergence parameters
- Output controls

### 12. **Site Location** ([Details](site_location_modifications.md))
- Climate variations
- Ground temperatures
- Design days

## Workflow Process

### 1. Configuration Phase
```yaml
modification:
  perform_modification: true
  modification_strategy:
    type: "scenarios"  # or "sensitivity", "optimization"
    num_variants: 5
  categories_to_modify:
    hvac:
      enabled: true
      strategy: "high_efficiency"
    lighting:
      enabled: true
      strategy: "led_retrofit"
```

### 2. IDF Selection
- Select base IDFs from generated building models
- Options: all, specific building IDs, or representative sample
- Maintains building ID tracking throughout process

### 3. Modification Application
```
For each building:
  For each variant:
    1. Load parsed IDF objects
    2. Apply category modifications
    3. Track all changes
    4. Generate modified IDF
    5. Store modification results
```

### 4. Output Generation
- Modified IDF files in `modified_idfs/`
- Modification reports in JSON/Parquet/CSV formats
- Detailed change tracking with before/after values
- Wide and long format data outputs

## Data Flow

```
Original IDF → Parser → Parsed Objects → Modifier → Modified Objects → Writer → Modified IDF
                              ↓                              ↓
                     Current Values DB              Modification Tracking
                                                            ↓
                                                    Analysis Reports
```

## Output Formats

### 1. Modified IDFs
- Location: `{job_output_dir}/modified_idfs/`
- Naming: `building_{id}_variant_{n}.idf`
- Preserves all non-modified objects

### 2. Modification Reports

#### JSON Format
```json
{
  "metadata": {
    "job_id": "string",
    "timestamp": "ISO-8601",
    "output_directory": "path"
  },
  "summary": {
    "total_variants": 10,
    "successful": 10,
    "total_modifications": 250
  },
  "results": [...]
}
```

#### Parquet Format (Wide)
| building_id | variant_id | hvac_cooling_cop | lighting_watts_per_area | ... |
|-------------|------------|------------------|-------------------------|-----|
| 1001 | variant_0 | 4.5 | 8.2 | ... |
| 1001 | variant_1 | 5.2 | 6.5 | ... |

#### Parquet Format (Long)
| building_id | variant_id | category | parameter | original_value | new_value |
|-------------|------------|----------|-----------|----------------|-----------|
| 1001 | variant_0 | hvac | cooling_cop | 3.2 | 4.5 |
| 1001 | variant_0 | lighting | watts_per_area | 12.0 | 8.2 |

### 3. Analysis Files
- Parameter changes with percentage differences
- Category-wise modification summaries
- Building-variant modification matrix

## Integration with Other Systems

### 1. Simulation Step
- Modified IDFs automatically queued for simulation
- Results parsed and stored separately
- Maintains variant tracking

### 2. Sensitivity Analysis
- Modification results feed into sensitivity calculations
- Parameter variations tracked across variants
- Multi-level analysis support (building/zone/equipment)

### 3. Surrogate Modeling
- Modification parameters become model inputs
- Simulation results become model outputs
- Enables rapid optimization studies

### 4. Calibration
- Modifications tested against measured data
- Parameter bounds informed by modification ranges
- Automated scenario generation

## Best Practices

### 1. Configuration
- Enable only necessary categories to reduce complexity
- Use appropriate strategies for building type
- Set realistic parameter ranges

### 2. Performance
- Batch similar modifications together
- Use parallel processing for large jobs
- Monitor memory usage with many variants

### 3. Validation
- Review modification reports before simulation
- Check for parameter conflicts
- Validate against engineering judgment

### 4. Analysis
- Use wide format for statistical analysis
- Use long format for detailed tracking
- Combine with simulation results for full picture

## Extension Guide

### Adding New Modifiers
1. Create new class inheriting from `BaseModifier`
2. Define parameter definitions in `_initialize_parameters()`
3. Implement modification strategies
4. Register in modifier loading system

### Adding New Strategies
1. Add strategy method to existing modifier
2. Implement modification logic
3. Update documentation
4. Add to configuration options

### Custom Workflows
1. Extend `ModificationEngine` for custom logic
2. Override `apply_modifications()` method
3. Integrate with workflow orchestrator

## Troubleshooting

### Common Issues
1. **Missing Parameters**: Check IDF has required objects
2. **Invalid Values**: Review parameter constraints
3. **File Not Found**: Verify IDF selection configuration
4. **Memory Issues**: Reduce variants or batch size

### Debug Options
- Enable debug logging in configuration
- Check modification reports for errors
- Review parsed object structure
- Validate modified IDFs with EnergyPlus

## Future Enhancements

1. **Machine Learning Integration**
   - Automated strategy selection
   - Optimal parameter determination
   - Pattern recognition in modifications

2. **Real-time Optimization**
   - Dynamic modification during simulation
   - Adaptive parameter adjustment
   - Convergence-based modification

3. **Cloud Scaling**
   - Distributed modification processing
   - Parallel variant generation
   - Result aggregation services

## References

- EnergyPlus Documentation: [https://energyplus.net/documentation](https://energyplus.net/documentation)
- ASHRAE Standards: Various efficiency guidelines
- Building Performance Institute: Best practices
- DOE Building Technologies Office: Energy conservation measures