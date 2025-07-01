# SQL Static Data Extraction Documentation

## Overview
The SQL static extraction module extracts non-timeseries summary data from EnergyPlus SQL output files. This includes performance summaries, sizing results, building characteristics, and simulation metadata that complement the timeseries data.

## Data Categories Extracted

### 1. Performance Summaries
Located in `performance_summaries/` directory.

#### Energy End Uses (`energy_end_uses.parquet`)
Extracted from multiple summary tables:
- **By Fuel Type**: Electricity, Natural Gas, District Cooling, District Heating, etc.
- **By End Use**: Heating, Cooling, Interior Lighting, Exterior Lighting, Interior Equipment, Exterior Equipment, Fans, Pumps, Heat Rejection, Humidification, Heat Recovery, Water Systems, Refrigeration, Generators
- **Metrics**: Annual consumption, peak demand, cost (if available)

#### Site and Source Energy (`site_source_energy.parquet`)
- Total Site Energy (kWh)
- Net Site Energy  
- Total Source Energy
- Net Source Energy
- Site-to-Source conversion factors

#### Comfort and Setpoint Not Met (`comfort_summary.parquet`)
- Time Setpoint Not Met During Occupied Heating (hr)
- Time Setpoint Not Met During Occupied Cooling (hr)
- Time Setpoint Not Met During Occupied (hr)
- Time Not Comfortable Based on Simple ASHRAE 55-2004 (hr)

#### Utility Use Per Conditioned Floor Area (`energy_intensity.parquet`)
- Energy Use Intensity (EUI) by fuel type (kWh/m²)
- Peak demand intensity (W/m²)

### 2. Sizing Results
Located in `sizing_results/` directory.

#### Zone Sizing (`zone_sizing.parquet`)
For each zone:
- User Design Load (W) - heating and cooling
- User Design Air Flow (m³/s) - heating and cooling
- Calculated Design Load (W)
- Calculated Design Air Flow (m³/s)
- Design Day Name
- Time of Peak Load
- Temperature at Peak (°C)
- Humidity Ratio at Peak (kg/kg)
- Outside Temperature at Peak (°C)

#### System Sizing (`system_sizing.parquet`)
For each air loop:
- Design Supply Air Flow Rate (m³/s)
- Calculated Cooling/Heating Design Air Flow (m³/s)
- User Cooling/Heating Design Capacity (W)
- Calculated Cooling/Heating Design Capacity (W)
- Central Cooling/Heating Design Supply Air Temperature (°C)
- Central Cooling/Heating Design Supply Air Humidity Ratio

#### Component Sizing (`component_sizing.parquet`)
For each sized component:
- Component Type and Name
- Description of Sizing
- Value (with units)
- Units
- Sizing Method (e.g., "Capacity", "Flow", "Area")

### 3. Building Characteristics
Located in `building_characteristics/` directory.

#### Zone Information (`zone_information.parquet`)
From Zones and ZoneInfoZoneLists tables:
- Zone Name
- Floor Area (m²)
- Volume (m³)
- Ceiling Height (m)
- Net Wall Area (m²)
- Window Area (m²)
- Window-Wall Ratio (%)
- Zone List assignments

#### Surface Details (`surface_details.parquet`)
From Surfaces table:
- Surface Name and Type
- Construction
- Area (m²) and Net Area
- Azimuth and Tilt
- Zone Name
- Outside Boundary Condition
- Window-Wall Ratio (for exterior walls)

#### Construction Properties (`construction_properties.parquet`)
From Constructions, ConstructionLayers, and Materials tables:
- Construction Name
- Layer sequence with materials
- Material properties:
  - Thickness (m)
  - Conductivity (W/m-K)
  - Density (kg/m³)
  - Specific Heat (J/kg-K)
  - R-Value (m²-K/W)
- Total R-Value and U-Factor

#### Nominal Equipment Loads (`equipment_loads.parquet`)
From NominalElectricEquipment, NominalGasEquipment, etc.:
- Zone Name
- Equipment Type
- Design Level (W)
- Power Density (W/m²)
- Schedule Name
- Fraction Radiant/Latent/Lost

