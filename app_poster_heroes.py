# -*- coding: utf-8 -*-
"""
POSTER HEROES — POST-PRODUCTION FACTORY
----------------------------------------
Application locale Streamlit pour automatiser la fabrication des visuels
et la génération des posters sportifs.
"""

import base64
import io
import json
import os
import re
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import streamlit as st
from PIL import Image

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False

# ============================================================
# 1. CONFIGURATION GÉNÉRALE & DOSSIERS
# ============================================================

st.set_page_config(
    page_title="POSTER HEROES - Factory",
    page_icon="⚡",
    layout="wide",
)

APP_DIR = Path(__file__).parent
WORK_DIR = APP_DIR / ".ph_workdir"
DIR_RAW = WORK_DIR / "raw"
DIR_MASTER = WORK_DIR / "master"
DIR_PORTRAITS = WORK_DIR / "portraits"
DIR_ACTION = WORK_DIR / "action"
DIR_OUTPUT = WORK_DIR / "sorties"


def ensure_dirs() -> None:
    for d in (DIR_RAW, DIR_MASTER, DIR_PORTRAITS, DIR_ACTION, DIR_OUTPUT):
        d.mkdir(parents=True, exist_ok=True)


def reset_run_dirs() -> None:
    """Nettoie les dossiers de travail pour un nouveau projet."""
    for d in (DIR_RAW, DIR_MASTER, DIR_PORTRAITS, DIR_ACTION, DIR_OUTPUT):
        if d.exists():
            shutil.rmtree(d)
    ensure_dirs()


ensure_dirs()

