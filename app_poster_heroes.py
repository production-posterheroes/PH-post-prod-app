# -*- coding: utf-8 -*-
"""
POSTER HEROES — POST-PRODUCTION FACTORY
----------------------------------------
Application locale Streamlit pour automatiser la fabrication des posters
sportifs individuels (portrait + photo en pieds + template de référence).

Cette version : design finalisé + logique métier (appariement, vérification,
export) sans appel API. Le module `generate_poster` est le point d'entrée
unique à brancher sur Nano Banana Pro dans une prochaine itération — voir
la fonction `generate_poster_placeholder()` en bas de fichier.
"""

import base64
import io
import json
import re
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

try:
    import numpy as np
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from google import genai
    from google.genai import types as genai_types

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# ============================================================
# 1. CONFIGURATION GÉNÉRALE & SPEC D'IMPRESSION
# ============================================================

st.set_page_config(
    page_title="POSTER HEROES - Factory",
    page_icon="⚡",
    layout="wide",
)

APP_DIR = Path(__file__).parent
WORK_DIR = APP_DIR / ".ph_workdir"
DIR_TEMPLATE = WORK_DIR / "template"
DIR_PORTRAITS = WORK_DIR / "portraits"
DIR_PIEDS = WORK_DIR / "pieds"
DIR_OUTPUT = WORK_DIR / "sorties"

# Spécification d'impression finale (utilisée pour le manifeste de génération)
# Format portrait (le sportif est vertical sur le poster) : largeur × hauteur
PRINT_WIDTH_CM = 40
PRINT_HEIGHT_CM = 60
PRINT_DPI = 300
COLOR_PROFILE = "sRGB"

# Ratios acceptés par l'API image de Nano Banana Pro (Gemini 3 Pro Image)
_ALLOWED_ASPECT_RATIOS = {
    "1:1": 1.0, "2:3": 2 / 3, "3:2": 3 / 2, "3:4": 3 / 4, "4:3": 4 / 3,
    "4:5": 4 / 5, "5:4": 5 / 4, "9:16": 9 / 16, "16:9": 16 / 9, "21:9": 21 / 9,
}


def nearest_aspect_ratio(width_cm: float, height_cm: float) -> str:
    target = width_cm / height_cm
    return min(_ALLOWED_ASPECT_RATIOS, key=lambda k: abs(_ALLOWED_ASPECT_RATIOS[k] - target))


PRINT_ASPECT_RATIO = nearest_aspect_ratio(PRINT_WIDTH_CM, PRINT_HEIGHT_CM)


def cm_to_px(cm: float, dpi: int = PRINT_DPI) -> int:
    return round(cm / 2.54 * dpi)


PRINT_WIDTH_PX = cm_to_px(PRINT_WIDTH_CM)
PRINT_HEIGHT_PX = cm_to_px(PRINT_HEIGHT_CM)


def ensure_dirs() -> None:
    for d in (DIR_TEMPLATE, DIR_PORTRAITS, DIR_PIEDS, DIR_OUTPUT):
        d.mkdir(parents=True, exist_ok=True)


def reset_run_dirs() -> None:
    """Nettoie les dossiers de travail avant une nouvelle production."""
    for d in (DIR_TEMPLATE, DIR_PORTRAITS, DIR_PIEDS, DIR_OUTPUT):
        if d.exists():
            shutil.rmtree(d)
    ensure_dirs()


