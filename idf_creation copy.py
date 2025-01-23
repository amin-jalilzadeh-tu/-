"""
idf_creation.py

Description:
  - This module handles the creation of EnergyPlus IDF files for a set of buildings.
  - It applies geometry, fenestration, HVAC, DHW, lighting, and ventilation settings,
    including any in-memory overrides.
  - It can also run simulations (via `simulate_all`) and post-process results
    (via `merge_all_results`), logging assigned parameters to CSV for tracking.

Usage in your main.py:
  from idf_creation import create_idfs_for_all_buildings
  
  # Then call:
  create_idfs_for_all_buildings(
      df_buildings=some_dataframe,
      scenario="scenario1",
      user_config_geom=...,
      user_config_lighting=...,
      ...
  )
"""

import os
import logging
import pandas as pd

from geomeppy import IDF

# Geometry modules
from idf_objects.geomz.building import create_building_with_roof_type
from idf_objects.geomz.geometry_overrides_from_excel import read_geometry_overrides_excel

# Fenestration & Materials
from idf_objects.fenez.fenestration import add_fenestration
from idf_objects.fenez.materials import update_construction_materials, assign_constructions_to_surfaces
from idf_objects.fenez.dict_override_excel import override_dictionaries_from_excel

# Lighting
from idf_objects.Elec.lighting import add_lights_and_parasitics
from idf_objects.Elec.lighting_lookup import lighting_lookup
from idf_objects.Elec.lighting_overrides_from_excel import (
    read_lighting_overrides_from_excel, 
    apply_lighting_overrides_to_lookup
)

# DHW
from idf_objects.DHW.water_heater import add_dhw_to_idf
from idf_objects.DHW.dhw_lookup import dhw_lookup as default_dhw_lookup
from idf_objects.DHW import dhw_lookup as dhw_lookup_module
from idf_objects.DHW.dhw_overrides_from_excel import override_dhw_lookup_from_excel

# HVAC
from idf_objects.HVAC.custom_hvac import add_HVAC_Ideal_to_all_zones
from idf_objects.HVAC.hvac_lookup import hvac_lookup
from idf_objects.HVAC.hvac_overrides_from_excel import (
    read_hvac_overrides_from_excel, 
    apply_hvac_overrides_to_lookup
)

# Ventilation
from idf_objects.ventilation.add_ventilation import add_ventilation_to_idf
from idf_objects.ventilation.ventilation_lookup import ventilation_lookup
from idf_objects.ventilation.ventilation_overrides_from_excel import (
    read_ventilation_overrides_from_excel,
    apply_ventilation_overrides_to_lookup
)

# Zone Sizing
from idf_objects.setzone.add_outdoor_air_and_zone_sizing_to_all_zones import add_outdoor_air_and_zone_sizing_to_all_zones

# Ground Temps
from idf_objects.tempground.add_ground_temperatures import add_ground_temperatures

# Outputs & Simulations
from idf_objects.outputdef.assign_output_settings import assign_output_settings
from idf_objects.outputdef.add_output_definitions import add_output_definitions
from postproc.merge_results import merge_all_results
from idf_objects.other.zonelist import create_zonelist

# EPW & simulations
from epw.run_epw_sims import simulate_all
from epw.epw_lookup import epw_lookup
from epw.epw_overrides_from_excel import read_epw_overrides_from_excel, apply_epw_overrides_to_lookup

# Materials data
from idf_objects.fenez.data_materials_residential import residential_materials_data
from idf_objects.fenez.data_materials_non_residential import non_residential_materials_data

# Shading
from idf_objects.shading.shading import add_shading_to_idf

# Default global flags (example)
CALIBRATION_STAGE = "pre_calibration"
STRATEGY = "B"
RANDOM_SEED = 42

# IDF config
idf_config = {
    "iddfile": "D:/EnergyPlus/Energy+.idd",
    "idf_file_path": "D:/Minimal.idf",       # base IDF
    "output_dir": "output/output_IDFs"       # folder to save generated IDFs
}


