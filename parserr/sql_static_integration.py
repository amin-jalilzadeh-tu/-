"""
Integration module for static SQL data extraction
Add this to your existing parsing workflow
"""

from pathlib import Path
from typing import Optional
import logging
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sql_static_extractor import SQLStaticExtractor

logger = logging.getLogger(__name__)


class EnhancedSQLParser:
    """
    Enhanced SQL parser that includes static data extraction
    This can be integrated into your existing SQL parsing workflow
    """
    
    def __init__(self, existing_sql_analyzer):
        """
        Initialize with existing SQL analyzer
        
        Args:
            existing_sql_analyzer: Your existing SQL analyzer instance
        """
        self.sql_analyzer = existing_sql_analyzer
        self.sql_path = existing_sql_analyzer.sql_path
        self.building_id = existing_sql_analyzer.building_id
        self.variant_id = existing_sql_analyzer.variant_id
        
    def extract_all_data(self, output_dir: Path, extract_timeseries: bool = True, 
                        extract_static: bool = True):
        """
        Extract both timeseries and static data
        
        Args:
            output_dir: Output directory
            extract_timeseries: Whether to extract timeseries (default True)
            extract_static: Whether to extract static data (default True)
        """
        # Extract timeseries using existing method
        if extract_timeseries:
            logger.info("Extracting timeseries data...")
            # Use your existing method
            timeseries_data = self.sql_analyzer.extract_timeseries()
            # Process as before...
        
        # Extract static data using new extractor
        if extract_static:
            logger.info("Extracting static data...")
            static_extractor = SQLStaticExtractor(
                self.sql_path,
                output_dir,
                self.building_id,
                self.variant_id
            )
            try:
                static_extractor.extract_all()
            finally:
                static_extractor.close()
                
        logger.info("Complete SQL extraction finished")


def add_static_extraction_to_existing_workflow(sql_analyzer_instance, output_dir: Path):
    """
    Simple function to add static extraction to your existing workflow
    Call this after creating your SQL analyzer instance
    
    Args:
        sql_analyzer_instance: Your existing SQL analyzer
        output_dir: Where to save the static data
    
    Example:
        # Your existing code
        sql_analyzer = EnhancedSQLAnalyzer(sql_path, data_manager)
        
        # Add static extraction
        add_static_extraction_to_existing_workflow(sql_analyzer, parsed_data_dir)
    """
    static_extractor = SQLStaticExtractor(
        sql_analyzer_instance.sql_path,
        output_dir,
        sql_analyzer_instance.building_id,
        sql_analyzer_instance.variant_id
    )
    
    try:
        static_extractor.extract_all()
        logger.info(f"Static data extraction complete for {sql_analyzer_instance.building_id}")
    except Exception as e:
        logger.error(f"Failed to extract static data: {e}")
    finally:
        static_extractor.close()


# Modification for your existing parse_sql.py or similar file
def enhanced_parse_sql_results(sql_path: Path, output_base_dir: Path, 
                              building_id: str, variant_id: str = 'base',
                              is_modified: bool = False):
    """
    Enhanced SQL parsing that includes static data
    This can replace or supplement your existing parse_sql_results function
    """
    from parserr.sql_analyzer import EnhancedSQLAnalyzer
    from parserr.sql_data_manager import SQLDataManager
    
    # Determine output directory
    if is_modified:
        output_dir = output_base_dir / 'parsed_modified_results'
    else:
        output_dir = output_base_dir / 'parsed_data'
    
    # Your existing timeseries extraction
    data_manager = SQLDataManager(output_dir)
    sql_analyzer = EnhancedSQLAnalyzer(
        sql_path, 
        data_manager,
        is_modified_results=is_modified
    )
    
    # Extract timeseries as before
    timeseries_data = sql_analyzer.extract_timeseries()
    # ... process timeseries ...
    
    # NEW: Add static extraction
    logger.info(f"Adding static data extraction for {building_id}")
    static_extractor = SQLStaticExtractor(
        sql_path,
        output_dir,
        building_id,
        variant_id
    )
    
    try:
        static_extractor.extract_all()
    finally:
        static_extractor.close()
    
    return True