#### Nominal Infiltration (`infiltration_nominal.parquet`)
From NominalInfiltration table:
- Zone Name
- Design Flow Rate (m³/s)
- Flow per Exterior Area (m³/s-m²)
- Air Changes per Hour
- Schedule Name
- Model Coefficients

#### Nominal Ventilation (`ventilation_nominal.parquet`)
From NominalVentilation table:
- Zone Name
- Outdoor Air Method
- Design Flow Rate (m³/s)
- Flow per Person/Area
- Schedule Name

### 4. Metadata
Located in `metadata/` directory.

#### Simulation Information (`simulation_info.parquet`)
From SimulationControl and related tables:
- EnergyPlus Version
- Timestamp of simulation
- Weather file used
- Number of timesteps per hour
- Simulation periods

#### Environment Periods (`environment_periods.parquet`)
From EnvironmentPeriods table:
- Environment Name and Type
- Start/End dates
- Total hours simulated

#### Errors and Warnings (`errors_warnings.parquet`)
From Errors table:
- Error Type (Warning, Severe, Fatal)
- Count
- Message
- Additional details

### 5. Additional Reports
Located in `detailed_reports/` directory.

#### Tabular Reports (`tabular_reports.parquet`)
From TabularDataWithStrings table:
- Report Name
- Table Name
- Row/Column Labels
- Values
- Units

## SQL Tables Accessed

The extractor queries these main SQL tables:
- TabularDataWithStrings (summary reports)
- Zones
- Surfaces  
- Constructions, ConstructionLayers, Materials
- NominalElectricEquipment, NominalGasEquipment, etc.
- NominalInfiltration, NominalVentilation
- ComponentSizes
- SystemSizes
- Errors
- EnvironmentPeriods
- SimulationControl

## Output Structure

```
parsed_data/
├── performance_summaries/
│   ├── energy_end_uses.parquet
│   ├── site_source_energy.parquet
│   ├── comfort_summary.parquet
│   └── energy_intensity.parquet
├── sizing_results/
│   ├── zone_sizing.parquet
│   ├── system_sizing.parquet
│   └── component_sizing.parquet
├── building_characteristics/
│   ├── zone_information.parquet
│   ├── surface_details.parquet
│   ├── construction_properties.parquet
│   ├── equipment_loads.parquet
│   ├── infiltration_nominal.parquet
│   └── ventilation_nominal.parquet
├── metadata/
│   ├── simulation_info.parquet
│   ├── environment_periods.parquet
│   └── errors_warnings.parquet
└── detailed_reports/
    └── tabular_reports.parquet
```

## Integration with Parsing Workflow

The static extraction is controlled by the `sql_static` flag in parse_types:

```python
parse_types = {
    "idf": True,
    "sql": True,      # Timeseries extraction
    "sql_static": True # Static data extraction
}
```

When enabled, static extraction runs after timeseries extraction and takes 2-5 seconds per SQL file.

## Data Processing Notes

1. **Unit Handling**: Data is stored in SI units with unit information preserved

2. **Missing Tables**: Gracefully handles missing tables (not all simulations have all tables)

3. **Multi-Building**: Properly tracks building_id for each record

4. **Null Values**: Handles SQL NULL values appropriately

5. **Data Types**: Preserves numeric vs. string types from SQL

## Use Cases

1. **Model Validation**: Compare sizing results with design documents

2. **Energy Analysis**: Detailed breakdown of energy use by end use

3. **Comfort Assessment**: Identify zones with comfort issues

4. **Envelope Analysis**: Window-wall ratios, construction properties

5. **Troubleshooting**: Review errors and warnings from simulation

## Quality Checks

1. **Data Completeness**: Verify expected tables are present

2. **Value Ranges**: Check for reasonable values (e.g., positive areas)

3. **Consistency**: Cross-check between related tables

4. **Building Totals**: Sum of zones should match building totals

5. **Error Review**: Check for severe errors or warnings

## Performance Optimization

1. **Batch Queries**: Extracts all data in single connection

2. **Selective Extraction**: Only processes tables that exist

3. **Efficient Storage**: Parquet format for fast retrieval

4. **Memory Management**: Processes large tables in chunks if needed

5. **Parallel Processing**: Can process multiple SQL files concurrently