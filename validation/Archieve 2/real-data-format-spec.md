# Real Data Format Specification for EnergyPlus Validation

## Overview
This document specifies the required format for real/measured data to validate EnergyPlus simulation results. The format supports multiple structures while ensuring compatibility with parsed simulation outputs.

## 1. Supported File Formats

### 1.1 CSV Format
- **Encoding**: UTF-8 (required)
- **Delimiter**: Comma (,)
- **Header**: Required on first row
- **Extension**: `.csv`

### 1.2 Parquet Format
- **Compression**: Snappy (default) or uncompressed
- **Extension**: `.parquet`
- **Schema**: Must match CSV structure

## 2. Data Structure Options

### Option A: Wide Format (Dates as Columns)
Best for: Small datasets, Excel exports, daily/monthly data

```csv
BuildingID,VariableName,01/01,01/02,01/03,...,12/31
4136737,Electricity:Facility [J](Daily),1234567,1234568,1234569,...,1234567
4136737,Heating:EnergyTransfer [J](Daily),2345678,2345679,2345680,...,2345678
```

**Advantages**: Easy to create in Excel, compact for daily data
**Note**: Date columns can be in various formats (see Section 3.4)

### Option B: Long Format (Normalized)
Best for: Large datasets, databases, hourly/sub-hourly data

```csv
BuildingID,VariableName,DateTime,Value
4136737,Electricity:Facility [J](Daily),2020-01-01,1234567
4136737,Electricity:Facility [J](Daily),2020-01-02,1234568
```

**Advantages**: Efficient for large datasets, database-friendly

### Option C: Zone-Level Format
Best for: Detailed analysis, zone-level validation

```csv
BuildingID,Zone,VariableName,DateTime,Value
4136737,Zone1,Zone Air Temperature [C](Hourly),2020-01-01 01:00:00,20.5
4136737,Zone2,Zone Air Temperature [C](Hourly),2020-01-01 01:00:00,21.0
```

**Advantages**: Preserves zone-level detail, matches simulation structure

## 3. Required Fields

### 3.1 Building Identification
- **Field Name**: `BuildingID` (required)
- **Type**: Integer or String
- **Examples**: `4136737`, `"building_001"`
- **Note**: Must match simulation building IDs exactly

### 3.2 Variable Identification
- **Field Name**: `VariableName` or `Variable`
- **Type**: String
- **Format**: Preferably include units and frequency
- **Examples**: 
  - `Electricity:Facility [J](Daily)`
  - `Total_Electricity_kWh`
  - `Zone Mean Air Temperature`

### 3.3 Date/Time Fields

#### For Wide Format:
Date columns should use one of these formats consistently:
- `MM/DD` → `01/31`, `12/25`
- `M/D` → `1/31`, `12/5`
- `MM/DD/YYYY` → `01/31/2020`
- `YYYY-MM-DD` → `2020-01-31`
- `DD/MM/YYYY` → `31/01/2020` (requires configuration flag)

#### For Long Format:
- **Field Name**: `DateTime` or `Date` or `Timestamp`
- **Formats Accepted**:
  ```
  2020-01-01 13:00:00   # Space separator
  2020-01-01T13:00:00   # ISO 8601
  01/31/2020 13:00:00   # US format
  2020-01-01            # Date only (assumes 00:00:00)
  ```

### 3.4 Value Field
- **Field Name**: `Value` (long format) or date columns (wide format)
- **Type**: Numeric (float or integer)
- **Missing Data**: Empty string, `NaN`, `null`, or `NA`
- **Units**: Must be specified in variable name or metadata

### 3.5 Optional Fields

#### Zone Identification
- **Field Name**: `Zone` or `ZoneName`
- **Type**: String
- **Use**: When providing zone-level data

#### Units
- **Field Name**: `Units`
- **Type**: String
- **Examples**: `J`, `kWh`, `W`, `C`

#### Data Quality
- **Field Name**: `Quality` or `Flag`
- **Type**: String/Integer
- **Use**: Mark questionable data

## 4. Energy Units Specification

### 4.1 Supported Energy Units
| Unit | Symbol | Conversion to Joules |
|------|--------|---------------------|
| Joules | J | 1 |
| Kilojoules | kJ | 1,000 |
| Megajoules | MJ | 1,000,000 |
| Kilowatt-hours | kWh | 3,600,000 |
| Therms | therm | 105,480,000 |
| British Thermal Units | BTU | 1,055.06 |
| Million BTU | MMBTU | 1,055,060,000 |

### 4.2 Unit Declaration
Units MUST be declared using one of these methods:

1. **In Variable Name** (Recommended):
   ```
   Electricity:Facility [kWh](Daily)
   Heating Energy (MJ)
   ```

2. **In Metadata File**:
   ```json
   {
     "units": {
       "energy": "kWh",
       "power": "kW",
       "temperature": "C"
     }
   }
   ```

3. **In Units Column**:
   ```csv
   BuildingID,VariableName,DateTime,Value,Units
   4136737,Electricity:Facility,2020-01-01,45.2,kWh
   ```

## 5. Variable Naming Convention

### 5.1 Standard EnergyPlus Variable Names
Use these exact names when possible:

**Energy Variables:**
- `Electricity:Facility [J](Daily)`
- `Heating:EnergyTransfer [J](Daily)`
- `Cooling:EnergyTransfer [J](Daily)`
- `InteriorLights:Electricity [J](Daily)`
- `InteriorEquipment:Electricity [J](Daily)`
- `Gas:Facility [J](Daily)`

