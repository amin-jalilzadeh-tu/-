# Elec/assign_lighting_values.py

import random
from .lighting_lookup import lighting_lookup
from .constants import (
    DEFAULT_LIGHTING_WM2,
    DEFAULT_PARASITIC_WM2,
    DEFAULT_TD,
    DEFAULT_TN,
    # If needed:
    # DEFAULT_EQUIP_FRACTION_LOST,
)
from .overrides_helper import find_applicable_overrides


def assign_lighting_parameters(
    building_id: int,
    building_type: str,
    age_range=None,
    calibration_stage: str = "pre_calibration",
    strategy: str = "A",
    random_seed: int = None,
    user_config: list = None,     # list of override dicts from lighting.json
    assigned_log: dict = None     # optional dictionary to store final picks
):
    """
    Determines final lighting parameters for a given building,
    merging any user overrides from `lighting.json` with default 
    ranges found in lighting_lookup[calibration_stage][building_type].

    The returned dict has keys like "lights_wm2", "parasitic_wm2", 
    "tD", "tN", "lights_fraction_radiant", etc. Each key maps to a
    sub-dict of the form:
      {
        "assigned_value": float,
        "min_val": float,
        "max_val": float,
        "object_name": "LIGHTS" or "ELECTRICEQUIPMENT" etc.
      }

    Steps:
      1) Identify default ranges from `lighting_lookup[calibration_stage][building_type]`.
         If building_type not found, fallback to constants.
      2) If user_config is provided, find all rows that match (building_id, building_type, age_range).
      3) Override the relevant ranges with those rows (either fixed_value => (v,v) or min_val/max_val).
      4) Pick the final assigned value from the resulting range using strategy:
         - "A" => midpoint
         - "B" => random.uniform
         - else => pick the lower bound
      5) Construct a final dict describing the assigned values 
         and (optionally) store in assigned_log[building_id].

    Parameters
    ----------
    building_id : int
        Unique identifier for the building (e.g. ogc_fid).
    building_type : str
        A string matching the keys in lighting_lookup[stage], e.g. "Residential" or "Non-Residential".
    age_range : str, optional
        If you want to filter overrides by age_range.
    calibration_stage : str, default "pre_calibration"
        Typically "pre_calibration" or "post_calibration" (used as a top-level key in lighting_lookup).
    strategy : {"A","B"}, default "A"
        "A" => pick midpoint in [min_val, max_val], "B" => pick random in that range.
    random_seed : int, optional
        If you want reproducible random picks, pass an integer seed.
    user_config : list of dicts, optional
        The override data from lighting.json. Each dict can have fields like:
          {
             "building_id": 4136730,
             "building_type": "Residential",
             "param_name": "lights_wm2",
             "min_val": 8.0,
             "max_val": 10.0
          }
        or "fixed_value": ...
    assigned_log : dict, optional
        If provided, the final structured picks are stored as assigned_log[building_id].

    Returns
    -------
    dict
        A dictionary describing final picks, e.g.:
        {
          "lights_wm2": {
            "assigned_value": 9.0,
            "min_val": 8.0,
            "max_val": 10.0,
            "object_name": "LIGHTS"
          },
          ...
        }
    """

    # (A) Set random seed if specified
    if random_seed is not None:
        random.seed(random_seed)

    # (B) Get the "stage_dict" for the given calibration_stage
    if calibration_stage not in lighting_lookup:
        calibration_stage = "pre_calibration"
    stage_dict = lighting_lookup[calibration_stage]

    # Convert building_type to a consistent case if needed, e.g. "Residential" => "Residential"
    # and "non_residential" => "Non-Residential" if that's your dictionary's exact key.
    # Example:
    if building_type.lower() == "residential":
        building_type = "Residential"
    elif building_type.lower() == "non_residential":
        building_type = "Non-Residential"

    # (C) If building_type not in the stage dict => fallback to "defaults"
    if building_type not in stage_dict:
        # Fallback block
        fallback = {
            "lights_wm2": {
                "assigned_value": DEFAULT_LIGHTING_WM2,
                "min_val": DEFAULT_LIGHTING_WM2,
                "max_val": DEFAULT_LIGHTING_WM2,
                "object_name": "LIGHTS"
            },
            "parasitic_wm2": {
                "assigned_value": DEFAULT_PARASITIC_WM2,
                "min_val": DEFAULT_PARASITIC_WM2,
                "max_val": DEFAULT_PARASITIC_WM2,
                "object_name": "ELECTRICEQUIPMENT"
            },
            "tD": {
                "assigned_value": DEFAULT_TD,
                "min_val": DEFAULT_TD,
                "max_val": DEFAULT_TD,
                "object_name": "LIGHTS_SCHEDULE"
            },
            "tN": {
                "assigned_value": DEFAULT_TN,
                "min_val": DEFAULT_TN,
                "max_val": DEFAULT_TN,
                "object_name": "LIGHTS_SCHEDULE"
            },
            "lights_fraction_radiant": {
                "assigned_value": 0.7,
                "min_val": 0.7,
                "max_val": 0.7,
                "object_name": "LIGHTS.Fraction_Radiant"
            },
            "lights_fraction_visible": {
                "assigned_value": 0.2,
                "min_val": 0.2,
                "max_val": 0.2,
                "object_name": "LIGHTS.Fraction_Visible"
            },
            "lights_fraction_replaceable": {
                "assigned_value": 1.0,
                "min_val": 1.0,
                "max_val": 1.0,
                "object_name": "LIGHTS.Fraction_Replaceable"
            },
            "equip_fraction_radiant": {
                "assigned_value": 0.0,
                "min_val": 0.0,
                "max_val": 0.0,
                "object_name": "ELECTRICEQUIPMENT.Fraction_Radiant"
            },
            "equip_fraction_lost": {
                "assigned_value": 1.0,
                "min_val": 1.0,
                "max_val": 1.0,
                "object_name": "ELECTRICEQUIPMENT.Fraction_Lost"
            }
        }
        if assigned_log is not None:
            assigned_log[building_id] = fallback
        return fallback

    # Otherwise, retrieve the param_dict for that building_type
    param_dict = stage_dict[building_type]

    # (D) Extract default ranges
    lights_rng    = param_dict.get("LIGHTS_WM2_range", (DEFAULT_LIGHTING_WM2, DEFAULT_LIGHTING_WM2))
    parasitic_rng = param_dict.get("PARASITIC_WM2_range", (DEFAULT_PARASITIC_WM2, DEFAULT_PARASITIC_WM2))
    tD_rng        = param_dict.get("tD_range", (DEFAULT_TD, DEFAULT_TD))
    tN_rng        = param_dict.get("tN_range", (DEFAULT_TN, DEFAULT_TN))

    lights_fraction_radiant_rng     = param_dict.get("lights_fraction_radiant_range", (0.7, 0.7))
    lights_fraction_visible_rng     = param_dict.get("lights_fraction_visible_range", (0.2, 0.2))
    lights_fraction_replace_rng     = param_dict.get("lights_fraction_replaceable_range", (1.0, 1.0))

    equip_fraction_radiant_rng = param_dict.get("equip_fraction_radiant_range", (0.0, 0.0))
    equip_fraction_lost_rng    = param_dict.get("equip_fraction_lost_range", (1.0, 1.0))

    # (E) Find any user overrides that apply
    if user_config is not None:
        matches = find_applicable_overrides(building_id, building_type, age_range, user_config)
    else:
        matches = []

    # Debug: See which overrides matched
    print(f"[DEBUG lighting] bldg_id={building_id}, type='{building_type}', matched overrides => {matches}")

    # (F) Override default ranges with user-config
    for row in matches:
        pname = row.get("param_name", "").strip().lower()
        fv = row.get("fixed_value", None)  # optional direct fix
        mn = row.get("min_val", None)
        mx = row.get("max_val", None)

        # If row has a fixed_value => treat it as (fv, fv)
        if fv is not None:
            rng = (float(fv), float(fv))
        elif mn is not None and mx is not None:
            rng = (float(mn), float(mx))
        else:
            rng = None

        if rng:
            if pname == "lights_wm2":
                lights_rng = rng
            elif pname == "parasitic_wm2":
                parasitic_rng = rng
            elif pname == "td":
                tD_rng = rng
            elif pname == "tn":
                tN_rng = rng
            elif pname == "lights_fraction_radiant":
                lights_fraction_radiant_rng = rng
            elif pname == "lights_fraction_visible":
                lights_fraction_visible_rng = rng
            elif pname == "lights_fraction_replaceable":
                lights_fraction_replace_rng = rng
            elif pname == "equip_fraction_radiant":
                equip_fraction_radiant_rng = rng
            elif pname == "equip_fraction_lost":
                equip_fraction_lost_rng = rng
            # else param_name not recognized => ignore

    # Helper to pick final value from a (min,max) range
    def pick_val(r):
        if strategy == "A":   # midpoint
            return (r[0] + r[1]) / 2.0
        elif strategy == "B": # random
            return random.uniform(r[0], r[1])
        else:
            # fallback => pick min
            return r[0]

    # (G) Pick final values
    assigned_lights = pick_val(lights_rng)
    assigned_paras  = pick_val(parasitic_rng)
    assigned_tD     = pick_val(tD_rng)
    assigned_tN     = pick_val(tN_rng)

    assigned_lights_frac_rad = pick_val(lights_fraction_radiant_rng)
    assigned_lights_frac_vis = pick_val(lights_fraction_visible_rng)
    assigned_lights_frac_rep = pick_val(lights_fraction_replace_rng)
    assigned_equip_frac_rad  = pick_val(equip_fraction_radiant_rng)
    assigned_equip_frac_lost = pick_val(equip_fraction_lost_rng)

    # (H) Build final dict
    assigned = {
        "lights_wm2": {
            "assigned_value": assigned_lights,
            "min_val": lights_rng[0],
            "max_val": lights_rng[1],
            "object_name": "LIGHTS"
        },
        "parasitic_wm2": {
            "assigned_value": assigned_paras,
            "min_val": parasitic_rng[0],
            "max_val": parasitic_rng[1],
            "object_name": "ELECTRICEQUIPMENT"
        },
        "tD": {
            "assigned_value": assigned_tD,
            "min_val": tD_rng[0],
            "max_val": tD_rng[1],
            "object_name": "LIGHTS_SCHEDULE"
        },
        "tN": {
            "assigned_value": assigned_tN,
            "min_val": tN_rng[0],
            "max_val": tN_rng[1],
            "object_name": "LIGHTS_SCHEDULE"
        },

        "lights_fraction_radiant": {
            "assigned_value": assigned_lights_frac_rad,
            "min_val": lights_fraction_radiant_rng[0],
            "max_val": lights_fraction_radiant_rng[1],
            "object_name": "LIGHTS.Fraction_Radiant"
        },
        "lights_fraction_visible": {
            "assigned_value": assigned_lights_frac_vis,
            "min_val": lights_fraction_visible_rng[0],
            "max_val": lights_fraction_visible_rng[1],
            "object_name": "LIGHTS.Fraction_Visible"
        },
        "lights_fraction_replaceable": {
            "assigned_value": assigned_lights_frac_rep,
            "min_val": lights_fraction_replace_rng[0],
            "max_val": lights_fraction_replace_rng[1],
            "object_name": "LIGHTS.Fraction_Replaceable"
        },

        "equip_fraction_radiant": {
            "assigned_value": assigned_equip_frac_rad,
            "min_val": equip_fraction_radiant_rng[0],
            "max_val": equip_fraction_radiant_rng[1],
            "object_name": "ELECTRICEQUIPMENT.Fraction_Radiant"
        },
        "equip_fraction_lost": {
            "assigned_value": assigned_equip_frac_lost,
            "min_val": equip_fraction_lost_rng[0],
            "max_val": equip_fraction_lost_rng[1],
            "object_name": "ELECTRICEQUIPMENT.Fraction_Lost"
        }
    }

    # (I) Optionally store in assigned_log
    if assigned_log is not None:
        assigned_log[building_id] = assigned

    return assigned
