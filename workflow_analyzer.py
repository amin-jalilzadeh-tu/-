#!/usr/bin/env python3
"""
E+ Unified Workflow Analyzer

A single comprehensive tool that:
1. Tracks workflow steps and their dependencies
2. Validates inputs/outputs for each step
3. Checks configuration vs actual data
4. Provides clear diagnostics and recommendations

Usage: python workflow_analyzer.py <job_output_directory>
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
from collections import defaultdict, OrderedDict

class UnifiedWorkflowAnalyzer:
    """Comprehensive workflow analyzer for E+ pipeline"""
    
    def __init__(self, job_output_dir: str):
        self.job_output_dir = Path(job_output_dir)
        self.job_id = self.job_output_dir.name
        
        # Setup logging
        self._setup_logging()
        
        # Define workflow structure
        self.workflow_steps = self._define_workflow_steps()
        
        # Results storage
        self.scan_results = {}
        self.config_data = None
        self.validation_results = {}
        self.issues = []
        self.recommendations = []
        
    def _setup_logging(self):
        """Setup logging configuration"""
        log_file = self.job_output_dir / "workflow_analysis.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _define_workflow_steps(self) -> OrderedDict:
        """Define workflow steps with dependencies and validation rules"""
        return OrderedDict([
            ('config', {
                'description': 'Configuration files',
                'outputs': ['combined.json'],
                'inputs': [],
                'validate': self._validate_config
            }),
            ('idf_creation', {
                'description': 'IDF file generation',
                'outputs': ['output_IDFs'],
                'inputs': ['config'],
                'expected_files': {
                    'output_IDFs': ['*.idf', 'idf_tracker.json']
                },
                'validate': self._validate_idf_creation
            }),
            ('simulation', {
                'description': 'EnergyPlus simulations',
                'outputs': ['Sim_Results'],
                'inputs': ['output_IDFs'],
                'expected_files': {
                    'Sim_Results/*': ['*.sql', '*.err', '*.htm', '*.csv']
                },
                'validate': self._validate_simulation
            }),
            ('parsing', {
                'description': 'Parse simulation results',
                'outputs': ['parsed_data'],
                'inputs': ['Sim_Results'],
                'expected_files': {
                    'parsed_data': ['*.parquet'],
                    'parsed_data/idf_data': ['*.parquet'],
                    'parsed_data/output_data': ['*.parquet']
                },
                'validate': self._validate_parsing
            }),
            ('modification', {
                'description': 'Modify IDF files',
                'outputs': ['modified_idfs'],
                'inputs': ['output_IDFs', 'parsed_data'],
                'expected_files': {
                    'modified_idfs': ['*.idf', 'modification_summary.json']
                },
                'validate': self._validate_modification
            }),
            ('modified_simulation', {
                'description': 'Simulate modified IDFs',
                'outputs': ['Modified_Sim_Results'],
                'inputs': ['modified_idfs'],
                'expected_files': {
                    'Modified_Sim_Results/*': ['*.sql', '*.err']
                },
                'validate': self._validate_modified_simulation
            }),
            ('modified_parsing', {
                'description': 'Parse modified results',
                'outputs': ['parsed_modified_results'],
                'inputs': ['Modified_Sim_Results'],
                'expected_files': {
                    'parsed_modified_results': ['*.parquet']
                },
                'validate': self._validate_modified_parsing
            }),
            ('sensitivity', {
                'description': 'Sensitivity analysis',
                'outputs': ['sensitivity_results'],
                'inputs': ['parsed_data', 'parsed_modified_results'],
                'expected_files': {
                    'sensitivity_results': ['sensitivity_rankings.parquet', 'sensitivity_metrics.json']
                },
                'validate': self._validate_sensitivity
            }),
            ('surrogate', {
                'description': 'Surrogate modeling',
                'outputs': ['surrogate_models'],
                'inputs': ['parsed_data', 'parsed_modified_results', 'sensitivity_results'],
                'expected_files': {
                    'surrogate_models/*/': ['model.pkl', 'config.json', 'performance_metrics.json']
                },
                'validate': self._validate_surrogate
            }),
            ('validation', {
                'description': 'Validation against measured data',
                'outputs': ['validation_results'],
                'inputs': ['parsed_data', 'parsed_modified_results'],
                'expected_files': {
                    'validation_results': ['validation_summary.json', '*.parquet']
                },
                'validate': self._validate_validation
            })
        ])
    
    def run_analysis(self) -> Dict:
        """Run complete workflow analysis"""
        self.logger.info("="*80)
        self.logger.info("E+ UNIFIED WORKFLOW ANALYZER")
        self.logger.info("="*80)
        self.logger.info(f"Job Directory: {self.job_output_dir}")
        self.logger.info(f"Job ID: {self.job_id}")
        self.logger.info(f"Analysis Started: {datetime.now()}")
        
        # 1. Scan directory structure
        self._scan_directory()
        
        # 2. Load configuration
        self._load_configuration()
        
        # 3. Validate each step
        for step_name, step_info in self.workflow_steps.items():
            self._analyze_step(step_name, step_info)
        
        # 4. Generate comprehensive report
        report = self._generate_report()
        
        # 5. Save results
        self._save_results(report)
        
        # 6. Print summary
        self._print_summary(report)
        
        return report
    
    def _scan_directory(self):
        """Scan the output directory structure"""
        self.logger.info("\nScanning directory structure...")
        
        for item in self.job_output_dir.iterdir():
            if item.is_dir():
                self.scan_results[item.name] = self._scan_dir_contents(item)
            elif item.is_file():
                if 'root_files' not in self.scan_results:
                    self.scan_results['root_files'] = {}
                self.scan_results['root_files'][item.name] = {
                    'type': 'file',
                    'size': item.stat().st_size,
                    'modified': datetime.fromtimestamp(item.stat().st_mtime)
                }
    
    def _scan_dir_contents(self, directory: Path) -> Dict:
        """Scan directory contents with details"""
        contents = {
            'type': 'directory',
            'files': {},
            'subdirs': {},
            'total_size': 0,
            'file_count': 0
        }
        
        for item in directory.iterdir():
            if item.is_file():
                contents['files'][item.name] = {
                    'size': item.stat().st_size,
                    'type': item.suffix
                }
                contents['total_size'] += item.stat().st_size
                contents['file_count'] += 1
            elif item.is_dir():
                subdir_info = self._scan_dir_contents(item)
                contents['subdirs'][item.name] = subdir_info
                contents['total_size'] += subdir_info['total_size']
                contents['file_count'] += subdir_info['file_count']
        
        return contents
    
    def _load_configuration(self):
        """Load and parse configuration file"""
        self.logger.info("\nLoading configuration...")
        
        config_files = list(self.job_output_dir.glob("combined*.json"))
        if not config_files:
            self.issues.append("Configuration file (combined.json) not found")
            self.logger.error("No configuration file found!")
            return
        
        try:
            with open(config_files[0], 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            self.logger.info(f"Loaded configuration from: {config_files[0].name}")
        except Exception as e:
            self.issues.append(f"Failed to load configuration: {str(e)}")
            self.logger.error(f"Failed to load configuration: {str(e)}")
    
    def _analyze_step(self, step_name: str, step_info: Dict):
        """Analyze a single workflow step"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Analyzing: {step_name} - {step_info['description']}")
        self.logger.info(f"{'='*60}")
        
        analysis = {
            'step': step_name,
            'description': step_info['description'],
            'status': 'unknown',
            'inputs': {},
            'outputs': {},
            'issues': [],
            'metrics': {}
        }
        
        # Check if step is enabled in config
        enabled = self._check_step_enabled(step_name)
        analysis['enabled'] = enabled
        
        if not enabled and step_name != 'config':
            analysis['status'] = 'disabled'
            self.logger.info(f"Step is DISABLED in configuration")
        else:
            # Check inputs
            for input_name in step_info['inputs']:
                input_status = self._check_input(input_name)
                analysis['inputs'][input_name] = input_status
                if not input_status['available']:
                    analysis['issues'].append(f"Missing input: {input_name}")
            
            # Check outputs
            for output_name in step_info['outputs']:
                output_status = self._check_output(output_name)
                analysis['outputs'][output_name] = output_status
            
            # Run step-specific validation
            if 'validate' in step_info:
                validation_result = step_info['validate']()
                analysis['validation'] = validation_result
                if validation_result.get('issues'):
                    analysis['issues'].extend(validation_result['issues'])
                if validation_result.get('metrics'):
                    analysis['metrics'].update(validation_result['metrics'])
            
            # Determine overall status
            has_inputs = all(inp['available'] for inp in analysis['inputs'].values()) if analysis['inputs'] else True
            has_outputs = any(out['exists'] for out in analysis['outputs'].values())
            
            if has_outputs:
                analysis['status'] = 'complete'
            elif has_inputs:
                analysis['status'] = 'ready'
            else:
                analysis['status'] = 'blocked'
        
        self.validation_results[step_name] = analysis
        
        # Log status
        status_symbol = {
            'complete': '✅',
            'ready': '🟡',
            'blocked': '❌',
            'disabled': '⏸️',
            'unknown': '❓'
        }
        self.logger.info(f"Status: {status_symbol[analysis['status']]} {analysis['status'].upper()}")
        
        if analysis['issues']:
            for issue in analysis['issues']:
                self.logger.warning(f"  Issue: {issue}")
    
    def _check_step_enabled(self, step_name: str) -> bool:
        """Check if step is enabled in configuration"""
        if not self.config_data:
            return False
        
        main_config = self.config_data.get('main_config', {})
        
        if step_name == 'config':
            return True
        elif step_name == 'idf_creation':
            return main_config.get('idf_creation', {}).get('perform_idf_creation', False)
        elif step_name == 'simulation':
            return main_config.get('idf_creation', {}).get('run_simulations', False)
        elif step_name == 'parsing':
            return main_config.get('parsing', {}).get('perform_parsing', False)
        elif step_name == 'modification':
            return main_config.get('modification', {}).get('perform_modification', False)
        elif step_name == 'modified_simulation':
            return (main_config.get('modification', {}).get('perform_modification', False) and
                    main_config.get('modification', {}).get('run_modified_simulations', True))
        elif step_name == 'modified_parsing':
            return (main_config.get('modification', {}).get('perform_modification', False) and
                    main_config.get('parsing', {}).get('perform_parsing_modified_results', True))
        elif step_name == 'sensitivity':
            return main_config.get('sensitivity', {}).get('perform_sensitivity', False)
        elif step_name == 'surrogate':
            return main_config.get('surrogate', {}).get('perform_surrogate', False)
        elif step_name == 'validation':
            return main_config.get('validation', {}).get('perform_validation', False)
        
        return False
    
    def _check_input(self, input_name: str) -> Dict:
        """Check if an input is available"""
        if input_name == 'config':
            return {
                'available': self.config_data is not None,
                'type': 'configuration',
                'path': 'combined.json'
            }
        else:
            # Check if the output directory exists
            available = input_name in self.scan_results
            return {
                'available': available,
                'type': 'directory',
                'path': input_name if available else None
            }
    
    def _check_output(self, output_name: str) -> Dict:
        """Check if an output exists"""
        if output_name == 'combined.json':
            exists = 'root_files' in self.scan_results and any(
                'combined' in f for f in self.scan_results.get('root_files', {})
            )
            return {
                'exists': exists,
                'type': 'file',
                'path': output_name if exists else None
            }
        else:
            exists = output_name in self.scan_results
            info = {
                'exists': exists,
                'type': 'directory',
                'path': output_name if exists else None
            }
            
            if exists:
                dir_info = self.scan_results[output_name]
                info['file_count'] = dir_info.get('file_count', 0)
                info['total_size_mb'] = dir_info.get('total_size', 0) / (1024 * 1024)
            
            return info
    
    # Validation methods for each step
    def _validate_config(self) -> Dict:
        """Validate configuration file"""
        result = {'issues': [], 'metrics': {}}
        
        if self.config_data:
            main_config = self.config_data.get('main_config', {})
            result['metrics']['enabled_steps'] = sum([
                main_config.get('idf_creation', {}).get('perform_idf_creation', False),
                main_config.get('parsing', {}).get('perform_parsing', False),
                main_config.get('modification', {}).get('perform_modification', False),
                main_config.get('sensitivity', {}).get('perform_sensitivity', False),
                main_config.get('surrogate', {}).get('perform_surrogate', False),
                main_config.get('validation', {}).get('perform_validation', False)
            ])
        else:
            result['issues'].append("Configuration not loaded")
        
        return result
    
    def _validate_idf_creation(self) -> Dict:
        """Validate IDF creation outputs"""
        result = {'issues': [], 'metrics': {}}
        
        if 'output_IDFs' in self.scan_results:
            idf_dir = self.scan_results['output_IDFs']
            idf_files = [f for f in idf_dir.get('files', {}) if f.endswith('.idf')]
            
            result['metrics']['idf_count'] = len(idf_files)
            result['metrics']['has_tracker'] = 'idf_tracker.json' in idf_dir.get('files', {})
            
            if len(idf_files) == 0:
                result['issues'].append("No IDF files found in output_IDFs")
            
            self.logger.info(f"  Found {len(idf_files)} IDF files")
        
        return result
    
    def _validate_simulation(self) -> Dict:
        """Validate simulation results"""
        result = {'issues': [], 'metrics': {}}
        
        if 'Sim_Results' in self.scan_results:
            sim_dir = self.scan_results['Sim_Results']
            building_dirs = sim_dir.get('subdirs', {})
            
            result['metrics']['building_count'] = len(building_dirs)
            
            # Check each building directory
            complete_sims = 0
            failed_sims = []
            
            for building_id, building_info in building_dirs.items():
                files = building_info.get('files', {})
                
                # Check for required files
                has_sql = any(f.endswith('.sql') for f in files)
                has_err = any(f.endswith('.err') for f in files)
                
                if has_sql:
                    complete_sims += 1
                else:
                    failed_sims.append(building_id)
            
            result['metrics']['complete_simulations'] = complete_sims
            result['metrics']['failed_simulations'] = len(failed_sims)
            
            if failed_sims:
                result['issues'].append(f"Failed simulations: {failed_sims[:5]}...")
            
            self.logger.info(f"  Simulations: {complete_sims} complete, {len(failed_sims)} failed")
        
        return result
    
    def _validate_parsing(self) -> Dict:
        """Validate parsing outputs"""
        result = {'issues': [], 'metrics': {}}
        
        if 'parsed_data' in self.scan_results:
            parsed_dir = self.scan_results['parsed_data']
            
            # Check for expected subdirectories
            has_idf_data = 'idf_data' in parsed_dir.get('subdirs', {})
            has_output_data = 'output_data' in parsed_dir.get('subdirs', {})
            
            result['metrics']['has_idf_data'] = has_idf_data
            result['metrics']['has_output_data'] = has_output_data
            
            # Count parquet files
            parquet_count = 0
            for subdir in parsed_dir.get('subdirs', {}).values():
                parquet_count += sum(1 for f in subdir.get('files', {}) if f.endswith('.parquet'))
            
            result['metrics']['parquet_file_count'] = parquet_count
            
            if parquet_count == 0:
                result['issues'].append("No parquet files found in parsed_data")
            
            self.logger.info(f"  Found {parquet_count} parquet files")
        
        return result
    
    def _validate_modification(self) -> Dict:
        """Validate modification outputs"""
        result = {'issues': [], 'metrics': {}}
        
        if 'modified_idfs' in self.scan_results:
            mod_dir = self.scan_results['modified_idfs']
            
            # Count modified IDF files
            mod_idf_count = sum(1 for f in mod_dir.get('files', {}) if f.endswith('.idf'))
            result['metrics']['modified_idf_count'] = mod_idf_count
            
            # Check for tracking file
            has_summary = 'modification_summary.json' in mod_dir.get('files', {})
            result['metrics']['has_summary'] = has_summary
            
            if mod_idf_count == 0:
                result['issues'].append("No modified IDF files found")
            
            self.logger.info(f"  Found {mod_idf_count} modified IDF files")
        
        return result
    
    def _validate_modified_simulation(self) -> Dict:
        """Validate modified simulation results"""
        result = {'issues': [], 'metrics': {}}
        
        if 'Modified_Sim_Results' in self.scan_results:
            sim_dir = self.scan_results['Modified_Sim_Results']
            building_dirs = sim_dir.get('subdirs', {})
            
            result['metrics']['modified_building_count'] = len(building_dirs)
            
            # Similar validation as regular simulation
            complete_sims = sum(
                1 for b_info in building_dirs.values()
                if any(f.endswith('.sql') for f in b_info.get('files', {}))
            )
            
            result['metrics']['complete_modified_simulations'] = complete_sims
            
            self.logger.info(f"  Modified simulations: {complete_sims} complete")
        
        return result
    
    def _validate_modified_parsing(self) -> Dict:
        """Validate modified parsing outputs"""
        result = {'issues': [], 'metrics': {}}
        
        if 'parsed_modified_results' in self.scan_results:
            parsed_dir = self.scan_results['parsed_modified_results']
            
            # Count parquet files
            parquet_count = sum(1 for f in parsed_dir.get('files', {}) if f.endswith('.parquet'))
            for subdir in parsed_dir.get('subdirs', {}).values():
                parquet_count += sum(1 for f in subdir.get('files', {}) if f.endswith('.parquet'))
            
            result['metrics']['modified_parquet_count'] = parquet_count
            
            if parquet_count == 0:
                result['issues'].append("No parquet files found in parsed_modified_results")
            
            self.logger.info(f"  Found {parquet_count} modified parquet files")
        
        return result
    
    def _validate_sensitivity(self) -> Dict:
        """Validate sensitivity analysis outputs"""
        result = {'issues': [], 'metrics': {}}
        
        if 'sensitivity_results' in self.scan_results:
            sens_dir = self.scan_results['sensitivity_results']
            files = sens_dir.get('files', {})
            
            # Check for key files
            has_rankings = 'sensitivity_rankings.parquet' in files
            has_metrics = 'sensitivity_metrics.json' in files
            
            result['metrics']['has_rankings'] = has_rankings
            result['metrics']['has_metrics'] = has_metrics
            
            if not has_rankings:
                result['issues'].append("Missing sensitivity_rankings.parquet")
            
            self.logger.info(f"  Rankings: {'✓' if has_rankings else '✗'}, Metrics: {'✓' if has_metrics else '✗'}")
        
        return result
    
    def _validate_surrogate(self) -> Dict:
        """Validate surrogate modeling outputs"""
        result = {'issues': [], 'metrics': {}}
        
        if 'surrogate_models' in self.scan_results:
            sur_dir = self.scan_results['surrogate_models']
            
            # Check for version directories
            version_dirs = sur_dir.get('subdirs', {})
            result['metrics']['model_versions'] = len(version_dirs)
            
            # Check latest version
            if version_dirs:
                latest_version = sorted(version_dirs.keys())[-1]
                latest_files = version_dirs[latest_version].get('files', {})
                
                has_model = any(f.endswith('.pkl') for f in latest_files)
                has_config = 'config.json' in latest_files
                has_metrics = 'performance_metrics.json' in latest_files
                
                result['metrics']['latest_version'] = latest_version
                result['metrics']['has_model'] = has_model
                result['metrics']['has_config'] = has_config
                result['metrics']['has_performance'] = has_metrics
                
                if not has_model:
                    result['issues'].append("No model file (.pkl) found")
            
            self.logger.info(f"  Found {len(version_dirs)} model versions")
        
        return result
    
    def _validate_validation(self) -> Dict:
        """Validate validation outputs"""
        result = {'issues': [], 'metrics': {}}
        
        if 'validation_results' in self.scan_results:
            val_dir = self.scan_results['validation_results']
            files = val_dir.get('files', {})
            
            has_summary = 'validation_summary.json' in files
            result['metrics']['has_summary'] = has_summary
            
            # Count validation result files
            result_files = sum(1 for f in files if f.endswith('.parquet'))
            result['metrics']['result_file_count'] = result_files
            
            self.logger.info(f"  Validation files: {result_files}")
        
        return result
    
    def _generate_report(self) -> Dict:
        """Generate comprehensive analysis report"""
        report = {
            'metadata': {
                'job_id': self.job_id,
                'job_directory': str(self.job_output_dir),
                'analysis_timestamp': datetime.now().isoformat(),
                'analyzer_version': '1.0'
            },
            'summary': self._generate_summary(),
            'workflow_state': self.validation_results,
            'recommendations': self._generate_recommendations(),
            'data_flow': self._analyze_data_flow()
        }
        
        return report
    
    def _generate_summary(self) -> Dict:
        """Generate executive summary"""
        total_steps = len(self.workflow_steps)
        
        # Count by status
        status_counts = defaultdict(int)
        for result in self.validation_results.values():
            status_counts[result['status']] += 1
        
        # Identify critical paths
        ready_steps = [k for k, v in self.validation_results.items() if v['status'] == 'ready']
        blocked_steps = [k for k, v in self.validation_results.items() if v['status'] == 'blocked']
        
        # Calculate progress
        complete_steps = status_counts.get('complete', 0)
        progress = (complete_steps / total_steps) * 100 if total_steps > 0 else 0
        
        return {
            'total_steps': total_steps,
            'steps_by_status': dict(status_counts),
            'progress_percentage': round(progress, 1),
            'ready_to_run': ready_steps,
            'blocked_steps': blocked_steps,
            'total_issues': sum(len(v.get('issues', [])) for v in self.validation_results.values())
        }
    
    def _generate_recommendations(self) -> List[Dict]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Check for ready steps
        for step_name, result in self.validation_results.items():
            if result['status'] == 'ready':
                step_info = self.workflow_steps[step_name]
                recommendations.append({
                    'priority': 'high',
                    'step': step_name,
                    'action': f"Run {step_name}",
                    'reason': f"{step_info['description']} - All inputs are available"
                })
        
        # Check for blocked steps
        for step_name, result in self.validation_results.items():
            if result['status'] == 'blocked':
                missing_inputs = [k for k, v in result['inputs'].items() if not v['available']]
                recommendations.append({
                    'priority': 'high',
                    'step': step_name,
                    'action': f"Generate missing inputs: {', '.join(missing_inputs)}",
                    'reason': f"{step_name} is blocked and cannot proceed"
                })
        
        # Check for disabled steps that might be needed
        for step_name, result in self.validation_results.items():
            if result['status'] == 'disabled' and step_name != 'config':
                # Check if any later steps need this
                dependents = [k for k, v in self.workflow_steps.items() 
                             if step_name in v['inputs']]
                if dependents:
                    enabled_dependents = [d for d in dependents 
                                        if self.validation_results[d].get('enabled', False)]
                    if enabled_dependents:
                        recommendations.append({
                            'priority': 'medium',
                            'step': step_name,
                            'action': f"Consider enabling {step_name}",
                            'reason': f"Required by: {', '.join(enabled_dependents)}"
                        })
        
        return recommendations
    
    def _analyze_data_flow(self) -> Dict:
        """Analyze data flow between steps"""
        flow = {}
        
        for step_name, result in self.validation_results.items():
            if result['status'] == 'complete':
                outputs = result.get('outputs', {})
                
                # Find which steps use these outputs
                consumers = []
                for other_step, other_info in self.workflow_steps.items():
                    for output_name in outputs:
                        if output_name in other_info['inputs']:
                            consumers.append(other_step)
                
                flow[step_name] = {
                    'produces': list(outputs.keys()),
                    'consumed_by': consumers,
                    'data_size_mb': sum(
                        out.get('total_size_mb', 0) 
                        for out in outputs.values()
                    )
                }
        
        return flow
    
    def _save_results(self, report: Dict):
        """Save analysis results"""
        # Save JSON report
        json_file = self.job_output_dir / "workflow_analysis_report.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save human-readable report
        text_file = self.job_output_dir / "workflow_analysis_summary.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(self._format_text_report(report))
        
        self.logger.info(f"\nReports saved:")
        self.logger.info(f"  - {json_file}")
        self.logger.info(f"  - {text_file}")
    
    def _format_text_report(self, report: Dict) -> str:
        """Format report as human-readable text"""
        lines = []
        lines.append("E+ WORKFLOW ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"Job ID: {report['metadata']['job_id']}")
        lines.append(f"Generated: {report['metadata']['analysis_timestamp']}")
        lines.append("")
        
        # Summary
        summary = report['summary']
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Progress: {summary['progress_percentage']}%")
        lines.append(f"Total steps: {summary['total_steps']}")
        
        status_symbols = {'complete': '✅', 'ready': '🟡', 'blocked': '❌', 'disabled': '⏸️'}
        for status, count in summary['steps_by_status'].items():
            lines.append(f"  {status_symbols.get(status, '?')} {status}: {count}")
        
        lines.append(f"Total issues: {summary['total_issues']}")
        lines.append("")
        
        # Workflow state
        lines.append("WORKFLOW STATE")
        lines.append("-" * 40)
        
        for step_name, state in report['workflow_state'].items():
            symbol = status_symbols.get(state['status'], '?')
            lines.append(f"\n{symbol} {step_name.upper()}: {state['status']}")
            lines.append(f"   {state['description']}")
            
            if state['issues']:
                lines.append("   Issues:")
                for issue in state['issues']:
                    lines.append(f"     - {issue}")
            
            if state.get('metrics'):
                lines.append("   Metrics:")
                for key, value in state['metrics'].items():
                    lines.append(f"     - {key}: {value}")
        
        lines.append("")
        
        # Recommendations
        if report['recommendations']:
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 40)
            
            high_priority = [r for r in report['recommendations'] if r['priority'] == 'high']
            medium_priority = [r for r in report['recommendations'] if r['priority'] == 'medium']
            
            if high_priority:
                lines.append("\nHigh Priority:")
                for rec in high_priority:
                    lines.append(f"  → {rec['action']}")
                    lines.append(f"    Reason: {rec['reason']}")
            
            if medium_priority:
                lines.append("\nMedium Priority:")
                for rec in medium_priority:
                    lines.append(f"  → {rec['action']}")
                    lines.append(f"    Reason: {rec['reason']}")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("For detailed analysis, see: workflow_analysis_report.json")
        
        return "\n".join(lines)
    
    def _print_summary(self, report: Dict):
        """Print summary to console"""
        print("\n" + "=" * 80)
        print("WORKFLOW ANALYSIS COMPLETE")
        print("=" * 80)
        
        summary = report['summary']
        print(f"\nProgress: {summary['progress_percentage']}% complete")
        
        if summary['ready_to_run']:
            print(f"\n✅ Ready to run: {', '.join(summary['ready_to_run'])}")
        
        if summary['blocked_steps']:
            print(f"\n❌ Blocked: {', '.join(summary['blocked_steps'])}")
        
        if summary['total_issues'] > 0:
            print(f"\n⚠️  {summary['total_issues']} issues found - check report for details")
        
        print(f"\nReports saved to: {self.job_output_dir}")


def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("E+ Unified Workflow Analyzer")
        print("=" * 40)
        print("\nUsage: python workflow_analyzer.py <job_output_directory>")
        print("\nThis tool will:")
        print("  1. Scan your output directory")
        print("  2. Check workflow dependencies")
        print("  3. Validate inputs/outputs for each step")
        print("  4. Provide actionable recommendations")
        print("\nExample:")
        print("  python workflow_analyzer.py output/6f912613-913d-40ea-ba14-eff7e6dc097f")
        sys.exit(1)
    
    job_output_dir = sys.argv[1]
    
    # Validate directory exists
    if not os.path.exists(job_output_dir):
        print(f"Error: Directory not found: {job_output_dir}")
        sys.exit(1)
    
    # Run analysis
    analyzer = UnifiedWorkflowAnalyzer(job_output_dir)
    report = analyzer.run_analysis()
    
    print("\nAnalysis complete! Check the generated reports for details.")


if __name__ == "__main__":
    main()
