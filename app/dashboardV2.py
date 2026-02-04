import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION & STYLE (TON DESIGN PRÉFÉRÉ)
# ==========================================
st.set_page_config(
    page_title="Pilotage Hospitalier - Flux & Tension",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS STRICTEMENT IDENTIQUE À TON ANCIEN DASHBOARD
st.markdown("""
<style>
    /* Métriques sur fond gris clair (Lisibilité Max) */
    div[data-testid="stMetric"] {
        background-color: rgba(240, 242, 246, 1) !important;
        border: 1px solid #D1D5DB !important;
        padding: 15px !important;
        border-radius: 8px !important;
        color: #1F2937 !important;
    }
    div[data-testid="stMetricLabel"] > label {
        color: #4B5563 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #111827 !important;
        font-weight: 700 !important;
    }
    h1, h2, h3 { 
        color: #0f4c81 !important; 
    }
    /* Mode Simulation : Alerte visuelle */
    .sim-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 15px;
    }
    /* Adaptation Dark Mode */
    @media (prefers-color-scheme: dark) {
        div[data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.1) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
        }
        div[data-testid="stMetricLabel"] > label { color: #E5E7EB !important; }
        div[data-testid="stMetricValue"] { color: #F9FAFB !important; }
        h1, h2, h3 { color: #60a5fa !important; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOTEUR DE DONNÉES (2018-2026 + SCÉNARIOS)
# ==========================================
@st.cache_data
def load_data():
    # Génération longue durée pour "Explorer les tendances"
    start_date = datetime(2018, 1, 1)
    end_date = datetime(2026, 12, 31)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    data = []
    for date in dates:
        # Tendance +5/an
        year_trend = (date.year - 2018) * 5 
        # Saisonnalité Hiver
        day_of_year = date.timetuple().tm_yday
        seasonality = np.cos((day_of_year / 365) * 2 * np.pi) * 40 
        # Pic Covid 2020-21
        covid = 50 if 2020 <= date.year <= 2021 else 0
        
        base_flux = int(300 + year_trend + seasonality + covid + np.random.normal(0, 15))
        data.append({'date': date, 'flux_base': base_flux})
    
    return pd.DataFrame(data)

# Recalcul dynamique de l'alerte selon les sliders
def calculate_alert_level(flux_total):
    if flux_total > 410: return "CRITIQUE"
    elif flux_total > 370: return "ALERTE"
    elif flux_total > 330: return "PRE-ALERTE"
    else: return "NORMAL"

# Générateur de la vue Lits/Personnel/Matériel
def generate_operational_view(total_flux, alerte_level, sim_rh_percent):
    services = ['Urgences', 'Pneumologie', 'Infectieux', 'Gériatrie', 'Chirurgie']
    capacite_totale = {'Urgences': 120, 'Pneumologie': 100, 'Infectieux': 80, 'Gériatrie': 200, 'Chirurgie': 350}
    flux_weights = [0.45, 0.15, 0.10, 0.20, 0.10]
    
    # Absentéisme de base (selon alerte) + SURCHARGE SIMULÉE (Grève, Epidémie)
    abs_base = 0.10
    if alerte_level == "ALERTE": abs_base = 0.15
    if alerte_level == "CRITIQUE": abs_base = 0.20
    
    abs_total = abs_base + (sim_rh_percent / 100.0)
    if abs_total > 1.0: abs_total = 1.0

    np.random.seed(int(total_flux)) 

    data = []
    for i, svc in enumerate(services):
        # Répartition Patients
        patients = int(total_flux * flux_weights[i])
        
        # Impact RH (Lits fermés)
        taux_abs_svc = abs_total + np.random.uniform(-0.02, 0.05)
        if taux_abs_svc < 0: taux_abs_svc = 0
        
        lits_totaux = capacite_totale[svc]
        lits_fermes = int(lits_totaux * taux_abs_svc)
        lits_ouverts = lits_totaux - lits_fermes
        
        # Dispo & Occupation
        lits_dispos = lits_ouverts - patients
        if lits_dispos < 0: lits_dispos = 0
        
        if lits_ouverts > 0:
            taux_occ = (patients / lits_ouverts) * 100
        else:
            taux_occ = 100
        if taux_occ > 100: taux_occ = 100

        data.append({
            "Service": svc,
            "Capacité Totale": lits_totaux,
            "Lits Fermés (RH)": lits_fermes, # KPI Clé pour "Prévision Besoins Personnel"
            "Lits Occupés": patients,
            "Lits Dispos": lits_dispos,      # KPI Clé pour "Prévision Besoins Lits"
            "Taux Occ. %": round(taux_occ, 1),
            "CCMU Moyen": round(np.random.uniform(2.1, 3.8), 1)
        })
        
    return pd.DataFrame(data)

df = load_data()

# ==========================================
# 3. SIDEBAR : EXPLORATION & SCÉNARIOS
# ==========================================
with st.sidebar:
    st.title("🎛️ Pilotage")
    st.markdown("---")
    
    if not df.empty:
        # A. NAVIGATION (Exploration Temporelle)
        st.subheader("1. Navigation")
        view_mode = st.radio("Vue :", ["Quotidien (Jour)", "Hebdo (Semaine)", "Mensuel (Mois)"], index=0)
        
        min_d, max_d = df['date'].min().date(), df['date'].max().date()
        default_val = datetime(2025, 2, 28).date()

        if view_mode == "Quotidien (Jour)":
            selected_date = st.date_input("Date Cible", value=default_val, min_value=min_d, max_value=max_d)
            start_date = end_date = pd.to_datetime(selected_date)
        elif view_mode == "Hebdo (Semaine)":
            selected_date = st.date_input("Semaine du...", value=default_val, min_value=min_d, max_value=max_d)
            start_date = pd.to_datetime(selected_date) - timedelta(days=selected_date.weekday())
            end_date = start_date + timedelta(days=6)
        else:
            c_y, c_m = st.columns(2)
            with c_y: year = st.selectbox("Année", range(2018, 2027), index=7)
            with c_m: month = st.selectbox("Mois", range(1, 13), index=1)
            start_date = pd.to_datetime(f"{year}-{month}-01")
            end_date = (start_date + pd.DateOffset(months=1)) - timedelta(days=1)
        
        st.markdown("---")
        
        # B. SCÉNARIOS (Répond à l'exigence "Simuler épidémie, grève...")
        st.subheader("2. Scénarios (Stress Test)")
        
        sim_flux = st.slider("🌊 Impact Flux (Afflux/Épidémie)", -50, 150, 0, step=10, 
                             help="Ajoute des patients au flux prévu par l'IA.")
        
        sim_rh = st.slider("⚠️ Impact RH (Grève/Absentéisme)", 0, 30, 0, step=5, format="+%d%%",
                           help="Simule une réduction du personnel (augmente les lits fermés).")
            
    else:
        st.stop()

# ==========================================
# 4. CALCULS (MOTEUR DE SIMULATION)
# ==========================================
mask_period = (df['date'] >= start_date) & (df['date'] <= end_date)
period_data = df.loc[mask_period]

if period_data.empty:
    st.error("Pas de données.")
    st.stop()

# Application Scénarios
if view_mode == "Quotidien (Jour)":
    base_flux = int(period_data['flux_base'].values[0])
else:
    base_flux = int(period_data['flux_base'].mean())

# FLUX FINAL = Base IA + Simulation Slider
final_flux = base_flux + sim_flux

# ALERTE FINALE = Recalculée sur le flux simulé
alerte_display = calculate_alert_level(final_flux)

# TABLEAU OPÉRATIONNEL = Prend en compte Flux Simulé + RH Simulé
df_ops = generate_operational_view(final_flux, alerte_display, sim_rh)

# KPIs Globaux
total_dispos = df_ops['Lits Dispos'].sum()
lits_ouverts_total = df_ops['Capacité Totale'].sum() - df_ops['Lits Fermés (RH)'].sum()
if lits_ouverts_total > 0:
    taux_global = round((df_ops['Lits Occupés'].sum() / lits_ouverts_total) * 100, 1)
else:
    taux_global = 100

# ==========================================
# 5. HEADER & ACTIONS (INTERFACE DÉCIDEUR)
# ==========================================
titre = selected_date.strftime('%d/%m/%Y') if view_mode == "Quotidien (Jour)" else f"{start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')}"
st.title(f"🏥 Météo Hospitalière : {titre}")

# Avertissement Simulation
if sim_flux != 0 or sim_rh != 0:
    st.markdown(f"""
    <div class="sim-box">
        ⚠️ SCÉNARIO ACTIVÉ : Flux {sim_flux:+} patients | Impact RH +{sim_rh}%
    </div>
    """, unsafe_allow_html=True)

# Consignes (Ajuster les ressources)
actions_map = {
    "NORMAL": ("🟢 **SITUATION STABLE** : Maintenir le dispositif habituel.", "success"),
    "PRE-ALERTE": ("🟡 **VIGILANCE** : Surveiller les Urgences. Prévoir astreintes.", "warning"),
    "ALERTE": ("🟠 **TENSION** : Ouvrir lits tampons. Déprogrammer non-urgent.", "warning"),
    "CRITIQUE": ("🔴 **PLAN BLANC** : Cellule de crise. Réquisition personnel.", "error")
}
msg, type_msg = actions_map.get(alerte_display, ("Inconnu", "info"))
if type_msg == "success": st.success(msg)
elif type_msg == "warning": st.warning(msg)
elif type_msg == "error": st.error(msg)
else: st.info(msg)

st.markdown("---")

# KPIs
c1, c2, c3, c4 = st.columns(4)
with c1: 
    st.metric("Niveau d'Alerte", alerte_display, delta="Simulé" if sim_flux!=0 else "IA Model", delta_color="off" if alerte_display=="NORMAL" else "inverse")
with c2: 
    st.metric("Taux Occupation", f"{taux_global}%", delta=f"{100-taux_global:.0f}% Marge", delta_color="inverse")
with c3: 
    # Le KPI qui répond à "Prévision besoins Personnel"
    st.metric("Lits Disponibles", f"{int(total_dispos)}", delta=f"-{df_ops['Lits Fermés (RH)'].sum()} lits (Impact RH)", delta_color="inverse") 
with c4: 
    st.metric("Flux Total (Simulé)", f"{final_flux}", delta=f"{sim_flux:+} Scénario" if sim_flux!=0 else "Flux Base")

# ==========================================
# 6. GRAPHIQUE (TENDANCES ADMISSIONS)
# ==========================================
st.subheader(f"📈 Tendance des Flux ({view_mode})")

today_real = datetime.now()
if view_mode == "Quotidien (Jour)":
    p_start, p_end = start_date - timedelta(days=7), start_date + timedelta(days=7)
else:
    p_start, p_end = start_date, end_date

mask_plot = (df['date'] >= p_start) & (df['date'] <= p_end)
chart_data = df.loc[mask_plot].copy()

# Ajout simulation graphique
chart_data['Flux Affiché'] = chart_data['flux_base'] + sim_flux
chart_data['Type'] = np.where(chart_data['date'] <= today_real, 'Historique', 'Simulation' if sim_flux!=0 else 'Prédiction')

fig = px.line(chart_data, x='date', y='Flux Affiché', color='Type', 
              color_discrete_map={'Historique': 'grey', 'Prédiction': '#0f4c81', 'Simulation': '#e67e22'},
              markers=True)

# Seuils
fig.add_hline(y=370, line_dash="dot", line_color="orange", annotation_text="Alerte")
fig.add_hline(y=410, line_dash="dot", line_color="red", annotation_text="Critique")

fig.update_layout(height=350, xaxis_title="", yaxis_title="Nb Patients", template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. DÉTAILS (AJUSTER RESSOURCES)
# ==========================================
st.subheader("🔍 Analyse Opérationnelle & Besoins")

t1, t2, t3 = st.tabs(["📊 Capacité & RH", "🔥 Gravité", "📋 Tableau Gestion"])

with t1:
    # Visualisation des besoins en lits vs personnel manquant
    df_melt = df_ops.melt(id_vars='Service', value_vars=['Lits Occupés', 'Lits Dispos', 'Lits Fermés (RH)'], var_name='État', value_name='Nombre')
    fig_bar = px.bar(df_melt, x='Service', y='Nombre', color='État', 
                     color_discrete_map={'Lits Occupés': '#3498db', 'Lits Dispos': '#2ecc71', 'Lits Fermés (RH)': '#e74c3c'},
                     title="Capacité Réelle (Impact Grève/Absentéisme en Rouge)")
    st.plotly_chart(fig_bar, use_container_width=True)

with t2:
    fig_grav = px.bar(df_ops, x='Service', y='CCMU Moyen', color='CCMU Moyen',
                      title="Sévérité Moyenne (Besoin Matériel)", color_continuous_scale='Reds', range_y=[1, 5])
    st.plotly_chart(fig_grav, use_container_width=True)

with t3:
    # Tableau style "Heatmap"
    st.dataframe(
        df_ops.style.background_gradient(subset=['Taux Occ. %'], cmap="Reds", vmin=50, vmax=110)
                .background_gradient(subset=['Lits Dispos'], cmap="Greens", vmin=0, vmax=20)
                .format({"Taux Occ. %": "{:.1f}%", "CCMU Moyen": "{:.1f}"}),
        use_container_width=True
    )
    if sim_rh > 0:
        st.warning(f"⚠️ **Note :** Le tableau intègre une perte de capacité de {sim_rh}% due au scénario RH.")