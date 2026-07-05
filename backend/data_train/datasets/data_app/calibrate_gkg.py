import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def load_bapanas_data(filepath):
    """
    Load and preprocess BAPANAS data.
    The user mentioned this is daily data, but the CSV is already monthly 
    (contains Tahun, Bulan columns). Thus, we parse it directly as monthly data.
    """
    df = pd.read_csv(filepath)
    
    # Mapping Indonesian months to numbers
    month_map = {
        'Januari': '01', 'Februari': '02', 'Maret': '03', 'April': '04',
        'Mei': '05', 'Juni': '06', 'Juli': '07', 'Agustus': '08',
        'September': '09', 'Oktober': '10', 'November': '11', 'Desember': '12'
    }
    
    # Remove thousands separator and convert to float (e.g., "5,756" -> 5756.0)
    # Convert to string first to avoid issues if some are already floats/ints
    df['Harga'] = df['Harga'].astype(str).str.replace(',', '').astype(float)
        
    # Create Date column set to the first day of each month
    df['Month_Num'] = df['Bulan'].str.strip().map(month_map)
    df['Date'] = pd.to_datetime(df['Tahun'].astype(str) + '-' + df['Month_Num'] + '-01')
    
    # Group by Date and mean() in case there are duplicates/daily data somehow
    df = df.groupby('Date')['Harga'].mean().reset_index()
    
    df = df.sort_values('Date').reset_index(drop=True)
    df['Source'] = 'BAPANAS'
    
    return df

def load_bps_data(filepath, year):
    """
    Load and preprocess BPS data.
    Extracts 'Harga Gabah Kering Giling (GKG) (Rp/Kg)' row and transposes to a monthly timeseries.
    """
    df = pd.read_csv(filepath)
    
    # Find the row for GKG
    gkg_row = df[df['Kriteria'].str.contains('Harga Gabah Kering Giling \\(GKG\\)', regex=True, na=False)].iloc[0]
    
    months = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
              'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    
    prices = []
    for m in months:
        val = gkg_row[m]
        # BPS values might be strings with commas or hyphens. Convert to float.
        if pd.isna(val) or val == '-':
            prices.append(np.nan)
        else:
            prices.append(float(str(val).replace(',', '')))
            
    # Create DataFrame
    month_map = {
        'Januari': '01', 'Februari': '02', 'Maret': '03', 'April': '04',
        'Mei': '05', 'Juni': '06', 'Juli': '07', 'Agustus': '08',
        'September': '09', 'Oktober': '10', 'November': '11', 'Desember': '12'
    }
    
    dates = pd.to_datetime([f"{year}-{month_map[m]}-01" for m in months])
    bps_df = pd.DataFrame({'Date': dates, 'Harga': prices})
    bps_df['Source'] = 'BPS'
    
    return bps_df

def calculate_calibration_factor(bps_df, bapanas_df, year=2019):
    """
    Calculate the Mean Bias Correction factor using overlapping data.
    Formula: Mean of (BAPANAS_2019 / BPS_2019)
    """
    bps_overlap = bps_df[bps_df['Date'].dt.year == year].set_index('Date')
    bapanas_overlap = bapanas_df[bapanas_df['Date'].dt.year == year].set_index('Date')
    
    # Merge on Date to ensure perfectly aligned
    merged = bps_overlap.join(bapanas_overlap, lsuffix='_bps', rsuffix='_bapanas')
    
    # Drop NaNs just in case some months are missing
    merged = merged.dropna(subset=['Harga_bps', 'Harga_bapanas'])
    
    # Calculate ratio for each month, then take the mean
    merged['Ratio'] = merged['Harga_bapanas'] / merged['Harga_bps']
    mean_bias_correction = merged['Ratio'].mean()
    
    print(f"Calculated Mean Bias Correction factor (BAPANAS/BPS) for {year}: {mean_bias_correction:.4f}")
    return mean_bias_correction

def calibrate_bps(bps_df, factor):
    """
    Apply the calibration factor to BPS data.
    """
    calibrated = bps_df.copy()
    calibrated['Harga'] = calibrated['Harga'] * factor
    calibrated['Source'] = 'BPS (Calibrated)'
    return calibrated

def plot_calibrated_data(final_df):
    """
    Visualize the final calibrated timeline, explicitly highlighting the 
    Dec 2018 - Jan 2019 transition zone.
    """
    plt.figure(figsize=(14, 7))
    
    # Split for plotting
    bps_data = final_df[final_df['Source'] == 'BPS (Calibrated)']
    bapanas_data = final_df[final_df['Source'] == 'BAPANAS']
    
    plt.plot(bps_data['Date'], bps_data['Harga'], marker='o', label='BPS 2018 (Calibrated)', color='blue')
    plt.plot(bapanas_data['Date'], bapanas_data['Harga'], marker='o', label='BAPANAS 2019-2026', color='green')
    
    # Highlight the transition zone (Dec 2018 - Jan 2019)
    transition_start = pd.to_datetime('2018-12-01')
    transition_end = pd.to_datetime('2019-01-01')
    plt.axvspan(transition_start, transition_end, color='red', alpha=0.3, label='Transition Zone (Dec 2018 - Jan 2019)')
    
    plt.title('Calibrated GKG Price (Rp/Kg) - Seamless Transition', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Price (Rp/Kg)', fontsize=12)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.show()

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'datav2', 'gkg')
    
    bapanas_file = os.path.join(data_dir, 'bapanas_2019-2026.csv')
    bps_2018_file = os.path.join(data_dir, 'bps_2018.csv')
    bps_2019_file = os.path.join(data_dir, 'bps_2019.csv')
    
    # 1. Load data
    print("Loading data...")
    bapanas_df = load_bapanas_data(bapanas_file)
    bps_2018_df = load_bps_data(bps_2018_file, 2018)
    bps_2019_df = load_bps_data(bps_2019_file, 2019)
    
    # 2. Calculate calibration factor using 2019 overlap
    factor = calculate_calibration_factor(bps_2019_df, bapanas_df, year=2019)
    
    # 3. Apply calibration factor to BPS 2018
    print("Calibrating BPS 2018 data...")
    calibrated_bps_2018 = calibrate_bps(bps_2018_df, factor)
    
    # 4. Concatenate data
    print("Concatenating into a unified timeline...")
    final_df = pd.concat([calibrated_bps_2018, bapanas_df], ignore_index=True)
    final_df = final_df.sort_values('Date').reset_index(drop=True)
    
    # Save the calibrated data
    output_file = os.path.join(data_dir, 'gkg_calibrated_2018_2026.csv')
    final_df.to_csv(output_file, index=False)
    print(f"Final calibrated data saved to {output_file}")
    
    # 5 & 6. Visualize
    print("Generating visualization...")
    plot_calibrated_data(final_df)

if __name__ == "__main__":
    main()
