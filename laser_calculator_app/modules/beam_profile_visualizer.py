import streamlit as st
import numpy as np
import plotly.graph_objects as go
from utils import UM_TO_CM, UJ_TO_J

# ======================================================================================
# --- NEW: CACHED CALCULATION FUNCTIONS (Best Practice for Performance) ---
# These functions handle the heavy math. Streamlit will only re-run them if an input changes.
# ======================================================================================

@st.cache_data
def calculate_interactive_simulation(p_dict):
    """Performs the heavy lifting for the simulator. Results are cached."""
    p = p_dict.copy() # Work with a copy to ensure cache safety
    w0_um = p["beam_diameter_um"] / 2
    pulse_energy_j = p["pulse_energy_uJ"] * UJ_TO_J
    r_um = np.linspace(-p["beam_diameter_um"] * 1.5, p["beam_diameter_um"] * 1.5, 501)
    
    if p["beam_profile"] == 'Gaussian':
        peak_fluence_j_cm2 = (2 * pulse_energy_j) / (np.pi * (w0_um * UM_TO_CM)**2) if w0_um > 0 else 0
        fluence_profile = peak_fluence_j_cm2 * np.exp(-2 * (r_um**2) / w0_um**2)
    else: # Top-Hat
        peak_fluence_j_cm2 = pulse_energy_j / (np.pi * (w0_um * UM_TO_CM)**2) if w0_um > 0 else 0
        fluence_profile = np.where(np.abs(r_um) <= w0_um, peak_fluence_j_cm2, 0)

    depth_profile_um = np.zeros_like(fluence_profile)
    ablation_mask = fluence_profile > p["ablation_threshold_j_cm2"]
    
    if np.any(ablation_mask):
        fluence_ratio = fluence_profile[ablation_mask] / p["ablation_threshold_j_cm2"]
        depth_profile_um[ablation_mask] = p["alpha_inv"] * np.log(fluence_ratio)
        if p["beam_profile"] == 'Gaussian':
            log_term = np.log(peak_fluence_j_cm2 / p["ablation_threshold_j_cm2"])
            top_diameter_um = np.sqrt(2 * w0_um**2 * log_term) if log_term > 0 else 0
        else:
            top_diameter_um = p["beam_diameter_um"] if peak_fluence_j_cm2 > p["ablation_threshold_j_cm2"] else 0
    else: 
        top_diameter_um = 0
    
    max_depth_per_pulse = depth_profile_um.max()
    total_depth_profile = p["number_of_shots"] * depth_profile_um
    final_via_profile = np.clip(total_depth_profile, 0, p["material_thickness"])
    
    through_mask = total_depth_profile >= p["material_thickness"]
    if np.any(through_mask):
        exit_indices = np.where(through_mask)[0]
        bottom_diameter_um = r_um[exit_indices[-1]] - r_um[exit_indices[0]]
    else: 
        bottom_diameter_um = 0.0

    if bottom_diameter_um > 0:
        radius_diff = (top_diameter_um - bottom_diameter_um) / 2.0
        taper_angle_deg = np.rad2deg(np.arctan(radius_diff / p["material_thickness"]))
        taper_ratio = radius_diff / p["material_thickness"]
    else:
        taper_angle_deg = 90.0
        taper_ratio = float('inf')

    return {
        "peak_fluence_j_cm2": peak_fluence_j_cm2, "max_depth_per_pulse": max_depth_per_pulse,
        "top_diameter_um": top_diameter_um, "bottom_diameter_um": bottom_diameter_um,
        "taper_angle_deg": taper_angle_deg, "taper_ratio": taper_ratio,
        "r_um": r_um, "fluence_profile": fluence_profile, "final_via_profile": final_via_profile,
        "w0_um": w0_um
    }

@st.cache_data
def calculate_goal_seeker_recipe(p):
    """Performs the heavy lifting for the goal seeker. Results are cached."""
    w0_cm = (p["beam_diameter_um"] / 2.0) * UM_TO_CM
    d_cm = p["target_diameter_um"] * UM_TO_CM
    required_peak_fluence = p["ablation_threshold_j_cm2"] * np.exp((d_cm**2) / (2 * w0_cm**2)) if w0_cm > 0 else 0
    required_energy_J = (required_peak_fluence * np.pi * w0_cm**2) / 2.0
    pulse_energy_uJ = required_energy_J / UJ_TO_J
    max_depth_per_pulse = p["alpha_inv"] * np.log(required_peak_fluence / p["ablation_threshold_j_cm2"]) if required_peak_fluence > p["ablation_threshold_j_cm2"] else 0
    
    if max_depth_per_pulse > 0:
        min_shots = int(np.ceil(p["material_thickness"] / max_depth_per_pulse))
        number_of_shots = min_shots + p["overkill_shots"]
    else: 
        number_of_shots = 0
    
    return {
        "pulse_energy_uJ": pulse_energy_uJ, "number_of_shots": number_of_shots
    }

