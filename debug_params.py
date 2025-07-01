import joblib
import pandas as pd

# Load sensitivity results
sens_df = pd.read_parquet("/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99/sensitivity_results/sensitivity_results.parquet")
print("Top 5 sensitivity parameters:")
top_params = sens_df.nlargest(5, 'sensitivity_score')
for _, row in top_params.iterrows():
    print(f"  {row['parameter']} (score: {row['sensitivity_score']:.2f})")

# Load model data
model_data = joblib.load("/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99/surrogate_models/surrogate_model.joblib")
feature_cols = model_data['feature_columns']

print("\nSome surrogate model features:")
for col in feature_cols[:10]:
    print(f"  {col}")

print("\nMatching example:")
# Try to match sensitivity parameter to feature column
sens_param = "shading*WINDOWSHADINGCONTROL*ShadingCtrl_Zone1_FrontPerimeter_Wall_0_window*Setpoint"
print(f"Sensitivity param: {sens_param}")

# Check for matches
for col in feature_cols:
    if "shading" in col.lower() and "setpoint" in col.lower() and "zone1" in col.lower():
        print(f"Potential match: {col}")
        break