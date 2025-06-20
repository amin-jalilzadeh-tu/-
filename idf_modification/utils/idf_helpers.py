"""
IDF manipulation helper utilities

This module provides functions to:
- Get and set IDF object fields
- Add and remove objects
- Find and copy objects
- Parse IDF values
"""

import copy
from typing import Any, List, Optional, Dict, Union, Tuple
from eppy.modeleditor import IDF
import logging

logger = logging.getLogger(__name__)


def get_idf_object(idf: IDF, object_type: str, object_name: str) -> Optional[Any]:
    """
    Get an IDF object by type and name
    
    Args:
        idf: The IDF file
        object_type: Type of the object (e.g., 'Zone', 'Material')
        object_name: Name of the object
        
    Returns:
        The IDF object or None if not found
    """
    try:
        object_type_upper = object_type.upper()
        
        if object_type_upper in idf.idfobjects:
            for obj in idf.idfobjects[object_type_upper]:
                if hasattr(obj, 'Name') and obj.Name == object_name:
                    return obj
                # Some objects use different name fields
                elif hasattr(obj, 'Zone_Name') and obj.Zone_Name == object_name:
                    return obj
                elif len(obj.obj) > 1 and obj.obj[1] == object_name:
                    return obj
    except Exception as e:
        logger.error(f"Error getting IDF object: {e}")
    
    return None


def get_idf_objects_by_type(idf: IDF, object_type: str) -> List[Any]:
    """
    Get all IDF objects of a specific type
    
    Args:
        idf: The IDF file
        object_type: Type of objects to retrieve
        
    Returns:
        List of IDF objects
    """
    try:
        object_type_upper = object_type.upper()
        if object_type_upper in idf.idfobjects:
            return list(idf.idfobjects[object_type_upper])
    except Exception as e:
        logger.error(f"Error getting IDF objects by type: {e}")
    
    return []


