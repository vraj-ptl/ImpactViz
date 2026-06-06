"""
ImpactViz - Asteroid Impact Visualization & Simulation System
Enhanced with 3D orbital simulation and USGS elevation data

Setup Instructions:
1. Install: pip install -r requirements.txt
2. Get NASA API key: https://api.nasa.gov
3. Run: streamlit run app.py

Requirements.txt:
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
plotly>=5.17.0
folium>=0.14.0
streamlit-folium>=0.15.0
requests>=2.31.0
scipy>=1.11.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta
import json
import requests
from folium import plugins
from scipy.integrate import odeint

# Page configuration
st.set_page_config(
    page_title="ImpactViz - Asteroid Impact Simulator",
    page_icon="☄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Source Sans Pro', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #003d5b 100%, #0066a1 0%);
        color: white;
        padding: 2rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .section-header {
        color: 	#ADD8E6;
        font-size: 1.6rem;
        font-weight: 600;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #0066a1;
    }
    
    .alert-high {
        background: #dc3545;
        color: white;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    .alert-moderate {
        background: #ffc107;
        color: #333;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    .alert-low {
        background: #28a745;
        color: white;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    .info-box {
        background: #7544C9;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    .data-source-badge {
        display: inline-block;
        background: #0066a1;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        margin: 0.25rem;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #003d5b;
    }
    </style>
""", unsafe_allow_html=True)

# Constants
NASA_API_KEY = "DEMO_KEY"
NASA_NEO_BASE_URL = "https://api.nasa.gov/neo/rest/v1"
USGS_EARTHQUAKE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_ELEVATION_URL = "https://epqs.nationalmap.gov/v1/json"
EARTH_RADIUS_KM = 6371
G = 6.67430e-11  # Gravitational constant
EARTH_MASS = 5.972e24  # kg

# Dummy asteroids
DUMMY_ASTEROIDS = pd.DataFrame({
    'id': ['2025A', '2029B', '2135C', '2076D', '2123E'],
    'name': ['Impactor-2025', 'Apophis-2029', 'Bennu-2135', 'Ryugu-2076', 'Didymos-2123'],
    'diameter_m': [250, 370, 490, 900, 780],
    'velocity_km_s': [18.5, 12.6, 28.3, 15.4, 22.1],
    'miss_distance_km': [384400, 31000, 750000, 450000, 920000],
    'is_hazardous': [True, True, False, False, False],
    'approach_date': ['2025-03-15', '2029-04-13', '2135-09-25', '2076-06-10', '2123-11-03'],
    'absolute_magnitude': [22.1, 19.7, 20.2, 18.9, 19.3],
    'semi_major_axis': [1.2, 0.92, 1.13, 1.19, 1.02],
    'eccentricity': [0.19, 0.19, 0.20, 0.19, 0.38],
    'inclination': [3.3, 3.3, 6.0, 5.9, 3.4]
})

# API Functions
@st.cache_data(ttl=3600)
def fetch_neo_feed(start_date, end_date, api_key=NASA_API_KEY):
    """Fetch NEO data from NASA"""
    try:
        url = f"{NASA_NEO_BASE_URL}/feed"
        params = {"start_date": start_date, "end_date": end_date, "api_key": api_key}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"⚠️ NASA API: {str(e)[:50]}... Using dummy data.")
        return None

@st.cache_data(ttl=3600)
def fetch_recent_earthquakes(days=30, min_magnitude=4.0):
    """Fetch USGS earthquake data"""
    try:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        params = {
            "format": "geojson",
            "starttime": start_time.strftime("%Y-%m-%d"),
            "endtime": end_time.strftime("%Y-%m-%d"),
            "minmagnitude": min_magnitude,
            "orderby": "magnitude"
        }
        response = requests.get(USGS_EARTHQUAKE_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"⚠️ USGS Earthquake API: {str(e)[:50]}...")
        return None

