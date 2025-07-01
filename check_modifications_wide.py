import pandas as pd
import json

# Check the modifications_detail_wide parquet
wide_file = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/modified_idfs/modifications_detail_wide_20250701_074321.parquet"

print("=" * 80)
print("ANALYZING MODIFICATIONS_DETAIL_WIDE.PARQUET")
print("=" * 80)

try:
    df = pd.read_parquet(wide_file)
    
    print(f"\nShape: {df.shape}")
    print(f"\nColumns ({len(df.columns)}):")
    for col in df.columns:
        print(f"  - {col}")
    
    print(f"\nFirst 3 rows:")
    print(df.head(3))
    
    # Check for parameter columns
    param_cols = [col for col in df.columns if 'param' in col.lower() or 'parameter' in col.lower()]
    print(f"\nParameter columns: {param_cols}")
    
except Exception as e:
    print(f"Error: {e}")

# Check modification report JSON
report_file = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/modified_idfs/modification_report_20250701_074321.json"

print("\n" + "=" * 80)
print("CHECKING MODIFICATION REPORT")
print("=" * 80)

try:
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    print(f"Report keys: {list(report.keys())}")
    
    if 'summary' in report:
        print(f"\nSummary info:")
        for key, value in report['summary'].items():
            print(f"  {key}: {value}")
            
    if 'parameters_modified' in report:
        print(f"\nParameters modified: {report['parameters_modified']}")
        
except Exception as e:
    print(f"Error: {e}")

# Let's check if there are results in Modified_Sim_Results
print("\n" + "=" * 80)
print("CHECKING MODIFIED_SIM_RESULTS")
print("=" * 80)

mod_results_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/Modified_Sim_Results"
try:
    if os.path.exists(mod_results_dir):
        subdirs = [d for d in os.listdir(mod_results_dir) if os.path.isdir(os.path.join(mod_results_dir, d))]
        print(f"Variant result directories: {len(subdirs)}")
        for d in subdirs[:5]:
            print(f"  - {d}")
            # Check for SQL files in the first variant
            if subdirs:
                variant_dir = os.path.join(mod_results_dir, subdirs[0])
                sql_files = [f for f in os.listdir(variant_dir) if f.endswith('.sql')]
                if sql_files:
                    print(f"\nSQL files in {subdirs[0]}: {sql_files}")
    else:
        print("Modified_Sim_Results directory does not exist")
        
except Exception as e:
    print(f"Error: {e}")

# Import os for directory operations
import os

# Generate a CSV file suitable for calibration from the comparison parquet files
print("\n" + "=" * 80)
print("GENERATING CALIBRATION CSV FORMAT")
print("=" * 80)

# Let's create a sample CSV that could be used for calibration
comparisons_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/parsed_modified_results/comparisons"

# Read multiple comparison files to create a consolidated view
try:
    all_data = []
    
    for file in os.listdir(comparisons_dir):
        if file.endswith('.parquet') and 'monthly' in file and 'from' not in file:
            filepath = os.path.join(comparisons_dir, file)
            df_temp = pd.read_parquet(filepath)
            
            # Extract variable type from filename
            var_type = file.replace('var_', '').replace('_na_monthly_b4136733.parquet', '')
            
            # Add variable type info
            df_temp['variable_type'] = var_type
            
            all_data.append(df_temp)
    
    if all_data:
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Create a calibration-friendly format
        calibration_df = combined_df.pivot_table(
            index=['timestamp', 'building_id'],
            columns='variable_type',
            values='base_value',
            aggfunc='first'
        ).reset_index()
        
        # Save as CSV
        output_csv = "/mnt/d/Documents/daily/E_Plus_2040_py/calibration_data_sample.csv"
        calibration_df.to_csv(output_csv, index=False)
        
        print(f"Created calibration CSV with shape: {calibration_df.shape}")
        print(f"Columns: {list(calibration_df.columns)}")
        print(f"\nFirst 5 rows:")
        print(calibration_df.head())
        print(f"\nSaved to: {output_csv}")
        
except Exception as e:
    print(f"Error creating calibration CSV: {e}")