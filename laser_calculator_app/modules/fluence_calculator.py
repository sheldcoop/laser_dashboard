import streamlit as st
import pandas as pd
from utils import parse_text_input, convert_df_to_csv
from core.fluence import calculate_fluence
from modules.download_utils import create_download_hub # <-- STEP 1: IMPORT THE TOOLKIT

def render():
    st.header("Calculate Fluence & Cumulative Dose")
    st.markdown("---")
    
    # --- UI State Management ---
    if 'clear_fluence_form' not in st.session_state:
        st.session_state.clear_fluence_form = False

    def clear_form():
        st.session_state.clear_fluence_form = True
        st.session_state.results_df = None

    # --- INPUT FORM ---
    use_avg_power = st.toggle(
        "Input using Average Power",
        help="Toggle on to calculate pulse energy from average power and repetition rate.",
        key="fluence_toggle"
    )

    with st.form(key="fluence_form"):
        col1, col2 = st.columns(2)
        with col1:
            if use_avg_power:
                avg_power_str = st.text_input("Average Power (mW)", placeholder="e.g., 80, 90, 100", key="fluence_power")
                rep_rate_str = st.text_input("Repetition Rate (kHz)", placeholder="e.g., 50, 60", key="fluence_rate")
            else:
                pulse_energy_str = st.text_input("Pulse Energy (µJ)", placeholder="e.g., 1.6, 1.8", key="fluence_energy")
        
        with col2:
            diameter_str = st.text_input("Beam Spot Diameter (1/e²) (µm)", placeholder="e.g., 10, 12", key="fluence_diameter")
            shots_str = st.text_input("Number of Shots", placeholder="e.g., 40, 50", key="fluence_shots")

        with st.expander("Show Formulas"):
            st.latex(r'''\text{Peak Fluence (J/cm²)} = 2 \times \frac{\text{Pulse Energy (J)}}{\text{Area (cm²)}}''')
            st.latex(r'''\text{Pulse Energy (J)} = \frac{\text{Average Power (W)}}{\text{Repetition Rate (Hz)}}''')

        # --- ACTION BUTTONS ---
        submit_button = st.form_submit_button(label='Calculate Fluence', type="primary")
        clear_button = st.form_submit_button(label='Clear', on_click=clear_form)

    if clear_button:
        st.rerun()

    # --- CALCULATION LOGIC ---
    if submit_button and not st.session_state.clear_fluence_form:
        try:
            diameter_list = parse_text_input(diameter_str)
            shots_list = [int(s) for s in parse_text_input(shots_str)]
            energy_list, power_list, rate_list = None, None, None

            if use_avg_power:
                power_list = parse_text_input(avg_power_str)
                rate_list = parse_text_input(rep_rate_str)
                if not all([power_list, rate_list, diameter_list, shots_list]):
                    st.warning("Please enter values in all required fields.")
                    return
            else:
                energy_list = parse_text_input(pulse_energy_str)
                if not all([energy_list, diameter_list, shots_list]):
                    st.warning("Please enter values in all required fields.")
                    return
            
            with st.spinner("Calculating..."):
                results_.df = calculate_fluence(
                    diameter_list=diameter_list, shots_list=shots_list,
                    energy_list=energy_list, power_list=power_list, rate_list=rate_list
                )
                st.session_state.results_df = results_df

        except ValueError as e:
            st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

    st.session_state.clear_fluence_form = False

    # --- DISPLAY RESULTS ---
    if 'results_df' in st.session_state and st.session_state.results_df is not None and not st.session_state.results_df.empty:
        st.markdown("---")
        st.markdown("### Calculation Results")

        df = st.session_state.results_df

        # --- METRIC DISPLAY FOR SINGLE RESULT ---
        if len(df) == 1:
            st.markdown("---")
            col1, col2 = st.columns(2)
            peak_fluence = df['Peak Fluence (J/cm²)'].iloc[0]
            cumulative_dose = df['Cumulative Dose (J/cm²)'].iloc[0]
            col1.metric(label="Peak Fluence", value=f"{peak_fluence:.3f} J/cm²")
            col2.metric(label="Cumulative Dose", value=f"{cumulative_dose:.3f} J/cm²")
            st.markdown("---")

        # --- DATAFRAME DISPLAY FOR ALL RESULTS ---
        ideal_order = [
            'Avg. Power (mW)', 'Rep. Rate (kHz)', 'Pulse Energy (µJ)',
            'Diameter (µm)', 'Number of Shots', 'Peak Fluence (J/cm²)', 'Cumulative Dose (J/cm²)'
        ]
        cols_to_show = [col for col in ideal_order if col in df.columns]
        formatters = {
            'Pulse Energy (µJ)': '{:.3f}', 'Peak Fluence (J/cm²)': '{:.3f}',
            'Cumulative Dose (J/cm²)': '{:.3f}', 'Area (cm²)': '{:.4e}'
        }
        st.dataframe(df[cols_to_show].style.format(formatters), use_container_width=True, hide_index=True)

        # --- STEP 2: USE THE MASTER TOOLKIT ---
        create_download_hub(df[cols_to_show], "fluence_results")
