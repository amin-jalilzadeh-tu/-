# modification_engine.py - Fixed version
"""
Enhanced Modification Engine with IDF writing capability
"""
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import copy

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from idf_modification.data_classes import (
    BuildingData, IDFObject, IDFParameter, 
    Modification, ParameterDefinition
)
from parserr.idf_parser import EnhancedIDFParser

from idf_modification.modification_tracker import ModificationTracker

# Import modifiers
from .modifiers.hvac_modifier import HVACModifier
from .modifiers.lighting_modifier import LightingModifier
from .modifiers.materials_modifier import MaterialsModifier
from .modifiers.infiltration_modifier import InfiltrationModifier
from .modifiers.ventilation_modifier import VentilationModifier
from .modifiers.equipment_modifier import EquipmentModifier
from .modifiers.dhw_modifier import DHWModifier
from .modifiers.schedules_modifier import SchedulesModifier
from .modifiers.shading_modifier import ShadingModifier
from .modifiers.simulation_control_modifier import SimulationControlModifier
from .modifiers.site_location_modifier import SiteLocationModifier
from .modifiers.geometry_modifier import GeometryModifier


class ModificationEngine:
    """
    Main engine for applying modifications to parsed IDF files
    """
    
    # Fix for modification_engine.py - Replace the __init__ method with this:

    def __init__(self, project_dir=None, config=None, output_path=None, session_id=None):
        """Initialize the modification engine
        
        Args:
            project_dir: Path to project directory containing parsed data
            config: Configuration dictionary
            output_path: Path to output directory (optional, defaults to project_dir/modified_idfs)
            session_id: Session identifier (optional)
        """
        # Set project directory
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        
        # Set configuration
        self.config = config or {}
        
        # Set output path
        if output_path:
            self.output_path = Path(output_path)
        else:
            self.output_path = self.project_dir / "modified_idfs"
        
        # Create output directory
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Set output directory for modified IDFs
        self.output_dir = self.output_path
        
        # Initialize session
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.modifications = []
        self.modification_count = 0
        self.building_modifications = {}
        self.session_start = datetime.now()
        self.current_session = None
        self.variants = {}
        self.current_variant = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize parser
        from parserr.idf_parser import EnhancedIDFParser
        self.parser = EnhancedIDFParser()
        
        # Initialize tracker
        self.tracker = ModificationTracker(output_path=self.output_path)
        self.tracker.session_id = self.session_id
        
        # Load modifiers
        self.modifiers = self._load_modifiers()
        
        # Log initialization
        self.logger.info(f"ModificationEngine initialized")
        self.logger.info(f"Project directory: {self.project_dir}")
        self.logger.info(f"Output directory: {self.output_path}")
        self.logger.info(f"Session ID: {self.session_id}")
    



    def _load_modifiers(self) -> Dict[str, Any]:
        """Load all available modifiers"""
        modifiers = {}
        
        # Map of category to modifier class
        modifier_classes = {
            'hvac': HVACModifier,
            'lighting': LightingModifier,
            'materials': MaterialsModifier,
            'infiltration': InfiltrationModifier,
            'ventilation': VentilationModifier,
            'equipment': EquipmentModifier,
            'dhw': DHWModifier,
            'schedules': SchedulesModifier,
            'shading': ShadingModifier,
            'simulation_control': SimulationControlModifier,
            'site_location': SiteLocationModifier,
            'geometry': GeometryModifier
        }
        
        # Instantiate modifiers
        parsed_data_path = self.project_dir / "parsed_data"
        
        for category, modifier_class in modifier_classes.items():
            try:
                modifiers[category] = modifier_class(
                    parsed_data_path=parsed_data_path,
                    modification_config=self.config.get('categories', {}).get(category, {})  # <-- Fixed: correct parameter name
                )
                self.logger.info(f"Loaded modifier: {modifier_class.__name__} for category '{category}'")
            except Exception as e:
                self.logger.error(f"Failed to load modifier for {category}: {e}")
        
        self.logger.info(f"Successfully loaded {len(modifiers)} modifiers: {list(modifiers.keys())}")
        return modifiers
    
    def apply_modifications_to_parsed(self,
                                    building_id: str,
                                    parsed_objects: Dict[str, List[IDFObject]],
                                    variant_id: str = "default",
                                    parameter_values: Dict[str, Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Apply modifications to parsed IDF objects
        
        Args:
            building_id: Building identifier
            parsed_objects: Dictionary of parsed objects by type
            variant_id: Variant identifier
            parameter_values: Dictionary of parameter values by category
            
        Returns:
            List of applied modifications
        """
        all_modifications = []
        
        # Track variant
        self.tracker.start_variant(variant_id)  # <-- Only pass variant_id
        
        # Get categories to modify
        if parameter_values:
            categories_to_modify = {k: v for k, v in parameter_values.items() 
                                  if k in self.modifiers}
        else:
            # Use all categories with default values
            categories_to_modify = {k: {} for k in self.modifiers.keys()}
        
        # Apply modifications for each category
        for category, params in categories_to_modify.items():
            if category not in self.modifiers:
                self.logger.warning(f"No modifier found for category: {category}")
                continue
            
            try:
                modifier = self.modifiers[category]
                
                # Load current values from parsed data with proper file mapping
                current_values = self._load_current_values_with_mapping(modifier, building_id)
                
                # Identify modifiable parameters
                modifiable_params = modifier.identify_modifiable_parameters(parsed_objects)
                
                # Apply modifications
                modifications = modifier.apply_modifications(
                    parsed_objects=parsed_objects,
                    modifiable_params=modifiable_params,
                    strategy=params.get('strategy', 'default')
                )
                
                # Validate and track modifications
                validated_mods = []
                for mod in modifications:
                    if modifier.validate_modification(mod):
                        validated_mods.append(mod)
                
                # Track modifications
                for mod in validated_mods:
                    self.tracker.add_modification(variant_id, mod)
                    
                    # Convert to dict for results
                    mod_dict = {
                        'building_id': building_id,
                        'variant_id': variant_id,
                        'category': category,
                        'object_type': mod.object_type,
                        'object_name': mod.object_name,
                        'parameter': mod.parameter,
                        'original_value': mod.original_value,
                        'new_value': mod.new_value,
                        'change_type': mod.change_type,
                        'rule_applied': mod.rule_applied,
                        'success': mod.success,
                        'validation_status': mod.validation_status,
                        'message': mod.message
                    }
                    all_modifications.append(mod_dict)
                
                self.logger.info(f"Applied {len(modifications)} modifications for {category}")
                
            except Exception as e:
                self.logger.error(f"Error applying {category} modifications: {e}")
                import traceback
                self.logger.debug(traceback.format_exc())
        
        # Complete variant tracking
        self.tracker.complete_variant(variant_id, None, all_modifications)
        
        return all_modifications
    
    def _load_current_values_with_mapping(self, modifier, building_id: str) -> Dict[str, pd.DataFrame]:
        """
        Load current values with proper file name mapping
        
        This handles the mismatch between expected file names and actual file names
        """
        current_values = {}
        
        # Get the base path
        parsed_data_path = self.project_dir / "parsed_data" / 'idf_data' / 'by_category'
        
        # Define file name mappings
        file_mappings = {
            'materials': ['materials_materials', 'materials_windowmaterials'],
            'constructions': ['materials_constructions']
        }
        
        # Get expected files from modifier
        category_files = modifier._get_category_files()
        
        for expected_file in category_files:
            loaded = False
            
            # Check if we have a mapping for this file
            if expected_file in file_mappings:
                # Try mapped file names
                for actual_file in file_mappings[expected_file]:
                    file_path = parsed_data_path / f"{actual_file}.parquet"
                    if file_path.exists():
                        df = pd.read_parquet(file_path)
                        if 'building_id' in df.columns:
                            df = df[df['building_id'] == building_id]
                        current_values[expected_file] = df
                        self.logger.debug(f"Loaded {len(df)} records from {actual_file} (mapped from {expected_file})")
                        loaded = True
                        break
            
            # If not loaded through mapping, try direct file name
            if not loaded:
                file_path = parsed_data_path / f"{expected_file}.parquet"
                if file_path.exists():
                    df = pd.read_parquet(file_path)
                    if 'building_id' in df.columns:
                        df = df[df['building_id'] == building_id]
                    current_values[expected_file] = df
                    self.logger.debug(f"Loaded {len(df)} records from {expected_file}")
                else:
                    self.logger.warning(f"File not found: {file_path}")
        
        modifier.current_values = current_values
        return current_values
    
    def write_parsed_objects_to_idf(self, parsed_objects: Dict[str, List[IDFObject]], 
                                   output_path: Path, 
                                   building_data: BuildingData) -> bool:
        """
        Write parsed objects back to IDF format
        
        Args:
            parsed_objects: Dictionary of parsed objects by type
            output_path: Path to write the IDF file
            building_data: Original BuildingData for reference
            
        Returns:
            True if successful
        """
        try:
            with open(output_path, 'w') as f:
                # Write header
                f.write("!-Generator IDFEditor 1.34\n")
                f.write("!-Option OriginalOrderTop UseSpecialFormat\n")
                f.write(f"!-Modified by Parser-Compatible Modification System\n")
                f.write(f"!-Modified Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"!-Session ID: {self.session_id}\n\n")
                
                # Define object order for proper IDF structure
                object_order = [
                    'VERSION',
                    'SIMULATIONCONTROL',
                    'BUILDING',
                    'SHADOWCALCULATION',
                    'SURFACECONVECTIONALGORITHM:INSIDE',
                    'SURFACECONVECTIONALGORITHM:OUTSIDE',
                    'HEATBALANCEALGORITHM',
                    'TIMESTEP',
                    'CONVERGENCELIMITS',
                    'SITE:LOCATION',
                    'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                    'SIZINGPERIOD:DESIGNDAY',
                    'RUNPERIOD',
                    'MATERIAL',
                    'MATERIAL:NOMASS',
                    'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
                    'CONSTRUCTION',
                    'GLOBALGEOMETRYRULES',
                    'ZONE',
                    'BUILDINGSURFACE:DETAILED',
                    'FENESTRATIONSURFACE:DETAILED',
                    'SCHEDULETYPELIMITS',
                    'SCHEDULE:COMPACT',
                    'SCHEDULE:CONSTANT',
                    'PEOPLE',
                    'LIGHTS',
                    'ELECTRICEQUIPMENT',
                    'ZONEINFILTRATION:DESIGNFLOWRATE',
                    'ZONEVENTILATION:DESIGNFLOWRATE',
                    'DESIGNSPECIFICATION:OUTDOORAIR',
                    'ZONEHVAC:IDEALLOADSAIRSYSTEM',
                    'ZONEHVAC:EQUIPMENTCONNECTIONS',
                    'ZONEHVAC:EQUIPMENTLIST',
                    'THERMOSTATSETPOINT:DUALSETPOINT',
                    'WATERHEATER:MIXED',
                    'OUTPUT:VARIABLE',
                    'OUTPUT:METER',
                    'OUTPUTCONTROL:TABLE:STYLE',
                    'OUTPUT:TABLE:SUMMARYREPORTS',
                    'OUTPUT:SQLITE'
                ]
                
                # Write objects in order
                written_types = set()
                
                # First pass: write in preferred order
                for obj_type in object_order:
                    if obj_type in parsed_objects:
                        objects = parsed_objects[obj_type]
                        for obj in objects:
                            self._write_idf_object(f, obj)
                        written_types.add(obj_type)
                
                # Second pass: write any remaining object types
                for obj_type, objects in parsed_objects.items():
                    if obj_type not in written_types:
                        for obj in objects:
                            self._write_idf_object(f, obj)
            
            self.logger.info(f"Successfully wrote modified IDF to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing IDF file: {e}")
            return False
    
    def _write_idf_object(self, file_handle, obj: IDFObject):
        """Write a single IDF object to file"""
        # Write object type
        file_handle.write(f"\n{obj.object_type},\n")
        
        # Write parameters
        for i, param in enumerate(obj.parameters):
            # Format the line with value and comment
            value = param.value if param.value else ""
            
            # Build comment
            comment_parts = []
            if param.field_name:
                comment_parts.append(param.field_name)
            if param.units:
                comment_parts.append(f"{{{param.units}}}")
            if param.comment:
                comment_parts.append(param.comment)
            
            comment = ", ".join(comment_parts) if comment_parts else ""
            
            # Determine line ending
            if i == len(obj.parameters) - 1:
                ending = ";"  # Last parameter
            else:
                ending = ","
            
            # Format the line with proper indentation
            if comment:
                file_handle.write(f"    {value}{ending}  !- {comment}\n")
            else:
                file_handle.write(f"    {value}{ending}\n")
    
    def modify_building(self, 
                       building_id: str, 
                       idf_path: Path,
                       parameter_values: Dict[str, Dict[str, Any]],
                       variant_id: str = "default") -> Dict[str, Any]:
        """
        Modify a single building's IDF using parsed structure
        
        Args:
            building_id: Building identifier
            idf_path: Path to IDF file
            parameter_values: Dictionary of parameter values by category
            variant_id: Variant identifier
            
        Returns:
            Dictionary with modification results
        """
        results = {
            'building_id': building_id,
            'variant_id': variant_id,
            'success': False,
            'modifications': [],
            'errors': [],
            'output_file': None
        }
        
        try:
            # Parse the IDF file
            self.logger.info(f"Parsing IDF file: {idf_path}")
            building_data = self.parser.parse_file(idf_path)
            
            # Get parsed objects
            parsed_objects = building_data.objects
            
            # Apply modifications
            all_modifications = self.apply_modifications_to_parsed(
                building_id=building_id,
                parsed_objects=parsed_objects,
                variant_id=variant_id,
                parameter_values=parameter_values
            )
            
            results['modifications'] = all_modifications
            
            # Write modified IDF if modifications were made
            if all_modifications and self.config['output_options'].get('save_modified_idfs', True):
                output_filename = f"building_{building_id}_{variant_id}.idf"
                output_path = self.output_dir / output_filename
                
                # Use the internal write method
                success = self.write_parsed_objects_to_idf(
                    parsed_objects=parsed_objects,
                    output_path=output_path,
                    building_data=building_data
                )
                
                if success:
                    results['success'] = True
                    results['output_file'] = str(output_path)
                    self.logger.info(f"Created modified IDF: {output_path}")
                else:
                    results['errors'].append("Failed to write modified IDF")
            
        except Exception as e:
            self.logger.error(f"Failed to modify building {building_id}: {e}")
            results['errors'].append(str(e))
            import traceback
            self.logger.debug(traceback.format_exc())
        
        return results
    
    def run_modifications(self, 
                         building_ids: Optional[List[str]] = None,
                         scenarios: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Run modifications on multiple buildings and scenarios
        
        Args:
            building_ids: List of building IDs to process
            scenarios: List of scenario configurations
            
        Returns:
            Dictionary with overall results
        """
        results = {
            'session_id': self.session_id,
            'buildings_processed': 0,
            'variants_created': 0,
            'modifications_applied': 0,
            'errors': []
        }
        
        try:
            # Start session
            self.tracker.start_session()
            
            # Select buildings
            buildings = self._select_buildings(building_ids)
            
            if not buildings:
                results['errors'].append("No buildings found to modify")
                return results
            
            # Process each building
            for building_id, idf_path in buildings:
                try:
                    # Apply each scenario
                    if scenarios:
                        for scenario in scenarios:
                            variant_id = scenario.get('id', 'default')
                            parameter_values = scenario.get('modifications', {})
                            
                            building_results = self.modify_building(
                                building_id=building_id,
                                idf_path=idf_path,
                                parameter_values=parameter_values,
                                variant_id=variant_id
                            )
                            
                            if building_results['success']:
                                results['variants_created'] += 1
                                results['modifications_applied'] += len(building_results['modifications'])
                            else:
                                results['errors'].extend(building_results['errors'])
                    else:
                        # Run with default modifications
                        building_results = self.modify_building(
                            building_id=building_id,
                            idf_path=idf_path,
                            parameter_values={},
                            variant_id='default'
                        )
                        
                        if building_results['success']:
                            results['variants_created'] += 1
                            results['modifications_applied'] += len(building_results['modifications'])
                    
                    results['buildings_processed'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing building {building_id}: {e}")
                    results['errors'].append(str(e))
            
        finally:
            self.tracker.end_session(results)
            
        return results
    
    def _select_buildings(self, building_ids: Optional[List[str]] = None) -> List[Tuple[str, Path]]:
        """Select buildings to modify based on configuration"""
        buildings = []
        
        # Get IDF directory
        idf_dir = self.project_dir / "output_IDFs"
        if not idf_dir.exists():
            idf_dir = self.project_dir
        
        # Get selection method from config
        selection = self.config.get('base_idf_selection', {})
        method = selection.get('method', 'all')
        
        if building_ids:
            # Use provided building IDs
            for bid in building_ids:
                pattern = f"*{bid}*.idf"
                files = list(idf_dir.glob(pattern))
                if files:
                    buildings.append((str(bid), files[0]))
        
        elif method == 'specific':
            # Use specific building IDs from config
            for bid in selection.get('building_ids', []):
                pattern = f"*{bid}*.idf"
                files = list(idf_dir.glob(pattern))
                if files:
                    buildings.append((str(bid), files[0]))
        
        elif method == 'representative':
            # Select representative buildings
            num_buildings = selection.get('num_buildings', 5)
            all_idfs = list(idf_dir.glob("*.idf"))[:num_buildings]
            for idf_file in all_idfs:
                bid = idf_file.stem.replace("building_", "").split("_")[0]
                buildings.append((bid, idf_file))
        
        else:  # method == 'all'
            # Select all buildings
            for idf_file in idf_dir.glob("*.idf"):
                bid = idf_file.stem.replace("building_", "").split("_")[0]
                buildings.append((bid, idf_file))
        
        self.logger.info(f"Selected {len(buildings)} buildings for modification")
        return buildings
    
    
    
    
    def _run_scenario_modifications(self, 
                                  buildings: List[Tuple[str, Path]], 
                                  dry_run: bool) -> Dict[str, Any]:
        """Run scenario-based modifications"""
        results = {
            'strategy': 'scenarios',
            'scenarios_processed': 0,
            'variants_by_scenario': {}
        }
        
        # Get scenarios
        scenarios = self.scenario_generator.generate_scenarios()
        results['scenarios_processed'] = len(scenarios)
        
        for scenario in scenarios:
            scenario_name = scenario['name']
            self.logger.info(f"Processing scenario: {scenario_name}")
            
            scenario_results = {
                'buildings': 0,
                'modifications': 0,
                'errors': []
            }
            
            # Create output directory for scenario
            scenario_dir = self.output_dir / scenario_name
            scenario_dir.mkdir(exist_ok=True)
            
            for building_id, idf_path in buildings:
                try:
                    # Apply scenario modifications
                    result = self.modify_building(
                        building_id=building_id,
                        idf_path=idf_path,
                        parameter_values=scenario['modifications'],
                        variant_id=scenario_name
                    )
                    
                    if result['success']:
                        scenario_results['buildings'] += 1
                        scenario_results['modifications'] += len(result['modifications'])
                    else:
                        scenario_results['errors'].extend(result['errors'])
                    
                except Exception as e:
                    self.logger.error(f"Error processing {building_id} for scenario {scenario_name}: {e}")
                    scenario_results['errors'].append(str(e))
            
            results['variants_by_scenario'][scenario_name] = scenario_results
        
        return results
    
    def _run_sampling_modifications(self, 
                                  buildings: List[Tuple[str, Path]], 
                                  dry_run: bool) -> Dict[str, Any]:
        """Run sampling-based modifications"""
        results = {
            'strategy': 'sampling',
            'samples_generated': 0,
            'sampling_method': self.config['modification_strategy'].get('sampling_method', 'uniform')
        }
        
        num_variants = self.config['modification_strategy'].get('num_variants', 10)
        results['samples_generated'] = num_variants
        
        # Generate parameter samples
        samples = self.scenario_generator.generate_samples(num_variants)
        
        for i, sample in enumerate(samples):
            variant_id = f"sample_{i:03d}"
            self.logger.info(f"Processing sample {i+1}/{num_variants}")
            
            for building_id, idf_path in buildings:
                try:
                    result = self.modify_building(
                        building_id=building_id,
                        idf_path=idf_path,
                        parameter_values=sample,
                        variant_id=variant_id
                    )
                    
                    results['modifications_applied'] = results.get('modifications_applied', 0)
                    if result['success']:
                        results['modifications_applied'] += len(result['modifications'])
                    
                except Exception as e:
                    self.logger.error(f"Error processing {building_id} for sample {i}: {e}")
                    results.setdefault('errors', []).append(str(e))
        
        return results
    
    def _run_optimization_modifications(self, 
                                      buildings: List[Tuple[str, Path]], 
                                      dry_run: bool) -> Dict[str, Any]:
        """Run optimization-based modifications"""
        results = {
            'strategy': 'optimization',
            'optimization_objectives': self.config['modification_strategy'].get('objectives', ['energy'])
        }
        
        # This is a simplified version - real optimization would use
        # iterative algorithms and simulation feedback
        self.logger.info("Running optimization-based modifications...")
        
        for objective in results['optimization_objectives']:
            self.logger.info(f"Optimizing for: {objective}")
            
            # Generate optimized parameters based on objective
            optimized_params = self.scenario_generator.generate_optimized_parameters(objective)
            
            for building_id, idf_path in buildings:
                try:
                    variant_id = f"optimized_{objective}"
                    result = self.modify_building(
                        building_id=building_id,
                        idf_path=idf_path,
                        parameter_values=optimized_params,
                        variant_id=variant_id
                    )
                    
                    results['variants_created'] = results.get('variants_created', 0) + 1
                    
                except Exception as e:
                    self.logger.error(f"Error optimizing {building_id} for {objective}: {e}")
                    results.setdefault('errors', []).append(str(e))
        
        return results
    
    def _generate_reports(self, results: Dict[str, Any]):
        """Generate modification reports"""
        report_dir = self.output_dir / "reports"
        report_dir.mkdir(exist_ok=True)
        
        # Summary report
        summary_path = report_dir / f"modification_summary_{self.session_id}.json"
        with open(summary_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Generated summary report: {summary_path}")
        
        # Detailed modifications report
        if self.tracker.modifications:
            mods_df = pd.DataFrame(self.tracker.modifications)
            mods_path = report_dir / f"detailed_modifications_{self.session_id}.csv"
            mods_df.to_csv(mods_path, index=False)
            self.logger.info(f"Generated detailed modifications report: {mods_path}")
        
        # Parameter changes report
        if self.config['output_options'].get('track_modifications', True):
            param_changes = self._analyze_parameter_changes()
            param_path = report_dir / f"parameter_changes_{self.session_id}.json"
            with open(param_path, 'w') as f:
                json.dump(param_changes, f, indent=2)
            self.logger.info(f"Generated parameter changes report: {param_path}")
    
    def _analyze_parameter_changes(self) -> Dict[str, Any]:
        """Analyze parameter changes across all modifications"""
        analysis = {
            'by_category': {},
            'by_parameter': {},
            'by_building': {},
            'statistics': {}
        }
        
        for mod in self.tracker.modifications:
            # By category
            category = mod.get('category', 'unknown')
            if category not in analysis['by_category']:
                analysis['by_category'][category] = 0
            analysis['by_category'][category] += 1
            
            # By parameter
            param = mod.get('parameter', 'unknown')
            if param not in analysis['by_parameter']:
                analysis['by_parameter'][param] = {
                    'count': 0,
                    'changes': []
                }
            analysis['by_parameter'][param]['count'] += 1
            
            # Track numeric changes
            if isinstance(mod.get('original_value'), (int, float)) and \
               isinstance(mod.get('new_value'), (int, float)):
                change_pct = ((mod['new_value'] - mod['original_value']) / 
                             mod['original_value'] * 100) if mod['original_value'] != 0 else 0
                analysis['by_parameter'][param]['changes'].append(change_pct)
            
            # By building
            building = mod.get('building_id', 'unknown')
            if building not in analysis['by_building']:
                analysis['by_building'][building] = 0
            analysis['by_building'][building] += 1
        
        # Calculate statistics
        analysis['statistics'] = {
            'total_modifications': len(self.tracker.modifications),
            'categories_modified': len(analysis['by_category']),
            'parameters_modified': len(analysis['by_parameter']),
            'buildings_modified': len(analysis['by_building'])
        }
        
        # Calculate average changes for numeric parameters
        for param, data in analysis['by_parameter'].items():
            if data['changes']:
                data['avg_change_pct'] = np.mean(data['changes'])
                data['std_change_pct'] = np.std(data['changes'])
        
        return analysis
    
    def process_batch(self, 
                     scenarios: List[Dict[str, Any]], 
                     parallel: bool = True, 
                     max_workers: int = None) -> pd.DataFrame:
        """
        Process multiple modification scenarios
        
        Args:
            scenarios: List of scenario configurations
            parallel: Whether to process in parallel
            max_workers: Maximum number of parallel workers
            
        Returns:
            DataFrame with all results
        """
        results = []
        
        if parallel and len(scenarios) > 1:
            with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
                future_to_scenario = {
                    executor.submit(self._process_single_scenario, scenario): scenario 
                    for scenario in scenarios
                }
                
                for future in concurrent.futures.as_completed(future_to_scenario):
                    scenario = future_to_scenario[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        self.logger.error(f"Error processing scenario: {e}")
                        results.append({
                            'scenario_id': scenario.get('scenario_id', 'unknown'),
                            'success': False,
                            'error': str(e)
                        })
        else:
            for scenario in scenarios:
                result = self._process_single_scenario(scenario)
                results.append(result)
        
        return pd.DataFrame(results)
    
    def _process_single_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single scenario"""
        scenario_id = scenario.get('scenario_id', 'unknown')
        building_id = scenario.get('building_id')
        idf_path = Path(scenario.get('idf_path'))
        parameter_values = scenario.get('parameters', {})
        
        self.logger.info(f"Processing scenario {scenario_id} for building {building_id}")
        
        # Apply modifications
        result = self.modify_building(
            building_id=building_id,
            idf_path=idf_path,
            parameter_values=parameter_values,
            variant_id=scenario_id
        )
        
        result['scenario_id'] = scenario_id
        
        return result