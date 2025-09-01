import streamlit as st

# Step 1: Import only the modules that exist and are being used.
from modules import (
    home,
    process_recommender,
    material_analyzer,
    liu_plot_analyzer,
    thermal_effects_calculator,
    beam_profile_visualizer,
    mask_finder,
    pulse_energy_calculator,
    fluence_calculator
)

# --- PAGE CONFIGURATION ---
st.set_page_config(
    layout="wide", 
    page_title="Laser Dashboard",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR PROFESSIONAL STYLING ---
# This CSS is stable and correct. No changes are needed here.
st.markdown("""
<style>
    /* Main App Styling */
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    /* Sidebar Styling */
    [data-testid="stSidebar"] { padding-top: 1.5rem; }
    /* Home Button Styling */
    [data-testid="stSidebar"] .stButton button[data-testid="stButton-Home"] {
        font-size: 1.5rem;
        font-weight: 700;
        padding: 10px 15px;
        text-align: left !important;
        background-color: transparent;
        color: #111827;
        border: none;
    }
    [data-testid="stSidebar"] .stButton button[data-testid="stButton-Home"]:hover {
        background-color: #F3F4F6;
        color: #ef4444;
    }
    [data-testid="stSidebar"] .stButton button[data-testid="stButton-Home"]:focus {
        box-shadow: none;
    }
    /* Sidebar Buttons (for tools) */
    [data-testid="stSidebar"] .stButton button {
        text-align: left !important;
        font-weight: 500;
        padding: 10px 15px;
        border-radius: 8px;
    }
    /* Sidebar Expanders */
    [data-testid="stSidebar"] .stExpander {
        border: none !important; box-shadow: none !important;
    }
    [data-testid="stSidebar"] .stExpander summary {
        padding: 10px 15px; border-radius: 8px; font-weight: 500; font-size: 1rem;
    }
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --- APP STATE AND NAVIGATION ---
if 'app_mode' not in st.session_state:
    st.session_state.app_mode = "Home"

# --- HIERARCHICAL MODULE DICTIONARY ---
# A single, clean dictionary to define the structure of the sidebar.
TOOL_CATEGORIES = {
    "Core Workflow": {
        "Material Analyzer": material_analyzer,
        "Process Recommender": process_recommender,
        "Microvia Process Simulator": beam_profile_visualizer,
    },
    "Advanced Analysis": {
        "Liu Plot Analyzer": liu_plot_analyzer,
        "Thermal Effects Calculator": thermal_effects_calculator,
    },
    "Fundamental Calculators": {
        "Mask Finder": mask_finder,
        "Pulse Energy": pulse_energy_calculator,
        "Fluence (Energy Density)": fluence_calculator,
    }
}

# --- SIDEBAR RENDERING ---
with st.sidebar:
    # A robust button as the Home anchor
    if st.button("Laser Dashboard", use_container_width=True, key="stButton-Home"):
        st.session_state.app_mode = "Home"
        st.rerun()
    
    st.markdown("---")
    
    # Render the tool groups in expanders
    for category_name, tools in TOOL_CATEGORIES.items():
        with st.expander(category_name, expanded=True):
            for tool_name, tool_module in tools.items():
                btn_type = "primary" if st.session_state.app_mode == tool_name else "secondary"
                if st.button(tool_name, use_container_width=True, type=btn_type):
                    st.session_state.app_mode = tool_name
                    st.rerun()


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
