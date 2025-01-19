# main_modifi.py

"""
Below is a conceptual example of how you might define a parameter space (with user overrides for building type, area, age, etc.) and generate initial parameter combinations using different Design of Experiments (DOE) strategies (e.g., full factorial, random, or Latin Hypercube). This is just a template; you will likely adapt it to your actual parameters, data structures, and workflow.

Initial Parameter Space & Design of Experiments (DOE)

Define the key parameters of interest (e.g., infiltration, occupant density, material thermal properties) along with reasonable ranges.
(Optional) Perform a design of experiments (e.g., Latin Hypercube, full factorial for small parameter sets, or random sampling) to systematically pick some initial parameter combinations.
as you see we make user configs to override lookups. we want that for example for a builing type with area, age building type and function, to generate many configurations and run simmulations. lets first work on it. 






Example orchestrator script for integrating HVAC, DHW, Ventilation, 
Electrical (lighting/parasitics), and Fenestration scenario picks.
"""

import os
import pandas as pd
import random

# 1) Import your common utilities
from common_utils import (
    load_assigned_csv,
    load_scenario_csv,
    load_idf,
    save_idf,
    generate_multiple_param_sets,
    save_param_scenarios_to_csv
)

# 2) Import your subsystem modules
from hvac_functions import apply_building_level_hvac, apply_zone_level_hvac
from dhw_functions import apply_dhw_params_to_idf
from vent_functions import apply_building_level_vent, apply_zone_level_vent

# (Assuming you have these two new modules)
#from elec_functions import apply_elec_params_to_idf  # or your actual function name
from fenez_functions import apply_object_level_fenez  # or your actual function name

###############################################################################
# USER CONFIG
###############################################################################

# Paths to your base IDF and IDD
BASE_IDF_PATH = r"D:\Documents\E_Plus_2030_py\output\output_IDFs\building_0.idf"
IDD_PATH      = r"D:\EnergyPlus\Energy+.idd"

# Example assigned CSVs
HVAC_CSV       = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_hvac_building.csv"
DHW_CSV        = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_dhw_params.csv"
VENT_CSV       = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_vent_building.csv"
ELEC_CSV       = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_lighting.csv"
FENEZ_CSV      = r"D:\Documents\E_Plus_2030_py\output\assigned\structured_fenez_params.csv"

VENT_ZONE_CSV  = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_vent_zones.csv"
# HVAC_ZONE_CSV  = ...
# etc.

# Output CSVs for scenario picks
HVAC_SCENARIO_CSV  = r"D:\Documents\E_Plus_2030_py\output\scenarios\scenario_params_hvac.csv"
DHW_SCENARIO_CSV   = r"D:\Documents\E_Plus_2030_py\output\scenarios\scenario_params_dhw.csv"
VENT_SCENARIO_CSV  = r"D:\Documents\E_Plus_2030_py\output\scenarios\scenario_params_vent.csv"
ELEC_SCENARIO_CSV  = r"D:\Documents\E_Plus_2030_py\output\scenarios\scenario_params_elec.csv"
# For fenestration, we typically rely on the structured_fenez_params.csv itself. 
# But you *could* also do a param-based approach if you like.
FENEZ_SCENARIO_CSV  = r"D:\Documents\E_Plus_2030_py\output\scenarios\scenario_params_fenez.csv"

# Output folder for newly generated scenario IDFs
OUTPUT_IDF_DIR = r"D:\Documents\E_Plus_2030_py\output\scenario_idfs"


