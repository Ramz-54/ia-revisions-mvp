\
import os
import io
import re
import csv
from typing import List, Tuple

import streamlit as st
import pandas as pd

from pypdf import PdfReader
import docx2txt
from pptx import Presentation

try:
    # OpenAI SDK v1.x
    from openai import OpenAI
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False

# ─────────────────────────────────────
# Helpers: read secrets/env
# ─────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", st.secrets.get("OPENAI_API_KEY", ""))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", st.secrets.get("OPENAI_MODEL", "gpt-4o-mini"))

# ─────────────────────────────────────
# UI – Sidebar
# ─────────────────────────────────────
st.set_page_config(page_title="IA Révisions Étudiant – MVP", page_icon="📚", layout="wide")
st.sidebar.title("⚙️ Configuration")
model = st.sidebar.text_input("Modèle (OpenAI)", value=OPENAI_MODEL)
max_flashcards = st.sidebar.slider("Nombre de flashcards", 5, 100, 20)
max_qcm = st.sidebar.slider("Nombre de QCM", 5, 50, 10)
summary_style = st.sidebar.selectbox(
    "Style de fiche",
    ["Ultra-court (post-it)", "Standard (fiche bac)", "Détaillé (type prof)"]
)

st.title("📚 IA Révisions Étudiant – MVP")
st.caption("Upload ton cours → Fiches + Flashcards + QCM en 1 clic.")

# ─────────────────────────────────────
# File parsers
# ─────────────────────────────────────
def extract_text_from_pdf(file) -> str:
    reader = PdfReader(file)
    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            pass
    return "\n".join(texts)

def extract_text_from_docx(file) -> str:
    # docx2txt expects a path; we handle BytesIO by saving temp
    data = file.read()
    tmp_path = "_tmp_upload.docx"
    with open(tmp_path, "wb") as f:
        f.write(data)
    text = docx2txt.process(tmp_path) or ""
    os.remove(tmp_path)
    return text

def extract_text_from_pptx(file) -> str:
    prs = Presentation(file)
    texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                texts.append(shape.text)
    return "\n".join(texts)

ALLOWED_TYPES = {
    "pdf": extract_text_from_pdf,
    "docx": extract_text_from_docx,
    "pptx": extract_text_from_pptx,
    "txt": lambda f: f.read().decode("utf-8", errors="ignore")
}

# ─────────────────────────────────────
# LLM prompts
# ─────────────────────────────────────
PROMPT_SUMMARY = (
    "Tu es un tuteur pédagogique. Fais une fiche de révision à partir du texte suivant. "
    "Propose 3 sections: 1) Points clés (bullet points), 2) Définitions essentielles, 3) Exemples/Application. "
    "Adapte la longueur au style demandé: {style}. \n\nTEXTE:\n{content}\n\nRéponds en Markdown propre."
)

PROMPT_FLASHCARDS = (
    "Génère des paires de flashcards (Question;Réponse) à partir du texte suivant. "
    "Questions courtes, réponses précises. Donne {n} paires. Sépare chaque paire sur une ligne via le séparateur ' | '. "
    "TEXTE:\n{content}"
)

PROMPT_QCM = (
    "Génère {n} QCM à partir du texte suivant. Pour chaque QCM, propose: \n"
    "- Énoncé \n- 4 options (A,B,C,D) \n- Indique la bonne réponse (A-D) et une brève justification.\n"
    "Format: \nQ: ...\nA) ...\nB) ...\nC) ...\nD) ...\nRéponse: X | Justification: ...\n---\n"
    "TEXTE:\n{content}"
)

# ─────────────────────────────────────
# LLM call (OpenAI style)
# ─────────────────────────────────────
def call_openai(prompt: str, temperature: float = 0.2) -> str:
    if not _HAS_OPENAI:
        raise RuntimeError("Le package openai n'est pas installé.")
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY absent. Ajoute-le dans Secrets.")
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": "Tu es un expert de la pédagogie claire."},
                      {"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"Erreur OpenAI: {e}")

# ─────────────────────────────────────
# Utils
# ─────────────────────────────────────
def normalize_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s or " ").strip()
    return s

def to_anki_csv(pairs: List[Tuple[str,str]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    for q, a in pairs:
        writer.writerow([q, a])
    return buf.getvalue().encode("utf-8")

# ─────────────────────────────────────
# Main UI blocks
# ─────────────────────────────────────
uploaded = st.file_uploader(
    "Téléverse tes cours (PDF/DOCX/PPTX/TXT)",
    type=list(ALLOWED_TYPES.keys()),
    accept_multiple_files=True
)

if uploaded:
    st.success(f"{len(uploaded)} fichier(s) uploadé(s).")

    all_texts = []
    for file in uploaded:
        ext = file.name.split(".")[-1].lower()
        parser = ALLOWED_TYPES.get(ext)
        if not parser:
            st.warning(f"Type non supporté: {file.name}")
            continue
        with st.spinner(f"Extraction du texte: {file.name}"):
            try:
                text = parser(file)
                text = normalize_text(text)
            except Exception as e:
                st.error(f"Erreur extraction {file.name}: {e}")
                text = ""
        if text:
            st.write(f"**Extrait ({file.name}) – 1ère page env.**")
            st.text(text[:800] + ("..." if len(text) > 800 else ""))
            all_texts.append(text)

    merged_text = "\n\n".join(all_texts)

    if merged_text.strip():
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📝 Générer Fiche(s)"):
                with st.spinner("Génération des fiches..."):
                    prompt = PROMPT_SUMMARY.format(style=summary_style, content=merged_text[:12000])
                    summary_md = call_openai(prompt)
                st.subheader("Fiche de révision")
                st.markdown(summary_md)
                st.download_button("Télécharger la fiche (MD)", summary_md.encode("utf-8"), file_name="fiche_revision.md")

        with col2:
            if st.button("🃏 Générer Flashcards"):
                with st.spinner("Génération des flashcards..."):
                    prompt = PROMPT_FLASHCARDS.format(n=max_flashcards, content=merged_text[:12000])
                    raw = call_openai(prompt)
                # Parse lines "Question | Réponse"
                pairs = []
                for line in raw.splitlines():
                    if "|" in line:
                        q, a = [t.strip(" -:") for t in line.split("|", 1)]
                        if q and a:
                            pairs.append((q, a))
                if not pairs:
                    st.warning("Aucune paire détectée. Vérifie le contenu du cours.")
                df = pd.DataFrame(pairs, columns=["Front (Question)", "Back (Réponse)"])
                st.dataframe(df, use_container_width=True)
                st.download_button(
                    "Télécharger Anki CSV",
                    to_anki_csv(pairs),
                    file_name="flashcards_anki.csv",
                    mime="text/csv"
                )

        with col3:
            if st.button("✅ Générer QCM"):
                with st.spinner("Génération des QCM..."):
                    prompt = PROMPT_QCM.format(n=max_qcm, content=merged_text[:12000])
                    qcm_text = call_openai(prompt)
                st.subheader("QCM")
                st.text(qcm_text)
                st.download_button("Télécharger QCM (TXT)", qcm_text.encode("utf-8"), file_name="qcm.txt")

    else:
        st.info("Upload un fichier pour commencer.")

# Footer
st.markdown("---")
st.caption("MVP pédagogique – généré avec Streamlit. Ajoute la détection des lacunes, le suivi progrès et l'OCR dans une v2.")
