# Elec/assign_lighting_values.py

import random
from .lighting_lookup import lighting_lookup
from .constants import (
    DEFAULT_LIGHTING_WM2,
    DEFAULT_PARASITIC_WM2,
    DEFAULT_TD,
    DEFAULT_TN,
    DEFAULT_EQUIP_FRACTION_LOST,
    
)
from .overrides_helper import find_applicable_overrides


def assign_lighting_parameters(
    building_id: int,
    building_type: str,
    age_range=None,
    calibration_stage: str = "pre_calibration",
    strategy: str = "A",
    random_seed: int = None,
    user_config: list = None,     # override table
    assigned_log: dict = None     # optional dictionary to store final picks
):
    """
    Returns a dict with each param as a sub-dict, for example:
      {
        "lights_wm2": {
           "assigned_value": <float>,
           "min_val": <float>,
           "max_val": <float>,
           "object_name": "LIGHTS"
        },
        "parasitic_wm2": { ... },
        "tD": { ... },
        "tN": { ... },

        "lights_fraction_radiant": {
           "assigned_value": <float>,
           "min_val": <float>,
           "max_val": <float>,
           "object_name": "LIGHTS.Fraction_Radiant"
        },
        ... etc. ...
      }

    Steps:
      1) Grab default ranges from lighting_lookup[calibration_stage][building_type].
      2) Find all matching user_config override rows for (building_id, building_type, age_range).
      3) If any row => override (min_val, max_val) or fix the value.
      4) Pick final value from the resulting range using strategy ("A"=midpoint, "B"=random).
      5) Log into assigned_log[building_id] if provided.
    """

    # Optionally seed the RNG for reproducible picks
    if random_seed is not None:
        random.seed(random_seed)

    # 1) Check calibration_stage in the lookup
    if calibration_stage not in lighting_lookup:
        calibration_stage = "pre_calibration"
    stage_dict = lighting_lookup[calibration_stage]

    # 2) Fallback if building_type not found
    if building_type not in stage_dict:
        # Return defaults (example fallback)
        fallback = {
            # Basic power densities + tD/tN
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

            # Fraction parameters for LIGHTS
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

            # Fraction parameters for ELECTRICEQUIPMENT
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

    # Extract default ranges from the table
    param_dict = stage_dict[building_type]

    # Basic power densities + burning hours
    lights_rng    = param_dict.get("LIGHTS_WM2_range", (DEFAULT_LIGHTING_WM2, DEFAULT_LIGHTING_WM2))
    parasitic_rng = param_dict.get("PARASITIC_WM2_range", (DEFAULT_PARASITIC_WM2, DEFAULT_PARASITIC_WM2))
    tD_rng        = param_dict.get("tD_range", (DEFAULT_TD, DEFAULT_TD))
    tN_rng        = param_dict.get("tN_range", (DEFAULT_TN, DEFAULT_TN))

    # Fraction parameters for LIGHTS
    lights_fraction_radiant_rng = param_dict.get("lights_fraction_radiant_range", (0.7, 0.7))
    lights_fraction_visible_rng = param_dict.get("lights_fraction_visible_range", (0.2, 0.2))
    lights_fraction_replaceable_rng = param_dict.get("lights_fraction_replaceable_range", (1.0, 1.0))

    # Fraction parameters for ELECTRICEQUIPMENT
    equip_fraction_radiant_rng = param_dict.get("equip_fraction_radiant_range", (0.0, 0.0))
    equip_fraction_lost_rng    = param_dict.get("equip_fraction_lost_range", (1.0, 1.0))

    # 3) Find override rows (if any)
    if user_config is not None:
        matches = find_applicable_overrides(building_id, building_type, age_range, user_config)
    else:
        matches = []

    # 4) Apply overrides
    for row in matches:
        pname = row.get("param_name", "").strip().lower()
        fv = row.get("fixed_value", None)
        mn = row.get("min_val", None)
        mx = row.get("max_val", None)

        # If we have a fixed_value => (fv, fv), else (mn, mx)
        if fv is not None:
            rng = (float(fv), float(fv))
        elif (mn is not None and mx is not None):
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
                lights_fraction_replaceable_rng = rng

            elif pname == "equip_fraction_radiant":
                equip_fraction_radiant_rng = rng
            elif pname == "equip_fraction_lost":
                equip_fraction_lost_rng = rng
            # else ignore unknown param_name

    # Helper to pick final value from a range
    def pick_val(r):
        if strategy == "A":  # midpoint
            val = (r[0] + r[1]) / 2.0
        elif strategy == "B":  # random
            val = random.uniform(r[0], r[1])
        else:
            # fallback or more logic if needed
            val = r[0]
        return val

    # 5) Pick final values
    assigned_lights = pick_val(lights_rng)
    assigned_paras = pick_val(parasitic_rng)
    assigned_tD = pick_val(tD_rng)
    assigned_tN = pick_val(tN_rng)

    assigned_lights_fraction_radiant = pick_val(lights_fraction_radiant_rng)
    assigned_lights_fraction_visible = pick_val(lights_fraction_visible_rng)
    assigned_lights_fraction_replace = pick_val(lights_fraction_replaceable_rng)
    assigned_equip_fraction_radiant  = pick_val(equip_fraction_radiant_rng)
    assigned_equip_fraction_lost     = pick_val(equip_fraction_lost_rng)

    # 6) Construct final structured dict
    assigned = {
        # Basic power densities + tD/tN
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

        # Fraction parameters (LIGHTS)
        "lights_fraction_radiant": {
            "assigned_value": assigned_lights_fraction_radiant,
            "min_val": lights_fraction_radiant_rng[0],
            "max_val": lights_fraction_radiant_rng[1],
            "object_name": "LIGHTS.Fraction_Radiant"
        },
        "lights_fraction_visible": {
            "assigned_value": assigned_lights_fraction_visible,
            "min_val": lights_fraction_visible_rng[0],
            "max_val": lights_fraction_visible_rng[1],
            "object_name": "LIGHTS.Fraction_Visible"
        },
        "lights_fraction_replaceable": {
            "assigned_value": assigned_lights_fraction_replace,
            "min_val": lights_fraction_replaceable_rng[0],
            "max_val": lights_fraction_replaceable_rng[1],
            "object_name": "LIGHTS.Fraction_Replaceable"
        },

        # Fraction parameters (ELECTRICEQUIPMENT)
        "equip_fraction_radiant": {
            "assigned_value": assigned_equip_fraction_radiant,
            "min_val": equip_fraction_radiant_rng[0],
            "max_val": equip_fraction_radiant_rng[1],
            "object_name": "ELECTRICEQUIPMENT.Fraction_Radiant"
        },
        "equip_fraction_lost": {
            "assigned_value": assigned_equip_fraction_lost,
            "min_val": equip_fraction_lost_rng[0],
            "max_val": equip_fraction_lost_rng[1],
            "object_name": "ELECTRICEQUIPMENT.Fraction_Lost"
        }
    }

    # 7) Log if needed
    if assigned_log is not None:
        assigned_log[building_id] = assigned

    return assigned
