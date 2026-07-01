# -*- coding: utf-8 -*-
import streamlit as st
import os
import time
import io
from PIL import Image
import zipfile

# 1. CONFIGURATION DE LA PAGE
st.set_page_config(
    page_title="POSTER HEROES - Factory",
    page_icon="⚡",
    layout="wide"
)

# 2. INJECTION CSS STRICTE (FOND JAUNE #f6c945 / BLOCS NOIRS ABSOLUS / FONT ANTON)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Anton&display=swap');

    /* Fond global de l'application */
    .stApp, .main {
        background-color: #f6c945 !important;
        font-family: 'Arial', sans-serif;
    }
    
    /* Typographie des grands titres hors blocs */
    h1, h2, h3 {
        font-family: 'Anton', sans-serif !important;
        text-transform: uppercase;
        color: #000000 !important;
        letter-spacing: 1px;
    }

    /* Forçage des conteneurs Streamlit en Blocs Noirs Absolus */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: none !important;
        padding: 30px !important;
        border-radius: 0px !important; /* Angles droits athlétiques */
        margin-bottom: 25px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.2);
    }

    /* Ajustement des textes à l'intérieur des blocs noirs */
    div[data-testid="stVerticalBlockBorderWrapper"] h2,
    div[data-testid="stVerticalBlockBorderWrapper"] h3,
    div[data-testid="stVerticalBlockBorderWrapper"] p,
    div[data-testid="stVerticalBlockBorderWrapper"] label {
        color: #ffffff !important;
        font-family: 'Arial', sans-serif;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] h2,
    div[data-testid="stVerticalBlockBorderWrapper"] h3 {
        font-family: 'Anton', sans-serif !important;
        letter-spacing: 1px;
    }

    /* Customisation des zones de Drop (Plus de transparence boueuse) */
    .stFileUploader section {
        background-color: #111111 !important;
        border: 2px dashed #f6c945 !important;
        border-radius: 0px !important;
        color: #ffffff !important;
    }
    
    .stFileUploader footer {
        display: none !important;
    }

    /* Bouton d'action principal POSTER HEROES */
    .stButton>button {
        background-color: #000000 !important;
        color: #f6c945 !important;
        font-family: 'Anton', sans-serif !important;
        border: 2px solid #000000 !important;
        border-radius: 0px !important;
        padding: 18px 30px !important;
        font-size: 22px !important;
        text-transform: uppercase;
        width: 100%;
        transition: 0.2s ease-in-out;
        margin-top: 10px;
    }
    
    .stButton>button:hover {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-color: #ffffff !important;
    }

    /* Customisation des messages d'information (Alerte de démarrage) */
    div[data-testid="stNotification"] {
        background-color: #000000 !important;
        border: 2px solid #000000 !important;
        border-radius: 0px !important;
    }
    div[data-testid="stNotification"] p {
        color: #f6c945 !important;
        font-weight: bold !important;
    }
    
    /* Barre de progression de traitement */
    .stProgress > div > div > div > div {
        background-color: #f6c945 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. STRUCTURE DE L'EN-TÊTE
col_l1, col_l2, col_l3 = st.columns([1, 1.8, 1])
with col_l2:
    try:
        # Utilisation directe de ton fichier logo7.png
        st.image("logo7.png", use_container_width=True)
    except:
        st.markdown("<h1 style='text-align: center;'>POSTER HEROES</h1>", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center; color: #000000;'>POST-PRODUCTION FACTORY V1.0</h3>", unsafe_allow_html=True)
st.write("---")

# --- INITIALISATION DES RÉPERTOIRES ---
def init_folders():
    for folder in ["temp_portraits", "temp_pieds", "temp_template", "temp_sorties"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
init_folders()

# --- BLOCS DE PRODUCTION DE L'INTERFACE ---

# CONTAINER ÉTAPE 1
with st.container(border=True):
    st.markdown("## ⚡ ÉTAPE 1 : LE TEMPLATE")
    template_file = st.file_uploader("Déposer le fond de poster vierge (.JPG ou .PNG)", type=["jpg", "jpeg", "png"], key="template")

# CONTAINER ÉTAPE 2
with st.container(border=True):
    st.markdown("## ⚡ ÉTAPE 2 : LES PHOTOS JOUEURS")
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 👤 PORTRAITS")
        portraits_files = st.file_uploader("Glisser les visages ici (Noms identiques aux photos en pieds)", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key="portraits")
        
    with c2:
        st.markdown("### 🏃‍♂️ PHOTOS EN PIEDS")
        pieds_files = st.file_uploader("Glissez les actions ici (Noms identiques aux portraits)", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key="pieds")

# --- TRAITEMENT LOGIQUE ---
if template_file and portraits_files and pieds_files:
    
    # Sauvegarde des fichiers
    template_path = os.path.join("temp_template", template_file.name)
    with open(template_path, "wb") as f: 
        f.write(template_file.read())
        
    portraits_dict = {f.name: f for f in portraits_files}
    pieds_dict = {f.name: f for f in pieds_files}
    
    for f in portraits_files:
        with open(os.path.join("temp_portraits", f.name), "wb") as b: b.write(f.read())
    for f in pieds_files:
        with open(os.path.join("temp_pieds", f.name), "wb") as b: b.write(f.read())

    # Alignement par nom exact
    paires = [n for n in portraits_dict.keys() if n in pieds_dict]
    
    # Affichage du bouton de déclenchement hors conteneur pour un style massif
    st.write("")
    if st.button(f"LANCER LA GÉNÉRATION DES {len(paires)} POSTERS"):
        bar = st.progress(0)
        status = st.empty()
        
        for idx, filename in enumerate(paires):
            status.markdown(f"**🤖 FUSION NANO BANANA PRO EN COURS : {filename}**")
            
            # Simulation de l'attente API
            time.sleep(0.7)
            img = Image.open(os.path.join("temp_portraits", filename))
            img.save(os.path.join("temp_sorties", filename))
            
            bar.progress((idx + 1) / len(paires))
            
        status.success("✨ PROCESSUS DE PRODUCTION COMPLÉTÉ")

        # CONTAINER ÉTAPE 3 (RÉCUPÉRATION)
        with st.container(border=True):
            st.markdown("## 📥 ÉTAPE 3 : RÉCUPÉRATION")
            
            # Compression ZIP
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as z:
                for f in paires:
                    z.write(os.path.join("temp_sorties", f), arcname=f)
            
            st.download_button(
                label="📦 TÉLÉCHARGER LE PACK ZIP COMPLET (POSTERS RENOMMÉS)",
                data=zip_buf.getvalue(),
                file_name="PROD_POSTER_HEROES.zip",
                mime="application/zip"
            )
            
            st.write("---")
            st.markdown("### 🗂️ APERÇU ET LIENS UNITAIRES")
            grid = st.columns(4)
            for i, f in enumerate(paires):
                with grid[i % 4]:
                    st.image(os.path.join("temp_sorties", f), use_container_width=True)
                    with open(os.path.join("temp_sorties", f), "rb") as b:
                        st.download_button(f"DL {f}", b, file_name=f, key=f"btn_{f}")
else:
    st.info("⚡ Factory en attente : Glisse ton template et tes paires de photos pour réveiller la machine.")
