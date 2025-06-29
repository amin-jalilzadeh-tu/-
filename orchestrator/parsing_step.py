"""
orchestrator/parsing_step.py v2.0

Enhanced parsing logic with proper base/variant separation
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import pandas as pd
import re

# Import the new separated modules
from parserr.idf_analyzer_main import IDFAnalyzer
from parserr.sql_analyzer_main import SQLAnalyzerMain
from parserr.idf_helpers import prepare_idf_files, get_idf_data_info
from parserr.sql_helpers import find_sql_files, get_sql_data_info, prepare_sql_file_pairs
from parserr.helpers import prepare_idf_sql_pairs_with_mapping


class CombinedAnalyzer:
    """Enhanced analyzer with proper base/variant handling"""
    
    def __init__(self, project_path: str, job_output_dir: str = None):
        self.project_path = Path(project_path)
        self.job_output_dir = Path(job_output_dir) if job_output_dir else None
        self.idf_analyzer = None
        self.sql_analyzer = None
        self.base_buildings = set()
        
        # Identify base buildings from output_IDFs
        if self.job_output_dir:
            self._identify_base_buildings()
    
    def _identify_base_buildings(self):
        """Identify base buildings from output_IDFs directory"""
        base_idfs_dir = self.job_output_dir / 'output_IDFs'
        
        if base_idfs_dir.exists():
            for idf_file in base_idfs_dir.glob('building_*.idf'):
                match = re.search(r'building_(\d+)\.idf', idf_file.name)
                if match:
                    self.base_buildings.add(match.group(1))
    
    def analyze_project(self, idf_sql_pairs: List[Tuple[str, str]],
                       categories: List[str] = None,
                       validate_outputs: bool = True,
                       building_id_map: Optional[Dict[str, str]] = None,
                       is_modified_results: bool = False):
        """Analyze project with both IDF and SQL files"""
        
        # Initialize analyzers if not already done
        if not self.idf_analyzer:
            self.idf_analyzer = IDFAnalyzer(self.project_path)
        if not self.sql_analyzer:
            self.sql_analyzer = SQLAnalyzerMain(self.project_path, self.job_output_dir)
        
        # Separate IDF and SQL files
        idf_files = []
        sql_files = []
        
        for idf_path, sql_path in idf_sql_pairs:
            if idf_path and os.path.exists(idf_path):
                idf_files.append(idf_path)
            if sql_path and os.path.exists(sql_path):
                sql_files.append(sql_path)
        
        # Parse IDF files first
        if idf_files:
            print(f"\nParsing {len(idf_files)} IDF files...")
            self.idf_analyzer.analyze_idf_files(
                idf_files=idf_files,
                categories=categories,
                building_id_map=building_id_map
            )
            
            # Get zone mappings and output configs from IDF analyzer
            zone_mappings = {}
            output_configs = {}
            
            for building_id, output_config in self.idf_analyzer.output_definitions.items():
                zone_mappings[building_id] = {}  # Would be populated from IDF data
                output_configs[building_id] = output_config
        
        # Parse SQL files
        if sql_files:
            print(f"\nParsing {len(sql_files)} SQL files...")
            
            self.sql_analyzer.analyze_sql_files(
                sql_files=sql_files,
                zone_mappings=zone_mappings if 'zone_mappings' in locals() else {},
                output_configs=output_configs if 'output_configs' in locals() else {},
                categories=categories,
                validate_outputs=validate_outputs,
                is_modified_results=is_modified_results
            )
    
    def close(self):
        """Close all connections"""
        if self.sql_analyzer:
            self.sql_analyzer.close()


def get_parsed_data_info(parser_output_dir: str) -> Dict[str, any]:
    """Get combined info about parsed IDF and SQL data"""
    info = {
        'parsed_data_dir': parser_output_dir,
        'base_data': {},
        'variant_data': {},
        'idf_data': {}
    }
    
    # Check for base data
    base_path = Path(parser_output_dir) / 'timeseries' / 'base_all_daily.parquet'
    if base_path.exists():
        try:
            base_df = pd.read_parquet(base_path)
            info['base_data'] = {
                'exists': True,
                'rows': len(base_df),
                'buildings': base_df['building_id'].nunique() if 'building_id' in base_df.columns else 0,
                'variables': base_df['VariableName'].nunique() if 'VariableName' in base_df.columns else 0,
                'date_columns': len([c for c in base_df.columns if c.startswith('20')])
            }
        except:
            info['base_data']['exists'] = False
    
    # Check for variant data
    variants_path = Path(parser_output_dir) / 'comparisons'
    if variants_path.exists():
        variant_files = list(variants_path.glob('*.parquet'))
        info['variant_data'] = {
            'exists': True,
            'comparison_files': len(variant_files),
            'buildings_with_variants': set()
        }
        
        # Extract building IDs from filenames
        for file in variant_files:
            match = re.search(r'_(\d+)\.parquet$', file.name)
            if match:
                info['variant_data']['buildings_with_variants'].add(match.group(1))
        
        info['variant_data']['buildings_with_variants'] = sorted(list(info['variant_data']['buildings_with_variants']))
    
    # Get IDF info
    idf_info = get_idf_data_info(parser_output_dir)
    info['idf_data'] = idf_info
    
    return info


def run_parsing(
    parsing_cfg: dict,
    main_config: dict,
    job_output_dir: str,
    job_id: str,
    logger: logging.Logger
) -> None:
    """
    Run parsing of IDF/SQL files to Parquet format with proper base data handling.
    """
    logger.info("[INFO] Parsing IDF/SQL files to Parquet format...")
    
    # Create parser output directory
    parser_output_dir = os.path.join(job_output_dir, "parsed_data")
    os.makedirs(parser_output_dir, exist_ok=True)
    
    # Initialize the combined analyzer
    analyzer = CombinedAnalyzer(parser_output_dir, job_output_dir)
    
    # Get parsing configuration details
    parse_mode = parsing_cfg.get("parse_mode", "all")
    parse_types = parsing_cfg.get("parse_types", {"idf": True, "sql": True})
    building_selection = parsing_cfg.get("building_selection", {})
    categories_to_parse = parsing_cfg.get("categories", None)
    
    # Use the same approach as before
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
    logger.info(f"[INFO] Base buildings identified: {sorted(analyzer.base_buildings)}")
    
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
    
    # Check parse_types to determine what to parse
    should_parse_idf = parse_types.get("idf", True)
    should_parse_sql = parse_types.get("sql", True)
    
    # Filter pairs based on parse_types
    if not should_parse_idf:
        # Convert to SQL-only pairs
        idf_sql_pairs = [(None, sql_path) for _, sql_path in idf_sql_pairs if sql_path]
    elif not should_parse_sql:
        # Convert to IDF-only pairs
        idf_sql_pairs = [(idf_path, None) for idf_path, _ in idf_sql_pairs if idf_path]
    
    # Run the analysis (BASE data)
    analyzer.analyze_project(
        idf_sql_pairs=idf_sql_pairs,
        categories=categories_to_parse,
        validate_outputs=True,
        building_id_map=building_id_map,
        is_modified_results=False  # This is BASE data
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
        'base_buildings': sorted(list(analyzer.base_buildings)),
        'configuration': {
            'parse_mode': parse_mode,
            'categories': categories_to_parse
        }
    }
    
    summary_path = os.path.join(parser_output_dir, 'parsing_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(parsing_summary, f, indent=2)
    
    # Get analysis summary from SQL analyzer
    if analyzer.sql_analyzer:
        analysis_summary = analyzer.sql_analyzer.get_analysis_summary()
        logger.info(f"[INFO] SQL Analysis Summary:")
        logger.info(f"  Base buildings: {analysis_summary['base_buildings']}")
        logger.info(f"  Base data available: {analysis_summary['data_availability']['base_data']}")
    
    logger.info(f"[INFO] Parsing complete. Data saved to: {parser_output_dir}")
    
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
    Parse modified simulation results with proper variant tracking.
    """
    logger.info("[INFO] Parsing modified simulation results...")
    
    # Create parser output directory
    parser_output_dir = os.path.join(job_output_dir, "parsed_modified_results")
    os.makedirs(parser_output_dir, exist_ok=True)
    
    # Initialize the analyzer
    analyzer = CombinedAnalyzer(parser_output_dir, job_output_dir)
    
    # Manually prepare IDF-SQL pairs for modified results
    idf_sql_pairs = []
    building_id_map = {}
    
    # Find all modified IDF files
    modified_idfs_path = Path(modified_idfs_dir)
    idf_files = list(modified_idfs_path.glob("building_*_variant_*.idf"))
    
    logger.info(f"[INFO] Found {len(idf_files)} modified IDF files")
    
    # Find SQL files in modified simulation output
    sim_output_path = Path(modified_sim_output)
    
    # Create mapping of building_id -> variant_num -> idf_file
    variant_mapping = {}
    for idf_file in idf_files:
        # Parse IDF filename: building_4136733_variant_0.idf
        match = re.search(r'building_(\d+)_variant_(\d+)\.idf', idf_file.name)
        if match:
            building_id = match.group(1)
            variant_num = match.group(2)
            
            if building_id not in variant_mapping:
                variant_mapping[building_id] = {}
            
            variant_mapping[building_id][variant_num] = idf_file
    
    # Now find SQL files and match them
    sql_files = list(sim_output_path.glob("**/*.sql"))
    logger.info(f"[INFO] Found {len(sql_files)} SQL files in modified results")
    
    # Match SQL files to IDFs
    for sql_file in sql_files:
        # Parse SQL filename: simulation_bldg1_4136733.sql
        match = re.search(r'simulation_bldg(\d+)_(\d+)\.sql', sql_file.name)
        if match:
            bldg_index = int(match.group(1))
            building_id = match.group(2)
            
            # The bldg index corresponds to variant number
            variant_num = str(bldg_index)
            
            # Find corresponding IDF
            if building_id in variant_mapping and variant_num in variant_mapping[building_id]:
                idf_file = variant_mapping[building_id][variant_num]
                idf_sql_pairs.append((str(idf_file), str(sql_file)))
                building_id_map[str(idf_file)] = building_id
                
                logger.info(f"  Matched: {idf_file.name} -> {sql_file.name}")
    
    if not idf_sql_pairs:
        logger.warning("[WARN] No valid IDF-SQL pairs found for modified results")
        return
    
    logger.info(f"[INFO] Found {len(idf_sql_pairs)} modified file pairs to parse")
    
    # Get parse categories
    parse_categories = parse_cfg.get("categories", None)
    
    # Run analysis with variant tracking (MODIFIED data)
    try:
        analyzer.analyze_project(
            idf_sql_pairs=idf_sql_pairs,
            categories=parse_categories,
            validate_outputs=True,
            building_id_map=building_id_map,
            is_modified_results=True  # This is MODIFIED data with variants
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
        'job_id': job_output_dir.split('/')[-1],
        'type': 'modified_results',
        'files_parsed': len(idf_sql_pairs),
        'parser_output_dir': parser_output_dir,
        'timestamp': datetime.now().isoformat(),
        'parsed_data_info': parsed_info,
        'buildings_with_variants': list(variant_mapping.keys())
    }
    
    summary_path = os.path.join(parser_output_dir, 'parsing_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(parsing_summary, f, indent=2)
    
    # Get analysis summary
    if analyzer.sql_analyzer:
        analysis_summary = analyzer.sql_analyzer.get_analysis_summary()
        logger.info(f"[INFO] Modified Results Analysis Summary:")
        logger.info(f"  Buildings with variants: {list(analysis_summary['variants_by_building'].keys())}")
        logger.info(f"  Variant comparisons created: {analysis_summary['data_availability']['variant_comparisons']}")
    
    logger.info(f"[INFO] Parsed modified results saved to: {parser_output_dir}")
    
    # Close analyzer
    analyzer.close()