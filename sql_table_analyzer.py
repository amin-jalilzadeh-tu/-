import sqlite3
import pandas as pd
from pathlib import Path
import json

def analyze_sql_tables(sql_path):
    """Analyze all tables in an EnergyPlus SQL file"""
    conn = sqlite3.connect(sql_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [table[0] for table in cursor.fetchall()]
    
    analysis = {}
    
    for table in tables:
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]
        
        # Get sample data if not too large
        sample_data = None
        if row_count > 0 and row_count < 1000:
            cursor.execute(f"SELECT * FROM {table} LIMIT 10")
            sample_data = cursor.fetchall()
        
        analysis[table] = {
            'columns': [{'name': col[1], 'type': col[2]} for col in columns],
            'row_count': row_count,
            'sample_data': sample_data
        }
    
    conn.close()
    return analysis

def analyze_tabular_data(sql_path):
    """Specifically analyze TabularData table"""
    conn = sqlite3.connect(sql_path)
    
    # First check the TabularData structure
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(TabularData)")
    columns = cursor.fetchall()
    print("\nTabularData columns:", [col[1] for col in columns])
    
    # Get sample data
    query = """
    SELECT * FROM TabularData LIMIT 20
    """
    df = pd.read_sql_query(query, conn)
    
    # Also get the string values
    strings_query = """
    SELECT s.StringIndex, s.Value, st.Value as StringType
    FROM Strings s
    JOIN StringTypes st ON s.StringTypeIndex = st.StringTypeIndex
    WHERE st.Value IN ('ReportName', 'TableName', 'ColumnName', 'RowName')
    """
    strings_df = pd.read_sql_query(strings_query, conn)
    
    conn.close()
    return df, strings_df

# Example usage
if __name__ == "__main__":
    sql_path = "/mnt/d/Documents/daily/E_Plus_2040_py/output/0aeab342-dea7-4def-89fa-0ef389ff4f09/Modified_Sim_Results/2020/simulation_bldg0_4136733.sql"
    
    # Analyze all tables
    analysis = analyze_sql_tables(sql_path)
    
    # Print summary
    print("SQL TABLE ANALYSIS SUMMARY")
    print("=" * 50)
    for table, info in analysis.items():
        print(f"\n{table}:")
        print(f"  Rows: {info['row_count']}")
        print(f"  Columns: {[col['name'] for col in info['columns']]}")
    
    # Analyze TabularData specifically
    print("\n\nTABULAR DATA REPORTS:")
    print("=" * 50)
    tabular_df, strings_df = analyze_tabular_data(sql_path)
    print("\nSample TabularData rows:")
    print(tabular_df.head(10))
    print("\nString mappings:")
    print(strings_df.head(20))