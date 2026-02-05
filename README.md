# 🏥 Hospital Command Center (HCC)

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28-red)](https://streamlit.io/)
[![XGBoost](https://img.shields.io/badge/Model-XGBoost-green)](https://xgboost.readthedocs.io/)
[![Status](https://img.shields.io/badge/Status-MVP-orange)]()

**Outil de Pilotage Capacitaire & Prédictif par Intelligence Artificielle.**

> *Projet réalisé dans le cadre du Master Data Science - Année 2025/2026.*

## 📄 Contexte
Ce projet est un **MVP (Minimum Viable Product)** développé pour répondre aux besoins de la direction de l'Hôpital de la Pitié-Salpêtrière. 

Face à la saturation récurrente des services et à la gestion "réactive" des crises, cet outil propose une approche **Data-Driven**. Il permet d'anticiper les tensions hospitalières à J+1 et de simuler des scénarios de crise (Grèves, Épidémies) pour ajuster les ressources en amont.

## 🚀 Fonctionnalités Clés

### 1. 🔮 Prédiction & Météo Hospitalière
- **Anticipation J+1 :** Prévision des flux d'admission basée sur l'historique et la saisonnalité.
- **Prospective 2026 :** Utilisation d'une méthode de **prédiction récursive (Multi-step)** pour projeter les tendances budgétaires sur l'année à venir.

### 2. 🎛️ Simulateur de Crise ("Stress Test")
- **Moteur "What-If" :** Permet à la direction de modifier les paramètres critiques en temps réel via des sliders.
- **Scénario Flux :** Simulation d'un afflux massif (ex: Accident, Épidémie).
- **Scénario RH :** Simulation d'un taux d'absentéisme élevé (ex: Grève, Burn-out).
- **Recalcul In-Memory :** Mise à jour instantanée des indicateurs sans latence (calcul vectoriel NumPy).

### 3. 📊 Pilotage Opérationnel
- **Tableau de bord Bed Manager :** Visualisation de la capacité nette (Lits Totaux - Lits Fermés RH).
- **Indicateurs Visuels :** Système d'alerte (Vert/Jaune/Rouge) pour une prise de décision rapide.

---

## ⚙️ Architecture & Data Strategy

### 🛡️ Données Synthétiques (Privacy by Design)
En raison des contraintes RGPD et de l'indisponibilité des données de santé réelles, nous avons développé un **générateur de données synthétiques** robuste :
- **Lois Statistiques :** Distribution Normale (Âge), Distribution Log-Normale (Durée de séjour/LOS).
- **Séries Temporelles :** Injection de tendances annuelles, saisonnalité hivernale et cycles hebdomadaires.
- **Feature Engineering :** Création de *Lag Features* (J-1, J-7) pour capturer l'inertie du système.

### 🧠 Modélisation (Machine Learning)
- **Modèle :** **XGBoost Regressor** (Gradient Boosting).
- **Justification :** Capacité à gérer les non-linéarités et les effets de seuil (saturation brutale) là où la régression linéaire échoue.
- **Performance :** MAE (Erreur Absolue Moyenne) ~13 patients.
- **Explicabilité :** Utilisation de **SHAP** pour garantir la transparence des décisions de l'IA.

---

## 🛠️ Installation & Démarrage

### Pré-requis
- Python 3.8 ou supérieur.
- Git.

### 1. Cloner le dépôt
```bash
git clone [https://github.com/aysatu/projet-data-pitie.git](https://github.com/aysatu/projet-data-pitie.git)
cd projet-data-pitie