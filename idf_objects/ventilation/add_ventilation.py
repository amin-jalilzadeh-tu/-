# ventilation/add_ventilation.py

from idf_objects.ventilation.assign_ventilation_values import (
    assign_ventilation_params_with_overrides
)
from idf_objects.ventilation.schedules import (
    create_always_on_schedule,
    create_day_night_schedule,
    create_workhours_schedule
)
from idf_objects.ventilation.create_ventilation_systems import create_ventilation_system
from idf_objects.ventilation.calc_functions import (
    calc_infiltration,
    calc_required_ventilation_flow
)
from idf_objects.ventilation.mappings import (
    safe_lower,
    map_age_range_to_year_key,
    map_infiltration_key,
    map_usage_key
)

def add_ventilation_to_idf(
    idf,
    building_row,
    calibration_stage="pre_calibration",
    strategy="A",            # "A" => pick midpoint, "B" => random, ...
    random_seed=None,
    user_config_vent=None,
    assigned_vent_log=None
):
    """
    Adds infiltration + ventilation to the IDF based on building_row data
    (using assign_ventilation_params_with_overrides). Creates infiltration
    and (optionally) ventilation objects in each zone. Also logs both
    building-level and zone-level picks to assigned_vent_log.

    Args:
        idf: geomeppy IDF object
        building_row: dict-like row containing e.g. "ogc_fid", "building_function", "age_range", "scenario", "area"
        calibration_stage: str, e.g. "pre_calibration" or "post_calibration"
        strategy: str, e.g. "A" => midpoint, "B" => random
        random_seed: int or None
        user_config_vent: list of user override dicts for ventilation
        assigned_vent_log: dict to store final building-level & zone-level picks

    Returns:
        None. (The IDF is modified in place; the picks are stored in assigned_vent_log if provided.)
    """

    # 1) Ensure key schedules exist (the default ones)
    if not idf.getobject("SCHEDULE:CONSTANT", "AlwaysOnSched"):
        create_always_on_schedule(idf, "AlwaysOnSched")
    if not idf.getobject("SCHEDULE:COMPACT", "VentSched_DayNight"):
        create_day_night_schedule(idf, "VentSched_DayNight")
    if not idf.getobject("SCHEDULE:COMPACT", "WorkHoursSched"):
        create_workhours_schedule(idf, "WorkHoursSched")

    # 2) Extract building info
    bldg_id = building_row.get("ogc_fid", 0)
    bldg_func = safe_lower(building_row.get("building_function", "residential"))
    if bldg_func not in ("residential", "non_residential"):
        bldg_func = "residential"

    age_range_str = building_row.get("age_range", "2015 and later")
    scenario = building_row.get("scenario", "scenario1")
    floor_area_m2 = building_row.get("area", 100.0)

    # 3) Decide infiltration key, usage key, etc.
    infiltration_key = map_infiltration_key(building_row)
    usage_key = map_usage_key(building_row)
    is_res = (bldg_func == "residential")

    # 4) Call the function that picks infiltration_base, year_factor, schedules, etc.
    assigned_vent = assign_ventilation_params_with_overrides(
        building_id=bldg_id,
        building_function=bldg_func,
        age_range=age_range_str,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_vent=user_config_vent,
        assigned_vent_log=None,        # We'll do the logging here instead
        infiltration_key=infiltration_key,
        year_key=map_age_range_to_year_key(age_range_str),
        is_residential=is_res,
        default_flow_exponent=0.67
    )

    # 5) Unpack the chosen building-level picks
    infiltration_base   = assigned_vent["infiltration_base"]
    infiltration_rng    = assigned_vent["infiltration_base_range"]
    year_factor         = assigned_vent["year_factor"]
    year_factor_rng     = assigned_vent["year_factor_range"]
    fan_pressure        = assigned_vent["fan_pressure"]
    fan_pressure_rng    = assigned_vent["fan_pressure_range"]
    f_ctrl              = assigned_vent["f_ctrl"]
    f_ctrl_rng          = assigned_vent["f_ctrl_range"]
    hrv_eff             = assigned_vent["hrv_eff"]
    hrv_eff_rng         = assigned_vent["hrv_eff_range"]

    infiltration_sched  = assigned_vent["infiltration_schedule_name"]
    ventilation_sched   = assigned_vent["ventilation_schedule_name"]
    system_type         = assigned_vent["system_type"]
    flow_exponent       = assigned_vent["flow_exponent"]

    # 6) Print or debug
    print(
        f"[VENT OVERRIDES] bldg={bldg_id}, infiltration_base={infiltration_base}, "
        f"year_factor={year_factor}, sys={system_type}, f_ctrl={f_ctrl}, "
        f"fanP={fan_pressure}, hrv_eff={hrv_eff}, infiltration_sched={infiltration_sched}, "
        f"vent_sched={ventilation_sched}"
    )

    # 7) Calculate total infiltration & ventilation flows for the building
    infiltration_m3_s_total = calc_infiltration(
        infiltration_base=infiltration_base,
        year_factor=year_factor,
        flow_exponent=flow_exponent,
        floor_area_m2=floor_area_m2
    )
    vent_flow_m3_s_total = calc_required_ventilation_flow(
        building_function=bldg_func,
        f_ctrl_val=f_ctrl,
        floor_area_m2=floor_area_m2,
        usage_key=usage_key
    )

    # 7b) Retrieve zones
    zones = idf.idfobjects["ZONE"]
    if not zones:
        print("[VENT] No zones found, skipping creation of infiltration/ventilation objects.")
        return

    n_zones = len(zones)
    infiltration_per_zone = infiltration_m3_s_total / n_zones
    vent_per_zone = vent_flow_m3_s_total / n_zones

    # 8) If we want to store building-level data in assigned_vent_log
    if assigned_vent_log is not None:
        if bldg_id not in assigned_vent_log:
            assigned_vent_log[bldg_id] = {}

        assigned_vent_log[bldg_id]["building_params"] = {
            # Numeric picks + ranges
            "infiltration_base": infiltration_base,
            "infiltration_base_range": infiltration_rng,
            "year_factor": year_factor,
            "year_factor_range": year_factor_rng,
            "fan_pressure": fan_pressure,
            "fan_pressure_range": fan_pressure_rng,
            "f_ctrl": f_ctrl,
            "f_ctrl_range": f_ctrl_rng,
            "hrv_eff": hrv_eff,
            "hrv_eff_range": hrv_eff_rng,
            # Schedules
            "infiltration_schedule_name": infiltration_sched,
            "ventilation_schedule_name": ventilation_sched,
            "system_type": system_type,
            "flow_exponent": flow_exponent,
            # Flows for entire building
            "infiltration_total_m3_s": infiltration_m3_s_total,
            "ventilation_total_m3_s": vent_flow_m3_s_total
        }

        # We'll create a sub-dict for zone-level data
        assigned_vent_log[bldg_id]["zones"] = {}

    print(
        f"[VENTILATION] Building {bldg_id}, system={system_type}, infiltration={infiltration_m3_s_total:.3f} m3/s, "
        f"vent={vent_flow_m3_s_total:.3f} m3/s, #zones={n_zones}"
    )

    # 9) For each zone => create infiltration + ventilation objects
    for zone_obj in zones:
        zone_name = zone_obj.Name

        iobj, vobj = create_ventilation_system(
            idf=idf,
            building_function=bldg_func,
            system_type=system_type,
            zone_name=zone_name,
            infiltration_m3_s=infiltration_per_zone,
            vent_flow_m3_s=vent_per_zone,
            infiltration_sched_name=infiltration_sched,
            ventilation_sched_name=ventilation_sched,
            pick_strategy="random" if strategy == "B" else "midpoint"
        )

        print(
            f"   => Created infiltration for {zone_name}: {infiltration_per_zone:.4f} m3/s, "
            f"ventilation: {vent_per_zone:.4f} m3/s"
        )

        # 9b) Log zone-level data
        if assigned_vent_log is not None:
            assigned_vent_log[bldg_id]["zones"][zone_name] = {
                "infiltration_object_name": iobj.Name,
                "infiltration_object_type": iobj.key,
                "infiltration_flow_m3_s": infiltration_per_zone,
                "infiltration_schedule_name": infiltration_sched,
                # If system_type != "D", we have vobj => ZONEVENTILATION:DESIGNFLOWRATE
                # If system_type == "D", vobj might be the same as iobj or None
                #   Actually in create_ventilation_system, iobj is infiltration, vobj is either
                #   a ZONEVENTILATION:DESIGNFLOWRATE or an IdealLoads object (for system D).
                "ventilation_object_name": vobj.Name if vobj else None,
                "ventilation_object_type": vobj.key if vobj else None,
                "ventilation_flow_m3_s": vent_per_zone if vobj else 0.0,
                "ventilation_schedule_name": ventilation_sched
            }

    # 10) If system_type == "D", optionally confirm HRV on IdealLoads
    # (The create_ventilation_system already sets sensible HRV if the IDD field exists).
    if system_type == "D" and hrv_eff > 0.0:
        for zone_obj in zones:
            zone_name = zone_obj.Name
            ideal_name = f"{zone_name} Ideal Loads"
            ideal_obj = idf.getobject("ZONEHVAC:IDEALLOADSAIRSYSTEM", ideal_name)
            if not ideal_obj:
                print(f"[VENT WARNING] {zone_name}: Ideal Loads not found for system D, can't set HRV.")
            else:
                if hasattr(ideal_obj, "Sensible_Heat_Recovery_Effectiveness"):
                    # It's presumably set in create_ventilation_system, but you could confirm or adjust:
                    print(f"      -> {zone_name} IdealLoads has HRV = {hrv_eff:.2f}")
                else:
                    print(f"      -> {zone_name} IdealLoads object lacks HRV fields in IDD.")
