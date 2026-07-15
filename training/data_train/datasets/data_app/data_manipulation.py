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
    Expects CSV with columns: time (YYYY-MM-DD), precipitation_sum (mm).
    """
    try:
        monthly_data = defaultdict(float) # We sum the rainfall
        
        with open(input_file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            for row in reader:
                if not row or len(row) < 2:
                    continue
                date_str = row[0]
                prec_str = row[1]
                
                # Extract year-month, assuming format YYYY-MM-DD
                # e.g. "2018-01-01" -> "2018-01"
                month_key = date_str[:7]
                
                try:
                    prec = float(prec_str)
                    
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

def extract_columns(input_file, output_dir):
    """
    Extracts curah_hujan, produksi_padi, inflasi_pangan columns into separate files.
    Each file will contain tanggal, tahun, and the respective column.
    """
    try:
        curah_hujan_data = []
        produksi_padi_data = []
        inflasi_pangan_data = []
        
        with open(input_file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tanggal = row.get('tanggal')
                tahun = row.get('tahun')
                
                curah_hujan_data.append({'tanggal': tanggal, 'tahun': tahun, 'curah_hujan': row.get('curah_hujan')})
                produksi_padi_data.append({'tanggal': tanggal, 'tahun': tahun, 'produksi_padi': row.get('produksi_padi')})
                inflasi_pangan_data.append({'tanggal': tanggal, 'tahun': tahun, 'inflasi_pangan': row.get('inflasi_pangan')})
                
        os.makedirs(output_dir, exist_ok=True)
        
        # Write curah_hujan
        ch_file = os.path.join(output_dir, 'curah_hujan_2021-2025.csv')
        with open(ch_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['tanggal', 'tahun', 'curah_hujan'])
            writer.writeheader()
            writer.writerows(curah_hujan_data)
            
        # Write produksi_padi
        pp_file = os.path.join(output_dir, 'produksi_padi_2021-2025.csv')
        with open(pp_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['tanggal', 'tahun', 'produksi_padi'])
            writer.writeheader()
            writer.writerows(produksi_padi_data)
            
        # Write inflasi_pangan
        ip_file = os.path.join(output_dir, 'inflasi_pangan_2021-2025.csv')
        with open(ip_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['tanggal', 'tahun', 'inflasi_pangan'])
            writer.writeheader()
            writer.writerows(inflasi_pangan_data)
            
        print(f"Extracted columns successfully saved to {output_dir}")
        
    except Exception as e:
        print(f"An error occurred during extraction: {e}")

def merge_inflasi(input_files, output_file):
    """
    Merges multiple monthly food-inflation CSV files into one chronological file.
    Handles both schemas present in the inflasi datasets:
      - 'tahun,bulan,inflasi_pangan'   (bulan as integer 1-12)
      - 'tanggal,tahun,inflasi_pangan' (tanggal as YYYY-MM-DD)
    Output columns: tanggal,tahun,inflasi_pangan (tanggal = first day of month).
    Files are processed in the given order; on overlapping months the later
    file wins. Uses utf-8-sig so a leading BOM is stripped automatically.
    """
    try:
        merged = {}  # 'YYYY-MM' -> [tanggal, tahun, inflasi_pangan]

        for input_file in input_files:
            if not os.path.exists(input_file):
                print(f"Warning: file not found, skipping: {input_file}")
                continue

            with open(input_file, mode='r', newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row:
                        continue

                    inflasi = (row.get('inflasi_pangan') or '').strip()
                    if inflasi == '':
                        continue

                    tanggal = (row.get('tanggal') or '').strip()
                    if tanggal:
                        # Schema: tanggal,tahun,inflasi_pangan
                        tahun = (row.get('tahun') or tanggal[:4]).strip()
                        month_key = tanggal[:7]
                    else:
                        # Schema: tahun,bulan,inflasi_pangan
                        tahun = (row.get('tahun') or '').strip()
                        bulan_str = (row.get('bulan') or '').strip()
                        if not tahun or not bulan_str:
                            continue
                        bulan = int(bulan_str)
                        tanggal = f"{tahun}-{bulan:02d}-01"
                        month_key = f"{tahun}-{bulan:02d}"

                    merged[month_key] = [tanggal, tahun, inflasi]

        rows_out = [merged[key] for key in sorted(merged.keys())]

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['tanggal', 'tahun', 'inflasi_pangan'])
            writer.writerows(rows_out)

        print(f"Merged inflasi data ({len(rows_out)} months) successfully saved to {output_file}")

    except Exception as e:
        print(f"An error occurred during inflasi merge: {e}")

def merge_produksi_padi(input_files, output_file):
    """
    Merges multiple monthly rice-production CSV files into one chronological file.
    Handles both schemas present in the produksi_padi datasets:
      - 'tahun,bulan,produksi_padi'   (bulan as integer 1-12)
      - 'tanggal,tahun,produksi_padi' (tanggal as YYYY-MM-DD)
    Output columns: tanggal,tahun,produksi_padi (tanggal = first day of month).
    Files are processed in the given order; on overlapping months the later
    file wins. Uses utf-8-sig so a leading BOM is stripped automatically.
    """
    try:
        merged = {}  # 'YYYY-MM' -> [tanggal, tahun, produksi_padi]

        for input_file in input_files:
            if not os.path.exists(input_file):
                print(f"Warning: file not found, skipping: {input_file}")
                continue

            with open(input_file, mode='r', newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row:
                        continue

                    produksi = (row.get('produksi_padi') or '').strip()
                    if produksi == '':
                        continue

                    tanggal = (row.get('tanggal') or '').strip()
                    if tanggal:
                        # Schema: tanggal,tahun,produksi_padi
                        tahun = (row.get('tahun') or tanggal[:4]).strip()
                        month_key = tanggal[:7]
                    else:
                        # Schema: tahun,bulan,produksi_padi
                        tahun = (row.get('tahun') or '').strip()
                        bulan_str = (row.get('bulan') or '').strip()
                        if not tahun or not bulan_str:
                            continue
                        bulan = int(bulan_str)
                        tanggal = f"{tahun}-{bulan:02d}-01"
                        month_key = f"{tahun}-{bulan:02d}"

                    merged[month_key] = [tanggal, tahun, produksi]

        rows_out = [merged[key] for key in sorted(merged.keys())]

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['tanggal', 'tahun', 'produksi_padi'])
            writer.writerows(rows_out)

        print(f"Merged produksi_padi data ({len(rows_out)} months) successfully saved to {output_file}")

    except Exception as e:
        print(f"An error occurred during produksi_padi merge: {e}")

def merge_all_features(base_dir, output_file):
    """
    Merge the five monthly feature files (beras, gkg, curah_hujan, produksi_padi,
    inflasi_pangan) into one dataset with the exact column order of
    harga_beras_2021_2025.csv:
        tanggal,tahun,bulan,lebaran,harga_beras,harga_gkg,
        curah_hujan,produksi_padi,inflasi_pangan
    Every file is keyed on its month (YYYY-MM). The 'lebaran' column has no
    source file and is filled with 0. Values are carried through verbatim.
    """
    try:
        def read_monthly(path, date_col, value_col):
            data = {}
            if not os.path.exists(path):
                print(f"Warning: file not found, skipping: {path}")
                return data
            with open(path, mode='r', newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = (row.get(date_col) or '').strip()[:7]  # 'YYYY-MM'
                    if not key:
                        continue
                    data[key] = (row.get(value_col) or '').strip()
            return data

        d = os.path.join(base_dir, 'datav2')
        beras = read_monthly(os.path.join(d, 'beras', 'beras_2018-2026_fix.csv'), 'bulan', 'harga_beras_rata_rata')
        gkg = read_monthly(os.path.join(d, 'gkg', 'gkg_calibrated_2018_2026_fix.csv'), 'Date', 'Harga')
        hujan = read_monthly(os.path.join(d, 'curah_hujan', 'curah_hujan_2018-2026_fix.csv'), 'bulan', 'total_curah_hujan')
        padi = read_monthly(os.path.join(d, 'padi', 'produksi_padi_2018-2026_fix.csv'), 'tanggal', 'produksi_padi')
        inflasi = read_monthly(os.path.join(d, 'inflasi', 'inflasi_pangan_2018-2026_fix.csv'), 'tanggal', 'inflasi_pangan')

        all_months = sorted(set(beras) | set(gkg) | set(hujan) | set(padi) | set(inflasi))

        rows = []
        for key in all_months:  # key = 'YYYY-MM'
            tahun, bulan = key.split('-')
            rows.append({
                'tanggal': f"{key}-01",
                'tahun': int(tahun),
                'bulan': int(bulan),
                'lebaran': 0,
                'harga_beras': beras.get(key, ''),
                'harga_gkg': gkg.get(key, ''),
                'curah_hujan': hujan.get(key, ''),
                'produksi_padi': padi.get(key, ''),
                'inflasi_pangan': inflasi.get(key, ''),
            })

        fieldnames = ['tanggal', 'tahun', 'bulan', 'lebaran', 'harga_beras',
                      'harga_gkg', 'curah_hujan', 'produksi_padi', 'inflasi_pangan']
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Final merged dataset ({len(rows)} months) successfully saved to {output_file}")

    except Exception as e:
        print(f"An error occurred during final merge: {e}")

if __name__ == '__main__':
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Process 2018-2020 data
    # beras_2018_2020_in = os.path.join(base_path, 'datav2', 'beras', 'beras_2018-2020_daily_cleaned.csv')
    # beras_2018_2020_out = os.path.join(base_path, 'datav2', 'beras', 'beras_2018-2020_monthly.csv')
    # if os.path.exists(beras_2018_2020_in):
    #     aggregate_monthly(beras_2018_2020_in, beras_2018_2020_out)

    # beras_2021_2025_in = os.path.join(base_path, 'datav2', 'beras', 'beras_2021-2025_daily_cleaned.csv')
    # beras_2021_2025_out = os.path.join(base_path, 'datav2', 'beras', 'beras_2021-2025_monthly.csv')
    # if os.path.exists(beras_2021_2025_in):
    #     aggregate_monthly(beras_2021_2025_in, beras_2021_2025_out)
    
    # Process 2025-2026 data
    # beras_2025_2026_in = os.path.join(base_path, 'datav2', 'beras', 'beras_2025-2026_daily_cleaned.csv')
    # beras_2025_2026_out = os.path.join(base_path, 'datav2', 'beras', 'beras_2025-2026_monthly.csv')
    # if os.path.exists(beras_2025_2026_in):
    #     aggregate_monthly(beras_2025_2026_in, beras_2025_2026_out)
    # Merge inflasi_pangan files into one 2018-2026 dataset
    inflasi_dir = os.path.join(base_path, 'datav2', 'inflasi')
    inflasi_inputs = [
        os.path.join(inflasi_dir, 'inflasi_pangan_2018-2020.csv'),
        os.path.join(inflasi_dir, 'inflasi_pangan_2021-2025.csv'),
        os.path.join(inflasi_dir, 'inflasi_pangan_2025-2026.csv'),
    ]
    inflasi_output = os.path.join(inflasi_dir, 'inflasi_pangan_2018-2026.csv')
    merge_inflasi(inflasi_inputs, inflasi_output)

    # Merge produksi_padi files into one 2018-2026 dataset
    padi_dir = os.path.join(base_path, 'datav2', 'padi')
    padi_inputs = [
        os.path.join(padi_dir, 'produksi_padi_2018-2020.csv'),
        os.path.join(padi_dir, 'produksi_padi_2021-2025.csv'),
        os.path.join(padi_dir, 'produksi_padi_2025-2026.csv'),
    ]
    padi_output = os.path.join(padi_dir, 'produksi_padi_2018-2026_fix.csv')
    merge_produksi_padi(padi_inputs, padi_output)

    # Merge all five feature files into the final dataset
    final_output = os.path.join(base_path, 'harga_beras_2018_2026.csv')
    merge_all_features(base_path, final_output)

    # Example usage for extract_columns:
    # input_dataset = os.path.join(base_path, 'harga_beras_2021_2025.csv')
    # output_dir = os.path.join(base_path, 'datav2')
    # extract_columns(input_dataset, output_dir)


    # curah_hujan_input = os.path.join(base_path, 'datav2', 'curah_hujan', 'curah_hujan_2018-2026_daily.csv')
    # curah_hujan_output = os.path.join(base_path, 'datav2', 'curah_hujan', 'curah_hujan_2018-2026_fix.csv')
    
    # aggregate_curah_hujan_monthly(curah_hujan_input, curah_hujan_output)
    
    # merged_output = os.path.join(base_path, 'datasets', 'processed', 'dataset_merged_beras_hujan.csv')
    # raw_dir = os.path.join(base_path, 'datasets', 'raw')
    # merge_datasets(output_csv, curah_hujan_output, raw_dir, merged_output)
