# postproc/merge_results.py

import os
import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def merge_all_results(
    base_output_dir,
    output_csv,
    convert_to_daily=False,
    daily_aggregator="mean"
):
    """
    Merges multiple simulation CSV files into one wide CSV, skipping *_Meter.csv or *_sz.csv.

    If convert_to_daily=True, it aggregates Hourly columns by day and merges with Daily columns.
    Otherwise, merges "as is."
    """

    data_dict = {}
    all_times = set()
    time_to_dt = {}  # Mapping from time_str to parsed_dt

    # Define valid aggregators
    aggregator_funcs = {
        "sum": np.sum,
        "mean": np.mean,
        "max": np.max,
        "min": np.min,
        "pick_first_hour": lambda x: x.iloc[0] if not x.empty else np.nan
    }

    if daily_aggregator not in aggregator_funcs:
        print(f"Warning: Aggregator '{daily_aggregator}' not recognized. Defaulting to 'mean'.")
        daily_aggregator = "mean"

    def aggregate_series(s, how):
        return aggregator_funcs.get(how, np.mean)(s)

    for root, dirs, files in os.walk(base_output_dir):
        for f in files:
            # Skip files containing '_Meter.csv' or '_sz.csv' (case-insensitive)
            if re.search(r'_Meter\.csv$', f, re.IGNORECASE) or re.search(r'_sz\.csv$', f, re.IGNORECASE):
                continue
            if not f.lower().endswith(".csv"):
                continue

            # Adjust the regex based on your file naming convention
            match = re.search(r'_bldg(\d+)\.csv$', f, re.IGNORECASE)
            if not match:
                continue
            bldg_id = int(match.group(1))

            file_path = os.path.join(root, f)
            print(f"[merge_all_results] Reading {file_path}, Building {bldg_id}")

            try:
                df = pd.read_csv(file_path, header=0, low_memory=False)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue

            if "Date/Time" not in df.columns:
                print(f"Warning: No 'Date/Time' column in {file_path}, skipping.")
                continue

            # Handle '24:00:00' by converting it to '00:00:00' of the next day
            def correct_time(x):
                x = str(x).strip()  # Ensure x is a string and remove leading/trailing spaces
                if '24:00:00' in x:
                    parts = x.split()
                    if len(parts) >= 1:
                        date_part = parts[0]
                        try:
                            date_obj = datetime.strptime(date_part, "%m/%d")
                            corrected_date = date_obj + timedelta(days=1)
                            return corrected_date.strftime("%m/%d 00:00:00")
                        except ValueError:
                            print(f"Warning: Unable to parse date part '{date_part}' in '{x}'.")
                            return x  # Return as is if parsing fails
                    else:
                        return x
                return x

            df["Date/Time_corrected"] = df["Date/Time"].astype(str).apply(correct_time)

            # Parse the corrected date/time
            def parse_dt(x):
                x = x.strip()  # Remove leading/trailing spaces
                parts = x.split()
                if len(parts) == 1:
                    # e.g., "01/21" => daily data
                    try:
                        return pd.to_datetime(parts[0] + "/2022", format="%m/%d/%Y", errors="coerce")
                    except:
                        return pd.NaT
                elif len(parts) == 2:
                    # "MM/DD" + "HH:MM:SS"
                    date_part, time_part = parts
                    # Append a dummy year, e.g., 2022
                    try:
                        return pd.to_datetime(f"2022/{date_part} {time_part}", format="%Y/%m/%d %H:%M:%S", errors="coerce")
                    except:
                        return pd.NaT
                return pd.NaT

            df["parsed_dt"] = df["Date/Time_corrected"].apply(parse_dt)

            for col in df.columns:
                if col in ["Date/Time", "Date/Time_corrected", "parsed_dt"]:
                    continue

                # Detect frequency
                freq_mode = "Unknown"
                if "(Hourly)" in col:
                    freq_mode = "Hourly"
                elif "(Daily)" in col:
                    freq_mode = "Daily"

                key = (bldg_id, col)

                if convert_to_daily:
                    subdf = pd.DataFrame({
                        "dt": df["parsed_dt"],
                        "val": pd.to_numeric(df[col], errors='coerce')  # Ensure numerical values
                    })

                    if freq_mode == "Hourly":
                        # Group by day
                        subdf.dropna(subset=["dt", "val"], inplace=True)
                        subdf["day_str"] = subdf["dt"].dt.strftime("%m/%d")
                        grouped = subdf.groupby("day_str")["val"]
                        day_vals = grouped.apply(lambda x: aggregate_series(x, daily_aggregator))

                        for day_s, v in day_vals.items():
                            if key not in data_dict:
                                data_dict[key] = {}
                            data_dict[key][day_s] = v

                    elif freq_mode == "Daily":
                        # One value per day
                        subdf.dropna(subset=["val"], inplace=True)
                        for i, row in subdf.iterrows():
                            dt_val = row["dt"]
                            val = row["val"]
                            if pd.isna(dt_val):
                                day_s = f"Day_{i}"
                            else:
                                day_s = dt_val.strftime("%m/%d")
                            if key not in data_dict:
                                data_dict[key] = {}
                            data_dict[key][day_s] = val

                    else:
                        # Treat as daily data if frequency is unknown
                        subdf.dropna(subset=["val"], inplace=True)
                        for i, row in subdf.iterrows():
                            dt_val = row["dt"]
                            val = row["val"]
                            if pd.isna(dt_val):
                                day_s = f"Day_{i}"
                            else:
                                day_s = dt_val.strftime("%m/%d")
                            if key not in data_dict:
                                data_dict[key] = {}
                            data_dict[key][day_s] = val

                else:
                    # Keep "as is" with original time strings
                    subdf = pd.DataFrame({
                        "time_str": df["Date/Time_corrected"].astype(str).apply(lambda x: x.strip()),  # Strip spaces
                        "val": pd.to_numeric(df[col], errors='coerce'),  # Ensure numerical values
                        "parsed_dt": df["parsed_dt"]  # Include parsed_dt for sorting
                    })
                    subdf.dropna(subset=["val"], inplace=True)

                    for i, row in subdf.iterrows():
                        tstr = row["time_str"]
                        val = row["val"]
                        parsed_dt = row["parsed_dt"]
                        if key not in data_dict:
                            data_dict[key] = {}
                        data_dict[key][tstr] = val
                        all_times.add(tstr)
                        # Store parsed_dt for sorting
                        if tstr not in time_to_dt:
                            time_to_dt[tstr] = parsed_dt

    # Determine sorted times
    if convert_to_daily:
        # Gather all unique day strings
        day_strings = set()
        for submap in data_dict.values():
            day_strings.update(submap.keys())
        try:
            sorted_times = sorted(list(day_strings), key=lambda x: datetime.strptime(x, "%m/%d"))
        except ValueError as ve:
            print(f"Error in sorting day strings: {ve}")
            sorted_times = sorted(list(day_strings))
        columns = ["BuildingID", "VariableName"] + sorted_times
    else:
        # Sort times based on parsed_dt
        try:
            # Create a list of tuples (time_str, parsed_dt) and sort by parsed_dt
            sorted_times = sorted(list(all_times), key=lambda x: (time_to_dt.get(x) if pd.notna(time_to_dt.get(x)) else datetime.min))
        except Exception as e:
            print(f"Error in sorting times: {e}")
            # Fallback to alphabetical sorting if sorting by datetime fails
            sorted_times = sorted(list(all_times))
        columns = ["BuildingID", "VariableName"] + sorted_times

    # Prepare rows for the final DataFrame
    rows = []
    for (bldg_id, var_name), tmap in data_dict.items():
        rowdata = [bldg_id, var_name]
        for t in sorted_times:
            val = tmap.get(t, np.nan)  # Use NaN for missing values
            rowdata.append(val)
        rows.append(rowdata)

    # Create the final DataFrame
    final_df = pd.DataFrame(rows, columns=columns)
    final_df.sort_values(by=["BuildingID", "VariableName"], inplace=True)

    # Save to CSV
    try:
        final_df.to_csv(output_csv, index=False)
        print(f"[merge_all_results] Successfully wrote merged CSV to {output_csv}")
    except Exception as e:
        print(f"Error writing to {output_csv}: {e}")




# postproc/postprocess.py

from idf_objects.postproc.merge_results import merge_all_results

def postprocess():
    base_output_dir = "D:/Sim_Results"
    out_csv_1 = "D:/merged_as_is.csv"
    out_csv_2 = "D:/merged_daily_mean.csv"
    out_csv_3 = "D:/merged_daily_sum.csv"

    # 1) Merge as is => some columns daily, some columns hourly
    merge_all_results(
        base_output_dir=base_output_dir,
        output_csv=out_csv_1,
        convert_to_daily=False
    )

    # 2) Convert everything to daily => aggregator=mean
    merge_all_results(
        base_output_dir=base_output_dir,
        output_csv=out_csv_2,
        convert_to_daily=True,
        daily_aggregator="mean"
    )

    # 3) Convert everything to daily => aggregator=sum
    merge_all_results(
        base_output_dir=base_output_dir,
        output_csv=out_csv_3,
        convert_to_daily=True,
        daily_aggregator="sum"
    )

if __name__ == "__main__":
    postprocess()
