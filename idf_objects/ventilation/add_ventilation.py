# ventilation/add_ventilation.py

import math # Import math for isnan check if needed
from typing import Optional, Dict, Any # Added typing

# Import specific objects/functions - ensure correct imports
try:
    from geomeppy import IDF
except ImportError:
    IDF = Any # Fallback if geomeppy not available

from idf_objects.ventilation.assign_ventilation_values import (
    assign_ventilation_params_with_overrides
)
from idf_objects.ventilation.schedules import (
    create_always_on_schedule,
    create_day_night_schedule,
    create_workhours_schedule,
    # ensure_schedule_type_limits # May not be needed here, called within schedule creation
)
from idf_objects.ventilation.create_ventilation_systems import create_ventilation_system
# ----- CORRECTED IMPORT HERE -----
from idf_objects.ventilation.calc_functions import (
    calc_infiltration_base_rate_per_m2, # <-- Use the new function name
    calc_required_ventilation_flow
)
# ----- END CORRECTION -----
from idf_objects.ventilation.mappings import (
    safe_lower,
    map_age_range_to_year_key,
    map_infiltration_key,
    map_usage_key
)

# Define type alias for clarity
BuildingRow = Dict[str, Any]
ZoneInfoMap = Dict[str, Dict[str, Any]]
AssignedVentLog = Dict[Any, Dict[str, Any]]


