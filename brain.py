"""
brain.py — El cerebro que se actualiza solo.

Mantiene un "banco de formatos" con un peso por cada uno. Cada vez que se sube un
video, se guarda qué formato se usó. Al día siguiente el sistema lee las
estadísticas reales de YouTube y sube o baja el peso de ese formato.
Además descubre formatos NUEVOS leyendo los Shorts que más están petando ahora
mismo (trends.py) y los añade al banco automáticamente.

Algoritmo: epsilon-greedy. 80% del tiempo explota lo que mejor funciona,
20% del tiempo explora algo nuevo. Así nunca se queda estancado en una moda muerta.
"""
import json, os, random, time

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
MEM = os.path.join(DATA, "memory.json")
EPSILON = 0.25  # % de exploración

# Formatos semilla. Basados en lo que funciona en Shorts a día de hoy:
# 15-30s, gancho en el segundo 0, loop perfecto, texto en pantalla siempre.
SEED = [
    {"id": "dato_impactante",  "plantilla": "Un dato que no te esperas sobre {tema}. Empieza con la afirmación más increíble, luego explícala en 3 frases cortas, y termina con una frase que conecte con el principio para que el video haga loop."},
    {"id": "top3_rapido",      "plantilla": "Cuenta atrás de 3 cosas brutales sobre {tema}, de menos a más impactante. Frases de máximo 8 palabras. La número 1 tiene que dejar al espectador con la boca abierta."},
    {"id": "mito_vs_realidad", "plantilla": "Desmonta una creencia falsa muy extendida sobre {tema}. Formato: 'Todo el mundo cree X... pero la verdad es Y'. Termina con el dato que lo prueba."},
    {"id": "pregunta_gancho",  "plantilla": "Abre con una pregunta imposible sobre {tema} que obligue a quedarse a ver la respuesta. Da la respuesta en el segundo 20. Cierra repitiendo la pregunta para el loop."},
    {"id": "si_pasara_esto",   "plantilla": "Escenario hipotético sobre {tema}: '¿Qué pasaría si...?'. Describe las consecuencias en escalada, de lo pequeño a lo catastrófico."},
    {"id": "no_sabias_que",    "plantilla": "Encadena 4 microdatos sobre {tema}, cada uno más raro que el anterior, separados por 'pero espera'. Ritmo muy rápido."},
]


def cargar():
    if os.path.exists(MEM):
        with open(MEM, encoding="utf-8") as f:
            return json.load(f)
    return {"formatos": {s["id"]: {"peso": 1.0, "plantilla": s["plantilla"],
                                   "usos": 0, "vistas_totales": 0} for s in SEED},
            "publicados": [], "actualizado": 0}


def guardar(m):
    m["actualizado"] = int(time.time())
    os.makedirs(DATA, exist_ok=True)
    with open(MEM, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)


def elegir_formato(m):
    fmts = m["formatos"]
    if random.random() < EPSILON:
        fid = random.choice(list(fmts))          # explorar
    else:
        fid = max(fmts, key=lambda k: fmts[k]["peso"])  # explotar
    return fid, fmts[fid]["plantilla"]


def registrar(m, video_id, formato, tema, titulo):
    m["publicados"].append({"video_id": video_id, "formato": formato,
                            "tema": tema, "titulo": titulo,
                            "ts": int(time.time()), "evaluado": False})
    m["formatos"][formato]["usos"] += 1


def aprender(m, stats):
    """stats = {video_id: vistas}. Recalcula pesos con el rendimiento real."""
    for p in m["publicados"]:
        if p["evaluado"] or p["video_id"] not in stats:
            continue
        if time.time() - p["ts"] < 48 * 3600:   # dar 48h de margen al algoritmo
            continue
        v = stats[p["video_id"]]
        f = m["formatos"].get(p["formato"])
        if not f:
            continue
        f["vistas_totales"] += v
        media = max(1, sum(x["vistas_totales"] for x in m["formatos"].values()) /
                    max(1, sum(x["usos"] for x in m["formatos"].values())))
        # peso sube si el video rinde por encima de la media del canal
        f["peso"] = round(max(0.05, f["peso"] * 0.7 + (v / media) * 0.3), 4)
        p["evaluado"] = True
    # poda: formatos muertos se eliminan para dejar sitio a los nuevos
    for fid in [k for k, v in m["formatos"].items()
                if v["usos"] >= 5 and v["peso"] < 0.15 and len(m["formatos"]) > 4]:
        del m["formatos"][fid]
    return m


def inyectar_formatos(m, nuevos):
    """Añade formatos descubiertos de las tendencias actuales, con peso medio."""
    if not m["formatos"]:
        return m
    medio = sum(v["peso"] for v in m["formatos"].values()) / len(m["formatos"])
    for n in nuevos:
        if n["id"] not in m["formatos"]:
            m["formatos"][n["id"]] = {"peso": round(medio, 4), "plantilla": n["plantilla"],
                                      "usos": 0, "vistas_totales": 0}
    return m
