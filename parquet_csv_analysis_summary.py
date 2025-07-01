"""
Summary of Parquet and CSV Files Analysis for Calibration

Author: Assistant
Date: 2025-07-01
"""

import pandas as pd
import os

print("=" * 80)
print("SUMMARY: PARQUET AND CSV FILES FOR CALIBRATION")
print("=" * 80)

print("\n1. PARQUET FILES IN parsed_modified_results/comparisons/")
print("-" * 50)
print("Location: output/e0e23b56-96a2-44b9-9936-76c15af196fb/parsed_modified_results/comparisons/")
print("\nStructure of var_electricity_facility_na_monthly_b4136733.parquet:")
print("- Shape: (365, 7)")
print("- Columns: timestamp, building_id, Zone, variable_name, category, Units, base_value")
print("- Contains: Daily electricity consumption data for building 4136733")
print("- Time period: 2013 full year")
print("- Values: Energy consumption in Joules")
print("\nNote: These files contain BASE simulation results only, not variant results.")

print("\n2. CSV FILES IN sensitivity_results/")
print("-" * 50)
print("Location: output/e0e23b56-96a2-44b9-9936-76c15af196fb/sensitivity_results/")
print("\nsensitivity_parameters.csv:")
print("- Shape: (41, 13)")
print("- Purpose: Parameter definitions for calibration")
print("- Contains: parameter names, sensitivity scores, min/max values, calibration priority")
print("- Key columns: parameter, sensitivity_score, min_value, max_value, calibration_priority")

print("\n3. MODIFICATION DATA")
print("-" * 50)
print("Location: output/e0e23b56-96a2-44b9-9936-76c15af196fb/modified_idfs/")
print("\nmodifications_detail_wide_*.parquet:")
print("- Shape: (47, 28)")
print("- Contains: Parameter values for all 19 variants")
print("- Columns: building_id, category, object_type, field, original, variant_0...variant_18")
print("- Purpose: Shows exact parameter values used in each variant simulation")

print("\n4. DATA SUITABLE FOR CALIBRATION")
print("-" * 50)
print("\nFor calibration workflows, you need to combine:")
print("1. Parameter values from modifications_detail_wide.parquet")
print("2. Simulation outputs from parsed results (need to be extracted per variant)")
print("3. Parameter definitions from sensitivity_parameters.csv")

print("\n5. RECOMMENDATIONS")
print("-" * 50)
print("To use these files for calibration:")
print("1. The modifications_detail_wide.parquet contains input parameter values for each variant")
print("2. Simulation outputs for each variant need to be extracted from Modified_Sim_Results")
print("3. Create a consolidated dataset with columns: variant_id, param_1, param_2, ..., output_1, output_2, ...")
print("4. Use calibration algorithms to find optimal parameter values that match measured data")

print("\n6. EXAMPLE WORKFLOW")
print("-" * 50)
print("# Read parameter values")
print("params_df = pd.read_parquet('modifications_detail_wide.parquet')")
print("# Transform to long format with variant_id, parameter columns")
print("# Read simulation outputs for each variant")
print("# Merge parameters with outputs")
print("# Apply calibration algorithm (e.g., optimization, Bayesian calibration)")

print("\n" + "=" * 80)