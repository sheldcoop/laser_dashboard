import streamlit as st

# Import all modules, including the new dose_target_seeker
from modules import (
    home, process_recommender, material_analyzer, liu_plot_analyzer, 
    thermal_effects_calculator, beam_profile_visualizer, mask_finder, 
    pulse_energy_calculator, fluence_calculator, report_generator,
    dose_target_seeker, # <-- Make sure this is imported
    documentation
)

# --- PAGE CONFIGURATION & CSS ---
st.set_page_config(layout="wide", page_title="Laser Dashboard", initial_sidebar_state="expanded")
# (Your CSS block goes here - omitted for brevity)
# ...

# --- APP STATE AND NAVIGATION ---
if 'app_mode' not in st.session_state:
    st.session_state.app_mode = "Home"

# --- HIERARCHICAL MODULE DICTIONARY ---
TOOL_CATEGORIES = {
    "Core Workflow": {
        "Material Analyzer": material_analyzer,
        "Process Recommender": process_recommender,
        "Microvia Process Simulator": beam_profile_visualizer,
        "Report Generator": report_generator,
    },
    "Advanced Analysis": {
        "Liu Plot Analyzer": liu_plot_analyzer,
        "Thermal Effects Calculator": thermal_effects_calculator,
    },
    "Fundamental Calculators": {
        "Dose Target Seeker": dose_target_seeker, # <-- Make sure this is in the dictionary
        "Fluence (Energy Density)": fluence_calculator,
        "Pulse Energy": pulse_energy_calculator,
        "Mask Finder": mask_finder,
    }
}

# --- SIDEBAR RENDERING ---
with st.sidebar:
    if st.button("Laser Dashboard", use_container_width=True, key="stButton-Home"):
        st.session_state.app_mode = "Home"
        st.rerun()
    st.markdown("---")
    for category_name, tools in TOOL_CATEGORIES.items():
        with st.expander(category_name, expanded=True):
            for tool_name, tool_module in tools.items():
                btn_type = "primary" if st.session_state.app_mode == tool_name else "secondary"
                if st.button(tool_name, use_container_width=True, type=btn_type):
                    st.session_state.app_mode = tool_name
                    st.rerun()
    st.markdown("---")
    doc_btn_type = "primary" if st.session_state.app_mode == "Scientific Reference" else "secondary"
    if st.button("🔬 Scientific Reference", use_container_width=True, type=doc_btn_type):
        st.session_state.app_mode = "Scientific Reference"
        st.rerun()

# --- MAIN PANEL DISPATCHER ---
# (The rest of your dispatcher code remains here, unchanged)
# ...


# --- MAIN PANEL DISPATCHER ---
# A simplified and more robust way to find and render the selected module.
ALL_TOOLS = {"Home": home}
for category in TOOL_CATEGORIES.values():
    ALL_TOOLS.update(category)

selected_module = ALL_TOOLS.get(st.session_state.app_mode)

if selected_module:
    selected_module.render()
else:
    # If for any reason the mode is invalid, safely return to Home.
    st.session_state.app_mode = "Home"
    st.rerun()
