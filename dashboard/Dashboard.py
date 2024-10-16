import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import zipfile

@st.cache_data
def load_data():
    # Load the CSV file from the zip archive
    with zipfile.ZipFile('final_airquality.zip', 'r') as zip_ref:
        with zip_ref.open('final_airquality.csv') as file:
            df = pd.read_csv(file)
    df['DateTime'] = pd.to_datetime(df['DateTime'])
    return df

sns.set_style('dark') 
sns.set_palette('dark')  

# Tampilan plot
def create_pollutant_subplots(data, pollutants, time_column, value_suffix, title):
    fig, axes = plt.subplots(3, 2, figsize=(20, 15), facecolor='black')
    fig.suptitle(title, fontsize=24, color='white')  
    
    for i, pollutant in enumerate(pollutants):
        ax = axes[i // 2, i % 2]
        if pollutant == 'O3':
            if value_suffix == '_interpolated':
                column = 'O3_hour_avg'
            else: 
                column = 'O3_8hour_avg'
        else:
            column = f'{pollutant}{value_suffix}'
        
        sns.lineplot(data=data, x=time_column, y=column, ax=ax, linewidth=2.5, color='#77d487')
        ax.set_title(f'{pollutant} Levels', fontsize=16, color='white')
        ax.set_xlabel('Date', fontsize=12, color='white')
        ax.set_ylabel('Concentration', fontsize=12, color='white')
        ax.tick_params(axis='both', which='major', labelsize=10, colors='gray')
        ax.grid(True, linestyle='--', alpha=0.7, color='gray')
        
        ax.set_facecolor('#2e3233') 
    
    plt.tight_layout()
    return fig

st.title('Dashboard Kualitas Udara')

# Sidebar input
st.sidebar.header('Select Parameters')
start_date = st.sidebar.date_input('Start Date', min_value=df['DateTime'].min().date(), max_value=df['DateTime'].max().date())
end_date = st.sidebar.date_input('End Date', min_value=start_date, max_value=df['DateTime'].max().date())
station = st.sidebar.selectbox('Select Station', df['station'].unique())

# Filter input
mask = (df['DateTime'].dt.date >= start_date) & (df['DateTime'].dt.date <= end_date) & (df['station'] == station)
selected_data = df.loc[mask]

if not selected_data.empty:
    st.header(f'Kualitas udara station {station}, rentang waktu: {start_date} hingga {end_date}')

    # Section 1: Rerata Polutan Jam
    st.subheader('1. Rerata Polutan /jam ')
    pollutants = ['PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3']
    fig_hourly = create_pollutant_subplots(
        selected_data,
        pollutants,
        'DateTime',
        '_interpolated',
        'Hourly Pollutant Levels'
    )
    
    st.pyplot(fig_hourly)

    # Section 2: Rerata Polutan Harian
    st.subheader('2. Rerata Polutan /hari')
    daily_avg = selected_data.groupby(selected_data['DateTime'].dt.date).agg({
        'PM2.5_day_avg': 'mean',
        'PM10_day_avg': 'mean',
        'SO2_day_avg': 'mean',
        'NO2_day_avg': 'mean',
        'CO_day_avg': 'mean',
        'O3_8hour_avg': 'mean',
    }).reset_index()

    fig_daily = create_pollutant_subplots(
        daily_avg,
        pollutants,
        'DateTime',
        '_day_avg',
        'Daily Average Pollutant Levels'
    )
    st.pyplot(fig_daily)

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

    total_hours = len(selected_data)
    good_hours = (
        (selected_data['PM2.5_interpolated'] <= pollutant_limits['PM2.5']['1h']) &
        (selected_data['PM10_interpolated'] <= pollutant_limits['PM10']['24h']) &
        (selected_data['SO2_interpolated'] <= pollutant_limits['SO2']['1h']) &
        (selected_data['NO2_interpolated'] <= pollutant_limits['NO2']['1h']) &
        (selected_data['CO_interpolated'] <= pollutant_limits['CO']['1h']) &
        (selected_data['O3_hour_avg'] <= pollutant_limits['O3']['1h'])
    ).sum()

    st.write(f"Total kualitas udara sehat: {good_hours} dari {total_hours} jam")
    st.write(f"Persentase kualitas udara sehat: {(good_hours / total_hours) * 100:.2f}%")

    # Pemilihan data > 365 hari (1 tahun)
    if (end_date - start_date).days > 365:
        st.write("Rerata Polutan:")
        year_avg = selected_data.groupby(selected_data['DateTime'].dt.year).agg({
            'PM2.5_day_avg': 'mean',
            'PM10_day_avg': 'mean',
            'SO2_day_avg': 'mean',
            'NO2_day_avg': 'mean',
            'CO_day_avg': 'mean',
            'O3_8hour_avg': 'mean'
        })
        st.dataframe(year_avg)

    # Expander
    with st.expander("Info Detail Ambang Batas Polutan"):
        st.write(""" 
        Ambang Batas Polutan yaitu:
        - PM2.5: 1h Average = 75, 24h Average = 45
        - PM10: 24h Average = 150, Year Average = 70
        - SO2: 1h Average = 500, 24h Average = 450, Year Average = 60
        - NO2: 1h Average = 2000, 24h Average = 80, Year Average = 40
        - CO: 1h Average = 4000, 24h Average = 10000
        - O3: 1h Average = 200, 8h Average = 160

        Jika nilai polutan tidak melebihi batas tersebut, maka akan terhitung sebagai good air quality, begitu pula sebaliknya.
        """)

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

else:
    st.warning('Tidak ada data untuk ditampilkan.')