def set_idf_object_field(idf_object: Any, field_name: str, value: Any) -> bool:
    """
    Set a field value in an IDF object
    
    Args:
        idf_object: The IDF object to modify
        field_name: Name of the field to set
        value: Value to set
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Try setting as attribute first
        if hasattr(idf_object, field_name):
            setattr(idf_object, field_name, value)
            return True
        
        # Try setting by field index
        field_idx = get_field_index(idf_object, field_name)
        if field_idx is not None:
            idf_object.obj[field_idx] = value
            return True
            
        logger.warning(f"Field '{field_name}' not found in object")
        return False
        
    except Exception as e:
        logger.error(f"Error setting field '{field_name}': {e}")
        return False


def add_idf_object(idf: IDF, object_type: str, **kwargs) -> Optional[Any]:
    """
    Add a new object to the IDF
    
    Args:
        idf: The IDF file
        object_type: Type of object to add
        **kwargs: Field values for the new object
        
    Returns:
        The created object or None if failed
    """
    try:
        object_type_upper = object_type.upper()
        
        # Create the new object
        new_obj = idf.newidfobject(object_type_upper)
        
        # Set field values
        for field_name, value in kwargs.items():
            if hasattr(new_obj, field_name):
                setattr(new_obj, field_name, value)
        
        return new_obj
        
    except Exception as e:
        logger.error(f"Error adding IDF object: {e}")
        return None


def remove_idf_object(idf: IDF, idf_object: Any) -> bool:
    """
    Remove an object from the IDF
    
    Args:
        idf: The IDF file
        idf_object: The object to remove
        
    Returns:
        True if successful, False otherwise
    """
    try:
        object_type = idf_object.obj[0].upper()
        
        if object_type in idf.idfobjects:
            idf.idfobjects[object_type].remove(idf_object)
            return True
            
    except Exception as e:
        logger.error(f"Error removing IDF object: {e}")
    
    return False


def copy_idf_object(idf: IDF, idf_object: Any, new_name: str) -> Optional[Any]:
    """
    Create a copy of an IDF object with a new name
    
    Args:
        idf: The IDF file
        idf_object: The object to copy
        new_name: Name for the new object
        
    Returns:
        The copied object or None if failed
    """
    try:
        object_type = idf_object.obj[0]
        
        # Create new object
        new_obj = idf.newidfobject(object_type)
        
        # Copy all fields
        for i, value in enumerate(idf_object.obj[1:], start=1):
            if i < len(new_obj.obj):
                new_obj.obj[i] = value
        
        # Set new name
        if hasattr(new_obj, 'Name'):
            new_obj.Name = new_name
        elif len(new_obj.obj) > 1:
            new_obj.obj[1] = new_name
        
        return new_obj
        
    except Exception as e:
        logger.error(f"Error copying IDF object: {e}")
        return None


def find_referenced_objects(idf: IDF, idf_object: Any) -> Dict[str, List[Any]]:
    """
    Find all objects that reference the given object
    
    Args:
        idf: The IDF file
        idf_object: The object to find references to
        
    Returns:
        Dictionary mapping object types to lists of referencing objects
    """
    references = {}
    
    try:
        # Get the name of the object
        obj_name = None
        if hasattr(idf_object, 'Name'):
            obj_name = idf_object.Name
        elif len(idf_object.obj) > 1:
            obj_name = idf_object.obj[1]
        
        if not obj_name:
            return references
        
        # Search all objects for references
        for obj_type in idf.idfobjects:
            for obj in idf.idfobjects[obj_type]:
                # Check all fields for references
                for i, value in enumerate(obj.obj[1:], start=1):
                    if value == obj_name and obj != idf_object:
                        if obj_type not in references:
                            references[obj_type] = []
                        if obj not in references[obj_type]:
                            references[obj_type].append(obj)
                        break
                
                # Check named attributes
                for attr in dir(obj):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(obj, attr)
                            if value == obj_name and obj != idf_object:
                                if obj_type not in references:
                                    references[obj_type] = []
                                if obj not in references[obj_type]:
                                    references[obj_type].append(obj)
                                break
                        except:
                            pass
    
    except Exception as e:
        logger.error(f"Error finding references: {e}")
    
    return references


def get_object_field_names(idf_object: Any) -> List[str]:
    """
    Get all field names for an IDF object
    
    Args:
        idf_object: The IDF object
        
    Returns:
        List of field names
    """
    field_names = []
    
    try:
        # Get field names from object definition
        if hasattr(idf_object, 'fieldnames'):
            field_names = list(idf_object.fieldnames)
        
        # Also check for additional attributes
        for attr in dir(idf_object):
            if not attr.startswith('_') and attr not in ['obj', 'objidd']:
                if hasattr(idf_object, attr) and attr not in field_names:
                    field_names.append(attr)
    
    except Exception as e:
        logger.error(f"Error getting field names: {e}")
    
    return field_names


def get_field_index(idf_object: Any, field_name: str) -> Optional[int]:
    """
    Get the index of a field in an IDF object
    
    Args:
        idf_object: The IDF object
        field_name: Name of the field
        
    Returns:
        Field index or None if not found
    """
    try:
        if hasattr(idf_object, 'fieldnames'):
            field_names = idf_object.fieldnames
            if field_name in field_names:
                return field_names.index(field_name)
        
        # Check if it's a valid attribute
        if hasattr(idf_object, field_name):
            # Try to find its position in obj
            value = getattr(idf_object, field_name)
            for i, obj_value in enumerate(idf_object.obj):
                if obj_value == value:
                    return i
    
    except Exception as e:
        logger.error(f"Error getting field index: {e}")
    
    return None


def parse_idf_value(value: str) -> Union[float, int, str]:
    """
    Parse an IDF value to appropriate Python type
    
    Args:
        value: String value from IDF
        
    Returns:
        Parsed value (float, int, or string)
    """
    if value is None or value == '':
        return value
    
    # Try to parse as number
    try:
        # Check if it's an integer
        if '.' not in str(value):
            return int(value)
        else:
            return float(value)
    except ValueError:
        # Return as string
        return str(value)


def get_object_info(idf_object: Any) -> Dict[str, Any]:
    """
    Get detailed information about an IDF object
    
    Args:
        idf_object: The IDF object
        
    Returns:
        Dictionary with object information
    """
    info = {
        'type': idf_object.obj[0] if idf_object.obj else 'Unknown',
        'fields': {},
        'raw_data': list(idf_object.obj)
    }
    
    try:
        # Get all field values
        field_names = get_object_field_names(idf_object)
        for field_name in field_names:
            if hasattr(idf_object, field_name):
                value = getattr(idf_object, field_name)
                info['fields'][field_name] = value
        
        # Add name if available
        if hasattr(idf_object, 'Name'):
            info['name'] = idf_object.Name
        elif len(idf_object.obj) > 1:
            info['name'] = idf_object.obj[1]
    
    except Exception as e:
        logger.error(f"Error getting object info: {e}")
    
    return info


def compare_objects(obj1: Any, obj2: Any) -> Dict[str, Tuple[Any, Any]]:
    """
    Compare two IDF objects and return differences
    
    Args:
        obj1: First IDF object
        obj2: Second IDF object
        
    Returns:
        Dictionary of field differences {field: (value1, value2)}
    """
    differences = {}
    
    try:
        # Get all fields from both objects
        fields1 = set(get_object_field_names(obj1))
        fields2 = set(get_object_field_names(obj2))
        all_fields = fields1.union(fields2)
        
        for field in all_fields:
            val1 = getattr(obj1, field, None) if hasattr(obj1, field) else None
            val2 = getattr(obj2, field, None) if hasattr(obj2, field) else None
            
            if val1 != val2:
                differences[field] = (val1, val2)
    
    except Exception as e:
        logger.error(f"Error comparing objects: {e}")
    
    return differences