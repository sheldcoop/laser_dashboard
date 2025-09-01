import streamlit as st
import numpy as np
import plotly.graph_objects as go
from utils import UM_TO_CM, UJ_TO_J

# ======================================================================================
# --- CALCULATION ENGINE (UNCHANGED) ---
# ======================================================================================
@st.cache_data
def calculate_tradeoffs(fixed_params):
    p = dict(fixed_params)
    spot_diameters = np.linspace(p['min_spot'], p['max_spot'], 200)
    w0s_um = spot_diameters / 2.0; w0s_cm = w0s_um * UM_TO_CM
    d_top_cm = p['target_diameter_um'] * UM_TO_CM
    
    required_peak_fluence = p['ablation_threshold'] * np.exp((d_top_cm**2) / (2 * w0s_cm**2))
    fluence_ratio = required_peak_fluence / p['ablation_threshold']
    
    depth_per_pulse = p['penetration_depth'] * np.log(fluence_ratio)
    total_shots = np.ceil(p['material_thickness'] / depth_per_pulse) + p['overkill_shots']
    
    fluence_at_bottom = p['ablation_threshold'] * np.exp(p['material_thickness'] / (total_shots * p['penetration_depth']))
    log_term_bottom = np.log(np.maximum(1, required_peak_fluence / fluence_at_bottom))
    bottom_diameter_um = np.sqrt(2 * w0s_um**2 * log_term_bottom)
    bottom_diameter_um = np.nan_to_num(bottom_diameter_um)
    
    taper_angle = np.rad2deg(np.arctan((p['target_diameter_um'] - bottom_diameter_um) / (2 * p['material_thickness'])))
    process_window = p['target_diameter_um'] - bottom_diameter_um

    return {
        "spot_diameters": spot_diameters, "fluence_ratios": fluence_ratio,
        "taper_angles": taper_angle, "process_windows": process_window
    }

# ======================================================================================
# --- GAUGE VISUALIZATION HELPER (WITH YOUR CUSTOM RANGES) ---
# ======================================================================================
def create_angular_gauge(value, title, unit, quality_ranges, higher_is_better=True):
    """Creates a professional Plotly angular gauge with your specified color logic."""
    
    if higher_is_better:
        green_range, yellow_range, red_range = [quality_ranges['average'], quality_ranges['max']], [quality_ranges['poor'], quality_ranges['average']], [0, quality_ranges['poor']]
    else:
        green_range, yellow_range, red_range = [0, quality_ranges['good']], [quality_ranges['good'], quality_ranges['average']], [quality_ranges['average'], quality_ranges['max']]

    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"<b>{title}</b><br><span style='font-size:0.9em;color:gray'>{unit}</span>", 'font': {"size": 16}},
        gauge = {
            'axis': {'range': [0, quality_ranges['max']], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#34495e", 'thickness': 0.3}, 'bgcolor': "white",
            'borderwidth': 2, 'bordercolor': "#ecf0f1",
            'steps': [
                {'range': green_range, 'color': '#2ecc71'},
                {'range': yellow_range, 'color': '#f1c40f'},
                {'range': red_range, 'color': '#e74c3c'}],
            'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.85, 'value': value}
        }))
    fig.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=30))
    return fig

