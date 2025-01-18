# outputdef/output_lookup.py

output_lookup = {
    # Variables
    "variables": [
        {
            "variable_name": "Facility Total Electric Demand Power",
            "default_frequency": "Daily"
        },
        {
            "variable_name": "Facility Total Gas Demand Power",
            "default_frequency": "Daily"
        },
        {
            "variable_name": "Zone Air Temperature Maximum",
            "default_frequency": "Daily"
        },
        # etc...
    ],

    # Meters
    "meters": [
        {
            "key_name": "Fans:Electricity",
            "default_frequency": "Timestep"
        },
        {
            "key_name": "Electricity:Facility",
            "default_frequency": "Timestep"
        },
        {
            "key_name": "Electricity:Building",
            "default_frequency": "Timestep"
        },
        {
            "key_name": "Electricity:*",  # wildcard
            "default_frequency": "Timestep"
        },
        # etc...
    ],

    # Monthly/Annual Table Objects (e.g. OUTPUT:TABLE:MONTHLY)
    "tables": [
        {
            "object_type": "OUTPUT:TABLE:MONTHLY",
            "name": "Building Loads - Heating",
            "fields": {
                "Digits_After_Decimal": 2,
                "Variable_or_Meter_1_Name": "Zone Air System Sensible Heating Energy",
                "Aggregation_Type_for_Variable_or_Meter_1": "SumOrAverage",
                "Variable_or_Meter_2_Name": "Zone Air System Sensible Heating Rate",
                "Aggregation_Type_for_Variable_or_Meter_2": "Maximum",
                "Variable_or_Meter_3_Name": "Site Outdoor Air Drybulb Temperature",
                "Aggregation_Type_for_Variable_or_Meter_3": "ValueWhenMaximumOrMinimum"
            }
        },
        {
            "object_type": "OUTPUT:TABLE:MONTHLY",
            "name": "Building Loads - Cooling",
            "fields": {
                "Digits_After_Decimal": 2,
                "Variable_or_Meter_1_Name": "Zone Air System Sensible Cooling Energy",
                "Aggregation_Type_for_Variable_or_Meter_1": "SumOrAverage",
                "Variable_or_Meter_2_Name": "Zone Air System Sensible Cooling Rate",
                "Aggregation_Type_for_Variable_or_Meter_2": "Maximum",
                "Variable_or_Meter_3_Name": "Site Outdoor Air Drybulb Temperature",
                "Aggregation_Type_for_Variable_or_Meter_3": "ValueWhenMaximumOrMinimum"
            }
        }
    ],

    # Summary reports
    "summary_reports": [
        "AllSummary"  # or "AllSummaryAndSizingPeriod", etc.
    ]
}
