import csv
import os
import datetime
from collections import defaultdict

def aggregate_monthly(input_file, output_file):
    """
    Aggregates daily price data to monthly data by calculating the monthly average.
    """
    try:
        monthly_data = defaultdict(list)
        
        with open(input_file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            for row in reader:
                if not row or len(row) < 2:
                    continue
                date_str = row[0]
                price_str = row[1]
                
                # Extract year-month, assuming format YYYY-MM-DD
                # e.g. "2021-01-01" -> "2021-01"
                month_key = date_str[:7] 
                
                try:
                    price = float(price_str)
                    monthly_data[month_key].append(price)
                except ValueError:
                    continue

        # Calculate average for each month
        monthly_averages = []
        for month in sorted(monthly_data.keys()):
            prices = monthly_data[month]
            avg_price = sum(prices) / len(prices)
            # Formatting to 2 decimal places
            monthly_averages.append([month, f"{avg_price:.2f}"])
            
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['bulan', 'harga_beras_rata_rata'])
            writer.writerows(monthly_averages)
            
        print(f"Monthly aggregated data successfully saved to {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

def aggregate_curah_hujan_monthly(input_file, output_file):
    """
    Aggregates daily rainfall data to monthly data by calculating the monthly sum.
    """
    try:
        monthly_data = defaultdict(float) # We sum the rainfall
        
        with open(input_file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            # YEAR,DOY,PRECTOTCORR,IMERG_PRECTOT
            
            for row in reader:
                if not row or len(row) < 3:
                    continue
                year_str = row[0]
                doy_str = row[1]
                prec_str = row[2]
                
                try:
                    year = int(year_str)
                    doy = int(doy_str)
                    prec = float(prec_str)
                    
                    # Convert YEAR and DOY to month
                    date = datetime.datetime(year, 1, 1) + datetime.timedelta(days=doy - 1)
                    month_key = date.strftime("%Y-%m")
                    
                    if prec >= 0:
                        monthly_data[month_key] += prec
                except ValueError:
                    continue

        # Sort the monthly data
        monthly_totals = []
        for month in sorted(monthly_data.keys()):
            total_prec = monthly_data[month]
            monthly_totals.append([month, f"{total_prec:.2f}"])
            
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['bulan', 'total_curah_hujan'])
            writer.writerows(monthly_totals)
            
        print(f"Monthly aggregated rainfall data successfully saved to {output_file}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

def merge_datasets(beras_file, curah_hujan_file, raw_dir, output_file):
    """
    Merges beras, curah_hujan, gkg, and produksi_padi monthly data.
    """
    try:
        # Read beras data
        beras_data = {}
        with open(beras_file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                beras_data[row['bulan']] = row['harga_beras_rata_rata']
                
        # Read curah hujan data
        hujan_data = {}
        with open(curah_hujan_file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                hujan_data[row['bulan']] = row['curah_hujan']
                
        # Read gkg and produksi data
        gkg_data = {}
        produksi_data = {}
        for year in range(2021, 2026):
            # GKG
            gkg_file = os.path.join(raw_dir, f'gkg_{year}.csv')
            if os.path.exists(gkg_file):
                with open(gkg_file, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if not row or 'bulan' not in row or not row['bulan'].strip():
                            continue
                        bulan = int(row['bulan'].strip())
                        month_key = f"{year}-{bulan:02d}"
                        gkg_data[month_key] = row['harga_gkg'].strip()
            
            # Produksi Padi
            produksi_file = os.path.join(raw_dir, f'produksi_padi_{year}.csv')
            if os.path.exists(produksi_file):
                with open(produksi_file, mode='r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if not row or 'bulan' not in row or not row['bulan'].strip():
                            continue
                        bulan = int(row['bulan'].strip())
                        month_key = f"{year}-{bulan:02d}"
                        produksi_data[month_key] = row['produksi_padi'].strip()
                
        # Get all unique months
        all_months = sorted(list(set(beras_data.keys()) | set(hujan_data.keys()) | set(gkg_data.keys()) | set(produksi_data.keys())))
        
        merged_data = []
        for month in all_months:
            harga_beras = beras_data.get(month, "")
            harga_gkg = gkg_data.get(month, "")
            hujan = hujan_data.get(month, "")
            produksi = produksi_data.get(month, "")
            merged_data.append({
                'tanggal': month, 
                'harga_beras': harga_beras, 
                'harga_gkg': harga_gkg,
                'curah_hujan': hujan,
                'produksi_padi': produksi
            })
            
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            fieldnames = ['tanggal', 'harga_beras', 'harga_gkg', 'curah_hujan', 'produksi_padi']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(merged_data)

        print(f"Merged data successfully saved to {output_file}")
        
    except Exception as e:
        print(f"An error occurred during merge: {e}")

if __name__ == '__main__':
    base_path = os.path.dirname(os.path.abspath(__file__))
    # input_csv = os.path.join(base_path, 'datasets', 'processed', 'data_beras_diy_cleaned.csv')
    output_csv = os.path.join(base_path, 'datasets', 'processed', 'data_beras_diy_monthly.csv')
    
    # aggregate_monthly(input_csv, output_csv)

    # curah_hujan_input = os.path.join(base_path, 'datasets', 'raw', 'curah_hujan.csv')
    curah_hujan_output = os.path.join(base_path, 'datasets', 'processed', 'curah_hujan_monthly.csv')
    
    # aggregate_curah_hujan_monthly(curah_hujan_input, curah_hujan_output)
    
    merged_output = os.path.join(base_path, 'datasets', 'processed', 'dataset_merged_beras_hujan.csv')
    raw_dir = os.path.join(base_path, 'datasets', 'raw')
    merge_datasets(output_csv, curah_hujan_output, raw_dir, merged_output)
