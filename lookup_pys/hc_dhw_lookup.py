import pandas as pd
import os

def read_range_or_value(row):
    """
    Checks if there's a single_value present.
    Else attempts to read (range_min, range_max).
    Returns one of:
      - float (if single_value is present),
      - tuple (val_min, val_max) if at least one is present,
      - None if everything is blank.
    """
    single_val = row.get('single_value', None)
    if pd.notna(single_val):
        # convert to float if possible
        try:
            return float(single_val)
        except ValueError:
            # fallback if it's a string
            return single_val
    
    # else check range_min / range_max
    min_val = row.get('range_min', None)
    max_val = row.get('range_max', None)
    
    if pd.isna(min_val) and pd.isna(max_val):
        return None
    
    # Convert if not None
    min_float = float(min_val) if pd.notna(min_val) else None
    max_float = float(max_val) if pd.notna(max_val) else None
    
    # If only one is present, replicate
    if min_float is not None and max_float is None:
        max_float = min_float
    elif max_float is not None and min_float is None:
        min_float = max_float
    
    return (min_float, max_float)


def create_dhw_lookup(excel_file_path, output_file_path):
    """
    Reads the specified Excel file, processes it to create a dhw_lookup dictionary,
    and writes out the dictionary to 'output_file_path'.
    """

    # 1) Check if file exists
    if not os.path.exists(excel_file_path):
        print(f"Error: {excel_file_path} not found.")
        return

    # 2) Read Excel
    try:
        df = pd.read_excel(excel_file_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # Clean columns
    df.columns = df.columns.str.strip().str.lower()
    df.replace('-', pd.NA, inplace=True)
    df.replace('', pd.NA, inplace=True)

    # 3) Initialize the final dictionary
    dhw_lookup = {
        "TABLE_13_1_KWH_PER_M2": {},
        "pre_calibration": {},
        "post_calibration": {}
    }

    # 4) Populate from Excel
    for _, row_data in df.iterrows():
        section_type = row_data.get('section_type', None)
        if pd.isna(section_type):
            continue
        section_type = str(section_type).strip()

        key_name = row_data.get('key_name', None)
        if pd.isna(key_name):
            continue
        key_name = str(key_name).strip()

        subkey_name = row_data.get('subkey_name', None)
        subkey_name = None if pd.isna(subkey_name) else str(subkey_name).strip()
        
        val = read_range_or_value(row_data)
        if val is None:
            # skip blank or incomplete row
            continue
        
        # Insert into dhw_lookup
        if section_type == "TABLE_13_1_KWH_PER_M2":
            # For the TABLE_13_1_KWH_PER_M2 section, we expect val to be numeric
            # (though we handle non-numeric gracefully below if it appears)
            dhw_lookup["TABLE_13_1_KWH_PER_M2"][key_name] = val
        
        elif section_type in ("pre_calibration", "post_calibration"):
            # Make sure the top-level key (e.g. "Residential_SingleFamily_Small") is present
            if key_name not in dhw_lookup[section_type]:
                dhw_lookup[section_type][key_name] = {}
            # If subkey_name is None => skip or decide what to do
            if subkey_name is None:
                continue
            # Store the value in the sub-dict
            dhw_lookup[section_type][key_name][subkey_name] = val

    # 5) Write out the dictionary to a .py file
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    except Exception as e:
        print(f"Error creating output directory: {e}")
        return
    
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write("# Automatically generated from DHW Excel data\n\n")
            f.write("dhw_lookup = {\n")
            
            # A) TABLE_13_1_KWH_PER_M2
            f.write('    "TABLE_13_1_KWH_PER_M2": {\n')
            for func_key, func_val in dhw_lookup["TABLE_13_1_KWH_PER_M2"].items():
                # Numeric single value or fallback
                if isinstance(func_val, (float, int)):
                    f.write(f'        "{func_key}": {func_val},\n')
                else:
                    # If it's a string or something else
                    f.write(f'        "{func_key}": "{func_val}",\n')
            f.write("    },\n\n")
            
            # B) pre_calibration
            f.write('    "pre_calibration": {\n')
            for bld_key, bld_val in dhw_lookup["pre_calibration"].items():
                f.write(f'        "{bld_key}": {{\n')
                for prop_key, prop_val in bld_val.items():
                    if isinstance(prop_val, tuple):
                        f.write(f'            "{prop_key}": {prop_val},\n')
                    elif isinstance(prop_val, (float, int)):
                        f.write(f'            "{prop_key}": {prop_val},\n')
                    else:
                        f.write(f'            "{prop_key}": "{prop_val}",\n')
                f.write("        },\n")
            f.write("    },\n\n")
            
            # C) post_calibration
            f.write('    "post_calibration": {\n')
            for bld_key, bld_val in dhw_lookup["post_calibration"].items():
                f.write(f'        "{bld_key}": {{\n')
                for prop_key, prop_val in bld_val.items():
                    if isinstance(prop_val, tuple):
                        f.write(f'            "{prop_key}": {prop_val},\n')
                    elif isinstance(prop_val, (float, int)):
                        f.write(f'            "{prop_key}": {prop_val},\n')
                    else:
                        f.write(f'            "{prop_key}": "{prop_val}",\n')
                f.write("        },\n")
            f.write("    },\n")
            
            f.write("}\n")

        print(f"dhw_lookup dictionary successfully exported to {output_file_path}")
    except Exception as e:
        print(f"Error writing dictionary to {output_file_path}: {e}")


