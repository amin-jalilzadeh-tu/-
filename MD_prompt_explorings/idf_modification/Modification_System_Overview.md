# IDF Modification System Overview

## Purpose

The IDF Modification System is a comprehensive framework for programmatically modifying EnergyPlus Input Data Files (IDF) to create building variants. It serves as the engine for calibration, sensitivity analysis, optimization studies, and scenario development.

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Layer                        │
│                 (modification_step.py)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  ModificationEngine                          │
│              (modification_engine.py)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • Load configuration                                │    │
│  │ • Select buildings                                  │    │
│  │ • Coordinate modifiers                              │    │
│  │ • Track modifications                               │    │
│  │ • Generate reports                                  │    │
│  └─────────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                Category-Specific Modifiers                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │   HVAC   │ │ Materials│ │ Lighting │ │Equipment │ ...  │
│  │ Modifier │ │ Modifier │ │ Modifier │ │ Modifier │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Support Systems                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ Parameter    │ │ Modification │ │   Rules &    │       │
│  │  Registry    │ │   Tracker    │ │ Validation   │       │
│  └──────────────┘ └──────────────┘ └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Key Classes and Their Responsibilities

### 1. ModificationEngine (`modification_engine.py`)

The central orchestrator of the modification system.

**Responsibilities:**
- Load and validate configuration
- Select IDF files based on criteria
- Coordinate multiple modifiers
- Apply modification strategies
- Generate variants
- Track all modifications
- Produce reports

**Key Methods:**
```python
class ModificationEngine:
    def __init__(self, project_dir: Path, config: dict):
        """Initialize with project directory and configuration"""
        
    def modify_building(self, building_id: str, idf_path: str, 
                       parameter_values: dict, variant_id: str) -> dict:
        """Apply modifications to a single building"""
        
    def write_parsed_objects_to_idf(self, parsed_objects: dict, 
                                   output_path: Path, building_data: dict):
        """Write modified objects back to IDF format"""
```

### 2. BaseModifier (`base_modifier.py`)

Abstract base class providing common functionality for all modifiers.

**Key Features:**
- Parameter definition framework
- Common modification methods
- Validation utilities
- Tracking integration

**Template Methods:**
```python
class BaseModifier(ABC):
    @abstractmethod
    def identify_modifiable_parameters(self, parsed_objects: dict) -> dict:
        """Identify parameters that can be modified"""
        
    @abstractmethod
    def apply_modifications(self, parsed_objects: dict, 
                          modifiable_params: dict, strategy: str) -> list:
        """Apply modifications based on strategy"""
        
    def validate_modification(self, param: ParameterDefinition, 
                            new_value: Any) -> bool:
        """Validate a proposed modification"""
```

### 3. ModificationConfig (`modification_config.py`)

Configuration management and validation.

**Configuration Schema:**
```json
{
  "modification": {
    "modification_strategy": {
      "type": "scenarios|sampling|optimization",
      "scenarios": ["baseline", "high_performance"],
      "num_variants": 5,
      "seed": 42
    },
    "base_idf_selection": {
      "criteria": "all|specific|pattern",
      "building_ids": ["4136733", "4136734"],
      "pattern": "building_*.idf"
    },
    "categories_to_modify": {
      "hvac": {
        "enabled": true,
        "strategy": "high_efficiency",
        "parameters": {}
      }
    },
    "output_options": {
      "save_modified_idfs": true,
      "track_modifications": true,
      "report_formats": ["json", "parquet", "csv", "html"],
      "output_directory": "modified_idfs"
    }
  }
}
```

### 4. ModificationTracker (`modification_tracker.py`)

Tracks all modifications made during the process.

**Tracking Data Structure:**
```python
{
    "building_id": "4136733",
    "variant_id": "variant_0",
    "timestamp": "2025-01-07T10:30:00",
    "modifications": [
        {
            "category": "hvac",
            "object_type": "COIL:COOLING:DX:SINGLESPEED",
            "object_name": "Main Cooling Coil",
            "field_name": "Gross Rated COP",
            "original_value": 3.5,
            "new_value": 4.5,
            "change_percentage": 28.57,
            "modification_rule": "high_efficiency",
            "validation_status": "valid"
        }
    ]
}
```

## Data Flow

### 1. Input Processing
```
IDF File → Parser → Parsed Objects (dict) → ModificationEngine
```

### 2. Modification Process
```
Parsed Objects → Identify Parameters → Apply Strategy → Modified Objects
```

### 3. Output Generation
```
Modified Objects → IDF Writer → Variant IDF File
                 → Tracker → Modification Reports
```

## Integration Points

### 1. With Parsing System
- Receives parsed IDF data in dictionary format
- Maintains structure compatibility
- Preserves all metadata and references

### 2. With Orchestrator
- Called via `run_modification()` in modification_step.py
- Returns modification results and file paths
- Provides data for downstream steps

### 3. With Analysis Systems
- Calibration uses modifications to match measured data
- Sensitivity analysis evaluates parameter impacts
- Surrogate models learn from modification results

## File Management

### Input Files
```
job_idf_dir/
├── building_4136733.idf    # Base IDF files
├── building_4136734.idf
└── building_4136735.idf
```

### Output Files
```
job_output_dir/
└── modified_idfs/
    ├── building_4136733_variant_0.idf
    ├── building_4136733_variant_1.idf
    ├── modification_report_20250107_103000.json
    ├── modifications_detail_wide_20250107_103000.parquet
    ├── modifications_summary_20250107_103000.parquet
    └── parameter_changes_20250107_103000.parquet
```

## Error Handling

The system implements comprehensive error handling:

1. **Configuration Validation**: Validates all configuration before processing
2. **Parameter Validation**: Ensures modifications meet constraints
3. **IDF Structure Validation**: Maintains valid IDF structure
4. **Graceful Degradation**: Continues with other buildings if one fails
5. **Detailed Logging**: Records all operations and errors

## Performance Considerations

1. **Batch Processing**: Processes multiple buildings in parallel
2. **Memory Efficiency**: Streams large IDF files
3. **Caching**: Reuses parsed data when possible
4. **Lazy Loading**: Loads modifiers only when needed

## Extension Points

The system is designed for extensibility:

1. **New Modifiers**: Add new category modifiers by extending BaseModifier
2. **Custom Strategies**: Implement new modification strategies
3. **Rules Engine**: Add custom validation and dependency rules
4. **Output Formats**: Add new report formats
5. **Integration**: Connect to new analysis systems