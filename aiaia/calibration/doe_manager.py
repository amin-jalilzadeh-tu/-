"""
doe_manager.py

This module defines how to build the initial parameter space
and generate sets of building configurations using various DOE methods.
"""

import itertools
import random
from typing import List, Dict, Union
import numpy as np
import pandas as pd

try:
    import pyDOE2  # If you want to use Latin Hypercube from pyDOE2
except ImportError:
    pyDOE2 = None


def define_parameter_space(building_type: str,
                           area: float,
                           age: int,
                           function_type: str,
                           user_overrides: Dict[str, Union[float, tuple]] = None
                           ) -> Dict[str, Dict[str, Union[float, tuple]]]:
    """
    Define the key parameters and their default ranges based on building metadata 
    (type, area, age, function). Optionally apply user overrides.

    :param building_type: e.g. "residential", "office", etc.
    :param area: building area (m²)
    :param age: approximate construction year
    :param function_type: e.g. "MeetingFunction", "Retail", ...
    :param user_overrides: a dictionary that can override any default range or value
    :return: A dictionary of parameters, each containing "min", "max", maybe "default"
             Example:
             {
               "infiltration_base": {"min": 0.5, "max": 1.5},
               "occupant_density": {"min": 10,  "max": 30},
               ...
             }
    """
    # Step 1: Start with a basic default ranges for your key calibration parameters.
    # These defaults might be derived from building codes or experience.
    param_space = {
        "infiltration_base": {"min": 0.5, "max": 1.5},  # ACH or m³/h/m² ...
        "occupant_density":  {"min": 8,   "max": 30},   # People per 100 m² ...
        "u_value_wall":      {"min": 0.3, "max": 1.0},  # W/m²K
        "lighting_power":    {"min": 5.0, "max": 15.0}, # W/m²
        # ... add as many as needed ...
    }

    # Step 2: Adjust ranges based on building metadata
    # For instance, if building is very old (pre-1980) => infiltration_base might be higher
    if age < 1980:
        param_space["infiltration_base"]["min"] = 1.0
        param_space["infiltration_base"]["max"] = 2.0
    
    # If function is "residential", occupant_density range might differ from "office"
    if building_type == "residential":
        param_space["occupant_density"]["min"] = 10
        param_space["occupant_density"]["max"] = 40

    # You can similarly adjust "u_value_wall" or other parameters for different building types
    # or areas, etc.

    # Step 3: Apply user overrides if provided
    if user_overrides:
        for pname, val in user_overrides.items():
            # If val is a tuple => interpret as (min, max)
            if isinstance(val, tuple) and len(val) == 2:
                param_space[pname] = {"min": val[0], "max": val[1]}
            # If val is a single float => just set min = max = val
            elif isinstance(val, (float, int)):
                param_space[pname] = {"min": val, "max": val}
            # Or any other logic you want for overrides

    return param_space


def generate_full_factorial(param_space: Dict[str, Dict[str, float]],
                            levels: int = 3) -> List[Dict[str, float]]:
    """
    Generate parameter combinations using a simple full factorial approach.
    Each parameter is discretized into `levels` points between [min, max].

    :param param_space: dict of {"param_name": {"min": float, "max": float}}
    :param levels: how many discrete points to use per parameter
    :return: a list of param_set dictionaries
    """
    # 1) For each parameter, build a list of discrete points
    param_points = {}
    for pname, bounds in param_space.items():
        pts = np.linspace(bounds["min"], bounds["max"], levels)
        param_points[pname] = pts

    # 2) Use itertools.product to create all combinations
    keys = list(param_points.keys())
    all_combos = []
    for combo in itertools.product(*(param_points[k] for k in keys)):
        param_set = {}
        for i, key in enumerate(keys):
            param_set[key] = combo[i]
        all_combos.append(param_set)

    return all_combos


def generate_random_sampling(param_space: Dict[str, Dict[str, float]],
                             n_samples: int = 10) -> List[Dict[str, float]]:
    """
    Generate parameter combinations using random uniform sampling within each [min, max].

    :param param_space: dict of {"param_name": {"min": float, "max": float}}
    :param n_samples: number of random points to generate
    :return: a list of param_set dictionaries
    """
    combos = []
    for _ in range(n_samples):
        param_set = {}
        for pname, bounds in param_space.items():
            val = random.uniform(bounds["min"], bounds["max"])
            param_set[pname] = val
        combos.append(param_set)
    return combos


