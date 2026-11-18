# Xale Yi v3 – production automatique 2D

- `xale_v3_auto.yml` (lundi, mercredi, vendredi, dimanche 10h17) : fabrique le prochain épisode
  (l'écrit avec Gemini si la file `episodes/` est vide), le range dans une Release GitHub avec sa miniature
  et ses Shorts, puis publie le plus ancien épisode prêt sur YouTube.
- `xale_v3_shorts.yml` (8h41, 13h41, 18h41) : publie le prochain Short de la file.
- `xale_v3_check.yml` : vérifie l'accès YouTube.

`config.json` : `publish_youtube` passe à `true` une fois l'audit de l'API YouTube accepté
(avant, YouTube bloque en privé les vidéos envoyées par l'API). `max_built_waiting` limite la réserve d'épisodes prêts.

Secrets : `ELEVENLABS_API_KEY`, `GEMINI_API_KEY`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
