"""
medios.py — Voz, imágenes y subtítulos. Todo gratis.

VOZ: edge-tts (voces neuronales de Microsoft, gratis e ilimitadas), con timestamp
     de cada palabra para los subtítulos karaoke.
IMAGEN: dos proveedores gratis, en cascada, con infraestructuras distintas para
     que si uno se cae el otro siga funcionando:
     1) Hugging Face (modelo FLUX.1-schnell) — principal
     2) Pollinations — respaldo, sin clave
"""
import asyncio, os, random, time, urllib.parse
import requests

VOCES = ["es-ES-AlvaroNeural", "es-ES-ElviraNeural",
         "es-MX-JorgeNeural", "es-ES-XimenaNeural"]
W, H = 1080, 1920

HF_MODELO = "black-forest-labs/FLUX.1-schnell"
HF_URL = f"https://api-inference.huggingface.co/models/{HF_MODELO}"


async def _tts(texto, voz, salida):
    import edge_tts
    com = edge_tts.Communicate(texto, voz, rate="+12%")
    palabras = []
    with open(salida, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                palabras.append({"t": ch["offset"] / 1e7, "d": ch["duration"] / 1e7,
                                 "w": ch["text"]})
    return palabras


def voz(texto, salida, voz_fija=None):
    v = voz_fija or random.choice(VOCES)
    print(f"[medios] voz: {v}")
    return asyncio.run(_tts(texto, v, salida)), v


def _imagen_huggingface(prompt, salida):
    clave = os.getenv("HF_API_KEY")
    if not clave:
        raise RuntimeError("sin HF_API_KEY")
    headers = {"Authorization": f"Bearer {clave}"}
    payload = {"inputs": prompt[:900],
              "parameters": {"width": W, "height": H, "num_inference_steps": 4}}
    for intento in range(4):
        r = requests.post(HF_URL, headers=headers, json=payload, timeout=60)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            with open(salida, "wb") as f:
                f.write(r.content)
            return salida
        if r.status_code == 503:          # modelo "despertando", hay que esperar
            espera = min(20, r.json().get("estimated_time", 8) if r.content else 8)
            print(f"[medios] HF cargando el modelo, espero {espera:.0f}s...")
            time.sleep(espera)
            continue
        raise RuntimeError(f"HF respondio {r.status_code}: {r.text[:200]}")
    raise RuntimeError("HF no arranco a tiempo")


def _imagen_pollinations(prompt, salida, seed=None):
    url = ("https://image.pollinations.ai/prompt/"
           + urllib.parse.quote(prompt[:900])
           + f"?width={W}&height={H}&model=flux&nologo=true&enhance=true"
           + f"&seed={seed or random.randint(1, 10**6)}")
    r = requests.get(url, timeout=180)
    if r.ok and len(r.content) > 20000:
        with open(salida, "wb") as f:
            f.write(r.content)
        return salida
    raise RuntimeError(f"Pollinations respondio {r.status_code}")


_PALETAS = [
    ("0f2027", "203a43", "2c5364"), ("360033", "0b8793", "0b8793"),
    ("1e130c", "9a8478", "1e130c"), ("232526", "414345", "232526"),
    ("0f0c29", "302b63", "24243e"), ("134e5e", "71b280", "134e5e"),
]


def _imagen_banco_local(salida):
    """Ultimo recurso: un fondo con degradado hecho con ffmpeg, sin depender de
    ninguna API. Nunca falla, asi que el video siempre se llega a generar."""
    import subprocess
    c1, c2, c3 = random.choice(_PALETAS)
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i",
        f"gradients=s={W}x{H}:c0=0x{c1}:c1=0x{c2}:x0={random.randint(0,W)}:"
        f"y0={random.randint(0,H)}:x1={random.randint(0,W)}:y1={random.randint(0,H)}",
        "-frames:v", "1", salida], check=True)
    print("[medios] AVISO: usando imagen de emergencia (degradado local)")
    return salida


def imagen(prompt, salida, seed=None):
    # 1) Hugging Face (principal)
    try:
        return _imagen_huggingface(prompt, salida)
    except Exception as e:
        print("[medios] Hugging Face fallo:", e)

    # 2) Pollinations (respaldo, infraestructura distinta)
    for intento in range(2):
        try:
            return _imagen_pollinations(prompt, salida, seed)
        except Exception as e:
            print(f"[medios] Pollinations intento {intento+1} fallo:", e)

    # 3) banco local: nunca falla, así el vídeo se genera siempre
    return _imagen_banco_local(salida)


def _esc(t):
    return t.replace("\\", "").replace("{", "").replace("}", "")


def _ts(s):
    s = max(0, s)
    h, r = divmod(s, 3600); m, sec = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{sec:05.2f}"


def subtitulos(palabras, salida, por_bloque=3):
    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: P,Arial Black,108,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,9,4,5,80,80,0,1
Style: A,Arial Black,116,&H0000E5FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,9,4,5,80,80,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    lineas = []
    for i in range(0, len(palabras), por_bloque):
        grupo = palabras[i:i + por_bloque]
        ini = grupo[0]["t"]
        fin = grupo[-1]["t"] + grupo[-1]["d"] + 0.06
        destacada = max(range(len(grupo)), key=lambda k: len(grupo[k]["w"]))
        txt = " ".join(
            (r"{\c&H0000E5FF&\fscx112\fscy112}" + _esc(g["w"]) + r"{\r}")
            if j == destacada else _esc(g["w"])
            for j, g in enumerate(grupo))
        lineas.append(f"Dialogue: 0,{_ts(ini)},{_ts(fin)},P,,0,0,0,"
                      r",{\fad(60,60)}" + txt)
    with open(salida, "w", encoding="utf-8") as f:
        f.write(cab + "\n".join(lineas) + "\n")
    return salida
