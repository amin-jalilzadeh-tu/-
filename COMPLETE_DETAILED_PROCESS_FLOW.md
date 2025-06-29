# Complete Detailed Process Flow of E_Plus_2040_py

## Table of Contents
1. [System Overview](#system-overview)
2. [Entry Points and Job Management](#entry-points-and-job-management)
3. [Input Data Structures and Formats](#input-data-structures-and-formats)
4. [Configuration Processing](#configuration-processing)
5. [Building Data Loading](#building-data-loading)
6. [IDF Generation Process](#idf-generation-process)
7. [Simulation Execution](#simulation-execution)
8. [Output Parsing and Data Transformation](#output-parsing-and-data-transformation)
9. [Post-Processing Modules](#post-processing-modules)
10. [Data Structures and Algorithms](#data-structures-and-algorithms)
11. [Mathematical Formulas and Calculations](#mathematical-formulas-and-calculations)
12. [File Formats and I/O Operations](#file-formats-and-io-operations)

---

## 1. System Overview

The E_Plus_2040_py system is a comprehensive building energy simulation platform that:
- Accepts building data and configuration via HTTP API
- Generates EnergyPlus IDF files with detailed building physics
- Runs parallel simulations across multiple climate scenarios
- Parses and aggregates results into analytical formats
- Supports sensitivity analysis, surrogate modeling, and calibration

### Architecture Components
```
┌─────────────────────────────────────────────────────────────────┐
│                        Flask API Layer                          │
│  - HTTP endpoints for job management                            │
│  - Asynchronous job execution                                   │
│  - Real-time log streaming                                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                     Job Manager Layer                           │
│  - Concurrent job execution (MAX_RUNNING_JOBS = 2)             │
│  - Thread-based execution model                                 │
│  - In-memory job state tracking                                 │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Layer                           │
│  - Workflow coordination                                        │
│  - Step-by-step execution                                       │
│  - Configuration management                                     │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                    Processing Modules                           │
│  - IDF Creation    - Parsing        - Sensitivity Analysis     │
│  - Simulation      - Modification   - Surrogate Modeling       │
│  - Validation      - Calibration    - Aggregation             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Entry Points and Job Management

### 2.1 Flask API Endpoints (app.py)

#### POST /jobs - Create Job
```python
@app.route("/jobs", methods=["POST"])
def create_job_endpoint():
    # Process flow:
    # 1. Receive combined JSON payload
    posted_data = request.get_json()
    
    # 2. Generate unique job_id (UUID v4)
    job_id = create_job(config={})  # Returns: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    
    # 3. Create isolated job directories
    job_subfolder = os.path.join("user_configs", job_id)
    job_output_folder = os.path.join("output", job_id)
    os.makedirs(job_subfolder, exist_ok=True)
    os.makedirs(job_output_folder, exist_ok=True)
    
    # 4. Split combined JSON into component files
    split_combined_json(posted_data, job_subfolder)
    
    # 5. Update job configuration
    new_config = {
        "job_id": job_id,
        "job_subfolder": job_subfolder,
        "output_subfolder": job_output_folder,
        "posted_data": posted_data
    }
```

#### POST /jobs/<job_id>/start - Start Job Execution
```python
def enqueue_job(job_id: str) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job["status"] != JobStatus.CREATED:
            return
        
        # Check concurrency limit
        running_count = sum(1 for j in _jobs.values() 
                          if j["status"] == JobStatus.RUNNING)
        
        if running_count < MAX_RUNNING_JOBS:
            _start_job(job_id)  # Start immediately
        else:
            job["status"] = JobStatus.QUEUED
            _waiting_jobs.put(job_id)  # Queue for later
```

### 2.2 Job Execution Thread
```python
def _job_thread_runner(job_id: str) -> None:
    try:
        job = _jobs[job_id]
        cancel_event = job["cancel_event"]
        
        # Import and run the main orchestrator
        from orchestrator import orchestrate_workflow
        orchestrate_workflow(job["config"], cancel_event=cancel_event)
        
        job["status"] = JobStatus.FINISHED
    except WorkflowCanceled:
        job["status"] = JobStatus.CANCELED
    except Exception as e:
        job["status"] = JobStatus.ERROR
        job["logs"].put(f"[Job {job_id}] crashed => {e}")
        job["logs"].put(traceback.format_exc())
    finally:
        _signal_end_of_logs(job_id)  # Put None sentinel
        _try_start_next_queued_job()  # Check queue
```

---

## 3. Input Data Structures and Formats

### 3.1 Combined JSON Input Structure
```json
{
  "dhw": [
    {
      "building_id": 413673000,        // Specific building override
      "param_name": "occupant_density_m2_per_person",
      "min_val": 127.0,
      "max_val": 233.0
    },
    {
      "building_function": "residential00",  // Function-based override
      "age_range": "1992-2005",
      "param_name": "setpoint_c",
      "min_val": 58.0,
      "max_val": 60.0
    }
  ],
  
  "epw": [
    {
      "building_id": 413673000,
      "fixed_epw_path": "data/weather/2050.epw"
    },
    {
      "desired_year": 2050,
      "override_year_to": 2020  // Force year in EPW header
    }
  ],
  
  "zone_sizing": [
    {
      "param_name": "cooling_supply_air_temp",
      "min_val": 12.0,
      "max_val": 15.0
    },
    {
      "param_name": "cooling_design_air_flow_method",
      "choices": ["Flow/Zone", "DesignDay", "DesignDayWithLimit"]
    }
  ],
  
  "main_config": {
    "use_database": true,
    "db_filter": {
      "pand_ids": ["0383100000001369", "0383100000001370"],
      "bbox_xy": [52000, 411000, 53000, 412000]
    },
    "filter_by": "pand_ids",
    
    "paths": {
      "dhw_excel": "config/dhw_config.xlsx",
      "epw_excel": "config/weather_mapping.xlsx",
      "building_data": "data/buildings.csv"
    },
    
    "excel_overrides": {
      "override_dhw_excel": true,
      "override_epw_excel": true,
      "override_fenez_excel": false
    },
    
    "idf_creation": {
      "perform_idf_creation": true,
      "scenario": "scenario1",
      "calibration_stage": "pre_calibration",
      "strategy": "B",  // A=midpoint, B=random
      "random_seed": 42,
      "run_simulations": true,
      "output_idf_dir": "output_IDFs"
    }
  }
}
```

### 3.2 Data Splitting Process (splitter.py)
```python
def split_combined_json(posted_data, output_folder):
    """
    Splits combined dict into separate JSON files.
    Each file maintains the original key structure.
    """
    for top_key, value in posted_data.items():
        # Handle empty values
        if value is None:
            value = []
        
        # Create output file with nested structure
        out_path = os.path.join(output_folder, f"{top_key}.json")
        with open(out_path, "w") as f:
            json.dump({top_key: value}, f, indent=2)
            
        logger.info(f"[split_combined_json] Wrote: {out_path}")
```

---

## 4. Configuration Processing

### 4.1 Configuration Loading and Merging
```python
def load_and_merge_config(user_configs_folder, job_config, logger):
    # Load base configuration
    main_config_path = os.path.join(user_configs_folder, "main_config.json")
    with open(main_config_path, "r") as f:
        existing_config_raw = json.load(f)
    main_config = existing_config_raw.get("main_config", {})
    
    # Deep merge with posted updates
    posted_data = job_config.get("posted_data", {})
    if "main_config" in posted_data:
        deep_merge_dicts(main_config, posted_data["main_config"])
        
    return main_config
```

### 4.2 Excel Override Processing

#### DHW Excel Override Structure
```python
# Excel columns: building_id, param_name, value
def override_dhw_lookup_from_excel_file(dhw_excel_path, default_dhw_lookup, override_dhw_flag):
    if override_dhw_flag and os.path.exists(dhw_excel_path):
        df = pd.read_excel(dhw_excel_path)
        
        # Process overrides
        for _, row in df.iterrows():
            building_id = row.get('building_id')
            param_name = row.get('param_name')
            value = row.get('value')
            
            # Apply to lookup structure
            if building_id in default_dhw_lookup:
                default_dhw_lookup[building_id][param_name] = value
```

### 4.3 User JSON Override Application
```python
def apply_json_overrides(user_configs_folder, user_flags, 
                        updated_res_data, updated_nonres_data, logger):
    # Load each component JSON
    components = ['dhw', 'epw', 'lighting', 'hvac', 'vent', 'geometry', 'shading']
    
    for component in components:
        if user_flags.get(f"override_{component}_json", False):
            json_path = os.path.join(user_configs_folder, f"{component}.json")
            
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    override_data = json.load(f).get(component, [])
                
                # Apply overrides based on component type
                # Building-specific or function-based matching
```

---

## 5. Building Data Loading

### 5.1 Database Schema and Query
```sql
-- PostgreSQL query with DISTINCT ON for unique buildings
SELECT DISTINCT ON (b.pand_id)
    -- Identifiers
    b.ogc_fid,              -- Unique feature ID
    b.pand_id,              -- Building ID
    
    -- Physical properties
    b.area,                 -- Floor area (m²)
    b.perimeter,            -- Building perimeter (m)
    b.gem_hoogte,           -- Average height (m)
    b.gem_bouwlagen,        -- Average number of floors
    
    -- Building type
    b.building_function,    -- 'residential' or 'non_residential'
    b.residential_type,     -- e.g., 'Apartment', 'Single-family'
    b.non_residential_type, -- e.g., 'Office', 'Retail'
    b.meestvoorkomendelabel,-- Most common energy label
    
    -- Age and construction
    b.bouwjaar,             -- Construction year
    b.age_range,            -- e.g., '1975-1991', '1992-2005'
    
    -- Orientation and exposure
    b.building_orientation, -- Degrees from north
    b.building_orientation_cardinal, -- N, NE, E, SE, S, SW, W, NW
    b.north_side,           -- 'Facade', 'Party', 'Adjacent'
    b.east_side,
    b.south_side,
    b.west_side,
    
    -- Envelope properties
    b.average_wwr,          -- Window-to-wall ratio
    b.b3_dak_type,          -- Roof type
    b.b3_opp_dak_plat,      -- Flat roof area
    b.b3_opp_dak_schuin,    -- Sloped roof area
    
    -- Location
    b.x, b.y,               -- RD coordinates
    b.lon, b.lat,           -- WGS84 coordinates
    b.postcode              -- Postal code

FROM amin.buildings_1_deducted b
WHERE [filter_conditions]
ORDER BY b.pand_id, b.ogc_fid  -- Take first ogc_fid per pand_id
```

### 5.2 Filter Types
```python
def load_buildings_from_db(filter_criteria=None, filter_by=None):
    # Filter implementations
    if filter_by == "meestvoorkomendepostcode":
        where_clauses.append("b.meestvoorkomendepostcode = ANY(:mpostcodes)")
        params["mpostcodes"] = filter_criteria.get("meestvoorkomendepostcode", [])
        
    elif filter_by == "pand_ids":
        where_clauses.append("b.pand_id = ANY(:pids)")
        params["pids"] = filter_criteria.get("pand_ids", [])
        
    elif filter_by == "bbox_xy":
        minx, miny, maxx, maxy = filter_criteria.get("bbox_xy", [0, 0, 0, 0])
        where_clauses.append("b.x BETWEEN :minx AND :maxx AND b.y BETWEEN :miny AND :maxy")
        
    elif filter_by == "bbox_latlon":
        min_lat, min_lon, max_lat, max_lon = filter_criteria.get("bbox_latlon", [0, 0, 0, 0])
        where_clauses.append("b.lat BETWEEN :min_lat AND :max_lat AND b.lon BETWEEN :min_lon AND :max_lon")
```

---

## 6. IDF Generation Process

### 6.1 IDF Creation Main Loop
```python
def create_idfs_for_all_buildings(
    df_buildings, scenario, calibration_stage, strategy, random_seed,
    user_config_geom, user_config_lighting, user_config_dhw,
    res_data, nonres_data, user_config_hvac, user_config_vent,
    user_config_epw, output_definitions,
    run_simulations=True, simulate_config=None,
    post_process=True, post_process_config=None,
    logs_base_dir=None
):
    # Initialize tracking dictionaries
    assigned_geom_log = {}
    assigned_lighting_log = {}
    assigned_dhw_log = {}
    assigned_fenez_log = {}
    assigned_hvac_log = {}
    assigned_vent_log = {}
    assigned_epw_log = {}
    
    # Process each building
    for idx, row in df_buildings.iterrows():
        idf = create_idf_for_building(
            building_row=row,
            building_index=idx,
            scenario=scenario,
            calibration_stage=calibration_stage,
            strategy=strategy,
            random_seed=random_seed,
            # ... all config parameters ...
        )
        
        # Save IDF
        idf_name = f"building_{idx}.idf"
        idf_path = os.path.join(idf_config["output_dir"], idf_name)
        idf.save(idf_path)
        df_buildings.at[idx, "idf_name"] = idf_name
```

### 6.2 Geometry Creation Process

#### 6.2.1 Geometry Parameter Assignment
```python
def assign_geometry_values(building_row, calibration_stage="pre_calibration", 
                          strategy="A", random_seed=None, user_config=None):
    # Get building properties
    bldg_id = building_row.get("ogc_fid", 0)
    bldg_function = building_row.get("building_function", "residential").lower()
    
    # Determine sub-type
    if bldg_function == "residential":
        sub_type = building_row.get("residential_type", "Two-and-a-half-story House")
        dict_for_function = geometry_lookup.get("residential", {}).get(sub_type, {})
    else:
        sub_type = building_row.get("non_residential_type", "Office Function")
        dict_for_function = geometry_lookup.get("non_residential", {}).get(sub_type, {})
    
    # Get calibration stage parameters
    param_dict = dict_for_function.get(calibration_stage, {
        "perimeter_depth_range": (2.0, 3.0),
        "has_core": False
    })
    
    # Apply strategy for range values
    perimeter_depth_range = param_dict.get("perimeter_depth_range", (2.0, 3.0))
    
    if strategy == "A":  # Midpoint
        perimeter_depth = (perimeter_depth_range[0] + perimeter_depth_range[1]) / 2.0
    elif strategy == "B":  # Random
        perimeter_depth = random.uniform(perimeter_depth_range[0], perimeter_depth_range[1])
    else:
        perimeter_depth = perimeter_depth_range[0]  # Min value
    
    return {
        "perimeter_depth": perimeter_depth,
        "has_core": param_dict.get("has_core", False)
    }
```

#### 6.2.2 Dimension Calculation from Area and Perimeter
```python
def compute_dimensions_from_area_perimeter(area, perimeter):
    """
    Solve for rectangle dimensions given area and perimeter.
    For rectangle: area = width * length, perimeter = 2 * (width + length)
    
    Solving the system:
    w * l = A
    w + l = P/2
    
    Leads to quadratic: w² - (P/2)w + A = 0
    """
    half_p = perimeter / 2.0
    discriminant = half_p**2 - 4*area
    
    if discriminant < 0:
        # Invalid - use square approximation
        side_length = math.sqrt(area)
        return side_length, side_length
    
    sqrt_disc = math.sqrt(discriminant)
    width = (half_p - sqrt_disc) / 2.0
    length = (half_p + sqrt_disc) / 2.0
    
    return width, length
```

#### 6.2.3 Building Polygon Creation
```python
def create_building_base_polygon(width, length, orientation):
    """
    Create rotated rectangle vertices.
    Origin at (0,0), rotate by orientation degrees.
    """
    # Create rectangle centered at origin
    half_w = width / 2.0
    half_l = length / 2.0
    
    # Initial vertices (counterclockwise from SW corner)
    vertices = [
        (-half_w, -half_l, 0),  # SW
        (half_w, -half_l, 0),   # SE
        (half_w, half_l, 0),    # NE
        (-half_w, half_l, 0)    # NW
    ]
    
    # Rotate by orientation
    angle_rad = math.radians(orientation)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    rotated_vertices = []
    for x, y, z in vertices:
        x_rot = x * cos_a - y * sin_a
        y_rot = x * sin_a + y * cos_a
        rotated_vertices.append((x_rot, y_rot, z))
    
    return rotated_vertices
```

#### 6.2.4 Zone Creation with Perimeter/Core
```python
def create_zones_with_perimeter_depth(idf, base_poly, wall_height, 
                                     perimeter_depth, has_core, 
                                     floor_type="Ground", is_top_floor=True):
    """
    Create perimeter and core zones based on depth parameter.
    """
    zones_created = []
    
    if perimeter_depth > 0:
        # Create perimeter zones (North, East, South, West)
        # Inset the polygon by perimeter_depth
        core_poly = inward_offset_polygon(base_poly, perimeter_depth)
        
        # Create 4 perimeter zones
        perimeter_zones = create_perimeter_zones(
            idf, base_poly, core_poly, wall_height, 
            floor_type, is_top_floor
        )
        zones_created.extend(perimeter_zones)
        
        if has_core and polygon_area(core_poly) > 0:
            # Create core zone
            core_zone = create_single_zone(
                idf, "Core", core_poly, wall_height,
                floor_bc=floor_type,
                wall_bcs=["Surface"] * 4,  # All internal
                is_top_floor=is_top_floor
            )
            zones_created.append(core_zone)
            
            # Link perimeter to core
            for p_zone in perimeter_zones:
                link_adjacent_zones(p_zone, core_zone)
    else:
        # Single zone building
        single_zone = create_single_zone(
            idf, "Zone1", base_poly, wall_height,
            floor_bc=floor_type,
            wall_bcs=["Outdoors"] * 4,
            is_top_floor=is_top_floor
        )
        zones_created.append(single_zone)
    
    return zones_created
```

### 6.3 Fenestration (Window) Assignment

#### 6.3.1 WWR Parameter Assignment
```python
def assign_fenestration_parameters(building_row, scenario, calibration_stage,
                                 strategy, random_seed, res_data, nonres_data):
    # Determine building type
    bldg_func = building_row.get("building_function", "residential").lower()
    age_range = building_row.get("age_range", "unknown")
    
    # Get appropriate data dictionary
    if bldg_func == "residential":
        bldg_type = building_row.get("residential_type", "unknown")
        fenez_data = res_data
    else:
        bldg_type = building_row.get("non_residential_type", "unknown") 
        fenez_data = nonres_data
    
    # Navigate to WWR range
    # Structure: data[age_range][bldg_type][scenario][calibration_stage]["wwr_range"]
    try:
        stage_data = fenez_data[age_range][bldg_type][scenario][calibration_stage]
        wwr_range = stage_data.get("wwr_range", (0.2, 0.4))
    except KeyError:
        wwr_range = (0.2, 0.4)  # Default fallback
    
    # Apply strategy
    if strategy == "A":
        wwr = (wwr_range[0] + wwr_range[1]) / 2.0
    elif strategy == "B":
        wwr = random.uniform(wwr_range[0], wwr_range[1])
    else:
        wwr = wwr_range[0]
    
    return wwr, wwr_range
```

#### 6.3.2 Window Surface Creation
```python
def add_fenestration(idf, building_row, scenario, calibration_stage, 
                    strategy, random_seed, res_data, nonres_data):
    # Get WWR
    wwr, wwr_range_used = assign_fenestration_parameters(
        building_row, scenario, calibration_stage, 
        strategy, random_seed, res_data, nonres_data
    )
    
    # Remove existing windows
    fen_objects = idf.idfobjects["FENESTRATIONSURFACE:DETAILED"]
    del fen_objects[:]
    
    # Use geomeppy to create windows on all exterior walls
    # This automatically:
    # 1. Finds all exterior wall surfaces
    # 2. Calculates window dimensions to achieve target WWR
    # 3. Centers windows on each wall
    # 4. Assigns construction "Window1C"
    from geomeppy import IDF as GeppyIDF
    GeppyIDF.set_wwr(idf, wwr=wwr, construction="Window1C")
```

### 6.4 Material and Construction Assignment

#### 6.4.1 Construction Updates Based on Age
```python
def update_construction_materials(idf, building_row, res_data, nonres_data):
    age_range = building_row.get("age_range", "unknown")
    bldg_func = building_row.get("building_function", "residential").lower()
    
    # Get construction data
    if bldg_func == "residential":
        construction_data = res_data.get(age_range, {}).get("constructions", {})
    else:
        construction_data = nonres_data.get(age_range, {}).get("constructions", {})
    
    # Update wall construction U-values
    wall_u_value = construction_data.get("wall_u_value", 0.5)
    roof_u_value = construction_data.get("roof_u_value", 0.3)
    floor_u_value = construction_data.get("floor_u_value", 0.4)
    window_u_value = construction_data.get("window_u_value", 2.0)
    
    # Create/update constructions
    update_construction_u_value(idf, "Exterior Wall", wall_u_value)
    update_construction_u_value(idf, "Roof", roof_u_value)
    update_construction_u_value(idf, "Ground Floor", floor_u_value)
    
    # Window construction with SHGC
    update_window_construction(
        idf, "Window1C", 
        u_value=window_u_value,
        shgc=construction_data.get("window_shgc", 0.6),
        visible_transmittance=construction_data.get("window_vt", 0.7)
    )
```

### 6.5 HVAC System Creation

#### 6.5.1 Ideal Loads Air System
```python
def add_HVAC_Ideal_to_all_zones(idf, building_row, calibration_stage="pre_calibration",
                               strategy="A", random_seed=None, user_config_hvac=None):
    # Get HVAC parameters
    hvac_params = assign_hvac_ideal_parameters(
        building_id=building_row.get("ogc_fid"),
        building_function=building_row.get("building_function"),
        residential_type=building_row.get("residential_type"),
        non_residential_type=building_row.get("non_residential_type"),
        age_range=building_row.get("age_range"),
        scenario=building_row.get("scenario", "default"),
        calibration_stage=calibration_stage,
        strategy=strategy,
        random_seed=random_seed,
        user_config_hvac=user_config_hvac
    )
    
    # Create schedules
    create_schedules_for_building(idf, hvac_params["schedule_details"], 
                                building_row.get("ogc_fid"))
    
    # Add ideal loads to each zone
    zones = idf.idfobjects["ZONE"]
    for zone in zones:
        ideal_loads = idf.newidfobject("ZONEHVAC:IDEALLOADSAIRSYSTEM")
        ideal_loads.Name = f"{zone.Name}_IdealLoads"
        ideal_loads.Zone_Name = zone.Name
        
        # Set parameters
        ideal_loads.Maximum_Heating_Supply_Air_Temperature = hvac_params["max_heating_supply_air_temp"]
        ideal_loads.Minimum_Cooling_Supply_Air_Temperature = hvac_params["min_cooling_supply_air_temp"]
        ideal_loads.Maximum_Heating_Supply_Air_Humidity_Ratio = hvac_params["max_heating_supply_air_hr"]
        ideal_loads.Minimum_Cooling_Supply_Air_Humidity_Ratio = hvac_params["min_cooling_supply_air_hr"]
        
        # Link to thermostat
        ideal_loads.Availability_Schedule_Name = hvac_params["availability_schedule"]
        
        # Create thermostat
        create_thermostat_for_zone(idf, zone, hvac_params)
```

#### 6.5.2 Schedule Creation
```python
def create_schedules_for_building(idf, schedule_details, building_id):
    """
    Create SCHEDULE:COMPACT objects for HVAC operation.
    """
    # Heating setpoint schedule
    heat_sched = idf.newidfobject("SCHEDULE:COMPACT")
    heat_sched.Name = f"HeatSetp_Bldg{building_id}"
    heat_sched.Schedule_Type_Limits_Name = "Temperature"
    
    # Schedule format:
    # Through: 12/31
    # For: Weekdays
    # Until: 6:00, [night_setpoint]
    # Until: 22:00, [day_setpoint]  
    # Until: 24:00, [night_setpoint]
    # For: Weekends...
    
    fields = []
    fields.append("Through: 12/31")
    
    # Weekday schedule
    fields.append("For: Weekdays")
    fields.append(f"Until: 6:00,{schedule_details['heat_night_setpoint']}")
    fields.append(f"Until: 22:00,{schedule_details['heat_day_setpoint']}")
    fields.append(f"Until: 24:00,{schedule_details['heat_night_setpoint']}")
    
    # Weekend schedule
    fields.append("For: AllOtherDays")
    fields.append(f"Until: 8:00,{schedule_details['heat_night_setpoint']}")
    fields.append(f"Until: 23:00,{schedule_details['heat_day_setpoint']}")
    fields.append(f"Until: 24:00,{schedule_details['heat_night_setpoint']}")
    
    # Assign fields
    for i, field_value in enumerate(fields):
        setattr(heat_sched, f"Field_{i+1}", field_value)
```

### 6.6 Lighting System
```python
def add_lights_and_parasitics(idf, building_row, strategy="A", 
                             user_config_lighting=None):
    # Get lighting power density
    lpd_params = assign_lighting_parameters(
        building_row, strategy, user_config_lighting
    )
    
    # Add to each zone
    zones = idf.idfobjects["ZONE"]
    for zone in zones:
        # Calculate zone area
        zone_area = calculate_zone_floor_area(zone)
        
        # Create lights object
        lights = idf.newidfobject("LIGHTS")
        lights.Name = f"{zone.Name}_Lights"
        lights.Zone_or_ZoneList_Name = zone.Name
        lights.Schedule_Name = lpd_params["schedule_name"]
        lights.Design_Level_Calculation_Method = "Watts/Area"
        lights.Watts_per_Zone_Floor_Area = lpd_params["watts_per_m2"]
        lights.Return_Air_Fraction = 0.0
        lights.Fraction_Radiant = 0.37
        lights.Fraction_Visible = 0.18
        lights.Fraction_Replaceable = 1.0
```

### 6.7 DHW (Domestic Hot Water) System

#### 6.7.1 DHW Parameter Assignment
```python
def assign_dhw_parameters(building_row, strategy="A", user_config_dhw=None):
    """
    Assign DHW parameters based on NTA 8800 standards.
    """
    bldg_func = building_row.get("building_function", "residential").lower()
    
    if bldg_func == "residential":
        # Residential: 45 L/person/day standard
        occupant_density = get_occupant_density(building_row)  # m²/person
        liters_per_person_day = 45.0  # NTA 8800 standard
        
        # Calculate total daily usage
        floor_area = building_row.get("area", 100.0)
        num_occupants = floor_area / occupant_density
        total_liters_per_day = num_occupants * liters_per_person_day
        
        # Convert to kWh (1 kWh heats ~13.76 liters by 62.5°C)
        kwh_per_day = total_liters_per_day / 13.76
        
    else:
        # Non-residential: Use lookup table
        nonres_type = building_row.get("non_residential_type", "Office")
        
        # NTA 8800 Table 14.5 values (kWh/m²/year)
        dhw_intensity_lookup = {
            "Office": 2.2,
            "Meeting": 2.2,
            "Healthcare": 15.3,
            "Retail": 2.2,
            "Sports": 50.9,
            "Accommodation": 31.7,
            "Education": 4.8
        }
        
        kwh_per_m2_year = dhw_intensity_lookup.get(nonres_type, 2.2)
        kwh_per_day = (building_row.get("area", 100.0) * kwh_per_m2_year) / 365.0
    
    return {
        "daily_energy_kwh": kwh_per_day,
        "setpoint_c": 60.0,  # Standard DHW temperature
        "deadband_c": 5.0    # Hysteresis
    }
```

#### 6.7.2 Water Heater Creation
```python
def add_dhw_to_idf(idf, building_row, dhw_params):
    # Create water heater
    heater = idf.newidfobject("WATERHEATER:MIXED")
    heater.Name = f"DHW_Heater_{building_row.get('ogc_fid', 0)}"
    
    # Sizing based on daily usage
    daily_kwh = dhw_params["daily_energy_kwh"]
    peak_draw_duration = 2.0  # hours
    heater_capacity = (daily_kwh / peak_draw_duration) * 1000  # W
    
    heater.Tank_Volume = daily_kwh * 20  # Liters (rough sizing)
    heater.Setpoint_Temperature_Schedule_Name = "DHW_Setpoint_Schedule"
    heater.Deadband_Temperature_Difference = dhw_params["deadband_c"]
    heater.Maximum_Temperature_Limit = 82.2  # Safety limit
    heater.Heater_Control_Type = "Cycle"
    
    # Efficiency parameters
    heater.Heater_Thermal_Efficiency = 0.8
    heater.Heater_Fuel_Type = "Electricity"
    heater.Heater_Maximum_Capacity = heater_capacity
    
    # Create usage schedule
    create_dhw_usage_schedule(idf, daily_kwh)
```

### 6.8 Output Variable Definitions
```python
def add_output_definitions(idf, output_definitions):
    """
    Add output variables and meters to track simulation results.
    """
    # Standard outputs
    standard_outputs = [
        ("Zone Mean Air Temperature", "Hourly"),
        ("Zone Total Internal Total Heating Energy", "Hourly"),
        ("Zone Ideal Loads Zone Total Cooling Energy", "Hourly"),
        ("Zone Ideal Loads Zone Total Heating Energy", "Hourly"),
        ("Zone Electric Equipment Electricity Energy", "Hourly"),
        ("Zone Lights Electricity Energy", "Hourly"),
        ("Water Heater Electricity Energy", "Hourly")
    ]
    
    for var_name, frequency in standard_outputs:
        output = idf.newidfobject("OUTPUT:VARIABLE")
        output.Key_Value = "*"  # All zones/objects
        output.Variable_Name = var_name
        output.Reporting_Frequency = frequency
    
    # Meters for totals
    meters = [
        "Electricity:Facility",
        "Electricity:HVAC",
        "Electricity:Building",
        "NaturalGas:Facility"
    ]
    
    for meter_name in meters:
        meter = idf.newidfobject("OUTPUT:METER")
        meter.Name = meter_name
        meter.Reporting_Frequency = "Hourly"
```

---

## 7. Simulation Execution

### 7.1 EPW File Assignment
```python
def assign_epw_for_building_with_overrides(building_row, user_config_epw=None):
    """
    Determine weather file for building based on location and year.
    """
    # Check user overrides first
    building_id = building_row.get("ogc_fid")
    
    if user_config_epw:
        for override in user_config_epw:
            if override.get("building_id") == building_id:
                if "fixed_epw_path" in override:
                    return override["fixed_epw_path"]
    
    # Default logic: map by location and year
    lat = building_row.get("lat", 52.0)
    lon = building_row.get("lon", 4.0)
    year = building_row.get("desired_climate_year", 2020)
    
    # Find nearest weather station
    epw_path = find_nearest_epw(lat, lon, year)
    
    return epw_path
```

### 7.2 Parallel Simulation Execution
```python
def simulate_all(df_buildings, idf_directory, iddfile, base_output_dir,
                user_config_epw=None, num_workers=4):
    """
    Run EnergyPlus simulations in parallel.
    """
    # Initialize IDD in parent process
    initialize_idd(iddfile)
    
    # Generate task list
    tasks = []
    for idx, row in df_buildings.iterrows():
        epw_path = assign_epw_for_building_with_overrides(row, user_config_epw)
        idf_name = row.get("idf_name")
        idf_path = os.path.join(idf_directory, idf_name)
        
        # Group outputs by year
        year = row.get("desired_climate_year", 2020)
        output_dir = os.path.join(base_output_dir, str(year))
        
        building_id = row.get("ogc_fid", idx)
        
        tasks.append((idf_path, epw_path, iddfile, output_dir, idx, building_id))
    
    # Run with multiprocessing
    with Pool(num_workers) as pool:
        results = pool.map(run_simulation, tasks)
```

### 7.3 Individual Simulation Run
```python
def run_simulation(args):
    """
    Execute single EnergyPlus simulation.
    """
    idf_path, epwfile, iddfile, output_directory, bldg_idx, building_id = args
    
    try:
        # Initialize IDD if needed
        initialize_idd(iddfile)
        
        # Load IDF with EPW
        idf = IDF(idf_path, epwfile)
        
        # Configure run options
        run_opts = {
            "output_prefix": f"simulation_bldg{bldg_idx}_{building_id}",
            "output_suffix": "C",
            "output_directory": output_directory,
            "readvars": True,      # Generate CSV from ESO
            "expandobjects": True   # Expand HVACTemplate objects
        }
        
        # Execute EnergyPlus
        idf.run(**run_opts)
        
        return True, f"Success: {idf_path}"
        
    except Exception as e:
        logging.error(f"Simulation failed for {building_id}: {e}")
        return False, f"Error: {idf_path} - {str(e)}"
```

---

## 8. Output Parsing and Data Transformation

### 8.1 SQL Database Structure
```sql
-- EnergyPlus SQLite output schema

-- Time index table
CREATE TABLE Time (
    TimeIndex INTEGER PRIMARY KEY,
    Month INTEGER,
    Day INTEGER,
    Hour INTEGER,
    Minute INTEGER,
    DayType TEXT,
    EnvironmentPeriodIndex INTEGER
);

-- Variable dictionary
CREATE TABLE ReportDataDictionary (
    ReportDataDictionaryIndex INTEGER PRIMARY KEY,
    IsMeter INTEGER,
    Type TEXT,
    IndexGroup TEXT,
    TimestepType TEXT,
    KeyValue TEXT,
    Name TEXT,
    ReportingFrequency TEXT,
    ScheduleName TEXT,
    Units TEXT
);

-- Actual data values
CREATE TABLE ReportData (
    ReportDataIndex INTEGER PRIMARY KEY,
    TimeIndex INTEGER,
    ReportDataDictionaryIndex INTEGER,
    Value REAL,
    FOREIGN KEY(TimeIndex) REFERENCES Time(TimeIndex),
    FOREIGN KEY(ReportDataDictionaryIndex) 
        REFERENCES ReportDataDictionary(ReportDataDictionaryIndex)
);
```

### 8.2 SQL Data Extraction
```python
def extract_timeseries_data(sql_path, building_id):
    """
    Extract time series data from EnergyPlus SQL output.
    """
    conn = sqlite3.connect(sql_path)
    
    # Query to get all time series data with proper timestamps
    query = """
    SELECT 
        t.Month,
        t.Day,
        t.Hour,
        t.Minute,
        rdd.KeyValue as Zone,
        rdd.Name as VariableName,
        rdd.Units,
        rdd.ReportingFrequency,
        rd.Value
    FROM ReportData rd
    JOIN Time t ON rd.TimeIndex = t.TimeIndex
    JOIN ReportDataDictionary rdd 
        ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
    WHERE rdd.ReportingFrequency IN ('Hourly', 'Daily', 'Monthly')
    ORDER BY t.Month, t.Day, t.Hour, t.Minute
    """
    
    df = pd.read_sql_query(query, conn)
    
    # Create proper datetime index
    df['DateTime'] = pd.to_datetime(
        df[['Month', 'Day', 'Hour', 'Minute']].assign(Year=2020)
    )
    
    # Add building identifier
    df['building_id'] = building_id
    
    conn.close()
    return df
```

### 8.3 Data Transformation to Parquet

#### 8.3.1 Pivot to Semi-Wide Format
```python
def transform_to_semi_wide_format(df_long):
    """
    Transform long format to semi-wide with dates as columns.
    
    Input columns: building_id, DateTime, Zone, VariableName, Value, Units
    Output columns: building_id, Zone, VariableName, Units, 2020-01-01, 2020-01-02, ...
    """
    # Create date column
    df_long['Date'] = df_long['DateTime'].dt.date
    
    # Group and aggregate (sum for energy, mean for temperature)
    aggregation_rules = {
        'Energy': 'sum',
        'Temperature': 'mean',
        'Power': 'mean',
        'Rate': 'mean'
    }
    
    # Determine aggregation method
    df_long['AggMethod'] = df_long['Units'].apply(
        lambda x: 'sum' if 'J' in x or 'Wh' in x else 'mean'
    )
    
    # Pivot with appropriate aggregation
    df_wide = df_long.pivot_table(
        index=['building_id', 'Zone', 'VariableName', 'Units'],
        columns='Date',
        values='Value',
        aggfunc=lambda x: x.sum() if x.name == 'sum' else x.mean()
    )
    
    # Reset index to get identifier columns
    df_wide = df_wide.reset_index()
    
    # Rename date columns to strings
    date_columns = [col for col in df_wide.columns if isinstance(col, date)]
    df_wide.columns = [
        col.strftime('%Y-%m-%d') if isinstance(col, date) else col 
        for col in df_wide.columns
    ]
    
    return df_wide
```

#### 8.3.2 Variable Categorization
```python
def categorize_variables(df):
    """
    Add category column based on variable name patterns.
    """
    categories = {
        'HVAC': ['Heating Energy', 'Cooling Energy', 'Fan', 'Pump'],
        'Lighting': ['Lights Electricity'],
        'Equipment': ['Electric Equipment'],
        'DHW': ['Water Heater', 'Water Use'],
        'Envelope': ['Surface Heat', 'Window Heat'],
        'Temperature': ['Mean Air Temperature', 'Operative Temperature'],
        'Comfort': ['PMV', 'PPD', 'Humidity'],
        'Total': ['Facility', 'Building']
    }
    
    df['Category'] = 'Other'
    
    for category, patterns in categories.items():
        mask = df['VariableName'].str.contains('|'.join(patterns), case=False)
        df.loc[mask, 'Category'] = category
    
    return df
```

### 8.4 Output File Structure
```
output/<job_id>/parser_output/
├── timeseries/
│   ├── base_all_hourly.parquet      # All hourly data
│   ├── base_all_daily.parquet       # Daily aggregations
│   ├── base_all_monthly.parquet     # Monthly aggregations
│   └── base_all_annual.parquet      # Annual summaries
├── comparisons/
│   ├── variant_comparison_12345.parquet  # Building-specific comparisons
│   └── summary_comparison.parquet        # Overall comparison metrics
├── summaries/
│   ├── annual_energy_by_building.parquet
│   ├── peak_loads.parquet
│   └── comfort_metrics.parquet
└── metadata/
    ├── variable_definitions.json
    ├── building_mappings.json
    └── parsing_log.json
```

---

## 9. Post-Processing Modules

### 9.1 Sensitivity Analysis

#### 9.1.1 Parameter Sampling
```python
def generate_parameter_samples(param_ranges, n_samples, method='sobol'):
    """
    Generate parameter samples for sensitivity analysis.
    """
    if method == 'sobol':
        # Sobol sequence for better space coverage
        from SALib.sample import sobol
        
        problem = {
            'num_vars': len(param_ranges),
            'names': list(param_ranges.keys()),
            'bounds': [[r[0], r[1]] for r in param_ranges.values()]
        }
        
        samples = sobol.sample(problem, n_samples)
        
    elif method == 'lhs':
        # Latin Hypercube Sampling
        from pyDOE import lhs
        
        n_params = len(param_ranges)
        samples = lhs(n_params, samples=n_samples)
        
        # Scale to actual ranges
        for i, (param, range_) in enumerate(param_ranges.items()):
            samples[:, i] = samples[:, i] * (range_[1] - range_[0]) + range_[0]
    
    return samples
```

#### 9.1.2 Sensitivity Indices Calculation
```python
def calculate_sensitivity_indices(Y, param_samples, method='sobol'):
    """
    Calculate sensitivity indices from simulation outputs.
    """
    if method == 'sobol':
        from SALib.analyze import sobol
        
        Si = sobol.analyze(problem, Y)
        
        # First-order indices (main effects)
        S1 = Si['S1']
        
        # Total-order indices (including interactions)
        ST = Si['ST']
        
        # Second-order indices (pairwise interactions)
        S2 = Si['S2']
        
    return {
        'first_order': S1,
        'total_order': ST,
        'second_order': S2,
        'confidence': Si['S1_conf']
    }
```

### 9.2 Surrogate Modeling

#### 9.2.1 Gaussian Process Regression
```python
def train_gp_surrogate(X_train, y_train, kernel_type='rbf'):
    """
    Train Gaussian Process surrogate model.
    """
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, Matern, RationalQuadratic
    
    # Select kernel
    if kernel_type == 'rbf':
        kernel = RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e2))
    elif kernel_type == 'matern':
        kernel = Matern(length_scale=1.0, nu=1.5)
    
    # Train GP
    gp = GaussianProcessRegressor(
        kernel=kernel,
        n_restarts_optimizer=10,
        alpha=1e-6,  # Noise level
        normalize_y=True
    )
    
    gp.fit(X_train, y_train)
    
    # Return model with uncertainty quantification
    return gp
```

#### 9.2.2 Neural Network Surrogate
```python
def train_nn_surrogate(X_train, y_train, hidden_layers=(50, 50)):
    """
    Train neural network surrogate model.
    """
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import StandardScaler
    
    # Scale inputs
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)
    
    # Train NN
    nn = MLPRegressor(
        hidden_layer_sizes=hidden_layers,
        activation='relu',
        solver='adam',
        max_iter=1000,
        early_stopping=True,
        validation_fraction=0.2
    )
    
    nn.fit(X_scaled, y_train)
    
    return nn, scaler
```

### 9.3 Calibration

#### 9.3.1 Objective Function
```python
def calibration_objective(params, measured_data, simulation_func):
    """
    Calculate calibration error metric.
    """
    # Run simulation with current parameters
    simulated_data = simulation_func(params)
    
    # Calculate RMSE
    rmse = np.sqrt(np.mean((simulated_data - measured_data)**2))
    
    # Calculate CV-RMSE (normalized by mean)
    cv_rmse = rmse / np.mean(measured_data) * 100
    
    # Calculate NMBE (Normalized Mean Bias Error)
    nmbe = np.mean(simulated_data - measured_data) / np.mean(measured_data) * 100
    
    # Combined objective (ASHRAE Guideline 14)
    # CV-RMSE < 30% (monthly), NMBE < 10%
    objective = cv_rmse + abs(nmbe)
    
    return objective
```

#### 9.3.2 Optimization Algorithms

##### Particle Swarm Optimization
```python
def calibrate_with_pso(objective_func, param_bounds, n_particles=30, n_iterations=100):
    """
    Particle Swarm Optimization for calibration.
    """
    n_params = len(param_bounds)
    
    # Initialize particles
    particles = np.random.uniform(
        low=[b[0] for b in param_bounds],
        high=[b[1] for b in param_bounds],
        size=(n_particles, n_params)
    )
    
    velocities = np.zeros_like(particles)
    p_best = particles.copy()
    p_best_scores = np.full(n_particles, np.inf)
    g_best = None
    g_best_score = np.inf
    
    # PSO parameters
    w = 0.7  # Inertia weight
    c1 = 1.5  # Cognitive parameter
    c2 = 1.5  # Social parameter
    
    for iteration in range(n_iterations):
        # Evaluate particles
        scores = np.array([objective_func(p) for p in particles])
        
        # Update personal bests
        improved = scores < p_best_scores
        p_best[improved] = particles[improved]
        p_best_scores[improved] = scores[improved]
        
        # Update global best
        best_idx = np.argmin(scores)
        if scores[best_idx] < g_best_score:
            g_best = particles[best_idx].copy()
            g_best_score = scores[best_idx]
        
        # Update velocities and positions
        r1 = np.random.random((n_particles, n_params))
        r2 = np.random.random((n_particles, n_params))
        
        velocities = (w * velocities + 
                     c1 * r1 * (p_best - particles) +
                     c2 * r2 * (g_best - particles))
        
        particles = particles + velocities
        
        # Enforce bounds
        particles = np.clip(particles, 
                          [b[0] for b in param_bounds],
                          [b[1] for b in param_bounds])
    
    return g_best, g_best_score
```

##### Differential Evolution
```python
def calibrate_with_de(objective_func, param_bounds, pop_size=50, n_generations=100):
    """
    Differential Evolution for calibration.
    """
    from scipy.optimize import differential_evolution
    
    result = differential_evolution(
        objective_func,
        param_bounds,
        popsize=pop_size,
        maxiter=n_generations,
        strategy='best1bin',  # DE/best/1/bin
        mutation=(0.5, 1.0),  # F parameter
        recombination=0.7,    # CR parameter
        disp=True,
        workers=-1  # Use all CPU cores
    )
    
    return result.x, result.fun
```

### 9.4 Validation

#### 9.4.1 Validation Metrics
```python
def calculate_validation_metrics(simulated, measured):
    """
    Calculate comprehensive validation metrics.
    """
    # Basic statistics
    rmse = np.sqrt(np.mean((simulated - measured)**2))
    mae = np.mean(np.abs(simulated - measured))
    mbe = np.mean(simulated - measured)
    
    # Normalized metrics
    cv_rmse = rmse / np.mean(measured) * 100
    nmbe = mbe / np.mean(measured) * 100
    
    # Correlation
    r2 = np.corrcoef(simulated, measured)[0, 1]**2
    
    # Peak accuracy
    peak_sim = np.max(simulated)
    peak_meas = np.max(measured)
    peak_error = abs(peak_sim - peak_meas) / peak_meas * 100
    
    # Time-weighted metrics (emphasize peak periods)
    weights = create_time_weights(measured)
    weighted_rmse = np.sqrt(np.mean(weights * (simulated - measured)**2))
    
    return {
        'RMSE': rmse,
        'CV-RMSE': cv_rmse,
        'MAE': mae,
        'MBE': mbe,
        'NMBE': nmbe,
        'R2': r2,
        'Peak_Error_%': peak_error,
        'Weighted_RMSE': weighted_rmse,
        'ASHRAE_14_Pass': cv_rmse < 30 and abs(nmbe) < 10
    }
```

#### 9.4.2 Time-Based Validation
```python
def validate_by_time_period(simulated, measured, timestamps):
    """
    Validate across different time periods.
    """
    df = pd.DataFrame({
        'simulated': simulated,
        'measured': measured,
        'timestamp': timestamps
    })
    
    # Add time components
    df['hour'] = df['timestamp'].dt.hour
    df['month'] = df['timestamp'].dt.month
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    
    results = {}
    
    # Hourly profile validation
    hourly_metrics = []
    for hour in range(24):
        hour_data = df[df['hour'] == hour]
        if len(hour_data) > 0:
            metrics = calculate_validation_metrics(
                hour_data['simulated'].values,
                hour_data['measured'].values
            )
            hourly_metrics.append(metrics)
    
    # Monthly validation
    monthly_metrics = []
    for month in range(1, 13):
        month_data = df[df['month'] == month]
        if len(month_data) > 0:
            metrics = calculate_validation_metrics(
                month_data['simulated'].values,
                month_data['measured'].values
            )
            monthly_metrics.append(metrics)
    
    # Weekday vs Weekend
    weekday_data = df[df['dayofweek'] < 5]
    weekend_data = df[df['dayofweek'] >= 5]
    
    weekday_metrics = calculate_validation_metrics(
        weekday_data['simulated'].values,
        weekday_data['measured'].values
    )
    
    weekend_metrics = calculate_validation_metrics(
        weekend_data['simulated'].values,
        weekend_data['measured'].values
    )
    
    return {
        'hourly': hourly_metrics,
        'monthly': monthly_metrics,
        'weekday': weekday_metrics,
        'weekend': weekend_metrics
    }
```

---

## 10. Data Structures and Algorithms

### 10.1 Lookup Dictionary Structures

#### 10.1.1 Geometry Lookup
```python
geometry_lookup = {
    "residential": {
        "Apartment": {
            "pre_calibration": {
                "perimeter_depth_range": (2.0, 3.0),
                "has_core": False
            },
            "calibrated": {
                "perimeter_depth_range": (2.5, 2.5),  # Fixed after calibration
                "has_core": False
            }
        },
        "Two-and-a-half-story House": {
            "pre_calibration": {
                "perimeter_depth_range": (3.0, 4.0),
                "has_core": False
            }
        }
    },
    "non_residential": {
        "Office Function": {
            "pre_calibration": {
                "perimeter_depth_range": (3.0, 5.0),
                "has_core": True  # Offices typically have core zones
            }
        }
    }
}
```

#### 10.1.2 DHW Usage Factors (NTA 8800)
```python
dhw_usage_factors = {
    "residential": {
        "base_usage_liters_per_person_day": 45.0,
        "temperature_rise_c": 62.5,  # From 10°C to 72.5°C
        "conversion_factor_kwh_per_liter": 0.0727  # 1/13.76
    },
    "non_residential": {
        # kWh/m²/year from NTA 8800 Table 14.5
        "Offices": 2.2,
        "Meeting": 2.2,
        "Healthcare": 15.3,
        "Healthcare_bedrooms": 31.7,
        "Education": 4.8,
        "Sports": 50.9,
        "Retail": 2.2,
        "Accommodation": 31.7
    }
}
```

#### 10.1.3 Schedule Templates
```python
schedule_templates = {
    "residential": {
        "occupancy": {
            "weekday": [
                (0, 6, 1.0),    # Night - full occupancy
                (6, 8, 0.5),    # Morning - partial
                (8, 18, 0.2),   # Day - mostly away
                (18, 22, 0.8),  # Evening - mostly home
                (22, 24, 1.0)   # Night - full occupancy
            ],
            "weekend": [
                (0, 8, 1.0),    # Sleep in
                (8, 10, 0.8),   # Morning
                (10, 18, 0.6),  # Day activities
                (18, 23, 0.9),  # Evening
                (23, 24, 1.0)   # Night
            ]
        }
    },
    "office": {
        "occupancy": {
            "weekday": [
                (0, 7, 0.0),    # Closed
                (7, 9, 0.5),    # Arrival
                (9, 12, 0.95),  # Morning work
                (12, 13, 0.5),  # Lunch
                (13, 17, 0.95), # Afternoon work
                (17, 19, 0.3),  # Departure
                (19, 24, 0.05)  # Cleaning/security
            ],
            "weekend": [
                (0, 24, 0.0)    # Closed
            ]
        }
    }
}
```

### 10.2 Parameter Range Management

#### 10.2.1 Range Selection Strategy
```python
def pick_value_from_range(range_tuple, strategy="A", random_seed=None):
    """
    Select value from range based on strategy.
    
    Strategies:
    - A: Midpoint (deterministic)
    - B: Random uniform
    - C: Random normal (centered at midpoint)
    - D: Latin Hypercube Sample point
    """
    min_val, max_val = range_tuple
    
    if strategy == "A":
        # Midpoint - most common for initial runs
        return (min_val + max_val) / 2.0
        
    elif strategy == "B":
        # Random uniform
        if random_seed:
            np.random.seed(random_seed)
        return np.random.uniform(min_val, max_val)
        
    elif strategy == "C":
        # Random normal, truncated to range
        if random_seed:
            np.random.seed(random_seed)
        mean = (min_val + max_val) / 2.0
        std = (max_val - min_val) / 6.0  # 99.7% within range
        value = np.random.normal(mean, std)
        return np.clip(value, min_val, max_val)
        
    elif strategy == "D":
        # Would need position in LHS sequence
        return min_val  # Placeholder
        
    else:
        # Default to minimum
        return min_val
```

### 10.3 Zone Naming Convention
```python
def generate_zone_name(floor_num, zone_type, orientation=None):
    """
    Generate consistent zone names.
    
    Examples:
    - Zone1_North (floor 1, north perimeter)
    - Zone2_Core (floor 2, core zone)
    - Zone1 (single zone building)
    """
    if zone_type == "single":
        return f"Zone{floor_num}"
    elif zone_type == "perimeter":
        return f"Zone{floor_num}_{orientation}"
    elif zone_type == "core":
        return f"Zone{floor_num}_Core"
    else:
        return f"Zone{floor_num}_{zone_type}"
```

---

## 11. Mathematical Formulas and Calculations

### 11.1 Thermal Calculations

#### 11.1.1 U-Value to R-Value Conversion
```python
def u_to_r_value(u_value):
    """Convert U-value (W/m²K) to R-value (m²K/W)"""
    return 1.0 / u_value

def r_to_u_value(r_value):
    """Convert R-value (m²K/W) to U-value (W/m²K)"""
    return 1.0 / r_value
```

#### 11.1.2 Construction U-Value Calculation
```python
def calculate_construction_u_value(layers):
    """
    Calculate overall U-value for multi-layer construction.
    
    layers: List of (thickness_m, conductivity_W_per_mK)
    """
    total_resistance = 0.0
    
    # Add surface resistances (typical values)
    r_inside = 0.13   # m²K/W (still air)
    r_outside = 0.04  # m²K/W (moving air)
    total_resistance += r_inside + r_outside
    
    # Add layer resistances
    for thickness, conductivity in layers:
        resistance = thickness / conductivity
        total_resistance += resistance
    
    u_value = 1.0 / total_resistance
    return u_value
```

### 11.2 Geometry Calculations

#### 11.2.1 Polygon Area (Shoelace Formula)
```python
def polygon_area(vertices):
    """
    Calculate area of polygon using shoelace formula.
    vertices: List of (x, y) tuples
    """
    n = len(vertices)
    area = 0.0
    
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    
    return abs(area) / 2.0
```

#### 11.2.2 Polygon Centroid
```python
def polygon_centroid(vertices):
    """
    Calculate centroid of polygon.
    """
    n = len(vertices)
    cx = 0.0
    cy = 0.0
    area = polygon_area(vertices)
    
    for i in range(n):
        j = (i + 1) % n
        factor = vertices[i][0] * vertices[j][1] - vertices[j][0] * vertices[i][1]
        cx += (vertices[i][0] + vertices[j][0]) * factor
        cy += (vertices[i][1] + vertices[j][1]) * factor
    
    cx /= (6.0 * area)
    cy /= (6.0 * area)
    
    return cx, cy
```

#### 11.2.3 Inward Polygon Offset
```python
def inward_offset_polygon(vertices, offset_distance):
    """
    Create inward offset of polygon for core zone creation.
    Uses vector perpendicular to each edge.
    """
    n = len(vertices)
    offset_vertices = []
    
    for i in range(n):
        # Get three consecutive vertices
        prev_idx = (i - 1) % n
        next_idx = (i + 1) % n
        
        v_prev = vertices[prev_idx]
        v_curr = vertices[i]
        v_next = vertices[next_idx]
        
        # Edge vectors
        edge1 = (v_curr[0] - v_prev[0], v_curr[1] - v_prev[1])
        edge2 = (v_next[0] - v_curr[0], v_next[1] - v_curr[1])
        
        # Perpendicular vectors (inward)
        perp1 = (-edge1[1], edge1[0])
        perp2 = (-edge2[1], edge2[0])
        
        # Normalize
        len1 = math.sqrt(perp1[0]**2 + perp1[1]**2)
        len2 = math.sqrt(perp2[0]**2 + perp2[1]**2)
        
        perp1 = (perp1[0]/len1, perp1[1]/len1)
        perp2 = (perp2[0]/len2, perp2[1]/len2)
        
        # Average direction
        avg_x = (perp1[0] + perp2[0]) / 2.0
        avg_y = (perp1[1] + perp2[1]) / 2.0
        
        # Offset vertex
        new_x = v_curr[0] + avg_x * offset_distance
        new_y = v_curr[1] + avg_y * offset_distance
        
        offset_vertices.append((new_x, new_y, v_curr[2]))  # Keep Z
    
    return offset_vertices
```

### 11.3 Energy Calculations

#### 11.3.1 DHW Energy Requirements
```python
def calculate_dhw_energy(volume_liters, temp_rise_c, efficiency=0.8):
    """
    Calculate energy needed to heat water.
    
    Q = m * c * ΔT / η
    where:
    - m = mass of water (kg) = volume (L) * 1 kg/L
    - c = specific heat of water = 4.186 kJ/kg·K
    - ΔT = temperature rise (K)
    - η = heater efficiency
    """
    mass_kg = volume_liters * 1.0  # 1 L = 1 kg for water
    specific_heat = 4.186  # kJ/kg·K
    
    energy_kj = mass_kg * specific_heat * temp_rise_c
    energy_kwh = energy_kj / 3600.0  # Convert kJ to kWh
    
    # Account for efficiency
    energy_required = energy_kwh / efficiency
    
    return energy_required
```

#### 11.3.2 Annual Energy Intensity
```python
def calculate_energy_intensity(total_energy_kwh, floor_area_m2, 
                             hours_operated=8760):
    """
    Calculate energy use intensity (EUI).
    """
    # Annual intensity
    eui_annual = total_energy_kwh / floor_area_m2  # kWh/m²/year
    
    # Power density
    power_density = total_energy_kwh / hours_operated  # kW
    power_density_m2 = power_density / floor_area_m2   # W/m²
    
    return {
        'EUI_kWh_m2_year': eui_annual,
        'power_density_W_m2': power_density_m2 * 1000
    }
```

### 11.4 Statistical Calculations

#### 11.4.1 Weighted RMSE
```python
def weighted_rmse(predicted, actual, weights=None):
    """
    Calculate weighted RMSE, useful for emphasizing peak periods.
    """
    if weights is None:
        weights = np.ones_like(predicted)
    
    weighted_errors = weights * (predicted - actual)**2
    wmse = np.sum(weighted_errors) / np.sum(weights)
    wrmse = np.sqrt(wmse)
    
    return wrmse
```

#### 11.4.2 Time-of-Use Weights
```python
def create_tou_weights(timestamps, peak_hours=(14, 18), 
                      peak_weight=3.0, off_peak_weight=1.0):
    """
    Create time-of-use weights for validation.
    """
    weights = np.ones(len(timestamps)) * off_peak_weight
    
    for i, ts in enumerate(timestamps):
        if peak_hours[0] <= ts.hour < peak_hours[1]:
            weights[i] = peak_weight
    
    return weights
```

---

## 12. File Formats and I/O Operations

### 12.1 Parquet File Operations

#### 12.1.1 Writing Parquet with Compression
```python
def save_to_parquet(df, filepath, compression='snappy'):
    """
    Save DataFrame to Parquet with optimization.
    """
    # Optimize data types
    df_optimized = optimize_dataframe_types(df)
    
    # Save with compression
    df_optimized.to_parquet(
        filepath,
        engine='pyarrow',
        compression=compression,
        index=False,
        use_dictionary=True,  # Dictionary encoding for strings
        row_group_size=50000  # Optimize for query performance
    )
```

#### 12.1.2 Parquet Schema Definition
```python
def create_parquet_schema():
    """
    Define schema for time series parquet files.
    """
    import pyarrow as pa
    
    schema = pa.schema([
        ('building_id', pa.string()),
        ('zone', pa.string()),
        ('variable_name', pa.string()),
        ('units', pa.string()),
        ('frequency', pa.string()),
        ('category', pa.string()),
        # Date columns as float64 for flexibility
        ('2020-01-01', pa.float64()),
        ('2020-01-02', pa.float64()),
        # ... more date columns
    ])
    
    return schema
```

### 12.2 Configuration File Formats

#### 12.2.1 Main Configuration Schema
```python
main_config_schema = {
    "type": "object",
    "properties": {
        "use_database": {"type": "boolean"},
        "db_filter": {
            "type": "object",
            "properties": {
                "pand_ids": {"type": "array", "items": {"type": "string"}},
                "bbox_xy": {"type": "array", "items": {"type": "number"}},
                "meestvoorkomendepostcode": {"type": "array", "items": {"type": "string"}}
            }
        },
        "filter_by": {"type": "string", "enum": ["pand_ids", "bbox_xy", "meestvoorkomendepostcode"]},
        "paths": {
            "type": "object",
            "properties": {
                "building_data": {"type": "string"},
                "dhw_excel": {"type": "string"},
                "epw_excel": {"type": "string"}
            }
        },
        "idf_creation": {
            "type": "object",
            "properties": {
                "perform_idf_creation": {"type": "boolean"},
                "scenario": {"type": "string"},
                "calibration_stage": {"type": "string"},
                "strategy": {"type": "string", "enum": ["A", "B", "C"]},
                "random_seed": {"type": "integer"},
                "run_simulations": {"type": "boolean"}
            }
        }
    },
    "required": ["filter_by"]
}
```

### 12.3 Log File Formats

#### 12.3.1 Assignment Log Structure
```python
def create_assignment_log_entry(building_id, parameter_name, 
                               assigned_value, range_used=None, 
                               override_source=None):
    """
    Create structured log entry for parameter assignments.
    """
    entry = {
        "building_id": building_id,
        "parameter": parameter_name,
        "assigned_value": assigned_value,
        "timestamp": datetime.now().isoformat()
    }
    
    if range_used:
        entry["range_min"] = range_used[0]
        entry["range_max"] = range_used[1]
        
    if override_source:
        entry["override_source"] = override_source  # "excel", "json", "default"
    
    return entry
```

#### 12.3.2 Consolidated Assignment CSV
```python
def save_assignment_logs(all_logs, output_path):
    """
    Save all parameter assignments to CSV for validation.
    """
    records = []
    
    for log_type, log_dict in all_logs.items():
        for building_id, params in log_dict.items():
            for param_name, value in params.items():
                record = {
                    'building_id': building_id,
                    'log_type': log_type,
                    'parameter': param_name,
                    'value': value
                }
                records.append(record)
    
    df_logs = pd.DataFrame(records)
    df_logs.to_csv(output_path, index=False)
```

### 12.4 Error Handling and Recovery

#### 12.4.1 Partial Result Saving
```python
def save_partial_results(results_so_far, checkpoint_path, job_id):
    """
    Save intermediate results for recovery.
    """
    checkpoint = {
        'job_id': job_id,
        'timestamp': datetime.now().isoformat(),
        'completed_buildings': results_so_far.get('completed', []),
        'failed_buildings': results_so_far.get('failed', []),
        'partial_data': results_so_far.get('data', {}),
        'last_successful_step': results_so_far.get('last_step', 'unknown')
    }
    
    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint, f, indent=2)
```

#### 12.4.2 Recovery from Checkpoint
```python
def recover_from_checkpoint(checkpoint_path, df_buildings):
    """
    Resume processing from saved checkpoint.
    """
    if not os.path.exists(checkpoint_path):
        return df_buildings, 0
    
    with open(checkpoint_path, 'r') as f:
        checkpoint = json.load(f)
    
    completed = set(checkpoint['completed_buildings'])
    
    # Filter to only uncompleted buildings
    df_remaining = df_buildings[
        ~df_buildings['ogc_fid'].astype(str).isin(completed)
    ]
    
    start_index = len(completed)
    
    return df_remaining, start_index
```

---

## Summary

This comprehensive documentation covers the entire E_Plus_2040_py system from input to output, including:

1. **Entry Points**: HTTP API with job management
2. **Data Flow**: JSON → Configuration → Building Data → IDF → Simulation → Parsing → Analysis
3. **Key Algorithms**: Parameter assignment strategies, geometry calculations, optimization methods
4. **Data Structures**: Lookup dictionaries, schedules, validation metrics
5. **Mathematical Formulas**: Thermal calculations, statistics, geometry
6. **File Formats**: Parquet for time series, JSON for configuration, SQL for simulation output

The system is designed for:
- **Scalability**: Parallel processing, job queuing
- **Flexibility**: Multiple override levels, configurable strategies
- **Traceability**: Comprehensive logging of all assignments
- **Robustness**: Error handling, checkpointing, validation

Each component is modular and can be extended or modified independently while maintaining the overall workflow integrity.