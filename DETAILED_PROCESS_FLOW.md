# Detailed Process Flow of E_Plus_2040_py Model

## 1. System Entry and Job Creation

### 1.1 Main Entry Point: Flask API (app.py)
- **Primary endpoint**: `POST /jobs`
- **Input**: Combined JSON payload containing all workflow configurations
- **Process**:
  1. Receives JSON data with multiple configuration sections
  2. Creates unique job_id (UUID)
  3. Creates job-specific folders:
     - `user_configs/<job_id>/` - for input config files
     - `output/<job_id>/` - for simulation results
  4. Splits combined JSON into separate files using `splitter.py`

### 1.2 Input Data Structure (combined.json)
The input JSON contains multiple configuration sections:
- **dhw**: Domestic hot water parameters
  - Building-specific settings (building_id)
  - Function-specific settings (building_function, age_range)
  - Parameters: occupant_density, liters_per_person, setpoint_c
  - Min/max values or fixed values

- **epw**: Weather file configurations
  - Fixed EPW paths per building
  - Year overrides

- **zone_sizing**: HVAC zone sizing parameters
  - Cooling/heating supply air temperatures
  - Air flow methods

- **equipment**: Electric equipment settings
  - Equipment density (W/m²)
  - Day/night schedule values

- **shading**: Window shading configurations
  - Slat angles
  - Solar reflectance
  - Blind distances

- **main_config**: Master configuration controlling workflow steps

### 1.3 Data Splitting Process (splitter.py)
- Takes combined JSON and creates individual files:
  - `dhw.json` → `{"dhw": [...]}`
  - `epw.json` → `{"epw": [...]}`
  - `main_config.json` → `{"main_config": {...}}`
  - etc.

## 2. Job Execution

### 2.1 Job Start: `POST /jobs/<job_id>/start`
- Enqueues job for execution
- Job manager controls concurrency (MAX_RUNNING_JOBS = 2)
- Creates background thread running `orchestrate_workflow`

### 2.2 Job Manager (job_manager.py)
- **Job States**: CREATED → QUEUED → RUNNING → FINISHED/ERROR/CANCELED
- **Job Structure**:
  ```python
  {
      "status": JobStatus,
      "config": dict,         # includes job_id and paths
      "logs": queue.Queue,    # for real-time streaming
      "thread": Thread,
      "result": Any,
      "cancel_event": Event
  }
  ```

## 3. Orchestration Workflow (orchestrator/main.py)

### 3.1 Environment Setup
1. **Job environment** setup:
   - Identifies user_configs folder
   - Creates output directories
   
2. **Configuration loading**:
   - Loads `main_config.json`
   - Deep merges with posted data if updates exist
   - Extracts sub-configurations for each module

### 3.2 Configuration Processing

#### Excel Overrides (if enabled)
- DHW lookup tables
- EPW weather files
- Lighting schedules
- HVAC systems
- Ventilation settings
- Fenestration properties

#### JSON Overrides (from user_configs/)
- Building-specific overrides
- Geometry modifications
- System parameter adjustments

### 3.3 Main Processing Steps

#### Step 1: IDF Creation (if enabled)
**Input Data Sources**:
- Building data from:
  - PostgreSQL database (if use_database=true)
  - CSV file (if use_database=false)
- Building attributes include:
  - Physical: area, perimeter, height, orientation
  - Location: x, y, lat, lon, postcode
  - Type: residential_type, non_residential_type
  - Age: bouwjaar, age_range
  - Envelope: average_wwr, side types (north/east/south/west)

**IDF Generation Process**:
1. For each building:
   - Create base IDF from template
   - Add geometry (create_building_with_roof_type)
   - Add fenestration (windows, materials)
   - Add lighting systems
   - Add electric equipment
   - Add DHW systems
   - Add HVAC (ideal loads)
   - Add ventilation
   - Add shading (if configured)
   - Add zone sizing
   - Add ground temperatures
   - Add output definitions

2. Save IDF files to `output/<job_id>/output_IDFs/`

#### Step 2: EnergyPlus Simulations (if enabled)
- Runs EnergyPlus for each generated IDF
- Uses specified EPW weather files
- Outputs:
  - SQL databases with detailed results
  - ESO files with time series data
  - ERR files with errors/warnings

#### Step 3: Parsing (if enabled)
- Converts EnergyPlus outputs to Parquet format
- Extracts time series data
- Processes energy consumption metrics

#### Step 4: Modification (if enabled)
- Applies building modifications
- Creates variant scenarios
- Re-runs simulations if needed

#### Step 5: Sensitivity Analysis (if enabled)
- Parameter sensitivity testing
- Multiple simulation runs with varied inputs
- Statistical analysis of results

#### Step 6: Surrogate Modeling (if enabled)
- Creates simplified models from simulation results
- Machine learning based approximations

#### Step 7: Calibration (if enabled)
- Adjusts model parameters to match measured data
- Optimization routines

#### Step 8: Validation (if enabled)
- Compares results against benchmarks
- Multiple validation stages possible

## 4. Data Formats and Structures

### 4.1 Building Data Structure (Database/CSV)
```
ogc_fid, pand_id, area, perimeter, height, 
building_orientation, building_function,
residential_type, non_residential_type,
north_side, east_side, south_side, west_side,
x, y, lat, lon, postcode, bouwjaar, age_range,
average_wwr, gem_hoogte, gem_bouwlagen, etc.
```

### 4.2 IDF File Structure
- EnergyPlus input format
- Text-based with object:field structure
- Contains all building physics definitions

### 4.3 Output Data Formats
- **Parquet files**: Compressed columnar format for time series
- **CSV files**: Building mappings and summaries
- **JSON files**: Configuration tracking and results

## 5. Logging and Monitoring

- Real-time log streaming via `GET /jobs/<job_id>/logs`
- Log queues per job for concurrent access
- Status tracking via `GET /jobs/<job_id>/status`

## 6. Results Access

- Results stored in `output/<job_id>/`
- Accessible via `GET /jobs/<job_id>/results`
- Includes:
  - Generated IDF files
  - Simulation outputs
  - Parsed data
  - Analysis results