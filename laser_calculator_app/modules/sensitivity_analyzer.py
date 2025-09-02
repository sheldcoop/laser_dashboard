import streamlit as st
import numpy as np
import plotly.graph_objects as go
from utils import UM_TO_CM, UJ_TO_J

# ======================================================================================
# --- NEW: CALCULATION ENGINE WITH CORRECTED LOGIC ---
# ======================================================================================
@st.cache_data
def calculate_tradeoffs(fixed_params):
    p = dict(fixed_params)
    spot_diameters = np.linspace(p['min_spot'], p['max_spot'], 200)
    w0s_um = spot_diameters / 2.0
    w0s_cm = w0s_um * UM_TO_CM
    
    # NEW LOGIC: Calculate Peak Fluence based on the FIXED pulse energy and VARYING spot size
    peak_fluence = (2 * (p['pulse_energy_uJ'] * UJ_TO_J)) / (np.pi * w0s_cm**2)
    fluence_ratio = peak_fluence / p['ablation_threshold']
    
    # Calculate the RESULTING Top Diameter (it's now an output, not an input)
    log_term_top = np.log(np.maximum(1, fluence_ratio))
    top_diameter_um = np.sqrt(2 * w0s_um**2 * log_term_top)
    top_diameter_um = np.nan_to_num(top_diameter_um)

    # The rest of the physics flows from this
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
    # This function is unchanged and correct.
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

