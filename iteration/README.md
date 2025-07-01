# Calibration Iteration System

This module provides an automated iteration system for the E_Plus_2040 calibration workflow, enabling iterative parameter optimization with convergence control and human intervention capabilities.

## Overview

The iteration system manages the complete cycle of:
1. **Parameter Lookup** → Initial parameters from configuration
2. **IDF Creation** → Building model generation with parameters
3. **Simulation** → EnergyPlus execution
4. **Parsing** → Result extraction to parquet format
5. **Validation** → Comparison with measured data
6. **Calibration** → Parameter optimization
7. **Feedback Loop** → Apply optimized parameters to next iteration

## Key Components

### 1. Iteration Controller (`iteration_controller.py`)
- Manages iteration lifecycle
- Implements convergence checking
- Handles state persistence for resumable workflows
- Supports multiple iteration strategies

### 2. Parameter Feedback (`parameter_feedback.py`)
- Converts calibration results to modification inputs
- Maps parameters between components
- Tracks parameter evolution
- Analyzes parameter sensitivity

### 3. Iteration Strategies (`iteration_strategies.py`)
- **Fixed Iterations**: Run specified number of iterations
- **Convergence-Based**: Stop when convergence criteria met
- **Adaptive**: Balances exploration and exploitation
- **Human-Guided**: Incorporates human decisions
- **Hybrid**: Combines multiple strategies

### 4. Parameter Store (`parameter_store.py`)
- Versioned parameter storage
- Parameter lineage tracking
- Checkpoint/restore functionality
- Comparison tools

### 5. Orchestrator Integration (`orchestrator_integration.py`)
- Seamlessly integrates with existing workflow
- Manages data flow between iterations
- Handles workflow configuration updates

## Configuration

Add to your `main_config.json`:

```json
{
  "iteration": {
    "enabled": true,
    "strategy": "adaptive",
    "max_iterations": 10,
    "min_iterations": 3,
    "convergence_tolerance": 0.01,
    "convergence_metric": "cv_rmse",
    "learning_rate": 0.1,
    "human_review_threshold": 0.15,
    "store_all_iterations": true
  }
}
```

### Configuration Options

- `enabled`: Enable/disable iteration system
- `strategy`: Iteration strategy to use
- `max_iterations`: Maximum number of iterations
- `min_iterations`: Minimum iterations before convergence check
- `convergence_tolerance`: Threshold for convergence
- `convergence_metric`: Metric to use for convergence (cv_rmse, rmse, nmbe, r2)
- `learning_rate`: Parameter adaptation rate
- `human_review_threshold`: Trigger human review when metric exceeds this
- `store_all_iterations`: Keep all iteration data

## Usage Example

### Basic Usage

```python
from iteration import IterationController, ParameterFeedback, ParameterStore

# Initialize components
controller = IterationController(job_id="my_job", config_path="config.json")
feedback = ParameterFeedback(job_id="my_job")
param_store = ParameterStore(job_id="my_job")

# Run iteration loop
while controller.should_continue():
    # Start iteration
    iter_info = controller.start_iteration()
    
    # Run your workflow with parameters
    results = run_workflow(iter_info['parameters'])
    
    # Extract metrics
    metrics = {
        'cv_rmse': results['cv_rmse'],
        'rmse': results['rmse'],
        'r2': results['r2']
    }
    
    # Store and complete iteration
    param_store.store_parameters(
        iteration_id=iter_info['iteration'],
        parameters=iter_info['parameters'],
        metrics=metrics
    )
    
    controller.complete_iteration(metrics, iter_info['parameters'])

# Get results
summary = controller.get_summary()
best_params = param_store.get_best_version()
```

### Integration with Orchestrator

The system automatically integrates with the existing orchestrator when enabled in configuration:

```python
# In your main orchestrator
from iteration.orchestrator_integration import integrate_iteration_system

@integrate_iteration_system
def orchestrate_workflow(job_config, cancel_event=None):
    # Your existing orchestrator code
    pass
```

## Data Flow

