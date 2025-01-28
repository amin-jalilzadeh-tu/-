"""
dhw_functions.py

Contains:
  1) create_dhw_scenarios(...)
     - Generates scenario param DataFrame with columns like:
         scenario_index, ogc_fid, param_name, param_value, param_min, param_max, picking_method
       for each building's DHW parameters.

  2) apply_dhw_params_to_idf(...)
     - Creates or updates schedules (UseFraction, Setpoint) and a WATERHEATER:MIXED object,
       partially preserving existing schedule time blocks if they exist.

In particular:
 - We ensure "Ambient_Temperature_Indicator" is set on WATERHEATER:MIXED, 
   so no error about missing property.
 - We do partial schedule editing in `_create_or_update_dhw_schedules()`.
"""

import os
import random
import pandas as pd
from eppy.modeleditor import IDF  # or adapt for geomeppy


##############################################################################
# 1) CREATE DHW SCENARIOS
##############################################################################

def create_dhw_scenarios(
    df_dhw_input,
    building_id,
    num_scenarios=5,
    picking_method="random_uniform",
    random_seed=42,
    scenario_csv_out=None
):
    """
    Generates a scenario-level DataFrame from assigned_dhw_params.csv rows 
    for the given building. If param_name ends in "_range", we parse min/max.
    Otherwise it's a fixed value. Then for each scenario, we can randomly pick
    param_value in [param_min, param_max] if picking_method="random_uniform".

    Columns in the final DF:
      [scenario_index, ogc_fid, param_name, param_value, param_min, param_max, picking_method]

    If scenario_csv_out is given, writes the CSV. Otherwise returns the DF only.
    """
    if random_seed is not None:
        random.seed(random_seed)

    # Filter for this building
    df_bldg = df_dhw_input[df_dhw_input["ogc_fid"] == building_id].copy()
    if df_bldg.empty:
        print(f"[create_dhw_scenarios] No DHW data for ogc_fid={building_id}.")
        return pd.DataFrame()

    # Parse param dictionary => list of {param_name, param_value, param_min, param_max}
    param_list = parse_building_dhw_params(df_bldg)

    scenario_rows = []
    for scn_i in range(num_scenarios):
        for p in param_list:
            p_name = p["param_name"]
            base_val = p["param_value"]
            p_min = p["param_min"]
            p_max = p["param_max"]

            new_val = pick_value(base_val, p_min, p_max, picking_method)

            scenario_rows.append({
                "scenario_index": scn_i,
                "ogc_fid": building_id,
                "param_name": p_name,
                "param_value": new_val,
                "param_min": p_min,
                "param_max": p_max,
                "picking_method": picking_method
            })

    df_scen = pd.DataFrame(scenario_rows)
    if scenario_csv_out:
        os.makedirs(os.path.dirname(scenario_csv_out), exist_ok=True)
        df_scen.to_csv(scenario_csv_out, index=False)
        print(f"[create_dhw_scenarios] Wrote => {scenario_csv_out}")

    return df_scen


def parse_building_dhw_params(df_bldg):
    """
    Helper to parse the building-level DHW params from assigned_dhw_params.csv.

    We expect lines like:
      param_name, assigned_value
      param_name_range, (xx, yy)

    We'll produce a list of dict e.g.:
      [
        {
          "param_name": "setpoint_c",
          "param_value": 58.0,
          "param_min": 55.0,
          "param_max": 60.0
        },
        ...
      ]
    """

    param_map = {}  # e.g. "setpoint_c" => { "value": X, "min": Y, "max": Z }

    for row in df_bldg.itertuples():
        name = row.param_name
        val  = row.assigned_value

        if name.endswith("_range"):
            base_name = name.replace("_range", "")
            if base_name not in param_map:
                param_map[base_name] = {"value": None, "min": None, "max": None}
            t = parse_tuple(val)
            if t and len(t) == 2:
                param_map[base_name]["min"] = t[0]
                param_map[base_name]["max"] = t[1]
        else:
            if name not in param_map:
                param_map[name] = {"value": None, "min": None, "max": None}
            param_map[name]["value"] = val

    # Convert param_map to a list
    result = []
    for p_name, dct in param_map.items():
        result.append({
            "param_name": p_name,
            "param_value": dct["value"],
            "param_min": dct["min"],
            "param_max": dct["max"]
        })
    return result


