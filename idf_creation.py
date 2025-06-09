###############################################################
# File: idf_creation.py
###############################################################
"""
idf_creation.py

Handles the creation of EnergyPlus IDF files for a list of buildings,
plus optional simulation runs and post-processing.

Key functionalities:
  1) create_idf_for_building(...) builds a single IDF using geomeppy,
     applying geometry, fenestration, HVAC, etc.
  2) create_idfs_for_all_buildings(...) loops over multiple buildings,
     then optionally runs simulations and merges results in one or more ways.

Updated to allow writing logs/results inside a specific job folder via logs_base_dir.
"""

import os
import logging
import pandas as pd

# geomeppy for IDF manipulation
from geomeppy import IDF

# --- Import your custom submodules ---
from idf_objects.geomz.building import create_building_with_roof_type
from idf_objects.fenez.fenestration import add_fenestration
from idf_objects.fenez.materials import (
    update_construction_materials,
    assign_constructions_to_surfaces
)
from idf_objects.Elec.lighting import add_lights_and_parasitics
from idf_objects.eequip.equipment import add_electric_equipment
from idf_objects.DHW.water_heater import add_dhw_to_idf
from idf_objects.HVAC.custom_hvac import add_HVAC_Ideal_to_all_zones
from idf_objects.ventilation.add_ventilation import add_ventilation_to_idf
from idf_objects.wshading.create_shading_objects import add_shading_objects # Corrected import if it was wshading
from idf_objects.setzone.add_outdoor_air_and_zone_sizing_to_all_zones import add_outdoor_air_and_zone_sizing_to_all_zones
from idf_objects.tempground.add_ground_temperatures import add_ground_temperatures
from idf_objects.other.zonelist import create_zonelist

# Output & simulation modules
from idf_objects.outputdef.assign_output_settings import assign_output_settings
from idf_objects.outputdef.add_output_definitions import add_output_definitions
from postproc.merge_results import merge_all_results
from epw.run_epw_sims import simulate_all

# Configure logger for this module (or ensure it's configured at the application entry point)
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logger.addHandler(logging.NullHandler()) # Be a good library/module

###############################################################################
# Global Default IDF Config
# (Override these via environment variables or main_config if needed.)
###############################################################################
idf_config = {
    "iddfile": "EnergyPlus/Energy+.idd",         # Default path to the IDD file
    "idf_file_path": "EnergyPlus/Minimal.idf",   # Default path to a minimal base IDF
    "output_dir": "output/output_IDFs"           # Default folder to save generated IDFs
}