# ======================================================================================
# MASTER RENDER FUNCTION
# ======================================================================================
def render():
    st.markdown("### Microvia Process Simulator")
    st.info("Interactively simulate a laser drilling process or generate a starting recipe for a specific goal.")
    st.markdown("---")

    col_inputs, col_outputs = st.columns([2, 3], gap="large")

    with col_inputs:
        st.subheader("Control Panel")
        params = render_inputs()

    with col_outputs:
        st.subheader("Results Canvas")
        render_outputs(params)

# ======================================================================================
# INPUT RENDERING FUNCTIONS
# ======================================================================================
def sync_widget(source_key, target_key):
    st.session_state[target_key] = st.session_state[source_key]

def render_inputs():
    if st.session_state.get("switch_to_simulator", False):
        st.session_state.simulator_mode = "Interactive Simulator"
        st.session_state.switch_to_simulator = False
    
    mode_options = ["Interactive Simulator", "Recipe Goal Seeker"]
    current_mode_index = mode_options.index(st.session_state.get("simulator_mode", "Interactive Simulator"))
    calc_mode = st.radio(
        "Select Mode", options=mode_options, index=current_mode_index, 
        key="simulator_mode", horizontal=True
    )

    if calc_mode == "Interactive Simulator":
        if "goal_seeker_results" in st.session_state:
            del st.session_state.goal_seeker_results
        return render_interactive_simulator_inputs()
    else:
        return render_goal_seeker_inputs()

def render_interactive_simulator_inputs():
    params = st.session_state.get("sim_params", {})
    p = {}

    # Initialize master state variables if they don't exist
    for key, default in [("pulse_energy", 10.00), ("beam_diameter", 30.01), ("ablation_threshold", 0.18),
                         ("alpha_inv", 0.30), ("material_thickness", 50.0)]:
        if key not in st.session_state:
            st.session_state[key] = float(params.get(key, default))
    if "number_of_shots" not in st.session_state:
        st.session_state.number_of_shots = int(params.get("number_of_shots", 75))

    with st.container(border=True):
        st.markdown("<h5>Laser Parameters</h5>", unsafe_allow_html=True)
        p["beam_profile"] = st.selectbox("Beam Profile", ["Gaussian", "Top-Hat"])
        
        c1, c2 = st.columns([3, 2])
        with c1:
            st.slider("Pulse Energy (µJ)", 0.01, 20.0, key="pe_slider", value=st.session_state.pulse_energy, on_change=sync_widget, args=("pe_slider", "pulse_energy"))
        with c2:
            st.number_input("PE Value", min_value=0.01, max_value=20.0, step=0.01, key="pe_num", value=st.session_state.pulse_energy, on_change=sync_widget, args=("pe_num", "pulse_energy"), label_visibility="collapsed")
        
        st.markdown("---")
        c1, c2 = st.columns([3, 2])
        with c1:
            st.slider("Beam Spot Diameter (µm)", 1.0, 50.0, key="bd_slider", value=st.session_state.beam_diameter, on_change=sync_widget, args=("bd_slider", "beam_diameter"))
        with c2:
            st.number_input("BD Value", min_value=1.0, max_value=50.0, step=0.1, key="bd_num", value=st.session_state.beam_diameter, on_change=sync_widget, args=("bd_num", "beam_diameter"), label_visibility="collapsed")

    with st.container(border=True):
        st.markdown("<h5>Material Properties</h5>", unsafe_allow_html=True)
        c1, c2 = st.columns([3, 2])
        with c1:
            st.slider("Ablation Threshold (J/cm²)", 0.01, 5.0, key="at_slider", value=st.session_state.ablation_threshold, on_change=sync_widget, args=("at_slider", "ablation_threshold"))
        with c2:
            st.number_input("AT Value", min_value=0.01, max_value=5.0, step=0.01, key="at_num", value=st.session_state.ablation_threshold, on_change=sync_widget, args=("at_num", "ablation_threshold"), label_visibility="collapsed")
        
        st.markdown("---")
        c1, c2 = st.columns([3, 2])
        with c1:
            st.slider("Penetration Depth (α⁻¹) (µm)", 0.01, 5.0, key="ai_slider", value=st.session_state.alpha_inv, on_change=sync_widget, args=("ai_slider", "alpha_inv"))
        with c2:
            st.number_input("AI Value", min_value=0.01, max_value=5.0, step=0.01, key="ai_num", value=st.session_state.alpha_inv, on_change=sync_widget, args=("ai_num", "alpha_inv"), label_visibility="collapsed")

    with st.container(border=True):
        st.markdown("<h5>Process Goal</h5>", unsafe_allow_html=True)
        c1, c2 = st.columns([3, 2])
        with c1:
            st.slider("Number of Shots", 1, 300, key="ns_slider", value=st.session_state.number_of_shots, on_change=sync_widget, args=("ns_slider", "number_of_shots"))
        with c2:
            st.number_input("NS Value", min_value=1, max_value=300, step=1, key="ns_num", value=st.session_state.number_of_shots, on_change=sync_widget, args=("ns_num", "number_of_shots"), label_visibility="collapsed")

        st.markdown("---")
        st.number_input("Material Thickness (µm)", 1.0, 200.0, value=st.session_state.material_thickness, key="mt_num", on_change=sync_widget, args=("mt_num", "material_thickness"))

    # Pass the master state variables to the calculation functions
    p["pulse_energy_uJ"] = st.session_state.pulse_energy
    p["beam_diameter_um"] = st.session_state.beam_diameter
    p["ablation_threshold_j_cm2"] = st.session_state.ablation_threshold
    p["alpha_inv"] = st.session_state.alpha_inv
    p["number_of_shots"] = st.session_state.number_of_shots
    p["material_thickness"] = st.session_state.material_thickness
    
    return p

