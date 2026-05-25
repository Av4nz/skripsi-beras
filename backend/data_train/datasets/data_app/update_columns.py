import csv
import os

file_path = '/mnt/affan/aNGODING/skripsi-prediksi-beras/backend/datasets/processed/dataset_merged_beras_hujan.csv'
temp_path = '/mnt/affan/aNGODING/skripsi-prediksi-beras/backend/datasets/processed/temp.csv'

with open(file_path, mode='r', newline='', encoding='utf-8') as infile, \
     open(temp_path, mode='w', newline='', encoding='utf-8') as outfile:
    
    reader = csv.DictReader(infile)
    # The current fields are: tanggal, harga_beras, harga_gkg, curah_hujan, produksi_padi, inflasi_pangan
    # New fields: tahun, bulan, lebaran, harga_beras, harga_gkg, curah_hujan, produksi_padi, inflasi_pangan
    
    # We want to insert tahun, bulan, lebaran at the beginning
    new_fieldnames = ['tahun', 'bulan', 'lebaran'] + [f for f in reader.fieldnames if f != 'tanggal']
    
    writer = csv.DictWriter(outfile, fieldnames=new_fieldnames)
    writer.writeheader()
    
    for row in reader:
        tanggal = row['tanggal']
        tahun, bulan = tanggal.split('-')
        
        new_row = {
            'tahun': tahun,
            'bulan': bulan,
            'lebaran': 0
        }
        for field in new_fieldnames:
            if field not in ['tahun', 'bulan', 'lebaran']:
                new_row[field] = row[field]
                
        writer.writerow(new_row)

# Replace the old file with the new file
os.replace(temp_path, file_path)
print(f"File updated successfully.")
