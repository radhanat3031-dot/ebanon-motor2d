"""El Deshuesadero (piezas de motor).

Salió de ebanon.py (original), alrededor de las líneas 7994-8166.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403
from mapas import refineria


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global barco, camara, colision, dibujo, entidades
    global estado, fundidora, mundo, transicion
    from interfaz import dibujo
    from mapas import barco, fundidora, transicion
    from nucleo import entidades, estado, mundo
    from sistemas import camara, colision


    
# ============================================================================
# DESHUESADERO (piezas de motor)
# ============================================================================
JUNK_DARKNESS = 0.45             # ← oscuridad dentro del deshuesadero
JUNK_ZOMBIE_CAP = 10             # ← máximo de zombis vivos allí
JUNK_ALARM_ZOMBIES = 4           # ← zombis extra cuando salta la alarma de un coche
JUNK_POS = [0, 0]                # tile del portón en la isla (lo fija gen_world)
junk = {"seen": None}
map_stashes = {}                 # guardado de los mapas nuevos (el deshuesadero y los que vengan)
refineria.MAP_DARK["junkyard"] = JUNK_DARKNESS


def gen_junkyard():
    
    W, H = 60, 40
    WALL, FLOOR = mundo.TILE_TYPE["ruin"], mundo.TILE_TYPE["hill"]
    WATER, ROAD, CAVE = mundo.TILE_TYPE["water"], mundo.TILE_TYPE["road"], mundo.TILE_TYPE["cave"]
    g = [[WALL] * W for _ in range(H)]

    def rect(x0, y0, x1, y1, t=FLOOR):
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                g[yy][xx] = t

    rect(2, 3, 57, 37)                         # todo el terreno
    for y in (5, 9, 17, 21):                   # filas de coches siniestrados
        for x in range(4, 54, 6):
            rect(x, y, x + 2, y + 1, WALL)
    rect(2, 15, 57, 15, WALL)                  # primera valla
    rect(8, 15, 10, 15)                        # huecos
    rect(44, 15, 46, 15)
    rect(2, 24, 57, 24, WALL)                  # segunda valla
    rect(26, 24, 28, 24)
    rect(50, 24, 52, 24)
    rect(2, 28, 57, 28, ROAD)                  # camino del patio
    rect(8, 30, 13, 31, WALL)                  # contenedores
    rect(44, 32, 49, 33, WALL)
    rect(20, 31, 24, 33, WATER)                # charco
    g[38][30] = CAVE                           # salida
    loot = []
    for (x, y) in ((8, 8), (20, 12), (36, 12), (48, 8), (14, 20), (32, 23), (44, 19),
                   (24, 27), (40, 27), (6, 29), (52, 29), (16, 35), (36, 35)):
        loot.append(("scrap", x, y))
    for (x, y) in ((12, 36), (48, 36)):
        loot.append(("wood", x, y))
    for (x, y) in ((4, 12), (55, 12)):
        loot.append(("herb", x, y))
    for (x, y) in ((30, 26), (10, 34)):
        loot.append(("berry", x, y))
    for (x, y) in ((3, 10), (56, 10), (30, 19)):
        loot.append(("ammo", x, y))
    for (x, y) in ((3, 4), (56, 4), (30, 8), (55, 20), (5, 23)):
        loot.append(("part", x, y))            # piezas de motor
    mundo.WORLD = g
    estado.WORLD_MASK = [[True] * W for _ in range(H)]
    estado.WORLD_W, estado.WORLD_H = W, H
    estado.WORLD_CENTER = (W // 2, H // 2)
    estado.WORLD_RADIUS = max(W, H)
    MINE_INFO["exit"] = (30 * TILE + 8, 38 * TILE + 8)
    MINE_INFO["start"] = (30 * TILE + 8, 36 * TILE + 8)
    MINE_INFO["lair"] = (-99999, -99999)
    return loot


def spawn_fixed_resources(loot):
    """Reparte el botín de un mapa fijo. Sirve para cualquier mapa nuevo."""
    for lst in (estado.wood_pickups, estado.rock_pickups, estado.scrap_pickups, estado.food_pickups, estado.ammo_pickups):
        lst.clear()
    for kind, tx, ty in loot:
        x, y = tx * TILE + 8, ty * TILE + 8
        pos = {"x": x, "y": y, "active": True, "timer": 0.0}
        if kind == "wood":
            estado.wood_pickups.append(dict(pos, type="tree"))
        elif kind == "scrap":
            estado.scrap_pickups.append(dict(pos, type="scrap"))
        elif kind in ("herb", "berry"):
            estado.food_pickups.append(dict(pos, type=kind))
        elif kind in ("diesel", "part"):           # objetos de carga: 1 por montón, no reaparecen
            estado.drops.append({"x": x, "y": y, "kind": "debris", "items": {kind: 1}})
        else:
            estado.ammo_pickups.append(pos)


def junkyard_gate_interact():
    if JUNK_POS == [0, 0]:
        return False
    if mundo.dist(estado.player.x, estado.player.y, JUNK_POS[0] * TILE + 8, JUNK_POS[1] * TILE + 8) > 3 * TILE:
        return False
    transicion.enter_map("junkyard")
    return True


def draw_junk_gate(surface):
    if estado.in_mine or JUNK_POS == [0, 0]:
        return
    wx, wy = JUNK_POS[0] * TILE + 8, JUNK_POS[1] * TILE + 8
    sx, sy = camara.world_to_screen(wx, wy)
    u = PIXEL_SCALE
    if not dibujo.draw_sprite(surface, "junk_gate", wx, wy, "center", False, (48, 48)):
        x0, y0 = sx - 24 * u, sy - 24 * u
        dibujo.px(surface, x0, y0, 48 * u, 48 * u, PALETTE["rock_dark"])
        dibujo.px(surface, x0 + 4 * u, y0 + 10 * u, 18 * u, 12 * u, (110, 58, 48))     # coche oxidado
        dibujo.px(surface, x0 + 7 * u, y0 + 5 * u, 12 * u, 6 * u, (90, 48, 40))
        dibujo.px(surface, x0 + 26 * u, y0 + 22 * u, 18 * u, 12 * u, (70, 86, 98))     # otro coche
        dibujo.px(surface, x0 + 29 * u, y0 + 17 * u, 12 * u, 6 * u, (58, 72, 82))
        dibujo.px(surface, x0 + 20 * u, y0 + 36 * u, 8 * u, 10 * u, (10, 10, 10))     # entrada
    if mundo.dist(estado.player.x, estado.player.y, wx, wy) <= 3 * TILE:
        t = FONT_SMALL.render("E: entrar al deshuesadero", True, (244, 224, 74))
        surface.blit(t, (sx - t.get_width() // 2, sy - 28 * u - t.get_height()))


def _target_arrow(surface, wx, wy, label, col):
    sx, sy = camara.world_to_screen(wx, wy)
    m = 40
    if m < sx < SCREEN_W - m and m < sy < SCREEN_H - m:
        return
    dx, dy = sx - SCREEN_W / 2, sy - SCREEN_H / 2
    l = math.hypot(dx, dy) or 1
    dx, dy = dx / l, dy / l
    kx = (SCREEN_W / 2 - m) / abs(dx) if abs(dx) > 1e-6 else 1e9
    ky = (SCREEN_H / 2 - m) / abs(dy) if abs(dy) > 1e-6 else 1e9
    k = min(kx, ky)
    ax, ay = SCREEN_W / 2 + dx * k, SCREEN_H / 2 + dy * k
    s = max(1, UI_S)
    pygame.draw.polygon(surface, col, [(ax + dx * 14 * s, ay + dy * 14 * s),
                                       (ax - dx * 8 * s - dy * 10 * s, ay - dy * 8 * s + dx * 10 * s),
                                       (ax - dx * 8 * s + dy * 10 * s, ay - dy * 8 * s - dx * 10 * s)])
    t = FONT_SMALL.render(f"{label} {int(mundo.dist(estado.player.x, estado.player.y, wx, wy) // TILE)}", True, col)
    surface.blit(t, (ax - dx * 26 * s - t.get_width() / 2, ay - dy * 26 * s - t.get_height() / 2))


def draw_junk_arrow(surface):
    """Flecha al deshuesadero: aparece cuando el casco está listo y te faltan piezas."""
    if estado.in_mine or JUNK_POS == [0, 0] or barco.boat["stage"] != 1 or estado.player.cargo.get("part", 0) >= 3:
        return
    _target_arrow(surface, JUNK_POS[0] * TILE + 8, JUNK_POS[1] * TILE + 8, "Deshuesadero", (190, 120, 90))


def alarm_horde(n):
    pygame.mixer.Channel(12).play(clock_alarm_sound)
    estado.log("¡Salta la alarma de un coche! Los zombis vienen hacia aquí.")
    got = 0
    for _ in range(300):
        if got >= n:
            break
        tx = int(estado.player.x // TILE) + random.randint(-22, 22)
        ty = int(estado.player.y // TILE) + random.randint(-22, 22)
        if (tx, ty) not in mine_field or mundo.tile_water(tx, ty):
            continue
        d = mundo.dist(tx * TILE, ty * TILE, estado.player.x, estado.player.y)
        if d < 9 * TILE or d > 22 * TILE:
            continue
        z = entidades.Zombie(tx * TILE + 8, ty * TILE + 8, MINE_ZOMBIE_SPEED)
        z.alert_t = 10.0
        estado.zombies.append(z)
        got += 1


def update_junkyard(dt):
    if not (estado.in_mine and fundidora.map_kind == "junkyard"):
        junk["seen"] = None
        return
    n = estado.player.cargo.get("part", 0)
    if junk["seen"] is not None and n > junk["seen"]:      # recogiste una pieza: salta la alarma
        alarm_horde(JUNK_ALARM_ZOMBIES)
    junk["seen"] = n


def debug_junk():
    """Atajo de prueba (Ctrl+U): te lleva junto al portón del deshuesadero."""
    if estado.in_mine or JUNK_POS == [0, 0]:
        return
    nx, ny = (JUNK_POS[0] + 5) * TILE + 8, JUNK_POS[1] * TILE + 8
    if not colision.blocked(int(nx // TILE), int(ny // TILE), False, ignore_props=True):
        estado.player.x, estado.player.y = nx, ny
    estado.log("PRUEBA: junto al portón del deshuesadero.")
