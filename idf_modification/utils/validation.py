"""
Validation utilities for IDF modifications

This module provides functions to validate:
- Modification parameters and values
- IDF object consistency
- Field values and types
- Object references and dependencies
"""

import re
from typing import Dict, List, Any, Optional, Union, Tuple
from eppy.modeleditor import IDF
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


# Field type patterns
NUMERIC_PATTERN = re.compile(r'^-?\d+\.?\d*$')
INTEGER_PATTERN = re.compile(r'^-?\d+$')
ALPHA_PATTERN = re.compile(r'^[A-Za-z]+$')
CHOICE_PATTERN = re.compile(r'^[A-Za-z0-9_\-\s]+$')


def validate_modification(modification: Dict[str, Any], 
                         parameter_registry: Optional[Dict] = None) -> Tuple[bool, List[str]]:
    """
    Validate a modification dictionary
    
    Args:
        modification: Dictionary containing modification details
        parameter_registry: Optional registry of valid parameters
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    # Check required fields
    required_fields = ['object_type', 'object_name', 'field', 'value']
    for field in required_fields:
        if field not in modification:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return False, errors
    
    # Validate object type
    if not isinstance(modification['object_type'], str):
        errors.append("Object type must be a string")
    
    # Validate field name
    if not isinstance(modification['field'], str):
        errors.append("Field name must be a string")
    
    # Check parameter registry if provided
    if parameter_registry:
        obj_type = modification['object_type']
        field = modification['field']
        
        if obj_type in parameter_registry:
            if field not in parameter_registry[obj_type].get('fields', {}):
                errors.append(f"Field '{field}' not valid for object type '{obj_type}'")
            else:
                # Validate value against parameter constraints
                field_info = parameter_registry[obj_type]['fields'][field]
                value_errors = validate_field_value(
                    modification['value'],
                    field_info.get('type'),
                    field_info.get('min'),
                    field_info.get('max'),
                    field_info.get('choices')
                )
                errors.extend(value_errors)
        else:
            errors.append(f"Unknown object type: {obj_type}")
    
    return len(errors) == 0, errors


def validate_idf_object(idf_object: Any, idf: IDF) -> Tuple[bool, List[str]]:
    """
    Validate an IDF object for consistency
    
    Args:
        idf_object: The IDF object to validate
        idf: The IDF file containing the object
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    try:
        # Check object exists
        if idf_object is None:
            errors.append("IDF object is None")
            return False, errors
        
        # Get object type and validate fields
        obj_type = idf_object.obj[0].upper()
        
        # Check required fields are not empty
        if hasattr(idf_object, 'required_fields'):
            for field in idf_object.required_fields:
                if not getattr(idf_object, field, None):
                    errors.append(f"Required field '{field}' is empty")
        
        # Validate numeric fields
        if hasattr(idf_object, 'numeric_fields'):
            for field in idf_object.numeric_fields:
                value = getattr(idf_object, field, None)
                if value is not None and value != '':
                    try:
                        float(value)
                    except ValueError:
                        errors.append(f"Field '{field}' must be numeric, got: {value}")
        
        # Check object references
        ref_errors = validate_object_references(idf_object, idf)
        errors.extend(ref_errors)
        
    except Exception as e:
        errors.append(f"Error validating object: {str(e)}")
    
    return len(errors) == 0, errors


