# ventilation/create_ventilation_systems.py

import random
import math # For isnan checks if needed
from typing import Optional, Any, Tuple # Added typing

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


def create_ventilation_system(
    idf: IDF,
    building_function: str,          # 'residential' or 'non_residential'
    system_type: str,                # 'A', 'B', 'C', or 'D'
    zone_name: str,
    # --- Zone-specific flows ---
    infiltration_m3_s: float,          # Calculated infiltration for THIS zone (m3/s)
    vent_flow_m3_s: float,             # Calculated required ventilation for THIS zone (m3/s)
    # --- Schedule names ---
    infiltration_sched_name: str ="AlwaysOnSched",
    ventilation_sched_name: str ="VentSched_DayNight",
    # --- Strategy for picking from ranges (e.g., fan eff) ---
    pick_strategy: str ="midpoint",   # or "random"
    # --- Parameters specifically for System D (IdealLoads) ---
    dsoa_object_name: Optional[str] =None, # Name of the DesignSpecification:OutdoorAir object
    hrv_sensible_effectiveness: float =0.0,
    hrv_latent_effectiveness: float =0.0 # Added latent effectiveness parameter
) -> Tuple[Optional[Any], Optional[Any]]: # Return type hint Any or specific eppy/geomeppy type
    """
    Creates EnergyPlus objects for infiltration and ventilation for a specific zone.

    1) Always creates a ZONEINFILTRATION:DESIGNFLOWRATE object using the provided
       zone-specific infiltration flow rate.
    2) Depending on system_type:
        - A/B/C: Creates a ZONEVENTILATION:DESIGNFLOWRATE object using the
                 zone-specific ventilation flow and sets fan parameters based on config.
        - D:     Finds the existing ZONEHVAC:IDEALLOADSAIRSYSTEM for the zone
                 and configures it to provide outdoor air ventilation based on
                 the referenced dsoa_object_name, also setting heat recovery.

    Args:
        idf: geomeppy IDF object.
        building_function (str): 'residential' or 'non_residential'.
        system_type (str): 'A', 'B', 'C', or 'D'.
        zone_name (str): Name of the target zone.
        infiltration_m3_s (float): Zone-specific infiltration flow rate (m3/s).
        vent_flow_m3_s (float): Zone-specific required ventilation flow rate (m3/s).
        infiltration_sched_name (str): Schedule name for infiltration.
        ventilation_sched_name (str): Schedule name for mechanical ventilation.
        pick_strategy (str): "midpoint" or "random" for selecting from parameter ranges.
        dsoa_object_name (str, optional): Name of the DesignSpecification:OutdoorAir object (required for System D).
        hrv_sensible_effectiveness (float): Sensible HRV effectiveness (for System D).
        hrv_latent_effectiveness (float): Latent HRV effectiveness (for System D).

    Returns:
        tuple: (infiltration_obj, vent_obj_or_ideal_obj)
               The created infiltration object and either the created ventilation object (A/B/C)
               or the modified IdealLoads object (D), or (None, None) if a critical error occurred.
    """

    # --- 1) Get System Configuration ---
    config = None
    try:
        # Use .get for safer dictionary access with defaults
        func_config = SYSTEMS_CONFIG.get(building_function)
        if not func_config:
            print(f"[WARNING] Building function '{building_function}' not found in SYSTEMS_CONFIG. Defaulting to 'residential'.")
            func_config = SYSTEMS_CONFIG.get("residential", {}) # Default to residential config or empty

        config = func_config.get(system_type)
        if not config:
             print(f"[WARNING] System type '{system_type}' not found for '{building_function}'. Defaulting to 'A'.")
             config = func_config.get("A", {}) # Default to system A config or empty

    except Exception as e:
        print(f"[ERROR] Failed to get system config for {building_function}/{system_type}: {e}")
        return None, None # Cannot proceed without config

    if not config: # Check if config retrieval failed completely
         print(f"[ERROR] System config for {building_function}/{system_type} is empty or invalid.")
         return None, None

    # --- 2) Helper to Pick Value from Range ---
    def pick_val(rng):
        """Picks value from (min, max) tuple based on pick_strategy."""
        if not isinstance(rng, (list, tuple)) or len(rng) != 2:
            # print(f"[DEBUG] Invalid range tuple: {rng}. Returning 0.") # Reduce verbosity
            return 0.0
        min_v, max_v = rng
        try:
            min_v = float(min_v)
            max_v = float(max_v)
            if math.isnan(min_v) or math.isnan(max_v): raise ValueError("NaN in range")
            if min_v > max_v: min_v = max_v # Ensure min <= max
        except (ValueError, TypeError):
             # print(f"[DEBUG] Invalid numeric values in range {rng}. Using 0.") # Reduce verbosity
             return 0.0

        if pick_strategy == "random":
            return random.uniform(min_v, max_v)
        else: # Default to midpoint
            return (min_v + max_v) / 2.0

    # --- 3) Create Infiltration Object (Always) ---
    iobj = None # Initialize
    try:
        iobj = idf.newidfobject("ZONEINFILTRATION:DESIGNFLOWRATE")
        # Generate a unique name - ensure zone_name is clean (no weird chars) if necessary
        base_name = f"Infil_{building_function}_{system_type}_{zone_name}"
        # Clean the base_name if needed (e.g., replace spaces, special chars)
        clean_base_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in base_name)

        # ----- CORRECTED NAME ASSIGNMENT HERE -----
        iobj.Name = clean_base_name
        # ----- END CORRECTION -----


        # Set zone name (handle potential variations in field name)
        zone_field_found = False
        if hasattr(iobj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
            iobj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_name
            zone_field_found = True
        elif hasattr(iobj, "Zone_or_ZoneList_Name"):
             iobj.Zone_or_ZoneList_Name = zone_name
             zone_field_found = True
        else:
             print(f"[ERROR] Could not find Zone Name field for ZONEINFILTRATION:DESIGNFLOWRATE.")
             # Handle error - maybe return None, None? For now, continue but obj might be invalid.

        if not zone_field_found:
             # If zone cannot be assigned, the object is useless
             raise ValueError("Failed to assign zone name to infiltration object.")

        # Assign infiltration schedule and zone-specific flow
        iobj.Schedule_Name = infiltration_sched_name
        iobj.Design_Flow_Rate_Calculation_Method = "Flow/Zone"
        # Ensure flow is not negative
        iobj.Design_Flow_Rate = max(0.0, infiltration_m3_s)

        # Set coefficients for constant flow (no dynamic response from weather)
        iobj.Constant_Term_Coefficient = 1.0
        iobj.Temperature_Term_Coefficient = 0.0
        iobj.Velocity_Term_Coefficient = 0.0
        iobj.Velocity_Squared_Term_Coefficient = 0.0

    except Exception as e:
        print(f"[ERROR] Failed to create ZONEINFILTRATION:DESIGNFLOWRATE for {zone_name}: {e}")
        # Decide how to handle: return None, None? Or just return the partially created iobj?
        # Returning None, None seems safer if core object creation fails.
        return None, None

    # --- 4) Prepare Chosen Parameter Values from Config ---
    chosen_params = {}
    range_dict = config.get("range_params", {})
    for param_name, rng in range_dict.items():
        chosen_val = pick_val(rng)
        chosen_params[param_name] = chosen_val

    # Get fixed parameters for the system type
    fixed_params = config.get("fixed_params", {})

    # Choose ventilation type (for Systems A/B/C)
    ventilation_type_list = config.get("ventilation_type_options", ["Natural"])
    chosen_vent_type = "Natural" # Default
    if ventilation_type_list:
        # If multiple options, pick one (randomly or first)
        chosen_vent_type = random.choice(ventilation_type_list) if pick_strategy == "random" else ventilation_type_list[0]

    # --- 5) Create/Configure Ventilation System Object ---
    vent_obj = None # Initialize

    if config.get("use_ideal_loads", False):
        # --- System D: Configure Existing IdealLoadsAirSystem ---
        ideal_name = f"{zone_name} Ideal Loads" # Assumes this naming convention is used elsewhere
        ideal_obj = idf.getobject("ZONEHVAC:IDEALLOADSAIRSYSTEM", ideal_name)

        if not ideal_obj:
            print(f"[VENT WARNING] ZONEHVAC:IDEALLOADSAIRSYSTEM '{ideal_name}' not found for System D in zone {zone_name}. Cannot configure ventilation.")
            # Return the infiltration object and None for the vent object
            return iobj, None
        else:
            # print(f"[VENT DEBUG] Configuring IdealLoads '{ideal_name}' for System D ventilation in zone {zone_name}.") # Reduced verbosity
            vent_obj = ideal_obj # Assign ideal_obj as the second return object

            # --- Enable Outdoor Air ---
            if not dsoa_object_name:
                 print(f"[VENT WARNING] DSOA object name not provided for System D config of {ideal_name}. OA will not be enabled.")
            elif hasattr(ideal_obj, "Design_Specification_Outdoor_Air_Object_Name"):
                 # Check if DSOA object actually exists in IDF (case-insensitive check)
                 if idf.getobject("DESIGNSPECIFICATION:OUTDOORAIR", dsoa_object_name.upper()):
                      ideal_obj.Design_Specification_Outdoor_Air_Object_Name = dsoa_object_name
                      # print(f"  -> Linked IdealLoads to DSOA: {dsoa_object_name}") # Reduced verbosity
                 else:
                      print(f"[VENT WARNING] Specified DSOA object '{dsoa_object_name}' not found in IDF for {ideal_name}. OA not linked.")
            else:
                 print(f"[VENT WARNING] IdealLoads object {ideal_name} lacks 'Design_Specification_Outdoor_Air_Object_Name' field.")

            # --- Set other fixed parameters from config ---
            for param_field, fixed_val in fixed_params.items():
                if param_field == "Design_Specification_Outdoor_Air_Object_Name": continue # Handled above
                if hasattr(ideal_obj, param_field):
                    try:
                        setattr(ideal_obj, param_field, fixed_val)
                    except Exception as set_err:
                         print(f"[VENT WARNING] Failed to set IdealLoads {param_field} = {fixed_val} for {ideal_name}: {set_err}")
                # else: # Reduce verbosity
                    # print(f"[VENT DEBUG] IdealLoads object {ideal_name} lacks field '{param_field}' from fixed_params config.")

            # --- Set Heat Recovery ---
            sens_eff = max(0.0, hrv_sensible_effectiveness) # Ensure non-negative
            lat_eff = max(0.0, hrv_latent_effectiveness)   # Ensure non-negative

            hr_type = "None"
            if sens_eff > 0 and lat_eff <= 0: hr_type = "Sensible"
            elif sens_eff > 0 and lat_eff > 0: hr_type = "Enthalpy"
            elif sens_eff <= 0 and lat_eff > 0: hr_type = "Enthalpy"

            try:
                if hasattr(ideal_obj, "Heat_Recovery_Type"):
                    # Only set HR Type if effectiveness > 0
                    ideal_obj.Heat_Recovery_Type = hr_type if (sens_eff > 0 or lat_eff > 0) else "None"
                if hasattr(ideal_obj, "Sensible_Heat_Recovery_Effectiveness"):
                    ideal_obj.Sensible_Heat_Recovery_Effectiveness = sens_eff
                if hasattr(ideal_obj, "Latent_Heat_Recovery_Effectiveness"):
                    ideal_obj.Latent_Heat_Recovery_Effectiveness = lat_eff
                # print(f"  -> Set IdealLoads Heat Recovery: Type={ideal_obj.Heat_Recovery_Type}, SensEff={sens_eff:.2f}, LatEff={lat_eff:.2f}") # Reduced verbosity
            except Exception as hr_err:
                 print(f"[VENT WARNING] Failed to set Heat Recovery fields for {ideal_name}: {hr_err}")

    else:
        # --- Systems A, B, C: Create ZONEVENTILATION:DESIGNFLOWRATE ---
        try:
            vent_obj_type = config.get("ventilation_object_type", "ZONEVENTILATION:DESIGNFLOWRATE")
            vobj = idf.newidfobject(vent_obj_type)
            vent_obj = vobj # Assign vobj as the second return object

            base_name = f"Vent_{building_function}_{system_type}_{zone_name}"
            clean_base_name = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in base_name)
            vobj.Name = clean_base_name

            # Set zone name
            zone_field_found = False
            if hasattr(vobj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
                vobj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_name
                zone_field_found = True
            elif hasattr(vobj, "Zone_or_ZoneList_Name"):
                 vobj.Zone_or_ZoneList_Name = zone_name
                 zone_field_found = True
            if not zone_field_found:
                 raise ValueError(f"Could not find Zone Name field for {vent_obj_type}.")

            # Assign ventilation schedule and zone-specific flow
            vobj.Schedule_Name = ventilation_sched_name
            vobj.Design_Flow_Rate_Calculation_Method = "Flow/Zone"
            vobj.Design_Flow_Rate = max(0.0, vent_flow_m3_s) # Ensure non-negative

            # Set Ventilation Type (Natural, Intake, Exhaust, Balanced)
            if hasattr(vobj, "Ventilation_Type"):
                vobj.Ventilation_Type = chosen_vent_type

            # Set Fan parameters if applicable (for Intake/Exhaust/Balanced types)
            if chosen_vent_type != "Natural":
                if hasattr(vobj, "Fan_Pressure_Rise") and "Fan_Pressure_Rise" in chosen_params:
                    vobj.Fan_Pressure_Rise = max(0.0, chosen_params["Fan_Pressure_Rise"])
                if hasattr(vobj, "Fan_Total_Efficiency") and "Fan_Total_Efficiency" in chosen_params:
                    eff = chosen_params["Fan_Total_Efficiency"]
                    vobj.Fan_Total_Efficiency = min(1.0, max(0.01, eff)) # Avoid 0 or <=0

        except Exception as e:
            print(f"[ERROR] Failed to create {config.get('ventilation_object_type')} for {zone_name}: {e}")
            vent_obj = None # Ensure vent_obj is None on error

    # --- 6) Return the created/modified objects ---
    return iobj, vent_obj