"""
Data Pipeline Manager for E_Plus_2040 workflow
Manages data flow between iterations and components
"""

import os
import json
import shutil
from pathlib import Path
import pandas as pd
from typing import Dict, List, Optional, Any
import logging


class DataPipelineManager:
    """Manages data flow between iterations and components"""
    
    def __init__(self, job_output_dir: str, logger: logging.Logger):
        """
        Initialize the data pipeline manager
        
        Args:
            job_output_dir: Base output directory for the job
            logger: Logger instance
        """
        self.job_output_dir = Path(job_output_dir)
        self.logger = logger
        
        # Create data registry directory
        self.registry_dir = self.job_output_dir / "data_registry"
        self.registry_dir.mkdir(exist_ok=True)
        
        # Data flow registry
        self.registry_file = self.registry_dir / "data_flow_registry.json"
        self.registry = self._load_or_initialize_registry()
        
        self.logger.info("[DATA_PIPELINE] Initialized data pipeline manager")
    
    def _load_or_initialize_registry(self) -> dict:
        """Load existing registry or initialize new one"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        else:
            registry = {
                "data_flows": [],
                "component_outputs": {},
                "iteration_data": {}
            }
            self._save_registry(registry)
            return registry
    
    def _save_registry(self, registry: dict = None):
        """Save registry to file"""
        if registry is None:
            registry = self.registry
        with open(self.registry_file, 'w') as f:
            json.dump(registry, f, indent=2)
    
    def register_output(self, component: str, iteration: int, output_type: str, 
                       output_path: str, metadata: dict = None):
        """
        Register a component output in the data flow registry
        
        Args:
            component: Component name (e.g., 'parsing', 'calibration')
            iteration: Iteration number
            output_type: Type of output (e.g., 'parsed_data', 'best_parameters')
            output_path: Path to the output
            metadata: Additional metadata
        """
        # Create registry entry
        entry = {
            "component": component,
            "iteration": iteration,
            "output_type": output_type,
            "output_path": str(output_path),
            "timestamp": pd.Timestamp.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Add to flows
        self.registry["data_flows"].append(entry)
        
        # Update component outputs
        comp_key = f"{component}_iter_{iteration}"
        if comp_key not in self.registry["component_outputs"]:
            self.registry["component_outputs"][comp_key] = {}
        self.registry["component_outputs"][comp_key][output_type] = str(output_path)
        
        # Update iteration data
        iter_key = f"iteration_{iteration}"
        if iter_key not in self.registry["iteration_data"]:
            self.registry["iteration_data"][iter_key] = {}
        if component not in self.registry["iteration_data"][iter_key]:
            self.registry["iteration_data"][iter_key][component] = {}
        self.registry["iteration_data"][iter_key][component][output_type] = str(output_path)
        
        self._save_registry()
        self.logger.info(f"[DATA_PIPELINE] Registered output: {component}/{output_type} for iteration {iteration}")
    
    def get_previous_output(self, component: str, output_type: str, 
                           current_iteration: int) -> Optional[str]:
        """
        Get output path from previous iteration
        
        Args:
            component: Component name
            output_type: Type of output
            current_iteration: Current iteration number
            
        Returns:
            Path to previous output or None if not found
        """
        if current_iteration <= 1:
            return None
        
        prev_iter = current_iteration - 1
        iter_key = f"iteration_{prev_iter}"
        
        try:
            path = self.registry["iteration_data"][iter_key][component][output_type]
            if Path(path).exists():
                self.logger.info(f"[DATA_PIPELINE] Found previous output: {component}/{output_type} from iteration {prev_iter}")
                return path
            else:
                self.logger.warning(f"[DATA_PIPELINE] Previous output file not found: {path}")
                return None
        except KeyError:
            self.logger.info(f"[DATA_PIPELINE] No previous output found for {component}/{output_type}")
            return None
    
    def link_calibration_to_idf(self, calibration_results_path: str, iteration: int) -> Optional[str]:
        """
        Create link from calibration results to IDF creation parameters
        
        Args:
            calibration_results_path: Path to calibration results
            iteration: Current iteration number
            
        Returns:
            Path to linked parameters file
        """
        if not Path(calibration_results_path).exists():
            self.logger.warning(f"[DATA_PIPELINE] Calibration results not found: {calibration_results_path}")
            return None
        
        # Create parameters directory
        params_dir = self.job_output_dir / "idf_parameters"
        params_dir.mkdir(exist_ok=True)
        
        # Copy and convert calibration results
        dest_file = params_dir / f"calibrated_params_iter_{iteration}.json"
        
        try:
            # Load calibration results
            with open(calibration_results_path, 'r') as f:
                cal_results = json.load(f)
            
            # Extract parameters in IDF-friendly format
            idf_params = self._convert_calibration_to_idf_format(cal_results)
            
            # Save converted parameters
            with open(dest_file, 'w') as f:
                json.dump(idf_params, f, indent=2)
            
            self.logger.info(f"[DATA_PIPELINE] Linked calibration results to IDF parameters: {dest_file}")
            return str(dest_file)
            
        except Exception as e:
            self.logger.error(f"[DATA_PIPELINE] Error linking calibration results: {e}")
            return None
    
    def _convert_calibration_to_idf_format(self, cal_results: dict) -> dict:
        """
        Convert calibration results to IDF parameter format
        
        Args:
            cal_results: Calibration results dictionary
            
        Returns:
            IDF-compatible parameter dictionary
        """
        idf_params = {
            "calibration_stage": "post_calibration",
            "parameters": {}
        }
        
        # Extract optimized parameters
        if "best_parameters" in cal_results:
            for param_key, value in cal_results["best_parameters"].items():
                # Parse parameter key format: category*object_type*object_name*field
                parts = param_key.split("*")
                if len(parts) == 4:
                    category, obj_type, obj_name, field = parts
                    
                    if category not in idf_params["parameters"]:
                        idf_params["parameters"][category] = []
                    
                    idf_params["parameters"][category].append({
                        "object_type": obj_type,
                        "object_name": obj_name,
                        "field": field,
                        "value": value
                    })
        
        return idf_params
    
    def link_validation_to_selection(self, validation_results_path: str, 
                                   iteration: int) -> Optional[str]:
        """
        Extract failed buildings from validation for next iteration
        
        Args:
            validation_results_path: Path to validation results
            iteration: Current iteration number
            
        Returns:
            Path to failed buildings file
        """
        if not Path(validation_results_path).exists():
            self.logger.warning(f"[DATA_PIPELINE] Validation results not found: {validation_results_path}")
            return None
        
        try:
            # Load validation results
            with open(validation_results_path, 'r') as f:
                val_results = json.load(f)
            
            # Extract failed buildings
            failed_buildings = []
            building_results = val_results.get("building_results", {})
            
            for building_id, results in building_results.items():
                if not results.get("passed", True):
                    failed_buildings.append({
                        "building_id": building_id,
                        "cvrmse": results.get("metrics", {}).get("cvrmse", None),
                        "nmbe": results.get("metrics", {}).get("nmbe", None)
                    })
            
            # Sort by CVRMSE (worst first)
            failed_buildings.sort(key=lambda x: x.get("cvrmse", float('inf')), reverse=True)
            
            # Save failed buildings
            output_dir = Path(validation_results_path).parent
            failed_file = output_dir / "failed_buildings.json"
            
            with open(failed_file, 'w') as f:
                json.dump({
                    "iteration": iteration,
                    "failed_count": len(failed_buildings),
                    "failed_buildings": [b["building_id"] for b in failed_buildings],
                    "building_metrics": failed_buildings
                }, f, indent=2)
            
            self.logger.info(f"[DATA_PIPELINE] Extracted {len(failed_buildings)} failed buildings")
            return str(failed_file)
            
        except Exception as e:
            self.logger.error(f"[DATA_PIPELINE] Error extracting failed buildings: {e}")
            return None
    
    def get_data_flow_summary(self) -> dict:
        """Get summary of all data flows"""
        summary = {
            "total_flows": len(self.registry["data_flows"]),
            "iterations": len(self.registry["iteration_data"]),
            "components": list(set(flow["component"] for flow in self.registry["data_flows"])),
            "latest_flows": self.registry["data_flows"][-10:]  # Last 10 flows
        }
        
        # Save summary
        summary_file = self.registry_dir / "data_flow_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
    def create_iteration_links(self, iteration: int):
        """
        Create all necessary data links for an iteration
        
        Args:
            iteration: Iteration number
        """
        if iteration <= 1:
            return
        
        links_created = []
        
        # Link calibration results to IDF parameters
        cal_path = self.get_previous_output("calibration", "best_parameters", iteration)
        if cal_path:
            idf_params_path = self.link_calibration_to_idf(cal_path, iteration)
            if idf_params_path:
                links_created.append(("calibration", "idf_parameters", idf_params_path))
        
        # Link validation results to building selection
        val_path = self.get_previous_output("validation", "validation_summary", iteration)
        if val_path:
            failed_buildings_path = self.link_validation_to_selection(val_path, iteration)
            if failed_buildings_path:
                links_created.append(("validation", "failed_buildings", failed_buildings_path))
        
        # Register created links
        for source, link_type, path in links_created:
            self.register_output(f"{source}_link", iteration, link_type, path)
        
        self.logger.info(f"[DATA_PIPELINE] Created {len(links_created)} data links for iteration {iteration}")