def create_idf_for_building(
    building_row,
    building_index,
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="B", # Note: Shading modules often default to "A", ensure consistency or pass explicitly
    random_seed=42,
    # Geometry
    user_config_geom=None,
    assigned_geom_log=None,
    # Lighting
    user_config_lighting=None,
    assigned_lighting_log=None,
    # Electric equipment
    user_config_equipment=None,
    assigned_equip_log=None,
    # DHW
    user_config_dhw=None,
    assigned_dhw_log=None,
    # Fenestration
    res_data=None,
    nonres_data=None,
    assigned_fenez_log=None,
    # Window Shading
    shading_type_key_for_blinds="my_external_louvers", # Explicit parameter for clarity
    user_config_shading=None, # This should be the specific config for the shading_type_key_for_blinds
    assigned_shading_log=None,
    apply_blind_shading=True, # To control if blind shading is added
    apply_geometric_shading=False, # To control if geometric shading is added
    shading_strategy = "A", # Shading often uses 'A' (midpoint) as default, can be different from global 'strategy'
    # HVAC
    user_config_hvac=None,
    assigned_hvac_log=None,
    # Vent
    user_config_vent=None,
    assigned_vent_log=None,
    # Zone sizing
    assigned_setzone_log=None,
    # Ground temps
    assigned_groundtemp_log=None,
    # Output definitions
    output_definitions=None
):
    """
    Build an IDF for a single building.
    """
    logger.info(f"Starting IDF creation for building_index: {building_index}, ogc_fid: {building_row.get('ogc_fid', 'N/A')}")
    # 1) Setup IDF from the minimal template
    IDF.setiddname(idf_config["iddfile"])
    idf = IDF(idf_config["idf_file_path"])

    # 2) Basic building object settings
    building_obj = idf.newidfobject("BUILDING")
    building_obj.Name = f"Sample_Building_{building_index}"

    orientation = building_row.get("building_orientation", 0.0)
    if pd.isna(orientation):
        orientation = 0.0
    building_obj.North_Axis = 0.0 # Geometry is rotated, building north axis remains 0

    logger.debug(f"[{building_index}] Set up base IDF and BUILDING object.")

    # 3) Create geometry
    if assigned_geom_log is not None and building_row.get("ogc_fid") not in assigned_geom_log:
        assigned_geom_log[building_row.get("ogc_fid")] = {}

    edge_types = []
    for side_col in ["north_side", "east_side", "south_side", "west_side"]:
        edge_types.append(building_row.get(side_col, "Facade"))

    create_building_with_roof_type(
        idf=idf,
        area=building_row.get("area", 100.0),
        perimeter=building_row.get("perimeter", 40.0),
        orientation=orientation,
        building_row=building_row,
        edge_types=edge_types,
        calibration_stage=calibration_stage,
        strategy=strategy, # Global strategy
        random_seed=random_seed,
        user_config=user_config_geom,
        assigned_geom_log=assigned_geom_log
    )
    logger.debug(f"[{building_index}] Geometry created.")

    # 4) Update materials & constructions
    construction_map = update_construction_materials(
        idf=idf,
        building_row=building_row,
        building_index=building_index,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy, # Global strategy
        random_seed=random_seed,
        user_config_fenez=None,
        assigned_fenez_log=assigned_fenez_log
    )
    assign_constructions_to_surfaces(idf, construction_map)
    logger.debug(f"[{building_index}] Materials and constructions updated and assigned.")

    # Create zone list for convenience
    create_zonelist(idf, zonelist_name="ALL_ZONES")
    logger.debug(f"[{building_index}] Zonelist 'ALL_ZONES' created.")

    # 5) Fenestration
    add_fenestration(
        idf=idf,
        building_row=building_row,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy, # Global strategy
        random_seed=random_seed,
        res_data=res_data,
        nonres_data=nonres_data,
        assigned_fenez_log=assigned_fenez_log
    )
    logger.debug(f"[{building_index}] Fenestration added.")

    # 6) Window shading (e.g., blinds)
    if apply_blind_shading or apply_geometric_shading:
        logger.info(f"[{building_index}] Applying window shading. Blinds: {apply_blind_shading}, Geometric: {apply_geometric_shading}")
        add_shading_objects(
            idf=idf,
            building_row=building_row,
            shading_type_key=shading_type_key_for_blinds,
            strategy=shading_strategy,
            random_seed=random_seed,
            user_config_shading=user_config_shading,
            assigned_shading_log=assigned_shading_log,
            create_blinds=apply_blind_shading,
            create_geometry_shading=apply_geometric_shading
        )
        logger.debug(f"[{building_index}] Window shading objects processed.")
    else:
        logger.info(f"[{building_index}] Skipping window shading.")

    # 7) Lighting
    add_lights_and_parasitics(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy, # Global strategy
        random_seed=random_seed,
        user_config=user_config_lighting,
        assigned_values_log=assigned_lighting_log
    )
    logger.debug(f"[{building_index}] Lighting and parasitics added.")

    # 8) Electric equipment
    add_electric_equipment(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy, # Global strategy
        random_seed=random_seed,
        user_config=user_config_equipment,
        assigned_values_log=assigned_equip_log,
        zonelist_name="ALL_ZONES",
    )
    logger.debug(f"[{building_index}] Electric equipment added.")

    # 9) DHW
    add_dhw_to_idf(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy, # Global strategy
        random_seed=random_seed,
        name_suffix=f"MyDHW_{building_index}",
        user_config_dhw=user_config_dhw,
        assigned_dhw_log=assigned_dhw_log,
        use_nta=True
    )
    logger.debug(f"[{building_index}] DHW system added.")

    # 10) HVAC
    add_HVAC_Ideal_to_all_zones(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy, # Global strategy
        random_seed=random_seed,
        user_config_hvac=user_config_hvac,
        assigned_hvac_log=assigned_hvac_log
    )
    logger.debug(f"[{building_index}] Ideal Loads HVAC system added.")

    # 11) Ventilation
    add_ventilation_to_idf(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_vent=user_config_vent,
        assigned_vent_log=assigned_vent_log,
        infiltration_model="weather",
    )
    logger.debug(f"[{building_index}] Ventilation and infiltration added.")

    # 12) Zone sizing
    add_outdoor_air_and_zone_sizing_to_all_zones(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        assigned_setzone_log=assigned_setzone_log
    )
    logger.debug(f"[{building_index}] Outdoor air and zone sizing objects added.")

    # 13) Ground temperatures
    add_ground_temperatures(
        idf=idf,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        assigned_groundtemp_log=assigned_groundtemp_log
    )
    logger.debug(f"[{building_index}] Ground temperatures added.")

    # 14) Output definitions
    if output_definitions is None:
        output_definitions = {
            "desired_variables": ["Facility Total Electric Demand Power", "Zone Air Temperature"],
            "desired_meters": ["Electricity:Facility"],
            "override_variable_frequency": "Hourly",
            "override_meter_frequency": "Hourly",
            "include_tables": True,
            "include_summary": True
        }
    out_settings = assign_output_settings(
        desired_variables=output_definitions.get("desired_variables", []),
        desired_meters=output_definitions.get("desired_meters", []),
        override_variable_frequency=output_definitions.get("override_variable_frequency", "Hourly"),
        override_meter_frequency=output_definitions.get("override_meter_frequency", "Hourly"),
        include_tables=output_definitions.get("include_tables", True),
        include_summary=output_definitions.get("include_summary", True)
    )
    add_output_definitions(idf, out_settings)
    logger.debug(f"[{building_index}] Output definitions added.")

    # 15) Save final IDF
    os.makedirs(idf_config["output_dir"], exist_ok=True)
    idf_filename = f"building_{building_row.get('ogc_fid', building_index)}.idf"
    idf_filename = idf_filename.replace(" ", "_").replace(":", "_") # Basic sanitization
    out_path = os.path.join(idf_config["output_dir"], idf_filename)
    
    try:
        idf.save(out_path)
        logger.info(f"IDF for building_index {building_index} saved at: {out_path}")
    except Exception as e:
        logger.error(f"Failed to save IDF for building_index {building_index} at {out_path}: {e}", exc_info=True)
        return None

    return out_path


