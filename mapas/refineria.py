"""Dinamita y Refinería.

Salió de ebanon.py (original), alrededor de las líneas 7697-7989.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403
from mapas import barco
from mapas import fundidora


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global baca_jefe, baca_pico, camara, colision, construccion
    global dibujo, estado, hombre_reloj, makadewaa, mina
    global mundo, neri_jefe, transicion
    from interfaz import dibujo
    from jefes import baca_jefe, baca_pico, hombre_reloj, makadewaa, neri_jefe
    from mapas import mina, transicion
    from nucleo import estado, mundo
    from sistemas import camara, colision, construccion


    
# ============================================================================
# DINAMITA Y REFINERÍA
# ============================================================================
DYNAMITE_KEY = pygame.K_g        # ← tecla para encender y lanzar dinamita
DYNAMITE_FUSE = 3.0              # ← segundos hasta explotar
DYNAMITE_RADIUS = 56             # ← radio de la explosión (unidades; 1 tile = 16)
DYNAMITE_DAMAGE = 140            # ← daño a zombis, crías y osos débiles
DYNAMITE_BOSS_DAMAGE = 60        # ← daño a jefes
DYNAMITE_STRUCT_DAMAGE = 150     # ← daño a tus estructuras (piedra y metal resisten)
DYNAMITE_PLAYER_DAMAGE = 40      # ← daño a ti si te alcanza (0 = no te hace daño)
DYNAMITE_COUNT = 6               # ← cuántas hay en la mina
DYNAMITE_THROW = 90              # ← distancia del lanzamiento
REFINERY_DARKNESS = 0.5          # ← oscuridad dentro de la refinería
REFINERY_ZOMBIE_CAP = 8          # ← máximo de zombis vivos allí
refinery_stash = None
REFINERY_POS = [0, 0]            # centro del complejo en la isla (tile), lo fija gen_world
REFINERY_BARRIER = set()         # tiles del anillo de escombros
dyn_sticks = []
dyn_blasts = []
barco.BOAT_LABELS["dynamite"] = "Dinamita"
ITEM_NAMES.update({"dynamite": "dinamita"})
DROP_KEYS[pygame.K_7] = "dynamite"       # con la mochila abierta: 7 tira dinamita, 8 tira diésel
DROP_KEYS[pygame.K_8] = "diesel"
MAP_DARK = {"mine": MINE_DARKNESS, "foundry": fundidora.FOUNDRY_DARKNESS, "refinery": REFINERY_DARKNESS}


# ── Dinamita ──
def light_dynamite():
    if estado.inventory_open or estado.active_chest or barco.boat["open"]:
        return
    if estado.player.cargo.get("dynamite", 0) <= 0:
        estado.log("No tienes dinamita.")
        return
    estado.player.cargo["dynamite"] -= 1
    dyn_sticks.append({"x": estado.player.x, "y": estado.player.y, "vx": estado.player.aim_x * 260, "vy": estado.player.aim_y * 260,
                       "fly": DYNAMITE_THROW / 260.0, "t": DYNAMITE_FUSE})
    pygame.mixer.Channel(24).play(bear_swipe_sound)
    estado.log("¡Dinamita encendida! Corre.")


def explode(x, y):
    R = DYNAMITE_RADIUS
    dyn_blasts.append({"x": x, "y": y, "t": 0.45})
    pygame.mixer.Channel(24).play(bear_slam_sound)
    neri_jefe.lair["shake"] = max(neri_jefe.lair["shake"], 1.2)
    for z in estado.zombies:
        if not z.dead and mundo.dist(x, y, z.x, z.y) < R:
            z.hp -= DYNAMITE_DAMAGE
            z.hit_flash = 0.15
            if z.hp <= 0:
                z.dead = True
    for bt in bats:
        if not bt.dead and mundo.dist(x, y, bt.x, bt.y) < R:
            bt.hp = 0
            bt.dead = True
    for p in neri_jefe.neri_pups:
        if not p.dead and mundo.dist(x, y, p.x, p.y) < R:
            neri_jefe.hit_pup(p, DYNAMITE_DAMAGE)
    for br in estado.bears:
        if not br.dead and mundo.dist(x, y, br.x, br.y) < R + 6 * br.size:
            makadewaa.hit_bear(br, DYNAMITE_DAMAGE if br.kind == "weak" else DYNAMITE_BOSS_DAMAGE, 20)
    if estado.boss and mundo.dist(x, y, estado.boss.x, estado.boss.y) < R + 12:
        hombre_reloj.hit_boss(DYNAMITE_BOSS_DAMAGE)
    if baca_jefe.baca and mundo.dist(x, y, baca_jefe.baca.x, baca_jefe.baca.y) < R + 6 * baca_jefe.baca.size:
        baca_jefe.hit_baca(DYNAMITE_BOSS_DAMAGE)
    if neri_jefe.neri and mundo.dist(x, y, neri_jefe.neri.x, neri_jefe.neri.y) < R + 6 * neri_jefe.neri.size:
        neri_jefe.hit_neri(DYNAMITE_BOSS_DAMAGE)
    d = mundo.dist(x, y, estado.player.x, estado.player.y)
    if d < R and not estado.god_mode and DYNAMITE_PLAYER_DAMAGE > 0:
        estado.player.hp = max(0, estado.player.hp - DYNAMITE_PLAYER_DAMAGE * (1.0 - 0.5 * d / R))
        estado.log("¡La explosión te alcanzó!")
    for st in list(estado.structures):
        if mundo.dist(x, y, st["x"], st["y"]) < R + 8:
            if st["type"] in ATTACKABLE and "hp" in st:
                construccion.damage_structure(st, DYNAMITE_STRUCT_DAMAGE)
            elif st["type"] in ("fire", "trapSpikes", "trapBear"):
                construccion.destroy_structure(st)
    tr = int(R // TILE) + 1
    cx_t, cy_t = int(x // TILE), int(y // TILE)
    opened = 0
    for ty in range(cy_t - tr, cy_t + tr + 1):
        for tx in range(cx_t - tr, cx_t + tr + 1):
            if math.hypot(tx * TILE + 8 - x, ty * TILE + 8 - y) > R:
                continue
            if estado.in_mine:
                if (tx, ty) in mine_breakable:
                    mundo.WORLD[ty][tx] = mundo.TILE_TYPE["hill"]
                    mine_breakable.discard((tx, ty))
                    mine_broken.append([tx, ty])
                    opened += 1
            elif (tx, ty) in REFINERY_BARRIER and mundo.tile_at(tx, ty) == mundo.TILE_TYPE["ruin"]:
                mundo.WORLD[ty][tx] = mundo.TILE_TYPE["ground"]
                baca_pico.broken_ruins.append([tx, ty])            # queda abierto también al guardar
                opened += 1
    if opened:
        estado.log("La pared se vino abajo." if estado.in_mine else "Los escombros cedieron. El camino a la refinería está abierto.")


def update_dynamite(dt):
    for s in dyn_sticks:
        if s["fly"] > 0:
            s["fly"] -= dt
            nx, ny = s["x"] + s["vx"] * dt, s["y"] + s["vy"] * dt
            if colision.blocked(int(nx // TILE), int(ny // TILE), False, ignore_props=True):
                s["fly"] = 0
            else:
                s["x"], s["y"] = nx, ny
        s["t"] -= dt
        if s["t"] <= 0:
            explode(s["x"], s["y"])
    dyn_sticks[:] = [s for s in dyn_sticks if s["t"] > 0]
    for b in dyn_blasts:
        b["t"] -= dt
    dyn_blasts[:] = [b for b in dyn_blasts if b["t"] > 0]


def draw_dynamite(surface):
    u = PIXEL_SCALE
    if not dyn_sticks and not dyn_blasts:
        return
    layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    for s in dyn_sticks:
        sx, sy = camara.world_to_screen(s["x"], s["y"])
        pygame.draw.circle(layer, (255, 80, 60, 90), (int(sx), int(sy)), int(DYNAMITE_RADIUS * u), 2)
        if not dibujo.draw_sprite(surface, "dynamite_lit", s["x"], s["y"], "center"):
            dibujo.px(surface, sx - 3 * u, sy - 4 * u, 6 * u, 8 * u, (176, 52, 44))
            dibujo.px(surface, sx - 3 * u, sy - 1 * u, 6 * u, 2 * u, (230, 220, 190))
            if (pygame.time.get_ticks() // 90) % 2 == 0:
                dibujo.px(surface, sx - 1 * u, sy - 7 * u, 2 * u, 3 * u, (255, 220, 90))
    for b in dyn_blasts:
        sx, sy = camara.world_to_screen(b["x"], b["y"])
        f = b["t"] / 0.45
        R = max(2, int(DYNAMITE_RADIUS * u * (1.2 - 0.5 * f)))
        pygame.draw.circle(layer, (255, 190, 90, int(200 * f)), (int(sx), int(sy)), R)
        pygame.draw.circle(layer, (255, 245, 210, int(255 * f)), (int(sx), int(sy)), R, max(2, int(5 * f)))
    surface.blit(layer, (0, 0))


def spawn_mine_dynamite():
    ex, ey = MINE_INFO["exit"]
    placed = 0
    for _ in range(3000):
        if placed >= DYNAMITE_COUNT:
            break
        tx = random.randint(5, MINE_W - 6)
        ty = random.randint(5, MINE_H - 6)
        if not mina._mine_open(tx, ty, 1) or mundo.dist(tx * TILE, ty * TILE, ex, ey) < 8 * TILE:
            continue
        estado.drops.append({"x": tx * TILE + 8, "y": ty * TILE + 8, "kind": "debris", "items": {"dynamite": 1}})
        placed += 1


def debug_dynamite():
    """Atajo de prueba (Ctrl+R): 5 de dinamita y te lleva junto al complejo de la refinería."""
    estado.player.cargo["dynamite"] = estado.player.cargo.get("dynamite", 0) + 5
    if not estado.in_mine and REFINERY_POS != [0, 0]:
        nx, ny = (REFINERY_POS[0] + 9) * TILE + 8, REFINERY_POS[1] * TILE + 8
        if not colision.blocked(int(nx // TILE), int(ny // TILE), False, ignore_props=True):
            estado.player.x, estado.player.y = nx, ny
    estado.log("PRUEBA: 5 de dinamita (G para lanzar).")


# ── Refinería: mapa fijo ──
def gen_refinery():
    
    W, H = 64, 40
    WALL, FLOOR = mundo.TILE_TYPE["ruin"], mundo.TILE_TYPE["hill"]
    WATER, ROAD, CAVE = mundo.TILE_TYPE["water"], mundo.TILE_TYPE["road"], mundo.TILE_TYPE["cave"]
    g = [[WALL] * W for _ in range(H)]

    def rect(x0, y0, x1, y1, t=FLOOR):
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                g[yy][xx] = t

    rect(6, 6, 57, 21)                         # nave de los tanques
    rect(1, 8, 4, 18)                          # taller oeste
    rect(5, 12, 5, 13)                         # puerta al taller
    rect(59, 8, 62, 18)                        # oficina este
    rect(58, 12, 58, 13)                       # puerta a la oficina
    rect(28, 22, 35, 26)                       # pasillo al patio
    rect(2, 27, 61, 37)                        # patio de entrada
    for x in (10, 18, 26, 34, 42, 50):
        rect(x, 9, x + 3, 12, WALL)            # tanques (fila norte)
    for x in (10, 18, 34, 42):
        rect(x, 16, x + 3, 19, WALL)           # tanques (fila sur)
    rect(6, 7, 57, 7, ROAD)                    # tuberías / vías
    rect(2, 30, 61, 30, ROAD)
    rect(46, 14, 50, 15, WATER)                # charcos
    rect(4, 33, 9, 35, WATER)
    rect(8, 31, 13, 32, WALL)                  # contenedores
    rect(50, 31, 55, 32, WALL)
    g[38][32] = CAVE                           # salida
    loot = []
    for (x, y) in ((3, 9), (3, 17), (60, 9), (60, 17), (8, 8), (55, 8), (15, 14), (44, 14),
                   (6, 29), (58, 29), (20, 34), (44, 34), (14, 36), (50, 36)):
        loot.append(("scrap", x, y))
    for (x, y) in ((12, 35), (57, 35), (30, 34), (25, 30)):
        loot.append(("wood", x, y))
    for (x, y) in ((3, 13), (61, 13)):
        loot.append(("herb", x, y))
    for (x, y) in ((16, 34), (48, 34)):
        loot.append(("berry", x, y))
    for (x, y) in ((2, 9), (61, 9), (30, 8), (32, 20)):
        loot.append(("ammo", x, y))
    for (x, y) in ((2, 16), (3, 10), (60, 10), (61, 16), (8, 20), (55, 20),
                   (24, 14), (40, 14), (10, 36), (52, 36), (28, 31), (36, 33)):
        loot.append(("diesel", x, y))
    mundo.WORLD = g
    estado.WORLD_MASK = [[True] * W for _ in range(H)]
    estado.WORLD_W, estado.WORLD_H = W, H
    estado.WORLD_CENTER = (W // 2, H // 2)
    estado.WORLD_RADIUS = max(W, H)
    MINE_INFO["exit"] = (32 * TILE + 8, 38 * TILE + 8)
    MINE_INFO["start"] = (32 * TILE + 8, 36 * TILE + 8)
    MINE_INFO["lair"] = (-99999, -99999)
    return loot


def spawn_refinery_resources(loot):
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
        elif kind == "diesel":                     # barril de diésel: 1 por barril, no reaparece
            estado.drops.append({"x": x, "y": y, "kind": "debris", "items": {"diesel": 1}})
        else:
            estado.ammo_pickups.append(pos)


# ── Portón de la refinería en la isla ──
def refinery_gate_interact():
    if REFINERY_POS == [0, 0]:
        return False
    if mundo.dist(estado.player.x, estado.player.y, REFINERY_POS[0] * TILE + 8, REFINERY_POS[1] * TILE + 8) > 3 * TILE:
        return False
    transicion.enter_map("refinery")
    return True


def draw_refinery_gate(surface):
    if estado.in_mine or REFINERY_POS == [0, 0]:
        return
    wx, wy = REFINERY_POS[0] * TILE + 8, REFINERY_POS[1] * TILE + 8
    sx, sy = camara.world_to_screen(wx, wy)
    u = PIXEL_SCALE
    if not dibujo.draw_sprite(surface, "refinery_gate", wx, wy, "center", False, (48, 48)):
        x0, y0 = sx - 24 * u, sy - 24 * u
        dibujo.px(surface, x0, y0, 48 * u, 48 * u, PALETTE["rock_dark"])
        dibujo.px(surface, x0 + 4 * u, y0 + 4 * u, 40 * u, 40 * u, PALETTE["gun_dark"])
        dibujo.px(surface, x0 + 23 * u, y0 + 4 * u, 2 * u, 40 * u, (10, 10, 10))
        for i in range(5):                                       # franjas de peligro
            dibujo.px(surface, x0 + 4 * u, y0 + (6 + i * 8) * u, 40 * u, 3 * u,
               (196, 160, 56) if i % 2 == 0 else (30, 30, 26))
    if mundo.dist(estado.player.x, estado.player.y, wx, wy) <= 3 * TILE:
        t = FONT_SMALL.render("E: entrar a la refinería", True, (244, 224, 74))
        surface.blit(t, (sx - t.get_width() // 2, sy - 28 * u - t.get_height()))


def draw_barrier_marks(surface, sx, sy):
    u = PIXEL_SCALE
    c = (176, 70, 52)
    pygame.draw.line(surface, c, (sx + 2 * u, sy + 2 * u), (sx + 14 * u, sy + 14 * u), max(1, u))
    pygame.draw.line(surface, c, (sx + 14 * u, sy + 2 * u), (sx + 2 * u, sy + 14 * u), max(1, u))


def draw_refinery_arrow(surface):
    """Flecha hacia la refinería: aparece cuando llevas dinamita."""
    if estado.in_mine or estado.player.cargo.get("dynamite", 0) <= 0 or REFINERY_POS == [0, 0]:
        return
    wx, wy = REFINERY_POS[0] * TILE + 8, REFINERY_POS[1] * TILE + 8
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
    col = (214, 150, 90)
    pygame.draw.polygon(surface, col, [(ax + dx * 14 * s, ay + dy * 14 * s),
                                       (ax - dx * 8 * s - dy * 10 * s, ay - dy * 8 * s + dx * 10 * s),
                                       (ax - dx * 8 * s + dy * 10 * s, ay - dy * 8 * s - dx * 10 * s)])
    t = FONT_SMALL.render(f"Refinería {int(mundo.dist(estado.player.x, estado.player.y, wx, wy) // TILE)}", True, col)
    surface.blit(t, (ax - dx * 26 * s - t.get_width() / 2, ay - dy * 26 * s - t.get_height() / 2))
