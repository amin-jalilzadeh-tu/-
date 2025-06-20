"""
Abstract base class for all IDF modifiers.

This module provides the base interface that all specific modifiers must implement.
"""
"""
Base Modifier Module - Abstract base class for all IDF modifiers
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import pandas as pd
from eppy.modeleditor import IDF
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
    """Abstract base class for all IDF modifiers"""
    
    def __init__(self, 
                 parsed_data_path: Path,
                 modification_config: Dict[str, Any],
                 logger: Optional[logging.Logger] = None):
        """
        Initialize base modifier
        
        Args:
            parsed_data_path: Path to parsed parquet data directory
            modification_config: Configuration for modifications
            logger: Logger instance
        """
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
        """
        Load current values from parsed parquet files
        
        Args:
            building_id: Building identifier
            
        Returns:
            Dictionary of dataframes with current values
        """
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
    
    def identify_modifiable_parameters(self, idf: IDF) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identify all parameters that can be modified
        
        Args:
            idf: IDF object to analyze
            
        Returns:
            Dictionary of modifiable parameters by object type
        """
        modifiable = {}
        
        for obj_type in self.get_modifiable_object_types():
            if obj_type in idf.idfobjects:
                objects = idf.idfobjects[obj_type]
                modifiable[obj_type] = []
                
                for obj in objects:
                    obj_params = {
                        'object': obj,
                        'name': obj.Name if hasattr(obj, 'Name') else f"{obj_type}_{id(obj)}",
                        'parameters': []
                    }
                    
                    # Check each parameter definition
                    for param_key, param_def in self.parameter_definitions.items():
                        if param_def.object_type == obj_type:
                            try:
                                current_value = self._get_parameter_value(obj, param_def)
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
                          idf: IDF, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List[ModificationResult]:
        """
        Apply modifications to IDF based on configuration and strategy
        
        Args:
            idf: IDF object to modify
            modifiable_params: Parameters that can be modified
            strategy: Modification strategy to apply
            
        Returns:
            List of modification results
        """
        self.modifications = []
        category_config = self.config.get(self.get_category_name(), {})
        
        if not category_config.get('enabled', False):
            self.logger.info(f"{self.get_category_name()} modifications disabled")
            return self.modifications
        
        # Apply modifications based on strategy
        strategy_config = category_config.get('strategy', 'default')
        parameters_config = category_config.get('parameters', {})
        
        for obj_type, objects in modifiable_params.items():
            for obj_info in objects:
                obj = obj_info['object']
                
                for param_info in obj_info['parameters']:
                    param_name = param_info['name']
                    param_def = param_info['definition']
                    current_value = param_info['current_value']
                    
                    # Check if this parameter should be modified
                    if param_def.field_name in parameters_config:
                        param_config = parameters_config[param_def.field_name]
                        
                        # Calculate new value based on method
                        new_value = self._calculate_new_value(
                            current_value, 
                            param_config,
                            param_def
                        )
                        
                        # Apply modification
                        if new_value != current_value:
                            result = self._apply_parameter_modification(
                                obj, param_def, current_value, new_value, param_config
                            )
                            self.modifications.append(result)
        
        return self.modifications
    
    def _calculate_new_value(self, 
                           current_value: Any, 
                           param_config: Dict[str, Any],
                           param_def: ParameterDefinition) -> Any:
        """Calculate new value based on modification method"""
        method = param_config.get('method', 'absolute')
        
        try:
            if method == 'absolute':
                # Set to specific value
                new_value = param_config.get('value', current_value)
                
            elif method == 'relative' or method == 'multiplier':
                # Multiply by factor
                if isinstance(param_config.get('range'), list):
                    import random
                    factor = random.uniform(*param_config['range'])
                else:
                    factor = param_config.get('factor', 1.0)
                new_value = float(current_value) * factor
                
            elif method == 'percentage':
                # Change by percentage
                if isinstance(param_config.get('range'), list):
                    import random
                    pct_change = random.uniform(*param_config['range'])
                else:
                    pct_change = param_config.get('change', 0)
                new_value = float(current_value) * (1 + pct_change / 100)
                
            elif method == 'range':
                # Sample within range
                import random
                new_value = random.uniform(*param_config['range'])
                
            elif method == 'discrete':
                # Choose from options
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
        if param_def.min_value is not None and value < param_def.min_value:
            value = param_def.min_value
        if param_def.max_value is not None and value > param_def.max_value:
            value = param_def.max_value
        if param_def.allowed_values is not None and value not in param_def.allowed_values:
            # Find closest allowed value
            if isinstance(value, (int, float)):
                value = min(param_def.allowed_values, key=lambda x: abs(x - value))
        return value
    
    def _apply_parameter_modification(self,
                                    obj: Any,
                                    param_def: ParameterDefinition,
                                    current_value: Any,
                                    new_value: Any,
                                    param_config: Dict[str, Any]) -> ModificationResult:
        """Apply modification to IDF object"""
        try:
            # Set the new value
            self._set_parameter_value(obj, param_def, new_value)
            
            result = ModificationResult(
                success=True,
                object_type=param_def.object_type,
                object_name=obj.Name if hasattr(obj, 'Name') else str(obj),
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
                object_name=obj.Name if hasattr(obj, 'Name') else str(obj),
                parameter=param_def.field_name,
                original_value=current_value,
                new_value=new_value,
                change_type=param_config.get('method', 'unknown'),
                validation_status='error',
                message=str(e)
            )
            self.logger.error(f"Failed to modify parameter: {e}")
            
        return result
    
    def _get_parameter_value(self, obj: Any, param_def: ParameterDefinition) -> Any:
        """Get parameter value from IDF object"""
        try:
            # Try field name first
            if hasattr(obj, param_def.field_name):
                return getattr(obj, param_def.field_name)
            # Try by index
            elif param_def.field_index < len(obj.obj):
                return obj.obj[param_def.field_index]
            else:
                return None
        except:
            return None
    
    def _set_parameter_value(self, obj: Any, param_def: ParameterDefinition, value: Any):
        """Set parameter value in IDF object"""
        # Try field name first
        if hasattr(obj, param_def.field_name):
            setattr(obj, param_def.field_name, value)
        # Try by index
        elif param_def.field_index < len(obj.obj):
            obj.obj[param_def.field_index] = value
        else:
            raise ValueError(f"Cannot set parameter {param_def.field_name}")
    
    def validate_modifications(self, 
                             idf: IDF,
                             modifications: List[ModificationResult]) -> List[ModificationResult]:
        """
        Validate modifications for consistency and constraints
        
        Args:
            idf: Modified IDF object
            modifications: List of modifications made
            
        Returns:
            Updated list of modifications with validation status
        """
        for mod in modifications:
            if mod.success:
                # Check dependencies
                if self.parameter_definitions.get(mod.parameter):
                    param_def = self.parameter_definitions[mod.parameter]
                    
                    # Validate dependencies
                    for dep in param_def.dependencies:
                        if not self._validate_dependency(idf, mod, dep):
                            mod.validation_status = 'dependency_error'
                            mod.message = f"Dependency validation failed: {dep}"
                            
        return modifications
    
    def _validate_dependency(self, idf: IDF, modification: ModificationResult, dependency: str) -> bool:
        """Validate a specific dependency"""
        # Override in subclasses for specific dependency checks
        return True
    
    def track_changes(self) -> pd.DataFrame:
        """
        Convert modifications to DataFrame for tracking
        
        Returns:
            DataFrame with modification details
        """
        if not self.modifications:
            return pd.DataFrame()
            
        data = []
        for mod in self.modifications:
            data.append({
                'category': self.get_category_name(),
                'object_type': mod.object_type,
                'object_name': mod.object_name,
                'parameter': mod.parameter,
                'original_value': str(mod.original_value),
                'new_value': str(mod.new_value),
                'change_type': mod.change_type,
                'rule_applied': mod.rule_applied,
                'success': mod.success,
                'validation_status': mod.validation_status,
                'message': mod.message
            })
            
        return pd.DataFrame(data)