```
Initial Parameters
    ↓
┌─────────────────────────────────────┐
│      ITERATION CONTROLLER           │
│  • Manages iteration lifecycle      │
│  • Checks convergence              │
│  • Handles state persistence       │
└─────────────────────────────────────┘
    ↓                      ↑
┌─────────────────┐    ┌─────────────────┐
│ PARAMETER STORE │    │ PARAMETER       │
│ • Version control│    │ FEEDBACK        │
│ • History track │    │ • Convert results│
└─────────────────┘    └─────────────────┘
    ↓                      ↑
┌─────────────────────────────────────┐
│         WORKFLOW EXECUTION          │
│  IDF → Simulation → Parse → Valid  │
└─────────────────────────────────────┘
```

## Output Structure

```
iterations/
├── {job_id}/
│   ├── iteration_state.json          # Current state
│   ├── parameter_store/              # Versioned parameters
│   │   ├── parameter_index.json      # Parameter index
│   │   ├── parameter_lineage.json    # Version relationships
│   │   └── versions/                 # Individual versions
│   ├── iteration_001/
│   │   ├── iteration_config.json     # Iteration configuration
│   │   ├── parameters.json           # Used parameters
│   │   ├── metrics.json              # Results metrics
│   │   └── modification_configs/     # Generated configs
│   │       ├── calibration_scenario.json
│   │       ├── envelope_modifications.json
│   │       ├── fenestration_modifications.json
│   │       └── hvac_modifications.json
│   └── iteration_summary.json        # Final summary
```

## Iteration Strategies

### Fixed Iterations
Runs a predetermined number of iterations regardless of performance.

### Convergence-Based
Stops when the change in the selected metric falls below the tolerance threshold.

### Adaptive
Dynamically adjusts parameter changes based on performance trends:
- **Exploration phase**: Larger parameter changes when stagnating
- **Exploitation phase**: Fine-tuning when close to optimum

### Human-Guided
Requests human input at key decision points:
- When performance is below threshold
- At regular intervals for review
- For critical parameter changes

### Hybrid
Combines multiple strategies, switching based on performance.

## Parameter Mapping

The system automatically maps calibration parameters to IDF modifications:

| Calibration Parameter | IDF Object | Field |
|----------------------|------------|-------|
| infiltration_rate | ZoneInfiltration:DesignFlowRate | Flow per Exterior Surface Area |
| window_u_value | WindowMaterial:SimpleGlazingSystem | U-Factor |
| wall_insulation | Material | Thickness |
| hvac_efficiency | Coil:Heating:Gas | Gas Burner Efficiency |
| cooling_cop | Coil:Cooling:DX:SingleSpeed | Rated COP |
| lighting_power_density | Lights | Watts per Zone Floor Area |

## Advanced Features

### State Persistence
- Iterations can be paused and resumed
- Full state saved after each iteration
- Crash recovery supported

### Parameter Evolution Tracking
- Track how parameters change over iterations
- Sensitivity analysis of parameters
- Export evolution history

### Checkpointing
```python
# Create checkpoint
param_store.create_checkpoint(version_id, "checkpoint_name")

# Restore from checkpoint
restored = param_store.restore_checkpoint("checkpoint_name")
```

### Comparison Tools
```python
# Compare two parameter versions
comparison = param_store.compare_versions("v001_abc", "v005_xyz")

# Export parameter evolution
param_store.export_parameter_evolution("evolution.csv")
```

## Testing

Run the test suite:
```bash
python test_iteration/test_iteration_system.py
```

This will:
- Test all iteration strategies
- Generate sample results
- Create visualization plots
- Validate convergence behavior

## Troubleshooting

### Common Issues

1. **Convergence not achieved**
   - Increase `max_iterations`
   - Adjust `convergence_tolerance`
   - Check if parameters are properly constrained

2. **Parameters not updating**
   - Verify parameter mapping in `parameter_feedback.py`
   - Check modification configs are generated correctly
   - Ensure workflow is using updated parameters

3. **State recovery fails**
   - Check `iteration_state.json` exists
   - Verify file permissions
   - Clear corrupted state and restart

## Future Enhancements

- Multi-objective optimization support
- Parallel iteration execution
- Machine learning-based parameter prediction
- Web interface for human review
- Integration with cloud computing resources