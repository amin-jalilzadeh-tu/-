"""
fix_directories.py - Ensure all required directories exist for the parser
"""
import os
from pathlib import Path


def fix_project_directories(project_path: str):
    """
    Ensure all required directories exist for the hierarchical data structure
    
    Args:
        project_path: Base path for the project data
    """
    project_path = Path(project_path)
    
    # Define all required directories
    directories = [
        'metadata',
        'idf_data/by_category',
        'idf_data/by_building',
        'sql_results/timeseries/hourly',
        'sql_results/timeseries/aggregated/daily',
        'sql_results/timeseries/aggregated/monthly',
        'sql_results/schedules',
        'sql_results/summary_metrics',
        'sql_results/output_validation',
        'relationships',
        'analysis_ready/feature_sets',
        'analysis_ready/output_analysis'
    ]
    
    # Create each directory
    for dir_path in directories:
        full_path = project_path / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
    
    # Create .gitkeep files to preserve empty directories
    for dir_path in directories:
        gitkeep_path = project_path / dir_path / '.gitkeep'
        if not gitkeep_path.exists():
            gitkeep_path.touch()
    
    return True