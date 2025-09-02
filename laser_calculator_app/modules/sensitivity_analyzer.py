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
# --- VISUALIZATION HELPER FUNCTIONS (GAUGE IS UNCHANGED, PREVIEW IS NEW) ---
# ======================================================================================
def create_angular_gauge(value, title, unit, quality_ranges, higher_is_better=True):
    # (This function is already perfect and remains unchanged)
    # ... (code omitted for brevity, it is the same as your working version)

# --- THE NEW "INTERACTIVE ENGINEERING BLUEPRINT" ---
def create_geometry_preview(top_d, bottom_d, height, taper):
    """Creates a rich, annotated engineering diagram of the via cross-section with an 'ideal' ghost."""
    
    max_width = top_d * 1.6
    
    fig = go.Figure()

    # 1. Draw the solid material block
    fig.add_shape(type="rect", x0=-max_width/2, y0=0, x1=max_width/2, y1=-height,
                  fillcolor="rgba(220, 220, 220, 0.7)", line_width=0)

    # 2. Draw the "Ideal Via" Ghost (a perfect rectangle)
    fig.add_shape(type="rect", x0=-top_d/2, y0=0, x1=top_d/2, y1=-height,
                  line=dict(color="rgba(50, 50, 50, 0.5)", width=2, dash="dot"))

    # 3. Draw the actual via cutout (trapezoid)
    fig.add_shape(type="path",
                  path=f"M {-top_d/2},0 L {top_d/2},0 L {bottom_d/2},{-height} L {-bottom_d/2},{-height} Z",
                  fillcolor="white", line=dict(color="#3498db", width=3))

    # --- Add Rich, CAD-Style Annotations ---
    # Top Diameter Dimension
    fig.add_shape(type="line", x0=-top_d/2, y0=height*0.2, x1=top_d/2, y1=height*0.2, line=dict(color="black", width=1))
    fig.add_annotation(x=0, y=height*0.25, text=f"Top: {top_d:.2f} µm", showarrow=False, yanchor="bottom")

    # Bottom Diameter Dimension
    if bottom_d > 0.1:
        fig.add_shape(type="line", x0=-bottom_d/2, y0=-height*1.2, x1=bottom_d/2, y1=-height*1.2, line=dict(color="black", width=1))
        fig.add_annotation(x=0, y=-height*1.25, text=f"Bottom: {bottom_d:.2f} µm", showarrow=False, yanchor="top")

    # Height Dimension
    fig.add_shape(type="line", x0=-max_width/2 * 0.7, y0=0, x1=-max_width/2 * 0.7, y1=-height, line=dict(color="black", width=1))
    fig.add_annotation(x=-max_width/2 * 0.75, y=-height/2, text=f"H = {height:.1f} µm", showarrow=False, xanchor="right", textangle=-90)

    # Taper Angle Annotation
    fig.add_annotation(x=top_d/2 * 1.1, y=-height/2, text=f"Taper: {taper:.1f}°", showarrow=True,
                       arrowhead=2, ax=40, ay=0, xanchor="left", font=dict(color="black"))
    
    # Clean up the layout to look like a diagram
    fig.update_layout(
        showlegend=False,
        xaxis=dict(visible=False, range=[-max_width/2 * 1.2, max_width/2 * 1.2]),
        yaxis=dict(visible=False, range=[-height*1.5, height*0.5], scaleanchor="x", scaleratio=1),
        margin=dict(l=20, r=20, t=20, b=20),
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
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
            target_diameter_um = st.number_input("Target Top Diameter (µm)", 1.0, 100.0, 50.0, 0.5)
            material_thickness = st.number_input("Material Thickness (µm)", 1.0, 200.0, 80.0, 1.0)
            ablation_threshold = st.number_input("Ablation Threshold (J/cm²)", 0.01, 10.0, 1.0, 0.01)
            penetration_depth = st.number_input("Penetration Depth (µm)", 0.01, 10.0, 0.50, 0.01)

        st.subheader("2. Explore the Trade-Off")
        with st.container(border=True):
            min_spot = target_diameter_um * 0.8
            max_spot = target_diameter_um * 2.0
            default_spot = target_diameter_um * 1.2 
            selected_spot = st.slider("Select a Beam Spot Diameter to analyze (µm)", min_value=min_spot, max_value=max_spot, value=default_spot)

    with col_outputs:
        # --- CALCULATIONS ---
        fixed_params = {"target_diameter_um": target_diameter_um, "material_thickness": material_thickness, "ablation_threshold": ablation_threshold, "penetration_depth": penetration_depth, "min_spot": min_spot, "max_spot": max_spot, "overkill_shots": 10}
        tradeoff_data = calculate_tradeoffs(frozenset(fixed_params.items()))
        idx = np.argmin(np.abs(tradeoff_data["spot_diameters"] - selected_spot))
        
        live_fluence_ratio = tradeoff_data["fluence_ratios"][idx]
        live_taper = tradeoff_data["taper_angles"][idx]
        live_window = tradeoff_data["process_windows"][idx]

        st.subheader("The Engineer's Scorecard")
        
        # --- IMPLEMENTING YOUR EXACT RANGES ---
        energy_ranges = {'good': 7, 'average': 10, 'max': 20}
        taper_ranges = {'good': 10, 'average': 13, 'max': 20}
        window_ranges = {'poor': target_diameter_um * 0.3, 'average': target_diameter_um * 0.6, 'max': target_diameter_um}
        
        g1, g2, g3 = st.columns(3)
        with g1:
            st.plotly_chart(create_angular_gauge(live_fluence_ratio, "Energy Efficiency", "x Threshold", energy_ranges, higher_is_better=False), use_container_width=True)
        with g2:
            st.plotly_chart(create_angular_gauge(live_taper, "Via Quality (Taper)", "°", taper_ranges, higher_is_better=False), use_container_width=True)
        with g3:
            st.plotly_chart(create_angular_gauge(live_window, "Process Stability", "µm", window_ranges, higher_is_better=True), use_container_width=True)

        # --- THE SMARTER "FINAL VERDICT" LOGIC ---
        st.markdown("---")
        st.subheader("Final Verdict")
        
        with st.container(border=True):
            # Define clear, readable thresholds based on our gauge ranges
            TAPER_REJECT_THRESHOLD = taper_ranges['average']
            TAPER_IDEAL_THRESHOLD = taper_ranges['good']
            BLOOMING_THRESHOLD_RATIO = 0.98 # Spot is significantly smaller
            INEFFICIENT_FLUENCE_RATIO = energy_ranges['average']

            # 1. Check for the most critical failure first
            if live_taper > TAPER_REJECT_THRESHOLD:
                st.error("❌ **REJECT (Poor Quality)**", icon="🚨")
                st.markdown(f"The resulting **taper angle of {live_taper:.1f}° is too high** for a reliable IC substrate process. This is the primary failure mode and must be corrected by **increasing the Beam Spot Diameter**.")
            
            # 2. Check for the specific high-risk "blooming" case
            elif selected_spot < (target_diameter_um * BLOOMING_THRESHOLD_RATIO):
                st.warning("⚠️ **HIGH RISK (Forced Blooming)**", icon="☢️")
                st.markdown("The **Beam Spot is significantly smaller than the target via**. This requires extreme energy intensity to 'bloom' the hole to size, creating an unstable, high-stress process that is not recommended for production.")

            # 3. Check for the "Golden Zone"
            elif live_taper <= TAPER_IDEAL_THRESHOLD and live_fluence_ratio <= INEFFICIENT_FLUENCE_RATIO:
                st.success("✅ **IDEAL PROCESS (Balanced)**", icon="👍")
                st.markdown(f"You have found the **'sweet spot'**. This recipe produces a world-class via with a **taper of {live_taper:.1f}°**. The energy usage is efficient, and the process is highly stable. This is the ideal regime for high-quality manufacturing.")
            
            # 4. Check for the stable but wasteful case
            elif live_taper <= TAPER_IDEAL_THRESHOLD and live_fluence_ratio > INEFFICIENT_FLUENCE_RATIO:
                st.info("💡 **STABLE BUT INEFFICIENT**", icon="💰")
                st.markdown(f"This recipe produces a **high-quality via (Taper: {live_taper:.1f}°)** and is very stable. However, the energy cost is becoming excessive. A slightly **smaller spot size** could likely achieve similar quality with better efficiency.")

            # 5. The catch-all "Good Compromise"
            else:
                 st.info("💡 **GOOD COMPROMISE**", icon="👌")
                 st.markdown("This is a **robust and reliable** recipe. It achieves acceptable via quality with good efficiency and stability. A solid choice for production.")

    # --- THE SCIENTIFIC EXPLANATION EXPANDER ---
    st.markdown("---")
    with st.expander("Understanding the Scorecard", expanded=False):
        st.subheader("Energy Efficiency")
        st.markdown("This gauge measures the **Fluence Ratio** (`Peak Fluence / Ablation Threshold`). A lower number is more efficient, as it means less excess energy is wasted as heat. The 'sweet spot' for most processes is between **2x and 10x** the threshold. Per your request, the optimal **Green Zone is 0-5x**.")
        
        st.subheader("Via Quality (Taper)")
        st.markdown("This measures the **Taper Angle (θ)**. A lower angle means straighter walls, which is critical for reliable copper plating. For IC Substrates, an angle **below 8° is excellent (Green Zone)**, while an angle **above 13° is a high risk for manufacturing (Red Zone)**.")

        st.subheader("Process Stability")
        st.markdown("This measures the **Process Window** (`Top Diameter - Bottom Diameter`). A wider window indicates a more 'forgiving' and stable process that is less sensitive to small drifts in laser power. A good process window is typically **at least 60%** of the target top diameter.")
