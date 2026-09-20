"""
Ejecuta esto UNA SOLA VEZ en tu ordenador. Te abre el navegador, inicias sesión
con la cuenta de tu canal, y te imprime el YT_REFRESH_TOKEN.
Copia ese token a los Secrets de GitHub y ya no vuelves a tocar nada nunca más.

    pip install google-auth-oauthlib
    python obtener_token.py
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]

CLIENT_ID = input("Pega tu Client ID: ").strip()
CLIENT_SECRET = input("Pega tu Client Secret: ").strip()

flow = InstalledAppFlow.from_client_config(
    {"installed": {"client_id": CLIENT_ID,
                   "client_secret": CLIENT_SECRET,
                   "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                   "token_uri": "https://oauth2.googleapis.com/token",
                   "redirect_uris": ["http://localhost"]}},
    SCOPES)

cred = flow.run_local_server(port=0, prompt="consent", access_type="offline")

print("\n" + "=" * 60)
print("YT_REFRESH_TOKEN =", cred.refresh_token)
print("=" * 60)
print("Guárdalo en GitHub > Settings > Secrets and variables > Actions")
