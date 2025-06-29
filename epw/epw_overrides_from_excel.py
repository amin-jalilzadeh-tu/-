# epw_overrides_from_excel.py

import pandas as pd
import copy

def read_epw_overrides_from_excel(excel_path):
    """
    Reads an Excel file with columns => file_path, year, lat, lon
    and returns a list of dicts => [ {"file_path":..., "year":..., "lat":..., "lon":...}, ... ]
    """
    df = pd.read_excel(excel_path)

    required_cols = ["file_path", "year", "lat", "lon"]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"Missing column '{c}' in {excel_path}")

    result = []
    for _, row in df.iterrows():
        fp = str(row["file_path"]).strip()
        yr = float(row["year"]) if not pd.isna(row["year"]) else 2020
        la = float(row["lat"]) if not pd.isna(row["lat"]) else 0.0
        lo = float(row["lon"]) if not pd.isna(row["lon"]) else 0.0

        epw_entry = {
            "file_path": fp,
            "year": int(yr),
            "lat": la,
            "lon": lo
        }
        result.append(epw_entry)

    return result


def apply_epw_overrides_to_lookup(default_lookup, override_list):
    """
    Merges override_list (a list of epw dicts) into default_lookup.
    If the 'year' already exists in default_lookup, we either replace it
    or keep both. For example, if you prefer to update the existing entry 
    for that year, you'd do something like "unique by year + lat/lon distance".
    Or you can just append everything, resulting in duplicates.

    We'll do a basic approach:
      - For each override in override_list => 
         if there's an exact match (same year, lat, lon) in default_lookup, replace it
         else append it as a new entry.
    """

    new_lookup = copy.deepcopy(default_lookup)

    for override in override_list:
        year_ov = override["year"]
        lat_ov = override["lat"]
        lon_ov = override["lon"]

        # see if there's a matching entry in new_lookup
        # we'll consider "matching" if year is the same and lat/lon difference is < small threshold
        found_match = False
        threshold_km = 0.5  # half a km lat-lon threshold (approx)
        # 1 deg lat ~ 111 km, so we'll do a simple approach:
        for i, existing in enumerate(new_lookup):
            if existing["year"] == year_ov:
                dist_lat = (existing["lat"] - lat_ov) * 111
                dist_lon = (existing["lon"] - lon_ov) * 111
                dist_km = (dist_lat**2 + dist_lon**2) ** 0.5
                if dist_km < threshold_km:
                    # assume it's a match => override
                    new_lookup[i] = override
                    found_match = True
                    break
        
        if not found_match:
            # just append
            new_lookup.append(override)

    return new_lookup
