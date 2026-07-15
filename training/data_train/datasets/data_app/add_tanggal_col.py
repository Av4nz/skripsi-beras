import csv
import os

file_path = '/mnt/affan/aNGODING/skripsi-prediksi-beras/backend/datasets/dataset_fixed.csv'
temp_path = '/mnt/affan/aNGODING/skripsi-prediksi-beras/backend/datasets/temp_tanggal.csv'

with open(file_path, mode='r', newline='', encoding='utf-8') as infile, \
     open(temp_path, mode='w', newline='', encoding='utf-8') as outfile:
    
    reader = csv.DictReader(infile)
    
    # We want to insert 'tanggal' at the beginning
    new_fieldnames = ['tanggal'] + reader.fieldnames
    
    writer = csv.DictWriter(outfile, fieldnames=new_fieldnames)
    writer.writeheader()
    
    for row in reader:
        tahun = row['tahun']
        bulan = int(row['bulan'])
        
        # Create a datetime string format YYYY-MM-DD where DD is 01
        # This is natively recognized as datetime by most tools (e.g., Pandas, Excel)
        tanggal = f"{tahun}-{bulan:02d}-01"
        
        new_row = {'tanggal': tanggal}
        for field in reader.fieldnames:
            new_row[field] = row[field]
                
        writer.writerow(new_row)

# Replace the old file with the new file
os.replace(temp_path, file_path)
print(f"File updated successfully, 'tanggal' column added with datetime string format.")