def validate_field_value(value: Any, 
                        field_type: Optional[str] = None,
                        min_value: Optional[float] = None,
                        max_value: Optional[float] = None,
                        choices: Optional[List[str]] = None) -> List[str]:
    """
    Validate a field value against constraints
    
    Args:
        value: The value to validate
        field_type: Expected type ('numeric', 'integer', 'alpha', 'choice', 'object-list')
        min_value: Minimum value for numeric fields
        max_value: Maximum value for numeric fields
        choices: List of valid choices for choice fields
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Type validation
    if field_type:
        if field_type == 'numeric':
            if not NUMERIC_PATTERN.match(str(value)):
                errors.append(f"Value must be numeric, got: {value}")
            else:
                num_val = float(value)
                if min_value is not None and num_val < min_value:
                    errors.append(f"Value {num_val} is below minimum {min_value}")
                if max_value is not None and num_val > max_value:
                    errors.append(f"Value {num_val} is above maximum {max_value}")
                    
        elif field_type == 'integer':
            if not INTEGER_PATTERN.match(str(value)):
                errors.append(f"Value must be an integer, got: {value}")
            else:
                int_val = int(value)
                if min_value is not None and int_val < min_value:
                    errors.append(f"Value {int_val} is below minimum {min_value}")
                if max_value is not None and int_val > max_value:
                    errors.append(f"Value {int_val} is above maximum {max_value}")
                    
        elif field_type == 'alpha':
            if not ALPHA_PATTERN.match(str(value)):
                errors.append(f"Value must contain only letters, got: {value}")
                
        elif field_type == 'choice' and choices:
            if str(value) not in choices:
                errors.append(f"Value must be one of {choices}, got: {value}")
    
    return errors


def validate_object_references(idf_object: Any, idf: IDF) -> List[str]:
    """
    Validate that object references exist in the IDF
    
    Args:
        idf_object: The IDF object to check
        idf: The IDF file to check references against
        
    Returns:
        List of error messages for missing references
    """
    errors = []
    
    try:
        # Common reference fields
        reference_fields = {
            'Zone_or_ZoneList_Name': 'ZONE',
            'Zone_Name': 'ZONE',
            'Schedule_Name': 'SCHEDULE:*',
            'Construction_Name': 'CONSTRUCTION',
            'Material_Name': 'MATERIAL:*',
            'Outside_Boundary_Object': None,  # Can be various types
            'Availability_Schedule_Name': 'SCHEDULE:*',
            'Heating_Coil_Name': '*:HEATING:*',
            'Cooling_Coil_Name': '*:COOLING:*',
            'Fan_Name': 'FAN:*',
            'Thermostat_Name': 'THERMOSTAT:*'
        }
        
        # Check each potential reference field
        for field_name, expected_type in reference_fields.items():
            if hasattr(idf_object, field_name):
                ref_name = getattr(idf_object, field_name)
                if ref_name and ref_name != '' and expected_type:
                    # Check if referenced object exists
                    if not find_object_by_name(idf, ref_name, expected_type):
                        errors.append(
                            f"Referenced {expected_type} '{ref_name}' "
                            f"in field '{field_name}' not found"
                        )
    
    except Exception as e:
        errors.append(f"Error checking references: {str(e)}")
    
    return errors


def find_object_by_name(idf: IDF, name: str, obj_type_pattern: str) -> bool:
    """
    Find an object by name and type pattern
    
    Args:
        idf: The IDF file to search
        name: Name of the object to find
        obj_type_pattern: Pattern for object type (can include wildcards)
        
    Returns:
        True if object found, False otherwise
    """
    try:
        # Handle wildcard patterns
        if '*' in obj_type_pattern:
            pattern = obj_type_pattern.replace('*', '.*')
            regex = re.compile(pattern, re.IGNORECASE)
            
            # Search all object types
            for obj_type in idf.idfobjects:
                if regex.match(obj_type):
                    objects = idf.idfobjects[obj_type]
                    for obj in objects:
                        if hasattr(obj, 'Name') and obj.Name == name:
                            return True
        else:
            # Direct type lookup
            if obj_type_pattern in idf.idfobjects:
                objects = idf.idfobjects[obj_type_pattern]
                for obj in objects:
                    if hasattr(obj, 'Name') and obj.Name == name:
                        return True
    
    except Exception:
        pass
    
    return False


def validate_modification_set(modifications: List[Dict[str, Any]], 
                            idf: IDF) -> Tuple[bool, List[str]]:
    """
    Validate a set of modifications for conflicts and dependencies
    
    Args:
        modifications: List of modification dictionaries
        idf: The IDF file to validate against
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    # Check for duplicate modifications to same field
    seen = set()
    for mod in modifications:
        key = (mod.get('object_type'), mod.get('object_name'), mod.get('field'))
        if key in seen:
            errors.append(
                f"Duplicate modification for {key[0]} '{key[1]}' field '{key[2]}'"
            )
        seen.add(key)
    
    # Check for conflicting modifications
    # (e.g., modifying a zone that's being deleted)
    deleted_objects = {
        (m['object_type'], m['object_name']) 
        for m in modifications 
        if m.get('action') == 'delete'
    }
    
    for mod in modifications:
        if mod.get('action') != 'delete':
            key = (mod['object_type'], mod['object_name'])
            if key in deleted_objects:
                errors.append(
                    f"Cannot modify {key[0]} '{key[1]}' - it's marked for deletion"
                )
    
    return len(errors) == 0, errors


def validate_scenario(scenario: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a modification scenario
    
    Args:
        scenario: Scenario dictionary containing modifications
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    # Check required scenario fields
    required = ['name', 'description', 'modifications']
    for field in required:
        if field not in scenario:
            errors.append(f"Scenario missing required field: {field}")
    
    if 'modifications' in scenario:
        if not isinstance(scenario['modifications'], list):
            errors.append("Scenario modifications must be a list")
        elif len(scenario['modifications']) == 0:
            errors.append("Scenario must contain at least one modification")
    
    return len(errors) == 0, errors