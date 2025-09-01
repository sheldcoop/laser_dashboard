import streamlit as st
import numpy as np
import plotly.graph_objects as go
from utils import UM_TO_CM, UJ_TO_J

# ======================================================================================
# --- CALCULATION ENGINE ---
# This function does all the heavy lifting. It's cached for high performance.
# ======================================================================================
@st.cache_data
def calculate_tradeoffs(fixed_params):
    """Calculates all metrics across a range of spot sizes for a fixed goal."""
    p = dict(fixed_params) # Convert from frozenset back to dict
    
    # Define the range of spot sizes to analyze
    spot_diameters = np.linspace(p['min_spot'], p['max_spot'], 150)
    w0s_um = spot_diameters / 2.0

    # Calculate required fluence for the fixed top diameter
    d_top_cm = p['target_diameter_um'] * UM_TO_CM
    w0s_cm = w0s_um * UM_TO_CM
    
    # Using the inverse Liu model to find required fluence
    required_peak_fluence = p['ablation_threshold'] * np.exp((d_top_cm**2) / (2 * w0s_cm**2))
    
    # Calculate all other metrics based on this required fluence
    required_energy_J = (required_peak_fluence * np.pi * w0s_cm**2) / 2.0
    required_pulse_energy_uJ = required_energy_J / UJ_TO_J
    
    depth_per_pulse = p['penetration_depth'] * np.log(required_peak_fluence / p['ablation_threshold'])
    
    # Use a fixed overkill to ensure a clean via for visualization
    min_shots = np.ceil(p['material_thickness'] / depth_per_pulse)
    total_shots = min_shots + p['overkill_shots']

    # --- Calculate Bottom Diameter (complex part) ---
    # We need to find the radius 'r' where the total depth equals material thickness
    # TotalDepth(r) = total_shots * alpha * ln(F(r)/F_th) = H
    # After solving for r, we get the bottom diameter
    fluence_at_bottom = p['ablation_threshold'] * np.exp(p['material_thickness'] / (total_shots * p['penetration_depth']))
    log_term_bottom = np.log(required_peak_fluence / fluence_at_bottom)
    bottom_diameter_um = np.sqrt(2 * w0s_um**2 * log_term_bottom)
    bottom_diameter_um = np.nan_to_num(bottom_diameter_um) # Handle cases where it doesn't drill through

    taper_angle = np.rad2deg(np.arctan((p['target_diameter_um'] - bottom_diameter_um) / (2 * p['material_thickness'])))
    process_window = p['target_diameter_um'] - bottom_diameter_um

    return {
        "spot_diameters": spot_diameters,
        "pulse_energies": required_pulse_energy_uJ,
        "taper_angles": taper_angle,
        "process_windows": process_window
    }

# ======================================================================================
# --- UI HELPER FUNCTIONS ---
# These functions create our custom "gauges".
# ======================================================================================
def create_gauge(title, value, max_value, unit, higher_is_better=False):
    """Creates a custom, color-coded progress bar gauge."""
    normalized_value = min(value / max_value, 1.0)
    
    if higher_is_better:
        # Green to Red (Bad to Good)
        hue = normalized_value * 120 
    else:
        # Red to Green (Good to Bad)
        hue = (1 - normalized_value) * 120

    bar_color = f"hsl({hue}, 70%, 50%)"
    
    st.markdown(f"**{title}**")
    st.markdown(f"""
        <div style="background-color: #f0f2f6; border-radius: 10px; padding: 5px;">
            <div style="background-color: {bar_color}; width: {normalized_value*100}%; height: 20px; border-radius: 5px; text-align: center; color: white; font-weight: bold; line-height: 20px;">
            </div>
        </div>
        <div style="text-align: right; color: #555;">{value:.2f} {unit}</div>
    """, unsafe_allow_html=True)

