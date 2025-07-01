# SQL Extraction Clarification

## What Remains UNCHANGED

### 1. **Timeseries Data Extraction** ✅ NO CHANGES NEEDED
- **Current Coverage**: Already extracting ALL timeseries data from ReportData/ReportDataDictionary
- **Structure**: Wide format parquet files remain the same
- **Files**: 
  - `timeseries/base_all_daily.parquet`
  - `timeseries/base_all_monthly.parquet`
  - Modified results comparisons in `comparisons/`

**Note**: The only minor addition could be extracting ReportExtendedData for peak timestamps, but the core timeseries extraction is complete.

### 2. **Modification Tracking** ✅ NO CHANGES NEEDED
- **Current Coverage**: Already tracking all modifications
- **Files**:
  - `modifications_summary_*.parquet`
  - `modifications_detail_wide_*.parquet`
  - `modifications_detail_long_*.parquet`
- **Comparisons**: Already comparing base vs variants for all variables

## What Gets ADDED (New Extractions)

### 1. **Static Performance Summaries** (from TabularData)
```
performance_summaries/
├── energy_end_uses.parquet         # Annual totals by end use
├── peak_demands.parquet            # Peak power demands
├── comfort_metrics.parquet         # Unmet hours, comfort violations
└── energy_intensity.parquet        # Energy per m²
```

### 2. **Design/Sizing Information** (from sizing tables)
```
sizing_results/
├── zone_sizing.parquet            # Design loads per zone
├── system_sizing.parquet          # HVAC system capacities
└── component_sizing.parquet       # Equipment design sizes
```

### 3. **Building Static Properties** (enhanced extraction)
```
building_characteristics/
├── envelope_summary.parquet       # From TabularData envelope reports
├── internal_loads_summary.parquet # From Nominal* tables
└── construction_details.parquet   # From ConstructionLayers
```

### 4. **Quality/Metadata** (from various tables)
```
metadata/
├── simulation_info.parquet        # From Simulations table
├── simulation_errors.parquet      # From Errors table (already extracted)
└── environment_periods.parquet    # From EnvironmentPeriods
```

## Summary

**NO CHANGES to:**
- Timeseries extraction (ReportData) - already complete
- Modification tracking - already complete
- Comparison structures - already complete

**ADD ONLY:**
- Static summaries from TabularData (~80% unutilized)
- Design/sizing data (completely missing)
- Enhanced building characteristics
- Additional metadata

The core timeseries and modification workflows remain untouched. We're just adding the missing static/summary data that EnergyPlus pre-calculates for us.