"""
idf_creation.py

Description:
  This module handles the creation of EnergyPlus IDF files for a list of buildings. 
  It applies geometry, fenestration, HVAC, DHW, lighting, and ventilation settings 
  (plus any user/Excel overrides), and can optionally run simulations and post-process the results.

Key Steps:
  1) Loop over each building in df_buildings.
  2) create_idf_for_building(...):
     - Sets up a base IDF using geomeppy
     - Applies geometry (roof type, orientation, etc.)
     - Creates or updates materials/constructions
     - Adds fenestration (window surfaces) based on final "res_data" or "nonres_data"
       which contain all Excel + JSON user overrides for fenestration
     - Adds lighting, DHW, HVAC, ventilation, zone sizing, ground temps, etc.
     - Saves the resulting IDF to disk
  3) If run_simulations=True, it calls simulate_all(...) to run E+ simulations in parallel.
  4) If post_process=True, merges the simulation outputs and writes CSV logs for assigned parameters.

Important: This file references sub-modules for geometry, fenestration, lighting, etc.
           You must have those modules present in your codebase, e.g.:
             idf_objects.geomz.building
             idf_objects.fenez.fenestration
             idf_objects.fenez.materials
             epw.run_epw_sims
             postproc.merge_results
             ... etc.
"""

import os
import logging
import pandas as pd

# geomeppy for IDF manipulation
from geomeppy import IDF

# Geometry modules (example placeholders)
from idf_objects.geomz.building import create_building_with_roof_type

# Fenestration & materials
from idf_objects.fenez.fenestration import add_fenestration
from idf_objects.fenez.materials import (
    update_construction_materials,
    assign_constructions_to_surfaces
)

# Lighting (example placeholders)
from idf_objects.Elec.lighting import add_lights_and_parasitics

# DHW (example placeholders)
from idf_objects.DHW.water_heater import add_dhw_to_idf

# HVAC (example placeholders)
from idf_objects.HVAC.custom_hvac import add_HVAC_Ideal_to_all_zones

# Ventilation (example placeholders)
from idf_objects.ventilation.add_ventilation import add_ventilation_to_idf

# Zone Sizing (example placeholders)
from idf_objects.setzone.add_outdoor_air_and_zone_sizing_to_all_zones import add_outdoor_air_and_zone_sizing_to_all_zones

# Ground Temps (example placeholder)
from idf_objects.tempground.add_ground_temperatures import add_ground_temperatures

from idf_objects.other.zonelist import create_zonelist



# Outputs & Simulations (example placeholders)
from idf_objects.outputdef.assign_output_settings import assign_output_settings
from idf_objects.outputdef.add_output_definitions import add_output_definitions
from postproc.merge_results import merge_all_results

# EPW & simulations
from epw.run_epw_sims import simulate_all

###############################################################################
# Default IDF config - update paths as needed
###############################################################################
idf_config = {
    "iddfile":       r"D:/EnergyPlus/Energy+.idd",  # Path to the Energy+.idd
    "idf_file_path": r"D:/Minimal.idf",            # A base minimal IDF for geomeppy
    "output_dir":    r"output/output_IDFs"         # Folder where we'll save each building's IDF
}

