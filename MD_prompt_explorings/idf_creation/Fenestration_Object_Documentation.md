# Fenestration Object Documentation

## Overview
The Fenestration module creates window objects (`FENESTRATIONSURFACE:DETAILED`) and associated materials and constructions in EnergyPlus IDF files. It handles window-to-wall ratio (WWR) calculations, material property assignment, and construction assembly based on building type, age, and scenario.

## Input Data

### Building Row Data
- **ogc_fid**: Unique building identifier
- **building_function**: "residential" or "non_residential"
- **residential_type**/**non_residential_type**: Specific building subtype
- **age_range**: Building construction period (e.g., "1946 - 1964", "2015 and later")
- **area**: Building floor area
- **perimeter**: Building perimeter
- **building_orientation**: Building orientation angle
- **window_area_m2** (optional): Pre-calculated window area
- **exterior_wall_area_m2** (optional): Pre-calculated exterior wall area
- **door_area_m2** (optional): Pre-calculated door area

### Base Data Sources
- **res_data**: Residential fenestration data dictionary
- **nonres_data**: Non-residential fenestration data dictionary
- Data structure: `{(building_type, age_range, scenario, calibration_stage): element_data}`

### Control Parameters
- **scenario**: Simulation scenario (e.g., "scenario1")
- **calibration_stage**: "pre_calibration" or "post_calibration"
- **strategy**: "A" (midpoint) or "B" (random within range)
- **random_seed**: For reproducible random values

### User Configuration (Optional)
- Excel overrides via dict_override_excel
- JSON overrides from user_configs/{job_id}/fenestration.json
- Can override WWR, R-values, U-values, and material properties

## Process Flow

### 1. Fenestration Data Assignment (assign_fenestration_values.py)

1. **Data Retrieval**:
   - Builds lookup key: `(building_type, age_range, scenario, calibration_stage)`
   - Retrieves element data from res_data or nonres_data
   - Falls back to default values if not found

2. **Element Data Structure**:
   ```python
   {
       "windows": {
           "area_m2": 50.0,
           "U_value_range": [1.5, 2.5],
           "material_window_lookup": "Window_Generic"
       },
       "exterior_wall": {
           "area_m2": 200.0,
           "R_value_range": [2.0, 4.0],
           "material_opaque_lookup": "Brick_Outer"
       },
       # Similar for roof, floor, doors, etc.
   }
   ```

3. **WWR Calculation**:
   ```python
   if use_computed_wwr:
       window_area = elements["windows"]["area_m2"]
       if include_doors_in_wwr:
           window_area += elements["doors"]["area_m2"]
       external_wall_area = elements["exterior_wall"]["area_m2"]
       wwr = window_area / external_wall_area
   ```

4. **Override Application**: Applied in order:
   - Base data from lookup
   - Excel overrides
   - JSON overrides

### 2. Material Creation (materials.py)

#### Material Types Created

1. **MATERIAL** (Opaque with mass):
   ```
   Material,
       Brick_Outer_ogc123,           ! Name
       Rough,                        ! Roughness
       0.1,                         ! Thickness {m}
       0.5,                         ! Conductivity {W/m-K}
       1920,                        ! Density {kg/m3}
       790,                         ! Specific Heat {J/kg-K}
       0.9,                         ! Thermal Absorptance
       0.7,                         ! Solar Absorptance
       0.7;                         ! Visible Absorptance
   ```

2. **MATERIAL:NOMASS** (Lightweight/insulation):
   ```
   Material:NoMass,
       Insulation_ogc123,           ! Name
       Rough,                       ! Roughness
       3.5;                        ! Thermal Resistance {m2-K/W}
   ```

3. **WINDOWMATERIAL:GLAZING**:
   ```
   WindowMaterial:Glazing,
       Window_Generic_ogc123,       ! Name
       SpectralAverage,            ! Optical Data Type
       ,                           ! Window Glass Spectral Data Set Name
       0.003,                      ! Thickness {m}
       0.775,                      ! Solar Transmittance
       0.071,                      ! Solar Reflectance Front
       0.071,                      ! Solar Reflectance Back
       0.881,                      ! Visible Transmittance
       0.080,                      ! Visible Reflectance Front
       0.080,                      ! Visible Reflectance Back
       0.0,                        ! Infrared Transmittance
       0.84,                       ! Infrared Hemispherical Emissivity Front
       0.84,                       ! Infrared Hemispherical Emissivity Back
       1.0;                        ! Conductivity {W/m-K}
   ```

4. **WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM**:
   ```
   WindowMaterial:SimpleGlazingSystem,
       Window_Simple_ogc123,        ! Name
       2.0,                        ! U-Factor {W/m2-K}
       0.4,                        ! Solar Heat Gain Coefficient
       0.5;                        ! Visible Transmittance
   ```

### 3. Construction Assembly

Creates construction objects linking materials:

```
Construction,
    exterior_wall_Construction_ogc123,
    Brick_Outer_ogc123,              ! Outside Layer
    Insulation_ogc123,               ! Layer 2
    Gypsum_Inner_ogc123;             ! Inside Layer
```

Fallback constructions created:
- CEILING1C, Ext_Walls1C, Int_Walls1C
- Roof1C, GroundFloor1C, IntFloor1C
- Window1C (default window construction)

### 4. Window Creation (fenestration.py)

1. **Remove Existing Windows**: Deletes all existing fenestration surfaces
2. **Apply WWR**: Uses geomeppy's `set_wwr()` function
3. **Uniform Distribution**: Windows placed uniformly on all exterior walls
4. **Construction Assignment**: Windows get Window1C or custom construction

### 5. Surface Construction Assignment

Surfaces assigned constructions based on:
- **Surface Type**: WALL, ROOF, CEILING, FLOOR
- **Boundary Condition**: OUTDOORS, GROUND, SURFACE, ADIABATIC

Assignment logic:
```python
if surface_type == "WALL" and boundary == "OUTDOORS":
    construction = "exterior_wall_Construction_ogc123"
elif surface_type == "ROOF" and boundary == "OUTDOORS":
    construction = "flat_roof_Construction_ogc123"
# etc.
```

## Key Calculations

### R-value ↔ U-value Conversion
```python
# R to U
if r_val != 0:
    u_val = 1.0 / r_val

# U to R
if u_val != 0:
    r_val = 1.0 / u_val
```

### Conductivity Calculation
```python
# For opaque materials
if r_val != 0:
    conductivity = thickness / r_val

# For windows (approximation)
if material_type == "WINDOWMATERIAL:GLAZING":
    conductivity = u_val * thickness
```

### Value Selection from Ranges
```python
# Strategy A: Midpoint
value = (min_val + max_val) / 2.0

# Strategy B: Random
value = random.uniform(min_val, max_val)
```

## Output Parameters Assigned

### Window Parameters
- **Window-to-Wall Ratio**: 0.1-0.4 typical range
- **Window U-value**: 1.5-5.0 W/m²·K (varies by age/type)
- **Solar Heat Gain Coefficient**: 0.3-0.7
- **Visible Transmittance**: 0.4-0.9

### Wall Parameters
- **R-value**: 1.0-5.0 m²·K/W (varies by age/construction)
- **Material Layers**: Typically 2-3 layers (exterior, insulation, interior)

### Roof Parameters
- **R-value**: 2.0-8.0 m²·K/W (higher than walls)
- **Construction**: Flat or pitched roof assemblies

## Logging

Detailed logging in `assigned_fenez_log`:
```python
{
    building_id: {
        "wwr": {
            "computed": True,
            "value": 0.25,
            "range": [0.2, 0.3]
        },
        "materials_created": {
            "Brick_Outer_ogc123": {
                "type": "MATERIAL",
                "thickness": 0.1,
                "conductivity": 0.5,
                # ... other properties
            }
        },
        "constructions_created": {
            "exterior_wall_Construction_ogc123": ["Brick_Outer_ogc123", "Insulation_ogc123"]
        },
        "elements": {
            "windows": {
                "area_m2": 50.0,
                "U_value": 2.0,
                "U_value_range": [1.5, 2.5]
            }
            # ... other elements
        }
    }
}
```

## Key Features

1. **Automatic Window Placement**: Uses geomeppy for uniform WWR distribution
2. **Material Property Ranges**: Supports uncertainty quantification
3. **Age-Based Properties**: Materials vary by construction period
4. **Hierarchical Overrides**: Base data → Excel → JSON
5. **Comprehensive Material Library**: Pre-defined materials in lookup tables
6. **Construction Assembly**: Automatic multi-layer construction creation
7. **Building-Specific Materials**: Unique material instances per building