import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
import os

# Add src to path if needed
sys.path.append(os.path.join(os.getcwd(), 'src'))

from analyzer import Analyzer
from reference_data import HEIGHT_DATA, HANDGRIP_DOM_DATA

# Page Config
st.set_page_config(page_title="DECADE Dashboard", layout="wide")

# Styling
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

st.title('DECADE Interaktives Dashboard')
st.markdown("---")

@st.cache_data
def load_data():
    csv_path = "data/anonym.csv"
    if not os.path.exists(csv_path):
        st.error(f"Datei nicht gefunden: {csv_path}")
        return None
    df = pd.read_csv(csv_path)
    return df

df = load_data()

if df is not None:
    analyzer = Analyzer(df)
    patient_ids = analyzer.get_all_patient_ids()[:15]

    # Sidebar for selection
    st.sidebar.header("Patienten-Auswahl")
    patient_id = st.sidebar.selectbox("Patienten-ID auswählen", patient_ids)

    if patient_id:
        p_data = analyzer.get_patient_data(patient_id)
        
        if p_data:
            meta = p_data['meta']
            sex = meta['sex']
            age = meta['age']
            
            # --- Header Infos ---
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("ID", meta['ID'])
            with col2:
                st.metric("Alter", f"{age} Jahre")
            with col3:
                st.metric("Geschlecht", "Weiblich" if sex == 'girls' else "Männlich")

            st.markdown("### Körperentwicklung & Kraft")

            def create_plotly_chart(metric_type, history_data, sex, title, ylabel):
                fig = go.Figure()
                
                ages = np.arange(6, 19, 1)
                
                # Percentiles names and their colors (matched to existing visualizer)
                p_names = ['P3', 'P10', 'P25', 'P50', 'P75', 'P90', 'P97']
                p_colors = {
                    'P97': 'rgba(204, 204, 204, 0.4)', 
                    'P90': 'rgba(204, 204, 204, 0.6)', 
                    'P75': 'rgba(136, 136, 136, 0.4)',
                    'P50': 'rgba(0, 0, 0, 0.8)',
                    'P25': 'rgba(136, 136, 136, 0.4)', 
                    'P10': 'rgba(204, 204, 204, 0.6)', 
                    'P3': 'rgba(204, 204, 204, 0.4)'
                }
                
                # Fetch Reference Data
                if metric_type == 'groesse':
                    ref_dict = HEIGHT_DATA.get(sex, {})
                elif metric_type == 'handkraft':
                    ref_dict = HANDGRIP_DOM_DATA.get(sex, {})
                else:
                    return None

                # Build Percentile Traces
                for i, p_name in enumerate(p_names):
                    y_vals = []
                    for a in ages:
                        if a in ref_dict:
                            y_vals.append(ref_dict[a][i])
                        else:
                            y_vals.append(None)
                    
                    line_style = dict(color=p_colors[p_name], width=1 if p_name != 'P50' else 3)
                    if p_name != 'P50':
                        line_style['dash'] = 'dash'
                    
                    fig.add_trace(go.Scatter(
                        x=ages, y=y_vals,
                        name=p_name,
                        line=line_style,
                        hoverinfo='skip', # Hide percentile hover to keep it clean
                        showlegend=True if p_name == 'P50' else False
                    ))

                # Add Patient History
                if history_data:
                    p_ages, p_vals = zip(*history_data)
                    
                    # Line
                    fig.add_trace(go.Scatter(
                        x=p_ages, y=p_vals,
                        name="Deine Messung",
                        mode='lines+markers',
                        line=dict(color='red', width=4),
                        marker=dict(size=10, color='red'),
                        hovertemplate="Alter: %{x:.1f} J<br>Wert: %{y:.1f} " + ylabel.split('(')[-1].replace(')', '') + "<extra></extra>"
                    ))
                    
                    # Highlight Last Point
                    fig.add_trace(go.Scatter(
                        x=[p_ages[-1]], y=[p_vals[-1]],
                        mode='markers',
                        marker=dict(size=15, color='red', line=dict(color='white', width=2)),
                        name="Aktuell",
                        showlegend=False,
                        hovertemplate="Aktuelle Messung<br>Alter: %{x:.1f} J<br>Wert: %{y:.1f}<extra></extra>"
                    ))

                fig.update_layout(
                    title=title,
                    xaxis_title="Alter (Jahre)",
                    yaxis_title=ylabel,
                    hovermode="closest",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=20, r=20, t=60, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                )
                fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
                fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
                
                return fig

            # Layout for Charts
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                history_height = p_data.get('groesse', {}).get('history', [])
                if history_height:
                    fig_height = create_plotly_chart(
                        'groesse', 
                        history_height, 
                        sex, 
                        "Körpergrösse Entwicklung", 
                        "Grösse (cm)"
                    )
                    if fig_height:
                        st.plotly_chart(fig_height, use_container_width=True)
                else:
                    st.info("Keine Daten für Körpergrösse vorhanden.")

            with chart_col2:
                history_hand = p_data.get('handkraft', {}).get('history', [])
                if history_hand:
                    fig_hand = create_plotly_chart(
                        'handkraft', 
                        history_hand, 
                        sex, 
                        "Handkraft Entwicklung", 
                        "Kraft (kg)"
                    )
                    if fig_hand:
                        st.plotly_chart(fig_hand, use_container_width=True)
                else:
                    st.info("Keine Daten für Handkraft vorhanden.")

            st.markdown("---")
            st.info("Hinweis: Dies ist eine anonymisierte Demo-Ansicht. Personenbezogene Daten werden nicht gespeichert.")
        else:
            st.warning(f"Keine Daten für Patient {patient_id} gefunden.")
else:
    st.error("Konnte Daten nicht laden. Bitte prüfe, ob data/anonym.csv vorhanden ist.")
