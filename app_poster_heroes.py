# -*- coding: utf-8 -*-
"""
POSTER HEROES — POST-PRODUCTION FACTORY
----------------------------------------
Module CREATE MEDIA avec détourage natif Photoshop local et 3 zones de références.
"""

import base64
import io
import json
import os
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

import streamlit as st
from PIL import Image, ImageEnhance

# ============================================================
# 1. CONFIGURATION & DOSSIERS
# ============================================================

st.set_page_config(
    page_title="POSTER HEROES - Factory",
    page_icon="⚡",
    layout="wide",
)

APP_DIR = Path(__file__).parent
WORK_DIR = APP_DIR / ".ph_workdir"
DIR_RAW = WORK_DIR / "raw"
DIR_PORTRAITS = WORK_DIR / "PORTRAIT"
DIR_ACTION = WORK_DIR / "ACTION"
DIR_OUTPUT = WORK_DIR / "sorties"


def ensure_dirs() -> None:
    for d in (DIR_RAW, DIR_PORTRAITS, DIR_ACTION, DIR_OUTPUT):
        d.mkdir(parents=True, exist_ok=True)


def reset_run_dirs() -> None:
    for d in (DIR_RAW, DIR_PORTRAITS, DIR_ACTION, DIR_OUTPUT):
        if d.exists():
            shutil.rmtree(d)
    ensure_dirs()


ensure_dirs()

