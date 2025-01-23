# water_heater.py

from .assign_dhw_values import assign_dhw_parameters
from .parameters import calculate_dhw_parameters
from .schedules import create_dhw_schedules

def add_dhw_to_idf(
    idf,
    building_row,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    name_suffix="MyDHW",
    user_config_dhw=None,
    assigned_dhw_log=None,
    use_nta=False
):
    """
    1) Retrieve 'dhw_key' from building_row (or fallback).
    2) Pull parameter ranges from dhw_lookup => assign final picks in assign_dhw_parameters().
    3) Merge with user_config_dhw if any (including building_function, age_range, etc.).
    4) Calculate occupant_count, daily usage, peak flow, etc.
    5) Create schedules, then WaterHeater:Mixed object in the IDF.
    6) Log object names and all relevant fields in assigned_dhw_log for debugging or future Eppy edits.
    """

    # Identify the building ID (or fallback to 0)
    bldg_id = building_row.get("ogc_fid", 0)

    # Ensure assigned_dhw_log has a dict for this building
    if assigned_dhw_log is not None and bldg_id not in assigned_dhw_log:
        assigned_dhw_log[bldg_id] = {}

    # Decide which DHW key to use, e.g. "Apartment" or "Office Function"
    dhw_building_key = building_row.get("dhw_key", "Detached House")

    # === NEW: Extract building_function and age_range to pass along ===
    bldg_func = building_row.get("building_function", "")  # e.g. "residential"
    bldg_age  = building_row.get("age_range", None)        # e.g. "1992 - 2005"
    # === END NEW ===

    # 1) Assign final picks from dhw_lookup (with user overrides, if any)
    assigned = assign_dhw_parameters(
        building_id=bldg_id,
        dhw_key=dhw_building_key,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_dhw=user_config_dhw,
        assigned_dhw_log=assigned_dhw_log,  # logging final picks + range
        building_row=building_row,
        use_nta=use_nta,
        building_function=bldg_func,  # <--- pass building function
        age_range=bldg_age           # <--- pass building age_range
    )

    # 2) Calculate occupant_count, daily liters, etc.
    occupant_count = building_row.get("occupant_count", None)
    floor_area_m2 = building_row.get("floor_area_m2", building_row.get("area", None))
    params = calculate_dhw_parameters(
        assigned,
        floor_area_m2=floor_area_m2,
        occupant_count=occupant_count
        # If you want to log derived values here, pass assigned_dhw_log + bldg_id
        # assigned_dhw_log=assigned_dhw_log,
        # building_id=bldg_id
    )

    # Optionally log derived occupant_count, daily_liters, etc. here:
    if assigned_dhw_log and bldg_id in assigned_dhw_log:
        assigned_dhw_log[bldg_id]["dhw_occupant_count"] = params["occupant_count"]
        assigned_dhw_log[bldg_id]["dhw_daily_liters"] = params["daily_liters"]
        assigned_dhw_log[bldg_id]["dhw_peak_flow_m3s"] = params["peak_flow_m3s"]
        assigned_dhw_log[bldg_id]["dhw_tank_volume_m3"] = params["tank_volume_m3"]
        assigned_dhw_log[bldg_id]["dhw_heater_capacity_w"] = params["heater_capacity_w"]

    # 3) Build schedules for use fraction & setpoint
    frac_sched_name, setpoint_sched_name = create_dhw_schedules(
        idf,
        schedule_name_suffix=name_suffix,
        setpoint_c=params["setpoint_c"],
        morning_val=assigned["sched_morning"],
        peak_val=assigned["sched_peak"],
        afternoon_val=assigned["sched_afternoon"],
        evening_val=assigned["sched_evening"]
    )

    # Optionally log schedule names
    if assigned_dhw_log and bldg_id in assigned_dhw_log:
        assigned_dhw_log[bldg_id]["dhw_fraction_schedule"] = frac_sched_name
        assigned_dhw_log[bldg_id]["dhw_setpoint_schedule"] = setpoint_sched_name

    # 4) Create the WaterHeater:Mixed object in E+
    wh_name = f"{name_suffix}_WaterHeater"

    # Simple logic: if it's a Non-Residential "Function", use gas + eff=0.8, else electric + eff=0.9
    if "Function" in dhw_building_key:
        fuel_type = "NaturalGas"
        heater_eff = 0.8
    else:
        fuel_type = "Electricity"
        heater_eff = 0.9

    wh_obj = idf.newidfobject(
        "WATERHEATER:MIXED",
        Name=wh_name,
        Tank_Volume=params["tank_volume_m3"],
        Setpoint_Temperature_Schedule_Name=setpoint_sched_name,
        Deadband_Temperature_Difference=2.0,
        Maximum_Temperature_Limit=80.0,
        Heater_Control_Type="CYCLE",
        Heater_Maximum_Capacity=params["heater_capacity_w"],
        Heater_Fuel_Type=fuel_type,
        Heater_Thermal_Efficiency=heater_eff,
        Off_Cycle_Parasitic_Fuel_Consumption_Rate=0.0,
        Off_Cycle_Parasitic_Fuel_Type="Electricity",
        Off_Cycle_Parasitic_Heat_Fraction_to_Tank=0.0,
        On_Cycle_Parasitic_Fuel_Consumption_Rate=0.0,
        On_Cycle_Parasitic_Fuel_Type="Electricity",
        On_Cycle_Parasitic_Heat_Fraction_to_Tank=0.0,
        Ambient_Temperature_Indicator="SCHEDULE",
        Ambient_Temperature_Schedule_Name="Always22C",
        Off_Cycle_Loss_Coefficient_to_Ambient_Temperature=5.0,
        On_Cycle_Loss_Coefficient_to_Ambient_Temperature=5.0,
        Peak_Use_Flow_Rate=params["peak_flow_m3s"],
        Use_Flow_Rate_Fraction_Schedule_Name=frac_sched_name
    )

    # 5) Log the newly created WaterHeater object name & fields
    if assigned_dhw_log and bldg_id in assigned_dhw_log:
        assigned_dhw_log[bldg_id]["dhw_waterheater_object_name"] = wh_obj.Name
        assigned_dhw_log[bldg_id]["dhw_heater_fuel_type"] = fuel_type
        assigned_dhw_log[bldg_id]["dhw_heater_thermal_eff"] = heater_eff

        # If you want a more 'fenestration-like' breakdown:
        wh_key = "dhw_waterheater"
        assigned_dhw_log[bldg_id][f"{wh_key}.obj_type"] = "WATERHEATER:MIXED"
        assigned_dhw_log[bldg_id][f"{wh_key}.Name"] = wh_obj.Name
        assigned_dhw_log[bldg_id][f"{wh_key}.Tank_Volume"] = wh_obj.Tank_Volume
        assigned_dhw_log[bldg_id][f"{wh_key}.Setpoint_Temperature_Schedule_Name"] = wh_obj.Setpoint_Temperature_Schedule_Name
        assigned_dhw_log[bldg_id][f"{wh_key}.Heater_Maximum_Capacity"] = wh_obj.Heater_Maximum_Capacity
        assigned_dhw_log[bldg_id][f"{wh_key}.Heater_Fuel_Type"] = wh_obj.Heater_Fuel_Type
        assigned_dhw_log[bldg_id][f"{wh_key}.Heater_Thermal_Efficiency"] = wh_obj.Heater_Thermal_Efficiency
        assigned_dhw_log[bldg_id][f"{wh_key}.Use_Flow_Rate_Fraction_Schedule_Name"] = wh_obj.Use_Flow_Rate_Fraction_Schedule_Name

    # Optional debug prints
    print(f"[DHW] building_id={bldg_id}, dhw_key={dhw_building_key}")
    print(f"     occupant_count={params['occupant_count']} daily_liters={params['daily_liters']:.1f}")
    print(f"     setpoint={params['setpoint_c']:.1f}C, tank_volume={params['tank_volume_m3']:.3f} m³")
    print(f"     schedules => {frac_sched_name}, {setpoint_sched_name}")
    print(f"     WATERHEATER => {wh_obj.Name}, fuel={fuel_type}, eff={heater_eff}")

    return wh_obj