def create_idfs_for_all_buildings(
    df_buildings,
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="B",
    random_seed=42,
    # partial user configs
    user_config_geom=None,
    user_config_lighting=None,
    user_config_equipment=None,
    user_config_dhw=None,
    res_data=None, # Fenestration base data
    nonres_data=None, # Fenestration base data
    user_config_shading=None,
    shading_type_key_for_blinds="my_external_louvers",
    apply_blind_shading=True,
    apply_geometric_shading=False,
    shading_strategy = "A",
    # Other configs
    user_config_hvac=None,
    user_config_vent=None,
    user_config_epw=None,
    output_definitions=None,
    run_simulations=True,
    simulate_config=None,
    post_process=True,
    post_process_config=None,
    logs_base_dir=None
):
    """
    Loops over df_buildings, calls create_idf_for_building for each.
    """
    func_logger = logging.getLogger(f"{__name__}.create_idfs_for_all_buildings")
    func_logger.info(f"Starting to create IDFs for {len(df_buildings)} buildings.")

    assigned_geom_log       = {}
    assigned_lighting_log   = {}
    assigned_equip_log      = {}
    assigned_dhw_log        = {}
    assigned_fenez_log      = {}
    assigned_shading_log    = {}
    assigned_hvac_log       = {}
    assigned_vent_log       = {}
    assigned_epw_log        = {}
    assigned_groundtemp_log = {}
    assigned_setzone_log    = {}

    for idx, row in df_buildings.iterrows():
        building_specific_seed = random_seed + idx 

        # Possibly filter shading overrides from user_config_shading if it’s a list of rules:
        specific_shading_overrides = {}
        if isinstance(user_config_shading, list):
            try:
                from idf_objects.wshading.shading_overrides_from_excel import pick_shading_params_from_rules
                bldg_identifier = row.get("ogc_fid", idx)
                specific_shading_overrides = pick_shading_params_from_rules(
                    building_id=bldg_identifier,
                    shading_type_key=shading_type_key_for_blinds,
                    all_rules=user_config_shading,
                    fallback={}
                )
                if specific_shading_overrides:
                    func_logger.info(f"Found specific Excel shading overrides for building {bldg_identifier}: {specific_shading_overrides}")
            except ImportError:
                func_logger.warning("shading_overrides_from_excel.py not found. Skipping Excel-based shading overrides.")
            except Exception as e_excel_override:
                func_logger.error(f"Error applying Excel shading overrides for building {row.get('ogc_fid', idx)}: {e_excel_override}", exc_info=True)
        elif isinstance(user_config_shading, dict):
            specific_shading_overrides = user_config_shading

        idf_path = create_idf_for_building(
            building_row=row,
            building_index=idx,
            scenario=scenario,
            calibration_stage=calibration_stage,
            strategy=strategy,
            random_seed=building_specific_seed,
            # geometry
            user_config_geom=user_config_geom,
            assigned_geom_log=assigned_geom_log,
            # lighting
            user_config_lighting=user_config_lighting,
            assigned_lighting_log=assigned_lighting_log,
            # electric equipment
            user_config_equipment=user_config_equipment,
            assigned_equip_log=assigned_equip_log,
            # DHW
            user_config_dhw=user_config_dhw,
            assigned_dhw_log=assigned_dhw_log,
            # Fenestration
            res_data=res_data,
            nonres_data=nonres_data,
            assigned_fenez_log=assigned_fenez_log,
            # Window shading
            shading_type_key_for_blinds=shading_type_key_for_blinds,
            user_config_shading=specific_shading_overrides,
            assigned_shading_log=assigned_shading_log,
            apply_blind_shading=apply_blind_shading,
            apply_geometric_shading=apply_geometric_shading,
            shading_strategy=shading_strategy,
            # HVAC
            user_config_hvac=user_config_hvac,
            assigned_hvac_log=assigned_hvac_log,
            # Vent
            user_config_vent=user_config_vent,
            assigned_vent_log=assigned_vent_log,
            # zone sizing
            assigned_setzone_log=assigned_setzone_log,
            # ground temps
            assigned_groundtemp_log=assigned_groundtemp_log,
            # output definitions
            output_definitions=output_definitions
        )
        if idf_path:
            df_buildings.loc[idx, "idf_name"] = os.path.basename(idf_path)
        else:
            df_buildings.loc[idx, "idf_name"] = "ERROR_CREATING_IDF"
            func_logger.error(f"IDF creation failed for building index {idx}. See previous errors.")

    if run_simulations:
        func_logger.info("Proceeding to run simulations for generated IDFs.")
        if simulate_config is None:
            simulate_config = {}

        sim_output_dir = os.path.join(logs_base_dir, "Sim_Results") if logs_base_dir else simulate_config.get("base_output_dir", "output/Sim_Results")
        os.makedirs(sim_output_dir, exist_ok=True)

        idf_directory = idf_config["output_dir"]
        iddfile       = idf_config["iddfile"]

        simulate_all(
            df_buildings=df_buildings[df_buildings["idf_name"] != "ERROR_CREATING_IDF"],
            idf_directory=idf_directory,
            iddfile=iddfile,
            base_output_dir=sim_output_dir,
            user_config_epw=user_config_epw,
            assigned_epw_log=assigned_epw_log,
            num_workers=simulate_config.get("num_workers", 4),
        )
    else:
        func_logger.info("Skipping simulations as per configuration.")

    if post_process:
        func_logger.info("Proceeding to post-process simulation results and write logs.")

        default_post_process_config = {
            "base_output_dir": "output/Sim_Results",
            "outputs": [{
                "convert_to_daily": False, "convert_to_monthly": False,
                "aggregator": "none", "output_csv": "output/results/merged_as_is.csv"
            }]
        }
        current_post_process_config = post_process_config if post_process_config is not None else default_post_process_config
        
        base_sim_dir_for_merge = os.path.join(logs_base_dir, "Sim_Results") if logs_base_dir else current_post_process_config.get("base_output_dir")
        
        multiple_outputs = current_post_process_config.get("outputs", [])

        for proc_item in multiple_outputs:
            out_csv_path = proc_item.get("output_csv", "output/results/merged_default.csv")
            if logs_base_dir and "output/" in out_csv_path:
                rel_filename = out_csv_path.split("output/", 1)[-1] 
                out_csv_path = os.path.join(logs_base_dir, rel_filename)
            
            os.makedirs(os.path.dirname(out_csv_path), exist_ok=True)

            merge_all_results(
                base_output_dir=base_sim_dir_for_merge,
                output_csv=out_csv_path,
                convert_to_daily=proc_item.get("convert_to_daily", False),
                daily_aggregator=proc_item.get("aggregator", "mean"),
                convert_to_monthly=proc_item.get("convert_to_monthly", False)
            )
            func_logger.info(f"Merged results saved to: {out_csv_path}")

        _write_geometry_csv(assigned_geom_log, logs_base_dir)
        _write_lighting_csv(assigned_lighting_log, logs_base_dir)
        _write_equipment_csv(assigned_equip_log, logs_base_dir)
        _write_fenestration_csv(assigned_fenez_log, logs_base_dir)
        _write_dhw_csv(assigned_dhw_log, logs_base_dir)
        # <--- REPLACED: use new specialized _write_hvac_csv(...) --->
        _write_hvac_csv(assigned_hvac_log, logs_base_dir)
        # <--- REPLACED: use new specialized _write_vent_csv(...) --->
        _write_vent_csv(assigned_vent_log, logs_base_dir)

        _write_shading_csv(assigned_shading_log, logs_base_dir)
        _write_groundtemp_csv(assigned_groundtemp_log, logs_base_dir)
        _write_setzone_csv(assigned_setzone_log, logs_base_dir)
        _write_epw_csv(assigned_epw_log, logs_base_dir)

        func_logger.info("Finished post-processing and writing all assigned parameter logs.")
    else:
        func_logger.info("Skipping post-processing as per configuration.")

    return df_buildings


