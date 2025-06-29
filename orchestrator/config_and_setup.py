"""
orchestrator/config_and_setup.py

All configuration, setup, and override functions.
"""

import os
import json
import logging
from typing import Dict, Any, Tuple, Optional

from splitter import deep_merge_dicts
import idf_creation

# Excel overrides
from excel_overrides import (
    override_dhw_lookup_from_excel_file,
    override_epw_lookup_from_excel_file,
    override_lighting_lookup_from_excel_file,
    override_hvac_lookup_from_excel_file,
    override_vent_lookup_from_excel_file
)

# Fenestration config
from idf_objects.fenez.fenez_config_manager import build_fenez_config


def setup_job_environment(job_config: dict, logger: logging.Logger) -> Tuple[Optional[str], Optional[str]]:
    """
    Setup the job environment including output directories.
    
    Returns:
        Tuple of (job_output_dir, user_configs_folder) or (None, None) on error
    """
    # Identify the user_configs folder
    user_configs_folder = job_config.get("job_subfolder")
    if not user_configs_folder or not os.path.isdir(user_configs_folder):
        logger.error(f"[ERROR] job_subfolder not found or invalid => {user_configs_folder}")
        return None, None

    # Build output directory
    job_id = job_config.get("job_id", "unknown_job_id")
    env_out_dir = os.environ.get("OUTPUT_DIR", "/usr/src/app/output")
    job_output_dir = os.path.join(env_out_dir, job_id)
    os.makedirs(job_output_dir, exist_ok=True)
    logger.info(f"[INFO] Using job-specific output folder: {job_output_dir}")
    
    return job_output_dir, user_configs_folder


def load_and_merge_config(user_configs_folder: str, job_config: dict, logger: logging.Logger) -> Optional[Dict[str, Any]]:
    """
    Load main_config.json and merge with posted data if present.
    
    Returns:
        The merged main_config dictionary or None on error
    """
    main_config_path = os.path.join(user_configs_folder, "main_config.json")
    if not os.path.isfile(main_config_path):
        logger.error(f"[ERROR] Cannot find main_config.json at {main_config_path}")
        return None

    # Load existing config
    with open(main_config_path, "r") as f:
        existing_config_raw = json.load(f)
    main_config = existing_config_raw.get("main_config", {})
    logger.info(f"[INFO] Loaded existing main_config from {main_config_path}.")

    # Merge posted_data if present
    posted_data = job_config.get("posted_data", {})
    if "main_config" in posted_data:
        logger.info("[INFO] Deep merging posted_data['main_config'] into main_config.")
        deep_merge_dicts(main_config, posted_data["main_config"])
        # optionally re-save
        with open(main_config_path, "w") as f:
            json.dump({"main_config": main_config}, f, indent=2)
    
    return main_config


def setup_idf_config(idf_cfg: dict, job_output_dir: str, logger: logging.Logger) -> None:
    """
    Setup IDF creation configuration including paths.
    """
    # Override from environment if set
    env_idd_path = os.environ.get("IDD_PATH")
    if env_idd_path:
        idf_creation.idf_config["iddfile"] = env_idd_path
    
    env_base_idf = os.environ.get("BASE_IDF_PATH")
    if env_base_idf:
        idf_creation.idf_config["idf_file_path"] = env_base_idf

    # Set default output directory
    job_idf_dir = os.path.join(job_output_dir, "output_IDFs")
    os.makedirs(job_idf_dir, exist_ok=True)
    idf_creation.idf_config["output_dir"] = job_idf_dir

    # Apply user overrides if present
    if "iddfile" in idf_cfg:
        idf_creation.idf_config["iddfile"] = idf_cfg["iddfile"]
    if "idf_file_path" in idf_cfg:
        idf_creation.idf_config["idf_file_path"] = idf_cfg["idf_file_path"]

    if "output_idf_dir" in idf_cfg:
        subfolder = idf_cfg["output_idf_dir"]
        full_dir = os.path.join(job_output_dir, subfolder)
        idf_creation.idf_config["output_dir"] = full_dir
    else:
        idf_creation.idf_config["output_dir"] = os.path.join(job_output_dir, "output_IDFs")


