# setzone/define_global_design_specs.py

def define_global_design_specs(idf):
    """
    Creates/updates a single DESIGNSPECIFICATION:OUTDOORAIR (DSOA_Global)
    and a single DESIGNSPECIFICATION:ZONEAIRDISTRIBUTION (DSZAD_Global)
    for the entire building.
    """

    # 1) DSOA_Global
    dsoa = idf.getobject("DESIGNSPECIFICATION:OUTDOORAIR", "DSOA_Global")
    if not dsoa:
        dsoa = idf.newidfobject("DESIGNSPECIFICATION:OUTDOORAIR")
        dsoa.Name = "DSOA_Global"

    # Example static or user-defined values:
    dsoa.Outdoor_Air_Method = "Sum"
    dsoa.Outdoor_Air_Flow_per_Person = 0.00236
    dsoa.Outdoor_Air_Flow_per_Zone_Floor_Area = 0.000305
    # Optional: dsoa.Outdoor_Air_Flow_per_Zone = ...
    # etc.

    # 2) DSZAD_Global
    dszad = idf.getobject("DESIGNSPECIFICATION:ZONEAIRDISTRIBUTION", "DSZAD_Global")
    if not dszad:
        dszad = idf.newidfobject("DESIGNSPECIFICATION:ZONEAIRDISTRIBUTION")
        dszad.Name = "DSZAD_Global"

    dszad.Zone_Air_Distribution_Effectiveness_in_Cooling_Mode = 1.0
    dszad.Zone_Air_Distribution_Effectiveness_in_Heating_Mode = 1.0
    dszad.Zone_Secondary_Recirculation_Fraction = 0.3

    return dsoa, dszad
