"""
Run calibration using the integrated workflow
"""

import warnings
warnings.filterwarnings('ignore')  # Suppress sklearn version warnings

import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.append('/mnt/d/Documents/daily/E_Plus_2040_py')

from calibration_workflow_integrated import IntegratedCalibrationWorkflow

def main():
    # Output directory with your data
    output_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/3cce1ec0-77e8-4121-94dd-6134bd6eff99"
    
    print("=== Initializing Calibration Workflow ===")
    workflow = IntegratedCalibrationWorkflow(output_dir)
    
    # Load existing results
    print("\n1. Loading existing results...")
    workflow.load_existing_results()
    
    # Select top parameters based on sensitivity
    print("\n2. Selecting calibration parameters...")
    param_specs = workflow.select_calibration_parameters(top_n=15, sensitivity_threshold=2.0)
    print(f"   Selected {len(param_specs)} parameters for calibration")
    
    print("\n   Top 5 parameters:")
    for i, spec in enumerate(param_specs[:5]):
        print(f"   {i+1}. {spec.name.split('_')[-1]}: [{spec.min_value:.2f}, {spec.max_value:.2f}]")
    
    # Load or create measured data
    print("\n3. Loading measured data...")
    # Try to load from validation results first
    validation_path = Path(output_dir) / "parsed_data" / "validation_results.parquet"
    if validation_path.exists():
        val_df = pd.read_parquet(validation_path)
        if 'real_value' in val_df.columns and not val_df['real_value'].isna().all():
            measured_data = pd.DataFrame({
                'electricity_total': val_df['real_value'].values,
                'month': range(1, len(val_df) + 1)
            })
            print("   Using real validation data")
        else:
            # Use dummy data
            measured_data = pd.DataFrame({
                'electricity_total': np.random.normal(50000, 5000, 12),
                'month': range(1, 13)
            })
            print("   Using simulated data (no real data found)")
    else:
        measured_data = pd.DataFrame({
            'electricity_total': np.random.normal(50000, 5000, 12),
            'month': range(1, 13)
        })
        print("   Using simulated data")
    
    print(f"   Average monthly consumption: {measured_data['electricity_total'].mean():.0f} kWh")
    
    # Run calibration
    print("\n4. Running calibration with surrogate model...")
    print("   Algorithm: Particle Swarm Optimization (PSO)")
    print("   Population: 20 particles")
    print("   Iterations: 30")
    print("   This will take approximately 30-60 seconds...\n")
    
    results = workflow.run_calibration(
        measured_data,
        algorithm='PSO',
        max_iter=30,
        population_size=20
    )
    
    # Display results
    print("\n=== CALIBRATION RESULTS ===")
    print(f"Best objective value: {results['best_objective']:.4f}")
    print(f"Final CVRMSE: {results['final_metrics']['CVRMSE']:.2f}%")
    print(f"Final NMBE: {results['final_metrics']['NMBE']:.2f}%")
    print(f"Total surrogate evaluations: {results['total_evaluations']}")
    print(f"Simulated total energy: {results['final_metrics']['simulated_total']:.0f} kWh")
    print(f"Measured total energy: {results['final_metrics']['measured_total']:.0f} kWh")
    
    print("\n=== TOP 10 CALIBRATED PARAMETERS ===")
    sorted_params = sorted(results['best_parameters'].items(), 
                          key=lambda x: abs(x[1]), reverse=True)
    for i, (param, value) in enumerate(sorted_params[:10]):
        short_name = param.split('_')[-1]
        print(f"{i+1:2d}. {short_name:30s}: {value:10.3f}")
    
    # Save results
    print("\n5. Saving calibrated parameters...")
    output_path = Path(output_dir) / "calibrated_parameters"
    workflow.save_calibrated_parameters(results, str(output_path))
    print(f"   Saved to: {output_path}")
    
    # Summary
    print("\n=== CALIBRATION COMPLETE ===")
    if results['final_metrics']['CVRMSE'] < 15:
        print("✓ CVRMSE is below 15% - Good calibration!")
    else:
        print("⚠ CVRMSE is above 15% - Further calibration may be needed")
    
    print("\nNext steps:")
    print("1. Use calibrated parameters to create new IDF files")
    print("2. Run full EnergyPlus simulation to validate results")
    print("3. Compare with measured data for final verification")


if __name__ == "__main__":
    main()