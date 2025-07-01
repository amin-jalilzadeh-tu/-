# SQL Extraction Gap Analysis

## Overview
This document provides a comprehensive analysis of what data is currently extracted from EnergyPlus SQL files versus what remains unextracted.

## Table-by-Table Analysis

### 1. **ReportData & ReportDataDictionary** ✅ FULLY EXTRACTED
**Currently Extracted:**
- All timeseries data based on variable categories (energy, weather, zones, etc.)
- Variable metadata (names, units, frequencies)
- Filtered by run period and date ranges

**Status:** Complete coverage for timeseries data

### 2. **Time** ✅ FULLY EXTRACTED
**Currently Extracted:**
- Timestamps for all data points
- Date ranges for simulations
- Period information

**Status:** Complete

### 3. **Schedules** ✅ FULLY EXTRACTED
**Currently Extracted:**
- Schedule names, types, min/max values
- Schedule indices for linking

**Status:** Complete

### 4. **Zones** ✅ FULLY EXTRACTED
**Currently Extracted:**
- Zone geometry (area, volume, ceiling height)
- Coordinates (min/max X,Y,Z)
- Multipliers
- Zone indices and names

**Status:** Complete

### 5. **Surfaces** ✅ FULLY EXTRACTED
**Currently Extracted:**
- Surface geometry (area, width, height)
- Orientation (azimuth, tilt)
- Construction assignments
- Surface types and classes

**Status:** Complete

### 6. **Constructions & ConstructionLayers** ⚠️ PARTIALLY EXTRACTED
**Currently Extracted:**
- Basic construction properties (U-values, layers)
- Absorptance values
- Window indicators

**Not Extracted:**
- ConstructionLayers table (material layer ordering)
- Detailed layer-by-layer properties

**Gap:** Layer sequencing information

### 7. **Materials** ✅ FULLY EXTRACTED
**Currently Extracted:**
- Thermal properties (conductivity, density, specific heat)
- Thickness
- Various absorptances

**Status:** Complete

### 8. **ComponentSizes** ✅ FULLY EXTRACTED
**Currently Extracted:**
- Equipment types and names
- Design capacities
- Flow rates
- Sizing values with units

**Status:** Complete

### 9. **ZoneSizes** ❌ NOT EXTRACTED
**Available but Not Extracted:**
- Zone-level design loads
- Design flow rates
- Peak conditions
- Design day information

**Gap:** Complete table unused

### 10. **SystemSizes** ❌ NOT EXTRACTED
**Available but Not Extracted:**
- System-level sizing results
- Peak load types
- Design capacities
- Design volume flows

**Gap:** Complete table unused

### 11. **TabularData** ⚠️ PARTIALLY EXTRACTED
**Currently Extracted:**
- Basic extraction capability exists
- Some energy end-use data
- Some comfort metrics

**Not Fully Utilized:**
- Detailed end-use breakdowns by subcategory
- Peak demand information
- Utility use per area metrics
- HVAC sizing summaries
- Equipment performance ratings
- Envelope summaries
- Lighting summaries
- Outdoor air details
- Sensible heat gain components

**Gap:** Only ~20% of available reports extracted

### 12. **Errors** ✅ FULLY EXTRACTED
**Currently Extracted:**
- Error messages, types, counts
- Warning categorization

**Status:** Complete

### 13. **NominalPeople** ⚠️ PARTIALLY EXTRACTED
**Currently Extracted:**
- Basic occupancy loads
- Zone assignments

**Not Extracted:**
- Activity/clothing schedules
- Comfort calculation parameters
- MRT calculation settings

**Gap:** Comfort-related parameters

### 14. **NominalLighting** ✅ FULLY EXTRACTED
**Currently Extracted:**
- Lighting power densities
- Zone assignments
- Heat gain fractions

**Status:** Complete

### 15. **NominalElectricEquipment** ❌ NOT EXTRACTED
**Available but Not Extracted:**
- Equipment power densities
- Heat gain fractions
- End-use subcategories
- Zone assignments

**Gap:** Complete table unused

### 16. **Other Equipment Tables** ❌ NOT EXTRACTED
- NominalGasEquipment
- NominalSteamEquipment
- NominalHotWaterEquipment
- NominalOtherEquipment
- NominalBaseboardHeaters

**Gap:** All equipment types except electric

### 17. **NominalInfiltration** ❌ NOT EXTRACTED
**Available but Not Extracted:**
- Design infiltration rates
- Zone assignments
- Schedule assignments

**Gap:** Complete table unused

### 18. **NominalVentilation** ❌ NOT EXTRACTED
**Available but Not Extracted:**
- Design ventilation rates
- Zone assignments
- Schedule assignments

**Gap:** Complete table unused

### 19. **EnvironmentPeriods** ⚠️ PARTIALLY EXTRACTED
**Currently Extracted:**
- Used for filtering run periods

**Not Extracted:**
- Environment names and types as standalone data

**Gap:** Environment metadata

### 20. **Simulations** ❌ NOT EXTRACTED
**Available but Not Extracted:**
- EnergyPlus version
- Timesteps per hour
- Completion status
- Timestamps

**Gap:** Simulation metadata

### 21. **Additional Tables Not Extracted:**
- ZoneLists
- ZoneGroups
- ZoneInfoZoneLists
- RoomAirModels
- DaylightMaps & related tables
- ReportExtendedData (min/max values with timestamps)
- StringTypes & Strings (lookup tables)

## Summary Statistics

### Extraction Coverage by Category:

1. **Timeseries Data**: 100% ✅
   - All energy, weather, zone, and system variables

2. **Building Geometry**: 90% ✅
   - Missing: Construction layer details

3. **Material Properties**: 100% ✅
   - All thermal properties extracted

4. **Internal Loads**: 40% ⚠️
   - Have: Lighting, people (partial)
   - Missing: All equipment types, infiltration, ventilation

5. **HVAC Sizing**: 20% ❌
   - Have: Component sizes only
   - Missing: Zone and system sizing results

6. **Performance Summaries**: 20% ❌
   - Have: Basic capability
   - Missing: Most detailed reports from TabularData

7. **Quality Metrics**: 60% ⚠️
   - Have: Errors
   - Missing: Simulation metadata, extended data

## High-Priority Gaps

### 1. **TabularData Deep Extraction**
This table contains the most valuable unextracted data:
- Detailed energy end-use breakdowns
- Peak demand profiles
- Comfort summaries
- Equipment performance metrics
- Building characteristic summaries

### 2. **Zone and System Sizing**
Critical for understanding HVAC design:
- ZoneSizes table
- SystemSizes table

### 3. **Complete Internal Loads**
- All equipment types (gas, steam, hot water, etc.)
- Design infiltration rates
- Design ventilation rates

### 4. **Extended Timeseries Metadata**
- ReportExtendedData (min/max values with exact timestamps)
- Better use of peak occurrence information

### 5. **Simulation Quality Data**
- Simulations table (version, settings)
- Environment period details

## Recommended Implementation Priority

1. **Immediate (High Value, Low Effort)**:
   - ZoneSizes extraction
   - SystemSizes extraction
   - NominalElectricEquipment extraction
   - Simulations metadata

2. **Short-term (High Value, Medium Effort)**:
   - Deep TabularData extraction for all report types
   - Complete equipment loads extraction
   - Infiltration/ventilation design rates

3. **Long-term (Nice to Have)**:
   - Construction layer details
   - Room air model data
   - Daylight mapping results
   - String lookup optimization