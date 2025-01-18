# outputdef/add_output_definitions.py

def add_output_definitions(idf, output_settings, assigned_output_log=None):
    """
    :param idf: EnergyPlus IDF object
    :param output_settings: dict with keys "variables", "meters", "tables", "summary_reports"
    :param assigned_output_log: optional dict for logging
    """
    # 1) Variables
    added_vars = []
    skipped_vars = []
    for var in output_settings["variables"]:
        var_name = var["variable_name"]
        freq = var["reporting_frequency"]

        existing_vars = [
            ov for ov in idf.idfobjects["OUTPUT:VARIABLE"]
            if ov.Variable_Name == var_name and ov.Reporting_Frequency.upper() == freq.upper()
        ]
        if not existing_vars:
            new_var = idf.newidfobject("OUTPUT:VARIABLE")
            new_var.Key_Value = "*"
            new_var.Variable_Name = var_name
            new_var.Reporting_Frequency = freq
            added_vars.append((var_name, freq))
        else:
            skipped_vars.append((var_name, freq))

    # 2) Meters
    added_meters = []
    skipped_meters = []
    for meter in output_settings["meters"]:
        key_name = meter["key_name"]
        freq = meter["reporting_frequency"]
        existing_meters = [
            om for om in idf.idfobjects["OUTPUT:METER"]
            if om.Key_Name == key_name and om.Reporting_Frequency.upper() == freq.upper()
        ]
        if not existing_meters:
            new_meter = idf.newidfobject("OUTPUT:METER")
            new_meter.Key_Name = key_name
            new_meter.Reporting_Frequency = freq
            added_meters.append((key_name, freq))
        else:
            skipped_meters.append((key_name, freq))

    # 3) Tables
    added_tables = []
    skipped_tables = []
    for tbl in output_settings["tables"]:
        obj_type = tbl["object_type"]  # e.g. "OUTPUT:TABLE:MONTHLY"
        name = tbl["name"]

        existing_tables = [ot for ot in idf.idfobjects[obj_type] if getattr(ot, "Name", "") == name]
        if not existing_tables:
            new_tbl = idf.newidfobject(obj_type)
            new_tbl.Name = name
            for field_name, field_val in tbl["fields"].items():
                setattr(new_tbl, field_name, field_val)
            added_tables.append(name)
        else:
            skipped_tables.append(name)

    # 4) Summary
    sr_added = []
    if output_settings["summary_reports"]:
        existing_sum = idf.idfobjects["OUTPUT:TABLE:SUMMARYREPORTS"]
        if not existing_sum:
            sum_obj = idf.newidfobject("OUTPUT:TABLE:SUMMARYREPORTS")
        else:
            sum_obj = existing_sum[0]

        idx = 1
        for sr in output_settings["summary_reports"]:
            field_name = f"Report_{idx}_Name"
            if hasattr(sum_obj, field_name):
                setattr(sum_obj, field_name, sr)
                sr_added.append(sr)
                idx += 1
            else:
                print(f"[OUTPUT] Warning: no more fields for summary report '{sr}'.")
                # optional skip or store as "skipped"

    # If assigned_output_log => store
    if assigned_output_log is not None:
        assigned_output_log["added_variables"] = added_vars
        assigned_output_log["skipped_variables"] = skipped_vars
        assigned_output_log["added_meters"] = added_meters
        assigned_output_log["skipped_meters"] = skipped_meters
        assigned_output_log["added_tables"] = added_tables
        assigned_output_log["skipped_tables"] = skipped_tables
        assigned_output_log["added_summary_reports"] = sr_added

    return
