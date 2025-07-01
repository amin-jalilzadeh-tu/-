"""
SQL Analyzer Main Module v2.0
Coordinates SQL analysis workflow with proper base/variant handling
"""

import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from datetime import datetime
import re

from .sql_analyzer import EnhancedSQLAnalyzer
from .sql_data_manager import SQLDataManager
from .sql_helpers import find_sql_files, validate_sql_outputs
from .sql_static_extractor import SQLStaticExtractor

class SQLAnalyzerMain:
    """Main coordinator for SQL analysis with base/variant tracking"""
    
    def __init__(self, project_path: Path, job_output_dir: Path = None):
        """Initialize SQL analyzer"""
        self.project_path = Path(project_path)
        self.job_output_dir = job_output_dir
        self.sql_data_manager = SQLDataManager(self.project_path)
        self.sql_analyzers = {}
        self.output_definitions = {}
        self.base_buildings = set()
        
        # Identify base buildings if job_output_dir provided
        if self.job_output_dir:
            self._identify_base_buildings()
    
    def _identify_base_buildings(self):
        """Identify which buildings are base (from output_IDFs)"""
        base_idfs_dir = self.job_output_dir / 'output_IDFs'
        
        if base_idfs_dir.exists():
            for idf in base_idfs_dir.glob('building_*.idf'):
                match = re.search(r'building_(\d+)\.idf', idf.name)
                if match:
                    self.base_buildings.add(match.group(1))
        
        # Pass to data manager
        self.sql_data_manager.set_base_buildings(self.base_buildings)
        
        print(f"Identified {len(self.base_buildings)} base buildings: {sorted(self.base_buildings)}")
    
    def analyze_sql_files(self, sql_files: List[str], 
                         zone_mappings: Dict[str, Dict[str, str]] = None,
                         output_configs: Dict[str, Dict] = None,
                         categories: List[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         validate_outputs: bool = True,
                         is_modified_results: bool = False,
                         extract_static_data: bool = True):
        """
        Analyze multiple SQL files
        
        Args:
            sql_files: List of SQL file paths
            zone_mappings: Zone mapping for each building
            output_configs: Output configuration for each building
            categories: Categories to extract
            start_date: Start date for extraction
            end_date: End date for extraction
            validate_outputs: Whether to validate outputs
            is_modified_results: Whether these are from Modified_Sim_Results
            extract_static_data: Whether to extract static/summary data (default True)
        """
        
        print(f"\nAnalyzing {len(sql_files)} SQL files")
        print(f"Is modified results: {is_modified_results}")
        
        zone_mappings = zone_mappings or {}
        output_configs = output_configs or {}
        
        output_validation_results = []
        
        for sql_path in sql_files:
            print(f"\nProcessing SQL: {Path(sql_path).name}")
            
            try:
                # Initialize SQL analyzer with base building info
                sql_analyzer = EnhancedSQLAnalyzer(
                    Path(sql_path), 
                    self.sql_data_manager,
                    base_buildings=self.base_buildings,
                    is_modified_results=is_modified_results
                )
                
                building_id = sql_analyzer.building_id
                variant_id = sql_analyzer.variant_id
                
                print(f"  Building ID: {building_id}, Variant: {variant_id}")
                
                self.sql_analyzers[f"{building_id}_{variant_id}"] = sql_analyzer
                
                # Get zone mapping for this building
                zone_mapping = zone_mappings.get(building_id, {})
                
                # Validate outputs if requested
                if validate_outputs and building_id in output_configs:
                    validation_result = self._validate_outputs(
                        building_id, 
                        sql_analyzer, 
                        output_configs[building_id]
                    )
                    validation_result['variant_id'] = variant_id
                    output_validation_results.append(validation_result)
                
                # Extract SQL data by category
                from .sql_analyzer import SQL_CATEGORY_MAPPINGS
                variables_by_category = SQL_CATEGORY_MAPPINGS if categories is None else {
                    cat: SQL_CATEGORY_MAPPINGS.get(cat, []) for cat in categories
                }
                
                print("  Extracting SQL time series data...")
                sql_analyzer.extract_and_save_all(
                    zone_mapping, 
                    variables_by_category,
                    start_date=start_date,
                    end_date=end_date,
                    variant_id=variant_id
                )
                
                # Extract static data using new extractor
                if extract_static_data:
                    print("  Extracting SQL static data...")
                    static_extractor = SQLStaticExtractor(
                        Path(sql_path),
                        self.project_path,  # This is the output directory
                        building_id,
                        variant_id
                    )
                    try:
                        static_extractor.extract_all()
                        print("  ✓ Static data extraction completed")
                    except Exception as e:
                        print(f"  ⚠ Static data extraction failed: {e}")
                    finally:
                        static_extractor.close()
                
                print(f"  ✓ SQL analysis completed for {building_id} ({variant_id})")
                
            except Exception as e:
                print(f"[ERROR] Failed to process SQL: {e}")
                import traceback
                traceback.print_exc()
        
        # After all files are processed, transform the data
        print("\nTransforming extracted data...")
        self.sql_data_manager.transform_and_save_base_data()
        
        if is_modified_results:
            # For modified results, we need to point to the base data location
            base_data_dir = self.job_output_dir / 'parsed_data' if self.job_output_dir else None
            self.sql_data_manager.transform_and_save_variant_comparisons(base_data_dir)
        
        # Clean up old structure
        self.sql_data_manager.cleanup_old_structure()
        
        # Save validation results if any
        if output_validation_results:
            self._save_validation_results(output_validation_results)
    
    def _validate_outputs(self, building_id: str, sql_analyzer: EnhancedSQLAnalyzer, 
                        output_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that SQL contains requested outputs"""
        validation_result = {
            'building_id': building_id,
            'total_requested': len(output_config.get('variables', [])),
            'found': 0,
            'missing': [],
            'existing': [],
            'partial': [],
            'coverage': 0.0
        }
        
        # Get available variables from SQL
        available_vars = sql_analyzer.get_available_outputs()
        
        if available_vars.empty:
            return validation_result
        
        # Create lookup set
        available_set = set()
        for _, row in available_vars.iterrows():
            available_set.add((row['VariableName'], row['KeyValue'], row['ReportingFrequency']))
        
        # Check each requested output
        for var_def in output_config.get('variables', []):
            key = var_def.get('key_value', '*')
            var_name = var_def.get('variable_name', '')
            freq = var_def.get('reporting_frequency', 'Hourly')
            
            found = False
            partial = False
            
            if key == '*':
                # Check if variable exists for any key
                matching = available_vars[
                    (available_vars['VariableName'] == var_name) & 
                    (available_vars['ReportingFrequency'] == freq)
                ]
                if not matching.empty:
                    found = True
                    if not matching['HasData'].all():
                        partial = True
            else:
                if (var_name, key, freq) in available_set:
                    found = True
                    specific = available_vars[
                        (available_vars['VariableName'] == var_name) & 
                        (available_vars['KeyValue'] == key) &
                        (available_vars['ReportingFrequency'] == freq)
                    ]
                    if not specific.empty and not specific.iloc[0]['HasData']:
                        partial = True
            
            if found:
                validation_result['found'] += 1
                validation_result['existing'].append({
                    'variable': var_name,
                    'key': key,
                    'frequency': freq,
                    'found_in_sql': True,
                    'has_data': not partial
                })
                if partial:
                    validation_result['partial'].append({
                        'variable': var_name,
                        'key': key,
                        'frequency': freq,
                        'reason': 'No data points found'
                    })
            else:
                validation_result['missing'].append({
                    'variable': var_name,
                    'key': key,
                    'frequency': freq
                })
        
        # Calculate coverage
        if validation_result['total_requested'] > 0:
            validation_result['coverage'] = (
                validation_result['found'] / validation_result['total_requested']
            ) * 100
        
        return validation_result
    
    def _save_validation_results(self, validation_results: List[Dict]):
        """Save validation results"""
        if not validation_results:
            return
        
        validation_df = pd.DataFrame(validation_results)
        output_path = self.project_path / 'metadata' / 'validation_results.parquet'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        validation_df.to_parquet(output_path, index=False)
        
        # Also save detailed missing/existing outputs
        all_missing = []
        all_existing = []
        
        for result in validation_results:
            building_id = result['building_id']
            variant_id = result.get('variant_id', 'base')
            
            for missing in result.get('missing', []):
                missing['building_id'] = building_id
                missing['variant_id'] = variant_id
                all_missing.append(missing)
            
            for existing in result.get('existing', []):
                existing['building_id'] = building_id
                existing['variant_id'] = variant_id
                all_existing.append(existing)
        
        if all_missing:
            missing_df = pd.DataFrame(all_missing)
            missing_path = self.project_path / 'metadata' / 'validation_missing.parquet'
            missing_df.to_parquet(missing_path, index=False)
        
        if all_existing:
            existing_df = pd.DataFrame(all_existing)
            existing_path = self.project_path / 'metadata' / 'validation_existing.parquet'
            existing_df.to_parquet(existing_path, index=False)
    
    def load_base_data(self, frequency: str = 'daily') -> pd.DataFrame:
        """Load base data in semi-wide format"""
        file_path = self.project_path / 'timeseries' / f'base_all_{frequency}.parquet'
        
        if file_path.exists():
            return pd.read_parquet(file_path)
        
        return pd.DataFrame()
    
    def load_variant_comparisons(self, variable_name: str = None, 
                               building_id: str = None,
                               frequency: str = 'daily') -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """Load variant comparison data"""
        variants_dir = self.project_path / 'comparisons'
        
        if not variants_dir.exists():
            return pd.DataFrame() if variable_name else {}
        
        if variable_name and building_id:
            # Load specific variable for specific building
            clean_var_name = (variable_name.lower()
                            .replace(':', '_')
                            .replace(' ', '_')
                            .replace('[', '')
                            .replace(']', '')
                            .replace('(', '')
                            .replace(')', ''))
            
            # Need to search for files matching pattern since unit is now in filename
            import glob
            pattern = f"var_{clean_var_name}_*_{frequency}_b{building_id}.parquet"
            matching_files = list(variants_dir.glob(pattern))
            if matching_files:
                file_path = matching_files[0]
            else:
                return pd.DataFrame()
            
            if file_path.exists():
                return pd.read_parquet(file_path)
            else:
                return pd.DataFrame()
        
        elif building_id:
            # Load all variables for a specific building
            result = {}
            for file_path in variants_dir.glob(f"*_{building_id}.parquet"):
                # Extract variable name from filename
                var_name = file_path.stem.replace(f'_{building_id}', '')
                result[var_name] = pd.read_parquet(file_path)
            return result
        
        else:
            # Load all comparison files
            result = {}
            for file_path in variants_dir.glob("*.parquet"):
                key = file_path.stem
                result[key] = pd.read_parquet(file_path)
            return result
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of analysis results"""
        summary = {
            'base_buildings': sorted(list(self.base_buildings)),
            'total_sql_files_analyzed': len(self.sql_analyzers),
            'variants_by_building': {},
            'data_availability': {}
        }
        
        # Count variants by building
        for key, analyzer in self.sql_analyzers.items():
            building_id = analyzer.building_id
            variant_id = analyzer.variant_id
            
            if building_id not in summary['variants_by_building']:
                summary['variants_by_building'][building_id] = []
            
            if variant_id != 'base':
                summary['variants_by_building'][building_id].append(variant_id)
        
        # Check data availability
        base_data_path = self.project_path / 'timeseries' / 'base' / 'daily' / 'all_variables.parquet'
        summary['data_availability']['base_data'] = base_data_path.exists()
        
        variants_dir = self.project_path / 'timeseries' / 'variants' / 'daily'
        if variants_dir.exists():
            variant_files = list(variants_dir.glob("*.parquet"))
            summary['data_availability']['variant_comparisons'] = len(variant_files)
        else:
            summary['data_availability']['variant_comparisons'] = 0
        
        return summary
    
    def close(self):
        """Close all SQL connections"""
        for sql_analyzer in self.sql_analyzers.values():
            sql_analyzer.close()