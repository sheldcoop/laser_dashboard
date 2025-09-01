import streamlit as st
import numpy as np
import plotly.graph_objects as go
from utils import UM_TO_CM, UJ_TO_J

# ======================================================================================
# --- CALCULATION ENGINE (REMAINS UNCHANGED) ---
# ======================================================================================
@st.cache_data
def calculate_tradeoffs(fixed_params):
    p = dict(fixed_params)
    spot_diameters = np.linspace(p['min_spot'], p['max_spot'], 200)
    w0s_um = spot_diameters / 2.0; w0s_cm = w0s_um * UM_TO_CM
    d_top_cm = p['target_diameter_um'] * UM_TO_CM
    
    required_peak_fluence = p['ablation_threshold'] * np.exp((d_top_cm**2) / (2 * w0s_cm**2))
    required_energy_J = (required_peak_fluence * np.pi * w0s_cm**2) / 2.0
    required_pulse_energy_uJ = required_energy_J / UJ_TO_J
    
    depth_per_pulse = p['penetration_depth'] * np.log(required_peak_fluence / p['ablation_threshold'])
    total_shots = np.ceil(p['material_thickness'] / depth_per_pulse) + p['overkill_shots']
    
    fluence_at_bottom = p['ablation_threshold'] * np.exp(p['material_thickness'] / (total_shots * p['penetration_depth']))
    log_term_bottom = np.log(np.maximum(1, required_peak_fluence / fluence_at_bottom))
    bottom_diameter_um = np.sqrt(2 * w0s_um**2 * log_term_bottom)
    bottom_diameter_um = np.nan_to_num(bottom_diameter_um)
    
    taper_angle = np.rad2deg(np.arctan((p['target_diameter_um'] - bottom_diameter_um) / (2 * p['material_thickness'])))
    process_window = p['target_diameter_um'] - bottom_diameter_um

    return {
        "spot_diameters": spot_diameters, "pulse_energies": required_pulse_energy_uJ,
        "taper_angles": taper_angle, "process_windows": process_window
    }

