# Equipment Modifications System

## Overview
The equipment modification system handles all equipment-related parameters in EnergyPlus IDF files, including electric equipment, fuel equipment, hot water equipment, steam equipment, and other equipment types. This system is crucial for modeling plug loads and process equipment energy consumption.

## Modified Object Types
- `ELECTRICEQUIPMENT` - Electric equipment/plug loads
- `FUELEQUIPMENT` - Fuel-based equipment
- `HOTWAREREQUIPMENT` - Hot water consuming equipment
- `STEAMEQUIPMENT` - Steam consuming equipment
- `OTHEREQUIPMENT` - Other equipment types

## Parameters Modified

### ELECTRICEQUIPMENT Object Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `design_level` | Design Level | 4 | float | W | - | plug_loads |
| `watts_per_area` | Watts per Zone Floor Area | 5 | float | W/m² | 0.0-50.0 | plug_loads |
| `watts_per_person` | Watts per Person | 6 | float | W/person | 0.0-500.0 | plug_loads |
| `fraction_latent` | Fraction Latent | 7 | float | - | 0.0-1.0 | zone_loads |
| `fraction_radiant` | Fraction Radiant | 8 | float | - | 0.0-1.0 | zone_loads |
| `fraction_lost` | Fraction Lost | 9 | float | - | 0.0-1.0 | zone_loads |

### FUELEQUIPMENT Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `fuel_type` | Fuel Type | 10 | str | - | See allowed values | fuel_use |

**Allowed Fuel Types**: Electricity, NaturalGas, PropaneGas, FuelOilNo1, FuelOilNo2, Coal, Diesel, Gasoline, OtherFuel1, OtherFuel2

## Modification Strategies

### 1. Efficient Equipment (`efficient_equipment`)
- **Purpose**: Simulate general equipment efficiency improvements
- **Modifications**:
  - Reduces equipment power by 15-30%
  - Power reduction factor randomly selected within range
  - Applied based on calculation method:
    - EquipmentLevel: Modifies Design Level
    - Watts/Area: Modifies Watts per Zone Floor Area
    - Watts/Person: Modifies Watts per Person

### 2. Energy Star Standards (`energy_star`)
- **Purpose**: Apply Energy Star certified equipment standards
- **Modifications**:
  - Reduces equipment power by 20-50%
  - Represents typical Energy Star savings
  - Higher reduction range than general efficient equipment
  - Applied to active calculation method parameters

### 3. Plug Load Reduction (`plug_load_reduction`)
- **Purpose**: Implement smart power strips and control strategies
- **Modifications**:
  - Reduces equipment power by 10-25%
  - Reduces Fraction Lost by 30-50%
  - Represents:
    - Smart power strips eliminating standby power
    - Automated controls turning off unused equipment
    - Better equipment management practices
  - Two-pronged approach:
    1. Direct power reduction (10-25%)
    2. Waste heat reduction (30-50% of Fraction Lost)

## Process Flow

### 1. Parameter Identification
```
Equipment Object → Identify Calculation Method (Field 3)
                → Locate Active Power Parameter
                → Find Heat Fraction Parameters
```

### 2. Value Modification
```
Current Value → Apply Reduction Factor → New Value
              → Update Parameter Value
              → Update Numeric Value
              → Create Modification Record
```

### 3. Calculation Method Logic
- **EquipmentLevel**: Modifies Design Level (W)
- **Watts/Area**: Modifies Watts per Zone Floor Area (W/m²)
- **Watts/Person**: Modifies Watts per Person (W/person)

## Integration Notes

### Relationship with Other Systems
- **Schedules**: Equipment schedules control operational hours
- **HVAC**: Equipment heat gains affect cooling loads
- **Ventilation**: Equipment density may affect ventilation requirements

### Common Use Cases
1. **Office Buildings**: Plug load reduction strategies
2. **Data Centers**: High-efficiency IT equipment
3. **Retail**: Energy Star appliances and equipment
4. **Healthcare**: Medical equipment efficiency improvements

### Performance Impact
- **Energy Savings**: 10-50% reduction in equipment energy use
- **Cooling Load Reduction**: Proportional to power and heat fraction reductions
- **Peak Demand**: Significant reduction potential with smart controls

## Technical Implementation Details

### Field Index Reference
- Field 0: Name
- Field 1: Zone or Zone List Name
- Field 2: Schedule Name
- Field 3: Design Level Calculation Method
- Fields 4-6: Power parameters (only one active based on method)
- Fields 7-9: Heat fraction parameters

### Validation Requirements
- Ensure calculation method matches modified parameter
- Verify heat fractions sum to ≤ 1.0
- Check power values remain positive
- Validate fuel type strings for FUELEQUIPMENT

### Error Handling
- Skip modification if calculation method not recognized
- Maintain original value if reduction would result in negative
- Log warnings for missing numeric values
- Handle missing or invalid fuel types gracefully