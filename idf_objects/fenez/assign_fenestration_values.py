"""
assign_fenestration_values.py

Provides a function to determine the final WWR (window-to-wall ratio)
for a given building, referencing a final fenestration dictionary
that already includes Excel + JSON overrides.

Usage Example:
    final_wwr, wwr_range_used = assign_fenestration_parameters(
        building_row=row,
        scenario="scenario1",
        calibration_stage="pre_calibration",
        strategy="B",
        random_seed=42,
        res_data=updated_res_data,
        nonres_data=updated_nonres_data,
        use_computed_wwr=False,
        include_doors_in_wwr=False
    )
"""

import random
from .materials_config import compute_wwr

def assign_fenestration_parameters(
    building_row,
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="B",
    random_seed=None,
    res_data=None,
    nonres_data=None,
    use_computed_wwr=False,
    include_doors_in_wwr=False
):
    """
    Determine the final WWR for this building. If use_computed_wwr=False,
    we look up a wwr_range from the final dictionaries and pick a value
    (randomly or midpoint, depending on 'strategy').

    If use_computed_wwr=True, we compute the ratio from sub-element areas
    (windows, doors if include_doors_in_wwr=True) vs. external_wall area.

    Parameters
    ----------
    building_row : dict or pandas.Series
        Must have building_function, age_range, possibly building_type, etc.
    scenario : str
        e.g. "scenario1"
    calibration_stage : str
        e.g. "pre_calibration"
    strategy : str
        "A" => pick midpoint from the wwr_range
        "B" => pick random uniform in the wwr_range
        ...
    random_seed : int
        For reproducible random picks if strategy="B".
    res_data, nonres_data : dict
        Final fenestration dictionaries that incorporate Excel & user JSON overrides.
        Each key in these dicts is (bldg_type, age_range, scenario, calibration_stage).
    use_computed_wwr : bool
        If True, compute WWR by summing sub-element areas (windows, doors if
        include_doors_in_wwr=True) vs. external_wall area from the data dicts.
    include_doors_in_wwr : bool
        If True, add door area to the fenestration area when computing WWR.

    Returns
    -------
    (final_wwr, wwr_range_used) : (float, tuple or None)
        The numeric WWR (0.0–1.0) and the range that was used (or None if computed).
    """
    if random_seed is not None:
        random.seed(random_seed)

    # A) Determine if building is residential or non_residential
    bldg_func = str(building_row.get("building_function", "residential")).lower()
    if bldg_func == "residential":
        fenez_dict = res_data
        bldg_type  = str(building_row.get("residential_type", "")).strip()
    else:
        fenez_dict = nonres_data
        bldg_type  = str(building_row.get("non_residential_type", "")).strip()

    age_range = str(building_row.get("age_range", "2015 and later"))
    scen = str(scenario)
    stage = str(calibration_stage)

    dict_key = (bldg_type, age_range, scen, stage)

    # B) If the user wants to compute WWR from sub-element areas
    if use_computed_wwr:
        # We can attempt to see if sub-element data exists in the dictionary,
        # or we can compute from the building_row if it has area columns.
        if not fenez_dict or dict_key not in fenez_dict:
            # fallback => compute from building_row if possible
            computed_val = compute_wwr_from_row(building_row, include_doors_in_wwr)
            return computed_val, None

        # If the dict_key is found, it might have an "elements" subdict
        entry = fenez_dict[dict_key]
        elements_subdict = entry.get("elements", {})
        final_wwr = compute_wwr(elements_subdict, include_doors=include_doors_in_wwr)
        return final_wwr, None

    # C) If not computing from sub-elements, then we pick from wwr_range
    if not fenez_dict or dict_key not in fenez_dict:
        # fallback => wwr=0.3, range=(0.3,0.3)
        return 0.30, (0.30, 0.30)

    entry = fenez_dict[dict_key]
    wwr_range = entry.get("wwr_range", (0.2, 0.3))

    min_v, max_v = wwr_range
    if min_v == max_v:
        final_wwr = min_v
    else:
        if strategy == "B":
            final_wwr = random.uniform(min_v, max_v)
        else:
            # strategy="A" => midpoint by default
            final_wwr = (min_v + max_v) / 2.0

    return final_wwr, wwr_range


def compute_wwr_from_row(building_row, include_doors_in_wwr=False):
    """
    Alternate fallback if you want to directly read building_row
    to compute the ratio of window_area / external_wall_area,
    including door_area if flagged.

    Returns a float WWR in [0,1].
    """
    # Example usage if your building_row has columns:
    # 'window_area_m2', 'exterior_wall_area_m2', 'door_area_m2'
    ext_wall_area = building_row.get("exterior_wall_area_m2", 100.0)
    if ext_wall_area <= 0:
        return 0.0

    window_area = building_row.get("window_area_m2", 0.0)
    if include_doors_in_wwr:
        door_area = building_row.get("door_area_m2", 0.0)
        window_area += door_area

    return window_area / ext_wall_area
