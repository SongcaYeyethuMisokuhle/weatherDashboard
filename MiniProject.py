import pandas as pd
import streamlit as st
import requests
import folium
import seaborn as sns
import pydeck as pdk
import matplotlib.pyplot as plt
from folium import Choropleth
from folium.plugins import MarkerCluster
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import pytz
from streamlit.components.v1 import html
import os

# Configure page layout
st.set_page_config(layout="wide", page_title="Comprehensive Weather Dashboard")

# Set Mapbox API key
os.environ["MAPBOX_API_KEY"] = "pk.eyJ1IjoiYXRsaWUiLCJhIjoiY21haDducXRqMDhnNjJqczcyOG16cGZjcSJ9.W6I1UjrMJIeHk2c0qEYBdA"

# Dashboard title and description
st.title("🌦️ Comprehensive Weather Dashboard")
st.markdown("""
*Your all-in-one weather analysis tool - view forecasts, compare cities, and analyze historical data*
""")

# --- CACHE FUNCTIONS ---
@st.cache_data(ttl=3600)
def get_city_coordinates(city_name, api_key):
    try:
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={api_key}"
        response = requests.get(geo_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0]['lat'], data[0]['lon'], None
            else:
                return None, None, "City not found."
        else:
            return None, None, f"API Error: {response.status_code}"
    except Exception as e:
        return None, None, f"Connection error: {str(e)}"

@st.cache_data(ttl=3600)
def get_weather_forecast(city, api_key):
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"API Error: {response.status_code}"
    except Exception as e:
        return None, f"Connection error: {str(e)}"

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("Weather Controls")
    
    # API Key
    api_key = st.text_input(
        "OpenWeatherMap API Key", 
        value="1a969a984098465fe910c2a3409188c9", 
        type="password",
        help="Enter your OpenWeatherMap API key. Default provided for demo."
    )
    
    # City Input
    city = st.text_input("Enter a city name:", "Johannesburg")
    
    # Forecast Settings
    st.subheader("Forecast Settings")
    forecast_days = st.slider("Forecast Days", min_value=1, max_value=5, value=3)
    data_filter = st.multiselect(
        "Data to Display",
        ["Temperature (°C)", "Humidity (%)", "Wind Speed (m/s)", "Description"],
        default=["Temperature (°C)", "Humidity (%)", "Wind Speed (m/s)"]
    )
    temperature_unit = st.radio("Temperature Unit", ["Celsius (°C)", "Fahrenheit (°F)"])

# Create tabs to separate the functionalities
tab1, tab2, tab3 = st.tabs(["🌤 Current & Forecast", "📊 Historical Data", "🏙 City Comparison"])

