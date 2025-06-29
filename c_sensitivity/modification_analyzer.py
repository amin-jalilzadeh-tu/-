"""
c_sensitivity/modification_analyzer.py

Consolidated modification-based sensitivity analysis with multi-level support.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
import json
from datetime import datetime

from .base_analyzer import BaseSensitivityAnalyzer
from .relationship_manager import RelationshipManager
from .statistical_methods import StatisticalMethods


@dataclass
class SensitivityResult:
    """Container for sensitivity results at any level"""
    level: str  # 'building', 'zone', 'equipment', 'cross-level'
    parameter: str
    category: str
    output_variable: str
    sensitivity_score: float
    statistical_significance: float
    confidence_interval: Tuple[float, float]
    n_samples: int
    metadata: Dict[str, Any]


class ModificationSensitivityAnalyzer(BaseSensitivityAnalyzer):
    """Analyzes sensitivity based on actual modifications with multi-level support"""
    
    def __init__(self, job_output_dir: Path, logger: Optional[logging.Logger] = None):
        super().__init__(job_output_dir, logger)
        
        # Initialize components
        self.relationship_manager = RelationshipManager(self.base_parsed_dir, self.logger)
        self.stats = StatisticalMethods()
        
        # Analysis configuration
        self.multi_level_enabled = True
        self.analysis_levels = ['building', 'zone', 'equipment']
        
        # Data containers
        self.modification_tracking = None
        self.modification_hierarchy = None
        self.zone_level_results = {}
        self.equipment_level_results = {}
        self.cross_level_results = []
        
    def get_analysis_type(self) -> str:
        return "modification"
    
    def load_modification_tracking(self, detect_scope: bool = True) -> pd.DataFrame:
        """Load modification tracking data with optional scope detection"""
        self.logger.info("Loading modification tracking data...")
        
        # Find latest modification file
        mod_files = list(self.modifications_dir.glob("modifications_detail_*.parquet"))
        if not mod_files:
            raise FileNotFoundError("No modification tracking files found")
        
        latest_file = max(mod_files, key=lambda x: x.stat().st_mtime)
        self.logger.info(f"Loading modifications from: {latest_file}")
        
        # Load and process
        df = pd.read_parquet(latest_file)
        
        # Parse numeric values
        df['original_value_numeric'] = pd.to_numeric(df['original_value'], errors='coerce')
        df['new_value_numeric'] = pd.to_numeric(df['new_value'], errors='coerce')
        df['param_delta'] = df['new_value_numeric'] - df['original_value_numeric']
        df['param_pct_change'] = (df['param_delta'] / df['original_value_numeric'].replace(0, np.nan)) * 100
        
        # Create detailed parameter key that includes ALL components
        # Handle empty field by using 'value' as default
        df['field_clean'] = df['field'].fillna('').str.strip()
        df['field_clean'] = df['field_clean'].replace('', 'value')
        
        # Create the full parameter key with all components
        df['param_key'] = (
            df['category'].astype(str) + '*' + 
            df['object_type'].astype(str) + '*' + 
            df['object_name'].astype(str) + '*' + 
            df['field_clean']
        )
        
        # Also create a short parameter name for display
        df['param_display_name'] = (
            df['category'].astype(str) + '_' + 
            df['object_name'].astype(str) + '_' + 
            df['field_clean']
        )
        
        # Detect scope if requested
        if detect_scope and self.multi_level_enabled:
            df = self._add_modification_scope(df)
        
        self.modification_tracking = df
        
        # Log unique parameters
        unique_params = df['param_key'].nunique()
        self.logger.info(f"Loaded {len(df)} modifications across {df['building_id'].nunique()} buildings")
        self.logger.info(f"Found {unique_params} unique parameters")
        
        # Debug: show some example parameter keys
        self.logger.debug("Example parameter keys:")
        for pk in df['param_key'].head(5):
            self.logger.debug(f"  {pk}")
        
        return df
    
    def _add_modification_scope(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add scope detection to modifications"""
        scopes = []
        affected_zones = []
        
        for _, row in df.iterrows():
            scope, zones = self.relationship_manager.detect_modification_scope(
                row['object_name'],
                row['object_type'],
                str(row['building_id'])
            )
            scopes.append(scope)
            affected_zones.append(zones)
        
        df['scope'] = scopes
        df['affected_zones'] = affected_zones
        
        # Create hierarchical view
        self.modification_hierarchy = self.relationship_manager.create_modification_hierarchy(df)
        
        # Log statistics
        scope_counts = df['scope'].value_counts()
        self.logger.info(f"Modification scopes: {scope_counts.to_dict()}")
        
        return df
    
    def calculate_sensitivity(self,
                            output_variables: Optional[List[str]] = None,
                            analysis_levels: Optional[List[str]] = None,
                            parameter_groups: Optional[Dict[str, List[str]]] = None,
                            aggregation: str = 'sum',
                            method: str = 'elasticity',
                            **kwargs) -> pd.DataFrame:
        """
        Calculate modification-based sensitivity at multiple levels
        
        Args:
            output_variables: Output variables to analyze
            analysis_levels: Levels to analyze ['building', 'zone', 'equipment']
            parameter_groups: Parameter grouping for analysis
            aggregation: How to aggregate outputs ('sum', 'mean')
            method: Analysis method ('elasticity', 'correlation', 'regression')
            **kwargs: Additional method-specific parameters
            
        Returns:
            DataFrame with multi-level sensitivity results
        """
        self.logger.info(f"Calculating modification sensitivity using {method} method...")
        
        if output_variables is None:
            output_variables = [
                "Heating:EnergyTransfer",
                "Cooling:EnergyTransfer",
                "Electricity:Facility"
            ]
        
        if analysis_levels is None:
            analysis_levels = self.analysis_levels if self.multi_level_enabled else ['building']
        
        # Ensure data is loaded
        if self.modification_tracking is None:
            self.load_modification_tracking(detect_scope=self.multi_level_enabled)
        
        if not self.base_results:
            self.load_simulation_results()
        
        # Calculate deltas at requested levels
        all_results = []
        
        if 'building' in analysis_levels:
            building_results = self._calculate_building_level_sensitivity(
                output_variables, aggregation, method, parameter_groups
            )
            all_results.extend(building_results)
        
        if 'zone' in analysis_levels and self.multi_level_enabled:
            zone_results = self._calculate_zone_level_sensitivity(
                output_variables, aggregation, method, parameter_groups
            )
            if zone_results:  # Check if not None
                all_results.extend(zone_results)
        
        if 'equipment' in analysis_levels and self.multi_level_enabled:
            equipment_results = self._calculate_equipment_level_sensitivity(
                output_variables, aggregation, method, parameter_groups
            )
            if equipment_results:  # Check if not None
                all_results.extend(equipment_results)
        
        # Calculate cross-level interactions if requested
        if kwargs.get('calculate_interactions', False) and len(analysis_levels) > 1:
            interaction_results = self._calculate_cross_level_interactions(
                output_variables, method
            )
            if interaction_results:  # Check if not None
                all_results.extend(interaction_results)
        
        # Convert to DataFrame
        results_df = self._results_to_dataframe(all_results)
        
        # Apply statistical significance testing
        if kwargs.get('test_significance', True):
            results_df = self._add_statistical_significance(results_df)
        
        # Weight by validation if requested
        if kwargs.get('weight_by_validation', False):
            results_df = self.weight_by_validation(results_df)
        
        return results_df
    
    def _calculate_building_level_sensitivity(self,
                                            output_variables: List[str],
                                            aggregation: str,
                                            method: str,
                                            parameter_groups: Optional[Dict[str, List[str]]]) -> List[SensitivityResult]:
        """Calculate sensitivity at building level"""
        self.logger.info("Calculating building-level sensitivity...")
        
        # Calculate output deltas
        output_deltas = self.calculate_output_deltas(output_variables, aggregation)
        
        if output_deltas.empty:
            return []
        
        # Calculate parameter aggregates
        param_aggregates = self._calculate_parameter_aggregates()
        
        # Apply analysis method
        if method == 'elasticity':
            results = self._elasticity_analysis(param_aggregates, output_deltas, 'building')
        elif method == 'correlation':
            results = self._correlation_analysis(param_aggregates, output_deltas, 'building')
        elif method == 'regression':
            results = self._regression_analysis(param_aggregates, output_deltas, 'building')
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return results
    
    def _calculate_zone_level_sensitivity(self,
                                        output_variables: List[str],
                                        aggregation: str,
                                        method: str,
                                        parameter_groups: Optional[Dict[str, List[str]]]) -> List[SensitivityResult]:
        """Calculate sensitivity at zone level"""
        self.logger.info("Calculating zone-level sensitivity...")
        
        # Load zone-level results
        if not self.zone_level_results:
            self._load_zone_level_results()
        
        results = []
        
        # Get zone-level modifications
        zone_mods = self.modification_tracking[
            self.modification_tracking['scope'].isin(['zone', 'equipment'])
        ]
        
        if zone_mods.empty:
            return results
        
        # Calculate zone deltas
        zone_deltas = self._calculate_zone_deltas(output_variables, aggregation)
        
        # Debug logging
        self.logger.debug(f"Zone deltas shape: {zone_deltas.shape if not zone_deltas.empty else 'empty'}")
        self.logger.debug(f"Zone deltas columns: {zone_deltas.columns.tolist() if not zone_deltas.empty else 'no columns'}")
        
        # Check if zone_deltas is empty or missing required columns
        if zone_deltas.empty:
            self.logger.warning("No zone deltas calculated - skipping zone-level sensitivity")
            return results
        
        if 'building_id' not in zone_deltas.columns:
            self.logger.warning("Zone deltas missing 'building_id' column - attempting to add from modifications")
            # Try to infer building_id from zone names if possible
            if 'zone' in zone_deltas.columns:
                # Create a mapping of zones to building_ids from modifications
                zone_to_building = {}
                for _, mod in self.modification_tracking.iterrows():
                    if 'affected_zones' in mod and isinstance(mod['affected_zones'], list):
                        for zone in mod['affected_zones']:
                            zone_to_building[zone] = mod['building_id']
                
                # Apply mapping
                zone_deltas['building_id'] = zone_deltas['zone'].map(zone_to_building)
                
                # Remove rows where we couldn't map building_id
                zone_deltas = zone_deltas.dropna(subset=['building_id'])
                
                if zone_deltas.empty:
                    self.logger.warning("Could not map building_ids to zones - skipping zone-level sensitivity")
                    return results
        
        # Process modifications for each zone
        # First, expand the affected_zones lists into individual rows
        expanded_mods = []
        for _, row in zone_mods.iterrows():
            affected_zones = row['affected_zones']
            if isinstance(affected_zones, list):
                for zone_name in affected_zones:
                    mod_row = row.copy()
                    mod_row['zone_name'] = zone_name
                    expanded_mods.append(mod_row)
            else:
                # Handle single zone case
                mod_row = row.copy()
                mod_row['zone_name'] = affected_zones
                expanded_mods.append(mod_row)
        
        if not expanded_mods:
            return results
        
        # Convert back to DataFrame
        # Convert back to DataFrame
        expanded_df = pd.DataFrame(expanded_mods)

        # Debug: Log what zones we're looking for
        self.logger.debug(f"Expanded modifications for {len(expanded_df)} zone modifications")
        if not expanded_df.empty:
            unique_zones_in_mods = expanded_df['zone_name'].unique()
            self.logger.debug(f"Unique zones in modifications: {unique_zones_in_mods.tolist()}")
            
            # Also log what zones we have in deltas
            if 'zone' in zone_deltas.columns:
                unique_zones_in_deltas = zone_deltas['zone'].unique()
                self.logger.debug(f"Unique zones in deltas: {unique_zones_in_deltas.tolist()}")
                
                # Check for mismatches
                zones_in_mods_not_in_deltas = set(unique_zones_in_mods) - set(unique_zones_in_deltas)
                if zones_in_mods_not_in_deltas:
                    self.logger.warning(f"Zones in modifications but not in deltas: {zones_in_mods_not_in_deltas}")









        
        # Group modifications by building and zone
        for (building_id, zone_name), group in expanded_df.groupby(['building_id', 'zone_name']):
            # Get zone-specific output changes
            try:
                zone_outputs = zone_deltas[
                    (zone_deltas['building_id'] == building_id) & 
                    (zone_deltas['zone'] == zone_name)
                ]
            except KeyError as e:
                self.logger.warning(f"Failed to filter zone deltas for building {building_id}, zone {zone_name}: {e}")
                continue
            
            if zone_outputs.empty:
                self.logger.debug(f"No zone outputs found for building {building_id}, zone {zone_name}")
                continue
            
            # Calculate sensitivity for this zone
            zone_params = self._aggregate_zone_parameters(group)
            
            if zone_params.empty:
                self.logger.debug(f"No zone parameters aggregated for building {building_id}, zone {zone_name}")
                continue
            
            # Apply analysis method
            try:
                if method == 'elasticity':
                    zone_results = self._elasticity_analysis(zone_params, zone_outputs, 'zone')
                elif method == 'correlation':
                    zone_results = self._correlation_analysis(zone_params, zone_outputs, 'zone')
                elif method == 'regression':
                    zone_results = self._regression_analysis(zone_params, zone_outputs, 'zone')
                else:
                    self.logger.warning(f"Unknown method: {method}, defaulting to elasticity")
                    zone_results = self._elasticity_analysis(zone_params, zone_outputs, 'zone')
                
                # Add zone metadata to results
                for result in zone_results:
                    if hasattr(result, 'metadata'):
                        result.metadata['zone_name'] = zone_name
                        result.metadata['building_id'] = building_id
                
                results.extend(zone_results)
                
            except Exception as e:
                self.logger.warning(f"Failed to calculate sensitivity for zone {zone_name} in building {building_id}: {e}")
                continue
        
        self.logger.info(f"Calculated {len(results)} zone-level sensitivity results")
        
        # IMPORTANT: Always return a list, even if empty
        return results
    
    def _calculate_equipment_level_sensitivity(self,
                                             output_variables: List[str],
                                             aggregation: str,
                                             method: str,
                                             parameter_groups: Optional[Dict[str, List[str]]]) -> List[SensitivityResult]:
        """Calculate sensitivity at equipment level"""
        self.logger.info("Calculating equipment-level sensitivity...")
        
        results = []
        
        # Get equipment-level modifications
        equip_mods = self.modification_tracking[
            self.modification_tracking['scope'] == 'equipment'
        ]
        
        if equip_mods.empty:
            return results
        
        # Group by equipment
        for (building_id, equipment_name), group in equip_mods.groupby(['building_id', 'object_name']):
            # Get affected zone
            zone = self.relationship_manager.get_zone_for_equipment(
                str(building_id), equipment_name
            )
            
            if not zone:
                continue
            
            # Get zone outputs
            zone_outputs = self._get_zone_outputs(building_id, zone, output_variables)
            
            if zone_outputs.empty:
                continue
            
            # Calculate sensitivity
            equip_params = self._aggregate_equipment_parameters(group)
            
            if method == 'elasticity':
                equip_results = self._elasticity_analysis(equip_params, zone_outputs, 'equipment')
            else:
                equip_results = self._correlation_analysis(equip_params, zone_outputs, 'equipment')
            
            # Add equipment metadata
            for result in equip_results:
                result.metadata['equipment_name'] = equipment_name
                result.metadata['affected_zone'] = zone
            
            results.extend(equip_results)
        
        return results
    
    def _calculate_cross_level_interactions(self,
                                        output_variables: List[str],
                                        method: str) -> List[SensitivityResult]:
        """Calculate interactions between different levels"""
        self.logger.info("Calculating cross-level interactions...")
        
        results = []
        
        # Zone parameters → Building outputs
        zone_to_building = self._analyze_zone_to_building_effects(output_variables, method)
        results.extend(zone_to_building)
        
        # Equipment parameters → Zone outputs
        equip_to_zone = self._analyze_equipment_to_zone_effects(output_variables, method)
        results.extend(equip_to_zone)
        
        return results

    # Fix for c_sensitivity/modification_analyzer.py
    # Replace the _analyze_zone_to_building_effects method starting around line 455

    # Bulletproof replacement for _analyze_zone_to_building_effects

    def _analyze_zone_to_building_effects(self,
                                        output_variables: List[str],
                                        method: str) -> List[SensitivityResult]:
        """Analyze how zone-level modifications affect building-level outputs"""
        results = []
        
        # Get zone-level modifications
        zone_mods = self.modification_tracking[
            self.modification_tracking['scope'] == 'zone'
        ]
        
        if zone_mods.empty:
            return results
        
        # Get building-level output deltas
        if self.output_deltas is None or self.output_deltas.empty:
            return results
        
        # Aggregate zone modifications by building
        building_zone_stats = {}
        for building_id in zone_mods['building_id'].unique():
            building_zone_mods = zone_mods[zone_mods['building_id'] == building_id]
            building_zone_stats[str(building_id)] = {
                'param_delta_mean': building_zone_mods['param_delta'].mean(),
                'param_delta_std': building_zone_mods['param_delta'].std(),
                'param_delta_count': len(building_zone_mods),
                'param_pct_change_mean': building_zone_mods['param_pct_change'].mean(),
                'param_pct_change_std': building_zone_mods['param_pct_change'].std()
            }
        
        # Group output deltas by building
        building_outputs = {}
        for idx, row in self.output_deltas.iterrows():
            building_id_str = str(row['building_id'])
            if building_id_str not in building_outputs:
                building_outputs[building_id_str] = []
            building_outputs[building_id_str].append(row)
        
        # Analyze each building
        for building_id_str, stats in building_zone_stats.items():
            if building_id_str not in building_outputs:
                continue
            
            # Convert list of rows back to DataFrame for this building
            building_output_df = pd.DataFrame(building_outputs[building_id_str])
            
            param_change = stats['param_pct_change_mean']
            n_samples = stats['param_delta_count']
            
            if param_change == 0 or pd.isna(param_change):
                continue
            
            # Create sensitivity results for cross-level effects
            for output_var in output_variables:
                # Find columns containing this output variable's delta
                output_cols = [
                    col for col in building_output_df.columns 
                    if output_var in col and '_delta' in col
                ]
                
                for col in output_cols:
                    # Calculate average output change
                    output_change = building_output_df[col].mean()
                    
                    if pd.isna(output_change):
                        continue
                    
                    # Calculate sensitivity score (elasticity)
                    if output_change != 0:
                        sensitivity = abs(output_change / param_change)
                    else:
                        sensitivity = 0
                    
                    # Create result
                    result = SensitivityResult(
                        level='cross-level',
                        parameter='zone_modifications_aggregate',
                        category='zone',
                        output_variable=output_var,
                        sensitivity_score=min(sensitivity, 1.0),  # Cap at 1.0
                        statistical_significance=0.05,  # Placeholder
                        confidence_interval=(0, 0),
                        n_samples=n_samples,
                        metadata={
                            'interaction_type': 'zone_to_building',
                            'building_id': building_id_str,
                            'avg_zone_param_change': float(param_change),
                            'avg_output_change': float(output_change) if not pd.isna(output_change) else 0
                        }
                    )
                    results.append(result)
        
        return results

    def _analyze_equipment_to_zone_effects(self,
                                        output_variables: List[str],
                                        method: str) -> List[SensitivityResult]:
        """Analyze how equipment-level modifications affect zone-level outputs"""
        results = []
        
        # Get equipment-level modifications
        equip_mods = self.modification_tracking[
            self.modification_tracking['scope'] == 'equipment'
        ]
        
        if equip_mods.empty or not self.zone_level_results:
            return results
        
        # Group by equipment and analyze effects on assigned zones
        for (building_id, equip_name), group in equip_mods.groupby(['building_id', 'object_name']):
            # Get affected zone
            zone = self.relationship_manager.get_zone_for_equipment(
                str(building_id), equip_name
            )
            
            if not zone:
                continue
            
            # Analyze impact on zone outputs
            # This is a simplified implementation
            avg_param_change = group['param_pct_change'].mean()
            
            if avg_param_change != 0:
                # Create cross-level sensitivity result
                result = SensitivityResult(
                    level='cross-level',
                    parameter=f'equipment_{equip_name}',
                    category='equipment',
                    output_variable='zone_outputs_aggregate',
                    sensitivity_score=0.5,  # Placeholder
                    statistical_significance=0.1,
                    confidence_interval=(0, 0),
                    n_samples=len(group),
                    metadata={
                        'interaction_type': 'equipment_to_zone',
                        'equipment_name': equip_name,
                        'affected_zone': zone,
                        'building_id': building_id
                    }
                )
                results.append(result)
        
        return results
    
    def _elasticity_analysis(self,
                            param_data: pd.DataFrame,
                            output_data: pd.DataFrame,
                            level: str) -> List[SensitivityResult]:
        """Calculate elasticity-based sensitivity with better column matching"""
        results = []
        
        # Debug logging
        self.logger.debug(f"[ELASTICITY] Starting {level} elasticity analysis")
        self.logger.debug(f"[ELASTICITY] param_data shape: {param_data.shape}")
        self.logger.debug(f"[ELASTICITY] output_data shape: {output_data.shape}")
        self.logger.debug(f"[ELASTICITY] param_data columns: {list(param_data.columns)}")
        self.logger.debug(f"[ELASTICITY] output_data columns: {list(output_data.columns)}")
        
        if param_data.empty or output_data.empty:
            self.logger.debug(f"[ELASTICITY] Empty data for {level} elasticity analysis")
            return results
        
        # For building-level analysis with aggregated parameters
        if level == 'building' and 'param_key' in param_data.columns:
            # Group by param_key to get unique parameters
            unique_params = param_data['param_key'].unique()
            self.logger.debug(f"[ELASTICITY] Found {len(unique_params)} unique parameters")
            
            for param_key in unique_params:
                # Get data for this specific parameter
                param_rows = param_data[param_data['param_key'] == param_key]
                
                if param_rows.empty:
                    continue
                    
                # Parse parameter components
                param_parts = self._parse_parameter_name(param_key)
                category = param_parts['category']
                
                # Get change values for this parameter
                if 'param_pct_change_mean' in param_rows.columns:
                    param_pct_change = param_rows.groupby('building_id')['param_pct_change_mean'].first()
                elif 'param_pct_change' in param_rows.columns:
                    param_pct_change = param_rows.groupby('building_id')['param_pct_change'].mean()
                else:
                    self.logger.debug(f"[ELASTICITY] No percentage change data for {param_key}")
                    continue
                
                # Process each output variable
                for output_col in output_data.columns:
                    if '_delta' not in output_col and '_pct_change' not in output_col:
                        continue
                        
                    # Extract output variable name
                    output_var = output_col.replace('_delta', '').replace('_pct_change', '')
                    
                    # Only use percentage change columns for elasticity
                    if '_pct_change' in output_col:
                        # Align data by building_id
                        for building_id in param_pct_change.index:
                            if building_id in output_data['building_id'].values:
                                # Get output change for this building
                                output_rows = output_data[output_data['building_id'] == building_id]
                                if output_rows.empty or output_col not in output_rows.columns:
                                    continue
                                    
                                output_pct_change = output_rows[output_col].iloc[0]
                                param_change = param_pct_change[building_id]
                                
                                # Skip if no change in parameter
                                if abs(param_change) < 0.001:
                                    continue
                                
                                # Calculate elasticity
                                elasticity = output_pct_change / param_change if param_change != 0 else 0
                                
                                # Create result
                                result = SensitivityResult(
                                    level=level,
                                    parameter=param_key,
                                    category=category,
                                    output_variable=output_var,
                                    sensitivity_score=min(abs(elasticity), 10.0),  # Cap at 10
                                    statistical_significance=0.05,  # Placeholder
                                    confidence_interval=(0, 0),
                                    n_samples=1,
                                    metadata={
                                        'elasticity': float(elasticity),
                                        'param_change': float(param_change),
                                        'output_change': float(output_pct_change),
                                        'building_id': str(building_id),
                                        'object_type': param_parts['object_type'],
                                        'object_name': param_parts['object_name'],
                                        'field_name': param_parts['field_name']
                                    }
                                )
                                results.append(result)
                                self.logger.debug(f"[ELASTICITY] Added result: {param_key} -> {output_var}, elasticity={elasticity:.4f}")
        
        else:
            # Original logic for other levels (zone, equipment)
            # Get parameter columns
            param_cols = [col for col in param_data.columns if '_delta' in col or '_pct_change' in col]
            output_cols = [col for col in output_data.columns if '_delta' in col or '_pct_change' in col]
            
            if not param_cols or not output_cols:
                self.logger.debug(f"No valid columns for {level} elasticity analysis")
                return results
            
            # Ensure both dataframes have the same index
            if len(param_data) != len(output_data):
                self.logger.debug(f"Index mismatch in {level} elasticity analysis: param_data has {len(param_data)} rows, output_data has {len(output_data)} rows")
                # Try to align by taking the first row of each
                if len(param_data) > 0 and len(output_data) > 0:
                    param_data = param_data.iloc[[0]]
                    output_data = output_data.iloc[[0]]
                else:
                    return results
            
            for param_col in param_cols:
                param_name = param_col.replace('_delta', '').replace('_pct_change', '')
                
                for output_col in output_cols:
                    output_name = output_col.replace('_delta', '').replace('_pct_change', '')
                    
                    try:
                        # Get the values
                        param_values = param_data[param_col].values
                        output_values = output_data[output_col].values
                        
                        # Skip if all zeros or NaN
                        if np.all(np.isnan(param_values)) or np.all(param_values == 0):
                            continue
                        if np.all(np.isnan(output_values)) or np.all(output_values == 0):
                            continue
                        
                        # Calculate elasticity
                        elasticity, stats_info = self.stats.calculate_elasticity(
                            pd.Series(param_values),
                            pd.Series(output_values)
                        )
                        
                        if elasticity is not None and not np.isnan(elasticity):
                            result = SensitivityResult(
                                level=level,
                                parameter=param_name,
                                category=self._get_parameter_category(param_name),
                                output_variable=output_name,
                                sensitivity_score=abs(elasticity),
                                statistical_significance=stats_info.get('p_value', 1.0),
                                confidence_interval=stats_info.get('confidence_interval', (0, 0)),
                                n_samples=len(param_values),
                                metadata={
                                    'elasticity': float(elasticity),
                                    'r_squared': stats_info.get('r_squared', 0)
                                }
                            )
                            results.append(result)
                            self.logger.debug(f"Calculated {level} elasticity for {param_name} -> {output_name}: {elasticity}")
                            
                    except Exception as e:
                        self.logger.debug(f"Error calculating elasticity for {param_name} -> {output_name}: {e}")
                        continue
        
        self.logger.info(f"[ELASTICITY] Calculated {len(results)} elasticity results for {level} level")
        return results
    
    def _correlation_analysis(self,
                            param_data: pd.DataFrame,
                            output_data: pd.DataFrame,
                            level: str) -> List[SensitivityResult]:
        """Calculate correlation-based sensitivity"""
        # Merge data for correlation
        merged_data = pd.merge(param_data, output_data, on='building_id', how='inner')
        
        # Get columns
        param_cols = [col for col in param_data.columns if col != 'building_id']
        output_cols = [col for col in output_data.columns if col != 'building_id' and '_delta' in col]
        
        # Calculate correlations
        results = []
        for param_col in param_cols:
            for output_col in output_cols:
                if param_col in merged_data.columns and output_col in merged_data.columns:
                    corr_result = self.stats.calculate_correlation(
                        merged_data[param_col],
                        merged_data[output_col]
                    )
                    
                    if corr_result['correlation'] is not None:
                        result = SensitivityResult(
                            level=level,
                            parameter=param_col,
                            category=self._get_parameter_category(param_col),
                            output_variable=output_col.replace('_delta', ''),
                            sensitivity_score=abs(corr_result['correlation']),
                            statistical_significance=corr_result['p_value'],
                            confidence_interval=corr_result['confidence_interval'],
                            n_samples=corr_result['n_samples'],
                            metadata={'correlation': corr_result['correlation']}
                        )
                        results.append(result)
        
        return results
    
    # Also fix _calculate_parameter_aggregates to ensure proper aggregation
    def _calculate_parameter_aggregates(self) -> pd.DataFrame:
        """Aggregate parameter changes by building while preserving parameter details"""
        if self.modification_tracking is None:
            return pd.DataFrame()
        
        # First, ensure we have the delta and pct_change columns calculated
        mod_df = self.modification_tracking.copy()
        
        # Filter out rows with invalid changes
        mod_df = mod_df[mod_df['param_pct_change'].notna() & (mod_df['param_pct_change'] != 0)]
        
        if mod_df.empty:
            self.logger.warning("No valid parameter changes found after filtering")
            return pd.DataFrame()
        
        # Group by building_id AND param_key to preserve parameter specificity
        agg_df = mod_df.groupby(
            ['building_id', 'param_key', 'category', 'object_type', 'object_name', 'field_clean']
        ).agg({
            'param_delta': ['mean', 'std', 'count'],
            'param_pct_change': ['mean', 'std'],
            'original_value_numeric': 'first',
            'new_value_numeric': 'first'
        }).reset_index()
        
        # Flatten column names
        agg_df.columns = [
            col[0] if col[1] == '' else f"{col[0]}_{col[1]}" 
            for col in agg_df.columns
        ]
        
        # Debug logging
        self.logger.info(f"[PARAM_AGG] Aggregated to {len(agg_df)} unique parameter-building combinations")
        self.logger.info(f"[PARAM_AGG] Unique parameters: {agg_df['param_key'].nunique()}")
        self.logger.info(f"[PARAM_AGG] Parameter categories: {agg_df['category'].unique()}")
        
        # Show some example parameters
        if len(agg_df) > 0:
            self.logger.debug("[PARAM_AGG] Example parameters:")
            for idx, row in agg_df.head(5).iterrows():
                self.logger.debug(f"  - {row['param_key']}: {row['param_pct_change_mean']:.2f}% change")
        
        return agg_df
    
    def _aggregate_zone_parameters(self, zone_mods: pd.DataFrame) -> pd.DataFrame:
        """Aggregate parameters for a specific zone"""
        if zone_mods.empty:
            return pd.DataFrame()
        
        # Preserve full parameter specificity
        agg_df = zone_mods.groupby(
            ['category', 'param_key', 'object_type', 'object_name', 'field_clean']
        ).agg({
            'param_delta': ['mean', 'std', 'count'],
            'param_pct_change': ['mean', 'std'],
            'original_value_numeric': 'first',
            'new_value_numeric': 'first'
        }).reset_index()
        
        # Flatten column names
        agg_df.columns = [
            col[0] if col[1] == '' else f"{col[0]}_{col[1]}" 
            for col in agg_df.columns
        ]
        
        return agg_df
    

    # PATCH FOR modification_analyzer.py
    # Add this method after _aggregate_zone_parameters (around line 780)

    def _aggregate_building_parameters_for_zone(self, building_mods: pd.DataFrame) -> pd.DataFrame:
        """Aggregate all building modifications for zone-level analysis"""
        if building_mods.empty:
            return pd.DataFrame()
        
        # Ensure we have the necessary columns
        if 'param_key' not in building_mods.columns:
            self.logger.warning("param_key column missing in building_mods")
            return pd.DataFrame()
        
        # Filter out rows with NaN values in key columns
        building_mods = building_mods.dropna(subset=['param_delta', 'param_pct_change'])
        
        if building_mods.empty:
            return pd.DataFrame()
        
        # Group by specific parameter key (not just category)
        agg_data = building_mods.groupby(['param_key', 'field_clean']).agg({
            'param_delta': 'mean',
            'param_pct_change': 'mean'
        }).reset_index()
        
        # Create a single-row DataFrame with all parameters as columns
        result = pd.DataFrame(index=[0])  # Single row with index 0
        
        for _, row in agg_data.iterrows():
            param_key = row['param_key']
            # Use the full parameter key for column names
            result[f"{param_key}_delta"] = row['param_delta']
            result[f"{param_key}_pct_change"] = row['param_pct_change']
        
        return result

    # REPLACE the entire _calculate_zone_level_sensitivity method (starting around line 190)
    # Fix for zone-level analysis in modification_analyzer.py
    # This replaces the _calculate_zone_level_sensitivity method

    def _calculate_zone_level_sensitivity(self,
                                        output_variables: List[str],
                                        aggregation: str,
                                        method: str,
                                        parameter_groups: Optional[Dict[str, List[str]]]) -> List[SensitivityResult]:
        """Calculate sensitivity at zone level - Fixed version"""
        self.logger.info("[ZONE] Calculating zone-level sensitivity...")
        
        # Load zone-level results
        if not self.zone_level_results:
            self._load_zone_level_results()
        
        results = []
        
        # Calculate zone deltas
        zone_deltas = self._calculate_zone_deltas(output_variables, aggregation)
        
        if zone_deltas.empty:
            self.logger.warning("[ZONE] No zone deltas calculated - skipping zone-level sensitivity")
            return results
        
        # Get all modifications (not just zone-scoped ones)
        # This is key - we analyze ALL modifications at zone level
        all_mods = self.modification_tracking
        
        if all_mods.empty:
            self.logger.warning("[ZONE] No modifications found")
            return results
        
        # Get unique zones from zone_deltas
        unique_zones = zone_deltas[['building_id', 'zone']].drop_duplicates()
        self.logger.info(f"[ZONE] Found {len(unique_zones)} unique zones with deltas")
        
        # Process each zone
        analyzed_zones = 0
        for _, zone_info in unique_zones.iterrows():
            building_id = zone_info['building_id']
            zone_name = zone_info['zone']
            
            # Skip non-zone entities
            if any(skip in zone_name.upper() for skip in ['WATERHEATER', 'PLANT', 'SYSTEM']):
                continue
            
            # Get all modifications for this building (not just zone-specific)
            building_mods = all_mods[all_mods['building_id'] == building_id]
            
            if building_mods.empty:
                self.logger.debug(f"[ZONE] No modifications found for building {building_id}")
                continue
            
            # Get zone-specific output changes
            zone_outputs = zone_deltas[
                (zone_deltas['building_id'] == building_id) & 
                (zone_deltas['zone'] == zone_name)
            ]
            
            if zone_outputs.empty:
                continue
            
            # Aggregate parameters for this building
            param_agg = building_mods.groupby(['param_key', 'category']).agg({
                'param_pct_change': 'mean',
                'param_delta': 'mean',
                'object_type': 'first',
                'object_name': 'first',
                'field_clean': 'first'
            }).reset_index()
            
            # Filter out parameters with no change
            param_agg = param_agg[param_agg['param_pct_change'].abs() > 0.001]
            
            if param_agg.empty:
                self.logger.debug(f"[ZONE] No parameter changes for building {building_id}")
                continue
            
            # Analyze each parameter against zone outputs
            for _, param_row in param_agg.iterrows():
                param_key = param_row['param_key']
                param_change = param_row['param_pct_change']
                
                # Process each output variable
                for var in output_variables:
                    var_clean = var.split('[')[0].strip()
                    
                    # Look for percentage change columns
                    pct_col = f'{var_clean}_pct_change'
                    if pct_col in zone_outputs.columns:
                        output_change = zone_outputs[pct_col].iloc[0]
                        
                        # Skip if no output change
                        if abs(output_change) < 0.001:
                            continue
                        
                        # Calculate elasticity
                        elasticity = output_change / param_change if param_change != 0 else 0
                        
                        # Create sensitivity result
                        result = SensitivityResult(
                            level='zone',
                            parameter=param_key,
                            category=param_row['category'],
                            output_variable=var_clean,
                            sensitivity_score=min(abs(elasticity), 10.0),  # Cap at 10
                            statistical_significance=0.05,
                            confidence_interval=(0, 0),
                            n_samples=1,
                            metadata={
                                'zone_name': zone_name,
                                'building_id': str(building_id),
                                'elasticity': float(elasticity),
                                'param_change': float(param_change),
                                'output_change': float(output_change),
                                'object_type': param_row['object_type'],
                                'object_name': param_row['object_name'],
                                'field_name': param_row['field_clean']
                            }
                        )
                        results.append(result)
                        analyzed_zones += 1
        
        self.logger.info(f"[ZONE] Calculated {len(results)} zone-level sensitivity results from {analyzed_zones} zone analyses")
        
        return results

    # UPDATE the _calculate_output_deltas method to handle missing data better (around line 140)
    def calculate_output_deltas(self, 
                            output_variables: List[str],
                            aggregation: str = 'sum',
                            groupby: Optional[List[str]] = None) -> pd.DataFrame:
        """Calculate changes in outputs between base and modified runs using comparison files"""
        self.logger.info("Calculating output deltas...")
        
        # Use new comparison file format
        comparison_deltas = self._calculate_deltas_from_comparison_files(
            output_variables, 
            frequency=self.config.get('result_frequency', 'daily')
        )
        
        if comparison_deltas.empty:
            self.logger.warning("No comparison data found. Make sure comparison files are available.")
            
        return comparison_deltas







    
    def _aggregate_equipment_parameters(self, equip_mods: pd.DataFrame) -> pd.DataFrame:
        """Aggregate parameters for specific equipment"""
        return equip_mods.groupby(['category', 'param_key']).agg({
            'param_delta': ['mean', 'std', 'count'],
            'param_pct_change': ['mean', 'std']
        }).reset_index()
    
    def _load_zone_level_results(self):
        """Load zone-level simulation results from new format"""
        self.logger.info("Loading zone-level simulation results...")
        
        # Load from new format - zones are included in base data
        base_path = self.base_parsed_dir / "timeseries" / "base_all_daily.parquet"
        if base_path.exists():
            try:
                base_df = pd.read_parquet(base_path)
                # Filter for zone data
                zone_df = base_df[base_df['Zone'].notna() & (base_df['Zone'] != '')]
                
                # Group by category
                for category in zone_df['category'].unique():
                    cat_df = zone_df[zone_df['category'] == category]
                    self.zone_level_results[f"{category}_base"] = cat_df
                
                self.logger.info(f"Loaded zone data for {len(zone_df['Zone'].unique())} zones")
            except Exception as e:
                self.logger.error(f"Failed to load zone data: {e}")
        
        # Load comparison data for zones
        comparison_path = self.modified_parsed_dir / "comparisons"
        if comparison_path.exists():
            # Zone data is included in comparison files
            self.logger.info("Zone-level modified results available in comparison files")
    
    def _calculate_zone_deltas(self, 
                            output_variables: List[str],
                            aggregation: str) -> pd.DataFrame:
        """Calculate output changes at zone level using comparison files"""
        zone_deltas = []
        
        # Use comparison files for zone-level deltas
        comparison_path = self.modified_parsed_dir / "comparisons"
        if not comparison_path.exists():
            self.logger.warning("No comparison files found for zone delta calculation")
            return pd.DataFrame()
        
        # Process comparison files to get zone-level deltas
        for var in output_variables:
            var_clean = var.split('[')[0].strip().lower()
            
            # Find comparison files for this variable
            pattern = f"var_*{var_clean}*_daily_*.parquet"
            var_files = list(comparison_path.glob(pattern))
            
            for file_path in var_files:
                try:
                    df = pd.read_parquet(file_path)
                    
                    # Only process if zone data is available
                    if 'Zone' not in df.columns or df['Zone'].isna().all():
                        continue
                    
                    # Get variant columns
                    variant_cols = [col for col in df.columns if col.startswith('variant_') and col.endswith('_value')]
                    
                    # Group by building and zone
                    for (building_id, zone), zone_group in df.groupby(['building_id', 'Zone']):
                        if pd.isna(zone) or zone == '' or 'WATERHEATER' in str(zone).upper():
                            continue
                        
                        base_sum = zone_group['base_value'].sum()
                        
                        # Average across variants
                        variant_sums = []
                        for var_col in variant_cols:
                            variant_sums.append(zone_group[var_col].sum())
                        
                        if variant_sums and base_sum != 0:
                            avg_variant = np.mean(variant_sums)
                            delta = avg_variant - base_sum
                            pct_change = (delta / base_sum * 100)
                            
                            zone_deltas.append({
                                'zone': zone,
                                'building_id': building_id,
                                'variable': var_clean,
                                f'{var_clean}_delta': delta,
                                f'{var_clean}_pct_change': pct_change,
                                'base_value': base_sum,
                                'modified_value': avg_variant
                            })
                
                except Exception as e:
                    self.logger.warning(f"Error processing zone data from {file_path}: {e}")
        
        return pd.DataFrame(zone_deltas)
        









    
    
    def _get_parameter_category(self, param_name: str) -> str:
        """Extract category from parameter name"""
        # Handle new format: category*object_type*object_name*field_name
        if '*' in param_name:
            parts = param_name.split('*')
            return parts[0] if parts else 'unknown'
        # Handle old format with underscores
        elif '_' in param_name:
            parts = param_name.split('_')
            return parts[0]
        return 'unknown'
    

    def _parse_parameter_name(self, param_name: str) -> Dict[str, str]:
        """Parse parameter name into components"""
        result = {
            'category': 'unknown',
            'object_type': '',
            'object_name': '',
            'field_name': ''
        }
        
        # Handle new format: category*object_type*object_name*field_name
        if '*' in param_name:
            parts = param_name.split('*')
            if len(parts) >= 1:
                result['category'] = parts[0]
            if len(parts) >= 2:
                result['object_type'] = parts[1]
            if len(parts) >= 3:
                result['object_name'] = parts[2]
            if len(parts) >= 4:
                result['field_name'] = parts[3]
        # Handle old format (backward compatibility)
        else:
            result['category'] = self._get_parameter_category(param_name)
            result['field_name'] = param_name
        
        return result



    def _results_to_dataframe(self, results: List[SensitivityResult]) -> pd.DataFrame:
        """Convert list of SensitivityResult objects to DataFrame"""
        if not results:
            return pd.DataFrame()
        
        records = []
        for result in results:
            record = {
                'level': result.level,
                'parameter': result.parameter,
                'category': result.category,
                'output_variable': result.output_variable,
                'sensitivity_score': result.sensitivity_score,
                'p_value': result.statistical_significance,
                'ci_lower': result.confidence_interval[0],
                'ci_upper': result.confidence_interval[1],
                'n_samples': result.n_samples
            }
            # Add metadata fields
            record.update(result.metadata)
            records.append(record)
        
        return pd.DataFrame(records)
    
    def _add_statistical_significance(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """Add significance levels based on p-values"""
        if 'p_value' not in results_df.columns:
            return results_df
        
        # Add significance stars
        conditions = [
            results_df['p_value'] < 0.001,
            results_df['p_value'] < 0.01,
            results_df['p_value'] < 0.05,
            results_df['p_value'] >= 0.05
        ]
        choices = ['***', '**', '*', '']
        results_df['significance'] = np.select(conditions, choices)
        
        # Add confidence level
        conf_conditions = [
            results_df['p_value'] < 0.01,
            results_df['p_value'] < 0.05,
            results_df['p_value'] >= 0.05
        ]
        conf_choices = ['high', 'medium', 'low']
        results_df['confidence_level'] = np.select(conf_conditions, conf_choices)
        
        return results_df
    
    def analyze_parameter_groups(self, 
                               sensitivity_df: pd.DataFrame,
                               parameter_groups: Optional[Dict[str, List[str]]] = None) -> pd.DataFrame:
        """Analyze sensitivity by parameter groups"""
        if parameter_groups is None:
            # Use categories as groups
            return sensitivity_df.groupby(['category', 'output_variable']).agg({
                'sensitivity_score': ['mean', 'std', 'max'],
                'n_samples': 'sum'
            }).reset_index()
        
        # Custom grouping
        group_results = []
        
        for group_name, params in parameter_groups.items():
            # Filter parameters in this group
            group_df = sensitivity_df[
                sensitivity_df['parameter'].str.contains('|'.join(params), case=False)
            ]
            
            if not group_df.empty:
                for output_var in group_df['output_variable'].unique():
                    var_df = group_df[group_df['output_variable'] == output_var]
                    
                    group_results.append({
                        'parameter_group': group_name,
                        'output_variable': output_var,
                        'avg_sensitivity': var_df['sensitivity_score'].mean(),
                        'max_sensitivity': var_df['sensitivity_score'].max(),
                        'std_sensitivity': var_df['sensitivity_score'].std(),
                        'n_parameters': len(var_df),
                        'total_samples': var_df['n_samples'].sum()
                    })
        
        return pd.DataFrame(group_results)
    
    def generate_report(self, 
                      sensitivity_df: pd.DataFrame,
                      group_analysis: Optional[pd.DataFrame] = None,
                      output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Generate comprehensive sensitivity report"""
        report = self.generate_base_report(sensitivity_df)
        
        # Add modification-specific information
        report['modification_summary'] = {
            'total_modifications': len(self.modification_tracking) if self.modification_tracking is not None else 0,
            'buildings_modified': self.modification_tracking['building_id'].nunique() if self.modification_tracking is not None else 0,
            'modification_scopes': self.modification_tracking['scope'].value_counts().to_dict() if self.modification_tracking is not None and 'scope' in self.modification_tracking else {}
        }
        
        # Add level-specific results
        if 'level' in sensitivity_df.columns:
            report['level_summary'] = {}
            for level in sensitivity_df['level'].unique():
                level_df = sensitivity_df[sensitivity_df['level'] == level]
                report['level_summary'][level] = {
                    'n_parameters': len(level_df),
                    'avg_sensitivity': float(level_df['sensitivity_score'].mean()),
                    'top_parameters': level_df.nlargest(5, 'sensitivity_score')[
                        ['parameter', 'sensitivity_score']
                    ].to_dict('records')
                }
        
        # Add group analysis
        if group_analysis is not None and not group_analysis.empty:
            report['group_analysis'] = group_analysis.to_dict('records')
        
        # Save if output directory provided
        if output_dir:
            report_path = output_dir / "modification_sensitivity_report.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
        
        return report
    
    def _calculate_deltas_from_comparison_files(self, 
                                               output_variables: List[str],
                                               frequency: str = 'daily') -> pd.DataFrame:
        """Calculate deltas using new comparison file format"""
        self.logger.info("Attempting to use new comparison file format...")
        
        comparison_path = self.modified_parsed_dir / "comparisons"
        if not comparison_path.exists():
            self.logger.info("No comparison directory found, falling back to old method")
            return pd.DataFrame()
        
        # Get all variants from modification tracking
        if self.modification_tracking is None:
            self.modification_tracking = self.load_modification_tracking()
        
        all_deltas = []
        
        # Get all comparison files for the frequency
        all_comparison_files = list(comparison_path.glob(f"var_*_{frequency}_*.parquet"))
        
        for var in output_variables:
            # Clean variable name - remove colons, brackets and convert to lowercase
            var_clean = var.split('[')[0].strip().lower()
            var_clean_normalized = var_clean.replace(':', '').replace('_', '')
            
            # Find matching files by checking if the normalized variable name matches
            var_files = []
            for file_path in all_comparison_files:
                # Parse filename to get variable name
                parts = file_path.stem.split('_')
                building_part = next((i for i, p in enumerate(parts) if p.startswith('b')), -1)
                
                if building_part > 0:
                    file_var_name = '_'.join(parts[1:building_part-2])
                    file_var_normalized = file_var_name.lower().replace('_', '')
                    
                    # Check if this file matches our variable
                    if var_clean_normalized in file_var_normalized or file_var_normalized in var_clean_normalized:
                        var_files.append(file_path)
            
            for file_path in var_files:
                try:
                    # Parse filename to get variable name
                    parts = file_path.stem.split('_')
                    building_part = next((i for i, p in enumerate(parts) if p.startswith('b')), -1)
                    
                    if building_part > 0:
                        variable_name = '_'.join(parts[1:building_part-2])
                        building_id = parts[building_part][1:]
                        
                        # Load comparison data
                        df = pd.read_parquet(file_path)
                        
                        # Get variant columns
                        variant_cols = [col for col in df.columns if col.startswith('variant_') and col.endswith('_value')]
                        
                        for variant_col in variant_cols:
                            variant_id = variant_col.replace('_value', '')
                            
                            # Get modifications for this variant and building
                            variant_mods = self.modification_tracking[
                                (self.modification_tracking['variant_id'] == variant_id) &
                                (self.modification_tracking['building_id'] == building_id)
                            ]
                            
                            if not variant_mods.empty:
                                # Calculate aggregated deltas
                                base_sum = df['base_value'].sum()
                                variant_sum = df[variant_col].sum()
                                
                                if base_sum != 0:
                                    abs_delta = variant_sum - base_sum
                                    pct_delta = (abs_delta / base_sum) * 100
                                    
                                    delta_record = {
                                        'building_id': building_id,
                                        'variant_id': variant_id,
                                        'category': df['category'].iloc[0] if 'category' in df.columns else 'unknown',
                                        'variable': var,
                                        'variable_clean': var_clean,
                                        f'{var_clean}_base': base_sum,
                                        f'{var_clean}_modified': variant_sum,
                                        f'{var_clean}_delta': abs_delta,
                                        f'{var_clean}_pct_change': pct_delta,
                                        'n_modifications': len(variant_mods)
                                    }
                                    
                                    all_deltas.append(delta_record)
                
                except Exception as e:
                    self.logger.warning(f"Failed to process comparison file {file_path}: {e}")
        
        if all_deltas:
            deltas_df = pd.DataFrame(all_deltas)
            
            # If multiple variants per building, aggregate to building level
            if 'variant_id' in deltas_df.columns:
                # Group by building and take mean of variants
                agg_dict = {col: 'mean' for col in deltas_df.columns 
                           if col not in ['building_id', 'variant_id', 'category', 'variable', 'variable_clean']}
                agg_dict['category'] = 'first'
                agg_dict['variable'] = 'first'
                agg_dict['variable_clean'] = 'first'
                
                deltas_df = deltas_df.groupby('building_id').agg(agg_dict).reset_index()
            
            self.logger.info(f"Calculated deltas from comparison files for {len(deltas_df)} buildings")
            return deltas_df
        
        return pd.DataFrame()
