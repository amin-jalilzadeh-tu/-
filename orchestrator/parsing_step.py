"""
orchestrator/parsing_step.py

Parsing logic for IDF/SQL files to Parquet format.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import pandas as pd

from parserr.energyplus_analyzer_main import EnergyPlusAnalyzer
from parserr.helpers import prepare_idf_sql_pairs_with_mapping, get_parsed_data_info


def run_parsing(
    parsing_cfg: dict,
    main_config: dict,
    job_output_dir: str,
    job_id: str,
    logger: logging.Logger
) -> None:
    """
    Run parsing of IDF/SQL files to Parquet format.
    """
    logger.info("[INFO] Parsing IDF/SQL files to Parquet format...")
    
    # Create parser output directory
    parser_output_dir = os.path.join(job_output_dir, "parsed_data")
    os.makedirs(parser_output_dir, exist_ok=True)
    
    # Initialize the analyzer
    analyzer = EnergyPlusAnalyzer(parser_output_dir)
    
    # Get parsing configuration details
    parse_mode = parsing_cfg.get("parse_mode", "all")
    parse_types = parsing_cfg.get("parse_types", {"idf": True, "sql": True})
    building_selection = parsing_cfg.get("building_selection", {})
    idf_content_cfg = parsing_cfg.get("idf_content", {})
    sql_content_cfg = parsing_cfg.get("sql_content", {})
    use_profile = parsing_cfg.get("use_profile")
    categories_to_parse = parsing_cfg.get("categories", None)
    
    # Apply profile if specified
    if use_profile:
        profiles = main_config.get("parsing_profiles", {})
        if use_profile in profiles:
            profile_cfg = profiles[use_profile]
            logger.info(f"[INFO] Using parsing profile: {use_profile}")
            # Merge profile settings with existing config
            if "parse_types" in profile_cfg:
                parse_types.update(profile_cfg["parse_types"])
            if "idf_content" in profile_cfg:
                idf_content_cfg.update(profile_cfg["idf_content"])
            if "sql_content" in profile_cfg:
                sql_content_cfg.update(profile_cfg["sql_content"])
    
    # Use the same approach as in successful test
    idf_map_csv = os.path.join(job_output_dir, "extracted_idf_buildings.csv")
    
    # Check if we have the mapping file
    if not os.path.isfile(idf_map_csv):
        logger.error(f"[ERROR] IDF mapping file not found: {idf_map_csv}")
        logger.error("[ERROR] Please run IDF creation first or provide mapping file")
        return
        
    # Use the proven method
    idf_sql_pairs, building_id_map = prepare_idf_sql_pairs_with_mapping(job_output_dir)
    
    if not idf_sql_pairs:
        logger.warning("[WARN] No valid file pairs found")
        return
        
    logger.info(f"[INFO] Found {len(idf_sql_pairs)} file pairs to parse")
    logger.info(f"[INFO] Parse mode: {parse_mode}")
    
    # Apply building selection if needed
    if parse_mode == "selective" and building_selection:
        mode = building_selection.get("mode", "all")
        if mode == "specific":
            building_ids = building_selection.get("building_ids", [])
            if building_ids:
                # Filter pairs based on building IDs
                filtered_pairs = []
                filtered_map = {}
                for idf_path, sql_path in idf_sql_pairs:
                    if idf_path in building_id_map:
                        bid = int(building_id_map[idf_path])
                        if bid in building_ids:
                            filtered_pairs.append((idf_path, sql_path))
                            filtered_map[idf_path] = building_id_map[idf_path]
                idf_sql_pairs = filtered_pairs
                building_id_map = filtered_map
                logger.info(f"[INFO] Filtered to {len(idf_sql_pairs)} buildings")
    
    # Run the standard analysis
    analyzer.analyze_project(
        idf_sql_pairs=idf_sql_pairs,
        categories=categories_to_parse,
        validate_outputs=True,
        building_id_map=building_id_map
    )
    
    # Get parsing summary
    parsed_info = get_parsed_data_info(parser_output_dir)
    
    # Save enhanced summary
    parsing_summary = {
        'job_id': job_id,
        'parse_mode': parse_mode,
        'parse_types': parse_types,
        'files_parsed': len(idf_sql_pairs),
        'parser_output_dir': parser_output_dir,
        'timestamp': datetime.now().isoformat(),
        'parsed_data_info': parsed_info,
        'configuration': {
            'parse_mode': parse_mode,
            'categories': categories_to_parse
        }
    }
    
    summary_path = os.path.join(parser_output_dir, 'parsing_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(parsing_summary, f, indent=2)
    
    logger.info(f"[INFO] Parsing complete. Data saved to: {parser_output_dir}")
    logger.info(f"[INFO] Total categories: {len(parsed_info['categories'])}")
    logger.info(f"[INFO] Total files: {parsed_info['total_files']}")
    
    # Close analyzer connections
    analyzer.close()


def run_parsing_modified_results(
    parse_cfg: dict,
    job_output_dir: str,
    modified_sim_output: str,
    modified_idfs_dir: str,
    idf_map_csv: str,
    logger: logging.Logger
) -> None:
    """
    Parse modified simulation results.
    """
    logger.info("[INFO] Parsing modified simulation results...")
    
    # Create parser output directory
    parser_output_dir = os.path.join(job_output_dir, "parsed_modified_results")
    os.makedirs(parser_output_dir, exist_ok=True)
    
    # Initialize the analyzer
    analyzer = EnergyPlusAnalyzer(parser_output_dir)
    
    # Manually prepare IDF-SQL pairs for modified results
    idf_sql_pairs = []
    building_id_map = {}
    
    # Load original building mapping
    if os.path.exists(idf_map_csv):
        mapping_df = pd.read_csv(idf_map_csv)
        # Create a lookup from original IDF names to building IDs
        orig_idf_to_building = {}
        for _, row in mapping_df.iterrows():
            idf_name = row['idf_name']
            building_id = str(row['ogc_fid'])
            # Extract base name without .idf extension
            base_name = os.path.splitext(idf_name)[0]
            orig_idf_to_building[base_name] = building_id
    
    # Find SQL files in modified simulation output
    sim_output_path = Path(modified_sim_output)
    
    # Look for SQL files in subdirectories (e.g., 2020/)
    sql_files = list(sim_output_path.glob('**/*.sql'))
    
    logger.info(f"[INFO] Found {len(sql_files)} SQL files in {modified_sim_output}")
    
    for sql_file in sql_files:
        # Extract building info from SQL filename
        # Expected format: simulation_bldg{idx}_{building_id}.sql
        sql_name = sql_file.stem
        
        # Try to extract building ID from filename
        if '_' in sql_name:
            parts = sql_name.split('_')
            # Look for the building ID in the last part
            potential_building_id = parts[-1]
            
            # Find corresponding IDF in modified_idfs_dir
            modified_idfs_path = Path(modified_idfs_dir)
            
            # Look for IDF files containing this building ID
            matching_idfs = list(modified_idfs_path.glob(f"*{potential_building_id}*.idf"))
            
            if matching_idfs:
                # Use the first matching IDF
                idf_file = matching_idfs[0]
                
                # Add to pairs
                idf_sql_pairs.append((str(idf_file), str(sql_file)))
                
                # Map to building ID
                building_id_map[str(idf_file)] = potential_building_id
                
                logger.debug(f"  Matched: {idf_file.name} -> {sql_file.name}")
    
    if not idf_sql_pairs:
        logger.warning("[WARN] No valid IDF-SQL pairs found for modified results")
        return
        
    logger.info(f"[INFO] Found {len(idf_sql_pairs)} modified file pairs to parse")
    
    # Get parse categories
    parse_categories = parse_cfg.get("categories", None)
    
    # Run analysis with the correct method
    try:
        analyzer.analyze_project(
            idf_sql_pairs=idf_sql_pairs,
            categories=parse_categories,
            validate_outputs=True,
            building_id_map=building_id_map
        )
        
        logger.info("[INFO] Modified results parsing complete")
        
    except Exception as e:
        logger.error(f"[ERROR] Failed to parse modified results: {e}")
        import traceback
        traceback.print_exc()
    
    # Get parsing summary
    parsed_info = get_parsed_data_info(parser_output_dir)
    
    # Save parsing summary
    parsing_summary = {
        'job_id': job_output_dir.split('/')[-1],  # Extract job_id from path
        'type': 'modified_results',
        'files_parsed': len(idf_sql_pairs),
        'parser_output_dir': parser_output_dir,
        'timestamp': datetime.now().isoformat(),
        'parsed_data_info': parsed_info
    }
    
    summary_path = os.path.join(parser_output_dir, 'parsing_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(parsing_summary, f, indent=2)
    
    logger.info(f"[INFO] Parsed modified results saved to: {parser_output_dir}")
    
    # Close analyzer
    analyzer.close()