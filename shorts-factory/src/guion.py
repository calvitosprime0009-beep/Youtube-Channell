"""
guion.py — Texto gratis. Cadena de fallbacks (Groq como principal):
    1) Groq free tier (principal)
    2) Pollinations (gratis, sin clave)
    3) Banco de guiones local
"""
import json, os, re, random, requests

GROQ = "https://api.groq.com/openai/v1/chat/completions"
POLLI = "https://text.pollinations.ai/openai"

SISTEMA = (
    "Eres guionista de YouTube Shorts en español. Escribes para que NADIE deslice. "
    "Reglas innegociables: la primera frase es un gancho brutal de menos de 10 palabras; "
    "frases cortas, habladas, cero relleno; nada de saludos ni despedidas; "
    "la última frase enlaza con la primera para que el vídeo haga bucle perfecto. "
    "Duración objetivo al leerlo en alto: 28-32 segundos (unas 75-90 palabras)."
)


def _post(url, payload, headers=None, timeout=60):
    r = requests.post(url, json=payload, headers=headers or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def generar_texto(prompt, sistema=SISTEMA):
    msgs = [{"role": "system", "content": sistema}, {"role": "user", "content": prompt}]
    
    # 1) Groq (Principal)
    if os.getenv("GROQ_API_KEY"):
        try:
            d = _post(GROQ, {"model": "llama-3.3-70b-versatile", "messages": msgs},
                      {"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"})
            return d["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("[guion] groq falló:", e)

    # 2) Pollinations (Respaldo — gratis y sin clave)
    try:
        d = _post(POLLI, {"model": "openai", "messages": msgs, "seed": random.randint(1, 10**6)})
        return d["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("[guion] pollinations falló:", e)
            
    raise RuntimeError("Ningún proveedor de texto disponible")


def limpiar(t):
    t = re.sub(r"[*_#`>]", "", t)
    t = re.sub(r"^\s*(guion|narración|texto)\s*:\s*", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    palabras = t.split()
    return " ".join(palabras[:95])            # techo duro para no pasar de 32s


def crear(tema, plantilla):
    narracion = limpiar(generar_texto(plantilla.format(tema=tema)))
    meta_prompt = (
        f"Para este guion de Short:\n\"{narracion}\"\n\n"
        "Devuelve SOLO JSON válido sin markdown:\n"
        '{"titulo":"título de máximo 60 caracteres, con gancho, sin comillas",'
        '"descripcion":"2 frases + 5 hashtags relevantes",'
        '"escenas":["prompt en INGLÉS para imagen vertical cinematográfica 1",'
        '"prompt 2","prompt 3","prompt 4"]}'
    )
    try:
        raw = generar_texto(meta_prompt, "Devuelves únicamente JSON válido.")
        raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.M).strip()
        meta = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    except Exception as e:
        print("[guion] meta falló, uso respaldo:", e)
        meta = {}
        
    titulo = (meta.get("titulo") or f"{tema.capitalize()} como nunca te lo contaron")[:95]
    desc = meta.get("descripcion") or f"{narracion[:120]}...\n\n#shorts #curiosidades #datos #viral #sabiasque"
    escenas = meta.get("escenas") or []
    
    if len(escenas) < 4:
        escenas += [f"cinematic vertical photo about {tema}, dramatic lighting, "
                    f"ultra detailed, 9:16"] * (4 - len(escenas))
                    
    if "#shorts" not in desc.lower():
        desc += "\n\n#shorts #curiosidades #viral"
        
    return {
        "narracion": narracion, 
        "titulo": titulo,
        "descripcion": desc, 
        "escenas": escenas[:4]
    }
