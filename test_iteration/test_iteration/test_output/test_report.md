# Iteration Test Report

## Summary
- Total iterations: 2
- Converged: True
- Final CVRMSE: 15.00%
- Final NMBE: 5.00%

## Performance History
| Iteration | CVRMSE | NMBE | Improvement |
|-----------|--------|------|-------------|
| 1 | 20.00% | 6.50% | - |
| 2 | 15.00% | 5.00% | 25.0% |

## Data Flow Test
- ✓ Calibration results conversion
- ✓ Building selection from validation
- ✓ Parameter feedback to IDF creation

## File Structure
```
test_output/
├── iteration_1/
│   ├── validation_results.json
│   └── calibration/
│       └── best_parameters.json
├── iteration_2/
│   └── validation_results.json
├── iteration_3/
│   └── validation_results.json
├── idf_parameters/
│   └── calibrated_params_iter_2.json
└── iteration_summary.json
```