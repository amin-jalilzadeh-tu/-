"""
Base Modifier Module - Abstract base class for all IDF modifiers
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
import numpy as np
from eppy.modeleditor import IDF
import json
from datetime import datetime


@dataclass
class ModificationParameter:
    """Represents a single parameter that can be modified"""
    object_type: str
    object_name: str
    field_name: str
    field_index: int
    current_value: Any
    new_value: Any = None
    units: str = ""
    modification_rule: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModificationScenario:
    """Represents a complete modification scenario"""
    scenario_id: str
    scenario_name: str
    description: str
    parameters: List[ModificationParameter] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BaseModifier(ABC):
    """Abstract base class for all IDF modifiers"""
    
    def __init__(self, category: str, parsed_data_path: Path = None):
        """
        Initialize the modifier
        
        Args:
            category: Category name (e.g., 'hvac', 'lighting')
            parsed_data_path: Path to parsed data directory
        """
        self.category = category
        self.parsed_data_path = parsed_data_path
        self.modifications_log = []
        self.parameter_definitions = self._load_parameter_definitions()
        
    @abstractmethod
    def identify_parameters(self, idf: IDF, building_id: str) -> List[ModificationParameter]:
        """
        Identify all modifiable parameters in the IDF
        
        Args:
            idf: The IDF object to analyze
            building_id: Building identifier
            
        Returns:
            List of modifiable parameters
        """
        pass
    
    @abstractmethod
    def generate_modifications(self, 
                             parameters: List[ModificationParameter],
                             strategy: str,
                             options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate modification values based on strategy
        
        Args:
            parameters: List of parameters to modify
            strategy: Modification strategy name
            options: Strategy-specific options
            
        Returns:
            List of modification sets (each set is a dict of param_id: new_value)
        """
        pass
    
    @abstractmethod
    def apply_modifications(self, 
                          idf: IDF, 
                          modifications: Dict[str, Any]) -> bool:
        """
        Apply modifications to the IDF
        
        Args:
            idf: The IDF object to modify
            modifications: Dict of parameter_id: new_value
            
        Returns:
            Success status
        """
        pass
    
    def validate_modifications(self, modifications: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate proposed modifications
        
        Args:
            modifications: Dict of parameter_id: new_value
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        for param_id, new_value in modifications.items():
            param = self._get_parameter_by_id(param_id)
            if not param:
                errors.append(f"Unknown parameter: {param_id}")
                continue
                
            # Check constraints
            if 'min_value' in param.constraints and new_value < param.constraints['min_value']:
                errors.append(f"{param_id}: Value {new_value} below minimum {param.constraints['min_value']}")
            
            if 'max_value' in param.constraints and new_value > param.constraints['max_value']:
                errors.append(f"{param_id}: Value {new_value} above maximum {param.constraints['max_value']}")
                
        return len(errors) == 0, errors
    
    def track_changes(self, 
                     scenario_id: str,
                     modifications: Dict[str, Any],
                     metadata: Dict[str, Any] = None):
        """
        Track modifications for later analysis
        
        Args:
            scenario_id: Unique scenario identifier
            modifications: Applied modifications
            metadata: Additional metadata
        """
        change_record = {
            'scenario_id': scenario_id,
            'category': self.category,
            'timestamp': datetime.now().isoformat(),
            'modifications': modifications,
            'metadata': metadata or {}
        }
        self.modifications_log.append(change_record)
    
    def load_parsed_data(self, building_id: str) -> Optional[pd.DataFrame]:
        """
        Load parsed data for the building and category
        
        Args:
            building_id: Building identifier
            
        Returns:
            DataFrame with parsed data or None
        """
        if not self.parsed_data_path:
            return None
            
        # Try different file patterns
        file_patterns = [
            f"{self.category}*.parquet",
            f"*{self.category}*.parquet",
            f"{self.category}.parquet"
        ]
        
        for pattern in file_patterns:
            files = list(self.parsed_data_path.glob(f"idf_data/by_category/{pattern}"))
            if files:
                df = pd.read_parquet(files[0])
                # Filter by building_id if column exists
                if 'building_id' in df.columns:
                    df = df[df['building_id'] == building_id]
                return df
                
        return None
    
    def _load_parameter_definitions(self) -> Dict[str, Any]:
        """Load parameter definitions for this category"""
        # This would load from a JSON file in real implementation
        return {}
    
    def _get_parameter_by_id(self, param_id: str) -> Optional[ModificationParameter]:
        """Get parameter by ID from current parameters"""
        # Implementation would search through identified parameters
        return None
    
    def get_modification_summary(self) -> pd.DataFrame:
        """Get summary of all modifications as DataFrame"""
        if not self.modifications_log:
            return pd.DataFrame()
            
        records = []
        for log in self.modifications_log:
            for param_id, new_value in log['modifications'].items():
                records.append({
                    'scenario_id': log['scenario_id'],
                    'category': log['category'],
                    'parameter': param_id,
                    'new_value': new_value,
                    'timestamp': log['timestamp']
                })
                
        return pd.DataFrame(records)
    
    @staticmethod
    def create_parameter_id(object_type: str, object_name: str, field_name: str) -> str:
        """Create unique parameter ID"""
        return f"{object_type}::{object_name}::{field_name}"
    
    @staticmethod
    def parse_parameter_id(param_id: str) -> Tuple[str, str, str]:
        """Parse parameter ID into components"""
        parts = param_id.split("::")
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
        return "", "", ""
    
    def apply_multiplier(self, current_value: float, multiplier: float, 
                        min_val: float = None, max_val: float = None) -> float:
        """Apply multiplier with optional bounds"""
        new_value = current_value * multiplier
        
        if min_val is not None:
            new_value = max(new_value, min_val)
        if max_val is not None:
            new_value = min(new_value, max_val)
            
        return new_value
    
    def apply_offset(self, current_value: float, offset: float,
                    min_val: float = None, max_val: float = None) -> float:
        """Apply offset with optional bounds"""
        new_value = current_value + offset
        
        if min_val is not None:
            new_value = max(new_value, min_val)
        if max_val is not None:
            new_value = min(new_value, max_val)
            
        return new_value
    
    def sample_range(self, min_val: float, max_val: float, 
                    n_samples: int, method: str = 'uniform') -> List[float]:
        """Sample values from range using specified method"""
        if method == 'uniform':
            return list(np.random.uniform(min_val, max_val, n_samples))
        elif method == 'linspace':
            return list(np.linspace(min_val, max_val, n_samples))
        elif method == 'normal':
            mean = (min_val + max_val) / 2
            std = (max_val - min_val) / 6  # 99.7% within range
            samples = np.random.normal(mean, std, n_samples)
            # Clip to range
            return list(np.clip(samples, min_val, max_val))
        else:
            raise ValueError(f"Unknown sampling method: {method}")