def create_geometry_preview(top_d, bottom_d, height, taper):
    """Creates the rich, annotated 'Interactive Engineering Blueprint'."""
    max_width = top_d * 1.6
    fig = go.Figure()

    # 1. Solid material block with gradient
    fig.add_shape(type="rect", x0=-max_width/2, y0=0, x1=max_width/2, y1=-height,
                  fillcolor="rgba(220, 220, 220, 0.7)", line_width=0, layer="below")

    # 2. "Ideal Via" ghost (a semi-transparent rectangle)
    fig.add_shape(type="rect", x0=-top_d/2, y0=0, x1=top_d/2, y1=-height,
                  line=dict(color="rgba(50, 50, 50, 0.5)", width=2, dash="dot"), layer="below",
                  fillcolor="rgba(200, 200, 200, 0.1)")

    # 3. Actual via cutout with inner shadow effect (using a gradient)
    fig.add_shape(type="path",
                  path=f"M {-top_d/2},0 L {top_d/2},0 L {bottom_d/2},{-height} L {-bottom_d/2},{-height} Z",
                  fillcolor="white", line=dict(color="#3498db", width=3), layer="below")

    # 4. Rich, CAD-Style Annotations
    fig.add_shape(type="line", x0=-top_d/2, y0=height*0.2, x1=top_d/2, y1=height*0.2, line=dict(color="black", width=1))
    fig.add_annotation(x=0, y=height*0.25, text=f"Top: {top_d:.2f} µm", showarrow=False, yanchor="bottom")
    if bottom_d > 0.1:
        fig.add_shape(type="line", x0=-bottom_d/2, y0=-height*1.2, x1=bottom_d/2, y1=-height*1.2, line=dict(color="black", width=1))
        fig.add_annotation(x=0, y=-height*1.25, text=f"Bottom: {bottom_d:.2f} µm", showarrow=False, yanchor="top")
    fig.add_shape(type="line", x0=-max_width/2 * 0.7, y0=0, x1=-max_width/2 * 0.7, y1=-height, line=dict(color="black", width=1))
    fig.add_annotation(x=-max_width/2 * 0.75, y=-height/2, text=f"H = {height:.1f} µm", showarrow=False, xanchor="right", textangle=-90)
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
        st.subheader("1. Define Your Fixed Recipe")
        with st.container(border=True):
            pulse_energy_uJ = st.number_input("Fixed Pulse Energy (µJ)", 1.0, 100.0, 20.0, 0.5)
            material_thickness = st.number_input("Material Thickness (µm)", 1.0, 200.0, 35.0, 1.0)
            ablation_threshold = st.number_input("Ablation Threshold (J/cm²)", 0.01, 10.0, 0.18, 0.01)
            penetration_depth = st.number_input("Penetration Depth (µm)", 0.01, 10.0, 0.90, 0.01)

        st.subheader("2. Explore the Trade-Off")
        with st.container(border=True):
            selected_spot = st.slider("Select a Beam Spot Diameter to analyze (µm)", min_value=10.0, max_value=80.0, value=30.0)

    with col_outputs:
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
        energy_ranges = {'good': 7, 'average': 10, 'max': 20}
        taper_ranges = {'good': 10, 'average': 13, 'max': 20}
        window_ranges = {'poor': live_top_d * 0.3, 'average': live_top_d * 0.6, 'max': live_top_d if live_top_d > 0 else 1}
        
        g1, g2, g3 = st.columns(3)
        with g1: st.plotly_chart(create_angular_gauge(live_fluence_ratio, "Energy Efficiency", "x Threshold", energy_ranges, higher_is_better=False), use_container_width=True)
        with g2: st.plotly_chart(create_angular_gauge(live_taper, "Via Quality (Taper)", "°", taper_ranges, higher_is_better=False), use_container_width=True)
        with g3: st.plotly_chart(create_angular_gauge(live_window, "Process Stability", "µm", window_ranges, higher_is_better=True), use_container_width=True)

        st.markdown("---")
        st.subheader("Final Verdict")
        with st.container(border=True):
            TAPER_REJECT_THRESHOLD = taper_ranges['average']
            TAPER_IDEAL_THRESHOLD = taper_ranges['good']
            INEFFICIENT_FLUENCE_RATIO = energy_ranges['average']

            if live_top_d < 5: # Catches cases where ablation is barely happening
                 st.error("❌ **REJECT (No Effective Process)**", icon="🚨")
                 st.markdown("The fluence is too low at this spot size to create a meaningful via. The process is not viable. You must **increase the Pulse Energy** or **decrease the Beam Spot Diameter**.")
            elif live_taper > TAPER_REJECT_THRESHOLD:
                st.error("❌ **REJECT (Poor Quality)**", icon="🚨")
                st.markdown(f"The resulting **taper angle of {live_taper:.1f}° is too high**. This process creates a 'V-shaped' via that is unsuitable for reliable manufacturing. The primary cause is a **Beam Spot Diameter that is too small** for the desired via size.")
            elif live_taper <= TAPER_IDEAL_THRESHOLD and live_fluence_ratio <= INEFFICIENT_FLUENCE_RATIO:
                st.success("✅ **IDEAL PROCESS (Balanced)**", icon="👍")
                st.markdown(f"You have found the **'sweet spot'**. This recipe produces a high-quality via with a **taper of {live_taper:.1f}°**. The energy usage is efficient, and the process is highly stable.")
            elif live_taper <= TAPER_IDEAL_THRESHOLD and live_fluence_ratio > INEFFICIENT_FLUENCE_RATIO:
                st.info("💡 **STABLE BUT INEFFICIENT**", icon="💰")
                st.markdown(f"This recipe produces a **high-quality via (Taper: {live_taper:.1f}°)**, but the energy cost is excessive. The **Beam Spot Diameter is much larger than necessary**, wasting energy.")
            else:
                 st.info("💡 **GOOD COMPROMISE**", icon="👌")
                 st.markdown("This is a **robust and reliable** recipe. It achieves acceptable via quality with good efficiency and stability. A solid choice for production.")

    st.markdown("---")
    with st.expander("Understanding the Scorecard & Preview", expanded=False):
        st.subheader("The Live Geometry Preview")
        st.markdown("This engineering blueprint shows a realistic cross-section of the via. The solid blue shape is the predicted via, while the dotted 'ghost' represents a perfect, straight-walled via. The goal is to make the blue shape match the ghost as closely as possible.")
        st.subheader("Energy Efficiency")
        st.markdown("Measures the **Fluence Ratio**. A lower number is more efficient. The optimal **Green Zone is 0-7x**.")
        st.subheader("Via Quality (Taper)")
        st.markdown("Measures the **Taper Angle (θ)**. A lower angle is better. An angle **below 10° is excellent (Green Zone)**, while an angle **above 13° is a high risk (Red Zone)**.")
        st.subheader("Process Stability")
        st.markdown("Measures the **Process Window** (`Top Diameter - Bottom Diameter`). A wider window is better. A good window is typically **at least 60%** of the resulting top diameter.")
