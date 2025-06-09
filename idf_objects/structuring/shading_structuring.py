"""
shading_structuring.py

Transforms the assigned shading log into a structured format with min/max ranges
for sensitivity analysis and modification.
"""
import pandas as pd
import os

def transform_shading_log_to_structured(csv_input, csv_output, user_shading_rules):
    """
    Reads the assigned shading log and adds min/max value columns based on user rules.

    Args:
        csv_input (str): Path to assigned_shading_params.csv
        csv_output (str): Path to write structured_shading_params.csv
        user_shading_rules (list): A list of dictionaries with shading rules.
    """
    if not os.path.exists(csv_input):
        print(f"[ERROR] Shading structuring input not found: {csv_input}")
        return

    df = pd.read_csv(csv_input)
    
    df['min_val'] = pd.NA
    df['max_val'] = pd.NA

    # Create a dictionary for quick rule lookup
    rules_map = {rule['param_name']: rule for rule in user_shading_rules}

    for index, row in df.iterrows():
        param_name = row['param_name']
        if param_name in rules_map:
            rule = rules_map[param_name]
            if 'fixed_value' in rule:
                # If fixed, assigned_value is overwritten and no range is set
                df.loc[index, 'assigned_value'] = rule['fixed_value']
            else:
                df.loc[index, 'min_val'] = rule.get('min_val')
                df.loc[index, 'max_val'] = rule.get('max_val')

    os.makedirs(os.path.dirname(csv_output), exist_ok=True)
    df.to_csv(csv_output, index=False)
    print(f"[INFO] Wrote structured shading params to {csv_output} ({len(df)} rows)")