**Temperature Variables:**
- `Zone Mean Air Temperature [C](Hourly)`
- `Site Outdoor Air Drybulb Temperature [C](Hourly)`

### 5.2 Custom Variable Names
If using custom names, provide mapping configuration:
```json
{
  "variable_mappings": {
    "Total_Elec_kWh": "Electricity:Facility [J](Daily)",
    "Heating_Gas_Therm": "Heating:Gas [J](Daily)",
    "Indoor_Temp_F": "Zone Mean Air Temperature [C](Hourly)"
  }
}
```

## 6. Time Resolution Requirements

### 6.1 Supported Frequencies
- **Timestep**: Simulation timestep (e.g., 10-min, 15-min)
- **Hourly**: 24 values per day
- **Daily**: 1 value per day
- **Monthly**: 1 value per month

### 6.2 Timestamp Alignment
- **Hourly**: Beginning of hour (01:00 = data for 01:00-02:00)
- **Daily**: Beginning of day (2020-01-01 = data for entire day)
- **Monthly**: First day of month

### 6.3 Missing Data
- Maximum allowed gaps: 10% of time period
- Gaps larger than 24 hours should be documented

## 7. Data Aggregation Rules

### 7.1 Zone to Building Aggregation
When aggregating zones to building level:

**Energy Variables**: Sum across zones
```
Building_Total = Sum(All_Zone_Values)
```

**Temperature Variables**: Area-weighted average
```
Building_Avg = Sum(Zone_Value × Zone_Area) / Sum(Zone_Areas)
```

**Power Variables**: Sum for total, average for density
```
Total_Power = Sum(Zone_Powers)
Power_Density = Total_Power / Total_Area
```

### 7.2 Time Aggregation
When aggregating to coarser time resolution:

**Energy**: Sum over time period
**Power/Rate**: Average over time period
**Temperature**: Average over time period

## 8. Example Files

### 8.1 Minimal Daily Wide Format
```csv
BuildingID,VariableName,01/01,01/02,01/03,01/04,01/05
4136737,Electricity:Facility [kWh](Daily),45.2,47.8,46.3,44.9,46.1
4136737,Heating:Gas [therm](Daily),12.5,13.3,11.7,10.2,11.8
```

### 8.2 Hourly Long Format with Units
```csv
BuildingID,VariableName,DateTime,Value,Units
4136737,Electricity:Facility,2020-01-01 00:00,5.2,kW
4136737,Electricity:Facility,2020-01-01 01:00,5.1,kW
4136737,Zone Mean Air Temperature,2020-01-01 00:00,68.5,F
```

### 8.3 Zone-Level with Metadata
```csv
BuildingID,Zone,VariableName,DateTime,Value,Units,Quality
4136737,Core_Zone,Zone Air Temperature,2020-01-01,21.2,C,Good
4136737,Perimeter_1,Zone Air Temperature,2020-01-01,20.8,C,Good
4136737,ALL,Electricity:Facility,2020-01-01,245.6,kWh,Good
```

## 9. Configuration File

### 9.1 Minimal Configuration
```json
{
  "real_data": {
    "path": "measured_data.csv",
    "format": "auto"
  },
  "units": {
    "energy": "kWh"
  }
}
```

### 9.2 Complete Configuration
```json
{
  "real_data": {
    "path": "measured_data.csv",
    "format": "wide",
    "date_parsing": {
      "formats": ["MM/DD", "MM/DD/YYYY"],
      "dayfirst": false
    }
  },
  "units": {
    "energy": "kWh",
    "power": "kW", 
    "temperature": "F"
  },
  "variable_mappings": {
    "Total_Electricity": "Electricity:Facility [J](Daily)",
    "Heating_Energy": "Heating:EnergyTransfer [J](Daily)"
  },
  "building_mappings": {
    "Bldg_A": "4136737",
    "Bldg_B": "4136738"
  },
  "aggregation": {
    "zones_to_building": true,
    "method": "sum"
  },
  "quality_filtering": {
    "remove_outliers": true,
    "outlier_sigma": 4
  }
}
```

## 10. Validation Checklist

Before using your data file, verify:

- [ ] Building IDs match simulation IDs exactly
- [ ] Variable names are consistent throughout file
- [ ] Units are clearly specified
- [ ] Date format is consistent
- [ ] No zeros used for missing data
- [ ] Leap year handled correctly (366 vs 365 days)
- [ ] Time zones documented if relevant
- [ ] File encoding is UTF-8
- [ ] Values are in expected ranges

## 11. Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Unit mismatch errors | Ensure units are declared; check kWh vs J |
| Date parsing errors | Use consistent format; specify in config |
| Missing building IDs | Verify IDs match simulation exactly |
| Zero values for missing | Use empty/NaN instead of 0 |
| Timezone issues | Convert to simulation timezone |
| Leap year mismatch | Include/exclude Feb 29 as needed |

## 12. Support for Legacy Formats

The validation system can handle legacy formats with configuration:

**Fixed-width format:**
```json
{
  "format": "fixed",
  "column_specs": {
    "BuildingID": [0, 10],
    "DateTime": [11, 25],
    "Value": [26, 35]
  }
}
```

**Excel files:**
Convert to CSV first, or use pandas to read and save as CSV/Parquet.

## 13. Performance Recommendations

- **< 1 GB**: CSV is fine
- **1-10 GB**: Use Parquet format
- **> 10 GB**: Use Parquet with partitioning by building or date
- **Hourly data**: Consider daily aggregation for faster validation
- **Many buildings**: Consider parallel processing configuration