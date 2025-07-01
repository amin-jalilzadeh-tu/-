"""
Calibration Feedback Module for E_Plus_2040 workflow
Converts calibration results to IDF creation parameters
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd


class CalibrationFeedback:
    """Handles conversion of calibration results to IDF parameters"""
    
    def __init__(self, job_output_dir: str, logger: logging.Logger):
        """
        Initialize calibration feedback handler
        
        Args:
            job_output_dir: Base output directory
            logger: Logger instance
        """
        self.job_output_dir = Path(job_output_dir)
        self.logger = logger
        
        # Create calibration feedback directory
        self.feedback_dir = self.job_output_dir / "calibration_feedback"
        self.feedback_dir.mkdir(exist_ok=True)
        
        self.logger.info("[CAL_FEEDBACK] Initialized calibration feedback handler")
    
    def load_calibration_results(self, calibration_path: str) -> Optional[dict]:
        """
        Load calibration results from file
        
        Args:
            calibration_path: Path to calibration results
            
        Returns:
            Calibration results dictionary or None
        """
        cal_path = Path(calibration_path)
        
        # Try different possible filenames
        possible_files = [
            cal_path / "best_parameters.json",
            cal_path / "calibration_results.json",
            cal_path / "optimized_parameters.json"
        ]
        
        for file_path in possible_files:
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        results = json.load(f)
                    self.logger.info(f"[CAL_FEEDBACK] Loaded calibration results from {file_path}")
                    return results
                except Exception as e:
                    self.logger.error(f"[CAL_FEEDBACK] Error loading {file_path}: {e}")
        
        self.logger.warning(f"[CAL_FEEDBACK] No calibration results found in {calibration_path}")
        return None
    
    def convert_to_idf_parameters(self, cal_results: dict, iteration: int) -> dict:
        """
        Convert calibration results to IDF creation parameter format
        
        Args:
            cal_results: Calibration results dictionary
            iteration: Current iteration number
            
        Returns:
            IDF-compatible parameter dictionary
        """
        idf_params = {
            "calibration_stage": "post_calibration",
            "iteration": iteration,
            "timestamp": pd.Timestamp.now().isoformat(),
            "overrides": {
                "dhw": [],
                "hvac": [],
                "lighting": [],
                "equipment": [],
                "materials": [],
                "fenestration": [],
                "schedules": []
            }
        }
        
        # Extract parameters based on format
        if "best_parameters" in cal_results:
            params = cal_results["best_parameters"]
        elif "optimized_values" in cal_results:
            params = cal_results["optimized_values"]
        else:
            params = cal_results
        
        # Convert each parameter
        for param_key, value in params.items():
            override = self._convert_parameter(param_key, value)
            if override:
                category = override["category"]
                if category in idf_params["overrides"]:
                    idf_params["overrides"][category].append(override["parameter"])
        
        # Remove empty categories
        idf_params["overrides"] = {k: v for k, v in idf_params["overrides"].items() if v}
        
        return idf_params
    
    def _convert_parameter(self, param_key: str, value: Any) -> Optional[dict]:
        """
        Convert a single calibration parameter to IDF format
        
        Args:
            param_key: Parameter key (e.g., "HVAC*Coil:Cooling*COIL_1*Rated COP")
            value: Parameter value
            
        Returns:
            Converted parameter or None
        """
        # Parse parameter key
        parts = param_key.split("*")
        
        if len(parts) < 3:
            self.logger.warning(f"[CAL_FEEDBACK] Invalid parameter key format: {param_key}")
            return None
        
        category = parts[0].lower()
        
        # Handle different parameter formats
        if len(parts) == 4:
            # Format: category*object_type*object_name*field
            obj_type, obj_name, field = parts[1], parts[2], parts[3]
            
            parameter = {
                "object_type": obj_type,
                "object_name": obj_name,
                "field": field,
                "value": value
            }
            
        elif len(parts) == 3:
            # Format: category*parameter_name*field
            param_name, field = parts[1], parts[2]
            
            parameter = {
                "param_name": param_name,
                "field": field,
                "value": value
            }
            
        else:
            # Format: category*parameter_name
            parameter = {
                "param_name": parts[1],
                "value": value
            }
        
        # Map category to IDF creation categories
        category_map = {
            "hvac": "hvac",
            "dhw": "dhw",
            "lighting": "lighting",
            "elec": "equipment",
            "equipment": "equipment",
            "material": "materials",
            "materials": "materials",
            "window": "fenestration",
            "fenestration": "fenestration",
            "schedule": "schedules",
            "schedules": "schedules"
        }
        
        mapped_category = category_map.get(category, category)
        
        return {
            "category": mapped_category,
            "parameter": parameter
        }
    
    def apply_to_config(self, main_config: dict, idf_params: dict) -> dict:
        """
        Apply calibrated parameters to main configuration
        
        Args:
            main_config: Main configuration dictionary
            idf_params: IDF parameters from calibration
            
        Returns:
            Updated configuration
        """
        # Update IDF creation config
        if "idf_creation" not in main_config:
            main_config["idf_creation"] = {}
        
        main_config["idf_creation"]["calibration_stage"] = idf_params["calibration_stage"]
        main_config["idf_creation"]["calibration_iteration"] = idf_params["iteration"]
        
        # Apply overrides to user configs
        for category, overrides in idf_params["overrides"].items():
            config_key = f"user_config_{category}"
            
            if config_key not in main_config:
                main_config[config_key] = []
            
            # Add calibration overrides
            for override in overrides:
                override["source"] = "calibration"
                override["iteration"] = idf_params["iteration"]
                main_config[config_key].append(override)
        
        self.logger.info(f"[CAL_FEEDBACK] Applied {sum(len(v) for v in idf_params['overrides'].values())} parameter overrides")
        
        return main_config
    
    def save_feedback_data(self, iteration: int, cal_results: dict, idf_params: dict):
        """
        Save calibration feedback data for tracking
        
        Args:
            iteration: Iteration number
            cal_results: Original calibration results
            idf_params: Converted IDF parameters
        """
        feedback_data = {
            "iteration": iteration,
            "timestamp": pd.Timestamp.now().isoformat(),
            "calibration_results": cal_results,
            "idf_parameters": idf_params,
            "parameter_count": sum(len(v) for v in idf_params["overrides"].values())
        }
        
        # Save to iteration-specific file
        feedback_file = self.feedback_dir / f"iteration_{iteration}_feedback.json"
        with open(feedback_file, 'w') as f:
            json.dump(feedback_data, f, indent=2)
        
        # Update overall feedback history
        history_file = self.feedback_dir / "feedback_history.json"
        if history_file.exists():
            with open(history_file, 'r') as f:
                history = json.load(f)
        else:
            history = []
        
        history.append({
            "iteration": iteration,
            "timestamp": feedback_data["timestamp"],
            "parameter_count": feedback_data["parameter_count"]
        })
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        self.logger.info(f"[CAL_FEEDBACK] Saved feedback data for iteration {iteration}")
    
    def get_calibrated_parameters_summary(self) -> pd.DataFrame:
        """
        Get summary of all calibrated parameters across iterations
        
        Returns:
            DataFrame with parameter changes
        """
        all_params = []
        
        for feedback_file in sorted(self.feedback_dir.glob("iteration_*_feedback.json")):
            with open(feedback_file, 'r') as f:
                data = json.load(f)
            
            iteration = data["iteration"]
            for category, overrides in data["idf_parameters"]["overrides"].items():
                for param in overrides:
                    param_record = {
                        "iteration": iteration,
                        "category": category,
                        "parameter": str(param),
                        "value": param.get("value", None)
                    }
                    all_params.append(param_record)
        
        if all_params:
            df = pd.DataFrame(all_params)
            summary_file = self.feedback_dir / "calibrated_parameters_summary.csv"
            df.to_csv(summary_file, index=False)
            self.logger.info(f"[CAL_FEEDBACK] Saved parameter summary to {summary_file}")
            return df
        else:
            return pd.DataFrame()