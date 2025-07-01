# Outputs Configuration Parsing Documentation

## Overview
The outputs parsing module extracts output variable definitions and reporting configurations from IDF files. These objects control what data EnergyPlus writes to various output files during simulation.

## IDF Objects Parsed

### 1. OUTPUT:VARIABLE
Requests specific output variables.

**Parameters Extracted:**
- `key_value`: Key Value (specific object name or "*" for all)
- `variable_name`: Variable Name (e.g., "Zone Mean Air Temperature")
- `reporting_frequency`: Reporting Frequency (Timestep, Hourly, Daily, Monthly, RunPeriod, Annual)
- Schedule Name (optional, for conditional output)

**Example:**
```
Output:Variable,*,Zone Mean Air Temperature,Hourly;
Output:Variable,West Zone,Zone Air Relative Humidity,Timestep;
```

### 2. OUTPUT:METER
Requests meter outputs (energy by fuel type/end use).

**Parameters Extracted:**
- `meter_name`: Meter Name (e.g., "Electricity:Facility", "InteriorLights:Electricity")
- `reporting_frequency`: Reporting Frequency

**Common Meters:**
- Electricity:Facility, Electricity:Building, Electricity:HVAC
- NaturalGas:Facility, NaturalGas:Building, NaturalGas:HVAC
- InteriorLights:Electricity, ExteriorLights:Electricity
- Cooling:Electricity, Heating:NaturalGas
- Fans:Electricity, Pumps:Electricity

### 3. OUTPUT:METER:METERFILEONLY
Meter output only to meter file (not SQL).

**Parameters Extracted:**
- Meter Name
- Reporting Frequency

### 4. OUTPUT:METER:CUMULATIVE
Cumulative meter values.

**Parameters Extracted:**
- Meter Name
- Reporting Frequency

### 5. OUTPUT:METER:CUMULATIVE:METERFILEONLY
Cumulative meter only to meter file.

**Parameters Extracted:**
- Meter Name
- Reporting Frequency

### 6. OUTPUT:TABLE:SUMMARYREPORTS
Predefined summary reports.

**Parameters Extracted:**
- `report_name`: Report Name(s)

**Common Reports:**
- AllSummary (includes all reports)
- AnnualBuildingUtilityPerformanceSummary
- InputVerificationandResultsSummary
- DemandEndUseComponentsSummary
- SourceEnergyEndUseComponentsSummary
- ClimaticDataSummary
- EnvelopeSummary
- EquipmentSummary
- HVACSizingSummary
- SystemSummary
- ComponentSizingSummary
- OutdoorAirSummary
- ObjectCountSummary

### 7. OUTPUT:TABLE:MONTHLY
Custom monthly reports.

**Parameters Extracted:**
- `table_name`: Name
- Digits After Decimal
- Variable or Meter Name / Aggregation Type pairs

**Aggregation Types:**
- SumOrAverage, Maximum, Minimum
- ValueWhenMaximumOrMinimum
- HoursNonZero, HoursZero
- HoursPositive, HoursNegative
- HoursInRange (requires min/max)

### 8. OUTPUT:TABLE:TIMEBINS
Time bin reports for frequency analysis.

**Parameters Extracted:**
- Key Value
- Variable Name
- Interval Start
- Interval Size
- Interval Count
- Schedule Name (optional)
- Variable Type (Energy/Demand)

### 9. OUTPUT:TABLE:ANNUAL
Annual reports with min/max/custom aggregation.

**Parameters Extracted:**
- Name
- Filter (optional)
- Schedule Name (optional)
- Variable/Aggregation/Units triplets

### 10. OUTPUT:SQLITE
Controls SQLite output file creation.

**Parameters Extracted:**
- `option_type`: Option Type (SimpleAndTabular, Simple)
- Unit Conversion for Tabular Data (None, JtoKWH, JtoMJ, JtoGJ, InchPound)

### 11. OUTPUTCONTROL:TABLE:STYLE
Format for tabular reports.

**Parameters Extracted:**
- `column_separator`: Column Separator (Comma, Tab, Fixed, HTML, XML)
- Unit Conversion (None, JtoKWH, JtoMJ, JtoGJ, InchPound)
- Include Table of Contents (Yes/No)

### 12. OUTPUT:SURFACES:DRAWING
DXF file output for geometry visualization.

**Parameters Extracted:**
- Report Type (DXF, DXF:WireFrame)
- Report Specifications 1 (Triangulate3DFace, ThickPolyline)
- Report Specifications 2 (RegularPolyline)

### 13. OUTPUT:SURFACES:LIST
Surface details report.

**Parameters Extracted:**
- Report Type (Lines, Vertices, Details, DetailsWithVertices, CostInfo)
- Report Specifications (IDF)

### 14. OUTPUT:SCHEDULES
Schedule values output.

**Parameters Extracted:**
- Key Field (Hourly, Timestep)
- Output as (CSV, IDF)

### 15. OUTPUT:CONSTRUCTIONS
Construction properties report.

**Parameters Extracted:**
- Output Type (Constructions, Materials, Constructions and Materials)

### 16. OUTPUT:ENERGYMANAGEMENTSYSTEM
EMS debug output.

**Parameters Extracted:**
- Actuator Availability Dictionary Reporting (None, NotByUniqueKeyNames, Verbose)
- Internal Variable Availability Dictionary Reporting
- EMS Runtime Language Debug Output Level (None, ErrorsOnly, Verbose)

