import pandas as pd
import os

def select_columns(input_file, output_dir, columns):
    """
    Reads a CSV file, selects specific columns, and saves the new data.
    
    Args:
        input_file (str): Path to the input CSV file.
        output_dir (str): Path to the directory where the cleaned file will be saved.
        columns (list): List of column names to keep.
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
        filtered_df = df[actual_cols]
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine output filename
        base_name = os.path.basename(input_file)
        output_file = os.path.join(output_dir, base_name)
        
        # Save the filtered dataframe
        filtered_df.to_csv(output_file, index=False)
        print(f"Successfully saved cleaned data to {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Get the directory of the current script to make paths relative to it
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Paths for the specific request
    input_csv = os.path.join(base_path, "datasets", "raw", "data_beras_diy.csv")
    output_directory = os.path.join(base_path, "datasets", "processed")
    
    # Columns requested by the user
    cols_to_keep = ["Tanggal_Loop", "Harga_Rp"]
    
    select_columns(input_csv, output_directory, cols_to_keep)
