import pandas as pd

# Check the actual file structure
file_path = "/mnt/d/Documents/daily/E_Plus_2040_py/output/38eb2e7b-709d-43ec-9635-18a7288d7540/parsed_modified_results/comparisons/var_electricity_facility_na_yearly_from_monthly_b4136733.parquet"

df = pd.read_parquet(file_path)
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print("\nFirst row:")
print(df.iloc[0])
print("\nData sample:")
print(df)