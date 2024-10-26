import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
import seaborn as sns
from datetime import datetime, timedelta
import zipfile
import os

#Import data
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(current_dir, 'final_airquality.zip')

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            extract_path = os.path.join(current_dir, 'data')
            zip_ref.extractall(extract_path)
        
        csv_path = os.path.join(extract_path, 'final_airquality.csv')
        
        df = pd.read_csv(csv_path, parse_dates=['DateTime'])
        return df
    except Exception as e:
        st.error(f"An error occurred while loading the data: {str(e)}")
        return None
    
#Preprocess DateTime
@st.cache_data
def preprocess_data(df):
    df['Date'] = df['DateTime'].dt.date
    return df
@st.cache_data
def filter_data(df, start_date, end_date, stations):
    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date) & (df['station'].isin(stations))
    return df.loc[mask]

#Mendefinisikan rerata polutan
@st.cache_data
def calculate_daily_avg(df):
    return df.groupby(['Date', 'station']).agg({
        'PM2.5_interpolated': 'mean',
        'PM10_interpolated': 'mean',
        'SO2_interpolated': 'mean',
        'NO2_interpolated': 'mean',
        'CO_interpolated': 'mean',
        'O3_interpolated': 'mean',
    }).reset_index()

# Tampilan warna Station
def get_station_colors(stations):
    color_map = plt.cm.get_cmap('tab10')
    return {station: to_rgba(color_map(i)) for i, station in enumerate(stations)}

#Batas polutan
@st.cache_data
def calculate_good_air_quality(df, station, pollutant_limits):
    station_data = df[df['station'] == station]
    total_hours = len(station_data)
    good_hours = (
        (station_data['PM2.5_interpolated'] <= pollutant_limits['PM2.5']['1h']) &
        (station_data['PM10_interpolated'] <= pollutant_limits['PM10']['24h']) &
        (station_data['SO2_interpolated'] <= pollutant_limits['SO2']['1h']) &
        (station_data['NO2_interpolated'] <= pollutant_limits['NO2']['1h']) &
        (station_data['CO_interpolated'] <= pollutant_limits['CO']['1h']) &
        (station_data['O3_hour_avg'] <= pollutant_limits['O3']['1h'])
    ).sum()
    return total_hours, good_hours

# Load & reprocess data
df = load_data()
if df is not None:
    df = preprocess_data(df)

# Sidebar input
st.sidebar.header('Select Parameters')
start_date = st.sidebar.date_input('Start Date', min_value=df['Date'].min(), max_value=df['Date'].max())
end_date = st.sidebar.date_input('End Date', min_value=start_date, max_value=df['Date'].max())
stations = st.sidebar.multiselect('Select Stations', df['station'].unique())

# Filter data
selected_data = filter_data(df, start_date, end_date, stations)

# Tampilan warna station 
station_color_dict = get_station_colors(stations)

if not selected_data.empty:
    st.title('Dashboard Kualitas Udara')
    st.header(f'Kualitas udara stations: {", ".join(stations)}, rentang waktu: {start_date} hingga {end_date}')

    # Section 1: Rerata Polutan Jam
    st.subheader('1. Rerata Polutan /jam ')
    pollutants = ['PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3']

    tabs = st.tabs(pollutants)
    for i, pollutant in enumerate(pollutants):
        with tabs[i]:
            fig, ax = plt.subplots(figsize=(12, 6))
            for station in stations:
                station_data = selected_data[selected_data['station'] == station]
                column = f'{pollutant}_interpolated' if pollutant != 'O3' else 'O3_hour_avg'
                ax.plot(station_data['DateTime'], station_data[column], label=station, color=station_color_dict[station])
            ax.set_title(f'{pollutant} Levels')
            ax.set_xlabel('Date')
            ax.set_ylabel('Concentration')
            ax.legend()
            st.pyplot(fig)

    # Section 2: Rerata Polutan Harian
    st.subheader('2. Rerata Polutan /hari')
    daily_avg = calculate_daily_avg(selected_data)

    tabs = st.tabs(pollutants)
    for i, pollutant in enumerate(pollutants):
        with tabs[i]:
            fig, ax = plt.subplots(figsize=(12, 6))
            for station in stations:
                station_data = daily_avg[daily_avg['station'] == station]
                column = f'{pollutant}_interpolated'
                ax.plot(station_data['Date'], station_data[column], label=station, 
                        color=station_color_dict[station], linewidth=2)
            
            ax.set_title(f'{pollutant} Daily Average')
            ax.set_xlabel('Date')
            ax.set_ylabel('Concentration')
            ax.legend()
                      
            st.pyplot(fig)

    # Section 3: Rekapitulasi kualitas udara
    st.subheader('3. Rekapitulasi Kualitas Udara')

    # Limit polutan
    pollutant_limits = {
        'PM2.5': {'1h': 75, '24h': 45},
        'PM10': {'24h': 150, 'year': 70},
        'SO2': {'1h': 500, '24h': 450, 'year': 60},
        'NO2': {'1h': 2000, '24h': 80, 'year': 40},
        'CO': {'1h': 4000, '24h': 10000},
        'O3': {'1h': 200, '8h': 160}
    }

    for station in stations:
        total_hours, good_hours = calculate_good_air_quality(selected_data, station, pollutant_limits)
        st.write(f"Station: {station}")
        st.write(f"Total kualitas udara sehat: {good_hours} dari {total_hours} jam")
        st.write(f"Persentase kualitas udara sehat: {(good_hours / total_hours) * 100:.2f}%")
        st.write("---")

    # Section 4: Parameter Eksternal
    st.subheader('4. Parameter Eksternal')
    parameters = ['TEMP', 'PRES', 'DEWP', 'RAIN', 'WSPM']

    for param in parameters:
        min_val = selected_data[f'{param}_interpolated'].min()
        max_val = selected_data[f'{param}_interpolated'].max()
        avg_val = selected_data[f'{param}_interpolated'].mean()
        
        st.metric(
            label=param,
            value=f"{avg_val:.2f}",
            delta=f"Range: {min_val:.2f} to {max_val:.2f}"
        )

    # Section 5: Crossplot Pollutants vs Parameters
    st.subheader('5. Crossplot Polutan vs Parameter Eksternal')
    
    pollutant_options = ['PM2.5_day_avg', 'PM10_day_avg', 'SO2_day_avg', 'NO2_day_avg', 'CO_day_avg', 'O3_8hour_avg']
    parameter_options = ['TEMP_day_avg', 'PRES_day_avg', 'DEWP_day_avg', 'RAIN_day_avg', 'WSPM_day_avg']

    pollutant_x = st.selectbox('Sumbu X', pollutant_options)
    pollutant_y = st.selectbox('Sumbu Y', pollutant_options)
    color_parameter = st.selectbox('Kontrol Warna', parameter_options)

    fig, ax = plt.subplots(figsize=(10, 8))
    scatter = ax.scatter(selected_data[pollutant_x], selected_data[pollutant_y], 
                         c=selected_data[color_parameter], cmap='viridis', alpha=0.6)
    
    plt.colorbar(scatter, label=color_parameter)
    ax.set_xlabel(pollutant_x)
    ax.set_ylabel(pollutant_y)
    ax.set_title(f'Crossplot: {pollutant_x} vs {pollutant_y}')
    
    st.pyplot(fig)

else:
    st.warning('Tidak ada data untuk ditampilkan.')