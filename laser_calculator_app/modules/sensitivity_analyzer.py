import streamlit as st
import numpy as np
import plotly.graph_objects as go
from utils import UM_TO_CM, UJ_TO_J

# ======================================================================================
# --- CALCULATION ENGINE (VERIFIED AND UNCHANGED) ---
# ======================================================================================
@st.cache_data
def calculate_tradeoffs(fixed_params):
    p = dict(fixed_params)
    spot_diameters = np.linspace(p['min_spot'], p['max_spot'], 200)
    w0s_um = spot_diameters / 2.0; w0s_cm = w0s_um * UM_TO_CM
    
    peak_fluence = (2 * (p['pulse_energy_uJ'] * UJ_TO_J)) / (np.pi * w0s_cm**2)
    fluence_ratio = peak_fluence / p['ablation_threshold']
    
    log_term_top = np.log(np.maximum(1, fluence_ratio))
    top_diameter_um = np.sqrt(2 * w0s_um**2 * log_term_top)
    top_diameter_um = np.nan_to_num(top_diameter_um)

    depth_per_pulse = p['penetration_depth'] * log_term_top
    total_shots = np.ceil(p['material_thickness'] / np.maximum(1e-9, depth_per_pulse)) + p['overkill_shots']
    
    fluence_at_bottom = p['ablation_threshold'] * np.exp(p['material_thickness'] / (total_shots * p['penetration_depth']))
    log_term_bottom = np.log(np.maximum(1, peak_fluence / fluence_at_bottom))
    bottom_diameter_um = np.sqrt(2 * w0s_um**2 * log_term_bottom)
    bottom_diameter_um = np.nan_to_num(bottom_diameter_um)
    
    taper_angle = np.rad2deg(np.arctan(np.maximum(0, (top_diameter_um - bottom_diameter_um)) / (2 * p['material_thickness'])))
    process_window = top_diameter_um - bottom_diameter_um

    return {
        "spot_diameters": spot_diameters, "fluence_ratios": fluence_ratio,
        "taper_angles": taper_angle, "process_windows": process_window,
        "top_diameters": top_diameter_um, "bottom_diameters": bottom_diameter_um
    }

# ======================================================================================
# --- VISUALIZATION HELPER FUNCTIONS ---
# ======================================================================================
def create_angular_gauge(value, title, unit, quality_ranges, higher_is_better=True):
    # This function is correct and remains unchanged.
    if higher_is_better:
        green_range, yellow_range, red_range = [quality_ranges['average'], quality_ranges['max']], [quality_ranges['poor'], quality_ranges['average']], [0, quality_ranges['poor']]
    else:
        green_range, yellow_range, red_range = [0, quality_ranges['good']], [quality_ranges['good'], quality_ranges['average']], [quality_ranges['average'], quality_ranges['max']]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        title={'text': f"<b>{title}</b><br><span style='font-size:0.9em;color:gray'>{unit}</span>", 'font': {"size": 16}},
        gauge={'axis': {'range': [0, quality_ranges['max']]}, 'bar': {'color': "#34495e"},
               'steps': [{'range': green_range, 'color': '#2ecc71'}, {'range': yellow_range, 'color': '#f1c40f'}, {'range': red_range, 'color': '#e74c3c'}]}))
    fig.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=30))
    return fig

