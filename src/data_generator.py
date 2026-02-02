import pandas as pd
import numpy as np
from datetime import timedelta, date
import random
import uuid
import os

# --- 1. CONFIGURATION "VÉRITÉ TERRAIN" (2018-2025) ---
START_DATE = date(2018, 1, 1)
END_DATE = date(2025, 12, 31)

# Capacité officielle (~1717 lits) éclatée par spécialité
CAPACITY_CONFIG = {
    "Cardiologie": {"Lits": 150, "Staff_Jour": 20},
    "Neurologie": {"Lits": 140, "Staff_Jour": 20},
    "Pneumologie": {"Lits": 100, "Staff_Jour": 15},
    "Infectieux": {"Lits": 80, "Staff_Jour": 12},
    "Geriatrie": {"Lits": 200, "Staff_Jour": 25},
    "Medecine_Interne": {"Lits": 174, "Staff_Jour": 20},
    "Chirurgie_Ortho": {"Lits": 200, "Staff_Jour": 25},
    "Chirurgie_Viscerale": {"Lits": 150, "Staff_Jour": 20},
    "Chirurgie_Cardio": {"Lits": 100, "Staff_Jour": 15},
    "Neurochirurgie": {"Lits": 111, "Staff_Jour": 15},
    "Psychiatrie": {"Lits": 115, "Staff_Jour": 25},
    "Gyneco_Obstetrique": {"Lits": 56, "Staff_Jour": 10},
    "Urgences": {"Lits": 100, "Staff_Jour": 60}
}

SERVICES = list(CAPACITY_CONFIG.keys())

MOTIFS_ADMISSION = [
    "Detresse Respiratoire", "Douleur Thoracique", "Suspicion AVC", "Traumatisme Membres", 
    "Traumatisme Cranien", "Douleur Abdominale Aigue", "Malaise/Syncope", "Fievre Inexpliquee",
    "Intoxication", "Crise d'Angoisse/Agitation", "Accouchement", "Chute Personne Agee"
]

TYPES_EQUIPEMENTS = [
    "Scanner", "IRM", "Echo-Doppler", "Radio Standard", "ECG", 
    "Ventilateur Respiratoire", "Moniteur Multiparametrique", "Chariot Urgence"
]

# NOUVEAU : Types de personnel enrichis
TYPES_PERSONNEL = ["Titulaire", "Contractuel", "Interim", "Vacataire", "Externe (Etudiant)"]

def get_context_covid(current_date):
    """Retourne l'impact du Covid selon la date"""
    impact = {"facteur_flux": 1.0, "priorite_infectieux": 1.0, "absenteisme_covid": 0.0}
    
    # Vague 1 : Mars - Mai 2020
    if date(2020, 3, 15) <= current_date <= date(2020, 5, 15):
        impact["facteur_flux"] = 0.6 
        impact["priorite_infectieux"] = 5.0 
        impact["absenteisme_covid"] = 0.15
        return "Crise Covid - Vague 1", impact
        
    # Vague 2 : Oct - Nov 2020
    if date(2020, 10, 15) <= current_date <= date(2020, 12, 15):
        impact["facteur_flux"] = 0.9
        impact["priorite_infectieux"] = 3.0
        impact["absenteisme_covid"] = 0.10
        return "Crise Covid - Vague 2", impact

    if current_date.year >= 2022:
        impact["absenteisme_covid"] = 0.05
        return "Post-Covid", impact

    return "Pre-Covid", impact

