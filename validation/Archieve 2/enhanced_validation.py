"""
enhanced_validation.py - Updated with configuration support
Enhanced validation module that works with parsed Parquet data and new configuration system
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import json
from datetime import datetime
import logging

from validation.metrics import mean_bias_error, cv_rmse, nmbe, analyze_peaks, analyze_ramp_rates
from validation.validation_data_loader import ValidationDataLoader
from validation.validation_config import ValidationConfig

logger = logging.getLogger(__name__)


class EnhancedValidator:
    """Enhanced validator with configuration-driven validation"""
    
    def __init__(self, job_output_dir: str, config: Union[Dict[str, Any], ValidationConfig]):
        self.job_output_dir = Path(job_output_dir)
        
        # Handle config input - can be dict or ValidationConfig instance
        if isinstance(config, dict):
            self.config_dict = config
            self.config = ValidationConfig(config_dict=config)
        else:
            self.config = config
            self.config_dict = config.to_dict()
        
        self.data_loader = ValidationDataLoader(job_output_dir, self.config)
        self.validation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Results storage
        self.summary_results = []
        self.detailed_results = []
        self.failed_results = []
        self.unit_conversion_log = []
        
    def validate(self) -> Dict[str, pd.DataFrame]:
        """
        Main validation method with improved error handling and unit conversion
        
        Returns:
            Dictionary with validation results DataFrames
        """
        logger.info("Starting enhanced validation process")
        
        # Load real data
        real_data_config = self.config_dict.get("real_data", {})
        real_data_path = real_data_config.get("path")
        
        if not real_data_path:
            raise ValueError("Real data path not specified in configuration")
        
        id_column = real_data_config.get("id_column", "BuildingID")
        
        logger.info(f"Loading real data from: {real_data_path}")
        try:
            real_df = self.data_loader.load_real_data(real_data_path, id_column)
        except Exception as e:
            logger.error(f"Error loading real data: {e}")
            raise
        
        # Log data summary
        self._log_data_summary("Real", real_df)
        
        # Get building mappings
        bldg_mappings = self._get_building_mappings(real_df)
        logger.info(f"Building mappings: {bldg_mappings}")
        
        # Get variables to compare
        variables_to_compare = self.config_dict.get("variables_to_compare", [])
        if not variables_to_compare:
            # Get all variables from real data
            if "VariableName" in real_df.columns:
                variables_to_compare = real_df["VariableName"].unique().tolist()
                logger.info(f"Auto-detected variables: {variables_to_compare}")
        
        # Process each building mapping
        for real_bldg_id, sim_bldg_ids in bldg_mappings.items():
            logger.info(f"\nProcessing real building {real_bldg_id} -> sim buildings {sim_bldg_ids}")
            
            # Get real data for this building
            real_bldg_data = real_df[real_df["BuildingID"] == str(real_bldg_id)]
            
            if real_bldg_data.empty:
                logger.warning(f"No real data for building {real_bldg_id}")
                continue
            
            # Load simulated data with proper error handling
            try:
                sim_data = self.data_loader.load_simulated_data_from_parsed(
                    sim_bldg_ids,
                    variables_to_compare,
                    frequency=self.config_dict.get("data_frequency", "daily")
                )
            except Exception as e:
                logger.error(f"Error loading simulated data: {e}")
                continue
            
            if sim_data.empty:
                logger.warning(f"No simulated data for buildings {sim_bldg_ids}")
                self._add_missing_data_result(real_bldg_id, sim_bldg_ids, variables_to_compare)
                continue
            
            # Log simulation data summary
            self._log_data_summary("Simulated", sim_data)
            
            # Transform to wide format if needed
            real_wide = self.data_loader.transform_to_wide_format(real_bldg_data)
            sim_wide = self.data_loader.transform_to_wide_format(sim_data)
            
            # Align data structures with unit conversion
            try:
                real_aligned, sim_aligned = self.data_loader.align_data_structures(real_wide, sim_wide)
                
                # Log any unit conversions that occurred
                self._log_unit_conversions(real_bldg_id, real_aligned, sim_aligned)
                
            except Exception as e:
                logger.error(f"Error aligning data: {e}")
                self._add_alignment_error_result(real_bldg_id, sim_bldg_ids, str(e))
                continue
            
            # Validate each sim building
            for sim_bldg_id in sim_bldg_ids:
                self._validate_building_pair(
                    real_bldg_id, 
                    sim_bldg_id,
                    real_aligned,
                    sim_aligned,
                    variables_to_compare
                )
        
        # Save results
        return self._save_results()
    
    def _log_data_summary(self, data_type: str, df: pd.DataFrame):
        """Log summary of loaded data"""
        logger.info(f"\n{data_type} Data Summary:")
        logger.info(f"  Shape: {df.shape}")
        
        if "BuildingID" in df.columns:
            buildings = df["BuildingID"].unique()
            logger.info(f"  Buildings: {len(buildings)} - {list(buildings[:5])}")
        
        if "VariableName" in df.columns:
            variables = df["VariableName"].unique()
            logger.info(f"  Variables: {len(variables)} - {list(variables[:5])}")
        
        # Check for value columns
        value_cols = [col for col in df.columns if col not in ["BuildingID", "VariableName", "DateTime", "Zone"]]
        if value_cols:
            logger.info(f"  Date/Value columns: {len(value_cols)}")
            if len(value_cols) < 10:
                logger.info(f"    Columns: {value_cols}")
            else:
                logger.info(f"    First few: {value_cols[:5]}")
    
    def _log_unit_conversions(self, building_id: str, real_df: pd.DataFrame, sim_df: pd.DataFrame):
        """Log any unit conversions that were applied"""
        # This would be enhanced to actually track conversions in the aligner
        # For now, just log that alignment was successful
        logger.info(f"Data alignment successful for building {building_id}")
    
    def _get_building_mappings(self, real_df: pd.DataFrame) -> Dict[str, List[str]]:
        """Get building ID mappings from config or real data"""
        mappings = {}
        
        if "building_mappings" in self.config_dict:
            # Use explicit mappings from config
            for real_str, sim_list in self.config_dict["building_mappings"].items():
                # Ensure all IDs are strings
                real_id = str(real_str)
                if isinstance(sim_list, list):
                    sim_ids = [str(s) for s in sim_list]
                else:
                    sim_ids = [str(sim_list)]
                mappings[real_id] = sim_ids
        else:
            # Use building IDs from real data
            if "BuildingID" in real_df.columns:
                real_ids = real_df["BuildingID"].unique()
                for real_id in real_ids:
                    mappings[str(real_id)] = [str(real_id)]
        
        return mappings
    
    def _validate_building_pair(self, real_bldg_id: str, sim_bldg_id: str,
                               real_df: pd.DataFrame, sim_df: pd.DataFrame,
                               variables: List[str]):
        """Validate a single building pair with better error handling"""
        
        # Filter sim data for this building
        sim_bldg_df = sim_df[sim_df["BuildingID"] == str(sim_bldg_id)]
        
        if sim_bldg_df.empty:
            logger.warning(f"No sim data for building {sim_bldg_id}")
            return
        
        # Get actual variables available in both datasets
        real_vars = set(real_df["VariableName"].unique()) if "VariableName" in real_df.columns else set()
        sim_vars = set(sim_bldg_df["VariableName"].unique()) if "VariableName" in sim_bldg_df.columns else set()
        
        # Find common variables
        common_vars = real_vars & sim_vars
        missing_in_sim = real_vars - sim_vars
        
        if missing_in_sim:
            logger.warning(f"Variables missing in simulation: {missing_in_sim}")
        
        # Validate each common variable
        for var_name in common_vars:
            logger.debug(f"Validating {var_name}")
            
            # Get data for this variable
            real_var = real_df[real_df["VariableName"] == var_name]
            sim_var = sim_bldg_df[sim_bldg_df["VariableName"] == var_name]
            
            if real_var.empty or sim_var.empty:
                continue
            
            # Extract values (excluding ID columns)
            date_cols = [col for col in real_var.columns if col not in ["BuildingID", "VariableName"]]
            
            # Ensure we have matching columns
            common_date_cols = [col for col in date_cols if col in sim_var.columns]
            
            if not common_date_cols:
                logger.warning(f"No common date columns for {var_name}")
                continue
            
            # Extract values for common dates
            real_values = real_var[common_date_cols].values.flatten()
            sim_values = sim_var[common_date_cols].values.flatten()
            
            # Remove NaN values
            mask = ~(np.isnan(real_values) | np.isnan(sim_values))
            real_values = real_values[mask]
            sim_values = sim_values[mask]
            
            if len(real_values) == 0:
                logger.warning(f"No valid data points for {var_name}")
                continue
            
            # Log value ranges for debugging
            logger.debug(f"  Real values: mean={np.mean(real_values):.2f}, "
                        f"min={np.min(real_values):.2f}, max={np.max(real_values):.2f}")
            logger.debug(f"  Sim values: mean={np.mean(sim_values):.2f}, "
                        f"min={np.min(sim_values):.2f}, max={np.max(sim_values):.2f}")
            
            # Check for potential unit issues
            value_ratio = np.mean(sim_values) / np.mean(real_values) if np.mean(real_values) != 0 else 0
            if value_ratio > 100 or value_ratio < 0.01:
                logger.warning(f"  Potential unit mismatch! Ratio: {value_ratio:.2f}")
                self.unit_conversion_log.append({
                    'building': f"{real_bldg_id}->{sim_bldg_id}",
                    'variable': var_name,
                    'ratio': value_ratio,
                    'real_mean': np.mean(real_values),
                    'sim_mean': np.mean(sim_values)
                })
            
            # Calculate metrics
            metrics = self._calculate_metrics(real_values, sim_values, var_name)
            
            # Add to results
            self._add_to_results(real_bldg_id, sim_bldg_id, var_name, metrics, common_date_cols)
    
    def _calculate_metrics(self, real_values: np.ndarray, sim_values: np.ndarray, 
                          var_name: str) -> Dict[str, Any]:
        """Calculate all validation metrics with threshold lookup"""
        
        # Get thresholds from config
        cvrmse_threshold = self.config.get_threshold('cvrmse', var_name)
        nmbe_threshold = self.config.get_threshold('nmbe', var_name)
        
        # Core metrics
        mbe = mean_bias_error(sim_values, real_values)
        cvrmse_val = cv_rmse(sim_values, real_values)
        nmbe_val = nmbe(sim_values, real_values)
        
        # Additional metrics
        rmse = np.sqrt(np.mean((sim_values - real_values) ** 2))
        mae = np.mean(np.abs(sim_values - real_values))
        
        # R-squared
        if np.var(real_values) > 0:
            r2 = 1 - (np.var(sim_values - real_values) / np.var(real_values))
        else:
            r2 = np.nan
        
        # Pass/fail determination
        pass_cvrmse = cvrmse_val <= cvrmse_threshold if not np.isnan(cvrmse_val) else False
        pass_nmbe = abs(nmbe_val) <= nmbe_threshold if not np.isnan(nmbe_val) else False
        overall_pass = pass_cvrmse and pass_nmbe
        
        metrics = {
            "mbe": mbe,
            "cvrmse": cvrmse_val,
            "nmbe": nmbe_val,
            "rmse": rmse,
            "mae": mae,
            "r2": r2,
            "pass_cvrmse": pass_cvrmse,
            "pass_nmbe": pass_nmbe,
            "pass": overall_pass,
            "cvrmse_threshold": cvrmse_threshold,
            "nmbe_threshold": nmbe_threshold,
            "data_points": len(real_values),
            "real_mean": np.mean(real_values),
            "sim_mean": np.mean(sim_values),
            "real_std": np.std(real_values),
            "sim_std": np.std(sim_values)
        }
        
        # Peak analysis if enabled
        analysis_options = self.config_dict.get("analysis_options", {})
        if analysis_options.get("peak_analysis", {}).get("perform", False):
            peak_metrics = analyze_peaks(
                real_values, 
                sim_values,
                n_peaks=analysis_options["peak_analysis"].get("n_peaks", 5)
            )
            metrics.update({f"peak_{k}": v for k, v in peak_metrics.items()})
        
        # Ramp rate analysis if enabled
        if analysis_options.get("ramp_rate_analysis", False):
            ramp_metrics = analyze_ramp_rates(real_values, sim_values)
            metrics.update({f"ramp_{k}": v for k, v in ramp_metrics.items()})
        
        return metrics
    
    def _add_to_results(self, real_bldg_id: str, sim_bldg_id: str, 
                       var_name: str, metrics: Dict[str, Any], date_cols: List[str]):
        """Add results to storage"""
        
        # Summary result
        summary_row = {
            "validation_id": self.validation_id,
            "timestamp": datetime.now().isoformat(),
            "real_building_id": real_bldg_id,
            "sim_building_id": sim_bldg_id,
            "variable_name": var_name,
            "variable_category": self._categorize_variable(var_name),
            "annual_cvrmse": metrics["cvrmse"],
            "annual_nmbe": metrics["nmbe"],
            "annual_mbe": metrics["mbe"],
            "annual_r2": metrics["r2"],
            "annual_pass": metrics["pass"],
            "pass_cvrmse": metrics["pass_cvrmse"],
            "pass_nmbe": metrics["pass_nmbe"],
            "cvrmse_threshold": metrics["cvrmse_threshold"],
            "nmbe_threshold": metrics["nmbe_threshold"],
            "data_points": metrics["data_points"],
            "data_completeness": metrics["data_points"] / len(date_cols) * 100 if date_cols else 0,
            "real_mean": metrics["real_mean"],
            "sim_mean": metrics["sim_mean"],
            "real_std": metrics["real_std"],
            "sim_std": metrics["sim_std"]
        }
        
        # Add peak metrics if available
        for key, value in metrics.items():
            if key.startswith("peak_") or key.startswith("ramp_"):
                summary_row[key] = value
        
        self.summary_results.append(summary_row)
        
        # Add to failed results if not passing
        if not metrics["pass"]:
            fail_row = summary_row.copy()
            fail_row["failure_reason"] = []
            
            if not metrics["pass_cvrmse"]:
                fail_row["failure_reason"].append(f"CVRMSE={metrics['cvrmse']:.1f}% > {metrics['cvrmse_threshold']}%")
            if not metrics["pass_nmbe"]:
                fail_row["failure_reason"].append(f"NMBE={abs(metrics['nmbe']):.1f}% > {metrics['nmbe_threshold']}%")
            
            # Check for unit issues
            value_ratio = metrics["sim_mean"] / metrics["real_mean"] if metrics["real_mean"] != 0 else 0
            if value_ratio > 100:
                fail_row["failure_reason"].append(f"Possible unit issue (ratio={value_ratio:.1f})")
            
            fail_row["failure_reason"] = "; ".join(fail_row["failure_reason"])
            
            self.failed_results.append(fail_row)
        
        # Detailed metrics
        detailed_row = {
            "validation_id": self.validation_id,
            "real_building_id": real_bldg_id,
            "sim_building_id": sim_bldg_id,
            "variable_name": var_name,
            "analysis_slice": "annual",
            "slice_type": "full",
            **metrics
        }
        self.detailed_results.append(detailed_row)
    
    def _add_missing_data_result(self, real_bldg_id: str, sim_bldg_ids: List[str], 
                                variables: List[str]):
        """Add result for missing simulation data"""
        for sim_bldg_id in sim_bldg_ids:
            for var_name in variables:
                fail_row = {
                    "validation_id": self.validation_id,
                    "timestamp": datetime.now().isoformat(),
                    "real_building_id": real_bldg_id,
                    "sim_building_id": sim_bldg_id,
                    "variable_name": var_name,
                    "failure_reason": "No simulation data found",
                    "annual_pass": False
                }
                self.failed_results.append(fail_row)
    
    def _add_alignment_error_result(self, real_bldg_id: str, sim_bldg_ids: List[str], 
                                   error_msg: str):
        """Add result for data alignment errors"""
        for sim_bldg_id in sim_bldg_ids:
            fail_row = {
                "validation_id": self.validation_id,
                "timestamp": datetime.now().isoformat(),
                "real_building_id": real_bldg_id,
                "sim_building_id": sim_bldg_id,
                "variable_name": "ALL",
                "failure_reason": f"Data alignment error: {error_msg}",
                "annual_pass": False
            }
            self.failed_results.append(fail_row)
    
    def _categorize_variable(self, var_name: str) -> str:
        """Categorize variable based on name"""
        var_lower = var_name.lower()
        
        if 'electricity' in var_lower:
            return 'electricity'
        elif 'heating' in var_lower:
            return 'heating'
        elif 'cooling' in var_lower:
            return 'cooling'
        elif 'temperature' in var_lower:
            return 'comfort'
        elif 'energy' in var_lower:
            return 'energy'
        else:
            return 'other'
    
    def _save_results(self) -> Dict[str, pd.DataFrame]:
        """Save all results to Parquet files"""
        output_dir = self.job_output_dir / "validation_results"
        output_dir.mkdir(exist_ok=True)
        
        results = {}
        
        # Save summary
        if self.summary_results:
            summary_df = pd.DataFrame(self.summary_results)
            summary_path = output_dir / "validation_summary.parquet"
            summary_df.to_parquet(summary_path, index=False)
            results["summary"] = summary_df
            logger.info(f"Saved summary results: {len(summary_df)} rows")
        
        # Save detailed metrics
        if self.detailed_results:
            detailed_df = pd.DataFrame(self.detailed_results)
            detailed_path = output_dir / "detailed_metrics.parquet"
            detailed_df.to_parquet(detailed_path, index=False)
            results["detailed"] = detailed_df
        
        # Save failed validations
        if self.failed_results:
            failed_df = pd.DataFrame(self.failed_results)
            failed_path = output_dir / "failed_validations.parquet"
            failed_df.to_parquet(failed_path, index=False)
            results["failed"] = failed_df
            logger.info(f"Saved failed validations: {len(failed_df)} rows")
        
        # Save unit conversion warnings
        if self.unit_conversion_log:
            unit_df = pd.DataFrame(self.unit_conversion_log)
            unit_path = output_dir / "unit_conversion_warnings.parquet"
            unit_df.to_parquet(unit_path, index=False)
            results["unit_warnings"] = unit_df
            logger.warning(f"Potential unit issues found: {len(unit_df)} warnings")
        
        # Save metadata
        metadata = {
            "validation_id": self.validation_id,
            "timestamp": datetime.now().isoformat(),
            "config": self.config.to_dict(),
            "total_validations": len(self.summary_results),
            "failed_validations": len(self.failed_results),
            "pass_rate": (len(self.summary_results) - len(self.failed_results)) / len(self.summary_results) * 100 if self.summary_results else 0,
            "variables_validated": list(set(r["variable_name"] for r in self.summary_results)) if self.summary_results else [],
            "buildings_validated": {
                "real": list(set(r["real_building_id"] for r in self.summary_results)) if self.summary_results else [],
                "sim": list(set(r["sim_building_id"] for r in self.summary_results)) if self.summary_results else []
            },
            "unit_warnings": len(self.unit_conversion_log)
        }
        
        metadata_path = output_dir / "validation_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Validation complete. Pass rate: {metadata['pass_rate']:.1f}%")
        
        return results