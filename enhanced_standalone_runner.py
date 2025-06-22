"""
Enhanced Standalone Runner
Runs modifications, simulations, and parsing independently or as a full pipeline
"""

import os
import sys
import json
import logging
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import pandas as pd
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import sqlite3

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import only the modules we know exist
from idf_modification.modification_engine import ModificationEngine
from idf_modification.modification_config import ModificationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedStandaloneRunner:
    """Enhanced runner for modifications, simulations, and parsing"""
    
    def __init__(self, job_id: str, config_path: str = None, base_output_dir: str = None):
        """
        Initialize the enhanced runner
        
        Args:
            job_id: The job ID from previous run
            config_path: Path to combined.json configuration file
            base_output_dir: Base output directory
        """
        self.job_id = job_id
        self.config_path = Path(config_path) if config_path else None
        
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
        
        # Verify job directory exists
        if not self.job_output_dir.exists():
            raise ValueError(f"Job output directory not found: {self.job_output_dir}")
        
        # Set up key paths
        self.idf_dir = self.job_output_dir / "output_IDFs"
        self.parsed_data_dir = self.job_output_dir / "parsed_data"
        self.modified_idfs_dir = self.job_output_dir / "modified_idfs"
        self.simulation_results_dir = self.job_output_dir / "simulation_results"
        self.analysis_dir = self.job_output_dir / "analysis"
        
        # Create necessary directories
        self.modified_idfs_dir.mkdir(exist_ok=True)
        self.simulation_results_dir.mkdir(exist_ok=True)
        self.analysis_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.load_configuration()
        
        logger.info(f"Initialized enhanced runner for job: {job_id}")
        logger.info(f"Job output directory: {self.job_output_dir}")
        
    def load_configuration(self):
        """Load configuration from combined.json"""
        if self.config_path and self.config_path.exists():
            config_file = self.config_path
        else:
            # Try to find config in typical locations
            possible_paths = [
                Path("combined.json"),
                Path(r"D:\Documents\daily\E_Plus_2040_py\combined.json"),
                Path("user_configs") / self.job_id / "combined.json",
                self.job_output_dir / "combined.json"
            ]
            
            config_file = None
            for path in possible_paths:
                if path.exists():
                    config_file = path
                    break
            
            if not config_file:
                raise FileNotFoundError("Could not find combined.json configuration file")
        
        logger.info(f"Loading configuration from: {config_file}")
        
        with open(config_file, 'r') as f:
            self.full_config = json.load(f)
        
        # Extract key configurations
        main_config = self.full_config.get('main_config', {})
        self.modification_cfg = main_config.get('modification', {})
        self.simulation_cfg = main_config.get('simulation', {})
        self.parsing_cfg = main_config.get('parsing', {})
        
        # Extract post-modification settings
        self.post_modification_cfg = self.modification_cfg.get('post_modification', {})
        
        logger.info("Configuration loaded successfully")
        
    def run_modifications_only(self):
        """Run only the modification step"""
        logger.info("="*60)
        logger.info("Running MODIFICATIONS ONLY")
        logger.info("="*60)
        
        from standalone_modification_runner import StandaloneModificationRunner
        
        # Use the existing standalone modification runner
        mod_runner = StandaloneModificationRunner(
            job_id=self.job_id,
            base_output_dir=str(self.base_output_dir)
        )
        
        # Override configuration with our loaded config
        mod_runner.modification_cfg = self.modification_cfg
        mod_runner.categories_to_modify = self.modification_cfg.get('categories_to_modify', {})
        
        # Run modifications
        results = mod_runner.run_modifications()
        
        # Save modification results for next steps
        results_path = self.modified_idfs_dir / "modification_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Modification results saved to: {results_path}")
        
        return results
        
    def run_simulations(self, modified_idfs=None):
        """Run simulations on modified IDFs"""
        logger.info("="*60)
        logger.info("Running SIMULATIONS")
        logger.info("="*60)
        
        if not self.post_modification_cfg.get('run_simulations', True):
            logger.info("Simulations disabled in configuration")
            return []
        
        # Get modified IDF files
        if modified_idfs is None:
            modified_idfs = list(self.modified_idfs_dir.glob("*.idf"))
            logger.info(f"Found {len(modified_idfs)} modified IDF files")
        
        if not modified_idfs:
            logger.warning("No modified IDF files found!")
            return []
        
        # Get simulation configuration
        sim_config = self.simulation_cfg.copy()
        
        # Get EnergyPlus path from various possible locations in config
        eplus_path = (
            sim_config.get('energyplus_path') or
            sim_config.get('eplus_path') or
            sim_config.get('energyplus_exe') or
            os.environ.get('EPLUS_PATH') or
            r'C:\EnergyPlusV9-5-0\energyplus.exe'
        )
        
        # Get weather assignment method
        weather_assignment = sim_config.get('weather_assignment', {})
        use_epw_module = weather_assignment.get('use_epw_module', False)
        
        # Default weather file from config
        default_weather_file = sim_config.get('weather_file', '')
        
        # If using EPW module, load it
        if use_epw_module:
            try:
                # Add parent directory to path for imports
                import sys
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from epw.assign_epw_file import assign_epw_for_building_with_overrides
                from epw.epw_lookup import epw_lookup
                
                # Load user config if specified
                user_config_epw = weather_assignment.get('user_config_epw', [])
                assigned_epw_log = {}
                
                logger.info("Using EPW assignment module for weather files")
            except ImportError as e:
                logger.warning(f"Could not import EPW module: {e}")
                use_epw_module = False
        
        # If not using EPW module and no default weather file, try to find one
        if not use_epw_module and not default_weather_file:
            # Try to find in job directory
            epw_files = list(self.job_output_dir.glob("*.epw"))
            if not epw_files:
                # Try parent directory
                epw_files = list(self.job_output_dir.parent.glob("*.epw"))
            if not epw_files:
                # Try data/weather directory
                project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                weather_dir = project_root / "data" / "weather"
                if weather_dir.exists():
                    epw_files = list(weather_dir.glob("*.epw"))
            
            if epw_files:
                default_weather_file = str(epw_files[0])
                logger.info(f"Auto-detected weather file: {default_weather_file}")
            else:
                logger.error("No weather file found! Please either:")
                logger.error("1. Add 'weather_file' to your simulation config in combined.json")
                logger.error("2. Place EPW files in data/weather/ directory")
                logger.error("3. Enable EPW module with 'use_epw_module': true")
                return []
        
        logger.info(f"Using EnergyPlus: {eplus_path}")
        
        # Prepare simulation tasks
        simulation_tasks = []
        for idf_path in modified_idfs:
            # Determine weather file for this building
            if use_epw_module:
                # Extract building info from filename
                building_id = idf_path.stem.split('_')[1] if '_' in idf_path.stem else 'unknown'
                
                # Create a building row for EPW assignment
                building_row = {
                    'ogc_fid': building_id,
                    'lat': weather_assignment.get('default_lat', 52.0),  # Default to Netherlands
                    'lon': weather_assignment.get('default_lon', 5.0),
                    'desired_climate_year': weather_assignment.get('default_year', 2020)
                }
                
                # Check if we have building-specific data
                building_data = weather_assignment.get('building_data', {})
                if building_id in building_data:
                    building_row.update(building_data[building_id])
                
                # Assign EPW file
                weather_file = assign_epw_for_building_with_overrides(
                    building_row=building_row,
                    user_config_epw=user_config_epw,
                    assigned_epw_log=assigned_epw_log
                )
                
                # Resolve relative paths
                if weather_file and not os.path.isabs(weather_file):
                    # Try relative to project root
                    project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    resolved_path = project_root / weather_file
                    if resolved_path.exists():
                        weather_file = str(resolved_path)
                        logger.debug(f"Resolved relative EPW path to: {weather_file}")
                    else:
                        logger.warning(f"Could not resolve relative EPW path: {weather_file}")
                
                if not weather_file or not os.path.isfile(weather_file):
                    logger.warning(f"No valid EPW file for building {building_id}, using default")
                    weather_file = default_weather_file
            else:
                weather_file = default_weather_file
            
            if not weather_file:
                logger.error(f"No weather file available for {idf_path.name}")
                continue
            
            # Create output directory based on variant
            variant_id = idf_path.stem.split('_')[-1] if '_variant_' in idf_path.stem else 'default'
            
            task = {
                'idf_path': str(idf_path),
                'weather_file': weather_file,
                'output_dir': str(self.simulation_results_dir / idf_path.stem),
                'eplus_path': eplus_path
            }
            simulation_tasks.append(task)
        
        if not simulation_tasks:
            logger.error("No simulation tasks created!")
            return []
        
        logger.info(f"Using weather file(s): {set(t['weather_file'] for t in simulation_tasks)}")
        
        # Run simulations
        simulation_results = []
        
        # Determine number of parallel processes
        num_processes = sim_config.get('num_processes', multiprocessing.cpu_count() - 1)
        num_processes = max(1, min(num_processes, len(simulation_tasks)))
        
        logger.info(f"Running {len(simulation_tasks)} simulations with {num_processes} processes")
        
        start_time = time.time()
        
        # Run simulations in parallel
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            future_to_task = {
                executor.submit(self._run_single_simulation, task): task 
                for task in simulation_tasks
            }
            
            completed = 0
            for future in as_completed(future_to_task):
                completed += 1
                task = future_to_task[future]
                
                try:
                    result = future.result()
                    simulation_results.append(result)
                    
                    status = "SUCCESS" if result['success'] else "FAILED"
                    logger.info(f"[{completed}/{len(simulation_tasks)}] {status}: {Path(task['idf_path']).name}")
                    
                except Exception as e:
                    logger.error(f"Simulation failed for {task['idf_path']}: {e}")
                    simulation_results.append({
                        'idf_path': task['idf_path'],
                        'success': False,
                        'error': str(e)
                    })
        
        elapsed_time = time.time() - start_time
        
        # Summary
        successful = sum(1 for r in simulation_results if r['success'])
        logger.info(f"\nSimulation Summary:")
        logger.info(f"  Total: {len(simulation_results)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {len(simulation_results) - successful}")
        logger.info(f"  Total time: {elapsed_time:.1f} seconds")
        logger.info(f"  Average time per simulation: {elapsed_time/len(simulation_results):.1f} seconds")
        
        # Save simulation results
        results_path = self.simulation_results_dir / "simulation_results.json"
        with open(results_path, 'w') as f:
            json.dump(simulation_results, f, indent=2, default=str)
        
        return simulation_results
        
    def _run_single_simulation(self, task):
        """Run a single EnergyPlus simulation"""
        idf_path = task['idf_path']
        weather_file = task['weather_file']
        output_dir = task['output_dir']
        eplus_path = task['eplus_path']
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Copy IDF file to output directory
        output_idf = Path(output_dir) / Path(idf_path).name
        shutil.copy2(idf_path, output_idf)
        
        # Run EnergyPlus
        cmd = [
            eplus_path,
            '-w', weather_file,
            '-d', output_dir,
            str(output_idf)
        ]
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            elapsed_time = time.time() - start_time
            
            # Check if simulation was successful
            sql_file = Path(output_dir) / "eplusout.sql"
            success = sql_file.exists() and result.returncode == 0
            
            return {
                'idf_path': idf_path,
                'output_dir': output_dir,
                'success': success,
                'elapsed_time': elapsed_time,
                'returncode': result.returncode,
                'sql_file': str(sql_file) if sql_file.exists() else None,
                'stdout': result.stdout[-1000:] if result.stdout else None,  # Last 1000 chars
                'stderr': result.stderr[-1000:] if result.stderr else None
            }
            
        except subprocess.TimeoutExpired:
            return {
                'idf_path': idf_path,
                'output_dir': output_dir,
                'success': False,
                'error': 'Simulation timeout (1 hour)',
                'elapsed_time': 3600
            }
        except Exception as e:
            return {
                'idf_path': idf_path,
                'output_dir': output_dir,
                'success': False,
                'error': str(e),
                'elapsed_time': time.time() - start_time
            }
            
    def parse_results(self, simulation_results=None):
        """Parse simulation results from SQL files"""
        logger.info("="*60)
        logger.info("PARSING RESULTS")
        logger.info("="*60)
        
        parse_config = self.post_modification_cfg.get('parse_results', {})
        
        if simulation_results is None:
            # Load from saved results
            results_path = self.simulation_results_dir / "simulation_results.json"
            if results_path.exists():
                with open(results_path, 'r') as f:
                    simulation_results = json.load(f)
            else:
                logger.error("No simulation results found!")
                return []
        
        # Filter successful simulations
        successful_sims = [r for r in simulation_results if r.get('success', False)]
        logger.info(f"Parsing results from {len(successful_sims)} successful simulations")
        
        parsed_results = []
        
        # Parse SQL results if enabled
        if parse_config.get('parse_sql', True):
            logger.info("Parsing SQL files...")
            
            categories = parse_config.get('categories', ['energy', 'comfort', 'loads'])
            
            for sim_result in successful_sims:
                sql_file = sim_result.get('sql_file')
                if not sql_file or not Path(sql_file).exists():
                    continue
                
                try:
                    # Parse SQL file
                    parsed_data = self._parse_sql_file(sql_file, categories)
                    
                    # Add metadata
                    parsed_data['metadata'] = {
                        'idf_path': sim_result['idf_path'],
                        'sql_file': sql_file,
                        'building_id': Path(sim_result['idf_path']).stem.split('_')[1] if '_' in Path(sim_result['idf_path']).stem else 'unknown',
                        'variant_id': Path(sim_result['idf_path']).stem.split('_')[-2] if '_' in Path(sim_result['idf_path']).stem else 'unknown'
                    }
                    
                    parsed_results.append(parsed_data)
                    
                except Exception as e:
                    logger.error(f"Failed to parse {sql_file}: {e}")
        
        # Save parsed results
        parsed_path = self.analysis_dir / f"parsed_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(parsed_path, 'w') as f:
            json.dump(parsed_results, f, indent=2, default=str)
        
        logger.info(f"Parsed results saved to: {parsed_path}")
        
        return parsed_results
        
    def _parse_sql_file(self, sql_file, categories):
        """Parse EnergyPlus SQL output file"""
        parsed_data = {}
        
        try:
            conn = sqlite3.connect(sql_file)
            
            if 'energy' in categories:
                # Query for energy consumption
                query = """
                SELECT 
                    ReportName,
                    ReportForString,
                    TableName,
                    ColumnName,
                    RowName,
                    Value,
                    Units
                FROM TabularDataWithStrings
                WHERE TableName IN ('Site and Source Energy', 'End Uses', 'Utility Use Per Conditioned Floor Area')
                """
                
                df = pd.read_sql_query(query, conn)
                
                # Extract key metrics
                energy_data = {}
                
                # Total site energy
                site_energy = df[(df['TableName'] == 'Site and Source Energy') & 
                               (df['RowName'] == 'Total Site Energy') & 
                               (df['ColumnName'] == 'Energy Per Total Building Area')]
                
                if not site_energy.empty:
                    energy_data['total_site_energy'] = float(site_energy.iloc[0]['Value'])
                    energy_data['energy_units'] = site_energy.iloc[0]['Units']
                
                # End uses
                end_uses = df[df['TableName'] == 'End Uses']
                if not end_uses.empty:
                    energy_data['end_uses'] = {}
                    for _, row in end_uses.iterrows():
                        if row['ColumnName'] == 'Electricity':
                            energy_data['end_uses'][row['RowName']] = float(row['Value'])
                
                parsed_data['energy'] = energy_data
                
            if 'comfort' in categories:
                # Query for comfort metrics
                query = """
                SELECT 
                    ReportName,
                    ReportForString,
                    TableName,
                    ColumnName,
                    RowName,
                    Value,
                    Units
                FROM TabularDataWithStrings
                WHERE TableName LIKE '%Comfort%' OR TableName LIKE '%Unmet%'
                """
                
                df = pd.read_sql_query(query, conn)
                
                comfort_data = {}
                
                # Extract unmet hours
                unmet_heating = df[(df['RowName'].str.contains('Heating', na=False)) & 
                                 (df['ColumnName'].str.contains('Hours', na=False))]
                
                if not unmet_heating.empty:
                    comfort_data['unmet_heating_hours'] = float(unmet_heating.iloc[0]['Value'])
                
                unmet_cooling = df[(df['RowName'].str.contains('Cooling', na=False)) & 
                                 (df['ColumnName'].str.contains('Hours', na=False))]
                
                if not unmet_cooling.empty:
                    comfort_data['unmet_cooling_hours'] = float(unmet_cooling.iloc[0]['Value'])
                
                parsed_data['comfort'] = comfort_data
                
            if 'loads' in categories:
                # Query for peak loads
                query = """
                SELECT 
                    ReportName,
                    ReportForString,
                    TableName,
                    ColumnName,
                    RowName,
                    Value,
                    Units
                FROM TabularDataWithStrings
                WHERE TableName LIKE '%Peak%' OR TableName LIKE '%Design%'
                """
                
                df = pd.read_sql_query(query, conn)
                
                loads_data = {}
                
                # Extract peak loads
                peak_cooling = df[(df['RowName'].str.contains('Cooling', na=False)) & 
                                (df['ColumnName'].str.contains('Load', na=False))]
                
                if not peak_cooling.empty:
                    loads_data['peak_cooling_load'] = float(peak_cooling.iloc[0]['Value'])
                
                peak_heating = df[(df['RowName'].str.contains('Heating', na=False)) & 
                                (df['ColumnName'].str.contains('Load', na=False))]
                
                if not peak_heating.empty:
                    loads_data['peak_heating_load'] = float(peak_heating.iloc[0]['Value'])
                
                parsed_data['loads'] = loads_data
                
            conn.close()
            
        except Exception as e:
            logger.error(f"Error parsing SQL file: {e}")
            
        return parsed_data
        
    def compare_with_baseline(self, parsed_results=None):
        """Compare modified results with baseline"""
        logger.info("="*60)
        logger.info("COMPARING WITH BASELINE")
        logger.info("="*60)
        
        if not self.post_modification_cfg.get('compare_with_baseline', True):
            logger.info("Baseline comparison disabled")
            return
        
        # Load parsed results if not provided
        if parsed_results is None:
            parsed_files = list(self.analysis_dir.glob("parsed_results_*.json"))
            if not parsed_files:
                logger.error("No parsed results found!")
                return
            
            # Use most recent
            parsed_path = sorted(parsed_files)[-1]
            with open(parsed_path, 'r') as f:
                parsed_results = json.load(f)
        
        # Group results by building
        results_by_building = {}
        baseline_results = {}
        
        for result in parsed_results:
            building_id = result['metadata']['building_id']
            variant_id = result['metadata']['variant_id']
            
            if building_id not in results_by_building:
                results_by_building[building_id] = {}
            
            # Check if this is baseline
            if variant_id == 'baseline' or 'baseline' in variant_id.lower():
                baseline_results[building_id] = result
            else:
                results_by_building[building_id][variant_id] = result
        
        # Calculate comparisons
        comparison_results = []
        
        for building_id, variants in results_by_building.items():
            baseline = baseline_results.get(building_id)
            
            if not baseline:
                logger.warning(f"No baseline found for building {building_id}")
                continue
            
            for variant_id, variant_result in variants.items():
                comparison = {
                    'building_id': building_id,
                    'variant_id': variant_id,
                    'savings': {}
                }
                
                # Calculate energy savings
                if 'energy' in baseline and 'energy' in variant_result:
                    baseline_energy = baseline['energy'].get('total_site_energy', 0)
                    variant_energy = variant_result['energy'].get('total_site_energy', 0)
                    
                    if baseline_energy > 0:
                        savings_pct = ((baseline_energy - variant_energy) / baseline_energy) * 100
                        comparison['savings']['energy_percent'] = savings_pct
                        comparison['savings']['energy_absolute'] = baseline_energy - variant_energy
                
                # Calculate comfort improvements
                if 'comfort' in baseline and 'comfort' in variant_result:
                    baseline_unmet = (baseline['comfort'].get('unmet_heating_hours', 0) + 
                                    baseline['comfort'].get('unmet_cooling_hours', 0))
                    variant_unmet = (variant_result['comfort'].get('unmet_heating_hours', 0) + 
                                   variant_result['comfort'].get('unmet_cooling_hours', 0))
                    
                    comparison['comfort'] = {
                        'baseline_unmet_hours': baseline_unmet,
                        'variant_unmet_hours': variant_unmet,
                        'improvement': baseline_unmet - variant_unmet
                    }
                
                comparison_results.append(comparison)
        
        # Generate comparison report
        analysis_options = self.post_modification_cfg.get('analysis_options', {})
        
        if analysis_options.get('generate_comparison_charts', True):
            self._generate_comparison_charts(comparison_results)
        
        if analysis_options.get('create_summary_dashboard', True):
            self._create_summary_dashboard(comparison_results)
        
        # Save comparison results
        comparison_path = self.analysis_dir / f"comparison_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(comparison_path, 'w') as f:
            json.dump(comparison_results, f, indent=2)
        
        logger.info(f"Comparison results saved to: {comparison_path}")
        
        return comparison_results
        
    def _generate_comparison_charts(self, comparison_results):
        """Generate comparison charts"""
        logger.info("Generating comparison charts...")
        
        # Create charts directory
        charts_dir = self.analysis_dir / "charts"
        charts_dir.mkdir(exist_ok=True)
        
        # Create summary CSV for easy plotting
        if comparison_results:
            df_data = []
            for result in comparison_results:
                df_data.append({
                    'building_id': result['building_id'],
                    'variant_id': result['variant_id'],
                    'energy_savings_pct': result['savings'].get('energy_percent', 0),
                    'energy_savings_abs': result['savings'].get('energy_absolute', 0),
                    'comfort_improvement': result.get('comfort', {}).get('improvement', 0)
                })
            
            df = pd.DataFrame(df_data)
            csv_path = charts_dir / "comparison_data.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"Comparison data saved to: {csv_path}")
        
    def _create_summary_dashboard(self, comparison_results):
        """Create summary dashboard"""
        logger.info("Creating summary dashboard...")
        
        dashboard_path = self.analysis_dir / f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Calculate summary statistics
        if not comparison_results:
            logger.warning("No comparison results to create dashboard")
            return
            
        total_buildings = len(set(r['building_id'] for r in comparison_results))
        energy_savings = [r['savings'].get('energy_percent', 0) for r in comparison_results]
        avg_savings = sum(energy_savings) / len(energy_savings) if energy_savings else 0
        max_savings = max(energy_savings) if energy_savings else 0
        min_savings = min(energy_savings) if energy_savings else 0
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Energy Modification Analysis Dashboard - Job {self.job_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                .header {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .summary-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .metric-value {{ font-size: 2.5em; font-weight: bold; margin: 10px 0; }}
                .metric-label {{ color: #666; font-size: 0.9em; text-transform: uppercase; }}
                .positive {{ color: #2e7d32; }}
                .negative {{ color: #d32f2f; }}
                .neutral {{ color: #1976d2; }}
                table {{ width: 100%; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                th, td {{ padding: 12px; text-align: left; }}
                th {{ background-color: #f5f5f5; font-weight: 600; color: #333; }}
                tr:hover {{ background-color: #f9f9f9; }}
                .footer {{ margin-top: 40px; padding: 20px; text-align: center; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Energy Modification Analysis Dashboard</h1>
                    <p><strong>Job ID:</strong> {self.job_id}</p>
                    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="metric-label">Total Buildings Analyzed</div>
                        <div class="metric-value neutral">{total_buildings}</div>
                    </div>
                    <div class="summary-card">
                        <div class="metric-label">Average Energy Savings</div>
                        <div class="metric-value {'positive' if avg_savings > 0 else 'negative'}">{avg_savings:.1f}%</div>
                    </div>
                    <div class="summary-card">
                        <div class="metric-label">Maximum Savings</div>
                        <div class="metric-value positive">{max_savings:.1f}%</div>
                    </div>
                    <div class="summary-card">
                        <div class="metric-label">Minimum Savings</div>
                        <div class="metric-value {'positive' if min_savings > 0 else 'negative'}">{min_savings:.1f}%</div>
                    </div>
                </div>
                
                <h2>Detailed Results by Building</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Building ID</th>
                            <th>Variant</th>
                            <th>Energy Savings (%)</th>
                            <th>Energy Savings (kWh)</th>
                            <th>Comfort Improvement (hours)</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for result in sorted(comparison_results, key=lambda x: (x['building_id'], x['variant_id'])):
            energy_pct = result['savings'].get('energy_percent', 0)
            energy_abs = result['savings'].get('energy_absolute', 0)
            comfort = result.get('comfort', {}).get('improvement', 0)
            
            html_content += f"""
                        <tr>
                            <td>{result['building_id']}</td>
                            <td>{result['variant_id']}</td>
                            <td class="{'positive' if energy_pct > 0 else 'negative'}">{energy_pct:.1f}%</td>
                            <td>{energy_abs:,.0f}</td>
                            <td class="{'positive' if comfort > 0 else 'negative'}">{comfort:.0f}</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
                
                <div class="footer">
                    <p>This report was generated automatically by the Enhanced Standalone Runner</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(dashboard_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Dashboard saved to: {dashboard_path}")
        
    def run_full_pipeline(self):
        """Run the complete pipeline: modifications -> simulations -> parsing -> analysis"""
        logger.info("="*60)
        logger.info("RUNNING FULL PIPELINE")
        logger.info("="*60)
        
        start_time = time.time()
        
        # Step 1: Modifications
        logger.info("\n--- Step 1: Modifications ---")
        modification_results = self.run_modifications_only()
        
        # Step 2: Simulations
        logger.info("\n--- Step 2: Simulations ---")
        simulation_results = self.run_simulations()
        
        # Step 3: Parsing
        logger.info("\n--- Step 3: Parsing ---")
        parsed_results = self.parse_results(simulation_results)
        
        # Step 4: Analysis
        logger.info("\n--- Step 4: Analysis ---")
        comparison_results = self.compare_with_baseline(parsed_results)
        
        total_time = time.time() - start_time
        
        logger.info("="*60)
        logger.info("PIPELINE COMPLETE")
        logger.info(f"Total execution time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        logger.info("="*60)
        
        # Generate final summary
        summary = {
            'job_id': self.job_id,
            'timestamp': datetime.now().isoformat(),
            'total_time_seconds': total_time,
            'steps_completed': {
                'modifications': len(modification_results) if modification_results else 0,
                'simulations': len(simulation_results) if simulation_results else 0,
                'parsed_results': len(parsed_results) if parsed_results else 0,
                'comparisons': len(comparison_results) if comparison_results else 0
            },
            'output_directories': {
                'modified_idfs': str(self.modified_idfs_dir),
                'simulation_results': str(self.simulation_results_dir),
                'analysis': str(self.analysis_dir)
            }
        }
        
        summary_path = self.job_output_dir / f"pipeline_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Pipeline summary saved to: {summary_path}")
        
        return {
            'modification_results': modification_results,
            'simulation_results': simulation_results,
            'parsed_results': parsed_results,
            'comparison_results': comparison_results,
            'total_time': total_time
        }
        
    def run_from_step(self, start_step='modifications'):
        """Run pipeline from a specific step"""
        steps = ['modifications', 'simulations', 'parsing', 'analysis']
        
        if start_step not in steps:
            raise ValueError(f"Invalid step: {start_step}. Must be one of {steps}")
        
        start_index = steps.index(start_step)
        
        results = {}
        
        for i, step in enumerate(steps[start_index:], start_index):
            logger.info(f"\n--- Running: {step} ---")
            
            if step == 'modifications':
                results['modifications'] = self.run_modifications_only()
            elif step == 'simulations':
                results['simulations'] = self.run_simulations()
            elif step == 'parsing':
                results['parsing'] = self.parse_results(results.get('simulations'))
            elif step == 'analysis':
                results['analysis'] = self.compare_with_baseline(results.get('parsing'))
        
        return results


def main():
    """Main function for command line execution"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Enhanced standalone runner for modifications, simulations, and analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test modifications only (safest to start)
  python enhanced_standalone_runner.py 650e5027-2c43-4a30-b588-5e4d72c0ac23 --modifications-only
  
  # Test with simulations
  python enhanced_standalone_runner.py 650e5027-2c43-4a30-b588-5e4d72c0ac23 --with-simulations
  
  # Full pipeline
  python enhanced_standalone_runner.py 650e5027-2c43-4a30-b588-5e4d72c0ac23 --full-pipeline
  
  # Start from specific step
  python enhanced_standalone_runner.py 650e5027-2c43-4a30-b588-5e4d72c0ac23 --from-step parsing
  
  # With custom config path
  python enhanced_standalone_runner.py 650e5027 --config D:\\Documents\\daily\\E_Plus_2040_py\\combined.json --full-pipeline
        """
    )
    
    parser.add_argument('job_id', help='Job ID from previous run')
    parser.add_argument('--config', help='Path to combined.json configuration file')
    parser.add_argument('--output-dir', help='Base output directory')
    
    # Execution modes
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--modifications-only', action='store_true', 
                           help='Run only modifications')
    mode_group.add_argument('--with-simulations', action='store_true',
                           help='Run modifications and simulations')
    mode_group.add_argument('--full-pipeline', action='store_true',
                           help='Run complete pipeline')
    mode_group.add_argument('--from-step', choices=['modifications', 'simulations', 'parsing', 'analysis'],
                           help='Start pipeline from specific step')
    
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--num-processes', type=int, help='Number of parallel processes for simulations')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize runner
        runner = EnhancedStandaloneRunner(
            job_id=args.job_id,
            config_path=args.config,
            base_output_dir=args.output_dir
        )
        
        # Override number of processes if specified
        if args.num_processes:
            runner.simulation_cfg['num_processes'] = args.num_processes
        
        # Execute based on mode
        if args.modifications_only:
            runner.run_modifications_only()
            
        elif args.with_simulations:
            runner.run_modifications_only()
            runner.run_simulations()
            
        elif args.full_pipeline:
            runner.run_full_pipeline()
            
        elif args.from_step:
            runner.run_from_step(args.from_step)
        
        logger.info("\nExecution completed successfully!")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Check if running with command line args
    if len(sys.argv) > 1:
        main()
    else:
        # For direct testing - modify these values as needed
        TEST_JOB_ID = "650e5027-2c43-4a30-b588-5e4d72c0ac23"
        TEST_CONFIG = r"D:\Documents\daily\E_Plus_2040_py\combined.json"
        
        logger.info("Running in test mode...")
        
        runner = EnhancedStandaloneRunner(
            job_id=TEST_JOB_ID,
            config_path=TEST_CONFIG
        )
        
        # Test modifications only first
        runner.run_modifications_only()
        
        # Or test full pipeline
        # runner.run_full_pipeline()