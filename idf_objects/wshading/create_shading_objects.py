"""
create_shading_objects.py

This module creates EnergyPlus shading objects in the IDF
(e.g., WindowMaterial:Blind, WindowProperty:ShadingControl,
 Shading:Building:Detailed, schedules, etc.).

It calls pick_shading_params(...) from assign_shading_values.py
to get final numeric parameter values. You can pass user/Excel overrides
to customize these parameters.

Usage:
  from idf_objects.wshading.create_shading_objects import add_shading_objects

  add_shading_objects(
      idf=idf,
      building_row=some_dict,
      shading_type_key="my_external_louvers",
      strategy="B",
      random_seed=42,
      user_config_shading=shading_dict,
      assigned_shading_log=shading_log_dict
  )
"""

import random
from .assign_shading_values import pick_shading_params
# from geomeppy import IDF  # or from eppy.bunch_subclass import EpBunch, if you prefer eppy

def add_shading_objects(
    idf,
    building_row,
    shading_type_key="my_external_louvers",
    strategy="A",
    random_seed=42,
    user_config_shading=None,
    assigned_shading_log=None,
    create_blinds=True,
    create_geometry_shading=False
):
    """
    Creates the necessary shading objects in the IDF: e.g. WindowMaterial:Blind,
    WindowProperty:ShadingControl, or geometry-based Shading:Building:Detailed.

    1) Loops over fenestration surfaces (or just once, depending on logic).
    2) Calls pick_shading_params(...) to get final numeric values (slat angles, etc.).
    3) Creates an EnergyPlus shading device (WindowMaterial:Blind + ShadingControl).
    4) Optionally, create an E+ schedule if dynamic shading is needed.
    5) Optionally, create Shading:Building:Detailed geometry if requested.

    Parameters
    ----------
    idf : IDF
        The IDF object where new objects will be added.
    building_row : dict or pandas.Series
        Row of building data, if needed to pick orientation/area, etc.
    shading_type_key : str
        Key in shading_lookup, e.g. "my_external_louvers".
    strategy : str
        "A" => pick midpoint from param ranges; "B" => pick random, etc.
    random_seed : int
        For reproducibility if strategy="B".
    user_config_shading : dict or None
        Shading overrides to pass to pick_shading_params(...).
        E.g. {
          "my_external_louvers": {
              "slat_angle_deg_range": (30, 60),
              ...
          }
        }
    assigned_shading_log : dict or None
        If provided, final shading params are stored under assigned_shading_log[window_id].
    create_blinds : bool
        If True, create blind-based shading objects (WindowMaterial:Blind + ShadingControl).
    create_geometry_shading : bool
        If True, create Shading:Building:Detailed geometry-based shading (e.g. overhangs).
        You can do both if your design includes both.
    """
    if random_seed is not None:
        random.seed(random_seed)

    # Example: If we want to add blinds to each "FENESTRATIONSURFACE:DETAILED" in the IDF
    if create_blinds:
        fen_surfaces = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]

        for fen in fen_surfaces:
            window_id = fen.Name

            # 1) Pick shading params (combines shading_lookup + user overrides)
            shading_params = pick_shading_params(
                window_id=window_id,
                shading_type_key=shading_type_key,
                strategy=strategy,
                user_config=user_config_shading,
                assigned_shading_log=assigned_shading_log,
            )

            # 2) Create a WindowMaterial:Blind object
            blind_mat = idf.newidfobject("WINDOWMATERIAL:BLIND")
            blind_mat.Name = shading_params["blind_name"] + f"_{window_id}"
            blind_mat.Slat_Orientation = shading_params["slat_orientation"]
            blind_mat.Slat_Width = shading_params["slat_width"]
            blind_mat.Slat_Separation = shading_params["slat_separation"]
            blind_mat.Slat_Thickness = shading_params["slat_thickness"]
            blind_mat.Slat_Angle = shading_params["slat_angle_deg"]
            blind_mat.Slat_Conductivity = shading_params["slat_conductivity"]
            # If your shading_lookup includes solar reflectances, IR emissivity, etc.:
            if "slat_beam_solar_transmittance" in shading_params:
                blind_mat.Slat_Beam_Solar_Transmittance = shading_params["slat_beam_solar_transmittance"]
            if "slat_beam_solar_reflectance" in shading_params:
                blind_mat.Front_Side_Slat_Beam_Solar_Reflectance = shading_params["slat_beam_solar_reflectance"]
                blind_mat.Back_Side_Slat_Beam_Solar_Reflectance = shading_params["slat_beam_solar_reflectance"]
            if "slat_diffuse_solar_transmittance" in shading_params:
                blind_mat.Slat_Diffuse_Solar_Transmittance = shading_params["slat_diffuse_solar_transmittance"]
            if "slat_diffuse_solar_reflectance" in shading_params:
                blind_mat.Front_Side_Slat_Diffuse_Solar_Reflectance = shading_params["slat_diffuse_solar_reflectance"]
                blind_mat.Back_Side_Slat_Diffuse_Solar_Reflectance = shading_params["slat_diffuse_solar_reflectance"]
            if "slat_beam_visible_transmittance" in shading_params:
                blind_mat.Slat_Beam_Visible_Transmittance = shading_params["slat_beam_visible_transmittance"]
            if "slat_beam_visible_reflectance" in shading_params:
                blind_mat.Front_Side_Slat_Beam_Visible_Reflectance = shading_params["slat_beam_visible_reflectance"]
                blind_mat.Back_Side_Slat_Beam_Visible_Reflectance = shading_params["slat_beam_visible_reflectance"]
            if "slat_diffuse_visible_transmittance" in shading_params:
                blind_mat.Slat_Diffuse_Visible_Transmittance = shading_params["slat_diffuse_visible_transmittance"]
            if "slat_diffuse_visible_reflectance" in shading_params:
                blind_mat.Front_Side_Slat_Diffuse_Visible_Reflectance = shading_params["slat_diffuse_visible_reflectance"]
                blind_mat.Back_Side_Slat_Diffuse_Visible_Reflectance = shading_params["slat_diffuse_visible_reflectance"]
            if "slat_ir_transmittance" in shading_params:
                blind_mat.Slat_IR_Transmittance = shading_params["slat_ir_transmittance"]
            if "slat_ir_emissivity" in shading_params:
                blind_mat.Front_Side_Slat_Infrared_Hemispherical_Emissivity = shading_params["slat_ir_emissivity"]
                blind_mat.Back_Side_Slat_Infrared_Hemispherical_Emissivity = shading_params["slat_ir_emissivity"]

            # 3) If dynamic shading => create or reference a schedule
            #    For example, if we want a schedule that changes slat angle or availability:
            #    We'll illustrate a simple static case here.
            shading_ctrl = idf.newidfobject("WINDOWPROPERTY:SHADINGCONTROL")
            shading_ctrl.Name = f"ShadingCtrl_{window_id}"
            shading_ctrl.Shading_Type = "Blind"
            shading_ctrl.Shading_Device_Material_Name = blind_mat.Name
            shading_ctrl.Type_of_Slats_Control = "FixedSlatAngle"
            shading_ctrl.Slat_Angle_Control_for_Fixed_Slat_Angle = shading_params["slat_angle_deg"]
            shading_ctrl.Shading_Control_Is_Scheduled = "No"
            shading_ctrl.Glare_Control_Is_Active = "No"

            # Link the shading control to this fenestration surface
            fen.Shading_Control_Name = shading_ctrl.Name

    # If you want geometry-based shading objects (overhangs, fins):
    # create them using "Shading:Building:Detailed":
    if create_geometry_shading:
        _create_overhang_example(idf, building_row, shading_type_key, strategy, user_config_shading)