def create_idf_for_building(
    building_row,
    building_index,
    scenario="scenario1",
    calibration_stage=CALIBRATION_STAGE,
    strategy=STRATEGY,
    random_seed=RANDOM_SEED,
    # geometry & lighting overrides + logs
    user_config_geom=None,
    assigned_geom_log=None,
    user_config_lighting=None,
    assigned_lighting_log=None,
    # DHW overrides + logs
    user_config_dhw=None,
    assigned_dhw_log=None,
    # Fenestration / Materials
    user_config_fenez=None,
    assigned_fenez_log=None,
    # HVAC
    user_config_hvac=None,
    assigned_hvac_log=None,
    # Ventilation
    user_config_vent=None,
    assigned_vent_log=None,
    # Zone sizing
    assigned_setzone_log=None,
    # Ground temps
    assigned_groundtemp_log=None,
    # Shading info (if needed)
    df_bldg_shading=None,
    df_trees_shading=None,
    assigned_shading_log=None
):
    """
    Builds an IDF for a single building row, applying all relevant overrides/logging.
    Returns the filename of the saved IDF.
    """
    # 1) Setup IDF
    IDF.setiddname(idf_config["iddfile"])
    idf = IDF(idf_config["idf_file_path"])

    building_obj = idf.newidfobject("BUILDING")
    building_obj.Name = f"Sample_Building_{building_index}"

    orientation = building_row.get("building_orientation", 0.0)
    if not pd.isna(orientation):
        building_obj.North_Axis = orientation

    # 2) Geometry
    edge_types = []
    for side_col in ["north_side", "east_side", "south_side", "west_side"]:
        edge_types.append(building_row.get(side_col, "facade"))

    create_building_with_roof_type(
        idf=idf,
        area=building_row["area"],
        perimeter=building_row["perimeter"],
        orientation=orientation,
        building_row=building_row,
        edge_types=edge_types,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config=user_config_geom,
        assigned_geom_log=assigned_geom_log
    )

    # 3) Materials & Constructions
    construction_map = update_construction_materials(
        idf=idf,
        building_row=building_row,
        building_index=building_index,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_fenez=user_config_fenez,
        assigned_fenez_log=assigned_fenez_log
    )
    assign_constructions_to_surfaces(idf, construction_map)

    # 4) Fenestration
    add_fenestration(
        idf=idf,
        building_row=building_row,
        scenario=scenario,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_fenez=user_config_fenez,
        assigned_fenez_log=assigned_fenez_log
    )

    # Create a zone list
    create_zonelist(idf, zonelist_name="ALL_ZONES")

    # 5) Lighting
    add_lights_and_parasitics(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config=user_config_lighting,
        assigned_values_log=assigned_lighting_log
    )

    # 6) DHW
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

    # 7) HVAC
    add_HVAC_Ideal_to_all_zones(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_hvac=user_config_hvac,
        assigned_hvac_log=assigned_hvac_log
    )

    # 8) Ventilation
    add_ventilation_to_idf(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_vent=user_config_vent,
        assigned_vent_log=assigned_vent_log
    )

    # 9) Zone Sizing
    add_outdoor_air_and_zone_sizing_to_all_zones(
        idf=idf,
        building_row=building_row,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        assigned_setzone_log=assigned_setzone_log
    )

    # 10) Ground Temps
    add_ground_temperatures(
        idf=idf,
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        assigned_groundtemp_log=assigned_groundtemp_log
    )

    # 11) Output definitions
    desired_vars = ["Facility Total Electric Demand Power", "Zone Air Temperature Maximum"]
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

    # (Optional) Shading addition if needed
    # add_shading_to_idf(
    #     idf=idf,
    #     df_bldg_shading=df_bldg_shading,
    #     df_trees_shading=df_trees_shading,
    #     assigned_shading_log=assigned_shading_log
    # )

    # 12) Save IDF
    os.makedirs(idf_config["output_dir"], exist_ok=True)
    idf_filename = f"building_{building_index}.idf"
    out_path = os.path.join(idf_config["output_dir"], idf_filename)
    idf.save(out_path)
    print(f"[create_idf_for_building] IDF saved at: {out_path}")

    return idf_filename


