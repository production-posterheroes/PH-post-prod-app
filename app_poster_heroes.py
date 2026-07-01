# -*- coding: utf-8 -*-
import streamlit as st
import os
import time
import io
from PIL import Image
import zipfile

# 1. CONFIGURATION DE LA PAGE
st.set_page_config(
    page_title="POSTER HEROES - Production Lab",
    page_icon="⚡",
    layout="wide"
)

# 2. INJECTION CSS POUR LA DA (JAUNE #f6c945 / NOIR / ANTON)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Anton&display=swap');

    /* Global */
    .main {
        background-color: #f6c945;
        color: #000000;
        font-family: 'Arial', sans-serif;
    }
    
    /* Titres */
    h1, h2, h3 {
        font-family: 'Anton', sans-serif !important;
        text-transform: uppercase;
        color: #000000 !important;
        letter-spacing: 1px;
    }

    /* Boutons */
    .stButton>button {
        background-color: #000000 !important;
        color: #f6c945 !important;
        font-family: 'Anton', sans-serif !important;
        border-radius: 0px !important;
        border: none !important;
        padding: 15px 30px !important;
        font-size: 20px !important;
        width: 100%;
        transition: 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    /* Zones d'Upload */
    .stFileUploader section {
        background-color: rgba(255, 255, 255, 0.4) !important;
        border: 2px dashed #000000 !important;
        border-radius: 0px !important;
    }

    /* Fond de sidebar et autres éléments Streamlit */
    .stApp {
        background-color: #f6c945;
    }

    /* Barre de progression */
    .stProgress > div > div > div > div {
        background-color: #000000 !important;
    }
    
    /* Cartes de prévisualisation */
    .img-card {
        background-color: #ffffff;
        padding: 10px;
        border: 2px solid #000000;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. HEADER AVEC LOGO
# Note : Pour que le logo s'affiche, dépose "logo.png" sur ton GitHub
col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
with col_l2:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.markdown("<h1 style='text-align: center;'>POSTER HEROES</h1>", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center;'>Post-Production Factory v1.0</h3>", unsafe_allow_html=True)
st.write("---")

# --- INITIALISATION ---
def init_folders():
    for folder in ["temp_portraits", "temp_pieds", "temp_template", "temp_sorties"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
init_folders()

# --- WORKFLOW ---

# ETAPE 1 : LE TEMPLATE
st.markdown("## ⚡ ÉTAPE 1 : LE TEMPLATE")
template_file = st.file_uploader("DÉPOSER LE FOND DE POSTER (.JPG, .PNG)", type=["jpg", "jpeg", "png"], key="template")

st.write("---")

# ETAPE 2 : LES ASSETS
st.markdown("## ⚡ ÉTAPE 2 : LES PHOTOS JOUEURS")
c1, c2 = st.columns(2)

with c1:
    st.markdown("### 👤 PORTRAITS")
    portraits_files = st.file_uploader("Glisser les visages ici", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key="portraits")

with c2:
    st.markdown("### 🏃‍♂️ PHOTOS EN PIEDS")
    pieds_files = st.file_uploader("Glissez les actions ici", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key="pieds")

# --- LOGIQUE DE PRODUCTION ---
if template_file and portraits_files and pieds_files:
    
    # Stockage
    template_path = os.path.join("temp_template", template_file.name)
    with open(template_path, "wb") as f: f.write(template_file.read())
        
    portraits_dict = {f.name: f for f in portraits_files}
    pieds_dict = {f.name: f for f in pieds_files}
    
    for f in portraits_files:
        with open(os.path.join("temp_portraits", f.name), "wb") as b: b.write(f.read())
    for f in pieds_files:
        with open(os.path.join("temp_pieds", f.name), "wb") as b: b.write(f.read())

    paires = [n for n in portraits_dict.keys() if n in pieds_dict]

    st.markdown(f"### ✅ **{len(paires)} JOUEURS PRÊTS POUR LA PRODUCTION**")
    
    # ETAPE 3 : LANCEMENT
    if st.button("LANCER LA GÉNÉRATION DES POSTERS"):
        bar = st.progress(0)
        status = st.empty()
        
        for idx, filename in enumerate(paires):
            status.markdown(f"**TRAITEMENT IA : {filename}**")
            
            # SIMULATION API NANO BANANA
            time.sleep(0.8)
            img = Image.open(os.path.join("temp_portraits", filename))
            img.save(os.path.join("temp_sorties", filename))
            
            bar.progress((idx + 1) / len(paires))
            
        status.success("✨ PRODUCTION TERMINÉE AVEC SUCCÈS")

        # ETAPE 4 : DOWNLOAD
        st.write("---")
        st.markdown("## 📥 ÉTAPE 3 : RÉCUPÉRATION")
        
        # ZIP
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as z:
            for f in paires:
                z.write(os.path.join("temp_sorties", f), arcname=f)
        
        st.download_button(
            label="📦 TÉLÉCHARGER LE PACK ZIP COMPLET",
            data=zip_buf.getvalue(),
            file_name="PROD_POSTER_HEROES.zip",
            mime="application/zip"
        )
        
        # Galerie
        st.markdown("### APERÇU UNITAIRE")
        grid = st.columns(4)
        for i, f in enumerate(paires):
            with grid[i % 4]:
                st.image(os.path.join("temp_sorties", f), use_container_width=True)
                with open(os.path.join("temp_sorties", f), "rb") as b:
                    st.download_button("DL", b, file_name=f, key=f"btn_{f}")

else:
    st.info("👋 Bienvenue Quentin. Dépose les fichiers pour activer la factory.")
