# Basic Iteration Loop Design for E_Plus_2040

## Overview
This document defines the structure for implementing a basic iteration loop that connects data flow from lookup → modify → parse → validate, with iteration control based on validation results.

## Core Concepts

### 1. Iteration Loop Structure
```
Initial Buildings → Base Simulation → Validation
                                           ↓
                                    Select Poor Performers
                                           ↓
                                    Apply Modifications
                                           ↓
                                    Simulate Variants
                                           ↓
                                    Parse & Validate
                                           ↓
                                    Check Convergence → Stop or Continue
```

### 2. Data Flow Per Iteration

#### Iteration 0 (Base Case)
1. **IDF Creation**: Create base IDFs from lookup values
2. **Simulation**: Run base simulations
3. **Parsing**: Extract results to parquet
4. **Validation**: Compare with measured data
5. **Selection**: Identify buildings that fail validation

#### Iteration N (Improvements)
1. **Modification**: Apply strategies to selected buildings
2. **Simulation**: Run modified variants
3. **Parsing**: Extract variant results
4. **Validation**: Check improvement
5. **Decision**: Continue or stop

### 3. File Organization Structure
```
job_output/
├── iterations/
│   ├── iteration_0/
│   │   ├── idfs/
│   │   ├── simulations/
│   │   ├── parsed_data/
│   │   └── validation_results/
│   ├── iteration_1/
│   │   ├── selected_buildings.json
│   │   ├── modification_strategy.json
│   │   ├── idfs/
│   │   ├── simulations/
│   │   ├── parsed_data/
│   │   └── validation_results/
│   └── ...
├── tracking/
│   ├── performance_history.parquet
│   ├── iteration_summary.json
│   └── convergence_metrics.json
└── final_results/
```

## Implementation Plan

### 1. New Module: `iteration_manager.py`
```python
class IterationManager:
    def __init__(self, config, job_output_dir):
        self.config = config
        self.job_output_dir = job_output_dir
        self.current_iteration = 0
        self.performance_history = []
        
    def run_iteration(self):
        """Execute one iteration of the workflow"""
        
    def select_buildings(self, validation_results):
        """Select buildings for next iteration based on performance"""
        
    def check_convergence(self):
        """Check if we should stop iterating"""
        
    def save_iteration_state(self):
        """Save current iteration data and state"""
```

### 2. Update `orchestrator/main.py`
Add iteration loop control:
```python
# After initial validation
if iteration_config.get("enable_iterations", False):
    iteration_manager = IterationManager(main_config, job_output_dir)
    
    while not iteration_manager.check_convergence():
        iteration_manager.run_iteration()
```

### 3. Configuration Structure
Add to `combined.json`:
```json
{
  "iteration_control": {
    "enable_iterations": true,
    "max_iterations": 5,
    "selection_strategy": "validation_failure",
    "selection_count": 10,
    "convergence_criteria": {
      "min_improvement": 0.01,
      "patience": 2
    },
    "modification_progression": {
      "iteration_1": {"intensity": "low"},
      "iteration_2": {"intensity": "medium"},
      "iteration_3": {"intensity": "high"}
    }
  }
}
```

### 4. Building Selection Logic
```python
def select_buildings_for_iteration(validation_results, strategy, count):
    if strategy == "validation_failure":
        # Select buildings that failed validation thresholds
        failed = validation_results[validation_results['passed'] == False]
        return failed.nlargest(count, 'cvrmse')['building_id'].tolist()
    
    elif strategy == "worst_performers":
        # Select buildings with highest error metrics
        return validation_results.nlargest(count, 'total_error')['building_id'].tolist()
    
    elif strategy == "least_improved":
        # Select buildings that improved least in last iteration
        # (requires performance history)
        pass
```

### 5. Data Connection Updates

#### A. Validation → Selection
- Validation results must include building-level metrics
- Add `building_id` to all validation outputs
- Create summary DataFrame with pass/fail status

#### B. Selection → Modification
- Pass selected building IDs to modification system
- Modification reads base parameters from iteration_0 parsed data
- Apply strategy based on iteration number

#### C. Modified Results → Tracking
- Store each iteration's results separately
- Track performance metrics across iterations
- Compare base vs modified for each building

## Code Changes Required

### 1. `validation_step.py`
```python
def run_validation_with_selection(parsed_data_dir, config, iteration=0):
    # Run normal validation
    results = run_validation(parsed_data_dir, config)
    
    # Add building-level summary
    building_summary = aggregate_validation_by_building(results)
    
    # Save for iteration tracking
    save_path = f"iterations/iteration_{iteration}/validation_summary.parquet"
    building_summary.to_parquet(save_path)
    
    return building_summary
```

### 2. `modification_step.py`
```python
def run_modification_for_iteration(building_ids, base_data_dir, iteration, strategy):
    # Load base parameters for selected buildings
    base_params = load_base_parameters(base_data_dir, building_ids)
    
    # Apply modification strategy based on iteration
    intensity = get_intensity_for_iteration(iteration)
    
    # Generate modifications
    modifications = generate_modifications(base_params, strategy, intensity)
    
    return modifications
```

### 3. Performance Tracking
```python
class PerformanceTracker:
    def __init__(self):
        self.history = pd.DataFrame()
        
    def record_iteration(self, iteration, building_id, metrics):
        record = {
            'iteration': iteration,
            'building_id': building_id,
            'timestamp': datetime.now(),
            **metrics
        }
        self.history = pd.concat([self.history, pd.DataFrame([record])])
        
    def get_improvement(self, building_id, metric='cvrmse'):
        building_history = self.history[self.history['building_id'] == building_id]
        if len(building_history) < 2:
            return 0
        return building_history[metric].iloc[-2] - building_history[metric].iloc[-1]
```

## Next Steps

1. **Phase 1**: Create `iteration_manager.py` with basic structure
2. **Phase 2**: Update validation to output building-level summaries
3. **Phase 3**: Connect validation results to building selection
4. **Phase 4**: Update modification to accept building lists
5. **Phase 5**: Implement performance tracking
6. **Phase 6**: Add convergence checking
7. **Phase 7**: Update orchestrator with iteration loop

## Simple Test Case

Start with:
- 10 buildings
- 3 iterations max
- Select 3 worst performers each iteration
- Low → Medium → High modification intensity
- Stop if average CVRMSE improves by < 1% in an iteration