###############################################################################
# create_idf_for_building
###############################################################################
def create_idf_for_building(
    building_row,
    building_index,
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="B",
    random_seed=42,
    # geometry overrides & log
    user_config_geom=None,
    assigned_geom_log=None,
    # lighting
    user_config_lighting=None,
    assigned_lighting_log=None,
    # DHW
    user_config_dhw=None,
    assigned_dhw_log=None,
    # Fenestration
    res_data=None,       # final residential fenestration dict (with overrides)
    nonres_data=None,    # final non-res fenestration dict (with overrides)
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
    assigned_groundtemp_log=None
):
    """
    Builds an IDF for a single building row, applying all relevant overrides/logs.
    Returns the filename of the saved IDF.

    Parameters
    ----------
    building_row : Series or dict
        Contains building attributes (area, perimeter, orientation, etc.)
    building_index : int
        Index in df_buildings (or a building ID)
    scenario : str
    calibration_stage : str
    strategy : str
        "A" => pick midpoint in range, "B" => pick random uniform, etc.
    random_seed : int
        For reproducible random picks.
    user_config_* : various
        Partial user override arrays from JSON, if needed
    assigned_*_log : dict
        If provided, we store the assigned final picks/ranges in it for CSV logging
    res_data, nonres_data : dict
        Fenestration/material dictionaries after Excel + JSON merges

    Returns
    -------
    out_path : str
        The path to the saved IDF file
    """
    # 1) Setup IDF from a minimal template
    IDF.setiddname(idf_config["iddfile"])
    idf = IDF(idf_config["idf_file_path"])

    # 2) Basic building object settings
    building_obj = idf.newidfobject("BUILDING")
    building_obj.Name = f"Sample_Building_{building_index}"

    orientation = building_row.get("building_orientation", 0.0)
    if not pd.isna(orientation):
        building_obj.North_Axis = orientation

    # 3) Geometry
    if assigned_geom_log is not None and building_row.get("ogc_fid") not in assigned_geom_log:
        assigned_geom_log[building_row.get("ogc_fid")] = {}

    edge_types = []
    for side_col in ["north_side", "east_side", "south_side", "west_side"]:
        edge_types.append(building_row.get(side_col, "facade"))

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

    # 4) Materials & Constructions
    construction_map = update_construction_materials(
        idf=idf,
        building_row=building_row,
        building_index=building_index,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_fenez=None,  # no direct user_config_fenez needed; we have res_data/nonres_data
        assigned_fenez_log=assigned_fenez_log
    )
    assign_constructions_to_surfaces(idf, construction_map)



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

    # 7) DHW
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

    # 8) HVAC
    add_HVAC_Ideal_to_all_zones(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_hvac=user_config_hvac,
        assigned_hvac_log=assigned_hvac_log
    )

    # 9) Ventilation
    add_ventilation_to_idf(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_vent=user_config_vent,
        assigned_vent_log=assigned_vent_log
    )

    # 10) Zone Sizing
    add_outdoor_air_and_zone_sizing_to_all_zones(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        assigned_setzone_log=assigned_setzone_log
    )

    # 11) Ground Temps
    add_ground_temperatures(
        idf=idf,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        assigned_groundtemp_log=assigned_groundtemp_log
    )

    # 12) Output definitions
    desired_vars   = ["Facility Total Electric Demand Power", "Zone Air Temperature"]
    desired_meters = ["Electricity:Facility"]

    out_settings = assign_output_settings(
        desired_variables=desired_vars,
        desired_meters=desired_meters,
        override_variable_frequency="Hourly",
        override_meter_frequency="Hourly",
        include_tables=True,
        include_summary=True
    )
    add_output_definitions(idf, out_settings)

    # 13) Save final IDF
    os.makedirs(idf_config["output_dir"], exist_ok=True)
    idf_filename = f"building_{building_index}.idf"
    out_path = os.path.join(idf_config["output_dir"], idf_filename)
    idf.save(out_path)
    print(f"[create_idf_for_building] IDF saved at: {out_path}")

    return out_path


###############################################################################
# create_idfs_for_all_buildings
###############################################################################
def create_idfs_for_all_buildings(
    df_buildings,
    scenario="scenario1",
    calibration_stage="pre_calibration",
    strategy="B",
    random_seed=42,
    # partial user configs
    user_config_geom=None,
    user_config_lighting=None,
    user_config_dhw=None,
    res_data=None,       # final res fenestration dict
    nonres_data=None,    # final non-res fenestration dict
    user_config_hvac=None,
    user_config_vent=None,
    user_config_epw=None,       # <--- NEW: pass EPW overrides here
    # simulation & postprocess
    run_simulations=True,
    simulate_config=None,
    post_process=True
):
    """
    Loops over df_buildings, calls create_idf_for_building for each building, 
    optionally runs E+ simulations, merges results, and writes assigned CSV logs.

    Parameters
    ----------
    df_buildings : pd.DataFrame
        Must contain columns like area, perimeter, orientation, ogc_fid, etc.
    scenario : str
    calibration_stage : str
    strategy : str
        "A" => midpoint picks, "B" => random uniform, etc.
    random_seed : int
    user_config_* : various
        Partial user overrides from JSON for geometry, lighting, etc.
    res_data, nonres_data : dict
        Fenestration dictionaries with Excel + JSON overrides
    run_simulations : bool
    simulate_config : dict
        e.g. {"num_workers": 4}
    post_process : bool
    """
    logger = logging.getLogger(__name__)

    # A) Prepare dictionaries to store final picks for each module
    assigned_geom_log        = {}
    assigned_lighting_log    = {}
    assigned_dhw_log         = {}
    assigned_fenez_log       = {}  # for fenestration
    assigned_hvac_log        = {}
    assigned_vent_log        = {}
    assigned_epw_log         = {}
    assigned_groundtemp_log  = {}
    assigned_setzone_log     = {}

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
            assigned_groundtemp_log=assigned_groundtemp_log
        )
        df_buildings.loc[idx, "idf_name"] = os.path.basename(idf_path)

    # C) If requested, run simulations
    if run_simulations:
        logger.info("[create_idfs_for_all_buildings] => Running simulations ...")
        idf_directory = idf_config["output_dir"]
        iddfile       = idf_config["iddfile"]
        base_output_dir = "output/Sim_Results"

        if simulate_config is None:
            simulate_config = {}
        num_workers = simulate_config.get("num_workers", 4)

        # Example call to your parallel simulation function
        simulate_all(
            df_buildings=df_buildings,
            idf_directory=idf_directory,
            iddfile=iddfile,
            base_output_dir=base_output_dir,
            user_config_epw=user_config_epw,   # <--- ensures override logic is used
            assigned_epw_log=assigned_epw_log,  # if you use it
            num_workers=num_workers
        )

    # D) If requested, post-process results and write assigned CSV logs
    if post_process:
        logger.info("[create_idfs_for_all_buildings] => Post-processing results & writing logs ...")

        base_output_dir = "output/Sim_Results"
        out_csv_as_is = "output/results/merged_as_is.csv"
        merge_all_results(
            base_output_dir=base_output_dir,
            output_csv=out_csv_as_is,
            convert_to_daily=False,
            convert_to_monthly=False
        )

        # Example daily mean
        out_csv_daily_mean = "output/results/merged_daily_mean.csv"
        merge_all_results(
            base_output_dir=base_output_dir,
            output_csv=out_csv_daily_mean,
            convert_to_daily=True,
            daily_aggregator="mean",
            convert_to_monthly=False
        )

        # Now write out CSV logs for each assigned_* dictionary
        _write_geometry_csv(assigned_geom_log)
        _write_lighting_csv(assigned_lighting_log)
        _write_fenestration_csv(assigned_fenez_log)
        _write_dhw_csv(assigned_dhw_log)
        _write_hvac_csv(assigned_hvac_log)
        _write_vent_csv(assigned_vent_log)
        # etc. (EPW, groundtemps, setzone)...

        logger.info("[create_idfs_for_all_buildings] => Done post-processing.")

    return df_buildings  # with an "idf_name" column


