# vent_functions.py

"""
Contains functions for applying Ventilation & Infiltration parameters
to an IDF in a manner similar to hvac_functions.py and dhw_functions.py.
"""

import random

##############################################################################
# 1) APPLY BUILDING-LEVEL VENTILATION
##############################################################################

def apply_building_level_vent(idf, param_dict):
    """
    Takes a dict of building-level ventilation parameters, e.g. from
    assigned_vent_building.csv (after scenario picks). Example keys:
      {
        "infiltration_base": 1.2278853596915769,
        "infiltration_base_range": (1.1,1.3),
        "year_factor": 0.9050021510445334,
        "year_factor_range": (0.9,1.1),
        "fan_pressure": 0.0,
        "fan_pressure_range": (0.0,0.0),
        "f_ctrl": 0.9223210738148823,
        "f_ctrl_range": (0.9,1.0),
        "hrv_eff": 0.0,
        "hrv_eff_range": (0.0,0.0),
        "infiltration_schedule_name": "AlwaysOnSched",
        "ventilation_schedule_name": "VentSched_DayNight",
        "system_type": "A",
        "flow_exponent": 0.67,
        "infiltration_total_m3_s": 0.001979822,
        "ventilation_total_m3_s": 0.035
      }

    This function:
     - Loops over all ZONE objects in the IDF
     - Creates infiltration objects and ventilation objects for each zone
       (or uses IdealLoads if system_type=="D").
     - Splits infiltration_total_m3_s among the zones,
       splits ventilation_total_m3_s among the zones.
     - Applies infiltration_schedule_name / ventilation_schedule_name.

    If you already have infiltration/vent objects, it can update them
    (or you can handle that in a separate function).
    """

    zones = idf.idfobjects["ZONE"]
    if not zones:
        print("[VENT] No zones found; skipping infiltration/ventilation creation.")
        return

    infiltration_m3_s_total = param_dict.get("infiltration_total_m3_s", 0.0)
    ventilation_m3_s_total  = param_dict.get("ventilation_total_m3_s", 0.0)
    n_zones = len(zones)
    if n_zones < 1:
        return

    # We distribute total infiltration & ventilation evenly among the zones
    infil_per_zone = infiltration_m3_s_total / n_zones
    vent_per_zone  = ventilation_m3_s_total / n_zones

    infiltration_sched = param_dict.get("infiltration_schedule_name", "AlwaysOnSched")
    ventilation_sched  = param_dict.get("ventilation_schedule_name", "VentSched_DayNight")
    system_type        = param_dict.get("system_type", "A")

    print(f"[VENT] Applying building-level infiltration={infiltration_m3_s_total:.5f} m3/s, "
          f"ventilation={ventilation_m3_s_total:.5f} m3/s, system={system_type}, n_zones={n_zones}")

    for zone_obj in zones:
        zone_name = zone_obj.Name
        # 1) Create infiltration object
        iobj_name = f"Infil_{system_type}_{zone_name}"
        iobj = _create_or_update_infiltration(
            idf, iobj_name, zone_name, infil_per_zone, infiltration_sched
        )

        # 2) If system_type != "D" => create a ZONEVENTILATION:DESIGNFLOWRATE object
        #    If system_type == "D" => update zone's IdealLoads or skip
        if system_type.upper() == "D":
            # Balanced mechanical with HRV => we might rely on IdealLoads (like an infiltration stand-in)
            vobj = _attach_vent_to_ideal_loads(idf, zone_name, vent_per_zone)
        else:
            # create zone ventilation design flow
            vobj_name = f"Vent_{system_type}_{zone_name}"
            vobj = _create_or_update_ventilation(
                idf, vobj_name, zone_name, vent_per_zone, ventilation_sched
            )

        # Optionally log or print
        print(f"  => Zone {zone_name}: infiltration={infil_per_zone:.5f}, vent={vent_per_zone:.5f}")