def apply_excel_overrides(def_dicts: dict, excel_flags: dict, paths_dict: dict, 
                         logger: logging.Logger) -> Dict[str, Any]:
    """
    Apply Excel overrides to default dictionaries.
    
    Returns:
        Dictionary containing all updated lookups
    """
    # Start with base data
    base_res_data    = def_dicts.get("res_data", {})
    base_nonres_data = def_dicts.get("nonres_data", {})
    dhw_lookup       = def_dicts.get("dhw", {})
    epw_lookup       = def_dicts.get("epw", [])
    lighting_lookup  = def_dicts.get("lighting", {})
    hvac_lookup      = def_dicts.get("hvac", {})
    vent_lookup      = def_dicts.get("vent", {})

    # Apply fenestration overrides
    updated_res_data, updated_nonres_data = build_fenez_config(
        base_res_data=base_res_data,
        base_nonres_data=base_nonres_data,
        excel_path=paths_dict.get("fenez_excel", ""),
        do_excel_override=excel_flags.get("override_fenez_excel", False),
        user_fenez_overrides=[]
    )

    # Apply other Excel overrides
    if excel_flags.get("override_dhw_excel", False):
        dhw_lookup = override_dhw_lookup_from_excel_file(
            dhw_excel_path=paths_dict.get("dhw_excel", ""),
            default_dhw_lookup=dhw_lookup,
            override_dhw_flag=True
        )

    if excel_flags.get("override_epw_excel", False):
        epw_lookup = override_epw_lookup_from_excel_file(
            epw_excel_path=paths_dict.get("epw_excel", ""),
            epw_lookup=epw_lookup,
            override_epw_flag=True
        )

    if excel_flags.get("override_lighting_excel", False):
        lighting_lookup = override_lighting_lookup_from_excel_file(
            lighting_excel_path=paths_dict.get("lighting_excel", ""),
            lighting_lookup=lighting_lookup,
            override_lighting_flag=True
        )

    if excel_flags.get("override_hvac_excel", False):
        hvac_lookup = override_hvac_lookup_from_excel_file(
            hvac_excel_path=paths_dict.get("hvac_excel", ""),
            hvac_lookup=hvac_lookup,
            override_hvac_flag=True
        )

    if excel_flags.get("override_vent_excel", False):
        vent_lookup = override_vent_lookup_from_excel_file(
            vent_excel_path=paths_dict.get("vent_excel", ""),
            vent_lookup=vent_lookup,
            override_vent_flag=True
        )
    
    return {
        "dhw": dhw_lookup,
        "epw": epw_lookup,
        "lighting": lighting_lookup,
        "hvac": hvac_lookup,
        "vent": vent_lookup,
        "res_data": updated_res_data,
        "nonres_data": updated_nonres_data
    }


def safe_load_subjson(user_configs_folder: str, fname: str, key: str, logger: logging.Logger) -> Optional[Any]:
    """
    Safely load a JSON file from user_configs folder.
    """
    full_path = os.path.join(user_configs_folder, fname)
    if os.path.isfile(full_path):
        try:
            with open(full_path, "r") as ff:
                data = json.load(ff)
            return data.get(key)
        except Exception as e:
            logger.error(f"[ERROR] loading {fname} => {e}")
    return None


def apply_json_overrides(user_configs_folder: str, user_flags: dict, 
                        updated_res_data: dict, updated_nonres_data: dict,
                        logger: logging.Logger) -> Dict[str, Any]:
    """
    Apply JSON overrides from user config files.
    
    Returns:
        Dictionary containing all overrides
    """
    # Fenestration
    user_fenez_data = []
    if user_flags.get("override_fenez_json", False):
        loaded = safe_load_subjson(user_configs_folder, "fenestration.json", "fenestration", logger)
        if loaded:
            user_fenez_data = loaded

    updated_res_data, updated_nonres_data = build_fenez_config(
        base_res_data=updated_res_data,
        base_nonres_data=updated_nonres_data,
        excel_path="",
        do_excel_override=False,
        user_fenez_overrides=user_fenez_data
    )

    # DHW
    user_config_dhw = None
    if user_flags.get("override_dhw_json", False):
        user_config_dhw = safe_load_subjson(user_configs_folder, "dhw.json", "dhw", logger)

    # EPW
    user_config_epw = []
    if user_flags.get("override_epw_json", False):
        e = safe_load_subjson(user_configs_folder, "epw.json", "epw", logger)
        if e:
            user_config_epw = e

    # Lighting
    user_config_lighting = None
    if user_flags.get("override_lighting_json", False):
        user_config_lighting = safe_load_subjson(user_configs_folder, "lighting.json", "lighting", logger)

    # HVAC
    user_config_hvac = None
    if user_flags.get("override_hvac_json", False):
        user_config_hvac = safe_load_subjson(user_configs_folder, "hvac.json", "hvac", logger)

    # Vent
    user_config_vent = []
    if user_flags.get("override_vent_json", False):
        v = safe_load_subjson(user_configs_folder, "vent.json", "vent", logger)
        if v:
            user_config_vent = v

    # Geometry
    geom_data = {}
    if user_flags.get("override_geometry_json", False):
        g = safe_load_subjson(user_configs_folder, "geometry.json", "geometry", logger)
        if g:
            geom_data["geometry"] = g

    # Shading
    shading_data = {}
    if user_flags.get("override_shading_json", False):
        s = safe_load_subjson(user_configs_folder, "shading.json", "shading", logger)
        if s:
            shading_data["shading"] = s
    
    return {
        "res_data": updated_res_data,
        "nonres_data": updated_nonres_data,
        "dhw": user_config_dhw,
        "epw": user_config_epw,
        "lighting": user_config_lighting,
        "hvac": user_config_hvac,
        "vent": user_config_vent,
        "geometry": geom_data,
        "shading": shading_data
    }