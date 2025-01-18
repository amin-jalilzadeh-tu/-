# ventilation/add_ventilation.py

from idf_objects.ventilation.assign_ventilation_values import assign_ventilation_params_with_overrides
from idf_objects.ventilation.schedules import (
    create_always_on_schedule,
    create_day_night_schedule,
    create_workhours_schedule
)
from idf_objects.ventilation.calc_functions import calc_infiltration, calc_required_ventilation_flow
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
    strategy="A",            # "A" => pick midpoint, "B" => random, etc.
    random_seed=None,
    user_config_vent=None,
    assigned_vent_log=None,
    zonelist_name="ALL_ZONES"  # <--- NEW param: specify which ZoneList to reference
):
    """
    Adds infiltration + ventilation to the IDF based on building_row data,
    but uses a single infiltration object and a single ventilation object
    that each reference a ZoneList (e.g. "ALL_ZONES"), rather than one object per zone.

    If system_type == "D", sets 'hrv_eff' on each zone's IdealLoads object.
    """

    # 1) Ensure key schedules exist
    if not idf.getobject("SCHEDULE:CONSTANT", "AlwaysOnSched"):
        create_always_on_schedule(idf, "AlwaysOnSched")
    if not idf.getobject("SCHEDULE:COMPACT", "VentSched_DayNight"):
        create_day_night_schedule(idf, "VentSched_DayNight")
    if not idf.getobject("SCHEDULE:COMPACT", "WorkHoursSched"):
        create_workhours_schedule(idf, "WorkHoursSched")

    # 2) Extract building data
    bldg_id = building_row.get("ogc_fid", 0)
    bldg_func = safe_lower(building_row.get("building_function", "residential"))
    if bldg_func not in ("residential", "non_residential"):
        bldg_func = "residential"

    age_range_str = building_row.get("age_range", "2015 and later")
    year_key = map_age_range_to_year_key(age_range_str)

    infiltration_key = map_infiltration_key(building_row)
    usage_key = map_usage_key(building_row)

    is_res = (bldg_func == "residential")
    floor_area_m2 = building_row.get("area", 100.0)
    scenario = building_row.get("scenario", "scenario1")

    # 3) Assign infiltration & ventilation parameters


    assigned_vent = assign_ventilation_params_with_overrides(
        building_id=bldg_id,
        building_function=bldg_func,
        age_range=age_range_str,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_vent=user_config_vent,
        assigned_vent_log=assigned_vent_log,
        infiltration_key=infiltration_key,
        year_key=year_key,
        is_residential=is_res,
        default_flow_exponent=0.67,
        usage_key=usage_key   # <--- Must be here

    )

    infiltration_base = assigned_vent["infiltration_base"]
    year_factor       = assigned_vent["year_factor"]
    system_type       = assigned_vent["system_type"]
    f_ctrl_val        = assigned_vent["f_ctrl"]
    fan_pressure      = assigned_vent["fan_pressure"]
    hrv_eff           = assigned_vent["hrv_eff"]

    # Schedules for infiltration & ventilation (could be "AlwaysOnSched", etc.)
    infiltration_sched = assigned_vent.get("infiltration_schedule_name", "AlwaysOnSched")
    ventilation_sched  = assigned_vent.get("ventilation_schedule_name",  "VentSched_DayNight")

    print(
        f"[VENT OVERRIDES] bldg_id={bldg_id}, infiltration={infiltration_base}, "
        f"year_factor={year_factor}, sys={system_type}, fanP={fan_pressure}, hrv_eff={hrv_eff}"
    )

    # 4) Calculate total infiltration flow (m³/s) for the whole building
    infiltration_m3_s_total = calc_infiltration(
        infiltration_base=infiltration_base,
        year_factor=year_factor,
        flow_exponent=0.67,
        floor_area_m2=floor_area_m2
    )

    # 5) Calculate total ventilation flow (m³/s) for the whole building
    vent_flow_m3_s_total = calc_required_ventilation_flow(
        building_function=bldg_func,
        f_ctrl_val=f_ctrl_val,
        floor_area_m2=floor_area_m2,
        usage_key=usage_key
    )

    # 6) Check zones in the IDF
    zones = idf.idfobjects["ZONE"]
    if not zones:
        print("[VENT] No zones found, skipping.")
        return
    n_zones = len(zones)

    # Because infiltration/vent objects replicate to each zone in the ZoneList,
    # we must give PER-ZONE flow = (total flow / number_of_zones).
    infiltration_per_zone = infiltration_m3_s_total / n_zones
    vent_per_zone         = vent_flow_m3_s_total / n_zones

    print(
        f"[VENTILATION] Bldg {bldg_id}, sys={system_type}, "
        f"infiltration(total)={infiltration_m3_s_total:.3f}, vent(total)={vent_flow_m3_s_total:.3f}, "
        f"zones={n_zones}, infiltration/zone={infiltration_per_zone:.4f}, vent/zone={vent_per_zone:.4f}"
    )

    # 7) Create a SINGLE infiltration object referencing the ZoneList
    #    => Each zone in that ZoneList gets infiltration_per_zone
    infil_obj = idf.getobject("ZONEINFILTRATION:DESIGNFLOWRATE", "Infiltration_AllZones")
    if not infil_obj:
        infil_obj = idf.newidfobject("ZONEINFILTRATION:DESIGNFLOWRATE")
        infil_obj.Name = "Infiltration_AllZones"
    infil_obj.Zone_or_ZoneList_Name = zonelist_name
    infil_obj.Schedule_Name = infiltration_sched
    infil_obj.Design_Flow_Rate_Calculation_Method = "Flow/Zone"
    infil_obj.Design_Flow_Rate = infiltration_per_zone
    infil_obj.Flow_coefficient = ""
    infil_obj.Crack_Distance_Factor = ""
    infil_obj.Sensible_Heat_Gain_Coefficient = ""
    infil_obj.Sensible_Heat_Loss_Coefficient = ""

    # 8) Create a SINGLE ventilation object referencing the ZoneList
    #    => Each zone in that ZoneList gets vent_per_zone
    vent_obj = idf.getobject("ZONEVENTILATION:DESIGNFLOWRATE", "Ventilation_AllZones")
    if not vent_obj:
        vent_obj = idf.newidfobject("ZONEVENTILATION:DESIGNFLOWRATE")
        vent_obj.Name = "Ventilation_AllZones"
    vent_obj.Zone_or_ZoneList_Name = zonelist_name
    vent_obj.Schedule_Name = ventilation_sched
    vent_obj.Design_Flow_Rate_Calculation_Method = "Flow/Zone"
    vent_obj.Design_Flow_Rate = vent_per_zone
    vent_obj.Fan_Pressure_Rise = fan_pressure  # if relevant
    vent_obj.Fan_Total_Efficiency = 0.7       # example default
    vent_obj.Fraction_of_Outdoor_Air = 1.0

    # 9) If system_type == "D", set HRV effectiveness on each zone's IdealLoads
    if system_type == "D" and hrv_eff > 0.0:
        for zone_obj in zones:
            zone_name = zone_obj.Name
            ideal_name = f"{zone_name} Ideal Loads"
            ideal_obj = idf.getobject("ZONEHVAC:IDEALLOADSAIRSYSTEM", ideal_name)
            if ideal_obj:
                if hasattr(ideal_obj, "Sensible_Heat_Recovery_Effectiveness"):
                    ideal_obj.Sensible_Heat_Recovery_Effectiveness = hrv_eff
                    print(f"   => {ideal_name} HRV eff set to {hrv_eff:.3f}")
            else:
                print(f"[VENT WARNING] {zone_name} Ideal Loads not found for system D. Skipping HRV eff.")

    return



#Important:

# EnergyPlus Behavior with ZoneList
#If you assign Zone_or_ZoneList_Name = "ALL_ZONES" in a ZoneInfiltration:DesignFlowRate or ZoneVentilation:DesignFlowRate, EnergyPlus automatically replicates that object for each zone in that ZoneList, with the same numeric inputs.
#So, if you put a total infiltration flow in Design_Flow_Rate and reference "ALL_ZONES", you’ll inadvertently multiply that total by the number of zones.
#Therefore, to achieve a total infiltration of X m³/s across the entire building, you must divide by the number of zones so that each zone receives its portion of X.
#Infiltration and Ventilation Variation
#This single-object approach assumes you want the same infiltration and ventilation rate for each zone. If you need them to differ by zone (due to exterior surface area, occupant loads, etc.), you’ll have to revert to creating per-zone objects.
#HRV/Energy Recovery
#The code below still loops over zones to set the HRV effectiveness in each ZONEHVAC:IDEALLOADSAIRSYSTEM, since each zone’s IdealLoads object is unique.