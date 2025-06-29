"""
Enhanced IDF Modification with Integrated Simulation Runner

This script modifies IDF files and runs simulations to compare energy performance.
"""

import os
import sys
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd
import time
from typing import Dict, List, Optional, Tuple

# Add project root to Python path
PROJECT_ROOT = Path(r"D:\Documents\daily\E_Plus_2040_py")
sys.path.insert(0, str(PROJECT_ROOT))

# Import required modules
from idf_modification.modification_engine import ModificationEngine
from parserr.idf_parser import EnhancedIDFParser
from epw.run_epw_sims import simulate_all, initialize_idd
from epw.assign_epw_file import assign_epw_for_building_with_overrides

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModificationAndSimulationRunner:
    """Run modifications and simulations together for comparison"""
    
    def __init__(self, config_path=None):
        """Initialize the runner"""
        self.project_root = PROJECT_ROOT
        self.config_path = config_path or PROJECT_ROOT / "combined.json"
        self.config = self._load_config()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = PROJECT_ROOT / "modification_simulation_tests" / self.timestamp
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default paths
        self.iddfile = PROJECT_ROOT / "EnergyPlus" / "Energy+.idd"
        self.epw_dir = PROJECT_ROOT / "data" / "weather"
        
        # Results storage
        self.simulation_results = {}
        self.modification_results = {}
        
        logger.info(f"Initialized ModificationAndSimulationRunner")
        logger.info(f"Output directory: {self.output_dir}")
        
    def _load_config(self):
        """Load configuration"""
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except:
            return {"modification": {}}
    
    def run_baseline_simulation(self, idf_path: Path, building_id: str) -> Dict[str, Any]:
        """Run simulation on original IDF file"""
        logger.info(f"\n=== Running baseline simulation for {building_id} ===")
        
        baseline_dir = self.output_dir / "baseline"
        baseline_dir.mkdir(exist_ok=True)
        
        # Copy original IDF to baseline directory
        baseline_idf = baseline_dir / f"{building_id}_baseline.idf"
        shutil.copy2(idf_path, baseline_idf)
        
        # Run simulation
        sim_results = self._run_single_simulation(
            idf_path=baseline_idf,
            output_dir=baseline_dir / "simulation",
            building_id=f"{building_id}_baseline"
        )
        
        if sim_results['success']:
            # Parse results
            energy_results = self._parse_simulation_results(
                sim_results['output_dir'], 
                f"{building_id}_baseline"
            )
            sim_results['energy_results'] = energy_results
            
        self.simulation_results[f"{building_id}_baseline"] = sim_results
        return sim_results
    
    def run_modification_scenarios(self, 
                                 idf_path: Path, 
                                 building_id: str,
                                 scenarios: Dict[str, Dict] = None) -> Dict[str, Any]:
        """Run multiple modification scenarios"""
        
        if scenarios is None:
            scenarios = self._get_default_scenarios()
        
        results = {}
        
        for scenario_name, scenario_config in scenarios.items():
            logger.info(f"\n=== Processing scenario: {scenario_name} ===")
            
            # Create scenario directory
            scenario_dir = self.output_dir / "scenarios" / scenario_name
            scenario_dir.mkdir(parents=True, exist_ok=True)
            
            # Apply modifications
            mod_result = self._apply_modifications(
                idf_path=idf_path,
                building_id=building_id,
                variant_id=scenario_name,
                categories=scenario_config,
                output_dir=scenario_dir
            )
            
            if mod_result['success']:
                # Run simulation on modified IDF
                sim_result = self._run_single_simulation(
                    idf_path=Path(mod_result['output_file']),
                    output_dir=scenario_dir / "simulation",
                    building_id=f"{building_id}_{scenario_name}"
                )
                
                if sim_result['success']:
                    # Parse results
                    energy_results = self._parse_simulation_results(
                        sim_result['output_dir'],
                        f"{building_id}_{scenario_name}"
                    )
                    sim_result['energy_results'] = energy_results
                
                results[scenario_name] = {
                    'modification': mod_result,
                    'simulation': sim_result
                }
            else:
                results[scenario_name] = {
                    'modification': mod_result,
                    'simulation': {'success': False, 'error': 'Modification failed'}
                }
            
            self.modification_results[f"{building_id}_{scenario_name}"] = mod_result
            self.simulation_results[f"{building_id}_{scenario_name}"] = sim_result
        
        return results
    
    def _apply_modifications(self, 
                           idf_path: Path,
                           building_id: str,
                           variant_id: str,
                           categories: Dict,
                           output_dir: Path) -> Dict[str, Any]:
        """Apply modifications to IDF"""
        
        # Initialize modification engine
        engine = ModificationEngine(
            project_dir=output_dir,
            config={"categories_to_modify": categories},
            output_path=output_dir / "modified_idfs"
        )
        
        try:
            result = engine.modify_building(
                building_id=building_id,
                idf_path=idf_path,
                parameter_values=categories,
                variant_id=variant_id
            )
            
            # Log modification summary
            if result['success']:
                logger.info(f"✓ Modifications applied: {len(result['modifications'])}")
                by_cat = {}
                for mod in result['modifications']:
                    cat = mod.get('category', 'unknown')
                    by_cat[cat] = by_cat.get(cat, 0) + 1
                for cat, count in by_cat.items():
                    logger.info(f"  - {cat}: {count} modifications")
            
            return result
            
        except Exception as e:
            logger.error(f"Modification failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'modifications': []
            }
    
    def _run_single_simulation(self, 
                             idf_path: Path,
                             output_dir: Path,
                             building_id: str) -> Dict[str, Any]:
        """Run a single simulation"""
        
        logger.info(f"Running simulation for {building_id}")
        start_time = time.time()
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get EPW file
        epw_path = self._get_epw_file()
        if not epw_path:
            return {
                'success': False,
                'error': 'No EPW file found',
                'elapsed_time': 0
            }
        
        # Create DataFrame for simulation
        df_buildings = pd.DataFrame([{
            'idf_name': idf_path.name,
            'ogc_fid': building_id,
            'lat': 52.0,
            'lon': 4.0,
            'desired_climate_year': 2023
        }])
        
        try:
            # Initialize IDD
            initialize_idd(str(self.iddfile))
            
            # Run simulation
            simulate_all(
                df_buildings=df_buildings,
                idf_directory=str(idf_path.parent),
                iddfile=str(self.iddfile),
                base_output_dir=str(output_dir),
                user_config_epw=[],
                assigned_epw_log={},
                num_workers=1
            )
            
            elapsed = time.time() - start_time
            
            return {
                'success': True,
                'output_dir': str(output_dir / "2023"),  # Year subdirectory
                'elapsed_time': elapsed,
                'epw_file': str(epw_path)
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Simulation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'elapsed_time': elapsed
            }
    
    def _get_epw_file(self) -> Optional[Path]:
        """Get EPW file for simulation"""
        # Look for EPW files
        epw_files = list(self.epw_dir.glob("*.epw"))
        if epw_files:
            # Prefer 2023 or current year EPW
            for epw in epw_files:
                if "2023" in epw.name or "current" in epw.name.lower():
                    return epw
            # Otherwise use first available
            return epw_files[0]
        return None
    
    def _parse_simulation_results(self, output_dir: str, building_id: str) -> Dict[str, float]:
        """Parse simulation results to get energy consumption"""
        
        results = {
            'total_energy': 0,
            'heating': 0,
            'cooling': 0,
            'lighting': 0,
            'equipment': 0
        }
        
        # Look for results files
        results_dir = Path(output_dir)
        
        # Try to find the meter output file
        meter_files = list(results_dir.glob("*Meter.csv"))
        if meter_files:
            try:
                # Read the meter file
                df = pd.read_csv(meter_files[0])
                
                # Sum annual values (simplified - you might need to adjust based on actual output)
                if 'Electricity:Facility [J](Hourly)' in df.columns:
                    results['total_energy'] = df['Electricity:Facility [J](Hourly)'].sum() / 3.6e9  # Convert to kWh
                if 'Heating:EnergyTransfer [J](Hourly)' in df.columns:
                    results['heating'] = df['Heating:EnergyTransfer [J](Hourly)'].sum() / 3.6e9
                if 'Cooling:EnergyTransfer [J](Hourly)' in df.columns:
                    results['cooling'] = df['Cooling:EnergyTransfer [J](Hourly)'].sum() / 3.6e9
                if 'InteriorLights:Electricity [J](Hourly)' in df.columns:
                    results['lighting'] = df['InteriorLights:Electricity [J](Hourly)'].sum() / 3.6e9
                if 'InteriorEquipment:Electricity [J](Hourly)' in df.columns:
                    results['equipment'] = df['InteriorEquipment:Electricity [J](Hourly)'].sum() / 3.6e9
                    
                logger.info(f"Parsed energy results for {building_id}:")
                logger.info(f"  Total: {results['total_energy']:.0f} kWh")
                logger.info(f"  Heating: {results['heating']:.0f} kWh")
                logger.info(f"  Cooling: {results['cooling']:.0f} kWh")
                
            except Exception as e:
                logger.error(f"Error parsing results: {e}")
        else:
            logger.warning(f"No meter file found in {output_dir}")
        
        return results
    
    def _get_default_scenarios(self) -> Dict[str, Dict]:
        """Get default modification scenarios"""
        return {
            "lighting_retrofit": {
                "lighting": {
                    "enabled": True,
                    "strategy": "led_retrofit",
                    "parameters": {
                        "watts_per_area": {"method": "percentage", "change": -50}
                    }
                }
            },
            "hvac_upgrade": {
                "hvac": {
                    "enabled": True,
                    "strategy": "high_efficiency",
                    "parameters": {
                        "cooling_cop": {"method": "percentage", "change": 30},
                        "heating_efficiency": {"method": "percentage", "change": 20}
                    }
                }
            },
            "envelope_improvement": {
                "materials": {
                    "enabled": True,
                    "strategy": "insulation_upgrade",
                    "parameters": {
                        "conductivity": {"method": "percentage", "change": -30}
                    }
                },
                "infiltration": {
                    "enabled": True,
                    "strategy": "air_sealing",
                    "parameters": {
                        "air_changes_per_hour": {"method": "percentage", "change": -40}
                    }
                }
            },
            "comprehensive": {
                "hvac": {
                    "enabled": True,
                    "parameters": {
                        "cooling_cop": {"method": "percentage", "change": 25}
                    }
                },
                "lighting": {
                    "enabled": True,
                    "parameters": {
                        "watts_per_area": {"method": "percentage", "change": -40}
                    }
                },
                "equipment": {
                    "enabled": True,
                    "parameters": {
                        "watts_per_area": {"method": "percentage", "change": -20}
                    }
                },
                "infiltration": {
                    "enabled": True,
                    "parameters": {
                        "air_changes_per_hour": {"method": "percentage", "change": -30}
                    }
                }
            }
        }
    
    def compare_results(self, baseline_id: str, scenario_ids: List[str]) -> pd.DataFrame:
        """Compare simulation results between baseline and scenarios"""
        
        comparison_data = []
        
        # Get baseline results
        baseline_key = f"{baseline_id}_baseline"
        if baseline_key not in self.simulation_results:
            logger.error(f"No baseline results found for {baseline_id}")
            return pd.DataFrame()
        
        baseline = self.simulation_results[baseline_key]
        if not baseline['success'] or 'energy_results' not in baseline:
            logger.error("Baseline simulation failed or no energy results")
            return pd.DataFrame()
        
        baseline_energy = baseline['energy_results']
        
        # Add baseline to comparison
        comparison_data.append({
            'scenario': 'baseline',
            'total_energy_kwh': baseline_energy['total_energy'],
            'heating_kwh': baseline_energy['heating'],
            'cooling_kwh': baseline_energy['cooling'],
            'lighting_kwh': baseline_energy['lighting'],
            'equipment_kwh': baseline_energy['equipment'],
            'savings_pct': 0,
            'heating_savings_pct': 0,
            'cooling_savings_pct': 0,
            'modifications': 0,
            'simulation_time': baseline['elapsed_time']
        })
        
        # Compare each scenario
        for scenario_id in scenario_ids:
            key = f"{baseline_id}_{scenario_id}"
            
            if key in self.simulation_results:
                sim_result = self.simulation_results[key]
                mod_result = self.modification_results.get(key, {})
                
                if sim_result.get('success') and 'energy_results' in sim_result:
                    energy = sim_result['energy_results']
                    
                    # Calculate savings
                    total_savings = ((baseline_energy['total_energy'] - energy['total_energy']) / 
                                   baseline_energy['total_energy'] * 100) if baseline_energy['total_energy'] > 0 else 0
                    
                    heating_savings = ((baseline_energy['heating'] - energy['heating']) / 
                                     baseline_energy['heating'] * 100) if baseline_energy['heating'] > 0 else 0
                    
                    cooling_savings = ((baseline_energy['cooling'] - energy['cooling']) / 
                                     baseline_energy['cooling'] * 100) if baseline_energy['cooling'] > 0 else 0
                    
                    comparison_data.append({
                        'scenario': scenario_id,
                        'total_energy_kwh': energy['total_energy'],
                        'heating_kwh': energy['heating'],
                        'cooling_kwh': energy['cooling'],
                        'lighting_kwh': energy['lighting'],
                        'equipment_kwh': energy['equipment'],
                        'savings_pct': total_savings,
                        'heating_savings_pct': heating_savings,
                        'cooling_savings_pct': cooling_savings,
                        'modifications': len(mod_result.get('modifications', [])),
                        'simulation_time': sim_result['elapsed_time']
                    })
                else:
                    comparison_data.append({
                        'scenario': scenario_id,
                        'total_energy_kwh': None,
                        'error': sim_result.get('error', 'Simulation failed')
                    })
        
        df = pd.DataFrame(comparison_data)
        
        # Save comparison
        comparison_path = self.output_dir / f"energy_comparison_{baseline_id}.csv"
        df.to_csv(comparison_path, index=False)
        logger.info(f"\nEnergy comparison saved to: {comparison_path}")
        
        return df
    
    def generate_report(self, building_id: str) -> Path:
        """Generate comprehensive report"""
        
        report_path = self.output_dir / f"modification_simulation_report_{building_id}.html"
        
        # Get comparison data
        scenarios = list(self._get_default_scenarios().keys())
        comparison_df = self.compare_results(building_id, scenarios)
        
        html_content = f"""
        <html>
        <head>
            <title>Modification and Simulation Report - Building {building_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .positive {{ color: green; font-weight: bold; }}
                .negative {{ color: red; }}
                .summary {{ background-color: #e7f3fe; padding: 15px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>IDF Modification and Simulation Report</h1>
            <p><strong>Building ID:</strong> {building_id}</p>
            <p><strong>Test Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <h2>Summary</h2>
                <p>Tested {len(scenarios)} modification scenarios with energy simulations.</p>
            </div>
            
            <h2>Energy Comparison Results</h2>
        """
        
        if not comparison_df.empty:
            # Convert DataFrame to HTML table
            html_table = comparison_df.to_html(index=False, escape=False)
            
            # Add formatting to savings columns
            html_table = html_table.replace('<td>', '<td>')
            # This is simplified - in production you'd want more sophisticated formatting
            
            html_content += html_table
        else:
            html_content += "<p>No comparison data available.</p>"
        
        html_content += """
            <h2>Modification Details</h2>
            <ul>
        """
        
        # Add modification summaries
        for scenario in scenarios:
            key = f"{building_id}_{scenario}"
            if key in self.modification_results:
                mod_result = self.modification_results[key]
                if mod_result.get('success'):
                    html_content += f"""
                    <li><strong>{scenario}:</strong> {len(mod_result.get('modifications', []))} modifications applied</li>
                    """
        
        html_content += """
            </ul>
        </body>
        </html>
        """
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        logger.info(f"\nReport generated: {report_path}")
        return report_path


