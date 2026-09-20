"""
youtube.py — Subida automática con la YouTube Data API v3 (gratis, 10.000 unidades
de cuota al día ≈ 6 subidas diarias) y lectura de estadísticas para el aprendizaje.

Usa un refresh_token de OAuth guardado como secreto, así no hace falta que tú
estés delante nunca más.
"""
import os, requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def _cred():
    return Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.readonly"])


def subir(ruta, titulo, descripcion, tags):
    yt = build("youtube", "v3", credentials=_cred(), cache_discovery=False)
    cuerpo = {"snippet": {"title": titulo[:95], "description": descripcion[:4900],
                          "tags": tags[:15], "categoryId": "27"},
              "status": {"privacyStatus": os.getenv("PRIVACIDAD", "public"),
                         "selfDeclaredMadeForKids": False}}
    pet = yt.videos().insert(part="snippet,status", body=cuerpo,
                             media_body=MediaFileUpload(ruta, chunksize=-1,
                                                        resumable=True))
    resp = None
    while resp is None:
        _, resp = pet.next_chunk()
    vid = resp["id"]
    print(f"[youtube] subido: https://youtube.com/shorts/{vid}")
    return vid


def estadisticas(ids):
    """Vistas reales de los vídeos ya publicados -> alimenta a brain.aprender()."""
    if not ids:
        return {}
    yt = build("youtube", "v3", credentials=_cred(), cache_discovery=False)
    out = {}
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="statistics", id=",".join(ids[i:i + 50])).execute()
        for it in r.get("items", []):
            out[it["id"]] = int(it["statistics"].get("viewCount", 0))
    return out
