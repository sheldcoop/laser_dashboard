import streamlit as st

# Import all modules
from modules import (
    home, process_recommender, material_analyzer, liu_plot_analyzer, 
    thermal_effects_calculator, beam_profile_visualizer, mask_finder, 
    pulse_energy_calculator, fluence_calculator, 
    documentation  # <-- 1. Import the new documentation module
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
        color: #111827; /* Dark text color */
        border: none;
    }
    [data-testid="stSidebar"] .stButton button[data-testid="stButton-Home"]:hover {
        background-color: #F3F4F6; /* Light gray hover */
        color: #ef4444; /* Theme color on hover */
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
# This dictionary is also correct and does not need to be changed.
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
    # Robust Button as Home Anchor
    if st.button("Laser Dashboard", use_container_width=True, key="stButton-Home"):
        st.session_state.app_mode = "Home"
        st.rerun()
    
    st.markdown("---")
    
    # All tool groups in expanders
    for category_name, tools in TOOL_CATEGORIES.items():
        with st.expander(category_name, expanded=True):
            for tool_name, tool_module in tools.items():
                btn_type = "primary" if st.session_state.app_mode == tool_name else "secondary"
                if st.button(tool_name, use_container_width=True, type=btn_type):
                    st.session_state.app_mode = tool_name
                    st.rerun()
    
    # <-- 2. Add the dedicated button for the documentation below the tool expanders
    st.markdown("---")
    doc_btn_type = "primary" if st.session_state.app_mode == "Scientific Reference" else "secondary"
    if st.button("🔬 Scientific Reference", use_container_width=True, type=doc_btn_type):
        st.session_state.app_mode = "Scientific Reference"
        st.rerun()


# --- MAIN PANEL DISPATCHER ---
selected_module = None

if st.session_state.app_mode == "Home":
    selected_module = home
# <-- 3. Add logic to handle the new "Scientific Reference" mode
elif st.session_state.app_mode == "Scientific Reference":
    selected_module = documentation
else:
    for category in TOOL_CATEGORIES.values():
        if st.session_state.app_mode in category:
            selected_module = category[st.session_state.app_mode]
            break

# Render the found module
if selected_module:
    selected_module.render()
else:
    st.session_state.app_mode = "Home"
    st.rerun()
