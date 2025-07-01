# EnergyPlus SQL Database Tables - Additional Data Extraction Opportunities

## Overview
The EnergyPlus SQL database contains numerous tables beyond timeseries data that provide valuable information for analysis. This document outlines what additional data could be extracted and how it would be useful for the analysis pipeline.

## 1. TabularData Table
**What it contains:**
- Pre-calculated summary reports from EnergyPlus
- Annual Building Utility Performance Summary
- Equipment Summary Reports
- HVAC Sizing Summary
- Zone Summary Reports
- Energy consumption breakdowns by end-use

**Available data structure:**
- ReportName: Type of report (e.g., "AnnualBuildingUtilityPerformanceSummary")
- TableName: Specific table within report (e.g., "End Uses", "Comfort and Setpoint Not Met Summary")
- RowName: Row identifier (e.g., "Heating", "Cooling", "Lighting")
- ColumnName: Column identifier (e.g., "Electricity [kWh]", "Natural Gas [kWh]")
- Value: The actual value
- Units: Units of measurement

**Use cases:**
- Quick access to annual energy consumption by end-use without processing timeseries
- Unmet hours and thermal comfort metrics
- Peak demand values
- Utility cost summaries
- Validate surrogate model predictions against EnergyPlus summaries

## 2. ComponentSizes Table
**What it contains:**
- Equipment sizing information for all HVAC components
- Design capacities for heating/cooling equipment
- Design flow rates for fans and pumps
- Sizing criteria and methods used

**Available data structure:**
- CompType: Component type (e.g., "Coil:Cooling:DX:SingleSpeed")
- CompName: Component name
- Description: What is being sized (e.g., "Design Size Gross Rated Total Cooling Capacity")
- Value: Sized value
- Units: Units (W, m3/s, etc.)

**Use cases:**
- Extract equipment capacities for cost estimation
- Analyze oversizing/undersizing patterns
- Correlate equipment sizes with energy consumption
- Input features for surrogate models predicting equipment requirements

## 3. SystemSizes Table
**What it contains:**
- HVAC system-level sizing results
- System airflow rates
- System heating/cooling capacities
- Supply air temperatures

**Use cases:**
- System-level performance analysis
- Validate HVAC system design assumptions
- Identify potential efficiency improvements

## 4. ZoneSizes Table
**What it contains:**
- Zone-level HVAC sizing information
- Zone heating/cooling loads
- Zone airflow requirements
- Design day conditions

**Use cases:**
- Zone-by-zone load analysis
- Identify critical zones driving system sizing
- Thermal zoning optimization

## 5. Zones Table
**What it contains:**
- Zone geometry information
- Floor areas and volumes
- Zone multipliers
- Bounding box coordinates (min/max X,Y,Z)
- Ceiling heights

**Available data structure:**
- ZoneName: Name of the zone
- Area: Floor area (m²)
- Volume: Zone volume (m³)
- CeilingHeight: Average ceiling height
- Coordinates: Bounding box dimensions

**Use cases:**
- Calculate building total floor area and volume
- Geometry-based features for surrogate models
- Space efficiency metrics (volume/area ratios)
- Zoning pattern analysis

## 6. Surfaces Table
**What it contains:**
- Detailed information about every surface in the model
- Surface areas, orientations (azimuth, tilt)
- Construction assignments
- Boundary conditions
- Window-to-wall ratios can be calculated

**Available data structure:**
- SurfaceName: Surface identifier
- Area: Surface area (m²)
- Azimuth: Orientation angle
- Tilt: Tilt angle (0=horizontal, 90=vertical)
- ConstructionIndex: Link to construction assembly
- ClassName: Surface type (Wall, Window, Floor, etc.)

**Use cases:**
- Calculate facade areas by orientation
- Window-to-wall ratio calculations
- Envelope area for heat transfer analysis
- Orientation-based solar exposure analysis

## 7. Constructions Table
**What it contains:**
- Construction assembly definitions
- Number of layers
- Overall U-values
- Surface properties (absorptance, roughness)

