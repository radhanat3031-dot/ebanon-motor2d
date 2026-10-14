"""Tónico de Baca (dash) y crías de Neri sueltas.

Salió de ebanon.py (original), alrededor de las líneas 6941-7080.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403
from nucleo import estado


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global actualizacion, ayudantes, barco, camara, colision
    global construccion, mundo, neri_jefe, spawn
    from jefes import neri_jefe
    from mapas import barco
    from npcs import ayudantes
    from nucleo import mundo
    from sistemas import actualizacion, camara, colision, construccion, spawn


    
# ============================================================================
# TÓNICO DE BACA (DASH) Y CRÍAS DE NERI SUELTAS
# ============================================================================
DASH_MOUSE_BUTTON = 3          # ← 3 = clic derecho (1 = izquierdo, 2 = rueda)
DASH_STAMINA_FRACTION = 1 / 3  # ← costo: fracción de la estamina máxima
DASH_DISTANCE = 72             # ← distancia en unidades (1 tile = 16)
DASH_TIME = 0.2                # ← duración del impulso (segundos)
DASH_IFRAMES = 0.12            # ← segundos iniciales sin recibir daño
DASH_COOLDOWN = 0.8            # ← pausa entre dashes
estado.player.dash_t = 0.0
estado.player.dash_cd = 0.0
estado.player.dash_dx = estado.player.dash_dy = 0.0
estado.player.dash_hp = 0.0
dash_trail = []

WILD_PUP_AGGRO = 130           # ← a qué distancia te notan (unidades)
WILD_PUP_FIRE_FEAR = 80        # ← distancia a una fogata encendida a la que huyen
WILD_PACK_EVERY = (70, 130)    # ← segundos entre manadas (mín, máx)
WILD_PACK_SIZE = (2, 3)        # ← crías por manada
WILD_PUP_CAP_ISLAND = 6        # ← máximo vivas en la isla
WILD_PUP_CAP_MINE = 4          # ← máximo vivas en la mina
WILD_PUP_MEAT_CHANCE = 0.5     # ← probabilidad de que dejen carne (comida)
wild_timer = [random.uniform(*WILD_PACK_EVERY)]


def try_dash():
    if not estado.player.has_tonic or estado.player.dash_t > 0 or estado.player.dash_cd > 0:
        return
    if estado.inventory_open or estado.active_chest or estado.pause_menu_open or barco.boat["open"]:        
        return
    if estado.build_selected:                               # el clic derecho cancela la construcción
        construccion.clear_build_selection()
        estado.log("Selección cancelada.")
        return
    cost = estado.player.max_stamina * DASH_STAMINA_FRACTION
    if estado.player.stamina < cost:
        estado.log("Sin fuerzas para el dash.")
        return
    mx, my = actualizacion.read_keyboard_move(pygame.key.get_pressed())
    if mx == 0 and my == 0:                          # quieto: dash hacia donde apuntas
        mx, my = estado.player.aim_x, estado.player.aim_y
    l = math.hypot(mx, my) or 1
    estado.player.dash_dx, estado.player.dash_dy = mx / l, my / l
    estado.player.stamina -= cost
    if not estado.god_mode:
        estado.player.hunger = max(0, estado.player.hunger - ayudantes.DASH_HUNGER_COST)
    estado.player.dash_t = DASH_TIME
    estado.player.dash_cd = DASH_COOLDOWN
    estado.player.dash_hp = estado.player.hp
    pygame.mixer.Channel(23).play(bear_swipe_sound)


def update_dash(dt):
    for t in dash_trail:
        t[2] -= dt
    dash_trail[:] = [t for t in dash_trail if t[2] > 0]
    if estado.player.dash_cd > 0:
        estado.player.dash_cd -= dt
    if estado.player.dash_t <= 0:
        return
    if DASH_TIME - estado.player.dash_t < DASH_IFRAMES:     # sin daño al inicio del dash
        estado.player.hp = max(estado.player.hp, estado.player.dash_hp)
    step = DASH_DISTANCE / DASH_TIME * dt
    nx, ny = estado.player.x + estado.player.dash_dx * step, estado.player.y + estado.player.dash_dy * step
    cur_t = (int(estado.player.x // TILE), int(estado.player.y // TILE))
    tx, ty = int(nx // TILE), int(ny // TILE)
    if ((tx, ty) == cur_t or not colision.blocked(tx, ty, False)) and not spawn.zombie_blocks_player(nx, ny):
        estado.player.x, estado.player.y = nx, ny
        dash_trail.append([estado.player.x, estado.player.y, 0.25])
        estado.player.dash_t -= dt
    else:
        estado.player.dash_t = 0.0                          # chocó con algo: termina el dash


def draw_dash_fx(surface):
    if not dash_trail:
        return
    layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    for t in dash_trail:
        sx, sy = camara.world_to_screen(t[0], t[1])
        f = max(0.0, t[2] / 0.25)
        pygame.draw.circle(layer, (190, 205, 215, int(130 * f)), (int(sx), int(sy)),
                           max(2, int(7 * PIXEL_SCALE * f)))
    surface.blit(layer, (0, 0))


def lit_fire_near(x, y, radius):
    for st in estado.structures:
        if st["type"] == "fire" and st.get("fuel", 1) > 0 and mundo.dist(x, y, st["x"], st["y"]) < radius:
            return st
    return None


def spawn_wild_pack():
    cap = WILD_PUP_CAP_MINE if estado.in_mine else WILD_PUP_CAP_ISLAND
    alive = sum(1 for p in neri_jefe.neri_pups if p.wild and not p.dead)
    if alive >= cap:
        return
    size = min(random.randint(*WILD_PACK_SIZE), cap - alive)
    for _ in range(80):
        span = 34 if estado.in_mine else 45
        tx = int(estado.player.x // TILE) + random.randint(-span, span)
        ty = int(estado.player.y // TILE) + random.randint(-span, span)
        if not (0 <= tx < estado.WORLD_W and 0 <= ty < estado.WORLD_H):
            continue
        if estado.in_mine and (tx, ty) not in mine_field:
            continue
        lo, hi = (14, 34) if estado.in_mine else (18, 45)
        d = mundo.dist(tx * TILE, ty * TILE, estado.player.x, estado.player.y)
        if d < lo * TILE or d > hi * TILE:
            continue
        if mundo.tile_solid(tx, ty) or mundo.tile_water(tx, ty) or not estado.WORLD_MASK[ty][tx]:
            continue
        if colision.near_fire(tx * TILE + 8, ty * TILE + 8):
            continue
        pack = random.randint(1, 10 ** 9)
        for _i in range(size):
            x, y = tx * TILE + 8 + random.uniform(-14, 14), ty * TILE + 8 + random.uniform(-14, 14)
            if mundo.tile_solid(int(x // TILE), int(y // TILE)):
                x, y = tx * TILE + 8, ty * TILE + 8
            p = neri_jefe.NeriPup(x, y)
            p.wild = True
            p.aggro = False
            p.pack = pack
            neri_jefe.neri_pups.append(p)
        return


def wild_spawn_tick(dt):
    if not neri_jefe.neri_defeated:                            # solo después de vencer a Neri
        return
    wild_timer[0] -= dt
    if wild_timer[0] <= 0:
        wild_timer[0] = random.uniform(*WILD_PACK_EVERY)
        spawn_wild_pack()


def debug_tonic():
    """Atajo de prueba (Ctrl+Y): te da el tónico y cuenta a Neri como derrotada."""
    
    estado.player.has_tonic = True
    neri_jefe.neri_defeated = True
    estado.log("PRUEBA: tienes el tónico y Neri cuenta como derrotada.")
