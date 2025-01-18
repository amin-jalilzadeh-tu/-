# DHW/parameters.py

def calculate_dhw_parameters(
    assigned: dict,
    floor_area_m2: float = None,
    occupant_count: int = None,
    assigned_dhw_log: dict = None,
    building_id=None
):
    """
    assigned = {
       "occupant_density_m2_per_person": ...,
       "liters_per_person_per_day": ...,
       "default_tank_volume_liters": ...,
       "default_heater_capacity_w": ...,
       "setpoint_c": ...,
       "usage_split_factor": ...,
       "peak_hours": ...
       (plus schedule fields if needed)
    }

    We compute:
      occupant_count (if not given)
      daily_liters
      peak_flow_m3s
      tank_volume_m3
      heater_capacity_w
      setpoint_c

    If assigned_dhw_log and building_id are provided, we can
    store these derived values in the log as well.
    """

    occupant_density = assigned.get("occupant_density_m2_per_person", None)
    liters_per_person = assigned.get("liters_per_person_per_day", 50.0)
    tank_liters = assigned.get("default_tank_volume_liters", 200.0)
    heater_w = assigned.get("default_heater_capacity_w", 4000.0)
    setpoint_c = assigned.get("setpoint_c", 60.0)
    usage_split_factor = assigned.get("usage_split_factor", 0.6)
    peak_hours = assigned.get("peak_hours", 2.0)

    # 1) occupant_count
    if occupant_count is None:
        if occupant_density and floor_area_m2:
            occupant_count = floor_area_m2 / occupant_density
        else:
            occupant_count = 4  # fallback
    occupant_count = int(round(occupant_count))

    # 2) daily liters
    daily_liters = occupant_count * liters_per_person

    # 3) daily m³
    daily_m3 = daily_liters / 1000.0

    # 4) peak flow
    if peak_hours > 0:
        peak_flow_m3s = (daily_m3 * usage_split_factor) / (peak_hours * 3600.0)
    else:
        peak_flow_m3s = daily_m3 / (24.0 * 3600.0)

    # 5) tank volume (m3)
    tank_volume_m3 = tank_liters / 1000.0

    # 6) Optionally log these derived values
    if assigned_dhw_log is not None and building_id is not None:
        if building_id not in assigned_dhw_log:
            assigned_dhw_log[building_id] = {}
        assigned_dhw_log[building_id]["dhw_occupant_count"] = occupant_count
        assigned_dhw_log[building_id]["dhw_daily_liters"] = daily_liters
        assigned_dhw_log[building_id]["dhw_peak_flow_m3s"] = peak_flow_m3s
        assigned_dhw_log[building_id]["dhw_tank_volume_m3"] = tank_volume_m3
        assigned_dhw_log[building_id]["dhw_heater_capacity_w"] = heater_w
        assigned_dhw_log[building_id]["dhw_setpoint_c"] = setpoint_c

    return {
        "occupant_count": occupant_count,
        "daily_liters": daily_liters,
        "peak_flow_m3s": peak_flow_m3s,
        "tank_volume_m3": tank_volume_m3,
        "heater_capacity_w": heater_w,
        "setpoint_c": setpoint_c
    }
