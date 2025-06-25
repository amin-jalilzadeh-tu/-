"""
Example script showing how to run modification-based sensitivity analysis
"""

from pathlib import Path
import logging
import json

# Import the modification sensitivity analyzer
from c_sensitivity.modification_sensitivity_analyzer import ModificationSensitivityAnalyzer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_modification_sensitivity_example(job_output_dir: str):
    """
    Example of running modification-based sensitivity analysis
    """
    # Initialize the analyzer
    analyzer = ModificationSensitivityAnalyzer(
        job_output_dir=Path(job_output_dir),
        logger=logger
    )
    
    # 1. Load modification tracking data
    logger.info("Loading modifications...")
    modifications = analyzer.load_modification_tracking()
    print(f"Found {len(modifications)} modifications across {modifications['building_id'].nunique()} buildings")
    print(f"Categories modified: {modifications['category'].unique()}")
    
    # 2. Load simulation results
    logger.info("Loading simulation results...")
    base_results, modified_results = analyzer.load_simulation_results(result_type='daily')
    print(f"Loaded {len(base_results)} base result categories")
    print(f"Loaded {len(modified_results)} modified result categories")
    
    # 3. Calculate output deltas
    logger.info("Calculating output changes...")
    output_variables = [
        "Heating:EnergyTransfer",
        "Cooling:EnergyTransfer",
        "Electricity:Facility"
    ]
    
    output_deltas = analyzer.calculate_output_deltas(output_variables)
    print(f"\nOutput deltas shape: {output_deltas.shape}")
    
    # Show sample of changes
    print("\nSample output changes:")
    for var in output_variables:
        delta_col = f"{var}_delta"
        pct_col = f"{var}_pct_change"
        if delta_col in output_deltas.columns:
            avg_change = output_deltas[pct_col].mean()
            print(f"  {var}: Average change = {avg_change:.1f}%")
    
    # 4. Calculate parameter aggregates
    logger.info("Aggregating parameter changes...")
    param_aggregates = analyzer.calculate_parameter_aggregates()
    print(f"\nParameter aggregates shape: {param_aggregates.shape}")
    
    # Show top parameter changes
    print("\nTop 5 parameter changes by magnitude:")
    top_params = param_aggregates.nlargest(5, 'avg_pct_change')
    for _, row in top_params.iterrows():
        print(f"  {row['category']}/{row['param_key']}: {row['avg_pct_change']:.1f}%")
    
    # 5. Calculate sensitivity scores
    logger.info("Calculating sensitivity scores...")
    
    # Define parameter groups (or use from config)
    parameter_groups = {
        'hvac': ['cooling_cop', 'heating_efficiency'],
        'lighting': ['watts_per_area', 'fraction_radiant'],
        'materials': ['conductivity', 'u_factor']
    }
    
    sensitivity_results = analyzer.calculate_sensitivity_scores(
        parameter_groups=parameter_groups
    )
    
    print(f"\nSensitivity results shape: {sensitivity_results.shape}")
    
    # Show top sensitive parameters
    print("\nTop 10 most sensitive parameters:")
    print("-" * 80)
    print(f"{'Parameter':<30} {'Category':<15} {'Output':<20} {'Score':<10} {'Correlation':<12}")
    print("-" * 80)
    
    for _, row in sensitivity_results.head(10).iterrows():
        param_short = row['parameter'][:30]
        output_short = row['output_variable'].replace('_delta', '')[:20]
        print(f"{param_short:<30} {row['category']:<15} {output_short:<20} "
              f"{row['sensitivity_score']:<10.3f} {row['correlation']:<12.3f}")
    
    # 6. Weight by validation (if available)
    if analyzer.validation_dir.exists():
        logger.info("Applying validation weighting...")
        sensitivity_results = analyzer.weight_by_validation(sensitivity_results)
        print("\nValidation weighting applied")
    
    # 7. Analyze parameter groups
    logger.info("Analyzing parameter groups...")
    group_analysis = analyzer.analyze_parameter_groups(sensitivity_results)
    
    print("\nCategory impact analysis:")
    print("-" * 60)
    print(f"{'Category':<15} {'Output':<25} {'Avg Score':<10} {'Rank':<5}")
    print("-" * 60)
    
    for _, row in group_analysis.head(10).iterrows():
        output_short = row['output_variable'].replace('_delta', '')[:25]
        print(f"{row['category']:<15} {output_short:<25} "
              f"{row['sensitivity_score_mean']:<10.3f} {int(row['impact_rank']):<5}")
    
    # 8. Generate report
    output_dir = Path(job_output_dir) / "sensitivity_results"
    output_dir.mkdir(exist_ok=True)
    
    logger.info("Generating report...")
    report = analyzer.generate_report(
        sensitivity_results,
        group_analysis,
        output_dir
    )
    
    print(f"\nReport saved to: {output_dir}")
    print(f"\nSummary:")
    print(f"  Most sensitive category: {report['summary']['most_sensitive_category']}")
    print(f"  Highest correlation: {report['summary']['highest_correlation']['parameter']} "
          f"→ {report['summary']['highest_correlation']['output']} "
          f"({report['summary']['highest_correlation']['correlation']:.3f})")
    
    return report


def check_prerequisites(job_output_dir: str) -> bool:
    """Check if all required data exists"""
    job_path = Path(job_output_dir)
    
    checks = {
        "Base parsed data": job_path / "parsed_data",
        "Modified parsed data": job_path / "parsed_modified_results",
        "Modification tracking": job_path / "modified_idfs",
        "Validation results (optional)": job_path / "validation_results"
    }
    
    all_good = True
    for name, path in checks.items():
        exists = path.exists()
        status = "✓" if exists else "✗"
        if "optional" not in name and not exists:
            all_good = False
        print(f"{status} {name}: {path}")
    
    return all_good


if __name__ == "__main__":
    # Example usage
    job_output_dir = "output/4bf9e689-3702-43be-9b0a-a02e936558fb"
    
    print("Checking prerequisites...")
    if check_prerequisites(job_output_dir):
        print("\nRunning modification sensitivity analysis...")
        report = run_modification_sensitivity_example(job_output_dir)
    else:
        print("\nMissing required data. Please ensure all steps have been run.")
