import csv
import os

file_path = '/mnt/affan/aNGODING/skripsi-prediksi-beras/backend/datasets/processed/dataset_merged_beras_hujan.csv'
temp_path = '/mnt/affan/aNGODING/skripsi-prediksi-beras/backend/datasets/processed/temp_bulan.csv'

with open(file_path, mode='r', newline='', encoding='utf-8') as infile, \
     open(temp_path, mode='w', newline='', encoding='utf-8') as outfile:
    
    reader = csv.DictReader(infile)
    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
    writer.writeheader()
    
    for row in reader:
        # Convert '01' to '1', etc.
        row['bulan'] = str(int(row['bulan']))
        writer.writerow(row)

# Replace the old file with the new file
os.replace(temp_path, file_path)
print(f"File updated successfully, 'bulan' is now an integer.")