###############################################################################
# Internal Helper Functions to Write Assigned Logs
###############################################################################
def _make_assigned_path(filename, logs_base_dir):
    assigned_dir = os.path.join(logs_base_dir, "assigned") if logs_base_dir else "output/assigned"
    os.makedirs(assigned_dir, exist_ok=True)
    return os.path.join(assigned_dir, filename)


def _write_generic_log_csv(log_dict, filename_base, id_column_name, logs_base_dir):
    rows = []
    if not log_dict:
        logger.debug(f"Log dictionary for {filename_base} is empty. Skipping CSV write.")
        return
    for item_id, params in log_dict.items():
        if isinstance(params, dict):
            for param_name, param_val in params.items():
                row_data = {id_column_name: item_id, "param_name": param_name}
                if isinstance(param_val, dict):
                    row_data.update(param_val)
                else:
                    row_data["assigned_value"] = param_val
                rows.append(row_data)
        else:
            rows.append({id_column_name: item_id, "param_name": "unknown", "assigned_value": str(params)})

    if not rows:
        logger.debug(f"No rows generated for {filename_base} CSV. Skipping write.")
        return
    
    df = pd.DataFrame(rows)
    common_cols = [id_column_name, "object_name", "param_name", "assigned_value", "min_val", "max_val", "shading_type_key_used", "strategy_used"]
    ordered_cols = [col for col in common_cols if col in df.columns]
    remaining_cols = [col for col in df.columns if col not in ordered_cols]
    df = df[ordered_cols + remaining_cols]

    out_path = _make_assigned_path(f"assigned_{filename_base}.csv", logs_base_dir)
    try:
        df.to_csv(out_path, index=False)
        logger.info(f"Successfully wrote {filename_base} log to {out_path}")
    except Exception as e:
        logger.error(f"Error writing {filename_base} log to {out_path}: {e}", exc_info=True)


