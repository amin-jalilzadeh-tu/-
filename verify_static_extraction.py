import pandas as pd
from pathlib import Path

# Check sample outputs
test_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/test_static_extraction")

print("STATIC EXTRACTION OUTPUT VERIFICATION")
print("=" * 60)

# 1. Energy End Uses
print("\n1. ENERGY END USES")
df = pd.read_parquet(test_dir / "performance_summaries" / "energy_end_uses.parquet")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print("\nSample data:")
print(df.head())

# 2. Zone Sizing
print("\n\n2. ZONE SIZING")
df = pd.read_parquet(test_dir / "sizing_results" / "zone_sizing.parquet")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print("\nSample data:")
print(df.head())

# 3. Zone Properties
print("\n\n3. ZONE PROPERTIES")
df = pd.read_parquet(test_dir / "building_characteristics" / "zone_properties.parquet")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print("\nSample data:")
print(df.head())

# 4. Check all created files
print("\n\nALL CREATED FILES:")
print("-" * 60)
for parquet_file in test_dir.rglob("*.parquet"):
    rel_path = parquet_file.relative_to(test_dir)
    file_size = parquet_file.stat().st_size
    df = pd.read_parquet(parquet_file)
    print(f"{rel_path}: {len(df)} rows, {file_size:,} bytes")