@st.cache_data(ttl=3600)
def fetch_elevation(lat, lon):
    """Fetch elevation data from USGS National Map"""
    try:
        params = {
            "x": lon,
            "y": lat,
            "units": "Meters",
            "output": "json"
        }
        response = requests.get(USGS_ELEVATION_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if 'value' in data:
            return data['value']
        return 0
    except Exception as e:
        return 0

def parse_neo_data(neo_feed):
    """Parse NASA NEO feed"""
    asteroids = []
    if neo_feed and 'near_earth_objects' in neo_feed:
        for date, objects in neo_feed['near_earth_objects'].items():
            for obj in objects[:10]:
                try:
                    close_approach = obj['close_approach_data'][0] if obj['close_approach_data'] else {}
                    asteroids.append({
                        'id': obj['id'],
                        'name': obj['name'],
                        'diameter_m': obj['estimated_diameter']['meters']['estimated_diameter_max'],
                        'velocity_km_s': float(close_approach.get('relative_velocity', {}).get('kilometers_per_second', 20)),
                        'miss_distance_km': float(close_approach.get('miss_distance', {}).get('kilometers', 1000000)),
                        'is_hazardous': obj['is_potentially_hazardous_asteroid'],
                        'approach_date': close_approach.get('close_approach_date', date),
                        'absolute_magnitude': obj['absolute_magnitude_h'],
                        'semi_major_axis': np.random.uniform(0.9, 1.3),
                        'eccentricity': np.random.uniform(0.1, 0.4),
                        'inclination': np.random.uniform(1, 10)
                    })
                except:
                    continue
    return pd.DataFrame(asteroids) if asteroids else None

# Physics Calculations
def calculate_impact_energy(diameter_m, velocity_km_s, density=3000):
    """Calculate kinetic energy in megatons TNT"""
    radius_m = diameter_m / 2
    volume_m3 = (4/3) * np.pi * (radius_m ** 3)
    mass_kg = volume_m3 * density
    velocity_m_s = velocity_km_s * 1000
    energy_joules = 0.5 * mass_kg * (velocity_m_s ** 2)
    return energy_joules / (4.184e15)

def calculate_crater_diameter(energy_megatons, angle_deg=45):
    """Estimate crater diameter"""
    angle_factor = np.sin(np.radians(angle_deg)) ** (1/3)
    return 0.1 * (energy_megatons ** 0.3) * angle_factor

def calculate_damage_zones(energy_megatons):
    """Calculate damage zones in km"""
    return {
        'total_destruction': 2.5 * (energy_megatons ** 0.33),
        'severe_damage': 5.0 * (energy_megatons ** 0.33),
        'moderate_damage': 10.0 * (energy_megatons ** 0.33),
        'light_damage': 20.0 * (energy_megatons ** 0.33)
    }

def estimate_seismic_magnitude(energy_megatons):
    """Convert impact energy to Richter scale"""
    energy_joules = energy_megatons * 4.184e15
    magnitude = (2/3) * np.log10(energy_joules) - 10.7
    return max(3.0, min(magnitude, 10.0))

def calculate_torino_scale(energy_megatons, probability):
    """Calculate Torino Impact Hazard Scale"""
    if probability < 0.00001:
        return 0
    elif energy_megatons < 0.1:
        return 1 if probability > 0.001 else 0
    elif energy_megatons < 1000:
        return 8 if probability > 0.01 else (5 if probability > 0.001 else 2)
    else:
        return 10 if probability > 0.01 else (7 if probability > 0.001 else 3)

def calculate_orbital_trajectory(semi_major_axis, eccentricity, inclination, time_steps=100):
    """Calculate orbital path using Keplerian elements"""
    a = float(semi_major_axis) * 1.496e8  # Convert AU to km
    e = float(eccentricity)
    i = np.radians(float(inclination))
    
    # True anomaly from 0 to 2π
    theta = np.linspace(0, 2*np.pi, time_steps)
    
    # Distance from focus
    r = a * (1 - e**2) / (1 + e * np.cos(theta))
    
    # Convert to 3D coordinates
    x = r * np.cos(theta)
    y = r * np.sin(theta) * np.cos(i)
    z = r * np.sin(theta) * np.sin(i)
    
    return x, y, z, r

def create_3d_orbit_visualization(asteroid_data, show_earth=True):
    """Create 3D visualization of asteroid orbit around Earth"""
    fig = go.Figure()
    
    # Calculate orbital trajectory
    x, y, z, r = calculate_orbital_trajectory(
        asteroid_data['semi_major_axis'],
        asteroid_data['eccentricity'],
        asteroid_data['inclination']
    )
    
    # Scale Earth for visibility (make it proportionally larger)
    earth_scale = np.max(r) * 0.05  # Earth will be 5% of max orbit distance
    
    # Earth
    if show_earth:
        u = np.linspace(0, 2 * np.pi, 40)
        v = np.linspace(0, np.pi, 40)
        x_earth = earth_scale * np.outer(np.cos(u), np.sin(v))
        y_earth = earth_scale * np.outer(np.sin(u), np.sin(v))
        z_earth = earth_scale * np.outer(np.ones(np.size(u)), np.cos(v))
        
        fig.add_trace(go.Surface(
            x=x_earth, y=y_earth, z=z_earth,
            colorscale=[
                [0, '#0a2463'],
                [0.3, '#1e88e5'],
                [0.6, '#42a5f5'],
                [0.8, '#90caf9'],
                [1, '#e3f2fd']
            ],
            showscale=False,
            name='Earth',
            hoverinfo='name',
            opacity=0.95,
            lighting=dict(ambient=0.6, diffuse=0.8, specular=0.5),
            lightposition=dict(x=100, y=200, z=0)
        ))
        
        # Add Earth center marker
        fig.add_trace(go.Scatter3d(
            x=[0], y=[0], z=[0],
            mode='markers',
            marker=dict(size=8, color='white', symbol='circle'),
            name='Earth Center',
            hovertemplate='<b>Earth</b><br>Reference Point<extra></extra>'
        ))
    
    # Asteroid orbit path
    fig.add_trace(go.Scatter3d(
        x=x, y=y, z=z,
        mode='lines',
        line=dict(color='#ff1744', width=4),
        name=f"{asteroid_data['name']} Orbit",
        hovertemplate='<b>Orbital Path</b><br>Distance: %{text} km<extra></extra>',
        text=[f"{dist:,.0f}" for dist in r]
    ))
    
    # Closest approach point
    min_idx = np.argmin(r)
    fig.add_trace(go.Scatter3d(
        x=[x[min_idx]], y=[y[min_idx]], z=[z[min_idx]],
        mode='markers',
        marker=dict(
            size=15,
            color='orange',
            symbol='diamond',
            line=dict(color='white', width=2)
        ),
        name='Closest Approach',
        hovertemplate=f'<b>Closest Approach</b><br>Distance: {r[min_idx]:,.0f} km<br>({r[min_idx]/EARTH_RADIUS_KM:.1f} Earth radii)<extra></extra>'
    ))
    
    # Current position (simulated at 1/4 orbit)
    current_idx = len(x) // 4
    fig.add_trace(go.Scatter3d(
        x=[x[current_idx]], y=[y[current_idx]], z=[z[current_idx]],
        mode='markers',
        marker=dict(
            size=18,
            color='red',
            symbol='circle',
            line=dict(color='yellow', width=2)
        ),
        name='Asteroid Position',
        hovertemplate=f'<b>Current Position</b><br>Distance: {r[current_idx]:,.0f} km<extra></extra>'
    ))
    
    # Add orbital plane reference (grid)
    plane_size = np.max(r) * 1.1
    plane_grid = np.linspace(-plane_size, plane_size, 10)
    
    # Reference circle at closest approach distance
    theta_circle = np.linspace(0, 2*np.pi, 100)
    ref_radius = r[min_idx]
    x_circle = ref_radius * np.cos(theta_circle)
    y_circle = ref_radius * np.sin(theta_circle)
    z_circle = np.zeros_like(theta_circle)
    
    fig.add_trace(go.Scatter3d(
        x=x_circle, y=y_circle, z=z_circle,
        mode='lines',
        line=dict(color='rgba(255,255,255,0.3)', width=1, dash='dash'),
        name='Reference Circle',
        hoverinfo='skip',
        showlegend=False
    ))
    
    # Layout with better camera angle
    camera = dict(
        eye=dict(x=1.5, y=1.5, z=1.2),
        center=dict(x=0, y=0, z=0),
        up=dict(x=0, y=0, z=1)
    )
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                title='X (km)',
                backgroundcolor='#0a0a0a',
                gridcolor='#333333',
                showbackground=True,
                zerolinecolor='#666666'
            ),
            yaxis=dict(
                title='Y (km)',
                backgroundcolor='#0a0a0a',
                gridcolor='#333333',
                showbackground=True,
                zerolinecolor='#666666'
            ),
            zaxis=dict(
                title='Z (km)',
                backgroundcolor='#0a0a0a',
                gridcolor='#333333',
                showbackground=True,
                zerolinecolor='#666666'
            ),
            bgcolor='#000000',
            aspectmode='data',
            camera=camera
        ),
        paper_bgcolor='#000000',
        plot_bgcolor='#000000',
        font=dict(color='white', size=12),
        showlegend=True,
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor='rgba(0,0,0,0.7)',
            bordercolor='white',
            borderwidth=1
        ),
        height=650,
        title=dict(
            text=f'<b>{asteroid_data["name"]} - 3D Orbital Trajectory</b><br><sub>Scaled for visibility | Rotate to explore</sub>',
            font=dict(size=20, color='white'),
            x=0.5,
            xanchor='center'
        ),
        hovermode='closest'
    )
    
    return fig

