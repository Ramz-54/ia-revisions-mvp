# IA Révisions Étudiant – MVP (Streamlit)

Prototype pour transformer des cours en **fiches**, **flashcards** (Anki CSV) et **QCM**.
- **Frontend**: Streamlit
- **LLM**: OpenAI (Chat Completions) – modèle par défaut `gpt-4o-mini`
- **Parsing**: PDF/DOCX/PPTX/TXT

## Lancer en local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...  # Windows: set OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-4o-mini
streamlit run app.py
```

## Déployer sur Streamlit Community Cloud
1. Pousse ce dossier sur un repo GitHub (public pour la démo).
2. Va sur https://streamlit.io/cloud → **New app** → choisis ton repo, branche, et `app.py`.
3. Dans **Settings → Secrets**, colle :
```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
```
4. **Deploy**. Ouvre l’URL et teste avec `sample/chapitre_exemple.txt`.

> En dev local, tu peux aussi créer `.streamlit/secrets.toml` avec le contenu ci-dessus,
> mais **ne le pousse jamais** sur GitHub.
