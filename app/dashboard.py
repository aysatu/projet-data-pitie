import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION & STYLE (TON CSS PRÉSERVÉ)
# ==========================================
st.set_page_config(
    page_title="Pilotage Hospitalier - Flux & Tension",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# TON CSS QUI MARCHE (Fond gris clair pour les KPIs)
st.markdown("""
<style>
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
    /* Style pour les sélecteurs radio */
    div[data-testid="stRadio"] > label {
        font-weight: bold;
        color: #0f4c81;
    }
    @media (prefers-color-scheme: dark) {
        div[data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.1) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
        }
        div[data-testid="stMetricLabel"] > label {
            color: #E5E7EB !important;
        }
        div[data-testid="stMetricValue"] {
            color: #F9FAFB !important;
        }
        h1, h2, h3 { 
            color: #60a5fa !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGIQUE MÉTIER & CHARGEMENT (2018-2026)
# ==========================================
@st.cache_data
def load_data():
    # Génération 2018-2026
    start_date = datetime(2018, 1, 1)
    end_date = datetime(2026, 12, 31)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    data = []
    for date in dates:
        # Tendance + Saisonnalité + Bruit
        year_trend = (date.year - 2018) * 5 
        day_of_year = date.timetuple().tm_yday
        seasonality = np.cos((day_of_year / 365) * 2 * np.pi) * 40 
        
        # Pic COVID simulé
        covid_spike = 0
        if 2020 <= date.year <= 2021: covid_spike = 50
        
        noise = np.random.normal(0, 15)
        flux_predit = int(300 + year_trend + seasonality + covid_spike + noise)
        
        # Logique d'alerte
        if flux_predit > 380: alerte = "CRITIQUE"
        elif flux_predit > 350: alerte = "ALERTE"
        elif flux_predit > 320: alerte = "PRE-ALERTE"
        else: alerte = "NORMAL"
            
        data.append({'date': date, 'flux_predit': flux_predit, 'niveau_alerte': alerte})
    
    return pd.DataFrame(data)

def generate_operational_view(total_flux, alerte_level):
    services = ['Urgences', 'Pneumologie', 'Infectieux', 'Gériatrie', 'Chirurgie']
    capacite_totale = {'Urgences': 120, 'Pneumologie': 100, 'Infectieux': 80, 'Gériatrie': 200, 'Chirurgie': 350}
    flux_weights = [0.45, 0.15, 0.10, 0.20, 0.10]
    
    absenteisme_base = 0.10
    if alerte_level == "ALERTE": absenteisme_base = 0.18
    if alerte_level == "CRITIQUE": absenteisme_base = 0.25

    np.random.seed(int(total_flux)) 

    data = []
    for i, svc in enumerate(services):
        patients_service = int(total_flux * flux_weights[i])
        
        taux_abs = absenteisme_base + np.random.uniform(-0.02, 0.05)
        lits_physiques = capacite_totale[svc]
        lits_fermes_rh = int(lits_physiques * taux_abs)
        
        lits_ouverts = lits_physiques - lits_fermes_rh
        lits_dispos = lits_ouverts - patients_service
        if lits_dispos < 0: lits_dispos = 0
        
        taux_occ = (patients_service / lits_ouverts) * 100 if lits_ouverts > 0 else 100
        if taux_occ > 100: taux_occ = 100
        
        ccmu_moyen = np.random.uniform(2.1, 3.8)

        data.append({
            "Service": svc,
            "Capacité Totale": lits_physiques,
            "Lits Fermés (RH)": lits_fermes_rh,
            "Lits Occupés": patients_service,
            "Lits Dispos": lits_dispos,
            "Taux Occ. %": round(taux_occ, 1),
            "CCMU Moyen": round(ccmu_moyen, 1)
        })
        
    return pd.DataFrame(data)

df = load_data()

# ==========================================
# 3. SIDEBAR (LOGIQUE DE NAVIGATION SEMAINE/MOIS AJOUTÉE)
# ==========================================
with st.sidebar:
    st.title("🎛️ Pilotage")
    st.markdown("---")
    
    if not df.empty:
        # A. CHOIX DU MODE DE VUE (L'ajout fonctionnel)
        view_mode = st.radio("Mode de Pilotage :", ["Quotidien (Jour)", "Hebdo (Semaine)", "Mensuel (Mois)"], index=0)
        st.markdown("---")

        min_d = df['date'].min().date()
        max_d = df['date'].max().date()
        default_val = datetime(2025, 2, 28).date()
        
        # B. SÉLECTEURS INTELLIGENTS SELON LA VUE
        if view_mode == "Quotidien (Jour)":
            selected_date = st.date_input("Date Cible", value=default_val, min_value=min_d, max_value=max_d)
            start_date = pd.to_datetime(selected_date)
            end_date = start_date
            
        elif view_mode == "Hebdo (Semaine)":
            selected_date = st.date_input("Sélectionner une date dans la semaine", value=default_val, min_value=min_d, max_value=max_d)
            start_date = pd.to_datetime(selected_date) - timedelta(days=selected_date.weekday())
            end_date = start_date + timedelta(days=6)
            st.info(f"Semaine du {start_date.strftime('%d/%m')} au {end_date.strftime('%d/%m')}")
            
        elif view_mode == "Mensuel (Mois)":
            c_y, c_m = st.columns(2)
            with c_y: year = st.selectbox("Année", range(2018, 2027), index=7) # 2025 par défaut
            with c_m: month = st.selectbox("Mois", range(1, 13), index=1) # Février
            start_date = pd.to_datetime(f"{year}-{month}-01")
            end_date = (start_date + pd.DateOffset(months=1)) - timedelta(days=1)
            
    else:
        st.stop()

# ==========================================
# 4. FILTRAGE ET CALCULS (ADAPTÉS VUE)
# ==========================================
mask_period = (df['date'] >= start_date) & (df['date'] <= end_date)
period_data = df.loc[mask_period]

if period_data.empty:
    st.error("Pas de données sur cette période.")
    st.stop()

# --- AGREGATION DES DONNEES ---
if view_mode == "Quotidien (Jour)":
    # Valeurs exactes
    flux_display = int(period_data['flux_predit'].values[0])
    alerte_display = period_data['niveau_alerte'].values[0]
    kpi_flux_label = "Flux Prédit (J)"
else:
    # Moyennes sur la période
    flux_display = int(period_data['flux_predit'].mean())
    # Alerte : On prend la pire rencontrée pour être prudent
    if "CRITIQUE" in period_data['niveau_alerte'].values: alerte_display = "CRITIQUE"
    elif "ALERTE" in period_data['niveau_alerte'].values: alerte_display = "ALERTE"
    elif "PRE-ALERTE" in period_data['niveau_alerte'].values: alerte_display = "PRE-ALERTE"
    else: alerte_display = "NORMAL"
    kpi_flux_label = "Flux Moyen / Jour"

# Génération des KPIs opérationnels basés sur ce flux (Exact ou Moyen)
df_ops = generate_operational_view(flux_display, alerte_display)

total_dispos = df_ops['Lits Dispos'].sum()
lits_ouverts_totaux = df_ops['Capacité Totale'].sum() - df_ops['Lits Fermés (RH)'].sum()
taux_global = round((df_ops['Lits Occupés'].sum() / lits_ouverts_totaux) * 100, 1)

# ==========================================
# 5. HEADER & ACTIONS
# ==========================================
titre_date = selected_date.strftime('%d/%m/%Y') if view_mode == "Quotidien (Jour)" else f"{start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')}"
st.title(f"🏥 Météo Hospitalière : {titre_date}")

actions_map = {
    "NORMAL": ("🟢 **SITUATION STABLE** : Fonctionnement standard.", "success"),
    "PRE-ALERTE": ("🟡 **VIGILANCE** : Surveiller les flux.", "warning"),
    "ALERTE": ("🟠 **TENSION** : Planifier renforts & déprogrammations.", "warning"),
    "CRITIQUE": ("🔴 **CRITIQUE** : Risque saturation majeur. Cellule de crise.", "error")
}
message, type_alerte = actions_map.get(alerte_display, ("Statut Inconnu", "info"))

if type_alerte == "success": st.success(message)
elif type_alerte == "warning": st.warning(message)
elif type_alerte == "error": st.error(message)
else: st.info(message)

st.markdown("---")

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Niveau d'Alerte", alerte_display, delta="Période", delta_color="off" if alerte_display=="NORMAL" else "inverse")
with c2: st.metric("Taux Occupation Moy.", f"{taux_global}%", delta=f"{100-taux_global:.0f}% Marge", delta_color="inverse")
with c3: st.metric("Lits Disponibles (Moy)", f"{int(total_dispos)}", delta="Net (après RH)") 
with c4: st.metric(kpi_flux_label, f"{flux_display}", delta="Patients")

# ==========================================
# 6. GRAPHIQUE DYNAMIQUE
# ==========================================
st.subheader(f"📈 Tendance des Flux ({view_mode})")

# Adaptation de la fenêtre du graphique selon le mode
today_real = datetime.now()

if view_mode == "Quotidien (Jour)":
    plot_start = start_date - timedelta(days=7)
    plot_end = start_date + timedelta(days=7)
else:
    # En mode période, on affiche exactement la période demandée
    plot_start = start_date
    plot_end = end_date

mask_plot = (df['date'] >= plot_start) & (df['date'] <= plot_end)
chart_data = df.loc[mask_plot].copy()

# Couleur Passé/Futur (basé sur la vraie date système)
chart_data['Type'] = np.where(chart_data['date'] <= today_real, 'Historique', 'Prédiction')

fig = px.line(chart_data, x='date', y='flux_predit', color='Type', 
              color_discrete_map={'Historique': 'grey', 'Prédiction': '#0f4c81'},
              markers=True)

# Ligne Aujourd'hui (Si dans la fenêtre)
if plot_start <= today_real <= plot_end:
    fig.add_vline(x=today_real, line_dash="dash", line_color="green", annotation_text="Aujourd'hui")

# Seuils visuels
fig.add_hline(y=350, line_dash="dot", line_color="orange", annotation_text="Alerte")
fig.add_hline(y=380, line_dash="dot", line_color="red", annotation_text="Critique")

fig.update_layout(height=350, xaxis_title="", yaxis_title="Nb Patients", template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. ANALYSE DÉTAILLÉE
# ==========================================
st.subheader("🔍 Analyse Opérationnelle (Moyenne Période)")

t1, t2, t3 = st.tabs(["📊 Capacité & Lits", "🔥 Gravité & Intensité", "📋 Tableau de Bord"])

with t1:
    df_melt = df_ops.melt(id_vars='Service', value_vars=['Lits Occupés', 'Lits Dispos', 'Lits Fermés (RH)'], var_name='État', value_name='Nombre')
    fig_bar = px.bar(df_melt, x='Service', y='Nombre', color='État', 
                     color_discrete_map={'Lits Occupés': '#3498db', 'Lits Dispos': '#2ecc71', 'Lits Fermés (RH)': '#e74c3c'},
                     title="Capacité Moyenne")
    st.plotly_chart(fig_bar, use_container_width=True)

with t2:
    fig_grav = px.bar(df_ops, x='Service', y='CCMU Moyen', color='CCMU Moyen',
                      title="Sévérité Moyenne", color_continuous_scale='Reds', range_y=[1, 5])
    st.plotly_chart(fig_grav, use_container_width=True)

with t3:
    st.dataframe(
        df_ops.style.background_gradient(subset=['Taux Occ. %'], cmap="Reds", vmin=50, vmax=110)
                .background_gradient(subset=['Lits Dispos'], cmap="Greens", vmin=0, vmax=20)
                .format({"Taux Occ. %": "{:.1f}%", "CCMU Moyen": "{:.1f}"}),
        use_container_width=True
    )
    if view_mode != "Quotidien (Jour)":
        st.caption("ℹ️ Note : Les valeurs affichées sont des **moyennes quotidiennes** sur la période sélectionnée.")