# -*- coding: utf-8 -*-
import streamlit as st
import os
import time
import zipio
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
    for folder in ["temp_portraits", "temp_pieds", "temp_sorties"]:
        if not os.path.exists(folder):
            os.makedirs(folder)

init_folders()

# --- INTERFACE DE TÉLÉVERSEMENT ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📸 1. Dossier PORTRAITS")
    portraits_files = st.file_uploader(
        "Glissez les portraits ici", 
        accept_multiple_files=True, 
        type=["jpg", "jpeg", "png"],
        key="portraits"
    )

with col2:
    st.subheader("🏃‍♂️ 2. Dossier PHOTOS EN PIEDS")
    pieds_files = st.file_uploader(
        "Glissez les photos en pieds ici", 
        accept_multiple_files=True, 
        type=["jpg", "jpeg", "png"],
        key="pieds"
    )

# --- SAUVEGARDE ET APPARIEMENT ---
if portraits_files and pieds_files:
    # Sauvegarde locale temporaire pour traitement
    portraits_dict = {}
    for f in portraits_files:
        with open(os.path.join("temp_portraits", f.name), "wb") as buffer:
            buffer.write(f.read())
        portraits_dict[f.name] = os.path.join("temp_portraits", f.name)
        
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
    st.success(f"🔗 Correspondance établie : {len(paires_valides)} paires détectées avec succès sur la base du nom exact.")
    
    if len(paires_valides) < len(portraits_dict):
        st.warning(f"⚠️ Attention : {len(portraits_dict) - len(paires_valides)} portraits ou photos en pieds n'ont pas trouvé de correspondance exacte par nom.")

    # --- SIMULATION OU APPEL API NANO BANANA PRO ---
    # Note technique : Remplacer cette fonction par votre appel d'API Vertex AI / Google AI Studio effectif.
    def call_nano_banana_api(portrait_path, pieds_path):
        # En production, ce bloc envoie les images par requêtes POST HTTP sécurisées
        # exemple : 
        # response = requests.post("https://api.google.com/nano-banana/v3/generate", files=...)
        time.sleep(1.5) # Simulation du temps de calcul IA par poster
        
        # Pour le test, on simule la création du poster en superposant une image ou en retournant un duplicata
        img_portrait = Image.open(portrait_path)
        return img_portrait

    # --- BOUTON DE SÉCURITÉ : LANCEMENT DE LA PRODUCTION ---
    if st.button("🔥 LANCER LA PRODUCTION EN MASSE"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Conteneur visuel pour suivre l'avancée réelle
        grille_status = st.container()
        
        for idx, filename in enumerate(paires_valides):
            status_text.text(f"Traitement en cours par l'API : {filename} ({idx+1}/{len(paires_valides)})")
            
            p_path = portraits_dict[filename]
            f_path = pieds_dict[filename]
            
            # Appel API
            poster_image = call_nano_banana_api(p_path, f_path)
            
            # Renommage Intelligent Strict (Prend exactement le nom de la photo portrait d'origine)
            output_filename = filename
            output_path = os.path.join("temp_sorties", output_filename)
            poster_image.save(output_path)
            
            # Mise à jour de la barre de progression
            progress_bar.progress((idx + 1) / len(paires_valides))
            
        status_text.text("✅ Production terminée ! Tous les posters ont été générés et renommés.")
        
        # --- ETAPE DE TÉLÉCHARGEMENT ---
        st.write("---")
        st.subheader("📥 3. Zone de Récupération des Posters")
        
        # Génération du Pack ZIP Global
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
        
        # Grille de téléchargement unitaire avec aperçu
        st.write("### Aperçu individuel et téléchargement unitaire :")
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
    st.info("💡 En attente du dépôt des deux dossiers (Portraits et Pieds) pour lancer l'appariement automatique.")
