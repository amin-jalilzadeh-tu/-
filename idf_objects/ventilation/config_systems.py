# ventilation/config_systems.py

"""
Defines a dictionary SYSTEMS_CONFIG with separate entries for:
  - building_function: "residential" vs. "non_residential"
  - system_type:       "A", "B", "C", or "D"

Each system entry has:
  1) "description"                => short text label
  2) "ventilation_object_type"    => e.g. 'ZONEVENTILATION:DESIGNFLOWRATE'
  3) "ventilation_type_options"   => a list of possible Ventilation_Type strings
  4) "range_params"               => dictionary of numeric fields that are stored as (min, max) ranges
  5) "use_ideal_loads"            => boolean (True if system D uses IdealLoads, etc.)

Later, in your `create_ventilation_systems.py`, you can pick or compute final single values:
  - either pick a random or midpoint from "Fan_Pressure_Rise" range
  - or pick one of the "ventilation_type_options", etc.
"""

SYSTEMS_CONFIG = {
    "residential": {
        # -----------------------------------------------------------
        # System A
        # -----------------------------------------------------------
        "A": {
            "description": "Natural supply + Natural exhaust",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE",
            "ventilation_type_options": [
                "Natural"  # Could allow more, e.g. "Intake", "Exhaust" if you want
            ],
            "range_params": {
                # If you want a zero fan pressure for natural, but let's keep an example range
                "Fan_Pressure_Rise": (0.0, 0.0),
                "Fan_Total_Efficiency": (0.6, 0.8)
            },
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System B
        # -----------------------------------------------------------
        "B": {
            "description": "Mechanical supply + Natural infiltration",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE",
            "ventilation_type_options": [
                "Intake"
            ],
            "range_params": {
                "Fan_Pressure_Rise": (40.0, 60.0),
                "Fan_Total_Efficiency": (0.65, 0.75)
            },
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System C
        # -----------------------------------------------------------
        "C": {
            "description": "Natural supply + Mechanical exhaust",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE",
            "ventilation_type_options": [
                "Exhaust"
            ],
            "range_params": {
                "Fan_Pressure_Rise": (40.0, 60.0),
                "Fan_Total_Efficiency": (0.65, 0.75)
            },
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System D
        # -----------------------------------------------------------
        "D": {
            "description": "Balanced mechanical (supply + exhaust), with HRV",
            "ventilation_object_type": "ZONEHVAC:IDEALLOADSAIRSYSTEM",
            "ventilation_type_options": [
                "Balanced"
            ],
            "range_params": {
                "Fan_Pressure_Rise": (50.0, 80.0),
                "Fan_Total_Efficiency": (0.7, 0.85),
                # Example for HRV fields if you want them here:
                "Sensible_Heat_Recovery_Effectiveness": (0.70, 0.80),
                "Latent_Heat_Recovery_Effectiveness": (0.0, 0.0)
            },
            "use_ideal_loads": True
        }
    },

    "non_residential": {
        # -----------------------------------------------------------
        # System A
        # -----------------------------------------------------------
        "A": {
            "description": "Natural supply + Natural exhaust",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE",
            "ventilation_type_options": [
                "Natural"
            ],
            "range_params": {
                "Fan_Pressure_Rise": (0.0, 0.0),
                "Fan_Total_Efficiency": (0.5, 0.6)
            },
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System B
        # -----------------------------------------------------------
        "B": {
            "description": "Mechanical supply + Natural exhaust",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE",
            "ventilation_type_options": [
                "Intake"
            ],
            "range_params": {
                "Fan_Pressure_Rise": (90.0, 110.0),
                "Fan_Total_Efficiency": (0.65, 0.75)
            },
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System C
        # -----------------------------------------------------------
        "C": {
            "description": "Natural supply + Mechanical exhaust",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE",
            "ventilation_type_options": [
                "Exhaust"
            ],
            "range_params": {
                "Fan_Pressure_Rise": (140.0, 160.0),
                "Fan_Total_Efficiency": (0.70, 0.80)
            },
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System D
        # -----------------------------------------------------------
        "D": {
            "description": "Balanced mechanical supply & exhaust (with optional HRV)",
            "ventilation_object_type": "ZONEHVAC:IDEALLOADSAIRSYSTEM",
            "ventilation_type_options": [
                "Balanced"
            ],
            "range_params": {
                "Fan_Pressure_Rise": (100.0, 120.0),
                "Fan_Total_Efficiency": (0.65, 0.80),
                "Sensible_Heat_Recovery_Effectiveness": (0.75, 0.85),
                "Latent_Heat_Recovery_Effectiveness": (0.0, 0.0)
            },
            "use_ideal_loads": True
        }
    }
}
