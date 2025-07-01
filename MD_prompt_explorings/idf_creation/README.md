# IDF Creation Documentation Index

This directory contains comprehensive documentation for all IDF object creation modules in the E_Plus_2040_py system. Each module is responsible for creating specific EnergyPlus objects and managing their parameters.

## Documentation Structure

### Core IDF Object Modules

1. **[DHW_Object_Documentation.md](DHW_Object_Documentation.md)**
   - Domestic Hot Water systems (WATERHEATER:MIXED)
   - Tank sizing, temperature schedules, flow calculations
   - NTA 8800 standard compliance

2. **[Lighting_Object_Documentation.md](Lighting_Object_Documentation.md)**
   - Lighting systems (LIGHTS) and parasitic loads (ELECTRICEQUIPMENT)
   - Power densities, schedules, heat gain fractions
   - Building-type specific patterns

3. **[HVAC_Object_Documentation.md](HVAC_Object_Documentation.md)**
   - Ideal Loads Air Systems (ZONEHVAC:IDEALLOADSAIRSYSTEM)
   - Thermostats, setpoints, supply air conditions
   - Zone equipment connections

4. **[Equipment_Object_Documentation.md](Equipment_Object_Documentation.md)**
   - Electric equipment/plug loads (ELECTRICEQUIPMENT)
   - Usage schedules, heat gain distribution
   - Building-type specific densities

5. **[Fenestration_Object_Documentation.md](Fenestration_Object_Documentation.md)**
   - Windows (FENESTRATIONSURFACE:DETAILED)
   - Materials (MATERIAL, WINDOWMATERIAL)
   - Constructions and WWR calculations

6. **[Remaining_Objects_Documentation.md](Remaining_Objects_Documentation.md)**
   - **Geometry**: Zones and surfaces (ZONE, BUILDINGSURFACE:DETAILED)
   - **Ventilation**: Infiltration and ventilation (ZONEINFILTRATION, ZONEVENTILATION)
   - **Window Shading**: Blinds and controls (WINDOWMATERIAL:BLIND, WINDOWSHADINGCONTROL)
   - **Zone Sizing**: Sizing parameters (SIZING:ZONE)
   - **Ground Temperature**: Monthly ground temperatures (SITE:GROUNDTEMPERATURE)

### Support Modules

7. **[OutputDefinitions_Documentation.md](OutputDefinitions_Documentation.md)**
   - Simulation output configuration
   - Variables, meters, tables, and reports
   - OUTPUT:VARIABLE, OUTPUT:METER objects

8. **[PostProcessing_Documentation.md](PostProcessing_Documentation.md)**
   - Results consolidation and aggregation
   - Time series data merging
   - Multiple building analysis support

9. **[Structuring_Module_Documentation.md](Structuring_Module_Documentation.md)**
   - Parameter structuring for scenario generation
   - Range extraction and organization
   - Calibration data preparation

10. **[Other_Module_Documentation.md](Other_Module_Documentation.md)**
    - Zone list creation (ZONELIST)
    - Utility functions
    - Shared functionality

11. **[Shading_Geometry_Documentation.md](Shading_Geometry_Documentation.md)**
    - External shading surfaces (SHADING:BUILDING:DETAILED)
    - Building and tree shadows
    - Seasonal transmittance schedules

### Overview Documents

12. **[IDF_Objects_Overview.md](IDF_Objects_Overview.md)**
    - High-level system architecture
    - Module interactions and data flow
    - Key design patterns and principles

## Module Relationships

```
Building Data → Geometry → Materials/Constructions → Fenestration
                   ↓
              Zone Creation → Internal Loads (Lighting, Equipment, DHW)
                   ↓
              HVAC Systems → Ventilation → Zone Sizing
                   ↓
              Shading → Ground Temperatures → Output Definitions
                   ↓
              IDF File → EnergyPlus Simulation → Post-Processing
```

## Key Concepts

### Archetype-Based Modeling
- Buildings categorized by function, type, and age
- Parameters assigned from lookup tables
- Support for calibration stages

### Parameter Assignment Strategy
- **Strategy A**: Midpoint of ranges (deterministic)
- **Strategy B**: Random within ranges (stochastic)
- **Default**: Minimum values (conservative)

### Override Hierarchy
1. Base lookup values
2. Excel-based overrides
3. JSON user configurations
4. Building-specific overrides

### Data Flow
1. **Input**: Building characteristics, user configurations
2. **Processing**: Lookup, assignment, calculation
3. **Output**: IDF objects, schedules, logging

## Usage Notes

- Each module can be used independently
- Modules communicate through standardized data structures
- All modules support comprehensive logging
- Designed for batch processing of multiple buildings

## Directory Structure
```
idf_objects/
├── DHW/              # Domestic hot water
├── Elec/             # Lighting
├── eequip/           # Equipment
├── fenez/            # Fenestration
├── geomz/            # Geometry
├── HVAC/             # HVAC systems
├── ventilation/      # Ventilation
├── wshading/         # Window shading
├── shading/          # Geometric shading
├── setzone/          # Zone sizing
├── tempground/       # Ground temperatures
├── outputdef/        # Output definitions
├── postproc/         # Post-processing
├── structuring/      # Data structuring
└── other/            # Utilities
```

## Contributing

When adding new modules:
1. Follow existing patterns for lookup tables
2. Implement parameter assignment with strategies
3. Support override mechanisms
4. Include comprehensive logging
5. Create documentation following the template