"""
Enhanced SQL Analyzer with Static Data Extraction
Integrates timeseries and non-timeseries SQL data extraction
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime

from sql_table_extractor import SQLTableExtractor


class EnhancedSQLAnalyzer:
    """Enhanced SQL analyzer that extracts both timeseries and static data"""
    
    def __init__(self, sql_path: Path, output_dir: Path, building_id: str, 
                 variant_id: str = 'base', is_base: bool = True):
        """
        Initialize enhanced SQL analyzer
        
        Args:
            sql_path: Path to SQL file
            output_dir: Directory for output files
            building_id: Building identifier
            variant_id: Variant identifier ('base' for base buildings)
            is_base: Whether this is a base building
        """
        self.sql_path = sql_path
        self.output_dir = Path(output_dir)
        self.building_id = building_id
        self.variant_id = variant_id
        self.is_base = is_base
        
        # Initialize extractors
        self.table_extractor = SQLTableExtractor(sql_path)
        
        # Create output directories
        self._setup_directories()
    
    def _setup_directories(self):
        """Create output directory structure"""
        if self.is_base:
            # Base building directories
            self.dirs = {
                'timeseries': self.output_dir / 'timeseries',
                'characteristics': self.output_dir / 'building_characteristics',
                'performance': self.output_dir / 'performance_analysis',
                'quality': self.output_dir / 'quality_control',
                'metadata': self.output_dir / 'metadata'
            }
        else:
            # Variant building directories
            self.dirs = {
                'timeseries': self.output_dir / 'timeseries',
                'comparisons': self.output_dir / 'comparisons',
                'performance': self.output_dir / 'variant_performance',
                'sensitivity': self.output_dir / 'sensitivity_analysis',
                'metadata': self.output_dir / 'metadata'
            }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def extract_all_data(self) -> Dict[str, Any]:
        """Extract all SQL data and save to appropriate locations"""
        results = {
            'building_id': self.building_id,
            'variant_id': self.variant_id,
            'extraction_time': datetime.now().isoformat(),
            'extracted_tables': []
        }
        
        # Extract static data (only for base buildings)
        if self.is_base:
            print(f"Extracting static data for base building {self.building_id}")
            self._extract_building_characteristics()
            results['extracted_tables'].extend(['geometry', 'envelope', 'constructions'])
        
        # Extract performance data (for all buildings)
        print(f"Extracting performance data for {self.building_id} ({self.variant_id})")
        self._extract_performance_summaries()
        results['extracted_tables'].extend(['annual_summary', 'equipment_sizing'])
        
        # Extract quality metrics
        self._extract_quality_metrics()
        results['extracted_tables'].append('quality_metrics')
        
        # Close connection
        self.table_extractor.close()
        
        return results
    
    def _extract_building_characteristics(self):
        """Extract static building characteristics (geometry, envelope, etc.)"""
        
        # 1. Extract geometry data
        zones_df = self.table_extractor.extract_zones()
        if not zones_df.empty:
            geometry_data = {
                'building_id': self.building_id,
                'total_floor_area_m2': zones_df['Area'].sum(),
                'total_volume_m3': zones_df['Volume'].sum(),
                'num_zones': len(zones_df),
                'num_floors': zones_df['Multiplier'].max(),  # Approximate
                'avg_ceiling_height_m': zones_df['CeilingHeight'].mean(),
                'min_ceiling_height_m': zones_df['CeilingHeight'].min(),
                'max_ceiling_height_m': zones_df['CeilingHeight'].max()
            }
            
            # Save geometry data
            geometry_df = pd.DataFrame([geometry_data])
            geometry_path = self.dirs['characteristics'] / 'geometry.parquet'
            if geometry_path.exists():
                existing_df = pd.read_parquet(geometry_path)
                geometry_df = pd.concat([existing_df, geometry_df], ignore_index=True)
                geometry_df = geometry_df.drop_duplicates(subset=['building_id'], keep='last')
            geometry_df.to_parquet(geometry_path, index=False)
        
        # 2. Extract envelope data
        surfaces_df = self.table_extractor.extract_surfaces()
        if not surfaces_df.empty:
            # Calculate envelope metrics
            exterior_walls = surfaces_df[surfaces_df['ClassName'] == 'Wall:Exterior']
            windows = surfaces_df[surfaces_df['ClassName'] == 'Window']
            roofs = surfaces_df[surfaces_df['ClassName'] == 'Roof']
            
            # Window-to-wall ratio by orientation
            envelope_data = {
                'building_id': self.building_id,
                'total_wall_area_m2': exterior_walls['Area'].sum(),
                'total_window_area_m2': windows['Area'].sum(),
                'total_roof_area_m2': roofs['Area'].sum(),
                'overall_wwr': windows['Area'].sum() / exterior_walls['Area'].sum() if not exterior_walls.empty else 0
            }
            
            # Calculate by orientation (using azimuth)
            for orientation, azimuth_range in [
                ('north', (315, 45)), ('east', (45, 135)),
                ('south', (135, 225)), ('west', (225, 315))
            ]:
                orient_walls = self._filter_by_azimuth(exterior_walls, azimuth_range)
                orient_windows = self._filter_by_azimuth(windows, azimuth_range)
                
                envelope_data[f'wall_area_{orientation}_m2'] = orient_walls['Area'].sum()
                envelope_data[f'window_area_{orientation}_m2'] = orient_windows['Area'].sum()
                envelope_data[f'wwr_{orientation}'] = (
                    orient_windows['Area'].sum() / orient_walls['Area'].sum() 
                    if not orient_walls.empty else 0
                )
            
            # Save envelope data
            envelope_df = pd.DataFrame([envelope_data])
            envelope_path = self.dirs['characteristics'] / 'envelope.parquet'
            if envelope_path.exists():
                existing_df = pd.read_parquet(envelope_path)
                envelope_df = pd.concat([existing_df, envelope_df], ignore_index=True)
                envelope_df = envelope_df.drop_duplicates(subset=['building_id'], keep='last')
            envelope_df.to_parquet(envelope_path, index=False)
        
        # 3. Extract construction properties
        constructions_df = self.table_extractor.extract_constructions()
        materials_df = self.table_extractor.extract_materials()
        
        if not constructions_df.empty:
            # Calculate average U-values
            wall_constructions = constructions_df[
                (constructions_df['TypeIsWindow'] == 0) & 
                (constructions_df['Name'].str.contains('Wall', case=False, na=False))
            ]
            window_constructions = constructions_df[constructions_df['TypeIsWindow'] == 1]
            roof_constructions = constructions_df[
                (constructions_df['TypeIsWindow'] == 0) & 
                (constructions_df['Name'].str.contains('Roof', case=False, na=False))
            ]
            
            construction_data = {
                'building_id': self.building_id,
                'avg_wall_uvalue': wall_constructions['Uvalue'].mean(),
                'min_wall_uvalue': wall_constructions['Uvalue'].min(),
                'max_wall_uvalue': wall_constructions['Uvalue'].max(),
                'avg_window_uvalue': window_constructions['Uvalue'].mean(),
                'avg_roof_uvalue': roof_constructions['Uvalue'].mean(),
                'num_construction_types': len(constructions_df),
                'num_materials': len(materials_df) if not materials_df.empty else 0
            }
            
            # Calculate thermal mass indicator
            if not materials_df.empty:
                construction_data['thermal_mass_indicator'] = self._calculate_thermal_mass(
                    materials_df, constructions_df
                )
            
            # Save construction data
            construction_df = pd.DataFrame([construction_data])
            construction_path = self.dirs['characteristics'] / 'constructions.parquet'
            if construction_path.exists():
                existing_df = pd.read_parquet(construction_path)
                construction_df = pd.concat([existing_df, construction_df], ignore_index=True)
                construction_df = construction_df.drop_duplicates(subset=['building_id'], keep='last')
            construction_df.to_parquet(construction_path, index=False)
        
        # 4. Extract design loads
        people_df = self.table_extractor.extract_nominal_people()
        lighting_df = self.table_extractor.extract_nominal_lighting()
        
        if not people_df.empty or not lighting_df.empty:
            floor_area = geometry_data.get('total_floor_area_m2', 1)  # Avoid division by zero
            
            design_loads_data = {
                'building_id': self.building_id,
                'occupancy_density_ppm2': people_df['NumberOfPeople'].sum() / floor_area if not people_df.empty else 0,
                'lighting_power_density_wm2': lighting_df['DesignLevel'].sum() / floor_area if not lighting_df.empty else 0,
                'total_occupancy': people_df['NumberOfPeople'].sum() if not people_df.empty else 0,
                'total_lighting_power_w': lighting_df['DesignLevel'].sum() if not lighting_df.empty else 0
            }
            
            # Save design loads
            loads_df = pd.DataFrame([design_loads_data])
            loads_path = self.dirs['characteristics'] / 'design_loads.parquet'
            if loads_path.exists():
                existing_df = pd.read_parquet(loads_path)
                loads_df = pd.concat([existing_df, loads_df], ignore_index=True)
                loads_df = loads_df.drop_duplicates(subset=['building_id'], keep='last')
            loads_df.to_parquet(loads_path, index=False)
    
    def _extract_performance_summaries(self):
        """Extract annual performance summaries"""
        
        # 1. Extract tabular data (annual summaries)
        tabular_df = self.table_extractor.extract_tabular_data()
        
        if not tabular_df.empty:
            # Extract energy by end-use
            annual_data = {
                'building_id': self.building_id,
                'variant_id': self.variant_id
            }
            
            # Energy consumption by end-use
            for end_use in ['Heating', 'Cooling', 'Interior Lighting', 'Interior Equipment', 
                           'Fans', 'Pumps', 'Heat Rejection', 'Water Systems']:
                elec_value = self._extract_tabular_value(
                    tabular_df, 'End Uses', end_use, 'Electricity [kWh]'
                )
                gas_value = self._extract_tabular_value(
                    tabular_df, 'End Uses', end_use, 'Natural Gas [kWh]'
                )
                
                if elec_value is not None:
                    annual_data[f'{end_use.lower().replace(" ", "_")}_elec_kwh'] = elec_value
                if gas_value is not None:
                    annual_data[f'{end_use.lower().replace(" ", "_")}_gas_kwh'] = gas_value
            
            # Total energy
            annual_data['total_electricity_kwh'] = self._extract_tabular_value(
                tabular_df, 'End Uses', 'Total End Uses', 'Electricity [kWh]'
            ) or 0
            annual_data['total_gas_kwh'] = self._extract_tabular_value(
                tabular_df, 'End Uses', 'Total End Uses', 'Natural Gas [kWh]'
            ) or 0
            annual_data['total_energy_kwh'] = (
                annual_data['total_electricity_kwh'] + annual_data['total_gas_kwh']
            )
            
            # Peak demands
            annual_data['peak_electricity_kw'] = self._extract_tabular_value(
                tabular_df, 'End Uses', 'Total End Uses', 'Electricity [W]'
            ) / 1000 if self._extract_tabular_value(
                tabular_df, 'End Uses', 'Total End Uses', 'Electricity [W]'
            ) else None
            
            # Comfort metrics
            annual_data['unmet_heating_hours'] = self._extract_tabular_value(
                tabular_df, 'Comfort and Setpoint Not Met Summary', 
                'Time Setpoint Not Met During Occupied Heating', 'Facility [Hours]'
            ) or 0
            annual_data['unmet_cooling_hours'] = self._extract_tabular_value(
                tabular_df, 'Comfort and Setpoint Not Met Summary',
                'Time Setpoint Not Met During Occupied Cooling', 'Facility [Hours]'
            ) or 0
            
            # Save annual summary
            annual_df = pd.DataFrame([annual_data])
            annual_path = self.dirs['performance'] / 'annual_summary.parquet'
            if annual_path.exists():
                existing_df = pd.read_parquet(annual_path)
                annual_df = pd.concat([existing_df, annual_df], ignore_index=True)
                annual_df = annual_df.drop_duplicates(
                    subset=['building_id', 'variant_id'], keep='last'
                )
            annual_df.to_parquet(annual_path, index=False)
        
        # 2. Extract equipment sizing
        component_sizes_df = self.table_extractor.extract_component_sizes()
        
        if not component_sizes_df.empty:
            # Aggregate by component type
            equipment_data = {
                'building_id': self.building_id,
                'variant_id': self.variant_id
            }
            
            # Cooling capacity
            cooling_components = component_sizes_df[
                component_sizes_df['CompType'].str.contains('Cooling', case=False, na=False)
            ]
            equipment_data['total_cooling_capacity_kw'] = (
                cooling_components[cooling_components['Units'] == 'W']['Value'].sum() / 1000
            )
            
            # Heating capacity
            heating_components = component_sizes_df[
                component_sizes_df['CompType'].str.contains('Heating|Boiler|Furnace', 
                                                           case=False, na=False)
            ]
            equipment_data['total_heating_capacity_kw'] = (
                heating_components[heating_components['Units'] == 'W']['Value'].sum() / 1000
            )
            
            # Fan flow rates
            fan_components = component_sizes_df[
                component_sizes_df['CompType'].str.contains('Fan', case=False, na=False)
            ]
            equipment_data['total_fan_flow_m3s'] = (
                fan_components[fan_components['Units'] == 'm3/s']['Value'].sum()
            )
            
            # Save equipment sizing
            equipment_df = pd.DataFrame([equipment_data])
            equipment_path = self.dirs['performance'] / 'equipment_sizing.parquet'
            if equipment_path.exists():
                existing_df = pd.read_parquet(equipment_path)
                equipment_df = pd.concat([existing_df, equipment_df], ignore_index=True)
                equipment_df = equipment_df.drop_duplicates(
                    subset=['building_id', 'variant_id'], keep='last'
                )
            equipment_df.to_parquet(equipment_path, index=False)
    
    def _extract_quality_metrics(self):
        """Extract simulation quality metrics"""
        
        errors_df = self.table_extractor.extract_errors()
        
        quality_data = {
            'building_id': self.building_id,
            'variant_id': self.variant_id,
            'total_warnings': 0,
            'total_severe_errors': 0,
            'total_fatal_errors': 0,
            'has_convergence_issues': False,
            'simulation_quality_score': 100  # Start with perfect score
        }
        
        if not errors_df.empty:
            # Count by error type
            for _, error in errors_df.iterrows():
                if error['ErrorType'] == 1:  # Warning
                    quality_data['total_warnings'] += error['Count']
                    quality_data['simulation_quality_score'] -= 0.1 * error['Count']
                elif error['ErrorType'] == 2:  # Severe
                    quality_data['total_severe_errors'] += error['Count']
                    quality_data['simulation_quality_score'] -= 1 * error['Count']
                elif error['ErrorType'] == 3:  # Fatal
                    quality_data['total_fatal_errors'] += error['Count']
                    quality_data['simulation_quality_score'] -= 10 * error['Count']
                
                # Check for convergence issues
                if 'convergence' in error['ErrorMessage'].lower():
                    quality_data['has_convergence_issues'] = True
                    quality_data['simulation_quality_score'] -= 5
        
        # Ensure score doesn't go below 0
        quality_data['simulation_quality_score'] = max(0, quality_data['simulation_quality_score'])
        
        # Save quality metrics
        quality_df = pd.DataFrame([quality_data])
        quality_path = self.dirs['quality'] / 'simulation_errors.parquet'
        if quality_path.exists():
            existing_df = pd.read_parquet(quality_path)
            quality_df = pd.concat([existing_df, quality_df], ignore_index=True)
            quality_df = quality_df.drop_duplicates(
                subset=['building_id', 'variant_id'], keep='last'
            )
        quality_df.to_parquet(quality_path, index=False)
    
    def _filter_by_azimuth(self, surfaces_df: pd.DataFrame, 
                          azimuth_range: Tuple[float, float]) -> pd.DataFrame:
        """Filter surfaces by azimuth angle range"""
        min_az, max_az = azimuth_range
        if min_az > max_az:  # Handles north (315-45)
            return surfaces_df[
                (surfaces_df['Azimuth'] >= min_az) | (surfaces_df['Azimuth'] <= max_az)
            ]
        else:
            return surfaces_df[
                (surfaces_df['Azimuth'] >= min_az) & (surfaces_df['Azimuth'] <= max_az)
            ]
    
    def _calculate_thermal_mass(self, materials_df: pd.DataFrame, 
                               constructions_df: pd.DataFrame) -> float:
        """Calculate thermal mass indicator"""
        # Simple thermal mass calculation: sum of (density * specific heat * thickness)
        thermal_mass = 0
        for _, material in materials_df.iterrows():
            if all(pd.notna([material['Density'], material['SpecificHeat'], 
                            material['Thickness']])):
                thermal_mass += (
                    material['Density'] * 
                    material['SpecificHeat'] * 
                    material['Thickness']
                )
        return thermal_mass
    
    def _extract_tabular_value(self, tabular_df: pd.DataFrame, table_name: str,
                              row_name: str, column_name: str) -> Optional[float]:
        """Extract a specific value from tabular data"""
        mask = (
            (tabular_df['TableName'] == table_name) & 
            (tabular_df['RowName'] == row_name) & 
            (tabular_df['ColumnName'] == column_name)
        )
        filtered = tabular_df[mask]
        
        if not filtered.empty:
            try:
                return float(filtered.iloc[0]['Value'])
            except:
                return None
        return None


# Example usage
if __name__ == "__main__":
    # Example for base building
    sql_path = Path("path/to/simulation_bldg0_4136733.sql")
    output_dir = Path("parsed_data")
    
    analyzer = EnhancedSQLAnalyzer(
        sql_path=sql_path,
        output_dir=output_dir,
        building_id="4136733",
        variant_id="base",
        is_base=True
    )
    
    # Extract all data
    results = analyzer.extract_all_data()
    print(f"Extraction complete: {results}")
    
    # Example for variant building
    variant_sql_path = Path("path/to/simulation_bldg1_4136733.sql")
    variant_output_dir = Path("parsed_modified_results")
    
    variant_analyzer = EnhancedSQLAnalyzer(
        sql_path=variant_sql_path,
        output_dir=variant_output_dir,
        building_id="4136733",
        variant_id="variant_1",
        is_base=False
    )
    
    variant_results = variant_analyzer.extract_all_data()
    print(f"Variant extraction complete: {variant_results}")