def render_goal_seeker_inputs():
    p = {}
    with st.container(border=True):
        st.markdown("<h5>🎯 Desired Via</h5>", unsafe_allow_html=True)
        p["target_diameter_um"] = st.number_input("Target Top Diameter (µm)", 1.0, 100.0, 25.0, 0.1)
        p["material_thickness"] = st.number_input("Material Thickness (µm)", 1.0, 200.0, 40.0, 1.0)
        p["overkill_shots"] = st.number_input("Overkill Shots", 0, 100, 10)

    with st.container(border=True):
        st.markdown("<h5>⚙️ Machine Constraints</h5>", unsafe_allow_html=True)
        p["beam_diameter_um"] = st.number_input("Beam Spot Diameter (µm)", 1.0, 100.0, 30.0, 0.5)

    with st.container(border=True):
        st.markdown("<h5>🔬 Material Properties</h5>", unsafe_allow_html=True)
        p["ablation_threshold_j_cm2"] = st.number_input("Ablation Threshold (J/cm²)", 0.01, 20.0, 0.9, 0.01)
        p["alpha_inv"] = st.number_input("Penetration Depth (α⁻¹) (µm)", 0.01, 10.0, 0.8, 0.01)

    return p

# ======================================================================================
# OUTPUT RENDERING FUNCTIONS
# ======================================================================================
def render_outputs(params):
    if st.session_state.simulator_mode == "Interactive Simulator":
        results = calculate_interactive_simulation(params)
        render_interactive_simulator_results(params, results)
    else:
        if st.button("Generate Recipe", type="primary", use_container_width=True):
            recipe = calculate_goal_seeker_recipe(params)
            st.session_state.goal_seeker_results = recipe
        
        if "goal_seeker_results" in st.session_state:
            render_goal_seeker_results(st.session_state.goal_seeker_results, params)
        else:
            st.info("Define your goal and click 'Generate Recipe' to see the results.")

