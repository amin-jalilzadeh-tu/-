# hvac_functions.py

"""
Contains functions for applying HVAC parameter changes to an IDF,
such as:
  1) Updating schedules (heating/cooling setpoints).
  2) Updating or creating Ideal Loads systems.
  3) Optionally applying zone-level logic.
"""

from eppy.modeleditor import IDF  # or adapt for geomeppy

##############################################################################
# 1) APPLY BUILDING-LEVEL HVAC
##############################################################################

def apply_building_level_hvac(idf, param_dict):
    """
    param_dict is a dictionary of HVAC parameters, for example:
      {
        "heating_day_setpoint": 20.3,
        "heating_night_setpoint": 15.0,
        "cooling_day_setpoint": 25.0,
        "cooling_night_setpoint": 27.0,
        "max_heating_supply_air_temp": 50.0,
        "min_cooling_supply_air_temp": 13.0,
        ...
      }

    This function:
      1) Updates "ZONE HEATING SETPOINTS" schedule (if day/night keys exist).
      2) Updates "ZONE COOLING SETPOINTS" schedule (if day/night keys exist).
      3) For each ZONEHVAC:IDEALLOADSAIRSYSTEM object, sets the
         Maximum_Heating_Supply_Air_Temperature and Minimum_Cooling_Supply_Air_Temperature
         if those keys are in param_dict.
    """

    # (1) Heating Setpoint Schedules
    if "heating_day_setpoint" in param_dict or "heating_night_setpoint" in param_dict:
        h_day = param_dict.get("heating_day_setpoint", 20.0)
        h_night = param_dict.get("heating_night_setpoint", 15.0)
        _modify_schedule_compact(
            idf,
            schedule_name="ZONE HEATING SETPOINTS",
            day_value=h_day,
            night_value=h_night,
            day_start="07:00",
            day_end="19:00"
        )

    # (2) Cooling Setpoint Schedules
    if "cooling_day_setpoint" in param_dict or "cooling_night_setpoint" in param_dict:
        c_day = param_dict.get("cooling_day_setpoint", 24.0)
        c_night = param_dict.get("cooling_night_setpoint", 27.0)
        _modify_schedule_compact(
            idf,
            schedule_name="ZONE COOLING SETPOINTS",
            day_value=c_day,
            night_value=c_night,
            day_start="07:00",
            day_end="19:00"
        )

    # (3) Ideal Loads Supply Temps
    max_heat = param_dict.get("max_heating_supply_air_temp", None)
    min_cool = param_dict.get("min_cooling_supply_air_temp", None)
    if max_heat is not None or min_cool is not None:
        _set_ideal_loads_supply_temps_all_zones(
            idf,
            max_heating_temp=max_heat,
            min_cooling_temp=min_cool
        )


##############################################################################
# Helper: Modify a SCHEDULE:COMPACT
##############################################################################

def _modify_schedule_compact(
    idf,
    schedule_name,
    day_value,
    night_value,
    day_start="07:00",
    day_end="19:00"
):
    """
    Overwrites a SCHEDULE:COMPACT object named `schedule_name` with three blocks:
      - Until day_start => night_value
      - Until day_end   => day_value
      - Until 24:00     => night_value

    The base IDF must already have a schedule object with that name
    (unless you're comfortable creating a new one from scratch).
    If it doesn't exist, we warn and skip.
    """
    sched_obj = idf.getobject("SCHEDULE:COMPACT", schedule_name.upper())
    if not sched_obj:
        print(f"[WARN] schedule '{schedule_name}' not found; skipping.")
        return

    # Typically:
    #  Field_1: "Through: 12/31"
    #  Field_2: "For: AllDays"
    #  Field_3: "Until: 07:00,15.0"
    #  Field_4: "Until: 19:00,20.0"
    #  Field_5: "Until: 24:00,15.0"

    sched_obj.Field_3 = f"Until: {day_start},{night_value:.2f}"
    sched_obj.Field_4 = f"Until: {day_end},{day_value:.2f}"
    sched_obj.Field_5 = f"Until: 24:00,{night_value:.2f}"

    print(f"[INFO] Updated schedule '{schedule_name}' => Day={day_value}, Night={night_value}")


##############################################################################
# Helper: Update IdealLoads for ALL ZONES
##############################################################################

def _set_ideal_loads_supply_temps_all_zones(idf, max_heating_temp=None, min_cooling_temp=None):
    """
    Loops over all 'ZONEHVAC:IDEALLOADSAIRSYSTEM' objects, sets:
      - Maximum_Heating_Supply_Air_Temperature = max_heating_temp
      - Minimum_Cooling_Supply_Air_Temperature = min_cooling_temp
    if provided.
    """
    ideal_objs = idf.idfobjects["ZONEHVAC:IDEALLOADSAIRSYSTEM"]
    for ideal in ideal_objs:
        if max_heating_temp is not None:
            ideal.Maximum_Heating_Supply_Air_Temperature = max_heating_temp
        if min_cooling_temp is not None:
            ideal.Minimum_Cooling_Supply_Air_Temperature = min_cooling_temp

        print(f"[INFO] Updated '{ideal.Name}' => "
              f"MaxHeat={max_heating_temp}, MinCool={min_cooling_temp}")


##############################################################################
# 2) OPTIONAL: ZONE-LEVEL
##############################################################################

def apply_zone_level_hvac(idf, df_zone_sub):
    """
    If you want to assign different setpoints or infiltration, etc. on a per-zone basis,
    parse df_zone_sub rows. Each row might say:
       zone_name, param_name, assigned_value
    Then update the IDF's zone-level objects accordingly.

    Currently just a placeholder function. 
    """
    pass
