"""
Central registry of modifiable IDF parameters.

This module maintains a registry of all parameters that can be modified
across different IDF object types.
"""
"""
Parameter Registry - Central registry of all modifiable parameters
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import pandas as pd

@dataclass
class ParameterInfo:
    """Complete information about a modifiable parameter"""
    category: str
    object_type: str
    field_name: str
    field_index: int
    data_type: str
    units: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default_value: Optional[Any] = None
    allowed_values: Optional[List[Any]] = None
    description: Optional[str] = None
    performance_impact: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    code_requirements: Dict[str, Any] = field(default_factory=dict)

class ParameterRegistry:
    """Central registry for all modifiable IDF parameters"""
    
    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize parameter registry
        
        Args:
            registry_path: Path to registry JSON file
        """
        self.parameters: Dict[str, ParameterInfo] = {}
        self.index_by_category: Dict[str, List[str]] = {}
        self.index_by_object: Dict[str, List[str]] = {}
        self.index_by_impact: Dict[str, List[str]] = {}
        self.index_by_tag: Dict[str, List[str]] = {}
        
        if registry_path:
            self.load_registry(registry_path)
        else:
            self._initialize_default_registry()
    
    def _initialize_default_registry(self):
        """Initialize with default parameter definitions"""
        # HVAC Parameters
        self.register_parameter(ParameterInfo(
            category='hvac',
            object_type='COIL:COOLING:DX:SINGLESPEED',
            field_name='Gross Rated COP',
            field_index=9,
            data_type='float',
            units='W/W',
            min_value=2.0,
            max_value=6.0,
            default_value=3.0,
            description='Coefficient of Performance at rated conditions',
            performance_impact='cooling_efficiency',
            tags=['efficiency', 'cooling', 'energy'],
            code_requirements={'ASHRAE_90.1': {'2019': 3.0, '2022': 3.2}}
        ))
        
        self.register_parameter(ParameterInfo(
            category='hvac',
            object_type='COIL:HEATING:ELECTRIC',
            field_name='Efficiency',
            field_index=3,
            data_type='float',
            units='',
            min_value=0.8,
            max_value=1.0,
            default_value=1.0,
            description='Heating coil efficiency',
            performance_impact='heating_efficiency',
            tags=['efficiency', 'heating', 'energy']
        ))
        
        # Lighting Parameters
        self.register_parameter(ParameterInfo(
            category='lighting',
            object_type='LIGHTS',
            field_name='Watts per Zone Floor Area',
            field_index=5,
            data_type='float',
            units='W/m2',
            min_value=0.0,
            max_value=30.0,
            default_value=10.0,
            description='Lighting power density',
            performance_impact='lighting_energy',
            tags=['lpd', 'energy', 'lighting'],
            code_requirements={'ASHRAE_90.1': {'2019': 8.5, '2022': 7.5}}
        ))
        
        # Infiltration Parameters
        self.register_parameter(ParameterInfo(
            category='infiltration',
            object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
            field_name='Air Changes per Hour',
            field_index=7,
            data_type='float',
            units='1/hr',
            min_value=0.0,
            max_value=5.0,
            default_value=0.5,
            description='Infiltration air change rate',
            performance_impact='infiltration_loads',
            tags=['envelope', 'air_leakage', 'energy']
        ))
        
        # Material Parameters
        self.register_parameter(ParameterInfo(
            category='materials',
            object_type='MATERIAL',
            field_name='Conductivity',
            field_index=3,
            data_type='float',
            units='W/m-K',
            min_value=0.01,
            max_value=5.0,
            description='Material thermal conductivity',
            performance_impact='thermal_resistance',
            tags=['insulation', 'envelope', 'heat_transfer']
        ))
        
        self.register_parameter(ParameterInfo(
            category='materials',
            object_type='WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
            field_name='U-Factor',
            field_index=1,
            data_type='float',
            units='W/m2-K',
            min_value=0.5,
            max_value=6.0,
            default_value=2.0,
            description='Window U-factor (thermal transmittance)',
            performance_impact='window_heat_transfer',
            tags=['windows', 'envelope', 'heat_transfer'],
            code_requirements={'ASHRAE_90.1': {'2019': 2.8, '2022': 2.5}}
        ))
        
        # Equipment Parameters
        self.register_parameter(ParameterInfo(
            category='equipment',
            object_type='ELECTRICEQUIPMENT',
            field_name='Watts per Zone Floor Area',
            field_index=5,
            data_type='float',
            units='W/m2',
            min_value=0.0,
            max_value=50.0,
            default_value=10.0,
            description='Equipment power density',
            performance_impact='plug_loads',
            tags=['equipment', 'plug_loads', 'energy']
        ))
        
        # Ventilation Parameters
        self.register_parameter(ParameterInfo(
            category='ventilation',
            object_type='DESIGNSPECIFICATION:OUTDOORAIR',
            field_name='Outdoor Air Flow per Person',
            field_index=2,
            data_type='float',
            units='m3/s-person',
            min_value=0.0,
            max_value=0.05,
            default_value=0.0025,
            description='Outdoor air ventilation rate per person',
            performance_impact='outdoor_air_loads',
            tags=['iaq', 'ventilation', 'outdoor_air'],
            code_requirements={'ASHRAE_62.1': {'2019': 0.0025}}
        ))
        
        # Add more parameters as needed...
    
    def register_parameter(self, param_info: ParameterInfo) -> str:
        """
        Register a new parameter
        
        Args:
            param_info: Parameter information
            
        Returns:
            Parameter key
        """
        # Create unique key
        key = f"{param_info.category}.{param_info.object_type}.{param_info.field_name}"
        
        # Store parameter
        self.parameters[key] = param_info
        
        # Update indices
        if param_info.category not in self.index_by_category:
            self.index_by_category[param_info.category] = []
        self.index_by_category[param_info.category].append(key)
        
        if param_info.object_type not in self.index_by_object:
            self.index_by_object[param_info.object_type] = []
        self.index_by_object[param_info.object_type].append(key)
        
        if param_info.performance_impact:
            if param_info.performance_impact not in self.index_by_impact:
                self.index_by_impact[param_info.performance_impact] = []
            self.index_by_impact[param_info.performance_impact].append(key)
        
        for tag in param_info.tags:
            if tag not in self.index_by_tag:
                self.index_by_tag[tag] = []
            self.index_by_tag[tag].append(key)
        
        return key
    
    def get_parameter(self, key: str) -> Optional[ParameterInfo]:
        """Get parameter by key"""
        return self.parameters.get(key)
    
    def get_parameters_by_category(self, category: str) -> List[ParameterInfo]:
        """Get all parameters in a category"""
        keys = self.index_by_category.get(category, [])
        return [self.parameters[key] for key in keys]
    
    def get_parameters_by_object(self, object_type: str) -> List[ParameterInfo]:
        """Get all parameters for an object type"""
        keys = self.index_by_object.get(object_type, [])
        return [self.parameters[key] for key in keys]
    
    def get_parameters_by_impact(self, impact: str) -> List[ParameterInfo]:
        """Get all parameters with specific performance impact"""
        keys = self.index_by_impact.get(impact, [])
        return [self.parameters[key] for key in keys]
    
    def get_parameters_by_tag(self, tag: str) -> List[ParameterInfo]:
        """Get all parameters with specific tag"""
        keys = self.index_by_tag.get(tag, [])
        return [self.parameters[key] for key in keys]
    
    def search_parameters(self, 
                         category: Optional[str] = None,
                         object_type: Optional[str] = None,
                         field_name: Optional[str] = None,
                         tags: Optional[List[str]] = None,
                         impact: Optional[str] = None) -> List[ParameterInfo]:
        """Search parameters with multiple criteria"""
        results = list(self.parameters.values())
        
        if category:
            results = [p for p in results if p.category == category]
        
        if object_type:
            results = [p for p in results if p.object_type == object_type]
        
        if field_name:
            results = [p for p in results if field_name.lower() in p.field_name.lower()]
        
        if tags:
            results = [p for p in results if any(tag in p.tags for tag in tags)]
        
        if impact:
            results = [p for p in results if p.performance_impact == impact]
        
        return results
    
    def get_code_requirements(self, 
                            standard: str = 'ASHRAE_90.1',
                            version: str = '2019') -> Dict[str, float]:
        """Get code requirements for all parameters"""
        requirements = {}
        
        for key, param in self.parameters.items():
            if standard in param.code_requirements:
                if version in param.code_requirements[standard]:
                    requirements[key] = param.code_requirements[standard][version]
        
        return requirements
    
    def validate_value(self, 
                      parameter_key: str, 
                      value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate a parameter value
        
        Args:
            parameter_key: Parameter key
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        param = self.parameters.get(parameter_key)
        if not param:
            return False, f"Unknown parameter: {parameter_key}"
        
        # Type validation
        try:
            if param.data_type == 'float':
                value = float(value)
            elif param.data_type == 'int':
                value = int(value)
            elif param.data_type == 'str':
                value = str(value)
        except (ValueError, TypeError):
            return False, f"Invalid type: expected {param.data_type}"
        
        # Range validation
        if param.min_value is not None and value < param.min_value:
            return False, f"Value {value} below minimum {param.min_value}"
        
        if param.max_value is not None and value > param.max_value:
            return False, f"Value {value} above maximum {param.max_value}"
        
        # Allowed values validation
        if param.allowed_values and value not in param.allowed_values:
            return False, f"Value {value} not in allowed values: {param.allowed_values}"
        
        return True, None
    
    def get_parameter_bounds(self, 
                           parameter_key: str) -> Tuple[Optional[float], Optional[float]]:
        """Get min/max bounds for a parameter"""
        param = self.parameters.get(parameter_key)
        if param:
            return param.min_value, param.max_value
        return None, None
    
    def export_to_dataframe(self) -> pd.DataFrame:
        """Export registry to pandas DataFrame"""
        data = []
        for key, param in self.parameters.items():
            row = asdict(param)
            row['key'] = key
            data.append(row)
        
        return pd.DataFrame(data)
    
    def save_registry(self, output_path: Path):
        """Save registry to JSON file"""
        data = {}
        for key, param in self.parameters.items():
            param_dict = asdict(param)
            # Convert lists to JSON-serializable format
            param_dict['dependencies'] = list(param_dict['dependencies'])
            param_dict['tags'] = list(param_dict['tags'])
            data[key] = param_dict
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_registry(self, input_path: Path):
        """Load registry from JSON file"""
        with open(input_path) as f:
            data = json.load(f)
        
        self.parameters.clear()
        self.index_by_category.clear()
        self.index_by_object.clear()
        self.index_by_impact.clear()
        self.index_by_tag.clear()
        
        for key, param_dict in data.items():
            param_info = ParameterInfo(**param_dict)
            self.parameters[key] = param_info
            # Rebuild indices
            self.register_parameter(param_info)
    
    def generate_documentation(self) -> str:
        """Generate markdown documentation of all parameters"""
        doc = ["# IDF Parameter Registry\n"]
        
        # Group by category
        for category in sorted(self.index_by_category.keys()):
            doc.append(f"\n## {category.title()}\n")
            
            params = self.get_parameters_by_category(category)
            for param in sorted(params, key=lambda p: p.object_type):
                doc.append(f"\n### {param.object_type} - {param.field_name}\n")
                doc.append(f"- **Field Index**: {param.field_index}\n")
                doc.append(f"- **Data Type**: {param.data_type}\n")
                if param.units:
                    doc.append(f"- **Units**: {param.units}\n")
                if param.min_value is not None:
                    doc.append(f"- **Min Value**: {param.min_value}\n")
                if param.max_value is not None:
                    doc.append(f"- **Max Value**: {param.max_value}\n")
                if param.default_value is not None:
                    doc.append(f"- **Default**: {param.default_value}\n")
                if param.description:
                    doc.append(f"- **Description**: {param.description}\n")
                if param.performance_impact:
                    doc.append(f"- **Performance Impact**: {param.performance_impact}\n")
                if param.tags:
                    doc.append(f"- **Tags**: {', '.join(param.tags)}\n")
                if param.code_requirements:
                    doc.append(f"- **Code Requirements**: {param.code_requirements}\n")
        
        return '\n'.join(doc)