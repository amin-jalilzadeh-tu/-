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
from idf_objects.setzone.add_outdoor_air_and_zone_sizing_to_all_zones import add_outdoor_air_and_zone_sizing_to_all_zones
from idf_objects.tempground.add_ground_temperatures import add_ground_temperatures
from idf_objects.other.zonelist import create_zonelist

# Output & simulation modules
from idf_objects.outputdef.assign_output_settings import assign_output_settings
from idf_objects.outputdef.add_output_definitions import add_output_definitions
from postproc.merge_results import merge_all_results
from epw.run_epw_sims import simulate_all

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
    strategy="B",
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
    Build an IDF for a single building, applying geometry, fenestration, lighting,
    HVAC, ventilation, zone sizing, ground temps, and user overrides.

    Returns
    -------
    out_path : str
        File path to the saved IDF.
    """
    # 1) Setup IDF from the minimal template
    IDF.setiddname(idf_config["iddfile"])
    idf = IDF(idf_config["idf_file_path"])

    # 2) Basic building object settings
    building_obj = idf.newidfobject("BUILDING")
    building_obj.Name = f"Sample_Building_{building_index}"

    orientation = building_row.get("building_orientation", 0.0)



    # for orientation correction this changed 
    #if not pd.isna(orientation):
    #    building_obj.North_Axis = orientation






    if pd.isna(orientation):
        orientation = 0.0

    # Apply orientation when creating geometry.  The BUILDING object's
    # North_Axis is kept at 0 so that the rotated geometry correctly
    # represents the building's orientation in the world coordinate system.
    building_obj.North_Axis = 0.0









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
        strategy=strategy,
        random_seed=random_seed,
        user_config=user_config_geom,
        assigned_geom_log=assigned_geom_log
    )

    # 4) Update materials & constructions
    construction_map = update_construction_materials(
        idf=idf,
        building_row=building_row,
        building_index=building_index,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_fenez=None,  # not used directly
        assigned_fenez_log=assigned_fenez_log
    )
    assign_constructions_to_surfaces(idf, construction_map)

    # Create zone list for convenience
    create_zonelist(idf, zonelist_name="ALL_ZONES")

    # 5) Fenestration
    add_fenestration(
        idf=idf,
        building_row=building_row,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        res_data=res_data,
        nonres_data=nonres_data,
        assigned_fenez_log=assigned_fenez_log
    )

    # 6) Lighting
    add_lights_and_parasitics(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config=user_config_lighting,
        assigned_values_log=assigned_lighting_log
    )

    # 7) Electric equipment
    add_electric_equipment(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config=user_config_equipment,
        assigned_values_log=assigned_equip_log,
        zonelist_name="ALL_ZONES",
    )
    # 8) DHW
    add_dhw_to_idf(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        name_suffix=f"MyDHW_{building_index}",
        user_config_dhw=user_config_dhw,
        assigned_dhw_log=assigned_dhw_log,
        use_nta=True
    )

    # 9) HVAC
    add_HVAC_Ideal_to_all_zones(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_hvac=user_config_hvac,
        assigned_hvac_log=assigned_hvac_log
    )

    # 10) Ventilation
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

    # 11) Zone sizing
    add_outdoor_air_and_zone_sizing_to_all_zones(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        assigned_setzone_log=assigned_setzone_log
    )

    # 12) Ground temperatures
    add_ground_temperatures(
        idf=idf,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        assigned_groundtemp_log=assigned_groundtemp_log
    )

    # 13) Output definitions
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

    # 13) Save final IDF
    os.makedirs(idf_config["output_dir"], exist_ok=True)
    idf_filename = f"building_{building_index}.idf"
    out_path = os.path.join(idf_config["output_dir"], idf_filename)
    idf.save(out_path)
    print(f"[create_idf_for_building] IDF saved at: {out_path}")

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
    res_data=None,
    nonres_data=None,
    user_config_hvac=None,
    user_config_vent=None,
    user_config_epw=None,  # pass epw config or list if relevant
    # output definitions
    output_definitions=None,
    # simulation & postprocess
    run_simulations=True,
    simulate_config=None,
    post_process=True,
    post_process_config=None,
    # NEW: Where to store logs and results
    logs_base_dir=None
):
    """
    Loops over df_buildings, calls create_idf_for_building for each building,
    optionally runs E+ simulations in parallel, and merges results if post_process=True.

    If logs_base_dir is provided, all assigned_*.csv and merged results go under that folder
    (e.g. logs_base_dir/assigned, logs_base_dir/Sim_Results, etc.).
    """
    logger = logging.getLogger(__name__)

    # A) Prepare dictionaries to store final picks for each module
    assigned_geom_log       = {}
    assigned_lighting_log   = {}
    assigned_equip_log      = {}
    assigned_dhw_log        = {}
    assigned_fenez_log      = {}
    assigned_hvac_log       = {}
    assigned_vent_log       = {}
    assigned_epw_log        = {}
    assigned_groundtemp_log = {}
    assigned_setzone_log    = {}

    # B) Create an IDF for each building
    for idx, row in df_buildings.iterrows():
        bldg_id = row.get("ogc_fid", idx)
        logger.info(f"--- Creating IDF for building index {idx}, ogc_fid={bldg_id} ---")

        idf_path = create_idf_for_building(
            building_row=row,
            building_index=idx,
            scenario=scenario,
            calibration_stage=calibration_stage,
            strategy=strategy,
            random_seed=random_seed,
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
        # Store the final IDF filename in df_buildings
        df_buildings.loc[idx, "idf_name"] = os.path.basename(idf_path)

    # C) If we’re told to run simulations
    if run_simulations:
        logger.info("[create_idfs_for_all_buildings] => Running simulations ...")
        if simulate_config is None:
            simulate_config = {}

        # Decide on a base_output_dir for sim results
        if logs_base_dir:
            sim_output_dir = os.path.join(logs_base_dir, "Sim_Results")
        else:
            sim_output_dir = simulate_config.get("base_output_dir", "output/Sim_Results")

        idf_directory = idf_config["output_dir"]
        iddfile       = idf_config["iddfile"]

        simulate_all(
            df_buildings=df_buildings,
            idf_directory=idf_directory,
            iddfile=iddfile,
            base_output_dir=sim_output_dir,
            user_config_epw=user_config_epw,
            assigned_epw_log=assigned_epw_log,
            num_workers=simulate_config.get("num_workers", 4)
            # ep_force_overwrite=simulate_config.get("ep_force_overwrite", False)
        )

    # D) Post-processing
    if post_process:
        logger.info("[create_idfs_for_all_buildings] => Post-processing results & writing logs ...")

        if post_process_config is None:
            post_process_config = {
                "base_output_dir": "output/Sim_Results",
                "outputs": [
                    {
                        "convert_to_daily": False,
                        "convert_to_monthly": False,
                        "aggregator": "none",
                        "output_csv": "output/results/merged_as_is.csv"
                    }
                ]
            }

        # If logs_base_dir is set, we override base_output_dir
        if logs_base_dir:
            post_process_config["base_output_dir"] = os.path.join(logs_base_dir, "Sim_Results")

        base_output_dir = post_process_config.get("base_output_dir", "output/Sim_Results")
        multiple_outputs = post_process_config.get("outputs", [])

        # Possibly handle multiple post-process outputs
        for proc_item in multiple_outputs:
            convert_daily = proc_item.get("convert_to_daily", False)
            convert_monthly = proc_item.get("convert_to_monthly", False)
            aggregator = proc_item.get("aggregator", "mean")  # daily aggregator
            out_csv = proc_item.get("output_csv", "output/results/merged_default.csv")

            # If logs_base_dir is set and the out_csv is still something like "output/results/..."
            # We can relocate it under logs_base_dir, e.g. logs_base_dir/results
            # Let's do a check:
            if logs_base_dir and "output/" in out_csv:
                # redirect to logs_base_dir
                # e.g. logs_base_dir/results/merged_default.csv
                # you can pick your subfolder naming
                rel_filename = out_csv.split("output/")[-1]  # e.g. results/merged_default.csv
                out_csv = os.path.join(logs_base_dir, rel_filename)

            # Make sure directory exists
            os.makedirs(os.path.dirname(out_csv), exist_ok=True)

            # Now merge the results
            merge_all_results(
                base_output_dir=base_output_dir,
                output_csv=out_csv,
                convert_to_daily=convert_daily,
                daily_aggregator=aggregator,
                convert_to_monthly=convert_monthly
            )

        # Write CSV logs for assigned parameters
        _write_geometry_csv(assigned_geom_log, logs_base_dir)
        _write_lighting_csv(assigned_lighting_log, logs_base_dir)
        _write_equipment_csv(assigned_equip_log, logs_base_dir)
        _write_fenestration_csv(assigned_fenez_log, logs_base_dir)
        _write_dhw_csv(assigned_dhw_log, logs_base_dir)
        _write_hvac_csv(assigned_hvac_log, logs_base_dir)
        _write_vent_csv(assigned_vent_log, logs_base_dir)
        # (If needed, also EPW or groundtemp logs, do similarly)

        logger.info("[create_idfs_for_all_buildings] => Done post-processing.")

    return df_buildings  # includes "idf_name" column


###############################################################################
# Internal Helper Functions to Write Assigned Logs
# -- Now accept logs_base_dir so we can place them in job_output_dir
###############################################################################
def _make_assigned_path(filename, logs_base_dir):
    """Helper to build the path for assigned_*.csv, given logs_base_dir."""
    if logs_base_dir:
        assigned_dir = os.path.join(logs_base_dir, "assigned")
    else:
        assigned_dir = "output/assigned"

    os.makedirs(assigned_dir, exist_ok=True)
    return os.path.join(assigned_dir, filename)


def _write_geometry_csv(assigned_geom_log, logs_base_dir):
    rows = []
    for bldg_id, param_dict in assigned_geom_log.items():
        for param_name, param_val in param_dict.items():
            rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,
                "assigned_value": param_val
            })
    if not rows:
        return
    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_geometry.csv", logs_base_dir)
    df.to_csv(out_path, index=False)


def _write_lighting_csv(assigned_lighting_log, logs_base_dir):
    rows = []
    for bldg_id, param_dict in assigned_lighting_log.items():
        for param_name, subdict in param_dict.items():
            assigned_val = subdict.get("assigned_value")
            min_v = subdict.get("min_val")
            max_v = subdict.get("max_val")
            obj_name = subdict.get("object_name", "")
            rows.append({
                "ogc_fid": bldg_id,
                "object_name": obj_name,
                "param_name": param_name,
                "assigned_value": assigned_val,
                "min_val": min_v,
                "max_val": max_v
            })
    if not rows:
        return
    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_lighting.csv", logs_base_dir)
    df.to_csv(out_path, index=False)


def _write_fenestration_csv(assigned_fenez_log, logs_base_dir):
    rows = []
    for bldg_id, param_dict in assigned_fenez_log.items():
        for key, val in param_dict.items():
            rows.append({
                "ogc_fid": bldg_id,
                "param_name": key,
                "assigned_value": val
            })
    if not rows:
        return
    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_fenez_params.csv", logs_base_dir)
    df.to_csv(out_path, index=False)


def _write_dhw_csv(assigned_dhw_log, logs_base_dir):
    rows = []
    for bldg_id, param_dict in assigned_dhw_log.items():
        for param_name, param_val in param_dict.items():
            rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,
                "assigned_value": param_val
            })
    if not rows:
        return
    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_dhw_params.csv", logs_base_dir)
    df.to_csv(out_path, index=False)


def _write_hvac_csv(assigned_hvac_log, logs_base_dir):
    rows = []
    for bldg_id, param_dict in assigned_hvac_log.items():
        for param_name, param_val in param_dict.items():
            rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,
                "assigned_value": param_val
            })
    if not rows:
        return
    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_hvac_params.csv", logs_base_dir)
    df.to_csv(out_path, index=False)


def _write_vent_csv(assigned_vent_log, logs_base_dir):
    rows = []
    for bldg_id, param_dict in assigned_vent_log.items():
        for param_name, param_val in param_dict.items():
            rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,
                "assigned_value": param_val
            })
    if not rows:
        return
    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_ventilation.csv", logs_base_dir)
    df.to_csv(out_path, index=False)


def _write_equipment_csv(assigned_equip_log, logs_base_dir):
    rows = []
    for bldg_id, param_dict in assigned_equip_log.items():
        for param_name, param_val in param_dict.items():
            rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,
                "assigned_value": param_val,
            })
    if not rows:
        return
    df = pd.DataFrame(rows)
    out_path = _make_assigned_path("assigned_equipment.csv", logs_base_dir)
    df.to_csv(out_path, index=False)
