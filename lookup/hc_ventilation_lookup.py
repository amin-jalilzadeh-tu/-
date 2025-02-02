import pandas as pd
import os

def read_range(row):
    """
    Reads range_min, range_max from a row.
    Returns:
      - (val_min, val_max) if at least one is not blank,
      - None if both are blank.
    If only one is present, returns (val, val).
    """
    val_min = row.get('range_min', None)
    val_max = row.get('range_max', None)
    
    # If both are completely blank, return None
    if pd.isna(val_min) and pd.isna(val_max):
        return None
    
    # Convert to float if not blank
    min_float = float(val_min) if pd.notna(val_min) else None
    max_float = float(val_max) if pd.notna(val_max) else None
    
    # If only one is provided, use the same value for both
    if min_float is not None and max_float is None:
        max_float = min_float
    elif max_float is not None and min_float is None:
        min_float = max_float
    
    return (min_float, max_float)


def create_ventilation_lookup(excel_file_path, output_file_path):
    """
    Reads the specified Excel file, processes it to build a ventilation_lookup dictionary,
    and writes the dictionary to 'output_file_path'.
    """

    # 1) Verify the Excel file exists
    if not os.path.exists(excel_file_path):
        print(f"Error: The file at {excel_file_path} was not found.")
        return

    # 2) Attempt to read the Excel file
    try:
        df = pd.read_excel(excel_file_path)
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return

    # Clean columns
    df.columns = df.columns.str.strip().str.lower()
    df.replace('-', pd.NA, inplace=True)
    df.replace('', pd.NA, inplace=True)

    # 3) Initialize the ventilation_lookup dictionary
    ventilation_lookup = {}

    # 4) Populate the dictionary
    for _, row_data in df.iterrows():
        # scenario
        scenario = row_data.get('scenario', None)
        if pd.isna(scenario):
            continue
        scenario = str(scenario).strip()
        
        # calibration_stage
        stage = row_data.get('calibration_stage', None)
        if pd.isna(stage):
            continue
        stage = str(stage).strip()
        
        # param_category
        category = row_data.get('param_category', None)
        if pd.isna(category):
            continue
        category = str(category).strip()
        
        # read_range
        rng = read_range(row_data)
        if rng is None:
            # skip if both min & max are blank
            continue
        
        # Create the scenario/stage if not exist
        if scenario not in ventilation_lookup:
            ventilation_lookup[scenario] = {}
        if stage not in ventilation_lookup[scenario]:
            ventilation_lookup[scenario][stage] = {}
        
        # param_subkey
        subkey = row_data.get('param_subkey', None)
        subkey = None if pd.isna(subkey) else str(subkey).strip()
        
        # param_nested_key
        nested_key = row_data.get('param_nested_key', None)
        nested_key = None if pd.isna(nested_key) else str(nested_key).strip()
        
        # Create the category dict if not exist
        if category not in ventilation_lookup[scenario][stage]:
            ventilation_lookup[scenario][stage][category] = {}
        
        # We have three possibilities:
        # 1) subkey is None => directly store the tuple at ventilation_lookup[scenario][stage][category]
        # 2) subkey present but nested_key is None => store tuple under [subkey]
        # 3) subkey AND nested_key => store tuple under [subkey][nested_key]

        if subkey is None:
            # Means we attach the tuple directly to category
            ventilation_lookup[scenario][stage][category] = rng
        else:
            # Ensure we have a dict at category
            if not isinstance(ventilation_lookup[scenario][stage][category], dict):
                # If category was already set to a tuple, that’s a conflict; we reset it to dict
                ventilation_lookup[scenario][stage][category] = {}
            
            if nested_key is None:
                ventilation_lookup[scenario][stage][category][subkey] = rng
            else:
                if subkey not in ventilation_lookup[scenario][stage][category]:
                    ventilation_lookup[scenario][stage][category][subkey] = {}
                
                ventilation_lookup[scenario][stage][category][subkey][nested_key] = rng

    # 5) Write the dictionary to a Python file
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    except Exception as e:
        print(f"Error creating output directory: {e}")
        return
    
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write("\"\"\"Automatically generated ventilation_lookup. Do not edit manually.\"\"\"\n\n")
            f.write("ventilation_lookup = {\n")
            
            # First-level: scenario
            for scenario_key, scenario_val in ventilation_lookup.items():
                f.write(f'    "{scenario_key}": {{\n')
                
                # second-level: calibration_stage
                for stage_key, stage_val in scenario_val.items():
                    f.write(f'        "{stage_key}": {{\n')
                    
                    # third-level: param_category
                    for cat_key, cat_val in stage_val.items():
                        f.write(f'            "{cat_key}": ')
                        
                        # If cat_val is a tuple, write directly
                        if isinstance(cat_val, tuple):
                            f.write(f"{cat_val},\n")
                        else:
                            # cat_val is a dict => subkeys
                            f.write("{\n")
                            
                            for subkey_key, subkey_val in cat_val.items():
                                # subkey_val could be a tuple or another dict
                                f.write(f'                "{subkey_key}": ')
                                if isinstance(subkey_val, tuple):
                                    f.write(f"{subkey_val},\n")
                                elif isinstance(subkey_val, dict):
                                    # We might have nested keys
                                    f.write("{\n")
                                    for nk, nk_val in subkey_val.items():
                                        f.write(f'                    "{nk}": {nk_val},\n')
                                    f.write("                },\n")
                                else:
                                    f.write(f"{subkey_val},\n")  # fallback
                            f.write("            },\n")
                    
                    f.write("        },\n")
                
                f.write("    },\n")
            
            f.write("}\n")
        
        print(f"ventilation_lookup dictionary successfully exported to {output_file_path}")
    except Exception as e:
        print(f"Error writing dictionary to {output_file_path}: {e}")
