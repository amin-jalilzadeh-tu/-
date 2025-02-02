import pandas as pd
import os

def read_range(row):
    """
    Reads temp_min, temp_max from the row.
    Returns:
      - (val_min, val_max) if at least one is not blank,
      - None if both are blank.
    If only one is provided, uses the same value for both.
    """
    tmin = row.get('temp_min', None)
    tmax = row.get('temp_max', None)
    
    if pd.isna(tmin) and pd.isna(tmax):
        return None
    
    min_val = float(tmin) if pd.notna(tmin) else None
    max_val = float(tmax) if pd.notna(tmax) else None
    
    if min_val is not None and max_val is None:
        max_val = min_val
    elif max_val is not None and min_val is None:
        min_val = max_val
    
    return (min_val, max_val)

def create_groundtemp_lookup(excel_file_path, output_file_path):
    """
    Reads the given Excel file (with 'scenario' and 'month' columns, plus 'temp_min'/'temp_max'),
    then writes out a groundtemp_lookup dictionary to 'output_file_path'.
    """
    # 1) Ensure the Excel file exists
    if not os.path.exists(excel_file_path):
        print(f"Error: The file at {excel_file_path} was not found.")
        return

    # 2) Attempt to read the file
    try:
        df = pd.read_excel(excel_file_path)
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return

    # 3) Clean columns
    df.columns = df.columns.str.strip().str.lower()

    # Replace '-' or '' with NaN
    df.replace('-', pd.NA, inplace=True)
    df.replace('', pd.NA, inplace=True)

    # 4) Build the groundtemp_lookup dictionary
    groundtemp_lookup = {}

    for _, row in df.iterrows():
        scenario = row.get('scenario', None)
        month = row.get('month', None)
        
        if pd.isna(scenario) or pd.isna(month):
            # skip if either is blank
            continue
        
        # Convert to strings
        scenario = str(scenario).strip()
        month = str(month).strip()
        
        # read_range for the temperature
        temp_tuple = read_range(row)
        if temp_tuple is None:
            continue  # skip if both temp_min and temp_max are blank
        
        # Create the scenario dict if not present
        if scenario not in groundtemp_lookup:
            groundtemp_lookup[scenario] = {}
        
        # Assign the temperature tuple to that month
        groundtemp_lookup[scenario][month] = temp_tuple

    # 5) Write dictionary to a Python file
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    except Exception as e:
        print(f"Error creating output directory: {e}")
        return
    
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write("\"\"\"Automatically generated groundtemp_lookup. Do not edit manually.\"\"\"\n\n")
            f.write("groundtemp_lookup = {\n")
            
            for scenario_key, months_dict in groundtemp_lookup.items():
                f.write(f'    "{scenario_key}": {{\n')
                for month_key, temp_val in months_dict.items():
                    f.write(f'        "{month_key}": {temp_val},\n')
                f.write("    },\n")
            
            f.write("}\n")
        
        print(f"groundtemp_lookup dictionary successfully exported to {output_file_path}")
    except Exception as e:
        print(f"Error writing dictionary to {output_file_path}: {e}")
