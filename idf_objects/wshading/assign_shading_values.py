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

# Configure logger for this module
logger = logging.getLogger(__name__)
# Set a default logging level if no handlers are configured by the main application
# This prevents "No handler found" warnings and allows debug messages to be seen if
# the main app configures logging at DEBUG level for this logger or a parent.
if not logger.hasHandlers():
    # BasicConfig should ideally be called only once at the application entry point.
    # If called here, it might affect other modules' logging if they haven't set up their own.
    # For library code, it's often better to let the application configure logging.
    # However, for debugging during development, this can be helpful.
    # logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s')
    # A less intrusive way for a library module:
    # logger.addHandler(logging.NullHandler())
    # For active debugging, let's assume we want to see the messages if the root logger is set to DEBUG.
    pass


def pick_val_from_range(rng_tuple, strategy="A", param_name_for_log="<unknown_param>"):
    """
    Helper function to pick a numeric value from a (min_val, max_val) tuple.

    - If strategy="A", picks the midpoint.
    - If strategy="B", picks a random value in [min_val, max_val].
    - Otherwise (e.g., strategy="C" or any other string), picks min_val.

    Parameters
    ----------
    rng_tuple : tuple or None
        A tuple of two numeric values (min_val, max_val) or None.
    strategy : str, optional
        The strategy to use for picking the value ("A", "B", or other). Defaults to "A".
    param_name_for_log : str, optional
        Name of the parameter this range belongs to, for logging.

    Returns
    -------
    float or int or None
        The picked numeric value, or None if input is invalid or values are missing.
    """
    logger.debug(f"pick_val_from_range called for '{param_name_for_log}' with range: {rng_tuple}, strategy: '{strategy}'")

    if not rng_tuple or not isinstance(rng_tuple, tuple) or len(rng_tuple) != 2:
        if rng_tuple is not None:
             logger.warning(f"Invalid rng_tuple for '{param_name_for_log}': {rng_tuple}. Expected a 2-element tuple or None.")
        else:
             logger.debug(f"rng_tuple for '{param_name_for_log}' is None.")
        return None

    min_val, max_val = rng_tuple

    if min_val is None and max_val is None:
        logger.debug(f"Both min_val and max_val are None for '{param_name_for_log}'. Returning None.")
        return None
    if min_val is None:
        logger.debug(f"min_val is None for '{param_name_for_log}', returning max_val: {max_val}")
        return max_val
    if max_val is None:
        logger.debug(f"max_val is None for '{param_name_for_log}', returning min_val: {min_val}")
        return min_val

    if not all(isinstance(v, (int, float)) for v in [min_val, max_val]):
        logger.warning(f"Non-numeric values in rng_tuple for '{param_name_for_log}': {rng_tuple}. Cannot pick value.")
        return None

    chosen_value = None
    if min_val == max_val:
        chosen_value = min_val
        logger.debug(f"min_val equals max_val for '{param_name_for_log}'. Picked: {chosen_value}")
    elif min_val > max_val:
        logger.warning(
            f"For '{param_name_for_log}', min_val ({min_val}) is greater than max_val ({max_val}). "
            f"Using min_val ({min_val}) as the value, as random.uniform requires min <= max."
        )
        # Defaulting to min_val in this swapped case, or could swap them if strategy 'B' is critical.
        # For strategy 'A', midpoint would be calculated on swapped values.
        # For safety and predictability with strategy 'B', let's just pick min_val.
        chosen_value = min_val # Or swap: temp_min, temp_max = max_val, min_val
    else:
        if strategy == "A":
            chosen_value = 0.5 * (min_val + max_val)
            logger.debug(f"Strategy 'A' (midpoint) for '{param_name_for_log}'. Picked: {chosen_value}")
        elif strategy == "B":
            chosen_value = random.uniform(min_val, max_val)
            logger.debug(f"Strategy 'B' (random) for '{param_name_for_log}'. Picked: {chosen_value}")
        else: # Default or other strategies pick min_val
            chosen_value = min_val
            logger.debug(f"Strategy '{strategy}' (default/min_val) for '{param_name_for_log}'. Picked: {chosen_value}")
    
    return chosen_value

