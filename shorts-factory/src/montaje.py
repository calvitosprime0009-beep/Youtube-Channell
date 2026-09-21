"""
montaje.py — Une todo con ffmpeg en un MP4 vertical 1080x1920.

Cambios frente a la versión anterior:
  - 6 movimientos de camara distintos que se van alternando (zoom in, zoom out,
    paneo izquierda-derecha, derecha-izquierda, diagonal en ambas direcciones),
    en vez de un solo zoom repetido en todas las escenas.
  - Transiciones tipo cine entre escenas (fundidos, barridos) en vez de cortes
    secos, usando xfade.
  - Grano de pelicula sutil + vineteado + un pelin mas de contraste/saturacion
    para que no se vea plano.
"""
import json, os, subprocess

W, H, FPS = 1080, 1920, 30
TRANSICION = 0.55                 # segundos que dura cada fundido entre escenas

EFECTOS = ["zoom_in", "zoom_out", "pan_lr", "pan_rl", "pan_tlbr", "pan_brtl"]
TRANSICIONES = ["fade", "wiperight", "wipeleft", "slideleft", "slideright", "circleopen"]
ZOOM_MAX = 1.30
ZOOM_PAN = 1.18                   # zoom fijo durante los paneos, deja margen para moverse


def duracion(path):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                          "-show_format", path], capture_output=True, text=True)
    return float(json.loads(out.stdout)["format"]["duration"])


def _filtro_escena(i, frames, efecto):
    """Devuelve la expresión zoompan (z, x, y) para el movimiento de camara i."""
    if efecto == "zoom_in":
        ritmo = (ZOOM_MAX - 1) / frames
        z = f"min(zoom+{ritmo:.6f},{ZOOM_MAX})"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif efecto == "zoom_out":
        ritmo = (ZOOM_MAX - 1) / frames
        z = f"if(lte(zoom,1.0),{ZOOM_MAX},max(1.001,zoom-{ritmo:.6f}))"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif efecto == "pan_lr":
        z = f"{ZOOM_PAN}"
        x = f"(iw-iw/zoom)*on/{max(frames-1,1)}"
        y = "ih/2-(ih/zoom/2)"
    elif efecto == "pan_rl":
        z = f"{ZOOM_PAN}"
        x = f"(iw-iw/zoom)*(1-on/{max(frames-1,1)})"
        y = "ih/2-(ih/zoom/2)"
    elif efecto == "pan_tlbr":
        z = f"{ZOOM_PAN}"
        x = f"(iw-iw/zoom)*on/{max(frames-1,1)}"
        y = f"(ih-ih/zoom)*on/{max(frames-1,1)}"
    else:  # pan_brtl
        z = f"{ZOOM_PAN}"
        x = f"(iw-iw/zoom)*(1-on/{max(frames-1,1)})"
        y = f"(ih-ih/zoom)*(1-on/{max(frames-1,1)})"
    return z, x, y


def render(imagenes, audio, ass, salida, musica=None):
    dur = duracion(audio)
    n = len(imagenes)
    # con transiciones solapadas, cada escena tiene que durar un poco mas para
    # que al final la duracion total siga cuadrando con el audio
    trozo = (dur + (n - 1) * TRANSICION) / n if n > 1 else dur
    frames = max(2, int(trozo * FPS))

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for img in imagenes:
        cmd += ["-loop", "1", "-t", f"{trozo:.3f}", "-i", img]
    cmd += ["-i", audio]
    idx_mus = None
    if musica and os.path.exists(musica):
        cmd += ["-i", musica]
        idx_mus = n + 1

    f = []
    for i in range(n):
        efecto = EFECTOS[i % len(EFECTOS)]
        z, x, y = _filtro_escena(i, frames, efecto)
        f.append(
            f"[{i}:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
            f"crop={W*2}:{H*2},"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},"
            f"format=yuv420p,setsar=1[v{i}]")

    # encadenar las escenas con transiciones tipo cine en vez de un corte seco
    prev = "v0"
    if n == 1:
        prev = "v0"
    else:
        for i in range(1, n):
            transicion = TRANSICIONES[(i - 1) % len(TRANSICIONES)]
            offset = i * (trozo - TRANSICION)
            nuevo = f"x{i}"
            f.append(f"[{prev}][v{i}]xfade=transition={transicion}:"
                     f"duration={TRANSICION:.3f}:offset={offset:.3f}[{nuevo}]")
            prev = nuevo

    # un toque de cine: mas contraste/saturacion, vineteado y grano sutil
    f.append(f"[{prev}]eq=contrast=1.06:saturation=1.10,vignette=PI/5,"
             f"noise=alls=8:allf=t+u[graded]")
    f.append(f"[graded]subtitles='{ass}'[vout]")

    if idx_mus is not None:
        f.append(f"[{idx_mus}:a]volume=0.11,afade=t=out:st={dur-1.2:.2f}:d=1.2[mus]")
        f.append(f"[{n}:a]volume=1.6,aformat=sample_fmts=fltp:sample_rates=44100:"
                 "channel_layouts=stereo[vz]")
        f.append("[vz][mus]amix=inputs=2:duration=first:dropout_transition=0[aout]")
    else:
        f.append(f"[{n}:a]volume=1.6[aout]")

    cmd += ["-filter_complex", ";".join(f),
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "21",
            "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
            "-t", f"{dur:.3f}", "-movflags", "+faststart", salida]
    subprocess.run(cmd, check=True)
    print(f"[montaje] listo: {salida} ({dur:.1f}s, {n} escenas)")
    return salida
