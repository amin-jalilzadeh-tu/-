"""
Compatibility module for backward compatibility
This module re-exports the separated data managers
"""

from .idf_data_manager import IDFDataManager
from .sql_data_manager import SQLDataManager

# Alias for backward compatibility
EnhancedHierarchicalDataManager = IDFDataManager

# If there were any shared functions, re-export them here