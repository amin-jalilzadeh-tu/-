# tempground/assign_groundtemp_values.py

import random
from .groundtemp_lookup import groundtemp_lookup

def assign_ground_temperatures(calibration_stage="pre_calibration", strategy="A", random_seed=None):
    if random_seed is not None:
        random.seed(random_seed)

    if calibration_stage not in groundtemp_lookup:
        calibration_stage = "pre_calibration"

    data = groundtemp_lookup[calibration_stage]

    def pick_val(rng):
        if rng[0] == rng[1]:
            return rng[0]
        if strategy == "A":
            return (rng[0] + rng[1]) / 2.0
        elif strategy == "B":
            return random.uniform(rng[0], rng[1])
        else:
            return rng[0]

    final_temps = {}
    final_temps["January"]   = pick_val(data["January"])
    final_temps["February"]  = pick_val(data["February"])
    final_temps["March"]     = pick_val(data["March"])
    final_temps["April"]     = pick_val(data["April"])
    final_temps["May"]       = pick_val(data["May"])
    final_temps["June"]      = pick_val(data["June"])
    final_temps["July"]      = pick_val(data["July"])
    final_temps["August"]    = pick_val(data["August"])
    final_temps["September"] = pick_val(data["September"])
    final_temps["October"]   = pick_val(data["October"])
    final_temps["November"]  = pick_val(data["November"])
    final_temps["December"]  = pick_val(data["December"])

    return final_temps
