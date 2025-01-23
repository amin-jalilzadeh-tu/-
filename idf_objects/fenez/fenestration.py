"""
fenestration.py

Handles the creation or updating of fenestration (windows, etc.) in a geomeppy IDF.
It references final fenestration dictionaries (res_data, nonres_data) that
already incorporate Excel + user JSON overrides. 
"""

import pandas as pd
from geomeppy import IDF as GeppyIDF
from .assign_fenestration_values import assign_fenestration_parameters


def add_fenestration(
    idf,
    building_row,
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="B",
    random_seed=None,
    res_data=None,
    nonres_data=None,
    assigned_fenez_log=None,
    use_computed_wwr=False,
    include_doors_in_wwr=False
):
    """
    Adds fenestration to the given IDF for the specified building_row.

    Steps:
      1) Determine building function => use 'res_data' or 'nonres_data'.
      2) Call 'assign_fenestration_parameters(...)' to get final WWR or computed WWR.
      3) Remove existing fenestration surfaces.
      4) Use geomeppy 'idf.set_wwr(...)' to add windows with the final WWR.
      5) Log picks & new fenestration object names in 'assigned_fenez_log'.

    Parameters
    ----------
    idf : geomeppy.IDF
        The IDF to modify.
    building_row : dict or Series
        Contains building attributes like ogc_fid, building_function, age_range, orientation, etc.
    scenario, calibration_stage, strategy : str
        For passing to the assignment logic or logging.
    random_seed : int
        For reproducible random picks in the WWR range.
    res_data : dict
        Final fenestration dictionary for residential (Excel + user JSON merged).
    nonres_data : dict
        Final fenestration dictionary for non-res (Excel + user JSON merged).
    assigned_fenez_log : dict
        A place to store assigned picks for CSV logging later.
    use_computed_wwr : bool
        If True, compute WWR from sub-element areas (windows, doors, etc.) 
        rather than from the dictionary's wwr_range.
    include_doors_in_wwr : bool
        If True, door area is counted as fenestration in the WWR ratio.
    """

    # 1) Determine final WWR (and WWR range used)
    wwr, wwr_range_used = assign_fenestration_parameters(
        building_row=building_row,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        res_data=res_data,
        nonres_data=nonres_data,
        use_computed_wwr=use_computed_wwr,
        include_doors_in_wwr=include_doors_in_wwr
    )

    # 2) Log final picks
    bldg_id = building_row.get("ogc_fid", None)
    if assigned_fenez_log and bldg_id is not None:
        if bldg_id not in assigned_fenez_log:
            assigned_fenez_log[bldg_id] = {}
        assigned_fenez_log[bldg_id]["fenez_final_wwr"] = wwr
        if wwr_range_used is not None:
            assigned_fenez_log[bldg_id]["fenez_wwr_range_used"] = wwr_range_used

    # 3) Remove existing fenestration surfaces
    fen_objects = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]
    del fen_objects[:]  # clear them

    # 4) Use geomeppy to create new window surfaces
    #    We assume the construction "Window1C" already exists or will be created in materials step
    GeppyIDF.set_wwr(idf, wwr=wwr, construction="Window1C")

    # 5) Optional: Log fenestration object names
    new_fens = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]
    if assigned_fenez_log and bldg_id is not None and new_fens:
        # store the new fenestration object names
        assigned_fenez_log[bldg_id]["fenez_fenestration_objects"] = [
            fen.Name for fen in new_fens
        ]

    print(f"[add_fenestration] Building: {bldg_id} => WWR={wwr:.3f}, used Window1C")
