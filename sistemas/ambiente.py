"""Árboles en arboledas y lluvia.

Salió de ebanon.py (original), alrededor de las líneas 6128-6253.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global ciclo_dia, deshuesadero, estado, fundidora, mundo
    global partida, refineria
    from mapas import deshuesadero, fundidora, refineria
    from nucleo import estado, mundo
    from sistemas import ciclo_dia, partida


            
# ── ÁRBOLES EN ARBOLEDAS ──
GROVES = (8, 9)                # ← cuántas arboledas (mín, máx)
GROVE_RADIUS = (8, 9)          # ← tamaño de cada arboleda (tiles)
TREE_LOOSE_FRACTION = 0.15     # ← fracción de árboles sueltos
CAVE_GROVE_TREES = 600          # ← árboles alrededor de la entrada de la mina
CAVE_GROVE_RADIUS = 8          # ← radio de esa arboleda (tiles)

def tree_spot_ok(tx, ty):
    if not (0 <= tx < estado.WORLD_W and 0 <= ty < estado.WORLD_H):
        return False
    if mundo.tile_at(tx, ty) in (mundo.TILE_TYPE["ruin"], mundo.TILE_TYPE["water"], mundo.TILE_TYPE["road"], mundo.TILE_TYPE["cave"]):
        return False
    if abs(tx - CAVE_POS[0]) <= 1 and abs(ty - CAVE_POS[1]) <= 1:
        return False                                   # la trampilla queda libre
    if abs(tx - deshuesadero.JUNK_POS[0]) <= 3 and abs(ty - deshuesadero.JUNK_POS[1]) <= 3:
        return False                                   # el portón queda libre
    if abs(tx - refineria.REFINERY_POS[0]) <= 7 and abs(ty - refineria.REFINERY_POS[1]) <= 7:
        return False                                   # el complejo queda libre
    if abs(tx - fundidora.FOUNDRY_POS[0]) <= 3 and abs(ty - fundidora.FOUNDRY_POS[1]) <= 3:     # comentar esta linea y la de abajo para que los arboles crezcan cerca del porton
        return False                                   # el portón queda libre
    if abs(tx - estado.WORLD_W // 2) <= 3 and abs(ty - estado.WORLD_H // 2) <= 3:
        return False                                   # zona de inicio libre
    return True

def spawn_trees():
    estado.wood_pickups.clear()
    used = set()

    def add(tx, ty):
        if (tx, ty) in used or not tree_spot_ok(tx, ty):
            return False
        used.add((tx, ty))
        estado.wood_pickups.append({"x": tx * TILE + 8, "y": ty * TILE + 8,
                             "active": True, "timer": 0.0, "type": "tree"})
        return True

    # 1) arboleda alrededor de la mina, con un sendero abierto hacia el centro de la isla
    ccx, ccy = CAVE_POS
    gap = math.atan2(estado.WORLD_H / 2 - ccy, estado.WORLD_W / 2 - ccx)
    placed = 0
    for _ in range(CAVE_GROVE_TREES * 8):
        if placed >= CAVE_GROVE_TREES:
            break
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(2.5, CAVE_GROVE_RADIUS)
        if abs((a - gap + math.pi) % (2 * math.pi) - math.pi) < 0.45:
            continue
        if add(int(ccx + math.cos(a) * r), int(ccy + math.sin(a) * r)):
            placed += 1

    # 2) arboledas repartidas por la isla
    loose = int(INITIAL_WOOD * TREE_LOOSE_FRACTION)
    n_groves = random.randint(*GROVES)
    per = max(4, (INITIAL_WOOD - loose - len(estado.wood_pickups)) // n_groves)
    for _ in range(n_groves):
        for _try in range(60):
            gx, gy = random.randint(0, estado.WORLD_W - 1), random.randint(0, estado.WORLD_H - 1)
            if tree_spot_ok(gx, gy):
                break
        else:
            continue
        rad = random.uniform(*GROVE_RADIUS)
        got = 0
        for _t in range(per * 4):
            if got >= per:
                break
            if add(gx + int(random.gauss(0, rad / 2)), gy + int(random.gauss(0, rad / 2))):
                got += 1

    # 3) árboles sueltos
    got = 0
    for _ in range(loose * 20):
        if got >= loose:
            break
        if add(random.randint(0, estado.WORLD_W - 1), random.randint(0, estado.WORLD_H - 1)):
            got += 1


# ── LLUVIA ALEATORIA ──
RAIN_DRY = (320, 500)           # ← segundos de tiempo seco entre lluvias (mín, máx)
RAIN_WET = (40, 120)           # ← segundos que dura cada lluvia (mín, máx)
RAIN_DROPS = 420               # ← gotas en pantalla con lluvia al máximo
RAIN_WIND = 70                 # ← inclinación de la lluvia
rain = {"on": False, "level": 0.0, "timer": random.uniform(20, 90)}
rain_drops = []
_rain_cache = {}

def update_rain(dt):
    rain["timer"] -= dt
    if rain["timer"] <= 0:
        rain["on"] = not rain["on"]
        rain["timer"] = random.uniform(*(RAIN_WET if rain["on"] else RAIN_DRY))
        if not estado.in_mine:
            estado.log("Empieza a llover." if rain["on"] else "La lluvia se detiene.")
    target = 1.0 if (rain["on"] and not estado.in_mine) else 0.0
    rain["level"] += (target - rain["level"]) * min(1.0, dt * 0.6)   # entra y sale poco a poco
    if rain["level"] < 0.01 and target == 0.0:
        rain["level"] = 0.0
    if partida.rain_sound is not None:
        partida.rain_sound.set_volume(0.3 * rain["level"])                    # el sonido sigue a la lluvia
    want = int(RAIN_DROPS * rain["level"])
    while len(rain_drops) < want:
        rain_drops.append([random.uniform(0, SCREEN_W), random.uniform(-SCREEN_H, 0),
                           random.uniform(600, 900), random.uniform(10, 18)])
    del rain_drops[want:]
    for d in rain_drops:
        d[1] += d[2] * dt
        d[0] += RAIN_WIND * dt
        if d[1] > SCREEN_H or d[0] > SCREEN_W + 20:
            d[0] = random.uniform(-40, SCREEN_W)
            d[1] = random.uniform(-60, 0)

def draw_rain(surface):
    lv = rain["level"]
    if lv <= 0.01 or estado.in_mine:
        return
    tint = _rain_cache.get("tint")
    if tint is None:
        tint = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        _rain_cache["tint"] = tint
    tint.fill((25, 35, 55, int(70 * lv)))                 # cielo gris y frío
    surface.blit(tint, (0, 0))
    k = 1.0 - 0.45 * ciclo_dia.night_darkness()                     # de noche las gotas se ven más tenues
    col = (int(150 * k), int(170 * k), int(200 * k))
    s = max(1, UI_S)
    for x, y, spd, ln in rain_drops:
        pygame.draw.line(surface, col, (x, y), (x + ln * s * RAIN_WIND / spd, y + ln * s), 1)
