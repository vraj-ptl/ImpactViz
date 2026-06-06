# ☄️ ImpactViz

**Near-Earth Object Impact Visualization & 3D Orbital Simulation System**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://impactviz-9ewfgbr7y2fxbrrvtv7aeb.streamlit.app/)

**Deployed App Link:** [https://impactviz-9ewfgbr7y2fxbrrvtv7aeb.streamlit.app/](https://impactviz-9ewfgbr7y2fxbrrvtv7aeb.streamlit.app/)

**NASA API Key:** `S0AmYT4r2WkXRmVq7yfDUC24c1jpByzXQwdV1eFa`

ImpactViz is a comprehensive scientific visualization tool designed to track, simulate, and analyze the potential impacts of Near-Earth Objects (NEOs). Using live data from NASA and the USGS, ImpactViz brings orbital mechanics and planetary defense to your browser.

---

## 🌟 Key Features

*   **📡 Live NASA Integration:** Automatically fetches real-time data on upcoming asteroid approaches using the NASA NEO API.
*   **🌌 3D Orbital Simulation:** Visualizes asteroid trajectories around Earth using Keplerian orbital elements (semi-major axis, eccentricity, inclination) in a fully interactive 3D space.
*   **💥 Impact Physics Engine:** Calculates kinetic energy, crater diameter, seismic magnitude, and Torino Impact Hazard Scale based on asteroid mass, velocity, density, and impact angle.
*   **🗺️ Interactive Damage Maps:** Renders blast radii and damage zones (Total Destruction, Severe, Moderate, Light) onto interactive folium maps using USGS topographic and elevation data.
*   **🌍 Seismic Activity Tracking:** Overlays recent global earthquakes from USGS to contextualize seismic risks.

---

## 🚀 How It Works (User Flow)

1.  **Select a Data Source:** 
    *   Choose between **Live NASA Data** (fetches asteroids approaching within the next few days), **Simulated Data**, or **Upload CSV** of custom asteroid parameters.
2.  **Configure Impact Parameters:**
    *   **Select Asteroid:** Pick an asteroid from the database to auto-fill its diameter, velocity, and orbital data.
    *   **Adjust Physics:** Manually tweak the asteroid's density, impact angle, and velocity.
    *   **Target Location:** Select a precise ground-zero impact location on the interactive map (or input Latitude/Longitude manually).
3.  **Run Simulation:**
    *   The app calculates the devastating potential of the impact.
    *   An interactive map will generate showing the exact crater size and color-coded damage zones extending outward.
4.  **Visualize the Orbit:**
    *   Navigate to the **3D Orbit Visualization** tab to explore how close the asteroid's orbital path comes to Earth.

---

## 💻 Local Installation & Setup

If you want to run ImpactViz locally on your own machine:

### 1. Clone the Repository
```bash
git clone https://github.com/vraj-ptl/ImpactViz.git
cd ImpactViz
```

### 2. Install Dependencies
Ensure you have Python installed, then install the required packages:
```bash
pip install -r requirements.txt
```

### 3. Run the Application
Start the Streamlit development server:
```bash
streamlit run src/app.py
```

### 4. Configure API Keys (Optional)
The app uses a `DEMO_KEY` for NASA's API by default, which is rate-limited. 
To avoid rate limits:
1. Get a free API key from [https://api.nasa.gov](https://api.nasa.gov).
2. Enter your key in the app's sidebar under **Configuration**.

---

## 🛠️ Technology Stack
*   **Frontend & Framework:** Streamlit
*   **Data Processing:** Pandas, NumPy, SciPy
*   **Visualizations:** Plotly (3D engine), Folium (Maps)
*   **External APIs:** NASA NEO API, USGS Earthquake & Elevation API
