# dhw_functions.py

"""
Contains functions for applying DHW (Domestic Hot Water) parameter changes
to an IDF, such as creating/updating WATERHEATER:MIXED objects and 
associated schedules.
"""

from eppy.modeleditor import IDF  # or adapt for geomeppy

##############################################################################
# 1) APPLY BUILDING-LEVEL DHW PARAMS
##############################################################################

def apply_dhw_params_to_idf(idf, param_dict, suffix="MyDHW"):
    """
    Takes a dictionary of DHW parameter picks, e.g.:
      {
        "setpoint_c": 60.0,
        "default_tank_volume_liters": 300.0,
        "default_heater_capacity_w": 4000.0,
        "sched_morning": 0.7,
        "sched_peak": 1.0,
        "sched_afternoon": 0.2,
        "sched_evening": 0.8,
        "heater_fuel_type": "Electricity",
        "heater_eff": 0.9,
        ...
      }
    Then:
      1) Creates or updates a usage fraction schedule <suffix>_UseFraction
      2) Creates or updates a setpoint schedule <suffix>_Setpoint
      3) Creates or updates a WATERHEATER:MIXED named <suffix>_WaterHeater
         with the new volume, capacity, etc.
    """

    # 1) Create/Update Schedules
    frac_sched_name, setpoint_sched_name = _create_or_update_dhw_schedules(
        idf,
        suffix,
        setpoint_c=param_dict.get("setpoint_c", 60.0),
        morning_val=param_dict.get("sched_morning", 0.7),
        peak_val=param_dict.get("sched_peak", 1.0),
        afternoon_val=param_dict.get("sched_afternoon", 0.2),
        evening_val=param_dict.get("sched_evening", 0.8)
    )

    # 2) WaterHeater:Mixed
    wh_name = f"{suffix}_WaterHeater"
    wh_obj = None
    # Check if it already exists
    existing_wh = [obj for obj in idf.idfobjects["WATERHEATER:MIXED"] if obj.Name == wh_name]
    if existing_wh:
        wh_obj = existing_wh[0]
    else:
        wh_obj = idf.newidfobject("WATERHEATER:MIXED", Name=wh_name)

    # Fill in fields
    tank_volume_m3 = (param_dict.get("default_tank_volume_liters", 200.0)) / 1000.0
    heater_capacity_w = param_dict.get("default_heater_capacity_w", 4000.0)
    fuel_type = param_dict.get("heater_fuel_type", "Electricity")
    eff = param_dict.get("heater_eff", 0.9)

    wh_obj.Tank_Volume = tank_volume_m3
    wh_obj.Setpoint_Temperature_Schedule_Name = setpoint_sched_name
    wh_obj.Heater_Maximum_Capacity = heater_capacity_w
    wh_obj.Use_Flow_Rate_Fraction_Schedule_Name = frac_sched_name
    wh_obj.Heater_Fuel_Type = fuel_type
    wh_obj.Heater_Thermal_Efficiency = eff

    # Example final log
    print(f"[DHW] Updated WaterHeater '{wh_obj.Name}' => "
          f"Volume={tank_volume_m3:.3f} m3, "
          f"Capacity={heater_capacity_w} W, "
          f"SetpointSched={setpoint_sched_name}, FlowFracSched={frac_sched_name}, "
          f"Fuel={fuel_type}, Eff={eff}")


##############################################################################
# Helper: Create or Update DHW Schedules
##############################################################################

def _create_or_update_dhw_schedules(
    idf,
    suffix,
    setpoint_c=60.0,
    morning_val=0.7,
    peak_val=1.0,
    afternoon_val=0.2,
    evening_val=0.8
):
    """
    Creates or overwrites two schedules:
      1) <suffix>_UseFraction => usage fraction schedule
      2) <suffix>_Setpoint   => constant setpoint schedule

    Each is a SCHEDULE:COMPACT object in the IDF. If it doesn't exist, we create it.
    If it does, we overwrite it.
    """
    # Fraction schedule
    frac_sched_name = f"{suffix}_UseFraction"
    frac_sch = idf.getobject("SCHEDULE:COMPACT", frac_sched_name.upper())
    if not frac_sch:
        frac_sch = idf.newidfobject("SCHEDULE:COMPACT", Name=frac_sched_name)

    frac_sch.Schedule_Type_Limits_Name = "Fraction"
    frac_sch.Field_1 = "Through: 12/31"
    frac_sch.Field_2 = "For: AllDays"
    # 0.0 until 06:00
    frac_sch.Field_3 = "Until: 06:00, 0.0"
    # 06:00-08:00 => morning
    frac_sch.Field_4 = f"Until: 08:00,{morning_val:.2f}"
    # 08:00-10:00 => peak
    frac_sch.Field_5 = f"Until: 10:00,{peak_val:.2f}"
    # 10:00-17:00 => afternoon
    frac_sch.Field_6 = f"Until: 17:00,{afternoon_val:.2f}"
    # 17:00-21:00 => evening
    frac_sch.Field_7 = f"Until: 21:00,{evening_val:.2f}"
    # 21:00-24:00 => back to morning_val for demonstration
    frac_sch.Field_8 = f"Until: 24:00,{morning_val:.2f}"

    # Setpoint schedule
    setpoint_sched_name = f"{suffix}_Setpoint"
    setpoint_sch = idf.getobject("SCHEDULE:COMPACT", setpoint_sched_name.upper())
    if not setpoint_sch:
        setpoint_sch = idf.newidfobject("SCHEDULE:COMPACT", Name=setpoint_sched_name)

    setpoint_sch.Schedule_Type_Limits_Name = "Temperature"
    setpoint_sch.Field_1 = "Through: 12/31"
    setpoint_sch.Field_2 = "For: AllDays"
    setpoint_sch.Field_3 = f"Until: 24:00,{setpoint_c:.2f}"

    return frac_sched_name, setpoint_sched_name
