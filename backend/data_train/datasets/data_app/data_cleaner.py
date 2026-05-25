import csv
import os

def clean_missing_prices(input_file, output_file):
    """
    Cleans a dataset by filling missing price values using Forward Fill.
    If the first few days are missing, it uses Backward Fill from the first valid price.
    """
    try:
        with open(input_file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
            
        # First pass: find the first non-empty value to use for initial empty rows
        first_valid = None
        for row in rows:
            if len(row) > 1 and row[1].strip():
                first_valid = row[1].strip()
                break
                
        # If no valid data found at all, we can't do anything
        if first_valid is None:
            print("No valid price data found in the file.")
            return

        last_valid = first_valid
        
        cleaned_rows = []
        for row in rows:
            date = row[0]
            price = row[1].strip() if len(row) > 1 else ""
            
            if not price:
                price = last_valid
            else:
                last_valid = price
                
            cleaned_rows.append([date, price])
            
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Save the cleaned data
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(cleaned_rows)
            
        print(f"Successfully cleaned data. Saved to {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    # Get the directory of the current script
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Input and output paths
    input_csv = os.path.join(base_path, 'datasets', 'raw', 'data_beras_diy_simple.csv')
    output_csv = os.path.join(base_path, 'datasets', 'processed', 'data_beras_diy_cleaned.csv')
    
    clean_missing_prices(input_csv, output_csv)
