"""
main_modifi.py

Handles the generation of scenario-based IDFs for sensitivity, surrogate, 
calibration, or any parametric runs.

Workflow Outline:
  1) Loads "assigned"/"structured" CSV data for HVAC, DHW, Vent, Elec, Fenestration.
  2) Generates multiple scenario picks (random or other) -> scenario_params_*.csv
  3) Loads scenario CSVs, loops over scenario_index, applies them to IDFs
  4) Optionally runs simulations, post-processes, and does validation
"""

import os
import pandas as pd

# ---------------------------------------------------------------------------
# Local modules
# ---------------------------------------------------------------------------
from modification.common_utils import (
    load_assigned_csv,
    load_scenario_csv,
    load_idf,
    save_idf,
    generate_multiple_param_sets,
    save_param_scenarios_to_csv
)

# HVAC
from modification.hvac_functions import (
    create_hvac_scenarios,
    apply_building_level_hvac,
    apply_zone_level_hvac
)

# DHW
from modification.dhw_functions import apply_dhw_params_to_idf

# Elec
from modification.elec_functions import (
    create_elec_scenarios,
    apply_building_level_elec,
    apply_object_level_elec
)

# Fenestration
from modification.fenez_functions2 import (
    create_fenez_scenarios,
    apply_object_level_fenez
)

# Vent
from modification.vent_functions import (
    create_vent_scenarios,
    apply_building_level_vent,
    apply_zone_level_vent
)


