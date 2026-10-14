"""Hojas de sprites (spritesheets): AQUÍ dices cómo está ordenada cada una.

Cada personaje tiene una entrada en HOJAS. Como las hojas gratuitas no siempre vienen en el mismo
orden, solo tienes que decir qué dirección es cada columna (o cada fila):

    "archivo"  nombre del PNG dentro de assets/spritesheets/
    "por"      "columnas" -> cada DIRECCIÓN es una columna (se lee de izquierda a derecha)
                             y los pasos de la caminata van hacia ABAJO.
               "filas"    -> cada DIRECCIÓN es una fila (se lee de arriba abajo)
                             y los pasos de la caminata van hacia la DERECHA.
    "orden"    qué dirección es cada columna (o fila), en ese orden. Palabras permitidas:
               "arriba", "abajo", "derecha", "izquierda".
    "tamano"   tamaño con que se dibuja en el juego (el Navegante mide 19, el zombi 28, los NPC 24).

Opcionales:
    "cuadro"   tamaño de cada cuadrito del PNG en píxeles: un número (cuadrado) o (ancho, alto),
               o "auto" para que lo calcule solo dividiendo la hoja. Si lo omites es "auto".
    "cuadros"  cuántos pasos de caminata tiene cada dirección (normalmente 4).
    "espejo"   direcciones que la hoja NO trae y se sacan volteando otra. Ejemplo, hoja con 3
               direcciones:  "orden": ["abajo", "arriba", "derecha"], "espejo": {"izquierda": "derecha"}
    "inicio"   (x, y) en píxeles donde empieza la cuadrícula, si la hoja tiene margen.

Para ver cómo quedó cada hoja:   py -3.12 ver_hojas.py   (o:  py -3.12 ver_hojas.py nina)
Para agregar un personaje nuevo: agrega su entrada aquí y cárgalo con  hojas.cargar("nombre", PIXEL_SCALE).
"""

import os
import pygame

RUTA_HOJAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "spritesheets")

# ============================================================================
# CONFIGURACIÓN DE CADA HOJA
# ============================================================================
HOJAS = {
    "navegante": {"archivo": "navegante_walk.png", "cuadro": 64, "por": "columnas",
                  "orden": ["abajo", "arriba", "derecha", "izquierda"], "tamano": 19},
    "zombi": {"archivo": "zombie_walk.png", "cuadro": 64, "por": "columnas",
              "orden": ["abajo", "arriba", "derecha", "izquierda"], "tamano": 28},
    # Nina: 4 columnas, de izquierda a derecha: arriba, abajo, derecha, izquierda
    "nina": {"archivo": "nina_walk.png", "cuadro": 64, "por": "columnas",
             "orden": ["arriba", "abajo", "derecha", "izquierda"], "tamano": 24},
    # Maru (la anciana): 4 filas, de arriba a abajo: arriba, derecha, abajo, izquierda
    "anciana": {"archivo": "anciana_walk.png", "cuadro": 64, "por": "filas",
                "orden": ["arriba", "izquierda", "abajo", "derecha"], "tamano": 24},
}

# ============================================================================
# CARGA (no hace falta tocar nada de aquí para abajo)
# ============================================================================
_DIRS = {"arriba": "up", "abajo": "down", "derecha": "right", "izquierda": "left",
         "up": "up", "down": "down", "right": "right", "left": "left"}
_NOMBRE_ES = {"up": "arriba", "down": "abajo", "right": "derecha", "left": "izquierda"}


class _Aviso(Exception):
    pass


def _dir(nombre):
    d = _DIRS.get(str(nombre).lower())
    if d is None:
        raise _Aviso(f"'{nombre}' no es una dirección válida. Usa: arriba, abajo, derecha, izquierda.")
    return d


