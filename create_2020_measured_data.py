import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Create fake measured data for 2020
start_date = datetime(2020, 1, 1)
end_date = datetime(2020, 12, 31)
dates = []
current = start_date

while current <= end_date:
    dates.append(current)
    current += timedelta(days=1)

# Generate realistic energy consumption patterns
np.random.seed(42)
n_days = len(dates)

# Base patterns with seasonal variation
day_of_year = np.arange(n_days)
seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * day_of_year / 365 - np.pi/2)  # Peak in winter

# Electricity: Facility (J) - Daily total electricity
base_electricity = 12e9  # 12 GJ base
electricity_values = base_electricity * (1 + 0.2 * np.random.randn(n_days)) * seasonal_factor

# Heating: Higher in winter
base_heating = 15e9  # 15 GJ base
heating_seasonal = 1 + 0.5 * np.cos(2 * np.pi * day_of_year / 365)  # Peak in winter
heating_values = base_heating * heating_seasonal * (1 + 0.15 * np.random.randn(n_days))
heating_values = np.maximum(heating_values, 0)  # No negative values

# Cooling: Higher in summer
base_cooling = 8e8  # 0.8 GJ base
cooling_seasonal = 1 + 0.8 * np.sin(2 * np.pi * day_of_year / 365)  # Peak in summer
cooling_values = base_cooling * cooling_seasonal * (1 + 0.2 * np.random.randn(n_days))
cooling_values = np.maximum(cooling_values, 0)  # No negative values

# Create DataFrame
data = []
for i, date in enumerate(dates):
    # Electricity
    data.append({
        'building_id': 4136733,
        'DateTime': date.strftime('%Y-%m-%d'),
        'Variable': 'Electricity:Facility [J](Daily)',
        'Value': electricity_values[i],
        'Units': 'J'
    })
    # Heating
    data.append({
        'building_id': 4136733,
        'DateTime': date.strftime('%Y-%m-%d'),
        'Variable': 'Heating:EnergyTransfer [J](Daily)',
        'Value': heating_values[i],
        'Units': 'J'
    })
    # Cooling
    data.append({
        'building_id': 4136733,
        'DateTime': date.strftime('%Y-%m-%d'),
        'Variable': 'Cooling:EnergyTransfer [J](Daily)',
        'Value': cooling_values[i],
        'Units': 'J'
    })

df = pd.DataFrame(data)

# Save to CSV
df.to_csv('data/test_validation_data/measured_data_energyplus_format_4136733_2020.csv', index=False)
print(f"Created {len(df)} rows of measured data for 2020")
print(f"Date range: {df['DateTime'].min()} to {df['DateTime'].max()}")
print(f"\nVariable summary:")
print(df['Variable'].value_counts())

# Also create parsed format for daily data
daily_data = []
for date in dates:
    date_str = date.strftime('%Y-%m-%d')
    date_data = df[df['DateTime'] == date_str]
    
    row = {
        'building_id': 4136733,
        'Date': date_str
    }
    
    for _, record in date_data.iterrows():
        var_name = record['Variable'].replace(' [J](Daily)', '').replace(':', '_')
        row[var_name] = record['Value']
    
    daily_data.append(row)

df_daily = pd.DataFrame(daily_data)
df_daily.to_csv('data/test_validation_data/measured_data_parsed_format_daily_4136733_2020.csv', index=False)
print(f"\nCreated parsed daily format with {len(df_daily)} rows")
print(f"Columns: {list(df_daily.columns)}")