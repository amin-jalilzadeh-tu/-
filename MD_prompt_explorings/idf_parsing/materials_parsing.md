# Materials and Constructions Parsing Documentation

## Overview
The materials parsing module extracts material properties and construction assemblies from IDF files and SQL simulation results. This includes opaque materials, window materials, and their thermal properties.

## IDF Objects Parsed

### 1. Opaque Materials

#### MATERIAL
Standard opaque material with full properties.

**Parameters Extracted:**
- Material Name
- `roughness`: Roughness (VeryRough, Rough, MediumRough, MediumSmooth, Smooth, VerySmooth)
- `thickness`: Thickness (m)
- `conductivity`: Conductivity (W/m-K)
- `density`: Density (kg/m³)
- `specific_heat`: Specific Heat (J/kg-K)
- Thermal Absorptance (default 0.9)
- Solar Absorptance (default 0.7)
- Visible Absorptance (default 0.7)

#### MATERIAL:NOMASS
Material with thermal resistance but no thermal mass.

**Parameters Extracted:**
- Material Name
- Roughness
- `thermal_resistance`: Thermal Resistance (m²-K/W)
- Thermal Absorptance
- Solar Absorptance
- Visible Absorptance

#### MATERIAL:AIRGAP
Air gap with thermal resistance.

**Parameters Extracted:**
- Material Name
- Thermal Resistance (m²-K/W)

#### MATERIAL:INFRAREDTRANSPARENT
Material transparent to infrared radiation.

**Parameters Extracted:**
- Material Name

### 2. Window Materials

#### WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM
Simplified window performance input.

**Parameters Extracted:**
- Material Name
- `u_factor`: U-Factor (W/m²-K)
- `solar_heat_gain`: Solar Heat Gain Coefficient
- Visible Transmittance (optional)

#### WINDOWMATERIAL:GLAZING
Detailed glazing layer properties.

**Parameters Extracted:**
- Material Name
- Optical Data Type
- Window Glass Spectral Data Set Name
- Thickness (m)
- Solar Transmittance at Normal Incidence
- Front/Back Side Solar Reflectance at Normal Incidence
- Visible Transmittance at Normal Incidence
- Front/Back Side Visible Reflectance at Normal Incidence
- Infrared Transmittance at Normal Incidence
- Front/Back Side Infrared Hemispherical Emissivity
- Conductivity (W/m-K)

#### WINDOWMATERIAL:GAS
Gas layer in windows.

**Parameters Extracted:**
- Material Name
- Gas Type (Air, Argon, Krypton, Xenon, Custom)
- Thickness (m)
- For custom gas: conductivity, viscosity, specific heat coefficients

#### WINDOWMATERIAL:GASMIXTURE
Gas mixture layer in windows.

**Parameters Extracted:**
- Material Name
- Thickness (m)
- Number of Gases in Mixture
- Gas 1/2/3/4 Type and Fraction

#### Window Shading Materials
- WINDOWMATERIAL:BLIND
- WINDOWMATERIAL:SCREEN  
- WINDOWMATERIAL:SHADE

**Parameters Extracted:**
- Material Name
- Slat properties (for blinds)
- Solar/Visible Transmittance and Reflectance
- Infrared properties
- Thickness
- Conductivity

### 3. Constructions

#### CONSTRUCTION
Assembly of material layers.

**Parameters Extracted:**
- Construction Name
- Outside Layer (material name)
- Layer 2, 3, 4... up to 10 (material names)
- Layer sequence from outside to inside

#### CONSTRUCTION:CFACTORUNDERGROUNDWALL
Underground wall with C-factor.

**Parameters Extracted:**
- Construction Name
- `u_factor`: C-Factor (W/m-K)
- Height (m)

#### CONSTRUCTION:FFACTORGROUNDFLOOR
Ground contact floor with F-factor.

**Parameters Extracted:**
- Construction Name
- `u_factor`: F-Factor (W/m-K)
- Area (m²)
- Perimeter Exposed (m)

#### CONSTRUCTION:INTERNALSOURCE
Construction with internal heat source.

**Parameters Extracted:**
- Construction Name
- Source Present After Layer Number
- Temperature Calculation Requested After Layer Number
- Dimensions for the Source
- Tube Spacing (m)

## SQL Variables Extracted

1. **Surface Inside Face Temperature** (°C)
2. **Surface Outside Face Temperature** (°C)
3. **Surface Inside Face Conduction Heat Transfer Rate** (W)
4. **Surface Outside Face Conduction Heat Transfer Rate** (W)
5. **Surface Average Face Conduction Heat Transfer Rate** (W)
6. **Surface Heat Storage Rate** (W)
7. **Surface Inside Face Convection Heat Transfer Rate** (W)
8. **Surface Outside Face Convection Heat Transfer Rate** (W)

## Key Metrics Calculated

1. **Average U-Value**
   - Area-weighted average U-value of all exterior surfaces
   - Units: W/m²-K

2. **Thermal Mass**
   - Total heat capacity of building envelope
   - Units: kJ/K

3. **Envelope Performance**
   - Combined metric considering U-value, thermal mass, and solar properties

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        ├── materials_materials.parquet
        ├── materials_windowmaterials.parquet
        └── materials_constructions.parquet
```

**materials_materials.parquet columns:**
- building_id
- material_name
- material_type
- thickness
- conductivity
- density
- specific_heat
- thermal_resistance
- roughness
- absorptance_properties

**materials_constructions.parquet columns:**
- building_id
- construction_name
- construction_type
- layer_sequence (as JSON array)
- total_thickness
- total_resistance
- u_value (calculated)

### SQL Timeseries Output
Surface heat transfer data in timeseries files.

## Data Processing Notes

1. **Layer Order**: Construction layers are ordered from outside to inside.

2. **Property Calculation**: Total construction R-value is sum of all layer R-values plus air films.

3. **Window Assemblies**: Complex window constructions may include multiple glazing and gas layers.

4. **Material Libraries**: Materials can be reused across multiple constructions.

5. **Thermal Bridges**: Not explicitly modeled in basic constructions.

## Construction Analysis

### U-Value Calculation
For layered constructions:
```
R_total = R_outside_air + Σ(R_layers) + R_inside_air
U = 1 / R_total
```

### Thermal Mass Calculation
For each material layer:
```
Thermal Mass = Area × Thickness × Density × Specific Heat
```

### Time Lag and Decrement Factor
Calculated from material properties to assess dynamic thermal performance.

## Special Considerations

1. **Phase Change Materials**: Require special material types not shown here.

2. **Variable Properties**: Some materials have temperature-dependent properties.

3. **Moisture Effects**: Basic materials don't include moisture transport.

4. **Spectral Properties**: Detailed window models use wavelength-dependent properties.

5. **Edge Effects**: 2D/3D heat transfer at edges not captured in 1D constructions.

## Quality Checks

1. **Material Existence**: All materials in constructions must be defined.

2. **Property Ranges**: Material properties must be within realistic ranges.

3. **Layer Limits**: Maximum 10 layers in standard constructions.

4. **Window Gas Thickness**: Gas layers typically 6-20mm for optimal performance.

5. **Thermal Resistance**: No negative thermal resistance values allowed.