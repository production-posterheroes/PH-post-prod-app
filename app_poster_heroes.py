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
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

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
PRINT_WIDTH_CM = 60
PRINT_HEIGHT_CM = 40
PRINT_DPI = 300
COLOR_PROFILE = "sRGB"


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
    "d'autre sur le poster. Éclairage et perspective cohérents avec le décor "
    "d'origine. Rendu final net, qualité studio, sans filigrane."
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


def generate_poster_real(pair: Pair, template_path: Path, client, prompt: str) -> Image.Image:
    """
    Appel réel à Nano Banana Pro. Envoie template + portrait + pieds en une
    seule requête multi-images, récupère l'image générée dans la réponse.
    Lève une exception explicite en cas d'échec (quota, facturation, réseau,
    réponse sans image) — à charge de l'appelant de l'afficher proprement.
    """
    response = client.models.generate_content(
        model=NANO_BANANA_MODEL,
        contents=[
            prompt,
            _image_part(template_path),
            _image_part(DIR_PORTRAITS / pair.portrait_name),
            _image_part(DIR_PIEDS / pair.pieds_name),
        ],
    )

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        parts = getattr(candidate.content, "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline is not None and inline.data:
                return Image.open(io.BytesIO(inline.data)).convert("RGB")

    # Pas d'image dans la réponse : on remonte le texte éventuel pour debug
    text_fallback = getattr(response, "text", None)
    raise RuntimeError(
        "Le modèle n'a renvoyé aucune image."
        + (f" Réponse : {text_fallback[:200]}" if text_fallback else "")
    )


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
# 6. ÉTAPE 1 — TEMPLATE
# ============================================================

with ph_block(
    "ph-step-1",
    "⚡ ÉTAPE 1",
    "LE TEMPLATE",
    "Déposez le poster de référence (.jpg). Nano Banana Pro s'appuiera "
    "dessus pour ne remplacer que le personnage.",
):
    template_file = st.file_uploader(
        "template", type=["jpg", "jpeg"], key="template", label_visibility="collapsed"
    )
    if template_file:
        st.markdown('<hr class="ph-divider">', unsafe_allow_html=True)
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
# 8. ÉTAPE 3 — VÉRIFICATION DE L'APPARIEMENT
# ============================================================

match: MatchResult | None = None

if template_file and portraits_files and pieds_files:
    save_uploads([template_file], DIR_TEMPLATE)
    save_uploads(portraits_files, DIR_PORTRAITS)
    save_uploads(pieds_files, DIR_PIEDS)

    match = build_pairs(
        [f.name for f in portraits_files], [f.name for f in pieds_files]
    )

    with ph_block(
        "ph-step-3",
        "⚡ ÉTAPE 3",
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
# 9. LANCEMENT & ÉTAPE 4 — RÉCUPÉRATION
# ============================================================

if match and match.pairs:
    client = get_genai_client()

    st.markdown('<hr class="ph-divider" style="border-top-color: rgba(0,0,0,0.2);">', unsafe_allow_html=True)

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
                        pair, template_path, client, DEFAULT_PROMPT
                    )
                else:
                    result_img = generate_poster_placeholder(pair, template_path)
                result_img.save(out_path, quality=95)
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
        with open(DIR_OUTPUT / "manifest.json", "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, ensure_ascii=False, indent=2)

        with ph_block(
            "ph-step-4",
            "📥 ÉTAPE 4",
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
