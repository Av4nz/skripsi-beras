import pandas as pd
import os

def select_columns(input_file, output_path, columns, rename_dict=None):
    """
    Reads a CSV file, selects specific columns, optionally renames them, and saves the new data.
    
    Args:
        input_file (str): Path to the input CSV file.
        output_path (str): Path to the output CSV file or directory.
        columns (list): List of column names to keep.
        rename_dict (dict, optional): Dictionary mapping old column names to new column names.
    """
    try:
        # Load the data
        df = pd.read_csv(input_file)
        
        # Case-insensitive column matching to ensure it works even if casing is slightly off
        col_map = {c.lower(): c for c in df.columns}
        actual_cols = []
        for col in columns:
            if col in df.columns:
                actual_cols.append(col)
            elif col.lower() in col_map:
                actual_cols.append(col_map[col.lower()])
            else:
                raise ValueError(f"Column '{col}' not found in the dataset.")
                
        # Select the columns
        filtered_df = df[actual_cols].copy()
        
        # Rename columns if requested
        if rename_dict:
            filtered_df.rename(columns=rename_dict, inplace=True)
        
        # Handle output path (if it ends with .csv, treat it as a file; else, a directory)
        if output_path.endswith('.csv'):
            output_file = output_path
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
        else:
            os.makedirs(output_path, exist_ok=True)
            base_name = os.path.basename(input_file)
            output_file = os.path.join(output_path, base_name)
        
        # Save the filtered dataframe
        filtered_df.to_csv(output_file, index=False)
        print(f"Successfully saved cleaned data to {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Get the directory of the current script to make paths relative to it
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Paths for the specific request
    input_csv = os.path.join(base_path, "datav2", "beras", "(raw)beras_2025-2026_daily.csv")
    output_csv = os.path.join(base_path, "datav2", "beras", "beras_2025-2026_daily.csv")
    
    # Columns requested by the user
    cols_to_keep = ["Tanggal_Loop", "Harga_Rp"]
    
    # Renaming mapping
    rename_mapping = {"Tanggal_Loop": "tanggal", "Harga_Rp": "harga_beras"}
    
    select_columns(input_csv, output_csv, cols_to_keep, rename_dict=rename_mapping)
