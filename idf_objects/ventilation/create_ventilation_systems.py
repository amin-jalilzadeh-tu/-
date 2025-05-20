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
    base_flow_m3_s: float,
    typical_delta_t: float = 10.0,
    typical_wind: float = 3.0,
):
    """Configure infiltration coefficients so that the infiltration flow
    varies with temperature difference and wind speed.

    The ``base_flow_m3_s`` value is assumed to correspond to the flow when
    ``typical_delta_t`` (degC) and ``typical_wind`` (m/s) occur.  Coefficients
    are chosen so that the resulting design flow rate equals ``base_flow_m3_s``
    under those typical conditions.
    """

    # Simple default coefficients that introduce dependence on \u0394T and wind
    A = 0.5
    B = 0.02
    C = 0.04
    D = 0.0

    denom = A + B * typical_delta_t + C * typical_wind + D * (typical_wind ** 2)
    if denom <= 0:
        denom = 1.0

    infil_obj.Design_Flow_Rate = base_flow_m3_s / denom
    infil_obj.Constant_Term_Coefficient = A
    infil_obj.Temperature_Term_Coefficient = B
    infil_obj.Velocity_Term_Coefficient = C
    infil_obj.Velocity_Squared_Term_Coefficient = D


def create_ventilation_system(
    idf: IDF,
    building_function: str,      # 'residential' or 'non_residential'
    system_type: str,            # 'A', 'B', 'C', or 'D'
    zone_name: str,
    # --- Zone-specific flows ---
    infiltration_m3_s: float,      # Calculated infiltration for THIS zone (m3/s)
    vent_flow_m3_s: float,         # Calculated required ventilation for THIS zone (m3/s)
    # --- Schedule names ---
    infiltration_sched_name: str = "AlwaysOnSched",
    ventilation_sched_name: str = "VentSched_DayNight",  # Used for ZoneVentilation and IdealLoads Availability
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
    # --- NEW: Overrides for fan parameters (for Systems A, B, C primarily) ---
    fan_pressure_override_Pa: Optional[float] = None,
    fan_efficiency_override: Optional[float] = None,
) -> Tuple[Optional[Any], Optional[Any]]:  # Return type hint Any or specific eppy/geomeppy type
    """
    Creates EnergyPlus objects for infiltration and ventilation for a specific zone.
    (Refer to previous docstring for more details)

    Key Updates:
    - More robust IdealLoadsAirSystem object lookup.
    - Uses fan_pressure_override_Pa and fan_efficiency_override if provided for Systems A,B,C.
    - Applies ventilation_sched_name to IdealLoadsAirSystem's Availability_Schedule_Name for System D.
    - ``infiltration_model`` selects between constant or weather-dependent infiltration.
    - ``typical_delta_t`` and ``typical_wind`` set the reference conditions for weather-dependent mode.
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
        # Generate a unique name
        base_name = f"Infil_{building_function[:4]}_{system_type}_{zone_name}"
        # Clean the base_name (replace spaces, special chars not allowed by E+)
        clean_base_name = "".join(c if c.isalnum() or c in ['-', '_', '.'] else '_' for c in base_name)[:100] # Max 100 chars
        iobj.Name = clean_base_name

        # Set zone name (handle potential variations in field name with hasattr)
        zone_field_assigned = False
        for field_name in ["Zone_or_ZoneList_Name", "Zone_Name", "Zone_or_ZoneList_or_Space_or_SpaceList_Name"]:
            if hasattr(iobj, field_name):
                setattr(iobj, field_name, zone_name)
                zone_field_assigned = True
                break
        if not zone_field_assigned:
            raise ValueError(f"Could not find or set Zone Name field for ZONEINFILTRATION:DESIGNFLOWRATE object '{iobj.Name}'.")

        iobj.Schedule_Name = infiltration_sched_name
        iobj.Design_Flow_Rate_Calculation_Method = "Flow/Zone"

        if infiltration_model.lower() == "weather":
            # In weather mode, use reference conditions to set coefficients
            apply_weather_coefficients(
                iobj,
                max(0.0, infiltration_m3_s),
                typical_delta_t=typical_delta_t,
                typical_wind=typical_wind,
            )
        else:
            # Constant flow with coefficients fixed at 1, 0, 0, 0
            iobj.Design_Flow_Rate = max(0.0, infiltration_m3_s)
            iobj.Constant_Term_Coefficient = 1.0
            iobj.Temperature_Term_Coefficient = 0.0
            iobj.Velocity_Term_Coefficient = 0.0
            iobj.Velocity_Squared_Term_Coefficient = 0.0

    except Exception as e:
        print(f"[ERROR] Failed to create ZONEINFILTRATION:DESIGNFLOWRATE for {zone_name}: {e}")
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
        # Try common naming patterns for IdealLoadsAirSystem
        possible_ideal_names = [
            f"{zone_name} Ideal Loads",
            f"{zone_name}_Ideal_Loads",
            f"IdealLoads_{zone_name}"
        ]
        ideal_obj_found = None
        for name_attempt in possible_ideal_names:
            ideal_obj_found = idf.getobject("ZONEHVAC:IDEALLOADSAIRSYSTEM", name_attempt.upper()) # Case-insensitive check
            if ideal_obj_found:
                # print(f"[VENT DEBUG] Found IdealLoadsAirSystem: '{ideal_obj_found.Name}' for zone {zone_name}")
                break
        
        if not ideal_obj_found:
            print(f"[VENT WARNING] ZONEHVAC:IDEALLOADSAIRSYSTEM not found using patterns for System D in zone {zone_name}. Tried: {possible_ideal_names}. Cannot configure OA or HRV.")
            return iobj, None # Return infiltration obj, but None for vent/ideal obj
        else:
            vent_obj_or_ideal_obj = ideal_obj_found # This is the object to be returned

            # Apply ventilation schedule to IdealLoads Availability
            if hasattr(vent_obj_or_ideal_obj, "Availability_Schedule_Name"):
                vent_obj_or_ideal_obj.Availability_Schedule_Name = ventilation_sched_name
                # print(f"  -> Set IdealLoads Availability Schedule: {ventilation_sched_name}")
            else:
                print(f"[VENT WARNING] IdealLoads object {vent_obj_or_ideal_obj.Name} lacks 'Availability_Schedule_Name' field.")

            # --- Enable Outdoor Air by linking DSOA object ---
            if dsoa_object_name: # If a DSOA name is provided (expected for System D)
                if hasattr(vent_obj_or_ideal_obj, "Design_Specification_Outdoor_Air_Object_Name"):
                    # Check if the DSOA object actually exists in the IDF
                    if idf.getobject("DESIGNSPECIFICATION:OUTDOORAIR", dsoa_object_name.upper()):
                        vent_obj_or_ideal_obj.Design_Specification_Outdoor_Air_Object_Name = dsoa_object_name
                        # print(f"  -> Linked IdealLoads to DSOA: {dsoa_object_name}")
                    else:
                        print(f"[VENT WARNING] Specified DSOA object '{dsoa_object_name}' not found in IDF for IdealLoads '{vent_obj_or_ideal_obj.Name}'. Outdoor Air not linked via DSOA.")
                else:
                    print(f"[VENT WARNING] IdealLoads object {vent_obj_or_ideal_obj.Name} lacks 'Design_Specification_Outdoor_Air_Object_Name' field.")
            else: # dsoa_object_name was not provided
                print(f"[VENT WARNING] DSOA object name not provided for System D configuration of IdealLoads '{vent_obj_or_ideal_obj.Name}'. Outdoor Air will not be enabled via DSOA method.")
                # Ensure the field is blanked if no DSOA is intended or available
                if hasattr(vent_obj_or_ideal_obj, "Design_Specification_Outdoor_Air_Object_Name"):
                     vent_obj_or_ideal_obj.Design_Specification_Outdoor_Air_Object_Name = ""


            # --- Set other fixed parameters from SYSTEMS_CONFIG for IdealLoads ---
            for param_field, fixed_val in fixed_params_from_config.items():
                if param_field == "Design_Specification_Outdoor_Air_Object_Name": continue # Handled above
                if hasattr(vent_obj_or_ideal_obj, param_field):
                    try:
                        setattr(vent_obj_or_ideal_obj, param_field, fixed_val)
                    except Exception as set_err:
                        print(f"[VENT WARNING] Failed to set IdealLoads {param_field} = {fixed_val} for {vent_obj_or_ideal_obj.Name}: {set_err}")
                # else: print(f"[VENT DEBUG] IdealLoads object {vent_obj_or_ideal_obj.Name} lacks field '{param_field}' from fixed_params config.")

            # --- Set Heat Recovery (using effectiveness values passed into this function) ---
            sens_eff = max(0.0, hrv_sensible_effectiveness)   # Ensure non-negative
            lat_eff = max(0.0, hrv_latent_effectiveness)    # Ensure non-negative

            hr_type = "None"
            if sens_eff > 0.001 and lat_eff > 0.001: # Threshold to consider effective
                hr_type = "Enthalpy"
            elif sens_eff > 0.001:
                hr_type = "Sensible"
            elif lat_eff > 0.001: # E+ uses Enthalpy for latent-only recovery with IdealLoads typically
                hr_type = "Enthalpy" # Or "Latent" if E+ version supports it distinctly for IdealLoads

            try:
                if hasattr(vent_obj_or_ideal_obj, "Heat_Recovery_Type"):
                    vent_obj_or_ideal_obj.Heat_Recovery_Type = hr_type
                if hasattr(vent_obj_or_ideal_obj, "Sensible_Heat_Recovery_Effectiveness"):
                    vent_obj_or_ideal_obj.Sensible_Heat_Recovery_Effectiveness = sens_eff if hr_type != "None" else 0.0
                if hasattr(vent_obj_or_ideal_obj, "Latent_Heat_Recovery_Effectiveness"):
                    vent_obj_or_ideal_obj.Latent_Heat_Recovery_Effectiveness = lat_eff if hr_type != "None" else 0.0
                # print(f"  -> Set IdealLoads Heat Recovery: Type={hr_type}, SensEff={sens_eff:.2f}, LatEff={lat_eff:.2f}")
            except Exception as hr_err:
                print(f"[VENT WARNING] Failed to set Heat Recovery fields for {vent_obj_or_ideal_obj.Name}: {hr_err}")

    else: # Systems A, B, C: Create ZONEVENTILATION:DESIGNFLOWRATE
        try:
            vent_obj_type_from_config = config.get("ventilation_object_type", "ZONEVENTILATION:DESIGNFLOWRATE")
            vobj = idf.newidfobject(vent_obj_type_from_config)
            vent_obj_or_ideal_obj = vobj # This is the object to be returned

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
            vobj.Design_Flow_Rate_Calculation_Method = "Flow/Zone"
            vobj.Design_Flow_Rate = max(0.0, vent_flow_m3_s) # Ensure non-negative

            if hasattr(vobj, "Ventilation_Type"):
                vobj.Ventilation_Type = chosen_vent_type_from_config # From SYSTEMS_CONFIG

            # Set Fan parameters if applicable (for Intake/Exhaust/Balanced, not Natural)
            # Prioritize overrides passed to this function.
            current_fan_pressure = 0.0
            current_fan_efficiency = 0.01 # Avoid division by zero

            if chosen_vent_type_from_config != "Natural":
                # Use override if valid, otherwise use value from SYSTEMS_CONFIG
                if fan_pressure_override_Pa is not None and fan_pressure_override_Pa > 0:
                    current_fan_pressure = fan_pressure_override_Pa
                else:
                    current_fan_pressure = chosen_params_from_config.get("Fan_Pressure_Rise", 0.0)

                if fan_efficiency_override is not None and 0.01 <= fan_efficiency_override <= 1.0:
                    current_fan_efficiency = fan_efficiency_override
                else:
                    current_fan_efficiency = chosen_params_from_config.get("Fan_Total_Efficiency", 0.7) # Default 0.7 if not in config
                    current_fan_efficiency = min(1.0, max(0.01, current_fan_efficiency)) # Clamp to valid range

                if hasattr(vobj, "Fan_Pressure_Rise"):
                    vobj.Fan_Pressure_Rise = max(0.0, current_fan_pressure)
                if hasattr(vobj, "Fan_Total_Efficiency"):
                    vobj.Fan_Total_Efficiency = current_fan_efficiency
                # print(f"  -> Set ZoneVent Fan: Pressure={vobj.Fan_Pressure_Rise:.1f} Pa, Efficiency={vobj.Fan_Total_Efficiency:.2f}")
            
            # Set other fixed parameters from config if any for ZoneVentilation objects
            for param_field, fixed_val in fixed_params_from_config.items():
                if hasattr(vobj, param_field):
                    try: setattr(vobj, param_field, fixed_val)
                    except Exception as set_err: print(f"[VENT WARNING] Failed to set {vent_obj_type_from_config} {param_field} = {fixed_val}: {set_err}")


        except Exception as e:
            print(f"[ERROR] Failed to create {config.get('ventilation_object_type', 'UNKNOWN_VENT_OBJECT')} for {zone_name}: {e}")
            vent_obj_or_ideal_obj = None # Ensure it's None on error

    # --- 6) Return the created/modified objects ---
    return iobj, vent_obj_or_ideal_obj