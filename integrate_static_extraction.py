"""
Integration script for static SQL data extraction
Integrates with existing parsing workflow
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from sql_static_extractor import extract_static_data_for_building

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_static_data_for_all_buildings(
    base_dir: Path,
    user_config_id: str,
    year: str = "2020",
    max_workers: int = 4
) -> Dict[str, List[str]]:
    """
    Extract static data for all buildings in a project
    
    Args:
        base_dir: Base directory containing output folder
        user_config_id: User configuration ID
        year: Simulation year
        max_workers: Number of parallel workers
    
    Returns:
        Dictionary with extraction status
    """
    output_base = base_dir / "output" / user_config_id
    results = {"success": [], "failed": []}
    
    # Process base buildings
    logger.info("Processing base buildings...")
    sim_results_dir = output_base / "Sim_Results" / year
    if sim_results_dir.exists():
        sql_files = list(sim_results_dir.glob("*.sql"))
        logger.info(f"Found {len(sql_files)} base building SQL files")
        
        output_dir = output_base / "parsed_data"
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for sql_path in sql_files:
                # Extract building ID from filename
                building_id = sql_path.stem.split('_')[-1]
                future = executor.submit(
                    extract_static_data_for_building,
                    sql_path,
                    output_dir,
                    building_id,
                    "base"
                )
                futures[future] = (building_id, "base")
            
            for future in as_completed(futures):
                building_id, variant_id = futures[future]
                try:
                    future.result()
                    results["success"].append(f"{building_id}_{variant_id}")
                    logger.info(f"Successfully extracted static data for {building_id} (base)")
                except Exception as e:
                    results["failed"].append(f"{building_id}_{variant_id}")
                    logger.error(f"Failed to extract static data for {building_id} (base): {e}")
    
    # Process modified buildings
    logger.info("Processing modified buildings...")
    modified_results_dir = output_base / "Modified_Sim_Results" / year
    if modified_results_dir.exists():
        sql_files = list(modified_results_dir.glob("*.sql"))
        logger.info(f"Found {len(sql_files)} modified building SQL files")
        
        output_dir = output_base / "parsed_modified_results"
        
        # Group by building to extract variants
        building_variants = {}
        for sql_path in sql_files:
            # Parse filename: simulation_bldg{variant}_{building_id}.sql
            parts = sql_path.stem.split('_')
            if len(parts) >= 3 and parts[1].startswith('bldg'):
                variant_num = parts[1].replace('bldg', '')
                building_id = parts[2]
                variant_id = f"variant_{variant_num}"
                
                if building_id not in building_variants:
                    building_variants[building_id] = []
                building_variants[building_id].append((sql_path, variant_id))
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for building_id, variants in building_variants.items():
                for sql_path, variant_id in variants:
                    future = executor.submit(
                        extract_static_data_for_building,
                        sql_path,
                        output_dir,
                        building_id,
                        variant_id
                    )
                    futures[future] = (building_id, variant_id)
            
            for future in as_completed(futures):
                building_id, variant_id = futures[future]
                try:
                    future.result()
                    results["success"].append(f"{building_id}_{variant_id}")
                    logger.info(f"Successfully extracted static data for {building_id} ({variant_id})")
                except Exception as e:
                    results["failed"].append(f"{building_id}_{variant_id}")
                    logger.error(f"Failed to extract static data for {building_id} ({variant_id}): {e}")
    
    # Log summary
    logger.info(f"\nExtraction complete!")
    logger.info(f"Success: {len(results['success'])} files")
    logger.info(f"Failed: {len(results['failed'])} files")
    
    return results


def add_static_extraction_to_workflow(
    existing_parser_output_dir: Path,
    sql_files: List[Path],
    building_ids: List[str],
    variant_ids: Optional[List[str]] = None
):
    """
    Add static extraction to existing parsing workflow
    Call this after timeseries extraction is complete
    
    Args:
        existing_parser_output_dir: Directory where parsed data is stored
        sql_files: List of SQL file paths
        building_ids: List of building IDs corresponding to SQL files
        variant_ids: List of variant IDs (optional, defaults to 'base')
    """
    if variant_ids is None:
        variant_ids = ['base'] * len(sql_files)
    
    logger.info("Adding static data extraction to existing workflow...")
    
    for sql_path, building_id, variant_id in zip(sql_files, building_ids, variant_ids):
        try:
            extract_static_data_for_building(
                sql_path,
                existing_parser_output_dir,
                building_id,
                variant_id
            )
            logger.info(f"Extracted static data for {building_id} ({variant_id})")
        except Exception as e:
            logger.error(f"Failed to extract static data for {building_id}: {e}")


def verify_extraction(output_dir: Path) -> Dict[str, List[str]]:
    """
    Verify that static data was extracted successfully
    
    Args:
        output_dir: Directory containing extracted data
    
    Returns:
        Dictionary of found files by category
    """
    categories = {
        'performance_summaries': [
            'energy_end_uses.parquet',
            'site_source_summary.parquet',
            'comfort_metrics.parquet',
            'energy_intensity.parquet',
            'peak_demands.parquet'
        ],
        'sizing_results': [
            'zone_sizing.parquet',
            'system_sizing.parquet',
            'component_sizing.parquet'
        ],
        'building_characteristics': [
            'envelope_summary.parquet',
            'construction_details.parquet',
            'zone_properties.parquet'
        ],
        'metadata': [
            'simulation_info.parquet',
            'environment_periods.parquet',
            'simulation_errors.parquet'
        ]
    }
    
    found_files = {}
    for category, expected_files in categories.items():
        category_dir = output_dir / category
        found_files[category] = []
        if category_dir.exists():
            for file_name in expected_files:
                if (category_dir / file_name).exists():
                    found_files[category].append(file_name)
    
    return found_files


if __name__ == "__main__":
    # Example usage
    base_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py")
    user_config_id = "0aeab342-dea7-4def-89fa-0ef389ff4f09"
    
    # Extract for all buildings
    results = extract_static_data_for_all_buildings(
        base_dir,
        user_config_id,
        year="2020",
        max_workers=4
    )
    
    # Verify extraction
    parsed_data_dir = base_dir / "output" / user_config_id / "parsed_data"
    found_files = verify_extraction(parsed_data_dir)
    
    print("\nVerification Results:")
    for category, files in found_files.items():
        print(f"\n{category}:")
        for file in files:
            print(f"  ✓ {file}")