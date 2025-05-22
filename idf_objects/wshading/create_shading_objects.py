"""
create_shading_objects.py

This module creates EnergyPlus shading objects in the IDF
(e.g., WindowMaterial:Blind, WindowShadingControl,
 Shading:Building:Detailed, schedules, etc.).

It calls pick_shading_params(...) from assign_shading_values.py
to get final numeric parameter values. You can pass user/Excel overrides
to customize these parameters.

Usage:
  from idf_objects.wshading.create_shading_objects import add_shading_objects

  add_shading_objects(
      idf=idf,
      building_row=some_dict, # Or other context identifier
      shading_type_key="my_external_louvers",
      strategy="A", # Or "B"
      random_seed=42,
      user_config_shading=shading_overrides_for_this_type, # Dict of overrides for this specific shading_type_key
      assigned_shading_log=shading_log_dict,
      create_blinds=True,
      create_geometry_shading=False
  )
"""

import random
import logging
from .assign_shading_values import pick_shading_params

logger = logging.getLogger(__name__)
# Configure logger if not already configured by the main application
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s')


def add_shading_objects(
    idf,
    building_row,  # Used for context, e.g., if shading depends on building properties
    shading_type_key="my_external_louvers",
    strategy="A",
    random_seed=42,
    user_config_shading=None,
    assigned_shading_log=None,
    create_blinds=True,
    create_geometry_shading=False,
):
    """
    Creates the necessary shading objects in the IDF: e.g. WindowMaterial:Blind,
    WindowShadingControl, or geometry-based Shading:Building:Detailed.

    1) Loops over fenestration surfaces (if creating blinds per window) or processes
       once for global shading elements.
    2) Calls pick_shading_params(...) to get final numeric values (slat angles, etc.).
    3) Creates EnergyPlus shading devices (e.g., WindowMaterial:Blind + ShadingControl).
    4) Optionally, creates an E+ schedule if dynamic shading is needed (example provided).
    5) Optionally, creates Shading:Building:Detailed geometry if requested.

    Parameters
    ----------
    idf : IDF object
        The IDF object (e.g., from geomeppy or eppy) where new objects will be added.
    building_row : dict or pandas.Series or object
        Contextual data for the building/element being processed. Can be used to
        derive window IDs or influence shading choices if needed.
    shading_type_key : str
        Key in shading_lookup (from shading_lookup.py) to define the base shading
        parameters, e.g., "my_external_louvers".
    strategy : str
        Strategy for picking values from ranges ("A" for midpoint, "B" for random,
        other for min_val). Passed to pick_shading_params.
    random_seed : int, optional
        Seed for random number generation if strategy="B". Defaults to 42.
    user_config_shading : dict or None
        A dictionary of overrides for the specified `shading_type_key`.
        E.g., {"slat_angle_deg_range": (30, 60), "slat_width": 0.05}.
        These are applied on top of `shading_lookup` defaults.
    assigned_shading_log : dict or None
        If provided, final shading params are stored here. Keys could be window_id
        or another relevant identifier.
    create_blinds : bool
        If True, attempts to create blind-based shading objects (WindowMaterial:Blind
        + WindowShadingControl) for fenestration surfaces.
    create_geometry_shading : bool
        If True, attempts to create Shading:Building:Detailed geometry-based shading
        (e.g., overhangs), using an example function.
    """
    if random_seed is not None:
        random.seed(random_seed)

    if not idf:
        logger.error("IDF object is None. Cannot add shading objects.")
        return

    logger.info(f"Starting add_shading_objects for shading_type_key: '{shading_type_key}'")

    # --- Create Blind Shading for Fenestration Surfaces ---
    if create_blinds:
        logger.info("Attempting to create blind shading for fenestration surfaces.")
        try:
            # Ensure 'FENESTRATIONSURFACE:DETAILED' key exists in idf.idfobjects
            fen_surfaces = idf.idfobjects.get("FENESTRATIONSURFACE:DETAILED", [])
            if not fen_surfaces:
                logger.warning(
                    "No 'FENESTRATIONSURFACE:DETAILED' objects found in IDF. Skipping blind creation."
                )
            else:
                logger.info(f"Found {len(fen_surfaces)} FENESTRATIONSURFACE:DETAILED objects to process.")
        except Exception as e: # Catch broader exceptions if idf.idfobjects itself is problematic
            logger.error(
                f"Could not retrieve FENESTRATIONSURFACE:DETAILED from IDF: {e}", exc_info=True
            )
            fen_surfaces = []

        for fen_idx, fen_surface_obj in enumerate(fen_surfaces):
            fen_name_attr = getattr(fen_surface_obj, "Name", None)
            # Use a more robust default name if the actual name is missing or empty
            window_id = fen_name_attr if fen_name_attr and fen_name_attr.strip() else f"FenSurface_Unnamed_{fen_idx}"
            
            logger.info(f"Processing fenestration surface: '{window_id}' (Index: {fen_idx})")

            try:
                # 1) Pick shading params (combines shading_lookup + user overrides)
                logger.debug(f"[{window_id}] Picking shading parameters with key '{shading_type_key}' and strategy '{strategy}'.")
                shading_params = pick_shading_params(
                    window_id=window_id,  # Used for logging within pick_shading_params
                    shading_type_key=shading_type_key,
                    strategy=strategy,
                    user_config=user_config_shading,  # Pass the specific overrides for this type
                    assigned_shading_log=assigned_shading_log,
                )

                if not shading_params:
                    logger.warning(
                        f"[{window_id}] No shading parameters resolved for key '{shading_type_key}'. Skipping blind creation for this window."
                    )
                    if assigned_shading_log is not None:
                        if window_id not in assigned_shading_log:
                            assigned_shading_log[window_id] = {}
                        assigned_shading_log[window_id]["shading_creation_status"] = f"Failed: No params for key {shading_type_key}"
                    continue

                logger.debug(f"[{window_id}] Resolved shading parameters: {shading_params}")

                # 2) Create or retrieve a WindowMaterial:Blind object
                base_blind_material_name_from_params = shading_params.get("blind_name", "DefaultBlindMaterial")
                # Ensure blind_mat_name is valid for E+ (no spaces, etc.)
                blind_mat_name = f"{base_blind_material_name_from_params}_{window_id.replace(' ', '_').replace(':', '_')}"
                
                logger.debug(f"[{window_id}] Target WindowMaterial:Blind name: '{blind_mat_name}'")

                existing_blind_mats_objects = idf.idfobjects.get("WINDOWMATERIAL:BLIND", [])
                blind_mat = next((bm for bm in existing_blind_mats_objects if getattr(bm, 'Name', None) == blind_mat_name), None)

                if blind_mat:
                    logger.info(
                        f"[{window_id}] WindowMaterial:Blind '{blind_mat_name}' already exists. Reusing."
                    )
                else:
                    logger.info(f"[{window_id}] Creating new WindowMaterial:Blind '{blind_mat_name}'.")
                    blind_mat = idf.newidfobject("WINDOWMATERIAL:BLIND")
                    blind_mat.Name = blind_mat_name

                    # --- Assign common blind material properties with defaults ---
                    blind_mat.Slat_Orientation = shading_params.get("slat_orientation", "Horizontal")
                    blind_mat.Slat_Width = shading_params.get("slat_width", 0.025)
                    blind_mat.Slat_Separation = shading_params.get("slat_separation", 0.020)
                    blind_mat.Slat_Thickness = shading_params.get("slat_thickness", 0.001)
                    blind_mat.Slat_Angle = shading_params.get("slat_angle_deg", 45.0) # This is for the material definition, not control
                    blind_mat.Slat_Conductivity = shading_params.get("slat_conductivity", 160.0)

                    # --- Optical Properties (ensure defaults if params are missing) ---
                    sbsr = shading_params.get("slat_beam_solar_reflectance", 0.7)
                    sdsr = shading_params.get("slat_diffuse_solar_reflectance", 0.7)
                    sbvr = shading_params.get("slat_beam_visible_reflectance", 0.7)
                    sdvr = shading_params.get("slat_diffuse_visible_reflectance", 0.7)
                    sir_em = shading_params.get("slat_ir_emissivity", 0.9)

                    blind_mat.Slat_Beam_Solar_Transmittance = shading_params.get("slat_beam_solar_transmittance", 0.0)
                    blind_mat.Front_Side_Slat_Beam_Solar_Reflectance = sbsr
                    blind_mat.Back_Side_Slat_Beam_Solar_Reflectance = shading_params.get("back_side_slat_beam_solar_reflectance", sbsr)

                    blind_mat.Slat_Diffuse_Solar_Transmittance = shading_params.get("slat_diffuse_solar_transmittance", 0.0)
                    blind_mat.Front_Side_Slat_Diffuse_Solar_Reflectance = sdsr
                    blind_mat.Back_Side_Slat_Diffuse_Solar_Reflectance = shading_params.get("back_side_slat_diffuse_solar_reflectance", sdsr)

                    blind_mat.Slat_Beam_Visible_Transmittance = shading_params.get("slat_beam_visible_transmittance", 0.0)
                    blind_mat.Front_Side_Slat_Beam_Visible_Reflectance = sbvr
                    blind_mat.Back_Side_Slat_Beam_Visible_Reflectance = shading_params.get("back_side_slat_beam_visible_reflectance", sbvr)

                    blind_mat.Slat_Diffuse_Visible_Transmittance = shading_params.get("slat_diffuse_visible_transmittance", 0.0)
                    blind_mat.Front_Side_Slat_Diffuse_Visible_Reflectance = sdvr
                    blind_mat.Back_Side_Slat_Diffuse_Visible_Reflectance = shading_params.get("back_side_slat_diffuse_visible_reflectance", sdvr)
                    
                    blind_mat.Slat_Infrared_Hemispherical_Transmittance = shading_params.get("slat_ir_transmittance", 0.0)
                    blind_mat.Front_Side_Slat_Infrared_Hemispherical_Emissivity = sir_em
                    blind_mat.Back_Side_Slat_Infrared_Hemispherical_Emissivity = shading_params.get("back_side_slat_ir_emissivity", sir_em)
                    
                    # --- Standard Optional Fields for WindowMaterial:Blind ---
                    if "blind_to_glass_distance" in shading_params:  # E+ Field: Blind to Glass Distance
                        # eppy uses the IDD field name with underscores. Earlier
                        # versions of this code attempted to use the
                        # ``Distance_between_Slat_and_Glazing`` attribute which
                        # does not exist in the EnergyPlus IDD and caused
                        # ``BadEPFieldError``.  The correct attribute name that
                        # corresponds to the "Blind to Glass Distance" field in
                        # the IDD is ``Blind_to_Glass_Distance``.
                        blind_mat.Blind_to_Glass_Distance = shading_params["blind_to_glass_distance"]
                    
                    # E+ Field: Slat_Opening_Multiplier. Uses 'slat_opening_multiplier' from updated lookup/params.
                    # Default to 0.5 if not found, which was in the IDF.
                    slat_opening_mult = shading_params.get("slat_opening_multiplier", 0.5) 
                    blind_mat.Slat_Opening_Multiplier = slat_opening_mult
                    
                    # Minimum_Output_Signal and Maximum_Output_Signal are not typically set directly unless complex control.
                    # The fields "Minimum Slat Angle" and "Maximum Slat Angle" are NOT part of WindowMaterial:Blind.
                    # They are part of WindowShadingControl for certain control types.

                    logger.debug(f"[{window_id}] Successfully created/configured WindowMaterial:Blind '{blind_mat.Name}'.")

                # 3) Create or retrieve WindowShadingControl object
                shading_ctrl_name = f"ShadingCtrl_{window_id.replace(' ', '_').replace(':', '_')}"
                logger.debug(f"[{window_id}] Target WindowShadingControl name: '{shading_ctrl_name}'")

                # Determine the zone name by looking up the base surface of the fenestration
                zone_name = None
                base_surface_name = getattr(fen_surface_obj, "Building_Surface_Name", None)
                if base_surface_name:
                    base_surfaces = idf.idfobjects.get("BUILDINGSURFACE:DETAILED", [])
                    bs_obj = next((bs for bs in base_surfaces if getattr(bs, 'Name', None) == base_surface_name), None)
                    if bs_obj:
                        zone_name = getattr(bs_obj, "Zone_Name", None)
                
                if zone_name is None or not zone_name.strip():
                    logger.error(f"[{window_id}] Cannot determine Zone Name for WindowShadingControl '{shading_ctrl_name}'. Skipping this control object.")
                    if assigned_shading_log is not None:
                        if window_id not in assigned_shading_log: assigned_shading_log[window_id] = {}
                        assigned_shading_log[window_id]["shading_creation_status"] = "Failed: Zone Name for ShadingControl could not be determined."
                    continue # Skip to the next fenestration surface

                existing_shading_ctrls_objects = idf.idfobjects.get("WINDOWSHADINGCONTROL", [])
                shading_ctrl = next((sc for sc in existing_shading_ctrls_objects if getattr(sc, 'Name', None) == shading_ctrl_name), None)

                if shading_ctrl:
                    logger.info(
                        f"[{window_id}] WindowShadingControl '{shading_ctrl_name}' already exists. Reusing."
                    )
                else:
                    logger.info(f"[{window_id}] Creating new WindowShadingControl '{shading_ctrl_name}'.")
                    shading_ctrl = idf.newidfobject("WINDOWSHADINGCONTROL")
                    shading_ctrl.Name = shading_ctrl_name
                    shading_ctrl.Zone_Name = zone_name # Zone Name is required and now validated

                    # Determine Shading_Type based on blind_to_glass_distance or a param
                    blind_dist = shading_params.get("blind_to_glass_distance", 0.05)  # Default to positive (exterior)
                    shading_device_type_ep = "ExteriorBlind"
                    if isinstance(blind_dist, (int, float)) and blind_dist < 0:
                        shading_device_type_ep = "InteriorBlind"
                    # Other types: "ExteriorScreen", "InteriorScreen", "BetweenGlassBlind", "BetweenGlassScreen", "Shade"
                    # This logic could be expanded if shading_params includes a more direct "shading_device_ep_type"
                    shading_ctrl.Shading_Type = shading_params.get("shading_device_ep_type", shading_device_type_ep)
                    
                    shading_ctrl.Shading_Device_Material_Name = blind_mat_name

                    shading_ctrl.Shading_Control_Type = shading_params.get("shading_control_type", "AlwaysOn") # E.g., AlwaysOn, OnIfHighSolarOnWindow, Scheduled
                    
                    # Slat control type, relevant if Shading_Type is a blind
                    if "Blind" in shading_ctrl.Shading_Type: # Covers InteriorBlind, ExteriorBlind, BetweenGlassBlind
                        shading_ctrl.Type_of_Slats_Control_for_Blinds = shading_params.get("slat_control_type", "FixedSlatAngle") # E.g., FixedSlatAngle, ScheduledSlatAngle, BlockBeamSolar

                        # Set Fixed_Slat_Angle if control type is FixedSlatAngle
                        if shading_ctrl.Type_of_Slats_Control_for_Blinds.lower() == "fixedslatangle":
                            # Use the corrected field name: Fixed_Slat_Angle
                            shading_ctrl.Fixed_Slat_Angle = shading_params.get("slat_angle_deg", 45.0)
                        
                        # Example for ScheduledSlatAngle (add more logic if using this)
                        # if shading_ctrl.Type_of_Slats_Control_for_Blinds.lower() == "scheduledslatangle":
                        #     shading_ctrl.Slat_Angle_Schedule_Name = shading_params.get("slat_angle_schedule_name", "DefaultSlatAngleSchedule")
                        #     # Ensure "DefaultSlatAngleSchedule" exists or is created.

                    # If Shading_Control_Type is "Scheduled"
                    if shading_ctrl.Shading_Control_Type.lower() == "scheduled":
                         shading_ctrl.Schedule_Name = shading_params.get("shading_control_schedule_name", "AlwaysOnSchedule") # Ensure this schedule exists
                         # The field "Shading_Control_Is_Scheduled" is not directly in WindowShadingControl.
                         # The presence of a Schedule_Name when Shading_Control_Type is "Scheduled" implies it.
                    
                    shading_ctrl.Glare_Control_Is_Active = shading_params.get("glare_control_is_active", "No")
                    # Add other fields like Setpoint, Glare_Control_Daylighting_Illuminance_Setpoint, etc. as needed.

                    logger.debug(f"[{window_id}] Successfully created/configured WindowShadingControl '{shading_ctrl.Name}'.")

                # Ensure the current fenestration surface is listed in the control object's extensible fields
                # This part can be tricky with IDF libraries. Geomeppy might have an add_extensible method.
                # Assuming a direct indexed approach for now, ensuring it doesn't overwrite.
                # Check if the fenestration surface is already in this control object
                is_fen_listed = False
                for i in range(1, 101): # Max extensible fields, adjust if needed
                    field_name = f"Fenestration_Surface_{i}_Name"
                    current_fen_on_ctrl = getattr(shading_ctrl, field_name, None)
                    if current_fen_on_ctrl == fen_name_attr:
                        is_fen_listed = True
                        break
                    if current_fen_on_ctrl is None or not current_fen_on_ctrl.strip(): # Found an empty slot
                        if not is_fen_listed: # Add if not already listed
                            setattr(shading_ctrl, field_name, fen_name_attr)
                            logger.debug(f"[{window_id}] Assigned fenestration '{fen_name_attr}' to {field_name} of '{shading_ctrl_name}'.")
                        is_fen_listed = True # Mark as listed (or handled)
                        break
                if not is_fen_listed:
                     logger.warning(f"[{window_id}] Could not assign fenestration '{fen_name_attr}' to WindowShadingControl '{shading_ctrl_name}' (no empty slots or already present).")


                if assigned_shading_log is not None:
                    if window_id not in assigned_shading_log:
                        assigned_shading_log[window_id] = {}
                    assigned_shading_log[window_id]["shading_creation_status"] = f"Linked to {shading_ctrl_name}"
                    assigned_shading_log[window_id]["shading_control_name_assigned"] = shading_ctrl_name
                    assigned_shading_log[window_id]["blind_material_name_used"] = blind_mat_name

            except Exception as e_fen_processing:
                logger.error(
                    f"Error processing blind for fenestration surface '{window_id}': {e_fen_processing}",
                    exc_info=True 
                )
                if assigned_shading_log is not None:
                    if window_id not in assigned_shading_log:
                        assigned_shading_log[window_id] = {}
                    assigned_shading_log[window_id]["shading_creation_status"] = f"Failed: Outer processing error - {str(e_fen_processing)}"
                continue  # Move to the next fenestration surface
        logger.info("Finished processing blind shading for fenestration surfaces.")


    # --- Create Geometry-Based Shading (e.g., Overhangs, Fins) ---
    if create_geometry_shading:
        logger.info(
            f"Attempting to create geometry-based shading using shading_type_key: '{shading_type_key}'"
        )
        # This typically would not loop per window unless geometry is window-specific.
        # The _create_overhang_example is a global example.
        # You might need a list of building elements or a different context for these.
        # Ensure user_config_shading passed here is relevant for geometric shading.
        _create_overhang_example(
            idf,
            building_row,  # Pass context
            shading_type_key=shading_type_key, # This key should be for geometric shading in shading_lookup
            strategy=strategy,
            user_config_shading=user_config_shading, 
        )
    
    num_blind_mats_final = len(idf.idfobjects.get("WINDOWMATERIAL:BLIND", []))
    num_shading_ctrls_final = len(idf.idfobjects.get("WINDOWSHADINGCONTROL", []))
    logger.info(f"Exiting add_shading_objects. Total WindowMaterial:Blind objects in IDF: {num_blind_mats_final}")
    logger.info(f"Exiting add_shading_objects. Total WindowShadingControl objects in IDF: {num_shading_ctrls_final}")


