"""
montaje.py — Une todo con ffmpeg en un MP4 vertical 1080x1920 listo para Shorts.
Efecto Ken Burns (zoom lento) en cada imagen para que no parezca una diapositiva
muerta: el movimiento constante es lo que sostiene la retención.
"""
import json, os, subprocess

W, H, FPS = 1080, 1920, 30


def duracion(path):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                          "-show_format", path], capture_output=True, text=True)
    return float(json.loads(out.stdout)["format"]["duration"])


def render(imagenes, audio, ass, salida, musica=None):
    dur = duracion(audio)
    n = len(imagenes)
    trozo = dur / n
    frames = max(1, int(trozo * FPS))

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
        # zoom alterno dentro/fuera para que dos escenas seguidas no se parezcan
        z = (f"zoompan=z='min(zoom+0.0013,1.22)'" if i % 2 == 0
             else f"zoompan=z='if(lte(zoom,1.0),1.22,max(1.001,zoom-0.0013))'")
        f.append(
            f"[{i}:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
            f"crop={W*2}:{H*2},{z}:d={frames}:s={W}x{H}:fps={FPS},"
            f"setsar=1,format=yuv420p[v{i}]")
    f.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[base]")
    f.append(f"[base]subtitles='{ass}'[vout]")

    if idx_mus is not None:
        f.append(f"[{idx_mus}:a]volume=0.11,afade=t=out:st={dur-1.2:.2f}:d=1.2[mus]")
        f.append(f"[{n}:a]volume=1.6,aformat=sample_fmts=fltp:sample_rates=44100:"
                 "channel_layouts=stereo[vz]")
        f.append("[vz][mus]amix=inputs=2:duration=first:dropout_transition=0[aout]")
        mapa_a = "[aout]"
    else:
        f.append(f"[{n}:a]volume=1.6[aout]")
        mapa_a = "[aout]"

    cmd += ["-filter_complex", ";".join(f),
            "-map", "[vout]", "-map", mapa_a,
            "-c:v", "libx264", "-preset", "medium", "-crf", "21",
            "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
            "-t", f"{dur:.3f}", "-movflags", "+faststart", salida]
    subprocess.run(cmd, check=True)
    print(f"[montaje] listo: {salida} ({dur:.1f}s)")
    return salida
