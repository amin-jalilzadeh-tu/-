# setzone/assign_zone_sizing_values.py

import random
from .zone_sizing_lookup import zone_sizing_lookup

def assign_zone_sizing_params(
    building_function: str,
    calibration_stage="pre_calibration",
    strategy="A",
    random_seed=None
):
    """
    Returns a dict of final zone sizing parameters 
    by picking from the pre/post calibration range for the building function.
    strategy: 
      - "A" => midpoint 
      - "B" => random uniform 
      - (others) => min
    """
    if random_seed is not None:
        random.seed(random_seed)

    # Fallback if not found
    if calibration_stage not in zone_sizing_lookup:
        calibration_stage = "pre_calibration"
    if building_function not in zone_sizing_lookup[calibration_stage]:
        building_function = "residential"

    data = zone_sizing_lookup[calibration_stage][building_function]

    def pick_val(rng):
        if rng[0] == rng[1]:
            return rng[0]  # fixed
        if strategy == "A":
            # midpoint
            return (rng[0] + rng[1]) / 2.0
        elif strategy == "B":
            # random
            return random.uniform(rng[0], rng[1])
        else:
            # fallback => pick min
            return rng[0]

    assigned = {}
    assigned["cooling_supply_air_temp"] = pick_val(data["cooling_supply_air_temp_range"])
    assigned["heating_supply_air_temp"] = pick_val(data["heating_supply_air_temp_range"])
    assigned["cooling_supply_air_hr"]   = pick_val(data["cooling_supply_air_hr_range"])
    assigned["heating_supply_air_hr"]   = pick_val(data["heating_supply_air_hr_range"])

    # for design air flow method, no range => just a string
    assigned["cooling_design_air_flow_method"] = data["cooling_design_air_flow_method"]
    assigned["heating_design_air_flow_method"] = data["heating_design_air_flow_method"]

    return assigned
