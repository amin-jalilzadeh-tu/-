# fenez/assign_fenestration_values.py

from .materials_config import get_extended_materials_data, compute_wwr

def assign_fenestration_parameters(
    building_row,
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config_fenez=None,
    assigned_fenez_log=None,
    use_computed_wwr=False,
    include_doors_in_wwr=False
):
    """
    Retrieve the final Window-to-Wall Ratio (WWR) for a building, optionally
    computing it from sub-element area data in materials_config.py.

    Parameters
    ----------
    building_row : dict
        A dictionary of building attributes (function, type, age_range, etc.).
    scenario : str
        E.g. "scenario1", "scenario2", etc. 
    calibration_stage : str
        E.g. "pre_calibration", "post_calibration".
    strategy : str
        "A" => pick midpoint in R/U ranges; "B" => pick random uniform. 
    random_seed : int
        If you want reproducible random picks.
    user_config_fenez : dict
        Optional override dictionary for fenestration parameters (WWR, materials).
    assigned_fenez_log : dict
        If provided, store the final WWR (and possibly other picks) under [building_id].
    use_computed_wwr : bool
        If True => compute the WWR from the sub-element areas for walls and windows
        (and optionally doors), else => use the wwr_range from the dictionary.
    include_doors_in_wwr : bool
        If True => when computing WWR, treat door area as part of fenestration.

    Returns
    -------
    final_wwr : float
        The final numeric WWR (0.0–1.0 typically).
    """

    # 1) Identify building function & type
    bldg_func = building_row.get("building_function", "residential")
    if bldg_func.lower() == "residential":
        building_type = building_row.get("residential_type", "UnknownHouseType")
    else:
        building_type = building_row.get("non_residential_type", "UnknownNonResType")

    age_range = building_row.get("age_range", "2015 and later")
    building_id = building_row.get("ogc_fid", None)

    # 2) Retrieve the full materials data dictionary for this building
    data = get_extended_materials_data(
        building_function=bldg_func,
        building_type=building_type,
        age_range=age_range,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_fenez=user_config_fenez
    )

    # 3) Decide how to get final WWR
    if not use_computed_wwr:
        # a) Use the wwr picked from data["wwr_range"]
        final_wwr = data["wwr"]
    else:
        # b) Compute from sub-elements
        elements_dict = data.get("elements", {})
        final_wwr = compute_wwr(elements_dict, include_doors=include_doors_in_wwr)

    # 4) Log the final WWR (if assigned_fenez_log is provided)
    if assigned_fenez_log is not None and building_id is not None:
        if building_id not in assigned_fenez_log:
            assigned_fenez_log[building_id] = {}
        assigned_fenez_log[building_id]["fenez_wwr"] = final_wwr

    return final_wwr