def parse_tuple(val):
    """
    If val is like "(145.0, 145.0)", parse to (145.0, 145.0). Otherwise None.
    """
    if not isinstance(val, str):
        return None
    s = val.strip()
    if not (s.startswith("(") and s.endswith(")")):
        return None
    try:
        inner = s[1:-1]  # remove parens
        parts = inner.split(",")
        if len(parts) != 2:
            return None
        p1 = float(parts[0])
        p2 = float(parts[1])
        return (p1, p2)
    except:
        return None


def pick_value(base_val, p_min, p_max, picking_method):
    """
    If picking_method=="random_uniform" and p_min/p_max are numeric and p_min!=p_max,
    pick random in [p_min, p_max]. Otherwise return base_val.
    """
    try:
        base_f = float(base_val)
    except:
        base_f = None

    if picking_method == "random_uniform" and p_min is not None and p_max is not None:
        try:
            fmin = float(p_min)
            fmax = float(p_max)
            if fmax != fmin:
                import random
                return random.uniform(fmin, fmax)
        except:
            pass
    return base_val


##############################################################################
# 2) APPLY BUILDING-LEVEL DHW PARAMS (with partial schedule editing)
##############################################################################

def apply_dhw_params_to_idf(idf, param_dict, suffix="MyDHW"):
    """
    Takes a dictionary of DHW parameter picks, e.g.:
      {
        "setpoint_c": 58.9,
        "default_tank_volume_liters": 277.5,
        "default_heater_capacity_w": 4223.2,
        "sched_morning": 0.62,
        "sched_peak": 0.98,
        "sched_afternoon": 0.20,
        "sched_evening": 0.68,
        "heater_fuel_type": "Electricity",
        "heater_eff": 0.9,
        ...
      }

    Then:
      1) Partially creates/updates a usage fraction schedule <suffix>_UseFraction
         ( preserving existing time blocks if present ).
      2) Partially creates/updates a setpoint schedule <suffix>_Setpoint 
         ( also preserving existing time blocks ).
      3) Creates or updates a WATERHEATER:MIXED object <suffix>_WaterHeater
         with the new volume, capacity, etc. 
         Ensures Ambient_Temperature_Indicator is set so you don't get the 
         "missing required property" error.
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
    existing_wh = [
        obj for obj in idf.idfobjects["WATERHEATER:MIXED"] 
        if obj.Name.upper() == wh_name.upper()
    ]
    if existing_wh:
        wh_obj = existing_wh[0]
    else:
        wh_obj = idf.newidfobject("WATERHEATER:MIXED", Name=wh_name)

    # Fill in fields (ensuring we set Ambient_Temperature_Indicator!)
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

    # Avoid the missing AmbientTemperatureIndicator error:
    # If your E+ version requires it, we set it explicitly:
    if not hasattr(wh_obj, "Ambient_Temperature_Indicator"):
        print("[DHW WARNING] This IDF object or IDD may not have 'Ambient_Temperature_Indicator' field!")
    else:
        # For example, set to "Schedule"
        wh_obj.Ambient_Temperature_Indicator = "Schedule"
        # Then define or point to a schedule for the ambient temp:
        if not hasattr(wh_obj, "Ambient_Temperature_Schedule_Name"):
            print("[DHW WARNING] IDD has no Ambient_Temperature_Schedule_Name field. Check version!")
        else:
            # Provide a schedule for ambient if needed:
            wh_obj.Ambient_Temperature_Schedule_Name = "Always22C"  # or any custom schedule

    print(f"[DHW] Updated WaterHeater '{wh_obj.Name}' => "
          f"Volume={tank_volume_m3:.3f} m3, "
          f"Capacity={heater_capacity_w} W, "
          f"SetpointSched={setpoint_sched_name}, FlowFracSched={frac_sched_name}, "
          f"Fuel={fuel_type}, Eff={eff}, "
          f"AmbientTempIndicator={getattr(wh_obj,'Ambient_Temperature_Indicator','N/A')}")


##############################################################################
# PARTIAL SCHEDULE UPDATES FOR DHW
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
    Creates or partially updates two schedules:
      1) <suffix>_UseFraction => usage fraction schedule
         with typical time-of-day patterns (0.0 until 06:00, morning, peak, etc.)
      2) <suffix>_Setpoint => constant setpoint (setpoint_c) all day

    If the schedule doesn't exist, we create it from scratch. 
    If it does exist, we parse each "Until: HH:MM, old_val" line 
    and only update the numeric portion, preserving time blocks.

    Returns (fraction_sched_name, setpoint_sched_name).
    """
    frac_sched_name = f"{suffix}_UseFraction"
    frac_sch = idf.getobject("SCHEDULE:COMPACT", frac_sched_name.upper())
    if not frac_sch:
        # Create from scratch with standard blocks
        frac_sch = idf.newidfobject("SCHEDULE:COMPACT", Name=frac_sched_name)
        frac_sch.Schedule_Type_Limits_Name = "Fraction"
        frac_sch.Field_1 = "Through: 12/31"
        frac_sch.Field_2 = "For: AllDays"
        # a typical pattern:
        frac_sch.Field_3 = "Until: 06:00, 0.0"
        frac_sch.Field_4 = f"Until: 08:00,{morning_val:.2f}"
        frac_sch.Field_5 = f"Until: 10:00,{peak_val:.2f}"
        frac_sch.Field_6 = f"Until: 17:00,{afternoon_val:.2f}"
        frac_sch.Field_7 = f"Until: 21:00,{evening_val:.2f}"
        frac_sch.Field_8 = f"Until: 24:00,{morning_val:.2f}"
        print(f"[DHW] Created new fraction schedule '{frac_sched_name}' with standard blocks.")
    else:
        # Partial update: parse each line
        frac_sch.Schedule_Type_Limits_Name = "Fraction"
        _partially_update_fraction_schedule(
            frac_sch,
            morning_val=morning_val,
            peak_val=peak_val,
            afternoon_val=afternoon_val,
            evening_val=evening_val
        )

    setpoint_sched_name = f"{suffix}_Setpoint"
    setpoint_sch = idf.getobject("SCHEDULE:COMPACT", setpoint_sched_name.upper())
    if not setpoint_sch:
        # create from scratch
        setpoint_sch = idf.newidfobject("SCHEDULE:COMPACT", Name=setpoint_sched_name)
        setpoint_sch.Schedule_Type_Limits_Name = "Temperature"
        setpoint_sch.Field_1 = "Through: 12/31"
        setpoint_sch.Field_2 = "For: AllDays"
        setpoint_sch.Field_3 = f"Until: 24:00,{setpoint_c:.2f}"
        print(f"[DHW] Created new setpoint schedule '{setpoint_sched_name}' = {setpoint_c} °C all day.")
    else:
        # partial update
        setpoint_sch.Schedule_Type_Limits_Name = "Temperature"
        _partially_update_setpoint_schedule(setpoint_sch, setpoint_c)

    return frac_sched_name, setpoint_sched_name


