import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from utils import UM_TO_CM, UJ_TO_J

# ======================================================================================
# --- THE "BRAINS": A Cached Calculation Function ---
# This does all the heavy math. Streamlit will only re-run it if the core goals change.
# ======================================================================================
@st.cache_data
def calculate_sensitivity_data(target_diameter_um, material_thickness, f_th, alpha_inv, spot_size_range):
    """
    Calculates the trade-offs across a range of beam spot sizes for a fixed target diameter.
    """
    results = []
    for spot_size in spot_size_range:
        w0_um = spot_size / 2.0
        
        # --- 1. Calculate Required Energy ---
        # This is the same robust logic from your Goal Seeker
        if w0_um > 0 and (target_diameter_um / 2.0) < w0_um:
            # Standard case: spot is larger than the desired hole radius
            log_term_for_fluence = (target_diameter_um**2) / (2 * w0_um**2)
        else:
            # Extreme case: trying to make a hole wider than the beam, requires massive energy
            log_term_for_fluence = (target_diameter_um**2) / (2 * w0_um**2)
            if log_term_for_fluence > 15: # Cap to prevent infinity errors, represents a practical limit
                log_term_for_fluence = 15

        required_peak_fluence = f_th * np.exp(log_term_for_fluence)
        required_energy_J = (required_peak_fluence * np.pi * (w0_um * UM_TO_CM)**2) / 2.0
        pulse_energy_uJ = required_energy_J / UJ_TO_J

        # --- 2. Calculate Resulting Geometry ---
        depth_per_pulse = alpha_inv * np.log(required_peak_fluence / f_th)
        
        if depth_per_pulse > 0:
            total_shots = int(np.ceil(material_thickness / depth_per_pulse))
            # Calculate total depth profile to find bottom diameter
            r_um = np.linspace(-spot_size * 1.5, spot_size * 1.5, 201)
            fluence_profile = required_peak_fluence * np.exp(-2 * (r_um**2) / w0_um**2)
            depth_profile = alpha_inv * np.log(fluence_profile / f_th)
            total_depth_profile = total_shots * depth_profile
            
            through_mask = total_depth_profile >= material_thickness
            if np.any(through_mask):
                exit_indices = np.where(through_mask)[0]
                bottom_diameter_um = r_um[exit_indices[-1]] - r_um[exit_indices[0]]
            else:
                bottom_diameter_um = 0
        else:
            bottom_diameter_um = 0

        if bottom_diameter_um > 0:
            radius_diff = (target_diameter_um - bottom_diameter_um) / 2.0
            taper_angle_deg = np.rad2deg(np.arctan(radius_diff / material_thickness))
        else:
            taper_angle_deg = 90.0
            
        process_window = target_diameter_um - bottom_diameter_um

        results.append({
            "Beam Spot Diameter (µm)": spot_size,
            "Required Pulse Energy (µJ)": pulse_energy_uJ,
            "Resulting Taper Angle (°)": taper_angle_deg,
            "Process Window (µm)": process_window
        })

    return pd.DataFrame(results)

# ======================================================================================
# --- THE "BODY": The Main Render Function for the UI ---
# ======================================================================================
def render():
    st.header("Spot Size Sensitivity Analyzer")
    st.markdown("---")
    st.info("Interactively explore how changing the Beam Spot Size impacts the energy, quality, and stability of your process for a fixed via diameter.", icon="🔬")

    # --- Two-Column "Control Room" Layout ---
    col_controls, col_canvas = st.columns([2, 3], gap="large")

    with col_controls:
        st.subheader("Control Panel")
        
        with st.container(border=True):
            st.markdown("##### 1. Define Your Fixed Goal")
            target_diameter = st.number_input("Target Top Diameter (µm)", 1.0, 100.0, 25.0, 0.5)
            mat_thick = st.number_input("Material Thickness (µm)", 1.0, 200.0, 40.0, 1.0)
            f_th = st.number_input("Ablation Threshold (J/cm²)", 0.01, 20.0, 0.9, 0.01)
            alpha_inv = st.number_input("Penetration Depth (µm)", 0.01, 10.0, 0.8, 0.01)

        with st.container(border=True):
            st.markdown("##### 2. Explore the Trade-Off")
            # The Master Slider
            selected_spot_size = st.slider(
                "Select a Beam Spot Diameter to analyze (µm)", 
                min_value=15.0, max_value=40.0, value=30.0, step=0.5
            )

    # --- Perform the full analysis across the entire range ---
    spot_size_range = np.linspace(15.0, 40.0, 100) # 100 points for a smooth curve
    df_results = calculate_sensitivity_data(target_diameter, mat_thick, f_th, alpha_inv, spot_size_range)

    with col_canvas:
        st.subheader("Trade-Off Canvas")

        # --- Find the specific results for the slider's current position ---
        closest_row = df_results.iloc[(df_results['Beam Spot Diameter (µm)'] - selected_spot_size).abs().argsort()[:1]]
        
        if not closest_row.empty:
            energy_val = closest_row["Required Pulse Energy (µJ)"].values[0]
            taper_val = closest_row["Resulting Taper Angle (°)"].values[0]
            window_val = closest_row["Process Window (µm)"].values[0]

            # --- Live Readout Panel ---
            st.markdown("<h6>Live Metrics for Selected Spot Size:</h6>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Required Energy", f"{energy_val:.2f} µJ", delta_color="inverse")
            m2.metric("Resulting Taper", f"{taper_val:.2f}°")
            m3.metric("Process Window", f"{window_val:.2f} µm")
            st.markdown("---")


        # --- The Three Synchronized Plots ---
        def create_tradeoff_plot(df, y_col, title, y_label):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Beam Spot Diameter (µm)"], y=df[y_col], mode='lines', line_width=3))
            fig.add_vline(x=selected_spot_size, line_width=2, line_dash="dash", line_color="red")
            fig.update_layout(title=title, xaxis_title="Beam Spot Diameter (µm)", yaxis_title=y_label, margin=dict(t=40, b=40))
            return fig

        fig_energy = create_tradeoff_plot(df_results, "Required Pulse Energy (µJ)", "<b>Plot 1:</b> The Energy Cost", "Pulse Energy (µJ)")
        fig_taper = create_tradeoff_plot(df_results, "Resulting Taper Angle (°)", "<b>Plot 2:</b> The Quality Trade-Off", "Taper Angle (°)")
        fig_window = create_tradeoff_plot(df_results, "Process Window (µm)", "<b>Plot 3:</b> The Stability Margin", "Process Window (µm)")
        
        st.plotly_chart(fig_energy, use_container_width=True)
        st.plotly_chart(fig_taper, use_container_width=True)
        st.plotly_chart(fig_window, use_container_width=True)