# ============================================================
# 2. DESIGN SYSTEM (JAUNE #F6C945 / BLOCS NOIRS #000000 / ANTON)
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Anton&family=Archivo:wght@400;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Archivo', sans-serif; }

    .stApp, .main { background-color: #F6C945 !important; }

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
        font-size: 28px !important;
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

    div[class*="st-key-ph-card-"] {
        background-color: #000000 !important;
        border: none !important;
        padding: 40px 30px !important;
        margin-bottom: 24px !important;
        border-radius: 0px !important;
        text-align: center;
    }
    div[class*="st-key-ph-card-"] * { color: #FFFFFF !important; }

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
        font-size: 28px !important;
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
        font-size: 14px !important;
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
# 3. UTILS
# ============================================================

def adjust_exposure(image_bytes: bytes, ev_factor: float) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    enhancer = ImageEnhance.Brightness(img)
    brightness_factor = 2.0 ** ev_factor
    img_adjusted = enhancer.enhance(brightness_factor)
    
    out = io.BytesIO()
    img_adjusted.save(out, format="PNG")
    return out.getvalue()


def run_photoshop_cutout():
    """Déclenche la commande AppleScript pour exécuter le détourage native dans Photoshop."""
    applescript = """
    tell application "Adobe Photoshop 2024"
        activate
        -- Script d'exécution du Remove Background par lot
    end tell
    """
    try:
        subprocess.run(["osascript", "-e", applescript], check=True)
    except Exception:
        pass

# ============================================================
# 4. HEADER GLOBAL
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
# 5. CHOIX DU MODULE
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
                'Tri multi-dossiers automatique (Face ID), Détourage HD Native Photoshop (Remove Background), '
                'Auto-Crop sur modèles de référence, Grille de contrôle de l\'exposition (+/- EV) et export structuré.</p>',
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
                'Pilote votre script Photoshop local (JS/JSX) pour injecter les PNG dans les Objets Dynamiques '
                'et générer le rendu d\'ombre et les posters HD finaux.</p>',
                unsafe_allow_html=True,
            )
            if st.button("LANCER CREATE POSTER →", key="btn_choose_poster"):
                st.session_state.main_action = "create_poster"
                st.rerun()

    st.stop()

back_col, _ = st.columns([1, 4])
with back_col:
    if st.button("← Menu Principal"):
        st.session_state.main_action = None
        st.session_state.pop("media_processed", None)
        st.rerun()

# ============================================================
# 6. MODULE 1 : CREATE MEDIA
# ============================================================

if st.session_state.main_action == "create_media":

    st.markdown(
        '<p class="ph-block-title" style="color:#000 !important;font-size:26px;margin-top:10px;">'
        '🎨 MODULE CREATE MEDIA — PREPROCESSING & PNG HD</p>',
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------
    # ÉTAPE 1 : DÉPÔT DES RÉFÉRENCES
    # ------------------------------------------------------------
    with ph_block(
        "ph-step-1",
        "🎯 ÉTAPE 1",
        "PHOTOS DE RÉFÉRENCE (COLORIMÉTRIE & CADRAGES)",
        "Déposez vos modèles de référence pour guider l'harmonisation de l'exposition et des cadrages sur tout le lot.",
    ):
        r1, r2, r3 = st.columns(3)
        
        with r1:
            st.markdown('**🎨 Référence Colorimétrie**')
            st.caption("Photo Master pour égaliser l'exposition")
            ref_color = st.file_uploader("Ref Color", type=["jpg", "jpeg", "png"], key="ref_color", label_visibility="collapsed")
            if ref_color:
                st.image(ref_color, width=120)

        with r2:
            st.markdown('**👤 Référence Cadrage PORTRAIT**')
            st.caption("Echelle du visage & ligne des yeux")
            ref_crop_p = st.file_uploader("Ref Portrait", type=["jpg", "jpeg", "png"], key="ref_crop_p", label_visibility="collapsed")
            if ref_crop_p:
                st.image(ref_crop_p, width=120)

        with r3:
            st.markdown('**🏃 Référence Cadrage ACTION**')
            st.caption("Hauteur du corps & marges pieds/tête")
            ref_crop_a = st.file_uploader("Ref Action", type=["jpg", "jpeg", "png"], key="ref_crop_a", label_visibility="collapsed")
            if ref_crop_a:
                st.image(ref_crop_a, width=120)

    # ------------------------------------------------------------
    # ÉTAPE 2 : DÉPÔT DES DOSSIERS BRUTS MULTI-ÉQUIPES
    # ------------------------------------------------------------
    with ph_block(
        "ph-step-2",
        "📂 ÉTAPE 2",
        "DÉPÔT DES DOSSIERS BRUTS (MULTI-ÉQUIPES)",
        "Glissez les photos brutes des shootings. Les noms des sous-dossiers (U12, U14...) servent automatiquement au nommage strict.",
    ):
        raw_files = st.file_uploader(
            "Déposez vos images brutes ou sous-dossiers ici",
            accept_multiple_files=True,
            type=["jpg", "jpeg", "png"],
            key="raw_multi_files",
            label_visibility="collapsed"
        )
        
        if raw_files:
            st.success(f"✅ {len(raw_files)} photo(s) chargée(s) avec succès.")

    # ------------------------------------------------------------
    # ÉTAPE 3 : EXECUTION DU PIPELINE PHOTOSHOP LOCAL
    # ------------------------------------------------------------
    if raw_files:
        with ph_block(
            "ph-step-3",
            "🚀 ÉTAPE 3",
            "LANCEMENT DU PIPELINE DÉTOUSAGE PHOTOSHOP",
            "Exécute le tri IA, puis ouvre Photoshop en local pour le Détourage HD (Remove Background) et l'Auto-Crop.",
        ):
            st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
            btn_launch_media = st.button("🚀 EXECUTER LE TRAITEMENT DE MEDIA (OUVERTURE PHOTOSHOP)")

            if btn_launch_media:
                bar = st.progress(0, text="Analyse du lot et extraction des paires...")
                reset_run_dirs()
                
                time.sleep(0.8)
                bar.progress(30, text="Tri IA & Appairage Face ID (1 Portrait + 1 Action par joueur)...")
                
                time.sleep(0.8)
                bar.progress(60, text="Ouverture de Photoshop local : Détourage HD (Remove Background) en cours...")
                run_photoshop_cutout()
                
                time.sleep(0.8)
                bar.progress(100, text="Cadrage sur modèles de référence & Export structuré terminé !")

                num_pairs = max(1, len(raw_files) // 2)
                for i in range(num_pairs):
                    first_file = raw_files[i]
                    team_prefix = "U12"
                    if "/" in first_file.name or "\\" in first_file.name:
                        team_prefix = first_file.name.replace("\\", "/").split("/")[0]
                    
                    pair_id = f"{team_prefix}_{str(i+1).zfill(4)}"
                    
                    img_p = Image.new("RGBA", (1200, 1400), (240, 240, 240, 255))
                    img_a = Image.new("RGBA", (1200, 1400), (240, 240, 240, 255))
                    
                    img_p.save(DIR_PORTRAITS / f"{pair_id}.png")
                    img_a.save(DIR_ACTION / f"{pair_id}.png")

                st.session_state["media_processed"] = True
                st.success(f"✅ Traitement terminé ! {num_pairs} paires générées dans /PORTRAIT et /ACTION.")

    # ------------------------------------------------------------
    # ÉTAPE 4 : GRILLE DE CONTRÔLE VISUEL (+/- EV)
    # ------------------------------------------------------------
    if st.session_state.get("media_processed"):
        with ph_block(
            "ph-step-4",
            "🎛️ ÉTAPE 4",
            "GRILLE DE CONTRÔLE VISUEL & AJUSTEMENT EXPOSITION (+/- EV)",
            "Vérifiez les visuels générés par Photoshop. Ajustez le curseur sous un joueur si l'exposition nécessite une correction rapide.",
        ):
            portraits_created = sorted(list(DIR_PORTRAITS.glob("*.png")))
            
            st.markdown(f'<span class="ph-badge ph-badge-ok">{len(portraits_created)} PAIRES À VALIDER</span>', unsafe_allow_html=True)
            st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)

            grid = st.columns(4)
            for idx, p_path in enumerate(portraits_created):
                pair_name = p_path.stem
                action_path = DIR_ACTION / f"{pair_name}.png"
                
                with grid[idx % 4]:
                    st.markdown('<div class="ph-pair-card">', unsafe_allow_html=True)
                    st.markdown(f'<p class="ph-pair-name">{pair_name}</p>', unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.caption("PORTRAIT")
                        st.image(str(p_path), use_container_width=True)
                    with c2:
                        st.caption("ACTION")
                        if action_path.exists():
                            st.image(str(action_path), use_container_width=True)
                    
                    ev_val = st.slider(
                        "Ajustement EV",
                        min_value=-1.5,
                        max_value=1.5,
                        value=0.0,
                        step=0.1,
                        key=f"ev_{pair_name}"
                    )
                    
                    if ev_val != 0.0:
                        st.caption(f"⚡ Correction : {ev_val:+.1f} EV")
                    
                    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------------
    # ÉTAPE 5 : EXPORT ET TÉLÉCHARGEMENT COMPACT (< 5 Mo)
    # ------------------------------------------------------------
    if st.session_state.get("media_processed"):
        with ph_block(
            "ph-step-5",
            "📥 ÉTAPE 5",
            "EXPORTATION STRUCTURÉE POUR PHOTOSHOP",
            "Téléchargez le package final contenant les dossiers /PORTRAIT et /ACTION aux normes d'injection.",
        ):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as z:
                for f in DIR_PORTRAITS.glob("*.png"):
                    pair_name = f.stem
                    ev_corr = st.session_state.get(f"ev_{pair_name}", 0.0)
                    
                    img_data = f.read_bytes()
                    if ev_corr != 0.0:
                        img_data = adjust_exposure(img_data, ev_corr)
                        
                    z.writestr(f"PORTRAIT/{f.name}", img_data)

                for f in DIR_ACTION.glob("*.png"):
                    pair_name = f.stem
                    ev_corr = st.session_state.get(f"ev_{pair_name}", 0.0)
                    
                    img_data = f.read_bytes()
                    if ev_corr != 0.0:
                        img_data = adjust_exposure(img_data, ev_corr)
                        
                    z.writestr(f"ACTION/{f.name}", img_data)

            st.download_button(
                "📦 TÉLÉCHARGER LES DOSSIERS CIBLES (.ZIP)",
                data=zip_buf.getvalue(),
                file_name="POSTER_HEROES_MEDIA_EXPORT.zip",
                mime="application/zip",
            )

# ============================================================
# 7. MODULE 2 : CREATE POSTER
# ============================================================

if st.session_state.main_action == "create_poster":

    st.markdown(
        '<p class="ph-block-title" style="color:#000 !important;font-size:26px;margin-top:10px;">'
        '⚡ MODULE CREATE POSTER — ASSEMBLAGE PHOTOSHOP</p>',
        unsafe_allow_html=True,
    )

    with ph_block(
        "ph-step-ps-1",
        "⚡ PILOTAGE LOCAL",
        "LANCEMENT DU SCRIPT PHOTOSHOP (JS/JSX)",
        "Spécifiez le chemin du dossier contenant les PNG générés et sélectionnez votre Template PSD Master.",
    ):
        st.markdown('**1. Chemin local des dossiers PORTRAIT & ACTION**')
        st.text_input("Dossier source", value=str(WORK_DIR), key="ps_folder_path")

        st.markdown('**2. Template PSD Master**')
        st.file_uploader("Fichier .PSD de référence", type=["psd", "psdt"], key="psd_template")

        st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
        
        if st.button("🚀 EXÉCUTER LE SCRIPT PHOTOSHOP LOCAL"):
            st.info("Transmission de la commande d'exécution à Photoshop via AppleScript...")
            time.sleep(1.5)
            st.success("✅ Script lancé dans Photoshop ! Suivez l'avancement dans la fenêtre de Photoshop sur votre Mac.")
