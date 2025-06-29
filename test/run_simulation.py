# test/run_simulation.py - Standalone Simulation Runner

import sys
import os
import logging
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add parent directories to path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# Import simulation module
from eppy.modeleditor import IDF
from epw.run_epw_sims import run_simulation, initialize_idd

class StandaloneSimulator:
    """Standalone simulator for testing modified IDFs"""
    
    def __init__(self, idd_path, epw_path):
        """Initialize the simulator
        
        Args:
            idd_path: Path to IDD file
            epw_path: Path to EPW weather file
        """
        self.idd_path = Path(idd_path)
        self.epw_path = Path(epw_path)
        self.logger = self._setup_logger()
        self.output_dir = Path('./simulation_results')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize IDD
        self._initialize_idd()
        
    def _setup_logger(self):
        """Setup logging"""
        logger = logging.getLogger('StandaloneSimulator')
        logger.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handler
        log_dir = Path('./logs')
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_dir / f'simulation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        return logger
    
    def _initialize_idd(self):
        """Initialize EnergyPlus IDD"""
        try:
            initialize_idd(str(self.idd_path))
            self.logger.info(f"IDD initialized: {self.idd_path}")
        except Exception as e:
            if "IDD file is set" in str(e):
                self.logger.info("IDD already initialized")
            else:
                raise
    
    def simulate_idf(self, idf_path, building_id=None, variant_id=None):
        """Run simulation on a single IDF
        
        Args:
            idf_path: Path to IDF file
            building_id: Building identifier
            variant_id: Variant identifier
            
        Returns:
            Dict with simulation results
        """
        idf_path = Path(idf_path)
        if not idf_path.exists():
            raise FileNotFoundError(f"IDF file not found: {idf_path}")
        
        if not building_id:
            building_id = idf_path.stem
        
        # Create output directory for this simulation
        sim_output_dir = self.output_dir / f"{building_id}_{variant_id or 'default'}"
        sim_output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Simulating IDF: {idf_path}")
        self.logger.info(f"Output directory: {sim_output_dir}")
        
        try:
            # Prepare simulation arguments
            args = (
                str(idf_path),
                str(self.epw_path),
                str(self.idd_path),
                str(sim_output_dir),
                0,  # building index
                building_id
            )
            
            # Run simulation
            success, message = run_simulation(args)
            
            if success:
                self.logger.info(f"Simulation successful: {message}")
                
                # Check for output files
                results = self._check_outputs(sim_output_dir, building_id)
                
                return {
                    'success': True,
                    'message': message,
                    'output_dir': str(sim_output_dir),
                    'results': results
                }
            else:
                self.logger.error(f"Simulation failed: {message}")
                return {
                    'success': False,
                    'message': message,
                    'output_dir': str(sim_output_dir),
                    'results': {}
                }
                
        except Exception as e:
            self.logger.error(f"Error during simulation: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return {
                'success': False,
                'message': str(e),
                'output_dir': str(sim_output_dir),
                'results': {}
            }
    
    def _check_outputs(self, output_dir, building_id):
        """Check simulation output files"""
        output_dir = Path(output_dir)
        results = {
            'csv_files': [],
            'sql_file': None,
            'err_file': None,
            'html_file': None
        }
        
        # Look for output files
        for file in output_dir.iterdir():
            if file.suffix == '.csv':
                results['csv_files'].append(str(file))
            elif file.suffix == '.sql':
                results['sql_file'] = str(file)
            elif file.suffix == '.err':
                results['err_file'] = str(file)
                # Check for errors
                self._check_err_file(file)
            elif file.suffix == '.html':
                results['html_file'] = str(file)
        
        return results
    
    def _check_err_file(self, err_file):
        """Check EnergyPlus error file for issues"""
        with open(err_file, 'r') as f:
            content = f.read()
            
        # Check for severe errors
        if "** Severe  **" in content:
            self.logger.warning("Severe errors found in simulation")
            # Extract severe errors
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "** Severe  **" in line:
                    self.logger.warning(f"Severe error: {line}")
                    # Show next few lines for context
                    for j in range(1, min(3, len(lines) - i)):
                        if lines[i + j].strip():
                            self.logger.warning(f"  {lines[i + j]}")
        
        # Check for fatal errors
        if "** Fatal  **" in content:
            self.logger.error("Fatal errors found in simulation")
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "** Fatal  **" in line:
                    self.logger.error(f"Fatal error: {line}")
                    for j in range(1, min(3, len(lines) - i)):
                        if lines[i + j].strip():
                            self.logger.error(f"  {lines[i + j]}")
    
    def simulate_batch(self, idf_files, parallel=False, num_workers=1):
        """Simulate multiple IDF files
        
        Args:
            idf_files: List of IDF file paths or list of dicts with 'idf_path', 'building_id', 'variant_id'
            parallel: Whether to run in parallel
            num_workers: Number of parallel workers
            
        Returns:
            List of simulation results
        """
        results = []
        
        # Normalize input
        tasks = []
        for item in idf_files:
            if isinstance(item, dict):
                tasks.append(item)
            else:
                # Assume it's a path
                tasks.append({
                    'idf_path': item,
                    'building_id': Path(item).stem,
                    'variant_id': 'default'
                })
        
        if parallel and num_workers > 1:
            # Parallel execution
            from multiprocessing import Pool
            with Pool(num_workers) as pool:
                results = pool.map(self._simulate_task, tasks)
        else:
            # Sequential execution
            for task in tasks:
                result = self._simulate_task(task)
                results.append(result)
        
        # Summary
        successful = sum(1 for r in results if r['success'])
        self.logger.info(f"Batch simulation complete: {successful}/{len(results)} successful")
        
        return results
    
    def _simulate_task(self, task):
        """Simulate a single task"""
        return self.simulate_idf(
            task['idf_path'],
            task.get('building_id'),
            task.get('variant_id')
        )
    
    def compare_results(self, baseline_dir, modified_dir):
        """Compare baseline and modified simulation results
        
        Args:
            baseline_dir: Directory with baseline results
            modified_dir: Directory with modified results
            
        Returns:
            Dict with comparison results
        """
        baseline_dir = Path(baseline_dir)
        modified_dir = Path(modified_dir)
        
        comparison = {}
        
        # Find CSV files
        baseline_csvs = list(baseline_dir.glob("*.csv"))
        modified_csvs = list(modified_dir.glob("*.csv"))
        
        self.logger.info(f"Comparing {len(baseline_csvs)} baseline vs {len(modified_csvs)} modified CSV files")
        
        # Compare meter files
        for baseline_csv in baseline_csvs:
            if "Meter" in baseline_csv.name:
                modified_csv = modified_dir / baseline_csv.name
                if modified_csv.exists():
                    comp = self._compare_meter_file(baseline_csv, modified_csv)
                    comparison[baseline_csv.name] = comp
        
        return comparison
    
    def _compare_meter_file(self, baseline_csv, modified_csv):
        """Compare two meter CSV files"""
        try:
            # EnergyPlus CSV files have a special format
            # First, find where the actual data starts
            def find_data_start(csv_file):
                with open(csv_file, 'r') as f:
                    for i, line in enumerate(f):
                        if line.strip() and not line.startswith('Program Version'):
                            # Check if this looks like a header line
                            if 'Date/Time' in line or 'DateTime' in line:
                                return i
                return 0
            
            # Find start of data in both files
            base_skip = find_data_start(baseline_csv)
            mod_skip = find_data_start(modified_csv)
            
            # Read CSVs with proper skip
            df_base = pd.read_csv(baseline_csv, skiprows=base_skip)
            df_mod = pd.read_csv(modified_csv, skiprows=mod_skip)
            
            # Clean column names (remove extra spaces)
            df_base.columns = df_base.columns.str.strip()
            df_mod.columns = df_mod.columns.str.strip()
            
            # Find energy columns (containing J for Joules or kWh)
            energy_cols = []
            for col in df_base.columns:
                if col != 'Date/Time' and col != 'DateTime':
                    # Check if it's an energy column
                    if '[J]' in col or '[kWh]' in col or 'Energy' in col:
                        energy_cols.append(col)
            
            comparison = {}
            for col in energy_cols:
                if col in df_mod.columns:
                    try:
                        # Convert to numeric, handling any non-numeric values
                        base_values = pd.to_numeric(df_base[col], errors='coerce')
                        mod_values = pd.to_numeric(df_mod[col], errors='coerce')
                        
                        # Sum, ignoring NaN values
                        base_total = base_values.sum()
                        mod_total = mod_values.sum()
                        
                        if base_total > 0:
                            pct_change = ((mod_total - base_total) / base_total) * 100
                        else:
                            pct_change = 0
                        
                        # Clean up column name for display
                        clean_col = col.replace('[J](Hourly)', '').replace('[kWh](Hourly)', '').strip()
                        
                        comparison[clean_col] = {
                            'baseline': base_total,
                            'modified': mod_total,
                            'change': mod_total - base_total,
                            'pct_change': pct_change
                        }
                    except Exception as e:
                        self.logger.debug(f"Error processing column {col}: {e}")
                        continue
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Error comparing files: {e}")
            # Try alternative approach - look for summary files
            return self._try_alternative_comparison(baseline_csv, modified_csv)


if __name__ == "__main__":
    # Test the simulator
    idd_path = r"D:\Documents\daily\E_Plus_2040_py\EnergyPlus\Energy+.idd"
    epw_path = r"D:\Documents\daily\E_Plus_2040_py\data\weather\2020.epw"
    
    simulator = StandaloneSimulator(idd_path, epw_path)
    
    # Example usage
    test_idf = r"D:\Documents\daily\E_Plus_2040_py\output\b0fb6596-3303-4494-bc5f-5741a4db5e11\output_IDFs\building_4136733.idf"
    
    if Path(test_idf).exists():
        results = simulator.simulate_idf(test_idf, building_id="4136733")
        print(f"Simulation results: {results['success']}")
        if results['success']:
            print(f"Output directory: {results['output_dir']}")
            print(f"CSV files: {len(results['results']['csv_files'])}")
    else:
        print(f"Test IDF not found: {test_idf}")