**Available data structure:**
- Name: Construction name
- TotalLayers: Number of material layers
- Uvalue: Overall thermal transmittance
- TypeIsWindow: Boolean for fenestration

**Use cases:**
- Envelope thermal performance metrics
- Identify construction types for retrofit analysis
- Correlate U-values with energy consumption

## 8. Materials Table
**What it contains:**
- Thermal properties of all materials
- Conductivity, density, specific heat
- Thickness for each material
- Surface properties (roughness, absorptance)

**Available data structure:**
- Name: Material name
- Thickness: Material thickness (m)
- Conductivity: Thermal conductivity (W/m-K)
- Density: Material density (kg/m³)
- SpecificHeat: Specific heat capacity (J/kg-K)

**Use cases:**
- Calculate thermal mass of building
- Material-based retrofit options
- Thermal resistance calculations
- Parametric material optimization

## 9. Schedules Table
**What it contains:**
- All schedule definitions used in the model
- Schedule types and limits
- Links schedules to their usage

**Available data structure:**
- ScheduleName: Schedule identifier
- ScheduleType: Type of schedule
- ScheduleMinimum/Maximum: Value limits

**Use cases:**
- Identify operating patterns
- Schedule optimization opportunities
- Occupancy pattern analysis

## 10. Errors Table
**What it contains:**
- Simulation warnings and errors
- Error counts and types
- Diagnostic information

**Available data structure:**
- ErrorMessage: Description of the issue
- ErrorType: Severity level
- Count: Number of occurrences

**Use cases:**
- Quality control for simulation results
- Identify common modeling issues
- Flag potentially unreliable results

## 11. NominalPeople Table
**What it contains:**
- Occupancy design loads by zone
- Number of people
- Activity levels
- Heat gain fractions

**Available data structure:**
- ZoneIndex: Zone identifier
- NumberOfPeople: Design occupancy
- Activity and heat gain parameters

**Use cases:**
- Occupancy density calculations
- Internal gain analysis
- Occupancy-based energy metrics

## 12. NominalLighting Table
**What it contains:**
- Lighting design loads by zone
- Lighting power density
- Heat gain fractions
- Schedule assignments

**Available data structure:**
- ZoneIndex: Zone identifier
- DesignLevel: Lighting power (W)
- Fractions for heat distribution

**Use cases:**
- Lighting power density (W/m²) calculations
- Lighting energy analysis
- Heat gain from lighting

## Integration with Current Pipeline

### Immediate Value Additions:
1. **Building Characteristics**: Extract total floor area, volume, and envelope area from Zones and Surfaces tables
2. **Equipment Sizing**: Use ComponentSizes for HVAC capacity features
3. **Annual Summaries**: Use TabularData for validation and quick metrics
4. **Construction Performance**: Extract U-values and material properties

### Enhanced Features for Surrogate Models:
```python
# Example feature engineering from SQL tables
features = {
    'total_floor_area': zones_df['Area'].sum(),
    'total_volume': zones_df['Volume'].sum(),
    'avg_ceiling_height': zones_df['CeilingHeight'].mean(),
    'total_envelope_area': surfaces_df[surfaces_df['ClassName'].isin(['Wall', 'Roof'])]['Area'].sum(),
    'window_area': surfaces_df[surfaces_df['ClassName'] == 'Window']['Area'].sum(),
    'window_wall_ratio': window_area / wall_area,
    'avg_wall_uvalue': constructions_df[constructions_df['TypeIsWindow'] == 0]['Uvalue'].mean(),
    'total_cooling_capacity': component_sizes_df[component_sizes_df['CompType'].str.contains('Cooling')]['Value'].sum(),
    'lighting_power_density': nominal_lighting_df['DesignLevel'].sum() / total_floor_area
}
```

### Validation Metrics:
- Compare surrogate predictions against TabularData summaries
- Use Errors table to flag problematic simulations
- Validate geometry calculations against Zones/Surfaces data

This additional data would significantly enhance the analysis capabilities and provide more comprehensive features for surrogate modeling while also enabling better validation and quality control.