#!/usr/bin/env python3
"""
Generate measured data for validation testing in various formats
Supports CSV and Parquet outputs with different structures
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from pathlib import Path
import random


class MeasuredDataGenerator:
    """Generate realistic measured data for testing validation"""
    
    def __init__(self, output_dir: str = "test_validation_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Building IDs to use
        self.building_ids = [4136737, 4136738, 4136739]
        
        # Variable definitions with realistic ranges
        self.variables = {
            'electricity': {
                'names': ['Total Electricity', 'Electricity Consumption', 'Facility Electricity'],
                'units': ['kWh', 'kWh', 'MWh'],
                'daily_range': (1000, 5000),  # kWh
                'hourly_range': (40, 200),     # kWh
                'seasonal_factor': {'winter': 1.2, 'summer': 1.4, 'spring': 1.0, 'fall': 1.0}
            },
            'heating': {
                'names': ['Heating Energy', 'Space Heating', 'Heating Consumption'],
                'units': ['kWh', 'MJ', 'J'],
                'daily_range': (500, 3000),    # kWh
                'hourly_range': (20, 125),     # kWh
                'seasonal_factor': {'winter': 2.0, 'summer': 0.1, 'spring': 0.5, 'fall': 0.8}
            },
            'cooling': {
                'names': ['Cooling Energy', 'Space Cooling', 'AC Energy'],
                'units': ['kWh', 'kWh', 'MJ'],
                'daily_range': (500, 2500),    # kWh
                'hourly_range': (20, 100),     # kWh
                'seasonal_factor': {'winter': 0.1, 'summer': 2.0, 'spring': 0.5, 'fall': 0.3}
            },
            'temperature': {
                'names': ['Indoor Temperature', 'Zone Temperature', 'Space Temp'],
                'units': ['C', 'F', 'C'],
                'daily_range': (20, 24),       # C
                'hourly_range': (19, 25),      # C
                'seasonal_factor': {'winter': 0.95, 'summer': 1.05, 'spring': 1.0, 'fall': 1.0}
            }
        }
        
        # Zone names for multi-zone examples
        self.zones = ['Zone1', 'Zone2', 'Zone3', 'Zone4', 'Zone5']
    
    def get_season(self, date):
        """Get season for a date"""
        month = date.month
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'fall'
    
    def add_noise(self, value, percent=5):
        """Add random noise to a value"""
        noise = value * (percent / 100) * (random.random() - 0.5) * 2
        return value + noise
    
    def convert_units(self, value, from_unit, to_unit):
        """Convert between units"""
        conversions = {
            ('kWh', 'J'): lambda x: x * 3600000,
            ('kWh', 'MJ'): lambda x: x * 3.6,
            ('kWh', 'MWh'): lambda x: x / 1000,
            ('C', 'F'): lambda x: x * 9/5 + 32,
            ('F', 'C'): lambda x: (x - 32) * 5/9
        }
        
        if from_unit == to_unit:
            return value
        
        key = (from_unit, to_unit)
        if key in conversions:
            return conversions[key](value)
        
        return value
    
    def generate_daily_simple(self):
        """Generate simple daily data - most basic format"""
        print("Generating simple daily data...")
        
        data = []
        start_date = datetime(2013, 1, 1)
        
        for building_id in self.building_ids[:2]:  # Just 2 buildings
            for day in range(365):
                date = start_date + timedelta(days=day)
                season = self.get_season(date)
                
                # Generate data for each variable type
                for var_type, config in self.variables.items():
                    var_name = config['names'][0]  # Use first name variant
                    unit = config['units'][0]      # Use first unit
                    
                    # Base value
                    min_val, max_val = config['daily_range']
                    base_value = random.uniform(min_val, max_val)
                    
                    # Apply seasonal factor
                    value = base_value * config['seasonal_factor'][season]
                    
                    # Add noise
                    value = self.add_noise(value)
                    
                    # For temperature, keep in reasonable range
                    if var_type == 'temperature':
                        value = max(18, min(26, value))
                    
                    data.append({
                        'building_id': building_id,
                        'DateTime': date.strftime('%Y-%m-%d'),
                        'Variable': var_name,
                        'Value': round(value, 2),
                        'Units': unit
                    })
        
        df = pd.DataFrame(data)
        
        # Save as CSV
        csv_path = self.output_dir / 'measured_data_simple.csv'
        df.to_csv(csv_path, index=False)
        print(f"  Saved: {csv_path}")
        
        # Save as Parquet
        parquet_path = self.output_dir / 'measured_data_simple.parquet'
        df.to_parquet(parquet_path, index=False)
        print(f"  Saved: {parquet_path}")
        
        return df
    
    def generate_hourly_detailed(self):
        """Generate detailed hourly data with zones"""
        print("\nGenerating detailed hourly data with zones...")
        
        data = []
        start_date = datetime(2013, 1, 1)
        
        # Generate for 1 month to keep file size reasonable
        for building_id in self.building_ids[:2]:
            for day in range(31):
                date = start_date + timedelta(days=day)
                season = self.get_season(date)
                
                for hour in range(24):
                    timestamp = date + timedelta(hours=hour)
                    
                    # Temperature data - zone level
                    if building_id == self.building_ids[0]:  # Multi-zone building
                        for zone in self.zones[:3]:
                            base_temp = 21 + 2 * np.sin((hour - 6) * np.pi / 12)  # Daily pattern
                            zone_offset = random.uniform(-1, 1)  # Zone variation
                            temp = base_temp + zone_offset
                            temp = self.add_noise(temp, 2)
                            
                            data.append({
                                'building_id': building_id,
                                'DateTime': timestamp,
                                'Variable': 'Zone Temperature',
                                'Zone': zone,
                                'Value': round(temp, 1),
                                'Units': 'C'
                            })
                    else:  # Single zone building
                        base_temp = 21 + 2 * np.sin((hour - 6) * np.pi / 12)
                        temp = self.add_noise(base_temp, 2)
                        
                        data.append({
                            'building_id': building_id,
                            'DateTime': timestamp,
                            'Variable': 'Zone Temperature',
                            'Zone': 'Zone1',
                            'Value': round(temp, 1),
                            'Units': 'C'
                        })
                    
                    # Energy data - building level
                    for var_type in ['electricity', 'heating', 'cooling']:
                        config = self.variables[var_type]
                        var_name = config['names'][0]
                        unit = config['units'][0]
                        
                        # Hourly pattern
                        hour_factor = 1.0
                        if var_type == 'electricity':
                            # Peak during business hours
                            if 8 <= hour <= 18:
                                hour_factor = 1.5
                            else:
                                hour_factor = 0.7
                        elif var_type == 'heating':
                            # Peak in morning and evening
                            if hour in [6, 7, 8, 18, 19, 20]:
                                hour_factor = 1.8
                            else:
                                hour_factor = 0.8
                        elif var_type == 'cooling':
                            # Peak in afternoon
                            if 12 <= hour <= 16:
                                hour_factor = 2.0
                            else:
                                hour_factor = 0.5
                        
                        min_val, max_val = config['hourly_range']
                        base_value = random.uniform(min_val, max_val)
                        value = base_value * config['seasonal_factor'][season] * hour_factor
                        value = self.add_noise(value)
                        
                        data.append({
                            'building_id': building_id,
                            'DateTime': timestamp,
                            'Variable': var_name,
                            'Zone': None,
                            'Value': round(value, 2),
                            'Units': unit
                        })
        
        df = pd.DataFrame(data)
        
        # Save as CSV
        csv_path = self.output_dir / 'measured_data_hourly.csv'
        df.to_csv(csv_path, index=False)
        print(f"  Saved: {csv_path}")
        
        # Save as Parquet
        parquet_path = self.output_dir / 'measured_data_hourly.parquet'
        df.to_parquet(parquet_path, index=False)
        print(f"  Saved: {parquet_path}")
        
        return df
    
    def generate_mixed_units_formats(self):
        """Generate data with mixed units and date formats"""
        print("\nGenerating mixed units and formats data...")
        
        data = []
        start_date = datetime(2013, 1, 1)
        
        # Different date formats to use
        date_formats = [
            '%Y-%m-%d',          # 2013-01-01
            '%m/%d/%Y',          # 01/01/2013
            '%d/%m/%Y',          # 01/01/2013
            '%Y/%m/%d',          # 2013/01/01
            '%m/%d/%Y %H:%M:%S', # 01/01/2013 00:00:00
        ]
        
        for building_id in self.building_ids:
            # Use different date format for each building
            date_format = date_formats[self.building_ids.index(building_id) % len(date_formats)]
            
            for day in range(30):  # One month
                date = start_date + timedelta(days=day)
                season = self.get_season(date)
                
                # Electricity in different units
                elec_config = self.variables['electricity']
                elec_value = random.uniform(*elec_config['daily_range'])
                elec_value *= elec_config['seasonal_factor'][season]
                
                # Different unit for each building
                if building_id == self.building_ids[0]:
                    elec_unit = 'kWh'
                elif building_id == self.building_ids[1]:
                    elec_unit = 'MWh'
                    elec_value = self.convert_units(elec_value, 'kWh', 'MWh')
                else:
                    elec_unit = 'J'
                    elec_value = self.convert_units(elec_value, 'kWh', 'J')
                
                data.append({
                    'building_id': building_id,
                    'DateTime': date.strftime(date_format),
                    'Variable': 'Electricity Consumption',
                    'Value': round(elec_value, 2),
                    'Units': elec_unit
                })
                
                # Heating in different units
                heat_config = self.variables['heating']
                heat_value = random.uniform(*heat_config['daily_range'])
                heat_value *= heat_config['seasonal_factor'][season]
                
                if building_id == self.building_ids[0]:
                    heat_unit = 'kWh'
                    heat_var = 'Heating Energy'
                elif building_id == self.building_ids[1]:
                    heat_unit = 'MJ'
                    heat_var = 'Space Heating'
                    heat_value = self.convert_units(heat_value, 'kWh', 'MJ')
                else:
                    heat_unit = 'J'
                    heat_var = 'Heating'
                    heat_value = self.convert_units(heat_value, 'kWh', 'J')
                
                data.append({
                    'building_id': building_id,
                    'DateTime': date.strftime(date_format),
                    'Variable': heat_var,
                    'Value': round(heat_value, 2),
                    'Units': heat_unit
                })
                
                # Temperature in C or F
                temp_config = self.variables['temperature']
                temp_value = random.uniform(*temp_config['daily_range'])
                
                if building_id == self.building_ids[1]:
                    temp_unit = 'F'
                    temp_var = 'Indoor Temp'
                    temp_value = self.convert_units(temp_value, 'C', 'F')
                else:
                    temp_unit = 'C'
                    temp_var = 'Indoor Temperature'
                
                data.append({
                    'building_id': building_id,
                    'DateTime': date.strftime(date_format),
                    'Variable': temp_var,
                    'Value': round(temp_value, 1),
                    'Units': temp_unit
                })
        
        df = pd.DataFrame(data)
        
        # Save as CSV
        csv_path = self.output_dir / 'measured_data_mixed.csv'
        df.to_csv(csv_path, index=False)
        print(f"  Saved: {csv_path}")
        
        # Save as Parquet
        parquet_path = self.output_dir / 'measured_data_mixed.parquet'
        df.to_parquet(parquet_path, index=False)
        print(f"  Saved: {parquet_path}")
        
        return df
    
    def generate_incomplete_data(self):
        """Generate data with missing values and gaps"""
        print("\nGenerating incomplete data with gaps...")
        
        data = []
        start_date = datetime(2013, 1, 1)
        
        for building_id in self.building_ids[:2]:
            for day in range(365):
                date = start_date + timedelta(days=day)
                season = self.get_season(date)
                
                # Skip some days randomly (10% chance)
                if random.random() < 0.1:
                    continue
                
                # Skip weekends for one building
                if building_id == self.building_ids[0] and date.weekday() >= 5:
                    continue
                
                # Generate data for each variable
                for var_type, config in self.variables.items():
                    # Skip cooling data in winter for one building
                    if (building_id == self.building_ids[1] and 
                        var_type == 'cooling' and season == 'winter'):
                        continue
                    
                    # Skip some variables randomly (5% chance)
                    if random.random() < 0.05:
                        continue
                    
                    var_name = config['names'][0]
                    unit = config['units'][0]
                    
                    min_val, max_val = config['daily_range']
                    base_value = random.uniform(min_val, max_val)
                    value = base_value * config['seasonal_factor'][season]
                    value = self.add_noise(value)
                    
                    # Occasionally insert NaN (2% chance)
                    if random.random() < 0.02:
                        value = np.nan
                    
                    data.append({
                        'building_id': building_id,
                        'DateTime': date.strftime('%Y-%m-%d'),
                        'Variable': var_name,
                        'Value': round(value, 2) if not pd.isna(value) else value,
                        'Units': unit
                    })
        
        df = pd.DataFrame(data)
        
        # Save as CSV
        csv_path = self.output_dir / 'measured_data_incomplete.csv'
        df.to_csv(csv_path, index=False)
        print(f"  Saved: {csv_path}")
        
        # Save as Parquet
        parquet_path = self.output_dir / 'measured_data_incomplete.parquet'
        df.to_parquet(parquet_path, index=False)
        print(f"  Saved: {parquet_path}")
        
        return df
    
    def generate_energyplus_format(self):
        """Generate data that matches EnergyPlus variable names exactly"""
        print("\nGenerating EnergyPlus format data...")
        
        data = []
        start_date = datetime(2013, 1, 1)
        
        # EnergyPlus style variable names
        ep_variables = {
            'electricity': 'Electricity:Facility [J](Daily)',
            'heating': 'Zone Air System Sensible Heating Energy',
            'cooling': 'Zone Air System Sensible Cooling Energy',
            'temperature': 'Zone Mean Air Temperature'
        }
        
        for building_id in self.building_ids[:2]:
            for day in range(365):
                date = start_date + timedelta(days=day)
                season = self.get_season(date)
                
                for var_type, ep_name in ep_variables.items():
                    config = self.variables[var_type]
                    
                    # Base value
                    min_val, max_val = config['daily_range']
                    base_value = random.uniform(min_val, max_val)
                    value = base_value * config['seasonal_factor'][season]
                    value = self.add_noise(value)
                    
                    # Convert to J for energy variables
                    if var_type in ['electricity', 'heating', 'cooling']:
                        unit = 'J'
                        value = self.convert_units(value, 'kWh', 'J')
                    else:
                        unit = 'C'
                    
                    data.append({
                        'building_id': building_id,
                        'DateTime': date,
                        'Variable': ep_name,
                        'Value': round(value, 2),
                        'Units': unit
                    })
        
        df = pd.DataFrame(data)
        
        # Save as CSV
        csv_path = self.output_dir / 'measured_data_energyplus_format.csv'
        df.to_csv(csv_path, index=False)
        print(f"  Saved: {csv_path}")
        
        # Save as Parquet
        parquet_path = self.output_dir / 'measured_data_energyplus_format.parquet'
        df.to_parquet(parquet_path, index=False)
        print(f"  Saved: {parquet_path}")
        
        return df
    
    def generate_wide_format(self):
        """Generate data in wide format (dates as columns)"""
        print("\nGenerating wide format data...")
        
        data = []
        start_date = datetime(2013, 1, 1)
        
        # Generate data first
        for building_id in self.building_ids[:2]:
            for var_type, config in self.variables.items():
                row = {
                    'BuildingID': building_id,
                    'VariableName': config['names'][0],
                    'Units': config['units'][0]
                }
                
                # Add values for each day
                for day in range(31):  # One month
                    date = start_date + timedelta(days=day)
                    season = self.get_season(date)
                    
                    min_val, max_val = config['daily_range']
                    base_value = random.uniform(min_val, max_val)
                    value = base_value * config['seasonal_factor'][season]
                    value = self.add_noise(value)
                    
                    # Date as column name
                    date_str = date.strftime('%m/%d')
                    row[date_str] = round(value, 2)
                
                data.append(row)
        
        df = pd.DataFrame(data)
        
        # Save as CSV
        csv_path = self.output_dir / 'measured_data_wide_format.csv'
        df.to_csv(csv_path, index=False)
        print(f"  Saved: {csv_path}")
        
        # Save as Parquet
        parquet_path = self.output_dir / 'measured_data_wide_format.parquet'
        df.to_parquet(parquet_path, index=False)
        print(f"  Saved: {parquet_path}")
        
        return df
    
    def generate_all(self):
        """Generate all data formats"""
        print(f"\nGenerating all test data formats in: {self.output_dir}\n")
        print("="*60)
        
        # Generate each format
        self.generate_daily_simple()
        self.generate_hourly_detailed()
        self.generate_mixed_units_formats()
        self.generate_incomplete_data()
        self.generate_energyplus_format()
        self.generate_wide_format()
        
        print("\n" + "="*60)
        print("All test data generated successfully!")
        print(f"Output directory: {self.output_dir}")
        
        # Create a summary
        summary = []
        for file in sorted(self.output_dir.glob('measured_data_*.csv')):
            df = pd.read_csv(file)
            summary.append({
                'File': file.name,
                'Rows': len(df),
                'Columns': list(df.columns),
                'Description': self._get_description(file.stem)
            })
        
        summary_df = pd.DataFrame(summary)
        summary_path = self.output_dir / 'data_summary.csv'
        summary_df.to_csv(summary_path, index=False)
        print(f"\nData summary saved to: {summary_path}")
    
    def _get_description(self, filename):
        """Get description for each data format"""
        descriptions = {
            'measured_data_simple': 'Basic daily data with standard units',
            'measured_data_hourly': 'Hourly data with zone-level temperatures',
            'measured_data_mixed': 'Mixed units and date formats',
            'measured_data_incomplete': 'Data with gaps and missing values',
            'measured_data_energyplus_format': 'EnergyPlus variable names and units',
            'measured_data_wide_format': 'Wide format with dates as columns'
        }
        return descriptions.get(filename, 'Test data')


if __name__ == "__main__":
    # Generate all test data
    generator = MeasuredDataGenerator()
    generator.generate_all()