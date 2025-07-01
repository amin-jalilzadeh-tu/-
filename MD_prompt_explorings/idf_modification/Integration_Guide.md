# IDF Modification System Integration Guide

## Overview

This guide explains how the IDF modification system integrates with other components of the E_Plus_2040_py workflow, including the orchestrator, parsing system, and analysis tools.

## Integration Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   IDF Creation  │────▶│  IDF Modification │────▶│   Simulation    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                           │
                               ▼                           ▼
                        ┌──────────────────┐       ┌─────────────────┐
                        │     Parsing      │◀──────│     Results     │
                        └──────────────────┘       └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │    Analysis      │
                        │  - Calibration   │
                        │  - Sensitivity   │
                        │  - Validation    │
                        └──────────────────┘
```

## Orchestrator Integration

### 1. Configuration Flow

The orchestrator passes configuration to the modification system:

```python
# In orchestrator/main.py
config = {
    "modification": {
        "modification_strategy": {
            "type": "scenarios",
            "scenarios": ["high_efficiency"],
            "num_variants": 5
        },
        "categories_to_modify": {
            "hvac": {"enabled": True, "strategy": "high_efficiency"},
            "envelope": {"enabled": True, "strategy": "super_insulation"}
        },
        "base_idf_selection": {
            "criteria": "all",
            "building_ids": None
        },
        "output_options": {
            "save_modified_idfs": True,
            "track_modifications": True,
            "report_formats": ["json", "parquet"]
        }
    }
}

# Call modification step
modification_results = run_modification(
    modification_cfg=config['modification'],
    job_output_dir=output_dir,
    job_idf_dir=idf_dir,
    logger=logger
)
```

### 2. Output Structure

The modification step returns:

```python
modification_results = {
    "success": True,
    "modified_buildings": [
        {
            "building_id": "4136733",
            "variants": [
                {
                    "variant_id": "variant_0",
                    "idf_path": "modified_idfs/building_4136733_variant_0.idf",
                    "modifications_count": 25,
                    "categories_modified": ["hvac", "envelope"]
                }
            ]
        }
    ],
    "tracking_files": {
        "json_report": "modification_report_20250107_103000.json",
        "parquet_files": [
            "modifications_detail_wide_20250107_103000.parquet",
            "parameter_changes_20250107_103000.parquet"
        ]
    },
    "summary": {
        "total_buildings": 5,
        "total_variants": 25,
        "total_modifications": 625
    }
}
```

### 3. Error Handling

```python
try:
    results = run_modification(modification_cfg, output_dir, idf_dir, logger)
    if results and results['success']:
        logger.info(f"Modified {results['summary']['total_variants']} variants")
    else:
        logger.error("Modification step failed")
        return None
except Exception as e:
    logger.error(f"Modification error: {str(e)}")
    return None
```

## Parsing System Integration

### 1. Input from Parser

The modification system receives parsed IDF data:

```python
# Parser output format
parsed_data = {
    "building_id": "4136733",
    "version": "24.1",
    "objects": {
        "COIL:COOLING:DX:SINGLESPEED": [
            {
                "object_type": "COIL:COOLING:DX:SINGLESPEED",
                "name": "Main Cooling Coil 1",
                "fields": [...],
                "field_names": [...],
                "zone_reference": "Zone 1"
            }
        ]
    },
    "metadata": {
        "parse_timestamp": "2025-01-07T10:00:00",
        "parser_version": "1.0"
    }
}
```

### 2. Parser Compatibility

The modification system maintains parser structure:

```python
def modify_parsed_objects(self, parsed_objects: dict) -> dict:
    """Modify while maintaining parser structure"""
    
    modified_objects = deepcopy(parsed_objects)
    
    for object_type, objects_list in modified_objects['objects'].items():
        for obj in objects_list:
            # Modifications preserve structure
            self.apply_modifications(obj)
            
    # Update metadata
    modified_objects['metadata']['modification_timestamp'] = datetime.now()
    modified_objects['metadata']['modification_version'] = self.version
    
    return modified_objects
```

### 3. Writing Modified IDFs

```python
def write_parsed_objects_to_idf(self, parsed_objects: dict, 
                               output_path: Path):
    """Write modified parsed objects back to IDF format"""
    
    with open(output_path, 'w') as f:
        # Write header
        f.write("!-Generator IDFEditor 1.51\n")
        f.write(f"!-Option SortedOrder\n")
        f.write(f"!-Modified by E_Plus_2040_py Modification System\n\n")
        
        # Write version
        f.write(f"VERSION,{parsed_objects['version']};\n\n")
        
        # Write objects in correct order
        for object_type in self.get_object_order():
            if object_type in parsed_objects['objects']:
                for obj in parsed_objects['objects'][object_type]:
                    self.write_object(f, obj)
```

## Calibration System Integration

### 1. Parameter Selection

Calibration uses modification tracking to select parameters:

```python
# In calibration system
def select_calibration_parameters(modification_tracking):
    """Select parameters based on modification history"""
    
    # Get frequently modified parameters
    param_counts = modification_tracking.groupby('parameter').size()
    frequent_params = param_counts[param_counts > 5].index
    
    # Get high-impact parameters
    impact_analysis = analyze_parameter_impact(modification_tracking)
    high_impact_params = impact_analysis[impact_analysis['impact'] > 0.1].index
    
    # Combine for calibration
    calibration_params = list(set(frequent_params) | set(high_impact_params))
    
    return calibration_params
```

### 2. Calibration Workflow

```python
# Calibration workflow using modifications
calibration_config = {
    "parameters_to_calibrate": [
        {
            "category": "hvac",
            "parameter": "cooling_cop",
            "bounds": [3.0, 5.0],
            "initial_value": 4.0
        }
    ],
    "modification_strategy": {
        "type": "optimization",
        "algorithm": "bayesian",
        "objective": "minimize_rmse"
    }
}

