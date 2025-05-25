# ventilation/add_ventilation.py

import math # Import math for isnan check if needed
from typing import Optional, Dict, Any # Added typing

# Import specific objects/functions - ensure correct imports
try:
    from geomeppy import IDF
    # Attempt to get IDFObject types for more specific hinting if possible
    # This might require geomeppy to be fully initialized or might not be feasible at module level
    # from geomeppy.idfobjects.geometry import Zone  # Example
    # from geomeppy.idfobjects.surface import BuildingSurfaceDetailed # Example
except ImportError:
    IDF = Any 
    # Zone = Any
    # BuildingSurfaceDetailed = Any


from idf_objects.ventilation.assign_ventilation_values import (
    assign_ventilation_params_with_overrides
)
from idf_objects.ventilation.schedules import (
    create_always_on_schedule,
    create_day_night_schedule,
    create_workhours_schedule,
)
from idf_objects.ventilation.create_ventilation_systems import create_ventilation_system
from idf_objects.ventilation.calc_functions import (
    calc_infiltration_rate_at_1Pa_per_m2, 
    calc_required_ventilation_flow
)
from idf_objects.ventilation.mappings import (
    safe_lower,
    map_age_range_to_year_key,
    map_infiltration_key,
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
    # Ensure we are getting the correct collection of surfaces
    # geomeppy typically stores IDF objects in idf.idfobjects['BUILDINGSURFACE:DETAILED']
    # or idf.idfobjects.get('BUILDINGSURFACE:DETAILED', [])
    surfaces = idf.idfobjects.get("BUILDINGSURFACE:DETAILED", [])
    if not surfaces: # Fallback for older geomeppy or different structure
        surfaces = idf.idfobjects.get("BuildingSurface:Detailed", [])


    for surface in surfaces:
        try:
            # Ensure surface.Zone_Name exists and is a string before calling .upper()
            surface_zone_name = getattr(surface, 'Zone_Name', None)
            if surface_zone_name is None:
                continue # Skip if no zone name

            surface_type_attr = getattr(surface, 'Surface_Type', '').lower()
            
            if surface_zone_name.upper() == zone_name.upper() and surface_type_attr == 'floor':
                # geomeppy's surface.area property should give the calculated area
                # For IDF objects directly, it might be 'Gross_Area' or similar if not using geomeppy's calculated properties
                surface_area = getattr(surface, 'area', 0.0) # geomeppy property
                if surface_area <= 1e-6 and hasattr(surface, 'Gross_Area'): # Fallback to raw IDF field if 'area' is not helpful
                    try:
                        surface_area = float(surface.Gross_Area)
                    except (ValueError, TypeError):
                        surface_area = 0.0

                if isinstance(surface_area, (float, int)) and surface_area > 0:
                    total_floor_surface_area += surface_area
        except Exception as e:
            surface_id = getattr(surface, 'Name', 'UnknownSurface')
            print(f"[WARNING] Error accessing properties for surface '{surface_id}' in zone '{zone_name}': {e}")
            continue # Skip this surface if there's an issue
    
    if total_floor_surface_area > 1e-6: # Use a small threshold to consider it valid
        print(f"[VENT INFO] Calculated floor area for zone '{zone_name}' by summing floor surfaces: {total_floor_surface_area:.2f} m2.")
    return total_floor_surface_area


def add_ventilation_to_idf(
    idf: IDF,
    building_row: BuildingRow,
    calibration_stage: str ="pre_calibration",
    strategy: str ="A",
    random_seed: Optional[int] =None,
    user_config_vent: Optional[list] =None,
    assigned_vent_log: Optional[AssignedVentLog] =None,
    zone_details: Optional[ZoneInfoMap] =None, 
    system_d_infiltration_reduction_factor: float = 1.0,
    infiltration_model: str = "constant",
    typical_delta_t: float = 10.0,
    typical_wind: float = 3.0
):
    """
    Adds infiltration + ventilation to the IDF based on ``building_row`` data.
    
    ``infiltration_model`` selects how infiltration varies with weather:
    ``"constant"`` keeps a fixed design flow, while ``"weather"`` applies
    coefficients based on ``typical_delta_t`` and ``typical_wind``.

    Enhancements:
    - Attempts to sum floor surface areas if ZONE object area is 'autocalculate'.
    - Dynamically sets DSOA Outdoor_Air_Flow_per_Zone_Floor_Area for System D based on
      base ventilation rates and f_ctrl.
    - Passes zone_floor_area_m2 to create_ventilation_system for "Flow/Area" calculations.
    """

    # --- 1) Ensure key schedules exist ---
    create_always_on_schedule(idf, "AlwaysOnSched")
    create_day_night_schedule(idf, "VentSched_DayNight")
    create_workhours_schedule(idf, "WorkHoursSched")

    # --- 2) Extract building info ---
    bldg_id = building_row.get("ogc_fid", "UnknownBuildingID") 
    bldg_func = safe_lower(building_row.get("building_function", "residential"))
    if bldg_func not in ("residential", "non_residential"):
        bldg_func = "residential" 

    age_range_str = building_row.get("age_range", "2015 and later") 
    scenario = building_row.get("scenario", "scenario1") 
    total_bldg_floor_area_m2_input = building_row.get("area", 100.0) 
    
    if not isinstance(total_bldg_floor_area_m2_input, (int,float)) or total_bldg_floor_area_m2_input <= 0:
        print(f"[VENT WARNING] Building {bldg_id}: Invalid total building floor area attribute ('area': {total_bldg_floor_area_m2_input}). Defaulting to 100.0 m2.")
        total_bldg_floor_area_m2_input = 100.0

    # --- 3) Decide lookup keys ---
    infiltration_key = map_infiltration_key(building_row) 
    usage_key = map_usage_key(building_row) 
    year_key = map_age_range_to_year_key(age_range_str) 
    is_res = (bldg_func == "residential")

    # --- 4) Assign building-level ventilation parameters ---
    assigned_vent = assign_ventilation_params_with_overrides(
        building_id=bldg_id, building_function=bldg_func, age_range=age_range_str,
        scenario=scenario, calibration_stage=calibration_stage, strategy=strategy,
        random_seed=random_seed, user_config_vent=user_config_vent,
        infiltration_key=infiltration_key, year_key=year_key, is_residential=is_res,
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
    infiltration_sched_name = assigned_vent["infiltration_schedule_name"]
    ventilation_sched_name = assigned_vent["ventilation_schedule_name"]
    system_type = assigned_vent["system_type"] 
    flow_exponent = assigned_vent["flow_exponent"]

    # --- 6) Debug Print ---
    print(
        f"[VENT PARAMS] Bldg={bldg_id}, Func={bldg_func}, AgeKey='{year_key}', Sys={system_type}\n"
        f"  LookupKeys: Infil='{infiltration_key}', Usage='{usage_key if usage_key else 'N/A'}'\n"
        f"  InfilParams: Base(L/s/m2@10Pa)={infiltration_base_L_s_m2_10Pa:.4f}, YearFactor={year_factor:.3f}, Exp={flow_exponent}\n"
        f"  VentParams: f_ctrl={f_ctrl:.3f}, HRV_SensEff={hrv_sens_eff:.3f}, HRV_LatEff={hrv_lat_eff:.3f}\n"
        f"  FanParams: Pressure={fan_pressure_Pa if fan_pressure_Pa is not None else 'N/A'} Pa, Efficiency={fan_total_efficiency if fan_total_efficiency is not None else 'N/A'}\n"
        f"  Schedules: Infil='{infiltration_sched_name}', Vent='{ventilation_sched_name}'"
    )

    # --- 7) Calculate Base Infiltration Rate (@1Pa) per m2 floor area ---
    infiltration_rate_at_1Pa_L_s_per_m2_floor_area = calc_infiltration_rate_at_1Pa_per_m2(
        infiltration_base_at_10Pa_per_m2=infiltration_base_L_s_m2_10Pa,
        year_factor=year_factor,
        flow_exponent=flow_exponent
    )

    if system_type == "D" and system_d_infiltration_reduction_factor != 1.0:
        effective_rate_before_reduction = infiltration_rate_at_1Pa_L_s_per_m2_floor_area
        infiltration_rate_at_1Pa_L_s_per_m2_floor_area *= system_d_infiltration_reduction_factor
        print(f"  System D: Infiltration rate reduced by factor {system_d_infiltration_reduction_factor:.2f} from {effective_rate_before_reduction:.4f} to {infiltration_rate_at_1Pa_L_s_per_m2_floor_area:.4f} L/s/m2 @ 1Pa")

    # --- 8) Calculate Total Required Mechanical Ventilation Flow for the building ---
    vent_flow_m3_s_total_building = calc_required_ventilation_flow(
        building_function=bldg_func,
        f_ctrl_val=f_ctrl, # Note: f_ctrl is applied *here* to the total building flow
        floor_area_m2=total_bldg_floor_area_m2_input, 
        usage_key=usage_key
    )

    # --- 9) Determine DSOA object name and ensure it exists for System D ---
    dsoa_object_name_global = "DSOA_Global" 
    if system_type == "D":
        dsoa_obj = idf.getobject("DESIGNSPECIFICATION:OUTDOORAIR", dsoa_object_name_global.upper())
        if not dsoa_obj:
            print(f"[VENT INFO] Building {bldg_id}: Creating default DesignSpecification:OutdoorAir: {dsoa_object_name_global}")
            try:
                dsoa_obj = idf.newidfobject("DESIGNSPECIFICATION:OUTDOORAIR")
                dsoa_obj.Name = dsoa_object_name_global
                # For "Flow/Area" method, this is the primary method.
                dsoa_obj.Outdoor_Air_Method = "Flow/Area" # << CHANGED to Flow/Area for explicitness
            except Exception as e:
                print(f"[ERROR] Building {bldg_id}: Failed to create {dsoa_object_name_global}: {e}")
                dsoa_obj = None # Ensure dsoa_obj is None if creation fails

        if dsoa_obj: # Proceed only if DSOA object exists or was successfully created
            # Dynamically set DSOA Outdoor_Air_Flow_per_Zone_Floor_Area
            base_design_rate_L_s_m2 = 0.0
            if bldg_func == "residential":
                base_design_rate_L_s_m2 = 0.9 # Default L/s/m2 for residential
            else: # Non-residential
                usage_flow_map_L_s_m2 = { # Should match the map in calc_required_ventilation_flow
                    "office_area_based": 1.0, "childcare": 4.8, "retail": 0.6,
                    "meeting_function": 1.0, "healthcare_function": 1.2, "sport_function": 1.5,
                    "cell_function": 0.8, "industrial_function": 0.5, "accommodation_function": 0.9,
                    "education_function": 1.1, "other_use_function": 0.6
                }
                base_design_rate_L_s_m2 = usage_flow_map_L_s_m2.get(usage_key, 1.0) # Default if key unknown
            
            # Apply f_ctrl to this base per-m2 rate for DSOA
            # Convert L/s/m2 to m3/s/m2 for DSOA field
            dsoa_flow_per_area_m3_s_m2 = (base_design_rate_L_s_m2 * f_ctrl) / 1000.0
            
            # The field name in geomeppy is Outdoor_Air_Flow_per_Zone_Floor_Area.
            # EnergyPlus IDD for "Flow/Area" method expects "Outdoor Air Flow per Floor Area".
            # Assuming geomeppy maps this correctly or the field name is suitable.
            dsoa_obj.Outdoor_Air_Flow_per_Zone_Floor_Area = dsoa_flow_per_area_m3_s_m2
            # Set other DSOA rate fields to 0 as "Flow/Area" is the sole driver
            dsoa_obj.Outdoor_Air_Flow_per_Person = 0.0 
            dsoa_obj.Outdoor_Air_Flow_per_Zone = 0.0
            dsoa_obj.Outdoor_Air_Flow_Air_Changes_per_Hour = 0.0
            print(f"  System D: Set DSOA '{dsoa_obj.Name}' Outdoor_Air_Flow_per_Zone_Floor_Area to {dsoa_flow_per_area_m3_s_m2:.6f} m3/s-m2 (derived from base rate {base_design_rate_L_s_m2:.2f} L/s/m2 and f_ctrl {f_ctrl:.3f})")

            # Optional: Assign a fraction schedule to DSOA if OA flow should vary by time
            # dsoa_obj.Outdoor_Air_Flow_Rate_Fraction_Schedule_Name = "Name_Of_OA_Fraction_Schedule"


    # --- 10) Get Zones and Prepare Zone Information Map ---
    # Ensure we get the correct collection name for ZONE objects
    zones_in_idf = idf.idfobjects.get("ZONE", [])
    if not zones_in_idf: # Fallback for older geomeppy or different structure
        zones_in_idf = idf.idfobjects.get("Zone", [])

    if not zones_in_idf:
        print(f"[VENT ERROR] Building {bldg_id}: No ZONE objects found. Cannot proceed."); return

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
        if valid_zone_details and temp_total_area > 1e-6: # Use a small threshold
            effective_zone_info_map = zone_details
            sum_of_individual_zone_areas = temp_total_area
        else: effective_zone_info_map = {}; sum_of_individual_zone_areas = 0.0 
    
    if not effective_zone_info_map or sum_of_individual_zone_areas <= 1e-6: 
        print(f"[VENT INFO] Bldg {bldg_id}: Calculating zone areas/core status from IDF (zone_details not provided, invalid, or zero area).")
        sum_of_individual_zone_areas = 0.0; effective_zone_info_map = {} 
        for zone_obj in zones_in_idf:
            zone_name_key = zone_obj.Name; area_val = 0.0; raw_field_value_str = ""
            try: # Try geomeppy's .floor_area property
                area_val = getattr(zone_obj, 'floor_area', 0.0) # Use getattr for safety
                if not isinstance(area_val, (float, int)) or area_val < 0: area_val = 0.0
            except Exception: area_val = 0.0
            
            if area_val < 1e-6: # If .floor_area didn't yield a positive area, try raw IDF field or summing surfaces
                area_val = 0.0 # Reset before trying next methods
                try: 
                    raw_field_value_str = str(getattr(zone_obj, 'Floor_Area', "")).strip().lower()
                    if raw_field_value_str == "autocalculate":
                        print(f"[VENT INFO] Bldg {bldg_id}: Zone '{zone_name_key}' Floor_Area is 'autocalculate'. Attempting to sum floor surfaces.")
                        area_val = get_zone_floor_area_from_surfaces(idf, zone_name_key)
                        if area_val < 1e-6:
                             print(f"[VENT WARNING] Bldg {bldg_id}: Zone '{zone_name_key}' - summing floor surfaces yielded {area_val:.4f} m2. Using 0 for this zone's area calculation.")
                             area_val = 0.0
                    elif raw_field_value_str: # If not autocalculate, try to convert
                        area_val = float(raw_field_value_str)
                        if area_val < 0: area_val = 0.0 
                except ValueError: 
                    print(f"[VENT WARNING] Bldg {bldg_id}: Zone '{zone_name_key}' Floor_Area field ('{raw_field_value_str}') is not 'autocalculate' and not a valid number. Using 0.")
                    area_val = 0.0
                except Exception as e_conv: 
                    print(f"[VENT WARNING] Bldg {bldg_id}: Error processing Floor_Area for zone '{zone_name_key}' (raw: '{raw_field_value_str}'): {e_conv}. Using 0.")
                    area_val = 0.0
            
            if area_val <= 1e-6 : # If still zero after all attempts
                 print(f"[VENT WARNING] Bldg {bldg_id}: Zone '{zone_name_key}' final determined area is {area_val:.4f} m2. This might cause issues if it's the only zone or all zones have zero area.")
            
            effective_zone_info_map[zone_name_key] = {'area': area_val, 'is_core': "_core" in safe_lower(zone_name_key)}
            sum_of_individual_zone_areas += area_val

    use_equal_split_fallback = False
    final_total_area_for_proportions = sum_of_individual_zone_areas

    if sum_of_individual_zone_areas <= 1e-6: # Use a small threshold
        print(f"[VENT ERROR] Bldg {bldg_id}: Sum of individual zone areas is {sum_of_individual_zone_areas}. Fallback active.")
        if total_bldg_floor_area_m2_input > 0 and num_zones > 0:
            use_equal_split_fallback = True
            average_zone_area_for_fallback = total_bldg_floor_area_m2_input / num_zones
            print(f"  Using total building area attribute {total_bldg_floor_area_m2_input}m2; average zone area for fallback: {average_zone_area_for_fallback:.2f}m2.")
            temp_map_for_fallback = {}
            for zone_obj_fb in zones_in_idf:
                temp_map_for_fallback[zone_obj_fb.Name] = {
                    'area': average_zone_area_for_fallback, 
                    'is_core': "_core" in safe_lower(zone_obj_fb.Name)
                }
            effective_zone_info_map = temp_map_for_fallback
            final_total_area_for_proportions = total_bldg_floor_area_m2_input 
        else:
            print(f"[VENT CRITICAL] Bldg {bldg_id}: Cannot distribute flows. Sum of zone areas is zero and input building area is zero or no zones. Aborting."); return

    # --- 11) Log Building-Level Parameters ---
    if assigned_vent_log is not None:
        if bldg_id not in assigned_vent_log: assigned_vent_log[bldg_id] = {}
        log_building_params = assigned_vent.copy()
        log_building_params["infiltration_rate_at_1Pa_L_s_per_m2_EFFECTIVE"] = infiltration_rate_at_1Pa_L_s_per_m2_floor_area
        log_building_params["ventilation_total_required_m3_s_building"] = vent_flow_m3_s_total_building
        log_building_params["total_bldg_floor_area_m2_input_attr"] = total_bldg_floor_area_m2_input
        log_building_params["sum_of_individual_zone_areas_derived"] = sum_of_individual_zone_areas 
        log_building_params["final_total_area_used_for_proportions"] = final_total_area_for_proportions
        log_building_params["flow_distribution_method"] = "EqualSplitFallbackLogicActive" if use_equal_split_fallback else "ProportionalToIndividualZoneArea"
        log_building_params["system_d_infiltration_reduction_factor_applied"] = system_d_infiltration_reduction_factor if system_type == "D" and system_d_infiltration_reduction_factor != 1.0 else None
        assigned_vent_log[bldg_id]["building_params"] = log_building_params
        assigned_vent_log[bldg_id]["zones"] = {} 

    print(
        f"[VENT FLOWS] Bldg={bldg_id}: BaseInfilRate(@1Pa,Effective)={infiltration_rate_at_1Pa_L_s_per_m2_floor_area:.4f} L/s/m2, "
        f"TotalMechVentReq={vent_flow_m3_s_total_building:.4f} m3/s, "
        f"DistMethod={'EqualSplitFallbackLogicActive' if use_equal_split_fallback else 'ProportionalToIndividualZoneArea'}"
    )
    
    # --- 12) Loop Through Zones: Calculate Zone Flows & Create IDF Objects ---
    for zone_obj_loopvar in zones_in_idf:
        zone_name_curr = zone_obj_loopvar.Name
        zone_info_curr = effective_zone_info_map.get(zone_name_curr)
        if not zone_info_curr: 
            print(f"[VENT CRITICAL ERROR] Zone '{zone_name_curr}' not found in effective map. Skipping."); continue 
            
        zone_floor_area_curr_m2 = zone_info_curr.get('area', 0.0) 
        is_core_zone_curr = zone_info_curr.get('is_core', False)

        infiltration_for_this_zone_m3_s = 0.0
        ventilation_for_this_zone_m3_s = 0.0

        if is_core_zone_curr:
            infiltration_for_this_zone_m3_s = 0.0 # Core zones typically have no direct envelope infiltration
        else: 
            if zone_floor_area_curr_m2 > 1e-6: # Only calculate if area is positive
                infiltration_L_s = infiltration_rate_at_1Pa_L_s_per_m2_floor_area * zone_floor_area_curr_m2
                infiltration_for_this_zone_m3_s = infiltration_L_s / 1000.0
        
        # Distribute total building mechanical ventilation proportionally to zone areas
        if final_total_area_for_proportions > 1e-6 and zone_floor_area_curr_m2 >= 0: # Allow zero area zones to get zero flow if proportional
            proportion = zone_floor_area_curr_m2 / final_total_area_for_proportions if final_total_area_for_proportions > 0 else 0
            ventilation_for_this_zone_m3_s = vent_flow_m3_s_total_building * proportion
        elif num_zones > 0 : # Fallback if total area for proportions is zero (e.g. all zones had zero area initially)
             ventilation_for_this_zone_m3_s = vent_flow_m3_s_total_building / num_zones
        
        fan_param_overrides = {}
        if fan_pressure_Pa is not None: fan_param_overrides["fan_pressure_override_Pa"] = fan_pressure_Pa
        if fan_total_efficiency is not None: fan_param_overrides["fan_efficiency_override"] = fan_total_efficiency
            
        iobj, vobj = create_ventilation_system(
            idf=idf,
            building_function=bldg_func,
            system_type=system_type,
            zone_name=zone_name_curr,
            infiltration_m3_s=infiltration_for_this_zone_m3_s, # This is TOTAL m3/s for the zone
            vent_flow_m3_s=ventilation_for_this_zone_m3_s,     # This is TOTAL m3/s for the zone
            zone_floor_area_m2=zone_floor_area_curr_m2,       # << PASSING ZONE AREA
            infiltration_sched_name=infiltration_sched_name,
            ventilation_sched_name=ventilation_sched_name,
            infiltration_model=infiltration_model,
            typical_delta_t=typical_delta_t,
            typical_wind=typical_wind,
            pick_strategy="random" if strategy == "B" else "midpoint",
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
                "infiltration_flow_m3_s_DESIGN_TOTAL_ZONE": infiltration_for_this_zone_m3_s, # Log the total zone flow
                "infiltration_flow_m3_s_m2_DESIGN_ZONE": (infiltration_for_this_zone_m3_s / zone_floor_area_curr_m2) if zone_floor_area_curr_m2 > 1e-6 else 0.0,
                "infiltration_schedule_name": infiltration_sched_name,
                "ventilation_object_name": vobj.Name if vobj else "N/A",
                "ventilation_object_type": vobj.key if vobj else "N/A",
                "ventilation_flow_m3_s_DESIGN_TOTAL_ZONE": ventilation_for_this_zone_m3_s if vobj else 0.0, # Log the total zone flow
                "ventilation_flow_m3_s_m2_DESIGN_ZONE": (ventilation_for_this_zone_m3_s / zone_floor_area_curr_m2) if vobj and zone_floor_area_curr_m2 > 1e-6 else 0.0,
                "ventilation_schedule_name": ventilation_sched_name,
                "zone_floor_area_m2_used_for_dist": zone_floor_area_curr_m2, 
                "is_core_zone": is_core_zone_curr
            }
        elif assigned_vent_log is not None: 
            print(f"[VENT WARNING] Building ID {bldg_id} not in log for zone {zone_name_curr}")

    print(f"[VENTILATION] Completed ventilation setup for Building {bldg_id}.")
