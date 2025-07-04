"""
Enhanced Base Modifier Module - Compatible with parsed IDF structure
Works with the parser's IDFObject and IDFParameter structure
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import pandas as pd
import logging
from dataclasses import dataclass, field
import json

@dataclass
class ModificationResult:
    """Container for modification results"""
    success: bool
    object_type: str
    object_name: str
    parameter: str
    original_value: Any
    new_value: Any
    change_type: str  # 'absolute', 'relative', 'percentage'
    rule_applied: Optional[str] = None
    validation_status: str = 'valid'
    message: Optional[str] = None
    zone_name: Optional[str] = None  # ADD THIS

@dataclass
class ParameterDefinition:
    """Definition of a modifiable parameter"""
    object_type: str
    field_name: str
    field_index: int
    data_type: type
    units: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    dependencies: List[str] = field(default_factory=list)
    performance_impact: Optional[str] = None

class BaseModifier(ABC):
    """Abstract base class for all IDF modifiers - Parser Compatible Version"""
    
    def __init__(self, 
                 parsed_data_path: Path,
                 modification_config: Dict[str, Any],
                 logger: Optional[logging.Logger] = None):
        """Initialize base modifier"""
        self.parsed_data_path = Path(parsed_data_path)
        self.config = modification_config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.modifications: List[ModificationResult] = []
        self.current_values: Dict[str, pd.DataFrame] = {}
        self.parameter_definitions: Dict[str, ParameterDefinition] = {}
        
        # Initialize parameter definitions for this modifier
        self._initialize_parameters()
        
    @abstractmethod
    def _initialize_parameters(self):
        """Initialize parameter definitions for this modifier"""
        pass
    
    @abstractmethod
    def get_category_name(self) -> str:
        """Return the category name for this modifier"""
        pass
    
    @abstractmethod
    def get_modifiable_object_types(self) -> List[str]:
        """Return list of IDF object types this modifier can handle"""
        pass
    
    def load_current_values(self, building_id: str) -> Dict[str, pd.DataFrame]:
        """Load current values from parsed parquet files"""
        self.logger.info(f"Loading current values for {self.get_category_name()}")
        current_values = {}
        
        # Load relevant parquet files based on category
        category_files = self._get_category_files()
        
        for file_name in category_files:
            file_path = self.parsed_data_path / 'idf_data' / 'by_category' / f"{file_name}.parquet"
            if file_path.exists():
                df = pd.read_parquet(file_path)
                # Filter by building_id if column exists
                if 'building_id' in df.columns:
                    df = df[df['building_id'] == building_id]
                current_values[file_name] = df
                self.logger.debug(f"Loaded {len(df)} records from {file_name}")
            else:
                self.logger.warning(f"File not found: {file_path}")
                
        self.current_values = current_values
        return current_values
    
    @abstractmethod
    def _get_category_files(self) -> List[str]:
        """Return list of parquet files to load for this category"""
        pass
    
    def identify_modifiable_parameters(self, parsed_objects: Dict[str, List[Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identify all parameters that can be modified from parsed objects
        
        Args:
            parsed_objects: Dictionary of parsed objects by type from the parser
            
        Returns:
            Dictionary of modifiable parameters by object type
        """
        modifiable = {}
        
        for obj_type in self.get_modifiable_object_types():
            if obj_type in parsed_objects:
                objects = parsed_objects[obj_type]
                modifiable[obj_type] = []
                
                for obj in objects:
                    obj_params = {
                        'object': obj,
                        'name': obj.name if hasattr(obj, 'name') else 'Unknown',
                        'parameters': []
                    }
                    
                    # Check each parameter definition
                    for param_key, param_def in self.parameter_definitions.items():
                        if param_def.object_type == obj_type:
                            try:
                                current_value = self._get_parameter_value_from_parsed(obj, param_def)
                                if current_value is not None:
                                    obj_params['parameters'].append({
                                        'name': param_def.field_name,
                                        'current_value': current_value,
                                        'definition': param_def
                                    })
                            except Exception as e:
                                self.logger.debug(f"Could not get {param_def.field_name}: {e}")
                    
                    if obj_params['parameters']:
                        modifiable[obj_type].append(obj_params)
        
        return modifiable
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List[ModificationResult]:
        """Apply modifications to parsed objects based on configuration and strategy"""
        modifications = []
        
        # Get parameter configuration for this category
        param_configs = self.config.get('parameters', {})
        
        for obj_type, objects in modifiable_params.items():
            for obj_info in objects:
                obj = obj_info['object']
                
                for param_info in obj_info['parameters']:
                    param_name = param_info['definition'].field_name
                    param_key = self._get_param_key(param_name)
                    
                    if param_key in param_configs:
                        param_config = param_configs[param_key]
                        
                        # Skip if disabled
                        if not param_config.get('enabled', True):
                            continue
                        
                        # Calculate new value
                        current_value = param_info['current_value']
                        new_value = self._calculate_new_value(
                            current_value, 
                            param_config,
                            param_info['definition']
                        )
                        
                        # Apply modification
                        result = self._apply_parameter_modification_to_parsed(
                            obj,
                            param_info['definition'],
                            current_value,
                            new_value,
                            param_config
                        )
                        
                        if obj_type == 'LIGHTS':
                            valid, error_msg = self._validate_lighting_fractions(obj)
                            if not valid:
                                self.logger.error(f"Validation failed: {error_msg}")




                        modifications.append(result)
                        self.modifications.append(result)
        
        return modifications
    
    def _get_param_key(self, field_name: str) -> str:
        """Convert field name to parameter key used in config"""
        # Convert "Watts per Zone Floor Area" to "watts_per_area"
        # This should match the keys used in parameter_definitions
        for key, param_def in self.parameter_definitions.items():
            if param_def.field_name == field_name:
                return key
        return field_name.lower().replace(' ', '_')
    
    def _calculate_new_value(self,
                           current_value: Any, 
                           param_config: Dict[str, Any],
                           param_def: ParameterDefinition) -> Any:
        """Calculate new value based on modification method"""
        method = param_config.get('method', 'absolute')
        
        try:
            if method == 'absolute':
                new_value = param_config.get('value', current_value)
                
            elif method == 'relative' or method == 'multiplier':
                if isinstance(param_config.get('range'), list):
                    import random
                    factor = random.uniform(*param_config['range'])
                else:
                    factor = param_config.get('factor', 1.0)
                new_value = float(current_value) * factor
                
            elif method == 'percentage':
                if isinstance(param_config.get('range'), list):
                    import random
                    pct_change = random.uniform(*param_config['range'])
                else:
                    pct_change = param_config.get('change', 0)
                new_value = float(current_value) * (1 + pct_change / 100)
                
            elif method == 'range':
                import random
                new_value = random.uniform(*param_config['range'])
                
            elif method == 'discrete':
                import random
                options = param_config.get('options', [current_value])
                new_value = random.choice(options)
                
            else:
                new_value = current_value
                
            # Apply constraints
            new_value = self._apply_constraints(new_value, param_def)
            
            # Maintain data type
            if param_def.data_type == int:
                new_value = int(round(new_value))
            elif param_def.data_type == float:
                new_value = float(new_value)
                
            return new_value
            
        except Exception as e:
            self.logger.error(f"Error calculating new value: {e}")
            return current_value
    
    def _apply_constraints(self, value: Any, param_def: ParameterDefinition) -> Any:
        """Apply min/max constraints to value"""
        # FIX: Add EnergyPlus-specific constraints first
        if param_def.object_type == 'FENESTRATIONSURFACE:DETAILED' and param_def.field_name == 'Multiplier':
            value = max(1.0, float(value))  # Ensure window multiplier >= 1.0
        
        # Apply general constraints
        if param_def.min_value is not None and value < param_def.min_value:
            value = param_def.min_value
        if param_def.max_value is not None and value > param_def.max_value:
            value = param_def.max_value

        if param_def.allowed_values is not None and value not in param_def.allowed_values:
            # Find closest allowed value
            if isinstance(value, (int, float)):
                value = min(param_def.allowed_values, key=lambda x: abs(x - value))
        return value
    


    def _validate_energyplus_constraints(self, param_def: ParameterDefinition, value: Any) -> Tuple[bool, str]:
        """Validate value against EnergyPlus-specific constraints"""
        
        # Window multiplier constraint
        if param_def.field_name == 'Multiplier' and param_def.object_type == 'FENESTRATIONSURFACE:DETAILED':
            if float(value) < 1.0:
                return False, f"Window multiplier must be >= 1.0, got {value}"
        
        # Material conductivity constraint
        if param_def.field_name == 'Conductivity' and param_def.object_type == 'MATERIAL':
            if float(value) < 0.01:
                return False, f"Material conductivity too low: {value}"
        
        # COP constraints
        if 'COP' in param_def.field_name.upper():
            if float(value) > 10.0:
                return False, f"COP unrealistically high: {value}"
        
        return True, ""



    def _validate_energyplus_constraints(self, param_def: ParameterDefinition, value: Any) -> Tuple[bool, str]:
        """Validate value against EnergyPlus-specific constraints"""
        
        # Window multiplier constraint
        if param_def.field_name == 'Multiplier' and param_def.object_type == 'FENESTRATIONSURFACE:DETAILED':
            if float(value) < 1.0:
                return False, f"Window multiplier must be >= 1.0, got {value}"
        
        # Material conductivity constraint
        if param_def.field_name == 'Conductivity' and param_def.object_type == 'MATERIAL':
            if float(value) < 0.01:
                return False, f"Material conductivity too low: {value}"
        
        # COP constraints
        if 'COP' in param_def.field_name.upper():
            if float(value) > 10.0:
                return False, f"COP unrealistically high: {value}"
        
        return True, ""

    def _validate_lighting_fractions(self, obj) -> Tuple[bool, str]:
        """Validate that lighting fractions sum to 1.0"""
        if obj.object_type != 'LIGHTS':
            return True, ""
        
        fractions = {'radiant': 0, 'visible': 0, 'return_air': 0}
        
        for param in obj.parameters:
            if param.field_name == 'Fraction Radiant':
                fractions['radiant'] = param.numeric_value or float(param.value or 0)
            elif param.field_name == 'Fraction Visible':
                fractions['visible'] = param.numeric_value or float(param.value or 0)
            elif param.field_name == 'Return Air Fraction':
                fractions['return_air'] = param.numeric_value or float(param.value or 0)
        
        total = sum(fractions.values())
        # Total should be <= 1.0 (the remainder is Fraction Lost)
        if total > 1.001:  # Allow small tolerance for floating point
            return False, f"Lighting fractions sum to {total:.3f}, exceeds 1.0 for {obj.name}"
        
        return True, ""







    def _apply_parameter_modification_to_parsed(self,
                                    obj: Any,
                                    param_def: ParameterDefinition,
                                    current_value: Any,
                                    new_value: Any,
                                    param_config: Dict[str, Any]) -> ModificationResult:
        """Apply modification to parsed IDF object"""
        try:
            # Set the new value in the parsed structure
            self._set_parameter_value_in_parsed(obj, param_def, new_value)
            
            result = ModificationResult(
                success=True,
                object_type=param_def.object_type,
                object_name=obj.name,
                parameter=param_def.field_name,
                original_value=current_value,
                new_value=new_value,
                change_type=param_config.get('method', 'unknown'),
                rule_applied=param_config.get('rule', None),
                validation_status='valid'
            )
            
            self.logger.info(f"Modified {result.object_type}.{result.parameter}: "
                           f"{result.original_value} → {result.new_value}")
            
        except Exception as e:
            result = ModificationResult(
                success=False,
                object_type=param_def.object_type,
                object_name=obj.name,
                parameter=param_def.field_name,
                original_value=current_value,
                new_value=new_value,
                change_type=param_config.get('method', 'unknown'),
                validation_status='error',
                message=str(e)
            )
            self.logger.error(f"Failed to modify parameter: {e}")
            
        return result
    
    def _get_parameter_value_from_parsed(self, obj: Any, param_def: ParameterDefinition) -> Any:
        """Get parameter value from parsed IDF object structure"""
        try:
            # Find parameter by field name
            for i, param in enumerate(obj.parameters):
                if hasattr(param, 'field_name') and param.field_name == param_def.field_name:
                    # Return numeric value if available, otherwise string value
                    if hasattr(param, 'numeric_value') and param.numeric_value is not None:
                        return param.numeric_value
                    elif hasattr(param, 'value'):
                        return param.value
                    return None
            
            # Try by index if field name not found
            if 0 <= param_def.field_index < len(obj.parameters):
                param = obj.parameters[param_def.field_index]
                if hasattr(param, 'numeric_value') and param.numeric_value is not None:
                    return param.numeric_value
                elif hasattr(param, 'value'):
                    return param.value
                    
            return None
        except Exception as e:
            self.logger.debug(f"Error getting parameter value: {e}")
            return None
    
    def _set_parameter_value_in_parsed(self, obj: Any, param_def: ParameterDefinition, value: Any):
        """Set parameter value in parsed IDF object structure"""
        # Find parameter by field name
        for param in obj.parameters:
            if param.field_name == param_def.field_name:
                param.value = str(value)
                # Update numeric value if applicable
                if isinstance(value, (int, float)):
                    param.numeric_value = float(value)
                return
        
        # Try by index if field name not found
        if 0 <= param_def.field_index < len(obj.parameters):
            param = obj.parameters[param_def.field_index]
            param.value = str(value)
            if isinstance(value, (int, float)):
                param.numeric_value = float(value)
            return
            
        raise ValueError(f"Cannot set parameter {param_def.field_name} - not found in object")
    
    # Add this method to base_modifier.py in the BaseModifier class

    def validate_modification(self, modification: ModificationResult) -> bool:
        """
        Validate a modification before applying it
        
        Args:
            modification: The modification result to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation
        if not modification.success:
            return False
        
        # Check if the parameter is known
        param_key = self._get_param_key(modification.parameter)
        if param_key not in self.parameter_definitions:
            self.logger.warning(f"Unknown parameter: {modification.parameter}")
            return True  # Allow unknown parameters for now
        
        param_def = self.parameter_definitions[param_key]
        
        # Validate data type
        if param_def.data_type == float:
            try:
                float(modification.new_value)
            except (ValueError, TypeError):
                self.logger.error(f"Invalid float value: {modification.new_value}")
                return False
        elif param_def.data_type == int:
            try:
                int(modification.new_value)
            except (ValueError, TypeError):
                self.logger.error(f"Invalid int value: {modification.new_value}")
                return False
        
        # Validate range
        if param_def.min_value is not None and float(modification.new_value) < param_def.min_value:
            self.logger.error(f"Value {modification.new_value} below minimum {param_def.min_value}")
            return False
        
        if param_def.max_value is not None and float(modification.new_value) > param_def.max_value:
            self.logger.error(f"Value {modification.new_value} above maximum {param_def.max_value}")
            return False
        
        # Validate allowed values
        if param_def.allowed_values and modification.new_value not in param_def.allowed_values:
            self.logger.error(f"Value {modification.new_value} not in allowed values: {param_def.allowed_values}")
            return False
        

        # Validate EnergyPlus constraints
        valid, error_msg = self._validate_energyplus_constraints(param_def, modification.new_value)
        if not valid:
            self.logger.error(f"EnergyPlus constraint violation: {error_msg}")
            return False




        return True
    
    def _validate_dependency(self, parsed_objects: Dict[str, List[Any]], 
                           modification: ModificationResult, 
                           dependency: str) -> bool:
        """Validate a specific dependency"""
        # This is a placeholder - implement specific dependency checks
        return True
    
    def export_modifications(self, output_path: Path) -> Path:
        """Export modifications to file"""
        mod_data = []
        for mod in self.modifications:
            mod_data.append({
                'timestamp': pd.Timestamp.now(),
                'object_type': mod.object_type,
                'object_name': mod.object_name,
                'parameter': mod.parameter,
                'original_value': mod.original_value,
                'new_value': mod.new_value,
                'change_type': mod.change_type,
                'rule_applied': mod.rule_applied,
                'validation_status': mod.validation_status,
                'message': mod.message
            })
        
        df = pd.DataFrame(mod_data)
        output_file = output_path / f"{self.get_category_name()}_modifications.csv"
        df.to_csv(output_file, index=False)
        
        return output_file
    
    def _create_modification_result(self, obj: Any, parameter_key: str, 
                                original_value: Any, new_value: Any, 
                                rule_applied: str) -> ModificationResult:
        """
        Create a ModificationResult with zone_name extraction
        """
        # Extract zone name based on object type
        zone_name = self._extract_zone_name_from_object(obj)
        
        # Get parameter definition if available
        param_def = self.parameter_definitions.get(parameter_key, None)
        field_name = param_def.field_name if param_def else parameter_key
        
        # FIX: Handle objects without proper names
        object_name = obj.name
        
        # Special handling for objects that don't have meaningful names
        if obj.object_type.upper() in ['SITE:GROUNDTEMPERATURE:BUILDINGSURFACE', 
                                        'TIMESTEP', 'SHADOWCALCULATION', 
                                        'SIMULATIONCONTROL', 'RUNPERIOD']:
            object_name = obj.object_type  # Use type as name
        elif not object_name or (isinstance(object_name, (int, float)) and 
                                not isinstance(object_name, str)):
            # If name is numeric or missing, use object type
            object_name = obj.object_type
        
        return ModificationResult(
            success=True,
            object_type=obj.object_type,
            object_name=object_name,  # Use fixed name
            parameter=field_name,
            original_value=original_value,
            new_value=new_value,
            change_type='absolute',
            rule_applied=rule_applied,
            validation_status='valid',
            zone_name=zone_name
        )

    def _extract_zone_name_from_object(self, obj: Any) -> str:
        """
        Extract zone name from an IDF object - Enhanced version
        """
        object_type = obj.object_type.upper()
        
        # Building-level objects
        building_level = {
            'TIMESTEP', 'SIMULATIONCONTROL', 'BUILDING', 'SHADOWCALCULATION',
            'HEATBALANCEALGORITHM', 'SURFACECONVECTIONALGORITHM:INSIDE',
            'SURFACECONVECTIONALGORITHM:OUTSIDE', 'SITE:LOCATION',
            'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE', 'RUNPERIOD',
            'RUNPERIODCONTROL:SPECIALDAYS', 'RUNPERIODCONTROL:DAYLIGHTSAVINGTIME',
            'GLOBALGEOMETRYRULES', 'OUTPUT:VARIABLE', 'OUTPUT:METER',
            'OUTPUT:TABLE:SUMMARYREPORTS', 'OUTPUT:SQLITE', 'OUTPUTCONTROL:TABLE:STYLE',
            'MATERIAL', 'MATERIAL:NOMASS', 'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
            'CONSTRUCTION', 'VERSION'
        }
        
        if object_type in building_level:
            return 'BUILDING'
        
        # For ZONE objects, the zone name is the object name itself
        if object_type == 'ZONE':
            return obj.name
        
        # For objects with explicit zone fields
        zone_field_objects = {
            'LIGHTS': 'Zone or ZoneList Name',
            'ELECTRICEQUIPMENT': 'Zone or ZoneList Name',
            'PEOPLE': 'Zone or ZoneList Name',
            'ZONEINFILTRATION:DESIGNFLOWRATE': 'Zone or ZoneList Name',
            'ZONEVENTILATION:DESIGNFLOWRATE': 'Zone or ZoneList Name',
            'BUILDINGSURFACE:DETAILED': 'Zone Name',
            'INTERNALMASS': 'Zone Name',
            'ZONEHVAC:IDEALLOADSAIRSYSTEM': 'Zone Name',
            'ZONEHVAC:EQUIPMENTCONNECTIONS': 'Zone Name',
            'THERMOSTATSETPOINT:DUALSETPOINT': 'Zone or ZoneList Name',
            'ZONECONTROL:THERMOSTAT': 'Zone or ZoneList Name',
            'SIZING:ZONE': 'Zone or ZoneList Name'
        }
        
        if object_type in zone_field_objects:
            field_name = zone_field_objects[object_type]
            # Look for the zone parameter
            for param in obj.parameters:
                if param.field_name == field_name:
                    zone_value = param.value
                    if zone_value:
                        # Check for special values
                        if zone_value.upper() in ['ALL_ZONES', '*', 'ALL ZONES', 'ALLZONES']:
                            return 'ALL_ZONES'
                        else:
                            return zone_value.upper()
                    break
        
        # For fenestration surfaces, extract from parent surface
        if object_type == 'FENESTRATIONSURFACE:DETAILED':
            # First try object name pattern
            import re
            
            # Common window naming patterns
            window_patterns = [
                r'^(Zone\d+)',                    # Zone1_Window
                r'^(\w+_ZN)',                     # CORE_ZN_Window
                r'^(\w+?)_\w+_Wall',             # Zone1_Front_Wall_Window
                r'^(\w+?)_.*window',             # Zone1_anything_window
            ]
            
            for pattern in window_patterns:
                match = re.search(pattern, obj.name, re.IGNORECASE)
                if match:
                    return match.group(1).upper()
            
            # Then try to get from Building Surface Name parameter
            for param in obj.parameters:
                if param.field_name == 'Building Surface Name':
                    parent_name = param.value
                    if parent_name:
                        # Extract zone from parent surface name
                        for pattern in window_patterns[:-1]:  # Skip the last pattern
                            match = re.search(pattern, parent_name, re.IGNORECASE)
                            if match:
                                return match.group(1).upper()
                    break
        
        # For objects that might have zone in their name
        if obj.name and isinstance(obj.name, str):
            import re
            # Generic zone extraction from object name
            match = re.search(r'(Zone\d+|CORE_ZN|\w+_ZN)', obj.name, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # Default for unknown zone association
        return 'UNKNOWN'
        
    