# -*- coding: utf-8 -*-
import streamlit as st
import os
import time
import io
from PIL import Image
import zipfile

# Configuration de la page Streamlit
st.set_page_config(
    page_title="POSTER HEROES - Production Locale",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 POSTER HEROES — Plateforme de Post-Production Locale")
st.write("Machine d'automatisation d'imagerie connectée à l'API Nano Banana Pro (Gemini Image API).")

# --- INITIALISATION DES DOSSIERS TEMPORAIRES ---
def init_folders():
    for folder in ["temp_portraits", "temp_pieds", "temp_template", "temp_sorties"]:
        if not os.path.exists(folder):
            os.makedirs(folder)

init_folders()

# --- INTERFACE DE TÉLÉVERSEMENT ---
st.subheader("🎨 1. Chargement du Template Graphique")
template_file = st.file_uploader(
    "Glissez le FOND DE POSTER (Template vierge) ici", 
    accept_multiple_files=False, 
    type=["jpg", "jpeg", "png", "psd"],
    key="template"
)

st.write("---")
st.subheader("📸 2. Chargement des Photos des Joueurs")

col1, col2 = st.columns(2)

with col1:
    st.write("📂 **Dossier PORTRAITS**")
    portraits_files = st.file_uploader(
        "Glissez les portraits ici", 
        accept_multiple_files=True, 
        type=["jpg", "jpeg", "png"],
        key="portraits"
    )

with col2:
    st.write("📂 **Dossier PHOTOS EN PIEDS**")
    pieds_files = st.file_uploader(
        "Glissez les photos en pieds ici", 
        accept_multiple_files=True, 
        type=["jpg", "jpeg", "png"],
        key="pieds"
    )

# --- SAUVEGARDE ET APPARIEMENT ---
if template_file and portraits_files and pieds_files:
    
    # Sauvegarde du template de fond
    template_path = os.path.join("temp_template", template_file.name)
    with open(template_path, "wb") as buffer:
        buffer.write(template_file.read())
        
    # Sauvegarde locale temporaire des portraits
    portraits_dict = {}
    for f in portraits_files:
        with open(os.path.join("temp_portraits", f.name), "wb") as buffer:
            buffer.write(f.read())
        portraits_dict[f.name] = os.path.join("temp_portraits", f.name)
        
    # Sauvegarde locale temporaire des photos en pieds
    pieds_dict = {}
    for f in pieds_files:
        with open(os.path.join("temp_pieds", f.name), "wb") as buffer:
            buffer.write(f.read())
        pieds_dict[f.name] = os.path.join("temp_pieds", f.name)

    # Détection des paires valides par nom exact
    paires_valides = []
    for name in portraits_dict.keys():
        if name in pieds_dict:
            paires_valides.append(name)

    # Affichage du statut d'appariement
    st.success(f"🔗 Template chargé : {template_file.name} | Correspondance établie : {len(paires_valides)} paires de joueurs détectées.")
    
    if len(paires_valides) < len(portraits_dict):
        st.warning(f"⚠️ Attention : {len(portraits_dict) - len(paires_valides)} portraits ou photos en pieds n'ont pas de correspondance exacte par le nom.")

    # --- SIMULATION APPEL API NANO BANANA PRO ---
    def call_nano_banana_api(portrait_path, pieds_path, bg_template_path):
        # Simulation du traitement IA (Détourage + Incrustation sur le template + Lumière)
        time.sleep(1.2) 
        
        # Pour le test, on retourne l'image du portrait simulée
        img_portrait = Image.open(portrait_path)
        return img_portrait

    # --- BOUTON DE LANCEMENT DE LA PRODUCTION ---
    if st.button("🔥 LANCER LA PRODUCTION EN MASSE"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, filename in enumerate(paires_valides):
            status_text.text(f"Fusion IA en cours : {filename} ({idx+1}/{len(paires_valides)})")
            
            p_path = portraits_dict[filename]
            f_path = pieds_dict[filename]
            
            # Appel API avec passage du template
            poster_image = call_nano_banana_api(p_path, f_path, template_path)
            
            # Renommage Intelligent Strict
            output_filename = filename
            output_path = os.path.join("temp_sorties", output_filename)
            poster_image.save(output_path)
            
            progress_bar.progress((idx + 1) / len(paires_valides))
            
        status_text.text("✅ Production terminée ! Tous les posters ont été fusionnés sur le template et renommés.")
        
        # --- ENREGISTREMENT ET TÉLÉCHARGEMENT ---
        st.write("---")
        st.subheader("📥 3. Zone de Récupération des Posters")
        
        # Création du ZIP complet
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for filename in paires_valides:
                file_path = os.path.join("temp_sorties", filename)
                if os.path.exists(file_path):
                    zip_file.write(file_path, arcname=filename)
        
        st.download_button(
            label="📦 TÉLÉCHARGER TOUT LE PACK (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name="PACK_POSTERS_HEROES.zip",
            mime="application/zip"
        )
        
        # Galerie d'aperçus
        st.write("### Aperçu individuel :")
        cols_preview = st.columns(4)
        for idx, filename in enumerate(paires_valides):
            file_path = os.path.join("temp_sorties", filename)
            with cols_preview[idx % 4]:
                st.image(file_path, caption=filename, use_container_width=True)
                with open(file_path, "rb") as file_bytes:
                    st.download_button(
                        label=f"Télécharger",
                        data=file_bytes,
                        file_name=filename,
                        mime="image/jpeg",
                        key=f"dl_{filename}"
                    )
else:
    st.info("💡 Pour activer la machine, dépose :
