import sqlite3
import pandas as pd
from pathlib import Path

def analyze_tabular_reports(sql_path):
    """Analyze what reports are available in TabularData"""
    conn = sqlite3.connect(sql_path)
    
    # Get all unique report names
    query = """
    SELECT DISTINCT 
        s1.Value as ReportName,
        s2.Value as TableName,
        COUNT(*) as NumRows
    FROM TabularData td
    LEFT JOIN Strings s1 ON td.ReportNameIndex = s1.StringIndex
    LEFT JOIN Strings s2 ON td.TableNameIndex = s2.StringIndex
    GROUP BY s1.Value, s2.Value
    ORDER BY s1.Value, s2.Value
    """
    
    reports_df = pd.read_sql_query(query, conn)
    
    # Get specific examples of useful tables
    useful_tables = [
        'Site and Source Energy',
        'End Uses',
        'End Uses By Subcategory',
        'Utility Use Per Conditioned Floor Area',
        'Comfort and Setpoint Not Met Summary',
        'HVAC Sizing Summary',
        'Equipment Summary',
        'Envelope Summary',
        'Lighting Summary',
        'Peak Demand'
    ]
    
    for table_name in useful_tables:
        print(f"\n\n{'='*60}")
        print(f"TABLE: {table_name}")
        print('='*60)
        
        # Get a sample of data from this table
        data_query = f"""
        SELECT 
            s3.Value as RowName,
            s4.Value as ColumnName,
            s5.Value as Units,
            td.Value
        FROM TabularData td
        LEFT JOIN Strings s2 ON td.TableNameIndex = s2.StringIndex
        LEFT JOIN Strings s3 ON td.RowNameIndex = s3.StringIndex
        LEFT JOIN Strings s4 ON td.ColumnNameIndex = s4.StringIndex
        LEFT JOIN Strings s5 ON td.UnitsIndex = s5.StringIndex
        WHERE s2.Value = '{table_name}'
        LIMIT 20
        """
        
        try:
            sample_df = pd.read_sql_query(data_query, conn)
            if not sample_df.empty:
                print(sample_df.to_string(index=False))
            else:
                print(f"No data found for table: {table_name}")
        except Exception as e:
            print(f"Error querying table {table_name}: {e}")
    
    conn.close()
    
    print("\n\nALL AVAILABLE REPORTS AND TABLES:")
    print("="*60)
    print(reports_df.to_string(index=False))
    
    return reports_df

if __name__ == "__main__":
    sql_path = "/mnt/d/Documents/daily/E_Plus_2040_py/output/0aeab342-dea7-4def-89fa-0ef389ff4f09/Modified_Sim_Results/2020/simulation_bldg0_4136733.sql"
    analyze_tabular_reports(sql_path)