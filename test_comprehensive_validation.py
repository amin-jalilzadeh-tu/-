#!/usr/bin/env python3
"""
Comprehensive test of all validation functions with fake measured data
Tests all capabilities and documents behavior
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from validation.smart_validation_wrapper import SmartValidationWrapper, run_smart_validation


class FakeMeasuredDataGenerator:
    """Generate realistic fake measured data for testing"""
    
    def __init__(self, building_id='4136733', year=2013):
        self.building_id = building_id
        self.year = year
        self.base_date = datetime(year, 1, 1)
        
        # Realistic base values (J/day scale)
        self.base_electricity = 1.5e10  # 15 GJ/day
        self.base_heating = 8e9  # 8 GJ/day winter
        self.base_cooling = 6e9  # 6 GJ/day summer
        
    def generate_seasonal_factor(self, day_of_year):
        """Generate seasonal variation"""
        # Sinusoidal variation through the year
        return np.sin(2 * np.pi * day_of_year / 365)
    
    def generate_daily_data(self, num_days=365):
        """Generate daily measured data with realistic patterns"""
        dates = [self.base_date + timedelta(days=i) for i in range(num_days)]
        data = []
        
        for i, date in enumerate(dates):
            day_of_year = date.timetuple().tm_yday
            seasonal = self.generate_seasonal_factor(day_of_year)
            
            # Add some random variation
            random_factor = 1 + np.random.normal(0, 0.1)
            
            # Electricity: relatively constant with small seasonal variation
            electricity = self.base_electricity * (1 + 0.2 * seasonal) * random_factor
            
            # Heating: high in winter, low in summer
            heating = max(0, self.base_heating * (1 - seasonal) * random_factor)
            
            # Cooling: high in summer, low in winter
            cooling = max(0, self.base_cooling * (1 + seasonal) * random_factor)
            
            # Temperature: seasonal variation
            temperature = 20 + 10 * seasonal + np.random.normal(0, 2)
            
            data.append({
                'building_id': self.building_id,
                'DateTime': date.strftime('%Y-%m-%d'),
                'Variable': 'Electricity:Facility [J](Hourly)',
                'Value': electricity,
                'Units': 'J'
            })
            
            data.append({
                'building_id': self.building_id,
                'DateTime': date.strftime('%Y-%m-%d'),
                'Variable': 'Zone Air System Sensible Heating Energy',
                'Value': heating,
                'Units': 'J'
            })
            
            data.append({
                'building_id': self.building_id,
                'DateTime': date.strftime('%Y-%m-%d'),
                'Variable': 'Zone Air System Sensible Cooling Energy',
                'Value': cooling,
                'Units': 'J'
            })
            
            data.append({
                'building_id': self.building_id,
                'DateTime': date.strftime('%Y-%m-%d'),
                'Variable': 'Zone Mean Air Temperature',
                'Value': temperature,
                'Units': 'C'
            })
        
        return pd.DataFrame(data)
    
    def generate_hourly_data(self, num_days=30):
        """Generate hourly data for testing frequency alignment"""
        dates = []
        for day in range(num_days):
            base = self.base_date + timedelta(days=day)
            for hour in range(24):
                dates.append(base + timedelta(hours=hour))
        
        data = []
        for date in dates:
            hour = date.hour
            day_of_year = date.timetuple().tm_yday
            seasonal = self.generate_seasonal_factor(day_of_year)
            
            # Hourly variation pattern
            hourly_factor = 0.7 + 0.6 * np.sin(2 * np.pi * (hour - 6) / 24)
            
            # Scale down to hourly values
            electricity = self.base_electricity / 24 * hourly_factor * (1 + 0.2 * seasonal)
            
            data.append({
                'building_id': self.building_id,
                'DateTime': date.strftime('%Y-%m-%d %H:%M:%S'),
                'Variable': 'Electricity:Facility [J](Hourly)',
                'Value': electricity,
                'Units': 'J'
            })
        
        return pd.DataFrame(data)
    
    def generate_monthly_data(self):
        """Generate monthly aggregated data"""
        daily_df = self.generate_daily_data(365)
        daily_df['DateTime'] = pd.to_datetime(daily_df['DateTime'])
        daily_df['Month'] = daily_df['DateTime'].dt.to_period('M')
        
        # Aggregate by month
        monthly_data = []
        for (building_id, variable, month), group in daily_df.groupby(['building_id', 'Variable', 'Month']):
            monthly_data.append({
                'building_id': building_id,
                'DateTime': str(month),
                'Variable': variable,
                'Value': group['Value'].sum() if 'Energy' in variable else group['Value'].mean(),
                'Units': group['Units'].iloc[0]
            })
        
        return pd.DataFrame(monthly_data)
    
    def generate_wide_format_data(self, num_days=31):
        """Generate wide format data (dates as columns)"""
        daily_df = self.generate_daily_data(num_days)
        
        # Pivot to wide format
        pivot_df = daily_df.pivot_table(
            index=['building_id', 'Variable', 'Units'],
            columns='DateTime',
            values='Value'
        ).reset_index()
        
        return pivot_df
    
    def generate_energyplus_format(self, num_days=365):
        """Generate data in EnergyPlus output format"""
        data = []
        dates = [self.base_date + timedelta(days=i) for i in range(num_days)]
        
        for date in dates:
            day_of_year = date.timetuple().tm_yday
            seasonal = self.generate_seasonal_factor(day_of_year)
            
            # Create row with all variables
            row = {
                'Date/Time': date.strftime('%m/%d  %H:%M:%S'),
                'Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)': 20 + 10 * seasonal,
                'Electricity:Facility [J](Hourly)': self.base_electricity * (1 + 0.2 * seasonal),
                'Heating:EnergyTransfer [J](Hourly)': max(0, self.base_heating * (1 - seasonal)),
                'Cooling:EnergyTransfer [J](Hourly)': max(0, self.base_cooling * (1 + seasonal))
            }
            data.append(row)
        
        return pd.DataFrame(data)


class ValidationTester:
    """Test all validation functions and document behavior"""
    
    def __init__(self, output_dir='/mnt/d/Documents/daily/E_Plus_2040_py/validation_test_comprehensive'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}
        
    def test_basic_validation(self):
        """Test basic validation workflow"""
        print("\n" + "="*60)
        print("TEST 1: Basic Validation Workflow")
        print("="*60)
        
        # Generate test data
        generator = FakeMeasuredDataGenerator()
        daily_data = generator.generate_daily_data(31)  # January only
        daily_data.to_csv(self.output_dir / 'measured_data_basic.csv', index=False)
        
        # Run validation
        config = {
            'target_frequency': 'daily',
            'variables_to_validate': ['Electricity', 'Heating', 'Cooling'],
            'show_mappings': True,
            'cvrmse_threshold': 30,
            'nmbe_threshold': 10
        }
        
        results = run_smart_validation(
            parsed_data_path='/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a/parsed_modified_results',
            real_data_path=str(self.output_dir / 'measured_data_basic.csv'),
            config=config,
            output_path=str(self.output_dir / 'test1_basic'),
            validate_variants=False
        )
        
        self.results['test1_basic'] = results
        return results
    
    def test_frequency_alignment(self):
        """Test frequency alignment capabilities"""
        print("\n" + "="*60)
        print("TEST 2: Frequency Alignment")
        print("="*60)
        
        generator = FakeMeasuredDataGenerator()
        
        # Test 1: Hourly to Daily
        hourly_data = generator.generate_hourly_data(31)
        hourly_data.to_csv(self.output_dir / 'measured_data_hourly.csv', index=False)
        
        config = {
            'target_frequency': 'daily',
            'variables_to_validate': ['Electricity'],
            'aggregation': {
                'target_frequency': 'daily',
                'methods': {
                    'energy': 'sum',
                    'temperature': 'mean'
                }
            }
        }
        
        results_hourly = run_smart_validation(
            parsed_data_path='/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a/parsed_modified_results',
            real_data_path=str(self.output_dir / 'measured_data_hourly.csv'),
            config=config,
            output_path=str(self.output_dir / 'test2_hourly_to_daily'),
            validate_variants=False
        )
        
        # Test 2: Monthly aggregation
        monthly_data = generator.generate_monthly_data()
        monthly_data.to_csv(self.output_dir / 'measured_data_monthly.csv', index=False)
        
        config['target_frequency'] = 'monthly'
        
        results_monthly = run_smart_validation(
            parsed_data_path='/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a/parsed_modified_results',
            real_data_path=str(self.output_dir / 'measured_data_monthly.csv'),
            config=config,
            output_path=str(self.output_dir / 'test2_monthly'),
            validate_variants=False
        )
        
        self.results['test2_frequency'] = {
            'hourly_to_daily': results_hourly,
            'monthly': results_monthly
        }
        return results_hourly, results_monthly
    
    def test_variable_mapping(self):
        """Test variable mapping capabilities"""
        print("\n" + "="*60)
        print("TEST 3: Variable Mapping")
        print("="*60)
        
        # Create data with different variable names
        generator = FakeMeasuredDataGenerator()
        data = generator.generate_daily_data(31)
        
        # Rename variables to test mapping
        data['Variable'] = data['Variable'].replace({
            'Electricity:Facility [J](Hourly)': 'Total Electricity Consumption',
            'Zone Air System Sensible Heating Energy': 'Heating Energy Usage',
            'Zone Air System Sensible Cooling Energy': 'Cooling Energy Usage'
        })
        
        data.to_csv(self.output_dir / 'measured_data_renamed.csv', index=False)
        
        config = {
            'target_frequency': 'daily',
            'variables_to_validate': ['Electricity', 'Heating', 'Cooling'],
            'show_mappings': True,
            'variable_mappings': {
                'Total Electricity Consumption': 'Electricity:Facility',
                'Heating Energy Usage': 'Heating:EnergyTransfer',
                'Cooling Energy Usage': 'Cooling:EnergyTransfer'
            }
        }
        
        results = run_smart_validation(
            parsed_data_path='/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a/parsed_modified_results',
            real_data_path=str(self.output_dir / 'measured_data_renamed.csv'),
            config=config,
            output_path=str(self.output_dir / 'test3_mapping'),
            validate_variants=False
        )
        
        self.results['test3_mapping'] = results
        return results
    
    def test_variant_validation(self):
        """Test variant validation capabilities"""
        print("\n" + "="*60)
        print("TEST 4: Variant Validation")
        print("="*60)
        
        generator = FakeMeasuredDataGenerator()
        data = generator.generate_daily_data(31)
        data.to_csv(self.output_dir / 'measured_data_variants.csv', index=False)
        
        config = {
            'target_frequency': 'daily',
            'variables_to_validate': ['Electricity', 'Heating', 'Cooling'],
            'show_mappings': False  # Less verbose for variant testing
        }
        
        results = run_smart_validation(
            parsed_data_path='/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a/parsed_modified_results',
            real_data_path=str(self.output_dir / 'measured_data_variants.csv'),
            config=config,
            output_path=str(self.output_dir / 'test4_variants'),
            validate_variants=True  # Enable variant validation
        )
        
        self.results['test4_variants'] = results
        return results
    
    def test_wide_format(self):
        """Test wide format data handling"""
        print("\n" + "="*60)
        print("TEST 5: Wide Format Data")
        print("="*60)
        
        generator = FakeMeasuredDataGenerator()
        wide_data = generator.generate_wide_format_data(31)
        wide_data.to_csv(self.output_dir / 'measured_data_wide.csv', index=False)
        
        config = {
            'target_frequency': 'daily',
            'variables_to_validate': ['Electricity', 'Heating', 'Cooling'],
            'data_format': 'wide'  # Specify wide format
        }
        
        results = run_smart_validation(
            parsed_data_path='/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a/parsed_modified_results',
            real_data_path=str(self.output_dir / 'measured_data_wide.csv'),
            config=config,
            output_path=str(self.output_dir / 'test5_wide'),
            validate_variants=False
        )
        
        self.results['test5_wide'] = results
        return results
    
    def test_advanced_config(self):
        """Test advanced configuration options"""
        print("\n" + "="*60)
        print("TEST 6: Advanced Configuration")
        print("="*60)
        
        generator = FakeMeasuredDataGenerator()
        data = generator.generate_daily_data(365)  # Full year
        data.to_csv(self.output_dir / 'measured_data_full_year.csv', index=False)
        
        config = {
            'target_frequency': 'monthly',
            'variables_to_validate': ['Electricity', 'Heating', 'Cooling', 'Temperature'],
            'aggregation': {
                'target_frequency': 'monthly',
                'frequency_mapping': {
                    'electricity': 'monthly',
                    'heating': 'monthly',
                    'cooling': 'monthly',
                    'temperature': 'monthly'
                },
                'methods': {
                    'energy': 'sum',
                    'temperature': 'mean',
                    'power': 'mean'
                }
            },
            'thresholds': {
                'default': {
                    'cvrmse': 30.0,
                    'nmbe': 10.0
                },
                'by_variable': {
                    'temperature': {
                        'cvrmse': 15.0,
                        'nmbe': 5.0
                    },
                    'electricity': {
                        'cvrmse': 25.0,
                        'nmbe': 10.0
                    }
                }
            },
            'logging': {
                'level': 'INFO',
                'show_mappings': True,
                'show_aggregations': True,
                'show_unit_conversions': True
            }
        }
        
        results = run_smart_validation(
            parsed_data_path='/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a/parsed_modified_results',
            real_data_path=str(self.output_dir / 'measured_data_full_year.csv'),
            config=config,
            output_path=str(self.output_dir / 'test6_advanced'),
            validate_variants=False
        )
        
        self.results['test6_advanced'] = results
        return results
    
    def generate_documentation(self):
        """Generate comprehensive documentation of validation functions"""
        doc_path = self.output_dir / 'VALIDATION_DOCUMENTATION.md'
        
        with open(doc_path, 'w') as f:
            f.write("# Smart Validation Wrapper - Comprehensive Documentation\n\n")
            f.write("Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
            
            # Overview
            f.write("## Overview\n\n")
            f.write("The Smart Validation Wrapper provides intelligent validation of EnergyPlus simulation results against measured data.\n")
            f.write("It handles variable mapping, frequency alignment, unit conversions, and multi-zone aggregation automatically.\n\n")
            
            # Core Functions
            f.write("## Core Functions\n\n")
            f.write("### 1. `run_smart_validation()`\n")
            f.write("**Purpose**: Main entry point for validation\n\n")
            f.write("**Parameters**:\n")
            f.write("- `parsed_data_path`: Path to parsed simulation data\n")
            f.write("- `real_data_path`: Path to measured/real data CSV\n")
            f.write("- `config`: Configuration dictionary\n")
            f.write("- `output_path`: Where to save results\n")
            f.write("- `validate_variants`: Enable variant validation (default: False)\n\n")
            
            f.write("**Returns**: Dictionary with validation results\n\n")
            
            f.write("### 2. `SmartValidationWrapper` Class\n")
            f.write("**Key Methods**:\n\n")
            
            f.write("#### `discover_available_data()`\n")
            f.write("- Scans parsed data directory\n")
            f.write("- Identifies available timeseries files\n")
            f.write("- Finds comparison files for variants\n")
            f.write("- Detects zones and aggregation needs\n\n")
            
            f.write("#### `load_and_parse_real_data()`\n")
            f.write("- Loads measured data CSV\n")
            f.write("- Handles multiple datetime formats\n")
            f.write("- Infers units from variable names\n")
            f.write("- Detects data frequency\n\n")
            
            f.write("#### `load_simulation_data()`\n")
            f.write("- Loads from timeseries or comparison files\n")
            f.write("- Handles multi-frequency data\n")
            f.write("- Supports wide and long formats\n\n")
            
            f.write("#### `align_frequencies()`\n")
            f.write("- Aligns real and simulated data frequencies\n")
            f.write("- Aggregates using appropriate methods:\n")
            f.write("  - Energy variables: sum\n")
            f.write("  - Temperature variables: mean\n")
            f.write("  - Power variables: mean\n\n")
            
            f.write("#### `create_variable_mappings()`\n")
            f.write("- Maps measured variables to simulation variables\n")
            f.write("- Uses three matching strategies:\n")
            f.write("  1. **Exact Match**: Variables match exactly\n")
            f.write("  2. **Fuzzy Match**: Levenshtein distance < 0.8\n")
            f.write("  3. **Semantic Match**: Pattern-based matching\n\n")
            
            f.write("#### `validate_all()` / `validate_all_variants()`\n")
            f.write("- Performs actual validation\n")
            f.write("- Calculates metrics (CVRMSE, NMBE)\n")
            f.write("- Handles zone aggregation\n")
            f.write("- Generates results and recommendations\n\n")
            
            # Configuration Options
            f.write("## Configuration Options\n\n")
            f.write("### Basic Configuration\n")
            f.write("```python\n")
            f.write("config = {\n")
            f.write("    'target_frequency': 'daily',  # daily, monthly, yearly\n")
            f.write("    'variables_to_validate': ['Electricity', 'Heating', 'Cooling'],\n")
            f.write("    'cvrmse_threshold': 30,  # ASHRAE Guideline 14\n")
            f.write("    'nmbe_threshold': 10     # ASHRAE Guideline 14\n")
            f.write("}\n")
            f.write("```\n\n")
            
            f.write("### Advanced Configuration\n")
            f.write("```python\n")
            f.write("config = {\n")
            f.write("    'target_frequency': 'monthly',\n")
            f.write("    'variables_to_validate': ['Electricity', 'Heating', 'Cooling'],\n")
            f.write("    \n")
            f.write("    # Aggregation settings\n")
            f.write("    'aggregation': {\n")
            f.write("        'target_frequency': 'monthly',\n")
            f.write("        'frequency_mapping': {\n")
            f.write("            'electricity': 'monthly',\n")
            f.write("            'heating': 'monthly'\n")
            f.write("        },\n")
            f.write("        'methods': {\n")
            f.write("            'energy': 'sum',\n")
            f.write("            'temperature': 'mean',\n")
            f.write("            'power': 'mean'\n")
            f.write("        }\n")
            f.write("    },\n")
            f.write("    \n")
            f.write("    # Custom thresholds\n")
            f.write("    'thresholds': {\n")
            f.write("        'default': {\n")
            f.write("            'cvrmse': 30.0,\n")
            f.write("            'nmbe': 10.0\n")
            f.write("        },\n")
            f.write("        'by_variable': {\n")
            f.write("            'temperature': {\n")
            f.write("                'cvrmse': 15.0,\n")
            f.write("                'nmbe': 5.0\n")
            f.write("            }\n")
            f.write("        }\n")
            f.write("    },\n")
            f.write("    \n")
            f.write("    # Logging options\n")
            f.write("    'logging': {\n")
            f.write("        'level': 'INFO',\n")
            f.write("        'show_mappings': True,\n")
            f.write("        'show_aggregations': True,\n")
            f.write("        'show_unit_conversions': True\n")
            f.write("    },\n")
            f.write("    \n")
            f.write("    # Variable mappings\n")
            f.write("    'variable_mappings': {\n")
            f.write("        'Custom Name': 'Simulation Variable Name'\n")
            f.write("    }\n")
            f.write("}\n")
            f.write("```\n\n")
            
            # Test Results
            f.write("## Test Results\n\n")
            
            for test_name, results in self.results.items():
                f.write(f"### {test_name.upper()}\n\n")
                
                if results and 'summary' in results:
                    summary = results['summary']
                    f.write("**Summary**:\n")
                    for key, value in summary.items():
                        f.write(f"- {key}: {value}\n")
                    f.write("\n")
                    
                    if 'mappings' in results and results['mappings']:
                        f.write("**Variable Mappings**:\n")
                        for mapping in results['mappings']:
                            f.write(f"- {mapping.real_var} → {mapping.sim_var} ")
                            f.write(f"(confidence: {mapping.confidence:.2f}, type: {mapping.match_type})\n")
                        f.write("\n")
                    
                    if 'validation_results' in results and results['validation_results']:
                        f.write("**Validation Results**:\n")
                        for vr in results['validation_results']:
                            f.write(f"- Building {vr['building_id']}, {vr['real_variable']}:\n")
                            f.write(f"  - CVRMSE: {vr['cvrmse']:.1f}% (threshold: {vr['cvrmse_threshold']}%)\n")
                            f.write(f"  - NMBE: {vr['nmbe']:.1f}% (threshold: ±{vr['nmbe_threshold']}%)\n")
                            f.write(f"  - Pass: {'✓' if vr['pass_cvrmse'] and vr['pass_nmbe'] else '✗'}\n")
                        f.write("\n")
            
            # Output Files
            f.write("## Output Files Generated\n\n")
            f.write("For each validation run, the following files are created:\n\n")
            f.write("1. **validation_summary.json**: Complete results in JSON format\n")
            f.write("2. **validation_results.parquet**: Detailed metrics in Parquet format\n")
            f.write("3. **validation_results.csv**: Same metrics in CSV format\n")
            f.write("4. **variable_mappings.csv**: How variables were mapped\n\n")
            
            # Metrics
            f.write("## Validation Metrics\n\n")
            f.write("### CVRMSE (Coefficient of Variation of Root Mean Square Error)\n")
            f.write("```\n")
            f.write("CVRMSE = (RMSE / mean(measured)) × 100%\n")
            f.write("```\n")
            f.write("- ASHRAE Guideline 14: < 30% for monthly data\n\n")
            
            f.write("### NMBE (Normalized Mean Bias Error)\n")
            f.write("```\n")
            f.write("NMBE = (sum(simulated - measured) / sum(measured)) × 100%\n")
            f.write("```\n")
            f.write("- ASHRAE Guideline 14: ±10% for monthly data\n\n")
            
            # Common Issues
            f.write("## Common Issues and Solutions\n\n")
            f.write("1. **No validation results generated**\n")
            f.write("   - Check date overlap between measured and simulated data\n")
            f.write("   - Ensure building IDs match\n\n")
            
            f.write("2. **Variable mapping failures**\n")
            f.write("   - Use explicit variable_mappings in config\n")
            f.write("   - Check variable names in both datasets\n\n")
            
            f.write("3. **High CVRMSE values**\n")
            f.write("   - Check unit consistency (J vs kWh)\n")
            f.write("   - Verify aggregation methods\n")
            f.write("   - Consider zone aggregation needs\n\n")
            
            f.write("4. **Missing data issues**\n")
            f.write("   - Ensure complete time series\n")
            f.write("   - Check for NaN values\n")
            f.write("   - Verify datetime parsing\n\n")
            
            print(f"\nDocumentation saved to: {doc_path}")
    
    def run_all_tests(self):
        """Run all validation tests"""
        print("\nStarting Comprehensive Validation Testing")
        print("="*60)
        
        # Run tests
        self.test_basic_validation()
        self.test_frequency_alignment()
        self.test_variable_mapping()
        self.test_variant_validation()
        self.test_wide_format()
        self.test_advanced_config()
        
        # Generate documentation
        self.generate_documentation()
        
        print("\n" + "="*60)
        print("All tests completed!")
        print(f"Results saved to: {self.output_dir}")
        print("="*60)


def main():
    """Main test execution"""
    # First, generate various test data files
    print("Generating test data files...")
    generator = FakeMeasuredDataGenerator(year=2013)
    
    # Create test data directory
    test_data_dir = Path('/mnt/d/Documents/daily/E_Plus_2040_py/test_validation_data')
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate different formats
    print("1. Generating daily data...")
    daily_data = generator.generate_daily_data(365)
    daily_data.to_csv(test_data_dir / 'measured_data_daily_2013.csv', index=False)
    print(f"   Created: {len(daily_data)} rows")
    
    print("2. Generating hourly data...")
    hourly_data = generator.generate_hourly_data(30)
    hourly_data.to_csv(test_data_dir / 'measured_data_hourly_2013.csv', index=False)
    print(f"   Created: {len(hourly_data)} rows")
    
    print("3. Generating monthly data...")
    monthly_data = generator.generate_monthly_data()
    monthly_data.to_csv(test_data_dir / 'measured_data_monthly_2013.csv', index=False)
    print(f"   Created: {len(monthly_data)} rows")
    
    print("4. Generating wide format data...")
    wide_data = generator.generate_wide_format_data(31)
    wide_data.to_csv(test_data_dir / 'measured_data_wide_2013.csv', index=False)
    print(f"   Created: {wide_data.shape[0]} rows × {wide_data.shape[1]} columns")
    
    print("5. Generating EnergyPlus format data...")
    energyplus_data = generator.generate_energyplus_format(365)
    energyplus_data.to_csv(test_data_dir / 'measured_data_energyplus_2013.csv', index=False)
    print(f"   Created: {len(energyplus_data)} rows")
    
    print(f"\nAll test data saved to: {test_data_dir}")
    
    # Run validation tests
    print("\n" + "="*60)
    tester = ValidationTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()