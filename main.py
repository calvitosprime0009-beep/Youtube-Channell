"""
main.py — Un ciclo completo: aprender -> detectar moda -> guionizar -> voz ->
imágenes -> subtítulos -> montar -> subir -> recordar.

Se ejecuta solo desde GitHub Actions. Tú no tocas nada.
"""
import os, random, re, sys, tempfile, traceback

sys.path.insert(0, os.path.dirname(__file__))
import brain, trends, guion, medios, montaje

RAIZ = os.path.join(os.path.dirname(__file__), "..")
SALIDA = os.path.join(RAIZ, "salida")
MUSICA = os.path.join(RAIZ, "data", "musica.mp3")   # opcional


def tags_de(texto, tema):
    base = ["shorts", "curiosidades", "sabiasque", "datos", "viral",
            "aprender", "misterio"]
    extra = [w.lower() for w in re.findall(r"\b[A-Za-zÁÉÍÓÚÑáéíóúñ]{5,}\b", tema)]
    return list(dict.fromkeys(extra + base))


def main():
    os.makedirs(SALIDA, exist_ok=True)
    m = brain.cargar()

    # 1. APRENDER de lo ya publicado
    if os.getenv("YT_REFRESH_TOKEN"):
        try:
            import youtube
            ids = [p["video_id"] for p in m["publicados"] if not p["evaluado"]]
            m = brain.aprender(m, youtube.estadisticas(ids))
            print("[main] pesos:", {k: v["peso"] for k, v in m["formatos"].items()})
        except Exception as e:
            print("[main] aprendizaje omitido:", e)

    # 2. ACTUALIZARSE A LA MODA ACTUAL (una vez de cada cuatro ejecuciones)
    if random.random() < 0.25 and os.getenv("YT_API_KEY"):
        nuevos = trends.destilar_formatos(
            trends.titulos_top(os.environ["YT_API_KEY"]), guion.generar_texto)
        m = brain.inyectar_formatos(m, nuevos)

    # 3. TEMA + FORMATO
    tema = random.choice(trends.temas_del_dia())
    fid, plantilla = brain.elegir_formato(m)
    print(f"[main] tema='{tema}' formato='{fid}'")

    # 4. GUION
    g = guion.crear(tema, plantilla)
    print("[main] guion:", g["narracion"][:120], "...")

    tmp = tempfile.mkdtemp()
    audio = os.path.join(tmp, "voz.mp3")
    palabras, _ = medios.voz(g["narracion"], audio)

    imgs = []
    for i, esc in enumerate(g["escenas"]):
        p = os.path.join(tmp, f"img{i}.jpg")
        try:
            imgs.append(medios.imagen(esc, p))
        except Exception as e:
            print("[main] escena", i, "falló:", e)
    if not imgs:
        raise RuntimeError("Sin imágenes, se aborta")

    ass = medios.subtitulos(palabras, os.path.join(tmp, "subs.ass"))
    video = os.path.join(SALIDA, "short.mp4")
    montaje.render(imgs, audio, ass, video,
                   MUSICA if os.path.exists(MUSICA) else None)

    # 5. SUBIR
    if os.getenv("YT_REFRESH_TOKEN"):
        import youtube
        vid = youtube.subir(video, g["titulo"], g["descripcion"],
                            tags_de(g["narracion"], tema))
        brain.registrar(m, vid, fid, tema, g["titulo"])
    else:
        print("[main] sin credenciales de YouTube: vídeo generado pero no subido")

    brain.guardar(m)
    print("[main] ciclo completado")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