def render_interactive_simulator_results(p, results):
    st.markdown("<h6>Process Metrics</h6>", unsafe_allow_html=True)
    m1, m2 = st.columns(2)
    m1.metric("Peak Fluence", f"{results['peak_fluence_j_cm2']:.2f} J/cm²")
    m2.metric("Depth per Pulse", f"{results['max_depth_per_pulse']:.2f} µm")

    st.markdown("<h6>Predicted Via Geometry</h6>", unsafe_allow_html=True)
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Top Diameter", f"{results['top_diameter_um']:.2f} µm")
    g2.metric("Bottom Diameter", f"{results['bottom_diameter_um']:.2f} µm")
    g3.metric("Wall Angle (Taper)", f"{results['taper_angle_deg']:.2f}°")
    g4.metric("Taper Ratio", f"{results['taper_ratio']:.3f}")
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    fig_fluence = go.Figure()
    fig_fluence.add_trace(go.Scatter(x=results['r_um'], y=results['fluence_profile'], mode='lines', name='Fluence', line=dict(color='#ef4444', width=3)))
    fig_fluence.add_trace(go.Scatter(x=results['r_um'], y=np.full_like(results['r_um'], p["ablation_threshold_j_cm2"]), name='Threshold', mode='lines', line=dict(color='grey', dash='dash')))
    if results['max_depth_per_pulse'] > 0:
        y_upper = np.maximum(results['fluence_profile'], p["ablation_threshold_j_cm2"])
        fig_fluence.add_trace(go.Scatter(x=results['r_um'], y=y_upper, fill='tonexty', mode='none', fillcolor='rgba(239, 68, 68, 0.2)'))
    fig_fluence.update_layout(title="<b>Cause:</b> Applied Fluence Profile", xaxis_title="Radial Position (µm)", yaxis_title="Fluence (J/cm²)", yaxis_range=[0, max(results['peak_fluence_j_cm2'] * 1.1, 1.0)], showlegend=False, margin=dict(t=50, l=10, r=10))
    
    fig_via = go.Figure()
    material_poly_x = np.concatenate([results['r_um'], results['r_um'][::-1]])
    material_poly_y = np.concatenate([-np.full_like(results['r_um'], p["material_thickness"]), -results['final_via_profile'][::-1]])
    fig_via.add_trace(go.Scatter(x=material_poly_x, y=material_poly_y, fill='toself', mode='lines', line_color='#3498db', fillcolor='rgba(220, 220, 220, 0.7)'))
    fig_via.add_trace(go.Scatter(x=results['r_um'], y=-results['final_via_profile'], mode='lines', line=dict(color='#3498db', width=3)))
    status_text = "SUCCESS" if results['bottom_diameter_um'] > 0 else "INCOMPLETE"
    status_color = "#16a34a" if results['bottom_diameter_um'] > 0 else "#ef4444"
    fig_via.add_annotation(x=0, y=-p["material_thickness"]/2, text=status_text, showarrow=False, font=dict(color=status_color, size=16), bgcolor="rgba(255,255,255,0.7)")
    fig_via.add_shape(type="line", x0=-results['top_diameter_um']/2, y0=p["material_thickness"]*0.1, x1=results['top_diameter_um']/2, y1=p["material_thickness"]*0.1, line=dict(color="black", width=1))
    fig_via.add_annotation(x=0, y=p["material_thickness"]*0.15, text=f"Top: {results['top_diameter_um']:.2f} µm", showarrow=False, yanchor="bottom")
    if results['bottom_diameter_um'] > 0:
        fig_via.add_shape(type="line", x0=-results['bottom_diameter_um']/2, y0=-p["material_thickness"]*1.1, x1=results['bottom_diameter_um']/2, y1=-p["material_thickness"]*1.1, line=dict(color="black", width=1))
        fig_via.add_annotation(x=0, y=-p["material_thickness"]*1.15, text=f"Bottom: {results['bottom_diameter_um']:.2f} µm", showarrow=False, yanchor="top")
    fig_via.update_layout(title="<b>Effect:</b> Predicted Microvia Cross-Section", xaxis_title="Radial Position (µm)", yaxis_title="Depth (µm)", yaxis_range=[-p["material_thickness"] * 1.5, p["material_thickness"] * 0.5], showlegend=False, margin=dict(t=50, l=10, r=10))
    
    p1, p2 = st.columns(2)
    p1.plotly_chart(fig_fluence, use_container_width=True)
    p2.plotly_chart(fig_via, use_container_width=True)

    with st.expander("Show Interactive 3D Via Visualization"):
        if results['max_depth_per_pulse'] > 0:
            x_3d, y_3d = np.meshgrid(results['r_um'], results['r_um'])
            R_sq = x_3d**2 + y_3d**2
            
            if p["beam_profile"] == 'Gaussian':
                fluence_3d = results['peak_fluence_j_cm2'] * np.exp(-2 * R_sq / results['w0_um']**2)
            else:
                fluence_3d = np.where(R_sq <= results['w0_um']**2, results['peak_fluence_j_cm2'], 0)

            depth_3d = np.zeros_like(fluence_3d)
            ablation_mask_3d = fluence_3d > p["ablation_threshold_j_cm2"]
            if np.any(ablation_mask_3d):
                fluence_ratio_3d = fluence_3d[ablation_mask_3d] / p["ablation_threshold_j_cm2"]
                depth_3d[ablation_mask_3d] = p["alpha_inv"] * np.log(fluence_ratio_3d)

            total_depth_3d = p["number_of_shots"] * depth_3d
            final_via_3d = np.clip(total_depth_3d, 0, p["material_thickness"])
            z_surface = -final_via_3d

            fig3d = go.Figure(data=[go.Surface(z=z_surface, x=x_3d, y=y_3d, colorscale='Cividis', showscale=False, lighting=dict(ambient=0.6, diffuse=1.0, specular=0.2, roughness=0.5), lightposition=dict(x=100, y=200, z=50))])
            fig3d.update_layout(title='3D View of Via in Material', scene=dict(xaxis_title='X (µm)', yaxis_title='Y (µm)', zaxis_title='Depth (µm)', aspectratio=dict(x=1, y=1, z=0.4), camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))), margin=dict(l=10, r=10, b=10, t=40))
            st.plotly_chart(fig3d, use_container_width=True)
        else:
            st.warning("No ablation occurs with the current settings. Cannot render 3D view.")
    
    st.markdown("---")
    st.markdown("<h5>Next Steps</h5>", unsafe_allow_html=True)
    if st.button("📝 Prepare Report for this Simulation", use_container_width=True):
        st.session_state.report_data = {
            "inputs": {
                "Beam Profile": p["beam_profile"], "Pulse Energy (µJ)": f"{p['pulse_energy_uJ']:.3f}",
                "Beam Diameter (µm)": f"{p['beam_diameter_um']:.2f}", "Ablation Threshold (J/cm²)": f"{p['ablation_threshold_j_cm2']:.3f}",
                "Penetration Depth (µm)": f"{p['alpha_inv']:.3f}", "Number of Shots": str(p['number_of_shots']),
                "Material Thickness (µm)": f"{p['material_thickness']:.2f}"
            },
            "metrics": {
                "Peak Fluence (J/cm²)": f"{results['peak_fluence_j_cm2']:.2f}", "Depth per Pulse (µm)": f"{results['max_depth_per_pulse']:.2f}",
                "Top Diameter (µm)": f"{results['top_diameter_um']:.2f}", "Bottom Diameter (µm)": f"{results['bottom_diameter_um']:.2f}",
                "Wall Angle (Taper) (°)": f"{results['taper_angle_deg']:.2f}", "Taper Ratio": f"{results['taper_ratio']:.3f}"
            },
            "fig_fluence": fig_fluence, "fig_via": fig_via
        }
        st.session_state.app_mode = "Report Generator"
        st.rerun()

