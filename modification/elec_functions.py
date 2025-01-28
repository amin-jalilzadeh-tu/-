"""
elec_functions.py

Provides functions for applying lighting + parasitic equipment parameters
to an EnergyPlus IDF, analogous to hvac_functions or vent_functions.

Contents:
  1) create_elec_scenarios(...)
     - Takes df_lighting with columns [ogc_fid, object_name, param_name, assigned_value, min_val, max_val],
       generates scenario picks, and writes them to CSV.

  2) apply_building_level_elec(idf, param_dict)
     - A building-level approach: lumps all lighting/EQ loads into one or two IDF objects (LIGHTS, ELECTRICEQUIPMENT),
       referencing an existing zone list and referencing "LightsSchedule" or "ParasiticSchedule".

  3) apply_object_level_elec(idf, df_lighting)
     - A row-by-row approach: reads from a scenario DataFrame and updates each LIGHTS/ELECTRICEQUIPMENT object directly.
"""

import os
import random
import pandas as pd

# ---------------------------------------------------------------------------
# 1) CREATE ELEC SCENARIOS
# ---------------------------------------------------------------------------
def create_elec_scenarios(
    df_lighting,
    building_id,
    num_scenarios=5,
    picking_method="random_uniform",
    random_seed=42,
    scenario_csv_out=None
):
    """
    Generates a scenario-level DataFrame from "assigned_lighting.csv" rows:
      Each row has: ogc_fid, object_name, param_name, assigned_value, min_val, max_val

    If picking_method=="random_uniform" and min_val < max_val, picks a random float in [min_val, max_val].
    Otherwise keeps assigned_value as is.

    Final columns in df_scen:
      scenario_index, ogc_fid, object_name, param_name, param_value,
      param_min, param_max, picking_method

    If scenario_csv_out is provided, we write it to that CSV.

    Returns:
      pd.DataFrame: the scenario DataFrame
    """
    if random_seed is not None:
        random.seed(random_seed)

    # filter for the building
    df_bldg = df_lighting[df_lighting["ogc_fid"] == building_id].copy()
    if df_bldg.empty:
        print(f"[create_elec_scenarios] No lighting data found for building {building_id}")
        return pd.DataFrame()

    scenario_rows = []

    # For each scenario
    for s in range(num_scenarios):
        for row in df_bldg.itertuples():
            obj_name = row.object_name
            p_name   = row.param_name

            base_val = row.assigned_value
            p_min    = row.min_val
            p_max    = row.max_val

            new_val  = pick_value(base_val, p_min, p_max, picking_method)

            scenario_rows.append({
                "scenario_index":  s,
                "ogc_fid":         building_id,
                "object_name":     obj_name,
                "param_name":      p_name,
                "param_value":     new_val,
                "param_min":       p_min,
                "param_max":       p_max,
                "picking_method":  picking_method
            })

    df_scen = pd.DataFrame(scenario_rows)

    if scenario_csv_out:
        os.makedirs(os.path.dirname(scenario_csv_out), exist_ok=True)
        df_scen.to_csv(scenario_csv_out, index=False)
        print(f"[create_elec_scenarios] Wrote scenario file => {scenario_csv_out}")

    return df_scen


def pick_value(base_val, p_min, p_max, picking_method):
    """
    If picking_method=="random_uniform" and p_min/p_max are numeric and p_min< p_max,
    pick a random float in [p_min, p_max].
    Otherwise keep base_val as is.
    """
    try:
        base_float = float(base_val)
    except:
        base_float = None

    if picking_method == "random_uniform":
        try:
            fmin = float(p_min)
            fmax = float(p_max)
            if fmax > fmin:
                return random.uniform(fmin, fmax)
        except:
            pass
    # fallback
    return base_val

