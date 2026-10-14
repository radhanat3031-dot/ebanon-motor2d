"""Cámara y conversión mundo -> pantalla.

Salió de ebanon.py (original), alrededor de las líneas 3694-3703.
"""

import random
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global estado, neri_jefe
    from jefes import neri_jefe
    from nucleo import estado


def update_camera():
    
    estado.camera_x = estado.player.x - (SCREEN_W / PIXEL_SCALE) / 2
    estado.camera_y = estado.player.y - (SCREEN_H / PIXEL_SCALE) / 2
    if neri_jefe.lair["shake"] > 0:
        estado.camera_x += random.uniform(-2, 2) * neri_jefe.lair["shake"]
        estado.camera_y += random.uniform(-2, 2) * neri_jefe.lair["shake"]
        
def world_to_screen(wx, wy):
    return (wx - estado.camera_x) * PIXEL_SCALE, (wy - estado.camera_y) * PIXEL_SCALE
