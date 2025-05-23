# File: idf_objects/HVAC/custom_hvac.py

from typing import Dict, Optional, Any, List

# Assuming these modules are in the same directory or accessible via path
from .assign_hvac_values import assign_hvac_ideal_parameters
from .schedule_creation import create_schedules_for_building

def add_HVAC_Ideal_to_all_zones(
    idf, # The IDF model object (e.g., from eppy)
    building_row: Optional[Dict[str, Any]] = None,
    calibration_stage: str = "pre_calibration",
    strategy: str = "A",
    random_seed: Optional[int] = None,
    user_config_hvac: Optional[List[Dict[str, Any]]] = None,
    assigned_hvac_log: Optional[Dict] = None
):
    """
    Adds an Ideal Loads Air System to every Zone in the IDF model, along with
    necessary schedules & setpoints derived from hvac_lookup data and user overrides.

    Args:
        idf: The IDF model object.
        building_row: A dictionary containing metadata about the building
                      (e.g., ogc_fid, building_function, age_range).
        calibration_stage: Stage identifier (e.g., "pre_calibration", "calibrated").
        strategy: Strategy for picking values from ranges ('A'=midpoint, 'B'=random).
        random_seed: Optional seed for reproducibility if strategy 'B' is used.
        user_config_hvac: Optional list of override dictionaries for HVAC parameters.
        assigned_hvac_log: Optional dictionary to store assigned parameters and logs.

    Modifies the `idf` object in place and optionally updates `assigned_hvac_log`.
    """

    # --- Basic Setup & Input Handling ---
    if building_row is None:
        building_row = {} # Use empty dict to avoid errors on .get()
        print("[Custom HVAC Warning] add_HVAC_Ideal_to_all_zones called without building_row metadata.")

    bldg_id = building_row.get("ogc_fid", 0) # Default to 0 if no ID provided
    bldg_func = building_row.get("building_function", "residential") # Default func
    res_type = building_row.get("residential_type") # Can be None if not residential
    nonres_type = building_row.get("non_residential_type") # Can be None if residential
    age_range = building_row.get("age_range", "unknown") # Default age
    scenario = building_row.get("scenario", "default_scenario") # Default scenario

    print(f"[Custom HVAC Info] Setting up Ideal Loads for Building ID: {bldg_id}, Function: {bldg_func}, Age: {age_range}")

    # --- 1) Get HVAC Parameters & Schedule Definitions ---
    try:
        hvac_params = assign_hvac_ideal_parameters(
            building_id=bldg_id,
            building_function=bldg_func,
            residential_type=res_type,
            non_residential_type=nonres_type,
            age_range=age_range,
            scenario=scenario,
            calibration_stage=calibration_stage,
            strategy=strategy,
            random_seed=random_seed,
            user_config_hvac=user_config_hvac,
            assigned_hvac_log=assigned_hvac_log # Pass log dict through
        )
    except Exception as e:
        print(f"[Custom HVAC Error] Failed to assign HVAC parameters for building {bldg_id}: {e}")
        return # Cannot proceed without parameters

    if not hvac_params or not isinstance(hvac_params, dict):
         print(f"[Custom HVAC Error] assign_hvac_ideal_parameters returned invalid data for building {bldg_id}. Aborting HVAC setup.")
         return

    # --- 2) Create Schedules in IDF ---
    schedule_details = hvac_params.get("schedule_details")
    if schedule_details and isinstance(schedule_details, dict):
        try:
            create_schedules_for_building(
                idf,
                schedule_details=schedule_details,
                building_id=bldg_id,
                assigned_hvac_log=assigned_hvac_log # Pass log dict through
            )
        except Exception as e:
            print(f"[Custom HVAC Error] Failed during schedule creation for building {bldg_id}: {e}")
            # Decide whether to proceed without custom schedules or abort
            # return
    else:
        print(f"[Custom HVAC Warning] No schedule_details found in hvac_params for building {bldg_id}. Schedules may not be created correctly.")


    # --- 3) Ensure Core IDF Objects Exist (Schedule Limits) ---
    # Check/create SCHEDULETYPELIMITS for Temperature
    if not idf.getobject("SCHEDULETYPELIMITS", "Temperature"):
        print("[Custom HVAC Info] Creating SCHEDULETYPELIMITS: Temperature")
        stl_temp = idf.newidfobject("SCHEDULETYPELIMITS")
        stl_temp.Name = "Temperature"
        stl_temp.Lower_Limit_Value = -100
        stl_temp.Upper_Limit_Value = 200
        stl_temp.Numeric_Type = "CONTINUOUS"
        # stl_temp.Unit_Type = "Temperature" # Optional depending on E+ version

    # Check/create SCHEDULETYPELIMITS for ControlType
    if not idf.getobject("SCHEDULETYPELIMITS", "ControlType"):
        print("[Custom HVAC Info] Creating SCHEDULETYPELIMITS: ControlType")
        stl_ctrl = idf.newidfobject("SCHEDULETYPELIMITS")
        stl_ctrl.Name = "ControlType"
        stl_ctrl.Lower_Limit_Value = 0
        stl_ctrl.Upper_Limit_Value = 4 # 0=Uncontrolled, 1=Thermo, 2=Humid, 3=Staged, 4=DualSetpt
        stl_ctrl.Numeric_Type = "DISCRETE"

    # Check/create SCHEDULETYPELIMITS for Fraction (FIX from previous analysis)
    if not idf.getobject("SCHEDULETYPELIMITS", "Fraction"):
        print("[Custom HVAC Info] Creating SCHEDULETYPELIMITS: Fraction")
        stl_frac = idf.newidfobject("SCHEDULETYPELIMITS")
        stl_frac.Name = "Fraction"
        stl_frac.Lower_Limit_Value = 0.0
        stl_frac.Upper_Limit_Value = 1.0
        stl_frac.Numeric_Type = "CONTINUOUS"
        # stl_frac.Unit_Type = "Dimensionless" # Optional

    # --- 4) Create Default Control Type Schedule (if needed) ---
    # This schedule tells the thermostat to use Dual Setpoints (Control Type 1)
    control_type_sched_name = "ZONE_CONTROL_TYPE_SCHEDULE" # Use underscore for safety
    ctrl_sched = idf.getobject("SCHEDULE:COMPACT", control_type_sched_name.upper())
    if not ctrl_sched:
        print(f"[Custom HVAC Info] Creating SCHEDULE:COMPACT: {control_type_sched_name}")
        ctrl_sched = idf.newidfobject("SCHEDULE:COMPACT")
        ctrl_sched.Name = control_type_sched_name
        ctrl_sched.Schedule_Type_Limits_Name = "ControlType"
        # --- FIX from previous analysis: Correct field format ---
        ctrl_sched.Field_1 = "Through: 12/31"  # No comma
        ctrl_sched.Field_2 = "For: AllDays"     # No comma
        # Control Type 4 corresponds to ThermostatSetpoint:DualSetpoint
        # which matches the thermostat object defined below.
        ctrl_sched.Field_3 = "Until: 24:00,4;"
    else:
        print(f"[Custom HVAC Info] Found existing schedule: {control_type_sched_name}")
        # Optionally verify/update its fields here if needed

    # --- 5) Retrieve Key Parameters for Ideal Loads ---
    try:
        max_heat_temp = hvac_params["max_heating_supply_air_temp"]
        min_cool_temp = hvac_params["min_cooling_supply_air_temp"]
    except KeyError as e:
         print(f"[Custom HVAC Error] Missing required temperature limit '{e}' in hvac_params for building {bldg_id}. Aborting.")
         return

    # Get the name of the HVAC availability schedule created earlier
    # Default to 'AlwaysOn' if not found, but log a warning
    hvac_avail_sched_name = "AlwaysOn" # Fallback default
    if schedule_details:
         hvac_avail_info = schedule_details.get("hvac_availability", {})
         hvac_avail_sched_name = hvac_avail_info.get("schedule_name", "HVAC_Avail_Sched") # Get name from lookup/override
         # Check if the schedule actually exists in the IDF after creation attempt
         if not idf.getobject("SCHEDULE:COMPACT", hvac_avail_sched_name.upper()):
             print(f"[Custom HVAC Warning] HVAC Availability schedule '{hvac_avail_sched_name}' not found in IDF. Defaulting IdealLoads Availability to 'AlwaysOn'.")
             hvac_avail_sched_name = "AlwaysOn" # Revert to default if creation failed/missing

    # Get the names for setpoint schedules (ensure consistency with schedule_creation.py)
    setpoint_sched_heat_name = "ZONE_HEATING_SETPOINTS" # Default name used in schedule_creation
    setpoint_sched_cool_name = "ZONE_COOLING_SETPOINTS" # Default name used in schedule_creation
    if schedule_details:
        setpoints_info = schedule_details.get("setpoints", {})
        setpoint_sched_heat_name = setpoints_info.get("schedule_name_heat", setpoint_sched_heat_name)
        setpoint_sched_cool_name = setpoints_info.get("schedule_name_cool", setpoint_sched_cool_name)
        # Check if these schedules exist
        if not idf.getobject("SCHEDULE:COMPACT", setpoint_sched_heat_name.upper()):
             print(f"[Custom HVAC Warning] Heating setpoint schedule '{setpoint_sched_heat_name}' not found in IDF.")
             # Thermostat object might fail later if schedule is missing
        if not idf.getobject("SCHEDULE:COMPACT", setpoint_sched_cool_name.upper()):
             print(f"[Custom HVAC Warning] Cooling setpoint schedule '{setpoint_sched_cool_name}' not found in IDF.")

    # --- 6) Process Each Zone ---
    zones = idf.idfobjects.get("ZONE", []) # Use .get for safety
    if not zones:
        print(f"[Custom HVAC Error] No ZONE objects found in the IDF model for building {bldg_id}. Cannot add HVAC systems.")
        return

    # Ensure the assigned_hvac_log structure is ready for zone data
    if assigned_hvac_log is not None:
        if bldg_id not in assigned_hvac_log:
            assigned_hvac_log[bldg_id] = {}
        if "zones" not in assigned_hvac_log[bldg_id]:
            assigned_hvac_log[bldg_id]["zones"] = {}

    print(f"[Custom HVAC Info] Processing {len(zones)} zones for Ideal Loads setup...")
    for zone_obj in zones:
        zone_name = zone_obj.Name
        print(f"  - Processing Zone: {zone_name}")

        # Define object names based on zone name
        thermostat_name = f"{zone_name}_CONTROLS"
        dual_setpoint_name = f"{zone_name}_SETPOINTS"
        equip_conn_name = zone_name # Convention often uses zone name
        equip_list_name = f"{zone_name}_EQUIPMENT"
        ideal_loads_name = f"{zone_name}_Ideal_Loads"
        inlet_nodelist_name = f"{zone_name}_INLETS"
        inlet_node_name = f"{zone_name}_INLET" # Single node for the list
        zone_node_name = f"{zone_name}_NODE"
        return_node_name = f"{zone_name}_OUTLET"


        # 6a) Create/Update Thermostat (ZONECONTROL:THERMOSTAT)
        # Use getobject for case-insensitive check if needed
        thermo = idf.getobject("ZONECONTROL:THERMOSTAT", thermostat_name.upper())
        if not thermo:
            thermo = idf.newidfobject("ZONECONTROL:THERMOSTAT")
            thermo.Name = thermostat_name
        # Assign zone name - check attribute based on potential E+ versions
        if hasattr(thermo, "Zone_or_ZoneList_or_Space_or_SpaceList_Name"):
            thermo.Zone_or_ZoneList_or_Space_or_SpaceList_Name = zone_name
        else:
            thermo.Zone_or_ZoneList_Name = zone_name # Older versions
        thermo.Control_Type_Schedule_Name = control_type_sched_name
        thermo.Control_1_Object_Type = "ThermostatSetpoint:DualSetpoint"
        thermo.Control_1_Name = dual_setpoint_name

        # 6b) Create/Update THERMOSTATSETPOINT:DUALSETPOINT
        dualset = idf.getobject("THERMOSTATSETPOINT:DUALSETPOINT", dual_setpoint_name.upper())
        if not dualset:
            dualset = idf.newidfobject("THERMOSTATSETPOINT:DUALSETPOINT")
            dualset.Name = dual_setpoint_name
        # --- Use the consistent schedule names identified earlier ---
        dualset.Heating_Setpoint_Temperature_Schedule_Name = setpoint_sched_heat_name
        dualset.Cooling_Setpoint_Temperature_Schedule_Name = setpoint_sched_cool_name


        # 6c) Create/Update ZONEHVAC:EQUIPMENTCONNECTIONS
        # Note: Name convention might vary; here using Zone Name directly
        eq_conn = idf.getobject("ZONEHVAC:EQUIPMENTCONNECTIONS", zone_name.upper())
        if not eq_conn:
            eq_conn = idf.newidfobject("ZONEHVAC:EQUIPMENTCONNECTIONS")
            eq_conn.Zone_Name = zone_name
        # Update fields
        eq_conn.Zone_Conditioning_Equipment_List_Name = equip_list_name
        eq_conn.Zone_Air_Inlet_Node_or_NodeList_Name = inlet_nodelist_name
        eq_conn.Zone_Air_Exhaust_Node_or_NodeList_Name = "" # Assuming no exhaust for ideal loads
        eq_conn.Zone_Air_Node_Name = zone_node_name
        eq_conn.Zone_Return_Air_Node_or_NodeList_Name = return_node_name


        # 6d) Create/Update ZONEHVAC:EQUIPMENTLIST
        eq_list = idf.getobject("ZONEHVAC:EQUIPMENTLIST", equip_list_name.upper())
        if not eq_list:
            eq_list = idf.newidfobject("ZONEHVAC:EQUIPMENTLIST")
            eq_list.Name = equip_list_name
        # Update fields - add Ideal Loads system
        eq_list.Load_Distribution_Scheme = "SequentialLoad" # Or UniformLoad, etc.
        eq_list.Zone_Equipment_1_Object_Type = "ZoneHVAC:IdealLoadsAirSystem"
        eq_list.Zone_Equipment_1_Name = ideal_loads_name
        eq_list.Zone_Equipment_1_Cooling_Sequence = 1
        eq_list.Zone_Equipment_1_Heating_or_NoLoad_Sequence = 1
        # Clear out other equipment slots if necessary
        # for i in range(2, 5): # Example: Clear eqpt 2, 3, 4
        #    setattr(eq_list, f"Zone_Equipment_{i}_Object_Type", "")
        #    setattr(eq_list, f"Zone_Equipment_{i}_Name", "")


        # 6e) Create/Update ZONEHVAC:IDEALLOADSAIRSYSTEM
        ideal = idf.getobject("ZONEHVAC:IDEALLOADSAIRSYSTEM", ideal_loads_name.upper())
        if not ideal:
            ideal = idf.newidfobject("ZONEHVAC:IDEALLOADSAIRSYSTEM")
            ideal.Name = ideal_loads_name
        # Update fields
        ideal.Availability_Schedule_Name = hvac_avail_sched_name # Use retrieved name
        ideal.Zone_Supply_Air_Node_Name = inlet_nodelist_name # Connects to inlet list
        ideal.Zone_Exhaust_Air_Node_Name = "" # Match connections object
        ideal.System_Inlet_Air_Node_Name = "" # Not connecting to outdoor air here

        # Supply air temperature limits
        ideal.Maximum_Heating_Supply_Air_Temperature = max_heat_temp
        ideal.Minimum_Cooling_Supply_Air_Temperature = min_cool_temp

        # Supply air humidity limits (optional, can be autosized or fixed)
        # ideal.Maximum_Heating_Supply_Air_Humidity_Ratio = 0.0156 # Example
        # ideal.Minimum_Cooling_Supply_Air_Humidity_Ratio = 0.0077 # Example

        # Heating/Cooling capacity limits
        ideal.Heating_Limit = "LimitFlowRateAndCapacity" # Or NoLimit, LimitCapacity, LimitFlowRate
        ideal.Maximum_Heating_Air_Flow_Rate = "Autosize"
        ideal.Maximum_Sensible_Heating_Capacity = "Autosize"

        ideal.Cooling_Limit = "LimitFlowRateAndCapacity"
        ideal.Maximum_Cooling_Air_Flow_Rate = "Autosize"
        ideal.Maximum_Total_Cooling_Capacity = "Autosize"

        # Optional: Dehumidification/Humidification Control
        ideal.Dehumidification_Control_Type = "None" # Or None, Humidistat, etc.
        # ideal.Cooling_Sensible_Heat_Ratio = 0.7 # Example if needed
        ideal.Humidification_Control_Type = "None" # Or None, Humidistat
        # ideal.Design_Specification_Outdoor_Air_Object_Name = "" # Can link DSOA if needed

        # Optional: Economizer / Heat Recovery
        # EnergyPlus 22.x does not accept "FixedDryBulb" for this field
        # (valid options are NoEconomizer, DifferentialDryBulb,
        #  DifferentialEnthalpy). Use NoEconomizer for compatibility.
        ideal.Outdoor_Air_Economizer_Type = "NoEconomizer"
        if hasattr(ideal, "Economizer_Maximum_Limit_Dry_Bulb_Temperature"):
            ideal.Economizer_Maximum_Limit_Dry_Bulb_Temperature = 18  # DegC
        else:
            print(
                f"[Custom HVAC Warning] IdealLoads object '{ideal.Name}' does not "
                "support 'Economizer_Maximum_Limit_Dry_Bulb_Temperature'."
            )
        ideal.Heat_Recovery_Type = "None"


        # 6f) Ensure NODELIST for supply inlets exists
        inlet_nl = idf.getobject("NODELIST", inlet_nodelist_name.upper())
        if not inlet_nl:
            inlet_nl = idf.newidfobject("NODELIST")
            inlet_nl.Name = inlet_nodelist_name
        # Ensure it points to the correct node(s)
        inlet_nl.Node_1_Name = inlet_node_name
        # Clear other nodes if necessary
        # inlet_nl.Node_2_Name = ""


        # 6g) Log zone-level info if requested
        if assigned_hvac_log is not None:
            # Ensure zone entry exists
            if zone_name not in assigned_hvac_log[bldg_id]["zones"]:
                assigned_hvac_log[bldg_id]["zones"][zone_name] = {}
            # Update with HVAC details for this zone
            assigned_hvac_log[bldg_id]["zones"][zone_name].update({
                "hvac_object_name": ideal_loads_name,
                "hvac_object_type": "ZONEHVAC:IDEALLOADSAIRSYSTEM",
                "availability_schedule": hvac_avail_sched_name,
                "thermostat_name": thermostat_name,
                "thermostat_dualsetpoint_name": dual_setpoint_name,
                "heating_setpoint_schedule": setpoint_sched_heat_name,
                "cooling_setpoint_schedule": setpoint_sched_cool_name,
            })

    # --- Final Logging ---
    print(f"[Custom HVAC Info] Completed Ideal Loads HVAC setup for all zones in building {bldg_id}.")

# Example usage (if run standalone for testing):
# if __name__ == '__main__':
#     from eppy.modeleditor import IDF
#     # Load a base IDF file
#     try:
#         idf = IDF("path/to/your/base_model.idf")
#     except FileNotFoundError:
#         print("Error: Base IDF file not found for testing.")
#         exit()
#
#     # Example building metadata
#     test_building_row = {
#         "ogc_fid": 999,
#         "building_function": "residential",
#         "residential_type": "Corner House", # Match a key in hvac_lookup
#         "age_range": "2015 and later",      # Match a key in hvac_lookup
#         "scenario": "scenario1"
#     }
#
#     # Example empty log dict
#     test_log = {}
#
#     # Call the function
#     add_HVAC_Ideal_to_all_zones(
#         idf,
#         building_row=test_building_row,
#         assigned_hvac_log=test_log
#         # Add other parameters as needed for test
#     )
#
#     # Save the modified IDF
#     idf.saveas("path/to/your/output_model_with_hvac.idf")
#     print("Saved modified IDF with Ideal Loads.")
#     # print("Log:", test_log) # Inspect the log if desired