# ---------------------------------------------------------------------------
# 2) APPLY BUILDING-LEVEL ELECTRICAL PARAMETERS
# ---------------------------------------------------------------------------
def apply_building_level_elec(idf, param_dict, zonelist_name="ALL_ZONES"):
    """
    Interprets a dictionary of lighting/electrical parameters, e.g.:

      param_dict = {
        "lights_wm2": 19.2788535969,
        "parasitic_wm2": 0.285,
        "lights_fraction_radiant": 0.7,
        "lights_fraction_visible": 0.2,
        "lights_fraction_replaceable": 1.0,
        "equip_fraction_radiant": 0.0,
        "equip_fraction_lost": 1.0,
        "lights_schedule_name": "LightsSchedule",      # <--- optional override
        "equip_schedule_name": "ParasiticSchedule"     # <--- optional override
      }

    Then we create or update:
      - One LIGHTS object for the entire building (via `zonelist_name`).
      - One ELECTRICEQUIPMENT object for parasitic loads.

    We reference existing schedules (e.g. "LightsSchedule" or "ParasiticSchedule")
    from the base IDF (instead of "AlwaysOn").
    """

    # Extract numeric picks
    lights_wm2          = float(param_dict.get("lights_wm2", 10.0))
    parasitic_wm2       = float(param_dict.get("parasitic_wm2", 0.285))
    lights_frac_radiant = float(param_dict.get("lights_fraction_radiant", 0.7))
    lights_frac_visible = float(param_dict.get("lights_fraction_visible", 0.2))
    lights_frac_replace = float(param_dict.get("lights_fraction_replaceable", 1.0))
    equip_frac_radiant  = float(param_dict.get("equip_fraction_radiant", 0.0))
    equip_frac_lost     = float(param_dict.get("equip_fraction_lost", 1.0))

    # Which schedules to use (must exist in your base IDF).
    # If param_dict doesn't have them, we default to "LightsSchedule" / "ParasiticSchedule".
    lights_sched_name = param_dict.get("lights_schedule_name", "LightsSchedule")
    equip_sched_name  = param_dict.get("equip_schedule_name",  "ParasiticSchedule")

    print("[ELEC] => Building-level electrical picks:")
    print(f"  lights_wm2={lights_wm2}, parasitic_wm2={parasitic_wm2}")
    print(f"  lights_frac_radiant={lights_frac_radiant}, visible={lights_frac_visible}, replaceable={lights_frac_replace}")
    print(f"  equip_frac_radiant={equip_frac_radiant}, equip_frac_lost={equip_frac_lost}")
    print(f"  schedules => lights={lights_sched_name}, equip={equip_sched_name}")

    # Create/update LIGHTS object
    lights_obj_name = f"Lights_{zonelist_name}"
    lights_obj = _create_or_update_lights_object(
        idf=idf,
        obj_name=lights_obj_name,
        zone_or_zonelist=zonelist_name,
        lights_wm2=lights_wm2,
        frac_radiant=lights_frac_radiant,
        frac_visible=lights_frac_visible,
        frac_replace=lights_frac_replace,
        lights_schedule_name=lights_sched_name
    )

    # Create/update ELECTRICEQUIPMENT object
    equip_obj_name = f"Equip_{zonelist_name}"
    equip_obj = _create_or_update_equip_object(
        idf=idf,
        obj_name=equip_obj_name,
        zone_or_zonelist=zonelist_name,
        equip_wm2=parasitic_wm2,
        frac_radiant=equip_frac_radiant,
        frac_lost=equip_frac_lost,
        equip_schedule_name=equip_sched_name
    )

    return lights_obj, equip_obj


