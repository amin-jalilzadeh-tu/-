import pandas as pd
from collections import defaultdict
import os

def create_geometry_lookup(excel_file_path, output_file_path):
    """
    Reads an Excel file to build a geometry_lookup dictionary, then
    writes it as a Python file to 'output_file_path'.
    """
    # 1) Read the Excel file
    try:
        df = pd.read_excel(excel_file_path)
    except FileNotFoundError:
        print(f"Error: The file {excel_file_path} does not exist.")
        return
    except Exception as e:
        print(f"An error occurred while reading the Excel file: {e}")
        return

    # 2) Build the dictionary using a defaultdict
    geometry_lookup = defaultdict(lambda: defaultdict(dict))

    # 3) Iterate over rows and populate geometry_lookup
    for index, row in df.iterrows():
        building_function = row['building_function']
        building_type = row['building_type']
        calibration_stage = str(row['calibration_stage']).strip()  # Ensure string & trim whitespace
        
        perimeter_depth_min = row['perimeter_depth_min']
        perimeter_depth_max = row['perimeter_depth_max']
        has_core_value = row['has_core_value']
        
        # Convert has_core_value to boolean
        if isinstance(has_core_value, str):
            has_core = has_core_value.strip().lower() == 'true'
        else:
            has_core = bool(has_core_value)
        
        # Define the calibration data
        calibration_data = {
            "perimeter_depth_range": (perimeter_depth_min, perimeter_depth_max),
            "has_core": has_core
        }
        
        # Insert into the dictionary
        geometry_lookup[building_function][building_type][calibration_stage] = calibration_data

    # 4) Convert to regular dict for serialization
    geometry_lookup = dict(geometry_lookup)

    # 5) Optionally, sort the dictionary keys for better readability
    def sort_dict(d):
        if isinstance(d, dict):
            return {k: sort_dict(v) for k, v in sorted(d.items())}
        return d

    geometry_lookup = sort_dict(geometry_lookup)

    # 6) A custom serializer to produce Python syntax with correct quoting
    def serialize_dict(d, indent=0):
        indent_space = '    ' * indent
        if isinstance(d, dict):
            items = []
            for i, (k, v) in enumerate(sorted(d.items())):
                key = f'"{k}"'
                value = serialize_dict(v, indent + 1)
                items.append(f'{indent_space}    {key}: {value}')
            return "{\n" + ",\n".join(items) + f"\n{indent_space}}}"
        elif isinstance(d, list):
            items = [serialize_dict(item, indent + 1) for item in d]
            return "[ " + ", ".join(items) + " ]"
        elif isinstance(d, tuple):
            items = ", ".join([serialize_dict(item, indent) for item in d])
            return f"({items})"
        elif isinstance(d, str):
            # Escape any double quotes
            escaped_str = d.replace('"', '\\"')
            return f'"{escaped_str}"'
        elif isinstance(d, bool):
            return "True" if d else "False"
        elif d is None:
            return "None"
        else:
            return str(d)

    serialized_geometry_lookup = serialize_dict(geometry_lookup, indent=0)

    # 7) Prepare content to write
    output_content = (
        "# This file is auto-generated. Do not edit manually.\n\n"
        "geometry_lookup = " + serialized_geometry_lookup + "\n"
    )

    # 8) Write out to the specified Python file
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(output_content)
        print(f"geometry_lookup dictionary has been successfully written to {output_file_path}")
    except Exception as e:
        print(f"An error occurred while writing to the file: {e}")