# ======================================================================================
# --- NEW: VISUALIZATION HELPER FOR ANGULAR GAUGES ---
# ======================================================================================
def create_angular_gauge(value, title, unit, quality_ranges, higher_is_better=True):
    """Creates a beautiful, professional Plotly angular gauge (speedometer)."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"<b>{title}</b><br><span style='font-size:0.9em;color:gray'>{unit}</span>", 'font': {"size": 16}},
        gauge = {
            'axis': {'range': [None, quality_ranges['max']], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#34495e", 'thickness': 0.3},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#ecf0f1",
            'steps': [
                {'range': [0, quality_ranges['poor']], 'color': '#e74c3c'},
                {'range': [quality_ranges['poor'], quality_ranges['average']], 'color': '#f1c40f'},
                {'range': [quality_ranges['average'], quality_ranges['max']], 'color': '#2ecc71'}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': quality_ranges['good_threshold']}
        }))
    fig.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=30))
    return fig

# ======================================================================================
# --- MAIN RENDER FUNCTION ---
# ======================================================================================
def render():
    st.title("Spot Size Sensitivity Analyzer")
    st.markdown("An interactive dashboard to explore the engineering trade-offs of choosing a laser spot size.")
    st.markdown("---")

    col_inputs, col_outputs = st.columns([2, 3], gap="large")

    with col_inputs:
        # --- CONTROL PANEL (UNCHANGED) ---
        st.subheader("1. Define Your Fixed Goal")
        with st.container(border=True):
            target_diameter_um = st.number_input("Target Top Diameter (µm)", 1.0, 100.0, 14.0, 0.5)
            material_thickness = st.number_input("Material Thickness (µm)", 1.0, 200.0, 25.0, 1.0)
            ablation_threshold = st.number_input("Ablation Threshold (J/cm²)", 0.01, 10.0, 0.50, 0.01)
            penetration_depth = st.number_input("Penetration Depth (µm)", 0.01, 10.0, 0.50, 0.01)

        st.subheader("2. Explore the Trade-Off")
        with st.container(border=True):
            min_spot, max_spot = target_diameter_um * 0.8, target_diameter_um * 2.0
            selected_spot = st.slider("Select a Beam Spot Diameter to analyze (µm)", min_value=min_spot, max_value=max_spot, value=target_diameter_um * 1.2)

    with col_outputs:
        # --- CALCULATIONS (UNCHANGED) ---
        fixed_params = {"target_diameter_um": target_diameter_um, "material_thickness": material_thickness, "ablation_threshold": ablation_threshold, "penetration_depth": penetration_depth, "min_spot": min_spot, "max_spot": max_spot, "overkill_shots": 10}
        tradeoff_data = calculate_tradeoffs(frozenset(fixed_params.items()))
        idx = np.argmin(np.abs(tradeoff_data["spot_diameters"] - selected_spot))
        live_energy = tradeoff_data["pulse_energies"][idx]
        live_taper = tradeoff_data["taper_angles"][idx]
        live_window = tradeoff_data["process_windows"][idx]

        # --- ANIMATED PLOT (UNCHANGED) ---
        st.subheader("The Live Story: Cause vs. Effect")
        w0_um = selected_spot / 2.0; w0_cm = w0_um * UM_TO_CM
        required_f0 = ablation_threshold * np.exp((target_diameter_um * UM_TO_CM)**2 / (2 * w0_cm**2))
        depth_per_pulse = penetration_depth * np.log(required_f0 / ablation_threshold)
        total_shots = np.ceil(material_thickness / depth_per_pulse) + 10
        r_um = np.linspace(-max_spot, max_spot, 401)
        fluence_profile = required_f0 * np.exp(-2 * r_um**2 / w0_um**2)
        depth_profile_um = penetration_depth * np.log(np.maximum(1, fluence_profile / ablation_threshold))
        total_depth_profile = total_shots * depth_profile_um
        final_via_profile = np.clip(total_depth_profile, 0, material_thickness)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=r_um, y=fluence_profile, mode='lines', line=dict(color='#e74c3c', width=4), name='Fluence'))
        fig.add_trace(go.Scatter(x=r_um, y=np.full_like(r_um, ablation_threshold), mode='lines', line=dict(color='grey', dash='dash')))
        y_upper = np.maximum(fluence_profile, ablation_threshold); fig.add_trace(go.Scatter(x=r_um, y=y_upper, fill='tonexty', mode='none', fillcolor='rgba(231, 76, 60, 0.2)'))
        fig.add_trace(go.Scatter(x=r_um, y=np.full_like(r_um, -material_thickness), fill='tonexty', y0=-final_via_profile, mode='lines', line_color='#3498db', fillcolor='rgba(236, 240, 241, 0.7)'))
        fig.add_trace(go.Scatter(x=r_um, y=-final_via_profile, mode='lines', line=dict(color='#2980b9', width=4)))
        fig.update_layout(xaxis_title="Radial Position (µm)", yaxis_title="Fluence / Depth (µm)", showlegend=False, height=300, margin=dict(t=20, l=10, r=10), yaxis_range=[-material_thickness * 1.5, max(required_f0 * 1.2, ablation_threshold * 5)])
        st.plotly_chart(fig, use_container_width=True)

        # --- NEW: THE ENGINEER'S SCORECARD ---
        st.markdown("---")
        st.subheader("The Engineer's Scorecard")
        
        # Define dynamic quality ranges for gauges
        energy_ranges = {'poor': np.percentile(tradeoff_data["pulse_energies"], 80), 'average': np.percentile(tradeoff_data["pulse_energies"], 40), 'good': 0, 'max': np.max(tradeoff_data["pulse_energies"]), 'good_threshold': np.percentile(tradeoff_data["pulse_energies"], 20)}
        taper_ranges = {'poor': 12, 'average': 8, 'good': 0, 'max': 20, 'good_threshold': 10} # Based on your rule
        window_ranges = {'poor': np.percentile(tradeoff_data["process_windows"], 20), 'average': np.percentile(tradeoff_data["process_windows"], 60), 'good': np.max(tradeoff_data["process_windows"]), 'max': np.max(tradeoff_data["process_windows"]), 'good_threshold': np.percentile(tradeoff_data["process_windows"], 80)}
        
        g1, g2, g3 = st.columns(3)
        with g1:
            st.plotly_chart(create_angular_gauge(live_energy, "Energy Efficiency", "µJ", energy_ranges, higher_is_better=False), use_container_width=True)
        with g2:
            st.plotly_chart(create_angular_gauge(live_taper, "Via Quality (Taper)", "°", taper_ranges, higher_is_better=False), use_container_width=True)
        with g3:
            st.plotly_chart(create_angular_gauge(live_window, "Process Stability", "µm", window_ranges, higher_is_better=True), use_container_width=True)

        # --- NEW: THE SMARTER EXECUTIVE SUMMARY ---
        st.markdown("---")
        st.subheader("Final Verdict")
        
        # Define the "sweet spot" for spot size based on your rule
        sweet_spot_min = target_diameter_um * 1.0
        sweet_spot_max = target_diameter_um * 1.20

        is_in_sweet_spot = sweet_spot_min <= selected_spot <= sweet_spot_max
        is_taper_good = live_taper < 15

        with st.container(border=True):
            if not is_taper_good:
                st.error("❌ **Recommendation: REJECT**", icon="🚨")
                st.markdown(f"The resulting **taper angle of {live_taper:.1f}° is too high** for a reliable IC substrate process. This recipe falls outside the acceptable 'golden zone' for quality. **Increase the Beam Spot Diameter** to improve the taper.")
            
            elif not is_in_sweet_spot:
                st.warning("🟡 **Recommendation: USE WITH CAUTION**", icon="⚠️")
                if selected_spot < sweet_spot_min:
                    st.markdown("The selected **Beam Spot is smaller than the target via**. This requires extreme energy intensity to 'bloom' the hole to size. While the taper is good, this is a high-stress, inefficient process that can lead to heat damage.")
                else: # Spot is too large
                    st.markdown("The selected **Beam Spot is much larger than necessary**. While this creates a very stable process with good taper, the **energy cost is becoming excessive**. A smaller spot size would be more efficient.")

            else: # Taper is good AND it's in the sweet spot
                st.success("✅ **Recommendation: IDEAL PROCESS**", icon="👍")
                st.markdown(f"You have found the **'sweet spot'**. This recipe produces an excellent via with a **taper of {live_taper:.1f}°**, which is well within the industry's 'golden zone' for IC substrates. The **energy cost is moderate**, and the process is **highly stable**. This is the ideal regime for high-quality manufacturing.")
