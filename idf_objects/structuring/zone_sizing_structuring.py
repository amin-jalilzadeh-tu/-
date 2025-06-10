"""
zone_sizing_structuring.py

Transforms the assigned zone sizing log into a structured format with min/max 
ranges or choices for scenario generation.
"""
import pandas as pd
import os
import json

def transform_zone_sizing_log_to_structured(csv_input, csv_output, user_sizing_rules):
    """
    Reads the assigned zone sizing log and adds min/max/choices columns.

    Args:
        csv_input (str): Path to assigned_zone_sizing_outdoor_air.csv
        csv_output (str): Path to write structured_zone_sizing.csv
        user_sizing_rules (list): A list of dictionaries with sizing rules.
    """
    if not os.path.exists(csv_input):
        print(f"[ERROR] Zone Sizing structuring input not found: {csv_input}")
        return

    df = pd.read_csv(csv_input)
    
    df['min_val'] = pd.NA
    df['max_val'] = pd.NA
    df['choices'] = pd.NA

    # Create a dictionary for quick rule lookup
    rules_map = {rule['param_name']: rule for rule in user_sizing_rules}

    for index, row in df.iterrows():
        param_name = row['param_name']
        if param_name in rules_map:
            rule = rules_map[param_name]
            if 'choices' in rule:
                # Store choices as a JSON string in the cell
                df.loc[index, 'choices'] = json.dumps(rule['choices'])
            else:
                df.loc[index, 'min_val'] = rule.get('min_val')
                df.loc[index, 'max_val'] = rule.get('max_val')

    os.makedirs(os.path.dirname(csv_output), exist_ok=True)
    df.to_csv(csv_output, index=False)
    print(f"[INFO] Wrote structured zone sizing params to {csv_output} ({len(df)} rows)")