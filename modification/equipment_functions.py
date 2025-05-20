"""equipment_functions.py

Provides helper functions for scenario generation and IDF updates for
building-level electric equipment loads. The overall style mirrors
``elec_functions.py`` but focuses on generic ELECTRICEQUIPMENT objects
that are separate from lighting/parasitic loads.
"""

import os
import pandas as pd
from idf_objects.eequip.schedules import create_equipment_schedule


# ---------------------------------------------------------------------------
# 1) CREATE EQUIPMENT SCENARIOS
# ---------------------------------------------------------------------------
def create_equipment_scenarios(
    df_equipment,
    building_id,
    num_scenarios=5,
    picking_method="random_uniform",
    random_seed=42,
    scenario_csv_out=None,
):
    """Build a scenario DataFrame from ``assigned_equipment.csv`` rows.

    Parameters
    ----------
    df_equipment : pd.DataFrame
        Rows for a single building with columns ``ogc_fid``, ``param_name`` and
        ``assigned_value``.
    building_id : int
        ID of the building we are processing.
    num_scenarios : int, default 5
        How many scenario rows to generate.
    picking_method : str, ignored for now
        Included for API compatibility.
    random_seed : int, optional
        Seed if future extensions use randomness.
    scenario_csv_out : str, optional
        Path to write ``scenario_params_equipment.csv``.
    """
    if random_seed is not None:
        import random
        random.seed(random_seed)

    df_bldg = df_equipment[df_equipment["ogc_fid"] == building_id].copy()
    if df_bldg.empty:
        print(f"[create_equipment_scenarios] No equipment data for building {building_id}")
        return pd.DataFrame()

    rows = []
    for s in range(num_scenarios):
        for row in df_bldg.itertuples():
            rows.append({
                "scenario_index": s,
                "ogc_fid": building_id,
                "param_name": row.param_name,
                "param_value": row.assigned_value,
                "param_min": None,
                "param_max": None,
                "picking_method": picking_method,
            })
    df_scen = pd.DataFrame(rows)

    if scenario_csv_out:
        os.makedirs(os.path.dirname(scenario_csv_out), exist_ok=True)
        df_scen.to_csv(scenario_csv_out, index=False)
        print(f"[create_equipment_scenarios] Wrote => {scenario_csv_out}")

    return df_scen


# ---------------------------------------------------------------------------
# 2) APPLY BUILDING-LEVEL EQUIPMENT PARAMETERS
# ---------------------------------------------------------------------------
def apply_building_level_equipment(idf, param_dict, zonelist_name="ALL_ZONES"):
    """Create or update a single ELECTRICEQUIPMENT object.

    ``param_dict`` typically contains at least ``equip_wm2``. Optional keys
    ``building_category`` and ``sub_type`` allow schedule generation using
    :func:`create_equipment_schedule`.
    """
    equip_wm2 = float(param_dict.get("equip_wm2", 3.0))
    bcat = param_dict.get("building_category", "Non-Residential")
    subtype = param_dict.get("sub_type", "Other Use Function")

    sched_name = create_equipment_schedule(
        idf,
        building_category=bcat,
        sub_type=subtype,
        schedule_name="EquipSchedule",
    )

    obj_name = f"Equip_{zonelist_name}"
    existing = [
        eq for eq in idf.idfobjects["ELECTRICEQUIPMENT"]
        if eq.Name.upper() == obj_name.upper()
    ]
    equip_obj = existing[0] if existing else idf.newidfobject("ELECTRICEQUIPMENT", Name=obj_name)

    if hasattr(equip_obj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
        equip_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zonelist_name
    else:
        equip_obj.Zone_or_ZoneList_Name = zonelist_name

    equip_obj.Schedule_Name = sched_name
    equip_obj.Design_Level_Calculation_Method = "Watts/Area"
    equip_obj.Watts_per_Zone_Floor_Area = equip_wm2

    return equip_obj


# ---------------------------------------------------------------------------
# 3) APPLY OBJECT-LEVEL EQUIPMENT PARAMETERS
# ---------------------------------------------------------------------------
def apply_object_level_equipment(idf, df_equipment):
    """Update ELECTRICEQUIPMENT objects row by row from a scenario DataFrame."""
    for row in df_equipment.itertuples():
        obj_name = row.object_name if hasattr(row, "object_name") else "ELECTRICEQUIPMENT"
        p_name = row.param_name
        val = row.param_value

        existing = [eq for eq in idf.idfobjects["ELECTRICEQUIPMENT"] if eq.Name.upper() == obj_name.upper()]
        equip_obj = existing[0] if existing else idf.newidfobject("ELECTRICEQUIPMENT", Name=obj_name)

        if p_name == "equip_wm2":
            equip_obj.Design_Level_Calculation_Method = "Watts/Area"
            equip_obj.Watts_per_Zone_Floor_Area = float(val)
        elif p_name == "Schedule_Name":
            equip_obj.Schedule_Name = val
        else:
            # Generic setter if attribute exists
            if hasattr(equip_obj, p_name):
                try:
                    setattr(equip_obj, p_name, float(val))
                except Exception:
                    setattr(equip_obj, p_name, val)

    return