### 17. OUTPUT:DIAGNOSTICS
Diagnostic outputs for debugging.

**Parameters Extracted:**
- Key 1, Key 2, etc.

**Common Keys:**
- DisplayAllWarnings
- DisplayExtraWarnings
- DisplayUnusedSchedules
- DisplayUnusedObjects
- DisplayAdvancedReportVariables
- DisplayZoneAirHeatBalanceOffBalance
- DoNotMirrorDetachedShading
- ReportDuringWarmup

### 18. OUTPUT:VARIABLEDICTIONARY
Variable dictionary output format.

**Parameters Extracted:**
- Key Field (IDF, Regular)
- Sort Option (Name, Ascending, Descending)

### 19. OUTPUTCONTROL:REPORTINGTOLERANCES
Tolerance for reporting unmet hours.

**Parameters Extracted:**
- Tolerance for Time Heating Setpoint Not Met (°C)
- Tolerance for Time Cooling Setpoint Not Met (°C)

### 20. OUTPUTCONTROL:FILES
Control which output files are generated.

**Parameters Extracted:**
- Output CSV (Yes/No)
- Output MTR (Yes/No)
- Output ESO (Yes/No)
- Output EIO (Yes/No)
- Output Tabular (Yes/No)
- Output SQLite (Yes/No)
- Output JSON (Yes/No)
- Output AUDIT (Yes/No)
- Output Zone Sizing (Yes/No)
- Output System Sizing (Yes/No)
- Output DXF (Yes/No)
- Output BND (Yes/No)
- Output RDD (Yes/No)
- Output MDD (Yes/No)
- Output MTD (Yes/No)
- Output END (Yes/No)
- Output SHD (Yes/No)

## Key Metrics Calculated

1. **Total Output Variables**
   - Count of requested output variables
   - Breakdown by reporting frequency

2. **Total Meters**
   - Count of requested meters
   - Energy tracking categories

3. **Reporting Frequencies**
   - Distribution of timestep vs hourly vs daily reporting

4. **Output Tables**
   - List of summary reports requested
   - Custom report definitions

## Output Structure

### IDF Data Output
```
parsed_data/
└── idf_data/
    └── building_{id}/
        └── outputs_all.parquet
```

**Columns in outputs_all.parquet:**
- building_id
- object_type
- key_value (for variables)
- variable_or_meter_name
- reporting_frequency
- report_specifications
- output_control_settings

### Impact on SQL Output
These objects determine what data appears in:
- Timeseries tables (ReportVariableData)
- Summary tables (TabularDataWithStrings)
- Energy meter tables

## Data Processing Notes

1. **Wildcard Usage**: Key Value "*" applies to all applicable objects.

2. **Frequency Impact**: Higher frequency = larger output files.

3. **Variable Availability**: Not all variables available for all objects.

4. **Meter Hierarchy**: Facility > Building > Zone > System > Equipment.

5. **Report Combinations**: Some reports include others (e.g., AllSummary).

## Common Output Configurations

### Minimal Output
```
Output:Variable,*,Zone Mean Air Temperature,Monthly;
Output:Meter,Electricity:Facility,Monthly;
Output:Table:SummaryReports,AnnualBuildingUtilityPerformanceSummary;
```

### Detailed Analysis
```
Output:Variable,*,Zone Mean Air Temperature,Hourly;
Output:Variable,*,Zone Air Relative Humidity,Hourly;
Output:Variable,*,Zone Windows Total Transmitted Solar Radiation Rate,Hourly;
Output:Meter,Electricity:*,Hourly;
Output:Table:SummaryReports,AllSummary;
```

### Debugging Configuration
```
Output:Variable,*,*,Timestep;  # All variables at timestep
Output:Diagnostics,DisplayAllWarnings,DisplayAdvancedReportVariables;
Output:EnergyManagementSystem,Verbose,Verbose,Verbose;
```

## Performance Considerations

### File Size Impact
- Timestep reporting: ~100-1000x larger than monthly
- Each variable adds ~8KB/year at hourly resolution
- SQL files can exceed several GB with detailed output

### Simulation Speed Impact
- Minor impact from output writing
- SQL writing slightly slower than CSV
- Excessive outputs can slow post-processing

## Quality Checks

1. **Variable Existence**: Verify requested variables exist for objects.

2. **Meter Validity**: Check meter names match EnergyPlus conventions.

3. **Frequency Selection**: Balance detail needs with file size.

4. **Report Selection**: Avoid redundant report requests.

5. **Output File Control**: Disable unneeded file formats.

## Best Practices

1. **Start Minimal**: Begin with monthly output, increase as needed.

2. **Use Meters**: For energy totals, meters are more efficient than summing variables.

3. **Targeted Output**: Specify key values instead of wildcards when possible.

4. **Summary Reports**: Use predefined reports for standard metrics.

5. **Custom Reports**: Create monthly/annual tables for specific KPIs.

## Troubleshooting

### Missing Output
- Check variable spelling exactly matches EnergyPlus names
- Verify object exists (key value)
- Ensure output frequency isn't too coarse

### Large Files
- Reduce reporting frequency
- Limit variables to essential ones
- Use meters instead of individual equipment variables

### Performance Issues
- Avoid timestep reporting for annual simulations
- Disable unneeded output files
- Use binary formats (SQL) over text (CSV) for large data