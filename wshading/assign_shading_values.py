# wshading/assign_shading_values.py

"""
Similar to assign_geometry_values or assign_fenestration_values, 
this module picks the final shading parameters from shading_lookup.py 
and optionally user overrides or Excel-based rules.
"""

import random
from .shading_lookup import shading_lookup

def pick_val_from_range(rng_tuple, strategy="A"):
    """
    Helper function to pick a numeric value from (min_val, max_val).
    - If strategy="A", picks the midpoint.
    - If strategy="B", picks a random value in [min_val, max_val].
    - Otherwise, picks min_val.
    """
    if not rng_tuple or len(rng_tuple) < 2:
        return None
    min_val, max_val = rng_tuple
    if min_val is None or max_val is None:
        return min_val if min_val is not None else max_val  # fallback
    if min_val == max_val:
        return min_val  # no variability
    if strategy == "A":
        return 0.5 * (min_val + max_val)
    elif strategy == "B":
        return random.uniform(min_val, max_val)
    else:
        return min_val

def pick_shading_params(
    window_id,
    shading_type_key="my_external_louvers",
    strategy="A",
    user_config=None,
    assigned_shading_log=None
):
    """
    1) Looks up default shading parameters from shading_lookup[shading_type_key].
    2) If user_config is provided, override or adjust some values if needed.
    3) Based on 'strategy', pick final numeric values (midpoint or random) from any ranges.
    4) Optionally log the final picks in assigned_shading_log.

    Parameters
    ----------
    window_id : str
        An identifier for the window (optional, for logging).
    shading_type_key : str
        The key in shading_lookup to use, e.g. "my_external_louvers".
    strategy : str
        "A" => pick midpoint from ranges; "B" => pick random.
        Otherwise => pick min_val for everything.
    user_config : dict or None
        Optional. E.g. { "my_external_louvers": { "slat_angle_deg_range": (30, 60) } } 
        to override certain ranges for all windows or certain IDs.
    assigned_shading_log : dict or None
        If provided, store final picks under assigned_shading_log[window_id].

    Returns
    -------
    dict
        A dictionary of final shading parameters, e.g.:
        {
          "blind_name": "MyExternalLouvers",
          "slat_orientation": "Horizontal",
          "slat_width": 0.025,
          ... 
        }
    """
    # 1) Fetch base parameters from shading_lookup
    base_params = shading_lookup.get(shading_type_key, {})
    final_params = dict(base_params)  # shallow copy

    # 2) If user_config => update the base_params or override certain fields
    #    Example structure for user_config might be:
    #    {
    #      "my_external_louvers": {
    #         "slat_angle_deg_range": (30, 60),
    #         ...
    #      }
    #    }
    if user_config and shading_type_key in user_config:
        overrides_for_this_type = user_config[shading_type_key]
        for key, val in overrides_for_this_type.items():
            if key in final_params and isinstance(val, tuple) and len(val) == 2:
                # e.g. override "slat_angle_deg_range" => (30, 60)
                final_params[key] = val
            else:
                # you could also allow single fixed values or booleans
                final_params[key] = val

    # 3) Convert all "*_range" fields to single numeric picks
    #    e.g. final_params["slat_width_range"] => final_params["slat_width"]
    #    We'll store them as final_params["slat_width"], etc.
    #    Then remove the old range key from final_params.
    fields_to_remove = []
    for field_key, field_val in final_params.items():
        if field_key.endswith("_range") and isinstance(field_val, tuple):
            # e.g. "slat_width_range"
            # strip off "_range" => "slat_width"
            param_name = field_key[:-6]  # everything except "_range"
            chosen_val = pick_val_from_range(field_val, strategy=strategy)
            final_params[param_name] = chosen_val
            fields_to_remove.append(field_key)

    # Clean up the range-based keys
    for ftr in fields_to_remove:
        del final_params[ftr]

    # 4) If assigned_shading_log is provided, store the final chosen values
    #    e.g. assigned_shading_log[window_id]["shading_params"] = final_params
    if assigned_shading_log is not None and window_id is not None:
        if window_id not in assigned_shading_log:
            assigned_shading_log[window_id] = {}
        assigned_shading_log[window_id]["shading_params"] = final_params

    return final_params
