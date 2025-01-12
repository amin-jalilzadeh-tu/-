# HVAC/custom_hvac.py

from .assign_hvac_values import assign_hvac_ideal_parameters

def add_HVAC_Ideal_to_all_zones(
    idf,
    building_row=None,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    user_config_hvac=None,
    assigned_hvac_log=None
):
    """
    Adds an Ideal Loads Air System to every Zone in the IDF,
    along with schedules & setpoints derived from hvac_lookup ranges
    and user_config_hvac overrides.

    Steps:
      1) Gather building-level parameters from assign_hvac_ideal_parameters(...),
         which returns a single dictionary 'hvac_params' (including final picks + ranges).
         That dictionary is also stored in assigned_hvac_log[bldg_id]["hvac_params"].

      2) Create or update the necessary schedules in the IDF for heating/cooling setpoints.
      3) For each zone, create or update:
         - ZONECONTROL:THERMOSTAT
         - THERMOSTATSETPOINT:DUALSETPOINT
         - ZONEHVAC:EQUIPMENTCONNECTIONS
         - ZONEHVAC:EQUIPMENTLIST
         - ZONEHVAC:IDEALLOADSAIRSYSTEM
         Then store zone-level info in assigned_hvac_log[bldg_id]["zones"][zone_name].

    Returns:
      None. (IDF is modified in-place; logging is stored in assigned_hvac_log if provided.)
    """

    # 1) Extract building info from building_row
    bldg_id = building_row.get("ogc_fid", 0)
    bldg_func = building_row.get("building_function", "residential")
    res_type = building_row.get("residential_type", "Two-and-a-half-story House")
    nonres_type = building_row.get("non_residential_type", "Meeting Function")
    age_range = building_row.get("age_range", "1900-2000")
    scenario = building_row.get("scenario", "scenario1")

    # 2) Call the function that picks HVAC setpoints + ranges
    #    => returns a single dictionary of final picks & ranges
    hvac_params = assign_hvac_ideal_parameters(
        building_id=bldg_id,
        building_function=bldg_func,
        residential_type=res_type,
        non_residential_type=nonres_type,
        age_range=age_range,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_hvac=user_config_hvac,
        assigned_hvac_log=assigned_hvac_log
    )
    # Example contents of hvac_params:
    # {
    #   "heating_day_setpoint": 20.28, "heating_day_setpoint_range": (19.0,21.0),
    #   "heating_night_setpoint": 15.03, "heating_night_setpoint_range": (15.0,16.0),
    #   "cooling_day_setpoint": 24.55, ...
    #   "max_heating_supply_air_temp": 52.36, ...
    #   "schedule_details": {...}
    # }

    # If assigned_hvac_log is not None, we already have hvac_params stored under
    # assigned_hvac_log[bldg_id]["hvac_params"] (done inside assign_hvac_values.py).

    # 3) Ensure schedule type limits exist
    if not idf.getobject("SCHEDULETYPELIMITS", "Temperature"):
        stl = idf.newidfobject("SCHEDULETYPELIMITS")
        stl.Name = "Temperature"
        stl.Lower_Limit_Value = -100
        stl.Upper_Limit_Value = 200
        stl.Numeric_Type = "CONTINUOUS"

    if not idf.getobject("SCHEDULETYPELIMITS", "ControlType"):
        stl = idf.newidfobject("SCHEDULETYPELIMITS")
        stl.Name = "ControlType"
        stl.Lower_Limit_Value = 0
        stl.Upper_Limit_Value = 4
        stl.Numeric_Type = "DISCRETE"

    # 4) Create a control type schedule if missing
    if not idf.getobject("SCHEDULE:COMPACT", "ZONE CONTROL TYPE SCHEDULE"):
        sc = idf.newidfobject("SCHEDULE:COMPACT")
        sc.Name = "ZONE CONTROL TYPE SCHEDULE"
        sc.Schedule_Type_Limits_Name = "ControlType"
        sc.Field_1 = "Through: 12/31"
        sc.Field_2 = "For: AllDays"
        sc.Field_3 = "Until: 24:00,4"  # dual setpoint

    # 5) Build or update the Heating Setpoint schedule (simplified example)
    #    We'll define day from 07:00-19:00 => day setpoint
    #    else => night setpoint
    h_day = hvac_params["heating_day_setpoint"]
    h_night = hvac_params["heating_night_setpoint"]

    if not idf.getobject("SCHEDULE:COMPACT", "ZONE HEATING SETPOINTS"):
        sc = idf.newidfobject("SCHEDULE:COMPACT")
        sc.Name = "ZONE HEATING SETPOINTS"
        sc.Schedule_Type_Limits_Name = "Temperature"
        sc.Field_1 = "Through: 12/31"
        sc.Field_2 = "For: AllDays"
        sc.Field_3 = f"Until: 07:00,{h_night:.2f}"
        sc.Field_4 = f"Until: 19:00,{h_day:.2f}"
        sc.Field_5 = f"Until: 24:00,{h_night:.2f}"
    else:
        # If the schedule object exists, you might update it similarly
        sc = idf.getobject("SCHEDULE:COMPACT", "ZONE HEATING SETPOINTS".upper())
        sc.Field_3 = f"Until: 07:00,{h_night:.2f}"
        sc.Field_4 = f"Until: 19:00,{h_day:.2f}"
        sc.Field_5 = f"Until: 24:00,{h_night:.2f}"

    # 6) Build or update the Cooling Setpoint schedule
    c_day = hvac_params["cooling_day_setpoint"]
    c_night = hvac_params["cooling_night_setpoint"]

    if not idf.getobject("SCHEDULE:COMPACT", "ZONE COOLING SETPOINTS"):
        sc = idf.newidfobject("SCHEDULE:COMPACT")
        sc.Name = "ZONE COOLING SETPOINTS"
        sc.Schedule_Type_Limits_Name = "Temperature"
        sc.Field_1 = "Through: 12/31"
        sc.Field_2 = "For: AllDays"
        sc.Field_3 = f"Until: 07:00,{c_night:.2f}"
        sc.Field_4 = f"Until: 19:00,{c_day:.2f}"
        sc.Field_5 = f"Until: 24:00,{c_night:.2f}"
    else:
        sc = idf.getobject("SCHEDULE:COMPACT", "ZONE COOLING SETPOINTS".upper())
        sc.Field_3 = f"Until: 07:00,{c_night:.2f}"
        sc.Field_4 = f"Until: 19:00,{c_day:.2f}"
        sc.Field_5 = f"Until: 24:00,{c_night:.2f}"

    # 7) For each zone, create:
    #    - ZONECONTROL:THERMOSTAT + THERMOSTATSETPOINT:DUALSETPOINT
    #    - ZONEHVAC:EQUIPMENTCONNECTIONS + ZONEHVAC:EQUIPMENTLIST
    #    - ZONEHVAC:IDEALLOADSAIRSYSTEM

    max_heat_temp = hvac_params["max_heating_supply_air_temp"]
    min_cool_temp = hvac_params["min_cooling_supply_air_temp"]

    zones = idf.idfobjects["ZONE"]
    if not zones:
        print("[HVAC] No zones found; skipping.")
        return

    # If we want to store zone-level data
    if assigned_hvac_log is not None and bldg_id not in assigned_hvac_log:
        assigned_hvac_log[bldg_id] = {}
    if assigned_hvac_log is not None and "zones" not in assigned_hvac_log[bldg_id]:
        assigned_hvac_log[bldg_id]["zones"] = {}

    for zone_obj in zones:
        zone_name = zone_obj.Name

        # 7a) Thermostat
        existing_thermo = [
            t for t in idf.idfobjects["ZONECONTROL:THERMOSTAT"]
            if (
                (hasattr(t, "Zone_or_ZoneList_or_Space_or_SpaceList_Name") and
                 getattr(t, "Zone_or_ZoneList_or_Space_or_SpaceList_Name") == zone_name)
                or
                (hasattr(t, "Zone_or_ZoneList_Name") and t.Zone_or_ZoneList_Name == zone_name)
            )
        ]
        if not existing_thermo:
            thermo = idf.newidfobject("ZONECONTROL:THERMOSTAT")
            thermo.Name = f"{zone_name} CONTROLS"
            if hasattr(thermo, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
                thermo.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_name
            else:
                thermo.Zone_or_ZoneList_Name = zone_name
            thermo.Control_Type_Schedule_Name = "ZONE CONTROL TYPE SCHEDULE"
            thermo.Control_1_Object_Type = "ThermostatSetpoint:DualSetpoint"
            thermo.Control_1_Name = f"{zone_name} SETPOINTS"

            # ThermostatSetpoint:DualSetpoint
            dual = idf.newidfobject("THERMOSTATSETPOINT:DUALSETPOINT")
            dual.Name = f"{zone_name} SETPOINTS"
            dual.Heating_Setpoint_Temperature_Schedule_Name = "ZONE HEATING SETPOINTS"
            dual.Cooling_Setpoint_Temperature_Schedule_Name = "ZONE COOLING SETPOINTS"
        else:
            # If it exists, you might update it or skip
            pass

        # 7b) EquipmentConnections
        existing_equip_conns = [
            ec for ec in idf.idfobjects["ZONEHVAC:EQUIPMENTCONNECTIONS"]
            if ec.Zone_Name == zone_name
        ]
        if not existing_equip_conns:
            eq_conn = idf.newidfobject("ZONEHVAC:EQUIPMENTCONNECTIONS")
            eq_conn.Zone_Name = zone_name
            eq_conn.Zone_Conditioning_Equipment_List_Name = f"{zone_name} EQUIPMENT"
            eq_conn.Zone_Air_Inlet_Node_or_NodeList_Name = f"{zone_name} INLETS"
            eq_conn.Zone_Air_Exhaust_Node_or_NodeList_Name = ""
            eq_conn.Zone_Air_Node_Name = f"{zone_name} NODE"
            eq_conn.Zone_Return_Air_Node_or_NodeList_Name = f"{zone_name} OUTLET"

        # 7c) EquipmentList
        existing_equip_lists = [
            el for el in idf.idfobjects["ZONEHVAC:EQUIPMENTLIST"]
            if el.Name == f"{zone_name} EQUIPMENT"
        ]
        if not existing_equip_lists:
            eq_list = idf.newidfobject("ZONEHVAC:EQUIPMENTLIST")
            eq_list.Name = f"{zone_name} EQUIPMENT"
            eq_list.Load_Distribution_Scheme = "SequentialLoad"
            eq_list.Zone_Equipment_1_Object_Type = "ZoneHVAC:IdealLoadsAirSystem"
            eq_list.Zone_Equipment_1_Name = f"{zone_name} Ideal Loads"
            eq_list.Zone_Equipment_1_Cooling_Sequence = 1
            eq_list.Zone_Equipment_1_Heating_or_NoLoad_Sequence = 1

        # 7d) IdealLoads
        existing_ideal = [
            ild for ild in idf.idfobjects["ZONEHVAC:IDEALLOADSAIRSYSTEM"]
            if ild.Name == f"{zone_name} Ideal Loads"
        ]
        if not existing_ideal:
            ideal = idf.newidfobject("ZONEHVAC:IDEALLOADSAIRSYSTEM")
            ideal.Name = f"{zone_name} Ideal Loads"
            ideal.Availability_Schedule_Name = ""  # or "AlwaysOn"
            ideal.Zone_Supply_Air_Node_Name = f"{zone_name} INLETS"
            ideal.Zone_Exhaust_Air_Node_Name = ""
            ideal.System_Inlet_Air_Node_Name = ""
            ideal.Maximum_Heating_Supply_Air_Temperature = max_heat_temp
            ideal.Minimum_Cooling_Supply_Air_Temperature = min_cool_temp
            ideal.Maximum_Heating_Supply_Air_Humidity_Ratio = 0.015
            # ideal.Minimum_Cooling_Air_Flow_Fraction = "Autosize"  <-- remove or conditionally set
            if hasattr(ideal, "Minimum_Cooling_Air_Flow_Fraction"):
                ideal.Minimum_Cooling_Air_Flow_Fraction = "Autosize"

            #ideal.Minimum_Cooling_Air_Flow_Fraction = "Autosize"
            ideal.Heating_Limit = "NoLimit"
            ideal.Maximum_Heating_Air_Flow_Rate = "Autosize"
            ideal.Cooling_Limit = "NoLimit"
            ideal.Maximum_Cooling_Air_Flow_Rate = "Autosize"
            ideal.Dehumidification_Control_Type = "ConstantSupplyHumidityRatio"
            ideal.Humidification_Control_Type = "ConstantSupplyHumidityRatio"
        else:
            # Update the existing IdealLoads object
            ideal = existing_ideal[0]
            ideal.Maximum_Heating_Supply_Air_Temperature = max_heat_temp
            ideal.Minimum_Cooling_Supply_Air_Temperature = min_cool_temp

        # 7e) NodeList for supply inlets
        existing_inlet_list = idf.getobject("NODELIST", f"{zone_name} INLETS")
        if not existing_inlet_list:
            nlist = idf.newidfobject("NODELIST")
            nlist.Name = f"{zone_name} INLETS"
            nlist.Node_1_Name = f"{zone_name} INLET"

        # 7f) Store zone-level data in assigned_hvac_log
        if assigned_hvac_log is not None:
            if "zones" not in assigned_hvac_log[bldg_id]:
                assigned_hvac_log[bldg_id]["zones"] = {}
            if zone_name not in assigned_hvac_log[bldg_id]["zones"]:
                assigned_hvac_log[bldg_id]["zones"][zone_name] = {}

            assigned_hvac_log[bldg_id]["zones"][zone_name]["hvac_object_name"] = ideal.Name
            assigned_hvac_log[bldg_id]["zones"][zone_name]["hvac_object_type"] = "ZONEHVAC:IDEALLOADSAIRSYSTEM"
            assigned_hvac_log[bldg_id]["zones"][zone_name]["heating_setpoint_schedule"] = "ZONE HEATING SETPOINTS"
            assigned_hvac_log[bldg_id]["zones"][zone_name]["cooling_setpoint_schedule"] = "ZONE COOLING SETPOINTS"
            assigned_hvac_log[bldg_id]["zones"][zone_name]["thermostat_name"] = f"{zone_name} CONTROLS"
            assigned_hvac_log[bldg_id]["zones"][zone_name]["thermostat_dualsetpoint_name"] = f"{zone_name} SETPOINTS"

    # Done
    print(f"[add_HVAC_Ideal_to_all_zones] Completed HVAC setup for building {bldg_id}.")
