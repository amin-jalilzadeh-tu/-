# ventilation/create_ventilation_systems.py

import random
import math  # For isnan checks if needed
from typing import Optional, Any, Tuple

# Import IDF class for type hinting (assuming geomeppy is used)
try:
    from geomeppy import IDF
except ImportError:
    IDF = Any # Fallback if geomeppy not available

# Assuming SYSTEMS_CONFIG is defined in this module or imported correctly
try:
    from .config_systems import SYSTEMS_CONFIG
except ImportError:
    # Handle case where config might be structured differently
    print("[ERROR] Could not import SYSTEMS_CONFIG from .config_systems. Ensure it's defined.")
    SYSTEMS_CONFIG = {} # Provide an empty dict to avoid crashes later, but setup will likely fail


# ---------------------------------------------------------------------------
# Helper: Apply weather-dependent infiltration coefficients
# ---------------------------------------------------------------------------
def apply_weather_coefficients(
    infil_obj: Any,
    base_flow_per_area_m3_s_m2: float, # Renamed for clarity: this is now m3/s per m2
    typical_delta_t: float = 10.0,
    typical_wind: float = 3.0,
):
    """
    FIX for VENT_007: Configure infiltration coefficients correctly.
    The Design_Flow_Rate should be the actual flow rate at design conditions,
    NOT a coefficient 'k' value.
    
    The coefficients should multiply the Design_Flow_Rate to give actual flow.
    At typical conditions (typical_delta_t, typical_wind), the total multiplier
    should be approximately 1.0.
    """
    
    # FIX for VENT_007: These coefficients should be normalized
    # so that at typical conditions, the total multiplier ≈ 1.0
    # Use pure weather dependence (A=0) for more realistic behavior
    A = 0.0   # No constant term - pure weather dependence
    B = 0.03  # Temperature term coefficient (per degC)
    C = 0.04  # Velocity term coefficient (per m/s)
    D = 0.0   # Velocity squared term coefficient (per (m/s)^2)
    
    # The Design_Flow_Rate should be the base rate at typical conditions
    infil_obj.Design_Flow_Rate = base_flow_per_area_m3_s_m2
    
    # Calculate what the total multiplier would be at typical conditions
    total_at_typical = A + B * typical_delta_t + C * typical_wind + D * (typical_wind ** 2)
    
    # Normalize coefficients so that at typical conditions, multiplier = 1.0
    if total_at_typical > 1e-6:  # Avoid division by zero
        infil_obj.Constant_Term_Coefficient = A / total_at_typical
        infil_obj.Temperature_Term_Coefficient = B / total_at_typical
        infil_obj.Velocity_Term_Coefficient = C / total_at_typical
        infil_obj.Velocity_Squared_Term_Coefficient = D / total_at_typical
        
        print(f"[VENT_007 FIX] Weather coefficients normalized: A={A/total_at_typical:.3f}, "
              f"B={B/total_at_typical:.3f}, C={C/total_at_typical:.3f}, D={D/total_at_typical:.3f}")
    else:
        # Fallback to constant if normalization fails
        print(f"[WARNING] Weather coefficient normalization failed (total={total_at_typical}). Using constant infiltration.")
        infil_obj.Constant_Term_Coefficient = 1.0
        infil_obj.Temperature_Term_Coefficient = 0.0
        infil_obj.Velocity_Term_Coefficient = 0.0
        infil_obj.Velocity_Squared_Term_Coefficient = 0.0


