"""
Standalone Simulation Runner for Modified IDFs
Runs EnergyPlus simulations on previously modified IDF files
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import traceback

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import simulation-related modules
from epw.run_epw_sims import simulate_all
from epw.assign_epw_file import assign_epw_for_building_with_overrides
import idf_creation  # For IDD config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StandaloneSimulationRunner:
    """Run simulations independently using existing modified IDFs"""
    
    def __init__(self, job_id: str, base_output_dir: str = None):
        """
        Initialize the runner
        
        Args:
            job_id: The job ID from previous run
            base_output_dir: Base output directory
        """
        self.job_id = job_id
        
        # Set up paths
        if base_output_dir:
            self.base_output_dir = Path(base_output_dir)
        else:
            # Try environment variable first, then fallback
            env_output_dir = os.environ.get("OUTPUT_DIR")
            if env_output_dir:
                self.base_output_dir = Path(env_output_dir)
            else:
                self.base_output_dir = Path(r"D:\Documents\daily\E_Plus_2040_py\output")
        
        self.job_output_dir = self.base_output_dir / job_id
        
        # Verify job directory exists
        if not self.job_output_dir.exists():
            raise ValueError(f"Job output directory not found: {self.job_output_dir}")
        
        # Set up key paths
        self.modified_idfs_dir = self.job_output_dir / "modified_idfs"
        self.modified_sim_output = self.job_output_dir / "Modified_Sim_Results"
        self.idf_map_csv = self.job_output_dir / "extracted_idf_buildings.csv"
        
        # Create output directory
        self.modified_sim_output.mkdir(exist_ok=True)
        
        # Initialize configuration placeholders
        self.main_config = {}
        self.modification_cfg = {}
        self.user_config_epw = None
        self.assigned_epw_log = {}
        
        logger.info(f"Initialized simulation runner for job: {job_id}")
        logger.info(f"Job output directory: {self.job_output_dir}")
        logger.info(f"Modified IDFs directory: {self.modified_idfs_dir}")
        logger.info(f"Simulation output directory: {self.modified_sim_output}")
        
    def load_configuration(self, config_path: str = None):
        """Load configuration from file"""
        if config_path:
            config_file = Path(config_path)
        else:
            # Try to find config in typical locations
            possible_paths = [
                Path("combined.json"),  # Check root directory first
                Path("user_configs") / self.job_id / "combined.json",
                Path("user_configs") / self.job_id / "main_config.json",
                self.job_output_dir / "combined.json",
                self.job_output_dir / "main_config.json"
            ]
            
            config_file = None
            for path in possible_paths:
                if path.exists():
                    config_file = path
                    break
            
            if not config_file:
                raise FileNotFoundError("Could not find configuration file")
        
        logger.info(f"Loading configuration from: {config_file}")
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Extract main configuration
        if 'main_config' in config_data:
            self.main_config = config_data['main_config']
        else:
            self.main_config = config_data
        
        # Extract specific configurations
        self.modification_cfg = self.main_config.get('modification', {})
        self.idf_cfg = self.main_config.get('idf_creation', {})
        self.user_flags = self.main_config.get('user_config_overrides', {})
        
        # Load EPW configuration
        if self.user_flags.get("override_epw_json", False):
            # First try to load from separate file
            try:
                self.load_epw_configuration()
            except Exception as e:
                logger.warning(f"Could not load separate EPW config: {e}")
                # Try to load from main config
                self.load_epw_from_main_config(config_data)
        
        # Set up IDF creation config (for IDD file path)
        self.setup_idf_config()
        
        logger.info("Configuration loaded successfully")
        
        return self.main_config
    
    def load_epw_configuration(self):
        """Load EPW configuration from user config"""
        job_config_dir = Path("user_configs") / self.job_id
        epw_json_path = job_config_dir / "user_config_epw.json"
        
        if epw_json_path.exists():
            with open(epw_json_path, 'r') as f:
                epw_data = json.load(f)
                self.user_config_epw = epw_data.get("epw", [])
                logger.info(f"Loaded EPW configuration with {len(self.user_config_epw)} entries")
        else:
            logger.warning(f"EPW configuration file not found: {epw_json_path}")
            raise FileNotFoundError(f"EPW configuration file not found: {epw_json_path}")
    
    def load_epw_from_main_config(self, config_data):
        """Load EPW configuration from main config data"""
        # Check if EPW config is in the main config
        if 'epw' in config_data:
            self.user_config_epw = config_data['epw']
            logger.info(f"Loaded EPW configuration from main config with {len(self.user_config_epw)} entries")
        else:
            logger.warning("No EPW configuration found in main config")
            self.user_config_epw = []
    
    def setup_idf_config(self):
        """Set up IDF creation configuration"""
        # Check environment variables first
        env_idd_path = os.environ.get("IDD_PATH")
        if env_idd_path:
            idf_creation.idf_config["iddfile"] = env_idd_path
        
        # Use config file values if available
        if "iddfile" in self.idf_cfg:
            idf_creation.idf_config["iddfile"] = self.idf_cfg["iddfile"]
        
        logger.info(f"IDD file path: {idf_creation.idf_config.get('iddfile', 'Not set')}")
    
    def load_building_data(self):
        """Load the IDF mapping data"""
        if not self.idf_map_csv.exists():
            raise FileNotFoundError(f"IDF mapping file not found: {self.idf_map_csv}")
        
        df_map = pd.read_csv(self.idf_map_csv)
        logger.info(f"Loaded building data for {len(df_map)} buildings")
        
        return df_map
    
    def find_modified_idfs(self):
        """Find all modified IDF files and match with building data"""
        if not self.modified_idfs_dir.exists():
            logger.error(f"Modified IDFs directory not found: {self.modified_idfs_dir}")
            return []
        
        # Load building mapping
        df_map = self.load_building_data()
        
        # Convert ogc_fid to string for consistent comparison
        df_map['ogc_fid_str'] = df_map['ogc_fid'].astype(str)
        
        # Find all modified IDF files
        modified_buildings = []
        
        for root, dirs, files in os.walk(self.modified_idfs_dir):
            for file in files:
                if file.endswith('.idf'):
                    full_path = os.path.join(root, file)
                    
                    # Extract building ID and variant from filename
                    # Expected format: building_4136733_scenario1_variant_0_20250112_110420.idf
                    parts = file.replace('.idf', '').split('_')
                    
                    if len(parts) >= 2 and parts[0] == 'building':
                        building_id = parts[1]
                        
                        # Find variant ID
                        variant_id = 'unknown'
                        if 'variant' in parts:
                            variant_idx = parts.index('variant')
                            if variant_idx + 1 < len(parts):
                                variant_id = f"variant_{parts[variant_idx + 1]}"
                        
                        logger.debug(f"Processing file: {file}, building_id: {building_id}, variant: {variant_id}")
                        
                        # Find original building data - compare as strings
                        orig_building = df_map[df_map['ogc_fid_str'] == building_id]
                        
                        if not orig_building.empty:
                            building_data = orig_building.iloc[0].to_dict()
                            
                            # Store relative path from modified_idfs_dir
                            rel_path = os.path.relpath(full_path, self.modified_idfs_dir)
                            building_data['idf_name'] = rel_path
                            building_data['variant_id'] = variant_id
                            building_data['original_ogc_fid'] = building_id
                            
                            # Ensure ogc_fid is string for consistency
                            building_data['ogc_fid'] = str(building_data['ogc_fid'])
                            
                            modified_buildings.append(building_data)
                            logger.debug(f"Added modified building: {building_id}, variant: {variant_id}")
                        else:
                            logger.warning(f"No building data found for ID '{building_id}'")
                            # Log what IDs are available for debugging
                            logger.debug(f"Available IDs in mapping: {df_map['ogc_fid_str'].unique()[:5].tolist()}...")
        
        logger.info(f"Found {len(modified_buildings)} modified IDF files")
        
        # Log summary by building
        if modified_buildings:
            df_modified = pd.DataFrame(modified_buildings)
            building_counts = df_modified.groupby('original_ogc_fid').size().to_dict()
            logger.info(f"Buildings to simulate: {building_counts}")
        
        return modified_buildings
    
    def run_simulations(self, specific_buildings=None, num_workers=None):
        """Run simulations on modified IDFs"""
        logger.info("="*60)
        logger.info("Starting simulation process")
        logger.info("="*60)
        
        # Get simulation configuration with better fallbacks
        post_mod_cfg = self.modification_cfg.get("post_modification", {})
        sim_config = post_mod_cfg.get("simulation_config", {})
        
        # If simulation_config not found in post_modification, check root level
        if not sim_config and "simulate_config" in self.idf_cfg:
            sim_config = self.idf_cfg["simulate_config"]
            logger.info("Using simulate_config from idf_creation section")
        
        if num_workers is None:
            num_workers = sim_config.get("num_workers", 4)
        
        # Find modified buildings
        modified_buildings = self.find_modified_idfs()
        
        if not modified_buildings:
            logger.error("No modified IDF files found!")
            return False
        
        # Filter specific buildings if requested
        if specific_buildings:
            filtered = []
            for building in modified_buildings:
                if building['original_ogc_fid'] in specific_buildings:
                    filtered.append(building)
            modified_buildings = filtered
            logger.info(f"Filtered to {len(modified_buildings)} buildings")
        
        # Convert to DataFrame for simulate_all
        df_modified = pd.DataFrame(modified_buildings)
        
        # Get EPW assignment strategy
        epw_assignment = sim_config.get("epw_assignment", "use_original")
        logger.info(f"Using EPW assignment strategy: {epw_assignment}")
        
        # Log simulation setup
        logger.info(f"Simulation setup:")
        logger.info(f"  - IDF directory: {self.modified_idfs_dir}")
        logger.info(f"  - Output directory: {self.modified_sim_output}")
        logger.info(f"  - Number of workers: {num_workers}")
        logger.info(f"  - IDD file: {idf_creation.idf_config.get('iddfile', 'Not set')}")
        logger.info(f"  - Total simulations to run: {len(df_modified)}")
        logger.info(f"  - EPW config available: {self.user_config_epw is not None}")
        
        # Run simulations
        start_time = datetime.now()
        
        try:
            simulate_all(
                df_buildings=df_modified,
                idf_directory=str(self.modified_idfs_dir),
                iddfile=idf_creation.idf_config["iddfile"],
                base_output_dir=str(self.modified_sim_output),
                user_config_epw=self.user_config_epw,
                assigned_epw_log=self.assigned_epw_log,
                num_workers=num_workers
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Completed simulations for {len(df_modified)} modified IDFs")
            logger.info(f"Total simulation time: {duration:.1f} seconds")
            logger.info(f"Average time per simulation: {duration/len(df_modified):.1f} seconds")
            
            # Generate simulation report
            self.generate_simulation_report(df_modified, duration)
            
            return True
            
        except Exception as e:
            logger.error(f"Simulation failed: {str(e)}")
            traceback.print_exc()
            return False
    
    def generate_simulation_report(self, df_simulated, duration):
        """Generate a report of simulation results"""
        report_path = self.modified_sim_output / f"simulation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Check which simulations completed successfully
        completed = []
        failed = []
        
        for _, building in df_simulated.iterrows():
            year = building.get('desired_climate_year', 2020)
            building_id = building.get('original_ogc_fid', building.get('ogc_fid', 'unknown'))
            variant_id = building.get('variant_id', 'unknown')
            
            # Check if output files exist
            output_dir = self.modified_sim_output / str(year)
            
            # Look for output files
            expected_prefix = f"simulation_bldg{building.name}_{building_id}"
            
            found_outputs = []
            if output_dir.exists():
                for file in output_dir.iterdir():
                    if file.name.startswith(expected_prefix):
                        found_outputs.append(file.name)
            
            if found_outputs:
                completed.append({
                    'building_id': building_id,
                    'variant_id': variant_id,
                    'year': year,
                    'output_files': found_outputs
                })
            else:
                failed.append({
                    'building_id': building_id,
                    'variant_id': variant_id,
                    'year': year,
                    'reason': 'No output files found'
                })
        
        report_data = {
            'metadata': {
                'job_id': self.job_id,
                'timestamp': datetime.now().isoformat(),
                'simulation_directory': str(self.modified_sim_output),
                'duration_seconds': duration
            },
            'summary': {
                'total_simulations': len(df_simulated),
                'completed': len(completed),
                'failed': len(failed),
                'success_rate': (len(completed) / len(df_simulated) * 100) if len(df_simulated) > 0 else 0
            },
            'completed_simulations': completed,
            'failed_simulations': failed
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"\nSimulation Report:")
        logger.info(f"  - Total: {len(df_simulated)}")
        logger.info(f"  - Completed: {len(completed)}")
        logger.info(f"  - Failed: {len(failed)}")
        logger.info(f"  - Success rate: {report_data['summary']['success_rate']:.1f}%")
        logger.info(f"  - Report saved to: {report_path}")
    
    def parse_results(self):
        """Parse simulation results (if enabled in config)"""
        parse_config = self.modification_cfg.get("post_modification", {}).get("parse_results", {})
        
        # Handle both formats: parse_results.enabled and just parse_results dict
        if isinstance(parse_config, dict) and len(parse_config) > 0:
            # If parse_config has keys, assume parsing is enabled
            enabled = parse_config.get("enabled", True)
        else:
            enabled = False
        
        if not enabled:
            logger.info("Result parsing is not enabled in configuration")
            return
        
        logger.info("Parsing simulation results...")
        
        # Import parser
        from parserr.energyplus_analyzer_main import EnergyPlusAnalyzer
        from parserr.helpers import prepare_idf_sql_pairs_with_mapping
        
        # Get parse configuration
        parse_idf = parse_config.get("parse_idf", False)
        parse_sql = parse_config.get("parse_sql", True)
        categories = parse_config.get("categories", None)
        
        # Prepare IDF-SQL pairs
        pairs_with_mapping = prepare_idf_sql_pairs_with_mapping(
            sim_output_dir=str(self.modified_sim_output),
            idf_dir=str(self.modified_idfs_dir),
            idf_map_csv=str(self.idf_map_csv)
        )
        
        if not pairs_with_mapping:
            logger.warning("No IDF-SQL pairs found for parsing")
            return
        
        logger.info(f"Found {len(pairs_with_mapping)} pairs to parse")
        
        # Initialize analyzer
        analyzer = EnergyPlusAnalyzer(
            save_raw_objects=True,
            batch_size=100,
            validate_outputs=True,
            output_dir=str(self.job_output_dir / "parsed_modified_results")
        )
        
        # Parse files
        try:
            analyzer.analyze_multiple_files(
                pairs_with_mapping,
                parse_idf=parse_idf,
                parse_sql=parse_sql,
                categories=categories,
                save_summary=True,
                save_by_category=True,
                save_by_building=True
            )
            
            logger.info("Parsing completed successfully")
            
        except Exception as e:
            logger.error(f"Parsing failed: {str(e)}")
            traceback.print_exc()
    
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        issues = []
        
        # Check modified IDFs directory
        if not self.modified_idfs_dir.exists():
            issues.append(f"Modified IDFs directory not found: {self.modified_idfs_dir}")
        else:
            idf_count = len(list(self.modified_idfs_dir.glob("**/*.idf")))
            if idf_count == 0:
                issues.append(f"No IDF files found in: {self.modified_idfs_dir}")
            else:
                logger.info(f"Found {idf_count} IDF files")
        
        # Check IDF mapping file
        if not self.idf_map_csv.exists():
            issues.append(f"IDF mapping file not found: {self.idf_map_csv}")
        
        # Check IDD file configuration
        idd_file = idf_creation.idf_config.get("iddfile")
        if not idd_file:
            issues.append("IDD file path not configured")
        elif not Path(idd_file).exists():
            issues.append(f"IDD file not found: {idd_file}")
        
        # Check EPW configuration if needed (more flexible)
        if self.user_flags.get("override_epw_json", False):
            if not self.user_config_epw and self.user_config_epw is not None:
                logger.warning("EPW configuration is empty but enabled")
            elif self.user_config_epw is None:
                logger.warning("EPW configuration enabled but not loaded - will use default EPW assignment")
        
        if issues:
            logger.error("Prerequisites check failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False
        
        logger.info("All prerequisites met")
        return True
    
    def test_single_building(self, building_id: str):
        """Test simulation on a single building"""
        logger.info(f"Running test simulation for building: {building_id}")
        
        return self.run_simulations(
            specific_buildings=[building_id],
            num_workers=1
        )


def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run EnergyPlus simulations on modified IDFs independently',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run simulations with default settings
  python standalone_simulation_runner.py 650e5027-2c43-4a30-b588-5e4d72c0ac23
  
  # Run with custom config and workers
  python standalone_simulation_runner.py 650e5027 --config my_config.json --workers 8
  
  # Test on specific building
  python standalone_simulation_runner.py 650e5027 --test-building 4136733
  
  # Run and parse results
  python standalone_simulation_runner.py 650e5027 --parse-results
  
  # Check prerequisites only
  python standalone_simulation_runner.py 650e5027 --check-only
        """
    )
    
    parser.add_argument('job_id', help='Job ID from previous run')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--output-dir', help='Base output directory')
    parser.add_argument('--workers', type=int, help='Number of parallel workers')
    parser.add_argument('--test-building', help='Test on specific building ID')
    parser.add_argument('--parse-results', action='store_true', 
                       help='Parse results after simulation')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check prerequisites, do not run')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize runner
        runner = StandaloneSimulationRunner(
            job_id=args.job_id,
            base_output_dir=args.output_dir
        )
        
        # Load configuration
        runner.load_configuration(args.config)
        
        # Check prerequisites
        if not runner.check_prerequisites():
            logger.error("Cannot proceed - prerequisites not met")
            sys.exit(1)
        
        if args.check_only:
            logger.info("Prerequisites check completed")
            sys.exit(0)
        
        # Run simulations
        success = False
        if args.test_building:
            success = runner.test_single_building(args.test_building)
        else:
            success = runner.run_simulations(num_workers=args.workers)
        
        # Parse results if requested
        if success and args.parse_results:
            runner.parse_results()
        
        logger.info("\nSimulation process completed!")
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # For direct testing without command line args
    TEST_JOB_ID = "650e5027-2c43-4a30-b588-5e4d72c0ac23"
    TEST_OUTPUT_DIR = r"D:\Documents\daily\E_Plus_2040_py\output"
    TEST_CONFIG_PATH = r"D:\Documents\daily\E_Plus_2040_py\combined.json"
    
    # Check if running with command line args
    if len(sys.argv) > 1:
        main()
    else:
        # Direct execution for testing
        logger.info("Running in test mode...")
        
        runner = StandaloneSimulationRunner(
            job_id=TEST_JOB_ID,
            base_output_dir=TEST_OUTPUT_DIR
        )
        
        # Load configuration from specific path
        runner.load_configuration(TEST_CONFIG_PATH)
        
        # Check prerequisites
        if runner.check_prerequisites():
            # Test on a single building first
            # runner.test_single_building("4136733")
            
            # Or run full simulations
            runner.run_simulations(num_workers=2)
            
            # Optionally parse results
            # runner.parse_results()