def main():
    os.makedirs(OUTPUT_IDF_DIR, exist_ok=True)

    ###########################################################################
    # STEP A) LOAD "ASSIGNED" CSVs (HVAC, DHW, Vent, Elec, Fenez)
    #         Possibly filter for a building of interest
    ###########################################################################
    building_id = 4136730  # example

    # HVAC
    df_hvac = load_assigned_csv(HVAC_CSV)
    df_hvac_sub = df_hvac[df_hvac["ogc_fid"] == building_id].copy()

    # DHW
    df_dhw = load_assigned_csv(DHW_CSV)
    df_dhw_sub = df_dhw[df_dhw["ogc_fid"] == building_id].copy()

    # Vent
    df_vent = load_assigned_csv(VENT_CSV)
    df_vent_sub = df_vent[df_vent["ogc_fid"] == building_id].copy()

    # Elec (lighting, parasitics)
    df_elec = load_assigned_csv(ELEC_CSV)
    df_elec_sub = df_elec[df_elec["ogc_fid"] == building_id].copy()

    # For fenestration, do the same "assigned" approach:
    df_fenez = load_assigned_csv(FENEZ_CSV)
    df_fenez_sub = df_fenez[df_fenez["ogc_fid"] == building_id].copy()


    # Fenestration => structured CSV approach
    # (We typically don't need to filter by building_id if the CSV already 
    #  has the building-level or zone-level references. Or do so if needed.)
    # df_fenez = load_assigned_csv(FENEZ_CSV)
    # df_fenez_sub = df_fenez[df_fenez["ogc_fid"] == building_id].copy()
    # We'll let apply_object_level_fenez(...) handle it directly if it can parse building_id, etc.

    ###########################################################################
    # STEP B) GENERATE MULTIPLE SCENARIO PICKS (if desired)
    ###########################################################################
    num_scenarios = 5  # smaller for demonstration

    # B1) HVAC scenarios
    hvac_scenarios = generate_multiple_param_sets(
        df_main_sub=df_hvac_sub,
        num_sets=num_scenarios,
        picking_method="random_uniform",
        scale_factor=0.5
    )
    save_param_scenarios_to_csv(
        all_scenarios=hvac_scenarios,
        building_id=building_id,
        out_csv=HVAC_SCENARIO_CSV
    )

    # B2) DHW scenarios
    dhw_scenarios = generate_multiple_param_sets(
        df_main_sub=df_dhw_sub,
        num_sets=num_scenarios,
        picking_method="random_uniform",
        scale_factor=0.5
    )
    save_param_scenarios_to_csv(
        all_scenarios=dhw_scenarios,
        building_id=building_id,
        out_csv=DHW_SCENARIO_CSV
    )

    # B3) Vent scenarios
    vent_scenarios = generate_multiple_param_sets(
        df_main_sub=df_vent_sub,
        num_sets=num_scenarios,
        picking_method="random_uniform",
        scale_factor=0.5
    )
    save_param_scenarios_to_csv(
        all_scenarios=vent_scenarios,
        building_id=building_id,
        out_csv=VENT_SCENARIO_CSV
    )

    # B4) Elec scenarios
    elec_scenarios = generate_multiple_param_sets(
        df_main_sub=df_elec_sub,
        num_sets=num_scenarios,
        picking_method="random_uniform",
        scale_factor=0.5
    )
    save_param_scenarios_to_csv(
            all_scenarios=elec_scenarios,
            building_id=building_id,
            out_csv=ELEC_SCENARIO_CSV
        )
    # B5) Fenez
    # We'll use the same approach to produce a scenario_params_fenez.csv
    fenez_scenarios = generate_multiple_param_sets(
        df_main_sub=df_fenez_sub,
        num_sets=num_scenarios,
        picking_method="random_uniform",
        scale_factor=0.5
    )
    save_param_scenarios_to_csv(
        all_scenarios=fenez_scenarios,
        building_id=building_id,
        out_csv=FENEZ_SCENARIO_CSV
    )
    

    ###########################################################################
    # STEP C) FOR EACH SCENARIO, LOAD BASE IDF, APPLY SUBSYSTEM PARAMS, SAVE
    ###########################################################################
    df_hvac_scen = load_scenario_csv(HVAC_SCENARIO_CSV)
    df_dhw_scen  = load_scenario_csv(DHW_SCENARIO_CSV)
    df_vent_scen = load_scenario_csv(VENT_SCENARIO_CSV)
    df_elec_scen = load_scenario_csv(ELEC_SCENARIO_CSV)
    df_fenez_scen = load_scenario_csv(FENEZ_SCENARIO_CSV)

    # We won't do a "scenario" approach for fenestration in this example 
    # but you can replicate if you want.

    hvac_groups = df_hvac_scen.groupby("scenario_index")
    dhw_groups  = df_dhw_scen.groupby("scenario_index")
    vent_groups = df_vent_scen.groupby("scenario_index")
    elec_groups = df_elec_scen.groupby("scenario_index")
    fenez_groups = df_fenez_scen.groupby("scenario_index")

    for i in range(num_scenarios):
        print(f"\n--- Processing scenario #{i} for building {building_id} ---")

        hvac_group_df = hvac_groups.get_group(i)
        dhw_group_df  = dhw_groups.get_group(i)
        vent_group_df = vent_groups.get_group(i)
        elec_group_df = elec_groups.get_group(i)
        fenez_group_df = fenez_groups.get_group(i)

        # Build param dict for HVAC
        hvac_param_dict = {}
        for row in hvac_group_df.itertuples():
            p_name = row.param_name
            val = row.assigned_value
            try:
                hvac_param_dict[p_name] = float(val)
            except:
                hvac_param_dict[p_name] = val

        # Build param dict for DHW
        dhw_param_dict = {}
        for row in dhw_group_df.itertuples():
            p_name = row.param_name
            val = row.assigned_value
            try:
                dhw_param_dict[p_name] = float(val)
            except:
                dhw_param_dict[p_name] = val

        # Build param dict for Vent
        vent_param_dict = {}
        for row in vent_group_df.itertuples():
            p_name = row.param_name
            val = row.assigned_value
            if p_name in ["system_type", "infiltration_schedule_name", "ventilation_schedule_name"]:
                vent_param_dict[p_name] = str(val)
            else:
                try:
                    vent_param_dict[p_name] = float(val)
                except:
                    vent_param_dict[p_name] = val

        # Build param dict for Elec
        elec_param_dict = {}
        for row in elec_group_df.itertuples():
            p_name = row.param_name
            val = row.assigned_value
            try:
                elec_param_dict[p_name] = float(val)
            except:
                elec_param_dict[p_name] = val


        # Fenestration
        fenez_param_dict = {}
        for row in fenez_group_df.itertuples():
            p_name = row.param_name
            val    = row.assigned_value
            try:
                fenez_param_dict[p_name] = float(val)
            except:
                fenez_param_dict[p_name] = val

        # 1) Load base IDF
        idf = load_idf(BASE_IDF_PATH, IDD_PATH)

        # 2) Apply HVAC
        apply_building_level_hvac(idf, hvac_param_dict)

        # 3) Apply DHW
        apply_dhw_params_to_idf(idf, dhw_param_dict, suffix=f"MyDHW_{i}")

        # 4) Apply Vent
        apply_building_level_vent(idf, vent_param_dict)

        # 5) Apply Elec
        #    e.g. sets lighting W/m2, schedule, fraction radiant, etc.
        #apply_elec_params_to_idf(idf, elec_param_dict)

        # 6) Apply Fenestration (object-level approach)
        #    If you want to handle fenestration param changes in each scenario,
        #    you could pass scenario data to your function. 
        #    But in this example, we rely on a single CSV for fenestration, so:
        apply_object_level_fenez(idf, FENEZ_CSV)

        # 7) Save new scenario IDF
        out_idf_name = f"building_{building_id}_scenario_{i}.idf"
        out_idf_path = os.path.join(OUTPUT_IDF_DIR, out_idf_name)
        save_idf(idf, out_idf_path)

    print("[INFO] All scenario IDFs processed successfully.")


if __name__ == "__main__":
    main()