def render_goal_seeker_results(recipe, p):
    st.markdown("<h5>Recommended Recipe</h5>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("Required Pulse Energy", f"{recipe['pulse_energy_uJ']:.3f} µJ")
    c2.metric("Required Number of Shots", f"{int(recipe['number_of_shots'])} shots")
    
    st.markdown("---")
    st.markdown("<h5>Next Steps</h5>", unsafe_allow_html=True)
    if st.button("➡️ Load this Recipe in the Interactive Simulator", use_container_width=True):
        st.session_state.sim_params = {
            "pulse_energy": recipe['pulse_energy_uJ'], "number_of_shots": recipe['number_of_shots'],
            "beam_diameter": p['beam_diameter_um'], "ablation_threshold": p['ablation_threshold_j_cm2'],
            "alpha_inv": p['alpha_inv'], "material_thickness": p['material_thickness']
        }
        st.session_state.switch_to_simulator = True
        # Also update the master state variables directly
        st.session_state.pulse_energy = recipe['pulse_energy_uJ']
        st.session_state.number_of_shots = int(recipe['number_of_shots'])
        st.session_state.beam_diameter = p['beam_diameter_um']
        st.session_state.ablation_threshold = p['ablation_threshold_j_cm2']
        st.session_state.alpha_inv = p['alpha_inv']
        st.session_state.material_thickness = p['material_thickness']
        st.rerun()