def run_modification_workflow(config):
    """
    Main orchestration function that:
      - Loads assigned/structured CSV data for each system (HVAC, DHW, Vent, Elec, Fenez)
      - Creates multiple scenario picks
      - Applies them to a base IDF, generating scenario IDFs
      - Optionally runs simulations, post-process, and validation.
    """
    # -----------------------------------------------------------------------
    # 1) Extract from config
    # -----------------------------------------------------------------------
    base_idf_path   = config["base_idf_path"]
    idd_path        = config["idd_path"]
    assigned_csvs   = config["assigned_csv"]
    scenario_csvs   = config["scenario_csv"]
    building_id     = config["building_id"]
    num_scenarios   = config["num_scenarios"]
    picking_method  = config["picking_method"]
    scale_factor    = config.get("picking_scale_factor", 1.0)
    output_idf_dir  = config["output_idf_dir"]

    os.makedirs(output_idf_dir, exist_ok=True)

    # -----------------------------------------------------------------------
    # 2) HVAC CSV (either building+zones or single 'hvac')
    # -----------------------------------------------------------------------
    df_hvac_bld_sub = pd.DataFrame()
    df_hvac_zn_sub  = pd.DataFrame()
    has_hvac_data   = False

    if "hvac_building" in assigned_csvs and "hvac_zones" in assigned_csvs:
        path_bld = assigned_csvs["hvac_building"]
        path_zn  = assigned_csvs["hvac_zones"]

        df_hvac_bld_all = load_assigned_csv(path_bld)
        df_hvac_zn_all  = load_assigned_csv(path_zn)
        df_hvac_bld_sub = df_hvac_bld_all[df_hvac_bld_all["ogc_fid"] == building_id].copy()
        df_hvac_zn_sub  = df_hvac_zn_all[df_hvac_zn_all["ogc_fid"] == building_id].copy()
        has_hvac_data = True
    elif "hvac" in assigned_csvs:
        # single CSV
        path_hvac_single = assigned_csvs["hvac"]
        df_hvac_all = load_assigned_csv(path_hvac_single)
        df_hvac_bld_sub = df_hvac_all[df_hvac_all["ogc_fid"] == building_id].copy()
        has_hvac_data = True

    # -----------------------------------------------------------------------
    # 3) DHW
    # -----------------------------------------------------------------------
    df_dhw_all = load_assigned_csv(assigned_csvs["dhw"])
    df_dhw_sub = df_dhw_all[df_dhw_all["ogc_fid"] == building_id].copy()

    # -----------------------------------------------------------------------
    # 4) Vent (either building+zones or single 'vent')
    # -----------------------------------------------------------------------
    df_vent_bld_sub = pd.DataFrame()
    df_vent_zn_sub  = pd.DataFrame()
    has_vent_data   = False

    if "vent_building" in assigned_csvs and "vent_zones" in assigned_csvs:
        vent_bld_path = assigned_csvs["vent_building"]
        vent_zn_path  = assigned_csvs["vent_zones"]
        df_vent_bld_all = load_assigned_csv(vent_bld_path)
        df_vent_zn_all  = load_assigned_csv(vent_zn_path)
        df_vent_bld_sub = df_vent_bld_all[df_vent_bld_all["ogc_fid"] == building_id].copy()
        df_vent_zn_sub  = df_vent_zn_all[df_vent_zn_all["ogc_fid"] == building_id].copy()
        has_vent_data = True
    elif "vent" in assigned_csvs:
        vent_single_path = assigned_csvs["vent"]
        df_vent_all = load_assigned_csv(vent_single_path)
        df_vent_bld_sub = df_vent_all[df_vent_all["ogc_fid"] == building_id].copy()
        has_vent_data = True

    # -----------------------------------------------------------------------
    # 5) Elec
    # -----------------------------------------------------------------------
    df_elec_all = load_assigned_csv(assigned_csvs["elec"])
    df_elec_sub = df_elec_all[df_elec_all["ogc_fid"] == building_id].copy()

    # -----------------------------------------------------------------------
    # 6) Fenestration
    # -----------------------------------------------------------------------
    df_fenez_all = load_assigned_csv(assigned_csvs["fenez"])
    df_fenez_sub = df_fenez_all[df_fenez_all["ogc_fid"] == building_id].copy()

    # -----------------------------------------------------------------------
    # 7) Generate scenario picks for each system
    # -----------------------------------------------------------------------

    # 7A) HVAC
    if has_hvac_data and (not df_hvac_bld_sub.empty or not df_hvac_zn_sub.empty):
        from modification.hvac_functions import create_hvac_scenarios
        df_scen_hvac = create_hvac_scenarios(
            df_building=df_hvac_bld_sub,
            df_zones=df_hvac_zn_sub,
            building_id=building_id,
            num_scenarios=num_scenarios,
            picking_method=picking_method,
            random_seed=42,
            scenario_csv_out=scenario_csvs["hvac"]
        )
    else:
        df_scen_hvac = pd.DataFrame()
        if "hvac" in assigned_csvs and not df_hvac_bld_sub.empty:
            hvac_scenarios = generate_multiple_param_sets(
                df_main_sub=df_hvac_bld_sub,
                num_sets=num_scenarios,
                picking_method=picking_method,
                scale_factor=scale_factor
            )
            save_param_scenarios_to_csv(hvac_scenarios, building_id, scenario_csvs["hvac"])

    # 7B) DHW
    # If you prefer a param_min/param_max approach, import create_dhw_scenarios. 
    # Otherwise, fallback to generate_multiple_param_sets:
    from modification.dhw_functions import create_dhw_scenarios
    df_scen_dhw = create_dhw_scenarios(
        df_dhw_input=df_dhw_sub,
        building_id=building_id,
        num_scenarios=num_scenarios,
        picking_method=picking_method,
        random_seed=42,
        scenario_csv_out=scenario_csvs["dhw"]
    )

    # If older approach:
    # dhw_scenarios = generate_multiple_param_sets(df_main_sub=df_dhw_sub, ...)
    # save_param_scenarios_to_csv(dhw_scenarios, building_id, scenario_csvs["dhw"])

    # 7C) Vent
    if has_vent_data and (not df_vent_bld_sub.empty or not df_vent_zn_sub.empty):
        df_scen_vent = create_vent_scenarios(
            df_building=df_vent_bld_sub,
            df_zones=df_vent_zn_sub,
            building_id=building_id,
            num_scenarios=num_scenarios,
            picking_method=picking_method,
            random_seed=42,
            scenario_csv_out=scenario_csvs["vent"]
        )
    else:
        df_scen_vent = pd.DataFrame()

    # 7D) Elec => "create_elec_scenarios" for param_min/param_max approach
    df_scen_elec = create_elec_scenarios(
        df_lighting=df_elec_sub,
        building_id=building_id,
        num_scenarios=num_scenarios,
        picking_method=picking_method,
        random_seed=42,
        scenario_csv_out=scenario_csvs["elec"]
    )

    # 7E) Fenestration
    df_scen_fenez = create_fenez_scenarios(
        df_struct_fenez=df_fenez_sub,
        building_id=building_id,
        num_scenarios=num_scenarios,
        picking_method=picking_method,
        random_seed=42,
        scenario_csv_out=scenario_csvs["fenez"]
    )

    # -----------------------------------------------------------------------
    # 8) Load scenario CSVs back, group by scenario_index
    # -----------------------------------------------------------------------
    df_hvac_scen  = load_scenario_csv(scenario_csvs["hvac"])  if os.path.isfile(scenario_csvs["hvac"])  else pd.DataFrame()
    df_dhw_scen   = load_scenario_csv(scenario_csvs["dhw"])   if os.path.isfile(scenario_csvs["dhw"])   else pd.DataFrame()
    df_vent_scen  = load_scenario_csv(scenario_csvs["vent"])  if os.path.isfile(scenario_csvs["vent"])  else pd.DataFrame()
    df_elec_scen  = load_scenario_csv(scenario_csvs["elec"])  if os.path.isfile(scenario_csvs["elec"])  else pd.DataFrame()
    df_fenez_scen = load_scenario_csv(scenario_csvs["fenez"]) if os.path.isfile(scenario_csvs["fenez"]) else pd.DataFrame()

    hvac_groups  = df_hvac_scen.groupby("scenario_index")  if not df_hvac_scen.empty  else None
    dhw_groups   = df_dhw_scen.groupby("scenario_index")   if not df_dhw_scen.empty   else None
    vent_groups  = df_vent_scen.groupby("scenario_index")  if not df_vent_scen.empty  else None
    elec_groups  = df_elec_scen.groupby("scenario_index")  if not df_elec_scen.empty  else None
    fenez_groups = df_fenez_scen.groupby("scenario_index") if not df_fenez_scen.empty else None

    # -----------------------------------------------------------------------
    # 9) For each scenario, load base IDF, apply parameters, save new IDF
    # -----------------------------------------------------------------------
    for i in range(num_scenarios):
        print(f"\n--- Creating scenario #{i} for building {building_id} ---")

        # 9A) Pull sub-DataFrames
        hvac_df = hvac_groups.get_group(i) if hvac_groups and i in hvac_groups.groups else pd.DataFrame()
        dhw_df  = dhw_groups.get_group(i)  if dhw_groups  and i in dhw_groups.groups  else pd.DataFrame()
        vent_df = vent_groups.get_group(i) if vent_groups and i in vent_groups.groups else pd.DataFrame()
        elec_df = elec_groups.get_group(i) if elec_groups and i in elec_groups.groups else pd.DataFrame()
        fenez_df= fenez_groups.get_group(i)if fenez_groups and i in fenez_groups.groups else pd.DataFrame()

        # 9B) For HVAC: building-level vs. zone-level
        hvac_bld_df  = hvac_df[hvac_df["zone_name"].isna()]   if not hvac_df.empty else pd.DataFrame()
        hvac_zone_df = hvac_df[hvac_df["zone_name"].notna()]  if not hvac_df.empty else pd.DataFrame()
        hvac_params  = _make_param_dict(hvac_bld_df)

        # 9C) Convert to param dict for DHW
        dhw_params = _make_param_dict(dhw_df)

        # 9D) Vent building vs. zone
        vent_bld_df  = vent_df[vent_df["zone_name"].isnull()] if not vent_df.empty else pd.DataFrame()
        vent_zone_df = vent_df[vent_df["zone_name"].notnull()]if not vent_df.empty else pd.DataFrame()
        vent_params  = _make_param_dict(vent_bld_df)

        # 9E) Elec => building-level approach or object-level
        elec_params = _make_param_dict(elec_df)

        # 9F) Load base IDF
        idf = load_idf(base_idf_path, idd_path)

        # 9G) Apply building-level + zone-level HVAC
        apply_building_level_hvac(idf, hvac_params)
        apply_zone_level_hvac(idf, hvac_zone_df)

        # 9H) Apply DHW
        apply_dhw_params_to_idf(idf, dhw_params, suffix=f"Scenario_{i}")

        # 9I) Apply Vent
        if not vent_bld_df.empty or not vent_zone_df.empty:
            apply_building_level_vent(idf, vent_params)
            apply_zone_level_vent(idf, vent_zone_df)

        # 9J) Apply Elec => building-level approach
        #    Or if you prefer object-level, do apply_object_level_elec(idf, elec_df)
        if not elec_df.empty:
            apply_building_level_elec(idf, elec_params, zonelist_name="ALL_ZONES")

        # 9K) Apply Fenestration (object-level)
        apply_object_level_fenez(idf, fenez_df)

        # 9L) Save scenario IDF
        scenario_idf_name = f"building_{building_id}_scenario_{i}.idf"
        scenario_idf_path = os.path.join(output_idf_dir, scenario_idf_name)
        save_idf(idf, scenario_idf_path)
        print(f"[INFO] Saved scenario IDF: {scenario_idf_path}")

    print("[INFO] All scenario IDFs generated successfully.")

    # -----------------------------------------------------------------------
    # 10) (Optional) Run Simulations
    # -----------------------------------------------------------------------
    if config.get("run_simulations", False):
        print("\n[INFO] Running simulations for scenario IDFs...")
        sim_cfg = config.get("simulation_config", {})
        # your simulate_all(...) or E+ runner here
        print("[INFO] Simulations complete (placeholder).")

    # -----------------------------------------------------------------------
    # 11) (Optional) Post-processing
    # -----------------------------------------------------------------------
    if config.get("perform_post_process", False):
        print("[INFO] Performing post-processing merges (placeholder).")
        ppcfg = config.get("post_process_config", {})
        # merge_all_results(...)
        print("[INFO] Post-processing step complete (placeholder).")

    # -----------------------------------------------------------------------
    # 12) (Optional) Validation
    # -----------------------------------------------------------------------
    if config.get("perform_validation", False):
        print("[INFO] Performing validation on scenario results (placeholder).")
        val_cfg = config["validation_config"]
        # run_validation_process(val_cfg)
        print("[INFO] Validation step complete (placeholder).")


def _make_param_dict(df_scenario):
    """
    Builds a dict {param_name: value} from a subset DataFrame, handling both
    'assigned_value' or 'param_value' columns in the scenario CSV.

    We check which column is present. If neither is found, we raise an error.
    """
    if df_scenario.empty:
        return {}

    possible_cols = list(df_scenario.columns)
    if "assigned_value" in possible_cols:
        val_col = "assigned_value"
    elif "param_value" in possible_cols:
        val_col = "param_value"
    else:
        raise AttributeError(
            "No 'assigned_value' or 'param_value' column found in scenario dataframe! "
            f"Columns are: {possible_cols}"
        )

    param_dict = {}
    for row in df_scenario.itertuples():
        p_name = row.param_name
        val    = getattr(row, val_col)
        # Attempt float
        try:
            param_dict[p_name] = float(val)
        except (ValueError, TypeError):
            param_dict[p_name] = val
    return param_dict