###############################################################################
# Helper functions to write assigned logs
###############################################################################
def _write_geometry_csv(assigned_geom_log):
    import pandas as pd
    rows = []
    for bldg_id, param_dict in assigned_geom_log.items():
        for param_name, param_val in param_dict.items():
            rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,
                "assigned_value": param_val
            })
    df = pd.DataFrame(rows)
    os.makedirs("output/assigned", exist_ok=True)
    out_path = "output/assigned/assigned_geometry.csv"
    df.to_csv(out_path, index=False)


def _write_lighting_csv(assigned_lighting_log):
    import pandas as pd
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
    df = pd.DataFrame(rows)
    os.makedirs("output/assigned", exist_ok=True)
    out_path = "output/assigned/assigned_lighting.csv"
    df.to_csv(out_path, index=False)


def _write_fenestration_csv(assigned_fenez_log):
    import pandas as pd
    rows = []
    for bldg_id, param_dict in assigned_fenez_log.items():
        for key, val in param_dict.items():
            # e.g. key="fenez_final_wwr", val=0.27 or key="fenez_wwr_range_used", val=(0.25, 0.3)
            rows.append({
                "ogc_fid": bldg_id,
                "param_name": key,
                "assigned_value": val
            })
    df = pd.DataFrame(rows)
    os.makedirs("output/assigned", exist_ok=True)
    out_path = "output/assigned/assigned_fenez_params.csv"
    df.to_csv(out_path, index=False)


def _write_dhw_csv(assigned_dhw_log):
    import pandas as pd
    rows = []
    for bldg_id, param_dict in assigned_dhw_log.items():
        for param_name, param_val in param_dict.items():
            rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,
                "assigned_value": param_val
            })
    df = pd.DataFrame(rows)
    os.makedirs("output/assigned", exist_ok=True)
    out_path = "output/assigned/assigned_dhw_params.csv"
    df.to_csv(out_path, index=False)


def _write_hvac_csv(assigned_hvac_log):
    import pandas as pd
    rows = []
    for bldg_id, param_dict in assigned_hvac_log.items():
        for param_name, param_val in param_dict.items():
            rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,
                "assigned_value": param_val
            })
    df = pd.DataFrame(rows)
    os.makedirs("output/assigned", exist_ok=True)
    out_path = "output/assigned/assigned_hvac_params.csv"
    df.to_csv(out_path, index=False)


def _write_vent_csv(assigned_vent_log):
    import pandas as pd
    rows = []
    for bldg_id, param_dict in assigned_vent_log.items():
        for param_name, param_val in param_dict.items():
            rows.append({
                "ogc_fid": bldg_id,
                "param_name": param_name,
                "assigned_value": param_val
            })
    df = pd.DataFrame(rows)
    os.makedirs("output/assigned", exist_ok=True)
    out_path = "output/assigned/assigned_ventilation.csv"
    df.to_csv(out_path, index=False)
