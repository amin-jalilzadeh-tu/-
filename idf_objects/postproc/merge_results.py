# postproc/merge_results.py

import os
import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from calendar import month_name

def merge_all_results(
    base_output_dir,
    output_csv,
    convert_to_daily=False,
    daily_aggregator="mean",
    convert_to_monthly=False,
    monthly_aggregator="mean",
    postproc_log=None  # <--- new
):
    """
    Merges multiple simulation CSV files into one wide CSV, skipping *_Meter.csv or *_sz.csv.

    Parameters:
    - base_output_dir (str): Directory containing the CSV files to merge.
    - output_csv (str): Path to the output merged CSV file.
    - convert_to_daily (bool): If True, aggregates Hourly data to Daily.
    - daily_aggregator (str): Aggregation method for daily conversion ('mean', 'sum', etc.).
    - convert_to_monthly (bool): If True, aggregates Daily data to Monthly.
    - monthly_aggregator (str): Aggregation method for monthly conversion ('mean', 'sum', etc.).

    Returns:
    - None: Writes the merged data to the specified CSV file.
    """
    if postproc_log is not None:
        postproc_log["base_output_dir"] = base_output_dir
        postproc_log["output_csv"] = output_csv
        postproc_log["convert_to_daily"] = convert_to_daily
        postproc_log["daily_aggregator"] = daily_aggregator
        postproc_log["convert_to_monthly"] = convert_to_monthly
        postproc_log["monthly_aggregator"] = monthly_aggregator


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

    # Validate user-provided aggregators
    if convert_to_daily and daily_aggregator not in aggregator_funcs:
        print(f"Warning: Aggregator '{daily_aggregator}' not recognized. Defaulting to 'mean'.")
        daily_aggregator = "mean"

    if convert_to_monthly and monthly_aggregator not in aggregator_funcs:
        print(f"Warning: Aggregator '{monthly_aggregator}' not recognized. Defaulting to 'mean'.")
        monthly_aggregator = "mean"

    def aggregate_series(s, how):
        """Aggregate a pandas Series using one of the known aggregator functions."""
        return aggregator_funcs.get(how, np.mean)(s)

    # Create a mapping from month name to month number for parsing
    month_to_num = {month: index for index, month in enumerate(month_name) if month}

    ###################################################
    # 1) Traverse the directory and read each CSV
    ###################################################
    for root, dirs, files in os.walk(base_output_dir):
        for f in files:
            # Skip files containing '_Meter.csv' or '_sz.csv' (case-insensitive)
            if re.search(r'_Meter\.csv$', f, re.IGNORECASE) or re.search(r'_sz\.csv$', f, re.IGNORECASE):
                continue
            if not f.lower().endswith(".csv"):
                continue

            # Adjust the regex based on your file naming convention
            # e.g., "simulation_bldg0.csv" => group(1) = 0
            match = re.search(r'_bldg(\d+)\.csv$', f, re.IGNORECASE)
            if not match:
                continue
            bldg_id = int(match.group(1))

            file_path = os.path.join(root, f)
            print(f"[merge_all_results] Reading {file_path}, Building {bldg_id}")

            ###################################################
            # 2) Read CSV into a DataFrame
            ###################################################
            try:
                df = pd.read_csv(file_path, header=0, low_memory=False)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue

            if "Date/Time" not in df.columns:
                print(f"Warning: No 'Date/Time' column in {file_path}, skipping.")
                continue

            ###################################################
            # 3) Correct '24:00:00' => '00:00:00' next day
            ###################################################
            def correct_time(x):
                """Handle '24:00:00' by converting it to '00:00:00' of the next day."""
                x = str(x).strip()  # Ensure x is a string
                if '24:00:00' in x:
                    parts = x.split()
                    if len(parts) >= 1:
                        date_part = parts[0]
                        try:
                            # Check if date_part is a month name
                            if date_part in month_to_num:
                                # Assign first day of the next month
                                month_num = month_to_num[date_part]
                                if month_num == 12:
                                    corrected_date = datetime(2022, 1, 1)
                                else:
                                    corrected_date = datetime(2022, month_num + 1, 1)
                            else:
                                # Assume MM/DD format
                                date_obj = datetime.strptime(date_part, "%m/%d")
                                corrected_date = date_obj + timedelta(days=1)
                            return corrected_date.strftime("%m/%d 00:00:00")
                        except ValueError:
                            print(f"Warning: Unable to parse date part '{date_part}' in '{x}'.")
                            return x  # Return original if parsing fails
                    else:
                        return x
                return x

            df["Date/Time_corrected"] = df["Date/Time"].astype(str).apply(correct_time)

            ###################################################
            # 4) Parse the corrected date/time
            ###################################################
            def parse_dt(x):
                """
                Parses various forms of Date/Time:
                  - Single piece (e.g. 'January', or '4'):
                      * If it is a month name => monthly data => datetime(2022, month_num, 1).
                      * If it is an integer 0-23 => interpret as hour => Jan 1, 2022, at that hour.
                  - Two pieces (e.g. '01/21 00:10:00', or '01/21 4'):
                      * If second part is recognized as time, parse with date. 
                  - Otherwise => pd.NaT.
                """
                x = x.strip()
                parts = x.split()
                if len(parts) == 1:
                    # Could be a month name or a single hour
                    single_part = parts[0]
                    # 1) Check if it's a month name
                    if single_part in month_to_num:
                        return datetime(2022, month_to_num[single_part], 1)
                    # 2) Check if it's an integer 0-23 => interpret as hour
                    try:
                        hr = int(single_part)
                        if 0 <= hr <= 23:
                            return datetime(2022, 1, 1, hr, 0, 0)
                        else:
                            return pd.NaT
                    except:
                        return pd.NaT
                elif len(parts) == 2:
                    # Typically "MM/DD HH:MM:SS" or "MM/DD HH" or "MM/DD HH:MM"
                    date_part, time_part = parts

                    # If date_part is a month name => not standard -> skip
                    if date_part in month_to_num:
                        return pd.NaT

                    # Parse date part
                    try:
                        date_obj = datetime.strptime(date_part, "%m/%d")
                    except ValueError:
                        return pd.NaT

                    # Now parse the time part
                    if ":" in time_part:
                        # Try known formats in sequence
                        t_obj = None
                        for fmt in ["%H:%M:%S", "%H:%M"]:
                            try:
                                t_obj = datetime.strptime(time_part, fmt)
                                break
                            except ValueError:
                                pass
                        if t_obj is None:
                            return pd.NaT
                        # Combine date_obj + time_obj
                        dt_combined = datetime(
                            2022, date_obj.month, date_obj.day,
                            t_obj.hour, t_obj.minute, t_obj.second
                        )
                        return dt_combined
                    else:
                        # If there's no colon, interpret as hour
                        try:
                            hr = int(time_part)
                            if 0 <= hr <= 23:
                                return datetime(2022, date_obj.month, date_obj.day, hr, 0, 0)
                            else:
                                return pd.NaT
                        except:
                            return pd.NaT
                else:
                    # More than 2 pieces => unknown
                    return pd.NaT

            df["parsed_dt"] = df["Date/Time_corrected"].apply(parse_dt)

            ###################################################
            # 5) Process each column (other than date/time)
            ###################################################
            for col in df.columns:
                if col in ["Date/Time", "Date/Time_corrected", "parsed_dt"]:
                    continue

                # Detect frequency
                # ------------------------------------------------------
                # Here we handle (Hourly), (Daily), (Monthly), (TimeStep).
                # We interpret (TimeStep) as if it were "Hourly" for aggregation.
                # ------------------------------------------------------
                freq_mode = "Unknown"
                if "(Hourly)" in col or "(TimeStep)" in col:
                    freq_mode = "Hourly"
                elif "(Daily)" in col:
                    freq_mode = "Daily"
                elif "(Monthly)" in col:
                    freq_mode = "Monthly"

                key = (bldg_id, col)

                ###################################################
                # 6) If converting, do daily or monthly aggregation
                ###################################################
                if convert_to_daily or convert_to_monthly:
                    subdf = pd.DataFrame({
                        "dt": df["parsed_dt"],
                        "val": pd.to_numeric(df[col], errors='coerce')  # numeric
                    })

                    if freq_mode == "Hourly":
                        # Convert Hourly (or TimeStep) to daily if requested
                        if convert_to_daily:
                            # Aggregate Hourly to Daily
                            subdf.dropna(subset=["dt", "val"], inplace=True)
                            subdf["day_str"] = subdf["dt"].dt.strftime("%m/%d")
                            grouped = subdf.groupby("day_str")["val"]
                            day_vals = grouped.apply(lambda x: aggregate_series(x, daily_aggregator))

                            for day_s, v in day_vals.items():
                                if key not in data_dict:
                                    data_dict[key] = {}
                                data_dict[key][day_s] = v

                    elif freq_mode == "Daily":
                        # If converting daily to monthly
                        if convert_to_monthly:
                            # Aggregate Daily to Monthly
                            subdf.dropna(subset=["dt", "val"], inplace=True)
                            subdf["month_str"] = subdf["dt"].dt.strftime("%B")
                            grouped = subdf.groupby("month_str")["val"]
                            month_vals = grouped.apply(lambda x: aggregate_series(x, monthly_aggregator))

                            for month_s, v in month_vals.items():
                                if key not in data_dict:
                                    data_dict[key] = {}
                                data_dict[key][month_s] = v
                        else:
                            # Keep Daily as is (no monthly conversion)
                            subdf.dropna(subset=["val"], inplace=True)
                            for i, row in subdf.iterrows():
                                dt_val = row["dt"]
                                val = row["val"]
                                if pd.isna(dt_val):
                                    day_s = f"Day_{i}"  # fallback
                                else:
                                    day_s = dt_val.strftime("%m/%d")
                                if key not in data_dict:
                                    data_dict[key] = {}
                                data_dict[key][day_s] = val

                    elif freq_mode == "Monthly":
                        # If converting monthly or leaving as is
                        subdf.dropna(subset=["val"], inplace=True)
                        for i, row in subdf.iterrows():
                            dt_val = row["dt"]
                            val = row["val"]
                            if pd.isna(dt_val):
                                month_s = f"Month_{i}"
                            else:
                                month_s = dt_val.strftime("%B")
                            if key not in data_dict:
                                data_dict[key] = {}
                            data_dict[key][month_s] = val
                    else:
                        # Unknown frequency => skip or warn
                        print(f"Warning: Unknown frequency for column '{col}' in Building {bldg_id}. Skipping.")
                        continue

                ###################################################
                # 7) If not converting => keep as-is (time_str keys)
                ###################################################
                else:
                    # Keep time-based data as-is
                    subdf = pd.DataFrame({
                        "time_str": df["Date/Time_corrected"].astype(str).apply(lambda x: x.strip()),
                        "val": pd.to_numeric(df[col], errors='coerce'),
                        "parsed_dt": df["parsed_dt"]
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
                        if tstr not in time_to_dt:
                            time_to_dt[tstr] = parsed_dt

    ###################################################
    # 8) Build a sorted list of time columns
    ###################################################
    if convert_to_monthly and convert_to_daily:
        # Convert Hourly -> Daily -> Monthly
        # We end up with month strings and day strings
        day_strings = set()
        month_strings = set()
        for submap in data_dict.values():
            for key_str in submap.keys():
                # day format = "MM/DD"
                # month format = "January", "February", ...
                if re.match(r'\d{2}/\d{2}', key_str):
                    day_strings.add(key_str)
                elif key_str in month_to_num:
                    month_strings.add(key_str)

        # Sort day strings
        try:
            sorted_days = sorted(list(day_strings), key=lambda x: datetime.strptime(x, "%m/%d"))
        except ValueError as ve:
            print(f"Error in sorting day strings: {ve}")
            sorted_days = sorted(list(day_strings))

        # Sort month strings
        try:
            sorted_months = sorted(list(month_strings), key=lambda x: month_to_num.get(x, 0))
        except ValueError as ve:
            print(f"Error in sorting month strings: {ve}")
            sorted_months = sorted(list(month_strings))

        sorted_times = sorted_months + sorted_days
        columns = ["BuildingID", "VariableName"] + sorted_times

    elif convert_to_monthly:
        # Only monthly
        month_strings = set()
        for submap in data_dict.values():
            for key_str in submap.keys():
                if key_str in month_to_num:
                    month_strings.add(key_str)
        try:
            sorted_times = sorted(list(month_strings), key=lambda x: month_to_num.get(x, 0))
        except ValueError as ve:
            print(f"Error in sorting month strings: {ve}")
            sorted_times = sorted(list(month_strings))
        columns = ["BuildingID", "VariableName"] + sorted_times

    elif convert_to_daily:
        # Only daily
        day_strings = set()
        for submap in data_dict.values():
            for key_str in submap.keys():
                day_strings.add(key_str)
        try:
            sorted_times = sorted(list(day_strings), key=lambda x: datetime.strptime(x, "%m/%d"))
        except ValueError as ve:
            print(f"Error in sorting day strings: {ve}")
            sorted_times = sorted(list(day_strings))
        columns = ["BuildingID", "VariableName"] + sorted_times

    else:
        # As is
        # Sort times by parsed_dt if available
        def safe_dt(tstr):
            dtval = time_to_dt.get(tstr)
            return dtval if pd.notna(dtval) else datetime.min

        try:
            sorted_times = sorted(list(all_times), key=lambda x: safe_dt(x))
        except Exception as e:
            print(f"Error in sorting times: {e}")
            sorted_times = sorted(list(all_times))

        columns = ["BuildingID", "VariableName"] + sorted_times

    ###################################################
    # 9) Build final DataFrame and write CSV
    ###################################################
    rows = []
    for (bldg_id, var_name), tmap in data_dict.items():
        rowdata = [bldg_id, var_name]
        for t in sorted_times:
            val = tmap.get(t, np.nan)  # Use NaN for missing
            rowdata.append(val)
        rows.append(rowdata)

    final_df = pd.DataFrame(rows, columns=columns)
    final_df.sort_values(by=["BuildingID", "VariableName"], inplace=True)

    # Save to CSV
    try:
        final_df.to_csv(output_csv, index=False)
        print(f"[merge_all_results] Successfully wrote merged CSV to {output_csv}")
        return
    except Exception as e:
        print(f"Error writing to {output_csv}: {e}")