# ======================================================================================
# --- MAIN RENDER FUNCTION ---
# ======================================================================================
def render():
    st.header("Spot Size Sensitivity Analyzer")
    st.markdown("An interactive dashboard to explore the engineering trade-offs of choosing a laser spot size.")
    st.markdown("---")

    col_inputs, col_outputs = st.columns([2, 3], gap="large")

    with col_inputs:
        # --- CONTROL PANEL ---
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
        # --- CALCULATIONS ---
        fixed_params = {"target_diameter_um": target_diameter_um, "material_thickness": material_thickness, "ablation_threshold": ablation_threshold, "penetration_depth": penetration_depth, "min_spot": min_spot, "max_spot": max_spot, "overkill_shots": 10}
        tradeoff_data = calculate_tradeoffs(frozenset(fixed_params.items()))
        idx = np.argmin(np.abs(tradeoff_data["spot_diameters"] - selected_spot))
        
        live_fluence_ratio = tradeoff_data["fluence_ratios"][idx]
        live_taper = tradeoff_data["taper_angles"][idx]
        live_window = tradeoff_data["process_windows"][idx]

        # --- THE ENGINEER'S SCORECARD (WITH YOUR CUSTOM RANGES) ---
        st.subheader("The Engineer's Scorecard")
        
        # --- IMPLEMENTING YOUR EXACT REQUESTS ---
        energy_ranges = {'poor': 10, 'average': 5, 'good': 0, 'max': 20} # Green: 0-5, Yellow: 5-10, Max: 20
        taper_ranges = {'poor': 13, 'average': 8, 'good': 0, 'max': 20}   # Green: 0-8, Yellow: 8-13
        window_ranges = {'poor': target_diameter_um * 0.25, 'average': target_diameter_um * 0.5, 'good': 0, 'max': target_diameter_um}
        
        g1, g2, g3 = st.columns(3)
        with g1:
            st.plotly_chart(create_angular_gauge(live_fluence_ratio, "Energy Efficiency", "x Threshold", energy_ranges, higher_is_better=False), use_container_width=True)
        with g2:
            st.plotly_chart(create_angular_gauge(live_taper, "Via Quality (Taper)", "°", taper_ranges, higher_is_better=False), use_container_width=True)
        with g3:
            st.plotly_chart(create_angular_gauge(live_window, "Process Stability", "µm", window_ranges, higher_is_better=True), use_container_width=True)

        # --- THE SMARTER "FINAL VERDICT" ---
        # (This section is unchanged and provides the final recommendation)
        st.markdown("---")
        st.subheader("Final Verdict")
        
        is_taper_good = live_taper < taper_ranges['average'] # Is taper in the green or yellow zone?
        is_fluence_good = live_fluence_ratio < energy_ranges['average'] # Is fluence in the green or yellow zone?

        with st.container(border=True):
            if selected_spot < target_diameter_um:
                st.warning("⚠️ **HIGH RISK (Forced Blooming)**", icon="☢️")
                st.markdown("The **Beam Spot is smaller than the target via**. This requires extreme energy intensity to 'bloom' the hole to size. This is a highly unstable, high-stress process that often leads to significant heat damage and is not recommended for production.")
            elif not is_taper_good:
                st.error("❌ **REJECT (Poor Quality)**", icon="🚨")
                st.markdown(f"The resulting **taper angle of {live_taper:.1f}° is too high** for a reliable IC substrate process. It falls outside the acceptable 'golden zone' for quality. **Increase the Beam Spot Diameter** to improve the taper.")
            elif is_taper_good and is_fluence_good:
                st.success("✅ **IDEAL PROCESS (Balanced)**", icon="👍")
                st.markdown(f"You have found the **'sweet spot'**. This recipe produces an excellent via with a **taper of {live_taper:.1f}°**, which is well within the industry's 'golden zone' for IC substrates. The **energy usage is efficient**, and the process is **highly stable**. This is the ideal regime for high-quality manufacturing.")
            else: # Taper might be good, but energy is inefficient
                 st.info("💡 **GOOD COMPROMISE (Stable but Inefficient)**", icon="👌")
                 st.markdown("This is a **robust and reliable** recipe with high via quality. However, the energy usage is becoming inefficient. A slightly smaller spot size could provide the same quality with a lower energy cost.")

    # --- NEW: THE SCIENTIFIC EXPLANATION EXPANDER ---
    st.markdown("---")
    with st.expander("Understanding the Scorecard", expanded=False):
        st.subheader("Energy Efficiency")
        st.markdown("This gauge measures the **Fluence Ratio** (`Peak Fluence / Ablation Threshold`). A lower number is more efficient, as it means less excess energy is being wasted as heat. The 'sweet spot' for most processes is between **2x and 10x** the threshold.")
        
        st.subheader("Via Quality (Taper)")
        st.markdown("This measures the **Taper Angle (θ)**. A lower angle means straighter walls, which is critical for reliable copper plating. For IC Substrates, an angle **below 8° is considered excellent ('Golden Zone')**, while an angle above 13° is typically a high risk for manufacturing.")

        st.subheader("Process Stability")
        st.markdown("This measures the **Process Window** (`Top Diameter - Bottom Diameter`). A wider window indicates a more 'forgiving' and stable process that is less sensitive to small drifts in laser power. A good process window is typically **at least 50%** of the target top diameter.")