# --- THE DEFINITIVE "PHOTOREALISTIC MICROGRAPH" FUNCTION V2 ---
def create_geometry_preview(top_d, bottom_d, height, taper):
    """Creates the rich, photorealistic, annotated 'Interactive Engineering Blueprint'."""
    if not all(np.isfinite([top_d, bottom_d, height, taper])) or top_d <= 0 or height <= 0:
        return go.Figure().update_layout(height=350, annotations=[dict(text="Invalid Process Parameters", showarrow=False)])

    max_width = top_d * 1.8
    copper_thickness = height * 0.05
    fig = go.Figure()

    # 1. Draw the ABF Dielectric (with corrected transparency)
    fig.add_shape(type="rect", x0=-max_width/2, y0=0, x1=max_width/2, y1=-height,
                  fillcolor='rgba(44, 62, 80, 0.7)', line_width=0, layer="below")
    
    # 2. Draw the Copper Layers - bottom is one piece, top is two pieces
    fig.add_shape(type="rect", x0=-max_width/2, y0=-height, x1=max_width/2, y1=-height-copper_thickness, fillcolor='#B87333', line_width=0, layer="below", opacity=0.8)
    fig.add_shape(type="rect", x0=-max_width/2, y0=copper_thickness, x1=-top_d/2, y1=0, fillcolor='#B87333', line_width=0, layer="below", opacity=0.8)
    fig.add_shape(type="rect", x0=top_d/2, y0=copper_thickness, x1=max_width/2, y1=0, fillcolor='#B87333', line_width=0, layer="below", opacity=0.8)

    # 3. Draw the "Ideal Via" Ghost
    fig.add_shape(type="rect", x0=-top_d/2, y0=copper_thickness, x1=top_d/2, y1=-height-copper_thickness,
                  line=dict(color="rgba(231, 76, 60, 0.6)", width=2, dash="dot"), layer="below",
                  fillcolor="rgba(231, 76, 60, 0.05)")

    # 4. Draw the copper-plated via walls
    via_x = [-top_d/2, top_d/2, bottom_d/2, -bottom_d/2]
    via_y = [0, 0, -height, -height]
    fig.add_trace(go.Scatter(x=via_x, y=via_y, fill="toself", fillcolor='white',
                             line=dict(color='#b87333', width=4), mode='lines'))
    
    # --- Add Rich, CAD-Style Annotations ---
    fig.add_shape(type="line", x0=-top_d/2, y0=copper_thickness*2.5, x1=top_d/2, y1=copper_thickness*2.5, line=dict(color="black", width=1))
    fig.add_annotation(x=0, y=copper_thickness*3, text=f"Top: {top_d:.2f} µm", showarrow=False, yanchor="bottom")
    if bottom_d > 0.1:
        fig.add_shape(type="line", x0=-bottom_d/2, y0=-height-copper_thickness*2.5, x1=bottom_d/2, y1=-height-copper_thickness*2.5, line=dict(color="black", width=1))
        fig.add_annotation(x=0, y=-height-copper_thickness*3, text=f"Bottom: {bottom_d:.2f} µm", showarrow=False, yanchor="top")
    fig.add_annotation(x=top_d/2 * 1.1, y=-height/2, text=f"Taper: {taper:.1f}°", showarrow=True, arrowhead=2, ax=40, ay=0, xanchor="left")
    
    fig.update_layout(showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
                      margin=dict(l=20, r=20, t=20, b=20), height=350, paper_bgcolor='rgba(0,0,0,0)')
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
        # Control Panel remains the same
        st.subheader("1. Define Your Fixed Recipe")
        with st.container(border=True):
            pulse_energy_uJ = st.number_input("Fixed Pulse Energy (µJ)", 1.0, 100.0, 18.0, 0.5)
            material_thickness = st.number_input("Material Thickness (µm)", 1.0, 200.0, 35.0, 1.0)
            ablation_threshold = st.number_input("Ablation Threshold (J/cm²)", 0.01, 10.0, 0.19, 0.01)
            penetration_depth = st.number_input("Penetration Depth (µm)", 0.01, 10.0, 0.74, 0.01)

        st.subheader("2. Explore the Trade-Off")
        with st.container(border=True):
            selected_spot = st.slider("Select a Beam Spot Diameter to analyze (µm)", min_value=10.0, max_value=80.0, value=17.82)

    with col_outputs:
        # Calculations remain the same
        fixed_params = {"pulse_energy_uJ": pulse_energy_uJ, "material_thickness": material_thickness, "ablation_threshold": ablation_threshold, "penetration_depth": penetration_depth, "min_spot": 10.0, "max_spot": 80.0, "overkill_shots": 10}
        tradeoff_data = calculate_tradeoffs(frozenset(fixed_params.items()))
        idx = np.argmin(np.abs(tradeoff_data["spot_diameters"] - selected_spot))
        
        live_fluence_ratio = tradeoff_data["fluence_ratios"][idx]
        live_taper = tradeoff_data["taper_angles"][idx]
        live_window = tradeoff_data["process_windows"][idx]
        live_top_d = tradeoff_data["top_diameters"][idx]
        live_bottom_d = tradeoff_data["bottom_diameters"][idx]

        st.subheader("Live Geometry Preview")
        st.plotly_chart(create_geometry_preview(live_top_d, live_bottom_d, material_thickness, live_taper), use_container_width=True)
        st.markdown("---")

        st.subheader("The Engineer's Scorecard")
        
        # --- DEFINITIVE FIX FOR GAUGE RANGES ---
        energy_ranges = {'good': 10, 'average': 50, 'max': 100} 
        taper_ranges = {'good': 8, 'average': 12, 'max': 20}
        window_ranges = {'poor': 4, 'average': 8, 'max': max(15, live_top_d if live_top_d > 0 else 15)}
        
        g1, g2, g3 = st.columns(3)
        with g1: st.plotly_chart(create_angular_gauge(live_fluence_ratio, "Energy Efficiency", "x Threshold", energy_ranges, higher_is_better=False), use_container_width=True)
        with g2: st.plotly_chart(create_angular_gauge(live_taper, "Via Quality (Taper)", "°", taper_ranges, higher_is_better=False), use_container_width=True)
        with g3: st.plotly_chart(create_angular_gauge(live_window, "Process Stability", "µm", window_ranges, higher_is_better=True), use_container_width=True)

        st.markdown("---")
        st.subheader("Final Verdict")
        # The smart narrator logic remains unchanged as it was already robust
        with st.container(border=True):
            # ... (omitted for brevity)

    st.markdown("---")
    with st.expander("Understanding the Scorecard & Preview", expanded=False):
        # ... (omitted for brevity)