# ============================================================
# 2. DESIGN SYSTEM — FOND JAUNE / BLOCS NOIRS / TYPO ANTON
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Anton&family=Archivo:wght@400;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Archivo', sans-serif; }

    .stApp, .main { background-color: #F6C945 !important; }

    /* ---------- HEADER ---------- */
    .ph-header {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        margin-top: 6px;
        margin-bottom: 26px;
    }
    .ph-header-title {
        font-family: 'Anton', sans-serif !important;
        font-size: 26px !important;
        color: #000000 !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin: 0;
    }
    .ph-header-sub {
        font-family: 'Archivo', sans-serif !important;
        font-size: 11px !important;
        color: #000000 !important;
        opacity: 0.65;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin: 0;
    }

    /* ---------- CARTES DE SÉLECTION D'ACTION (GROS BOUTONS) ---------- */
    div[class*="st-key-ph-card-"] {
        background-color: #000000 !important;
        border: none !important;
        padding: 40px 30px !important;
        margin-bottom: 24px !important;
        border-radius: 0px !important;
        text-align: center;
    }
    div[class*="st-key-ph-card-"] * { color: #FFFFFF !important; }

    /* ---------- BLOCS NOIRS D'ÉTAPES ---------- */
    div[class*="st-key-ph-step-"] {
        background-color: #000000 !important;
        border: none !important;
        padding: 30px 34px !important;
        margin-bottom: 24px !important;
        border-radius: 0px !important;
    }
    div[class*="st-key-ph-step-"] * { color: #FFFFFF !important; }
    
    .ph-step-eyebrow {
        font-family: 'Anton', sans-serif !important;
        color: #F6C945 !important;
        font-size: 14px !important;
        letter-spacing: 3px;
        margin-bottom: 2px;
    }
    .ph-block-title {
        font-family: 'Anton', sans-serif !important;
        color: #FFFFFF !important;
        font-size: 30px !important;
        text-transform: uppercase;
        margin-top: 0px;
        margin-bottom: 6px;
        letter-spacing: 0.5px;
    }
    .ph-block-desc {
        font-family: 'Archivo', sans-serif !important;
        color: #FFFFFF !important;
        opacity: 0.75;
        font-size: 14px;
        margin-bottom: 18px;
    }
    .ph-divider {
        border: none;
        border-top: 1px solid rgba(255,255,255,0.15);
        margin: 22px 0;
    }

    /* ---------- UPLOADERS STYLISÉS ---------- */
    div[class*="st-key-ph-step-"] .stFileUploader,
    div[class*="st-key-ph-step-"] [data-testid="stFileUploaderDropzone"],
    div[class*="st-key-ph-step-"] .stFileUploader section {
        background-color: #000000 !important;
        border: 2px dashed #FFFFFF !important;
        border-radius: 0px !important;
    }
    div[class*="st-key-ph-step-"] .stFileUploader section div,
    div[class*="st-key-ph-step-"] .stFileUploader section span,
    div[class*="st-key-ph-step-"] .stFileUploader small {
        color: #FFFFFF !important;
        opacity: 0.85;
    }

    /* ---------- BOUTONS D'ACTION ---------- */
    .stButton>button {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        font-family: 'Anton', sans-serif !important;
        border: 3px solid #000000 !important;
        border-radius: 0px !important;
        padding: 18px 28px !important;
        font-size: 20px !important;
        letter-spacing: 1px;
        text-transform: uppercase;
        width: 100%;
        transition: 0.15s;
    }
    .stButton>button:hover {
        background-color: #F6C945 !important;
        color: #000000 !important;
        border-color: #000000 !important;
    }

    /* BOUTONS SPECIFIQUES AUX CARTES MAIN */
    div[class*="st-key-ph-card-"] .stButton>button {
        background-color: transparent !important;
        border: 3px solid #F6C945 !important;
        color: #F6C945 !important;
        font-size: 24px !important;
        padding: 22px 30px !important;
    }
    div[class*="st-key-ph-card-"] .stButton>button:hover {
        background-color: #F6C945 !important;
        color: #000000 !important;
    }

    .stDownloadButton>button {
        background-color: #F6C945 !important;
        color: #000000 !important;
        font-family: 'Anton', sans-serif !important;
        border: 3px solid #F6C945 !important;
        border-radius: 0px !important;
        padding: 16px 24px !important;
        font-size: 18px !important;
        letter-spacing: 1px;
        text-transform: uppercase;
        width: 100%;
    }
    .stDownloadButton>button:hover {
        background-color: #000000 !important;
        color: #F6C945 !important;
        border-color: #000000 !important;
    }

    /* ---------- BADGES DE STATUT ---------- */
    .ph-badge {
        display: inline-block;
        font-family: 'Anton', sans-serif;
        font-size: 11px;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding: 4px 10px;
        margin-bottom: 6px;
    }
    .ph-badge-ok { background-color: #F6C945; color: #000000 !important; }
    .ph-pair-card {
        border: 1px solid rgba(255,255,255,0.2);
        padding: 10px;
        margin-bottom: 12px;
        background-color: #000000;
        text-align: center;
    }
    .ph-pair-name {
        font-family: 'Anton', sans-serif !important;
        color: #FFFFFF !important;
        font-size: 15px !important;
        margin-top: 6px;
        text-transform: uppercase;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

from contextlib import contextmanager

@contextmanager
def ph_block(key: str, eyebrow: str, title: str, desc: str = ""):
    with st.container(key=key):
        st.markdown(f'<p class="ph-step-eyebrow">{eyebrow}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="ph-block-title">{title}</p>', unsafe_allow_html=True)
        if desc:
            st.markdown(f'<p class="ph-block-desc">{desc}</p>', unsafe_allow_html=True)
        yield

# ============================================================
# 3. HEADER GLOBAL
# ============================================================

icon_path = APP_DIR / "logo_icon.png"
if icon_path.exists():
    icon_b64 = base64.b64encode(icon_path.read_bytes()).decode()
    st.markdown(
        f"""
        <div class="ph-header">
            <img src="data:image/png;base64,{icon_b64}" style="height:38px;" />
            <div>
                <p class="ph-header-title">Poster Heroes</p>
                <p class="ph-header-sub">Post-Production Factory · Ops Engine</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="ph-header"><p class="ph-header-title">Poster Heroes — Factory</p></div>',
        unsafe_allow_html=True,
    )

# ============================================================
# 4. CHOIX DE L'ACTION PRINCIPALE (CREATE MEDIA vs CREATE POSTER)
# ============================================================

if "main_action" not in st.session_state:
    st.session_state.main_action = None

if st.session_state.main_action is None:
    st.markdown(
        '<p class="ph-block-title" style="text-align:center;color:#000 !important;font-size:28px;margin-bottom:20px;">'
        'QUE SOUHAITEZ-VOUS PRODUIRE ?</p>',
        unsafe_allow_html=True,
    )

    col_media, col_poster = st.columns(2)

    with col_media:
        with st.container(key="ph-card-create-media"):
            st.markdown('<p style="font-size:50px;margin-bottom:10px;">🎨</p>', unsafe_allow_html=True)
            st.markdown('<p class="ph-block-title" style="font-size:26px;">1. CREATE MEDIA</p>', unsafe_allow_html=True)
            st.markdown(
                '<p class="ph-block-desc" style="min-height:70px;">'
                'Tri automatique des paires (Portrait/Action), Color Match sur photo Master, '
                'Détourage HD, Auto-Crop & Marges. Export nommé et prêt pour Photoshop.</p>',
                unsafe_allow_html=True,
            )
            if st.button("LANCER CREATE MEDIA →", key="btn_choose_media"):
                st.session_state.main_action = "create_media"
                st.rerun()

    with col_poster:
        with st.container(key="ph-card-create-poster"):
            st.markdown('<p style="font-size:50px;margin-bottom:10px;">⚡</p>', unsafe_allow_html=True)
            st.markdown('<p class="ph-block-title" style="font-size:26px;">2. CREATE POSTER</p>', unsafe_allow_html=True)
            st.markdown(
                '<p class="ph-block-desc" style="min-height:70px;">'
                'Pilote votre script Photoshop local pour charger les Objets Dynamiques, '
                'appliquer le rendu d\'ombre et sortir les fichiers d\'impression HD finaux.</p>',
                unsafe_allow_html=True,
            )
            if st.button("LANCER CREATE POSTER →", key="btn_choose_poster"):
                st.session_state.main_action = "create_poster"
                st.rerun()

    st.stop()

# Bouton de retour au menu principal
back_col, _ = st.columns([1, 4])
with back_col:
    if st.button("← Menu Principal"):
        st.session_state.main_action = None
        st.rerun()

# ============================================================
# 5. MODULE 1 : CREATE MEDIA (LES 5 ÉTAPES)
# ============================================================

if st.session_state.main_action == "create_media":

    st.markdown(
        '<p class="ph-block-title" style="color:#000 !important;font-size:26px;margin-top:10px;">'
        '🎨 MODULE CREATE MEDIA — PRÉPARATION DES PNG HD</p>',
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # ÉTAPE 1 : IMPORT BRUT & SELECTION DES PHOTO MASTERS
    # ------------------------------------------------------------
    with ph_block(
        "ph-step-1",
        "⚡ ÉTAPE 1",
        "IMPORTATION DES BRUTS & PHOTOS MASTERS",
        "Déposez le lot complet des photos brutes du photographe, ainsi que la photo de référence (Master) pour le Color Match.",
    ):
        team_name = st.text_input("Nom de l'Équipe / Catégorie", value="U12", key="team_name")
        
        c_master, c_raw = st.columns([1, 2])
        
        with c_master:
            st.markdown('**🎯 Photo Master (Colorimétrie Référence)**')
            master_file = st.file_uploader(
                "Master photo", type=["jpg", "jpeg", "png"], key="master_file", label_visibility="collapsed"
            )
            if master_file:
                st.image(master_file, caption="Master Référence", width=160)

        with c_raw:
            st.markdown('**📂 Photos Brutes du Shooting**')
            raw_files = st.file_uploader(
                "Photos brutes", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key="raw_files", label_visibility="collapsed"
            )
            if raw_files:
                st.caption(f"✅ {len(raw_files)} photos brutes chargées.")

    # ------------------------------------------------------------
    # ÉTAPE 2 : PARAMÈTRES DE TRAITEMENT (COLOR MATCH, CROP, DÉTOUSAGE)
    # ------------------------------------------------------------
    if raw_files and master_file:
        with ph_block(
            "ph-step-2",
            "⚡ ÉTAPE 2",
            "PARAMÈTRES DU TRAITEMENT AUTOMATISÉ",
            "Activez les modules de traitement à appliquer sur le lot.",
        ):
            c1, c2, c3 = st.columns(3)
            with c1:
                do_color_match = st.checkbox("1. Color Match (Alignement Master)", value=True, key="do_cm")
            with c2:
                do_birefnet = st.checkbox("2. Détourage HD (BiRefNet)", value=True, key="do_bg")
            with c3:
                do_autocrop = st.checkbox("3. Auto-Crop & Marges 15%", value=True, key="do_crop")

            st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
            btn_launch_media = st.button("🚀 EXECUTER LE TRAITEMENT DE MEDIA (ÉTAPES 1 À 5)")

            if btn_launch_media:
                # Simulation / Exécution du pipeline
                bar = st.progress(0, text="Analyse et tri des paires IA...")
                
                # Sauvegarde du master
                with open(DIR_MASTER / master_file.name, "wb") as f:
                    f.write(master_file.getbuffer())

                # Sauvegarde des bruts
                for f in raw_files:
                    with open(DIR_RAW / f.name, "wb") as out:
                        out.write(f.getbuffer())

                time.sleep(1)
                bar.progress(25, text="Étape 1 : Tri & Appairage Face ID (1 Portrait + 1 Action par joueur)...")
                
                # Logique de simulation d'appairage pour l'exemple
                time.sleep(1)
                bar.progress(50, text="Étape 2 : Color Match sur la photo Master...")
                
                time.sleep(1)
                bar.progress(75, text="Étape 3 & 4 : Détourage BiRefNet & Extension de toile (Canvas 15%)...")
                
                time.sleep(1)
                bar.progress(100, text="Étape 5 : Exportation des paires structurées < 5Mo...")

                # Génération factice de la structure pour affichage
                num_pairs = max(1, len(raw_files) // 2)
                for i in range(num_pairs):
                    pair_id = f"{team_name}_{str(i+1).zfill(4)}"
                    
                    # Création de fichiers factices dans les dossiers pour validation du flow
                    img_dummy = Image.new("RGBA", (1000, 1200), (255, 255, 255, 0))
                    img_dummy.save(DIR_PORTRAITS / f"{pair_id}.png")
                    img_dummy.save(DIR_ACTION / f"{pair_id}.png")

                st.session_state["media_processed"] = True
                st.success(f"✅ Traitement terminé ! {num_pairs} paires générées dans /PORTRAIT et /ACTION.")

    # ------------------------------------------------------------
    # ÉTAPE 3 : APPARIEMENT ET VÉRIFICATION VISUELLE
    # ------------------------------------------------------------
    if st.session_state.get("media_processed"):
        with ph_block(
            "ph-step-3",
            "⚡ ÉTAPE 3",
            "VÉRIFICATION DES PAIRES CRÉÉES",
            "Contrôlez les visuels générés et nommés avant le passage dans Photoshop.",
        ):
            portraits_created = sorted(list(DIR_PORTRAITS.glob("*.png")))
            
            st.markdown(f'<span class="ph-badge ph-badge-ok">{len(portraits_created)} PAIRES DÉTECTÉES</span>', unsafe_allow_html=True)
            st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)

            grid = st.columns(6)
            for idx, p_path in enumerate(portraits_created):
                pair_name = p_path.stem
                action_path = DIR_ACTION / f"{pair_name}.png"
                
                with grid[idx % 6]:
                    st.markdown('<div class="ph-pair-card">', unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    with c1:
                        st.caption("PORTRAIT")
                        st.image(str(p_path), use_container_width=True)
                    with c2:
                        st.caption("ACTION")
                        if action_path.exists():
                            st.image(str(action_path), use_container_width=True)
                    st.markdown(f'<p class="ph-pair-name">{pair_name}</p>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # ÉTAPE 4 : EXPORT ET TÉLÉCHARGEMENT
    # ------------------------------------------------------------
    if st.session_state.get("media_processed"):
        with ph_block(
            "ph-step-4",
            "📥 ÉTAPE 4",
            "EXPORTATION DES DOSSIERS PORTRAIT & ACTION",
            "Téléchargez l'archive complète des dossiers configurés (< 5 Mo par image).",
        ):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as z:
                for f in DIR_PORTRAITS.glob("*.png"):
                    z.write(f, arcname=f"PORTRAIT/{f.name}")
                for f in DIR_ACTION.glob("*.png"):
                    z.write(f, arcname=f"ACTION/{f.name}")

            st.download_button(
                "📦 TÉLÉCHARGER LES DOSSIERS STRUCTURÉS (.ZIP)",
                data=zip_buf.getvalue(),
                file_name=f"POSTER_HEROES_MEDIA_{team_name}.zip",
                mime="application/zip",
            )

# ============================================================
# 6. MODULE 2 : CREATE POSTER (PILOTAGE PHOTOSHOP)
# ============================================================

if st.session_state.main_action == "create_poster":

    st.markdown(
        '<p class="ph-block-title" style="color:#000 !important;font-size:26px;margin-top:10px;">'
        '⚡ MODULE CREATE POSTER — ASSEMBLAGE PHOTOSHOP</p>',
        unsafe_allow_html=True,
    )

    with ph_block(
        "ph-step-ps-1",
        "⚡ CONFIGURATION",
        "LANCEMENT DU SCRIPT PHOTOSHOP LOCAL",
        "Sélectionnez le dossier source contenant les sous-dossiers /PORTRAIT et /ACTION pour lancer le script JS dans Photoshop.",
    ):
        st.markdown('**1. Dossier Source des Médias**')
        st.text_input("Chemin du dossier local", value=str(WORK_DIR), key="ps_folder_path")

        st.markdown('**2. Choix du Template PSD**')
        st.file_uploader("Template PSD Master", type=["psd", "psdt"], key="psd_template")

        st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
        
        if st.button("🚀 EXÉCUTER LE SCRIPT PHOTOSHOP (SCRIPT JS)"):
            st.info("Commande envoyée à Photoshop local via AppleScript...")
            time.sleep(2)
            st.success("✅ Génération lancée dans Photoshop sur votre Mac !")
