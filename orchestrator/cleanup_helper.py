"""
Cleanup Helper Module
Removes duplicate files and old directory structures
"""

import os
import shutil
from pathlib import Path
from typing import List, Set
import logging


def cleanup_parsed_data(job_output_dir: str, logger: logging.Logger = None):
    """
    Clean up old parsing structure and duplicate files
    
    Args:
        job_output_dir: Job output directory
        logger: Logger instance
    """
    if not logger:
        logger = logging.getLogger(__name__)
    
    job_path = Path(job_output_dir)
    
    # Directories to clean up
    old_structures = [
        # In parsed_data
        'parsed_data/sql_results/timeseries/raw',
        'parsed_data/sql_results/timeseries/hourly',
        'parsed_data/sql_results/timeseries/aggregated',
        'parsed_data/sql_results/by_building',
        'parsed_data/idf_data/by_building',
        
        # In parsed_modified_results
        'parsed_modified_results/sql_results/timeseries/raw',
        'parsed_modified_results/sql_results/timeseries/hourly',
        'parsed_modified_results/sql_results/timeseries/aggregated',
        'parsed_modified_results/sql_results/by_building',
        'parsed_modified_results/idf_data/by_building',
    ]
    
    logger.info("[INFO] Cleaning up old parsing structures...")
    
    for old_dir in old_structures:
        dir_path = job_path / old_dir
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                logger.info(f"  Removed: {old_dir}")
            except Exception as e:
                logger.error(f"  Failed to remove {old_dir}: {e}")
    
    # Clean up empty directories
    clean_empty_dirs(job_path / 'parsed_data')
    clean_empty_dirs(job_path / 'parsed_modified_results')
    
    logger.info("[INFO] Cleanup complete")


def clean_empty_dirs(base_path: Path):
    """Remove empty directories recursively"""
    if not base_path.exists():
        return
    
    # Walk through directory tree bottom-up
    for dirpath, dirnames, filenames in os.walk(str(base_path), topdown=False):
        # If directory is empty (no files and no subdirectories)
        if not filenames and not dirnames:
            try:
                os.rmdir(dirpath)
            except:
                pass


def verify_new_structure(job_output_dir: str) -> dict:
    """
    Verify the new parsing structure is correct
    
    Returns:
        Dictionary with verification results
    """
    job_path = Path(job_output_dir)
    results = {
        'base_data': {},
        'variant_data': {},
        'issues': []
    }
    
    # Check base data
    base_file = job_path / 'parsed_data' / 'timeseries' / 'base' / 'daily' / 'all_variables.parquet'
    results['base_data']['exists'] = base_file.exists()
    results['base_data']['path'] = str(base_file)
    
    if base_file.exists():
        results['base_data']['size_mb'] = base_file.stat().st_size / (1024 * 1024)
    
    # Check variant data
    variants_dir = job_path / 'parsed_data' / 'timeseries' / 'variants' / 'daily'
    if variants_dir.exists():
        variant_files = list(variants_dir.glob('*.parquet'))
        results['variant_data']['exists'] = True
        results['variant_data']['num_files'] = len(variant_files)
        results['variant_data']['total_size_mb'] = sum(f.stat().st_size for f in variant_files) / (1024 * 1024)
        
        # Extract unique buildings with variants
        buildings_with_variants = set()
        for f in variant_files:
            import re
            match = re.search(r'_(\d+)\.parquet$', f.name)
            if match:
                buildings_with_variants.add(match.group(1))
        
        results['variant_data']['buildings'] = sorted(list(buildings_with_variants))
    else:
        results['variant_data']['exists'] = False
    
    # Check for issues
    # Issue 1: Old structures still exist
    old_dirs = [
        'parsed_data/sql_results/timeseries/raw',
        'parsed_data/sql_results/timeseries/hourly',
        'parsed_modified_results/sql_results/timeseries/raw'
    ]
    
    for old_dir in old_dirs:
        if (job_path / old_dir).exists():
            results['issues'].append(f"Old directory still exists: {old_dir}")
    
    # Issue 2: No base data but variants exist
    if not results['base_data']['exists'] and results['variant_data'].get('exists', False):
        results['issues'].append("Variant data exists but no base data found")
    
    return results


def migrate_old_data(job_output_dir: str, logger: logging.Logger = None):
    """
    Migrate data from old structure to new structure if needed
    
    Args:
        job_output_dir: Job output directory
        logger: Logger instance
    """
    if not logger:
        logger = logging.getLogger(__name__)
    
    job_path = Path(job_output_dir)
    
    # Check if migration is needed
    old_base_path = job_path / 'parsed_data' / 'sql_results' / 'timeseries' / 'base' / 'daily'
    new_base_path = job_path / 'parsed_data' / 'timeseries' / 'base' / 'daily'
    
    if old_base_path.exists() and not new_base_path.exists():
        logger.info("[INFO] Migrating data from old structure to new structure...")
        
        # Create new directories
        new_base_path.mkdir(parents=True, exist_ok=True)
        
        # Move base data
        old_base_file = old_base_path / 'all_variables.parquet'
        if old_base_file.exists():
            shutil.move(str(old_base_file), str(new_base_path / 'all_variables.parquet'))
            logger.info("  Migrated base data")
        
        # Move variant data
        old_variants_path = job_path / 'parsed_data' / 'sql_results' / 'timeseries' / 'variants' / 'daily'
        new_variants_path = job_path / 'parsed_data' / 'timeseries' / 'variants' / 'daily'
        
        if old_variants_path.exists() and not new_variants_path.exists():
            new_variants_path.mkdir(parents=True, exist_ok=True)
            
            for old_file in old_variants_path.glob('*.parquet'):
                shutil.move(str(old_file), str(new_variants_path / old_file.name))
            
            logger.info(f"  Migrated {len(list(old_variants_path.glob('*.parquet')))} variant files")
        
        logger.info("[INFO] Migration complete")


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        job_dir = sys.argv[1]
        
        # Run cleanup
        cleanup_parsed_data(job_dir)
        
        # Verify structure
        results = verify_new_structure(job_dir)
        
        print("\nVerification Results:")
        print(f"Base data exists: {results['base_data']['exists']}")
        print(f"Variant data exists: {results['variant_data'].get('exists', False)}")
        
        if results['issues']:
            print("\nIssues found:")
            for issue in results['issues']:
                print(f"  - {issue}")
        else:
            print("\nNo issues found!")