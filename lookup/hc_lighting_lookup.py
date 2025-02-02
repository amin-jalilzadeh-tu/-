import pandas as pd
import os

def read_range(row, min_col, max_col):
    """
    Returns a tuple (val_min, val_max) if either is not blank;
    returns None if both are blank.
    """
    val_min = row[min_col] if min_col in row and pd.notna(row[min_col]) else None
    val_max = row[max_col] if max_col in row and pd.notna(row[max_col]) else None
    
    if val_min is None and val_max is None:
        return None  # skip if both blank
    
    # Convert to float if not None
    val_min = float(val_min) if val_min is not None else None
    val_max = float(val_max) if val_max is not None else None
    return (val_min, val_max)

def create_lighting_lookup(excel_file_path, output_file_path):
    """
    Reads 'lighting_lookup.xlsx' (or specified file) to build a nested dictionary:
        lighting_lookup[scenario][building_function][building_subtype] = {
            "LIGHTS_WM2_range": (min, max),
            "PARASITIC_WM2_range": (min, max),
            "tD_range": (min, max),
            "tN_range": (min, max),
        }
    Then writes this dictionary to 'output_file_path'.
    """

    # 1) Check if the Excel file exists
    if not os.path.exists(excel_file_path):
        print(f"Error: The file at {excel_file_path} was not found.")
        return

    # 2) Attempt to read the Excel file
    try:
        df = pd.read_excel(excel_file_path)
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return

    # Clean column names
    df.columns = df.columns.str.strip().str.lower()

    # Replace '-' or '' with NaN
    df.replace('-', pd.NA, inplace=True)
    df.replace('', pd.NA, inplace=True)

    # 3) Build the lighting_lookup dictionary
    lighting_lookup = {}

    # Iterate over each row
    for _, row in df.iterrows():
        # scenario
        scenario = str(row['scenario']).strip() if pd.notna(row.get('scenario')) else None
        if not scenario:
            continue
        
        # building_function
        building_func = str(row['building_function']).strip() if pd.notna(row.get('building_function')) else None
        if not building_func:
            continue
        
        # building_subtype
        building_subtype = str(row['building_subtype']).strip() if pd.notna(row.get('building_subtype')) else None
        if not building_subtype:
            continue

        # Ensure nested structure
        if scenario not in lighting_lookup:
            lighting_lookup[scenario] = {}
        if building_func not in lighting_lookup[scenario]:
            lighting_lookup[scenario][building_func] = {}

        # Sub-dictionary for this row
        sub_dict = {}

        # Read the various ranges
        lw_range = read_range(row, 'lights_wm2_min', 'lights_wm2_max')
        if lw_range is not None:
            sub_dict['LIGHTS_WM2_range'] = lw_range
        
        pwr_range = read_range(row, 'parasitic_wm2_min', 'parasitic_wm2_max')
        if pwr_range is not None:
            sub_dict['PARASITIC_WM2_range'] = pwr_range

        td_range = read_range(row, 'td_min', 'td_max')
        if td_range is not None:
            sub_dict['tD_range'] = td_range

        tn_range = read_range(row, 'tn_min', 'tn_max')
        if tn_range is not None:
            sub_dict['tN_range'] = tn_range

        # If there's data in sub_dict, attach it
        if sub_dict:
            lighting_lookup[scenario][building_func][building_subtype] = sub_dict

    # 4) Write the dictionary to a Python file
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    except Exception as e:
        print(f"Error creating output directory: {e}")
        return

    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write("\"\"\"Automatically generated lighting_lookup. Do not edit manually.\"\"\"\n\n")
            f.write("lighting_lookup = {\n")
            
            for scenario_key, scenario_val in lighting_lookup.items():
                f.write(f'    "{scenario_key}": {{\n')
                
                for func_key, func_val in scenario_val.items():
                    f.write(f'        "{func_key}": {{\n')
                    
                    for subtype_key, subtype_val in func_val.items():
                        f.write(f'            "{subtype_key}": {{\n')
                        
                        for prop_key, prop_val in subtype_val.items():
                            if isinstance(prop_val, tuple):
                                f.write(f'                "{prop_key}": {prop_val},\n')
                            else:
                                f.write(f'                "{prop_key}": {prop_val},\n')
                        
                        f.write("            },\n")
                    
                    f.write("        },\n")
                
                f.write("    },\n")
            
            f.write("}\n")
        
        print(f"lighting_lookup dictionary successfully exported to {output_file_path}")
    except Exception as e:
        print(f"Error writing to {output_file_path}: {e}")