# Run calibration with modifications
for iteration in range(max_iterations):
    # Generate parameter values
    param_values = optimizer.suggest_parameters()
    
    # Apply modifications
    modification_results = apply_calibration_modifications(
        base_idf, param_values
    )
    
    # Simulate and evaluate
    simulation_results = run_simulation(modification_results['idf_path'])
    error = calculate_error(simulation_results, measured_data)
    
    # Update optimizer
    optimizer.update(param_values, error)
```

## Sensitivity Analysis Integration

### 1. Parameter Space Definition

```python
# Use modification registry for sensitivity analysis
from idf_modification.parameter_registry import PARAMETER_REGISTRY

def create_sensitivity_space():
    """Create parameter space from modification system"""
    
    parameter_space = {}
    
    for category, params in PARAMETER_REGISTRY.items():
        for param_name, param_def in params.items():
            parameter_space[f"{category}_{param_name}"] = {
                'bounds': [param_def['min_value'], param_def['max_value']],
                'distribution': 'uniform',
                'units': param_def['units']
            }
    
    return parameter_space
```

### 2. Sensitivity Workflow

```python
# Sensitivity analysis workflow
sensitivity_config = {
    "method": "morris",
    "parameters": parameter_space,
    "num_samples": 100,
    "modification_strategy": {
        "type": "sampling",
        "method": "morris_trajectories"
    }
}

# Generate sensitivity variants
variants = []
for trajectory in morris_trajectories:
    modification_results = apply_sensitivity_modifications(
        base_idf, trajectory
    )
    variants.append(modification_results)

# Analyze results
sensitivity_indices = calculate_sensitivity_indices(variants)
```

## Surrogate Model Integration

### 1. Training Data Generation

```python
# Generate training data using modifications
def generate_surrogate_training_data(n_samples=1000):
    """Generate diverse building variants for surrogate training"""
    
    training_configs = []
    
    for i in range(n_samples):
        # Random parameter selection
        config = {
            "modification_strategy": {
                "type": "sampling",
                "method": "latin_hypercube",
                "num_variants": 1
            },
            "categories_to_modify": {
                category: {
                    "enabled": True,
                    "parameters": select_random_parameters(category)
                }
                for category in ['hvac', 'envelope', 'lighting']
            }
        }
        training_configs.append(config)
    
    return training_configs
```

### 2. Feature Extraction

```python
# Extract features from modification tracking
def extract_surrogate_features(modification_tracking):
    """Extract features for surrogate model"""
    
    features = {}
    
    # Parameter values
    param_values = modification_tracking.pivot(
        index='building_id',
        columns='parameter',
        values='new_value'
    )
    features.update(param_values.to_dict('records')[0])
    
    # Derived features
    features['total_envelope_r'] = calculate_total_r_value(modification_tracking)
    features['hvac_efficiency_score'] = calculate_hvac_score(modification_tracking)
    
    return features
```

## Data Flow Between Systems

### 1. Forward Flow
```
IDF Creation → Base IDF Files
                    ↓
            Modification System
                    ↓
            Modified IDF Files
                    ↓
               Simulation
                    ↓
             Results (SQL)
                    ↓
               Parsing
                    ↓
        Analysis (Cal/Sens/Val)
```

### 2. Feedback Flow
```
Analysis Results
        ↓
New Parameter Values
        ↓
Modification System
        ↓
Updated Variants
```

### 3. Tracking Flow
```
Every Modification
        ↓
Tracking System
        ↓
Multiple Output Formats
        ↓
All Analysis Systems
```

## Best Practices for Integration

### 1. Configuration Management
```python
# Centralized configuration
class ModificationConfigManager:
    def __init__(self, base_config):
        self.base_config = base_config
        
    def get_config_for_step(self, step_name):
        """Get configuration for specific workflow step"""
        if step_name == 'calibration':
            return self.adapt_for_calibration()
        elif step_name == 'sensitivity':
            return self.adapt_for_sensitivity()
```

### 2. Error Propagation
```python
# Consistent error handling across systems
class ModificationError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}
        
    def to_dict(self):
        return {
            'error': str(self),
            'details': self.details,
            'timestamp': datetime.now().isoformat()
        }
```

### 3. Performance Optimization
```python
# Batch processing for efficiency
def batch_modify_buildings(building_ids, modification_config):
    """Modify multiple buildings in parallel"""
    
    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(
                modify_single_building, 
                bid, 
                modification_config
            ): bid 
            for bid in building_ids
        }
        
        results = {}
        for future in as_completed(futures):
            building_id = futures[future]
            try:
                results[building_id] = future.result()
            except Exception as e:
                logger.error(f"Failed to modify {building_id}: {e}")
                
    return results
```

## Monitoring and Debugging

### 1. Logging Integration
```python
# Structured logging for tracking
logger.info("Modification started", extra={
    'building_id': building_id,
    'variant_id': variant_id,
    'strategy': strategy,
    'categories': categories
})
```

### 2. Performance Metrics
```python
# Track modification performance
metrics = {
    'modification_time': end_time - start_time,
    'objects_modified': len(modified_objects),
    'validation_time': validation_duration,
    'file_write_time': write_duration
}
```

### 3. Debugging Tools
```python
# Debug modification issues
def debug_modification_failure(building_id, error):
    """Detailed debugging for failed modifications"""
    
    debug_info = {
        'building_id': building_id,
        'error': str(error),
        'traceback': traceback.format_exc(),
        'parsed_objects': get_parsed_objects_summary(building_id),
        'modification_history': get_modification_history(building_id)
    }
    
    save_debug_report(debug_info)
```