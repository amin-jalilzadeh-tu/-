# setzone/add_outdoor_air_and_zone_sizing_to_all_zones.py

from geomeppy import IDF
from .assign_zone_sizing_values import assign_zone_sizing_params
from .define_global_design_specs import define_global_design_specs

def add_outdoor_air_and_zone_sizing_to_all_zones(
    idf: IDF,
    building_row: dict,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    assigned_setzone_log=None,  # <--- for logging
    zonelist_name="ALL_ZONES"   # <--- NEW param to reference a single ZoneList
):
    """
    1) Creates/updates a SINGLE DESIGNSPECIFICATION:OUTDOORAIR (DSOA_Global) 
       and a SINGLE DESIGNSPECIFICATION:ZONEAIRDISTRIBUTION (DSZAD_Global)
       for the entire building.

    2) Creates/updates a SINGLE SIZING:ZONE object that references a ZoneList
       (instead of creating multiple SIZING:ZONE objects, one per zone).

    3) Optionally logs final picks in assigned_setzone_log.

    NB: With a single SIZING:ZONE referencing a ZoneList, all zones in that list
        share the same supply-air conditions. If you need differences zone-by-zone,
        revert to the original per-zone approach.
    """

    # ---------------------------------------------------------------------
    # 1) Create the global design spec objects if needed
    # ---------------------------------------------------------------------
    dsoa_obj, dszad_obj = define_global_design_specs(idf)
    # e.g., dsoa_obj.Name => "DSOA_Global", dszad_obj.Name => "DSZAD_Global"

    # ---------------------------------------------------------------------
    # 2) Determine building function
    # ---------------------------------------------------------------------
    bldg_func = building_row.get("building_function", "residential")
    if bldg_func not in ["residential", "non_residential"]:
        bldg_func = "residential"

    # ---------------------------------------------------------------------
    # 3) Get assigned sizing parameters
    # ---------------------------------------------------------------------
    assigned = assign_zone_sizing_params(
        building_function=bldg_func,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed
    )
    # assigned => dict of { 
    #   "cooling_supply_air_temp", 
    #   "heating_supply_air_temp", 
    #   "cooling_supply_air_hr", 
    #   "heating_supply_air_hr",
    #   "cooling_design_air_flow_method",
    #   "heating_design_air_flow_method",
    #   ... 
    # }

    # ---------------------------------------------------------------------
    # 4) Create or retrieve a SINGLE SIZING:ZONE referencing a ZoneList
    # ---------------------------------------------------------------------
    existing_sizing_obj = None
    for sz in idf.idfobjects["SIZING:ZONE"]:
        zone_field = (
            "Zone_or_ZoneList_or_Space_or_SpaceList_Name"
            if hasattr(sz, "Zone_or_ZoneList_or_Space_or_SpaceList_Name")
            else "Zone_or_ZoneList_Name"
        )
        if getattr(sz, zone_field, "").upper() == zonelist_name.upper():
            existing_sizing_obj = sz
            break

    if not existing_sizing_obj:
        sz_obj = idf.newidfobject("SIZING:ZONE")
        zone_field = (
            "Zone_or_ZoneList_or_Space_or_SpaceList_Name"
            if hasattr(sz_obj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name")
            else "Zone_or_ZoneList_Name"
        )
        setattr(sz_obj, zone_field, zonelist_name)
    else:
        sz_obj = existing_sizing_obj

    # ---------------------------------------------------------------------
    # 5) Fill in the SIZING:ZONE fields
    # ---------------------------------------------------------------------
    sz_obj.Zone_Cooling_Design_Supply_Air_Temperature = assigned["cooling_supply_air_temp"]
    sz_obj.Zone_Heating_Design_Supply_Air_Temperature = assigned["heating_supply_air_temp"]
    sz_obj.Zone_Cooling_Design_Supply_Air_Humidity_Ratio = assigned["cooling_supply_air_hr"]
    sz_obj.Zone_Heating_Design_Supply_Air_Humidity_Ratio = assigned["heating_supply_air_hr"]

    sz_obj.Design_Specification_Outdoor_Air_Object_Name = dsoa_obj.Name
    sz_obj.Design_Specification_Zone_Air_Distribution_Object_Name = dszad_obj.Name

    # Sizing factors
    sz_obj.Zone_Heating_Sizing_Factor = 1.0
    sz_obj.Zone_Cooling_Sizing_Factor = 1.0

    # Air flow methods
    sz_obj.Cooling_Design_Air_Flow_Method = assigned["cooling_design_air_flow_method"]
    sz_obj.Heating_Design_Air_Flow_Method = assigned["heating_design_air_flow_method"]

    # ---------------------------------------------------------------------
    # 6) Optional logging
    # ---------------------------------------------------------------------
    if assigned_setzone_log is not None:
        bldg_id = building_row.get("ogc_fid", 0)
        assigned_setzone_log[bldg_id] = assigned

    return
