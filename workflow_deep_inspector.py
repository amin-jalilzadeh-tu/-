"""
E+ Workflow Configuration Analyzer

Performs three-way analysis between:
1. Configuration (combined.json) - What should happen
2. Code expectations - What Python modules expect
3. Actual data - What really exists
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set, Any
import glob
import logging
import re

class WorkflowConfigurationAnalyzer:
    """Analyzes workflow configuration vs code expectations vs reality"""
    
    def __init__(self, job_output_dir: str):
        self.job_output_dir = Path(job_output_dir)
        self.job_id = self.job_output_dir.name
        
        # Setup logging
        self.setup_logging()
        
        # Will be populated by analysis
        self.config = None
        self.actual_data = {}
        self.code_expectations = self._define_code_expectations()
        self.analysis_results = {}
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.job_output_dir / "configuration_analysis.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_configuration(self) -> bool:
        """Load combined.json configuration file"""
        config_files = list(self.job_output_dir.glob("combined*.json"))
        
        if not config_files:
            self.logger.error("No combined.json configuration file found!")
            return False
        
        config_file = config_files[0]
        self.logger.info(f"Loading configuration from: {config_file.name}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            return True
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            return False
    
    def _define_code_expectations(self) -> Dict[str, Dict]:
        """Define what each Python module expects based on code analysis"""
        return {
            'idf_creation': {
                'module': 'idf_creation_step.py',
                'config_keys': ['idf_creation'],
                'expected_inputs': {
                    'building_data': {
                        'type': 'csv',
                        'required_columns': ['building_id', 'building_function', 'building_type', 'age_range'],
                        'config_path': 'paths.building_data'
                    },
                    'user_configs': {
                        'type': 'json',
                        'sections': ['dhw', 'epw', 'fenestration', 'geometry', 'hvac', 'lighting', 'vent', 'shading'],
                        'config_path': 'user_config_overrides'
                    }
                },
                'expected_outputs': {
                    'output_IDFs': {
                        'type': 'directory',
                        'files': '*.idf',
                        'config_path': 'idf_creation.output_idf_dir'
                    },
                    'idf_tracker.json': {
                        'type': 'file',
                        'content': 'IDF creation metadata'
                    }
                }
            },
            
            'simulation': {
                'module': 'simulation_step.py',
                'config_keys': ['idf_creation.run_simulations'],
                'expected_inputs': {
                    'idf_files': {
                        'type': 'idf',
                        'path': 'output_IDFs/*.idf'
                    },
                    'weather_files': {
                        'type': 'epw',
                        'config_path': 'epw'
                    }
                },
                'expected_outputs': {
                    'Sim_Results': {
                        'type': 'directory',
                        'files': ['*.sql', '*.htm', '*.csv'],
                        'per_building': True
                    }
                }
            },
            
            'parsing': {
                'module': 'parsing_step.py',
                'config_keys': ['parsing'],
                'expected_inputs': {
                    'sql_files': {
                        'type': 'sql',
                        'path': 'Sim_Results/*/*.sql',
                        'required_if': 'parsing.parse_types.sql'
                    },
                    'idf_files': {
                        'type': 'idf',
                        'path': 'output_IDFs/*.idf',
                        'required_if': 'parsing.parse_types.idf'
                    }
                },
                'expected_outputs': {
                    'parsed_data': {
                        'type': 'directory',
                        'subdirs': ['idf_data', 'output_data'],
                        'files': {
                            'idf_data/by_category': ['*.parquet'],
                            'output_data': ['*.parquet']
                        }
                    }
                }
            },
            
            'modification': {
                'module': 'modification_step.py',
                'config_keys': ['modification'],
                'expected_inputs': {
                    'base_idfs': {
                        'type': 'idf',
                        'path': 'output_IDFs/*.idf'
                    },
                    'parsed_data': {
                        'type': 'parquet',
                        'path': 'parsed_data/idf_data/by_category/*.parquet',
                        'optional': True
                    }
                },
                'expected_outputs': {
                    'modified_idfs': {
                        'type': 'directory',
                        'files': ['*.idf', 'modification_summary.json'],
                        'subdirs': ['scenario_*', 'variant_*']
                    }
                }
            },
            
            'sensitivity': {
                'module': 'sensitivity_step.py',
                'config_keys': ['sensitivity'],
                'expected_inputs': {
                    'parsed_output_data': {
                        'type': 'parquet',
                        'path': 'parsed_data/output_data/*.parquet',
                        'required_columns': {
                            'building_energy': ['building_id', 'datetime', 'variable_name', 'value'],
                            'zone_data': ['building_id', 'zone_name', 'datetime', 'temperature']
                        }
                    },
                    'parsed_idf_data': {
                        'type': 'parquet',
                        'path': 'parsed_data/idf_data/by_category/*.parquet',
                        'categories': ['lighting', 'hvac', 'materials', 'infiltration']
                    },
                    'parsed_modified_results': {
                        'type': 'parquet',
                        'path': 'parsed_modified_results/output_data/*.parquet',
                        'required_if': 'sensitivity.analysis_type == "modification_based"'
                    }
                },
                'expected_outputs': {
                    'sensitivity_results': {
                        'type': 'directory',
                        'files': {
                            'rankings': ['sensitivity_rankings.parquet', 'parameter_impacts.parquet'],
                            'reports': ['sensitivity_summary.json', '*.html'],
                            'advanced': ['uncertainty_analysis_results.parquet', 'threshold_analysis_results.parquet']
                        }
                    }
                }
            },
            
            'surrogate': {
                'module': 'surrogate_step.py',
                'config_keys': ['surrogate'],
                'expected_inputs': {
                    'sensitivity_results': {
                        'type': 'parquet',
                        'path': 'sensitivity_results/*.parquet',
                        'filter_by': 'surrogate.sensitivity_results_path'
                    },
                    'modification_data': {
                        'type': 'mixed',
                        'paths': [
                            'parsed_data/idf_data/',
                            'parsed_modified_results/'
                        ],
                        'required_if': 'surrogate.require_modifications'
                    }
                },
                'expected_outputs': {
                    'surrogate_models': {
                        'type': 'directory',
                        'files': {
                            'models': ['*.pkl', '*.joblib'],
                            'metadata': ['model_config.json', 'feature_importance.json'],
                            'validation': ['validation_report.json']
                        },
                        'versioning': 'surrogate.output_management.version'
                    }
                }
            },
            
            'validation': {
                'module': 'validation_step.py',
                'config_keys': ['validation'],
                'expected_inputs': {
                    'simulation_data': {
                        'type': 'parquet',
                        'path': 'parsed_data/output_data/*.parquet',
                        'stages': {
                            'baseline': 'parsed_data',
                            'modified': 'parsed_modified_results'
                        }
                    },
                    'measured_data': {
                        'type': 'csv',
                        'config_path': 'validation.stages.*.config.real_data_path',
                        'required_columns': ['building_id', 'datetime', 'variable', 'value', 'units']
                    }
                },
                'expected_outputs': {
                    'validation_results': {
                        'type': 'directory',
                        'subdirs': ['baseline', 'modified'],
                        'files': ['validation_summary.json', '*.html', '*.parquet']
                    }
                }
            }
        }
    
    def scan_actual_data(self):
        """Scan the output directory to find what actually exists"""
        self.logger.info("\n" + "="*80)
        self.logger.info("SCANNING ACTUAL DATA")
        self.logger.info("="*80)
        
        for item in self.job_output_dir.iterdir():
            if item.is_dir():
                self.actual_data[item.name] = self._scan_directory_deep(item)
            elif item.is_file():
                if 'root_files' not in self.actual_data:
                    self.actual_data['root_files'] = {}
                self.actual_data['root_files'][item.name] = self._analyze_file(item)
    
    def _scan_directory_deep(self, directory: Path) -> Dict:
        """Recursively scan directory and analyze contents"""
        result = {
            'type': 'directory',
            'path': str(directory.relative_to(self.job_output_dir)),
            'files': {},
            'subdirs': {}
        }
        
        for item in directory.iterdir():
            if item.is_file():
                result['files'][item.name] = self._analyze_file(item)
            elif item.is_dir():
                result['subdirs'][item.name] = self._scan_directory_deep(item)
        
        return result
    
    def _analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single file"""
        info = {
            'type': file_path.suffix[1:] if file_path.suffix else 'unknown',
            'size': file_path.stat().st_size,
            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
        }
        
        # Analyze specific file types
        if file_path.suffix == '.parquet':
            try:
                df = pd.read_parquet(file_path)
                info.update({
                    'shape': df.shape,
                    'columns': list(df.columns),
                    'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
                    'sample_values': self._get_sample_values(df)
                })
            except:
                info['error'] = 'Failed to read parquet'
        
        elif file_path.suffix == '.json':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                info['structure'] = self._analyze_json_structure(data)
            except:
                info['error'] = 'Failed to read JSON'
        
        elif file_path.suffix == '.csv':
            try:
                df = pd.read_csv(file_path, nrows=5)
                info.update({
                    'columns': list(df.columns),
                    'sample_rows': len(df)
                })
            except:
                info['error'] = 'Failed to read CSV'
        
        return info
    
    def _get_sample_values(self, df: pd.DataFrame) -> Dict:
        """Get sample values from dataframe columns"""
        samples = {}
        for col in df.columns[:10]:  # Limit to first 10 columns
            if df[col].nunique() < 20:
                samples[col] = sorted(df[col].dropna().unique().tolist())[:5]
            else:
                samples[col] = {
                    'dtype': str(df[col].dtype),
                    'unique': int(df[col].nunique()),
                    'nulls': int(df[col].isnull().sum())
                }
        return samples
    
    def _analyze_json_structure(self, data: Any, max_depth: int = 3, current_depth: int = 0) -> Any:
        """Analyze JSON structure recursively"""
        if current_depth >= max_depth:
            return "..."
        
        if isinstance(data, dict):
            return {
                'type': 'dict',
                'keys': list(data.keys())[:10],
                'size': len(data)
            }
        elif isinstance(data, list):
            return {
                'type': 'list',
                'length': len(data),
                'item_type': type(data[0]).__name__ if data else 'empty'
            }
        else:
            return type(data).__name__
    
    def analyze_step(self, step_name: str) -> Dict:
        """Analyze a specific workflow step"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"ANALYZING: {step_name.upper()}")
        self.logger.info(f"{'='*60}")
        
        step_spec = self.code_expectations.get(step_name, {})
        analysis = {
            'step': step_name,
            'configuration': {},
            'code_expects': step_spec,
            'actual_data': {},
            'issues': [],
            'recommendations': []
        }
        
        # 1. Check configuration
        config_status = self._check_configuration(step_name, step_spec)
        analysis['configuration'] = config_status
        
        # 2. Check expected inputs
        if 'expected_inputs' in step_spec:
            input_analysis = self._check_inputs(step_name, step_spec['expected_inputs'])
            analysis['inputs'] = input_analysis
        
        # 3. Check expected outputs
        if 'expected_outputs' in step_spec:
            output_analysis = self._check_outputs(step_name, step_spec['expected_outputs'])
            analysis['outputs'] = output_analysis
        
        # 4. Generate diagnostics
        self._generate_diagnostics(analysis)
        
        return analysis
    
    def _check_configuration(self, step_name: str, step_spec: Dict) -> Dict:
        """Check if step is properly configured"""
        config_status = {
            'enabled': False,
            'config_present': False,
            'settings': {}
        }
        
        if not self.config:
            return config_status
        
        # Check if step is enabled
        if step_name == 'idf_creation':
            enabled = self.config.get('main_config', {}).get('idf_creation', {}).get('perform_idf_creation', False)
            config_section = self.config.get('main_config', {}).get('idf_creation', {})
        elif step_name == 'simulation':
            enabled = self.config.get('main_config', {}).get('idf_creation', {}).get('run_simulations', False)
            config_section = self.config.get('main_config', {}).get('idf_creation', {}).get('simulate_config', {})
        elif step_name == 'parsing':
            enabled = self.config.get('main_config', {}).get('parsing', {}).get('perform_parsing', False)
            config_section = self.config.get('main_config', {}).get('parsing', {})
        elif step_name == 'modification':
            enabled = self.config.get('main_config', {}).get('modification', {}).get('perform_modification', False)
            config_section = self.config.get('main_config', {}).get('modification', {})
        elif step_name == 'sensitivity':
            enabled = self.config.get('main_config', {}).get('sensitivity', {}).get('perform_sensitivity', False)
            config_section = self.config.get('main_config', {}).get('sensitivity', {})
        elif step_name == 'surrogate':
            enabled = self.config.get('main_config', {}).get('surrogate', {}).get('perform_surrogate', False)
            config_section = self.config.get('main_config', {}).get('surrogate', {})
        elif step_name == 'validation':
            enabled = self.config.get('main_config', {}).get('validation', {}).get('perform_validation', False)
            config_section = self.config.get('main_config', {}).get('validation', {})
        else:
            enabled = False
            config_section = {}
        
        config_status['enabled'] = enabled
        config_status['config_present'] = bool(config_section)
        config_status['settings'] = self._extract_key_settings(config_section)
        
        self.logger.info(f"Configuration: {'ENABLED' if enabled else 'DISABLED'}")
        if config_status['settings']:
            for key, value in list(config_status['settings'].items())[:5]:
                self.logger.info(f"  {key}: {value}")
        
        return config_status
    
    def _extract_key_settings(self, config_section: Dict) -> Dict:
        """Extract key settings from configuration section"""
        key_settings = {}
        
        # Extract important settings
        important_keys = [
            'perform_', 'method', 'strategy', 'analysis_type', 'output_dir',
            'parse_types', 'categories_to_modify', 'target_variables',
            'time_slicing', 'use_integrated_pipeline', 'stages'
        ]
        
        for key, value in config_section.items():
            if any(important in key for important in important_keys):
                if isinstance(value, dict):
                    key_settings[key] = f"dict with {len(value)} keys"
                elif isinstance(value, list):
                    key_settings[key] = f"list with {len(value)} items"
                else:
                    key_settings[key] = value
        
        return key_settings
    
    def _check_inputs(self, step_name: str, expected_inputs: Dict) -> Dict:
        """Check if expected inputs exist"""
        input_status = {}
        
        for input_name, input_spec in expected_inputs.items():
            self.logger.info(f"\nChecking input: {input_name}")
            
            status = {
                'expected': input_spec,
                'found': False,
                'actual_path': None,
                'issues': []
            }
            
            # Check different path patterns
            if 'path' in input_spec:
                found_files = self._find_files_by_pattern(input_spec['path'])
                if found_files:
                    status['found'] = True
                    status['actual_files'] = found_files
                    self.logger.info(f"  ✓ Found {len(found_files)} files matching pattern")
                else:
                    status['issues'].append(f"No files found matching: {input_spec['path']}")
                    self.logger.warning(f"  ✗ No files found matching: {input_spec['path']}")
            
            # Check required columns if applicable
            if status['found'] and 'required_columns' in input_spec:
                column_issues = self._check_columns(found_files[0], input_spec['required_columns'])
                status['column_check'] = column_issues
                if column_issues:
                    status['issues'].extend(column_issues)
            
            input_status[input_name] = status
        
        return input_status
    
    def _check_outputs(self, step_name: str, expected_outputs: Dict) -> Dict:
        """Check if expected outputs exist"""
        output_status = {}
        
        for output_name, output_spec in expected_outputs.items():
            self.logger.info(f"\nChecking output: {output_name}")
            
            status = {
                'expected': output_spec,
                'found': False,
                'actual_path': None,
                'issues': []
            }
            
            # Check if directory exists
            if output_name in self.actual_data:
                status['found'] = True
                status['actual_path'] = output_name
                self.logger.info(f"  ✓ Found output directory: {output_name}")
                
                # Check for expected files
                if 'files' in output_spec:
                    actual_files = self._get_all_files_in_dir(self.actual_data[output_name])
                    if isinstance(output_spec['files'], dict):
                        for subdir, patterns in output_spec['files'].items():
                            for pattern in patterns:
                                if not any(self._matches_pattern(f, pattern) for f in actual_files):
                                    status['issues'].append(f"Missing expected file pattern: {subdir}/{pattern}")
                    elif isinstance(output_spec['files'], list):
                        for pattern in output_spec['files']:
                            if not any(self._matches_pattern(f, pattern) for f in actual_files):
                                status['issues'].append(f"Missing expected file pattern: {pattern}")
            else:
                status['issues'].append(f"Output directory not found: {output_name}")
                self.logger.warning(f"  ✗ Output directory not found: {output_name}")
            
            output_status[output_name] = status
        
        return output_status
    
    def _find_files_by_pattern(self, pattern: str) -> List[Path]:
        """Find files matching a pattern"""
        search_path = self.job_output_dir / pattern
        matches = glob.glob(str(search_path))
        return [Path(m) for m in matches]
    
    def _check_columns(self, file_path: Path, expected_columns: Any) -> List[str]:
        """Check if file has expected columns"""
        issues = []
        
        if not file_path.exists():
            return ["File not found"]
        
        if file_path.suffix == '.parquet':
            try:
                df = pd.read_parquet(file_path)
                actual_columns = set(df.columns)
                
                if isinstance(expected_columns, dict):
                    # Different expected columns for different file types
                    for file_type, columns in expected_columns.items():
                        if file_type in file_path.name:
                            missing = set(columns) - actual_columns
                            if missing:
                                issues.append(f"Missing columns in {file_path.name}: {missing}")
                else:
                    # Single list of expected columns
                    missing = set(expected_columns) - actual_columns
                    if missing:
                        issues.append(f"Missing columns: {missing}")
            except Exception as e:
                issues.append(f"Failed to read parquet: {str(e)}")
        
        return issues
    
    def _get_all_files_in_dir(self, dir_info: Dict) -> List[str]:
        """Recursively get all files in a directory structure"""
        files = []
        
        if 'files' in dir_info:
            files.extend(dir_info['files'].keys())
        
        if 'subdirs' in dir_info:
            for subdir_info in dir_info['subdirs'].values():
                files.extend(self._get_all_files_in_dir(subdir_info))
        
        return files
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches a pattern"""
        if '*' in pattern:
            # Convert glob pattern to regex
            regex_pattern = pattern.replace('*', '.*').replace('?', '.')
            return bool(re.match(regex_pattern, filename))
        else:
            return pattern in filename
    
    def _generate_diagnostics(self, analysis: Dict):
        """Generate specific diagnostics and recommendations"""
        step_name = analysis['step']
        
        # Check configuration issues
        if not analysis['configuration']['enabled']:
            analysis['issues'].append(f"{step_name} is DISABLED in configuration")
            analysis['recommendations'].append(f"Enable {step_name} by setting perform_{step_name}=true")
        
        # Check input issues
        if 'inputs' in analysis:
            for input_name, input_status in analysis['inputs'].items():
                if not input_status['found']:
                    analysis['issues'].append(f"Missing required input: {input_name}")
                    
                    # Generate specific recommendations
                    if 'simulation_data' in input_name and 'parsing' in step_name:
                        analysis['recommendations'].append("Run simulation step first to generate SQL files")
                    elif 'parsed_data' in input_name:
                        analysis['recommendations'].append("Run parsing step to extract data from simulation results")
                    elif 'sensitivity_results' in input_name:
                        analysis['recommendations'].append("Run sensitivity analysis first")
        
        # Check output issues
        if 'outputs' in analysis:
            for output_name, output_status in analysis['outputs'].items():
                if output_status['found'] and output_status['issues']:
                    for issue in output_status['issues']:
                        analysis['issues'].append(issue)
    
    def generate_comprehensive_report(self) -> Dict:
        """Generate comprehensive analysis report"""
        self.logger.info("\n" + "="*80)
        self.logger.info("E+ WORKFLOW CONFIGURATION ANALYSIS")
        self.logger.info("="*80)
        
        # Load configuration
        if not self.load_configuration():
            return {"error": "Failed to load configuration"}
        
        # Scan actual data
        self.scan_actual_data()
        
        # Analyze each step
        steps = ['idf_creation', 'simulation', 'parsing', 'modification', 
                 'sensitivity', 'surrogate', 'validation']
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'job_id': self.job_id,
            'steps': {}
        }
        
        for step in steps:
            report['steps'][step] = self.analyze_step(step)
        
        # Generate summary
        report['summary'] = self._generate_summary(report['steps'])
        
        return report
    
    def _generate_summary(self, steps_analysis: Dict) -> Dict:
        """Generate summary of analysis"""
        summary = {
            'total_steps': len(steps_analysis),
            'enabled_steps': sum(1 for s in steps_analysis.values() if s['configuration']['enabled']),
            'steps_with_issues': sum(1 for s in steps_analysis.values() if s['issues']),
            'ready_to_run': [],
            'blocked_steps': [],
            'completed_steps': []
        }
        
        for step_name, analysis in steps_analysis.items():
            if not analysis['configuration']['enabled']:
                continue
            
            has_inputs = all(inp.get('found', False) for inp in analysis.get('inputs', {}).values())
            has_outputs = any(out.get('found', False) for out in analysis.get('outputs', {}).values())
            
            if has_outputs:
                summary['completed_steps'].append(step_name)
            elif has_inputs:
                summary['ready_to_run'].append(step_name)
            else:
                summary['blocked_steps'].append(step_name)
        
        return summary
    
    def print_report(self, report: Dict):
        """Print human-readable report"""
        print("\n" + "="*80)
        print("WORKFLOW CONFIGURATION ANALYSIS REPORT")
        print("="*80)
        print(f"Job ID: {report['job_id']}")
        print(f"Generated: {report['timestamp']}")
        
        # Summary
        summary = report['summary']
        print(f"\nSUMMARY:")
        print(f"  Total steps: {summary['total_steps']}")
        print(f"  Enabled steps: {summary['enabled_steps']}")
        print(f"  Steps with issues: {summary['steps_with_issues']}")
        
        if summary['completed_steps']:
            print(f"\n✅ COMPLETED: {', '.join(summary['completed_steps'])}")
        if summary['ready_to_run']:
            print(f"\n🟡 READY TO RUN: {', '.join(summary['ready_to_run'])}")
        if summary['blocked_steps']:
            print(f"\n❌ BLOCKED: {', '.join(summary['blocked_steps'])}")
        
        # Detailed analysis
        print("\n" + "-"*80)
        print("DETAILED ANALYSIS:")
        print("-"*80)
        
        for step_name, analysis in report['steps'].items():
            config = analysis['configuration']
            
            print(f"\n{step_name.upper()}:")
            print(f"  Status: {'ENABLED' if config['enabled'] else 'DISABLED'}")
            
            if config['enabled']:
                # Show key settings
                if config['settings']:
                    print("  Key settings:")
                    for key, value in list(config['settings'].items())[:3]:
                        print(f"    - {key}: {value}")
                
                # Show input status
                if 'inputs' in analysis:
                    print("  Inputs:")
                    for inp_name, inp_status in analysis['inputs'].items():
                        status = "✓" if inp_status['found'] else "✗"
                        print(f"    {status} {inp_name}")
                        if inp_status['issues']:
                            for issue in inp_status['issues']:
                                print(f"      ⚠ {issue}")
                
                # Show output status
                if 'outputs' in analysis:
                    print("  Outputs:")
                    for out_name, out_status in analysis['outputs'].items():
                        status = "✓" if out_status['found'] else "✗"
                        print(f"    {status} {out_name}")
                        if out_status['issues']:
                            for issue in out_status['issues']:
                                print(f"      ⚠ {issue}")
                
                # Show recommendations
                if analysis['recommendations']:
                    print("  Recommendations:")
                    for rec in analysis['recommendations']:
                        print(f"    → {rec}")
    
    def save_reports(self, report: Dict):
        """Save analysis reports"""
        # Save JSON report
        json_file = self.job_output_dir / "configuration_analysis.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save text report
        text_file = self.job_output_dir / "configuration_analysis.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            # Redirect print to file
            import sys
            old_stdout = sys.stdout
            sys.stdout = f
            self.print_report(report)
            sys.stdout = old_stdout
        
        self.logger.info(f"\nReports saved:")
        self.logger.info(f"  - {json_file}")
        self.logger.info(f"  - {text_file}")


def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python workflow_config_analyzer.py <job_output_directory>")
        print("\nThis tool will:")
        print("  1. Read your combined.json configuration")
        print("  2. Check what each Python module expects")
        print("  3. Scan what actually exists in your output")
        print("  4. Identify mismatches and provide fixes")
        sys.exit(1)
    
    job_output_dir = sys.argv[1]
    
    # Create analyzer
    analyzer = WorkflowConfigurationAnalyzer(job_output_dir)
    
    # Generate report
    report = analyzer.generate_comprehensive_report()
    
    # Print and save results
    analyzer.print_report(report)
    analyzer.save_reports(report)


if __name__ == "__main__":
    main()