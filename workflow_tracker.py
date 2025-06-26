"""
E+ Workflow Dependency Tracker and Validator

This script analyzes the E+ workflow, tracks dependencies between steps,
and validates that inputs are properly generated and ready to use.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set, Any
import pandas as pd
import glob

class WorkflowStep:
    """Represents a single step in the workflow"""
    def __init__(self, name: str, enabled_flag: str, config_section: str):
        self.name = name
        self.enabled_flag = enabled_flag
        self.config_section = config_section
        self.inputs = []
        self.outputs = []
        self.dependencies = []
        self.validation_rules = []

class WorkflowTracker:
    """Tracks and validates the E+ workflow execution"""
    
    def __init__(self, job_output_dir: str):
        self.job_output_dir = Path(job_output_dir)
        self.job_id = self.job_output_dir.name
        self.base_dir = self.job_output_dir.parent.parent
        
        # Setup logging
        self.setup_logging()
        
        # Define workflow steps with their dependencies
        self.workflow_steps = self._define_workflow_steps()
        
        # Track execution status
        self.execution_status = {}
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.job_output_dir / "workflow_tracker.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _define_workflow_steps(self) -> Dict[str, WorkflowStep]:
        """Define all workflow steps and their dependencies"""
        steps = {}
        
        # 1. IDF Creation Step
        idf_step = WorkflowStep(
            name="IDF Creation",
            enabled_flag="perform_idf_creation",
            config_section="idf_creation"
        )
        idf_step.inputs = [
            ("config", "user_configs_folder"),
            ("data", "idf_templates"),
            ("data", "weather_files")
        ]
        idf_step.outputs = [
            ("output_IDFs", "*.idf"),
            ("idf_tracker.json", None)
        ]
        steps["idf_creation"] = idf_step
        
        # 2. Simulation Step
        sim_step = WorkflowStep(
            name="Simulation",
            enabled_flag="run_simulations",
            config_section="idf_creation"
        )
        sim_step.inputs = [
            ("output_IDFs", "*.idf"),
            ("weather", "*.epw")
        ]
        sim_step.outputs = [
            ("Sim_Results", "*.sql"),
            ("Sim_Results", "*.htm"),
            ("Sim_Results", "*.csv")
        ]
        sim_step.dependencies = ["idf_creation"]
        steps["simulation"] = sim_step
        
        # 3. Parsing Step
        parse_step = WorkflowStep(
            name="Parsing",
            enabled_flag="perform_parsing",
            config_section="parsing"
        )
        parse_step.inputs = [
            ("Sim_Results", "*.sql"),
            ("output_IDFs", "*.idf")
        ]
        parse_step.outputs = [
            ("parsed_data", "*.parquet"),
            ("parsed_data/idf_data", "*.parquet"),
            ("parsed_data/output_data", "*.parquet")
        ]
        parse_step.dependencies = ["simulation"]
        steps["parsing"] = parse_step
        
        # 4. Modification Step
        mod_step = WorkflowStep(
            name="Modification",
            enabled_flag="perform_modification",
            config_section="modification"
        )
        mod_step.inputs = [
            ("output_IDFs", "*.idf"),
            ("parsed_data", "*.parquet")
        ]
        mod_step.outputs = [
            ("modified_idfs", "*.idf"),
            ("modified_idfs/modification_summary.json", None),
            ("modified_idfs/*/modification_report.json", None)
        ]
        mod_step.dependencies = ["parsing"]
        steps["modification"] = mod_step
        
        # 5. Modified Simulation Step
        mod_sim_step = WorkflowStep(
            name="Modified Simulation",
            enabled_flag="run_modified_simulations",
            config_section="modification.post_modification"
        )
        mod_sim_step.inputs = [
            ("modified_idfs", "*.idf")
        ]
        mod_sim_step.outputs = [
            ("Modified_Sim_Results", "*.sql"),
            ("Modified_Sim_Results", "*.csv")
        ]
        mod_sim_step.dependencies = ["modification"]
        steps["modified_simulation"] = mod_sim_step
        
        # 6. Modified Parsing Step
        mod_parse_step = WorkflowStep(
            name="Modified Parsing",
            enabled_flag="parse_modified_results",
            config_section="modification.post_modification"
        )
        mod_parse_step.inputs = [
            ("Modified_Sim_Results", "*.sql"),
            ("modified_idfs", "*.idf")
        ]
        mod_parse_step.outputs = [
            ("parsed_modified_results", "*.parquet")
        ]
        mod_parse_step.dependencies = ["modified_simulation"]
        steps["modified_parsing"] = mod_parse_step
        
        # 7. Validation Step
        val_step = WorkflowStep(
            name="Validation",
            enabled_flag="perform_validation",
            config_section="validation"
        )
        val_step.inputs = [
            ("parsed_data", "*.parquet"),
            ("parsed_modified_results", "*.parquet"),
            ("measured_data.csv", None)
        ]
        val_step.outputs = [
            ("validation_results", "*.json"),
            ("validation_results", "*.html")
        ]
        val_step.dependencies = ["parsing", "modified_parsing"]
        steps["validation"] = val_step
        
        # 8. Sensitivity Analysis Step
        sens_step = WorkflowStep(
            name="Sensitivity Analysis",
            enabled_flag="perform_sensitivity",
            config_section="sensitivity"
        )
        sens_step.inputs = [
            ("parsed_data", "*.parquet"),
            ("parsed_modified_results", "*.parquet")
        ]
        sens_step.outputs = [
            ("sensitivity_results", "*.parquet"),
            ("sensitivity_results", "*.json"),
            ("sensitivity_results", "*.html")
        ]
        sens_step.dependencies = ["parsing", "modified_parsing"]
        steps["sensitivity"] = sens_step
        
        # 9. Surrogate Modeling Step
        surr_step = WorkflowStep(
            name="Surrogate Modeling",
            enabled_flag="perform_surrogate",
            config_section="surrogate"
        )
        surr_step.inputs = [
            ("parsed_data", "*.parquet"),
            ("parsed_modified_results", "*.parquet"),
            ("sensitivity_results", "*.parquet")
        ]
        surr_step.outputs = [
            ("surrogate_models", "*.pkl"),
            ("surrogate_models", "*.json"),
            ("surrogate_models/validation_report.json", None)
        ]
        surr_step.dependencies = ["sensitivity"]
        steps["surrogate"] = surr_step
        
        # 10. Calibration Step
        cal_step = WorkflowStep(
            name="Calibration",
            enabled_flag="perform_calibration",
            config_section="calibration"
        )
        cal_step.inputs = [
            ("surrogate_models", "*.pkl"),
            ("validation_results", "*.json")
        ]
        cal_step.outputs = [
            ("calibration_results", "*.json"),
            ("calibration_results", "*.parquet")
        ]
        cal_step.dependencies = ["surrogate", "validation"]
        steps["calibration"] = cal_step
        
        return steps
    
    def check_file_exists(self, relative_path: str, pattern: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Check if file(s) exist in the job output directory"""
        full_path = self.job_output_dir / relative_path
        
        if pattern:
            # Check for pattern match
            search_path = full_path / pattern if full_path.is_dir() else full_path.parent / pattern
            matches = glob.glob(str(search_path))
            return len(matches) > 0, matches
        else:
            # Check for specific file
            return full_path.exists(), [str(full_path)] if full_path.exists() else []
    
    def validate_step_inputs(self, step: WorkflowStep) -> Dict[str, bool]:
        """Validate all inputs for a workflow step"""
        input_status = {}
        
        for input_path, pattern in step.inputs:
            exists, files = self.check_file_exists(input_path, pattern)
            input_key = f"{input_path}/{pattern}" if pattern else input_path
            input_status[input_key] = {
                "exists": exists,
                "files": files,
                "count": len(files)
            }
            
        return input_status
    
    def validate_step_outputs(self, step: WorkflowStep) -> Dict[str, bool]:
        """Validate all outputs for a workflow step"""
        output_status = {}
        
        for output_path, pattern in step.outputs:
            exists, files = self.check_file_exists(output_path, pattern)
            output_key = f"{output_path}/{pattern}" if pattern else output_path
            output_status[output_key] = {
                "exists": exists,
                "files": files,
                "count": len(files)
            }
            
        return output_status
    
    def check_dependencies_met(self, step_name: str) -> Tuple[bool, List[str]]:
        """Check if all dependencies for a step are met"""
        step = self.workflow_steps.get(step_name)
        if not step:
            return False, [f"Step {step_name} not found"]
        
        missing_deps = []
        for dep in step.dependencies:
            dep_step = self.workflow_steps.get(dep)
            if dep_step:
                # Check if dependency step has completed (all outputs exist)
                output_status = self.validate_step_outputs(dep_step)
                for output, status in output_status.items():
                    if not status["exists"]:
                        missing_deps.append(f"{dep}: {output}")
        
        return len(missing_deps) == 0, missing_deps
    
    def analyze_workflow(self) -> Dict[str, Any]:
        """Analyze the entire workflow and return comprehensive status"""
        analysis = {
            "job_id": self.job_id,
            "job_output_dir": str(self.job_output_dir),
            "timestamp": datetime.now().isoformat(),
            "steps": {}
        }
        
        # Check configuration file
        config_files = list(self.job_output_dir.glob("combined*.json"))
        if config_files:
            with open(config_files[0], 'r', encoding='utf-8') as f:
                config = json.load(f)
                main_config = config.get("main_config", {})
        else:
            main_config = {}
            self.logger.warning("No configuration file found")
        
        # Analyze each step
        for step_name, step in self.workflow_steps.items():
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Analyzing step: {step.name}")
            self.logger.info(f"{'='*60}")
            
            # Check if step is enabled
            config_section = main_config
            for section in step.config_section.split('.'):
                config_section = config_section.get(section, {})
            
            enabled = config_section.get(step.enabled_flag, False)
            
            # Check dependencies
            deps_met, missing_deps = self.check_dependencies_met(step_name)
            
            # Validate inputs and outputs
            input_status = self.validate_step_inputs(step)
            output_status = self.validate_step_outputs(step)
            
            # Determine step status
            inputs_ready = all(status["exists"] for status in input_status.values())
            outputs_ready = all(status["exists"] for status in output_status.values())
            
            if not enabled:
                status = "DISABLED"
            elif not deps_met:
                status = "BLOCKED"
            elif not inputs_ready:
                status = "MISSING_INPUTS"
            elif outputs_ready:
                status = "COMPLETED"
            else:
                status = "READY"
            
            step_analysis = {
                "name": step.name,
                "enabled": enabled,
                "status": status,
                "dependencies_met": deps_met,
                "missing_dependencies": missing_deps,
                "inputs": input_status,
                "outputs": output_status,
                "input_summary": {
                    "total": len(input_status),
                    "ready": sum(1 for s in input_status.values() if s["exists"]),
                    "missing": sum(1 for s in input_status.values() if not s["exists"])
                },
                "output_summary": {
                    "total": len(output_status),
                    "ready": sum(1 for s in output_status.values() if s["exists"]),
                    "missing": sum(1 for s in output_status.values() if not s["exists"])
                }
            }
            
            analysis["steps"][step_name] = step_analysis
            
            # Log summary
            self.logger.info(f"Status: {status}")
            self.logger.info(f"Enabled: {enabled}")
            self.logger.info(f"Dependencies met: {deps_met}")
            self.logger.info(f"Inputs ready: {step_analysis['input_summary']['ready']}/{step_analysis['input_summary']['total']}")
            self.logger.info(f"Outputs ready: {step_analysis['output_summary']['ready']}/{step_analysis['output_summary']['total']}")
            
            if missing_deps:
                self.logger.warning(f"Missing dependencies: {missing_deps}")
            
            # Log missing inputs
            for input_name, status in input_status.items():
                if not status["exists"]:
                    self.logger.warning(f"Missing input: {input_name}")
            
            # Log generated outputs
            for output_name, status in output_status.items():
                if status["exists"]:
                    self.logger.info(f"Generated output: {output_name} ({status['count']} files)")
        
        return analysis
    
    def generate_workflow_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a detailed HTML report of the workflow status"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>E+ Workflow Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                .metadata {{ background: #f0f0f0; padding: 10px; border-radius: 5px; margin-bottom: 20px; }}
                .step {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                .status-COMPLETED {{ background: #d4f4dd; }}
                .status-READY {{ background: #fff3cd; }}
                .status-BLOCKED {{ background: #f8d7da; }}
                .status-DISABLED {{ background: #e7e7e7; }}
                .status-MISSING_INPUTS {{ background: #ffeaa7; }}
                .summary {{ display: flex; gap: 20px; margin: 10px 0; }}
                .summary-box {{ padding: 10px; background: #f9f9f9; border-radius: 3px; }}
                .file-list {{ font-size: 0.9em; color: #666; margin-left: 20px; }}
                .missing {{ color: #d32f2f; }}
                .exists {{ color: #388e3c; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #f2f2f2; }}
                .dependency-graph {{ margin: 20px 0; padding: 20px; background: #fafafa; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>E+ Workflow Analysis Report</h1>
            
            <div class="metadata">
                <strong>Job ID:</strong> {analysis['job_id']}<br>
                <strong>Output Directory:</strong> {analysis['job_output_dir']}<br>
                <strong>Analysis Time:</strong> {analysis['timestamp']}
            </div>
            
            <h2>Workflow Summary</h2>
            <table>
                <tr>
                    <th>Step</th>
                    <th>Status</th>
                    <th>Enabled</th>
                    <th>Dependencies Met</th>
                    <th>Inputs Ready</th>
                    <th>Outputs Generated</th>
                </tr>
        """
        
        for step_name, step_data in analysis['steps'].items():
            html += f"""
                <tr class="status-{step_data['status']}">
                    <td>{step_data['name']}</td>
                    <td><strong>{step_data['status']}</strong></td>
                    <td>{'✓' if step_data['enabled'] else '✗'}</td>
                    <td>{'✓' if step_data['dependencies_met'] else '✗'}</td>
                    <td>{step_data['input_summary']['ready']}/{step_data['input_summary']['total']}</td>
                    <td>{step_data['output_summary']['ready']}/{step_data['output_summary']['total']}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <h2>Detailed Step Analysis</h2>
        """
        
        for step_name, step_data in analysis['steps'].items():
            html += f"""
            <div class="step status-{step_data['status']}">
                <h3>{step_data['name']}</h3>
                <div class="summary">
                    <div class="summary-box">
                        <strong>Status:</strong> {step_data['status']}
                    </div>
                    <div class="summary-box">
                        <strong>Enabled:</strong> {'Yes' if step_data['enabled'] else 'No'}
                    </div>
                    <div class="summary-box">
                        <strong>Dependencies:</strong> {'Met' if step_data['dependencies_met'] else 'Not Met'}
                    </div>
                </div>
            """
            
            if step_data['missing_dependencies']:
                html += f"""
                <div class="missing">
                    <strong>Missing Dependencies:</strong>
                    <ul>
                        {''.join(f'<li>{dep}</li>' for dep in step_data['missing_dependencies'])}
                    </ul>
                </div>
                """
            
            # Inputs section
            html += "<h4>Inputs:</h4><ul>"
            for input_name, status in step_data['inputs'].items():
                class_name = "exists" if status['exists'] else "missing"
                html += f"""
                <li class="{class_name}">
                    {input_name}: {'✓' if status['exists'] else '✗'} ({status['count']} files)
                """
                if status['exists'] and status['count'] <= 5:
                    html += "<div class='file-list'>"
                    for file in status['files']:
                        html += f"{os.path.basename(file)}<br>"
                    html += "</div>"
                html += "</li>"
            html += "</ul>"
            
            # Outputs section
            html += "<h4>Outputs:</h4><ul>"
            for output_name, status in step_data['outputs'].items():
                class_name = "exists" if status['exists'] else "missing"
                html += f"""
                <li class="{class_name}">
                    {output_name}: {'✓' if status['exists'] else '✗'} ({status['count']} files)
                """
                if status['exists'] and status['count'] <= 5:
                    html += "<div class='file-list'>"
                    for file in status['files']:
                        html += f"{os.path.basename(file)}<br>"
                    html += "</div>"
                html += "</li>"
            html += "</ul>"
            
            html += "</div>"
        
        html += """
            <h2>Workflow Dependency Graph</h2>
            <div class="dependency-graph">
                <pre>
IDF Creation
    ↓
Simulation
    ↓
Parsing ─────────────┐
    ↓                 ↓
Modification     Validation
    ↓                 ↓
Modified Simulation   ↓
    ↓                 ↓
Modified Parsing ─────┤
    ↓                 ↓
Sensitivity Analysis  ↓
    ↓                 ↓
Surrogate Modeling ───┤
    ↓                 ↓
Calibration ←─────────┘
                </pre>
            </div>
            
        </body>
        </html>
        """
        
        return html
    
    def validate_data_quality(self) -> Dict[str, Any]:
        """Validate the quality of data at each step"""
        quality_report = {
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # Check parsed data quality
        parsed_data_dir = self.job_output_dir / "parsed_data"
        if parsed_data_dir.exists():
            quality_report["checks"]["parsed_data"] = self._check_parquet_files(parsed_data_dir)
        
        # Check modified results quality
        modified_data_dir = self.job_output_dir / "parsed_modified_results"
        if modified_data_dir.exists():
            quality_report["checks"]["modified_data"] = self._check_parquet_files(modified_data_dir)
        
        # Check sensitivity results
        sens_dir = self.job_output_dir / "sensitivity_results"
        if sens_dir.exists():
            sens_files = list(sens_dir.glob("*.parquet"))
            if sens_files:
                quality_report["checks"]["sensitivity"] = {
                    "file_count": len(sens_files),
                    "files": [f.name for f in sens_files]
                }
        
        return quality_report
    
    def _check_parquet_files(self, directory: Path) -> Dict[str, Any]:
        """Check quality of parquet files in a directory"""
        report = {
            "total_files": 0,
            "total_rows": 0,
            "files": {}
        }
        
        for parquet_file in directory.rglob("*.parquet"):
            try:
                df = pd.read_parquet(parquet_file)
                report["files"][str(parquet_file.relative_to(directory))] = {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "missing_values": df.isnull().sum().to_dict()
                }
                report["total_files"] += 1
                report["total_rows"] += len(df)
            except Exception as e:
                report["files"][str(parquet_file.relative_to(directory))] = {
                    "error": str(e)
                }
        
        return report
    
    def run_full_analysis(self):
        """Run complete workflow analysis and generate reports"""
        self.logger.info("="*80)
        self.logger.info("E+ WORKFLOW DEPENDENCY TRACKER AND VALIDATOR")
        self.logger.info("="*80)
        
        # Run workflow analysis
        analysis = self.analyze_workflow()
        
        # Save analysis as JSON
        analysis_file = self.job_output_dir / "workflow_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        self.logger.info(f"\nSaved analysis to: {analysis_file}")
        
        # Generate HTML report
        html_report = self.generate_workflow_report(analysis)
        report_file = self.job_output_dir / "workflow_analysis_report.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_report)
        self.logger.info(f"Generated HTML report: {report_file}")
        
        # Run data quality checks
        quality_report = self.validate_data_quality()
        quality_file = self.job_output_dir / "data_quality_report.json"
        with open(quality_file, 'w', encoding='utf-8') as f:
            json.dump(quality_report, f, indent=2)
        self.logger.info(f"Generated data quality report: {quality_file}")
        
        # Print summary
        self.logger.info("\n" + "="*80)
        self.logger.info("WORKFLOW SUMMARY")
        self.logger.info("="*80)
        
        status_counts = {}
        for step_data in analysis['steps'].values():
            status = step_data['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            self.logger.info(f"{status}: {count} steps")
        
        # Identify next actionable steps
        self.logger.info("\n" + "="*80)
        self.logger.info("NEXT ACTIONABLE STEPS")
        self.logger.info("="*80)
        
        for step_name, step_data in analysis['steps'].items():
            if step_data['status'] == 'READY':
                self.logger.info(f"- {step_data['name']} is ready to run")
            elif step_data['status'] == 'MISSING_INPUTS':
                self.logger.info(f"- {step_data['name']} is missing inputs:")
                for input_name, status in step_data['inputs'].items():
                    if not status['exists']:
                        self.logger.info(f"  * {input_name}")


def main():
    """Main entry point for the workflow tracker"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python workflow_tracker.py <job_output_directory>")
        print("\nExample paths from your last run:")
        print("  D:\\Documents\\daily\\E_Plus_2040_py\\output\\6f912613-913d-40ea-ba14-eff7e6dc097f")
        sys.exit(1)
    
    job_output_dir = sys.argv[1]
    
    if not os.path.exists(job_output_dir):
        print(f"Error: Directory not found: {job_output_dir}")
        sys.exit(1)
    
    # Create and run tracker
    tracker = WorkflowTracker(job_output_dir)
    tracker.run_full_analysis()
    
    print(f"\nAnalysis complete! Check the following files in {job_output_dir}:")
    print("  - workflow_analysis.json: Detailed analysis data")
    print("  - workflow_analysis_report.html: Visual HTML report")
    print("  - data_quality_report.json: Data quality checks")
    print("  - workflow_tracker.log: Detailed execution log")


if __name__ == "__main__":
    main()