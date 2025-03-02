import os
import pandas as pd

def check_number_of_columns_and_extract(file_list_path, expected_columns, output_txt_path):
    """
    Reads a text file line by line. Each line is a path to a CSV or Excel file.
    Checks if each file has the expected number of columns,
    then appends a text-based report (including file content in CSV format) to 'output_txt_path'.
    
    IMPORTANT CHANGE:
    - If a file has *more* columns than expected, only the first 'expected_columns' columns
      are written to the output file.
    - If a file has *fewer* columns than expected, all columns in the file are still written,
      because there's nothing extra to trim. (You can adjust if you prefer an error or different behavior.)
    """
    with open(file_list_path, 'r', encoding='utf-8') as f:
        file_paths = [line.strip() for line in f if line.strip()]

    # Open the output text file in write mode
    with open(output_txt_path, 'w', encoding='utf-8') as out:
        out.write("=== CHECK NUMBER OF COLUMNS REPORT ===\n\n")
        
        for file_path in file_paths:
            out.write(f"File: {file_path}\n")

            if not os.path.isfile(file_path):
                out.write("  Status: File not found\n\n")
                continue
            
            ext = os.path.splitext(file_path)[1].lower()
            try:
                # Load CSV or Excel
                if ext in [".csv", ".txt"]:
                    df = pd.read_csv(file_path)
                elif ext in [".xls", ".xlsx", ".xlsm"]:
                    df = pd.read_excel(file_path)
                else:
                    out.write(f"  Status: Unsupported file extension: {ext}\n\n")
                    continue

                found_columns = df.shape[1]
                status = "OK" if found_columns == expected_columns else "Mismatch"
                
                out.write(f"  Status: {status}\n")
                out.write(f"  Found columns: {found_columns}\n")
                out.write(f"  Expected columns: {expected_columns}\n\n")

                # Trim DataFrame columns if we have more columns than expected
                if found_columns > expected_columns:
                    trimmed_df = df.iloc[:, :expected_columns]
                else:
                    # If fewer or equal to expected, just use the original
                    trimmed_df = df

                # Now write the actual data from the (trimmed) DataFrame as CSV text
                out.write("  -- File Content Start --\n")
                csv_text = trimmed_df.to_csv(index=False)
                out.write(csv_text)
                out.write("  -- File Content End --\n\n")

            except Exception as e:
                out.write(f"  Status: Error reading file: {e}\n\n")


def check_number_of_rows_and_extract(file_list_path, expected_rows, output_txt_path):
    """
    Reads a text file line by line. Each line is a path to a CSV or Excel file.
    Checks if each file has the expected number of rows,
    then appends a text-based report (including file content in CSV format) to 'output_txt_path'.
    
    IMPORTANT CHANGE:
    - If a file has *more* rows than expected, only the first 'expected_rows' rows
      are written to the output file.
    - If a file has *fewer* rows than expected, all rows in the file are still written.
    """
    with open(file_list_path, 'r', encoding='utf-8') as f:
        file_paths = [line.strip() for line in f if line.strip()]

    with open(output_txt_path, 'w', encoding='utf-8') as out:
        out.write("=== CHECK NUMBER OF ROWS REPORT ===\n\n")
        
        for file_path in file_paths:
            out.write(f"File: {file_path}\n")

            if not os.path.isfile(file_path):
                out.write("  Status: File not found\n\n")
                continue
            
            ext = os.path.splitext(file_path)[1].lower()
            try:
                # Load CSV or Excel
                if ext in [".csv", ".txt"]:
                    df = pd.read_csv(file_path)
                elif ext in [".xls", ".xlsx", ".xlsm"]:
                    df = pd.read_excel(file_path)
                else:
                    out.write(f"  Status: Unsupported file extension: {ext}\n\n")
                    continue

                found_rows = df.shape[0]
                status = "OK" if found_rows == expected_rows else "Mismatch"
                
                out.write(f"  Status: {status}\n")
                out.write(f"  Found rows: {found_rows}\n")
                out.write(f"  Expected rows: {expected_rows}\n\n")

                # Trim DataFrame rows if we have more rows than expected
                if found_rows > expected_rows:
                    trimmed_df = df.iloc[:expected_rows, :]
                else:
                    # If fewer or equal to expected, just use the original
                    trimmed_df = df

                # Now write the actual data from the (trimmed) DataFrame as CSV text
                out.write("  -- File Content Start --\n")
                csv_text = trimmed_df.to_csv(index=False)
                out.write(csv_text)
                out.write("  -- File Content End --\n\n")

            except Exception as e:
                out.write(f"  Status: Error reading file: {e}\n\n")


if __name__ == "__main__":
    """
    Optional CLI usage example:
    
    python check_files.py columns file_list.txt 5 output.txt
    python check_files.py rows file_list.txt 100 output.txt
    """
    import sys
    if len(sys.argv) < 5:
        print("Usage:")
        print("  python check_files.py columns <file_list_path> <expected_columns> <output_txt_path>")
        print("  python check_files.py rows <file_list_path> <expected_rows> <output_txt_path>")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    file_list = sys.argv[2]
    expected_value = int(sys.argv[3])
    output_file = sys.argv[4]
    
    if mode == "columns":
        check_number_of_columns_and_extract(file_list, expected_value, output_file)
    elif mode == "rows":
        check_number_of_rows_and_extract(file_list, expected_value, output_file)
    else:
        print("Mode should be either 'columns' or 'rows'.")
        sys.exit(1)