def _write_geometry_csv(assigned_geom_log, logs_base_dir):
    _write_generic_log_csv(assigned_geom_log, "geometry", "ogc_fid", logs_base_dir)

def _write_lighting_csv(assigned_lighting_log, logs_base_dir):
    rows = []
    for bldg_id, param_dict in assigned_lighting_log.items():
        for param_key, details in param_dict.items():
            rows.append({
               "ogc_fid": bldg_id,
               "object_name": details.get("object_name", param_key),
               "param_name": param_key,
               "assigned_value": details.get("assigned_value"),
               "min_val": details.get("min_val"),
               "max_val": details.get("max_val")
            })
    if not rows:
        return
    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_lighting.csv", logs_base_dir)
    df.to_csv(out_path, index=False)
    logger.info(f"Lighting log written to {out_path}")


def _write_equipment_csv(assigned_equip_log, logs_base_dir):
    rows = []
    for bldg_id, outer_dict in assigned_equip_log.items():
        param_dict = outer_dict.get("assigned", outer_dict)
        for param_key, details in param_dict.items():
            rows.append({
                "ogc_fid": bldg_id,
                "object_name": details.get("object_name", param_key),
                "param_name": param_key,
                "assigned_value": details.get("assigned_value"),
                "min_val": details.get("min_val"),
                "max_val": details.get("max_val")
            })
    if not rows:
        return
    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_equipment.csv", logs_base_dir)
    df.to_csv(out_path, index=False)
    logger.info(f"Equipment log written to {out_path}")


