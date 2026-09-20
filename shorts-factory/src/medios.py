"""
medios.py — Voz, imágenes y subtítulos. Todo gratis.

VOZ: edge-tts (las voces neuronales de Microsoft, gratis e ilimitadas). Además nos
     devuelve el timestamp de CADA palabra, así que los subtítulos tipo karaoke
     salen perfectos sin usar Whisper ni gastar CPU.
IMAGEN: image.pollinations.ai (modelo Flux, gratis y sin clave, sin marca de agua).
"""
import asyncio, os, random, urllib.parse
import requests

VOCES = ["es-ES-AlvaroNeural", "es-ES-ElviraNeural",
         "es-MX-JorgeNeural", "es-ES-XimenaNeural"]
W, H = 1080, 1920


async def _tts(texto, voz, salida):
    import edge_tts
    com = edge_tts.Communicate(texto, voz, rate="+12%")  # +12% = ritmo de Shorts
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


def imagen(prompt, salida, seed=None):
    url = ("https://image.pollinations.ai/prompt/"
           + urllib.parse.quote(prompt[:900])
           + f"?width={W}&height={H}&model=flux&nologo=true&enhance=true"
           + f"&seed={seed or random.randint(1, 10**6)}")
    for intento in range(3):
        try:
            r = requests.get(url, timeout=180)
            if r.ok and len(r.content) > 20000:
                with open(salida, "wb") as f:
                    f.write(r.content)
                return salida
        except Exception as e:
            print(f"[medios] imagen intento {intento+1}:", e)
    raise RuntimeError("No se pudo generar la imagen")


def _esc(t):
    return t.replace("\\", "").replace("{", "").replace("}", "")


def _ts(s):
    s = max(0, s)
    h, r = divmod(s, 3600); m, sec = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{sec:05.2f}"


def subtitulos(palabras, salida, por_bloque=3):
    """Subtítulos grandes, centrados, 3 palabras por golpe. El algoritmo de
    Shorts LEE este texto en pantalla, así que también mejora el alcance."""
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
        # una palabra del bloque se resalta en amarillo: engancha la mirada
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
