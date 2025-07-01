"""
SQL Extraction Coverage Summary
Shows what's currently extracted vs available
"""

# Define all SQL tables and their extraction status
sql_tables = {
    # Timeseries Tables
    "ReportData": {"status": "✅ FULL", "usage": "All timeseries data"},
    "ReportDataDictionary": {"status": "✅ FULL", "usage": "Variable metadata"},
    "Time": {"status": "✅ FULL", "usage": "Timestamps"},
    "ReportExtendedData": {"status": "❌ NONE", "usage": "Min/max values with timestamps"},
    
    # Building Geometry
    "Zones": {"status": "✅ FULL", "usage": "Zone geometry, volumes, areas"},
    "Surfaces": {"status": "✅ FULL", "usage": "Surface geometry, orientations"},
    "Constructions": {"status": "✅ FULL", "usage": "Construction properties, U-values"},
    "ConstructionLayers": {"status": "❌ NONE", "usage": "Layer ordering"},
    "Materials": {"status": "✅ FULL", "usage": "Material thermal properties"},
    
    # Internal Loads
    "NominalPeople": {"status": "⚠️ PARTIAL", "usage": "Basic occupancy, missing comfort params"},
    "NominalLighting": {"status": "✅ FULL", "usage": "Lighting power densities"},
    "NominalElectricEquipment": {"status": "❌ NONE", "usage": "Electric equipment loads"},
    "NominalGasEquipment": {"status": "❌ NONE", "usage": "Gas equipment loads"},
    "NominalSteamEquipment": {"status": "❌ NONE", "usage": "Steam equipment loads"},
    "NominalHotWaterEquipment": {"status": "❌ NONE", "usage": "Hot water equipment"},
    "NominalOtherEquipment": {"status": "❌ NONE", "usage": "Other equipment"},
    "NominalBaseboardHeaters": {"status": "❌ NONE", "usage": "Baseboard heaters"},
    "NominalInfiltration": {"status": "❌ NONE", "usage": "Design infiltration rates"},
    "NominalVentilation": {"status": "❌ NONE", "usage": "Design ventilation rates"},
    
    # HVAC Sizing
    "ComponentSizes": {"status": "✅ FULL", "usage": "Equipment capacities"},
    "ZoneSizes": {"status": "❌ NONE", "usage": "Zone design loads and flows"},
    "SystemSizes": {"status": "❌ NONE", "usage": "System design capacities"},
    
    # Performance Summaries
    "TabularData": {"status": "⚠️ PARTIAL", "usage": "~20% extracted, contains 150+ reports"},
    
    # Other
    "Schedules": {"status": "✅ FULL", "usage": "Schedule definitions"},
    "Errors": {"status": "✅ FULL", "usage": "Warnings and errors"},
    "Simulations": {"status": "❌ NONE", "usage": "Simulation metadata"},
    "EnvironmentPeriods": {"status": "⚠️ PARTIAL", "usage": "Used for filtering only"},
    
    # Rarely Used
    "ZoneLists": {"status": "❌ NONE", "usage": "Zone groupings"},
    "ZoneGroups": {"status": "❌ NONE", "usage": "Zone group definitions"},
    "ZoneInfoZoneLists": {"status": "❌ NONE", "usage": "Zone list mappings"},
    "RoomAirModels": {"status": "❌ NONE", "usage": "Air model settings"},
    "DaylightMaps": {"status": "❌ NONE", "usage": "Daylight calculations"},
    "StringTypes": {"status": "❌ NONE", "usage": "String lookups"},
    "Strings": {"status": "❌ NONE", "usage": "String values"},
}

# Calculate statistics
total_tables = len(sql_tables)
fully_extracted = sum(1 for t in sql_tables.values() if t["status"] == "✅ FULL")
partially_extracted = sum(1 for t in sql_tables.values() if t["status"] == "⚠️ PARTIAL")
not_extracted = sum(1 for t in sql_tables.values() if t["status"] == "❌ NONE")

print("SQL TABLE EXTRACTION COVERAGE SUMMARY")
print("=" * 60)
print(f"Total SQL Tables: {total_tables}")
print(f"Fully Extracted: {fully_extracted} ({fully_extracted/total_tables*100:.1f}%)")
print(f"Partially Extracted: {partially_extracted} ({partially_extracted/total_tables*100:.1f}%)")
print(f"Not Extracted: {not_extracted} ({not_extracted/total_tables*100:.1f}%)")
print()

# Group by category
print("\nBY CATEGORY:")
print("-" * 60)

categories = {
    "Timeseries Data": ["ReportData", "ReportDataDictionary", "Time", "ReportExtendedData"],
    "Building Geometry": ["Zones", "Surfaces", "Constructions", "ConstructionLayers", "Materials"],
    "Internal Loads": [k for k in sql_tables.keys() if k.startswith("Nominal")],
    "HVAC Sizing": ["ComponentSizes", "ZoneSizes", "SystemSizes"],
    "Performance Reports": ["TabularData"],
    "Metadata": ["Schedules", "Errors", "Simulations", "EnvironmentPeriods"],
}

for category, tables in categories.items():
    extracted = sum(1 for t in tables if sql_tables[t]["status"] == "✅ FULL")
    partial = sum(1 for t in tables if sql_tables[t]["status"] == "⚠️ PARTIAL")
    total = len(tables)
    print(f"\n{category}:")
    print(f"  Coverage: {extracted}/{total} full, {partial}/{total} partial")
    for table in tables:
        print(f"    {table}: {sql_tables[table]['status']} - {sql_tables[table]['usage']}")

# High-value missing data
print("\n\nHIGH-VALUE MISSING DATA:")
print("-" * 60)
high_value_missing = [
    ("TabularData (full extraction)", "150+ pre-calculated reports including energy end-uses, peak demands, comfort metrics"),
    ("ZoneSizes", "Zone design loads, airflows, peak conditions"),
    ("SystemSizes", "System capacities and design flows"),
    ("NominalElectricEquipment", "Electric equipment power densities"),
    ("NominalInfiltration/Ventilation", "Design infiltration and ventilation rates"),
    ("ReportExtendedData", "Peak values with exact timestamps"),
]

for table, description in high_value_missing:
    print(f"\n{table}:")
    print(f"  {description}")