def _write_fenestration_csv(assigned_fenez_log, logs_base_dir):
    _write_generic_log_csv(assigned_fenez_log, "fenez_params", "ogc_fid", logs_base_dir)

def _write_dhw_csv(assigned_dhw_log, logs_base_dir):
    _write_generic_log_csv(assigned_dhw_log, "dhw_params", "ogc_fid", logs_base_dir)


###############################################################################
# UPDATED: Specialized code to ensure HVAC CSV has "assigned_value" column
###############################################################################
def _write_hvac_csv(assigned_hvac_log, logs_base_dir):
    """
    Specialized function to flatten building-level vs. zone-level HVAC data
    into rows each containing an 'assigned_value'.
    """
    rows = []
    if not assigned_hvac_log:
        logger.debug("HVAC log is empty. Skipping CSV.")
        return

    for bldg_id, hvac_data in assigned_hvac_log.items():
        # 1) building-level HVAC parameters
        hvac_params = hvac_data.get("hvac_params", {})
        for param_name, param_val in hvac_params.items():
            rows.append({
                "ogc_fid": bldg_id,
                "zone_name": None,
                "param_name": param_name,
                "assigned_value": param_val
            })

        # 2) zone-level HVAC parameters
        if "zones" in hvac_data:
            for zone_name, zone_info in hvac_data["zones"].items():
                for param_name, param_val in zone_info.items():
                    rows.append({
                        "ogc_fid": bldg_id,
                        "zone_name": zone_name,
                        "param_name": param_name,
                        "assigned_value": param_val
                    })

    if not rows:
        logger.debug("No rows generated for assigned_hvac_params.csv. Skipping write.")
        return

    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_hvac_params.csv", logs_base_dir)
    df.to_csv(out_path, index=False)
    logger.info(f"HVAC log written to {out_path}")


