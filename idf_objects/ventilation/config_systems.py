# ventilation/config_systems.py

"""
Defines SYSTEMS_CONFIG: a dictionary organizing ventilation system properties.

Structure:
  SYSTEMS_CONFIG[building_function][system_type]

Each system entry contains:
  - description: Short text label.
  - ventilation_object_type: The primary EnergyPlus object used for this system's
      ventilation component (e.g., 'ZONEVENTILATION:DESIGNFLOWRATE' or
      'ZONEHVAC:IDEALLOADSAIRSYSTEM').
  - ventilation_type_options: List of allowed values for the 'Ventilation Type'
      field if using ZONEVENTILATION:DESIGNFLOWRATE.
  - range_params: Dictionary holding (min, max) tuples for parameters that can vary
      (e.g., fan efficiency, HRV effectiveness). Final values are picked later.
  - fixed_params: Dictionary holding fixed values for parameters specific to this
      system type (e.g., Heat Recovery Type for System D).
  - use_ideal_loads: Boolean, True if System D uses IdealLoads for ventilation.

This config informs `create_ventilation_systems.py` how to build the IDF objects.
"""

SYSTEMS_CONFIG = {
    "residential": {
        # -----------------------------------------------------------
        # System A: Natural Ventilation (Natural Supply + Natural Exhaust/Infiltration)
        # -----------------------------------------------------------
        "A": {
            "description": "Natural supply + Natural exhaust/infiltration",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE", # Models natural ventilation openings
            "ventilation_type_options": ["Natural"], # Requires temp/wind difference driven by E+
            "range_params": {
                # Fan parameters are irrelevant for purely Natural Ventilation_Type
                "Fan_Pressure_Rise": (0.0, 0.0),
                "Fan_Total_Efficiency": (1.0, 1.0), # Set to 1 to avoid division by zero if used
            },
            "fixed_params": {
                 # No specific fixed params needed for ZONEVENTILATION with Natural type
            },
            "use_ideal_loads": False # Does not use IdealLoads for ventilation part
        },

        # -----------------------------------------------------------
        # System B: Mechanical Supply + Natural Exhaust/Infiltration
        # -----------------------------------------------------------
        "B": {
            "description": "Mechanical supply + Natural exhaust/infiltration",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE", # Models mechanical intake fan
            "ventilation_type_options": ["Intake"], # Represents supply fan
            "range_params": {
                "Fan_Pressure_Rise": (40.0, 60.0),   # Pa, typical for simple supply
                "Fan_Total_Efficiency": (0.65, 0.75) # Fan efficiency range
            },
             "fixed_params": {
                 # No specific fixed params needed for ZONEVENTILATION with Intake type
            },
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System C: Natural Supply/Infiltration + Mechanical Exhaust
        # -----------------------------------------------------------
        "C": {
            "description": "Natural supply/infiltration + Mechanical exhaust",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE", # Models mechanical exhaust fan
            "ventilation_type_options": ["Exhaust"], # Represents exhaust fan
            "range_params": {
                "Fan_Pressure_Rise": (40.0, 60.0),   # Pa, typical for simple exhaust
                "Fan_Total_Efficiency": (0.65, 0.75) # Fan efficiency range
            },
            "fixed_params": {
                 # No specific fixed params needed for ZONEVENTILATION with Exhaust type
            },
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System D: Balanced Mechanical (Supply + Exhaust) with HRV
        # Uses IdealLoadsAirSystem to represent this.
        # -----------------------------------------------------------
        "D": {
            "description": "Balanced mechanical (supply + exhaust), with HRV",
            # The ventilation *component* is handled by IdealLoads
            "ventilation_object_type": "ZONEHVAC:IDEALLOADSAIRSYSTEM",
            # These options aren't directly used by IdealLoads but represent the intent
            "ventilation_type_options": ["Balanced"],
            "range_params": {
                # Note: Fan power for IdealLoads is not directly calculated from these.
                # These might inform other calculations or checks if needed.
                # "Fan_Pressure_Rise": (50.0, 80.0), # Pa, typical for balanced system
                # "Fan_Total_Efficiency": (0.7, 0.85), # Fan efficiency range

                # HRV effectiveness ranges ARE used to set IdealLoads fields
                "Sensible_Heat_Recovery_Effectiveness": (0.70, 0.80),
                "Latent_Heat_Recovery_Effectiveness": (0.0, 0.0) # Assumed no latent recovery unless specified
            },
            "fixed_params": {
                 # These parameters MUST be set on the IdealLoads object for System D ventilation
                 "Design_Specification_Outdoor_Air_Object_Name": None, # Placeholder - Name set dynamically
                 "Outdoor_Air_Economizer_Type": "NoEconomizer", # Typically no economizer for basic ventilation
                 "Heat_Recovery_Type": "Sensible" # Set based on effectiveness > 0 (can be dynamic later)
                 # Add "Demand_Controlled_Ventilation_Type": "None" if needed
            },
            "use_ideal_loads": True # Confirms IdealLoads handles ventilation
        }
    }, # End residential

    "non_residential": {
        # -----------------------------------------------------------
        # System A: Natural Ventilation
        # -----------------------------------------------------------
        "A": {
            "description": "Natural supply + Natural exhaust/infiltration",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE",
            "ventilation_type_options": ["Natural"],
            "range_params": {
                "Fan_Pressure_Rise": (0.0, 0.0),
                "Fan_Total_Efficiency": (1.0, 1.0),
            },
             "fixed_params": {},
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System B: Mechanical Supply
        # -----------------------------------------------------------
        "B": {
            "description": "Mechanical supply + Natural exhaust/infiltration",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE",
            "ventilation_type_options": ["Intake"],
            "range_params": {
                "Fan_Pressure_Rise": (90.0, 110.0),  # Pa, higher for non-res
                "Fan_Total_Efficiency": (0.65, 0.75)
            },
             "fixed_params": {},
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System C: Mechanical Exhaust
        # -----------------------------------------------------------
        "C": {
            "description": "Natural supply/infiltration + Mechanical exhaust",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE",
            "ventilation_type_options": ["Exhaust"],
            "range_params": {
                "Fan_Pressure_Rise": (140.0, 160.0), # Pa, higher for non-res exhaust
                "Fan_Total_Efficiency": (0.70, 0.80)
            },
            "fixed_params": {},
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System D: Balanced Mechanical (Supply + Exhaust) with HRV/Economizer
        # Uses IdealLoadsAirSystem.
        # -----------------------------------------------------------
        "D": {
            "description": "Balanced mechanical supply & exhaust (with optional HRV/Economizer)",
            "ventilation_object_type": "ZONEHVAC:IDEALLOADSAIRSYSTEM",
            "ventilation_type_options": ["Balanced"],
            "range_params": {
                # HRV effectiveness ranges ARE used to set IdealLoads fields
                "Sensible_Heat_Recovery_Effectiveness": (0.75, 0.85),
                "Latent_Heat_Recovery_Effectiveness": (0.0, 0.0) # Assumed no latent
                # Fan parameters might inform external calcs if needed
                # "Fan_Pressure_Rise": (100.0, 120.0),
                # "Fan_Total_Efficiency": (0.65, 0.80),
            },
             "fixed_params": {
                 # These parameters MUST be set on the IdealLoads object for System D ventilation
                 "Design_Specification_Outdoor_Air_Object_Name": None, # Placeholder - Name set dynamically
                 "Outdoor_Air_Economizer_Type": "NoEconomizer", # Could be changed based on logic elsewhere if desired
                 "Heat_Recovery_Type": "Sensible" # Default, adjust if latent eff > 0
            },
            "use_ideal_loads": True
        }
    } # End non_residential
} # End SYSTEMS_CONFIG