# ============================================================
# 2. DESIGN SYSTEM — BLOCS NOIRS / TITRES BLANCS / FOND JAUNE
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Anton&family=Archivo:wght@400;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Archivo', sans-serif; }

    .stApp, .main { background-color: #F6C945 !important; }

    /* ---------- HEADER ---------- */
    .sub-title {
        font-family: 'Anton', sans-serif !important;
        font-size: 20px !important;
        text-align: center;
        color: #000000 !important;
        text-transform: uppercase;
        letter-spacing: 3px;
        margin-top: 0px;
        margin-bottom: 35px;
        opacity: 0.85;
    }

    /* ---------- BLOCS NOIRS (une étape = un bloc réel st.container(key=)) ---------- */
    div[class*="st-key-ph-step-"] {
        background-color: #000000 !important;
        border: none !important;
        box-shadow: none !important;
        padding: 30px 34px !important;
        margin-bottom: 24px !important;
        border-radius: 0px !important;
    }
    div[class*="st-key-ph-step-"] * { border-radius: 0px !important; }
    div[class*="st-key-ph-step-"],
    div[class*="st-key-ph-step-"] p,
    div[class*="st-key-ph-step-"] span,
    div[class*="st-key-ph-step-"] label,
    div[class*="st-key-ph-step-"] div,
    div[class*="st-key-ph-step-"] small {
        color: #FFFFFF !important;
    }
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
    .ph-asset-title {
        font-family: 'Anton', sans-serif !important;
        color: #FFFFFF !important;
        font-size: 17px !important;
        text-transform: uppercase;
        margin-bottom: 4px;
        letter-spacing: 0.5px;
    }
    .ph-asset-desc {
        color: #FFFFFF !important;
        opacity: 0.6;
        font-size: 13px;
        margin-bottom: 12px;
    }
    .ph-divider {
        border: none;
        border-top: 1px solid rgba(255,255,255,0.15);
        margin: 22px 0;
    }

    /* ---------- UPLOADERS : bloc noir pur, pointillés blancs, texte blanc ---------- */
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
    div[class*="st-key-ph-step-"] .stFileUploader section button {
        background-color: transparent !important;
        color: #FFFFFF !important;
        border: 1.5px solid #FFFFFF !important;
        border-radius: 0px !important;
    }
    div[class*="st-key-ph-step-"] .stFileUploader section button:hover {
        background-color: #F6C945 !important;
        color: #000000 !important;
        border-color: #F6C945 !important;
    }
    div[class*="st-key-ph-step-"] .stFileUploader footer { display: none !important; }
    div[class*="st-key-ph-step-"] [data-testid="stFileUploaderFileName"] { color: #FFFFFF !important; }

    /* ---------- BADGES DE STATUT (appariement) ---------- */
    .ph-badge {
        display: inline-block;
        font-family: 'Anton', sans-serif;
        font-size: 11px;
        letter-spacing: 1px;
        text-transform: uppercase;
        padding: 4px 10px;
        margin-bottom: 6px;
        border-radius: 0px;
    }
    .ph-badge-ok { background-color: #F6C945; color: #000000 !important; }
    .ph-badge-order { background-color: transparent; color: #F6C945 !important; border: 1px solid #F6C945; }
    .ph-badge-warn { background-color: #E4453A; color: #FFFFFF !important; }

    .ph-pair-card {
        border: 1px solid rgba(255,255,255,0.2);
        padding: 8px;
        margin-bottom: 12px;
        background-color: #000000;
    }
    .ph-pair-name {
        font-family: 'Anton', sans-serif !important;
        color: #FFFFFF !important;
        font-size: 15px !important;
        letter-spacing: 0.5px;
        margin: 6px 0 0 0;
        text-transform: uppercase;
    }

    /* ---------- BOUTON D'ACTION PRINCIPAL ---------- */
    .stButton>button {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        font-family: 'Anton', sans-serif !important;
        border: 3px solid #000000 !important;
        border-radius: 0px !important;
        padding: 20px 30px !important;
        font-size: 22px !important;
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
    /* Boutons "CHOISIR" à l'intérieur des cartes de parcours : contour blanc
       transparent, pour rester visibles sur le fond déjà noir de la carte. */
    div[class*="st-key-ph-step-card-"] .stButton>button {
        background-color: transparent !important;
        border: 2px solid #FFFFFF !important;
        color: #FFFFFF !important;
        font-size: 16px !important;
        padding: 12px 20px !important;
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

    /* ---------- PROGRESS BAR ---------- */
    .stProgress > div > div > div > div { background-color: #F6C945 !important; }
    .stProgress > div > div > div { background-color: #333333 !important; }
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
        font-size: 22px !important;
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
    </style>
    """,
    unsafe_allow_html=True,
)


from contextlib import contextmanager


@contextmanager
def ph_block(key: str, eyebrow: str, title: str, desc: str = ""):
    """
    Un vrai bloc noir qui englobe TOUT son contenu (titres, uploaders,
    images...). st.container(key=...) génère une classe CSS `st-key-<key>`
    sur le conteneur réel du DOM — contrairement à un <div> ouvert/fermé
    dans deux st.markdown() séparés, qui ne peut pas envelopper les
    widgets Streamlit intercalés.
    """
    with st.container(key=key):
        st.markdown(f'<p class="ph-step-eyebrow">{eyebrow}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="ph-block-title">{title}</p>', unsafe_allow_html=True)
        if desc:
            st.markdown(f'<p class="ph-block-desc">{desc}</p>', unsafe_allow_html=True)
        yield


# ============================================================
# 3. HEADER
# ============================================================

icon_path = APP_DIR / "logo_icon.png"
if icon_path.exists():
    import base64

    icon_b64 = base64.b64encode(icon_path.read_bytes()).decode()
    st.markdown(
        f"""
        <div class="ph-header">
            <img src="data:image/png;base64,{icon_b64}" style="height:34px;" />
            <div>
                <p class="ph-header-title">Poster Heroes</p>
                <p class="ph-header-sub">Post-Production Factory · V2.0</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="ph-header"><p class="ph-header-title">Poster Heroes</p></div>',
        unsafe_allow_html=True,
    )

ensure_dirs()

# ============================================================
# 4. UTILITAIRES MÉTIER — TRI NATUREL & APPARIEMENT
# ============================================================


def natural_key(name: str):
    """Tri chronologique naturel : img2 avant img10."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def athlete_label(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    return stem.title() if stem else filename


@dataclass
class Pair:
    athlete: str
    portrait_name: str
    pieds_name: str
    match_type: str  # "nom" | "ordre"


@dataclass
class MatchResult:
    pairs: list = field(default_factory=list)
    orphan_portraits: list = field(default_factory=list)
    orphan_pieds: list = field(default_factory=list)


def build_pairs(portrait_names: list[str], pieds_names: list[str]) -> MatchResult:
    """
    Apparie portraits <-> pieds :
    1. Priorité au nom de fichier identique.
    2. Le reste est apparié par ordre chronologique (tri naturel des noms).
    Les fichiers en surplus (l'un des deux dossiers a plus de fichiers)
    restent orphelins et sont signalés.
    """
    result = MatchResult()

    remaining_portraits = sorted(portrait_names, key=natural_key)
    remaining_pieds = sorted(pieds_names, key=natural_key)

    # 1. Appariement exact par nom
    exact = [n for n in remaining_portraits if n in remaining_pieds]
    for name in exact:
        result.pairs.append(Pair(athlete_label(name), name, name, "nom"))
        remaining_portraits.remove(name)
        remaining_pieds.remove(name)

    # 2. Appariement par ordre pour le reste
    n = min(len(remaining_portraits), len(remaining_pieds))
    for i in range(n):
        p_name, f_name = remaining_portraits[i], remaining_pieds[i]
        result.pairs.append(Pair(athlete_label(p_name), p_name, f_name, "ordre"))

    result.orphan_portraits = remaining_portraits[n:]
    result.orphan_pieds = remaining_pieds[n:]

    # Ordre final chronologique global
    result.pairs.sort(key=lambda p: natural_key(p.portrait_name))
    return result


def save_uploads(files, folder: Path) -> None:
    for f in files:
        with open(folder / f.name, "wb") as out:
            out.write(f.getbuffer())


# ============================================================
# 4bis. PRÉ-TRAITEMENT AUTOMATIQUE (SANS IA — algorithmes classiques)
# ============================================================
# Corrige exposition/balance des blancs et recadre automatiquement les
# portraits (détection de visage) et photos en pieds (détection de
# silhouette), avec des méthodes déterministes OpenCV — aucun appel API,
# aucun coût, résultat reproductible à l'identique.

_FACE_CASCADE = None
_EYE_CASCADE = None
_HOG_PERSON_DETECTOR = None


def _get_face_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is None and CV2_AVAILABLE:
        bundled_path = APP_DIR / "haarcascade_frontalface_default.xml"
        if bundled_path.exists():
            cascade_path = str(bundled_path)
        else:
            # Repli : certaines installations d'opencv-python-headless
            # n'exposent pas cv2.data selon la version.
            try:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            except Exception:
                return None
        try:
            loaded = cv2.CascadeClassifier(cascade_path)
            _FACE_CASCADE = loaded if not loaded.empty() else None
        except Exception:
            # Installation OpenCV incomplète/corrompue sur l'environnement de
            # déploiement — on se replie sur "pas de détection" plutôt que
            # de faire planter toute l'étape d'édition.
            _FACE_CASCADE = None
    return _FACE_CASCADE


def _get_eye_cascade():
    global _EYE_CASCADE
    if _EYE_CASCADE is None and CV2_AVAILABLE:
        bundled_path = APP_DIR / "haarcascade_eye.xml"
        if bundled_path.exists():
            cascade_path = str(bundled_path)
        else:
            try:
                cascade_path = cv2.data.haarcascades + "haarcascade_eye.xml"
            except Exception:
                return None
        try:
            loaded = cv2.CascadeClassifier(cascade_path)
            _EYE_CASCADE = loaded if not loaded.empty() else None
        except Exception:
            _EYE_CASCADE = None
    return _EYE_CASCADE


def _get_hog_detector():
    global _HOG_PERSON_DETECTOR
    if _HOG_PERSON_DETECTOR is None and CV2_AVAILABLE:
        try:
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            _HOG_PERSON_DETECTOR = hog
        except Exception:
            _HOG_PERSON_DETECTOR = None
    return _HOG_PERSON_DETECTOR


def _pil_to_cv(img: Image.Image):
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def _cv_to_pil(arr) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))


def _crop_box_centered(bgr, cx: float, cy: float, box_w: float, box_h: float):
    """Découpe classique clampée aux limites de l'image (utilisée en fallback)."""
    h, w = bgr.shape[:2]
    left = int(max(0, min(cx - box_w / 2, w - box_w)))
    top = int(max(0, min(cy - box_h / 2, h - box_h)))
    box_w, box_h = int(min(box_w, w)), int(min(box_h, h))
    return bgr[top: top + box_h, left: left + box_w]


def _frame_on_white_canvas(bgr, box_left: float, box_top: float, box_w: float, box_h: float):
    """
    Place la portion [box_left..box_left+box_w] x [box_top..box_top+box_h] de
    l'image source sur un canevas BLANC de taille (box_w, box_h). Si le cadre
    calculé déborde des limites réelles de la photo, la zone manquante reste
    blanche — aucune reconstruction, aucun pixel inventé.
    """
    h, w = bgr.shape[:2]
    box_w, box_h = max(1, int(round(box_w))), max(1, int(round(box_h)))
    canvas = np.full((box_h, box_w, 3), 255, dtype=np.uint8)

    x0, y0 = max(0.0, box_left), max(0.0, box_top)
    x1, y1 = min(float(w), box_left + box_w), min(float(h), box_top + box_h)
    if x1 <= x0 or y1 <= y0:
        return canvas  # aucun recouvrement : canevas 100% blanc

    src_crop = bgr[int(y0):int(y1), int(x0):int(x1)]
    dest_x, dest_y = int(round(x0 - box_left)), int(round(y0 - box_top))
    dest_x = max(0, min(dest_x, box_w - src_crop.shape[1]))
    dest_y = max(0, min(dest_y, box_h - src_crop.shape[0]))
    canvas[dest_y:dest_y + src_crop.shape[0], dest_x:dest_x + src_crop.shape[1]] = src_crop
    return canvas


def detect_subject(bgr, kind: str):
    """
    Retourne (cx, cy, largeur_sujet, hauteur_sujet) du sujet détecté, ou None.
    Portrait -> visage (Haar cascade) étendu en "tête + épaules".
    Pieds -> silhouette entière (HOG).
    Toute erreur (installation OpenCV cassée, etc.) retombe sur None plutôt
    que de faire planter l'édition — le repli "cadre entier" prend le relais.
    """
    try:
        if kind == "portrait":
            cascade = _get_face_cascade()
            if cascade is None:
                return None
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            if len(faces) == 0:
                return None
            x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            subj_h = fh * 3.2  # tête + cheveux + épaules
            subj_w = fw * 1.8
            return (x + fw / 2, y + fh * 0.45, subj_w, subj_h)
        else:
            hog = _get_hog_detector()
            if hog is None:
                return None
            rects, weights = hog.detectMultiScale(bgr, winStride=(8, 8), padding=(8, 8), scale=1.05)
            if len(rects) == 0:
                return None
            idx = int(np.argmax(weights)) if len(weights) else 0
            x, y, pw, ph = rects[idx]
            return (x + pw / 2, y + ph / 2, pw, ph)
    except Exception:
        return None


def frame_subject_with_padding(
    bgr, kind: str, canvas_ratio: float, target_scale_pct: float, target_vpos_pct: float
):
    """
    Place le sujet détecté à une échelle et une position verticale données,
    toujours centré horizontalement, sur un canevas au ratio demandé. Les
    zones du canevas non couvertes par la photo source restent blanches.
    - target_scale_pct : le sujet occupe X% de la hauteur du canevas final.
    - target_vpos_pct : le centre du sujet est positionné à Y% depuis le haut.
    Sans détection : image entière centrée sur un canevas blanc (fallback sûr).
    """
    h, w = bgr.shape[:2]
    subject = detect_subject(bgr, kind)
    if subject is None:
        cx, cy, subj_h = w / 2, h / 2, h
    else:
        cx, cy, _subj_w, subj_h = subject

    canvas_h = subj_h / max(target_scale_pct, 1.0) * 100.0
    canvas_w = canvas_h * canvas_ratio
    box_top = cy - canvas_h * (target_vpos_pct / 100.0)
    box_left = cx - canvas_w / 2
    return _frame_on_white_canvas(bgr, box_left, box_top, canvas_w, canvas_h)


def frame_portrait_ruled(bgr):
    """
    Cadrage 1:1 strict, règle des tiers, tel que spécifié :
    - Cadre carré (1:1).
    - Ligne horizontale supérieure du tiers alignée sur les YEUX (détection
      réelle via cascade dédiée, pas une approximation de bbox visage).
    - Largeur du visage occupant le tiers central (les lignes verticales des
      tiers coupent approximativement les oreilles) -> largeur du cadre =
      3x la largeur du visage détecté, centré horizontalement dessus.
    Repli (aucun visage détecté, ou toute erreur) : cadre carré centré sur
    l'image entière. Retourne (image, succès: bool, raison: str|None) — la
    raison n'est renseignée qu'en cas de repli, pour un diagnostic réel côté
    appelant plutôt qu'un échec silencieux.
    """
    h, w = bgr.shape[:2]
    try:
        cascade = _get_face_cascade()
        if cascade is None:
            raise ValueError("cascade visage indisponible")
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(faces) == 0:
            raise ValueError("aucun visage détecté")
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])

        # Détection des yeux DANS la zone du visage pour une ligne précise
        eye_y_abs = None
        eye_cascade = _get_eye_cascade()
        if eye_cascade is not None:
            face_roi = gray[max(0, y):y + fh, max(0, x):x + fw]
            if face_roi.size > 0:
                eyes = eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=6, minSize=(15, 15))
                eyes = [e for e in eyes if e[1] < fh * 0.6]  # écarte les faux positifs bas du visage
                if len(eyes) >= 1:
                    eye_y_abs = sum(y + ey + eh / 2 for (ex, ey, ew, eh) in eyes) / len(eyes)
        if eye_y_abs is None:
            eye_y_abs = y + fh * 0.42  # repli anatomique standard si les yeux ne sont pas détectés

        face_cx = x + fw / 2
        frame_w = fw * 3.0  # le visage occupe le tiers central -> cadre = 3x sa largeur
        frame_h = frame_w   # carré
        frame_left = face_cx - frame_w / 2
        frame_top = eye_y_abs - frame_h / 3.0  # les yeux sur la ligne horizontale du 1er tiers

        return _frame_on_white_canvas(bgr, frame_left, frame_top, frame_w, frame_h), True, None
    except Exception as exc:
        side = min(w, h)
        left, top = (w - side) / 2, (h - side) / 2
        return _frame_on_white_canvas(bgr, left, top, side, side), False, str(exc)


def derive_reference_framing(kind: str, reference_bytes: bytes):
    """
    Analyse une photo de référence et en déduit le cadrage à reproduire sur
    tout le lot : ratio du cadre (dimensions de la référence elle-même),
    échelle du sujet (% de la hauteur), position verticale (% depuis le haut).
    Sans détection, ou en cas de panne OpenCV : repli sûr sur le cadre entier
    de la référence (échelle 100%, centré verticalement) — jamais de crash.
    """
    ref_img = Image.open(io.BytesIO(reference_bytes))
    w, h = ref_img.size  # via PIL, ne dépend pas d'OpenCV
    canvas_ratio = w / h if h else 1.0

    if not CV2_AVAILABLE:
        return canvas_ratio, 100.0, 50.0

    try:
        ref_bgr = _pil_to_cv(ref_img)
        subject = detect_subject(ref_bgr, kind)
        if subject is None:
            return canvas_ratio, 100.0, 50.0
        _cx, cy, _subj_w, subj_h = subject
        target_scale_pct = max(1.0, min(100.0, subj_h / h * 100.0))
        target_vpos_pct = max(0.0, min(100.0, cy / h * 100.0))
        return canvas_ratio, target_scale_pct, target_vpos_pct
    except Exception:
        return canvas_ratio, 100.0, 50.0


def auto_white_balance(bgr):
    """Gray-world : ramène les 3 canaux à une moyenne commune (retire les dominantes)."""
    b, g, r = cv2.split(bgr.astype(np.float32))
    avg = (b.mean() + g.mean() + r.mean()) / 3.0
    b *= avg / max(b.mean(), 1e-6)
    g *= avg / max(g.mean(), 1e-6)
    r *= avg / max(r.mean(), 1e-6)
    return np.clip(cv2.merge([b, g, r]), 0, 255).astype(np.uint8)


def auto_exposure_contrast(bgr):
    """CLAHE sur le canal de luminance (LAB) : ré-équilibre exposition/contraste local."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l2, a, b]), cv2.COLOR_LAB2BGR)


def match_color_to_reference(bgr, ref_bgr):
    """
    Transfert de couleur de Reinhard (espace LAB) : recale la moyenne et
    l'écart-type de chaque canal de l'image source sur ceux de l'image de
    référence. Aligne la signature colorimétrique sans dépendre du contenu
    (contrairement au histogram matching classique).
    """
    src_lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    ref_lab = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    for i in range(3):
        s_mean, s_std = src_lab[:, :, i].mean(), src_lab[:, :, i].std()
        r_mean, r_std = ref_lab[:, :, i].mean(), ref_lab[:, :, i].std()
        s_std = s_std if s_std > 1e-6 else 1.0
        src_lab[:, :, i] = (src_lab[:, :, i] - s_mean) * (r_std / s_std) + r_mean
    src_lab = np.clip(src_lab, 0, 255).astype(np.uint8)
    return cv2.cvtColor(src_lab, cv2.COLOR_LAB2BGR)


def preprocess_image(
    image_bytes: bytes,
    kind: str,  # "portrait" | "pieds"
    do_correct: bool,
    correct_mode: str,  # "auto" | "reference"
    reference_bytes: bytes | None,
    do_frame: bool,
    canvas_ratio: float,
    target_scale_pct: float,
    target_vpos_pct: float,
):
    """
    Pipeline complet : correction colorimétrique puis placement, sans IA.
    Retourne (bytes_jpeg, cadrage_ok: bool, raison_repli: str|None) — le
    statut de cadrage reflète ce qui s'est RÉELLEMENT passé (succès de la
    détection utilisée pour le recadrage), pas une vérification parallèle
    qui pourrait donner un faux positif.
    Filet de sécurité global : si OpenCV plante pour une raison quelconque
    (installation cassée sur l'environnement de déploiement, image
    corrompue...), on renvoie l'image d'origine inchangée plutôt que de
    faire planter toute l'étape d'édition pour le reste du lot.
    """
    img = Image.open(io.BytesIO(image_bytes))
    if not CV2_AVAILABLE:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=100, subsampling=0)
        return buf.getvalue(), (not do_frame), ("OpenCV indisponible" if do_frame else None)

    try:
        bgr = _pil_to_cv(img)

        if do_correct:
            if correct_mode == "reference" and reference_bytes:
                ref_bgr = _pil_to_cv(Image.open(io.BytesIO(reference_bytes)))
                bgr = match_color_to_reference(bgr, ref_bgr)
            else:
                bgr = auto_white_balance(bgr)
                bgr = auto_exposure_contrast(bgr)

        frame_ok, frame_reason = True, None
        if do_frame:
            if kind == "portrait":
                bgr, frame_ok, frame_reason = frame_portrait_ruled(bgr)
            else:
                subject_found = detect_subject(bgr, kind) is not None
                bgr = frame_subject_with_padding(bgr, kind, canvas_ratio, target_scale_pct, target_vpos_pct)
                frame_ok = subject_found
                frame_reason = None if subject_found else "aucune silhouette détectée"

        out_buf = io.BytesIO()
        _cv_to_pil(bgr).save(out_buf, "JPEG", quality=100, subsampling=0)
        return out_buf.getvalue(), frame_ok, frame_reason
    except Exception as exc:
        # Panne OpenCV imprévue : on ressort l'image d'origine inchangée,
        # au même niveau de qualité, plutôt que de bloquer tout le lot.
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "JPEG", quality=100, subsampling=0)
        return buf.getvalue(), False, f"erreur pipeline : {exc}"


# ============================================================
# 5. GÉNÉRATION (PLACEHOLDER — POINT DE BRANCHEMENT API)
# ============================================================



# ============================================================
# 5bis. GÉNÉRATION RÉELLE — NANO BANANA PRO (Gemini 3 Pro Image)
# ============================================================

NANO_BANANA_MODEL = "gemini-3-pro-image-preview"
PRICE_PER_IMAGE_4K_USD = 0.24  # tarif indicatif, sortie 4K, à vérifier périodiquement

DEFAULT_PROMPT = (
    "Tu reçois trois images : (1) un poster sportif de référence, (2) le "
    "portrait d'un athlète, (3) une photo de cet athlète en action / en pieds. "
    "Recompose EXACTEMENT le poster (1) à l'identique — mise en page, "
    "typographies, logos, couleurs, décor, effets — en remplaçant uniquement "
    "le personnage présent sur le poster par ce nouvel athlète, en fusionnant "
    "naturellement son visage (2) avec sa posture/action (3). Ne modifie rien "
    "d'autre sur le poster.\n"
    "IMPORTANT 1— Le rendu colorimétrique final du portrait et de la photo en "
    "pieds doit être dans la même ambiance colorimétrique, clareté et "
    "netteté que sur le poster de référence.\n"
    "IMPORTANT 2— Respecter toujours la position et la direction originale "
    "des photos sources (2) et (3). Tu ne dois pas inventer une nouvelle "
    "position, ni faire d'effet miroir.\n"
    "IMPORTANT 3— Les ombres en dessous des pieds lors de l'ajout sur le "
    "nouveau poster doivent être toujours finement travaillées et réalistes.\n"
    "IMPORTANT 4— Les dimensions dans l'espace de l'ajout des photos sources "
    "(2) et (3) doivent respecter au maximum les dimensions dans l'espace du "
    "poster de référence.\n"
    "Rendu final net, qualité studio, sans filigrane."
)


@st.cache_resource(show_spinner=False)
def get_genai_client():
    """Client mis en cache pour toute la session Streamlit."""
    if not GENAI_AVAILABLE:
        return None
    api_key = st.secrets.get("GEMINI_API_KEY") if hasattr(st, "secrets") else None
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def _image_part(path: Path):
    data = path.read_bytes()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return genai_types.Part.from_bytes(data=data, mime_type=mime)


def generate_poster_real(
    pair: Pair, template_path: Path, client, prompt: str, max_retries: int = 3
) -> Image.Image:
    """
    Appel réel à Nano Banana Pro. Envoie template + portrait + pieds en une
    seule requête multi-images, récupère l'image générée dans la réponse.
    Réessaie automatiquement (backoff exponentiel) sur les erreurs
    transitoires (503 surcharge serveur, 429 quota temporaire). Lève une
    exception explicite pour tout le reste (blocage sécurité, réseau...).
    """
    config = genai_types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=genai_types.ImageConfig(
            image_size="4K",
            aspect_ratio=PRINT_ASPECT_RATIO,
        ),
    )

    contents = [
        prompt,
        _image_part(template_path),
        _image_part(DIR_PORTRAITS / pair.portrait_name),
        _image_part(DIR_PIEDS / pair.pieds_name),
    ]

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=NANO_BANANA_MODEL, contents=contents, config=config
            )
            break
        except Exception as exc:
            last_error = exc
            transient = any(code in str(exc) for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))
            if not transient or attempt == max_retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))  # 2s, 4s, 8s...
    else:
        raise last_error

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        parts = getattr(candidate.content, "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline is not None and inline.data:
                return Image.open(io.BytesIO(inline.data)).convert("RGB")

    # Pas d'image : on récupère un maximum de diagnostic avant de lever l'erreur
    diagnostics = []
    prompt_feedback = getattr(response, "prompt_feedback", None)
    if prompt_feedback is not None:
        block_reason = getattr(prompt_feedback, "block_reason", None)
        if block_reason:
            diagnostics.append(f"prompt bloqué : {block_reason}")

    for candidate in candidates:
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason and str(finish_reason) not in ("STOP", "FinishReason.STOP"):
            diagnostics.append(f"finish_reason : {finish_reason}")

    text_fallback = getattr(response, "text", None)
    if text_fallback:
        diagnostics.append(f"texte renvoyé : {text_fallback[:200]}")

    detail = " | ".join(diagnostics) if diagnostics else "aucune information de diagnostic disponible"
    raise RuntimeError(f"Le modèle n'a renvoyé aucune image ({detail}).")


def apply_overlays(poster: Image.Image, overlay_bytes_list: list[bytes]) -> Image.Image:
    """
    Colle des PNG (logo, textes...) par-dessus le poster final. Chaque PNG est
    attendu à la taille EXACTE du poster (même canevas, transparent partout
    sauf les éléments à figer) — donc redimensionné à la taille du poster puis
    collé en pleine page, sans aucun réglage de position. Ces éléments ne
    passent JAMAIS par l'IA : pixels d'origine, garantis identiques d'un
    poster à l'autre.
    """
    poster = poster.convert("RGBA")
    W, H = poster.size
    for data in overlay_bytes_list:
        overlay_img = Image.open(io.BytesIO(data)).convert("RGBA")
        if overlay_img.size != (W, H):
            overlay_img = overlay_img.resize((W, H), Image.LANCZOS)
        poster.paste(overlay_img, (0, 0), overlay_img)
    return poster.convert("RGB")


def generate_poster_placeholder(pair: Pair, template_path: Path) -> Image.Image:
    """
    ⚠️ PLACEHOLDER — pas d'appel IA ici.
    Produit une planche de contrôle (contact sheet) montrant le template,
    le portrait et la photo en pieds côte à côte, pour valider visuellement
    l'appariement avant de brancher Nano Banana Pro sur cette fonction.
    """
    thumb_h = 480
    portrait_img = Image.open(DIR_PORTRAITS / pair.portrait_name).convert("RGB")
    pieds_img = Image.open(DIR_PIEDS / pair.pieds_name).convert("RGB")
    template_img = Image.open(template_path).convert("RGB")

    def resize_h(img, h):
        w = int(img.width * (h / img.height))
        return img.resize((w, h))

    portrait_img = resize_h(portrait_img, thumb_h)
    pieds_img = resize_h(pieds_img, thumb_h)
    template_img = resize_h(template_img, thumb_h)

    gap = 16
    total_w = portrait_img.width + pieds_img.width + template_img.width + gap * 2
    canvas = Image.new("RGB", (total_w, thumb_h + 60), "#0A0A0A")
    x = 0
    for img in (template_img, portrait_img, pieds_img):
        canvas.paste(img, (x, 50))
        x += img.width + gap

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22
        )
    except Exception:
        font = ImageFont.load_default()
    draw.text((10, 12), f"STAGING · {pair.athlete}", fill="#F6C945", font=font)

    return canvas


def build_manifest(match: MatchResult, template_name: str) -> dict:
    return {
        "template": template_name,
        "print_spec": {
            "width_cm": PRINT_WIDTH_CM,
            "height_cm": PRINT_HEIGHT_CM,
            "dpi": PRINT_DPI,
            "width_px": PRINT_WIDTH_PX,
            "height_px": PRINT_HEIGHT_PX,
            "color_profile": COLOR_PROFILE,
        },
        "status": "PENDING_NANO_BANANA_GENERATION",
        "jobs": [
            {
                "athlete": p.athlete,
                "portrait_file": p.portrait_name,
                "pieds_file": p.pieds_name,
                "match_type": p.match_type,
                "output_filename": f"{Path(p.portrait_name).stem}_POSTER.jpg",
            }
            for p in match.pairs
        ],
        "orphans": {
            "portraits_sans_pieds": match.orphan_portraits,
            "pieds_sans_portrait": match.orphan_pieds,
        },
    }


# ============================================================
# 5bis. ÉTAPE 0 — CHOIX DU PARCOURS
# ============================================================

# ============================================================
# 5bis. ÉTAPE 0 — CHOIX DU PARCOURS (navigation par cartes)
# ============================================================

if "app_mode" not in st.session_state:
    st.session_state.app_mode = None

if st.session_state.app_mode is None:
    st.markdown(
        '<p class="ph-block-title" style="text-align:center;color:#000 !important;font-size:26px;">'
        "QUE SOUHAITEZ-VOUS FAIRE ?</p>"
        '<p style="text-align:center;color:#000;opacity:0.7;margin-bottom:24px;">'
        "Choisissez un parcours pour continuer</p>",
        unsafe_allow_html=True,
    )

    cards = [
        (
            "edition", "🎨", "ÉDITION DES IMAGES",
            "Correction colorimétrique + cadrage automatique, calés sur vos "
            "références. Sans IA générative, sans coût.",
        ),
        (
            "posters", "⚡", "CRÉATION DES POSTERS",
            "Vos photos sont déjà éditées ailleurs. Passe directement à la "
            "génération des posters avec Nano Banana Pro.",
        ),
        (
            "both", "🎨⚡", "ÉDITION + POSTERS",
            "Le parcours complet : édition automatique des photos, puis "
            "génération des posters.",
        ),
    ]
    card_cols = st.columns(3)
    for col, (mode_id, icon, title, desc) in zip(card_cols, cards):
        with col:
            with st.container(key=f"ph-step-card-{mode_id}"):
                st.markdown(
                    f'<p style="font-size:42px;text-align:center;margin-bottom:6px;">{icon}</p>'
                    f'<p class="ph-block-title" style="text-align:center;font-size:19px;">{title}</p>'
                    f'<p class="ph-block-desc" style="text-align:center;min-height:75px;">{desc}</p>',
                    unsafe_allow_html=True,
                )
                if st.button("CHOISIR →", key=f"choose_{mode_id}", use_container_width=True):
                    st.session_state.app_mode = mode_id
                    st.rerun()
    st.stop()

APP_MODE = st.session_state.app_mode
SHOW_EDITION = APP_MODE in ("edition", "both")
SHOW_POSTERS = APP_MODE in ("posters", "both") or st.session_state.get("proceed_to_posters", False)

back_col, _ = st.columns([1, 5])
with back_col:
    if st.button("← Changer de parcours"):
        st.session_state.app_mode = None
        st.rerun()

# ============================================================
# 6. ÉTAPE 1 — RÉFÉRENCES
# ============================================================

with ph_block(
    "ph-step-1",
    "⚡ ÉTAPE 1",
    "RÉFÉRENCES",
    "Déposez les images de référence : elles pilotent la colorimétrie et le "
    "cadrage appliqués à tout le lot.",
):
    template_file = None
    portrait_ref_file = None
    pieds_ref_file = None

    if SHOW_POSTERS:
        st.markdown('<p class="ph-asset-title">🖼️ Poster de référence</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="ph-asset-desc">Utilisé par Nano Banana Pro pour la mise en page finale.</p>',
            unsafe_allow_html=True,
        )
        template_file = st.file_uploader(
            "template", type=["jpg", "jpeg"], key="template", label_visibility="collapsed"
        )
        if template_file:
            tcol1, tcol2 = st.columns([1, 3])
            with tcol1:
                st.image(template_file, caption=template_file.name, width=180)
            with tcol2:
                tmpl_img = Image.open(template_file)
                st.markdown(
                    f"""
                    <p class="ph-asset-title">Format de sortie visé</p>
                    <p class="ph-asset-desc" style="opacity:0.9;">
                    {PRINT_WIDTH_CM} × {PRINT_HEIGHT_CM} cm · {PRINT_DPI} dpi · {COLOR_PROFILE}<br>
                    Soit {PRINT_WIDTH_PX} × {PRINT_HEIGHT_PX} px en sortie finale.<br><br>
                    Template importé : {tmpl_img.width} × {tmpl_img.height} px
                    </p>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)

    if SHOW_EDITION:
        st.markdown(
            '<p class="ph-asset-title">🎯 Références d\'édition (1 photo idéale par catégorie)</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="ph-asset-desc">Le cadrage (échelle + position) et la colorimétrie de ces '
            "deux références seront reproduits automatiquement sur tout le lot.</p>",
            unsafe_allow_html=True,
        )
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown('<p class="ph-asset-title">👤 Référence portrait</p>', unsafe_allow_html=True)
            portrait_ref_file = st.file_uploader(
                "portrait_ref", type=["jpg", "jpeg", "png"], key="portrait_ref",
                label_visibility="collapsed",
            )
            if portrait_ref_file:
                st.image(portrait_ref_file, width=150)
        with rc2:
            st.markdown('<p class="ph-asset-title">🏃 Référence pieds</p>', unsafe_allow_html=True)
            pieds_ref_file = st.file_uploader(
                "pieds_ref", type=["jpg", "jpeg", "png"], key="pieds_ref",
                label_visibility="collapsed",
            )
            if pieds_ref_file:
                st.image(pieds_ref_file, width=150)

# ============================================================
# 7. ÉTAPE 2 — PHOTOS JOUEURS
# ============================================================

with ph_block(
    "ph-step-2",
    "⚡ ÉTAPE 2",
    "LES PHOTOS JOUEURS",
    "Même nombre de photos dans chaque bloc, mêmes noms de fichiers si "
    "possible, et dans l'ordre chronologique — pour un appariement fiable.",
):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<p class="ph-asset-title">👤 Portraits</p>', unsafe_allow_html=True)
        st.markdown('<p class="ph-asset-desc">Glissez les visages ici</p>', unsafe_allow_html=True)
        portraits_files = st.file_uploader(
            "portraits",
            accept_multiple_files=True,
            type=["jpg", "jpeg", "png"],
            key="portraits",
            label_visibility="collapsed",
        )
    with c2:
        st.markdown('<p class="ph-asset-title">🏃 Photos en pieds</p>', unsafe_allow_html=True)
        st.markdown('<p class="ph-asset-desc">Glissez les actions ici</p>', unsafe_allow_html=True)
        pieds_files = st.file_uploader(
            "pieds",
            accept_multiple_files=True,
            type=["jpg", "jpeg", "png"],
            key="pieds",
            label_visibility="collapsed",
        )

# ============================================================
# 8. ÉTAPE 3 — ÉDITION DES IMAGES (SANS IA)
# ============================================================

match: MatchResult | None = None

refs_ready = (not SHOW_EDITION) or bool(portrait_ref_file and pieds_ref_file)
template_ready = (not SHOW_POSTERS) or bool(template_file)

if refs_ready and template_ready and portraits_files and pieds_files:
    if template_file:
        save_uploads([template_file], DIR_TEMPLATE)
    save_uploads(portraits_files, DIR_PORTRAITS)
    save_uploads(pieds_files, DIR_PIEDS)

    if SHOW_EDITION:
        if CV2_AVAILABLE:
            with ph_block(
                "ph-step-3",
                "⚡ ÉTAPE 3",
                "ÉDITION DES IMAGES (SANS IA)",
                "Portraits : cadrage 1:1 strict (règle des tiers, yeux alignés). "
                "Pieds : cadrage calé sur votre référence. Colorimétrie alignée "
                "sur les références. Marges blanches si besoin. Export 100% "
                "qualité, mêmes noms de fichiers.",
            ):
                pieds_ratio, pieds_scale, pieds_vpos = derive_reference_framing(
                    "pieds", pieds_ref_file.getvalue()
                )

                st.markdown('<p class="ph-asset-title">📐 Cadrage appliqué</p>', unsafe_allow_html=True)
                dc1, dc2 = st.columns(2)
                with dc1:
                    st.caption("👤 Portrait — règle des tiers 1:1 fixe (yeux sur la ligne supérieure)")
                with dc2:
                    st.caption(
                        f"🏃 Pieds — ratio {pieds_ratio:.2f}, sujet à "
                        f"{pieds_scale:.0f}% de hauteur, position {pieds_vpos:.0f}% depuis le haut"
                    )

                with st.expander("🔧 Ajustement fin — Pieds (optionnel)"):
                    pieds_scale = st.slider("Échelle (%)", 10, 100, int(pieds_scale), key="adj_scale_f")
                    pieds_vpos = st.slider("Position verticale (%)", 0, 100, int(pieds_vpos), key="adj_vpos_f")

                # Diagnostic visible du moteur de détection — évite un repli
                # silencieux (cadre centré sur toute la photo) sans que
                # personne ne comprenne pourquoi le résultat "n'a rien à voir".
                _face_ok = _get_face_cascade() is not None
                _eye_ok = _get_eye_cascade() is not None
                _hog_ok = _get_hog_detector() is not None
                if _face_ok and _eye_ok and _hog_ok:
                    st.caption("✅ Moteur de détection opérationnel (visage, yeux, silhouette).")
                else:
                    missing = []
                    if not _face_ok:
                        missing.append("visage")
                    if not _eye_ok:
                        missing.append("yeux")
                    if not _hog_ok:
                        missing.append("silhouette")
                    st.error(
                        f"⚠️ Détection **{', '.join(missing)}** indisponible sur ce "
                        "déploiement (installation OpenCV incomplète/cassée). Les "
                        "photos concernées retomberont sur un cadre centré sur "
                        "l'image ENTIÈRE, pas sur le sujet — d'où un résultat "
                        "'sans rapport'. Rebootez l'app depuis 'Manage app' sur "
                        "Streamlit Cloud (Clear cache + Reboot) avant de continuer."
                    )

                do_correct = st.checkbox(
                    "Aligner la colorimétrie sur les références", value=True, key="do_correct"
                )
                do_frame = st.checkbox(
                    "Appliquer le cadrage (règle des tiers / référence pieds)", value=True, key="do_frame"
                )

                apply_preproc = st.button("🧹 Appliquer l'édition à tout le lot")

                if apply_preproc:
                    bar_pp = st.progress(0, text="Traitement en cours…")
                    total = len(portraits_files) + len(pieds_files)
                    done = 0
                    no_detection = []  # (nom, raison réelle du repli)
                    jobs = [
                        ("portrait", portraits_files, DIR_PORTRAITS, portrait_ref_file.getvalue(),
                         1.0, 100.0, 50.0),  # ratio/scale/vpos ignorés pour "portrait" (règle fixe)
                        ("pieds", pieds_files, DIR_PIEDS, pieds_ref_file.getvalue(),
                         pieds_ratio, pieds_scale, pieds_vpos),
                    ]
                    for kind, files, folder, ref_bytes, ratio, scale_pct, vpos_pct in jobs:
                        for f in files:
                            path = folder / f.name
                            raw_bytes = path.read_bytes()

                            new_bytes, frame_ok, frame_reason = preprocess_image(
                                raw_bytes, kind, do_correct, "reference",
                                ref_bytes, do_frame, ratio, scale_pct, vpos_pct,
                            )
                            if do_frame and not frame_ok:
                                no_detection.append((f"{kind} — {f.name}", frame_reason))
                            path.write_bytes(new_bytes)  # même nom de fichier, écrasé sur place
                            done += 1
                            bar_pp.progress(done / total, text=f"{f.name}")
                    st.success(f"{total} photo(s) éditée(s) avec succès — 100% qualité, noms préservés.")
                    if no_detection:
                        st.warning(
                            f"⚠️ Cadrage de repli (image entière centrée) sur "
                            f"{len(no_detection)} photo(s) — raison réelle indiquée :\n\n"
                            + "\n".join(f"- {n} ({r})" for n, r in no_detection)
                        )
                    st.session_state["_edition_done"] = True

                if st.session_state.get("_edition_done"):
                    st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
                    st.markdown('<p class="ph-asset-title">Aperçu (taille moyenne)</p>', unsafe_allow_html=True)
                    grid_pp = st.columns(4)
                    all_items = (
                        [(n.name, DIR_PORTRAITS) for n in portraits_files][:2]
                        + [(n.name, DIR_PIEDS) for n in pieds_files][:2]
                    )
                    for i, (name, folder) in enumerate(all_items):
                        with grid_pp[i % 4]:
                            st.image(str(folder / name), caption=name, width=220)

                    st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
                    st.markdown('<p class="ph-asset-title">Et maintenant ?</p>', unsafe_allow_html=True)
                    next_col1, next_col2 = st.columns(2)
                    with next_col1:
                        zip_buf_ed = io.BytesIO()
                        with zipfile.ZipFile(zip_buf_ed, "w") as z:
                            for f in portraits_files:
                                z.write(DIR_PORTRAITS / f.name, arcname=f"portraits/{f.name}")
                            for f in pieds_files:
                                z.write(DIR_PIEDS / f.name, arcname=f"pieds/{f.name}")
                        st.download_button(
                            "📦 TÉLÉCHARGER LES IMAGES ÉDITÉES",
                            data=zip_buf_ed.getvalue(),
                            file_name="POSTER_HEROES_IMAGES_EDITEES.zip",
                            mime="application/zip",
                        )
                    with next_col2:
                        if not SHOW_POSTERS:
                            if st.button("➡️ PASSER À LA CRÉATION DES POSTERS"):
                                st.session_state["proceed_to_posters"] = True
                                st.rerun()
                        else:
                            st.caption("✅ Continuez ci-dessous vers la création des posters.")
        else:
            st.info(
                "OpenCV non installé — l'édition automatique n'est pas "
                "disponible. Ajoutez `opencv-python-headless` à requirements.txt."
            )

    if SHOW_POSTERS:
        match = build_pairs(
            [f.name for f in portraits_files], [f.name for f in pieds_files]
        )

# ============================================================
# 8bis. ÉTAPE 4 — VÉRIFICATION DE L'APPARIEMENT
# ============================================================

if SHOW_POSTERS and match is not None:
    with ph_block(
        "ph-step-4",
        "⚡ ÉTAPE 4",
        "VÉRIFICATION DE L'APPARIEMENT",
        f"{len(match.pairs)} paire(s) détectée(s) sur "
        f"{len(portraits_files)} portrait(s) / {len(pieds_files)} photo(s) en pieds.",
    ):
        n_by_name = sum(1 for p in match.pairs if p.match_type == "nom")
        n_by_order = sum(1 for p in match.pairs if p.match_type == "ordre")
        st.markdown(
            f'<span class="ph-badge ph-badge-ok">{n_by_name} par nom identique</span> '
            f'<span class="ph-badge ph-badge-order">{n_by_order} par ordre chrono.</span>',
            unsafe_allow_html=True,
        )

        if match.orphan_portraits or match.orphan_pieds:
            st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
            if match.orphan_portraits:
                st.warning(
                    "Portrait(s) sans photo en pieds correspondante : "
                    + ", ".join(match.orphan_portraits)
                )
            if match.orphan_pieds:
                st.warning(
                    "Photo(s) en pieds sans portrait correspondant : "
                    + ", ".join(match.orphan_pieds)
                )

        if match.pairs:
            st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
            grid = st.columns(8)
            for i, p in enumerate(match.pairs):
                with grid[i % 8]:
                    st.markdown('<div class="ph-pair-card">', unsafe_allow_html=True)
                    ic1, ic2 = st.columns(2)
                    with ic1:
                        st.image(str(DIR_PORTRAITS / p.portrait_name), width=70)
                    with ic2:
                        st.image(str(DIR_PIEDS / p.pieds_name), width=70)
                    badge_cls = "ph-badge-ok" if p.match_type == "nom" else "ph-badge-order"
                    badge_txt = "NOM" if p.match_type == "nom" else "ORDRE"
                    st.markdown(
                        f'<span class="ph-badge {badge_cls}">{badge_txt}</span>'
                        f'<p class="ph-pair-name">{p.athlete}</p>',
                        unsafe_allow_html=True,
                    )
                    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# 9. LANCEMENT & ÉTAPE 5 — RÉGLAGES
# ============================================================

if match and match.pairs:
    client = get_genai_client()

    with ph_block(
        "ph-step-5",
        "⚡ ÉTAPE 5",
        "RÉGLAGES & LANCEMENT",
        "Ajustez le prompt envoyé à Nano Banana Pro si besoin (colorimétrie, "
        "cadrage, style...), choisissez le mode, puis lancez.",
    ):
        mode_options = ["🧪 Mode test (staging, gratuit)"]
        if client is not None:
            mode_options.append("⚡ Génération réelle (Nano Banana Pro, payant)")
        else:
            st.info(
                "Clé API absente ou SDK non installé — seul le mode test est "
                "disponible. Vérifiez `.streamlit/secrets.toml` et `pip install google-genai`."
            )

        mode = st.radio("Mode de production", mode_options, label_visibility="collapsed")
        real_mode = mode.startswith("⚡")

        st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
        st.markdown(
            '<p class="ph-asset-title">🖼️ Éléments fixes à recoller (logo, textes)</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="ph-asset-desc">PNG transparents, à la taille EXACTE du poster '
            "final (même canevas). Collés tels quels, pleine page, APRÈS la "
            "génération IA — jamais réinterprétés.</p>",
            unsafe_allow_html=True,
        )
        overlay_files = st.file_uploader(
            "overlays",
            type=["png"],
            accept_multiple_files=True,
            key="overlays",
            label_visibility="collapsed",
        )

        overlays_bytes = [f.getvalue() for f in overlay_files] if overlay_files else []
        if overlays_bytes and template_file:
            preview_base = Image.open(template_file).convert("RGBA")
            preview_img = apply_overlays(preview_base, overlays_bytes)
            st.image(preview_img, caption="Aperçu du collage (sur le template)", width=260)

        st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
        st.markdown('<p class="ph-asset-title">📝 Prompt envoyé à l\'IA</p>', unsafe_allow_html=True)
        prompt_text = st.text_area(
            "prompt",
            value=DEFAULT_PROMPT,
            height=220,
            label_visibility="collapsed",
        )
        if st.button("↺ Réinitialiser le prompt par défaut"):
            prompt_text = DEFAULT_PROMPT
            st.rerun()

        if real_mode:
            estimate = len(match.pairs) * PRICE_PER_IMAGE_4K_USD
            st.warning(
                f"Coût estimé pour {len(match.pairs)} poster(s) en 4K : "
                f"environ {estimate:.2f} $ (tarif indicatif Nano Banana Pro, à vérifier)."
            )

        launch = st.button(f"PRODUIRE LES {len(match.pairs)} POSTERS")

    if launch:
        for f in DIR_OUTPUT.glob("*"):
            f.unlink()

        bar = st.progress(0, text="Préparation des jobs de génération…")
        template_path = DIR_TEMPLATE / template_file.name
        errors = []

        for idx, pair in enumerate(match.pairs):
            suffix = "POSTER" if real_mode else "STAGING"
            out_path = DIR_OUTPUT / f"{Path(pair.portrait_name).stem}_{suffix}.jpg"
            try:
                if real_mode:
                    result_img = generate_poster_real(
                        pair, template_path, client, prompt_text
                    )
                    if overlays_bytes:
                        result_img = apply_overlays(result_img, overlays_bytes)
                    result_img.save(out_path, "JPEG", quality=100, subsampling=0)
                else:
                    result_img = generate_poster_placeholder(pair, template_path)
                    if overlays_bytes:
                        result_img = apply_overlays(result_img, overlays_bytes)
                    result_img.save(out_path, "JPEG", quality=92)
            except Exception as exc:
                errors.append(f"{pair.athlete} : {exc}")
            bar.progress(
                (idx + 1) / len(match.pairs),
                text=f"{pair.athlete} ({idx + 1}/{len(match.pairs)})",
            )

        if errors:
            st.error(
                "Échec sur "
                + f"{len(errors)}/{len(match.pairs)} poster(s) :\n\n"
                + "\n".join(f"- {e}" for e in errors)
            )

        manifest = build_manifest(match, template_file.name)
        manifest["status"] = "GENERATED" if real_mode else "STAGING_ONLY"
        manifest["prompt_used"] = prompt_text
        manifest["overlays_count"] = len(overlays_bytes)
        with open(DIR_OUTPUT / "manifest.json", "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, ensure_ascii=False, indent=2)

        with ph_block(
            "ph-step-6",
            "📥 ÉTAPE 6",
            "RÉCUPÉRATION",
            (
                "Posters générés par Nano Banana Pro, prêts à l'impression."
                if real_mode
                else "Aperçus de staging (contrôle d'appariement) — mode test, "
                "aucun appel API facturé."
            ),
        ):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as z:
                for f in DIR_OUTPUT.glob("*"):
                    z.write(f, arcname=f.name)

            zip_name = "POSTER_HEROES_POSTERS.zip" if real_mode else "POSTER_HEROES_STAGING.zip"
            st.download_button(
                "📦 TÉLÉCHARGER LE PACK ZIP COMPLET",
                data=zip_buf.getvalue(),
                file_name=zip_name,
                mime="application/zip",
            )

            st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
            st.markdown('<p class="ph-asset-title">🗂️ Aperçu unitaire</p>', unsafe_allow_html=True)
            grid = st.columns(8)
            suffix = "POSTER" if real_mode else "STAGING"
            for i, pair in enumerate(match.pairs):
                out_path = DIR_OUTPUT / f"{Path(pair.portrait_name).stem}_{suffix}.jpg"
                with grid[i % 8]:
                    if out_path.exists():
                        st.image(str(out_path), caption=pair.athlete, width=170)
                    else:
                        st.caption(f"❌ {pair.athlete}")
