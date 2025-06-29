# Project Overview

This repository automates the entire process of creating, running, and post-processing EnergyPlus simulations for one or more buildings. It combines geometry generation, HVAC/DHW/fenestration parameter assignment, advanced scenario or calibration methods, and a REST API (Flask/Gunicorn) for managing simulation jobs.

## Key Features

- **Parametric & Scenario-Based Modeling**  
  Generate IDFs (EnergyPlus files) from default rules or user overrides; apply random or fixed picks for sensitivity, calibration, or scenario analysis.

- **Automated Simulation & Parallel Execution**  
  Seamlessly run EnergyPlus in parallel, merge or aggregate the results (daily/monthly), and log everything for traceability.

- **Post-Processing & Validation**  
  Compare simulated results with measured data, compute MBE/CV(RMSE), and output structured validation reports or plots.

- **Sensitivity & Surrogate Methods**  
  Perform Morris or Sobol analyses with SALib, or build Random Forest–based surrogate models to speed up parametric explorations.

- **Calibration Approaches**
  Random search, genetic algorithms, or Bayesian optimization to match real data, producing best-fit parameter sets.
- **Electric Equipment Modeling**
  Dedicated support for building-level ELECTRICEQUIPMENT objects with schedule generation and scenario workflows.

- **API & Job Management**  
  A Flask-based service that orchestrates “jobs” via a concurrency-limited queue. Each job’s logs can be streamed live, canceled, or retrieved for final outputs.

---

## Major Modules

   - **`geomz`, `fenez`, `DHW`, `HVAC`, `ventilation`, `Elec`, `eequip`, `setzone`, etc.**
     Each folder configures a specific aspect of building energy modeling:
       - Default lookup dictionaries (WWR ranges, R-values, etc.).
       - Functions to apply user/Excel/JSON overrides.
       - Methods to create or update relevant EnergyPlus objects (walls, glazing, water heaters, thermostats, etc.).

2. **`structuring`, `postproc`, `validation`**  
   - **`structuring`:** Flattens assigned-parameter logs (min/max picks) into cleaner CSVs.  
   - **`postproc/merge_results.py`:** Merges multiple simulation output files into a single aggregated CSV, optionally converting hourly → daily/monthly.  
   - **`validation`:** Compares simulated vs. real data, calculating MBE/CV(RMSE) and generating pass/fail reports or plots.

3. **`unified_sensitivity`, `unified_surrogate`, `unified_calibration`**  
   - **Sensitivity:** Uses correlation, Morris, or Sobol methods to rank parameter influence.  
   - **Surrogate:** Builds Random Forest models from scenario results for faster prediction.  
   - **Calibration:** Random, genetic, or Bayesian searches to minimize error, returning best-fit parameter sets.

4. **`idf_creation.py` & `main_modifi.py`**  
   - **`idf_creation.py`:** Builds base IDFs from building metadata, merges geometry/HVAC/fenestration modules, runs simulations, saves logs.  
   - **`main_modifi.py`:** Extends these steps for parametric scenarios—picking random or scaled values and generating multiple scenario IDFs.

5. **`epw` (Weather Handling)**  
   Assigns an EPW file (closest year/location) or uses user overrides, then runs EnergyPlus in parallel.

6. **`job_manager.py`, `app.py`, `orchestrator.py`**  
   - **`job_manager.py`:** In-memory system for job queues, concurrency limits, cancellations, real-time logs.  
   - **`app.py`:** Flask endpoints for creating jobs, streaming logs, canceling or retrieving results.  
   - **`orchestrator.py`:** High-level coordinator that loads configs, applies overrides, creates IDFs, runs scenarios/validation/sensitivity/calibration, and zips/emails outputs.

7. **`database_handler.py`**  
   Connects to PostgreSQL to load building records, filtering by bounding box or building ID.

8. **Utilities**  
   - **`zip_and_mail.py`:** Archives final output and emails results.  
   - **`cleanup_old_jobs.py`:** Removes job folders older than a set threshold.

---

## Containerization

- **`Dockerfile`**  
  Builds a Python 3.9 image with EnergyPlus v22.2.0, plus all required Python dependencies, then launches Gunicorn.

- **`docker-compose.yml`**  
  Orchestrates the main application container alongside a PostgreSQL database. Manages networking, environment variables, and persistent volumes.

---

## Why This Project?

1. **Automated End-to-End**  
   From raw building info to validated simulation results, everything is orchestrated in one pipeline.

2. **Scalable & Flexible**  
   Parallel job execution, random/advanced calibration, sensitivity analyses, plus a REST API for remote workflows.

3. **Extensive Overrides & Param Customization**  
   Merges defaults with user-provided Excel/JSON inputs, refining or randomizing building models easily.

4. **Transparent Logging & Validation**  
   Logs every chosen parameter, compares final outputs with real data, and provides structured validation metrics.

---

## Required `.env` File

To use database features and/or email-sending capabilities, you need to create a `.env` file in the project root, containing entries like:

```bash
# Example .env

# Core paths
IDD_PATH=/usr/local/EnergyPlus-22.2.0/Energy+.idd
BASE_IDF_PATH=/usr/src/app/data/Minimal.idf
EPWFILE=/usr/src/app/data/weather/2020.epw
OUTPUT_DIR=/usr/src/app/output

# Postgres DB
DB_NAME=research
DB_USER=postgres
DB_PASSWORD=yourPassword
DB_HOST=someDatabaseHost
DB_PORT=5432

# EnergyPlus version
ENERGYPLUS_VERSION=22.2.0

# SMTP (for sending emails)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SMTP_USERNAME=yourEmail@gmail.com
SMTP_PASSWORD=yourEmailPassword
MAIL_SENDER=yourEmail@gmail.com
```

Adjust values for your database credentials and/or SMTP server details.

---

## Example: Calling the API

Here’s a sample PowerShell script you can use to create and start a simulation job on `localhost:8000` (Docker default):

```powershell
# 1) Read combined.json as a single string
$postData = Get-Content -Raw .\combined.json

# 2) Create the job
Write-Host "Creating job..."
$createResponse = Invoke-RestMethod `
    -Method POST `
    -Uri "http://localhost:8000/jobs" `
    -Headers @{ "Content-Type" = "application/json" } `
    -Body $postData

# 3) Extract the job_id
$jobId = $createResponse.job_id
Write-Host "Created job with ID:" $jobId

# 4) Start the job
Write-Host "Starting job..."
$startResponse = Invoke-RestMethod `
    -Method POST `
    -Uri "http://localhost:8000/jobs/$jobId/start"
Write-Host ($startResponse | ConvertTo-Json)

# 5) Stream logs in real time using curl.exe
Write-Host "Streaming logs..."
curl.exe http://localhost:8000/jobs/$jobId/logs
```

---

**In short, this repo unifies geometry creation, param assignment, scenario-based runs, calibration, and validation into a cohesive energy-modeling pipeline—backed by a REST API for managing large batches of EnergyPlus simulations.**
```
