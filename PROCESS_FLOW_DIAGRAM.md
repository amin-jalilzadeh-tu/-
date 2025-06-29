# E_Plus_2040_py Process Flow Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (HTTP Requests)                          │
└─────────────────────────────────────────┬───────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FLASK API (app.py)                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────────────┐   │
│  │ POST /jobs  │  │ POST /start  │  │ GET /logs  │  │ GET /results     │   │
│  └──────┬──────┘  └──────┬───────┘  └─────┬──────┘  └────────┬─────────┘   │
│         │                 │                 │                  │              │
│         ▼                 ▼                 ▼                  ▼              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────────────┐   │
│  │Create Job   │  │Enqueue Job   │  │Stream Logs │  │Retrieve Results  │   │
│  └─────────────┘  └──────────────┘  └────────────┘  └──────────────────┘   │
└─────────────────────────────────────────┬───────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          JOB MANAGER (job_manager.py)                        │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────────────┐   │
│  │Job Queue    │  │Thread Pool   │  │Log Queues  │  │Status Tracking   │   │
│  └─────────────┘  └──────────────┘  └────────────┘  └──────────────────┘   │
└─────────────────────────────────────────┬───────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR (orchestrator/main.py)                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Detailed Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INPUT STAGE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Combined JSON ──┬──> splitter.py ──┬──> dhw.json                          │
│                  │                   ├──> epw.json                          │
│                  │                   ├──> main_config.json                  │
│                  │                   ├──> geometry.json                     │
│                  │                   ├──> shading.json                      │
│                  │                   └──> [other configs].json              │
│                  │                                                          │
│                  └──> Job Config ────> job_id, paths, settings              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CONFIGURATION STAGE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  main_config.json ──┬──> Load & Merge ──> Merged Config                    │
│                     │                                                        │
│  Excel Files ───────┼──> Override Functions ──┬──> DHW Lookup              │
│                     │                          ├──> EPW Lookup              │
│                     │                          ├──> Lighting Lookup         │
│                     │                          ├──> HVAC Lookup             │
│                     │                          └──> Ventilation Lookup      │
│                     │                                                        │
│  User JSONs ────────┴──> Apply Overrides ─────> Final Parameters           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BUILDING DATA STAGE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  IF use_database:                                                           │
│    PostgreSQL ──> SQL Query ──> DataFrame                                   │
│                                                                              │
│  ELSE:                                                                       │
│    CSV File ─────────────────> DataFrame                                    │
│                                                                              │
│  DataFrame columns:                                                          │
│    ogc_fid, pand_id, area, perimeter, height,                              │
│    building_orientation, building_function,                                 │
│    residential_type, non_residential_type,                                  │
│    x, y, lat, lon, postcode, age_range, etc.                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            IDF CREATION STAGE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  For Each Building:                                                          │
│                                                                              │
│  Building Data ──┬──> Geometry Creation ──┬──> Zones                       │
│                  │                         ├──> Surfaces                     │
│                  │                         └──> Orientation                  │
│                  │                                                          │
│                  ├──> Fenestration ───────┬──> WWR Assignment              │
│                  │                         └──> Window Objects              │
│                  │                                                          │
│                  ├──> Materials ──────────┬──> Constructions               │
│                  │                         └──> Layer Properties            │
│                  │                                                          │
│                  ├──> HVAC Systems ───────┬──> Ideal Loads                 │
│                  │                         ├──> Schedules                   │
│                  │                         └──> Setpoints                   │
│                  │                                                          │
│                  ├──> Lighting & Equipment                                  │
│                  ├──> DHW Systems                                           │
│                  ├──> Ventilation                                           │
│                  └──> Output Definitions                                     │
│                                                                              │
│  Output: building_N.idf files                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SIMULATION STAGE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  IDF Files ──┬──> EPW Assignment ──> Weather File Selection                │
│              │                                                              │
│              └──> EnergyPlus ──────┬──> SQL Database                      │
│                  (Parallel)         ├──> ESO Time Series                   │
│                                    ├──> CSV Reports                        │
│                                    └──> ERR Logs                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PARSING STAGE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SQL Files ──┬──> SQL Analyzer ────┬──> Time Series Data                  │
│              │                      ├──> Summary Reports                    │
│              │                      └──> Variable Mappings                  │
│              │                                                              │
│  IDF Files ──┴──> IDF Analyzer ────┬──> Zone Mappings                     │
│                                     └──> Output Configurations              │
│                                                                              │
│  Output Format: Parquet Files (columnar, compressed)                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        POST-PROCESSING STAGES                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │ Modification   │  │ Sensitivity    │  │ Surrogate      │               │
│  │ - Variants     │  │ - Parameter    │  │ - ML Models    │               │
│  │ - Re-simulate  │  │   Sampling     │  │ - Predictions  │               │
│  └────────────────┘  │ - Analysis     │  └────────────────┘               │
│                      └────────────────┘                                     │
│                                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │ Calibration    │  │ Validation     │  │ Aggregation    │               │
│  │ - Optimization │  │ - Benchmarks   │  │ - Summaries    │               │
│  │ - Tuning       │  │ - Comparisons  │  │ - Reports      │               │
│  └────────────────┘  └────────────────┘  └────────────────┘               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            OUTPUT STRUCTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  output/<job_id>/                                                           │
│    ├── output_IDFs/              # Generated building models                │
│    ├── simulation_results/       # Raw EnergyPlus outputs                  │
│    │   ├── 2020/                                                           │
│    │   ├── 2030/                                                           │
│    │   └── 2050/                                                           │
│    ├── parser_output/           # Structured data                          │
│    │   ├── timeseries/                                                     │
│    │   ├── comparisons/                                                    │
│    │   └── summaries/                                                      │
│    ├── sensitivity/             # Sensitivity results                      │
│    ├── surrogate/              # ML models                                 │
│    └── logs/                   # Process logs                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Data Transformations

### 1. JSON → Configuration Objects
```
Input:  {"param_name": "value", "min_val": 10, "max_val": 20}
Output: Parameter object with validation and range handling
```

### 2. Building Data → IDF Geometry
```
Input:  area=100m², perimeter=40m, floors=2, height=6m
Output: Zone objects with 3D surfaces and thermal properties
```

### 3. Parameters → Schedules
```
Input:  Occupancy patterns, setpoint ranges
Output: SCHEDULE:COMPACT objects with hourly values
```

### 4. IDF + EPW → Simulation Results
```
Input:  Building model + Weather data
Output: SQLite DB with hourly energy flows
```

### 5. SQL → Parquet
```
Input:  Relational time series data
Output: Columnar format optimized for analytics
```

## Parallel Processing Points

1. **IDF Creation**: Multiple buildings processed independently
2. **Simulations**: Parallel EnergyPlus runs (limited by CPU cores)
3. **Parsing**: Concurrent SQL/IDF file processing
4. **Post-processing**: Independent analysis pipelines

## Error Handling & Recovery

- Job cancellation at any stage via cancel_event
- Partial results saved even if later stages fail
- Comprehensive logging at each transformation
- Input validation before expensive operations