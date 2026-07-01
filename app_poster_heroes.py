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

# 2. INJECTION CSS PROPRE ET IMPLIQUABLE (FORÇAGE GRAPHIQUE)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Anton&display=swap');

    /* Fond jaune global */
    .stApp, .main {
        background-color: #f6c945 !important;
    }
    
    /* Titre principal et sous-titres hors blocs */
    .main-title {
        font-family: 'Anton', sans-serif !important;
        font-size: 70px !important;
        text-align: center;
        color: #000000 !important;
        line-height: 1 !important;
        margin-bottom: 0px;
        text-transform: uppercase;
    }
    .sub-title {
        font-family: 'Anton', sans-serif !important;
        font-size: 24px !important;
        text-align: center;
        color: #000000 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 5px;
        margin-bottom: 30px;
    }

    /* CRÉATION DES BLOCS NOIRS ABSOLUS (MAQUETTE REF 1) */
    .custom-black-block {
        background-color: #000000 !important;
        padding: 35px !important;
        margin-bottom: 25px !important;
        border-radius: 0px !important; /* Angles carrés */
    }
    
    /* Titres Étape 1 & 2 en Blanc pur */
    .block-title {
        font-family: 'Anton', sans-serif !important;
        color: #ffffff !important;
        font-size: 32px !important;
        text-transform: uppercase;
        margin-top: 0px;
        margin-bottom: 5px;
        letter-spacing: 1px;
    }
    .block-label {
        color: #ffffff !important;
        font-family: 'Arial', sans-serif;
        font-size: 14px;
        margin-bottom: 15px;
    }
    .asset-title {
        font-family: 'Anton', sans-serif !important;
        color: #ffffff !important;
        font-size: 20px !important;
        text-transform: uppercase;
        margin-bottom: 5px;
    }

    /* Customisation des zones d'upload : Fond Jaune / Pointillés Noirs */
    .stFileUploader section {
        background-color: #f6c945 !important;
        border: 2px dashed #000000 !important;
        border-radius: 0px !important;
    }
    /* Couleur du texte à l'intérieur de la zone d'upload */
    .stFileUploader section div, .stFileUploader section span, .stFileUploader section button {
        color: #000000 !important;
    }
    .stFileUploader footer {
        display: none !important; /* Cache les mentions inutiles de Streamlit */
    }

    /* Bouton d'action principal POSTER HEROES */
    .stButton>button {
        background-color: #000000 !important;
        color: #f6c945 !important;
        font-family: 'Anton', sans-serif !important;
        border: 3px solid #000000 !important;
        border-radius: 0px !important;
        padding: 20px 30px !important;
        font-size: 24px !important;
        text-transform: uppercase;
        width: 100%;
        transition: 0.2s;
    }
    .stButton>button:hover {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. HEADER AVEC TON LOGO ET LE SOUSTRE DE LA MAQUETTE
col_l1, col_l2, col_l3 = st.columns([1, 1.8, 1])
with col_l2:
    try:
        st.image("logo7.png", use_container_width=True)
    except:
        st.markdown("<p class='main-title'>POSTER HEROES</p>", unsafe_allow_html=True)

st.markdown("<p class='sub-title'>POST-PRODUCTION FACTORY V1.0</p>", unsafe_allow_html=True)

# --- INITIALISATION DES RÉPERTOIRES ---
if not os.path.exists("temp_portraits"): os.makedirs("temp_portraits")
if not os.path.exists("temp_pieds"): os.makedirs("temp_pieds")
if not os.path.exists("temp_template"): os.makedirs("temp_template")
if not os.path.exists("temp_sorties"): os.makedirs("temp_sorties")

# --- CONSTRUTION DES BLOCS NOIRS DE LA MAQUETTE ---

# ⚡ BLOC ÉTAPE 1
st.markdown('<div class="custom-black-block">', unsafe_allow_html=True)
st.markdown('<p class="block-title">⚡ ÉTAPE 1 : LE TEMPLATE</p>', unsafe_allow_html=True)
st.markdown('<p class="block-label">DÉPOSER LE FOND DE POSTER (.JPG, .PNG)</p>', unsafe_allow_html=True)
template_file = st.file_uploader("", type=["jpg", "jpeg", "png"], key="template", label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# ⚡ BLOC ÉTAPE 2
st.markdown('<div class="custom-black-block">', unsafe_allow_html=True)
st.markdown('<p class="block-title">⚡ ÉTAPE 2 : LES PHOTOS JOUEURS</p>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown('<p class="asset-title">👤 PORTRAITS</p>', unsafe_allow_html=True)
    st.markdown('<p class="block-label">Glisser les visages ici</p>', unsafe_allow_html=True)
    portraits_files = st.file_uploader("", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key="portraits", label_visibility="collapsed")
with c2:
    st.markdown('<p class="asset-title">🏃‍♂️ PHOTOS EN PIEDS</p>', unsafe_allow_html=True)
    st.markdown('<p class="block-label">Glissez les actions ici</p>', unsafe_allow_html=True)
    pieds_files = st.file_uploader("", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key="pieds", label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# --- TRAITEMENT ET AGENCEMENT ---
if template_file and portraits_files and pieds_files:
    
    # Stockage
    template_path = os.path.join("temp_template", template_file.name)
    with open(template_path, "wb") as f: f.write(template_file.read())
    
    portraits_dict = {f.name: f for f in portraits_files}
    pieds_dict = {f.name: f for f in pieds_files}
    paires = [n for n in portraits_dict.keys() if n in pieds_dict]
    
    # Gros bouton d'action sous les blocs
    st.write("")
    if st.button(f"LANCER LA GÉNÉRATION DES {len(paires)} POSTERS"):
        bar = st.progress(0)
        
        for idx, filename in enumerate(paires):
            with open(os.path.join("temp_sorties", filename), "wb") as out:
                out.write(portraits_dict[filename].read())
            time.sleep(0.3)
            bar.progress((idx + 1) / len(paires))
            
        # BLOC ÉTAPE 3 (RÉCUPÉRATION)
        st.markdown('<div class="custom-black-block">', unsafe_allow_html=True)
        st.markdown('<p class="block-title">📥 ÉTAPE 3 : RÉCUPÉRATION</p>', unsafe_allow_html=True)
        
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as z:
            for f in paires: z.write(os.path.join("temp_sorties", f), arcname=f)
        
        st.download_button(
            label="📦 TÉLENTRE LE PACK ZIP COMPLET",
            data=zip_buf.getvalue(),
            file_name="PROD_POSTER_HEROES.zip",
            mime="application/zip"
        )
        
        st.markdown('<p class="asset-title" style="margin-top:20px;">🗂️ APERÇU UNITAIRE</p>', unsafe_allow_html=True)
        grid = st.columns(4)
        for i, f in enumerate(paires):
            with grid[i % 4]:
                st.image(os.path.join("temp_sorties", f), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
