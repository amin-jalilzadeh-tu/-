# ventilation/schedule_lookup.py

"""
This file defines SCHEDULE_LOOKUP, a dictionary organizing realistic, ranged
schedule patterns for building archetypes, suitable for energy modeling.

Rationale for Improvement:
1.  More Detailed Time Slices: Schedules are broken down into more granular periods,
    including morning/evening peaks, daytime setbacks, lunch breaks, and janitorial
    hours to better capture building dynamics.
2.  Logic-Driven Ranges: The (min, max) value ranges are not arbitrary.
    - A low minimum (e.g., 0.0-0.1) during unoccupied hours reflects Demand-Controlled
      Ventilation (DCV) providing minimal background airflow.
    - A tight, high range (e.g., 0.95-1.0) during peak occupancy represents the
      system running at full design capacity.
    - Broader ranges during shoulder periods represent operational uncertainty.
3.  Clearer Ventilation vs. Infiltration Logic:
    - Ventilation (Mechanical): This schedule is a proxy for occupancy and internal
      loads. It is significantly reduced or turned off when the building is empty.
    - Infiltration (Natural): This schedule represents the 'availability' of leakage
      paths. For non-residential buildings, it is modeled as being higher when the
      mechanical ventilation is off (no pressurization) and lower during operational
      hours. For residential buildings, it remains high, proxying for occupant presence
      and window-opening behavior.

Structure:
SCHEDULE_LOOKUP[building_function][archetype_key][purpose][day_type]
"""

