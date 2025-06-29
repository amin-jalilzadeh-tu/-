# Baseline Validation Issues Summary

## Investigation Results

### Issue 1: "Electricity:Facility [J](Hourly)" Not Mapping to "Electricity:Facility"

**Status: This is NOT the actual issue**

The semantic mapping is working correctly:
- Measured variable: `Electricity:Facility [J](Hourly)`
- Simulation variable: `Electricity:Facility`
- After normalization, both become: `electricity_facility`
- The mapping logic successfully matches these variables

The error message about Electricity:Facility not being found is misleading - it's actually being mapped correctly, but the validation fails at the date alignment stage.

### Issue 2: "No overlapping dates for building 4136733" 

**Status: This is the REAL issue**

The date mismatch is causing all validations to fail:
- **Baseline simulation data**: 2013-01-02 to 2014-01-01
- **Measured data**: 2020-01-01 to 2020-12-31
- **Result**: No overlapping dates, so validation cannot proceed

### Root Cause

The baseline simulation was run with:
- Weather file: Likely for 2013-2014
- Simulation period: 2013-2014

But the measured data being used for validation is from 2020.

## Solutions

### Option 1: Re-run Baseline Simulation for 2020 (Recommended)
- Update the weather file to use 2020 data
- Update simulation run period to 2020
- This will ensure proper date alignment

### Option 2: Use Year-Agnostic Date Matching
- Modify the validation code to match by month/day only, ignoring year
- This assumes seasonal patterns are similar across years
- Less accurate but could work for rough validation

### Option 3: Provide 2013-2014 Measured Data
- Replace the current measured data file with data from 2013-2014
- This requires historical measured data availability

## Code Locations

1. **Date alignment logic**: `validation/smart_validation_wrapper.py`, line ~1400-1461
2. **Wide-to-long conversion**: `validation/smart_validation_wrapper.py`, line ~528-574
3. **Variable mapping**: Working correctly at line ~1156-1216

## Verification

The baseline parquet files show:
- Data exists for building 4136733
- Variable "Electricity:Facility" is present
- Values are populated (e.g., 6399384.98 J for 2013-01-02)

The issue is purely the year mismatch between simulation (2013-2014) and measured data (2020).