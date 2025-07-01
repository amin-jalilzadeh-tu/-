import pandas as pd
import os

# Check the sensitivity_results.parquet file
parquet_file = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/sensitivity_results/sensitivity_results.parquet"

print("=" * 80)
print("ANALYZING SENSITIVITY_RESULTS.PARQUET")
print("=" * 80)

try:
    df = pd.read_parquet(parquet_file)
    
    print(f"\nFile: {os.path.basename(parquet_file)}")
    print(f"Shape: {df.shape}")
    print(f"\nColumns ({len(df.columns)}):")
    for col in df.columns:
        print(f"  - {col}")
    
    print(f"\nData types:")
    print(df.dtypes)
    
    print(f"\nFirst 5 rows:")
    print(df.head())
    
    # Check for simulation output columns
    output_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['electricity', 'cooling', 'heating', 'energy', 'consumption'])]
    if output_cols:
        print(f"\nEnergy/Output columns found ({len(output_cols)}):")
        for col in output_cols[:10]:  # Show first 10
            print(f"  - {col}")
            
    # Check for variant/scenario information
    if 'variant_id' in df.columns:
        print(f"\nNumber of variants: {df['variant_id'].nunique()}")
        print(f"Variant IDs: {sorted(df['variant_id'].unique())[:10]}")  # Show first 10
        
    if 'building_id' in df.columns:
        print(f"\nBuilding IDs: {df['building_id'].unique()}")
        
    # Sample some data for a specific output variable
    if output_cols:
        sample_col = output_cols[0]
        print(f"\nSample data for '{sample_col}':")
        print(df[[col for col in ['variant_id', 'building_id', sample_col] if col in df.columns]].head(10))
        
except Exception as e:
    print(f"Error reading parquet file: {e}")

# Let's also check the example sensitivity_for_surrogate.parquet
example_file = "/mnt/d/Documents/daily/E_Plus_2040_py/_output_example/6f912613-913d-40ea-ba14-eff7e6dc097f/sensitivity_results/sensitivity_for_surrogate.parquet"

print("\n" + "=" * 80)
print("CHECKING EXAMPLE SENSITIVITY_FOR_SURROGATE.PARQUET")
print("=" * 80)

try:
    df_example = pd.read_parquet(example_file)
    
    print(f"\nFile: {os.path.basename(example_file)}")
    print(f"Shape: {df_example.shape}")
    print(f"\nColumns ({len(df_example.columns)}):")
    
    # Group columns by type
    param_cols = [col for col in df_example.columns if col.startswith('param_')]
    output_cols = [col for col in df_example.columns if not col.startswith('param_') and col not in ['variant_id', 'building_id']]
    
    print(f"\nParameter columns ({len(param_cols)}):")
    for col in param_cols[:5]:  # Show first 5
        print(f"  - {col}")
    if len(param_cols) > 5:
        print(f"  ... and {len(param_cols) - 5} more")
        
    print(f"\nOutput columns ({len(output_cols)}):")
    for col in output_cols[:5]:  # Show first 5
        print(f"  - {col}")
    if len(output_cols) > 5:
        print(f"  ... and {len(output_cols) - 5} more")
        
    print(f"\nFirst 3 rows (showing variant_id and first few columns):")
    display_cols = ['variant_id'] + param_cols[:3] + output_cols[:2]
    display_cols = [col for col in display_cols if col in df_example.columns]
    print(df_example[display_cols].head(3))
    
except Exception as e:
    print(f"Error reading example parquet file: {e}")