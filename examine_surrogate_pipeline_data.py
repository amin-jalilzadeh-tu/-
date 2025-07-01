import pandas as pd
import os

# Base directory for surrogate pipeline data
base_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/surrogate_pipeline_export/20250701_074531"

print("=" * 80)
print("EXAMINING ELECTRICITY FACILITY DATA FROM SURROGATE PIPELINE")
print("=" * 80)

# Check electricity facility data
elec_file = os.path.join(base_dir, "1_inputs/comparison_outputs/electricity_facility_na.parquet")
try:
    df_elec = pd.read_parquet(elec_file)
    
    print(f"\nElectricity Facility Data:")
    print(f"Shape: {df_elec.shape}")
    print(f"Columns: {list(df_elec.columns)}")
    
    # Check for variant columns
    variant_cols = [col for col in df_elec.columns if 'variant' in col.lower() or col.startswith('v') and any(c.isdigit() for c in col)]
    if variant_cols:
        print(f"\nVariant columns found ({len(variant_cols)}): {variant_cols[:5]}...")
        
    print(f"\nFirst 3 rows (subset of columns):")
    display_cols = list(df_elec.columns)[:10]
    print(df_elec[display_cols].head(3))
    
except Exception as e:
    print(f"Error reading electricity file: {e}")

print("\n" + "=" * 80)
print("EXAMINING MODIFICATIONS DATA")
print("=" * 80)

# Check modifications data
mod_file = os.path.join(base_dir, "1_inputs/modifications_wide.parquet")
try:
    df_mod = pd.read_parquet(mod_file)
    
    print(f"\nModifications Wide Data:")
    print(f"Shape: {df_mod.shape}")
    print(f"Columns: {list(df_mod.columns)}")
    
    # Show variant columns
    variant_cols = [col for col in df_mod.columns if col.startswith('variant_')]
    print(f"\nVariant columns ({len(variant_cols)}): {variant_cols}")
    
    print(f"\nFirst 3 rows of parameter modifications:")
    display_cols = ['building_id', 'category', 'object_type', 'field', 'original'] + variant_cols[:3]
    display_cols = [col for col in display_cols if col in df_mod.columns]
    print(df_mod[display_cols].head(3))
    
except Exception as e:
    print(f"Error reading modifications file: {e}")

print("\n" + "=" * 80)
print("EXAMINING ALIGNED DATA FOR TRAINING")
print("=" * 80)

# Check aligned data
aligned_file = os.path.join(base_dir, "3_preprocessing/aligned_data.parquet")
try:
    df_aligned = pd.read_parquet(aligned_file)
    
    print(f"\nAligned Data (ready for calibration/training):")
    print(f"Shape: {df_aligned.shape}")
    print(f"Columns ({len(df_aligned.columns)}):")
    
    # Categorize columns
    param_cols = [col for col in df_aligned.columns if col.startswith('param_')]
    output_cols = [col for col in df_aligned.columns if any(keyword in col for keyword in ['electricity', 'cooling', 'heating', 'energy'])]
    
    print(f"\nParameter columns ({len(param_cols)}):")
    for col in param_cols[:5]:
        print(f"  - {col}")
    if len(param_cols) > 5:
        print(f"  ... and {len(param_cols) - 5} more")
        
    print(f"\nOutput columns ({len(output_cols)}):")
    for col in output_cols[:5]:
        print(f"  - {col}")
    if len(output_cols) > 5:
        print(f"  ... and {len(output_cols) - 5} more")
        
    print(f"\nFirst 3 rows (sample columns):")
    sample_cols = ['variant_id', 'building_id'] + param_cols[:2] + output_cols[:2]
    sample_cols = [col for col in sample_cols if col in df_aligned.columns]
    print(df_aligned[sample_cols].head(3))
    
    # Save a sample as CSV for calibration
    csv_output = "/mnt/d/Documents/daily/E_Plus_2040_py/calibration_data_from_surrogate.csv"
    df_aligned.to_csv(csv_output, index=False)
    print(f"\nSaved aligned data to: {csv_output}")
    print(f"This file contains {df_aligned.shape[0]} rows with parameter values and simulation outputs suitable for calibration.")
    
except Exception as e:
    print(f"Error reading aligned file: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nAvailable data for calibration:")
print("1. Parameter definitions: sensitivity_parameters.csv")
print("2. Base simulation outputs: parsed_modified_results/comparisons/*.parquet")
print("3. Variant parameter values: modifications_wide.parquet") 
print("4. Aligned parameter-output data: aligned_data.parquet (best for calibration)")
print("\nThe aligned_data.parquet file contains both input parameters and corresponding")
print("simulation outputs for all variants, making it ideal for calibration workflows.")