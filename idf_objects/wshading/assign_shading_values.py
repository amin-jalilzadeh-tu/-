"""
assign_shading_values.py

This module picks the final shading parameters from shading_lookup.py
and optionally user overrides or Excel-based rules. The actual creation
of EnergyPlus objects (e.g. WindowMaterial:Blind, Shading:Building:Detailed, etc.)
will happen in another file (e.g. create_shading_objects.py).
"""

import random
import logging
from .shading_lookup import shading_lookup # Assuming shading_lookup.py is in the same directory

logger = logging.getLogger(__name__)

def pick_val_from_range(rng_tuple, strategy="A"):
    """
    Helper function to pick a numeric value from a (min_val, max_val) tuple.

    - If strategy="A", picks the midpoint.
    - If strategy="B", picks a random value in [min_val, max_val].
    - Otherwise (e.g., strategy="C" or any other string), picks min_val.

    Parameters
    ----------
    rng_tuple : tuple or None
        A tuple of two numeric values (min_val, max_val) or None.
        If None or not a 2-element tuple, returns None.
        If min_val or max_val is None, attempts to return the non-None value,
        or None if both are None.
    strategy : str, optional
        The strategy to use for picking the value ("A", "B", or other).
        Defaults to "A".

    Returns
    -------
    float or int or None
        The picked numeric value, or None if input is invalid or values are missing.
    """
    if not rng_tuple or not isinstance(rng_tuple, tuple) or len(rng_tuple) != 2:
        if rng_tuple is not None: # Log if it's not None but still invalid
             logger.warning(f"Invalid rng_tuple: {rng_tuple}. Expected a 2-element tuple or None.")
        return None

    min_val, max_val = rng_tuple

    if min_val is None and max_val is None:
        return None
    if min_val is None:
        return max_val # Return max_val if min_val is None
    if max_val is None:
        return min_val # Return min_val if max_val is None

    # Ensure min_val and max_val are numbers if they are not None
    if not all(isinstance(v, (int, float)) for v in [min_val, max_val] if v is not None):
        logger.warning(f"Non-numeric values in rng_tuple: {rng_tuple}. Cannot pick value.")
        return None # Or handle as per specific logic, e.g., return first valid number

    if min_val == max_val:
        return min_val  # No variability

    if min_val > max_val:
        logger.warning(
            f"min_val ({min_val}) is greater than max_val ({max_val}) in range tuple. "
            f"Swapping them for strategy 'A'. For strategy 'B', this might lead to issues if not handled by random.uniform."
        )
        # For midpoint, swapping is fine. For random, random.uniform might error or behave unexpectedly.
        # Python's random.uniform(a,b) requires a <= b.
        if strategy == "B":
            # To be safe, either swap, or return min_val, or log and let it potentially error
            # Choosing to swap for random.uniform to ensure it works:
            min_val, max_val = max_val, min_val


    if strategy == "A":
        return 0.5 * (min_val + max_val)
    elif strategy == "B":
        return random.uniform(min_val, max_val)
    else: # Default or other strategies pick min_val
        return min_val

