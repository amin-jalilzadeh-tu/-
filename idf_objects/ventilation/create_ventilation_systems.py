# ventilation/create_ventilation_systems.py

import random
from idf_objects.ventilation.config_systems import SYSTEMS_CONFIG

def create_ventilation_system(
    idf,
    building_function,      # 'residential' or 'non_residential'
    system_type,            # 'A', 'B', 'C', or 'D'
    zone_name,
    infiltration_m3_s,
    vent_flow_m3_s,
    infiltration_sched_name="AlwaysOnSched",
    ventilation_sched_name="VentSched_DayNight",
    pick_strategy="midpoint"  # or "random"
):
    """
    Creates two objects for the zone:
      1) A ZONEINFILTRATION:DESIGNFLOWRATE object (always).
      2) Depending on system_type:
         - A/B/C => a ZONEVENTILATION:DESIGNFLOWRATE object
         - D     => modifies an existing ZONEHVAC:IDEALLOADSAIRSYSTEM
                    (already added by add_HVAC_Ideal_to_all_zones, if used)

    Returns (infiltration_obj, vent_obj_or_ideal_obj).
    """

    # -------------------------------------------------------
    # 1) Grab the config for this system
    # -------------------------------------------------------
    if building_function not in SYSTEMS_CONFIG:
        building_function = "residential"
    if system_type not in SYSTEMS_CONFIG[building_function]:
        system_type = "A"

    config = SYSTEMS_CONFIG[building_function][system_type]

    # -------------------------------------------------------
    # 2) Helper to pick a single value from a (min, max) range
    # -------------------------------------------------------
    def pick_val(rng):
        """
        rng is (min_val, max_val).
        pick_strategy == 'midpoint' => return average
        pick_strategy == 'random'   => return random.uniform(...)
        """
        if pick_strategy == "random":
            return random.uniform(rng[0], rng[1])
        else:
            # default => midpoint
            return (rng[0] + rng[1]) / 2.0

    # -------------------------------------------------------
    # 3) Create infiltration object (ZONEINFILTRATION:DESIGNFLOWRATE)
    # -------------------------------------------------------
    iobj = idf.newidfobject("ZONEINFILTRATION:DESIGNFLOWRATE")
    iobj.Name = f"Infil_{building_function}_{system_type}_{zone_name}"

    # Some E+ versions use .Zone_or_ZoneList_or_Space_or_SpaceList_Name
    # others use .Zone_or_ZoneList_Name
    if hasattr(iobj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
        iobj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_name
    else:
        iobj.Zone_or_ZoneList_Name = zone_name

    # Assign infiltration schedule and flow
    iobj.Schedule_Name = infiltration_sched_name
    iobj.Design_Flow_Rate_Calculation_Method = "Flow/Zone"
    iobj.Design_Flow_Rate = infiltration_m3_s

    # -------------------------------------------------------
    # 4) Prepare final param values from config["range_params"]
    #    e.g. fan pressure, heat recovery, etc.
    # -------------------------------------------------------
    chosen_params = {}
    range_dict = config.get("range_params", {})
    for param_name, rng in range_dict.items():
        chosen_val = pick_val(rng)
        chosen_params[param_name] = chosen_val

    # Choose from the ventilation_type_options if present
    ventilation_type_list = config.get("ventilation_type_options", [])
    if ventilation_type_list:
        chosen_vent_type = random.choice(ventilation_type_list)
    else:
        chosen_vent_type = "Natural"  # fallback if none provided

    # -------------------------------------------------------
    # 5) If system D => update an existing IdealLoads object
    #    else => create a ZONEVENTILATION:DESIGNFLOWRATE
    # -------------------------------------------------------
    if config["use_ideal_loads"]:
        # System D => Balanced mechanical => find the existing IdealLoads object
        ideal_name = f"{zone_name} Ideal Loads"
        ideal_obj = idf.getobject("ZONEHVAC:IDEALLOADSAIRSYSTEM", ideal_name)

        if ideal_obj:
            # Example: set fields in the IdealLoads that exist in chosen_params
            # e.g. if param_name == "Sensible_Heat_Recovery_Effectiveness"
            for param_field, final_val in chosen_params.items():
                # We must confirm the IDD field name matches param_field
                if hasattr(ideal_obj, param_field):
                    setattr(ideal_obj, param_field, final_val)

            # If desired, you could limit the air flow to 'vent_flow_m3_s' here:
            #   ideal_obj.Heating_Limit = "LimitFlowRate"
            #   ideal_obj.Maximum_Heating_Air_Flow_Rate = vent_flow_m3_s
            #   ideal_obj.Cooling_Limit = "LimitFlowRate"
            #   ideal_obj.Maximum_Cooling_Air_Flow_Rate = vent_flow_m3_s

            return iobj, ideal_obj
        else:
            print(f"[VENT WARNING] {zone_name} Ideal Loads not found; system D creation skipped.")
            return iobj, None

    else:
        # Systems A, B, C => create a ZONEVENTILATION:DESIGNFLOWRATE
        vobj = idf.newidfobject(config["ventilation_object_type"])
        vobj.Name = f"Vent_{building_function}_{system_type}_{zone_name}"
        if hasattr(vobj, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
            vobj.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_name
        else:
            vobj.Zone_or_ZoneList_Name = zone_name

        # Assign the chosen (or default) ventilation schedule and flow
        vobj.Schedule_Name = ventilation_sched_name
        vobj.Design_Flow_Rate_Calculation_Method = "Flow/Zone"
        vobj.Design_Flow_Rate = vent_flow_m3_s

        # Insert system-specific fields if they exist in the object
        if hasattr(vobj, "Ventilation_Type"):
            vobj.Ventilation_Type = chosen_vent_type

        if hasattr(vobj, "Fan_Pressure_Rise") and "Fan_Pressure_Rise" in chosen_params:
            vobj.Fan_Pressure_Rise = chosen_params["Fan_Pressure_Rise"]

        if hasattr(vobj, "Fan_Total_Efficiency") and "Fan_Total_Efficiency" in chosen_params:
            vobj.Fan_Total_Efficiency = chosen_params["Fan_Total_Efficiency"]

        return iobj, vobj
