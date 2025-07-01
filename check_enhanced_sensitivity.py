import pandas as pd
import os

# Check the enhanced_sensitivity.csv file
csv_file = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/enhanced_sensitivity.csv"

print("=" * 80)
print("ANALYZING ENHANCED SENSITIVITY CSV FILE")
print("=" * 80)

try:
    df = pd.read_csv(csv_file)
    
    print(f"\nFile: {os.path.basename(csv_file)}")
    print(f"Shape: {df.shape}")
    print(f"\nColumns ({len(df.columns)}):")
    for col in df.columns:
        print(f"  - {col}")
    
    print(f"\nData types:")
    print(df.dtypes)
    
    print(f"\nFirst 5 rows:")
    print(df.head())
    
    # Check if this contains simulation results
    value_columns = [col for col in df.columns if 'value' in col.lower() or 'result' in col.lower()]
    if value_columns:
        print(f"\nValue/Result columns found: {value_columns}")
        
    # Check for variant information
    if 'variant' in df.columns or 'variant_id' in df.columns:
        variant_col = 'variant' if 'variant' in df.columns else 'variant_id'
        print(f"\nNumber of variants: {df[variant_col].nunique()}")
        
except Exception as e:
    print(f"Error reading CSV file: {e}")

# Also check the example calibration_parameters.csv
example_csv = "/mnt/d/Documents/daily/E_Plus_2040_py/_output_example/6f912613-913d-40ea-ba14-eff7e6dc097f/sensitivity_results/calibration_parameters.csv"

print("\n" + "=" * 80)
print("CHECKING EXAMPLE CALIBRATION_PARAMETERS.CSV")
print("=" * 80)

try:
    df_example = pd.read_csv(example_csv)
    
    print(f"\nFile: {os.path.basename(example_csv)}")
    print(f"Shape: {df_example.shape}")
    print(f"\nColumns ({len(df_example.columns)}):")
    for col in df_example.columns:
        print(f"  - {col}")
    
    print(f"\nFirst 3 rows:")
    print(df_example.head(3))
    
except Exception as e:
    print(f"Error reading example CSV file: {e}")