with tab1:
    # --- CURRENT WEATHER & FORECAST TAB ---
    st.header(f"Weather in {city.title()}")
    
    # Get coordinates
    with st.spinner("Loading location data..."):
        lat, lon, coord_error = get_city_coordinates(city, api_key)
        
    if coord_error:
        st.error(f"Error: {coord_error}")
        st.stop()
    
    # Get forecast data
    weather_url = f'http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric'
    with st.spinner("Fetching weather forecast..."):
        response = requests.get(weather_url)
        data = response.json()
        
    if 'list' not in data:
        st.error(f"Forecast API error: {data.get('message', 'Unknown error')}")
        st.stop()
    
    # Process forecast data
    forecast_list = data['list'][:forecast_days * 8]
    forecast_data = []
    
    for item in forecast_list:
        temp = item['main']['temp']
        if temperature_unit == "Fahrenheit (°F)":
            temp = (temp * 9/5) + 32
            
        forecast_data.append({
            "Datetime": datetime.fromtimestamp(item['dt']),
            "Temperature (°C)" if temperature_unit == "Celsius (°C)" else "Temperature (°F)": temp,
            "Humidity (%)": item['main']['humidity'],
            "Wind Speed (m/s)": item['wind']['speed'],
            "Description": item['weather'][0]['description'].title(),
            "Weather Icon": item['weather'][0]['icon']
        })
    
    forecast_df = pd.DataFrame(forecast_data)
    
    # Sunrise/Sunset Info
    sunrise_ts = data.get("city", {}).get("sunrise")
    sunset_ts = data.get("city", {}).get("sunset")
    if sunrise_ts and sunset_ts:
        sunrise = datetime.fromtimestamp(sunrise_ts).strftime('%H:%M')
        sunset = datetime.fromtimestamp(sunset_ts).strftime('%H:%M')
        st.sidebar.markdown(f"🌅 **Sunrise:** {sunrise}")
        st.sidebar.markdown(f"🌇 **Sunset:** {sunset}")
    
    # Alerts
    alerts = []
    temp_col = "Temperature (°C)" if temperature_unit == "Celsius (°C)" else "Temperature (°F)"
    
    if forecast_df["Wind Speed (m/s)"].max() > 10:
        alerts.append("⚠ High wind alert: Wind speed exceeds 10 m/s in forecast!")
    
    if forecast_df[temp_col].max() > (35 if temperature_unit == "Celsius (°C)" else 95):
        alerts.append(f"🔥 Extreme heat warning: Temperatures above {35 if temperature_unit == 'Celsius (°C)' else 95}° expected!")
    
    # Current weather display
    if len(forecast_df) > 0:
        current = forecast_df.iloc[0]
        temp_str = "Temperature (°C)" if temperature_unit == "Celsius (°C)" else "Temperature (°F)"
        
        st.subheader(f"Current Weather in {city.title()}")
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            icon_code = current['Weather Icon']
            icon_url = f"http://openweathermap.org/img/wn/{icon_code}@4x.png"
            st.image(icon_url, width=150)
            st.markdown(f"### {current['Description']}")
            
        with col2:
            st.metric("Temperature", f"{current[temp_str]:.1f}°")
            
        with col3:
            st.metric("Humidity", f"{current['Humidity (%)']}%")
            
        with col4:
            st.metric("Wind Speed", f"{current['Wind Speed (m/s)']:.1f} m/s")
    
    for alert in alerts:
        st.error(alert)
    
    # Map visualization
    st.subheader("📍 Location")
    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/satellite-v9",
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=10),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=pd.DataFrame({"lat": [lat], "lon": [lon], "name": [city.title()]}),
                get_position='[lon, lat]',
                get_color='[255, 0, 0, 160]',
                get_radius=5000
            ),
            pdk.Layer(
                "TextLayer",
                data=pd.DataFrame({"lat": [lat], "lon": [lon], "text": [city.title()]}),
                get_position='[lon, lat]',
                get_text='text',
                get_size=16,
                get_color='[0,0,0]',
                get_alignment_baseline="'bottom'"
            )
        ]
    ))
    
    # Forecast charts
    st.subheader(f"{forecast_days}-Day Weather Forecast for {city.title()}")
    
    forecast_df['Date'] = forecast_df['Datetime'].dt.date
    daily_forecast = forecast_df.groupby('Date').agg({
        temp_col: ['mean', 'min', 'max'],
        'Humidity (%)': 'mean',
        'Wind Speed (m/s)': 'mean',
        'Description': lambda x: x.value_counts().index[0]
    }).reset_index()
    
    daily_forecast.columns = ['Date', 'Temp_Avg', 'Temp_Min', 'Temp_Max', 'Humidity', 'Wind', 'Description']
    
    temp_unit_symbol = "°C" if temperature_unit == "Celsius (°C)" else "°F"
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_forecast['Date'], 
        y=daily_forecast['Temp_Max'],
        mode='lines+markers',
        name=f'Max Temp ({temp_unit_symbol})',
        line=dict(color='red')
    ))
    fig.add_trace(go.Scatter(
        x=daily_forecast['Date'], 
        y=daily_forecast['Temp_Min'],
        mode='lines+markers',
        name=f'Min Temp ({temp_unit_symbol})',
        line=dict(color='blue')
    ))
    fig.add_trace(go.Scatter(
        x=daily_forecast['Date'], 
        y=daily_forecast['Temp_Avg'],
        mode='lines+markers',
        name=f'Avg Temp ({temp_unit_symbol})',
        line=dict(color='green')
    ))
    fig.update_layout(
        title=f'Temperature Forecast ({temp_unit_symbol})',
        xaxis_title='Date',
        yaxis_title=f'Temperature ({temp_unit_symbol})',
        legend=dict(y=0.5, font_size=10)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    if "Humidity (%)" in data_filter or "Wind Speed (m/s)" in data_filter:
        col1, col2 = st.columns(2)
        
        if "Humidity (%)" in data_filter:
            with col1:
                fig_humidity = px.bar(
                    daily_forecast, 
                    x='Date', 
                    y='Humidity',
                    title='Humidity Forecast (%)'
                )
                st.plotly_chart(fig_humidity, use_container_width=True)
        
        if "Wind Speed (m/s)" in data_filter:
            with col2:
                fig_wind = px.bar(
                    daily_forecast, 
                    x='Date', 
                    y='Wind',
                    title='Wind Speed Forecast (m/s)'
                )
                st.plotly_chart(fig_wind, use_container_width=True)

    st.subheader("Hourly Forecast")
    forecast_df['Datetime'] = forecast_df['Datetime'].dt.strftime('%Y-%m-%d %H:%M')
    display_cols = ["Datetime"] + data_filter
    st.dataframe(forecast_df[display_cols], use_container_width=True)
    
    csv = forecast_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Forecast CSV", csv, "weather_forecast.csv", "text/csv")

with tab2:
    # --- HISTORICAL WEATHER DATA TAB ---
    st.header("Historical Weather Data")
    
    # Get city from sidebar or use default
    historical_city = st.text_input("Enter a city name for historical data:", city, key="historical_city")

    # Ensure the city is entered
    if historical_city:
        # Get coordinates
        latitude, longitude = None, None
        geo_url = f'http://api.openweathermap.org/data/2.5/weather?q={historical_city}&appid={api_key}'
        response = requests.get(geo_url)
        data = response.json()

        if response.status_code == 200 and 'coord' in data:
            latitude = data['coord']['lat']
            longitude = data['coord']['lon']

            # Sunrise/Sunset Times
            sun_api = f"https://api.sunrise-sunset.org/json?lat={latitude}&lng={longitude}&formatted=0"
            sun_response = requests.get(sun_api)
            sun_data = sun_response.json()

            if sun_data['status'] == 'OK':
                sunrise_utc = pd.to_datetime(sun_data['results']['sunrise'])
                sunset_utc = pd.to_datetime(sun_data['results']['sunset'])

                # Convert to local time (e.g., Africa/Johannesburg)
                sunrise_local = sunrise_utc.tz_convert('Africa/Johannesburg').strftime('%H:%M')
                sunset_local = sunset_utc.tz_convert('Africa/Johannesburg').strftime('%H:%M')

                # Display as a metric
                st.metric("🌞 Daylight", f"🌅 {sunrise_local} | 🌇 {sunset_local}")
            else:
                st.warning("Could not fetch sunrise/sunset data.")
        else:
            st.error(f"Could not find the city: {historical_city}")
        
        if latitude and longitude:
            # Parameters for NASA API request
            start_date = '20220101'
            end_date = '20241231'
            parameters = 'T2M,PRECTOTCORR,RH2M'
            community = 'AG'

            # Build the NASA POWER API URL with the user's city coordinates
            url = f'https://power.larc.nasa.gov/api/temporal/daily/point?parameters={parameters}&start={start_date}&end={end_date}&latitude={latitude}&longitude={longitude}&format=JSON&community={community}'

            # Request the data
            response = requests.get(url)
            data = response.json()

            if 'properties' not in data:
                st.error("Error: Data not found.")
            else:
                # Extract the daily data
                daily_data = data['properties']['parameter']
                dates = list(daily_data['T2M'].keys())

                # Build the DataFrame
                df = pd.DataFrame({
                    'date': pd.to_datetime(dates),
                    'temperature_C': list(daily_data['T2M'].values()),
                    'precipitation_mm': list(daily_data['PRECTOTCORR'].values()),
                    'humidity_%': list(daily_data['RH2M'].values())
                })

                # Display data preview
                st.write("Historical weather data loaded successfully:")
                st.dataframe(df.head())

                # Plot Interactive Chart
                st.title(f"Historical Weather Data for {historical_city}")

                start_date = st.date_input('Select Start Date', df['date'].min(), key='hist_start')
                end_date = st.date_input('Select End Date', df['date'].max(), key='hist_end')

                # Filter based on selected dates
                filtered_data = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]

                # Let the user choose which weather parameter to visualize
                st.subheader("Choose Weather Parameter to View")
                parameter = st.selectbox("Select parameter", options=[col for col in df.columns if col != 'date'])

                fig = px.line(
                    filtered_data,
                    x='date',
                    y=parameter,
                    title=f"{parameter} for {historical_city} from {start_date} to {end_date}",
                    labels={parameter: parameter.replace('_', ' ').title(), 'date': 'Date'},
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)