def _create_or_update_infiltration(idf, obj_name, zone_name, infil_flow_m3_s, sched_name):
    """
    Creates or updates a ZONEINFILTRATION:DESIGNFLOWRATE object.
    """
    existing = [
        inf for inf in idf.idfobjects["ZONEINFILTRATION:DESIGNFLOWRATE"]
        if inf.Name == obj_name
    ]
    if existing:
        iobj = existing[0]
    else:
        iobj = idf.newidfobject("ZONEINFILTRATION:DESIGNFLOWRATE", Name=obj_name)

    if hasattr(iobj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
        iobj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_name
    else:
        iobj.Zone_or_ZoneList_Name = zone_name

    iobj.Schedule_Name = sched_name
    iobj.Design_Flow_Rate_Calculation_Method = "Flow/Zone"
    iobj.Design_Flow_Rate = infil_flow_m3_s
    return iobj


def _create_or_update_ventilation(idf, obj_name, zone_name, vent_flow_m3_s, sched_name):
    """
    Creates or updates a ZONEVENTILATION:DESIGNFLOWRATE object.
    """
    existing = [
        vent for vent in idf.idfobjects["ZONEVENTILATION:DESIGNFLOWRATE"]
        if vent.Name == obj_name
    ]
    if existing:
        vobj = existing[0]
    else:
        vobj = idf.newidfobject("ZONEVENTILATION:DESIGNFLOWRATE", Name=obj_name)

    if hasattr(vobj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
        vobj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_name
    else:
        vobj.Zone_or_ZoneList_Name = zone_name

    vobj.Schedule_Name = sched_name
    vobj.Design_Flow_Rate_Calculation_Method = "Flow/Zone"
    vobj.Design_Flow_Rate = vent_flow_m3_s
    return vobj


def _attach_vent_to_ideal_loads(idf, zone_name, vent_flow_m3_s):
    """
    If system_type=="D", we rely on ZONEHVAC:IDEALLOADSAIRSYSTEM for ventilation.
    Typically you'd set the supply air flow rates. We'll do a simple approach:
      - find <zone_name> Ideal Loads
      - set Maximum_Cooling_Air_Flow_Rate & Maximum_Heating_Air_Flow_Rate to vent_flow_m3_s
    Or store additional fields (like infiltration fraction).
    """
    ideal_name = f"{zone_name} Ideal Loads"
    ideal_obj = [
        ild for ild in idf.idfobjects["ZONEHVAC:IDEALLOADSAIRSYSTEM"]
        if ild.Name == ideal_name
    ]
    if not ideal_obj:
        print(f"[VENT WARNING] {zone_name} Ideal Loads not found; can't set vent flow. Skipping.")
        return None

    iobj = ideal_obj[0]
    # Example approach => "NoLimit" or "LimitFlowRate"
    iobj.Heating_Limit = "LimitFlowRate"
    iobj.Maximum_Heating_Air_Flow_Rate = vent_flow_m3_s
    iobj.Cooling_Limit = "LimitFlowRate"
    iobj.Maximum_Cooling_Air_Flow_Rate = vent_flow_m3_s

    # E+ allows infiltration to be done as well in the same object if desired,
    # but usually infiltration is a separate "ZONEINFILTRATION:DESIGNFLOWRATE".
    return iobj


##############################################################################
# 2) APPLY ZONE-LEVEL VENTILATION
##############################################################################

def apply_zone_level_vent(idf, df_zone_sub):
    """
    Given a DataFrame with columns like:
       ogc_fid, zone_name, param_name, param_value

    Specifically for infiltration & ventilation, you might have:
       zone_name, infiltration_object_name, infiltration_object_type, infiltration_flow_m3_s,
       infiltration_schedule_name, ventilation_object_name, ventilation_object_type,
       ventilation_flow_m3_s, ventilation_schedule_name

    For each row in df_zone_sub, create or update the infiltration + ventilation objects
    named as in param_value.

    Example row:
       ogc_fid=4136730, zone_name="Zone1", param_name="infiltration_object_name", param_value="Infil_A_Zone1"
       ...
    We can parse df_zone_sub row by row or group by zone_name.

    Steps:
      1) group by zone_name
      2) parse infiltration object name + type + flow + schedule
      3) parse ventilation object name + type + flow + schedule
      4) create or update these objects in the IDF.
    """
    # We'll group by "zone_name" so we can gather infiltration/vent info in a single pass.
    zone_groups = df_zone_sub.groupby("zone_name")

    for zone_name, zone_df in zone_groups:
        # We'll keep a local dictionary for infiltration & ventilation info
        infil_name = None
        infil_type = "ZONEINFILTRATION:DESIGNFLOWRATE"
        infil_flow = 0.0
        infil_sched = "AlwaysOnSched"

        vent_name = None
        vent_type = "ZONEVENTILATION:DESIGNFLOWRATE"
        vent_flow = 0.0
        vent_sched = "AlwaysOnSched"

        for row in zone_df.itertuples():
            pname = row.param_name
            val   = row.param_value

            # Try to interpret numeric fields
            try:
                val_float = float(val)
            except:
                val_float = None

            if pname == "infiltration_object_name":
                infil_name = val
            elif pname == "infiltration_object_type":
                infil_type = val
            elif pname == "infiltration_flow_m3_s" and val_float is not None:
                infil_flow = val_float
            elif pname == "infiltration_schedule_name":
                infil_sched = val

            elif pname == "ventilation_object_name":
                vent_name = val
            elif pname == "ventilation_object_type":
                vent_type = val
            elif pname == "ventilation_flow_m3_s" and val_float is not None:
                vent_flow = val_float
            elif pname == "ventilation_schedule_name":
                vent_sched = val

        # Now we have infiltration + vent parameters for zone_name
        # Create or update infiltration object
        iobj = _create_zone_level_object(
            idf, obj_name=infil_name, obj_type=infil_type,
            zone_name=zone_name,
            design_flow=infil_flow,
            sched_name=infil_sched
        )

        # Create or update ventilation (or attach to IdealLoads if type=ZONEHVAC:IDEALLOADSAIRSYSTEM)
        vobj = None
        if vent_type.upper() == "ZONEHVAC:IDEALLOADSAIRSYSTEM":
            # We interpret vent_name as the "Name" of an existing IdealLoads
            # Then set max flow to vent_flow, or we skip if not found
            ideal = idf.getobject(vent_type, vent_name.upper())
            if ideal:
                # set max flow
                ideal.Heating_Limit = "LimitFlowRate"
                ideal.Maximum_Heating_Air_Flow_Rate = vent_flow
                ideal.Cooling_Limit = "LimitFlowRate"
                ideal.Maximum_Cooling_Air_Flow_Rate = vent_flow
                vobj = ideal
                print(f"[VENT] Updated IdealLoads '{vent_name}' => flow={vent_flow:.5f}")
            else:
                print(f"[VENT WARNING] IdealLoads '{vent_name}' not found for zone '{zone_name}'.")
        else:
            # Assume "ZONEVENTILATION:DESIGNFLOWRATE"
            vobj = _create_zone_level_object(
                idf, obj_name=vent_name, obj_type=vent_type,
                zone_name=zone_name,
                design_flow=vent_flow,
                sched_name=vent_sched
            )

        print(f"Zone={zone_name} => infiltration={infil_name}@{infil_flow:.5f}, vent={vent_name}@{vent_flow:.5f}")


def _create_zone_level_object(idf, obj_name, obj_type, zone_name, design_flow, sched_name):
    """
    A helper that creates or updates a zone-level infiltration or ventilation object,
    depending on obj_type (e.g. "ZONEINFILTRATION:DESIGNFLOWRATE",
    "ZONEVENTILATION:DESIGNFLOWRATE", etc.).
    """
    if not obj_type:
        print(f"[VENT WARNING] No obj_type provided for zone {zone_name}, skipping.")
        return None
    if not obj_name:
        print(f"[VENT WARNING] No obj_name provided for zone {zone_name}, skipping.")
        return None

    # If the IDF doesn't have that object type, we skip
    # (E.g. if user typed 'ZONEINFILTRATION:DESIGNFLOWRATE' incorrectly)
    obj_type_upper = obj_type.upper()
    if obj_type_upper not in idf.idfobjects:
        print(f"[VENT WARNING] IDF has no object type '{obj_type_upper}'. Skipping zone {zone_name}.")
        return None

    existing = [
        obj for obj in idf.idfobjects[obj_type_upper]
        if obj.Name.upper() == obj_name.upper()
    ]
    if existing:
        obj = existing[0]
    else:
        obj = idf.newidfobject(obj_type_upper, Name=obj_name)

    # Assign the zone name
    if hasattr(obj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
        obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_name
    else:
        # older or different IDD field name
        obj.Zone_or_ZoneList_Name = zone_name

    if hasattr(obj, "Schedule_Name"):
        obj.Schedule_Name = sched_name

    # For infiltration/vent design flow
    if hasattr(obj, "Design_Flow_Rate_Calculation_Method"):
        obj.Design_Flow_Rate_Calculation_Method = "Flow/Zone"
        obj.Design_Flow_Rate = design_flow
    else:
        # If it's IdealLoads or something else, we do a custom approach
        pass

    return obj
