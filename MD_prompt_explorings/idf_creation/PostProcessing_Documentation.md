# Post-Processing Module Documentation

## Overview
The Post-Processing module consolidates EnergyPlus simulation outputs from multiple buildings into unified datasets for analysis. It handles various time formats, aggregation methods, and data structures to create analysis-ready outputs.

## Module: merge_results.py

### Purpose
Merges individual building simulation CSV outputs into consolidated wide-format CSV files, enabling comparative analysis across multiple buildings and variables.

### Key Functions

#### 1. parse_datetime()
Handles various EnergyPlus datetime formats:
- `MM/DD HH:MM:SS` → Assumes current year
- `MM/DD` → Date only (for daily data)
- `YYYY-MM-DD HH:MM:SS` → Full datetime
- Special handling for `24:00:00` → Converts to `00:00:00` next day

#### 2. aggregate_to_periods()
Aggregates hourly data to coarser time periods:
- **Hourly**: No aggregation
- **Daily**: Groups by date
- **Monthly**: Groups by year-month

Supports multiple aggregation methods:
- `sum`: Total over period
- `mean`: Average over period  
- `max`: Maximum value in period
- `min`: Minimum value in period

#### 3. merge_all_results()
Main consolidation function that:
1. Finds all simulation output CSVs
2. Reads and parses each file
3. Extracts building ID from filename
4. Pivots data to wide format
5. Merges all buildings together

### Input Data Structure

**Individual Building CSV** (from EnergyPlus):
```csv
Date/Time,Environment:Site Outdoor Air Drybulb Temperature [C](TimeStep),THERMAL ZONE 1:Zone Mean Air Temperature [C](TimeStep)
01/01  00:15:00,2.5,20.1
01/01  00:30:00,2.4,20.0
...
```

### Processing Steps

1. **File Discovery**:
   - Searches for `simulation_*.csv` or `*.csv` in output directory
   - Extracts building ID from filename pattern

2. **Data Reading**:
   - Reads CSV with proper encoding handling
   - Parses datetime column with format detection
   - Handles missing or malformed data

3. **Time Period Aggregation**:
   ```python
   if period == 'daily':
       df['Date'] = df['Datetime'].dt.date
       df_grouped = df.groupby('Date').agg(agg_method)
   elif period == 'monthly':
       df['Month'] = df['Datetime'].dt.to_period('M')
       df_grouped = df.groupby('Month').agg(agg_method)
   ```

4. **Wide Format Transformation**:
   ```python
   # From: Multiple rows per building/time
   # To: One row per time, columns for each building/variable
   df_wide = df_melted.pivot_table(
       index='Datetime',
       columns=['BuildingID', 'VariableName'],
       values='Value'
   )
   ```

### Output Data Structure

**Consolidated Wide Format CSV**:
```csv
Datetime,Building1_Zone Air Temperature,Building1_Electric Demand,Building2_Zone Air Temperature,Building2_Electric Demand
2024-01-01 00:00:00,20.1,1500.5,19.8,1600.2
2024-01-01 01:00:00,20.0,1450.3,19.7,1550.8
...
```

### Configuration Options

```python
merge_all_results(
    output_dir='path/to/outputs',
    output_file='merged_results.csv',
    period='hourly',        # 'hourly', 'daily', 'monthly'
    agg_method='sum',       # 'sum', 'mean', 'max', 'min'
    sep=','                 # CSV separator
)
```

### Error Handling

1. **Missing Files**: Skips if no CSV files found
2. **Parsing Errors**: Logs warnings for unparseable dates
3. **Empty Data**: Handles buildings with no data gracefully
4. **Encoding Issues**: Tries multiple encodings (utf-8, latin-1)

### Performance Considerations

- **Memory Usage**: Loads all data into memory
- **Large Datasets**: Consider chunking for very large simulations
- **Time Complexity**: O(n*m) where n=timesteps, m=buildings

### Integration with Analysis

Output feeds into:
1. **Calibration Scripts**: Compare simulated vs measured
2. **Visualization Tools**: Time series plots, heatmaps
3. **Statistical Analysis**: Building performance metrics
4. **Report Generation**: Automated summary creation

### Example Usage

```python
# Basic usage - hourly data
merge_all_results(
    output_dir='simulation_outputs/',
    output_file='all_buildings_hourly.csv'
)

# Daily aggregation with sum
merge_all_results(
    output_dir='simulation_outputs/',
    output_file='all_buildings_daily.csv',
    period='daily',
    agg_method='sum'
)

# Monthly averages
merge_all_results(
    output_dir='simulation_outputs/',
    output_file='all_buildings_monthly_avg.csv',
    period='monthly',
    agg_method='mean'
)
```

### Output Files

1. **Hourly Merged**: Full resolution time series
2. **Daily Aggregated**: Daily totals/averages
3. **Monthly Summary**: Monthly statistics
4. **Variable Inventory**: List of all tracked variables

### Best Practices

1. **Consistent Naming**: Use standard building ID formats
2. **Output Selection**: Limit variables in IDF to reduce file size
3. **Aggregation Choice**: 
   - Energy: Use 'sum'
   - Temperature: Use 'mean'
   - Peak demands: Use 'max'
4. **Time Zone Handling**: Ensure consistent time zones
5. **Data Validation**: Check merged data against individual files