# Materials and Fenestration Modifications System

## Overview
The materials modification system handles all building envelope materials including opaque materials (walls, roofs, floors), windows/fenestration, and construction assemblies in EnergyPlus IDF files.

## Modified Object Types

### Opaque Materials
- `MATERIAL` - Standard opaque materials with mass
- `MATERIAL:NOMASS` - Lightweight materials (insulation, air films)
- `MATERIAL:INFRAREDTRANSPARENT` - IR transparent materials
- `MATERIAL:AIRGAP` - Air gap layers

### Window/Fenestration Materials
- `WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM` - Simplified window definitions
- `WINDOWMATERIAL:GLAZING` - Detailed glazing layers
- `WINDOWMATERIAL:GAS` - Gas fill layers
- `WINDOWMATERIAL:GASMIXTURE` - Mixed gas fills
- `WINDOWMATERIAL:SHADE` - Window shading devices
- `WINDOWMATERIAL:BLIND` - Window blinds
- `WINDOWMATERIAL:SCREEN` - Insect screens

### Construction Assemblies
- `CONSTRUCTION` - Layer-by-layer construction definitions
- `CONSTRUCTION:COMPLEXFENESTRATIONSTATE` - Complex fenestration
- `CONSTRUCTION:WINDOWDATAFILE` - Window data from files

## Parameters Modified

### MATERIAL (Opaque) Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `thickness` | Thickness | 2 | float | m | 0.001-1.0 | thermal_resistance |
| `conductivity` | Conductivity | 3 | float | W/m-K | 0.01-5.0 | thermal_resistance |
| `density` | Density | 4 | float | kg/m³ | 10-3000 | thermal_mass |
| `specific_heat` | Specific Heat | 5 | float | J/kg-K | 100-5000 | thermal_mass |
| `thermal_absorptance` | Thermal Absorptance | 6 | float | - | 0.1-0.99 | surface_heat_transfer |
| `solar_absorptance` | Solar Absorptance | 7 | float | - | 0.1-0.99 | solar_gains |
| `visible_absorptance` | Visible Absorptance | 8 | float | - | 0.1-0.99 | daylighting |

### MATERIAL:NOMASS Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `thermal_resistance` | Thermal Resistance | 2 | float | m²-K/W | 0.001-10.0 | thermal_resistance |

### WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `u_factor` | U-Factor | 1 | float | W/m²-K | 0.5-6.0 | window_heat_transfer |
| `shgc` | Solar Heat Gain Coefficient | 2 | float | - | 0.1-0.9 | solar_gains |
| `visible_transmittance` | Visible Transmittance | 3 | float | - | 0.1-0.9 | daylighting |

## Modification Strategies

### 1. Insulation Upgrade (`insulation_upgrade`)
- **Purpose**: Improve thermal resistance of opaque assemblies
- **Modifications**:
  - **For insulation materials** (conductivity < 0.1 W/m-K):
    - Reduces conductivity by 20-40%
    - Increases thickness by 20-50% (max 0.5m)
  - **For MATERIAL:NOMASS**:
    - Increases thermal resistance by 50-100% (max R-10)
  - Targets walls, roofs, and floors

### 2. Window Upgrade (`window_upgrade`)
- **Purpose**: Install high-performance windows
- **Modifications**:
  - **U-Factor**: Sets to 0.8-1.5 W/m²-K (high-performance range)
  - **SHGC**: Sets to 0.25-0.4 (optimized for cooling climates)
  - **Visible Transmittance**: Sets to 0.6-0.8 (maintains daylighting)
  - Simulates triple-pane, low-e, argon-filled windows

### 3. Thermal Mass Increase (`thermal_mass`)
- **Purpose**: Add thermal mass for load shifting
- **Modifications**:
  - **Density**: Increases by 20-50% for materials < 2000 kg/m³
  - **Specific Heat**: Increases by 10-30%
  - Helps reduce temperature swings and peak loads

### 4. Cool Roof (`cool_roof`)
- **Purpose**: Reduce roof heat gain
- **Modifications**:
  - **Solar Absorptance**: Reduces to 0.2-0.3 (high reflectance)
  - **Thermal Absorptance**: Reduces to 0.8-0.9
  - Targets roof materials specifically

## Process Flow

1. **Material Identification**:
   - Scans for all material and construction objects
   - Identifies material types (opaque, window, etc.)
   - Maps materials to construction assemblies

2. **Property Analysis**:
   - Extracts current thermal properties
   - Identifies improvement opportunities
   - Validates physical constraints

3. **Strategic Modification**:
   - Applies targeted improvements based on strategy
   - Maintains material property relationships
   - Ensures physically realistic values

4. **File Handling**:
   - Maps parser output files:
     - `materials_materials.parquet` → materials data
     - `materials_windowmaterials.parquet` → window data
     - `materials_constructions.parquet` → construction data
   - Combines related data for comprehensive modifications

## Output Structure

Each modification produces a result containing:
```json
{
  "building_id": "string",
  "variant_id": "string",
  "category": "materials",
  "object_type": "MATERIAL",
  "object_name": "string",
  "zone_name": "string",
  "parameter": "conductivity",
  "field_name": "Conductivity",
  "original_value": 0.05,
  "new_value": 0.03,
  "strategy": "insulation_upgrade",
  "timestamp": "ISO timestamp"
}
```

## Integration Notes

- Material changes affect all surfaces using those materials
- Window upgrades impact both energy and daylighting
- Thermal mass changes affect comfort and HVAC operation
- Cool roofs primarily benefit cooling-dominated climates
- Construction assembly relationships must be preserved

## Performance Impact

- **Insulation Upgrade**:
  - Reduces conduction heat transfer
  - Lowers heating/cooling loads
  - Improves comfort

- **Window Upgrade**:
  - Reduces window heat loss/gain
  - Controls solar gains
  - Maintains daylighting benefits

- **Thermal Mass**:
  - Dampens temperature swings
  - Shifts peak loads
  - Can reduce HVAC equipment size

- **Cool Roof**:
  - Reduces cooling loads
  - Lowers roof surface temperatures
  - May slightly increase heating loads

## Typical Energy Savings

- **Insulation Upgrade**: 10-25% heating/cooling energy reduction
- **Window Upgrade**: 15-30% reduction in window-related loads
- **Thermal Mass**: 5-15% peak load reduction
- **Cool Roof**: 10-20% cooling energy reduction
- **Combined Envelope Measures**: Up to 40% HVAC energy reduction