def add_ventilation_to_idf(
    idf: IDF,
    building_row: BuildingRow,
    calibration_stage: str ="pre_calibration",
    strategy: str ="A",            # "A" => pick midpoint, "B" => random, ...
    random_seed: Optional[int] =None,
    user_config_vent: Optional[list] =None,
    assigned_vent_log: Optional[AssignedVentLog] =None,
    zone_details: Optional[ZoneInfoMap] =None # Optional: Pre-calculated dict {zone_name: {area: A, vol: V, ext_area: E, is_core: bool}}
):
    """
    Adds infiltration + ventilation to the IDF based on building_row data.
    Determines system type and parameters using assign_ventilation_params_with_overrides.
    Calculates required flows and distributes them per zone based on area/type.
    Creates infiltration and (optionally) ventilation objects in each zone via create_ventilation_system.
    Logs building-level parameters and zone-level flows/objects to assigned_vent_log.

    Args:
        idf: geomeppy IDF object
        building_row: dict-like row containing e.g. "ogc_fid", "building_function", "age_range", "scenario", "area"
        calibration_stage: str, e.g. "pre_calibration" or "post_calibration"
        strategy: str, e.g. "A" => midpoint, "B" => random
        random_seed: int or None
        user_config_vent: list of user override dicts for ventilation
        assigned_vent_log: dict to store final building-level & zone-level picks
        zone_details: dict (optional), pre-calculated zone properties like area, volume, exterior area, core status.

    Returns:
        None. (The IDF is modified in place; the picks are stored in assigned_vent_log if provided.)
    """

    # --- 1) Ensure key schedules exist ---
    # Schedules module now handles ensuring ScheduleTypeLimits internally
    create_always_on_schedule(idf, "AlwaysOnSched")
    create_day_night_schedule(idf, "VentSched_DayNight")
    create_workhours_schedule(idf, "WorkHoursSched")

    # --- 2) Extract building info ---
    bldg_id = building_row.get("ogc_fid", 0)
    bldg_func = safe_lower(building_row.get("building_function", "residential"))
    if bldg_func not in ("residential", "non_residential"):
        bldg_func = "residential"

    age_range_str = building_row.get("age_range", "2015 and later")
    scenario = building_row.get("scenario", "scenario1")
    # Use total building floor area primarily for required ventilation calculation
    total_bldg_floor_area_m2 = building_row.get("area", 100.0)
    if total_bldg_floor_area_m2 is None or math.isnan(total_bldg_floor_area_m2) or total_bldg_floor_area_m2 <= 0:
         print(f"[VENT WARNING] Invalid total building floor area ({total_bldg_floor_area_m2}), defaulting to 100.0 m2.")
         total_bldg_floor_area_m2 = 100.0

    # --- 3) Decide lookup keys ---
    infiltration_key = map_infiltration_key(building_row)
    usage_key = map_usage_key(building_row)
    year_key = map_age_range_to_year_key(age_range_str)
    is_res = (bldg_func == "residential")

    # --- 4) Assign building-level ventilation parameters from lookups/overrides ---
    assigned_vent = assign_ventilation_params_with_overrides(
        building_id=bldg_id,
        building_function=bldg_func,
        age_range=age_range_str,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_vent=user_config_vent,
        assigned_vent_log=None,  # Log locally first
        infiltration_key=infiltration_key,
        year_key=year_key,
        is_residential=is_res,
        default_flow_exponent=0.67 # Standard exponent
    )

    # --- 5) Unpack the chosen building-level parameters ---
    infiltration_base   = assigned_vent["infiltration_base"]
    infiltration_rng    = assigned_vent["infiltration_base_range"]
    year_factor         = assigned_vent["year_factor"]
    year_factor_rng     = assigned_vent["year_factor_range"]
    # fan_pressure        = assigned_vent["fan_pressure"] # Might not be used directly here
    # fan_pressure_rng    = assigned_vent["fan_pressure_range"]
    f_ctrl              = assigned_vent["f_ctrl"]
    f_ctrl_rng          = assigned_vent["f_ctrl_range"]
    hrv_eff             = assigned_vent["hrv_eff"]
    hrv_eff_rng         = assigned_vent["hrv_eff_range"]

    infiltration_sched  = assigned_vent["infiltration_schedule_name"]
    ventilation_sched   = assigned_vent["ventilation_schedule_name"]
    system_type         = assigned_vent["system_type"]
    flow_exponent       = assigned_vent["flow_exponent"]

    # --- 6) Debug Print ---
    print(
        f"[VENT PARAMS] bldg={bldg_id}, func={bldg_func}, age={age_range_str}\n"
        f"  Lookup Keys: infil='{infiltration_key}', usage='{usage_key}', year='{year_key}'\n"
        f"  Chosen Params: infiltration_base={infiltration_base:.3f}, year_factor={year_factor:.3f}, "
        f"sys={system_type}, f_ctrl={f_ctrl:.3f}, hrv_eff={hrv_eff:.3f}\n"
        f"  Schedules: infil='{infiltration_sched}', vent='{ventilation_sched}'"
    )

    # --- 7) Calculate Base Infiltration Rate (@1Pa) per m2 floor area ---
    # ----- CORRECTED FUNCTION CALL HERE -----
    infiltration_rate_qv1_m3_h_per_m2 = calc_infiltration_base_rate_per_m2(
        infiltration_base=infiltration_base,
        year_factor=year_factor,
        flow_exponent=flow_exponent
    )
    # ----- END CORRECTION -----


    # --- 8) Calculate Total Required Ventilation Flow (respecting minimums) ---
    vent_flow_m3_s_total = calc_required_ventilation_flow(
        building_function=bldg_func,
        f_ctrl_val=f_ctrl,
        floor_area_m2=total_bldg_floor_area_m2, # Use total area here
        usage_key=usage_key
    )

    # --- 9) Determine DSOA object name and ensure it exists ---
    # Assuming SIZING:ZONE uses "DSOA_Global". This name should be consistent.
    dsoa_object_name = "DSOA_Global"
    if system_type == "D":
        dsoa_obj = idf.getobject("DESIGNSPECIFICATION:OUTDOORAIR", dsoa_object_name.upper()) # Use upper for check
        if not dsoa_obj:
            print(f"[VENT INFO] Creating default {dsoa_object_name} object.")
            try:
                dsoa_obj = idf.newidfobject("DESIGNSPECIFICATION:OUTDOORAIR")
                dsoa_obj.Name = dsoa_object_name
                dsoa_obj.Outdoor_Air_Method = "Sum"
                # Set default rates (these might need adjustment based on standards)
                dsoa_obj.Outdoor_Air_Flow_per_Person = 0.00236 # ~5 cfm/person (Lowish for residential)
                dsoa_obj.Outdoor_Air_Flow_per_Zone_Floor_Area = 0.000305 # ~0.06 cfm/ft2
                dsoa_obj.Outdoor_Air_Flow_per_Zone = 0
                dsoa_obj.Outdoor_Air_Flow_Air_Changes_per_Hour = 0
                # Schedule Type Limits for OutdoorAir objects might be needed - handled in schedules.py now?
                # ensure_schedule_type_limits(idf, "Minimum Outdoor Air Flow Rate", unit_type="VolumetricFlowRate") # Example if needed here
            except Exception as e:
                 print(f"[ERROR] Failed to create DESIGNSPECIFICATION:OUTDOORAIR {dsoa_object_name}: {e}")
                 # If DSOA creation fails, System D might not work correctly. Consider implications.


    # --- 10) Get Zones and Calculate Total Zone Floor Area for Distribution ---
    zones = idf.idfobjects["ZONE"]
    if not zones:
        print("[VENT ERROR] No zones found, skipping creation of infiltration/ventilation objects.")
        return

    n_zones = len(zones)
    calculated_total_zone_floor_area = 0.0
    zone_info_map: ZoneInfoMap = {} # Store fetched info

    # Pre-calculate zone areas and identify core zones
    if zone_details:
        # Use pre-calculated details if provided
        calculated_total_zone_floor_area = sum(d.get('area', 0) for d in zone_details.values() if d.get('area') and d['area'] > 0)
        zone_info_map = zone_details # Assumes zone_details includes 'area' and 'is_core'
    else:
        # Calculate on the fly
        print("[VENT INFO] Calculating zone areas on the fly...")
        for zone_obj in zones:
            zone_name = zone_obj.Name
            zone_area = 0.0 # Default
            try:
                # Attempt to get floor area using geomeppy's property
                zone_area = zone_obj.floor_area # Assumes geomeppy IDF object
                if isinstance(zone_area, str) or zone_area <= 0:
                     raise ValueError("Invalid area value initially")
            except (AttributeError, ValueError, Exception):
                 try:
                     # Fallback or alternative method if .floor_area fails/is bad
                     zone_area = float(zone_obj.Floor_Area) # Access raw field if needed
                     if zone_area <= 0: raise ValueError("Raw Floor_Area field <= 0")
                 except (AttributeError, ValueError, Exception) as area_err:
                     print(f"[VENT WARNING] Could not get valid floor area for zone {zone_name}: {area_err}. Excluding from area sum.")
                     zone_area = 0.0 # Treat as zero area if retrieval fails

            is_core = "_core" in safe_lower(zone_name) # Simple check based on naming convention
            zone_info_map[zone_name] = {'area': zone_area, 'is_core': is_core}
            calculated_total_zone_floor_area += zone_area

    if calculated_total_zone_floor_area <= 0:
         print("[VENT ERROR] Total calculated zone floor area is zero or negative. Cannot distribute flows accurately.")
         # Fallback: Use building area if zone areas failed
         if total_bldg_floor_area_m2 > 0:
              print(f"[VENT WARNING] Using total building area {total_bldg_floor_area_m2} for flow distribution due to zone area issues.")
              calculated_total_zone_floor_area = total_bldg_floor_area_m2
              # Need to assign area back to zones for proportional split, maybe equally? Risky.
              # Reverting to equal split if zone areas are unreliable
              print("[VENT WARNING] Reverting to equal flow split per zone due to area calculation issues.")
              use_equal_split = True
              # Re-populate zone_info_map with equal area fraction if needed for loop below
              equal_area_per_zone = total_bldg_floor_area_m2 / n_zones if n_zones > 0 else 0
              for z_name in zone_info_map: zone_info_map[z_name]['area'] = equal_area_per_zone

         else:
              print("[VENT ERROR] Cannot proceed without valid floor area.")
              return # Cannot proceed
    else:
         use_equal_split = False

    # --- 11) Log Building-Level Parameters (Before Zone Loop) ---
    if assigned_vent_log is not None:
        if bldg_id not in assigned_vent_log:
            assigned_vent_log[bldg_id] = {}

        # Use assigned_vent dict directly as it contains all needed params + ranges
        assigned_vent_log[bldg_id]["building_params"] = assigned_vent.copy() # Use a copy

        # Add calculated rates/totals to the log
        assigned_vent_log[bldg_id]["building_params"]["infiltration_rate_qv1_m3_h_per_m2"] = infiltration_rate_qv1_m3_h_per_m2
        assigned_vent_log[bldg_id]["building_params"]["ventilation_total_required_m3_s"] = vent_flow_m3_s_total
        assigned_vent_log[bldg_id]["building_params"]["total_bldg_floor_area_m2"] = total_bldg_floor_area_m2
        assigned_vent_log[bldg_id]["building_params"]["total_zone_floor_area_m2_calc"] = calculated_total_zone_floor_area
        assigned_vent_log[bldg_id]["building_params"]["distribution_method"] = "EqualSplitFallback" if use_equal_split else "ProportionalArea"

        # Prepare for zone data
        assigned_vent_log[bldg_id]["zones"] = {}

    print(
        f"[VENTILATION FLOWS] Building {bldg_id}: System={system_type}, "
        f"Base Infil Rate (@1Pa)={infiltration_rate_qv1_m3_h_per_m2:.3f} m3/h/m2, "
        f"Total Vent Required={vent_flow_m3_s_total:.4f} m3/s, "
        f"Dist Method={'EqualSplitFallback' if use_equal_split else 'ProportionalArea'}"
    )

    # --- 12) Loop Through Zones: Calculate Zone Flows & Create Objects ---
    for zone_obj in zones:
        zone_name = zone_obj.Name
        zone_info = zone_info_map.get(zone_name, {'area': 0, 'is_core': "_core" in safe_lower(zone_name)}) # Add default is_core check
        zone_floor_area = zone_info.get('area', 0)
        is_core = zone_info.get('is_core', False)

        # --- Calculate Infiltration Flow for this Zone ---
        infiltration_for_this_zone_m3_s = 0.0
        if use_equal_split:
             # Fallback calculation (equal split of total potential infiltration)
             base_total_infil_m3s = (infiltration_rate_qv1_m3_h_per_m2 * calculated_total_zone_floor_area) / 3600.0 # Use area sum used for split
             infiltration_for_this_zone_m3_s = base_total_infil_m3s / n_zones if n_zones > 0 else 0.0
        elif is_core:
            # Assign minimal or zero infiltration to core zones
            infiltration_for_this_zone_m3_s = 0.0 # Or a very small nominal value if preferred
        elif zone_floor_area > 0:
            # Apply base rate to perimeter zone's floor area
            # Convert m3/h/m2 * m2 => m3/h, then divide by 3600 => m3/s
            infiltration_for_this_zone_m3_s = (infiltration_rate_qv1_m3_h_per_m2 * zone_floor_area) / 3600.0
        # else: zone_area is 0, flow remains 0

        # --- Calculate Ventilation Flow for this Zone ---
        ventilation_for_this_zone_m3_s = 0.0
        if use_equal_split:
             # Fallback if area calculation failed
             ventilation_for_this_zone_m3_s = vent_flow_m3_s_total / n_zones if n_zones > 0 else 0.0
        elif calculated_total_zone_floor_area > 0 and zone_floor_area >= 0: # Allow zone_area 0 here
            # Distribute total required ventilation proportionally to zone floor area
            proportion = (zone_floor_area / calculated_total_zone_floor_area) if calculated_total_zone_floor_area > 0 else 0
            ventilation_for_this_zone_m3_s = vent_flow_m3_s_total * proportion
        # else: total area is 0, flow remains 0

        # --- Create IDF Objects ---
        # Pass zone-specific flows and DSOA name
        # Make sure hrv effectiveness values are passed correctly
        iobj, vobj = create_ventilation_system(
            idf=idf,
            building_function=bldg_func,
            system_type=system_type,
            zone_name=zone_name,
            # Pass calculated zone-specific flows
            infiltration_m3_s=infiltration_for_this_zone_m3_s,
            vent_flow_m3_s=ventilation_for_this_zone_m3_s,
            infiltration_sched_name=infiltration_sched,
            ventilation_sched_name=ventilation_sched,
            pick_strategy="random" if strategy == "B" else "midpoint", # Strategy for fan efficiency etc.
            # Pass DSOA name for System D configuration
            dsoa_object_name=dsoa_object_name if system_type == "D" else None,
            # Pass HRV effectiveness for System D
            hrv_sensible_effectiveness = hrv_eff if system_type == "D" else 0.0,
            # Pass latent effectiveness if it exists in assigned_vent (add if needed)
            hrv_latent_effectiveness = assigned_vent.get("hrv_lat_eff", 0.0) if system_type == "D" else 0.0
        )

        # --- Log Zone-Level Data ---
        if assigned_vent_log is not None and bldg_id in assigned_vent_log:
            assigned_vent_log[bldg_id]["zones"][zone_name] = {
                "infiltration_object_name": iobj.Name if iobj else None,
                "infiltration_object_type": iobj.key if iobj else None,
                "infiltration_flow_m3_s": infiltration_for_this_zone_m3_s, # Log the calculated zone flow
                "infiltration_schedule_name": infiltration_sched,
                "ventilation_object_name": vobj.Name if vobj else None,
                "ventilation_object_type": vobj.key if vobj else None,
                "ventilation_flow_m3_s": ventilation_for_this_zone_m3_s if vobj else 0.0, # Log the calculated zone flow
                "ventilation_schedule_name": ventilation_sched,
                "zone_floor_area": zone_floor_area,
                "is_core": is_core
            }
        elif assigned_vent_log is not None:
             print(f"[WARNING] Building ID {bldg_id} not found in assigned_vent_log for zone {zone_name}")


    print(f"[VENTILATION] Completed ventilation setup for Building {bldg_id}.")