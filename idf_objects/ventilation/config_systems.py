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
      (e.g., fan efficiency, HRV effectiveness). Final values are picked by
      create_ventilation_system.py using these ranges IF NOT OVERRIDDEN by
      parameters passed directly to that function.
  - fixed_params: Dictionary holding fixed values for parameters specific to this
      system type (e.g., Heat Recovery Type for System D, though this is also
      dynamically set in create_ventilation_system.py based on effectiveness).
  - use_ideal_loads: Boolean, True if System D uses IdealLoads for ventilation.

This config informs create_ventilation_systems.py how to build the IDF objects.
The parameters in 'range_params' act as DEFAULTS if more specific values
(e.g., from assign_ventilation_values.py) are not passed into create_ventilation_system.py.
"""

SYSTEMS_CONFIG = {
    "residential": {
        # -----------------------------------------------------------
        # System A: Natural Ventilation (Natural Supply + Natural Exhaust/Infiltration)
        # -----------------------------------------------------------
        "A": {
            "description": "Natural supply + Natural exhaust/infiltration",
            "ventilation_object_type": "ZONEVENTILATION:DESIGNFLOWRATE", # Models natural ventilation openings
            "ventilation_type_options": ["Natural"], # E+ calculates flow based on wind/temp diffs, modulated by schedule and design flow rate.
            "range_params": {
                # For "Natural" Ventilation_Type, Fan_Pressure_Rise and Fan_Total_Efficiency are ignored by E+.
                # Setting them to 0 and 1 respectively is good practice.
                "Fan_Pressure_Rise": (0.0, 0.0),    # Pa
                "Fan_Total_Efficiency": (1.0, 1.0), # Dimensionless (set to 1 to avoid potential div by zero if code tried to use it)
            },
            "fixed_params": {
                # No specific fixed params needed for ZONEVENTILATION with Natural type via this config.
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
                "Fan_Pressure_Rise": (40.0, 60.0),    # Pa, typical for simple residential supply
                "Fan_Total_Efficiency": (0.65, 0.75) # Default fan efficiency range if not overridden
            },
            "fixed_params": {
                # No specific fixed params needed for ZONEVENTILATION with Intake type here.
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
                "Fan_Pressure_Rise": (40.0, 60.0),    # Pa, typical for simple residential exhaust
                "Fan_Total_Efficiency": (0.65, 0.75) # Default fan efficiency range if not overridden
            },
            "fixed_params": {
                # No specific fixed params needed for ZONEVENTILATION with Exhaust type here.
            },
            "use_ideal_loads": False
        },

        # -----------------------------------------------------------
        # System D: Balanced Mechanical (Supply + Exhaust) with HRV
        # Uses IdealLoadsAirSystem to represent this.
        # HRV effectiveness is passed directly to create_ventilation_system,
        # so these range_params are fallbacks if that mechanism fails or isn't used.
        # -----------------------------------------------------------
        "D": {
            "description": "Balanced mechanical (supply + exhaust), with HRV",
            "ventilation_object_type": "ZONEHVAC:IDEALLOADSAIRSYSTEM", # Ventilation handled by IdealLoads
            "ventilation_type_options": ["Balanced"], # Not directly used by IdealLoads but indicates intent
            "range_params": {
                # Note: Fan power for IdealLoads is not directly set using these pressure/efficiency values.
                # IdealLoads system has its own way of meeting loads ideally.
                # These might inform SFP calculations if done externally.
                # "Fan_Pressure_Rise": (50.0, 80.0), # Pa, (Commented out as IdealLoads is different)
                # "Fan_Total_Efficiency": (0.7, 0.85), # (Commented out)

                # HRV effectiveness ranges defined here are DEFAULTS if specific values are not
                # passed into create_ventilation_system.py. The primary path for HRV effectiveness
                # is via assign_ventilation_values.py -> add_ventilation.py -> create_ventilation_system.py args.
                "Sensible_Heat_Recovery_Effectiveness": (0.70, 0.80),
                "Latent_Heat_Recovery_Effectiveness": (0.0, 0.0) # Default assumes no latent recovery for residential
            },
            "fixed_params": {
                # These parameters are typically set on the IdealLoads object for System D ventilation.
                # Design_Specification_Outdoor_Air_Object_Name is set dynamically in create_ventilation_system.
                "Outdoor_Air_Economizer_Type": "NoEconomizer", # Typically no economizer for basic residential HRV systems
                # Heat_Recovery_Type is set dynamically in create_ventilation_system based on actual effectiveness values.
                # "Heat_Recovery_Type": "Sensible" # Initial thought, but now dynamic
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
                "Fan_Pressure_Rise": (90.0, 110.0),  # Pa, typically higher for non-res supply
                "Fan_Total_Efficiency": (0.65, 0.75) # Default if not overridden
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
                "Fan_Pressure_Rise": (140.0, 160.0), # Pa, typically higher for non-res exhaust
                "Fan_Total_Efficiency": (0.70, 0.80)  # Default if not overridden
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
            "ventilation_type_options": ["Balanced"], # Intent indicator
            "range_params": {
                # Default HRV effectiveness ranges if not overridden by values passed to create_ventilation_system.
                "Sensible_Heat_Recovery_Effectiveness": (0.75, 0.85),
                "Latent_Heat_Recovery_Effectiveness": (0.0, 0.0) # Default assumes no latent for non-res, can be overridden
                # Fan parameters for IdealLoads are not used directly for E+ fan energy.
                # "Fan_Pressure_Rise": (100.0, 120.0),
                # "Fan_Total_Efficiency": (0.65, 0.80),
            },
            "fixed_params": {
                "Outdoor_Air_Economizer_Type": "NoEconomizer", # Default, could be made configurable or scenario-dependent
                # Heat_Recovery_Type is set dynamically in create_ventilation_system.
            },
            "use_ideal_loads": True
        }
    } # End non_residential
} # End SYSTEMS_CONFIG