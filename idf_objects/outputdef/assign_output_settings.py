# outputdef/assign_output_settings.py

from .output_lookup import output_lookup

def assign_output_settings(
    desired_variables=None,
    desired_meters=None,
    override_variable_frequency=None,
    override_meter_frequency=None,
    include_tables=True,
    include_summary=True,
    assigned_output_log=None  # <--- optional
):
    """
    Returns a dictionary describing which outputs to create:
      - variables (with freq)
      - meters (with freq)
      - tables
      - summary_reports

    Logging approach:
      If assigned_output_log is provided, store final picks there.
    """

    if desired_variables is None:
        desired_variables = [v["variable_name"] for v in output_lookup["variables"]]
    if desired_meters is None:
        desired_meters = [m["key_name"] for m in output_lookup["meters"]]

    # 1) Build final list for variables
    final_variables = []
    for var_def in output_lookup["variables"]:
        if var_def["variable_name"] in desired_variables:
            freq = override_variable_frequency or var_def["default_frequency"]
            final_variables.append({
                "variable_name": var_def["variable_name"],
                "reporting_frequency": freq
            })

    # 2) Build final list for meters
    final_meters = []
    for meter_def in output_lookup["meters"]:
        if meter_def["key_name"] in desired_meters:
            freq = override_meter_frequency or meter_def["default_frequency"]
            final_meters.append({
                "key_name": meter_def["key_name"],
                "reporting_frequency": freq
            })

    # 3) Tables
    final_tables = []
    if include_tables:
        for tbl in output_lookup["tables"]:
            final_tables.append(tbl)

    # 4) Summary
    final_summary = []
    if include_summary:
        for sr in output_lookup["summary_reports"]:
            final_summary.append(sr)

    # 5) Build final dict
    result = {
        "variables": final_variables,
        "meters": final_meters,
        "tables": final_tables,
        "summary_reports": final_summary
    }

    # 6) If logging, store it
    if assigned_output_log is not None:
        # We might just store them under a key e.g. "final_output_settings"
        assigned_output_log["final_output_settings"] = result

    return result