def _create_overhang_example(idf, building_row, shading_type_key, strategy, user_config_shading):
    """
    Example function to demonstrate geometry-based shading (Shading:Building:Detailed).
    In real usage, you’d compute or retrieve the overhang geometry from building_row
    or shading_params. This is just a placeholder.
    """
    # Suppose we pick some shading params that define the overhang depth
    shading_params = pick_shading_params(
        window_id="Global_Overhang", 
        shading_type_key=shading_type_key,
        strategy=strategy,
        user_config=user_config_shading
    )

    # Let's say we read an "overhang_depth" from shading_params
    overhang_depth = shading_params.get("overhang_depth", 1.0)  # default 1m

    # Create a Shading:Building:Detailed object
    shading_obj = idf.newidfobject("SHADING:BUILDING:DETAILED")
    shading_obj.Name = "Overhang_North"
    shading_obj.Shading_Surface_Type = "Overhang"  # or "Fin" or just blank

    # Hard-coded example geometry (4 vertices):
    # This is purely illustrative. You’d typically compute X/Y based on
    # building_row geometry, window width, or orientation, etc.
    shading_obj.Number_of_Vertices = 4

    # Vertex 1
    shading_obj.Vertex_1_Xcoordinate = 0.0
    shading_obj.Vertex_1_Ycoordinate = 5.0
    shading_obj.Vertex_1_Zcoordinate = 3.0
    # Vertex 2
    shading_obj.Vertex_2_Xcoordinate = overhang_depth
    shading_obj.Vertex_2_Ycoordinate = 5.0
    shading_obj.Vertex_2_Zcoordinate = 3.0
    # Vertex 3
    shading_obj.Vertex_3_Xcoordinate = overhang_depth
    shading_obj.Vertex_3_Ycoordinate = 5.0
    shading_obj.Vertex_3_Zcoordinate = 2.8
    # Vertex 4
    shading_obj.Vertex_4_Xcoordinate = 0.0
    shading_obj.Vertex_4_Ycoordinate = 5.0
    shading_obj.Vertex_4_Zcoordinate = 2.8

    # If shading_params included “tilt_angle” or “width”, you could
    # incorporate them in the above coordinates.


def add_shading_schedule(idf, schedule_name="MyShadingSchedule"):
    """
    Example of how you might create a schedule for dynamic shading control.
    You can call this within add_shading_objects if you want a non-fixed schedule.
    """
    sched = idf.newidfobject("SCHEDULE:COMPACT")
    sched.Name = schedule_name
    sched.Schedule_Type_Limits_Name = "Fraction"
    # Simple example: always 1.0
    sched.Field_1 = "Through: 12/31"
    sched.Field_2 = "For: AllDays"
    sched.Field_3 = "Until: 24:00, 1.0"

    return sched