with tab3:
    # --- CITY COMPARISON TAB ---
    st.header("City Weather & Population Comparison")
    
    # User input - moved to sidebar
    with st.sidebar:
        st.subheader("City Comparison Settings")
        col1, col2 = st.columns(2)
        with col1:
            city1 = st.text_input("First city", value="Johannesburg", key="city1")
        with col2:
            city2 = st.text_input("Second city", value="Cape Town", key="city2")

    # Compare button
    if st.button("Compare Cities"):
        def get_city_data(city_name):
            # First get coordinates
            geo_url = f'http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={api_key}'
            geo_response = requests.get(geo_url)
            
            if geo_response.status_code != 200 or not geo_response.json():
                return None
            
            geo_data = geo_response.json()[0]
            lat, lon = geo_data['lat'], geo_data['lon']
            
            # Then get current weather
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            weather_response = requests.get(weather_url)
            
            if weather_response.status_code != 200:
                return None
                
            weather_data = weather_response.json()
            
            # Get population data from Geonames API (free tier)
            try:
                geonames_user = 'demo'  # Replace with your Geonames username
                geonames_url = f"http://api.geonames.org/searchJSON?name={city_name}&maxRows=1&username={geonames_user}"
                geonames_response = requests.get(geonames_url)
                population = geonames_response.json()['geonames'][0]['population'] if geonames_response.status_code == 200 else "Data not available"
            except:
                population = "Data not available"
            
            return {
                'City': city_name.title(),
                'Latitude': lat,
                'Longitude': lon,
                'Population': population,
                'Temperature': weather_data['main']['temp'],
                'Humidity': weather_data['main']['humidity'],
                'Conditions': weather_data['weather'][0]['description'],
                'Icon': weather_data['weather'][0]['icon']
            }

        data1 = get_city_data(city1)
        data2 = get_city_data(city2)

        if not data1 or not data2:
            st.error("⚠️ Could not fetch data for one or both cities. Please check the city names.")
        else:
            # Display raw data
            df = pd.DataFrame([data1, data2])
            
            st.markdown("### 🏙️ City Details")
            st.dataframe(df.set_index("City"))

            # Create interactive folium map with temperature markers
            st.markdown("### 🌡️ Interactive Weather Map")
            
            # Calculate center point between the two cities
            avg_lat = (data1['Latitude'] + data2['Latitude']) / 2
            avg_lon = (data1['Longitude'] + data2['Longitude']) / 2
            
            # Create folium map
            m = folium.Map(location=[avg_lat, avg_lon], zoom_start=6)
            
            # Add markers with weather info
            for city_data in [data1, data2]:
                # Get weather icon
                icon_url = f"http://openweathermap.org/img/wn/{city_data['Icon']}@2x.png"
                
                # Create popup content
                popup_content = f"""
                <div style="font-family: Arial; width: 200px;">
                    <h4 style="margin: 5px 0; color: #1a5fb4;">{city_data['City']}</h4>
                    <div style="display: flex; align-items: center;">
                        <img src="{icon_url}" style="width: 50px; height: 50px; margin-right: 10px;">
                        <div>
                            <p style="margin: 3px 0; font-size: 18px;"><b>{city_data['Temperature']}°C</b></p>
                            <p style="margin: 3px 0;">{city_data['Conditions'].capitalize()}</p>
                        </div>
                    </div>
                    <p style="margin: 8px 0 3px 0;"><b>Humidity:</b> {city_data['Humidity']}%</p>
                    <p style="margin: 3px 0;"><b>Population:</b> {city_data['Population'] if isinstance(city_data['Population'], str) else f"{city_data['Population']:,}"}</p>
                </div>
                """
                
                folium.Marker(
                    location=[city_data['Latitude'], city_data['Longitude']],
                    popup=folium.Popup(popup_content, max_width=300),
                    icon=folium.features.CustomIcon(icon_url, icon_size=(50, 50)),
                    tooltip=f"{city_data['City']}: {city_data['Temperature']}°C"
                ).add_to(m)
            
            # Add a line connecting the two cities
            folium.PolyLine(
                locations=[[data1['Latitude'], data1['Longitude']], 
                         [data2['Latitude'], data2['Longitude']]],
                color='blue',
                weight=2,
                dash_array='5,5'
            ).add_to(m)
            
            # Display the map in Streamlit
            st_folium = html(m._repr_html_(), height=500)
            
            # Comparison metrics
            st.markdown("### 📊 Comparison Metrics")
            
            # Create comparison charts only if we have numerical population data
            if isinstance(data1['Population'], (int, float)) and isinstance(data2['Population'], (int, float)):
                # Temperature comparison
                fig_temp = px.bar(
                    df,
                    x="City",
                    y="Temperature",
                    color="City",
                    title="Temperature Comparison (°C)",
                    labels={"Temperature": "Temperature (°C)"},
                    height=400,
                )
                st.plotly_chart(fig_temp, use_container_width=True)
                
                # Population comparison
                fig_pop = px.bar(
                    df,
                    x="City",
                    y="Population",
                    color="City",
                    title="Population Comparison",
                    labels={"Population": "Population"},
                    height=400,
                )
                st.plotly_chart(fig_pop, use_container_width=True)
            else:
                st.warning("Population data not available for both cities. Only temperature comparison shown.")
                
                # Temperature comparison only
                fig_temp = px.bar(
                    df,
                    x="City",
                    y="Temperature",
                    color="City",
                    title="Temperature Comparison (°C)",
                    labels={"Temperature": "Temperature (°C)"},
                    height=400,
                )
                st.plotly_chart(fig_temp, use_container_width=True)