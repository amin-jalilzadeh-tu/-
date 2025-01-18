# fenez/assign_fenestration_values.py

from .materials_config import get_extended_materials_data, compute_wwr

def assign_fenestration_parameters(
    building_row,
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config_fenez=None,
    use_computed_wwr=False,
    include_doors_in_wwr=False
):
    """
    Retrieve the final Window-to-Wall Ratio (WWR) for a building, optionally
    computing it from sub-element areas (windows, doors, etc.). Then return
    (final_wwr, wwr_range_used).

    Parameters
    ----------
    building_row : dict
        A dictionary of building attributes (function, type, age_range, etc.).
    scenario : str
        E.g. "scenario1".
    calibration_stage : str
        E.g. "pre_calibration".
    strategy : str
        "A" => pick midpoint in ranges; "B" => pick random uniform.
    random_seed : int
        If you want reproducible random picks.
    user_config_fenez : dict
        Optional override dictionary for fenestration parameters (WWR, materials, etc.).
    use_computed_wwr : bool
        If True => compute the WWR from the sub-element areas in materials_config.py.
        If False => use the wwr range & final wwr from the dictionary.
    include_doors_in_wwr : bool
        If True => treat door area as part of fenestration area when computing WWR.

    Returns
    -------
    (final_wwr, wwr_range_used) : (float, tuple or None)
        final_wwr => the numeric WWR (0.0–1.0).
        wwr_range_used => the range that was used to pick the WWR, or None if computed.
    """

    # 1) Identify building function & type
    bldg_func = building_row.get("building_function", "residential")
    if bldg_func.lower() == "residential":
        building_type = building_row.get("residential_type", "UnknownHouseType")
    else:
        building_type = building_row.get("non_residential_type", "UnknownNonResType")

    # 2) Age range & scenario
    age_range = building_row.get("age_range", "2015 and later")

    # 3) Retrieve all fenestration/material data
    #    This returns a dict containing e.g.:
    #    {
    #      "wwr": 0.32,
    #      "wwr_range_used": (0.3, 0.35),
    #      "elements": {...},
    #      ...
    #    }
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

    # 4) Decide how to finalize the WWR
    #    By default, we use data["wwr"] which was either:
    #      - random/midpoint pick from wwr_range
    #      - or user_config_fenez["wwr"] if present
    final_wwr = data["wwr"]
    wwr_range_used = data.get("wwr_range_used", None)

    if use_computed_wwr:
        # Overwrite final_wwr by actually computing from the sub-element areas
        elements_dict = data.get("elements", {})
        final_wwr = compute_wwr(elements_dict, include_doors=include_doors_in_wwr)
        # In this scenario, we might say wwr_range_used = None
        wwr_range_used = None

    return final_wwr, wwr_range_used