def _create_overhang_example(
    idf, building_row_context, shading_type_key, strategy, user_config_shading
):
    """
    Example function to demonstrate geometry-based shading (Shading:Building:Detailed).
    In real usage, you’d compute or retrieve the overhang geometry from
    building_row_context, other geometric inputs, or detailed shading_params.
    This is a placeholder and creates a fixed, illustrative overhang.

    Parameters
    ----------
    idf : IDF object
    building_row_context : dict or object
        Contextual data (e.g., building dimensions, orientation) that could inform geometry.
    shading_type_key : str
        Key to look up base parameters, potentially for overhang depth, etc.
        This should point to an entry in shading_lookup.py suitable for geometric shading.
    strategy : str
        Strategy for picking values from ranges.
    user_config_shading : dict or None
        Overrides for parameters relevant to this geometric shading.
    """
    logger.info(f"Executing _create_overhang_example for shading_type_key: {shading_type_key}.")
    
    # For geometry, the 'window_id' for pick_shading_params might be a generic name
    # if the overhang is not tied to a specific window but rather a facade or building.
    # The `user_config_shading` passed here should be the specific overrides for this `shading_type_key`.
    shading_params = pick_shading_params(
        window_id="GeometricShading_Example",  # Generic ID for logging these params
        shading_type_key=shading_type_key,
        strategy=strategy,
        user_config=user_config_shading, 
    )

    if not shading_params:
        logger.warning(
            f"No parameters resolved for geometric shading example with key '{shading_type_key}'. Skipping creation."
        )
        return

    # Example: Expecting "shading_element_name" and "overhang_depth" from shading_params
    overhang_name = shading_params.get("shading_element_name", "Default_Overhang_Example")
    overhang_depth = shading_params.get("overhang_depth", 1.0)  # Default 1m depth if not in params

    # Ensure name is valid for E+
    overhang_name = overhang_name.replace(' ', '_').replace(':', '_')

    # Check if this shading object already exists
    existing_shading_geom_objects = idf.idfobjects.get("SHADING:BUILDING:DETAILED", [])
    if any(getattr(sg, 'Name', None) == overhang_name for sg in existing_shading_geom_objects):
        logger.info(
            f"Shading:Building:Detailed '{overhang_name}' already exists. Skipping creation."
        )
        return

    try:
        shading_obj = idf.newidfobject("SHADING:BUILDING:DETAILED")
        shading_obj.Name = overhang_name
        # Base_Surface_Name: Optional, if the overhang is attached to a specific surface.
        # Transmittance_Schedule_Name: Optional, if transmittance varies.

        # --- Illustrative Geometry ---
        # This is purely illustrative. Real geometry calculation is complex and depends heavily on
        # building_row_context (facade dimensions, window positions, building orientation)
        # and detailed parameters from shading_params (width, tilt, offsets, etc.).
        # The coordinates MUST be in absolute world coordinates.

        logger.info(f"Illustrative geometry for '{overhang_name}': This is a placeholder and needs actual geometric calculation.")
        
        # Example: A 5m wide overhang, 'overhang_depth' deep, at Z=3.0, on a conceptual North facade (Y positive from facade plane)
        # These coordinates would need to be calculated based on the actual building.
        # Assume facade starts at X=0, Y=0 (local to facade segment) and is oriented North.
        # World coordinates would depend on building's position and orientation.
        
        # For simplicity, let's define a rectangle parallel to XY plane, offset in Y.
        # This is NOT a realistic overhang calculation.
        x_start = 0.0
        width = 5.0
        z_level = 3.0
        y_facade = 0.0 # Assuming facade is at Y=0 for this example segment

        shading_obj.Number_of_Vertices = 4
        # Vertices are typically counter-clockwise when viewed from outside looking towards the building.
        # For an overhang on a North wall (Y-positive is "out"), this means Y increases.

        # Vertex 1 (Bottom-Left of overhang, at facade)
        shading_obj.Vertex_1_X_coordinate = x_start
        shading_obj.Vertex_1_Y_coordinate = y_facade 
        shading_obj.Vertex_1_Z_coordinate = z_level

        # Vertex 2 (Bottom-Right of overhang, at facade)
        shading_obj.Vertex_2_X_coordinate = x_start + width
        shading_obj.Vertex_2_Y_coordinate = y_facade
        shading_obj.Vertex_2_Z_coordinate = z_level

        # Vertex 3 (Top-Right of overhang, projecting outwards)
        shading_obj.Vertex_3_X_coordinate = x_start + width
        shading_obj.Vertex_3_Y_coordinate = y_facade + overhang_depth # Projects 'overhang_depth'
        shading_obj.Vertex_3_Z_coordinate = z_level 

        # Vertex 4 (Top-Left of overhang, projecting outwards)
        shading_obj.Vertex_4_X_coordinate = x_start
        shading_obj.Vertex_4_Y_coordinate = y_facade + overhang_depth
        shading_obj.Vertex_4_Z_coordinate = z_level

        logger.debug(
            f"Created placeholder Shading:Building:Detailed '{shading_obj.Name}' with illustrative depth {overhang_depth}m."
        )

    except Exception as e:
        logger.error(f"Error creating Shading:Building:Detailed '{overhang_name}': {e}", exc_info=True)


