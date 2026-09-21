"""
guion.py — Texto gratis. Cadena de fallbacks (Groq como principal):
    1) Groq free tier (principal) — modelo openai/gpt-oss-20b
    2) Pollinations (gratis, sin clave, pero inestable: solo red de seguridad)
    3) Banco de guiones local (NUNCA falla: garantiza que siempre sale un vídeo)
"""
import json, os, re, random, requests

GROQ = "https://api.groq.com/openai/v1/chat/completions"
POLLI = "https://text.pollinations.ai/openai"

# Groq retiró llama-3.1-8b-instant y llama-3.3-70b-versatile el 16-ago-2026.
# Su reemplazo oficial recomendado es gpt-oss-20b (rápido) / gpt-oss-120b (más listo).
MODELO_GROQ = "openai/gpt-oss-20b"

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

    # 1) Groq (principal)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            d = _post(GROQ, {"model": MODELO_GROQ, "messages": msgs},
                      {"Authorization": f"Bearer {groq_key}"})
            print("[guion] Groq OK")
            return d["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("[guion] groq falló:", e)
    else:
        print("[guion] GROQ_API_KEY no está definida")

    # 2) Pollinations (respaldo, gratis y sin clave — pero cae a ratos)
    try:
        d = _post(POLLI, {"model": "openai", "messages": msgs, "seed": random.randint(1, 10**6)})
        print("[guion] Pollinations OK")
        return d["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("[guion] pollinations falló:", e)

    # 3) sin proveedor disponible: que decida el que llama (crear() usa el banco local)
    raise RuntimeError("Ningún proveedor de texto disponible")


def limpiar(t):
    t = re.sub(r"[*_#`>]", "", t)
    t = re.sub(r"^\s*(guion|guión|narración|texto)\s*:\s*", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    palabras = t.split()
    return " ".join(palabras[:95])            # techo duro para no pasar de 32s


# ------------------------------------------------------- red de seguridad final
# Si Groq Y Pollinations fallan a la vez, el canal NO se para: usa esto y sube igual.
BANCO = [
    "Esto que estás viendo no debería existir. {tema} esconde algo que la mayoría "
    "de la gente jamás llega a saber. Durante años se dio por imposible. Hoy "
    "sabemos que estábamos equivocados en casi todo. Y lo más inquietante no es "
    "el descubrimiento. Es cuánto tiempo lo tuvimos delante sin verlo. Por eso "
    "esto que estás viendo no debería existir.",
    "Nadie te contó esto sobre {tema}. Y cuando lo entiendas, no vas a poder "
    "dejar de verlo en todas partes. Empieza con algo pequeño, casi ridículo. "
    "Luego escala. Y al final cambia por completo la forma en que miras algo que "
    "tienes delante cada día. Por eso nadie te contó esto sobre {tema}.",
    "Tres cosas sobre {tema} que parecen mentira. La tercera es la que de verdad "
    "importa. La primera te sorprende. La segunda te incomoda. La tercera te "
    "obliga a replanteártelo todo. Y ninguna de las tres es un truco. Todas están "
    "documentadas. Por eso son tres cosas que parecen mentira.",
]


def _respaldo(tema):
    print("[guion] AVISO: usando el banco local de guiones (Groq y Pollinations fallaron)")
    return random.choice(BANCO).format(tema=tema)


def crear(tema, plantilla):
    try:
        narracion = limpiar(generar_texto(plantilla.format(tema=tema)))
        if len(narracion.split()) < 20:
            raise ValueError("guion demasiado corto")
    except Exception as e:
        print("[guion] generación fallida:", e)
        narracion = limpiar(_respaldo(tema))

    meta_prompt = (
        f"Para este guion de Short:\n\"{narracion}\"\n\n"
        "Devuelve SOLO JSON válido sin markdown:\n"
        '{"titulo":"título de máximo 60 caracteres, con gancho, sin comillas",'
        '"descripcion":"2 frases + 5 hashtags relevantes",'
        '"escenas":["prompt en INGLÉS para imagen vertical cinematográfica 1",'
        '"prompt 2","prompt 3","prompt 4"]}'
    )
    meta = {}
    try:
        raw = generar_texto(meta_prompt, "Devuelves únicamente JSON válido.")
        raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.M).strip()
        meta = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    except Exception as e:
        print("[guion] meta falló, uso respaldo:", e)

    titulo = (meta.get("titulo") or f"{tema.capitalize()} como nunca te lo contaron")[:95]
    desc = meta.get("descripcion") or f"{narracion[:120]}...\n\n#shorts #curiosidades #datos #viral #sabiasque"
    escenas = [e for e in (meta.get("escenas") or []) if isinstance(e, str) and e.strip()]
    while len(escenas) < 4:
        escenas.append(f"cinematic vertical photo about {tema}, dramatic lighting, "
                       f"ultra detailed, 9:16, shot {len(escenas)+1}")
    if "#shorts" not in desc.lower():
        desc += "\n\n#shorts #curiosidades #viral"

    return {
        "narracion": narracion,
        "titulo": titulo,
        "descripcion": desc,
        "escenas": escenas[:4]
    }