def pick_shading_params(
    window_id, # Retained for logging, though not strictly used for parameter picking logic here
    shading_type_key="my_external_louvers",
    strategy="A",
    user_config=None,
    assigned_shading_log=None
):
    """
    1) Looks up default shading parameters from shading_lookup[shading_type_key].
    2) If user_config is provided, overrides or adjusts some values. The user_config
       is expected to be a dictionary where keys are parameter names (e.g.,
       "slat_angle_deg_range") and values are the new values or new ranges.
       This `user_config` should be specific to the `shading_type_key` being processed.
    3) Based on 'strategy', picks final numeric values (midpoint, random, or min)
       from any ranges in these parameters.
    4) Optionally logs the final picks in assigned_shading_log.

    Parameters
    ----------
    window_id : str
        An identifier for the window (primarily for logging purposes).
    shading_type_key : str
        The key in shading_lookup to use, e.g., "my_external_louvers".
    strategy : str
        "A" => pick midpoint from ranges; "B" => pick random.
        Otherwise => pick min_val from ranges.
    user_config : dict or None
        A dictionary of overrides specific to this `shading_type_key`.
        E.g., { "slat_angle_deg_range": (30, 60), "slat_width": 0.05 }.
        This dict directly contains parameter names and their override values.
    assigned_shading_log : dict or None
        If provided, store final picks under assigned_shading_log[window_id].

    Returns
    -------
    dict
        A dictionary of final shading parameters with single numeric values, e.g.:
        {
          "blind_name": "MyExternalLouvers",
          "slat_orientation": "Horizontal",
          "slat_width": 0.025,
          "slat_angle_deg": 45.0,
          ...
        }
        Returns an empty dictionary if base_params for shading_type_key are not found.
    """
    base_params = shading_lookup.get(shading_type_key)
    if not base_params:
        logger.error(f"Shading type key '{shading_type_key}' not found in shading_lookup.")
        if assigned_shading_log is not None and window_id is not None:
            if window_id not in assigned_shading_log:
                assigned_shading_log[window_id] = {}
            assigned_shading_log[window_id]["shading_params_error"] = f"Key '{shading_type_key}' not in lookup."
        return {}

    # Start with a deepcopy if base_params might contain nested mutable structures,
    # though for typical shading_lookup, shallow copy is often sufficient.
    # Using shallow copy as per original, assuming values are simple types or tuples.
    final_params = dict(base_params)

    # 2) Apply user overrides
    # user_config here is already the specific set of overrides for this shading_type_key.
    if user_config and isinstance(user_config, dict):
        for key, override_val in user_config.items():
            # If the override_val is a tuple and the original key also ended with _range
            # (or if the new key ends with _range), it's likely an override for a range.
            # Otherwise, it's a direct value replacement or a new parameter.
            final_params[key] = override_val
            # Log if an existing parameter is being overridden
            # if key in base_params:
            # logger.debug(f"For {shading_type_key}, '{key}' overridden from '{base_params[key]}' to '{override_val}'")
            # else:
            # logger.debug(f"For {shading_type_key}, new param '{key}' added with value '{override_val}'")


    # 3) Convert all "*_range" fields to single numeric picks
    #    Also convert any single values that were specified as ranges in lookup/override.
    processed_params = {}
    params_to_remove_range_suffix = []

    for field_key, field_val in list(final_params.items()):
        if field_key.endswith("_range"):
            param_name_base = field_key[:-6]  # remove "_range"
            if isinstance(field_val, tuple): # It's a range, pick a value
                chosen_val = pick_val_from_range(field_val, strategy=strategy)
                if chosen_val is not None:
                    processed_params[param_name_base] = chosen_val
                else:
                    logger.warning(f"Could not pick value for '{field_key}' with value {field_val} for {shading_type_key}. Parameter '{param_name_base}' will be missing.")
                params_to_remove_range_suffix.append(field_key)
            else: # It ends with _range but isn't a tuple, treat as direct value for param_name_base
                logger.warning(f"Field '{field_key}' for {shading_type_key} ends with '_range' but is not a tuple: {field_val}. Using value directly for '{param_name_base}'.")
                processed_params[param_name_base] = field_val
                params_to_remove_range_suffix.append(field_key)
        else:
            # If field_val is a tuple (e.g. from an override that set a non-range field to a tuple)
            # AND it's meant to be a range that needs picking (e.g. user_config provided ("width": (0.1,0.2))
            # then pick_val_from_range should be used.
            # Current logic assumes explicit *_range suffix for picking.
            # If a non-range parameter is overridden with a tuple, it stays a tuple unless handled elsewhere.
            # For simplicity, we only act on *_range keys here.
            # Non-range parameters are kept as is.
            processed_params[field_key] = field_val

    # Clean up the original *_range keys from final_params if they were processed
    for key_to_remove in params_to_remove_range_suffix:
        if key_to_remove in final_params : # It might have been overwritten by a direct key (param_name_base) already
            final_params.pop(key_to_remove, None)


    # Update final_params with the processed (picked) values
    final_params.update(processed_params)


    # 4) Log if needed
    if assigned_shading_log is not None and window_id is not None:
        if window_id not in assigned_shading_log:
            assigned_shading_log[window_id] = {}
        # Store a copy to avoid external modification if final_params is mutable and reused.
        assigned_shading_log[window_id]["shading_params"] = dict(final_params)

    return final_params