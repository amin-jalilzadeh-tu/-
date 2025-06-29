import pandas as pd
import json
import os

output_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99"

# Check parsed data structure
print("=== PARSED DATA STRUCTURE ===")
try:
    # Check timeseries data
    daily_data = pd.read_parquet(os.path.join(output_dir, "parsed_data/timeseries/base_all_daily.parquet"))
    print("\n1. Daily Timeseries Data Shape:", daily_data.shape)
    print("Columns:", list(daily_data.columns)[:10], "...")
    print("First few rows:")
    print(daily_data.head())
    
    # Check IDF data
    geometry_data = pd.read_parquet(os.path.join(output_dir, "parsed_data/idf_data/by_category/geometry_zones.parquet"))
    print("\n2. IDF Geometry Zones Data:")
    print("Shape:", geometry_data.shape)
    print("Columns:", list(geometry_data.columns))
    
    # Check equipment data
    equipment_data = pd.read_parquet(os.path.join(output_dir, "parsed_data/idf_data/by_category/equipment.parquet"))
    print("\n3. Equipment Data:")
    print("Shape:", equipment_data.shape)
    print("Sample data:")
    print(equipment_data.head())
    
except Exception as e:
    print(f"Error reading parsed data: {e}")

# Check sensitivity parameters
print("\n\n=== SENSITIVITY PARAMETERS ===")
try:
    sensitivity_params = pd.read_csv(os.path.join(output_dir, "sensitivity_results/sensitivity_parameters.csv"))
    print("Shape:", sensitivity_params.shape)
    print("Columns:", list(sensitivity_params.columns))
    print("\nTop 5 parameters:")
    print(sensitivity_params.head())
except Exception as e:
    print(f"Error reading sensitivity parameters: {e}")

# Check surrogate model training data structure
print("\n\n=== SURROGATE MODEL DATA ===")
try:
    # Check if training data exists
    training_data_path = os.path.join(output_dir, "surrogate_models/training_data.csv")
    if os.path.exists(training_data_path):
        training_data = pd.read_csv(training_data_path)
        print("Training Data Shape:", training_data.shape)
        print("Columns:", list(training_data.columns))
    else:
        print("No training_data.csv found in surrogate_models directory")
        
    # Check feature importance
    feature_imp_path = os.path.join(output_dir, "surrogate_models/v1.0/feature_importance.csv")
    if os.path.exists(feature_imp_path):
        feature_imp = pd.read_csv(feature_imp_path)
        print("\nFeature Importance:")
        print(feature_imp.head(10))
except Exception as e:
    print(f"Error reading surrogate data: {e}")

# Check modification data
print("\n\n=== MODIFICATION DATA ===")
try:
    mod_report = os.path.join(output_dir, "modified_idfs/modification_report_20250629_202858.json")
    with open(mod_report, 'r') as f:
        mod_data = json.load(f)
    print("Number of variants:", len(mod_data.get('variants', [])))
    if mod_data.get('variants'):
        print("\nFirst variant modifications:")
        first_variant = mod_data['variants'][0]
        print(f"Variant ID: {first_variant['variant_id']}")
        print(f"Number of modifications: {len(first_variant['modifications'])}")
        if first_variant['modifications']:
            print("\nSample modification:")
            print(json.dumps(first_variant['modifications'][0], indent=2))
except Exception as e:
    print(f"Error reading modification data: {e}")

# Check comparison data structure
print("\n\n=== COMPARISON DATA STRUCTURE ===")
try:
    comp_dir = os.path.join(output_dir, "parsed_modified_results/comparisons")
    comp_files = os.listdir(comp_dir)
    print(f"Number of comparison files: {len(comp_files)}")
    if comp_files:
        # Read a sample comparison file
        sample_file = comp_files[0]
        comp_data = pd.read_parquet(os.path.join(comp_dir, sample_file))
        print(f"\nSample file: {sample_file}")
        print(f"Shape: {comp_data.shape}")
        print(f"Columns: {list(comp_data.columns)}")
        print("\nFirst few rows:")
        print(comp_data.head())
except Exception as e:
    print(f"Error reading comparison data: {e}")