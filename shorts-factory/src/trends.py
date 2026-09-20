"""
trends.py — Detecta qué se está viendo AHORA. Todo gratis, sin claves de pago.

Fuentes:
 1. Google Trends RSS diario (gratis, sin API key) -> temas calientes del día.
 2. YouTube Data API videos.list chart=mostPopular (cuota gratuita) -> qué títulos
    están petando en Shorts en tu país. De ahí se destilan formatos nuevos.

Así el canal se "actualiza solo a las nuevas modas": los temas cambian cada día y
los formatos se regeneran cada semana a partir de los títulos reales que triunfan.
"""
import os, re, random, html
import requests

PAIS = os.getenv("PAIS", "ES")
IDIOMA = os.getenv("IDIOMA", "es")

TEMAS_RESPALDO = [
    "el espacio profundo", "el fondo del océano", "el cuerpo humano",
    "animales extremos", "la historia que no te contaron", "física cuántica",
    "el cerebro", "inteligencia artificial", "civilizaciones perdidas",
    "récords imposibles", "misterios sin resolver", "el dinero y el poder",
]


def temas_del_dia(n=6):
    temas = []
    try:
        r = requests.get(
            f"https://trends.google.com/trending/rss?geo={PAIS}", timeout=20)
        if r.ok:
            temas = [html.unescape(t) for t in
                     re.findall(r"<title>(?!Daily Search Trends)(.*?)</title>", r.text)]
            temas = [t.strip() for t in temas if 3 < len(t.strip()) < 60]
    except Exception as e:
        print("[trends] Google Trends no disponible:", e)
    # Los trends puros suelen ser fútbol/famosos: los mezclamos con temas
    # evergreen para que el canal tenga identidad y no sea ruido.
    pool = temas[:10] + TEMAS_RESPALDO
    random.shuffle(pool)
    return pool[:n]


def titulos_top(api_key, n=30):
    """Títulos de los videos más vistos ahora mismo en tu país."""
    try:
        r = requests.get("https://www.googleapis.com/youtube/v3/videos", timeout=20,
                         params={"part": "snippet", "chart": "mostPopular",
                                 "regionCode": PAIS, "maxResults": min(n, 50),
                                 "key": api_key})
        return [i["snippet"]["title"] for i in r.json().get("items", [])]
    except Exception as e:
        print("[trends] mostPopular falló:", e)
        return []


def destilar_formatos(titulos, generar_texto):
    """Le pide a la IA que mire los títulos que triunfan y proponga 2 formatos
    nuevos de guion. Esto es lo que hace que el sistema no se quede anticuado."""
    if not titulos:
        return []
    prompt = (
        "Estos son títulos de vídeos que ahora mismo están arrasando en YouTube:\n- "
        + "\n- ".join(titulos[:25])
        + "\n\nDetecta 2 PATRONES o formatos narrativos que se repitan y que funcionen "
          "en un Short vertical de 30 segundos. Devuelve SOLO un JSON válido, sin "
          "markdown, con esta forma exacta:\n"
          '[{"id":"nombre_corto_sin_espacios","plantilla":"instrucción para escribir '
          'un guion de 30s sobre {tema} siguiendo ese patrón"}]'
    )
    try:
        import json
        txt = generar_texto(prompt)
        txt = re.sub(r"^```(json)?|```$", "", txt.strip(), flags=re.M).strip()
        datos = json.loads(txt[txt.index("["):txt.rindex("]") + 1])
        out = []
        for d in datos[:2]:
            fid = re.sub(r"\W+", "_", str(d.get("id", ""))).strip("_").lower()[:40]
            if fid and "{tema}" in str(d.get("plantilla", "")):
                out.append({"id": fid, "plantilla": d["plantilla"]})
        print("[trends] formatos nuevos descubiertos:", [o["id"] for o in out])
        return out
    except Exception as e:
        print("[trends] no se pudieron destilar formatos:", e)
        return []
