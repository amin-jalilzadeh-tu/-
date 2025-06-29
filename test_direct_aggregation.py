#!/usr/bin/env python3
"""Direct test of aggregation logic"""

import pandas as pd
import numpy as np
import re
from collections import defaultdict

def aggregate_base_columns_test(df, from_freq, to_freq):
    """Test version of aggregate_base_columns"""
    if from_freq == to_freq:
        return df
    
    # Get metadata columns
    meta_cols = ['building_id', 'variant_id', 'VariableName', 'category', 'Zone', 'Units']
    meta_cols = [col for col in meta_cols if col in df.columns]
    
    # Get date columns
    if from_freq == 'daily':
        date_pattern = r'\d{4}-\d{2}-\d{2}$'
    else:
        return df
    
    date_cols = [col for col in df.columns if re.match(date_pattern, str(col))]
    
    if not date_cols:
        return df
    
    # Group columns by target period
    grouped_cols = defaultdict(list)
    
    if from_freq == 'daily' and to_freq == 'yearly':
        for col in date_cols:
            year_key = col[:4]  # YYYY
            grouped_cols[year_key].append(col)
    elif from_freq == 'daily' and to_freq == 'monthly':
        for col in date_cols:
            month_key = col[:7]  # YYYY-MM
            grouped_cols[month_key].append(col)
    else:
        return df
    
    # Create new dataframe with aggregated columns
    result_df = df[meta_cols].copy()
    
    # Process each row
    for idx, row in df.iterrows():
        var_name = row.get('VariableName', '')
        
        # For energy variables, use sum
        if 'Energy' in var_name or 'Electricity' in var_name:
            agg_method = 'sum'
        else:
            agg_method = 'mean'
        
        # Aggregate each time group
        for new_col, source_cols in grouped_cols.items():
            values = row[source_cols].values
            # Remove NaN values
            values = values[~pd.isna(values)]
            
            if len(values) > 0:
                if agg_method == 'sum':
                    result_df.loc[idx, new_col] = np.sum(values)
                else:
                    result_df.loc[idx, new_col] = np.mean(values)
            else:
                result_df.loc[idx, new_col] = np.nan
    
    return result_df

# Create test data
dates = pd.date_range('2013-01-01', '2013-12-31', freq='D')
date_cols = [d.strftime('%Y-%m-%d') for d in dates]

data = {
    'building_id': [4136733, 4136733],
    'variant_id': ['base', 'base'],
    'VariableName': ['Electricity:Facility', 'Zone Air Temperature'],
    'category': ['energy_meters', 'zones'],
    'Zone': ['Building', 'Zone1'],
    'Units': ['J', 'C']
}

# Add daily values
for i, date_col in enumerate(date_cols):
    # Electricity: 6.4 MJ per day
    # Temperature: varies around 20C
    data[date_col] = [6.4e6, 20 + 5*np.sin(i/365*2*np.pi)]

df = pd.DataFrame(data)

print("Original data shape:", df.shape)
print("Number of date columns:", len(date_cols))
print("\nFirst few columns:", df.columns[:10].tolist())

# Test daily to yearly
print("\n" + "="*50)
print("Testing daily to yearly aggregation")
print("="*50)

yearly_df = aggregate_base_columns_test(df, 'daily', 'yearly')
yearly_cols = [col for col in yearly_df.columns if col.startswith('20')]

print(f"Result shape: {yearly_df.shape}")
print(f"Yearly columns: {yearly_cols}")

if len(yearly_cols) == 1:
    print("✓ SUCCESS: Got single year column")
    
    # Check values
    for idx, row in yearly_df.iterrows():
        var_name = row['VariableName']
        yearly_value = row['2013']
        daily_sum = df.iloc[idx][date_cols].sum()
        
        print(f"\n{var_name}:")
        print(f"  Aggregation method: {'sum' if 'Energy' in var_name or 'Electricity' in var_name else 'mean'}")
        print(f"  Daily sum: {daily_sum:.2e}")
        print(f"  Yearly value: {yearly_value:.2e}")
        
        if 'Electricity' in var_name:
            expected_yearly = 6.4e6 * 365  # 365 days
            print(f"  Expected (365 * 6.4e6): {expected_yearly:.2e}")
            print(f"  Match: {np.isclose(yearly_value, expected_yearly)}")
else:
    print(f"✗ FAILED: Expected 1 year column, got {len(yearly_cols)}")

# Test daily to monthly
print("\n" + "="*50)
print("Testing daily to monthly aggregation")
print("="*50)

monthly_df = aggregate_base_columns_test(df, 'daily', 'monthly')
monthly_cols = [col for col in monthly_df.columns if re.match(r'\d{4}-\d{2}$', col)]

print(f"Result shape: {monthly_df.shape}")
print(f"Number of monthly columns: {len(monthly_cols)}")
print(f"First few monthly columns: {monthly_cols[:5]}")

if len(monthly_cols) == 12:
    print("✓ SUCCESS: Got 12 month columns")
    
    # Check January values
    jan_col = '2013-01'
    if jan_col in monthly_df.columns:
        print(f"\nJanuary values:")
        for idx, row in monthly_df.iterrows():
            var_name = row['VariableName']
            jan_value = row[jan_col]
            print(f"  {var_name}: {jan_value:.2e}")
else:
    print(f"✗ FAILED: Expected 12 month columns, got {len(monthly_cols)}")