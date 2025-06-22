"""
Data classes for IDF parsing and modification system
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum


class ModificationStatus(Enum):
    """Status of a modification"""
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    VALIDATED = "validated"
    REJECTED = "rejected"


class ChangeType(Enum):
    """Type of change made to a parameter"""
    ABSOLUTE = "absolute"
    PERCENTAGE = "percentage"
    RELATIVE = "relative"
    REPLACEMENT = "replacement"


@dataclass
class IDFParameter:
    """Represents a single parameter in an IDF object"""
    field_name: Optional[str] = None
    field_index: int = 0
    value: str = ""
    numeric_value: Optional[float] = None
    units: Optional[str] = None
    comment: Optional[str] = None
    
    def __post_init__(self):
        """Try to parse numeric value if not provided"""
        if self.numeric_value is None and self.value:
            try:
                self.numeric_value = float(self.value)
            except (ValueError, TypeError):
                pass


@dataclass
class IDFObject:
    """Represents a complete IDF object"""
    object_type: str
    name: str = ""
    parameters: List[IDFParameter] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)
    line_number: Optional[int] = None
    
    def get_parameter(self, field_name: str) -> Optional[IDFParameter]:
        """Get parameter by field name"""
        for param in self.parameters:
            if param.field_name == field_name:
                return param
        return None
    
    def get_parameter_by_index(self, index: int) -> Optional[IDFParameter]:
        """Get parameter by index"""
        if 0 <= index < len(self.parameters):
            return self.parameters[index]
        return None


@dataclass
class BuildingData:
    """Container for all parsed building data"""
    building_id: str
    file_path: str
    objects: Dict[str, List[IDFObject]] = field(default_factory=dict)
    version: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_objects_by_type(self, object_type: str) -> List[IDFObject]:
        """Get all objects of a specific type"""
        return self.objects.get(object_type, [])
    
    def add_object(self, obj: IDFObject):
        """Add an object to the building data"""
        if obj.object_type not in self.objects:
            self.objects[obj.object_type] = []
        self.objects[obj.object_type].append(obj)


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
    default_value: Optional[Any] = None
    description: Optional[str] = None
    performance_impact: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def validate_value(self, value: Any) -> bool:
        """Validate if a value is within acceptable range"""
        if self.data_type == float or self.data_type == int:
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
        return True


@dataclass
class Modification:
    """Represents a single modification to an IDF parameter"""
    # Identity
    building_id: str
    variant_id: str
    category: str
    
    # Target
    object_type: str
    object_name: str
    parameter: str
    
    # Change details
    original_value: Any
    new_value: Any
    change_type: ChangeType = ChangeType.ABSOLUTE
    change_percentage: Optional[float] = None
    
    # Metadata
    rule_applied: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Status
    success: bool = False
    validation_status: ModificationStatus = ModificationStatus.PENDING
    message: Optional[str] = None
    
    def apply_to_parameter(self, param: IDFParameter) -> bool:
        """Apply this modification to a parameter"""
        try:
            param.value = str(self.new_value)
            if isinstance(self.new_value, (int, float)):
                param.numeric_value = float(self.new_value)
            self.success = True
            self.validation_status = ModificationStatus.APPLIED
            return True
        except Exception as e:
            self.success = False
            self.validation_status = ModificationStatus.FAILED
            self.message = str(e)
            return False


@dataclass
class ModificationResult:
    """Result of applying modifications"""
    building_id: str
    variant_id: str
    total_attempted: int = 0
    total_successful: int = 0
    total_failed: int = 0
    modifications: List[Modification] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    output_file: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_attempted == 0:
            return 0.0
        return self.total_successful / self.total_attempted * 100


@dataclass
class VariantInfo:
    """Information about a building variant"""
    variant_id: str
    building_id: str
    base_idf_path: str
    modified_idf_path: Optional[str] = None
    modifications_applied: int = 0
    creation_time: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
