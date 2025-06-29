#!/usr/bin/env python3
"""
Recreate the full year test data for building 4136733
"""

import pandas as pd
import numpy as np

# Generate realistic daily electricity values
dates = pd.date_range('2013-01-01', '2013-12-31', freq='D')

# Use same parameters as before
np.random.seed(42)
base_daily = 1777.8  # kWh per day average
seasonal_variation = 200 * np.sin(2 * np.pi * np.arange(len(dates)) / 365)
random_variation = np.random.normal(0, 50, len(dates))

test_data = []
for i, date in enumerate(dates):
    value = base_daily + seasonal_variation[i] + random_variation[i]
    test_data.append({
        'building_id': '4136733',
        'DateTime': date.strftime('%Y-%m-%d'),
        'Variable': 'Total Electricity',
        'Value': max(0, value),  # Ensure non-negative
        'Units': 'kWh'
    })

# Save test data
test_df = pd.DataFrame(test_data)
test_df.to_csv('measured_data_4136733_full.csv', index=False)
print(f"Created measured_data_4136733_full.csv with {len(test_df)} days of data")