def _partially_update_fraction_schedule(sched_obj, 
                                        morning_val=0.7, 
                                        peak_val=1.0, 
                                        afternoon_val=0.2, 
                                        evening_val=0.8):
    """
    Loops over existing "Until: HH:MM, old_val" lines in a fraction schedule, 
    and overwrites the numeric portion based on time-of-day:

       0 <= time < 6  => 0.0
       6 <= time < 8  => morning_val
       8 <= time <10  => peak_val
       10<= time <17 => afternoon_val
       17<= time <21 => evening_val
       21<= time <=24 => morning_val

    If the schedule has more or fewer time blocks, 
    each block is updated according to where its 'Until: HH:MM' 
    fits in these intervals.
    """
    field_count = len(sched_obj.fieldvalues)
    for i in range(field_count):
        line_str = sched_obj.fieldvalues[i]
        if not isinstance(line_str, str):
            continue
        if "until:" not in line_str.lower():
            continue

        time_str, old_val = parse_schedule_until_line(line_str)
        if time_str is None:
            continue

        mins = _time_to_minutes(time_str)
        new_val = _pick_fraction_for_time(mins, morning_val, peak_val, afternoon_val, evening_val)
        sched_obj.fieldvalues[i] = f"Until: {time_str},{new_val:.2f}"

    print(f"[DHW] Updated usage fraction schedule '{sched_obj.Name}' with new daypattern.")