SCHEDULE_LOOKUP = {
    # =====================================================================
    # Residential Building Schedules
    # =====================================================================
    "residential": {
        "default": {  # Fallback: A typical family home pattern
            "ventilation": {
                # Weekday: People leave for work/school.
                "weekday": [(0, 6, (0.30, 0.50)),    # Night setback
                            (6, 9, (0.80, 1.00)),    # Morning peak (showers, breakfast)
                            (9, 16, (0.40, 0.60)),   # Daytime low (unoccupied/less active)
                            (16, 22, (0.90, 1.00)),  # Evening peak (cooking, activity)
                            (22, 24, (0.30, 0.50))], # Night setback
                # Weekend: People are home more often and activity is spread out.
                "weekend": [(0, 8, (0.40, 0.60)),    # Later night setback
                            (8, 23, (0.85, 1.00)),   # Broad, high daytime activity
                            (23, 24, (0.40, 0.60))], # Night setback
            },
            "infiltration": {
                # Potential for infiltration and window opening is always high when occupied.
                "allday": [(0, 24, (0.90, 1.00))],
            }
        },
        "Apartment": { # Often smaller, with quicker temperature/air quality changes.
            "ventilation": {
                "weekday": [(0, 6, (0.25, 0.40)), (6, 9, (0.85, 1.00)), (9, 17, (0.30, 0.50)), (17, 23, (0.95, 1.00)), (23, 24, (0.25, 0.40))],
                "weekend": [(0, 8, (0.40, 0.60)), (8, 23, (0.90, 1.00)), (23, 24, (0.40, 0.60))],
            },
            "infiltration": {
                "allday": [(0, 24, (0.90, 1.00))],
            }
        },
    },

    # =====================================================================
    # Non-Residential Building Schedules
    # =====================================================================
    "non_residential": {
        "default": {  # Fallback: Generic 9-5 Office.
            "ventilation": {
                "weekday": [(0, 7, (0.00, 0.10)), (7, 18, (0.90, 1.00)), (18, 24, (0.00, 0.10))],
                "weekend": [(0, 24, (0.00, 0.05))],
            },
            "infiltration": {
                "weekday": [(0, 7, (0.80, 1.00)), (7, 18, (0.30, 0.50)), (18, 24, (0.80, 1.00))],
                "weekend": [(0, 24, (0.90, 1.00))]
            }
        },
        "Office Function": {
            "ventilation": {
                "weekday": [(0, 7, (0.05, 0.15)),    # Night/unoccupied DCV rate
                            (7, 9, (0.95, 1.00)),    # Morning arrival peak
                            (9, 12, (0.90, 1.00)),   # Core morning work
                            (12, 14, (0.70, 0.85)),  # Lunch period dip
                            (14, 17, (0.90, 1.00)),  # Core afternoon work
                            (17, 18, (0.60, 0.80)),  # People leaving
                            (18, 20, (0.20, 0.30)),  # Cleaning crew period
                            (20, 24, (0.05, 0.15))], # Unoccupied
                "weekend": [(0, 24, (0.00, 0.10))],  # Weekend (minimal/off)
            },
            "infiltration": {
                "weekday": [(0, 7, (0.80, 1.00)), (7, 18, (0.25, 0.45)), (18, 24, (0.80, 1.00))], # Suppressed by HVAC pressure during day
                "weekend": [(0, 24, (0.90, 1.00))],
            }
        },
        "Retail Function": { # Assumes a store in a shopping street or mall
            "ventilation": {
                "weekday": [(0, 8, (0.05, 0.10)),    # Pre-opening
                            (8, 10, (0.70, 0.90)),   # Opening/stocking
                            (10, 19, (0.95, 1.00)),  # Peak customer hours
                            (19, 21, (0.40, 0.60)),  # Closing/cleaning
                            (21, 24, (0.05, 0.10))], # Closed
                "weekend": [(0, 9, (0.05, 0.15)),    # Saturday/Sunday opening prep
                            (9, 18, (0.95, 1.00)),   # Peak weekend customers
                            (18, 20, (0.40, 0.60)),  # Closing
                            (20, 24, (0.05, 0.15))], # Closed
            },
            "infiltration": { # Dominated by door openings
                "weekday": [(0, 9, (0.40, 0.60)), (9, 20, (0.80, 1.00)), (20, 24, (0.40, 0.60))],
                "weekend": [(0, 9, (0.40, 0.60)), (9, 19, (0.90, 1.00)), (19, 24, (0.40, 0.60))],
            }
        },
        "Education Function": { # School
            "ventilation": {
                "weekday": [(0, 7, (0.00, 0.10)),    # Unoccupied
                            (7, 12, (0.95, 1.00)),   # Morning classes
                            (12, 13, (0.50, 0.70)),  # Lunch break (less classroom occupancy)
                            (13, 16, (0.95, 1.00)),  # Afternoon classes
                            (16, 18, (0.30, 0.50)),  # After-school care / activities
                            (18, 24, (0.00, 0.10))], # Closed
                "weekend": [(0, 24, (0.00, 0.05))],  # No regular activity
            },
            "infiltration": {
                "weekday": [(0, 7, (0.70, 0.90)), (7, 17, (0.40, 0.60)), (17, 24, (0.70, 0.90))],
                "weekend": [(0, 24, (0.80, 1.00))],
            }
        },
        "Healthcare Function": { # Hospital (24/7 operation)
            "ventilation": {
                # High minimum rates required at all times.
                "allday": [(0, 7, (0.65, 0.80)),    # Night (lower activity, but still high demand)
                           (7, 21, (0.90, 1.00)),   # Daytime (procedures, visitors)
                           (21, 24, (0.65, 0.80))], # Evening/early night
            },
            "infiltration": {
                # Often pressurized; infiltration is minimized and controlled.
                "allday": [(0, 24, (0.10, 0.25))]
            }
        },
        "Accommodation Function": { # Hotel
             "ventilation": {
                "allday": [(0, 6, (0.50, 0.70)),    # Night (occupied rooms)
                           (6, 10, (0.85, 1.00)),   # Morning checkout/breakfast peak
                           (10, 16, (0.40, 0.60)),  # Mid-day low (guests out, cleaning)
                           (16, 24, (0.90, 1.00))], # Evening check-in / guests returning
            },
            "infiltration": {
                "allday": [(0, 24, (0.60, 0.80))] # Higher quality construction than average residential
            }
        },
    }
}