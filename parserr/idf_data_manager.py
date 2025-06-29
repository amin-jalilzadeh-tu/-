"""
IDF Data Manager Module
Handles IDF-specific data storage
"""

import os
import json
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

class IDFDataManager:
    """Manages IDF-specific data storage"""
    
    def __init__(self, base_path: Union[str, Path]):
        """Initialize IDF data manager"""
        self.base_path = Path(base_path)
        self._initialize_structure()
        self._category_buffers = {}
        
    def _initialize_structure(self):
        """Create IDF-specific directory structure"""
        directories = [
            'metadata',
            'idf_data/by_category',
            'idf_data/by_building',
            'relationships',
            'analysis_ready/feature_sets'
        ]
        
        for dir_path in directories:
            (self.base_path / dir_path).mkdir(parents=True, exist_ok=True)
    
    def update_project_manifest(self, total_buildings: int, categories: List[str]):
        """Update project manifest"""
        manifest = {
            'project_id': self.base_path.name,
            'created': datetime.now().isoformat(),
            'total_buildings': total_buildings,
            'categories_tracked': categories,
            'last_updated': datetime.now().isoformat(),
            'data_version': '3.1',
            'file_structure': {
                'idf_data': {
                    'by_category': 'Consolidated category files across all buildings',
                    'by_building': 'Complete parameter snapshots per building'
                }
            }
        }
        
        manifest_path = self.base_path / 'metadata' / 'project_manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def update_building_registry(self, building_data: pd.DataFrame):
        """Update building registry"""
        registry_path = self.base_path / 'metadata' / 'building_registry.parquet'
        
        required_cols = ['building_id', 'ogc_fid', 'idf_path', 'zone_count', 
                        'status', 'last_modified', 'variant_id']
        
        for col in required_cols:
            if col not in building_data.columns:
                if col == 'last_modified':
                    building_data[col] = datetime.now()
                elif col == 'status':
                    building_data[col] = 'completed'
                else:
                    building_data[col] = None
        
        building_data[required_cols].to_parquet(registry_path, index=False)
    
    def save_idf_category_data(self, category_file: str, data: pd.DataFrame, 
                            mode: str = 'append'):
        """Save IDF data to consolidated category files"""
        if data.empty:
            return
        
        if 'variant_id' not in data.columns:
            data['variant_id'] = 'base'
            
        file_path = self.base_path / 'idf_data' / 'by_category' / f"{category_file}.parquet"
        
        if mode == 'append' and file_path.exists():
            existing_data = pd.read_parquet(file_path)
            combined_data = pd.concat([existing_data, data], ignore_index=True)
            
            if 'building_id' in combined_data.columns and 'object_name' in combined_data.columns:
                combined_data = combined_data.drop_duplicates(
                    subset=['building_id', 'object_name'], 
                    keep='last'
                )
            
            combined_data.to_parquet(file_path, index=False)
        else:
            data.to_parquet(file_path, index=False)
    
    def buffer_category_data(self, category_file: str, data: pd.DataFrame):
        """Buffer category data for batch writing"""
        if data.empty:
            return
            
        if category_file not in self._category_buffers:
            self._category_buffers[category_file] = []
        
        self._category_buffers[category_file].append(data)
    
    def flush_category_buffers(self):
        """Flush all buffered category data to disk"""
        for category_file, data_list in self._category_buffers.items():
            if data_list:
                combined_data = pd.concat(data_list, ignore_index=True)
                self.save_idf_category_data(category_file, combined_data)
        
        self._category_buffers.clear()
    
    def save_building_snapshot(self, building_id: str, all_params: pd.DataFrame):
        """Save complete parameter snapshot for a building"""
        snapshot_path = self.base_path / 'idf_data' / 'by_building' / f"{building_id}_snapshot.parquet"
        all_params.to_parquet(snapshot_path, index=False)
    
    def save_relationships(self, relationship_type: str, data: pd.DataFrame):
        """Save relationship data"""
        if data.empty:
            return
            
        output_path = self.base_path / 'relationships' / f"{relationship_type}.parquet"
        
        if output_path.exists():
            existing_data = pd.read_parquet(output_path)
            combined_data = pd.concat([existing_data, data], ignore_index=True)
            
            if relationship_type == 'zone_mappings':
                combined_data = combined_data.drop_duplicates(
                    subset=['building_id', 'idf_zone_name'], 
                    keep='last'
                )
            elif relationship_type == 'equipment_assignments':
                combined_data = combined_data.drop_duplicates(
                    subset=['building_id', 'equipment_name', 'assigned_zone'], 
                    keep='last'
                )
            
            combined_data.to_parquet(output_path, index=False)
        else:
            data.to_parquet(output_path, index=False)
    
    def save_analysis_ready_data(self, data: pd.DataFrame, dataset_name: str):
        """Save analysis-ready datasets"""
        if data.empty:
            return
            
        if dataset_name == 'parameter_matrix':
            output_path = self.base_path / 'analysis_ready' / 'parameter_matrix.parquet'
        else:
            output_path = self.base_path / 'analysis_ready' / 'feature_sets' / f"{dataset_name}.parquet"
        
        data.to_parquet(output_path, index=False)
    
    def load_category_data(self, category_file: str) -> pd.DataFrame:
        """Load IDF data for a specific category file"""
        file_path = self.base_path / 'idf_data' / 'by_category' / f"{category_file}.parquet"
        
        if file_path.exists():
            return pd.read_parquet(file_path)
        
        return pd.DataFrame()
    
    def load_building_snapshot(self, building_id: str) -> pd.DataFrame:
        """Load complete parameter snapshot for a building"""
        snapshot_path = self.base_path / 'idf_data' / 'by_building' / f"{building_id}_snapshot.parquet"
        
        if snapshot_path.exists():
            return pd.read_parquet(snapshot_path)
        return pd.DataFrame()
    
    def update_category_schemas(self):
        """Save category schemas"""
        schemas = {}
        
        category_path = self.base_path / 'idf_data' / 'by_category'
        for file_path in category_path.glob('*.parquet'):
            try:
                df = pd.read_parquet(file_path)
                if not df.empty:
                    schemas[file_path.stem] = {
                        'columns': list(df.columns),
                        'dtypes': df.dtypes.astype(str).to_dict(),
                        'row_count': len(df),
                        'building_count': df['building_id'].nunique() if 'building_id' in df.columns else 0
                    }
                    
                    if file_path.stem == 'outputs_all' and 'output_type' in df.columns:
                        schemas[file_path.stem]['output_types'] = df['output_type'].value_counts().to_dict()
                else:
                    schemas[file_path.stem] = {
                        'columns': [],
                        'dtypes': {},
                        'row_count': 0,
                        'building_count': 0
                    }
            except Exception as e:
                schemas[file_path.stem] = {'error': f'Could not read schema: {str(e)}'}
        
        schema_path = self.base_path / 'metadata' / 'category_schemas.json'
        with open(schema_path, 'w') as f:
            json.dump(schemas, f, indent=2)
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of IDF data"""
        summary = {
            'base_path': str(self.base_path),
            'categories': {},
            'buildings': [],
            'relationships': []
        }
        
        # Check category files
        category_path = self.base_path / 'idf_data' / 'by_category'
        for file_path in category_path.glob('*.parquet'):
            category_name = file_path.stem
            try:
                df = pd.read_parquet(file_path)
                summary['categories'][category_name] = {
                    'rows': len(df),
                    'buildings': df['building_id'].nunique() if 'building_id' in df.columns else 0
                }
            except:
                summary['categories'][category_name] = {'error': 'Could not read file'}
        
        # Check buildings
        building_path = self.base_path / 'idf_data' / 'by_building'
        if building_path.exists():
            summary['buildings'] = [f.stem.replace('_snapshot', '') for f in building_path.glob('*_snapshot.parquet')]
        
        # Check relationships
        rel_path = self.base_path / 'relationships'
        if rel_path.exists():
            summary['relationships'] = [f.stem for f in rel_path.glob('*.parquet')]
        
        return summary

def create_idf_parameter_matrix(data_manager: IDFDataManager,
                               building_ids: List[str] = None) -> pd.DataFrame:
    """Create parameter matrix for IDF analysis"""
    all_params = []
    
    # Define which category files to include
    category_files = {
        'geometry_zones': ['volume', 'floor_area', 'ceiling_height'],
        'materials_constructions': ['outside_layer', 'layer_2', 'layer_3'],
        'hvac_equipment': ['cooling_capacity', 'heating_capacity', 'cop'],
        'hvac_thermostats': ['heating_setpoint_temperature_schedule_name', 
                            'cooling_setpoint_temperature_schedule_name'],
        'ventilation': ['design_flow_rate', 'air_changes_per_hour'],
        'infiltration': ['design_flow_rate', 'air_changes_per_hour'],
        'lighting': ['lighting_level', 'watts_per_zone_floor_area'],
        'equipment': ['design_level', 'watts_per_zone_floor_area'],
        'dhw': ['tank_volume', 'heater_maximum_capacity']
    }
    
    for file_name, key_params in category_files.items():
        cat_data = data_manager.load_category_data(file_name)
        if not cat_data.empty:
            if 'building_id' not in cat_data.columns:
                print(f"Warning: No building_id column in {file_name}")
                continue
                
            cols_to_keep = ['building_id']
            params_found = []
            
            for param in key_params:
                possible_names = [
                    param,
                    param + '_numeric',
                    param.replace('_', ' ').title().replace(' ', '_').lower(),
                    param.replace('_', ' ').lower()
                ]
                
                for col_name in possible_names:
                    if col_name in cat_data.columns:
                        try:
                            test_numeric = pd.to_numeric(cat_data[col_name], errors='coerce')
                            if not test_numeric.isna().all():
                                cols_to_keep.append(col_name)
                                params_found.append(col_name)
                                break
                        except:
                            continue
            
            if len(cols_to_keep) > 1:
                subset_data = cat_data[cols_to_keep].copy()
                
                numeric_cols = subset_data.select_dtypes(include=[np.number]).columns.tolist()
                numeric_cols = [col for col in numeric_cols if col != 'building_id']
                
                if numeric_cols:
                    agg_dict = {col: 'mean' for col in numeric_cols}
                    subset_data = subset_data.groupby('building_id').agg(agg_dict).reset_index()
                else:
                    subset_data = subset_data.groupby('building_id').first().reset_index()
                
                prefix = file_name.split('_')[0]
                subset_data.columns = ['building_id'] + [f"{prefix}_{col}" for col in subset_data.columns[1:]]
                
                all_params.append(subset_data)
    
    if all_params:
        matrix = all_params[0]
        for df in all_params[1:]:
            matrix = matrix.merge(df, on='building_id', how='outer')
        
        if building_ids:
            matrix = matrix[matrix['building_id'].isin(building_ids)]
        
        data_manager.save_analysis_ready_data(matrix, 'parameter_matrix')
        
        return matrix
    
    return pd.DataFrame()