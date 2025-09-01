import streamlit as st
import numpy as np
from utils import UM_TO_CM, UJ_TO_J

def render():
    st.header("Dose Target Seeker")
    st.markdown("---")
    st.info("Calculate the required laser settings to achieve a specific Cumulative Dose.", icon="🎯")

    with st.container(border=True):
        # --- MODE SELECTION ---
        solve_for = st.radio(
            "What do you want to calculate?",
            ["Required Average Power", "Required Number of Shots"],
            horizontal=True,
            key="dose_seeker_mode"
        )

        st.markdown("---")

        # --- COMMON INPUTS ---
        st.subheader("Process & Material Inputs")
        col1, col2, col3 = st.columns(3)
        with col1:
            target_dose = st.number_input("Target Cumulative Dose (J/cm²)", min_value=0.1, value=175.0, step=1.0)
        with col2:
            beam_diameter_um = st.number_input("Beam Spot Diameter (1/e²) (µm)", min_value=1.0, value=30.0, step=0.5)
        with col3:
            rep_rate_khz = st.number_input("Repetition Rate (kHz)", min_value=1.0, value=50.0, step=1.0)

        # --- CONDITIONAL INPUTS (THE CONSTRAINT) ---
        st.subheader("Process Constraint")
        if solve_for == "Required Average Power":
            number_of_shots = st.number_input("Target Number of Shots", min_value=1, value=50, step=1)
        else: # Solve for Number of Shots
            avg_power_mW = st.number_input("Available Average Power (mW)", min_value=0.1, value=500.0, step=1.0)
        
        st.markdown("<br>", unsafe_allow_html=True)
        calculate_button = st.button("Calculate Recipe", use_container_width=True, type="primary")

    if calculate_button:
        try:
            # --- REVERSE CALCULATIONS ---
            area_cm2 = np.pi * ((beam_diameter_um / 2.0) * UM_TO_CM)**2
            
            if solve_for == "Required Average Power":
                if number_of_shots <= 0:
                    st.error("Number of Shots must be greater than zero.")
                    return
                
                required_peak_fluence = target_dose / number_of_shots
                required_pulse_energy_J = (required_peak_fluence * area_cm2) / 2.0
                required_avg_power_W = required_pulse_energy_J * (rep_rate_khz * 1000)
                required_avg_power_mW = required_avg_power_W * 1000
                
                # Store results for display
                st.session_state.dose_results = {
                    "Required Avg. Power (mW)": f"{required_avg_power_mW:.2f}",
                    "Implied Pulse Energy (µJ)": f"{(required_avg_power_mW / rep_rate_khz):.3f}",
                    "Resulting Peak Fluence (J/cm²)": f"{required_peak_fluence:.3f}"
                }

            else: # Solve for Number of Shots
                if avg_power_mW <= 0:
                    st.error("Average Power must be greater than zero.")
                    return
                
                pulse_energy_uJ = avg_power_mW / rep_rate_khz
                pulse_energy_J = pulse_energy_uJ * UJ_TO_J
                peak_fluence = (2 * pulse_energy_J) / area_cm2
                
                if peak_fluence <= 0:
                    st.error("Calculated Peak Fluence is zero or negative. Cannot achieve target dose with these settings.")
                    return

                required_shots = np.ceil(target_dose / peak_fluence)

                st.session_state.dose_results = {
                    "Required Number of Shots": f"{int(required_shots)}",
                    "Using Pulse Energy (µJ)": f"{pulse_energy_uJ:.3f}",
                    "Resulting Peak Fluence (J/cm²)": f"{peak_fluence:.3f}"
                }
        except Exception as e:
            st.error(f"An error occurred during calculation: {e}")

    if 'dose_results' in st.session_state:
        st.markdown("---")
        st.markdown(f'<p class="results-header">Calculation Results</p>', unsafe_allow_html=True)
        
        res_col1, res_col2, res_col3 = st.columns(3)
        results = st.session_state.dose_results
        
        # Display metrics in a consistent order
        key1 = list(results.keys())[0]
        key2 = list(results.keys())[1]
        key3 = list(results.keys())[2]
        
        res_col1.metric(key1, results[key1])
        res_col2.metric(key2, results[key2])
        res_col3.metric(key3, results[key3])
