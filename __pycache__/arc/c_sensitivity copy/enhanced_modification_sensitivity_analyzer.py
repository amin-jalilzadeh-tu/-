"""
c_sensitivity/enhanced_modification_sensitivity_analyzer.py

Enhanced analyzer with multi-level support for building, zone, and equipment analysis.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
import json
from datetime import datetime
from scipy import stats
import warnings

from .relationship_manager import RelationshipManager
from .modification_sensitivity_analyzer import ModificationSensitivityResult

warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)

@dataclass
class MultiLevelSensitivityResult:
    """Container for multi-level sensitivity results"""
    level: str  # 'building', 'zone', 'equipment', 'cross-level'
    source_scope: str  # Where parameter is defined
    target_scope: str  # Where output is measured
    parameter: str
    category: str
    output_variable: str
    output_zone: Optional[str]  # Which zone for zone-level outputs
    sensitivity_score: float
    correlation: float
    p_value: float
    n_samples: int
    mean_param_change: float
    mean_output_change: float
    elasticity: float
    confidence_level: str
    affected_zones: List[str]

class EnhancedModificationSensitivityAnalyzer:
    """Enhanced analyzer with zone and equipment level analysis"""
    
    def __init__(self, job_output_dir: Path, logger: Optional[logging.Logger] = None):
        self.job_output_dir = Path(job_output_dir)
        self.logger = logger or logging.getLogger(__name__)
        
        # Define paths
        self.base_parsed_dir = self.job_output_dir / "parsed_data"
        self.modified_parsed_dir = self.job_output_dir / "parsed_modified_results"
        self.modifications_dir = self.job_output_dir / "modified_idfs"
        self.validation_dir = self.job_output_dir / "validation_results"
        
        # Initialize relationship manager
        self.relationship_manager = RelationshipManager(self.base_parsed_dir, self.logger)
        
        # Data containers
        self.modification_tracking = None
        self.modification_hierarchy = None
        self.base_results = {}
        self.modified_results = {}
        self.zone_level_deltas = {}
        self.building_level_deltas = {}
        self.multi_level_results = []
    
    def load_modification_tracking_with_scope(self) -> pd.DataFrame:
        """Load modification tracking and determine scope for each modification"""
        self.logger.info("Loading modification tracking with scope detection...")
        
        # Find latest modification detail file
        mod_files = list(self.modifications_dir.glob("modifications_detail_*.parquet"))
        if not mod_files:
            raise FileNotFoundError("No modification tracking files found")
            
        latest_file = max(mod_files, key=lambda x: x.stat().st_mtime)
        self.logger.info(f"Loading modifications from: {latest_file}")
        
        # Load modifications
        df = pd.read_parquet(latest_file)
        
        # Parse numeric values
        df['original_value_numeric'] = pd.to_numeric(df['original_value'], errors='coerce')
        df['new_value_numeric'] = pd.to_numeric(df['new_value'], errors='coerce')
        df['param_delta'] = df['new_value_numeric'] - df['original_value_numeric']
        df['param_pct_change'] = (df['param_delta'] / df['original_value_numeric'].replace(0, np.nan)) * 100
        df['param_key'] = df['category'] + '_' + df['object_type'] + '_' + df['field_name']
        
        # Detect scope for each modification
        scopes = []
        affected_zones_list = []
        
        for _, row in df.iterrows():
            scope, affected_zones = self.relationship_manager.detect_modification_scope(
                row['object_name'],
                row['object_type'],
                str(row['building_id'])
            )
            scopes.append(scope)
            affected_zones_list.append(affected_zones)
        
        df['scope'] = scopes
        df['affected_zones'] = affected_zones_list
        
        self.modification_tracking = df
        
        # Create hierarchical view
        self.modification_hierarchy = self.relationship_manager.create_modification_hierarchy(df)
        
        # Log statistics
        scope_counts = df['scope'].value_counts()
        self.logger.info(f"Modification scopes: {scope_counts.to_dict()}")
        self.logger.info(f"Total modifications: {len(df)}")
        
        return df
    
    def load_zone_level_results(self, result_type: str = 'daily') -> Tuple[Dict, Dict]:
        """Load simulation results at zone level"""
        self.logger.info(f"Loading zone-level {result_type} results...")
        
        # Categories that have zone-level data
        zone_categories = ['hvac', 'temperature', 'ventilation', 'zones']
        
        base_zone_results = {}
        modified_zone_results = {}
        
        for category in zone_categories:
            # Base results
            base_path = self.base_parsed_dir / f"sql_results/timeseries/aggregated/{result_type}/{category}_{result_type}.parquet"
            if base_path.exists():
                df = pd.read_parquet(base_path)
                # Keep zone information
                if 'Zone' in df.columns:
                    base_zone_results[category] = df
                    self.logger.debug(f"Loaded base {category} with {df['Zone'].nunique()} zones")
            
            # Modified results
            mod_path = self.modified_parsed_dir / f"sql_results/timeseries/aggregated/{result_type}/{category}_{result_type}.parquet"
            if mod_path.exists():
                df = pd.read_parquet(mod_path)
                if 'Zone' in df.columns:
                    modified_zone_results[category] = df
                    self.logger.debug(f"Loaded modified {category} with {df['Zone'].nunique()} zones")
        
        return base_zone_results, modified_zone_results
    
    def calculate_zone_level_deltas(self, 
                                  output_variables: List[str], 
                                  aggregation: str = 'sum') -> pd.DataFrame:
        """Calculate output deltas at zone level"""
        self.logger.info("Calculating zone-level output deltas...")
        
        # Load zone results if not already loaded
        if not hasattr(self, 'base_zone_results'):
            self.base_zone_results, self.modified_zone_results = self.load_zone_level_results()
        
        delta_records = []
        
        # Get unique building-zone combinations from modifications
        zone_modifications = self.modification_tracking[self.modification_tracking['scope'].isin(['zone', 'equipment'])]
        
        for building_id in zone_modifications['building_id'].unique():
            building_zones = self.relationship_manager.get_building_zones(str(building_id))
            
            for zone in building_zones:
                # Get SQL zone name
                sql_zone = self.relationship_manager.get_sql_zone_name(str(building_id), zone)
                
                zone_deltas = {
                    'building_id': building_id,
                    'zone': zone,
                    'sql_zone': sql_zone
                }
                
                # Calculate deltas for each variable
                for var_name in output_variables:
                    var_found = False
                    
                    for category in self.base_zone_results:
                        if var_name in self.base_zone_results[category].columns or \
                           ('Variable' in self.base_zone_results[category].columns and 
                            var_name in self.base_zone_results[category]['Variable'].unique()):
                            
                            # Get base and modified data for this zone
                            base_df = self.base_zone_results[category]
                            mod_df = self.modified_zone_results.get(category, pd.DataFrame())
                            
                            if mod_df.empty:
                                continue
                            
                            # Filter by building and zone
                            if 'Variable' in base_df.columns:
                                base_data = base_df[
                                    (base_df['building_id'] == building_id) & 
                                    (base_df['Zone'] == sql_zone) &
                                    (base_df['Variable'] == var_name)
                                ]
                                mod_data = mod_df[
                                    (mod_df['building_id'] == building_id) & 
                                    (mod_df['Zone'] == sql_zone) &
                                    (mod_df['Variable'] == var_name)
                                ]
                            else:
                                base_data = base_df[
                                    (base_df['building_id'] == building_id) & 
                                    (base_df['Zone'] == sql_zone)
                                ]
                                mod_data = mod_df[
                                    (mod_df['building_id'] == building_id) & 
                                    (mod_df['Zone'] == sql_zone)
                                ]
                            
                            if len(base_data) > 0 and len(mod_data) > 0:
                                # Aggregate values
                                if aggregation == 'sum':
                                    base_val = base_data.get('Value', base_data.get(var_name, pd.Series())).sum()
                                    mod_val = mod_data.get('Value', mod_data.get(var_name, pd.Series())).sum()
                                elif aggregation == 'mean':
                                    base_val = base_data.get('Value', base_data.get(var_name, pd.Series())).mean()
                                    mod_val = mod_data.get('Value', mod_data.get(var_name, pd.Series())).mean()
                                else:
                                    base_val = base_data.get('Value', base_data.get(var_name, pd.Series())).max()
                                    mod_val = mod_data.get('Value', mod_data.get(var_name, pd.Series())).max()
                                
                                # Store deltas
                                zone_deltas[f"{var_name}_base"] = base_val
                                zone_deltas[f"{var_name}_modified"] = mod_val
                                zone_deltas[f"{var_name}_delta"] = mod_val - base_val
                                zone_deltas[f"{var_name}_pct_change"] = ((mod_val - base_val) / base_val * 100) if base_val != 0 else 0
                                
                                var_found = True
                                break
                    
                    if not var_found:
                        self.logger.debug(f"Variable {var_name} not found for zone {zone}")
                
                delta_records.append(zone_deltas)
        
        df_deltas = pd.DataFrame(delta_records)
        self.zone_level_deltas = df_deltas
        
        return df_deltas
    
    def aggregate_zones_to_building(self, zone_deltas: pd.DataFrame) -> pd.DataFrame:
        """Aggregate zone-level deltas to building level"""
        self.logger.info("Aggregating zone deltas to building level...")
        
        building_records = []
        
        for building_id in zone_deltas['building_id'].unique():
            building_data = zone_deltas[zone_deltas['building_id'] == building_id]
            
            building_deltas = {'building_id': building_id}
            
            # Get value columns (those ending with _base, _modified, _delta, _pct_change)
            value_cols = [col for col in building_data.columns 
                         if col.endswith(('_base', '_modified', '_delta', '_pct_change'))]
            
            # Aggregate based on variable type
            for col in value_cols:
                if col.endswith('_pct_change'):
                    # Average percentage changes
                    building_deltas[col] = building_data[col].mean()
                elif 'Temperature' in col:
                    # Average temperatures (could weight by zone volume)
                    weights = self.relationship_manager.get_zone_weights(str(building_id), 'volume')
                    if weights:
                        weighted_sum = 0
                        for _, zone_row in building_data.iterrows():
                            zone_name = zone_row['zone']
                            weight = weights.get(zone_name, 1.0 / len(building_data))
                            weighted_sum += zone_row[col] * weight
                        building_deltas[col] = weighted_sum
                    else:
                        building_deltas[col] = building_data[col].mean()
                else:
                    # Sum energy values
                    building_deltas[col] = building_data[col].sum()
            
            building_records.append(building_deltas)
        
        return pd.DataFrame(building_records)
    
    def calculate_multi_level_sensitivity(self, 
                                        parameter_groups: Optional[Dict[str, List[str]]] = None,
                                        output_variables: Optional[List[str]] = None) -> pd.DataFrame:
        """Calculate sensitivity at multiple levels"""
        self.logger.info("Calculating multi-level sensitivity...")
        
        if output_variables is None:
            output_variables = ['Heating:EnergyTransfer', 'Cooling:EnergyTransfer', 'Electricity:Facility']
        
        # Clean variable names
        output_vars_clean = [var.split('[')[0].strip() for var in output_variables]
        
        # Ensure we have building-level deltas
        if not hasattr(self, 'building_level_deltas') or self.building_level_deltas is None:
            if hasattr(self, 'zone_level_deltas') and not self.zone_level_deltas.empty:
                self.building_level_deltas = self.aggregate_zones_to_building(self.zone_level_deltas)
            else:
                self.logger.error("No zone-level deltas available for aggregation")
                return pd.DataFrame()
        
        results = []
        
        # 1. Zone-to-Zone sensitivity
        self.logger.info("Calculating zone-to-zone sensitivity...")
        zone_results = self._calculate_zone_to_zone_sensitivity(parameter_groups, output_vars_clean)
        results.extend(zone_results)
        
        # 2. Zone-to-Building sensitivity
        self.logger.info("Calculating zone-to-building sensitivity...")
        zone_to_building_results = self._calculate_zone_to_building_sensitivity(parameter_groups, output_vars_clean)
        results.extend(zone_to_building_results)
        
        # 3. Equipment-to-Zone sensitivity
        self.logger.info("Calculating equipment-to-zone sensitivity...")
        equipment_results = self._calculate_equipment_to_zone_sensitivity(parameter_groups, output_vars_clean)
        results.extend(equipment_results)
        
        # 4. Building-to-Building sensitivity
        self.logger.info("Calculating building-to-building sensitivity...")
        building_results = self._calculate_building_to_building_sensitivity(parameter_groups, output_vars_clean)
        results.extend(building_results)
        
        # Convert to DataFrame
        if results:
            df_results = pd.DataFrame([vars(r) for r in results])
            df_results = df_results.sort_values('sensitivity_score', ascending=False)
            self.multi_level_results = df_results
            return df_results
        else:
            return pd.DataFrame()
    
    def _calculate_zone_to_zone_sensitivity(self, 
                                          parameter_groups: Dict[str, List[str]], 
                                          output_variables: List[str]) -> List[MultiLevelSensitivityResult]:
        """Calculate sensitivity between zone parameters and zone outputs"""
        results = []
        
        # Get zone-level modifications
        zone_mods = self.modification_tracking[self.modification_tracking['scope'] == 'zone']
        
        if zone_mods.empty or self.zone_level_deltas.empty:
            return results
        
        # Explode the affected_zones list into separate rows
        zone_mods_exploded = zone_mods.explode('affected_zones')
        # Now group by individual zones
        for (building_id, zone), zone_group in zone_mods_exploded.groupby(['building_id', 'affected_zones']):
            # Unpack affected zones (it's a list)
            if isinstance(zone, list) and zone:
                zone = zone[0]
            else:
                continue
            
            # Get zone output deltas
            zone_outputs = self.zone_level_deltas[
                (self.zone_level_deltas['building_id'] == building_id) &
                (self.zone_level_deltas['zone'] == zone)
            ]
            
            if zone_outputs.empty:
                continue
            
            # Analyze each parameter category
            for category in zone_group['category'].unique():
                cat_mods = zone_group[zone_group['category'] == category]
                
                # Calculate average parameter change
                avg_param_change = cat_mods['param_pct_change'].mean()
                
                # Check each output variable
                for output_var in output_variables:
                    delta_col = f"{output_var}_delta"
                    pct_col = f"{output_var}_pct_change"
                    
                    if delta_col in zone_outputs.columns:
                        output_delta = zone_outputs[delta_col].iloc[0]
                        output_pct = zone_outputs[pct_col].iloc[0] if pct_col in zone_outputs.columns else 0
                        
                        # Calculate correlation (simplified for single zone)
                        if abs(avg_param_change) > 0.01 and abs(output_pct) > 0.01:
                            # Simple correlation estimate
                            correlation = np.sign(avg_param_change) * np.sign(output_pct)
                            elasticity = output_pct / avg_param_change if avg_param_change != 0 else 0
                            sensitivity_score = abs(correlation) * (1 + abs(elasticity))
                            
                            result = MultiLevelSensitivityResult(
                                level='zone-to-zone',
                                source_scope='zone',
                                target_scope='zone',
                                parameter=f"{category}_zone_params",
                                category=category,
                                output_variable=output_var,
                                output_zone=zone,
                                sensitivity_score=sensitivity_score,
                                correlation=correlation,
                                p_value=0.05,  # Placeholder
                                n_samples=len(cat_mods),
                                mean_param_change=avg_param_change,
                                mean_output_change=output_pct,
                                elasticity=elasticity,
                                confidence_level='medium',
                                affected_zones=[zone]
                            )
                            results.append(result)
        
        return results
    
    def _calculate_zone_to_building_sensitivity(self,
                                            parameter_groups: Dict[str, List[str]],
                                            output_variables: List[str]) -> List[MultiLevelSensitivityResult]:
        """Calculate sensitivity between zone parameters and building outputs"""
        results = []
        
        # Get zone-level modifications
        zone_mods = self.modification_tracking[self.modification_tracking['scope'] == 'zone']
        
        if zone_mods.empty:
            return results
        
        # Ensure we have building-level deltas
        if not hasattr(self, 'building_level_deltas') or self.building_level_deltas is None:
            if hasattr(self, 'zone_level_deltas') and not self.zone_level_deltas.empty:
                self.building_level_deltas = self.aggregate_zones_to_building(self.zone_level_deltas)
            else:
                self.logger.warning("No zone-level deltas available for building aggregation")
                return results
        
        # Check if building_level_deltas is a DataFrame and has required columns
        if not isinstance(self.building_level_deltas, pd.DataFrame) or self.building_level_deltas.empty:
            self.logger.warning("Building level deltas is empty or not a DataFrame")
            return results
        
        if 'building_id' not in self.building_level_deltas.columns:
            self.logger.error("building_id column missing from building_level_deltas")
            return results
        
        # Group by building and category
        for (building_id, category), group in zone_mods.groupby(['building_id', 'category']):
            # Get building-level outputs
            building_outputs = self.building_level_deltas[
                self.building_level_deltas['building_id'] == building_id
            ]
            
            if building_outputs.empty:
                continue
            
            # Calculate aggregate parameter change
            avg_param_change = group['param_pct_change'].mean()
            affected_zones = []
            for zones in group['affected_zones']:
                if isinstance(zones, list):
                    affected_zones.extend(zones)
            affected_zones = list(set(affected_zones))
            
            # Check each output variable
            for output_var in output_variables:
                delta_col = f"{output_var}_delta"
                pct_col = f"{output_var}_pct_change"
                
                if delta_col in building_outputs.columns:
                    output_pct = building_outputs[pct_col].iloc[0] if pct_col in building_outputs.columns else 0
                    
                    if abs(avg_param_change) > 0.01 and abs(output_pct) > 0.01:
                        correlation = np.sign(avg_param_change) * np.sign(output_pct) * 0.7  # Reduce for cross-level
                        elasticity = output_pct / avg_param_change if avg_param_change != 0 else 0
                        sensitivity_score = abs(correlation) * (1 + abs(elasticity))
                        
                        result = MultiLevelSensitivityResult(
                            level='zone-to-building',
                            source_scope='zone',
                            target_scope='building',
                            parameter=f"{category}_zone_params",
                            category=category,
                            output_variable=output_var,
                            output_zone=None,
                            sensitivity_score=sensitivity_score,
                            correlation=correlation,
                            p_value=0.1,  # Higher p-value for cross-level
                            n_samples=len(group),
                            mean_param_change=avg_param_change,
                            mean_output_change=output_pct,
                            elasticity=elasticity,
                            confidence_level='medium',
                            affected_zones=affected_zones
                        )
                        results.append(result)
        
        return results
        
    def _calculate_equipment_to_zone_sensitivity(self,
                                               parameter_groups: Dict[str, List[str]],
                                               output_variables: List[str]) -> List[MultiLevelSensitivityResult]:
        """Calculate sensitivity between equipment parameters and zone outputs"""
        results = []
        
        # Get equipment-level modifications
        equip_mods = self.modification_tracking[self.modification_tracking['scope'] == 'equipment']
        
        if equip_mods.empty or self.zone_level_deltas.empty:
            return results
        
        # Group by equipment
        for _, mod in equip_mods.iterrows():
            building_id = mod['building_id']
            equipment_name = mod['object_name']
            category = mod['category']
            
            # Get affected zone
            affected_zone = self.relationship_manager.get_zone_for_equipment(
                str(building_id), equipment_name
            )
            
            if not affected_zone:
                continue
            
            # Get zone outputs
            zone_outputs = self.zone_level_deltas[
                (self.zone_level_deltas['building_id'] == building_id) &
                (self.zone_level_deltas['zone'] == affected_zone)
            ]
            
            if zone_outputs.empty:
                continue
            
            # Calculate sensitivity
            param_change = mod['param_pct_change']
            
            for output_var in output_variables:
                pct_col = f"{output_var}_pct_change"
                
                if pct_col in zone_outputs.columns:
                    output_pct = zone_outputs[pct_col].iloc[0]
                    
                    if abs(param_change) > 0.01 and abs(output_pct) > 0.01:
                        correlation = np.sign(param_change) * np.sign(output_pct) * 0.8
                        elasticity = output_pct / param_change if param_change != 0 else 0
                        sensitivity_score = abs(correlation) * (1 + abs(elasticity))
                        
                        result = MultiLevelSensitivityResult(
                            level='equipment-to-zone',
                            source_scope='equipment',
                            target_scope='zone',
                            parameter=f"{equipment_name}_{mod['field_name']}",
                            category=category,
                            output_variable=output_var,
                            output_zone=affected_zone,
                            sensitivity_score=sensitivity_score,
                            correlation=correlation,
                            p_value=0.05,
                            n_samples=1,
                            mean_param_change=param_change,
                            mean_output_change=output_pct,
                            elasticity=elasticity,
                            confidence_level='medium',
                            affected_zones=[affected_zone]
                        )
                        results.append(result)
        
        return results
    
    def _calculate_building_to_building_sensitivity(self,
                                                  parameter_groups: Dict[str, List[str]],
                                                  output_variables: List[str]) -> List[MultiLevelSensitivityResult]:
        """Calculate sensitivity between building parameters and building outputs"""
        results = []
        
        # Get building-level modifications
        building_mods = self.modification_tracking[self.modification_tracking['scope'] == 'building']
        
        if building_mods.empty:
            return results
        
        # Use aggregated building deltas
        if not hasattr(self, 'building_level_deltas'):
            self.building_level_deltas = self.aggregate_zones_to_building(self.zone_level_deltas)
        
        # Group by category
        for category in building_mods['category'].unique():
            cat_mods = building_mods[building_mods['category'] == category]
            
            # Match with building outputs
            merged_data = []
            for _, mod in cat_mods.iterrows():
                building_id = mod['building_id']
                building_output = self.building_level_deltas[
                    self.building_level_deltas['building_id'] == building_id
                ]
                
                if not building_output.empty:
                    merged_data.append({
                        'building_id': building_id,
                        'param_change': mod['param_pct_change'],
                        **building_output.iloc[0].to_dict()
                    })
            
            if len(merged_data) >= 3:  # Need at least 3 points
                df_merged = pd.DataFrame(merged_data)
                
                for output_var in output_variables:
                    pct_col = f"{output_var}_pct_change"
                    
                    if pct_col in df_merged.columns:
                        # Calculate correlation
                        corr, p_value = stats.pearsonr(
                            df_merged['param_change'],
                            df_merged[pct_col]
                        )
                        
                        # Calculate elasticity
                        mean_param = df_merged['param_change'].mean()
                        mean_output = df_merged[pct_col].mean()
                        elasticity = mean_output / mean_param if mean_param != 0 else 0
                        
                        sensitivity_score = abs(corr) * (1 + abs(elasticity))
                        
                        # Confidence based on p-value
                        if p_value < 0.01:
                            confidence = 'high'
                        elif p_value < 0.05:
                            confidence = 'medium'
                        else:
                            confidence = 'low'
                        
                        result = MultiLevelSensitivityResult(
                            level='building-to-building',
                            source_scope='building',
                            target_scope='building',
                            parameter=f"{category}_building_params",
                            category=category,
                            output_variable=output_var,
                            output_zone=None,
                            sensitivity_score=sensitivity_score,
                            correlation=corr,
                            p_value=p_value,
                            n_samples=len(df_merged),
                            mean_param_change=mean_param,
                            mean_output_change=mean_output,
                            elasticity=elasticity,
                            confidence_level=confidence,
                            affected_zones=[]  # All zones
                        )
                        results.append(result)
        
        return results
    
    def generate_multi_level_report(self, 
                                  sensitivity_df: pd.DataFrame,
                                  output_path: Path) -> Dict[str, Any]:
        """Generate comprehensive multi-level sensitivity report"""
        self.logger.info("Generating multi-level sensitivity report...")
        
        # Group results by level
        level_groups = sensitivity_df.groupby('level')
        
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'job_id': self.job_output_dir.name,
                'analysis_type': 'multi_level_modification_based',
                'n_buildings': self.modification_tracking['building_id'].nunique(),
                'n_zones_analyzed': len(self.zone_level_deltas['zone'].unique()) if not self.zone_level_deltas.empty else 0,
                'n_modifications': len(self.modification_tracking)
            },
            'summary_by_level': {},
            'top_sensitivities_by_level': {},
            'cross_level_insights': {},
            'zone_specific_insights': {},
            'detailed_results': sensitivity_df.to_dict('records')
        }
        
        # Analyze each level
        for level, level_data in level_groups:
            report['summary_by_level'][level] = {
                'n_relationships': len(level_data),
                'avg_sensitivity': level_data['sensitivity_score'].mean(),
                'max_sensitivity': level_data['sensitivity_score'].max(),
                'most_sensitive_category': level_data.loc[level_data['sensitivity_score'].idxmax(), 'category'],
                'confidence_distribution': level_data['confidence_level'].value_counts().to_dict()
            }
            
            # Top sensitivities
            report['top_sensitivities_by_level'][level] = level_data.nlargest(5, 'sensitivity_score')[
                ['parameter', 'output_variable', 'sensitivity_score', 'correlation', 'elasticity']
            ].to_dict('records')
        
        # Cross-level insights
        if 'zone-to-building' in report['summary_by_level']:
            report['cross_level_insights']['zone_impact_on_building'] = {
                'average_amplification': sensitivity_df[
                    sensitivity_df['level'] == 'zone-to-building'
                ]['elasticity'].mean(),
                'most_impactful_zones': self._get_most_impactful_zones(sensitivity_df)
            }
        
        # Zone-specific insights
        zone_data = sensitivity_df[sensitivity_df['output_zone'].notna()]
        if not zone_data.empty:
            zone_groups = zone_data.groupby('output_zone')
            for zone, zone_df in zone_groups:
                report['zone_specific_insights'][zone] = {
                    'most_sensitive_parameter': zone_df.loc[zone_df['sensitivity_score'].idxmax(), 'parameter'],
                    'avg_sensitivity': zone_df['sensitivity_score'].mean(),
                    'n_parameters': zone_df['parameter'].nunique()
                }
        
        # Save report
        report_file = output_path / 'multi_level_sensitivity_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save detailed results
        sensitivity_df.to_parquet(output_path / 'multi_level_sensitivity_detailed.parquet')
        
        # Save level summaries
        level_summary = sensitivity_df.groupby(['level', 'category']).agg({
            'sensitivity_score': ['mean', 'max', 'count'],
            'correlation': 'mean',
            'elasticity': 'mean'
        }).round(3)
        level_summary.to_csv(output_path / 'sensitivity_by_level_and_category.csv')
        
        self.logger.info(f"Multi-level report saved to: {report_file}")
        
        return report
    
    def _get_most_impactful_zones(self, sensitivity_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify zones with highest impact on building performance"""
        zone_impact = {}
        
        zone_to_building = sensitivity_df[sensitivity_df['level'] == 'zone-to-building']
        if not zone_to_building.empty:
            # Process each row to handle the list of affected zones
            for idx, row in zone_to_building.iterrows():
                zones = row['affected_zones']
                if isinstance(zones, list):
                    # Process each zone in the list
                    for zone in zones:
                        if zone not in zone_impact:
                            zone_impact[zone] = {
                                'scores': [],
                                'categories': set()
                            }
                        zone_impact[zone]['scores'].append(row['sensitivity_score'])
                        zone_impact[zone]['categories'].add(row['category'])
                elif isinstance(zones, str):
                    # Handle case where it might be a single string
                    if zones not in zone_impact:
                        zone_impact[zones] = {
                            'scores': [],
                            'categories': set()
                        }
                    zone_impact[zones]['scores'].append(row['sensitivity_score'])
                    zone_impact[zones]['categories'].add(row['category'])
        
        # Calculate average impact for each zone
        zone_impact_list = []
        for zone, data in zone_impact.items():
            zone_impact_list.append({
                'zone': zone,
                'avg_impact': np.mean(data['scores']),
                'max_impact': np.max(data['scores']),
                'n_categories': len(data['categories'])
            })
        
        # Sort by average impact
        zone_impact_list.sort(key=lambda x: x['avg_impact'], reverse=True)
        
        return zone_impact_list[:5]  # Top 5 zones