def _partially_update_setpoint_schedule(sched_obj, setpoint_c):
    """
    Loops over existing "Until: HH:MM, old_val" lines, 
    sets all numeric portions to `setpoint_c`.
    """
    field_count = len(sched_obj.fieldvalues)
    for i in range(field_count):
        line_str = sched_obj.fieldvalues[i]
        if not isinstance(line_str, str):
            continue
        if "until:" not in line_str.lower():
            continue

        time_str, old_val = parse_schedule_until_line(line_str)
        if time_str is None:
            continue

        sched_obj.fieldvalues[i] = f"Until: {time_str},{setpoint_c:.2f}"

    print(f"[DHW] Updated setpoint schedule '{sched_obj.Name}' => {setpoint_c} °C for all blocks.")


def parse_schedule_until_line(line_str: str):
    """
    Parses a single line like "Until: 07:00, 15.0".
    Returns (time_str, float_value).
    If parsing fails, returns (None, None).
    """
    if not isinstance(line_str, str):
        return (None, None)
    line_str = line_str.strip()
    if not line_str.lower().startswith("until:"):
        return (None, None)

    try:
        remainder = line_str.split("Until:", 1)[1].strip()  # e.g. "07:00,15.0"
        time_part, val_str = remainder.split(",", 1)
        time_str = time_part.strip()
        val_float = float(val_str.strip())
        return (time_str, val_float)
    except:
        return (None, None)


def _time_to_minutes(tstr):
    """
    Converts "HH:MM" to integer minutes. 
    E.g. "06:00" => 360, "10:30" => 630. 
    Returns 9999 if parsing fails.
    """
    try:
        parts = tstr.split(":")
        hh = int(parts[0])
        mm = int(parts[1]) if len(parts) > 1 else 0
        return hh * 60 + mm
    except:
        return 9999


def _pick_fraction_for_time(mins, morning_val, peak_val, afternoon_val, evening_val):
    """
    Returns the usage fraction based on intervals:
      0 <= t < 360(6:00) => 0.0
      360 <= t < 480(8:00) => morning_val
      480 <= t < 600(10:00) => peak_val
      600 <= t < 1020(17:00) => afternoon_val
      1020<= t <1260(21:00) => evening_val
      >=1260 => morning_val
    Adjust as you wish.
    """
    if mins < 360:   # before 06:00
        return 0.0
    elif mins < 480: # 06:00 - 08:00
        return morning_val
    elif mins < 600: # 08:00 - 10:00
        return peak_val
    elif mins < 1020: # 10:00 - 17:00
        return afternoon_val
    elif mins < 1260: # 17:00 - 21:00
        return evening_val
    else:            # 21:00 - 24:00
        return morning_val
