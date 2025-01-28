"""
dhw_structuring.py

Transforms the "assigned_dhw_params.csv" file into a structured CSV, merging
range data (e.g. "R_value_range") with the final assigned values. Also
captures E+ object type/name if present.

Usage (standalone):
    python dhw_structuring.py

Or import and call "transform_dhw_log_to_structured(...)" from your main code.
"""

import pandas as pd
import ast
import os

def transform_dhw_log_to_structured(
    csv_input="output/assigned/assigned_dhw_params.csv",
    csv_output="output/assigned/structured_dhw_params.csv",
):
    """
    Reads the 'flat' DHW CSV with columns (ogc_fid, param_name, assigned_value).
    Produces a 'structured' CSV with columns:
       ogc_fid, sub_key, eplus_object_type, eplus_object_name,
       param_name, param_value, param_min, param_max

    Key logic:
      - If param_name ends with "_range", parse min/max from assigned_value
        and store them in memory.
      - If param_name is the same as the range version minus "_range",
        unify them in one row => param_value + param_min + param_max.
      - If param_name includes '.obj_type' or '.Name', we store them
        so we can fill eplus_object_type/eplus_object_name in final row.
    """

    df = pd.read_csv(csv_input)

    # We'll keep data in a nested dictionary:
    # final_dict[(ogc_fid, sub_key, base_param)] = {
    #    "value": <float or str>,
    #    "min": <float or None>,
    #    "max": <float or None>,
    #    "obj_type": <str or None>,
    #    "obj_name": <str or None>
    # }
    final_dict = {}

    def get_subdict(fid, s_key, base_param):
        if (fid, s_key, base_param) not in final_dict:
            final_dict[(fid, s_key, base_param)] = {
                "value": None,
                "min": None,
                "max": None,
                "obj_type": None,
                "obj_name": None
            }
        return final_dict[(fid, s_key, base_param)]

    for i, row in df.iterrows():
        # Must have these columns
        if "ogc_fid" not in row or "param_name" not in row or "assigned_value" not in row:
            continue

        ogc_fid = row["ogc_fid"]
        param_name = str(row["param_name"])
        assigned_value = row["assigned_value"]

        # If you only want to transform "dhw_" lines, you could do:
        # if not param_name.startswith("dhw_"):
        #     continue

        # Attempt sub_key parse. If we see "dhw_waterheater.obj_type" => sub_key="dhw_waterheater", field="obj_type"
        # If param_name has no dot => sub_key="dhw_top" or something default
        sub_key = "dhw_top"
        field = param_name
        if '.' in param_name:
            parts = param_name.split('.', 1)
            sub_key, field = parts[0], parts[1]
        # e.g. sub_key="dhw_waterheater", field="obj_type"

        if field.endswith("_range"):
            # e.g. "setpoint_c_range"
            base_param = field[:-6]  # remove "_range"
            subd = get_subdict(ogc_fid, sub_key, base_param)

            # parse assigned_value => (minVal, maxVal)
            try:
                tval = ast.literal_eval(str(assigned_value))
                if isinstance(tval, (list, tuple)) and len(tval) == 2:
                    subd["min"], subd["max"] = tval
            except:
                pass

        elif field in ("obj_type", "Name"):
            # E+ object pointer
            # We'll store them in base_param="EPOBJ"
            base_param = "EPOBJ"
            subd = get_subdict(ogc_fid, sub_key, base_param)

            if field == "obj_type":
                subd["obj_type"] = assigned_value
            else:  # "Name"
                subd["obj_name"] = assigned_value

        else:
            # normal param => e.g. "setpoint_c"
            base_param = field
            subd = get_subdict(ogc_fid, sub_key, base_param)
            subd["value"] = assigned_value

    # Now we have a dict that merges range with final value, object type, etc.
    # We'll produce final rows with columns we want:
    structured_rows = []
    for (fid, s_key, base_param), valdict in final_dict.items():
        # If base_param == "EPOBJ", that means it's the object reference (obj_type, obj_name)
        # We'll handle them below if you want them as separate param rows or
        # or you can attach them to everything else. Let's do the approach
        # where we have "param_name" = "obj_type", "param_name" = "Name" as separate lines
        # or you can skip them as normal param lines. We'll do a combination approach.

        if base_param == "EPOBJ":
            # object-level
            # param row for obj_type
            if valdict["obj_type"] is not None:
                structured_rows.append({
                    "ogc_fid": fid,
                    "sub_key": s_key,
                    "eplus_object_type": valdict["obj_type"],
                    "eplus_object_name": valdict["obj_name"],
                    "param_name": "obj_type",
                    "param_value": valdict["obj_type"],
                    "param_min": None,
                    "param_max": None
                })
            # param row for Name
            if valdict["obj_name"] is not None:
                structured_rows.append({
                    "ogc_fid": fid,
                    "sub_key": s_key,
                    "eplus_object_type": valdict["obj_type"],
                    "eplus_object_name": valdict["obj_name"],
                    "param_name": "Name",
                    "param_value": valdict["obj_name"],
                    "param_min": None,
                    "param_max": None
                })
        else:
            # normal param => occupant_density, setpoint_c, etc.
            param_val = valdict["value"]
            param_min = valdict["min"]
            param_max = valdict["max"]

            # we might want to parse them as floats
            def try_float(x):
                try:
                    return float(x)
                except:
                    return x

            param_val = try_float(param_val)
            param_min = try_float(param_min)
            param_max = try_float(param_max)

            # find if there's an "EPOBJ" for this sub_key => attach eplus_object_type/eplus_object_name
            ep_obj = final_dict.get((fid, s_key, "EPOBJ"), {})
            eplus_type = ep_obj.get("obj_type", None)
            eplus_name = ep_obj.get("obj_name", None)

            structured_rows.append({
                "ogc_fid": fid,
                "sub_key": s_key,
                "eplus_object_type": eplus_type,
                "eplus_object_name": eplus_name,
                "param_name": base_param,
                "param_value": param_val,
                "param_min": param_min,
                "param_max": param_max
            })

    # Convert to DataFrame
    df_struct = pd.DataFrame(structured_rows)

    # Sort if you like
    df_struct.sort_values(by=["ogc_fid", "sub_key", "param_name"], inplace=True)

    # Write
    os.makedirs(os.path.dirname(csv_output), exist_ok=True)
    df_struct.to_csv(csv_output, index=False)
    print(f"[transform_dhw_log_to_structured] => Wrote structured CSV to {csv_output}")


def main():
    """
    Example CLI entry point:
      - Reads 'D:/Documents/E_Plus_2030_py/output/assigned/assigned_dhw_params.csv'
      - Transforms it, merges range fields, extracts E+ object references,
      - Writes 'D:/Documents/E_Plus_2030_py/output/assigned/structured_dhw_params.csv'
    """
    csv_in = r"D:\Documents\E_Plus_2030_py\output\assigned\assigned_dhw_params.csv"
    csv_out = r"D:\Documents\E_Plus_2030_py\output\assigned\structured_dhw_params.csv"

    transform_dhw_log_to_structured(
        csv_input=csv_in,
        csv_output=csv_out
    )

if __name__ == "__main__":
    main()