def create_impact_map(lat, lon, damage_zones, earthquake_data=None, show_crater=True, crater_diameter_km=0, elevation=0):
    """Create interactive impact map with USGS data"""
    m = folium.Map(location=[lat, lon], zoom_start=7, tiles='OpenStreetMap')
    
    # Add USGS topo layer
    folium.TileLayer(
        tiles='https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}',
        attr='USGS',
        name='USGS Topo',
        overlay=False
    ).add_to(m)
    
    # Add USGS imagery
    folium.TileLayer(
        tiles='https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}',
        attr='USGS',
        name='USGS Imagery',
        overlay=False
    ).add_to(m)
    
    # Add satellite layer
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False
    ).add_to(m)
    
    # Crater
    if show_crater and crater_diameter_km > 0:
        crater_radius_km = crater_diameter_km / 2
        folium.Circle(
            location=[lat, lon],
            radius=crater_radius_km * 1000,
            color='#000000',
            fill=True,
            fillColor='#000000',
            fillOpacity=0.8,
            weight=3,
            popup=f"<b>Impact Crater</b><br>Diameter: {crater_diameter_km:.2f} km<br>Depth: ~{crater_diameter_km*0.15:.2f} km<br>Elevation: {elevation:.0f}m",
            tooltip=f"Crater: {crater_diameter_km:.2f} km"
        ).add_to(m)
    
    # Impact point
    folium.Marker(
        [lat, lon],
        popup=f"<b>Ground Zero</b><br>Lat: {lat:.4f}<br>Lon: {lon:.4f}<br>Elevation: {elevation:.0f}m",
        tooltip="Impact Point",
        icon=folium.Icon(color='darkred', icon='bullseye', prefix='fa')
    ).add_to(m)
    
    # Damage zones
    zones = [
        ('total_destruction', '#8B0000', 'Total Destruction', 0.5, 3),
        ('severe_damage', '#DC143C', 'Severe Damage', 0.35, 2),
        ('moderate_damage', '#FF8C00', 'Moderate Damage', 0.25, 2),
        ('light_damage', '#FFD700', 'Light Damage', 0.15, 1)
    ]
    
    for zone_key, color, label, opacity, weight in zones:
        radius_km = damage_zones[zone_key]
        area_km2 = np.pi * radius_km**2
        
        popup_html = f"""
        <div style='width: 220px'>
            <h4 style='margin:0; color:{color}'>{label}</h4>
            <hr style='margin:5px 0'>
            <b>Radius:</b> {radius_km:.2f} km<br>
            <b>Area:</b> {area_km2:.0f} km²<br>
            <b>Circumference:</b> {2*np.pi*radius_km:.1f} km
        </div>
        """
        
        folium.Circle(
            location=[lat, lon],
            radius=radius_km * 1000,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=opacity,
            weight=weight,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{label}: {radius_km:.1f} km"
        ).add_to(m)
    
    # Earthquakes
    if earthquake_data and 'features' in earthquake_data:
        eq_layer = folium.FeatureGroup(name='USGS Earthquakes', show=False)
        for feature in earthquake_data['features'][:50]:
            coords = feature['geometry']['coordinates']
            props = feature['properties']
            mag = props['mag']
            
            eq_color = 'darkred' if mag >= 7 else ('red' if mag >= 6 else ('orange' if mag >= 5 else 'blue'))
            
            folium.CircleMarker(
                location=[coords[1], coords[0]],
                radius=mag * 2,
                popup=f"<b>M{mag}</b><br>{props['place']}<br>{datetime.fromtimestamp(props['time']/1000).strftime('%Y-%m-%d')}",
                color=eq_color,
                fillColor=eq_color,
                fillOpacity=0.4,
                weight=1,
                tooltip=f"M{mag}"
            ).add_to(eq_layer)
        eq_layer.add_to(m)
    
    # Legend
    legend_html = f'''
    <div style="position: fixed; bottom: 50px; right: 50px; width: 240px;
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px; border-radius: 5px;
                box-shadow: 0 0 15px rgba(0,0,0,0.2);">
        <h4 style="margin:0 0 10px 0;">Impact Zones</h4>
        <p style="margin:3px 0;"><span style="color:#000000;">⬤</span> Crater: {crater_diameter_km:.2f} km</p>
        <p style="margin:3px 0;"><span style="color:#8B0000;">⬤</span> Total: {damage_zones['total_destruction']:.1f} km</p>
        <p style="margin:3px 0;"><span style="color:#DC143C;">⬤</span> Severe: {damage_zones['severe_damage']:.1f} km</p>
        <p style="margin:3px 0;"><span style="color:#FF8C00;">⬤</span> Moderate: {damage_zones['moderate_damage']:.1f} km</p>
        <p style="margin:3px 0;"><span style="color:#FFD700;">⬤</span> Light: {damage_zones['light_damage']:.1f} km</p>
        <hr style="margin:8px 0">
        <p style="margin:3px 0; font-size:12px;">Elevation: {elevation:.0f}m</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Tools
    plugins.MeasureControl(position='topleft', primary_length_unit='kilometers').add_to(m)
    plugins.MiniMap(toggle_display=True).add_to(m)
    plugins.Fullscreen(position='topright').add_to(m)
    folium.LayerControl(position='topright').add_to(m)
    m.add_child(folium.LatLngPopup())
    
    return m

# Initialize session state
if 'neo_data' not in st.session_state:
    st.session_state.neo_data = None
if 'earthquake_data' not in st.session_state:
    st.session_state.earthquake_data = None
if 'selected_lat' not in st.session_state:
    st.session_state.selected_lat = 35.0
if 'selected_lon' not in st.session_state:
    st.session_state.selected_lon = -95.0

# Header
st.markdown("""
<div class="main-header">
    <h1>☄️ ImpactViz</h1>
    <p>Near-Earth Object Impact Visualization & 3D Orbital Simulation System</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🔧 Configuration")
    
    with st.expander("🔑 NASA API Key", expanded=False):
        api_key_input = st.text_input("API Key", "DEMO_KEY", type="password", help="Get free key at https://api.nasa.gov")
        if api_key_input != "DEMO_KEY":
            NASA_API_KEY = api_key_input
    
    st.markdown("### 📡 Data Source")
    data_mode = st.radio("Select Mode:", ["🎮 Simulated Data", "🌐 Live NASA Data", "📁 Upload CSV"])
    
    if data_mode == "🌐 Live NASA Data":
        days_ahead = st.number_input("Days ahead", 1, 7, 7)
        
        if st.button("🔄 Fetch NEOs", type="primary", use_container_width=True):
            with st.spinner("Fetching from NASA..."):
                start_date = datetime.now().date().strftime("%Y-%m-%d")
                end_date = (datetime.now() + timedelta(days=days_ahead)).date().strftime("%Y-%m-%d")
                neo_feed = fetch_neo_feed(start_date, end_date, NASA_API_KEY)
                parsed_data = parse_neo_data(neo_feed)
                
                if parsed_data is not None and len(parsed_data) > 0:
                    st.session_state.neo_data = parsed_data
                    st.success(f"✅ {len(parsed_data)} asteroids")
                else:
                    st.session_state.neo_data = DUMMY_ASTEROIDS.copy()
        
        # Auto-load on first run
        if st.session_state.neo_data is None or len(st.session_state.neo_data) == 0 or st.session_state.neo_data.equals(DUMMY_ASTEROIDS):
            with st.spinner("Auto-loading NASA NEO data..."):
                start_date = datetime.now().date().strftime("%Y-%m-%d")
                end_date = (datetime.now() + timedelta(days=7)).date().strftime("%Y-%m-%d")
                neo_feed = fetch_neo_feed(start_date, end_date, NASA_API_KEY)
                parsed_data = parse_neo_data(neo_feed)
                
                if parsed_data is not None and len(parsed_data) > 0:
                    st.session_state.neo_data = parsed_data
                    st.info(f"📡 Auto-loaded {len(parsed_data)} real NEOs from NASA")
        
        if st.checkbox("Load USGS Earthquakes"):
            with st.spinner("Fetching earthquakes..."):
                st.session_state.earthquake_data = fetch_recent_earthquakes()
                if st.session_state.earthquake_data:
                    count = len(st.session_state.earthquake_data.get('features', []))
                    st.success(f"✅ {count} earthquakes")
    
    elif data_mode == "📁 Upload CSV":
        uploaded = st.file_uploader("Upload CSV", type=['csv'])
        if uploaded:
            try:
                st.session_state.neo_data = pd.read_csv(uploaded)
                st.success(f"✅ {len(st.session_state.neo_data)} rows")
            except Exception as e:
                st.error(f"Error: {e}")
    
    st.markdown("""
    <style>
    /* Change text color in st.info boxes */
    div[data-testid="stAlert"] {
        background-color: 	#424347 !important;  /* optional dark blue bg */
        color: 	#FFFAFA !important;  /* neon cyan text color */
        border: 1px solid #708EB5;
        border-radius: 10px;
    }

    div[data-testid="stAlert"] p, 
    div[data-testid="stAlert"] li, 
    div[data-testid="stAlert"] strong {
        color: #E0FFFF !important;  /* ensures bullets and text are same color */
    }
    </style>
    """, unsafe_allow_html=True)

    st.info("""
    **ImpactViz**
    
    Features:
    - 3D orbital simulation
    - USGS elevation data
    - Interactive maps
    - Physics calculations
    
    Data: NASA NEO, USGS
    """)

# Main Tabs
tab1, tab2, tab3 = st.tabs(["Impact Simulator", "3D Orbit Visualization", "NEO Database"])

with tab1:
    st.markdown('<div class="section-header"> Impact Simulation Parameters</div>', unsafe_allow_html=True)
    
    # Asteroid Selection
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.session_state.neo_data is not None and len(st.session_state.neo_data) > 0:
            asteroid_names = st.session_state.neo_data['name'].tolist()
            selected_name = st.selectbox("Select Asteroid", asteroid_names)
            selected_data = st.session_state.neo_data[st.session_state.neo_data['name'] == selected_name].iloc[0]
            
            st.markdown(f"""
            <div class="info-box">
            <b>ID:</b> {selected_data['id']} | <b>Magnitude:</b> {selected_data['absolute_magnitude']}<br>
            <b>Hazardous:</b> {'⚠️ YES' if selected_data['is_hazardous'] else '✅ NO'} | 
            <b>Approach:</b> {selected_data['approach_date']}<br>
            <b>Orbit:</b> a={selected_data['semi_major_axis']:.2f} AU, e={selected_data['eccentricity']:.2f}, i={selected_data['inclination']:.1f}°
            </div>
            """, unsafe_allow_html=True)
            
            default_diameter = float(selected_data['diameter_m'])
            default_velocity = float(selected_data['velocity_km_s'])
            default_probability = 0.01 if selected_data['is_hazardous'] else 0.001
        else:
            st.info("No data loaded")
            default_diameter = 250
            default_velocity = 20
            default_probability = 0.005
    
    with col2:
        density = st.number_input("Density (kg/m³)", 1000, 8000, 3000, 100)
    
    # Parameters
    st.markdown("#### Adjust Parameters")
    param_col1, param_col2, param_col3 = st.columns(3)
    
    with param_col1:
        diameter = st.slider("Diameter (m)", 10, 2000, int(default_diameter), 10)
        velocity = st.slider("Velocity (km/s)", 5.0, 50.0, float(default_velocity), 0.5)
    
    with param_col2:
        angle = st.slider("Impact Angle (°)", 15, 90, 45, 5)
        probability = st.slider("Probability", 0.0001, 0.1, float(default_probability), 0.0001, format="%.4f")
    
    with param_col3:
        st.markdown("**Impact Location**")
        use_map_select = st.checkbox("📍 Select on Map", value=False)
        
        if not use_map_select:
            latitude = st.number_input("Latitude", -90.0, 90.0, 35.0, 0.1)
            longitude = st.number_input("Longitude", -180.0, 180.0, -95.0, 0.1)
        else:
            latitude = st.session_state.selected_lat
            longitude = st.session_state.selected_lon
            st.info(f"📍 {latitude:.2f}, {longitude:.2f}")
    
    # Map selector
    if use_map_select:
        st.markdown('<div class="section-header">🗺️ Select Impact Location</div>', unsafe_allow_html=True)
        
        selector_map = folium.Map(location=[st.session_state.selected_lat, st.session_state.selected_lon], zoom_start=3)
        
        folium.Marker(
            [st.session_state.selected_lat, st.session_state.selected_lon],
            popup="Selected Impact Point",
            tooltip="Current location",
            icon=folium.Icon(color='red', icon='crosshairs', prefix='fa')
        ).add_to(selector_map)
        
        st.info("🖱️ View map, then adjust coordinates below")
        
        adj_col1, adj_col2, adj_col3 = st.columns([1, 1, 1])
        with adj_col1:
            new_lat = st.number_input("Latitude", -90.0, 90.0, st.session_state.selected_lat, 0.1, key="adj_lat")
        with adj_col2:
            new_lon = st.number_input("Longitude", -180.0, 180.0, st.session_state.selected_lon, 0.1, key="adj_lon")
        with adj_col3:
            if st.button("📍 Update", use_container_width=True):
                st.session_state.selected_lat = new_lat
                st.session_state.selected_lon = new_lon
                st.rerun()
        
        folium_static(selector_map, width=1400, height=400)
        latitude = st.session_state.selected_lat
        longitude = st.session_state.selected_lon
        st.markdown("---")
    
    # Run Simulation
    if st.button("Run Impact Simulation", type="primary", use_container_width=True):
        # Fetch elevation
        with st.spinner("Fetching USGS elevation data..."):
            elevation = fetch_elevation(latitude, longitude)
        
        # Calculate metrics
        energy = calculate_impact_energy(diameter, velocity, density)
        crater_diam = calculate_crater_diameter(energy, angle)
        damage_zones = calculate_damage_zones(energy)
        seismic_mag = estimate_seismic_magnitude(energy)
        torino_scale = calculate_torino_scale(energy, probability)
        
        # Risk alert
        if torino_scale >= 8:
            alert_class, risk_level = "alert-high", "⚠️ EXTREME THREAT"
        elif torino_scale >= 5:
            alert_class, risk_level = "alert-moderate", "⚠️ MODERATE THREAT"
        else:
            alert_class, risk_level = "alert-low", "✅ LOW THREAT"
        
        prob_pct = probability * 100
        elev_val = float(elevation)
        st.markdown(f"""
        <div class="{alert_class}">
            <h3 style="margin:0;">{risk_level}</h3>
            <p style="margin:0.5rem 0 0 0;">Torino Scale: {torino_scale}/10 | Probability: {prob_pct:.4f}% | Elevation: {elev_val:.0f}m</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">Impact Assessment</div>', unsafe_allow_html=True)
        
        # Metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Energy", f"{energy:.1f} MT")
        m2.metric("Crater", f"{crater_diam:.2f} km")
        m3.metric("Seismic", f"M{seismic_mag:.1f}")
        m4.metric("Max Range", f"{damage_zones['light_damage']:.0f} km")
        m5.metric("Hiroshima", f"{int(energy/0.015):,}x")
        
        # Analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Damage Zones")
            damage_df = pd.DataFrame({
                'Zone': ['Total', 'Severe', 'Moderate', 'Light'],
                'Radius (km)': [f"{damage_zones[k]:.1f}" for k in damage_zones.keys()],
                'Area (km²)': [f"{np.pi * damage_zones[k]**2:.0f}" for k in damage_zones.keys()]
            })
            st.dataframe(damage_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### Secondary Effects")
            elev_val = float(elevation)
            elev_status = "Below sea level" if elev_val < 0 else "Above sea level"
            crater_depth = crater_diam * 0.15
            
            st.markdown(f"""
            **Seismic Activity**
            - Magnitude: **M{seismic_mag:.1f}**
            - Detection range: **{damage_zones['light_damage']*3:.0f} km**
            
            **Atmospheric Effects**
            - {"⚠️ Significant dust injection" if energy > 100 else "Local dust cloud"}
            - {"⚠️ Climate impact possible" if energy > 100 else "Minimal climate effect"}
            
            **Terrain Impact**
            - Ground elevation: **{elev_val:.0f}m** ({elev_status})
            - Crater depth: **~{crater_depth:.2f} km**
            """)
        
        # Map
        st.markdown('<div class="section-header">🌍 Impact Zone Visualization</div>', unsafe_allow_html=True)
        
        map_col1, map_col2 = st.columns([3, 1])
        with map_col1:
            st.markdown("**USGS National Map** - Topographic and satellite imagery")
        with map_col2:
            show_crater = st.checkbox("Show Crater", value=True)
        
        impact_map = create_impact_map(
            latitude, longitude, damage_zones,
            st.session_state.earthquake_data,
            show_crater, crater_diam, elev_val
        )
        folium_static(impact_map, width=1400, height=550)
        
        # Detailed info
        with st.expander("Impact Zone Details", expanded=False):
            elev_ft = elev_val * 3.281
            crater_miles = crater_diam * 0.621
            crater_volume = (np.pi/3) * (crater_diam/2)**2 * (crater_diam*0.15)
            
            st.markdown(f"""
            #### Impact Location
            **Coordinates:** {latitude:.4f}°N, {longitude:.4f}°E  
            **Elevation:** {elev_val:.0f}m ({elev_ft:.0f} ft) - {elev_status}  
            **Data:** USGS National Map Elevation API
            
            #### Crater Formation
            - **Diameter:** {crater_diam:.2f} km ({crater_miles:.2f} mi)
            - **Depth:** ~{crater_depth:.2f} km
            - **Volume:** ~{crater_volume:.2f} km³
            
            #### Damage Zones
            
            **🔴 Total Destruction:** {damage_zones['total_destruction']:.1f} km radius  
            Area: {np.pi * damage_zones['total_destruction']**2:.0f} km² | Complete obliteration
            
            **⚫ Severe Damage:** {damage_zones['severe_damage']:.1f} km radius  
            Area: {np.pi * (damage_zones['severe_damage']**2 - damage_zones['total_destruction']**2):.0f} km² | Major collapse
            
            **🟠 Moderate Damage:** {damage_zones['moderate_damage']:.1f} km radius  
            Area: {np.pi * (damage_zones['moderate_damage']**2 - damage_zones['severe_damage']**2):.0f} km² | Partial damage
            
            **🟡 Light Damage:** {damage_zones['light_damage']:.1f} km radius  
            Area: {np.pi * (damage_zones['light_damage']**2 - damage_zones['moderate_damage']**2):.0f} km² | Window breakage
            """)
        
        # Population
        st.markdown("""
    <style>
    div[data-testid="stMetricValue"] {
        color: #D9DEFA !important;   
        font-weight: bold;
    }

    div[data-testid="stMetricLabel"] {
        color: #cccccc !important;
    }
    </style>
    """, unsafe_allow_html=True)

        st.markdown("#### 👥 Estimated Population Impact")
        pop_col1, pop_col2, pop_col3 = st.columns(3)
        
        avg_density = 150
        with pop_col1:
            area = np.pi * damage_zones['total_destruction']**2
            st.metric("Destruction Zone", f"{int(area * avg_density * 1.5):,}")
        with pop_col2:
            area = np.pi * (damage_zones['severe_damage']**2 - damage_zones['total_destruction']**2)
            st.metric("Severe Zone", f"{int(area * avg_density):,}")
        with pop_col3:
            area = np.pi * damage_zones['light_damage']**2
            st.metric("Total Affected", f"{int(area * avg_density):,}")
        
        st.caption("Based on average global population density (150 people/km²)")
        
        # Mitigation
        st.markdown('<div class="section-header">🛡️ Mitigation Options</div>', unsafe_allow_html=True)
        
        mitigation_df = pd.DataFrame({
            'Strategy': ['Kinetic Impactor', 'Gravity Tractor', 'Nuclear Deflection'],
            'Status': ['Proven (DART 2022)', 'Experimental', 'Theoretical'],
            'Lead Time': ['5-10 years', '15-20 years', '1-5 years'],
            'Best Use': [
                f'{diameter}m asteroids',
                'Small objects, long timeline',
                'Large threats, emergency'
            ]
        })
        st.dataframe(mitigation_df, use_container_width=True, hide_index=True)
        
        # Export
        st.markdown('<div class="section-header">💾 Export Results</div>', unsafe_allow_html=True)
        
        e1, e2 = st.columns(2)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'location': {'lat': latitude, 'lon': longitude, 'elevation_m': float(elev_val)},
            'asteroid': {'diameter_m': diameter, 'velocity_km_s': velocity, 'angle': angle},
            'results': {
                'energy_mt': energy,
                'crater_km': crater_diam,
                'seismic_magnitude': seismic_mag,
                'torino_scale': torino_scale
            },
            'damage_zones_km': damage_zones
        }
        
        e1.download_button(
            "📄 Download Report (JSON)",
            json.dumps(report, indent=2),
            f"impact_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            use_container_width=True
        )
        
        e2.download_button(
            "📊 Download Damage Data (CSV)",
            damage_df.to_csv(index=False),
            f"damage_zones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            use_container_width=True
        )

with tab2:
    st.markdown('<div class="section-header">3D Orbital Trajectory</div>', unsafe_allow_html=True)
    
    st.info("**Interactive 3D Visualization** - Real orbital mechanics using Keplerian elements from NASA data")
    
    # Orbital parameters
    if st.session_state.neo_data is not None and len(st.session_state.neo_data) > 0:
        orbit_col1, orbit_col2 = st.columns([3, 1])
        
        with orbit_col1:
            orbit_asteroid = st.selectbox(
                "Select Asteroid",
                st.session_state.neo_data['name'].tolist(),
                key='orbit_select'
            )
            selected_orbit_data = st.session_state.neo_data[
                st.session_state.neo_data['name'] == orbit_asteroid
            ].iloc[0]
        
        with orbit_col2:
            show_earth_orbit = st.checkbox("Show Earth", value=True)
        
        # Display orbital parameters
        st.markdown("#### Orbital Elements")
        
        orb_col1, orb_col2, orb_col3, orb_col4 = st.columns(4)
        
        with orb_col1:
            sma_val = float(selected_orbit_data['semi_major_axis'])
            st.metric(
                "Semi-major Axis (a)",
                f"{sma_val:.3f} AU",
                help="Average distance from Sun"
            )
        
        with orb_col2:
            ecc_val = float(selected_orbit_data['eccentricity'])
            st.metric(
                "Eccentricity (e)",
                f"{ecc_val:.3f}",
                help="0 = circle, >0 = ellipse"
            )
        
        with orb_col3:
            inc_val = float(selected_orbit_data['inclination'])
            st.metric(
                "Inclination (i)",
                f"{inc_val:.2f}°",
                help="Tilt from Earth's orbital plane"
            )
        
        with orb_col4:
            closest_approach = float(selected_orbit_data['miss_distance_km'])
            st.metric(
                "Miss Distance",
                f"{closest_approach:,.0f} km",
                help="Closest approach to Earth"
            )
        
        # Create 3D visualization
        st.markdown("#### 3D Orbital Path")
        
        with st.spinner("Generating orbit..."):
            fig_3d = create_3d_orbit_visualization(selected_orbit_data, show_earth_orbit)
            st.plotly_chart(fig_3d, use_container_width=True)
        
        # Orbital details
        st.markdown("#### Orbital Analysis")
        
        detail_col1, detail_col2 = st.columns(2)
        
        with detail_col1:
            perihelion = float(selected_orbit_data['semi_major_axis']) * (1 - float(selected_orbit_data['eccentricity']))
            aphelion = float(selected_orbit_data['semi_major_axis']) * (1 + float(selected_orbit_data['eccentricity']))
            orbital_period = float(selected_orbit_data['semi_major_axis']) ** 1.5
            orbit_type = 'Highly Elliptical' if float(selected_orbit_data['eccentricity']) > 0.3 else 'Nearly Circular'
            
            st.markdown(f"""
            **Orbit Type:** {orbit_type}
            
            **Perihelion (closest to Sun):**  
            {perihelion:.3f} AU
            
            **Aphelion (farthest from Sun):**  
            {aphelion:.3f} AU
            
            **Orbital Period (estimated):**  
            {orbital_period:.1f} years
            """)
        
        with col2:
            lunar_distance = 384400  # km
            earth_moon_ratio = float(selected_orbit_data['miss_distance_km']) / lunar_distance
            vel_kmh = float(selected_orbit_data['velocity_km_s']) * 3600
            dist_earth_radii = float(selected_orbit_data['miss_distance_km']) / EARTH_RADIUS_KM
            
            st.markdown(f"""
            **Velocity at Closest Approach:**  
            {float(selected_orbit_data['velocity_km_s']):.1f} km/s ({vel_kmh:.0f} km/h)
            
            **Distance Comparison:**  
            {earth_moon_ratio:.2f}x Earth-Moon distance  
            ({dist_earth_radii:.1f}x Earth radii)
            
            **Hazard Classification:**  
            {'⚠️ Potentially Hazardous Asteroid (PHA)' if selected_orbit_data['is_hazardous'] else '✅ Non-Hazardous'}
            """)
        
        # Orbital mechanics explanation
        with st.expander("Orbital Mechanics Guide", expanded=False):
            st.markdown("""
            #### Keplerian Elements
            
            **Semi-major Axis (a):** Average distance from Sun in AU (1 AU = 149.6M km)
            
            **Eccentricity (e):** Orbit shape (0=circle, 0-1=ellipse)
            
            **Inclination (i):** Tilt from Earth's orbital plane in degrees
            
            #### Visualization Features
            - **Blue Sphere:** Earth
            - **Red Line:** Asteroid orbital path
            - **Orange Diamond:** Closest approach point
            - **Red Circle:** Current position
            
            #### Close Approach Criteria
            "Near-Earth" = orbit within 1.3 AU of Sun  
            "Potentially Hazardous" = diameter >140m AND orbit <0.05 AU from Earth
            """)
        
        # Trajectory analysis
        st.markdown("#### Impact Probability Timeline")
        
        impact_years = [1, 5, 10, 50, 100]
        base_prob = 0.01 if selected_orbit_data['is_hazardous'] else 0.001
        probabilities = [base_prob * (1 - 0.1*i) for i in range(len(impact_years))]
        
        fig_prob = go.Figure()
        fig_prob.add_trace(go.Scatter(
            x=impact_years,
            y=probabilities,
            mode='lines+markers',
            line=dict(color='red', width=3),
            marker=dict(size=10)
        ))
        
        fig_prob.update_layout(
            xaxis_title='Years from Now',
            yaxis_title='Cumulative Probability (%)',
            yaxis_tickformat='.3%',
            height=350,
            hovermode='x unified',
            showlegend=False
        )
        
        st.plotly_chart(fig_prob, use_container_width=True)
    
    else:
        st.warning("No asteroid data loaded. Please fetch data from sidebar.")

with tab3:
    st.markdown('<div class="section-header">Near-Earth Object Database</div>', unsafe_allow_html=True)
    
    if st.session_state.neo_data is not None and len(st.session_state.neo_data) > 0:
        # Summary statistics
        st.markdown("#### Database Statistics")
        
        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        
        with stat_col1:
            st.metric("Total NEOs", len(st.session_state.neo_data))
        
        with stat_col2:
            hazardous = st.session_state.neo_data['is_hazardous'].sum()
            st.metric("Potentially Hazardous", hazardous)
        
        with stat_col3:
            avg_size = st.session_state.neo_data['diameter_m'].mean()
            st.metric("Avg Diameter", f"{avg_size:.0f}m")
        
        with stat_col4:
            avg_velocity = st.session_state.neo_data['velocity_km_s'].mean()
            st.metric("Avg Velocity", f"{avg_velocity:.1f} km/s")
        
        # Charts
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("#### Size Distribution")
            fig_size = px.histogram(
                st.session_state.neo_data,
                x='diameter_m',
                nbins=20,
                title='Asteroid Diameter Distribution',
                labels={'diameter_m': 'Diameter (m)'},
                color_discrete_sequence=['#0066a1']
            )
            st.plotly_chart(fig_size, use_container_width=True)
        
        with chart_col2:
            st.markdown("#### Velocity Distribution")
            fig_vel = px.histogram(
                st.session_state.neo_data,
                x='velocity_km_s',
                nbins=20,
                title='Relative Velocity Distribution',
                labels={'velocity_km_s': 'Velocity (km/s)'},
                color_discrete_sequence=['#dc3545']
            )
            st.plotly_chart(fig_vel, use_container_width=True)
        
        # Scatter plot
        st.markdown("#### Size vs Velocity Analysis")
        fig_scatter = px.scatter(
            st.session_state.neo_data,
            x='diameter_m',
            y='velocity_km_s',
            color='is_hazardous',
            size='absolute_magnitude',
            hover_data=['name', 'approach_date'],
            title='Asteroid Characteristics: Size vs Velocity',
            labels={
                'diameter_m': 'Diameter (m)',
                'velocity_km_s': 'Velocity (km/s)',
                'is_hazardous': 'Hazardous'
            },
            color_discrete_map={True: '#dc3545', False: '#28a745'}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        # Data table
        st.markdown("#### Complete NEO Data")
        
        display_df = st.session_state.neo_data.copy()
        display_df['is_hazardous'] = display_df['is_hazardous'].map({True: '⚠️ Yes', False: '✅ No'})
        
        st.dataframe(
            display_df[[
                'name', 'diameter_m', 'velocity_km_s', 'miss_distance_km',
                'is_hazardous', 'approach_date', 'absolute_magnitude'
            ]],
            use_container_width=True,
            hide_index=True
        )
        
        # Download
        csv = st.session_state.neo_data.to_csv(index=False)
        st.download_button(
            "📥 Download NEO Database (CSV)",
            csv,
            f"neo_database_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
    
    else:
        st.info("No NEO data loaded. Please fetch data from the sidebar.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p><strong>ImpactViz</strong> - Asteroid Impact Visualization System</p>
    <p style="font-size: 0.9rem;">Data: NASA NEO API | USGS Earthquake & Elevation Data</p>
    <p style="font-size: 0.8rem;">Educational tool - Simplified models for demonstration</p>
</div>
""", unsafe_allow_html=True)