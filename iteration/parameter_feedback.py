import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class ParameterFeedback:
    """
    Handles conversion of calibration results to modification inputs
    and manages parameter flow between iterations
    """
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.base_dir = Path(f"iterations/{job_id}")
        
        # Parameter mapping configuration
        self.parameter_mapping = self._load_parameter_mapping()
        
    def _load_parameter_mapping(self) -> Dict[str, Dict[str, Any]]:
        """Load parameter mapping configuration"""
        # Define how calibration parameters map to modification configs
        return {
            # Envelope parameters
            'infiltration_rate': {
                'modification_type': 'envelope',
                'idf_object': 'ZoneInfiltration:DesignFlowRate',
                'field': 'Flow per Exterior Surface Area',
                'unit_conversion': 1.0,
                'constraints': {'min': 0.0001, 'max': 0.003}
            },
            'window_u_value': {
                'modification_type': 'fenestration',
                'idf_object': 'WindowMaterial:SimpleGlazingSystem',
                'field': 'U-Factor',
                'unit_conversion': 1.0,
                'constraints': {'min': 0.5, 'max': 6.0}
            },
            'wall_insulation': {
                'modification_type': 'envelope',
                'idf_object': 'Material',
                'field': 'Thickness',
                'unit_conversion': 1.0,
                'constraints': {'min': 0.01, 'max': 0.5}
            },
            'hvac_efficiency': {
                'modification_type': 'hvac',
                'idf_object': 'Coil:Heating:Gas',
                'field': 'Gas Burner Efficiency',
                'unit_conversion': 1.0,
                'constraints': {'min': 0.7, 'max': 0.98}
            },
            'cooling_cop': {
                'modification_type': 'hvac',
                'idf_object': 'Coil:Cooling:DX:SingleSpeed',
                'field': 'Rated COP',
                'unit_conversion': 1.0,
                'constraints': {'min': 2.0, 'max': 6.0}
            },
            'lighting_power_density': {
                'modification_type': 'lighting',
                'idf_object': 'Lights',
                'field': 'Watts per Zone Floor Area',
                'unit_conversion': 1.0,
                'constraints': {'min': 2.0, 'max': 20.0}
            },
            'equipment_power_density': {
                'modification_type': 'equipment',
                'idf_object': 'ElectricEquipment',
                'field': 'Watts per Zone Floor Area',
                'unit_conversion': 1.0,
                'constraints': {'min': 2.0, 'max': 30.0}
            },
            'shading_transmittance': {
                'modification_type': 'shading',
                'idf_object': 'WindowMaterial:Shade',
                'field': 'Solar Transmittance',
                'unit_conversion': 1.0,
                'constraints': {'min': 0.0, 'max': 0.9}
            }
        }
    
    def convert_calibration_to_modification(self, 
                                           calibration_params: Dict[str, float],
                                           iteration_dir: str) -> Dict[str, Any]:
        """
        Convert calibration parameters to modification configuration
        """
        logger.info(f"Converting calibration parameters for iteration in {iteration_dir}")
        
        # Group parameters by modification type
        modifications_by_type = {}
        
        for param_name, param_value in calibration_params.items():
            if param_name in self.parameter_mapping:
                mapping = self.parameter_mapping[param_name]
                mod_type = mapping['modification_type']
                
                if mod_type not in modifications_by_type:
                    modifications_by_type[mod_type] = {}
                
                # Apply constraints
                constrained_value = self._apply_constraints(param_value, mapping['constraints'])
                
                # Apply unit conversion
                converted_value = constrained_value * mapping['unit_conversion']
                
                modifications_by_type[mod_type][param_name] = {
                    'value': converted_value,
                    'idf_object': mapping['idf_object'],
                    'field': mapping['field'],
                    'original_value': param_value
                }
        
        # Create modification configuration files
        modification_configs = self._create_modification_configs(modifications_by_type, iteration_dir)
        
        return modification_configs
    
    def _apply_constraints(self, value: float, constraints: Dict[str, float]) -> float:
        """Apply min/max constraints to parameter value"""
        if 'min' in constraints:
            value = max(value, constraints['min'])
        if 'max' in constraints:
            value = min(value, constraints['max'])
        return value
    
    def _create_modification_configs(self, 
                                   modifications_by_type: Dict[str, Dict],
                                   iteration_dir: str) -> Dict[str, Any]:
        """
        Create modification configuration files for each type
        """
        config_dir = Path(iteration_dir) / 'modification_configs'
        config_dir.mkdir(exist_ok=True)
        
        configs_created = {}
        
        # Create scenario file
        scenario_data = {
            'scenario_name': f'iteration_{Path(iteration_dir).name}',
            'description': f'Automatically generated from calibration iteration',
            'timestamp': datetime.now().isoformat(),
            'modifications': []
        }
        
        for mod_type, modifications in modifications_by_type.items():
            # Create individual modification config
            mod_config = {
                'modification_type': mod_type,
                'parameters': modifications,
                'apply_to_all_zones': True,
                'apply_to_all_surfaces': True
            }
            
            # Save modification config
            config_file = config_dir / f'{mod_type}_modifications.json'
            with open(config_file, 'w') as f:
                json.dump(mod_config, f, indent=2)
            
            configs_created[mod_type] = str(config_file)
            
            # Add to scenario
            scenario_data['modifications'].append({
                'type': mod_type,
                'config_file': str(config_file),
                'enabled': True
            })
        
        # Save scenario file
        scenario_file = config_dir / 'calibration_scenario.json'
        with open(scenario_file, 'w') as f:
            json.dump(scenario_data, f, indent=2)
        
        configs_created['scenario'] = str(scenario_file)
        
        logger.info(f"Created {len(configs_created)} modification configs in {config_dir}")
        
        return configs_created
    
    def create_idf_modification_script(self, 
                                     calibration_params: Dict[str, float],
                                     base_idf_path: str,
                                     output_idf_path: str) -> str:
        """
        Create a script to directly modify IDF file with calibrated parameters
        """
        script_content = f"""
import json
from pathlib import Path
from eppy import modeleditor
from eppy.modeleditor import IDF

# Load calibrated parameters
params = {json.dumps(calibration_params, indent=2)}

# Load base IDF
IDF.setiddfile('path/to/Energy+.idd')  # Update with correct path
idf = IDF('{base_idf_path}')

# Apply modifications
"""
        
        for param_name, param_value in calibration_params.items():
            if param_name in self.parameter_mapping:
                mapping = self.parameter_mapping[param_name]
                script_content += f"""
# Modify {param_name}
objects = idf.idfobjects['{mapping['idf_object']}']
for obj in objects:
    obj['{mapping['field']}'] = {param_value}
"""
        
        script_content += f"""
# Save modified IDF
idf.saveas('{output_idf_path}')
print(f"Modified IDF saved to {output_idf_path}")
"""
        
        return script_content
    
    def track_parameter_evolution(self, iteration_id: int) -> pd.DataFrame:
        """
        Track how parameters evolved across iterations
        """
        parameter_history = []
        
        # Collect parameters from all iterations
        for i in range(1, iteration_id + 1):
            iter_dir = self.base_dir / f'iteration_{i:03d}'
            param_file = iter_dir / 'parameters.json'
            
            if param_file.exists():
                with open(param_file, 'r') as f:
                    params = json.load(f)
                    params['iteration'] = i
                    parameter_history.append(params)
        
        if parameter_history:
            df = pd.DataFrame(parameter_history)
            df.set_index('iteration', inplace=True)
            return df
        else:
            return pd.DataFrame()
    
    def analyze_parameter_sensitivity(self, 
                                    parameter_history: pd.DataFrame,
                                    metrics_history: pd.DataFrame) -> Dict[str, float]:
        """
        Analyze sensitivity of metrics to parameter changes
        """
        sensitivity_scores = {}
        
        for param in parameter_history.columns:
            if param in metrics_history.columns:
                continue
                
            # Calculate correlation between parameter changes and metric improvements
            param_changes = parameter_history[param].diff()
            metric_changes = metrics_history['cv_rmse'].diff()
            
            # Remove NaN values
            valid_indices = ~(param_changes.isna() | metric_changes.isna())
            if valid_indices.sum() > 1:
                correlation = np.corrcoef(
                    param_changes[valid_indices],
                    metric_changes[valid_indices]
                )[0, 1]
                
                sensitivity_scores[param] = abs(correlation)
        
        return sensitivity_scores
    
    def suggest_next_parameters(self, 
                              current_params: Dict[str, float],
                              sensitivity_scores: Dict[str, float],
                              improvement_target: float = 0.1) -> Dict[str, float]:
        """
        Suggest parameters for next iteration based on sensitivity analysis
        """
        suggested_params = current_params.copy()
        
        # Sort parameters by sensitivity
        sorted_params = sorted(sensitivity_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Focus on most sensitive parameters
        for param_name, sensitivity in sorted_params[:3]:  # Top 3 most sensitive
            if param_name in suggested_params:
                current_value = suggested_params[param_name]
                
                # Larger changes for more sensitive parameters
                change_magnitude = improvement_target * sensitivity
                
                # Random direction with bias based on previous performance
                direction = np.random.choice([-1, 1], p=[0.3, 0.7])  # Bias towards increase
                
                new_value = current_value * (1 + direction * change_magnitude)
                
                # Apply constraints
                if param_name in self.parameter_mapping:
                    constraints = self.parameter_mapping[param_name]['constraints']
                    new_value = self._apply_constraints(new_value, constraints)
                
                suggested_params[param_name] = new_value
        
        return suggested_params
    
    def export_parameter_report(self, output_path: str):
        """
        Export comprehensive parameter evolution report
        """
        # Get parameter history
        param_history = self.track_parameter_evolution(100)  # Max 100 iterations
        
        if param_history.empty:
            logger.warning("No parameter history found")
            return
        
        # Create report
        report = {
            'job_id': self.job_id,
            'total_iterations': len(param_history),
            'parameter_ranges': {},
            'parameter_changes': {},
            'final_parameters': {}
        }
        
        for param in param_history.columns:
            report['parameter_ranges'][param] = {
                'min': float(param_history[param].min()),
                'max': float(param_history[param].max()),
                'mean': float(param_history[param].mean()),
                'std': float(param_history[param].std())
            }
            
            report['parameter_changes'][param] = {
                'total_change': float(param_history[param].iloc[-1] - param_history[param].iloc[0]),
                'percent_change': float((param_history[param].iloc[-1] - param_history[param].iloc[0]) / param_history[param].iloc[0] * 100)
            }
            
            report['final_parameters'][param] = float(param_history[param].iloc[-1])
        
        # Save report
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Also save parameter history as CSV
        csv_path = Path(output_path).with_suffix('.csv')
        param_history.to_csv(csv_path)
        
        logger.info(f"Parameter report exported to {output_path}")