import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from utils import UM_TO_CM, UJ_TO_J

def render():
    st.header("Dose Target Recipe Explorer")
    st.markdown("---")
    st.info("Explore all combinations of Power and Shots required to achieve a specific Cumulative Dose.", icon="探索")

    with st.container(border=True):
        # --- INPUTS ---
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🎯 Process Goal")
            target_dose = st.number_input("Target Cumulative Dose (J/cm²)", min_value=0.1, value=175.0, step=1.0)
            beam_diameter_um = st.number_input("Beam Spot Diameter (1/e²) (µm)", min_value=1.0, value=30.0, step=0.5)
            rep_rate_khz = st.number_input("Repetition Rate (kHz)", min_value=1.0, value=50.0, step=1.0)
        
        with col2:
            st.subheader("⚙️ Your Machine's Constraints")
            max_power_mW = st.number_input("Maximum Available Power (mW)", min_value=1.0, value=1000.0, step=10.0, help="What is the highest power your laser can reliably output?")
            min_shots = st.number_input("Minimum Practical Shots", min_value=1, value=10, step=1)
            max_shots = st.number_input("Maximum Practical Shots", min_value=1, value=200, step=1)
        
        st.markdown("<br>", unsafe_allow_html=True)
        calculate_button = st.button("Explore Possible Recipes", use_container_width=True, type="primary")

    if calculate_button:
        try:
            if min_shots >= max_shots:
                st.error("Minimum Practical Shots must be less than Maximum Practical Shots.")
                return

            # --- CORE CALCULATIONS ---
            area_cm2 = np.pi * ((beam_diameter_um / 2.0) * UM_TO_CM)**2
            
            # Generate a range of shots for the plot and table
            shots_range = np.arange(min_shots, max_shots + 1)
            
            # Calculate required parameters for each number of shots
            required_peak_fluence = target_dose / shots_range
            required_pulse_energy_J = (required_peak_fluence * area_cm2) / 2.0
            required_avg_power_W = required_pulse_energy_J * (rep_rate_khz * 1000)
            required_avg_power_mW = required_avg_power_W * 1000
            
            # Create a DataFrame for the results table
            df = pd.DataFrame({
                "Number of Shots": shots_range,
                "Required Avg. Power (mW)": required_avg_power_mW,
                "Resulting Peak Fluence (J/cm²)": required_peak_fluence,
                "Implied Pulse Energy (µJ)": (required_avg_power_mW / rep_rate_khz)
            })
            
            # Add a column to check if the recipe is possible on the user's machine
            df["Achievable"] = df["Required Avg. Power (mW)"] <= max_power_mW
            
            # --- CREATE PLOT ---
            fig = go.Figure()
            # Add the main trade-off curve
            fig.add_trace(go.Scatter(x=df["Number of Shots"], y=df["Required Avg. Power (mW)"], mode='lines', name='Required Power'))
            # Add a horizontal line for the machine's power limit
            fig.add_hline(y=max_power_mW, line_dash="dash", line_color="red", annotation_text="Your Max Power", annotation_position="bottom right")
            fig.update_layout(
                title="Power vs. Shots Trade-Off",
                xaxis_title="Number of Shots",
                yaxis_title="Required Average Power (mW)",
            )
            
            # Store results in session state for display
            st.session_state.dose_explorer_results = {"figure": fig, "dataframe": df}

        except Exception as e:
            st.error(f"An error occurred during calculation: {e}")

    if 'dose_explorer_results' in st.session_state:
        results = st.session_state.dose_explorer_results
        fig = results["figure"]
        df = results["dataframe"]
        
        st.markdown("---")
        st.markdown(f'<p class="results-header">Recipe Exploration Canvas</p>', unsafe_allow_html=True)
        
        # Display the interactive plot
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f'<p class="results-header">Possible Recipes Table</p>', unsafe_allow_html=True)
        
        # Function to style the DataFrame
        def style_achievable(row):
            if row.Achievable:
                return ['background-color: #d1fae5'] * len(row) # Light green
            else:
                return ['background-color: #fee2e2'] * len(row) # Light red

        # Display the styled DataFrame
        st.dataframe(
            df.style.apply(style_achievable, axis=1).format({
                "Required Avg. Power (mW)": "{:.2f}",
                "Resulting Peak Fluence (J/cm²)": "{:.3f}",
                "Implied Pulse Energy (µJ)": "{:.3f}"
            }),
            use_container_width=True,
            hide_index=True
        )
