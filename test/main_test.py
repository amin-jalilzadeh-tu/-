# test/main_test.py - Main Test Script for Standalone Modification and Simulation

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
import time
import argparse

# Import test modules
from modifier import StandaloneModifier
from run_simulation import StandaloneSimulator

class ModificationTestRunner:
    """Main test runner for modification and simulation workflow"""
    
    def __init__(self, config_path):
        """Initialize test runner
        
        Args:
            config_path: Path to test configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Initialize output_dir before logger
        self.output_dir = Path(self.config['paths'].get('output_dir', './test_output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Now we can setup logger
        self.logger = self._setup_logger()
        
        # Initialize components
        self.modifier = None
        self.simulator = None
        
        # Results storage
        self.results = {
            'test_name': self.config['test_name'],
            'start_time': datetime.now().isoformat(),
            'scenarios': {}
        }
        
    def _load_config(self):
        """Load test configuration"""
        if not self.config_path.exists():
            print(f"Error: Configuration file not found: {self.config_path}")
            print("Creating default configuration...")
            # Create a default config
            default_config = {
                "test_name": "Default Test Configuration",
                "paths": {
                    "output_dir": "./test_output"
                },
                "test_scenarios": [{
                    "name": "baseline",
                    "description": "Baseline - no modifications",
                    "modifications": {}
                }],
                "simulation_options": {
                    "run_baseline": True,
                    "run_modified": True,
                    "compare_results": True
                }
            }
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
            
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            # Validate required fields
            if 'paths' not in config:
                config['paths'] = {"output_dir": "./test_output"}
            if 'output_dir' not in config['paths']:
                config['paths']['output_dir'] = "./test_output"
                
            return config
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    def _setup_logger(self):
        """Setup logging"""
        logger = logging.getLogger('ModificationTestRunner')
        logger.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handler
        log_dir = self.output_dir / 'logs'
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_dir / f'test_run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        return logger
    
    def run_tests(self):
        """Run all test scenarios"""
        self.logger.info(f"Starting test run: {self.config['test_name']}")
        self.logger.info(f"Test IDF: {self.config['paths']['test_idf']}")
        
        # Check if test IDF exists
        test_idf = Path(self.config['paths']['test_idf'])
        if not test_idf.exists():
            self.logger.error(f"Test IDF not found: {test_idf}")
            return False
        
        # Initialize simulator
        self.simulator = StandaloneSimulator(
            self.config['paths']['idd_file'],
            self.config['paths']['epw_file']
        )
        
        # Run baseline if requested
        if self.config['simulation_options']['run_baseline']:
            self.logger.info("=" * 60)
            self.logger.info("Running baseline simulation...")
            self._run_baseline()
        
        # Run each test scenario
        for scenario in self.config['test_scenarios']:
            if scenario['name'] != 'baseline' or not self.config['simulation_options']['run_baseline']:
                self.logger.info("=" * 60)
                self.logger.info(f"Running scenario: {scenario['name']}")
                self._run_scenario(scenario)
        
        # Compare results if requested
        if self.config['simulation_options']['compare_results']:
            self.logger.info("=" * 60)
            self.logger.info("Comparing results...")
            self._compare_all_results()
        
        # Save final results
        self._save_results()
        
        self.logger.info("Test run complete!")
        return True
    
    def _run_baseline(self):
        """Run baseline simulation"""
        start_time = time.time()
        
        # Run simulation on original IDF
        sim_results = self.simulator.simulate_idf(
            self.config['paths']['test_idf'],
            building_id="4136733",
            variant_id="baseline"
        )
        
        elapsed_time = time.time() - start_time
        
        self.results['scenarios']['baseline'] = {
            'description': 'Baseline - no modifications',
            'modification_results': None,
            'simulation_results': sim_results,
            'elapsed_time': elapsed_time
        }
        
        if sim_results['success']:
            self.logger.info(f"Baseline simulation successful (took {elapsed_time:.1f}s)")
        else:
            self.logger.error("Baseline simulation failed")
    
    def _run_scenario(self, scenario):
        """Run a single test scenario"""
        start_time = time.time()
        scenario_name = scenario['name']
        
        # Skip baseline if already run
        if scenario_name == 'baseline' and 'baseline' in self.results['scenarios']:
            return
        
        # Create scenario-specific modifier with the modifications
        scenario_config = self.config.copy()
        scenario_config['modification']['categories_to_modify'] = scenario['modifications']
        
        # Initialize modifier for this scenario
        modifier = StandaloneModifier()
        modifier.config = scenario_config
        
        # Apply modifications
        self.logger.info(f"Applying modifications for {scenario_name}...")
        mod_results = modifier.modify_idf(
            self.config['paths']['test_idf'],
            building_id="4136733",
            variant_id=scenario_name
        )
        
        sim_results = None
        if mod_results['success'] and self.config['simulation_options']['run_modified']:
            # Run simulation on modified IDF
            self.logger.info(f"Running simulation for {scenario_name}...")
            sim_results = self.simulator.simulate_idf(
                mod_results['output_file'],
                building_id="4136733",
                variant_id=scenario_name
            )
        
        elapsed_time = time.time() - start_time
        
        # Store results
        self.results['scenarios'][scenario_name] = {
            'description': scenario['description'],
            'modification_results': mod_results,
            'simulation_results': sim_results,
            'elapsed_time': elapsed_time
        }
        
        if mod_results['success']:
            self.logger.info(f"Scenario {scenario_name} complete (took {elapsed_time:.1f}s)")
            self.logger.info(f"  - Modifications: {len(mod_results['modifications'])}")
            if sim_results and sim_results['success']:
                self.logger.info(f"  - Simulation: Success")
        else:
            self.logger.error(f"Scenario {scenario_name} failed")
    
    def _compare_all_results(self):
        """Compare all scenario results against baseline"""
        if 'baseline' not in self.results['scenarios']:
            self.logger.warning("No baseline results to compare against")
            return
        
        baseline = self.results['scenarios']['baseline']
        if not baseline['simulation_results'] or not baseline['simulation_results']['success']:
            self.logger.warning("Baseline simulation failed - cannot compare")
            return
        
        baseline_dir = Path(baseline['simulation_results']['output_dir'])
        
        comparisons = {}
        for scenario_name, scenario_data in self.results['scenarios'].items():
            if scenario_name == 'baseline':
                continue
                
            if scenario_data['simulation_results'] and scenario_data['simulation_results']['success']:
                self.logger.info(f"Comparing {scenario_name} to baseline...")
                modified_dir = Path(scenario_data['simulation_results']['output_dir'])
                
                comparison = self.simulator.compare_results(baseline_dir, modified_dir)
                comparisons[scenario_name] = comparison
                
                # Log summary
                self._log_comparison_summary(scenario_name, comparison)
        
        self.results['comparisons'] = comparisons
    
    def _log_comparison_summary(self, scenario_name, comparison):
        """Log comparison summary"""
        self.logger.info(f"\nComparison summary for {scenario_name}:")
        
        total_savings = {}
        for file_name, file_comp in comparison.items():
            for meter, values in file_comp.items():
                if 'pct_change' in values:
                    # Extract meter type
                    meter_type = meter.split('[')[0].strip()
                    if meter_type not in total_savings:
                        total_savings[meter_type] = []
                    total_savings[meter_type].append(values['pct_change'])
        
        for meter_type, savings in total_savings.items():
            avg_savings = sum(savings) / len(savings)
            self.logger.info(f"  - {meter_type}: {avg_savings:.1f}% change")
    
    def _save_results(self):
        """Save all test results"""
        self.results['end_time'] = datetime.now().isoformat()
        
        # Save JSON results
        results_path = self.output_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        self.logger.info(f"Results saved to: {results_path}")
        
        # Generate summary report
        self._generate_summary_report()
    
    def _generate_summary_report(self):
        """Generate a summary report"""
        report_path = self.output_dir / f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_path, 'w') as f:
            f.write(f"Test Summary Report\n")
            f.write(f"==================\n\n")
            f.write(f"Test Name: {self.config['test_name']}\n")
            f.write(f"Test IDF: {self.config['paths']['test_idf']}\n")
            f.write(f"Start Time: {self.results['start_time']}\n")
            f.write(f"End Time: {self.results['end_time']}\n\n")
            
            f.write(f"Scenarios Run:\n")
            f.write(f"--------------\n")
            
            for scenario_name, scenario_data in self.results['scenarios'].items():
                f.write(f"\n{scenario_name}:\n")
                f.write(f"  Description: {scenario_data['description']}\n")
                f.write(f"  Elapsed Time: {scenario_data['elapsed_time']:.1f}s\n")
                
                if scenario_data['modification_results']:
                    mod_results = scenario_data['modification_results']
                    f.write(f"  Modifications: {len(mod_results['modifications'])}\n")
                    f.write(f"  Modification Success: {mod_results['success']}\n")
                
                if scenario_data['simulation_results']:
                    sim_results = scenario_data['simulation_results']
                    f.write(f"  Simulation Success: {sim_results['success']}\n")
            
            if 'comparisons' in self.results:
                f.write(f"\n\nEnergy Savings Summary:\n")
                f.write(f"----------------------\n")
                
                for scenario_name, comparison in self.results['comparisons'].items():
                    f.write(f"\n{scenario_name}:\n")
                    
                    # Calculate average savings
                    all_savings = []
                    for file_comp in comparison.values():
                        for meter_values in file_comp.values():
                            if 'pct_change' in meter_values:
                                all_savings.append(meter_values['pct_change'])
                    
                    if all_savings:
                        avg_savings = sum(all_savings) / len(all_savings)
                        f.write(f"  Average Energy Change: {avg_savings:.1f}%\n")
        
        self.logger.info(f"Summary report saved to: {report_path}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run IDF modification and simulation tests')
    parser.add_argument('--config', type=str, default='test_config.json',
                        help='Path to test configuration file')
    parser.add_argument('--scenarios', type=str, nargs='+',
                        help='Specific scenarios to run (default: all)')
    args = parser.parse_args()
    
    # Run tests
    runner = ModificationTestRunner(args.config)
    
    # Filter scenarios if specified
    if args.scenarios:
        runner.config['test_scenarios'] = [
            s for s in runner.config['test_scenarios'] 
            if s['name'] in args.scenarios
        ]
    
    success = runner.run_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())