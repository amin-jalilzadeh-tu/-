# Docker Fix Instructions for Surrogate Modeling

## Quick Fix Steps

### 1. Identify Your Docker Container
```bash
docker ps
```
Look for your E_Plus container name.

### 2. Copy Fixed Files to Container

Option A: Use the provided script
```bash
chmod +x copy_fixes_to_docker.sh
./copy_fixes_to_docker.sh
```

Option B: Manual copy (replace `<container_name>` with your actual container name)
```bash
docker cp c_surrogate/surrogate_data_extractor.py <container_name>:/usr/src/app/c_surrogate/
docker cp c_surrogate/surrogate_pipeline_tracker.py <container_name>:/usr/src/app/c_surrogate/
docker cp c_surrogate/surrogate_data_consolidator.py <container_name>:/usr/src/app/c_surrogate/
docker cp c_surrogate/surrogate_data_preprocessor.py <container_name>:/usr/src/app/c_surrogate/
docker cp c_surrogate/unified_surrogate.py <container_name>:/usr/src/app/c_surrogate/
```

### 3. Add Target Variables to Config
Make sure your config includes target variables for the surrogate model:

```json
{
  "surrogate": {
    "enabled": true,
    "target_variable": [
      "electricity_facility_na_yearly_from_monthly",
      "heating_energytransfer_na_yearly_from_monthly",
      "cooling_energytransfer_na_yearly_from_monthly"
    ]
  }
}
```

## What Was Fixed

1. **Type Checking Issues**: Fixed multiple places where code assumed DataFrame but got dictionary
2. **Data Consolidation**: Added proper handling for comparison_outputs dictionary structure
3. **Pipeline Tracker**: Updated to handle both DataFrames and dictionaries properly

## Permanent Solution

To make these changes permanent, rebuild your Docker image:

```bash
docker-compose build
docker-compose up -d
```

## Verification

After applying fixes, check the surrogate export directory:
- `/output/<job_id>/surrogate_pipeline_export/`
- Should contain subdirectories: `1_inputs`, `2_extraction`, `3_preprocessing`, etc.
- Check `1_inputs/comparison_outputs/` for the properly exported comparison data

## Troubleshooting

If you still get errors:
1. Check that all files were copied successfully
2. Restart the container if needed: `docker restart <container_name>`
3. Check logs: `docker logs <container_name> --tail 100`