import pandas as pd
import os

def create_envelop_lookup(excel_file_path, output_file_path, dict_name="envelop_materials_data"):
    """
    Reads the specified Excel file (e.g. envelop_nonres5.xlsx or envelop_res5.xlsx),
    processes it to create a dictionary, and writes out the dictionary to 'output_file_path'.
    The dictionary will have the variable name given by 'dict_name'.
    """

    # 1) Check if file exists
    if not os.path.exists(excel_file_path):
        print(f"Error: The file at {excel_file_path} was not found.")
        return

    # 2) Read the Excel file into a pandas DataFrame
    try:
        df = pd.read_excel(excel_file_path)
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return

    # 3) Clean/inspect column names
    original_cols = df.columns.tolist()
    df.columns = df.columns.str.strip().str.lower()
    cleaned_cols = df.columns.tolist()

    print("\n--- Envelop Lookup ---")
    print(f"Excel File: {excel_file_path}")
    print("Original Column Names:", original_cols)
    print("Cleaned Column Names:", cleaned_cols)
    print("First 5 Rows:\n", df.head())

    # 4) Check if required columns are present
    required_columns = [
        'building_function', 'building_type', 'year_range', 'scenario',
        'calibration_stage', 'element', 'area_m2', 'r_value_min',
        'r_value_max', 'u_value_min', 'u_value_max', 'roughness',
        'material_opaque_lookup', 'material_window_lookup',
        'min_wwr', 'max_wwr'
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: Missing columns: {missing_columns}")
        return
    else:
        print("All required columns are present.")

    # 5) Replace any placeholder '-' with NaN
    df.replace('-', pd.NA, inplace=True)

    # 6) Initialize the main dictionary
    envelop_data = {}

    # 7) Group the DataFrame
    grouped = df.groupby(['building_function', 'building_type', 'year_range', 'scenario', 'calibration_stage'])

    for group_keys, group_df in grouped:
        building_function, building_type, year_range, scenario, calibration_stage = group_keys
        
        # A tuple that identifies the scenario
        dict_key = (building_type, year_range, scenario, calibration_stage)
        
        # Sub-dictionary for this group
        sub_dict = {}

        # -- Fallback / top-level values from the first row of group --
        first_row = group_df.iloc[0]
        
        # roughness
        roughness = first_row['roughness'] if pd.notna(first_row['roughness']) else None
        sub_dict['roughness'] = roughness
        
        # wwr_range
        min_wwr = first_row['min_wwr'] if pd.notna(first_row['min_wwr']) else None
        max_wwr = first_row['max_wwr'] if pd.notna(first_row['max_wwr']) else None
        sub_dict['wwr_range'] = (
            float(min_wwr) if min_wwr else None,
            float(max_wwr) if max_wwr else None
        )
        
        # fallback opaque
        fallback_opaque = first_row['material_opaque_lookup'] if pd.notna(first_row['material_opaque_lookup']) else None
        sub_dict['material_opaque_lookup'] = fallback_opaque
        
        # fallback window
        fallback_window = first_row['material_window_lookup'] if pd.notna(first_row['material_window_lookup']) else None
        sub_dict['material_window_lookup'] = fallback_window
        
        # -- Process each row's element data --
        for _, row in group_df.iterrows():
            element_name = row['element']  # e.g. "exterior_wall", "ground_floor", ...
            element_dict = {}
            
            # area_m2
            if pd.notna(row['area_m2']):
                element_dict['area_m2'] = float(row['area_m2'])
            else:
                element_dict['area_m2'] = None
            
            # R_value_range
            R_min = row['r_value_min']
            R_max = row['r_value_max']
            if pd.notna(R_min) and pd.notna(R_max):
                element_dict['R_value_range'] = (float(R_min), float(R_max))
            elif pd.notna(R_min):
                element_dict['R_value_range'] = (float(R_min), float(R_min))
            else:
                element_dict['R_value_range'] = (None, None)
            
            # U_value_range
            U_min = row['u_value_min']
            U_max = row['u_value_max']
            if pd.notna(U_min) and pd.notna(U_max):
                element_dict['U_value_range'] = (float(U_min), float(U_max))
            elif pd.notna(U_min):
                element_dict['U_value_range'] = (float(U_min), float(U_min))
            else:
                element_dict['U_value_range'] = (None, None)
            
            # material_opaque_lookup
            if pd.notna(row['material_opaque_lookup']):
                element_dict['material_opaque_lookup'] = row['material_opaque_lookup']
            elif fallback_opaque:
                element_dict['material_opaque_lookup'] = fallback_opaque
            
            # material_window_lookup
            if pd.notna(row['material_window_lookup']):
                element_dict['material_window_lookup'] = row['material_window_lookup']
            elif fallback_window:
                element_dict['material_window_lookup'] = fallback_window

            # Store element_dict
            sub_dict[element_name] = element_dict
        
        # Add sub_dict to main dictionary
        envelop_data[dict_key] = sub_dict

    # 8) Write out the dictionary to a .py file
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    except Exception as e:
        print(f"Error creating output directory: {e}")
        return
    
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            # Start writing the dictionary with the user-defined variable name (dict_name)
            f.write(f"{dict_name} = {{\n")
            for key, value in envelop_data.items():
                f.write(f"    {key}: {{\n")
                for sub_key, sub_value in value.items():
                    # If it's a nested dict (like sub_value == {'area_m2': X, 'R_value_range': Y, ...})
                    if isinstance(sub_value, dict):
                        f.write(f"        \"{sub_key}\": {{\n")
                        for inner_key, inner_val in sub_value.items():
                            if isinstance(inner_val, tuple):
                                f.write(f"            \"{inner_key}\": {inner_val},\n")
                            elif isinstance(inner_val, (float, int)):
                                f.write(f"            \"{inner_key}\": {inner_val},\n")
                            elif inner_val is None:
                                f.write(f"            \"{inner_key}\": None,\n")
                            else:
                                f.write(f"            \"{inner_key}\": \"{inner_val}\",\n")
                        f.write("        },\n")
                    # If sub_value is a tuple or scalar
                    elif isinstance(sub_value, tuple):
                        f.write(f"        \"{sub_key}\": {sub_value},\n")
                    elif isinstance(sub_value, (float, int)):
                        f.write(f"        \"{sub_key}\": {sub_value},\n")
                    elif sub_value is None:
                        f.write(f"        \"{sub_key}\": None,\n")
                    else:
                        f.write(f"        \"{sub_key}\": \"{sub_value}\",\n")
                f.write("    },\n\n")
            f.write("}\n")
        print(f"\nDictionary successfully created and exported to {output_file_path}")
    except Exception as e:
        print(f"Error writing dictionary to {output_file_path}: {e}")