def create_ventilation_system(
    idf: IDF,
    building_function: str,     # 'residential' or 'non_residential'
    system_type: str,           # 'A', 'B', 'C', or 'D'
    zone_name: str,
    # --- Zone-specific flows ---
    infiltration_m3_s: float,     # TOTAL Calculated infiltration for THIS zone (m3/s)
    vent_flow_m3_s: float,        # TOTAL Calculated required ventilation for THIS zone (m3/s)
    zone_floor_area_m2: float,  # << NEW PARAMETER: Floor area of the current zone (m2)
    # --- Schedule names ---
    infiltration_sched_name: str = "AlwaysOnSched",
    ventilation_sched_name: str = "VentSched_DayNight", # Used for ZoneVentilation and IdealLoads Availability
    # --- Infiltration modelling ---
    infiltration_model: str = "constant",  # "constant" or "weather"
    typical_delta_t: float = 10.0,
    typical_wind: float = 3.0,
    # --- Strategy for picking from ranges (e.g., fan eff from SYSTEMS_CONFIG) ---
    pick_strategy: str = "midpoint",  # or "random"
    # --- Parameters specifically for System D (IdealLoads) ---
    dsoa_object_name: Optional[str] = None,  # Name of the DesignSpecification:OutdoorAir object
    hrv_sensible_effectiveness: float = 0.0,
    hrv_latent_effectiveness: float = 0.0,
    # --- Overrides for fan parameters (for Systems A, B, C primarily) ---
    fan_pressure_override_Pa: Optional[float] = None,
    fan_efficiency_override: Optional[float] = None,
) -> Tuple[Optional[Any], Optional[Any]]:  # Return type hint Any or specific eppy/geomeppy type
    """
    Creates EnergyPlus objects for infiltration and ventilation for a specific zone.

    Key Updates for "Flow Area":
    - Added `zone_floor_area_m2` parameter.
    - For ZONEINFILTRATION:DESIGNFLOWRATE and ZONEVENTILATION:DESIGNFLOWRATE:
        - Design_Flow_Rate_Calculation_Method is set to "Flow/Area".
        - Design_Flow_Rate is set to the flow rate per m2 of zone floor area (m3/s/m2).
    - `apply_weather_coefficients` now works with per-area flow rates.
    - IdealLoadsAirSystem (System D) continues to use DesignSpecification:OutdoorAir,
      which itself is configured with per-area rates in add_ventilation.py.
    """

    # --- 1) Get System Configuration from SYSTEMS_CONFIG ---
    config = None
    try:
        func_config = SYSTEMS_CONFIG.get(building_function)
        if not func_config:
            print(f"[WARNING] Building function '{building_function}' not found in SYSTEMS_CONFIG. Defaulting to 'residential'.")
            func_config = SYSTEMS_CONFIG.get("residential", {})

        config = func_config.get(system_type)
        if not config:
            print(f"[WARNING] System type '{system_type}' not found for '{building_function}'. Defaulting to 'A' for {building_function}.")
            config = func_config.get("A", {}) # Default to system A config for the given function
            if not config and building_function == "non_residential": # Further fallback if 'A' also not in func_config
                 config = SYSTEMS_CONFIG.get("residential", {}).get("A",{})
    except Exception as e:
        print(f"[ERROR] Failed to get system config for {building_function}/{system_type}: {e}")
        return None, None # Cannot proceed without config

    if not config: # Check if config retrieval failed completely
        print(f"[ERROR] System config for {building_function}/{system_type} is empty or invalid after fallbacks.")
        return None, None

    # --- 2) Helper to Pick Value from Range (from SYSTEMS_CONFIG if no override) ---
    def pick_val(rng_tuple):
        """Picks value from (min, max) tuple based on pick_strategy."""
        if not isinstance(rng_tuple, (list, tuple)) or len(rng_tuple) != 2:
            # print(f"[DEBUG] Invalid range tuple: {rng_tuple}. Returning 0.0.")
            return 0.0
        min_v, max_v = rng_tuple
        try:
            min_v = float(min_v)
            max_v = float(max_v)
            if math.isnan(min_v) or math.isnan(max_v): raise ValueError("NaN in range")
            if min_v > max_v: min_v = max_v # Ensure min <= max
        except (ValueError, TypeError):
            # print(f"[DEBUG] Invalid numeric values in range {rng_tuple}. Using 0.0.")
            return 0.0

        if pick_strategy == "random":
            return random.uniform(min_v, max_v)
        else: # Default to midpoint
            return (min_v + max_v) / 2.0

    # --- 3) Create Infiltration Object (Always created, flow can be zero) ---
    iobj = None
    try:
        iobj = idf.newidfobject("ZONEINFILTRATION:DESIGNFLOWRATE")
        base_name = f"Infil_{building_function[:4]}_{system_type}_{zone_name}"
        clean_base_name = "".join(c if c.isalnum() or c in ['-', '_', '.'] else '_' for c in base_name)[:100] # Max 100 chars
        iobj.Name = clean_base_name

        zone_field_assigned = False
        for field_name in ["Zone_or_ZoneList_Name", "Zone_Name", "Zone_or_ZoneList_or_Space_or_SpaceList_Name"]:
            if hasattr(iobj, field_name):
                setattr(iobj, field_name, zone_name)
                zone_field_assigned = True
                break
        if not zone_field_assigned:
            raise ValueError(f"Could not find or set Zone Name field for ZONEINFILTRATION:DESIGNFLOWRATE object '{iobj.Name}'.")

        iobj.Schedule_Name = infiltration_sched_name
        iobj.Design_Flow_Rate_Calculation_Method = "Flow/Area" # << CHANGED to Flow/Area

        # Calculate infiltration flow per unit area
        infiltration_flow_per_area_m3_s_m2 = 0.0
        if zone_floor_area_m2 > 1e-6: # Avoid division by zero for very small or zero area zones
            infiltration_flow_per_area_m3_s_m2 = infiltration_m3_s / zone_floor_area_m2
        elif infiltration_m3_s > 1e-9: # If there's flow but no area, it's an issue
             print(f"[WARNING] Zone '{zone_name}' has infiltration flow {infiltration_m3_s} m3/s but area is {zone_floor_area_m2} m2. Cannot calculate Flow/Area. Setting infiltration per area to 0.")


        if infiltration_model.lower() == "weather":
            # FIX for VENT_007: apply_weather_coefficients now works correctly
            apply_weather_coefficients(
                iobj,
                max(0.0, infiltration_flow_per_area_m3_s_m2), # Pass per-area rate
                typical_delta_t=typical_delta_t,
                typical_wind=typical_wind,
            )
        else: # "constant" model
            iobj.Design_Flow_Rate = max(0.0, infiltration_flow_per_area_m3_s_m2) # Set per-area rate
            iobj.Constant_Term_Coefficient = 1.0
            iobj.Temperature_Term_Coefficient = 0.0
            iobj.Velocity_Term_Coefficient = 0.0
            iobj.Velocity_Squared_Term_Coefficient = 0.0
            # For "constant" with "Flow/Area", the Design_Flow_Rate is simply the m3/s/m2 value.
            # The coefficients effectively make it Q = Design_Flow_Rate * 1.0

    except Exception as e:
        print(f"[ERROR] Failed to create ZONEINFILTRATION:DESIGNFLOWRATE for {zone_name}: {e}")
        # If iobj was partially created, it might be good to remove it, but geomeppy handles this.
        return None, None # Return None, None if infiltration object creation fails

    # --- 4) Prepare Chosen Parameter Values from Config (for fallback if no overrides) ---
    chosen_params_from_config = {} # Parameters like fan pressure/eff from SYSTEMS_CONFIG
    range_dict_from_config = config.get("range_params", {})
    for param_name, rng in range_dict_from_config.items():
        chosen_val = pick_val(rng)
        chosen_params_from_config[param_name] = chosen_val

    fixed_params_from_config = config.get("fixed_params", {})
    ventilation_type_options = config.get("ventilation_type_options", ["Natural"]) # Default to Natural
    chosen_vent_type_from_config = random.choice(ventilation_type_options) if pick_strategy == "random" and ventilation_type_options else ventilation_type_options[0]

    # --- 5) Create/Configure Ventilation System Object ---
    vent_obj_or_ideal_obj = None # Initialize

    if config.get("use_ideal_loads", False): # Typically System D
        # --- System D: Configure Existing IdealLoadsAirSystem ---
        # IdealLoadsAirSystem uses DesignSpecification:OutdoorAir, which is already set up
        # with per-area rates in add_ventilation.py. No direct "Flow/Area" change needed here for OA.
        possible_ideal_names = [
            f"{zone_name} Ideal Loads",
            f"{zone_name}_Ideal_Loads",
            f"IdealLoads_{zone_name}"
        ]
        ideal_obj_found = None
        for name_attempt in possible_ideal_names:
            ideal_obj_found = idf.getobject("ZONEHVAC:IDEALLOADSAIRSYSTEM", name_attempt.upper()) # Case-insensitive check
            if ideal_obj_found:
                break
        
        if not ideal_obj_found:
            print(f"[VENT WARNING] ZONEHVAC:IDEALLOADSAIRSYSTEM not found using patterns for System D in zone {zone_name}. Tried: {possible_ideal_names}. Cannot configure OA or HRV.")
            return iobj, None # Return infiltration obj, but None for vent/ideal obj
        else:
            vent_obj_or_ideal_obj = ideal_obj_found

            if hasattr(vent_obj_or_ideal_obj, "Availability_Schedule_Name"):
                vent_obj_or_ideal_obj.Availability_Schedule_Name = ventilation_sched_name
            else:
                print(f"[VENT WARNING] IdealLoads object {vent_obj_or_ideal_obj.Name} lacks 'Availability_Schedule_Name' field.")

            if dsoa_object_name:
                if hasattr(vent_obj_or_ideal_obj, "Design_Specification_Outdoor_Air_Object_Name"):
                    if idf.getobject("DESIGNSPECIFICATION:OUTDOORAIR", dsoa_object_name.upper()):
                        vent_obj_or_ideal_obj.Design_Specification_Outdoor_Air_Object_Name = dsoa_object_name
                    else:
                        print(f"[VENT WARNING] Specified DSOA object '{dsoa_object_name}' not found in IDF for IdealLoads '{vent_obj_or_ideal_obj.Name}'. Outdoor Air not linked via DSOA.")
                else:
                    print(f"[VENT WARNING] IdealLoads object {vent_obj_or_ideal_obj.Name} lacks 'Design_Specification_Outdoor_Air_Object_Name' field.")
            else:
                print(f"[VENT WARNING] DSOA object name not provided for System D configuration of IdealLoads '{vent_obj_or_ideal_obj.Name}'. Outdoor Air will not be enabled via DSOA method.")
                if hasattr(vent_obj_or_ideal_obj, "Design_Specification_Outdoor_Air_Object_Name"):
                    vent_obj_or_ideal_obj.Design_Specification_Outdoor_Air_Object_Name = ""

            for param_field, fixed_val in fixed_params_from_config.items():
                if param_field == "Design_Specification_Outdoor_Air_Object_Name": continue
                if hasattr(vent_obj_or_ideal_obj, param_field):
                    try:
                        setattr(vent_obj_or_ideal_obj, param_field, fixed_val)
                    except Exception as set_err:
                        print(f"[VENT WARNING] Failed to set IdealLoads {param_field} = {fixed_val} for {vent_obj_or_ideal_obj.Name}: {set_err}")

            sens_eff = max(0.0, hrv_sensible_effectiveness)
            lat_eff = max(0.0, hrv_latent_effectiveness)
            hr_type = "None"
            if sens_eff > 0.001 and lat_eff > 0.001:
                hr_type = "Enthalpy"
            elif sens_eff > 0.001:
                hr_type = "Sensible"
            elif lat_eff > 0.001:
                hr_type = "Enthalpy" # Or "Latent" if E+ version supports

            try:
                if hasattr(vent_obj_or_ideal_obj, "Heat_Recovery_Type"):
                    vent_obj_or_ideal_obj.Heat_Recovery_Type = hr_type
                if hasattr(vent_obj_or_ideal_obj, "Sensible_Heat_Recovery_Effectiveness"):
                    vent_obj_or_ideal_obj.Sensible_Heat_Recovery_Effectiveness = sens_eff if hr_type != "None" else 0.0
                if hasattr(vent_obj_or_ideal_obj, "Latent_Heat_Recovery_Effectiveness"):
                    vent_obj_or_ideal_obj.Latent_Heat_Recovery_Effectiveness = lat_eff if hr_type != "None" else 0.0
            except Exception as hr_err:
                print(f"[VENT WARNING] Failed to set Heat Recovery fields for {vent_obj_or_ideal_obj.Name}: {hr_err}")

    else: # Systems A, B, C: Create ZONEVENTILATION:DESIGNFLOWRATE
        try:
            vent_obj_type_from_config = config.get("ventilation_object_type", "ZONEVENTILATION:DESIGNFLOWRATE")
            vobj = idf.newidfobject(vent_obj_type_from_config)
            vent_obj_or_ideal_obj = vobj

            base_name = f"Vent_{building_function[:4]}_{system_type}_{zone_name}"
            clean_base_name = "".join(c if c.isalnum() or c in ['-', '_', '.'] else '_' for c in base_name)[:100]
            vobj.Name = clean_base_name

            zone_field_assigned = False
            for field_name in ["Zone_or_ZoneList_Name", "Zone_Name", "Zone_or_ZoneList_or_Space_or_SpaceList_Name"]:
                if hasattr(vobj, field_name):
                    setattr(vobj, field_name, zone_name)
                    zone_field_assigned = True
                    break
            if not zone_field_assigned:
                raise ValueError(f"Could not find or set Zone Name field for {vent_obj_type_from_config} object '{vobj.Name}'.")

            vobj.Schedule_Name = ventilation_sched_name
            vobj.Design_Flow_Rate_Calculation_Method = "Flow/Area" # << CHANGED to Flow/Area

            # Calculate ventilation flow per unit area
            ventilation_flow_per_area_m3_s_m2 = 0.0
            if zone_floor_area_m2 > 1e-6: # Avoid division by zero
                ventilation_flow_per_area_m3_s_m2 = vent_flow_m3_s / zone_floor_area_m2
            elif vent_flow_m3_s > 1e-9: # If there's flow but no area, it's an issue
                print(f"[WARNING] Zone '{zone_name}' has ventilation flow {vent_flow_m3_s} m3/s but area is {zone_floor_area_m2} m2. Cannot calculate Flow/Area. Setting ventilation per area to 0.")

            vobj.Design_Flow_Rate = max(0.0, ventilation_flow_per_area_m3_s_m2) # Set per-area rate

            if hasattr(vobj, "Ventilation_Type"):
                vobj.Ventilation_Type = chosen_vent_type_from_config

            # FIX for VENT_013: Natural ventilation should vary with conditions
            if chosen_vent_type_from_config == "Natural":
                # Natural ventilation should respond to temperature and wind
                vobj.Constant_Term_Coefficient = 0.0
                vobj.Temperature_Term_Coefficient = 0.05  # Opens more with temp difference
                vobj.Velocity_Term_Coefficient = 0.10    # Wind-driven ventilation
                vobj.Velocity_Squared_Term_Coefficient = 0.02
                print(f"[VENT_013 FIX] Natural ventilation configured with weather-dependent coefficients for zone {zone_name}")
            else:
                # Mechanical ventilation is constant (not affected by weather)
                vobj.Constant_Term_Coefficient = 1.0
                vobj.Temperature_Term_Coefficient = 0.0
                vobj.Velocity_Term_Coefficient = 0.0
                vobj.Velocity_Squared_Term_Coefficient = 0.0

            current_fan_pressure = 0.0
            current_fan_efficiency = 0.01 # Avoid division by zero

            if chosen_vent_type_from_config != "Natural":
                if fan_pressure_override_Pa is not None and fan_pressure_override_Pa >= 0: # Allow 0 pressure
                    current_fan_pressure = fan_pressure_override_Pa
                else:
                    current_fan_pressure = chosen_params_from_config.get("Fan_Pressure_Rise", 0.0)

                if fan_efficiency_override is not None and 0.01 <= fan_efficiency_override <= 1.0:
                    current_fan_efficiency = fan_efficiency_override
                else:
                    current_fan_efficiency = chosen_params_from_config.get("Fan_Total_Efficiency", 0.7)
                    current_fan_efficiency = min(1.0, max(0.01, current_fan_efficiency))

                if hasattr(vobj, "Fan_Pressure_Rise"):
                    vobj.Fan_Pressure_Rise = max(0.0, current_fan_pressure)
                if hasattr(vobj, "Fan_Total_Efficiency"):
                    vobj.Fan_Total_Efficiency = current_fan_efficiency
            
            for param_field, fixed_val in fixed_params_from_config.items():
                if hasattr(vobj, param_field):
                    try: setattr(vobj, param_field, fixed_val)
                    except Exception as set_err: print(f"[VENT WARNING] Failed to set {vent_obj_type_from_config} {param_field} = {fixed_val}: {set_err}")

        except Exception as e:
            print(f"[ERROR] Failed to create {config.get('ventilation_object_type', 'UNKNOWN_VENT_OBJECT')} for {zone_name}: {e}")
            vent_obj_or_ideal_obj = None

    # --- 6) Return the created/modified objects ---
    return iobj, vent_obj_or_ideal_obj