"""Ciclo de día y noche.

Salió de ebanon.py (original), alrededor de las líneas 1147-1203.
"""

import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global estado
    from nucleo import estado


# ----------------------------------------------------------------------------
# 6. CICLO DÍA / NOCHE
# ----------------------------------------------------------------------------
def ring_alarm(msg):
    if not estado.player.has_watch:      # la alarma es del reloj; quita esta línea si la quieres siempre
        return
    pygame.mixer.Channel(12).play(clock_alarm_sound)
    estado.log(msg)
    
def update_day_night(dt):
    global alarm_pre_done, alarm_end_done
    estado.world_time += dt / DAY_LENGTH
    if estado.world_time >= 1:
        estado.world_time -= 1
        estado.day_count += 1
        estado.log(f"Amanece. Día {estado.day_count}.")

    # Alarma antes de la locura
    pre = ALARM_PRE_HOUR / 24
    if pre <= estado.world_time < pre + 1 / 48:
        if not alarm_pre_done:
            alarm_pre_done = True
            ring_alarm("Suena la alarma: Debo refugiarme.")
    else:
        alarm_pre_done = False

    # Alarma al terminar la locura
    end = ALARM_END_HOUR / 24
    if end <= estado.world_time < end + 1 / 48:
        if not alarm_end_done:
            alarm_end_done = True
            ring_alarm("Suena la alarma: la locura terminó.")
    else:
        alarm_end_done = False
                            
# Umbrales del ciclo día/noche (un solo lugar para ajustar todo)
DAWN_START = 0.166   # ~4:00, empieza a aclarar
DAWN_END   = 0.250   # ~6:00, ya es de día completo
DUSK_START = 0.792  # ~19:00, empieza a oscurecer
DUSK_END   = 0.875   # ~21:00, noche completa
FRENZY_START = (DUSK_START + DUSK_END) / 2    # ≈ 20:00, empieza la locura
FRENZY_END   = (DAWN_START + DAWN_END) / 2    # ≈ 5:00, termina la locura
ALARM_LEAD   = 1 / 24                         # 1 hora antes
alarm_pre_done = False
alarm_end_done = False

def night_darkness():
    t = estado.world_time
    if t < DAWN_START:
        return 1.0
    if t < DAWN_END:
        return 1.0 - (t - DAWN_START) / (DAWN_END - DAWN_START)
    if t < DUSK_START:
        return 0.0
    if t < DUSK_END:
        return (t - DUSK_START) / (DUSK_END - DUSK_START)
    return 1.0

def is_night():
    return night_darkness() >= 0.5
