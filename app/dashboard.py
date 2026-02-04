import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Pilotage Hospitalier - Flux & Tension",
    page_icon="🏥",
    layout="wide"
)

# --- GÉNÉRATION DE DONNÉES FICTIVES (MOCK DATA) ---
# Cette fonction simule vos données pour que le dashboard soit visuel tout de suite
def get_mock_data():
    # Services
    services = ['Urgences', 'Pneumologie', 'Infectieux', 'Chirurgie', 'Réa']
    
    # Création d'un dataframe opérationnel
    data = []
    for svc in services:
        total_lits = np.random.randint(20, 50)
        lits_fermes = np.random.randint(0, 5) # Dû à l'absentéisme
        occupes = np.random.randint(total_lits - lits_fermes - 5, total_lits - lits_fermes)
        dispos = (total_lits - lits_fermes) - occupes
        taux_occ = round((occupes / (total_lits - lits_fermes)) * 100, 1)
        gravite_moyenne = np.random.randint(1, 5)
        
        data.append([svc, total_lits, lits_fermes, occupes, dispos, taux_occ, gravite_moyenne])
        
    df_ops = pd.DataFrame(data, columns=['Service', 'Lits Totaux', 'Lits Fermés (RH)', 'Lits Occupés', 'Lits Dispos', 'Taux Occupation %', 'CCMU Moyen'])
    
    # Données temporelles pour le flux (Passé + Futur)
    dates = pd.date_range(end=datetime.now() + timedelta(days=1), periods=48, freq='H')
    flux = [np.random.randint(5, 20) + (i/2) for i in range(48)] # Tendance à la hausse
    df_flux = pd.DataFrame({'Heure': dates, 'Arrivées': flux})
    df_flux['Type'] = ['Réel'] * 24 + ['Prédiction'] * 24
    
    return df_ops, df_flux

# Chargement des données
df_ops, df_flux = get_mock_data()

# --- CALCUL DES KPIS GLOBAUX ---
total_lits_dispos = df_ops['Lits Dispos'].sum()
taux_occupation_global = round(df_ops['Lits Occupés'].sum() / (df_ops['Lits Totaux'].sum() - df_ops['Lits Fermés (RH)'].sum()) * 100, 1)
flux_j_plus_1 = df_flux[df_flux['Type'] == 'Prédiction']['Arrivées'].sum()

# Détermination du niveau d'alerte (Logique métier)
if taux_occupation_global > 90 or total_lits_dispos < 5:
    niveau_alerte = "CRITIQUE"
    couleur_alerte = "inverse" # Rouge dans st.metric
elif taux_occupation_global > 80:
    niveau_alerte = "TENSION"
    couleur_alerte = "off"
else:
    niveau_alerte = "NORMAL"
    couleur_alerte = "normal"

# --- INTERFACE UTILISATEUR ---

# 1. EN-TÊTE & KPIS (D'après photo 1 & 2)
st.title("🏥 Dashboard Opérationnel : Flux & Activité")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Niveau d'Alerte", value=niveau_alerte, delta="Seuil Crise > 90%", delta_color=couleur_alerte)

with col2:
    st.metric(label="Taux d'Occupation Global", value=f"{taux_occupation_global}%", delta=f"{100-taux_occupation_global}% marge", delta_color="inverse")

with col3:
    st.metric(label="Lits Disponibles (Temps Réel)", value=total_lits_dispos, delta="-2 vs hier")

with col4:
    st.metric(label="Prévision Flux (24h)", value=int(flux_j_plus_1), delta="+15% vs J-1")

# 2. SECTION FLUX & PRÉDICTION (D'après photo 2 "Flux attendu à J+1")
st.markdown("### 📈 Dynamique des Flux (Réel vs Prédiction)")

# Graphique combiné Passé/Futur
fig_flux = px.line(df_flux, x='Heure', y='Arrivées', color='Type', 
                   color_discrete_map={"Réel": "green", "Prédiction": "red"},
                   title="Flux Patients : Historique 24h et Prévision 24h")
# Ajout d'une zone d'ombre pour marquer le futur
fig_flux.add_vrect(x0=datetime.now(), x1=df_flux['Heure'].max(), fillcolor="red", opacity=0.1, line_width=0)
st.plotly_chart(fig_flux, use_container_width=True)

# 3. ANALYSE DÉTAILLÉE (D'après photo 2 "Répartition par service" & "Gravité")
st.markdown("### 🔍 Analyse par Service & Gravité")

tab1, tab2 = st.tabs(["Vue Services (Lits)", "Vue Gravité (Patients)"])

with tab1:
    # Graphique en barres de l'occupation par service
    fig_occ = px.bar(df_ops, x='Service', y=['Lits Occupés', 'Lits Dispos'], 
                     title="Capacité par Service", barmode='stack',
                     color_discrete_map={'Lits Occupés': '#ef553b', 'Lits Dispos': '#00cc96'})
    st.plotly_chart(fig_occ, use_container_width=True)

with tab2:
    # Graphique de la gravité (CCMU)
    fig_grav = px.bar(df_ops, x='Service', y='CCMU Moyen', color='CCMU Moyen',
                      title="Intensité Moyenne de la Prise en Charge (CCMU)",
                      color_continuous_scale='RdYlGn_r') # Rouge si élevé
    st.plotly_chart(fig_grav, use_container_width=True)

# 4. TABLEAU OPÉRATIONNEL (D'après photo 1 "Table opérationnel")
st.markdown("### 📋 Tableau de Bord Opérationnel (Gestion des Lits)")

# Styling du tableau pour mettre en évidence les lits dispos
st.dataframe(
    df_ops.style.background_gradient(subset=['Taux Occupation %'], cmap="Reds")
          .background_gradient(subset=['Lits Dispos'], cmap="Greens"),
    use_container_width=True
)

# Note de bas de page sur l'absentéisme (Basé sur l'analyse précédente)
st.warning("⚠️ **Note RH :** Les 'Lits Fermés' sont calculés sur la base du taux d'absentéisme actuel. Un taux > 20% impacte directement la capacité d'accueil.")