def describir(nombre):
    """Texto corto con cómo está configurada una hoja."""
    cfg = HOJAS[nombre]
    cols = cfg["por"] == "columnas"
    orden = ", ".join("—" if d is None else _NOMBRE_ES[_dir(d)] for d in cfg["orden"])
    sentido = "columnas (de izquierda a derecha)" if cols else "filas (de arriba a abajo)"
    extra = ""
    if cfg.get("espejo"):
        extra = "  ·  volteadas: " + ", ".join(f"{k} = {v}" for k, v in cfg["espejo"].items())
    return f"{cfg['archivo']}  ·  direcciones por {sentido}: {orden}{extra}"


def cargar(nombre, escala, tamano=None):
    """Devuelve {"up": [cuadros], "down": [...], "left": [...], "right": [...]} ya escalados,
    o None si no se pudo (entonces el juego dibuja una figura simple)."""
    cfg = HOJAS.get(nombre)
    if cfg is None:
        print(f"[hojas] '{nombre}' no está en HOJAS (nucleo/hojas.py).")
        return None
    try:
        return _cargar(cfg, escala, tamano)
    except _Aviso as e:
        print(f"[hojas] {nombre}: {e}")
    except Exception as e:
        print(f"[hojas] {nombre}: no pude cargarla ({e})")
    return None


def _cargar(cfg, escala, tamano):
    ruta = os.path.join(RUTA_HOJAS, cfg["archivo"])
    if not os.path.exists(ruta):
        raise _Aviso(f"no encuentro {cfg['archivo']} en assets/spritesheets/ (se dibuja una figura simple).")
    por = cfg.get("por", "columnas")
    if por not in ("columnas", "filas"):
        raise _Aviso("'por' debe ser \"columnas\" o \"filas\".")
    orden = [None if d is None else _dir(d) for d in cfg["orden"]]
    vistos = [d for d in orden if d is not None]
    if len(set(vistos)) != len(vistos):
        raise _Aviso("hay una dirección repetida en 'orden'.")
    pasos = int(cfg.get("cuadros", 4))
    hoja = pygame.image.load(ruta).convert_alpha()
    ancho, alto = hoja.get_size()
    cols, filas = (len(orden), pasos) if por == "columnas" else (pasos, len(orden))
    ox, oy = cfg.get("inicio", (0, 0))

    cuadro = cfg.get("cuadro", "auto")
    if cuadro == "auto":
        fw, fh = (ancho - ox) // cols, (alto - oy) // filas
    elif isinstance(cuadro, (tuple, list)):
        fw, fh = int(cuadro[0]), int(cuadro[1])
    else:
        fw = fh = int(cuadro)
    if fw <= 0 or fh <= 0 or ox + cols * fw > ancho or oy + filas * fh > alto:
        raise _Aviso(f"la hoja mide {ancho}x{alto} pero con cuadros de {fw}x{fh}, {len(orden)} direcciones y "
                     f"{pasos} pasos necesito al menos {ox + cols * fw}x{oy + filas * fh}. "
                     f"Revisa 'cuadro', 'cuadros' y 'orden'.")

    lado = max(1, int((tamano or cfg.get("tamano", 24)) * escala))
    out = {}
    for i, d in enumerate(orden):
        if d is None:
            continue
        cuadros = []
        for k in range(pasos):
            c, f = (i, k) if por == "columnas" else (k, i)
            rect = pygame.Rect(ox + c * fw, oy + f * fh, fw, fh)
            cuadros.append(pygame.transform.scale(hoja.subsurface(rect).copy(), (lado, lado)))
        out[d] = cuadros
    for destino, origen in cfg.get("espejo", {}).items():
        destino, origen = _dir(destino), _dir(origen)
        if origen not in out:
            raise _Aviso(f"'espejo' pide voltear '{_NOMBRE_ES[origen]}' pero esa dirección no está en 'orden'.")
        out[destino] = [pygame.transform.flip(f, True, False) for f in out[origen]]
    faltan = [_NOMBRE_ES[d] for d in ("up", "down", "left", "right") if d not in out]
    if faltan:
        raise _Aviso("falta la dirección " + ", ".join(faltan) + ": agrégala en 'orden' o en 'espejo'.")
    return out
