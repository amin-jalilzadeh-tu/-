# fenez/fenestration.py

def add_fenestration(
    idf,
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
    1) Compute or retrieve the final WWR using assign_fenestration_parameters(...).
    2) Remove existing FENESTRATIONSURFACE:DETAILED from the IDF.
    3) Use geomeppy.IDF.set_wwr(...) to create new window surfaces referencing "Window1C".
    4) (Optional) Log WWR range used, plus the new fenestration surface names.

    Parameters
    ----------
    idf : geomeppy.IDF
        The IDF to modify
    building_row : dict
        Contains building info (ogc_fid, function, type, etc.)
    scenario, calibration_stage, strategy, random_seed : str / int
        Passed through to assign_fenestration_parameters
    user_config_fenez : dict
        Optional overrides for fenestration
    assigned_fenez_log : dict
        If provided, we log WWR picks & fenestration object names under
        assigned_fenez_log[building_id].
    use_computed_wwr : bool
        If True, compute WWR from sub-element areas (windows, doors, etc.),
        else pick from wwr_range in the dictionary.
    include_doors_in_wwr : bool
        If True, door area is included in the fenestration area for the WWR ratio.
    """

    from geomeppy import IDF as GeppyIDF
    from .assign_fenestration_values import assign_fenestration_parameters

    # 1) Assign fenestration parameters (including final WWR).
    wwr, wwr_range_used = assign_fenestration_parameters(
        building_row=building_row,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_fenez=user_config_fenez,
        use_computed_wwr=use_computed_wwr,
        include_doors_in_wwr=include_doors_in_wwr
        # assigned_fenez_log is not passed here, so
        # we do our own logging below in this function
    )

    # (Optional) Log the final WWR, WWR range in assigned_fenez_log
    bldg_id = building_row.get("ogc_fid", None)
    if assigned_fenez_log and bldg_id is not None:
        if bldg_id not in assigned_fenez_log:
            assigned_fenez_log[bldg_id] = {}
        assigned_fenez_log[bldg_id]["fenez_final_wwr"] = wwr
        if wwr_range_used is not None:
            assigned_fenez_log[bldg_id]["fenez_wwr_range_used"] = wwr_range_used

    # 2) Remove any existing fenestration objects
    fen_objects = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]
    del fen_objects[:]

    # 3) Use geomeppy to create new window surfaces
    #    We assume the construction "Window1C" exists in the IDF
    GeppyIDF.set_wwr(idf, wwr=wwr, construction="Window1C")

    # 4) (Optional) After creating them, log the new fenestration surface names.
    new_fens = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]
    if assigned_fenez_log and bldg_id is not None and new_fens:
        assigned_fenez_log[bldg_id]["fenez_fenestration_objects"] = [
            fen.Name for fen in new_fens
        ]

    print(f"[add_fenestration] Building: {bldg_id} => WWR={wwr:.3f}, used Window1C")
