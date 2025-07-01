import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path

def analyze_parquet_structure(parquet_path):
    """Analyze the structure of a parquet file"""
    # Read parquet file
    df = pd.read_parquet(parquet_path)
    
    # Get schema
    parquet_file = pq.ParquetFile(parquet_path)
    schema = parquet_file.schema
    
    print(f"\nFile: {Path(parquet_path).name}")
    print("=" * 60)
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print("\nColumn Details:")
    for col in df.columns:
        print(f"  {col}: {df[col].dtype}")
    
    print("\nSample Data (first 3 rows):")
    print(df.head(3))
    
    return df

# Analyze different types of parquet files
print("PARQUET STRUCTURE ANALYSIS")
print("=" * 80)

# 1. Timeseries data
print("\n1. TIMESERIES DATA")
try:
    df = analyze_parquet_structure("/mnt/d/Documents/daily/E_Plus_2040_py/output/0aeab342-dea7-4def-89fa-0ef389ff4f09/parsed_data/timeseries/base_all_daily.parquet")
except Exception as e:
    print(f"Error: {e}")

# 2. IDF Category data
print("\n\n2. IDF CATEGORY DATA - Equipment")
try:
    df = analyze_parquet_structure("/mnt/d/Documents/daily/E_Plus_2040_py/output/0aeab342-dea7-4def-89fa-0ef389ff4f09/parsed_data/idf_data/by_category/equipment.parquet")
except Exception as e:
    print(f"Error: {e}")

# 3. Building snapshot
print("\n\n3. BUILDING SNAPSHOT")
try:
    df = analyze_parquet_structure("/mnt/d/Documents/daily/E_Plus_2040_py/output/0aeab342-dea7-4def-89fa-0ef389ff4f09/parsed_data/idf_data/by_building/4136733_snapshot.parquet")
except Exception as e:
    print(f"Error: {e}")

# 4. Metadata
print("\n\n4. METADATA - Building Registry")
try:
    df = analyze_parquet_structure("/mnt/d/Documents/daily/E_Plus_2040_py/output/0aeab342-dea7-4def-89fa-0ef389ff4f09/parsed_data/metadata/building_registry.parquet")
except Exception as e:
    print(f"Error: {e}")

# 5. Comparison data
print("\n\n5. COMPARISON DATA")
try:
    df = analyze_parquet_structure("/mnt/d/Documents/daily/E_Plus_2040_py/output/0aeab342-dea7-4def-89fa-0ef389ff4f09/parsed_modified_results/comparisons/var_electricity_facility_na_daily_b4136733.parquet")
except Exception as e:
    print(f"Error: {e}")