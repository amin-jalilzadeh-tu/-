# eequip/assign_equip_values.py

import random
from .equip_lookup import equip_lookup
from .overrides_helper import find_applicable_overrides  # if you use override logic

def assign_equipment_parameters(
    building_id: int,
    building_type: str,
    age_range=None,
    calibration_stage: str = "pre_calibration",
    strategy: str = "A",
    random_seed: int = None,
    user_config: list = None,     # override table (list of dicts)
    assigned_log: dict = None     # optional dictionary to store final picks
):
    """
    Returns a dict with "equip_wm2", "tD", "tN", etc. for electric equipment.

    Steps:
      1) Check calibration_stage in equip_lookup; else fallback to "pre_calibration".
      2) Get the dictionary for building_type (if missing => pick some default).
      3) If user_config is provided, find all matching override rows for (building_id, building_type, age_range).
      4) For each matching row, override the param's range (min_val, max_val).
      5) Pick final value from the resulting range using 'strategy':
         - A => midpoint
         - B => random
         - else => pick the min_val
      6) Return assigned dictionary, optionally log it in assigned_log[building_id].
    """

    if random_seed is not None:
        random.seed(random_seed)

    # 1) Grab the stage dictionary or fallback
    if calibration_stage not in equip_lookup:
        calibration_stage = "pre_calibration"
    stage_dict = equip_lookup[calibration_stage]

    # 2) Fallback if building_type not found
    if building_type not in stage_dict:
        # Minimal fallback approach
        equip_rng = (3.0, 3.0)
        tD_rng    = (500, 500)
        tN_rng    = (200, 200)
    else:
        param_dict = stage_dict[building_type]
        equip_rng = param_dict.get("EQUIP_WM2_range", (3.0, 3.0))
        tD_rng    = param_dict.get("tD_range", (500, 500))
        tN_rng    = param_dict.get("tN_range", (200, 200))

    # 3) Find override rows
    if user_config is not None:
        matches = find_applicable_overrides(building_id, building_type, age_range, user_config)
    else:
        matches = []

    # 4) Apply overrides
    for row in matches:
        pname = row["param_name"]  # e.g. "equip_wm2", "tD", "tN"
        mn = row["min_val"]
        mx = row["max_val"]

        # Update the relevant range
        if pname == "equip_wm2":
            equip_rng = (mn, mx)
        elif pname == "tD":
            tD_rng = (mn, mx)
        elif pname == "tN":
            tN_rng = (mn, mx)
        # else ignore

    # 5) Strategy to pick final values
    def pick_val(r):
        if strategy == "A":  # midpoint
            return (r[0] + r[1]) / 2.0
        elif strategy == "B":  # random
            return random.uniform(r[0], r[1])
        else:
            return r[0]

    assigned = {
        "equip_wm2": pick_val(equip_rng),
        "tD": pick_val(tD_rng),
        "tN": pick_val(tN_rng)
    }

    # 6) Optional logging
    if assigned_log is not None:
        assigned_log[building_id] = assigned

    return assigned
