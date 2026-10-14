"""Eventos: cada día puede pasar algo. Se sortea al amanecer y se avisa por pantalla.

    HORDA      Al caer la noche suena un tañido y una horda marcha hacia donde estás. Mientras más días
               llevas, más zombis vienen. Si acabas con todos, encuentras botín (y casi siempre una página
               del diario). Si amanece antes, la horda se dispersa.
    TORMENTA   El cielo se cierra y llueve fuerte un buen rato (con el clima: mojado y frío).
    NAUFRAGIO  Aparecen restos en el mar; el aviso dice hacia qué lado de la isla. Hay botín (ver exploracion.py).

El día 1 nunca hay eventos, y no se repite el mismo evento dos días seguidos.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global ambiente, ciclo_dia, entidades, estado, exploracion, hud, mundo
    from interfaz import hud
    from nucleo import entidades, estado, mundo
    from sistemas import ambiente, ciclo_dia, exploracion


# ============================================================================
# AJUSTES (todo lo que quieras tocar está aquí)
# ============================================================================
EVENT_FROM_DAY = 2                                   # ← desde qué día puede haber eventos
EVENT_WEIGHTS = {"horda": 45, "tormenta": 25, "naufragio": 25, "ninguno": 20}   # ← qué tan probable es cada uno
HORDE_BASE = 8                                       # ← zombis de la primera horda...
HORDE_PER_DAY = 3                                    # ← ...más esto por cada día que llevas
HORDE_MAX = 40                                       # ← tope de zombis en una horda
HORDE_BATCH = 5                                      # ← cuántos aparecen cada vez
HORDE_EVERY = 2.5                                    # ← cada cuántos segundos aparece otro grupo
HORDE_SPEED = 75                                     # ← velocidad de los zombis de la horda
WORLD_ZOMBIE_CAP = 1000                                # ← no aparecen más si ya hay tantos zombis en el mundo
HORDE_REWARD = {"scrap": 4, "food": 2, "bandages": 1}    # ← botín base al vencerla (la chatarra sube con los días)
HORDE_PAGE_CHANCE = 0.60                             # ← probabilidad de página del diario al vencerla
STORM_TIME = 110                                     # ← segundos que dura la tormenta

S = {"day": None, "plan": None, "when": 0.0, "done": False, "last": None, "horde": None, "storm": 0.0}


def reset():
    S.update({"day": None, "plan": None, "when": 0.0, "done": False, "last": None, "horde": None, "storm": 0.0})


# ============================================================================
# SORTEO DEL DÍA
# ============================================================================
def _roll_day(day):
    S["day"], S["done"], S["plan"] = day, False, None
    if S["horde"] is not None and not ciclo_dia.is_night():          # amaneció con la horda sin terminar
        S["horde"] = None
    if day < EVENT_FROM_DAY:
        S["done"] = True
        return
    opciones = {k: v for k, v in EVENT_WEIGHTS.items() if k != S["last"] or k == "ninguno"}
    plan = random.choices(list(opciones), weights=list(opciones.values()))[0]
    S["last"] = plan
    S["plan"] = None if plan == "ninguno" else plan
    S["when"] = random.uniform(0.12, 0.55)
    if S["plan"] in ("tormenta", "naufragio") and estado.world_time > S["when"] + 0.2:
        S["done"] = True                                              # cargaste tarde: este día ya pasó


def _base_center():
    p = estado.player
    s = [st for st in estado.structures if st["type"] != "dock"]
    if len(s) < 3:
        return p.x, p.y
    return sum(st["x"] for st in s) / len(s), sum(st["y"] for st in s) / len(s)


# ============================================================================
# HORDA
# ============================================================================
def start_horde():
    n = min(HORDE_MAX, HORDE_BASE + HORDE_PER_DAY * (estado.day_count - 1))
    S["horde"] = {"left": n, "total": n, "t": 0.0, "zs": [], "alive": 0}
    pygame.mixer.Channel(12).play(clock_alarm_sound)
    estado.log("Un tañido lejano cruza la isla. Una horda marcha hacia el refugio.")


def _spawn_horde_zombie():
    cx, cy = _base_center()
    min_d = math.hypot(SCREEN_W, SCREEN_H) / PIXEL_SCALE / 2 + 2 * TILE        # fuera de la pantalla
    for _ in range(16):
        a = random.uniform(0, math.tau)
        d = min_d + random.uniform(0, 8 * TILE)
        tx, ty = int((cx + math.cos(a) * d) // TILE), int((cy + math.sin(a) * d) // TILE)
        if not (0 <= tx < estado.WORLD_W and 0 <= ty < estado.WORLD_H):
            continue
        if not estado.WORLD_MASK[ty][tx] or mundo.tile_water(tx, ty) or mundo.tile_solid(tx, ty):
            continue
        z = entidades.Zombie(tx * TILE + 8, ty * TILE + 8, HORDE_SPEED)
        z.alert_t = 20.0
        estado.zombies.append(z)
        return z
    return None


def _horde_tick(dt):
    h = S["horde"]
    if h is None:
        return
    night = ciclo_dia.is_night()
    if not night:
        h["left"] = 0                                                   # amaneció: no vienen más
    h["t"] += dt
    while h["left"] > 0 and h["t"] >= HORDE_EVERY:
        h["t"] -= HORDE_EVERY
        for _ in range(HORDE_BATCH):
            if h["left"] > 0 and len(estado.zombies) < WORLD_ZOMBIE_CAP:
                z = _spawn_horde_zombie()
                if z is not None:
                    h["zs"].append(z)
                h["left"] -= 1
    alive = [z for z in h["zs"] if not z.dead and z in estado.zombies]
    for z in alive:
        z.alert_t = max(z.alert_t, 15.0)                                # la horda siempre sabe dónde estás
    h["alive"] = len(alive)
    if h["left"] == 0 and not alive:
        if h["zs"]:
            _horde_victory()
        S["horde"] = None
    elif h["left"] == 0 and not night:
        estado.log("Amanece: lo que queda de la horda se dispersa.")
        S["horde"] = None


def _horde_victory():
    reward = dict(HORDE_REWARD)
    reward["scrap"] += estado.day_count
    for item, n in reward.items():
        exploracion.give(item, n)
    estado.log("La horda cayó. Entre los restos encuentras: " + exploracion._texto_botin(reward) + ".")
    if random.random() < HORDE_PAGE_CHANCE:
        exploracion.give_page()


# ============================================================================
# TORMENTA Y NAUFRAGIO
# ============================================================================
def start_storm():
    ambiente.rain["on"] = True
    ambiente.rain["timer"] = max(ambiente.rain["timer"], STORM_TIME)
    S["storm"] = STORM_TIME
    estado.log("El cielo se cierra: viene una tormenta.")


def start_wreck():
    rumbo = exploracion.spawn_wreck()
    if rumbo:
        estado.log(f"El mar trajo restos de un naufragio al {rumbo} de la isla. Habría que nadar hasta allí… con cuidado.")


# ============================================================================
# ACTUALIZACIÓN
# ============================================================================
def update(dt):
    if estado.in_mine or estado.player.hp <= 0:
        return
    if S["day"] != estado.day_count:
        _roll_day(estado.day_count)
    if S["storm"] > 0:
        S["storm"] -= dt
    if not S["done"] and S["plan"]:
        plan = S["plan"]
        if plan == "horda" and ciclo_dia.is_night():
            S["done"] = True
            start_horde()
        elif plan == "tormenta" and estado.world_time >= S["when"]:
            S["done"] = True
            start_storm()
        elif plan == "naufragio" and estado.world_time >= S["when"]:
            S["done"] = True
            start_wreck()
    _horde_tick(dt)


# ============================================================================
# PANTALLA
# ============================================================================
def draw_banner(surface):
    lines = []
    h = S["horde"]
    if h is not None:
        lines.append((f"HORDA: quedan {h['alive'] + h['left']}", (230, 90, 80)))
    for w in exploracion.wrecks:
        lines.append((f"Naufragio al {w['dir']} de la isla ({int(w['t'] // 60)}:{int(w['t'] % 60):02d})", (130, 190, 220)))
    if S["storm"] > 0:
        lines.append(("Tormenta", (150, 165, 185)))
    for i, (txt, col) in enumerate(lines):
        img = FONT_SMALL.render(txt, True, col)
        surface.blit(img, ((SCREEN_W - img.get_width()) // 2, int((8 + i * 18) * UI_S)))
