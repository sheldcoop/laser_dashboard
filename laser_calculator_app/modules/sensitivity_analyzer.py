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
# --- NEW: SCORING AND VISUALIZATION HELPERS ---
# ======================================================================================
def calculate_score(fluence_ratio, taper_angle, process_window_pct):
    """Calculates a holistic score from 0-100 based on weighted metrics."""
    # Normalize each metric to a 0-1 score
    # Efficiency: Score is high for low fluence ratios (2x-10x is ideal)
    eff_score = np.interp(fluence_ratio, [2, 10, 50, 200], [1.0, 1.0, 0.5, 0.1])
    # Quality: Score is high for low taper angles (<8 is ideal)
    taper_score = np.interp(taper_angle, [0, 8, 12, 20], [1.0, 1.0, 0.6, 0.1])
    # Stability: Score is high for a wide process window
    stability_score = np.interp(process_window_pct, [0, 0.2, 0.5, 0.8], [0.1, 0.6, 1.0, 1.0])
    
    # Weighted average (Taper quality is most important)
    overall_score = (eff_score * 0.25) + (taper_score * 0.50) + (stability_score * 0.25)
    return int(overall_score * 100), int(eff_score*100), int(taper_score*100), int(stability_score*100)

def render_scorecard(score, eff_score, taper_score, stability_score):
    """Renders the new progress bar scorecard and verdict."""
    
    def get_score_color(s):
        if s >= 90: return "green", "Excellent"
        if s >= 70: return "lightgreen", "Good"
        if s >= 50: return "orange", "Acceptable"
        return "red", "Poor"

    # Custom CSS to color the progress bars
    st.markdown(f"""
        <style>
            .stProgress > div > div > div > div {{
                background-color: {get_score_color(eff_score)[0]};
            }}
            #taper_progress .stProgress > div > div > div > div {{
                background-color: {get_score_color(taper_score)[0]};
            }}
            #stability_progress .stProgress > div > div > div > div {{
                background-color: {get_score_color(stability_score)[0]};
            }}
        </style>
        """, unsafe_allow_html=True)

    st.subheader("The Engineer's Scorecard")
    overall_color, overall_rating = get_score_color(score)
    st.metric(label="Overall Process Score", value=f"{score} / 100", delta=overall_rating)
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1: st.write("**Energy Efficiency**")
    with c2: st.write(f"**Score: {eff_score}/100** ({get_score_color(eff_score)[1]})")
    st.progress(eff_score)

    c1, c2 = st.columns(2)
    with c1: st.write("**Via Quality (Taper)**")
    with c2: st.write(f"**Score: {taper_score}/100** ({get_score_color(taper_score)[1]})")
    st.markdown('<div id="taper_progress">', unsafe_allow_html=True)
    st.progress(taper_score)
    st.markdown('</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1: st.write("**Process Stability**")
    with c2: st.write(f"**Score: {stability_score}/100** ({get_score_color(stability_score)[1]})")
    st.markdown('<div id="stability_progress">', unsafe_allow_html=True)
    st.progress(stability_score)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Final Verdict")
    with st.container(border=True):
        if score >= 90:
            st.success("✅ **Recommendation: IDEAL PROCESS**", icon="👍")
            st.markdown("This recipe represents an **optimal balance** of energy efficiency, world-class via quality, and high process stability. It is the ideal regime for high-volume, high-reliability manufacturing.")
        elif score >= 70:
            st.info("💡 **Recommendation: GOOD COMPROMISE**", icon="👌")
            st.markdown("This is a **robust and reliable** recipe. While not perfectly optimal in every category, it achieves high via quality with acceptable efficiency and stability. A solid choice for production.")
        elif score >= 50:
            st.warning("🟡 **Recommendation: USE WITH CAUTION**", icon="⚠️")
            st.markdown("This recipe has **significant trade-offs**. While it may achieve the target, it likely suffers from either poor energy efficiency (high cost/heat) or low process stability (sensitive to error). Use only if other options are not available.")
        else:
            st.error("❌ **Recommendation: REJECT**", icon="🚨")
            st.markdown("This recipe is **not recommended**. It is either highly unstable, produces a low-quality via (high taper), or is extremely inefficient. It falls outside the acceptable window for a reliable manufacturing process.")

# ======================================================================================
# --- MAIN RENDER FUNCTION ---
# ======================================================================================
def render():
    st.title("Spot Size Sensitivity Analyzer")
    st.markdown("An interactive dashboard to explore the engineering trade-offs of choosing a laser spot size.")
    st.markdown("---")

    col_inputs, col_outputs = st.columns([2, 3], gap="large")

    with col_inputs:
        # --- CONTROL PANEL ---
        st.subheader("1. Define Your Fixed Goal")
        with st.container(border=True):
            target_diameter_um = st.number_input("Target Top Diameter (µm)", 1.0, 100.0, 14.0, 0.5)
            material_thickness = st.number_input("Material Thickness (µm)", 1.0, 200.0, 25.0, 1.0)
            ablation_threshold = st.number_input("Ablation Threshold (J/cm²)", 0.01, 10.0, 0.50, 0.01)
            penetration_depth = st.number_input("Penetration Depth (µm)", 0.01, 10.0, 0.50, 0.01)

        st.subheader("2. Explore the Trade-Off")
        with st.container(border=True):
            min_spot, max_spot = target_diameter_um * 0.8, target_diameter_um * 2.0
            selected_spot = st.slider("Select a Beam Spot Diameter to analyze (µm)", min_value=min_spot, max_value=max_spot, value=target_diameter_um * 1.2)

    with col_outputs:
        # --- CALCULATIONS ---
        fixed_params = {"target_diameter_um": target_diameter_um, "material_thickness": material_thickness, "ablation_threshold": ablation_threshold, "penetration_depth": penetration_depth, "min_spot": min_spot, "max_spot": max_spot, "overkill_shots": 10}
        tradeoff_data = calculate_tradeoffs(frozenset(fixed_params.items()))
        idx = np.argmin(np.abs(tradeoff_data["spot_diameters"] - selected_spot))
        
        live_fluence_ratio = tradeoff_data["fluence_ratios"][idx]
        live_taper = tradeoff_data["taper_angles"][idx]
        live_window = tradeoff_data["process_windows"][idx]

        # --- SCORECARD ---
        overall_score, eff_score, taper_score, stability_score = calculate_score(live_fluence_ratio, live_taper, live_window / target_diameter_um)
        render_scorecard(overall_score, eff_score, taper_score, stability_score)
