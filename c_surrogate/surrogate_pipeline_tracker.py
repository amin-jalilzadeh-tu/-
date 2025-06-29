"""
surrogate_pipeline_tracker.py

Tracks and exports all data and processes in the surrogate modeling pipeline.
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import joblib

logger = logging.getLogger(__name__)


class SurrogatePipelineTracker:
    """Tracks all data and processes in the surrogate pipeline."""
    
    def __init__(self, job_output_dir: str, run_id: str = None):
        self.job_output_dir = Path(job_output_dir)
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create export directory
        self.export_dir = self.job_output_dir / "surrogate_pipeline_export" / self.run_id
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize tracking data
        self.pipeline_data = {
            "run_id": self.run_id,
            "start_time": datetime.now().isoformat(),
            "job_output_dir": str(self.job_output_dir),
            "steps": {},
            "inputs": {},
            "outputs": {},
            "errors": [],
            "warnings": []
        }
        
        # Create subdirectories
        self.dirs = {
            "inputs": self.export_dir / "1_inputs",
            "extraction": self.export_dir / "2_extraction",
            "preprocessing": self.export_dir / "3_preprocessing",
            "modeling": self.export_dir / "4_modeling",
            "outputs": self.export_dir / "5_outputs",
            "logs": self.export_dir / "logs"
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
    
    def log_step(self, step_name: str, status: str, details: Dict[str, Any] = None):
        """Log a pipeline step."""
        self.pipeline_data["steps"][step_name] = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "details": details or {}
        }
        
        # Also write to log file
        log_file = self.dirs["logs"] / "pipeline_steps.log"
        with open(log_file, "a") as f:
            f.write(f"\n[{datetime.now().isoformat()}] {step_name}: {status}\n")
            if details:
                f.write(f"Details: {json.dumps(details, indent=2)}\n")
    
    def export_input_data(self, data_dict: Dict[str, pd.DataFrame], step: str = "inputs"):
        """Export input dataframes to parquet and create summary."""
        step_dir = self.dirs.get(step, self.dirs["inputs"])
        
        summary = {
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "data_files": {}
        }
        
        for name, df in data_dict.items():
            if df is not None and not df.empty:
                # Save parquet
                file_path = step_dir / f"{name}.parquet"
                df.to_parquet(file_path, index=False)
                
                # Create summary
                summary["data_files"][name] = {
                    "path": str(file_path),
                    "shape": df.shape,
                    "columns": list(df.columns),
                    "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                    "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
                    "null_counts": df.isnull().sum().to_dict(),
                    "sample_rows": df.head(3).to_dict(orient="records")
                }
        
        # Save summary
        summary_path = step_dir / f"{step}_data_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        
        return summary
    
    def export_process_details(self, process_name: str, details: Dict[str, Any], step: str):
        """Export details about a specific process."""
        step_dir = self.dirs.get(step, self.dirs["logs"])
        
        process_file = step_dir / f"process_{process_name}.json"
        with open(process_file, "w") as f:
            json.dump({
                "process": process_name,
                "timestamp": datetime.now().isoformat(),
                "details": details
            }, f, indent=2, default=str)
    
    def track_extraction(self, extractor_summary: Dict[str, Any], extracted_data: Dict[str, pd.DataFrame]):
        """Track data extraction phase."""
        self.log_step("data_extraction", "started")
        
        # Export extracted data
        extraction_summary = self.export_input_data(extracted_data, "inputs")
        
        # Export extraction process details
        self.export_process_details("extraction", {
            "extractor_summary": extractor_summary,
            "data_sources": list(extracted_data.keys()),
            "total_memory_mb": sum(
                df.memory_usage(deep=True).sum() / 1024 / 1024 
                for df in extracted_data.values() 
                if df is not None
            )
        }, "extraction")
        
        self.log_step("data_extraction", "completed", {
            "files_extracted": len(extracted_data),
            "total_rows": sum(len(df) for df in extracted_data.values() if df is not None)
        })
    
    def track_preprocessing(self, preprocessor_metadata: Dict[str, Any], 
                          features: pd.DataFrame, targets: pd.DataFrame,
                          processing_steps: List[str] = None):
        """Track preprocessing phase."""
        self.log_step("preprocessing", "started")
        
        # Export preprocessed data
        self.export_input_data({
            "preprocessed_features": features,
            "preprocessed_targets": targets
        }, "preprocessing")
        
        # Export preprocessing details
        self.export_process_details("preprocessing", {
            "metadata": preprocessor_metadata,
            "processing_steps": processing_steps or [],
            "feature_engineering": {
                "original_features": preprocessor_metadata.get("original_features", 0),
                "final_features": len(features.columns),
                "samples": len(features)
            }
        }, "preprocessing")
        
        # Create feature report
        feature_report = {
            "features": list(features.columns),
            "feature_statistics": features.describe().to_dict(),
            "correlations": features.corr().to_dict() if len(features.columns) < 50 else "Too many features for correlation matrix"
        }
        
        report_path = self.dirs["preprocessing"] / "feature_report.json"
        with open(report_path, "w") as f:
            json.dump(feature_report, f, indent=2, default=str)
        
        self.log_step("preprocessing", "completed", {
            "n_features": len(features.columns),
            "n_samples": len(features)
        })
    
    def track_model_training(self, model_info: Dict[str, Any], metrics: Dict[str, float],
                           feature_importance: pd.DataFrame = None,
                           model_comparison: Dict[str, Any] = None):
        """Track model training phase."""
        self.log_step("model_training", "started", {"model_type": model_info.get("model_type")})
        
        # Export model training details
        self.export_process_details("model_training", {
            "model_info": model_info,
            "metrics": metrics,
            "model_comparison": model_comparison
        }, "modeling")
        
        # Export feature importance if available
        if feature_importance is not None:
            feature_importance.to_csv(
                self.dirs["modeling"] / "feature_importance.csv", 
                index=False
            )
        
        # Save training metrics
        metrics_path = self.dirs["modeling"] / "training_metrics.json"
        with open(metrics_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "model_type": model_info.get("model_type"),
                "metrics": metrics,
                "best_params": model_info.get("best_params", {})
            }, f, indent=2)
        
        self.log_step("model_training", "completed", {
            "model_type": model_info.get("model_type"),
            "primary_metric": metrics.get("r2", metrics.get("overall_r2"))
        })
    
    def track_output_generation(self, validation_results: Dict[str, Any] = None,
                              prediction_examples: Dict[str, Any] = None,
                              artifacts_saved: List[str] = None):
        """Track output generation phase."""
        self.log_step("output_generation", "started")
        
        # Export validation results
        if validation_results:
            val_path = self.dirs["outputs"] / "validation_results.json"
            with open(val_path, "w") as f:
                json.dump(validation_results, f, indent=2, default=str)
        
        # Export prediction examples
        if prediction_examples:
            pred_path = self.dirs["outputs"] / "prediction_examples.json"
            with open(pred_path, "w") as f:
                json.dump(prediction_examples, f, indent=2, default=str)
        
        # Track artifacts
        self.export_process_details("output_generation", {
            "artifacts_saved": artifacts_saved or [],
            "validation_completed": validation_results is not None,
            "prediction_interface_created": prediction_examples is not None
        }, "outputs")
        
        self.log_step("output_generation", "completed", {
            "artifacts_count": len(artifacts_saved or [])
        })
    
    def add_warning(self, warning: str):
        """Add a warning to the pipeline log."""
        self.pipeline_data["warnings"].append({
            "timestamp": datetime.now().isoformat(),
            "message": warning
        })
        logger.warning(f"[Pipeline Tracker] {warning}")
    
    def add_error(self, error: str):
        """Add an error to the pipeline log."""
        self.pipeline_data["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "message": error
        })
        logger.error(f"[Pipeline Tracker] {error}")
    
    def export_configuration(self, config: Dict[str, Any]):
        """Export the configuration used for the pipeline."""
        config_path = self.dirs["inputs"] / "configuration.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2, default=str)
    
    def create_pipeline_summary(self):
        """Create final pipeline summary report."""
        self.pipeline_data["end_time"] = datetime.now().isoformat()
        
        # Calculate duration
        start = datetime.fromisoformat(self.pipeline_data["start_time"])
        end = datetime.fromisoformat(self.pipeline_data["end_time"])
        self.pipeline_data["duration_seconds"] = (end - start).total_seconds()
        
        # Save main summary
        summary_path = self.export_dir / "pipeline_summary.json"
        with open(summary_path, "w") as f:
            json.dump(self.pipeline_data, f, indent=2, default=str)
        
        # Create markdown report
        self._create_markdown_report()
    
    def _create_markdown_report(self):
        """Create a readable markdown report."""
        report_path = self.export_dir / "pipeline_report.md"
        
        with open(report_path, "w") as f:
            f.write(f"# Surrogate Pipeline Report\n\n")
            f.write(f"**Run ID:** {self.run_id}\n")
            f.write(f"**Start Time:** {self.pipeline_data['start_time']}\n")
            f.write(f"**End Time:** {self.pipeline_data.get('end_time', 'In Progress')}\n")
            f.write(f"**Duration:** {self.pipeline_data.get('duration_seconds', 0):.2f} seconds\n\n")
            
            f.write("## Pipeline Steps\n\n")
            for step, info in self.pipeline_data["steps"].items():
                f.write(f"### {step}\n")
                f.write(f"- **Status:** {info['status']}\n")
                f.write(f"- **Time:** {info['timestamp']}\n")
                if info['details']:
                    f.write(f"- **Details:** {json.dumps(info['details'], indent=2)}\n")
                f.write("\n")
            
            if self.pipeline_data["errors"]:
                f.write("## Errors\n\n")
                for error in self.pipeline_data["errors"]:
                    f.write(f"- {error['message']} (at {error['timestamp']})\n")
                f.write("\n")
            
            if self.pipeline_data["warnings"]:
                f.write("## Warnings\n\n")
                for warning in self.pipeline_data["warnings"]:
                    f.write(f"- {warning['message']} (at {warning['timestamp']})\n")
                f.write("\n")
    
    def _convert_numpy_types(self, obj):
        """Convert numpy types to native Python types for JSON serialization."""
        import numpy as np
        
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Series):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: self._convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        return obj

    def generate_data_quality_report(self, data: pd.DataFrame, name: str):
        """Generate a data quality report for a dataframe."""
        quality_report = {
            "dataset": name,
            "timestamp": datetime.now().isoformat(),
            "shape": data.shape,
            "memory_usage_mb": data.memory_usage(deep=True).sum() / 1024 / 1024,
            "null_analysis": {
                "total_nulls": int(data.isnull().sum().sum()),  # Convert to int
                "null_columns": data.columns[data.isnull().any()].tolist(),
                "null_percentages": (data.isnull().sum() / len(data) * 100).to_dict()
            },
            "duplicates": {
                "duplicate_rows": int(data.duplicated().sum()),  # Convert to int
                "duplicate_percentage": float(data.duplicated().sum() / len(data) * 100)  # Convert to float
            },
            "numeric_summary": {}
        }
        
        # Add numeric column statistics
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            quality_report["numeric_summary"][col] = {
                "mean": float(data[col].mean()),
                "std": float(data[col].std()),
                "min": float(data[col].min()),
                "max": float(data[col].max()),
                "zeros": int((data[col] == 0).sum()),
                "outliers": int(((data[col] - data[col].mean()).abs() > 3 * data[col].std()).sum())
            }
        
        # Convert the entire report to ensure all numpy types are handled
        return self._convert_numpy_types(quality_report)