def generate_latin_hypercube(param_space: Dict[str, Dict[str, float]],
                             n_samples: int = 10) -> List[Dict[str, float]]:
    """
    Use pyDOE2's Latin Hypercube method to sample parameter space.
    If pyDOE2 isn't installed, fallback to random.

    :param param_space: dict of {"param_name": {"min": float, "max": float}}
    :param n_samples: number of samples in the LHS
    :return: a list of param_set dictionaries
    """
    if not pyDOE2:
        print("[WARN] pyDOE2 not installed. Falling back to random sampling.")
        return generate_random_sampling(param_space, n_samples=n_samples)

    # 1) Number of parameters
    param_names = list(param_space.keys())
    dim = len(param_names)

    # 2) Generate LHS in [0,1]^dim
    lhs_matrix = pyDOE2.lhs(dim, samples=n_samples, criterion='center')

    # 3) Scale each dimension to the [min, max] for that param
    combos = []
    for i in range(n_samples):
        param_set = {}
        for j, pname in enumerate(param_names):
            bounds = param_space[pname]
            # Scale from [0,1] => [min, max]
            val = lhs_matrix[i, j] * (bounds["max"] - bounds["min"]) + bounds["min"]
            param_set[pname] = val
        combos.append(param_set)

    return combos


def generate_initial_configurations(building_type: str,
                                    area: float,
                                    age: int,
                                    function_type: str,
                                    method: str = "full_factorial",
                                    user_overrides: Dict[str, Union[float, tuple]] = None,
                                    levels_or_samples: int = 5
                                    ) -> List[Dict[str, float]]:
    """
    High-level function that:
      1. Defines parameter space
      2. Generates initial parameter combos using the chosen DOE method.

    :param building_type: e.g. "residential", "office", etc.
    :param area: building area (m²)
    :param age: building year
    :param function_type: e.g. "MeetingFunction", "Retail", ...
    :param method: one of ["full_factorial", "random", "lhs"]
    :param user_overrides: custom dictionary to override param ranges
    :param levels_or_samples: if method=="full_factorial", we use `levels`.
                              if method=="random"/"lhs", we use `n_samples`.
    :return: list of param_set dicts
    """
    # 1) Define default param space with logic for building metadata
    param_space = define_parameter_space(building_type, area, age, function_type, user_overrides)

    # 2) Based on method, generate combos
    if method == "full_factorial":
        combos = generate_full_factorial(param_space, levels=levels_or_samples)
    elif method == "random":
        combos = generate_random_sampling(param_space, n_samples=levels_or_samples)
    elif method == "lhs":
        combos = generate_latin_hypercube(param_space, n_samples=levels_or_samples)
    else:
        raise ValueError(f"Unknown DOE method: {method}")

    return combos


# ----------------------------------------------------------------------------
# Example usage:

if __name__ == "__main__":
    # Let's say we have a building from 1975, type "residential"
    building_type = "residential"
    area = 120.0
    age = 1975
    function_type = "SingleFamily"

    # We pass a user override dict for infiltration_base:
    overrides = {"infiltration_base": (1.2, 2.0)}  # override default range

    # Generate combos using full factorial with 3 levels
    config_sets = generate_initial_configurations(building_type, area, age, function_type,
                                                  method="full_factorial",
                                                  user_overrides=overrides,
                                                  levels_or_samples=3)

    print("[INFO] Full Factorial Config Count:", len(config_sets))
    for i, cset in enumerate(config_sets):
        print(f"Config #{i+1} -> {cset}")
    
    # Or random sampling of 5 combos:
    rnd_sets = generate_initial_configurations(building_type, area, age, function_type,
                                               method="random",
                                               user_overrides=overrides,
                                               levels_or_samples=5)
    print("\n[INFO] Random Config Count:", len(rnd_sets))
    for i, cset in enumerate(rnd_sets):
        print(f"Random #{i+1} -> {cset}")

    # If you have pyDOE2, try LHS
    lhs_sets = generate_initial_configurations(building_type, area, age, function_type,
                                               method="lhs",
                                               user_overrides=overrides,
                                               levels_or_samples=5)
    print("\n[INFO] LHS Config Count:", len(lhs_sets))
    for i, cset in enumerate(lhs_sets):
        print(f"LHS #{i+1} -> {cset}")