def create_idfs_for_all_buildings(
    df_buildings,
    scenario="scenario1",
    calibration_stage=CALIBRATION_STAGE,
    strategy=STRATEGY,
    random_seed=RANDOM_SEED,
    user_config_geom=None,
    user_config_lighting=None,
    user_config_dhw=None,
    user_config_fenez=None,
    user_config_hvac=None,
    user_config_vent=None,
    df_bldg_shading=None,
    df_trees_shading=None,
    assigned_shading_log=None,
    run_simulations=True,
    simulate_config=None,
    post_process=True
):
    """
    Loops over df_buildings, creates IDFs for each building, optionally runs simulations,
    post-processes results, and writes assigned CSV logs.

    :param df_buildings: DataFrame with building data (area, perimeter, orientation, etc.)
    :param scenario: e.g. "scenario1"
    :param calibration_stage: e.g. "pre_calibration"
    :param strategy: "B", "C", etc.
    :param run_simulations: if True, calls simulate_all
    :param simulate_config: dict with config for simulate_all (num_workers, etc.)
    :param post_process: if True, merges results and writes assigned CSV logs
    :return: the updated DataFrame with a column "idf_name"
    """

    # 1) Create dictionaries to store final picks
    assigned_geom_log = {}
    assigned_lighting_log = {}
    assigned_dhw_log = {}
    assigned_fenez_log = {}
    assigned_hvac_log = {}
    assigned_vent_log = {}
    assigned_epw_log = {}
    assigned_groundtemp_log = {}
    assigned_setzone_log = {}

    # 2) Create IDFs for each building
    for idx, row in df_buildings.iterrows():
        print(f"--- Creating IDF for building index {idx} ---")
        idf_filename = create_idf_for_building(
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
            user_config_fenez=user_config_fenez,
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
            # shading
            df_bldg_shading=df_bldg_shading,
            df_trees_shading=df_trees_shading,
            assigned_shading_log=assigned_shading_log
        )
        df_buildings.loc[idx, "idf_name"] = idf_filename

    # 3) Run simulations if requested
    if run_simulations:
        idf_directory = idf_config["output_dir"]
        iddfile = idf_config["iddfile"]
        base_output_dir = "output/Sim_Results"

        # Example: parse simulate_config
        if simulate_config is None:
            simulate_config = {}
        num_workers = simulate_config.get("num_workers", 4)

        # Now call simulate_all
        simulate_all(
            df_buildings=df_buildings,
            idf_directory=idf_directory,
            iddfile=iddfile,
            base_output_dir=base_output_dir,
            # if you have user_config_epw or assigned_epw_log, pass them:
            
            assigned_epw_log=assigned_epw_log,
            num_workers=num_workers
        )

    # 4) If post-processing is enabled, merge results and write out assigned CSV logs
    if post_process:
        base_output_dir = "output/Sim_Results"
        out_csv_as_is = "output/results/merged_as_is.csv"

        merge_all_results(
            base_output_dir=base_output_dir,
            output_csv=out_csv_as_is,
            convert_to_daily=False,
            convert_to_monthly=False
        )

        # example daily mean
        out_csv_daily_mean = "output/results/merged_daily_mean.csv"
        merge_all_results(
            base_output_dir=base_output_dir,
            output_csv=out_csv_daily_mean,
            convert_to_daily=True,
            daily_aggregator="mean",
            convert_to_monthly=False
        )

        # Now write out CSV logs for each assigned_* dictionary
        # Geometry
        geom_rows = []
        for bldg_id, param_dict in assigned_geom_log.items():
            for param_name, param_val in param_dict.items():
                geom_rows.append({
                    "ogc_fid": bldg_id,
                    "param_name": param_name,
                    "assigned_value": param_val
                })
        df_geom = pd.DataFrame(geom_rows)
        df_geom.to_csv("output/assigned/assigned_geometry.csv", index=False)

        # Lighting
        light_rows = []
        for bldg_id, param_dict in assigned_lighting_log.items():
            for param_name, subdict in param_dict.items():
                assigned_val = subdict.get("assigned_value")
                min_v = subdict.get("min_val")
                max_v = subdict.get("max_val")
                obj_name = subdict.get("object_name", "")
                light_rows.append({
                    "ogc_fid": bldg_id,
                    "object_name": obj_name,
                    "param_name": param_name,
                    "assigned_value": assigned_val,
                    "min_val": min_v,
                    "max_val": max_v
                })
        df_lights = pd.DataFrame(light_rows)
        df_lights.to_csv("output/assigned/assigned_lighting.csv", index=False)

        # Fenestration
        fenez_rows = []
        for bldg_id, param_dict in assigned_fenez_log.items():
            for p_name, p_val in param_dict.items():
                fenez_rows.append({
                    "ogc_fid": bldg_id,
                    "param_name": p_name,
                    "assigned_value": p_val
                })
        df_fenez = pd.DataFrame(fenez_rows)
        df_fenez.to_csv("output/assigned/assigned_fenez_params.csv", index=False)

        # HVAC
        hvac_rows = []
        for bldg_id, param_dict in assigned_hvac_log.items():
            for param_name, param_val in param_dict.items():
                hvac_rows.append({
                    "ogc_fid": bldg_id,
                    "param_name": param_name,
                    "assigned_value": param_val
                })
        df_hvac = pd.DataFrame(hvac_rows)
        df_hvac.to_csv("output/assigned/assigned_hvac_params.csv", index=False)

        # DHW
        dhw_rows = []
        for bldg_id, param_dict in assigned_dhw_log.items():
            for param_name, param_val in param_dict.items():
                dhw_rows.append({
                    "ogc_fid": bldg_id,
                    "param_name": param_name,
                    "assigned_value": param_val
                })
        df_dhw = pd.DataFrame(dhw_rows)
        df_dhw.to_csv("output/assigned/assigned_dhw_params.csv", index=False)

        # Ventilation
        vent_rows = []
        for bldg_id, param_dict in assigned_vent_log.items():
            for param_name, param_val in param_dict.items():
                vent_rows.append({
                    "ogc_fid": bldg_id,
                    "param_name": param_name,
                    "assigned_value": param_val
                })
        df_vent = pd.DataFrame(vent_rows)
        df_vent.to_csv("output/assigned/assigned_ventilation.csv", index=False)

        # EPW
        epw_rows = []
        for bldg_id, epw_path in assigned_epw_log.items():
            epw_rows.append({
                "ogc_fid": bldg_id,
                "epw_path": epw_path
            })
        df_epw_assigned = pd.DataFrame(epw_rows)
        df_epw_assigned.to_csv("output/assigned/assigned_epw_paths.csv", index=False)

        # Ground temps
        rows = []
        ground_temps = assigned_groundtemp_log.get("ground_temperatures", {})
        for month_name, temp_val in ground_temps.items():
            rows.append({
                "month": month_name,
                "temp_value": temp_val
            })
        df_ground = pd.DataFrame(rows)
        df_ground.to_csv("output/assigned/assigned_ground_temps.csv", index=False)

        # Zone Sizing
        setzone_rows = []
        for bldg_id, param_dict in assigned_setzone_log.items():
            for p_name, p_val in param_dict.items():
                setzone_rows.append({
                    "ogc_fid": bldg_id,
                    "param_name": p_name,
                    "assigned_value": p_val
                })
        df_setzone = pd.DataFrame(setzone_rows)
        df_setzone.to_csv("output/assigned/assigned_setzone_params.csv", index=False)

        # If shading was assigned
        if assigned_shading_log:
            # up to you how to flatten assigned_shading_log
            pass

        print("[create_idfs_for_all_buildings] Post-processing and CSV logs have been written.")

    return df_buildings  # Now with 'idf_name' column
