import pandas as pd
import os

def create_epw_lookup(excel_file_path, output_file_path):
    """
    Reads an Excel file containing EPW data and produces a list of dictionaries,
    each describing an EPW file (with fields like file_path, year, lat, lon, etc.).
    Writes the resulting list to a Python file at 'output_file_path'.
    """

    # 1) Check if file exists
    if not os.path.exists(excel_file_path):
        print(f"Error: The file at {excel_file_path} was not found.")
        return

    # 2) Try reading the Excel
    try:
        df = pd.read_excel(excel_file_path)
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return

    # 3) Clean column names
    df.columns = df.columns.str.strip().str.lower()

    # Replace '-' or '' with NaN
    df.replace('-', pd.NA, inplace=True)
    df.replace('', pd.NA, inplace=True)

    # 4) Initialize the epw_lookup list
    epw_lookup_list = []

    for _, row in df.iterrows():
        # Make sure we have a valid file_path
        file_path = row['file_path'] if 'file_path' in row and pd.notna(row['file_path']) else None
        if not file_path:
            # Skip row if no file_path
            continue

        # year, lat, lon conversions
        year_val = None
        if 'year' in row and pd.notna(row['year']):
            try:
                year_val = int(row['year'])
            except ValueError:
                pass  # remains None if invalid

        lat_val = None
        if 'lat' in row and pd.notna(row['lat']):
            try:
                lat_val = float(row['lat'])
            except ValueError:
                pass

        lon_val = None
        if 'lon' in row and pd.notna(row['lon']):
            try:
                lon_val = float(row['lon'])
            except ValueError:
                pass

        # Construct the dictionary for this row
        epw_entry = {}
        epw_entry["file_path"] = str(file_path)

        if year_val is not None:
            epw_entry["year"] = year_val
        if lat_val is not None:
            epw_entry["lat"] = lat_val
        if lon_val is not None:
            epw_entry["lon"] = lon_val

        # If more columns exist, handle similarly:
        # climate_zone = row['climate_zone'] if 'climate_zone' in row and pd.notna(row['climate_zone']) else None
        # if climate_zone:
        #     epw_entry["climate_zone"] = str(climate_zone)

        # Add to the list
        epw_lookup_list.append(epw_entry)

    # 5) Write epw_lookup_list to a .py file
    try:
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    except Exception as e:
        print(f"Error creating output directory: {e}")
        return
    
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write("# Automatically generated epw_lookup. Do not edit manually.\n\n")
            f.write("epw_lookup = [\n")
            
            for entry in epw_lookup_list:
                f.write("    {\n")
                for k, v in entry.items():
                    # If string, wrap in quotes
                    if isinstance(v, str):
                        f.write(f'        "{k}": "{v}",\n')
                    else:
                        f.write(f'        "{k}": {v},\n')
                f.write("    },\n")
            
            f.write("]\n")
        
        print(f"epw_lookup list successfully exported to {output_file_path}")
    except Exception as e:
        print(f"Error writing to {output_file_path}: {e}")
