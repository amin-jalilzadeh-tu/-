"""
equipment_structuring.py

Reads the assigned equipment log and prepares it for scenario generation.
For now, this is a simple pass-through as min/max are already in the source.
"""
import pandas as pd
import os
import shutil

def transform_equipment_log_to_structured(csv_input, csv_output, user_equipment_rules):
    """
    Reads assigned_equipment.csv and saves it as structured_equipment.csv.

    In the future, this could be expanded to apply the user_equipment_rules
    to override or validate the min/max values.
    """
    if not os.path.exists(csv_input):
        print(f"[ERROR] Equipment structuring input not found: {csv_input}")
        return

    # For now, we just copy the file as it already contains the necessary columns
    os.makedirs(os.path.dirname(csv_output), exist_ok=True)
    shutil.copy(csv_input, csv_output)
    
    df = pd.read_csv(csv_output)
    print(f"[INFO] Wrote structured equipment params to {csv_output} ({len(df)} rows)")