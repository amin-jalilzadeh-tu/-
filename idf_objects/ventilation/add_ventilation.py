# ventilation/add_ventilation.py

import math
from typing import Optional, Dict, Any

# Import specific objects/functions - ensure correct imports
try:
    from geomeppy import IDF
except ImportError:
    IDF = Any

# Import local modules
from idf_objects.ventilation.assign_ventilation_values import (
    assign_ventilation_params_with_overrides
)
from idf_objects.ventilation import schedules # Updated import to get the module
from idf_objects.ventilation.create_ventilation_systems import create_ventilation_system
from idf_objects.ventilation.calc_functions import (
    calc_infiltration_rate_at_1Pa_per_m2,
    calc_required_ventilation_flow
)
from idf_objects.ventilation.mappings import (
    safe_lower,
    map_age_range_to_year_key,
    map_infiltration_key, # This provides the archetype_key
    map_usage_key
)

# Define type alias for clarity
BuildingRow = Dict[str, Any]
ZoneInfoMap = Dict[str, Dict[str, Any]] # e.g., {zone_name: {'area': float, 'is_core': bool}}
AssignedVentLog = Dict[Any, Dict[str, Any]]


def get_zone_floor_area_from_surfaces(idf: IDF, zone_name: str) -> float:
    """
    Calculates the zone's floor area by summing the areas of its 'floor' surfaces.
    This is a fallback if the ZONE object's Floor_Area is 'autocalculate' or not resolved.
    """
    total_floor_surface_area = 0.0
    surfaces = idf.idfobjects.get("BUILDINGSURFACE:DETAILED", [])
    if not surfaces:
        surfaces = idf.idfobjects.get("BuildingSurface:Detailed", [])

    for surface in surfaces:
        try:
            surface_zone_name = getattr(surface, 'Zone_Name', None)
            if surface_zone_name is None:
                continue

            surface_type_attr = getattr(surface, 'Surface_Type', '').lower()

            if surface_zone_name.upper() == zone_name.upper() and surface_type_attr == 'floor':
                surface_area = getattr(surface, 'area', 0.0)
                if surface_area <= 1e-6 and hasattr(surface, 'Gross_Area'):
                    try:
                        surface_area = float(surface.Gross_Area)
                    except (ValueError, TypeError):
                        surface_area = 0.0
                if isinstance(surface_area, (float, int)) and surface_area > 0:
                    total_floor_surface_area += surface_area
        except Exception as e:
            surface_id = getattr(surface, 'Name', 'UnknownSurface')
            print(f"[WARNING] add_ventilation.py: Error accessing properties for surface '{surface_id}' in zone '{zone_name}': {e}")
            continue

    if total_floor_surface_area > 1e-6:
        print(f"[VENT INFO] add_ventilation.py: Calculated floor area for zone '{zone_name}' by summing floor surfaces: {total_floor_surface_area:.2f} m2.")
    return total_floor_surface_area


