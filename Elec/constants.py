# Elec/constants.py

"""
Global constants or default fallback values for the lighting module.
These can be overridden by user configs or Excel-based overrides.
"""

# Default power density values (W/m²)
DEFAULT_LIGHTING_WM2 = 10.0
DEFAULT_PARASITIC_WM2 = 0.285

# Default burning hours if not found in the lookup
DEFAULT_TD = 2000
DEFAULT_TN = 300

# Optional: If you want fraction parameter defaults here
# (instead of defining them in the fallback block of assign_lighting_values.py),
# you can do so, e.g.:
DEFAULT_LIGHTS_FRACTION_RADIANT = 0.7
DEFAULT_LIGHTS_FRACTION_VISIBLE = 0.2
DEFAULT_LIGHTS_FRACTION_REPLACEABLE = 1.0

DEFAULT_EQUIP_FRACTION_RADIANT = 0.0
DEFAULT_EQUIP_FRACTION_LOST = 1.0

# You can import & use these defaults in assign_lighting_values.py
# or wherever you handle fraction parameters.
