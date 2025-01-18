# tempground/add_ground_temperatures.py

from .assign_groundtemp_values import assign_ground_temperatures

def add_ground_temperatures(
    idf,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None,
    assigned_groundtemp_log=None  # <--- new for logging
):
    """
    1) Removes existing SITE:GROUNDTEMPERATURE:BUILDINGSURFACE objects
    2) Assigns new monthly temps from assign_ground_temperatures
    3) Optionally logs them into assigned_groundtemp_log if provided
    """

    # Remove existing ground temperature objects
    existing_ground_temps = idf.idfobjects["SITE:GROUNDTEMPERATURE:BUILDINGSURFACE"]
    for temp in existing_ground_temps[:]:
        idf.removeidfobject(temp)

    # 1) Assign new monthly temps
    final_temps = assign_ground_temperatures(
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed
    )

    # 2) Create new object
    ground_obj = idf.newidfobject("SITE:GROUNDTEMPERATURE:BUILDINGSURFACE")
    ground_obj.January_Ground_Temperature   = final_temps["January"]
    ground_obj.February_Ground_Temperature  = final_temps["February"]
    ground_obj.March_Ground_Temperature     = final_temps["March"]
    ground_obj.April_Ground_Temperature     = final_temps["April"]
    ground_obj.May_Ground_Temperature       = final_temps["May"]
    ground_obj.June_Ground_Temperature      = final_temps["June"]
    ground_obj.July_Ground_Temperature      = final_temps["July"]
    ground_obj.August_Ground_Temperature    = final_temps["August"]
    ground_obj.September_Ground_Temperature = final_temps["September"]
    ground_obj.October_Ground_Temperature   = final_temps["October"]
    ground_obj.November_Ground_Temperature  = final_temps["November"]
    ground_obj.December_Ground_Temperature  = final_temps["December"]

    print("[GROUND TEMPS] Created SITE:GROUNDTEMPERATURE:BUILDINGSURFACE with monthly values:", final_temps)

    # 3) Log assigned if desired
    if assigned_groundtemp_log is not None:
        # If you have a building_id, pass it in; or store just one global set.
        # For now, we do a single “global” entry, e.g. assigned_groundtemp_log["global"] = final_temps
        assigned_groundtemp_log["ground_temperatures"] = final_temps

    return ground_obj
