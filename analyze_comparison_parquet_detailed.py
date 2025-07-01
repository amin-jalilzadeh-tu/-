import pandas as pd
import os

# Check a monthly electricity file
parquet_file = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/parsed_modified_results/comparisons/var_electricity_facility_na_monthly_b4136733.parquet"

print("=" * 80)
print("DETAILED ANALYSIS OF COMPARISON PARQUET FILE")
print("=" * 80)

try:
    df = pd.read_parquet(parquet_file)
    
    print(f"\nFile: {os.path.basename(parquet_file)}")
    print(f"Shape: {df.shape}")
    
    # Show all columns
    print(f"\nAll columns ({len(df.columns)}):")
    for col in df.columns:
        print(f"  - {col}")
    
    # Check if there are variant columns
    variant_cols = [col for col in df.columns if 'variant' in col.lower() or col.startswith('v') and col[1:].isdigit()]
    if variant_cols:
        print(f"\nVariant columns found: {variant_cols}")
    else:
        print("\nNo obvious variant columns found.")
        
    # Check column pattern
    value_cols = [col for col in df.columns if 'value' in col.lower() or col.endswith('_value')]
    if value_cols:
        print(f"\nValue columns: {value_cols}")
        
    # Show first few rows with all columns
    print(f"\nFirst 3 rows (all columns):")
    print(df.head(3))
    
    # Show unique values for non-numeric columns
    non_numeric_cols = df.select_dtypes(include=['object']).columns
    print(f"\nUnique values in non-numeric columns:")
    for col in non_numeric_cols:
        unique_vals = df[col].unique()
        if len(unique_vals) <= 10:
            print(f"  {col}: {unique_vals}")
        else:
            print(f"  {col}: {len(unique_vals)} unique values")
            
except Exception as e:
    print(f"Error: {e}")

# Let's check the timeseries directory for variant data
print("\n" + "=" * 80)
print("CHECKING TIMESERIES DIRECTORY")
print("=" * 80)

timeseries_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/parsed_modified_results/timeseries"
try:
    files = os.listdir(timeseries_dir)
    print(f"Files in timeseries directory: {len(files)}")
    # Show first 10 files
    for f in files[:10]:
        print(f"  - {f}")
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more files")
        
    # Check if there are variant-specific files
    variant_files = [f for f in files if 'variant' in f or '_v' in f]
    if variant_files:
        print(f"\nVariant-specific files found: {len(variant_files)}")
        for f in variant_files[:5]:
            print(f"  - {f}")
            
except Exception as e:
    print(f"Error listing timeseries directory: {e}")

# Check the temp_raw/variants directory
print("\n" + "=" * 80)
print("CHECKING TEMP_RAW/VARIANTS DIRECTORY")
print("=" * 80)

variants_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/parsed_modified_results/temp_raw/variants"
try:
    if os.path.exists(variants_dir):
        files = os.listdir(variants_dir)
        print(f"Files in variants directory: {len(files)}")
        # Show first 10 files
        for f in files[:10]:
            print(f"  - {f}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more files")
            
        # Check one variant file if exists
        if files:
            sample_file = os.path.join(variants_dir, files[0])
            if sample_file.endswith('.parquet'):
                print(f"\nChecking sample variant file: {files[0]}")
                df_variant = pd.read_parquet(sample_file)
                print(f"Shape: {df_variant.shape}")
                print(f"Columns: {list(df_variant.columns)[:10]}")  # First 10 columns
    else:
        print("Variants directory does not exist")
        
except Exception as e:
    print(f"Error: {e}")