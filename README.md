# Fábrica de Shorts — sistema autónomo y gratuito

Genera y sube 3 YouTube Shorts de ~30 s al día, solo, sin que toques nada, y
**aprende de sus propios resultados** para mejorar con el tiempo.

## Cómo funciona el ciclo (cada ejecución)

1. **Aprende** — lee las vistas reales de los Shorts que subió hace más de 48 h y
   sube o baja el peso del formato que usó en cada uno.
2. **Se actualiza a la moda** — de vez en cuando mira los vídeos más vistos de tu
   país, detecta qué patrones narrativos están triunfando y se **inventa formatos
   nuevos** que añade a su banco. Los formatos que rinden mal se eliminan solos.
3. **Elige** tema (Google Trends del día) y formato (bandit ε-greedy: 75 % explota
   lo que funciona, 25 % experimenta).
4. **Escribe** el guion, el título, la descripción y los prompts de imagen.
5. **Narra** con voz neuronal y **genera 4 imágenes verticales** con Flux.
6. **Monta**: 1080×1920, zoom Ken Burns, subtítulos karaoke palabra a palabra.
7. **Sube** a YouTube y **guarda en su memoria** qué hizo, para el paso 1 de mañana.

## Decisiones de diseño (y por qué)

| Decisión | Motivo |
|---|---|
| 28–32 s, cierre que enlaza con la apertura | la tasa de finalización es **la** señal del algoritmo de Shorts en 2026; el bucle infla la retención |
| Gancho de <10 palabras en el segundo 0 | la media de visionado ha caído a ~16 s: si no enganchas ya, no enganchas |
| Subtítulos quemados siempre | YouTube lee el texto en pantalla para clasificar el vídeo |
| Imagen fija + Ken Burns, no vídeo generado | vídeo por IA de calidad no es gratis; el zoom constante da sensación de movimiento sin coste |

## Coste

**0 €.** Texto e imágenes: Pollinations (sin clave). Voz: edge-tts. Servidor:
GitHub Actions (gratis ilimitado en repos públicos). Subida: cuota gratuita de la
YouTube Data API (~6 vídeos/día, usamos 3).

## Puesta en marcha (15 min, una sola vez)

1. Crea un repo **público** en GitHub y sube esta carpeta.
2. En [Google Cloud Console](https://console.cloud.google.com): crea un proyecto →
   habilita **YouTube Data API v3** → **Credenciales** → crea una *API key* y un
   *ID de cliente OAuth* de tipo **Aplicación de escritorio**.
   En *Pantalla de consentimiento* añade tu correo como **usuario de prueba**.
3. En tu PC: `pip install google-auth-oauthlib && python obtener_token.py`
4. En el repo → **Settings → Secrets and variables → Actions**, añade:
   - `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, `YT_API_KEY`
   - *(opcional)* `GROQ_API_KEY` y `GEMINI_API_KEY` como red de seguridad del texto
5. Pestaña **Actions → Fábrica de Shorts → Run workflow**. Mira el primer vídeo.
6. Si te gusta, no hagas nada más. Ya está funcionando solo.

> Empieza con `PRIVACIDAD: unlisted` en `.github/workflows/shorts.yml` para revisar
> los primeros 3 o 4 vídeos, y cámbialo a `public` cuando estés conforme.

## Ajustes rápidos

- **Más o menos vídeos al día**: cambia las horas del `cron`.
- **Otro país/idioma**: variable `PAIS` en el workflow.
- **Música de fondo**: pon un `musica.mp3` libre de derechos en `data/`; se mezcla
  solo al 11 % de volumen. Sin archivo, el vídeo va solo con voz.
- **Otra temática**: edita `TEMAS_RESPALDO` en `src/trends.py`.
