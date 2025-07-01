import pandas as pd
import os

# Define paths
parquet_file = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/parsed_modified_results/comparisons/var_electricity_facility_na_monthly_b4136733.parquet"
csv_file = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/sensitivity_results/sensitivity_parameters.csv"

print("=" * 80)
print("ANALYZING PARQUET FILE")
print("=" * 80)

# Read the parquet file
try:
    df_parquet = pd.read_parquet(parquet_file)
    
    print(f"\nFile: {os.path.basename(parquet_file)}")
    print(f"Shape: {df_parquet.shape}")
    print(f"\nColumns ({len(df_parquet.columns)}):")
    for col in df_parquet.columns:
        print(f"  - {col}")
    
    print(f"\nData types:")
    print(df_parquet.dtypes)
    
    print(f"\nFirst 5 rows:")
    print(df_parquet.head())
    
    print(f"\nBasic statistics:")
    print(df_parquet.describe())
    
    # Check for unique values in key columns
    if 'building_id' in df_parquet.columns:
        print(f"\nUnique building IDs: {df_parquet['building_id'].unique()}")
    
    if 'variant_id' in df_parquet.columns:
        print(f"\nUnique variant IDs: {sorted(df_parquet['variant_id'].unique())}")
        
    if 'month' in df_parquet.columns:
        print(f"\nUnique months: {sorted(df_parquet['month'].unique())}")
        
except Exception as e:
    print(f"Error reading parquet file: {e}")

print("\n" + "=" * 80)
print("ANALYZING CSV FILE FOR CALIBRATION")
print("=" * 80)

# Read the CSV file
try:
    df_csv = pd.read_csv(csv_file)
    
    print(f"\nFile: {os.path.basename(csv_file)}")
    print(f"Shape: {df_csv.shape}")
    print(f"\nColumns ({len(df_csv.columns)}):")
    for col in df_csv.columns:
        print(f"  - {col}")
    
    print(f"\nData types:")
    print(df_csv.dtypes)
    
    print(f"\nFirst 5 rows:")
    print(df_csv.head())
    
    # Check if this file contains parameter definitions
    if 'parameter' in df_csv.columns or 'parameter_name' in df_csv.columns:
        print("\nThis appears to be a parameter definition file for calibration.")
        
except Exception as e:
    print(f"Error reading CSV file: {e}")

# Also check for other CSV files in sensitivity_results
print("\n" + "=" * 80)
print("OTHER CSV FILES IN SENSITIVITY_RESULTS")
print("=" * 80)

sensitivity_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/sensitivity_results"
csv_files = [f for f in os.listdir(sensitivity_dir) if f.endswith('.csv')]
print(f"Found {len(csv_files)} CSV files:")
for f in csv_files:
    print(f"  - {f}")