"""
SQL Table Data Extractor for EnergyPlus Databases
Extracts valuable data from non-timeseries SQL tables
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any

class SQLTableExtractor:
    """Extract data from EnergyPlus SQL database tables"""
    
    def __init__(self, sql_path: Path):
        """Initialize with SQL database path"""
        self.sql_path = sql_path
        self.conn = sqlite3.connect(str(sql_path))
        
    def get_available_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
        """
        tables = pd.read_sql_query(query, self.conn)
        return tables['name'].tolist()
    
    def extract_tabular_data(self) -> pd.DataFrame:
        """
        Extract TabularData table containing pre-calculated summary reports
        This includes Annual Building Utility Performance Summary, 
        Equipment Summary, HVAC Sizing Summary, etc.
        """
        query = """
        SELECT 
            ReportName,
            ReportForString,
            TableName,
            ColumnName,
            RowName,
            Value,
            Units
        FROM TabularData
        ORDER BY ReportName, TableName, RowName, ColumnName
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_component_sizes(self) -> pd.DataFrame:
        """
        Extract ComponentSizes table containing equipment sizing information
        Includes design capacities, flow rates, and sizing criteria
        """
        query = """
        SELECT 
            CompType,
            CompName,
            Description,
            Value,
            Units
        FROM ComponentSizes
        ORDER BY CompType, CompName
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_system_sizes(self) -> pd.DataFrame:
        """
        Extract SystemSizes table containing HVAC system sizing results
        """
        query = """
        SELECT * FROM SystemSizes
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_zone_sizes(self) -> pd.DataFrame:
        """
        Extract ZoneSizes table containing zone-level sizing information
        """
        query = """
        SELECT * FROM ZoneSizes
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_zones(self) -> pd.DataFrame:
        """
        Extract Zones table containing zone geometry and properties
        Includes areas, volumes, multipliers, and coordinates
        """
        query = """
        SELECT 
            ZoneName,
            ZoneIndex,
            Area,
            Volume,
            Multiplier,
            ListMultiplier,
            MinimumX,
            MaximumX,
            MinimumY,
            MaximumY,
            MinimumZ,
            MaximumZ,
            CeilingHeight,
            IsPartOfTotalArea
        FROM Zones
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_surfaces(self) -> pd.DataFrame:
        """
        Extract Surfaces table containing detailed surface information
        Includes areas, orientations, constructions, and boundary conditions
        """
        query = """
        SELECT 
            SurfaceName,
            SurfaceIndex,
            Area,
            Azimuth,
            Tilt,
            Width,
            Height,
            Reveal,
            ConstructionIndex,
            ClassName,
            EnclosureIndex,
            ZoneIndex,
            ExtBoundCondObjectIndex
        FROM Surfaces
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_constructions(self) -> pd.DataFrame:
        """
        Extract Constructions table containing construction assemblies
        """
        query = """
        SELECT 
            ConstructionIndex,
            Name,
            TotalLayers,
            TotalSolidLayers,
            TotalGlassLayers,
            InsideAbsorptance,
            OutsideAbsorptance,
            InsideRoughness,
            OutsideRoughness,
            TypeIsWindow,
            Uvalue
        FROM Constructions
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_materials(self) -> pd.DataFrame:
        """
        Extract Materials table containing material properties
        """
        query = """
        SELECT 
            MaterialIndex,
            Name,
            MaterialType,
            Thickness,
            Conductivity,
            Density,
            SpecificHeat,
            Roughness,
            ThermalAbsorptance,
            SolarAbsorptance,
            VisibleAbsorptance
        FROM Materials
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_schedules(self) -> pd.DataFrame:
        """
        Extract Schedules table containing schedule definitions
        """
        query = """
        SELECT 
            ScheduleIndex,
            ScheduleName,
            ScheduleType,
            ScheduleMinimum,
            ScheduleMaximum
        FROM Schedules
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_errors(self) -> pd.DataFrame:
        """
        Extract Errors table containing simulation warnings and errors
        """
        query = """
        SELECT 
            ErrorIndex,
            ErrorMessage,
            ErrorType,
            Count
        FROM Errors
        ORDER BY ErrorType, Count DESC
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_nominal_people(self) -> pd.DataFrame:
        """
        Extract NominalPeople table containing occupancy design loads
        """
        query = """
        SELECT 
            ObjectIndex,
            ObjectName,
            ZoneIndex,
            NumberOfPeople,
            NumberOfPeopleScheduleIndex,
            ActivityLevelScheduleIndex,
            FractionRadiant,
            FractionConvected,
            UserSpecifiedSensibleFraction
        FROM NominalPeople
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_nominal_lighting(self) -> pd.DataFrame:
        """
        Extract NominalLighting table containing lighting design loads
        """
        query = """
        SELECT 
            ObjectIndex,
            ObjectName,
            ZoneIndex,
            ScheduleIndex,
            DesignLevel,
            FractionReturnAir,
            FractionRadiant,
            FractionShortWave,
            FractionReplaceable,
            FractionConvected
        FROM NominalLighting
        """
        try:
            return pd.read_sql_query(query, self.conn)
        except:
            return pd.DataFrame()
    
    def extract_all_tables(self) -> Dict[str, pd.DataFrame]:
        """Extract all valuable tables from the SQL database"""
        tables = {
            'tabular_data': self.extract_tabular_data(),
            'component_sizes': self.extract_component_sizes(),
            'system_sizes': self.extract_system_sizes(),
            'zone_sizes': self.extract_zone_sizes(),
            'zones': self.extract_zones(),
            'surfaces': self.extract_surfaces(),
            'constructions': self.extract_constructions(),
            'materials': self.extract_materials(),
            'schedules': self.extract_schedules(),
            'errors': self.extract_errors(),
            'nominal_people': self.extract_nominal_people(),
            'nominal_lighting': self.extract_nominal_lighting()
        }
        
        # Filter out empty tables
        return {k: v for k, v in tables.items() if not v.empty}
    
    def close(self):
        """Close database connection"""
        self.conn.close()


# Example usage and analysis of what each table provides
if __name__ == "__main__":
    # Example path - replace with actual SQL file
    sql_path = Path("path/to/simulation.sql")
    
    if sql_path.exists():
        extractor = SQLTableExtractor(sql_path)
        
        # Get all available tables
        available_tables = extractor.get_available_tables()
        print(f"Available tables: {available_tables}")
        
        # Extract all valuable tables
        all_tables = extractor.extract_all_tables()
        
        # Analyze each table
        for table_name, df in all_tables.items():
            print(f"\n{table_name.upper()} Table:")
            print(f"  Rows: {len(df)}")
            print(f"  Columns: {list(df.columns)}")
            
            # Show sample data
            if len(df) > 0:
                print(f"  Sample data:")
                print(df.head(3))
        
        extractor.close()