def add_shading_schedule(
    idf, schedule_name="DefaultShadingSchedule", schedule_type="Fraction"
):
    """
    Example of how you might create a schedule for dynamic shading control
    (e.g., for Shading_Control_Schedule_Name in WindowShadingControl).

    Parameters
    ----------
    idf : IDF object
    schedule_name : str
        Name for the new schedule.
    schedule_type : str
        Type of schedule, e.g., "Fraction", "OnOff", "Temperature".

    Returns
    -------
    The created schedule object, or None if creation fails.
    """
    logger.info(
        f"Attempting to create/retrieve schedule: '{schedule_name}' of type '{schedule_type}'."
    )
    
    # Ensure schedule_name is valid for E+
    schedule_name_ep = schedule_name.replace(' ', '_').replace(':', '_')


    # Check if schedule already exists (assuming Schedule:Compact for this example)
    # More robust checking would involve checking other schedule types too.
    schedule_objects = idf.idfobjects.get("SCHEDULE:COMPACT", [])
    existing_schedule = next((s for s in schedule_objects if getattr(s, 'Name', None) == schedule_name_ep), None)
    
    if existing_schedule:
        logger.info(f"Schedule:Compact '{schedule_name_ep}' already exists. Reusing.")
        return existing_schedule

    try:
        # Using SCHEDULE:COMPACT for simplicity.
        sched = idf.newidfobject("SCHEDULE:COMPACT")
        sched.Name = schedule_name_ep

        # Schedule_Type_Limits_Name links to a ScheduleTypeLimits object.
        # Assume ScheduleTypeLimits Name matches the schedule_type for simplicity,
        # e.g., if schedule_type is "Fraction", it looks for a ScheduleTypeLimits named "Fraction".
        stl_name = schedule_type 
        
        stl_objects = idf.idfobjects.get("SCHEDULETYPELIMITS", [])
        existing_stl = next((stl for stl in stl_objects if getattr(stl, 'Name', None) == stl_name), None)

        if not existing_stl:
            logger.warning(
                f"ScheduleTypeLimits '{stl_name}' not found. Creating a basic one for '{schedule_name_ep}'."
            )
            new_stl = idf.newidfobject("SCHEDULETYPELIMITS")
            new_stl.Name = stl_name
            if schedule_type.lower() == "fraction":
                new_stl.Lower_Limit_Value = 0.0
                new_stl.Upper_Limit_Value = 1.0
                new_stl.Numeric_Type = "Continuous" # Or Discrete if it's 0 or 1 steps
            elif schedule_type.lower() == "onoff": 
                new_stl.Lower_Limit_Value = 0.0
                new_stl.Upper_Limit_Value = 1.0
                new_stl.Numeric_Type = "Discrete"
            elif schedule_type.lower() == "temperature":
                new_stl.Lower_Limit_Value = -100.0 
                new_stl.Upper_Limit_Value = 200.0  
                new_stl.Numeric_Type = "Continuous"
            else: # Default for unknown types
                logger.warning(
                    f"No default setup for ScheduleTypeLimits '{schedule_type}'. Defaulting to Fraction-like limits (0-1, Continuous)."
                )
                new_stl.Lower_Limit_Value = 0.0
                new_stl.Upper_Limit_Value = 1.0
                new_stl.Numeric_Type = "Continuous" 

        sched.Schedule_Type_Limits_Name = stl_name

        # Simple example: always 1.0 (e.g., shades always active if scheduled and this schedule is used)
        # Field format for SCHEDULE:COMPACT: "Through: MM/DD", "For: Days", "Until: HH:MM, Value", ...
        sched.Field_1 = "Through: 12/31"  # Through end of year
        sched.Field_2 = "For: AllDays"  # For all day types
        sched.Field_3 = "Until: 24:00"   # Until midnight
        sched.Field_4 = "1.0"            # Value is 1.0
        # Add more fields for complex schedules.

        logger.debug(f"Created Schedule:Compact '{sched.Name}'.")
        return sched
    except Exception as e:
        logger.error(f"Error creating schedule '{schedule_name_ep}': {e}", exc_info=True)
        return None