# ======================================================================================
# --- MAIN RENDER FUNCTION ---
# This function builds the entire page.
# ======================================================================================
def render():
    st.title("Spot Size Sensitivity Analyzer")
    st.markdown("An interactive storybook to explore the engineering trade-offs of choosing a laser spot size.")
    st.markdown("---")

    # --- LAYOUT ---
    col_inputs, col_outputs = st.columns([2, 3], gap="large")

    # ===================== LEFT COLUMN: THE CONTROL PANEL =====================
    with col_inputs:
        st.subheader("1. Define Your Fixed Goal")
        with st.container(border=True):
            target_diameter_um = st.number_input("Target Top Diameter (µm)", 1.0, 100.0, 25.0, 0.5)
            material_thickness = st.number_input("Material Thickness (µm)", 1.0, 200.0, 30.0, 1.0)
            ablation_threshold = st.number_input("Ablation Threshold (J/cm²)", 0.01, 10.0, 0.2, 0.01)
            penetration_depth = st.number_input("Penetration Depth (µm)", 0.01, 10.0, 0.39, 0.01)

        st.subheader("2. Explore the Trade-Off")
        with st.container(border=True):
            min_spot, max_spot = target_diameter_um * 0.6, target_diameter_um * 2.0
            selected_spot = st.slider(
                "Select a Beam Spot Diameter to analyze (µm)", 
                min_value=min_spot, 
                max_value=max_spot, 
                value=target_diameter_um * 0.98 # Start slightly smaller for effect
            )

    # ===================== RIGHT COLUMN: THE LIVE STORY =====================
    with col_outputs:
        fixed_params = {
            "target_diameter_um": target_diameter_um,
            "material_thickness": material_thickness,
            "ablation_threshold": ablation_threshold,
            "penetration_depth": penetration_depth,
            "min_spot": min_spot,
            "max_spot": max_spot,
            "overkill_shots": 10 # Hardcoded for clean vias
        }
        
        # Run the main calculation
        tradeoff_data = calculate_tradeoffs(frozenset(fixed_params.items()))
        
        # Find the index corresponding to the slider's position
        idx = np.argmin(np.abs(tradeoff_data["spot_diameters"] - selected_spot))
        
        # Get the live values for the metrics
        live_energy = tradeoff_data["pulse_energies"][idx]
        live_taper = tradeoff_data["taper_angles"][idx]
        live_window = tradeoff_data["process_windows"][idx]

        # --- LIVE METRICS PANEL ---
        st.subheader("Live Readout for Selected Spot Size")
        m1, m2, m3 = st.columns(3)
        m1.metric("Required Energy", f"{live_energy:.2f} µJ")
        m2.metric("Resulting Taper", f"{live_taper:.2f}°")
        m3.metric("Process Window", f"{live_window:.2f} µm")
        st.markdown("---")
        
        # --- THE ANIMATED CAUSE & EFFECT DIAGRAM ---
        # Calculate the profiles for the *selected* spot size
        w0_um = selected_spot / 2.0
        w0_cm = w0_um * UM_TO_CM
        required_f0 = ablation_threshold * np.exp((target_diameter_um * UM_TO_CM)**2 / (2 * w0_cm**2))
        depth_per_pulse = penetration_depth * np.log(required_f0 / ablation_threshold)
        min_shots = np.ceil(material_thickness / depth_per_pulse)
        total_shots = min_shots + 10

        r_um = np.linspace(-max_spot, max_spot, 401)
        fluence_profile = required_f0 * np.exp(-2 * r_um**2 / w0_um**2)
        depth_profile_um = penetration_depth * np.log(np.maximum(1, fluence_profile / ablation_threshold))
        total_depth_profile = total_shots * depth_profile_um
        final_via_profile = np.clip(total_depth_profile, 0, material_thickness)

        fig = go.Figure()
        # The "Cause" (Fluence) - Top Half
        fig.add_trace(go.Scatter(x=r_um, y=fluence_profile, mode='lines', line=dict(color='#ef4444', width=3), name='Fluence'))
        fig.add_trace(go.Scatter(x=r_um, y=np.full_like(r_um, ablation_threshold), mode='lines', line=dict(color='grey', dash='dash'), name='Threshold'))
        y_upper = np.maximum(fluence_profile, ablation_threshold)
        fig.add_trace(go.Scatter(x=r_um, y=y_upper, fill='tonexty', mode='none', fillcolor='rgba(239, 68, 68, 0.2)'))
        
        # The "Effect" (Via) - Bottom Half
        fig.add_trace(go.Scatter(x=r_um, y=np.full_like(r_um, -material_thickness), fill='tonexty', y0=-final_via_profile, mode='lines', line_color='#3498db', fillcolor='rgba(220, 220, 220, 0.7)'))
        fig.add_trace(go.Scatter(x=r_um, y=-final_via_profile, mode='lines', line=dict(color='#3498db', width=3)))

        fig.update_layout(
            title="<b>The Live Story:</b> Cause (Energy Profile) & Effect (Via Shape)",
            xaxis_title="Radial Position (µm)", yaxis_title="Fluence (J/cm²) / Depth (µm)",
            showlegend=False, height=400, margin=dict(t=50, l=10, r=10),
            yaxis_range=[-material_thickness * 1.5, max(required_f0 * 1.2, ablation_threshold * 5)]
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- THE GAUGES ---
        st.markdown("---")
        st.subheader("Trade-Off Gauges")
        g1, g2, g3 = st.columns(3)
        with g1:
            create_gauge("Energy Cost / Laser Strain", live_energy, np.max(tradeoff_data["pulse_energies"]), "µJ", higher_is_better=False)
        with g2:
            create_gauge("Via Quality (Lower Taper is Better)", live_taper, np.max(tradeoff_data["taper_angles"]), "°", higher_is_better=False)
        with g3:
            create_gauge("Process Stability (Wider Window is Better)", live_window, np.max(tradeoff_data["process_windows"]), "µm", higher_is_better=True)

        # --- THE DYNAMIC NARRATOR ---
        st.markdown("---")
        narrator_container = st.container(border=True)
        with narrator_container:
            if selected_spot < target_diameter_um * 1.05:
                st.markdown("#### The 'Finesse' Approach")
                st.markdown("Notice the **low energy cost**. The laser is working efficiently. However, the sharp energy profile creates a **V-shaped via** with poor taper quality. This process is also **less stable** and highly sensitive to small changes in laser power.")
            elif selected_spot > target_diameter_um * 1.5:
                st.markdown("#### The 'Brute Force' Approach")
                st.markdown("See how the **energy cost is extremely high**? The laser is working very hard. But the flat, wide energy profile creates a **high-quality, straight-walled via**. This process is **very stable** and robust against minor fluctuations.")
            else:
                st.markdown("#### The 'Balanced' Approach")
                st.markdown("You are in the **'sweet spot'**. The energy cost is moderate, and the via quality is excellent. This recipe provides a good balance between efficiency, quality, and process stability. This is often the ideal target for manufacturing.")
