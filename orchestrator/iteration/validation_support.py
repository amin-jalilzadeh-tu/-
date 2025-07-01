"""
Validation support functions for iteration workflow
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
import json


def extract_building_summary(validation_results: Dict[str, Any]) -> pd.DataFrame:
    """
    Extract building-level summary from validation results.
    
    Args:
        validation_results: Validation results dictionary
        
    Returns:
        DataFrame with building-level metrics
    """
    building_data = []
    
    # Handle different validation result formats
    if "building_results" in validation_results:
        # Format 1: building_results dictionary
        for building_id, metrics in validation_results["building_results"].items():
            record = {
                "building_id": building_id,
                "validation_passed": metrics.get("passed", False),
                "cvrmse": metrics.get("metrics", {}).get("cvrmse", float('inf')),
                "nmbe": metrics.get("metrics", {}).get("nmbe", float('inf')),
                "mbe": metrics.get("metrics", {}).get("mbe", 0.0)
            }
            building_data.append(record)
    
    elif "results_by_variable" in validation_results:
        # Format 2: results by variable - aggregate to building level
        var_results = validation_results["results_by_variable"]
        building_metrics = {}
        
        for var_name, var_data in var_results.items():
            if "building_metrics" in var_data:
                for building_id, metrics in var_data["building_metrics"].items():
                    if building_id not in building_metrics:
                        building_metrics[building_id] = {
                            "cvrmse_values": [],
                            "nmbe_values": []
                        }
                    building_metrics[building_id]["cvrmse_values"].append(
                        metrics.get("cvrmse", float('inf'))
                    )
                    building_metrics[building_id]["nmbe_values"].append(
                        metrics.get("nmbe", float('inf'))
                    )
        
        # Average across variables for each building
        for building_id, metrics in building_metrics.items():
            avg_cvrmse = sum(metrics["cvrmse_values"]) / len(metrics["cvrmse_values"])
            avg_nmbe = sum(metrics["nmbe_values"]) / len(metrics["nmbe_values"])
            
            record = {
                "building_id": building_id,
                "validation_passed": avg_cvrmse < 30.0,  # Default threshold
                "cvrmse": avg_cvrmse,
                "nmbe": avg_nmbe,
                "mbe": 0.0  # Not available in this format
            }
            building_data.append(record)
    
    # Create DataFrame
    if building_data:
        df = pd.DataFrame(building_data)
        # Ensure building_id is string
        df["building_id"] = df["building_id"].astype(str)
        return df
    else:
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=["building_id", "validation_passed", "cvrmse", "nmbe", "mbe"])


def save_iteration_validation_results(
    validation_results: Dict[str, Any],
    building_summary: pd.DataFrame,
    iteration_dir: Path,
    iteration: int
):
    """
    Save validation results for iteration tracking.
    
    Args:
        validation_results: Full validation results
        building_summary: Building-level summary DataFrame
        iteration_dir: Directory for iteration data
        iteration: Iteration number
    """
    validation_dir = iteration_dir / "validation"
    validation_dir.mkdir(exist_ok=True)
    
    # Save full results as JSON
    results_file = validation_dir / "validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(validation_results, f, indent=2)
    
    # Save building summary as parquet and CSV
    summary_parquet = validation_dir / "validation_summary.parquet"
    summary_csv = validation_dir / "validation_summary.csv"
    
    building_summary.to_parquet(summary_parquet)
    building_summary.to_csv(summary_csv, index=False)
    
    # Save failed buildings separately for easy access
    failed_buildings = building_summary[~building_summary["validation_passed"]]
    if not failed_buildings.empty:
        failed_file = validation_dir / "failed_buildings.json"
        failed_data = {
            "iteration": iteration,
            "failed_count": len(failed_buildings),
            "failed_buildings": failed_buildings["building_id"].tolist(),
            "failed_metrics": failed_buildings.to_dict('records')
        }
        with open(failed_file, 'w') as f:
            json.dump(failed_data, f, indent=2)