def main():
    """Main function for testing modifications with simulations"""
    
    # Configuration
    IDF_PATH = r"D:\Documents\daily\E_Plus_2040_py\output\b0fb6596-3303-4494-bc5f-5741a4db5e11\output_IDFs\building_4136733.idf"
    BUILDING_ID = "4136733"
    
    # Initialize runner
    runner = ModificationAndSimulationRunner()
    
    logger.info("\n" + "="*80)
    logger.info("MODIFICATION AND SIMULATION TEST")
    logger.info("="*80)
    
    # Step 1: Run baseline simulation
    logger.info("\n[Step 1/3] Running baseline simulation...")
    baseline_result = runner.run_baseline_simulation(Path(IDF_PATH), BUILDING_ID)
    
    if not baseline_result['success']:
        logger.error("Baseline simulation failed. Exiting.")
        return
    
    # Step 2: Run modification scenarios with simulations
    logger.info("\n[Step 2/3] Running modification scenarios...")
    scenario_results = runner.run_modification_scenarios(Path(IDF_PATH), BUILDING_ID)
    
    # Step 3: Compare results and generate report
    logger.info("\n[Step 3/3] Comparing results...")
    comparison_df = runner.compare_results(BUILDING_ID, list(scenario_results.keys()))
    
    if not comparison_df.empty:
        print("\n" + "="*80)
        print("ENERGY COMPARISON SUMMARY")
        print("="*80)
        print(comparison_df.to_string(index=False))
        
        # Highlight best performing scenario
        if 'savings_pct' in comparison_df.columns:
            best_scenario = comparison_df.loc[comparison_df['savings_pct'].idxmax()]
            if best_scenario['savings_pct'] > 0:
                print(f"\n✓ Best performing scenario: {best_scenario['scenario']}")
                print(f"  Energy savings: {best_scenario['savings_pct']:.1f}%")
                print(f"  Modifications applied: {int(best_scenario['modifications'])}")
    
    # Generate report
    report_path = runner.generate_report(BUILDING_ID)
    
    print(f"\n" + "="*80)
    print(f"Test completed. All outputs saved to:")
    print(f"{runner.output_dir}")
    print("="*80)


if __name__ == "__main__":
    main()