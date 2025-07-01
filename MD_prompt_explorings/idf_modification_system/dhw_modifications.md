# DHW (Domestic Hot Water) Modifications System

## Overview
The DHW modification system handles all domestic hot water-related parameters in EnergyPlus IDF files, including water heaters, water use equipment, and associated piping and pumping systems.

## Modified Object Types
- `WATERHEATER:MIXED` - Standard mixed tank water heaters
- `WATERHEATER:STRATIFIED` - Stratified tank water heaters
- `WATERUSE:EQUIPMENT` - Water-using fixtures and equipment
- `WATERUSE:CONNECTIONS` - Connections between water use and supply
- `PLANTLOOP` - Hot water plant loops
- `PUMP:VARIABLESPEED` - Variable speed circulation pumps
- `PUMP:CONSTANTSPEED` - Constant speed circulation pumps
- `PIPE:ADIABATIC` - Adiabatic (no heat loss) pipes
- `PIPE:INDOOR` - Indoor piping with heat loss
- `PIPE:OUTDOOR` - Outdoor piping with heat loss

## Parameters Modified

### WATERHEATER:MIXED Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `tank_volume` | Tank Volume | 1 | float | m³ | 0.1-10.0 | dhw_capacity |
| `setpoint_temperature_schedule` | Setpoint Temperature Schedule Name | 2 | str | - | - | dhw_energy |
| `deadband_temperature` | Deadband Temperature Difference | 3 | float | ΔC | 0.5-10.0 | dhw_cycling |
| `heater_capacity` | Heater Maximum Capacity | 6 | float | W | 1000-50000 | dhw_power |
| `heater_efficiency` | Heater Thermal Efficiency | 11 | float | - | 0.5-0.99 | dhw_efficiency |
| `off_cycle_loss_coefficient` | Off Cycle Loss Coefficient to Ambient Temperature | 25 | float | W/K | 0.0-10.0 | dhw_standby_loss |
| `peak_flow_rate` | Peak Use Flow Rate | 30 | float | m³/s | 0.0-0.01 | dhw_sizing |

### WATERUSE:EQUIPMENT Parameters

| Parameter | Field Name | Field Index | Data Type | Units | Range | Impact |
|-----------|------------|-------------|-----------|--------|--------|---------|
| `use_flow_rate` | Peak Flow Rate | 4 | float | m³/s | 0.0-0.001 | dhw_demand |

## Modification Strategies

### 1. Efficiency Upgrade (`efficiency_upgrade`)
- **Purpose**: Improve water heater efficiency and reduce standby losses
- **Modifications**:
  - Increases Heater Thermal Efficiency by 10-20%
  - Reduces Off Cycle Loss Coefficient by 20-40%
  - Maximum efficiency capped at 0.99
  - Simulates improved insulation and burner technology

### 2. Low Flow Fixtures (`low_flow`)
- **Purpose**: Reduce hot water consumption through efficient fixtures
- **Modifications**:
  - Reduces Peak Flow Rate in WATERUSE:EQUIPMENT by 20-40%
  - Simulates installation of low-flow showerheads, faucets, etc.
  - Maintains adequate flow for functionality

### 3. Heat Pump Conversion (`heat_pump_conversion`)
- **Purpose**: Convert to high-efficiency heat pump water heater
- **Modifications**:
  - Multiplies Heater Thermal Efficiency by 2.5
  - Simulates COP (Coefficient of Performance) of 2-3
  - Maximum efficiency capped at 0.99
  - Note: Simplified approach - actual heat pumps would be modeled differently

## Process Flow

1. **Parameter Extraction**:
   - Identifies DHW-related objects in parsed IDF
   - Extracts current values for efficiency, flow rates, and losses
   - Maps parameters to their exact field positions

2. **Value Modification**:
   - Applies strategy-specific improvements
   - Validates new values against physical constraints
   - Ensures efficiency values remain below 1.0

3. **System Integration**:
   - Maintains connections between water heaters and use equipment
   - Preserves plant loop configurations
   - Updates related pump and pipe parameters if needed

## Output Structure

Each modification produces a result containing:
```json
{
  "building_id": "string",
  "variant_id": "string", 
  "category": "dhw",
  "object_type": "WATERHEATER:MIXED",
  "object_name": "string",
  "zone_name": "string",
  "parameter": "parameter_key",
  "field_name": "EnergyPlus field name",
  "original_value": "numeric",
  "new_value": "numeric",
  "strategy": "strategy_name",
  "timestamp": "ISO timestamp"
}
```

## Integration Notes

- DHW systems interact with space heating in some configurations
- Efficiency changes affect gas/electric consumption
- Flow rate changes impact both water and energy use
- Heat pump conversions may require electrical system considerations
- Standby losses affect 24/7 energy consumption

## Performance Impact

- **Direct Effects**:
  - Reduces water heating energy (gas or electric)
  - Reduces water consumption
  - Reduces standby energy losses

- **Indirect Effects**:
  - Less heat gain to conditioned spaces (may increase heating loads)
  - Reduced water/sewer costs
  - Peak demand reduction for electric water heaters

## Typical Energy Savings

- **Efficiency Upgrade**: 10-20% reduction in water heating energy
- **Low Flow Fixtures**: 20-40% reduction in hot water use
- **Heat Pump Conversion**: 50-70% reduction in water heating energy
- **Combined Measures**: Up to 80% reduction possible