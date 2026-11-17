# Xale Yi v3 – production automatique 2D

Chaque mardi et vendredi, `.github/workflows/xale_v3_auto.yml` :
1. prend le prochain épisode de `episodes/` non publié (sinon l'écrit avec Gemini, `write_episode.py`) ;
2. génère les voix, la chanson et les bruitages avec ElevenLabs (`make_audio.py`) ;
3. monte l'épisode, le Short vertical et la miniature (`render.py`, moteur `engine.py`) ;
4. publie sur YouTube (`publish.py`) et note l'avancement dans `state/published.json`.

Secrets GitHub : `ELEVENLABS_API_KEY`, `GEMINI_API_KEY`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
Lancement manuel : onglet Actions → « Xale Yi v3 » → Run workflow (publish = 0 pour un essai sans publication).
Personnages, voix et décors : `series.py` et `assets/`. Plan de saison : `season.md`.
