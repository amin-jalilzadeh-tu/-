"""
Variant Mapping Utilities
Handles identification of base buildings and variant mappings
"""

import re
from pathlib import Path
from typing import Dict, Set, Tuple

def identify_base_buildings(job_output_dir: Path) -> Set[str]:
    """Identify which buildings are base (from output_IDFs)"""
    base_buildings = set()
    base_idfs_dir = job_output_dir / 'output_IDFs'
    
    if base_idfs_dir.exists():
        for idf in base_idfs_dir.glob('building_*.idf'):
            match = re.search(r'building_(\d+)\.idf', idf.name)
            if match:
                base_buildings.add(match.group(1))
    
    return base_buildings

def create_variant_mapping(job_output_dir: Path) -> Dict[str, Dict[str, Path]]:
    """Create mapping of building -> variant -> SQL file path"""
    variant_mapping = {}
    
    # Check modified IDFs to see which buildings have variants
    modified_idfs_dir = job_output_dir / 'modified_idfs'
    if modified_idfs_dir.exists():
        for idf in modified_idfs_dir.glob('building_*_variant_*.idf'):
            match = re.search(r'building_(\d+)_variant_(\d+)\.idf', idf.name)
            if match:
                building_id = match.group(1)
                variant_num = match.group(2)
                
                if building_id not in variant_mapping:
                    variant_mapping[building_id] = {}
                
                # SQL uses offset numbering: bldg1 = variant_0, bldg2 = variant_1, etc.
                sql_bldg_num = int(variant_num) + 1
                variant_mapping[building_id][f'variant_{variant_num}'] = sql_bldg_num
    
    return variant_mapping

def get_sql_variant_info(sql_filename: str, variant_mapping: Dict[str, Dict[str, int]]) -> Tuple[str, str]:
    """
    Extract building ID and variant ID from SQL filename
    Returns: (building_id, variant_id)
    """
    # Match pattern: simulation_bldg{X}_{building_id}.sql
    match = re.search(r'simulation_bldg(\d+)_(\d+)\.sql', sql_filename)
    if match:
        bldg_num = int(match.group(1))
        building_id = match.group(2)
        
        # Check if this is a variant
        if bldg_num == 0:
            # Base simulation
            return building_id, 'base'
        else:
            # Find which variant this is
            if building_id in variant_mapping:
                for variant_id, sql_num in variant_mapping[building_id].items():
                    if sql_num == bldg_num:
                        return building_id, variant_id
            
            # Fallback: assume variant_{bldg_num-1}
            return building_id, f'variant_{bldg_num-1}'
    
    return None, None