def add_ventilation_to_idf(
    idf: IDF,
    building_row: BuildingRow,
    calibration_stage: str = "pre_calibration",
    strategy: str = "A", # This is the parameter picking strategy (A, B, C)
    random_seed: Optional[int] = None,
    user_config_vent: Optional[list] = None,
    assigned_vent_log: Optional[AssignedVentLog] = None,
    zone_details: Optional[ZoneInfoMap] = None,
    system_d_infiltration_reduction_factor: float = 1.0,
    infiltration_model: str = "constant",
    typical_delta_t: float = 10.0,
    typical_wind: float = 3.0
):
    """
    Adds infiltration + ventilation to the IDF based on building_row data,
    using archetype-specific schedules.
    """

    # --- 1) Ensure Fallback Schedules Exist ---
    # Only 'AlwaysOnSched' is strictly needed as a global fallback.
    # Archetype-specific schedules will be created dynamically.
    schedules.create_always_on_schedule(idf, "AlwaysOnSched")
    # The generic day/night and workhours schedules are no longer created by default here.
    # They can be created by schedules.get_or_create_archetype_schedule if its lookup points to their patterns.

    # --- 2) Extract building info ---
    bldg_id = building_row.get("ogc_fid", "UnknownBuildingID")
    bldg_func = safe_lower(building_row.get("building_function", "residential"))
    if bldg_func not in ("residential", "non_residential"):
        bldg_func = "residential"

    age_range_str = building_row.get("age_range", "2015 and later")
    scenario = building_row.get("scenario", "scenario1")
    total_bldg_floor_area_m2_input = building_row.get("area", 100.0)

    if not isinstance(total_bldg_floor_area_m2_input, (int, float)) or total_bldg_floor_area_m2_input <= 0:
        print(f"[VENT WARNING] add_ventilation.py: Building {bldg_id}: Invalid total building floor area attribute ('area': {total_bldg_floor_area_m2_input}). Defaulting to 100.0 m2.")
        total_bldg_floor_area_m2_input = 100.0

    # --- 3) Decide lookup keys ---
    # 'infiltration_key' serves as the primary archetype key for schedules as well
    archetype_key = map_infiltration_key(building_row)
    usage_key = map_usage_key(building_row)
    year_key = map_age_range_to_year_key(age_range_str)
    is_res = (bldg_func == "residential")

    # --- 4) Assign building-level ventilation parameters ---
    # This now also determines the *names* for archetype-specific schedules
    assigned_vent = assign_ventilation_params_with_overrides(
        building_id=bldg_id, building_function=bldg_func, age_range=age_range_str,
        scenario=scenario, calibration_stage=calibration_stage, strategy=strategy,
        random_seed=random_seed, user_config_vent=user_config_vent,
        infiltration_key=archetype_key, year_key=year_key, is_residential=is_res,
        default_flow_exponent=0.67
    )

    # --- 5) Unpack chosen building-level parameters ---
    infiltration_base_L_s_m2_10Pa = assigned_vent["infiltration_base_L_s_m2_10Pa"]
    year_factor = assigned_vent["year_factor"]
    fan_pressure_Pa = assigned_vent.get("fan_pressure")
    fan_total_efficiency = assigned_vent.get("fan_total_efficiency")
    f_ctrl = assigned_vent["f_ctrl"]
    hrv_sens_eff = assigned_vent["hrv_eff"]
    hrv_lat_eff = assigned_vent.get("hrv_lat_eff", 0.0)
    # These are now archetype-specific names (or overridden by user_config_vent)
    final_infiltration_sched_name = assigned_vent["infiltration_schedule_name"]
    final_ventilation_sched_name = assigned_vent["ventilation_schedule_name"]
    system_type = assigned_vent["system_type"]
    flow_exponent = assigned_vent["flow_exponent"]
    # The 'strategy' (A, B, C) used for picking parameters will also be used for picking schedule values
    parameter_pick_strategy = strategy # Keep the original strategy name for clarity if needed

    # --- 6) Ensure Archetype-Specific Schedules are Created and Get Chosen Patterns ---
    vent_sched_obj, chosen_vent_wd_pattern, chosen_vent_we_pattern = schedules.get_or_create_archetype_schedule(
        idf=idf,
        target_schedule_name=final_ventilation_sched_name,
        building_function=bldg_func,
        archetype_key=archetype_key,
        purpose="ventilation",
        strategy=parameter_pick_strategy # Use the same strategy for schedule value picking
    )

    infil_sched_obj, chosen_infil_wd_pattern, chosen_infil_we_pattern = schedules.get_or_create_archetype_schedule(
        idf=idf,
        target_schedule_name=final_infiltration_sched_name,
        building_function=bldg_func,
        archetype_key=archetype_key,
        purpose="infiltration",
        strategy=parameter_pick_strategy
    )

    if not vent_sched_obj:
        print(f"[VENT CRITICAL] add_ventilation.py: Failed to create ventilation schedule '{final_ventilation_sched_name}' for Bldg {bldg_id}. Aborting ventilation setup.")
        return
    if not infil_sched_obj:
        print(f"[VENT CRITICAL] add_ventilation.py: Failed to create infiltration schedule '{final_infiltration_sched_name}' for Bldg {bldg_id}. Aborting ventilation setup.")
        return
        
    # Update names in case a fallback name was used by get_or_create_archetype_schedule
    final_ventilation_sched_name = vent_sched_obj.Name
    final_infiltration_sched_name = infil_sched_obj.Name
    
    # --- 7) Debug Print (now includes final schedule names) ---
    print(
        f"[VENT PARAMS] Bldg={bldg_id}, Func={bldg_func}, AgeKey='{year_key}', Sys={system_type}\n"
        f"  LookupKeys: Archetype='{archetype_key}', Usage='{usage_key if usage_key else 'N/A'}'\n"
        f"  InfilParams: Base(L/s/m2@10Pa)={infiltration_base_L_s_m2_10Pa:.4f}, YearFactor={year_factor:.3f}, Exp={flow_exponent}\n"
        f"  VentParams: f_ctrl={f_ctrl:.3f}, HRV_SensEff={hrv_sens_eff:.3f}, HRV_LatEff={hrv_lat_eff:.3f}\n"
        f"  FanParams: Pressure={fan_pressure_Pa if fan_pressure_Pa is not None else 'N/A'} Pa, Efficiency={fan_total_efficiency if fan_total_efficiency is not None else 'N/A'}\n"
        f"  Schedules: Infil='{final_infiltration_sched_name}', Vent='{final_ventilation_sched_name}' (Strategy: {parameter_pick_strategy})"
    )

    # --- 8) Calculate Base Infiltration Rate (@1Pa) per m2 floor area ---
    infiltration_rate_at_1Pa_L_s_per_m2_floor_area = calc_infiltration_rate_at_1Pa_per_m2(
        infiltration_base_at_10Pa_per_m2=infiltration_base_L_s_m2_10Pa,
        year_factor=year_factor,
        flow_exponent=flow_exponent
    )
    if system_type == "D" and system_d_infiltration_reduction_factor != 1.0:
        # ... (infiltration reduction logic remains the same) ...
        effective_rate_before_reduction = infiltration_rate_at_1Pa_L_s_per_m2_floor_area
        infiltration_rate_at_1Pa_L_s_per_m2_floor_area *= system_d_infiltration_reduction_factor
        print(f"  System D: Infiltration rate reduced by factor {system_d_infiltration_reduction_factor:.2f} from {effective_rate_before_reduction:.4f} to {infiltration_rate_at_1Pa_L_s_per_m2_floor_area:.4f} L/s/m2 @ 1Pa")


    # --- 9) Calculate Total Required Mechanical Ventilation Flow for the building ---
    vent_flow_m3_s_total_building = calc_required_ventilation_flow(
        building_function=bldg_func,
        f_ctrl_val=f_ctrl,
        floor_area_m2=total_bldg_floor_area_m2_input,
        usage_key=usage_key
    )

    # --- 10) Determine DSOA object name and ensure it exists for System D ---
    # ... (DSOA logic remains the same) ...
    dsoa_object_name_global = "DSOA_Global" 
    if system_type == "D":
        dsoa_obj = idf.getobject("DESIGNSPECIFICATION:OUTDOORAIR", dsoa_object_name_global.upper())
        if not dsoa_obj:
            print(f"[VENT INFO] add_ventilation.py: Building {bldg_id}: Creating default DesignSpecification:OutdoorAir: {dsoa_object_name_global}")
            try:
                dsoa_obj = idf.newidfobject("DESIGNSPECIFICATION:OUTDOORAIR", Name=dsoa_object_name_global)
                dsoa_obj.Outdoor_Air_Method = "Flow/Area" 
            except Exception as e:
                print(f"[ERROR] add_ventilation.py: Building {bldg_id}: Failed to create {dsoa_object_name_global}: {e}")
                dsoa_obj = None

        if dsoa_obj: 
            base_design_rate_L_s_m2 = 0.0
            if bldg_func == "residential":
                base_design_rate_L_s_m2 = 0.9
            else: 
                usage_flow_map_L_s_m2 = { 
                    "office_area_based": 1.0, "childcare": 4.8, "retail": 0.6,
                    "meeting_function": 1.0, "healthcare_function": 1.2, "sport_function": 1.5,
                    "cell_function": 0.8, "industrial_function": 0.5, "accommodation_function": 0.9,
                    "education_function": 1.1, "other_use_function": 0.6
                }
                base_design_rate_L_s_m2 = usage_flow_map_L_s_m2.get(usage_key, 1.0)
            
            dsoa_flow_per_area_m3_s_m2 = (base_design_rate_L_s_m2 * f_ctrl) / 1000.0
            dsoa_obj.Outdoor_Air_Flow_per_Zone_Floor_Area = dsoa_flow_per_area_m3_s_m2
            dsoa_obj.Outdoor_Air_Flow_per_Person = 0.0 
            dsoa_obj.Outdoor_Air_Flow_per_Zone = 0.0
            dsoa_obj.Outdoor_Air_Flow_Air_Changes_per_Hour = 0.0
            print(f"  System D: Set DSOA '{dsoa_obj.Name}' Outdoor_Air_Flow_per_Zone_Floor_Area to {dsoa_flow_per_area_m3_s_m2:.6f} m3/s-m2 (base {base_design_rate_L_s_m2:.2f} L/s/m2, f_ctrl {f_ctrl:.3f})")


    # --- 11) Get Zones and Prepare Zone Information Map ---
    # ... (Zone area calculation logic remains the same) ...
    zones_in_idf = idf.idfobjects.get("ZONE", [])
    if not zones_in_idf: zones_in_idf = idf.idfobjects.get("Zone", [])
    if not zones_in_idf:
        print(f"[VENT ERROR] add_ventilation.py: Building {bldg_id}: No ZONE objects found. Cannot proceed."); return

    num_zones = len(zones_in_idf)
    effective_zone_info_map: ZoneInfoMap = {}
    sum_of_individual_zone_areas = 0.0

    if zone_details: 
        valid_zone_details = True; temp_total_area = 0.0
        for zd_name, zd_props in zone_details.items():
            if not (isinstance(zd_props, dict) and 'area' in zd_props and 
                    isinstance(zd_props['area'], (float, int)) and zd_props['area'] >= 0 and 
                    'is_core' in zd_props and isinstance(zd_props['is_core'], bool)):
                valid_zone_details = False; break
            temp_total_area += zd_props['area']
        if valid_zone_details and temp_total_area > 1e-6:
            effective_zone_info_map = zone_details
            sum_of_individual_zone_areas = temp_total_area
        else: effective_zone_info_map = {}; sum_of_individual_zone_areas = 0.0 
    
    if not effective_zone_info_map or sum_of_individual_zone_areas <= 1e-6: 
        print(f"[VENT INFO] add_ventilation.py: Bldg {bldg_id}: Calculating zone areas/core status from IDF.")
        sum_of_individual_zone_areas = 0.0; effective_zone_info_map = {} 
        for zone_obj in zones_in_idf:
            # ... (detailed area calculation logic as before) ...
            zone_name_key = zone_obj.Name; area_val = 0.0; raw_field_value_str = ""
            try: area_val = getattr(zone_obj, 'floor_area', 0.0) 
            except Exception: area_val = 0.0
            if not isinstance(area_val, (float, int)) or area_val < 0: area_val = 0.0
            
            if area_val < 1e-6: 
                area_val = 0.0 
                try: 
                    raw_field_value_str = str(getattr(zone_obj, 'Floor_Area', "")).strip().lower()
                    if raw_field_value_str == "autocalculate":
                        area_val = get_zone_floor_area_from_surfaces(idf, zone_name_key)
                        if area_val < 1e-6: area_val = 0.0
                    elif raw_field_value_str: area_val = float(raw_field_value_str)
                    if area_val < 0: area_val = 0.0 
                except Exception: area_val = 0.0
            effective_zone_info_map[zone_name_key] = {'area': area_val, 'is_core': "_core" in safe_lower(zone_name_key)}
            sum_of_individual_zone_areas += area_val

    use_equal_split_fallback = False
    final_total_area_for_proportions = sum_of_individual_zone_areas

    if sum_of_individual_zone_areas <= 1e-6:
        print(f"[VENT ERROR] add_ventilation.py: Bldg {bldg_id}: Sum of individual zone areas is {sum_of_individual_zone_areas}. Fallback active.")
        if total_bldg_floor_area_m2_input > 0 and num_zones > 0:
            use_equal_split_fallback = True
            average_zone_area_for_fallback = total_bldg_floor_area_m2_input / num_zones
            # ... (fallback logic as before) ...
            temp_map_for_fallback = {}
            for zone_obj_fb in zones_in_idf:
                temp_map_for_fallback[zone_obj_fb.Name] = {'area': average_zone_area_for_fallback, 'is_core': "_core" in safe_lower(zone_obj_fb.Name)}
            effective_zone_info_map = temp_map_for_fallback
            final_total_area_for_proportions = total_bldg_floor_area_m2_input 
        else:
            print(f"[VENT CRITICAL] add_ventilation.py: Bldg {bldg_id}: Cannot distribute flows. Sum of zone areas is zero and input building area is zero or no zones. Aborting."); return


    # --- 12) Log Building-Level Parameters & Chosen Schedule Patterns ---
    if assigned_vent_log is not None:
        if bldg_id not in assigned_vent_log: assigned_vent_log[bldg_id] = {}
        log_building_params = assigned_vent.copy()
        # ... (existing log_building_params assignments) ...
        log_building_params["infiltration_rate_at_1Pa_L_s_per_m2_EFFECTIVE"] = infiltration_rate_at_1Pa_L_s_per_m2_floor_area
        log_building_params["ventilation_total_required_m3_s_building"] = vent_flow_m3_s_total_building
        log_building_params["total_bldg_floor_area_m2_input_attr"] = total_bldg_floor_area_m2_input
        log_building_params["sum_of_individual_zone_areas_derived"] = sum_of_individual_zone_areas 
        log_building_params["final_total_area_used_for_proportions"] = final_total_area_for_proportions
        log_building_params["flow_distribution_method"] = "EqualSplitFallbackLogicActive" if use_equal_split_fallback else "ProportionalToIndividualZoneArea"
        log_building_params["system_d_infiltration_reduction_factor_applied"] = system_d_infiltration_reduction_factor if system_type == "D" and system_d_infiltration_reduction_factor != 1.0 else None

        assigned_vent_log[bldg_id]["building_params"] = log_building_params

        # ---- NEW LOGGING SECTION for SCHEDULES ----
        schedule_log_details = {}
        if vent_sched_obj:
            schedule_log_details["ventilation_schedule_name"] = vent_sched_obj.Name
            if chosen_vent_wd_pattern: # Log chosen patterns only if newly created or returned by creator
                schedule_log_details["ventilation_chosen_weekday_pattern"] = chosen_vent_wd_pattern
            if chosen_vent_we_pattern:
                schedule_log_details["ventilation_chosen_weekend_pattern"] = chosen_vent_we_pattern
        if infil_sched_obj:
            schedule_log_details["infiltration_schedule_name"] = infil_sched_obj.Name
            if chosen_infil_wd_pattern:
                schedule_log_details["infiltration_chosen_weekday_pattern"] = chosen_infil_wd_pattern
            if chosen_infil_we_pattern:
                schedule_log_details["infiltration_chosen_weekend_pattern"] = chosen_infil_we_pattern
        assigned_vent_log[bldg_id]["schedule_details"] = schedule_log_details
        # --- END NEW LOGGING SECTION ---

        assigned_vent_log[bldg_id]["zones"] = {}

    print(
        f"[VENT FLOWS] add_ventilation.py: Bldg={bldg_id}: BaseInfilRate(@1Pa,Eff)={infiltration_rate_at_1Pa_L_s_per_m2_floor_area:.4f} L/s/m2, "
        f"TotalMechVentReq={vent_flow_m3_s_total_building:.4f} m3/s, "
        f"DistMethod={'EqualSplitFallbackLogicActive' if use_equal_split_fallback else 'ProportionalToIndividualZoneArea'}"
    )

    # --- 13) Loop Through Zones: Calculate Zone Flows & Create IDF Objects ---
    for zone_obj_loopvar in zones_in_idf:
        # ... (zone loop logic remains the same, using final_infiltration_sched_name and final_ventilation_sched_name) ...
        zone_name_curr = zone_obj_loopvar.Name
        zone_info_curr = effective_zone_info_map.get(zone_name_curr)
        if not zone_info_curr: 
            print(f"[VENT CRITICAL ERROR] add_ventilation.py: Zone '{zone_name_curr}' not found in effective map. Skipping."); continue 
            
        zone_floor_area_curr_m2 = zone_info_curr.get('area', 0.0) 
        is_core_zone_curr = zone_info_curr.get('is_core', False)

        infiltration_for_this_zone_m3_s = 0.0
        ventilation_for_this_zone_m3_s = 0.0

        if is_core_zone_curr:
            infiltration_for_this_zone_m3_s = 0.0
        else: 
            if zone_floor_area_curr_m2 > 1e-6:
                infiltration_L_s = infiltration_rate_at_1Pa_L_s_per_m2_floor_area * zone_floor_area_curr_m2
                infiltration_for_this_zone_m3_s = infiltration_L_s / 1000.0
        
        if final_total_area_for_proportions > 1e-6 and zone_floor_area_curr_m2 >= 0:
            proportion = zone_floor_area_curr_m2 / final_total_area_for_proportions if final_total_area_for_proportions > 0 else 0
            ventilation_for_this_zone_m3_s = vent_flow_m3_s_total_building * proportion
        elif num_zones > 0 :
             ventilation_for_this_zone_m3_s = vent_flow_m3_s_total_building / num_zones
        
        fan_param_overrides = {}
        if fan_pressure_Pa is not None: fan_param_overrides["fan_pressure_override_Pa"] = fan_pressure_Pa
        if fan_total_efficiency is not None: fan_param_overrides["fan_efficiency_override"] = fan_total_efficiency
            
        iobj, vobj = create_ventilation_system(
            idf=idf,
            building_function=bldg_func,
            system_type=system_type,
            zone_name=zone_name_curr,
            infiltration_m3_s=infiltration_for_this_zone_m3_s,
            vent_flow_m3_s=ventilation_for_this_zone_m3_s,
            zone_floor_area_m2=zone_floor_area_curr_m2,
            infiltration_sched_name=final_infiltration_sched_name, # Use the dynamically determined name
            ventilation_sched_name=final_ventilation_sched_name,   # Use the dynamically determined name
            infiltration_model=infiltration_model,
            typical_delta_t=typical_delta_t,
            typical_wind=typical_wind,
            pick_strategy=parameter_pick_strategy, # Use consistent strategy
            dsoa_object_name=dsoa_object_name_global if system_type == "D" else None,
            hrv_sensible_effectiveness=hrv_sens_eff if system_type == "D" else 0.0,
            hrv_latent_effectiveness=hrv_lat_eff if system_type == "D" else 0.0,
            **fan_param_overrides,
        )

        if assigned_vent_log is not None and bldg_id in assigned_vent_log: 
            if "zones" not in assigned_vent_log[bldg_id]:
                assigned_vent_log[bldg_id]["zones"] = {}
            assigned_vent_log[bldg_id]["zones"][zone_name_curr] = {
                "infiltration_object_name": iobj.Name if iobj else "N/A", 
                "infiltration_object_type": iobj.key if iobj else "N/A",
                "infiltration_flow_m3_s_DESIGN_TOTAL_ZONE": infiltration_for_this_zone_m3_s,
                "infiltration_flow_m3_s_m2_DESIGN_ZONE": (infiltration_for_this_zone_m3_s / zone_floor_area_curr_m2) if zone_floor_area_curr_m2 > 1e-6 else 0.0,
                "infiltration_schedule_name": final_infiltration_sched_name,
                "ventilation_object_name": vobj.Name if vobj else "N/A",
                "ventilation_object_type": vobj.key if vobj else "N/A",
                "ventilation_flow_m3_s_DESIGN_TOTAL_ZONE": ventilation_for_this_zone_m3_s if vobj else 0.0,
                "ventilation_flow_m3_s_m2_DESIGN_ZONE": (ventilation_for_this_zone_m3_s / zone_floor_area_curr_m2) if vobj and zone_floor_area_curr_m2 > 1e-6 else 0.0,
                "ventilation_schedule_name": final_ventilation_sched_name,
                "zone_floor_area_m2_used_for_dist": zone_floor_area_curr_m2, 
                "is_core_zone": is_core_zone_curr
            }
        elif assigned_vent_log is not None: 
            print(f"[VENT WARNING] add_ventilation.py: Building ID {bldg_id} not in log for zone {zone_name_curr}")

    print(f"[VENTILATION] add_ventilation.py: Completed ventilation setup for Building {bldg_id}.")