def _create_or_update_lights_object(
    idf,
    obj_name,
    zone_or_zonelist="ALL_ZONES",
    lights_wm2=10.0,
    frac_radiant=0.7,
    frac_visible=0.2,
    frac_replace=1.0,
    lights_schedule_name="LightsSchedule"
):
    """
    Creates/updates a LIGHTS object with 'Watts/Area' method,
    referencing an existing schedule (lights_schedule_name).
    """
    existing = [
        lt for lt in idf.idfobjects["LIGHTS"]
        if lt.Name.upper() == obj_name.upper()
    ]
    if existing:
        lights_obj = existing[0]
    else:
        lights_obj = idf.newidfobject("LIGHTS", Name=obj_name)

    # zone or zone list
    if hasattr(lights_obj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
        lights_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_or_zonelist
    else:
        lights_obj.Zone_or_ZoneList_Name = zone_or_zonelist

    # design method
    lights_obj.Design_Level_Calculation_Method = "Watts/Area"
    lights_obj.Watts_per_Zone_Floor_Area = lights_wm2

    # use the existing lighting schedule from your base IDF
    lights_obj.Schedule_Name = lights_schedule_name

    # fractions
    if hasattr(lights_obj, "Fraction_Radiant"):
        lights_obj.Fraction_Radiant = frac_radiant
    if hasattr(lights_obj, "Fraction_Visible"):
        lights_obj.Fraction_Visible = frac_visible
    if hasattr(lights_obj, "Fraction_Replaceable"):
        lights_obj.Fraction_Replaceable = frac_replace

    return lights_obj


def _create_or_update_equip_object(
    idf,
    obj_name,
    zone_or_zonelist="ALL_ZONES",
    equip_wm2=0.285,
    frac_radiant=0.0,
    frac_lost=1.0,
    equip_schedule_name="ParasiticSchedule"
):
    """
    Creates/updates an ELECTRICEQUIPMENT object with 'Watts/Area' method,
    referencing an existing schedule (equip_schedule_name).
    """
    existing = [
        eq for eq in idf.idfobjects["ELECTRICEQUIPMENT"]
        if eq.Name.upper() == obj_name.upper()
    ]
    if existing:
        equip_obj = existing[0]
    else:
        equip_obj = idf.newidfobject("ELECTRICEQUIPMENT", Name=obj_name)

    if hasattr(equip_obj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
        equip_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_or_zonelist
    else:
        equip_obj.Zone_or_ZoneList_Name = zone_or_zonelist

    equip_obj.Design_Level_Calculation_Method = "Watts/Area"
    equip_obj.Watts_per_Zone_Floor_Area = equip_wm2

    # use the existing equipment schedule from your base IDF
    equip_obj.Schedule_Name = equip_schedule_name

    # fraction fields
    if hasattr(equip_obj, "Fraction_Radiant"):
        equip_obj.Fraction_Radiant = frac_radiant
    if hasattr(equip_obj, "Fraction_Lost"):
        equip_obj.Fraction_Lost = frac_lost

    return equip_obj

# ---------------------------------------------------------------------------
# 3) APPLY OBJECT-LEVEL ELECTRIC PARAMETERS
# ---------------------------------------------------------------------------
def apply_object_level_elec(idf, df_lighting):
    """
    Reads a scenario DataFrame with columns:
      [ogc_fid, object_name, param_name, param_value, param_min, param_max, ...]
    For each object_name, we parse param_name=>param_value pairs
    and update or create the corresponding IDF object.

    e.g. assigned_lighting.csv might have:
      ogc_fid, object_name, param_name, assigned_value, ...
      4136730, LIGHTS, lights_wm2, 19.2788535969
      4136730, ELECTRICEQUIPMENT, parasitic_wm2, 0.285
      4136730, LIGHTS.Fraction_Radiant, lights_fraction_radiant, 0.7
      ...

    Steps:
      1) group by object_name
      2) build a param_dict
      3) update the IDF object accordingly
    """
    object_groups = df_lighting.groupby("object_name")

    for obj_name, group_df in object_groups:
        print(f"[ELEC] Handling object_name='{obj_name}' with {len(group_df)} rows.")
        param_dict = {}
        for row in group_df.itertuples():
            p_name = row.param_name
            val    = row.param_value
            # attempt float
            try:
                param_dict[p_name] = float(val)
            except:
                param_dict[p_name] = val

        # Decide how to update the IDF object
        if obj_name.upper() == "LIGHTS":
            _update_generic_lights_obj(idf, "LIGHTS", param_dict)
        elif obj_name.upper() == "ELECTRICEQUIPMENT":
            _update_generic_equip_obj(idf, "ELECTRICEQUIPMENT", param_dict)
        elif "SCHEDULE" in obj_name.upper():
            pass  # e.g. "LIGHTS_SCHEDULE": your code for schedule logic
        else:
            print(f"[ELEC WARNING] Unknown object_name='{obj_name}', skipping or handle differently.")


def _update_generic_lights_obj(idf, obj_name, param_dict):
    """
    Example for updating a LIGHTS object named `obj_name`.
    param_dict might have "lights_wm2", "lights_fraction_radiant", etc.
    """
    existing = [lt for lt in idf.idfobjects["LIGHTS"] if lt.Name.upper() == obj_name.upper()]
    if existing:
        lights_obj = existing[0]
    else:
        lights_obj = idf.newidfobject("LIGHTS", Name=obj_name)

    if "lights_wm2" in param_dict:
        lights_obj.Design_Level_Calculation_Method = "Watts/Area"
        lights_obj.Watts_per_Zone_Floor_Area = float(param_dict["lights_wm2"])

    if "lights_fraction_radiant" in param_dict and hasattr(lights_obj, "Fraction_Radiant"):
        lights_obj.Fraction_Radiant = float(param_dict["lights_fraction_radiant"])

    if "lights_fraction_visible" in param_dict and hasattr(lights_obj, "Fraction_Visible"):
        lights_obj.Fraction_Visible = float(param_dict["lights_fraction_visible"])

    if "lights_fraction_replaceable" in param_dict and hasattr(lights_obj, "Fraction_Replaceable"):
        lights_obj.Fraction_Replaceable = float(param_dict["lights_fraction_replaceable"])


def _update_generic_equip_obj(idf, obj_name, param_dict):
    """
    Example for updating an ELECTRICEQUIPMENT object. param_dict might have:
      "parasitic_wm2", "equip_fraction_radiant", "equip_fraction_lost", etc.
    """
    existing = [eq for eq in idf.idfobjects["ELECTRICEQUIPMENT"] if eq.Name.upper() == obj_name.upper()]
    if existing:
        equip_obj = existing[0]
    else:
        equip_obj = idf.newidfobject("ELECTRICEQUIPMENT", Name=obj_name)

    if "parasitic_wm2" in param_dict:
        equip_obj.Design_Level_Calculation_Method = "Watts/Area"
        equip_obj.Watts_per_Zone_Floor_Area = float(param_dict["parasitic_wm2"])

    if "equip_fraction_radiant" in param_dict and hasattr(equip_obj, "Fraction_Radiant"):
        equip_obj.Fraction_Radiant = float(param_dict["equip_fraction_radiant"])

    if "equip_fraction_lost" in param_dict and hasattr(equip_obj, "Fraction_Lost"):
        equip_obj.Fraction_Lost = float(param_dict["equip_fraction_lost"])
