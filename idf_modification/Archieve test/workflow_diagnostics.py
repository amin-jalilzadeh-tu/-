"""
Workflow Diagnostics Tool
Identifies issues in the EnergyPlus modification and simulation workflow
"""

import os
import sys
import json
import logging
from pathlib import Path
import pandas as pd
import traceback
from datetime import datetime
import subprocess

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowDiagnostics:
    """Diagnose issues in the EnergyPlus workflow"""
    
    def __init__(self, job_id: str, base_output_dir: str = None):
        """Initialize diagnostics"""
        self.job_id = job_id
        self.issues = []
        self.warnings = []
        self.info = []
        
        # Set up paths
        if base_output_dir:
            self.base_output_dir = Path(base_output_dir)
        else:
            env_output_dir = os.environ.get("OUTPUT_DIR")
            if env_output_dir:
                self.base_output_dir = Path(env_output_dir)
            else:
                self.base_output_dir = Path(r"D:\Documents\daily\E_Plus_2040_py\output")
        
        self.job_output_dir = self.base_output_dir / job_id
        
        logger.info(f"Running diagnostics for job: {job_id}")
        
    def run_full_diagnostics(self):
        """Run all diagnostic checks"""
        logger.info("="*60)
        logger.info("WORKFLOW DIAGNOSTICS")
        logger.info("="*60)
        
        # Check basic structure
        self.check_directory_structure()
        
        # Check configuration
        self.check_configuration()
        
        # Check IDF files
        self.check_idf_files()
        
        # Check modification outputs
        self.check_modification_outputs()
        
        # Check simulation prerequisites
        self.check_simulation_prerequisites()
        
        # Check EnergyPlus installation
        self.check_energyplus_installation()
        
        # Check file permissions
        self.check_file_permissions()
        
        # Generate report
        self.generate_diagnostic_report()
        
    def check_directory_structure(self):
        """Check if all expected directories exist"""
        logger.info("\n1. Checking directory structure...")
        
        expected_dirs = {
            'job_output': self.job_output_dir,
            'output_IDFs': self.job_output_dir / 'output_IDFs',
            'modified_idfs': self.job_output_dir / 'modified_idfs',
            'Sim_Results': self.job_output_dir / 'Sim_Results',
            'Modified_Sim_Results': self.job_output_dir / 'Modified_Sim_Results',
            'parsed_data': self.job_output_dir / 'parsed_data'
        }
        
        for name, path in expected_dirs.items():
            if path.exists():
                count = len(list(path.glob('**/*'))) if path.is_dir() else 0
                self.info.append(f"✓ {name}: exists ({count} files)")
            else:
                self.warnings.append(f"✗ {name}: missing ({path})")
    
    def check_configuration(self):
        """Check configuration files"""
        logger.info("\n2. Checking configuration...")
        
        # Check for config files
        config_locations = [
            Path("user_configs") / self.job_id / "combined.json",
            Path("user_configs") / self.job_id / "main_config.json",
            self.job_output_dir / "combined.json",
            self.job_output_dir / "main_config.json"
        ]
        
        config_found = False
        for config_path in config_locations:
            if config_path.exists():
                config_found = True
                self.info.append(f"✓ Config found: {config_path}")
                
                # Load and check config
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    # Check key sections
                    if 'main_config' in config:
                        main_config = config['main_config']
                    else:
                        main_config = config
                    
                    # Check modification settings
                    mod_cfg = main_config.get('modification', {})
                    if mod_cfg.get('perform_modification', False):
                        self.info.append("✓ Modification enabled")
                        
                        post_mod = mod_cfg.get('post_modification', {})
                        if post_mod.get('run_simulations', False):
                            self.info.append("✓ Post-modification simulations enabled")
                        else:
                            self.warnings.append("⚠ Post-modification simulations disabled")
                    
                    # Check IDF creation settings
                    idf_cfg = main_config.get('idf_creation', {})
                    if 'iddfile' in idf_cfg:
                        idd_path = Path(idf_cfg['iddfile'])
                        if idd_path.exists():
                            self.info.append(f"✓ IDD file configured: {idd_path}")
                        else:
                            self.issues.append(f"✗ IDD file not found: {idd_path}")
                    else:
                        self.issues.append("✗ IDD file not configured")
                        
                except Exception as e:
                    self.issues.append(f"✗ Error reading config: {e}")
        
        if not config_found:
            self.issues.append("✗ No configuration file found")
    
    def check_idf_files(self):
        """Check IDF files in various directories"""
        logger.info("\n3. Checking IDF files...")
        
        # Check original IDFs
        original_idf_dir = self.job_output_dir / 'output_IDFs'
        if original_idf_dir.exists():
            original_idfs = list(original_idf_dir.glob('*.idf'))
            self.info.append(f"✓ Original IDFs: {len(original_idfs)} files")
            
            # Check IDF mapping
            idf_map_csv = self.job_output_dir / 'extracted_idf_buildings.csv'
            if idf_map_csv.exists():
                try:
                    df_map = pd.read_csv(idf_map_csv)
                    self.info.append(f"✓ IDF mapping: {len(df_map)} entries")
                    
                    # Check if all IDFs are mapped
                    mapped_ids = set(df_map['ogc_fid'].astype(str))
                    for idf in original_idfs[:5]:  # Check first 5
                        building_id = idf.stem.replace('building_', '')
                        if building_id not in mapped_ids:
                            self.warnings.append(f"⚠ IDF not in mapping: {idf.name}")
                            
                except Exception as e:
                    self.issues.append(f"✗ Error reading IDF mapping: {e}")
            else:
                self.issues.append("✗ IDF mapping file missing")
        else:
            self.issues.append("✗ Original IDF directory missing")
        
        # Check modified IDFs
        modified_idf_dir = self.job_output_dir / 'modified_idfs'
        if modified_idf_dir.exists():
            modified_idfs = list(modified_idf_dir.glob('**/*.idf'))
            self.info.append(f"✓ Modified IDFs: {len(modified_idfs)} files")
            
            # Check naming convention
            for idf in modified_idfs[:3]:  # Check first 3
                parts = idf.stem.split('_')
                if len(parts) < 4 or parts[0] != 'building':
                    self.warnings.append(f"⚠ Non-standard IDF name: {idf.name}")
        else:
            self.warnings.append("⚠ Modified IDF directory missing")
    
    def check_modification_outputs(self):
        """Check modification process outputs"""
        logger.info("\n4. Checking modification outputs...")
        
        mod_dir = self.job_output_dir / 'modified_idfs'
        if not mod_dir.exists():
            self.warnings.append("⚠ No modification outputs found")
            return
        
        # Check for reports
        report_types = [
            ('JSON', '*.json'),
            ('HTML', '*.html'),
            ('CSV', '*.csv'),
            ('Markdown', '*.md'),
            ('Parquet', '*.parquet')
        ]
        
        for report_type, pattern in report_types:
            reports = list(mod_dir.glob(pattern))
            if reports:
                self.info.append(f"✓ {report_type} reports: {len(reports)} files")
                
                # Check report content for JSON
                if report_type == 'JSON' and reports:
                    try:
                        with open(reports[0], 'r') as f:
                            report_data = json.load(f)
                        
                        summary = report_data.get('summary', {})
                        total = summary.get('total_attempts', 0)
                        success = summary.get('successful', 0)
                        
                        if total > 0:
                            rate = (success / total) * 100
                            self.info.append(f"  - Success rate: {rate:.1f}% ({success}/{total})")
                            
                            if rate < 50:
                                self.warnings.append(f"⚠ Low modification success rate: {rate:.1f}%")
                                
                                # Check for common errors
                                results = report_data.get('detailed_results', [])
                                error_counts = {}
                                for result in results:
                                    if not result.get('success', False):
                                        for error in result.get('errors', []):
                                            error_counts[error] = error_counts.get(error, 0) + 1
                                
                                if error_counts:
                                    self.warnings.append("  Common errors:")
                                    for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                                        self.warnings.append(f"    - {error} ({count} times)")
                                        
                    except Exception as e:
                        self.warnings.append(f"⚠ Error reading JSON report: {e}")
    
    def check_simulation_prerequisites(self):
        """Check simulation prerequisites"""
        logger.info("\n5. Checking simulation prerequisites...")
        
        # Check for EPW files
        epw_locations = [
            Path("data/weather"),
            self.job_output_dir / "weather",
            Path("user_configs") / self.job_id
        ]
        
        epw_found = False
        for location in epw_locations:
            if location.exists():
                epw_files = list(location.glob("*.epw"))
                if epw_files:
                    epw_found = True
                    self.info.append(f"✓ EPW files found in {location}: {len(epw_files)} files")
        
        if not epw_found:
            self.issues.append("✗ No EPW files found")
        
        # Check EPW configuration
        epw_config_path = Path("user_configs") / self.job_id / "user_config_epw.json"
        if epw_config_path.exists():
            try:
                with open(epw_config_path, 'r') as f:
                    epw_config = json.load(f)
                
                epw_list = epw_config.get('epw', [])
                self.info.append(f"✓ EPW configuration: {len(epw_list)} entries")
                
                # Validate EPW paths
                invalid_epw = []
                for entry in epw_list[:5]:  # Check first 5
                    epw_path = entry.get('epw_path', '')
                    if epw_path and not Path(epw_path).exists():
                        # Try relative paths
                        found = False
                        for base in epw_locations:
                            if (base / epw_path).exists():
                                found = True
                                break
                        
                        if not found:
                            invalid_epw.append(epw_path)
                
                if invalid_epw:
                    self.warnings.append(f"⚠ Invalid EPW paths: {len(invalid_epw)}")
                    for path in invalid_epw[:3]:
                        self.warnings.append(f"    - {path}")
                        
            except Exception as e:
                self.warnings.append(f"⚠ Error reading EPW config: {e}")
        else:
            self.info.append("ℹ No custom EPW configuration")
    
    def check_energyplus_installation(self):
        """Check EnergyPlus installation"""
        logger.info("\n6. Checking EnergyPlus installation...")
        
        # Common EnergyPlus locations
        ep_locations = [
            Path("C:/EnergyPlusV9-5-0/energyplus.exe"),
            Path("/usr/local/EnergyPlus-9-5-0/energyplus"),
            Path.home() / "EnergyPlus" / "energyplus.exe"
        ]
        
        # Check environment variable
        ep_env = os.environ.get("ENERGYPLUS_PATH")
        if ep_env:
            ep_locations.insert(0, Path(ep_env))
        
        ep_found = False
        for ep_path in ep_locations:
            if ep_path.exists():
                ep_found = True
                self.info.append(f"✓ EnergyPlus found: {ep_path}")
                
                # Try to get version
                try:
                    result = subprocess.run(
                        [str(ep_path), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        self.info.append(f"  Version: {version}")
                except Exception as e:
                    self.warnings.append(f"⚠ Could not get EnergyPlus version: {e}")
                
                break
        
        if not ep_found:
            self.issues.append("✗ EnergyPlus executable not found")
            self.issues.append("  Set ENERGYPLUS_PATH environment variable")
    
    def check_file_permissions(self):
        """Check file permissions"""
        logger.info("\n7. Checking file permissions...")
        
        # Check write permissions
        test_dirs = [
            self.job_output_dir,
            self.job_output_dir / 'Modified_Sim_Results'
        ]
        
        for test_dir in test_dirs:
            if test_dir.exists():
                test_file = test_dir / f"test_write_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tmp"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                    self.info.append(f"✓ Write permission: {test_dir}")
                except Exception as e:
                    self.issues.append(f"✗ No write permission: {test_dir}")
                    self.issues.append(f"  Error: {e}")
    
    def check_memory_and_disk(self):
        """Check available memory and disk space"""
        logger.info("\n8. Checking system resources...")
        
        try:
            import psutil
            
            # Check disk space
            disk_usage = psutil.disk_usage(str(self.job_output_dir))
            free_gb = disk_usage.free / (1024**3)
            
            if free_gb < 10:
                self.warnings.append(f"⚠ Low disk space: {free_gb:.1f} GB free")
            else:
                self.info.append(f"✓ Disk space: {free_gb:.1f} GB free")
            
            # Check memory
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            
            if available_gb < 4:
                self.warnings.append(f"⚠ Low memory: {available_gb:.1f} GB available")
            else:
                self.info.append(f"✓ Memory: {available_gb:.1f} GB available")
                
        except ImportError:
            self.info.append("ℹ psutil not installed - skipping resource check")
    
    def generate_diagnostic_report(self):
        """Generate comprehensive diagnostic report"""
        logger.info("\n" + "="*60)
        logger.info("DIAGNOSTIC SUMMARY")
        logger.info("="*60)
        
        # Print issues
        if self.issues:
            logger.error(f"\n❌ CRITICAL ISSUES ({len(self.issues)}):")
            for issue in self.issues:
                logger.error(f"  {issue}")
        
        # Print warnings
        if self.warnings:
            logger.warning(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                logger.warning(f"  {warning}")
        
        # Print info
        if self.info:
            logger.info(f"\n✅ CHECKS PASSED ({len(self.info)}):")
            for info in self.info[:10]:  # Show first 10
                logger.info(f"  {info}")
            
            if len(self.info) > 10:
                logger.info(f"  ... and {len(self.info) - 10} more")
        
        # Generate report file
        report_path = self.job_output_dir / f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            'job_id': self.job_id,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'critical_issues': len(self.issues),
                'warnings': len(self.warnings),
                'passed_checks': len(self.info),
                'can_proceed': len(self.issues) == 0
            },
            'critical_issues': self.issues,
            'warnings': self.warnings,
            'passed_checks': self.info,
            'recommendations': self.generate_recommendations()
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"\n📄 Detailed report saved to: {report_path}")
        
        # Overall assessment
        if len(self.issues) == 0:
            logger.info("\n✅ WORKFLOW READY - No critical issues found")
        else:
            logger.error(f"\n❌ WORKFLOW BLOCKED - {len(self.issues)} critical issues must be resolved")
    
    def generate_recommendations(self):
        """Generate recommendations based on diagnostics"""
        recommendations = []
        
        # Check for common patterns
        if any("IDD file" in issue for issue in self.issues):
            recommendations.append({
                'issue': 'IDD file configuration',
                'action': 'Set IDD_PATH environment variable or update idf_creation.iddfile in config',
                'priority': 'HIGH'
            })
        
        if any("EPW" in issue for issue in self.issues):
            recommendations.append({
                'issue': 'EPW file configuration',
                'action': 'Ensure EPW files are available and paths are correct in user_config_epw.json',
                'priority': 'HIGH'
            })
        
        if any("EnergyPlus" in issue for issue in self.issues):
            recommendations.append({
                'issue': 'EnergyPlus not found',
                'action': 'Install EnergyPlus or set ENERGYPLUS_PATH environment variable',
                'priority': 'HIGH'
            })
        
        if any("success rate" in warning for warning in self.warnings):
            recommendations.append({
                'issue': 'Low modification success rate',
                'action': 'Review modification parameters and rules - some may be invalid',
                'priority': 'MEDIUM'
            })
        
        if any("disk space" in warning for warning in self.warnings):
            recommendations.append({
                'issue': 'Low disk space',
                'action': 'Free up disk space or change output directory',
                'priority': 'MEDIUM'
            })
        
        return recommendations


def main():
    """Main function for diagnostics"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Diagnose issues in EnergyPlus workflow'
    )
    
    parser.add_argument('job_id', help='Job ID to diagnose')
    parser.add_argument('--output-dir', help='Base output directory')
    parser.add_argument('--check-resources', action='store_true',
                       help='Also check system resources')
    
    args = parser.parse_args()
    
    try:
        diagnostics = WorkflowDiagnostics(
            job_id=args.job_id,
            base_output_dir=args.output_dir
        )
        
        diagnostics.run_full_diagnostics()
        
        if args.check_resources:
            diagnostics.check_memory_and_disk()
        
    except Exception as e:
        logger.error(f"Diagnostic error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    # For direct testing
    TEST_JOB_ID = "650e5027-2c43-4a30-b588-5e4d72c0ac23"
    
    if len(sys.argv) > 1:
        main()
    else:
        # Direct execution
        diagnostics = WorkflowDiagnostics(TEST_JOB_ID)
        diagnostics.run_full_diagnostics()
        diagnostics.check_memory_and_disk()