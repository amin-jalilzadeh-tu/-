import joblib

# Check main model
model_main = joblib.load("/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99/surrogate_models/surrogate_model.joblib")
print("Main model type:", type(model_main))
print("Main model:", model_main)

# Check v1.0 model
model_v1 = joblib.load("/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99/surrogate_models/v1.0/surrogate_model.joblib")
print("\nV1.0 model type:", type(model_v1))

# Check scaler
scaler = joblib.load("/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99/surrogate_models/v1.0/feature_scaler.joblib")
print("\nScaler type:", type(scaler))