def generate_grand_dataset():
    print(f"🏥 Simulation Pitié-Salpêtrière {START_DATE.year}-{END_DATE.year} (SHIFTS 12H - JOUR/NUIT)...")
    
    patients_data = []
    rh_data = []
    materiel_data = []
    
    current_date = START_DATE
    
    while current_date <= END_DATE:
        # --- CONTEXTE ---
        month = current_date.month
        weekday = current_date.weekday()
        periode_nom, covid_ctx = get_context_covid(current_date)
        is_winter = month in [12, 1, 2]
        
        # --- 1. GÉNÉRATION RH (BOUCLE JOUR/NUIT) ---
        # On stocke le planning exact pour savoir qui travaille quand
        daily_staff_planning = {} 
        
        for svc in SERVICES:
            cfg = CAPACITY_CONFIG[svc]
            daily_staff_planning[svc] = {"Jour": 0, "Nuit": 0}
            
            # ON GÉNÈRE 2 ÉQUIPES PAR JOUR : 07h-19h et 19h-07h
            for shift_name in ["Jour", "Nuit"]:
                
                if shift_name == "Jour":
                    horaire = "07h-19h" # Shift 12h
                    ts_poste = pd.Timestamp(current_date) + pd.Timedelta(hours=7)
                    base_staff = cfg["Staff_Jour"]
                else:
                    horaire = "19h-07h" # Shift 12h
                    ts_poste = pd.Timestamp(current_date) + pd.Timedelta(hours=19)
                    
                    # Règle Métier : Réduction la nuit
                    if svc == "Urgences":
                        base_staff = int(cfg["Staff_Jour"] * 0.75) 
                    elif svc in ["Infectieux", "Pneumologie"] and "Covid" in periode_nom:
                        base_staff = int(cfg["Staff_Jour"] * 0.6)
                    else:
                        base_staff = int(cfg["Staff_Jour"] * 0.35)

                # Calcul Absenteisme
                abs_base = 0.08
                if is_winter: abs_base += 0.05
                abs_total = abs_base + covid_ctx["absenteisme_covid"]
                
                taux_abs = min(0.40, np.random.beta(5, 50) + abs_total)
                staff_pres = int(base_staff * (1 - taux_abs))
                
                # Heures Supp (Si crise > 15% absents)
                heures_supp = 0
                if taux_abs > 0.15:
                    heures_supp = int((base_staff - staff_pres) * 0.5 * 12) # Basé sur 12h

                # Choix Type Personnel (Plus varié)
                # Probabilités par défaut : Titulaire majoritaire
                probs = [0.70, 0.10, 0.10, 0.05, 0.05] 
                if "Covid" in periode_nom:
                     # Plus d'interim et vacataires pendant le Covid
                     probs = [0.55, 0.10, 0.20, 0.10, 0.05]
                
                type_perso = np.random.choice(TYPES_PERSONNEL, p=probs)

                # SAUVEGARDE RH
                rh_data.append({
                    "id_personnel": f"TEAM-{svc[:3]}-{shift_name[0]}-{current_date.strftime('%Y%m%d')}",
                    "date_heure_prise_poste": ts_poste,
                    "service": svc,
                    "shift": shift_name,
                    "horaires_de_travail": horaire,
                    "type_de_personnel": type_perso,
                    "effectif_theorique": base_staff,
                    "effectif_present": staff_pres,
                    "taux_absenteisme": round(taux_abs, 2),
                    "heures_supp": heures_supp
                })
                
                # Mise en mémoire pour les patients
                daily_staff_planning[svc][shift_name] = staff_pres

        # --- 2. MATÉRIEL (Inventaire à 08h00) ---
        materiel_snapshot_ts = pd.Timestamp(current_date) + pd.Timedelta(hours=8)
        daily_lits_status = {}
        
        for svc in SERVICES:
            lits_total = CAPACITY_CONFIG[svc]["Lits"]
            occ_rate = np.random.uniform(0.85, 0.98) 
            if periode_nom == "Crise Covid - Vague 1" and svc not in ["Infectieux", "Pneumologie"]: occ_rate = 0.4
            
            lits_occ = int(lits_total * occ_rate)
            lits_dispo = max(0, lits_total - lits_occ)
            
            equip_stat = "Operationnel"
            if np.random.random() < 0.03: equip_stat = "Panne/Maintenance"
            
            type_lit = "Lit Standard"
            if svc == "Urgences": type_lit = "Brancard"
            elif svc == "Infectieux" and covid_ctx["priorite_infectieux"] > 1: type_lit = "Chambre Isolement"

            materiel_data.append({
                "date_heure_inventaire": materiel_snapshot_ts,
                "services": svc,
                "types_de_lits_disponibles": type_lit,
                "nbre_lits_dispos": lits_dispo,
                "equipements_disponibles": random.choice(TYPES_EQUIPEMENTS) if equip_stat == "Operationnel" else "Indisponible"
            })
            daily_lits_status[svc] = lits_dispo

        # --- 3. PATIENTS (Flux Continu) ---
        season_factor = 1.3 if is_winter else 1.0
        day_factor = 1.15 if weekday == 0 else (0.85 if weekday == 6 else 1.0)
        lambd = 274 * season_factor * day_factor * covid_ctx["facteur_flux"]
        nb_patients = np.random.poisson(lambd)
        
        for _ in range(nb_patients):
            # Choix Service
            weights = [100 if s == "Urgences" else (10 * covid_ctx["priorite_infectieux"] if s in ["Infectieux", "Pneumologie"] else 10) for s in SERVICES]
            svc_adm = random.choices(SERVICES, weights=weights)[0]
            
            # Motif & Gravité
            motif = random.choice(MOTIFS_ADMISSION)
            if svc_adm == "Cardiologie": motif = "Douleur Thoracique"
            elif (svc_adm in ["Infectieux", "Pneumologie"]) and (is_winter or "Covid" in periode_nom): motif = "Detresse Respiratoire"
            
            ccmu = random.choices([1, 2, 3, 4, 5], weights=[0.3, 0.3, 0.25, 0.1, 0.05])[0]
            
            # Timestamp Arrivée
            hour_arrival = int(np.random.normal(14, 6)) % 24
            ts_arrival = pd.Timestamp(current_date) + pd.Timedelta(hours=hour_arrival, minutes=random.randint(0,59))
            
            # LOGIQUE COHÉRENTE : Quel staff est là QUAND le patient arrive ?
            staff_actif = 0
            # Si arrivée entre 07h et 19h -> Equipe Jour
            if 7 <= hour_arrival < 19:
                staff_actif = daily_staff_planning[svc_adm]["Jour"]
            else:
                staff_actif = daily_staff_planning[svc_adm]["Nuit"]
            
            # Durée Séjour (Impactée par le staff présent à l'instant T)
            mu = 2.5 + (0.5 if hour_arrival > 20 or hour_arrival < 7 else 0)
            
            # Pénalité Staff (Si ratio patients/staff explose)
            if (nb_patients / 24) > max(1, staff_actif): # Sécurité division par 0
                 mu += 0.5

            los = np.random.lognormal(mu, 0.6)
            
            # Pénalité Lit
            if daily_lits_status[svc_adm] == 0: los += np.random.uniform(4, 12)
            
            # Issue
            issue = "Retour Domicile"
            if ccmu >= 3 or svc_adm != "Urgences": issue = "Transfert"
            if ccmu == 5 and np.random.random() < 0.15: issue = "Deces"

            patients_data.append({
                "ID_Patient": str(uuid.uuid4())[:8],
                "age": int(np.random.normal(60, 25)),
                "sexe": random.choice(["M", "F"]),
                "motif_admission": motif,
                "ccmu": ccmu,
                "duree_hospitalisation": round(los, 1),
                "date_et_heure_admission": ts_arrival,
                "service_admission": svc_adm,
                "issue": issue
            })
            
        current_date += timedelta(days=1)

    print("💾 Sauvegarde des fichiers...")
    os.makedirs("data/raw", exist_ok=True)
    pd.DataFrame(patients_data).to_csv("data/raw/patients.csv", index=False)
    pd.DataFrame(rh_data).to_csv("data/raw/personnel.csv", index=False)
    pd.DataFrame(materiel_data).to_csv("data/raw/materiel.csv", index=False)
    print(f"✅ Terminé !")

if __name__ == "__main__":
    generate_grand_dataset()