def pick_shading_params(
    window_id, 
    shading_type_key="my_external_louvers",
    strategy="A",
    user_config=None, # This should be specific to the shading_type_key
    assigned_shading_log=None
):
    """
    1) Looks up default shading parameters from shading_lookup[shading_type_key].
    2) If user_config is provided, overrides or adjusts some values.
    3) Based on 'strategy', picks final numeric values from any ranges.
    4) Optionally logs the final picks in assigned_shading_log.

    Parameters (same as before) ...

    Returns
    -------
    dict
        A dictionary of final shading parameters with single numeric values.
        Returns an empty dictionary if base_params for shading_type_key are not found.
    """
    logger.debug(f"pick_shading_params called for window_id: '{window_id}', shading_type_key: '{shading_type_key}', strategy: '{strategy}'")
    
    base_params = shading_lookup.get(shading_type_key)
    if not base_params:
        logger.error(f"Shading type key '{shading_type_key}' not found in shading_lookup.")
        if assigned_shading_log is not None and window_id is not None:
            if window_id not in assigned_shading_log:
                assigned_shading_log[window_id] = {}
            assigned_shading_log[window_id]["shading_params_error"] = f"Key '{shading_type_key}' not in lookup."
        return {}
    
    logger.debug(f"Base parameters for '{shading_type_key}' from lookup: {base_params}")

    # Start with a copy of base_params. Using dict() creates a shallow copy.
    final_params = dict(base_params)

    # 2) Apply user overrides
    if user_config and isinstance(user_config, dict):
        logger.debug(f"Applying user_config for '{shading_type_key}': {user_config}")
        for key, override_val in user_config.items():
            if key in final_params:
                logger.debug(f"  Overriding '{key}': from '{final_params[key]}' to '{override_val}'")
            else:
                logger.debug(f"  Adding new param '{key}' with value '{override_val}'")
            final_params[key] = override_val
    else:
        logger.debug(f"No user_config provided or it's not a dict for '{shading_type_key}'.")

    logger.debug(f"Parameters after applying user_config (before range picking) for '{shading_type_key}': {final_params}")

    # 3) Convert all "*_range" fields to single numeric picks
    #    Also, if a non-range field was overridden with a tuple by user_config,
    #    and we want to interpret that as a range to be picked, this logic needs to be robust.
    #    Current logic primarily acts on keys explicitly ending with "_range".
    
    processed_params = {} # Store picked values here
    # Iterate over a copy of keys if modifying the dictionary during iteration (though here we build a new one)
    
    for field_key in list(final_params.keys()): # list() for a stable copy of keys
        field_val = final_params[field_key]
        
        if field_key.endswith("_range"):
            param_name_base = field_key[:-6]  # remove "_range" suffix
            
            if isinstance(field_val, tuple): # It's a range, pick a value
                logger.debug(f"  Processing range field '{field_key}' with value {field_val}")
                chosen_val = pick_val_from_range(field_val, strategy=strategy, param_name_for_log=field_key)
                if chosen_val is not None:
                    processed_params[param_name_base] = chosen_val
                    logger.debug(f"    Picked value for '{param_name_base}': {chosen_val}")
                else:
                    # If pick_val_from_range returns None, param_name_base won't be in processed_params.
                    # This means it will be missing from the final output if not set otherwise.
                    logger.warning(f"    Could not pick value for '{field_key}' (value: {field_val}) for {shading_type_key}. Parameter '{param_name_base}' will be missing or use its non-range value if one exists.")
                
                # Remove the original _range key from final_params as we've processed it into processed_params
                # However, it's safer to build up processed_params and then update final_params,
                # or construct a completely new dictionary for the return.
                # Let's remove it from the original `final_params` copy to avoid confusion later.
                # final_params.pop(field_key, None) # This was modifying during iteration if not on list(final_params.keys())
            else: 
                # Field ends with _range but isn't a tuple (e.g., overridden by a single value)
                logger.warning(f"  Field '{field_key}' for {shading_type_key} ends with '_range' but is not a tuple: {field_val}. Using value directly for '{param_name_base}'.")
                processed_params[param_name_base] = field_val
                # final_params.pop(field_key, None)
        else:
            # This is a non-range key. Keep its value as is from final_params.
            # These will be merged with picked range values.
            # If a user overrode 'slat_width' with a tuple e.g. ("slat_width": (0.1,0.2))
            # and it's NOT slat_width_range, it would remain a tuple here.
            # The current design expects explicit _range suffix for picking.
            processed_params[field_key] = field_val
            logger.debug(f"  Keeping non-range field '{field_key}' with value: {field_val}")


    # The `processed_params` dictionary now contains all original non-range parameters
    # and the processed (picked) values for the range parameters.
    # This becomes the new `final_params`.
    final_params_picked = processed_params

    logger.debug(f"Final processed parameters for '{shading_type_key}' (after range picking): {final_params_picked}")

    # 4) Log if needed
    if assigned_shading_log is not None and window_id is not None:
        if window_id not in assigned_shading_log:
            assigned_shading_log[window_id] = {}
        # Store a copy of the final picked parameters
        assigned_shading_log[window_id]["shading_params_picked"] = dict(final_params_picked)
        assigned_shading_log[window_id]["shading_type_key_used"] = shading_type_key
        assigned_shading_log[window_id]["strategy_used"] = strategy
        logger.debug(f"Logged final picked parameters for window_id '{window_id}'")

    return final_params_picked