###############################################################################
# UPDATED: Specialized code to ensure Vent CSV has "assigned_value" column
###############################################################################
def _write_vent_csv(assigned_vent_log, logs_base_dir):
    """
    Specialized function to flatten building-level vs. zone-level Vent data
    into rows each containing an 'assigned_value'.
    """
    rows = []
    if not assigned_vent_log:
        logger.debug("Ventilation log is empty. Skipping CSV.")
        return

    for bldg_id, vent_data in assigned_vent_log.items():
        # 1) building-level ventilation parameters
        bld_params = vent_data.get("building_params", {})
        for param_name, param_val in bld_params.items():
            rows.append({
                "ogc_fid": bldg_id,
                "zone_name": None,
                "param_name": param_name,
                "assigned_value": param_val
            })

        # 2) schedule_details
        sched_details = vent_data.get("schedule_details", {})
        for param_name, param_val in sched_details.items():
            rows.append({
                "ogc_fid": bldg_id,
                "zone_name": None,
                "param_name": param_name,
                "assigned_value": param_val
            })

        # 3) zone-level ventilation parameters
        zones_dict = vent_data.get("zones", {})
        for zone_name, zinfo in zones_dict.items():
            for param_name, param_val in zinfo.items():
                rows.append({
                    "ogc_fid": bldg_id,
                    "zone_name": zone_name,
                    "param_name": param_name,
                    "assigned_value": param_val
                })

    if not rows:
        logger.debug("No rows generated for assigned_ventilation.csv. Skipping write.")
        return

    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_ventilation.csv", logs_base_dir)
    df.to_csv(out_path, index=False)
    logger.info(f"Ventilation log written to {out_path}")


def _write_shading_csv(assigned_shading_log, logs_base_dir):
    rows = []
    for window_id, data_for_window in assigned_shading_log.items():
        shading_params = data_for_window.get("shading_params_picked", {})
        status = data_for_window.get("shading_creation_status", "")
        type_key = data_for_window.get("shading_type_key_used", "")
        strategy = data_for_window.get("strategy_used", "")
        control_name = data_for_window.get("shading_control_name_assigned", "")
        blind_mat_name = data_for_window.get("blind_material_name_used", "")

        if not shading_params and not status:
            continue

        base_row_info = {
            "window_id": window_id,
            "shading_type_key": type_key,
            "strategy": strategy,
            "creation_status": status,
            "control_name": control_name,
            "blind_material_name": blind_mat_name
        }

        if shading_params:
            for param_name, param_val in shading_params.items():
                row = base_row_info.copy()
                row["param_name"] = param_name
                row["assigned_value"] = str(param_val)
                rows.append(row)
        else:
            row = base_row_info.copy()
            row["param_name"] = "N/A"
            row["assigned_value"] = "N/A (No params picked or error)"
            rows.append(row)
            
    if not rows:
        logger.debug("No data to write for assigned_shading_params.csv")
        return
        
    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_shading_params.csv", logs_base_dir)
    df.to_csv(out_path, index=False)
    logger.info(f"Shading parameters log written to {out_path}")


def _write_groundtemp_csv(assigned_groundtemp_log, logs_base_dir):
    _write_generic_log_csv(assigned_groundtemp_log, "ground_temperatures", "building_id_or_global", logs_base_dir)

def _write_setzone_csv(assigned_setzone_log, logs_base_dir):
    _write_generic_log_csv(assigned_setzone_log, "zone_sizing_outdoor_air", "ogc_fid", logs_base_dir)

def _write_epw_csv(assigned_epw_log, logs_base_dir):
    _write_generic_log_csv(assigned_epw_log, "epw_assignments", "ogc_fid", logs_base_dir)
