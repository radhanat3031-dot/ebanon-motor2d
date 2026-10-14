"""Dibujo del mundo: sprites, tiles, estructuras, enemigos, noche.

Salió de ebanon.py (original), alrededor de las líneas 3708-4444.
"""

import math
import os
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global ambiente, baca_jefe, baca_pico, barco, camara
    global ciclo_dia, colision, deshuesadero, estado, fundidora
    global makadewaa, mina, mundo, neri_jefe, refineria
    global tonico
    global tiburones
    global estaciones
    global clima
    global exploracion
    global salto
    from jefes import baca_jefe, baca_pico, makadewaa, neri_jefe, tonico
    from mapas import barco, deshuesadero, fundidora, mina, refineria
    from nucleo import estado, mundo
    from sistemas import ambiente, camara, ciclo_dia, colision
    from sistemas import tiburones
    from sistemas import estaciones
    from sistemas import clima
    from sistemas import exploracion
    from sistemas import salto


# ----------------------------------------------------------------------------
# 14. RENDER
# ----------------------------------------------------------------------------
def px(surface, x, y, w, h, color):
    pygame.draw.rect(surface, color, pygame.Rect(round(x), round(y), max(1, round(w)), max(1, round(h))))
    
# ── SPRITES (con respaldo: si falta el archivo se usa el dibujo de siempre) ──
SPRITE_DIR = os.path.join(ASSETS_DIR, "sprites")
SPRITE_DEBUG = False     # True: imprime en consola los sprites que faltan (una vez cada uno)
SPRITE_SIZES = {         # tamaño en unidades del mundo (1 tile = 16). Lo que no esté aquí mide 16x16
    "res_tree": (24, 32),
    "hatch_island": (48, 48), "hatch_mine": (48, 48),
}
TILE_SPRITE_NAMES = {0: "tile_grass", 1: "tile_dirt", 2: "tile_road", 3: "tile_water",
                     4: "tile_ruin", 5: "tile_cave"}
_sprite_cache = {}

def get_sprite(name, w=TILE, h=TILE, flip=False):
    key = (name, w, h, flip)
    if key in _sprite_cache:
        return _sprite_cache[key]
    img = None
    path = os.path.join(SPRITE_DIR, name + ".png")
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, (max(1, int(w * PIXEL_SCALE)), max(1, int(h * PIXEL_SCALE))))
            if flip:
                img = pygame.transform.flip(img, True, False)
        except Exception as e:
            print(f"Sprite '{name}' no se pudo cargar:", e)
            img = None
    elif SPRITE_DEBUG:
        print("Falta sprite:", name)
    _sprite_cache[key] = img
    return img

def draw_sprite(surface, name, wx, wy, anchor="bottom", flip=False, size=None):
    """Dibuja el sprite centrado en (wx, wy) del mundo. Devuelve False si no existe (y no dibuja nada)."""
    w, h = size or SPRITE_SIZES.get(name, (TILE, TILE))
    spr = get_sprite(name, w, h, flip)
    if spr is None:
        return False
    sx, sy = camara.world_to_screen(wx, wy)
    u = PIXEL_SCALE
    if anchor == "center":
        surface.blit(spr, (round(sx - w * u / 2), round(sy - h * u / 2)))
    else:
        surface.blit(spr, (round(sx - w * u / 2), round(sy + 8 * u - h * u)))
    return True

def draw_cracks(surface, sx, sy):
    u = PIXEL_SCALE
    cc = (214, 128, 64)
    pygame.draw.lines(surface, cc, False, [(sx + 3 * u, sy + 2 * u), (sx + 7 * u, sy + 6 * u),
                                           (sx + 5 * u, sy + 9 * u), (sx + 10 * u, sy + 13 * u)], max(1, u))
    pygame.draw.lines(surface, cc, False, [(sx + 11 * u, sy + 3 * u), (sx + 9 * u, sy + 7 * u),
                                           (sx + 13 * u, sy + 10 * u)], max(1, u))

def draw_tile(surface, tx, ty):
    t = mundo.tile_at(tx, ty)
    sx, sy = camara.world_to_screen(tx * TILE, ty * TILE)
    u = PIXEL_SCALE
    checker = (tx + ty) % 2 == 0
    marked = estado.in_mine and (tx, ty) in mine_breakable
    barrier = (not estado.in_mine) and (tx, ty) in refineria.REFINERY_BARRIER and t == mundo.TILE_TYPE["ruin"]
    spr = get_sprite("tile_barrier") if barrier else None
    if spr is None and estado.in_mine and (tx, ty) in neri_jefe.lair_rubble:
        spr = get_sprite("tile_rubble")    
    if spr is None:
        spr = get_sprite(TILE_SPRITE_NAMES.get(t, "tile_ruin"))        
    if spr is not None:                                   # hay sprite: se usa
        surface.blit(spr, (round(sx), round(sy)))
        makadewaa.draw_ruin_damage(surface, tx, ty, sx, sy)
        if barrier and get_sprite("tile_barrier") is None:
            refineria.draw_barrier_marks(surface, sx, sy)
        if marked:            
            bs = get_sprite("tile_wall_breakable")
            if bs is not None:
                surface.blit(bs, (round(sx), round(sy)))
            else:
                draw_cracks(surface, sx, sy)
        return
    # ---- sin sprite: el dibujo de siempre ----
    pairs = {0: ("grass1", "grass2"), 1: ("dirt1", "dirt2"), 2: ("road1", "road2"),
             3: ("water1", "water2"), 5: ("dirt1", "dirt2")}
    c1, c2 = pairs.get(t, ("ruin1", "ruin2"))
    color = PALETTE[c1] if checker else PALETTE[c2]
    if marked:
        color = (74, 62, 48) if checker else (66, 55, 42)
    elif estado.in_mine and (tx, ty) in neri_jefe.lair_rubble:
        color = (62, 56, 50) if checker else (52, 47, 42)
    elif barrier:
        color = (78, 60, 54) if checker else (68, 52, 46)
    px(surface, sx, sy, TILE * u, TILE * u, color)
    if t == mundo.TILE_TYPE["cave"]:
        px(surface, sx + 1 * u, sy + 2 * u, 14 * u, 13 * u, (28, 26, 22))
        inner = (150, 138, 90) if estado.in_mine else (8, 8, 8)      # en la mina se ve la luz del día
        px(surface, sx + 3 * u, sy + 5 * u, 10 * u, 10 * u, inner)
        px(surface, sx + 2 * u, sy + 4 * u, 2 * u, 11 * u, PALETTE["wall"])
        px(surface, sx + 12 * u, sy + 4 * u, 2 * u, 11 * u, PALETTE["wall"])
        px(surface, sx + 2 * u, sy + 3 * u, 12 * u, 2 * u, PALETTE["wall_dark"])
        return
    makadewaa.draw_ruin_damage(surface, tx, ty, sx, sy)
    if barrier:
        refineria.draw_barrier_marks(surface, sx, sy)
    if not estado.in_mine:        
        return
    if t == mundo.TILE_TYPE["ruin"]:        
        if mundo.tile_at(tx, ty + 1) != mundo.TILE_TYPE["ruin"]:
            px(surface, sx, sy + 13 * u, TILE * u, 3 * u, (24, 25, 20))
        if marked:                                          # grietas = se puede romper
            draw_cracks(surface, sx, sy)
        if (tx, ty) in neri_jefe.lair_rubble:                         # escombros del derrumbe
            px(surface, sx + 3 * u, sy + 3 * u, 4 * u, 3 * u, PALETTE["rock"])
            px(surface, sx + 9 * u, sy + 8 * u, 5 * u, 4 * u, PALETTE["rock_dark"])
    elif t == mundo.TILE_TYPE["road"]:                            # vías de mina
        if checker:
            px(surface, sx + 2 * u, sy + 6 * u, 12 * u, 3 * u, PALETTE["wall_dark"])
        else:
            px(surface, sx + 6 * u, sy + 2 * u, 3 * u, 12 * u, PALETTE["wall_dark"])
        px(surface, sx + 7 * u, sy + 7 * u, 2 * u, 2 * u, PALETTE["gun_metal"])
                
def draw_resource(surface, r):
    if not r["active"]:
        return
    sx, sy = camara.world_to_screen(r["x"] - 8, r["y"] - 8)
    u = PIXEL_SCALE
    t = r["type"]
    key = {"tree": "res_mine_wood" if estado.in_mine else "res_tree",
           "berry": "res_mushroom" if estado.in_mine else "res_berry",
           "rock": "res_rock", "scrap": "res_scrap", "herb": "res_herb"}.get(t)
    if key and draw_sprite(surface, key, r["x"], r["y"]):
        return    
    if estado.in_mine and t == "tree":                     # en la mina: vigas apiladas
        px(surface, sx + 2 * u, sy + 10 * u, 12 * u, 3 * u, PALETTE["tree_trunk"])
        px(surface, sx + 3 * u, sy + 7 * u, 10 * u, 3 * u, PALETTE["door_plank"])
        px(surface, sx + 4 * u, sy + 4 * u, 8 * u, 3 * u, PALETTE["wall"])
        px(surface, sx + 2 * u, sy + 13 * u, 12 * u, 1 * u, PALETTE["wall_dark"])
    elif estado.in_mine and t == "berry":                  # en la mina: hongos
        px(surface, sx + 7 * u, sy + 9 * u, 2 * u, 5 * u, (200, 190, 170))
        px(surface, sx + 4 * u, sy + 6 * u, 8 * u, 4 * u, (150, 70, 60))
        px(surface, sx + 6 * u, sy + 7 * u, 2 * u, 1 * u, (232, 224, 200))
    elif t == "tree":        
        px(surface, sx + 5 * u, sy + 9 * u, 3 * u, 6 * u, PALETTE["tree_trunk"])
        px(surface, sx + 1 * u, sy + 1 * u, 11 * u, 8 * u, PALETTE["tree_leaf"])
        px(surface, sx + 2 * u, sy, 9 * u, 2 * u, PALETTE["tree_leaf_dark"])
    elif t == "rock":
        px(surface, sx + 2 * u, sy + 6 * u, 12 * u, 7 * u, PALETTE["rock"])
        px(surface, sx + 2 * u, sy + 11 * u, 12 * u, 2 * u, PALETTE["rock_dark"])
    elif t == "scrap":
        px(surface, sx + 1 * u, sy + 7 * u, 13 * u, 6 * u, PALETTE["scrap_pile"])
        px(surface, sx + 1 * u, sy + 11 * u, 13 * u, 2 * u, PALETTE["scrap_pile_dark"])
    elif t == "herb":
        px(surface, sx + 5 * u, sy + 7 * u, 6 * u, 6 * u, PALETTE["herb_leaf"])
        px(surface, sx + 7 * u, sy + 9 * u, 2 * u, 2 * u, PALETTE["herb_flower"])
    else:
        px(surface, sx + 4 * u, sy + 4 * u, 8 * u, 8 * u, PALETTE["tree_leaf"])
        px(surface, sx + 6 * u, sy + 6 * u, 2 * u, 2 * u, PALETTE["fire2"])
        px(surface, sx + 9 * u, sy + 8 * u, 2 * u, 2 * u, PALETTE["fire2"])

def draw_gun_pickup(surface):
    if not estado.gun_pickup or estado.gun_pickup["taken"]:
        return
    if draw_sprite(surface, "res_gun", estado.gun_pickup["x"], estado.gun_pickup["y"]):
        return
    sx, sy = camara.world_to_screen(estado.gun_pickup["x"] - 8, estado.gun_pickup["y"] - 8)
    u = PIXEL_SCALE
    bob = math.sin(pygame.time.get_ticks() / 300) * 1.5
    px(surface, sx + 3 * u, sy + 8 * u + bob, 8 * u, 3 * u, PALETTE["gun_metal"])
    px(surface, sx + 3 * u, sy + 11 * u + bob, 3 * u, 4 * u, PALETTE["gun_grip"])
    px(surface, sx + 9 * u, sy + 7 * u + bob, 3 * u, 2 * u, PALETTE["gun_dark"])

def draw_ammo_pickup(surface, a):
    if not a["active"]:
        return
    if draw_sprite(surface, "res_ammo", a["x"], a["y"]):
        return
    sx, sy = camara.world_to_screen(a["x"] - 8, a["y"] - 8)
    u = PIXEL_SCALE
    px(surface, sx + 2 * u, sy + 7 * u, 12 * u, 8 * u, PALETTE["crate"])
    px(surface, sx + 2 * u, sy + 12 * u, 12 * u, 3 * u, PALETTE["crate_dark"])
    px(surface, sx + 6 * u, sy + 9 * u, 4 * u, 4 * u, PALETTE["crate_mark"])

def draw_bullet(surface, b):
    sx, sy = camara.world_to_screen(b["x"] - 2, b["y"] - 2)
    px(surface, sx, sy, 3 * PIXEL_SCALE, 3 * PIXEL_SCALE, PALETTE["bullet"])

def draw_structure(surface, st):
    sx, sy = camara.world_to_screen(st["x"] - 8, st["y"] - 8)
    u = PIXEL_SCALE
    t = st["type"]
    name = "st_door_open" if (t == "door" and st.get("open")) else "st_" + t
    if t == "door" and st.get("metal"):
        name = "st_doorMetal_open" if st.get("open") else "st_doorMetal"    
    if t == "fire" and st.get("fuel", 1) <= 0:
        name = "st_fire_out"
    has_spr = draw_sprite(surface, name, st["x"], st["y"])
    if has_spr:
        pass
    elif t == "dock":
        px(surface, sx, sy + 3 * u, 16 * u, 10 * u, PALETTE["door_plank"])
        for i in range(1, 4):
            px(surface, sx + i * 4 * u, sy + 3 * u, 1 * u, 10 * u, PALETTE["door_dark"])
        px(surface, sx + 1 * u, sy + 12 * u, 2 * u, 3 * u, PALETTE["wall_dark"])
        px(surface, sx + 13 * u, sy + 12 * u, 2 * u, 3 * u, PALETTE["wall_dark"])
    elif t == "bench":
        estaciones.draw_bench(surface, sx, sy)
    elif t == "wall":         
        px(surface, sx, sy, 16 * u, 16 * u, PALETTE["wall"])
        px(surface, sx, sy + 13 * u, 16 * u, 3 * u, PALETTE["wall_dark"])
        px(surface, sx, sy, 16 * u, 2 * u, PALETTE["wall_dark"])
    elif t == "wallStone":
        px(surface, sx, sy, 16 * u, 16 * u, PALETTE["rock"])
        px(surface, sx, sy + 13 * u, 16 * u, 3 * u, PALETTE["rock_dark"])
        px(surface, sx, sy, 16 * u, 2 * u, PALETTE["rock_dark"])
        px(surface, sx + 5 * u, sy + 5 * u, 3 * u, 3 * u, PALETTE["rock_dark"])
        px(surface, sx + 9 * u, sy + 9 * u, 3 * u, 3 * u, PALETTE["rock_dark"])
    elif t == "door" and st.get("metal"):
        px(surface, sx, sy, 16 * u, 16 * u, PALETTE["gun_dark"])
        if not st["open"]:
            px(surface, sx + 2 * u, sy + 1 * u, 12 * u, 14 * u, PALETTE["gun_metal"])
            px(surface, sx + 2 * u, sy + 5 * u, 12 * u, 1 * u, PALETTE["gun_dark"])
            px(surface, sx + 2 * u, sy + 10 * u, 12 * u, 1 * u, PALETTE["gun_dark"])
            px(surface, sx + 10 * u, sy + 7 * u, 2 * u, 2 * u, PALETTE["fire1"])
        else:
            px(surface, sx + 1 * u, sy + 1 * u, 3 * u, 14 * u, PALETTE["gun_metal"])
    elif t == "door":        
        px(surface, sx, sy, 16 * u, 16 * u, PALETTE["door_open_frame"])
        if not st["open"]:
            px(surface, sx + 2 * u, sy + 1 * u, 12 * u, 14 * u, PALETTE["door_plank"])
            px(surface, sx + 9 * u, sy + 7 * u, 2 * u, 2 * u, PALETTE["door_dark"])
        else:
            px(surface, sx + 1 * u, sy + 1 * u, 3 * u, 14 * u, PALETTE["door_plank"])
    elif t == "fire":
        px(surface, sx + 6 * u, sy + 10 * u, 4 * u, 4 * u, (42, 42, 42))
        if st.get("fuel", 1) > 0:
            flick = math.sin(pygame.time.get_ticks() / 90) * 1.5
            px(surface, sx + 6 * u, sy + 6 * u + flick, 4 * u, 6 * u, PALETTE["fire2"])
            px(surface, sx + 7 * u, sy + 3 * u + flick, 2 * u, 5 * u, PALETTE["fire1"])
        else:
            px(surface, sx + 6 * u, sy + 9 * u, 4 * u, 1 * u, (90, 60, 40))   # brasas apagadas
    elif t == "trapSpikes":
        px(surface, sx + 2 * u, sy + 11 * u, 12 * u, 3 * u, PALETTE["wall_dark"])
        for i in range(4):
            px(surface, sx + (3 + i * 3) * u, sy + 5 * u, 2 * u, 7 * u, PALETTE["gun_metal"])
            px(surface, sx + (3 + i * 3) * u, sy + 4 * u, 2 * u, 2 * u, (220, 220, 210))
    elif t == "trapBear":
        px(surface, sx + 3 * u, sy + 6 * u, 10 * u, 8 * u, PALETTE["gun_dark"])
        px(surface, sx + 5 * u, sy + 8 * u, 6 * u, 4 * u, PALETTE["door_dark"])
        for i in range(4):
            px(surface, sx + (4 + i * 2) * u, sy + 5 * u, 1 * u, 2 * u, PALETTE["gun_metal"])
            px(surface, sx + (4 + i * 2) * u, sy + 13 * u, 1 * u, 2 * u, PALETTE["gun_metal"])
        px(surface, sx + 7 * u, sy + 9 * u, 2 * u, 2 * u, PALETTE["crate_mark"])        
    else:
        px(surface, sx + 2 * u, sy + 6 * u, 12 * u, 8 * u, PALETTE["chest"])
        px(surface, sx + 2 * u, sy + 9 * u, 12 * u, 2 * u, PALETTE["chest_dark"])
    if "hp" in st and st["hp"] < st["max_hp"]:
        px(surface, sx + 1 * u, sy - 3 * u, 14 * u, 2 * u, (0, 0, 0))
        px(surface, sx + 1 * u, sy - 3 * u, 14 * u * max(0.0, st["hp"] / st["max_hp"]), 2 * u, (184, 67, 59))
    if t == "fire" and "fuel" in st:
        px(surface, sx + 2 * u, sy + 15 * u, 12 * u, 1 * u, (0, 0, 0))
        if st["fuel"] > 0:
            px(surface, sx + 2 * u, sy + 15 * u, 12 * u * min(1.0, st["fuel"] / FIRE_MAX_FUEL), 1 * u, PALETTE["fire1"])

def draw_character(surface, x, y, facing, vx, vy, anim_t, body_color, body_dark, head_color, hit_flash):
    sx, sy = camara.world_to_screen(x - 8, y - 8)
    u = PIXEL_SCALE
    bob = math.sin(anim_t * 8) if math.hypot(vx, vy) > 1 else 0
    bc = (255, 255, 255) if hit_flash > 0 else body_color
    hc = (255, 255, 255) if hit_flash > 0 else head_color
    px(surface, sx + 4 * u, sy + 7 * u + bob, 8 * u, 7 * u, bc)
    px(surface, sx + 4 * u, sy + 12 * u + bob, 3 * u, 3 * u, body_dark)
    px(surface, sx + 9 * u, sy + 12 * u + bob, 3 * u, 3 * u, body_dark)
    px(surface, sx + 5 * u, sy + 2 * u + bob, 6 * u, 6 * u, hc)
    if facing >= 0:
        px(surface, sx + 10 * u, sy + 8 * u + bob, 2 * u, 2 * u, body_dark)
    else:
        px(surface, sx + 4 * u, sy + 8 * u + bob, 2 * u, 2 * u, body_dark)

def draw_swing(surface, x, y, action_anim):
    if not action_anim or action_anim["t"] <= 0:
        return
    a = action_anim
    if a["type"] == "pick":
        baca_pico.draw_pick_swing(surface, x, y, a)
        return
    sx, sy = camara.world_to_screen(x - 8, y - 8)    
    u = PIXEL_SCALE
    alpha = max(0.0, a["t"] / a["total"])
    base = PALETTE["bullet"] if a["type"] == "gun" else (242, 239, 224)
    col = (*base, int(255 * alpha))
    dx, dy = a["dx"], a["dy"]
    surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    if dx > 0:
        pygame.draw.rect(surf, col, (sx + 13 * u, sy + 3 * u, 5 * u, 3 * u))
        pygame.draw.rect(surf, col, (sx + 16 * u, sy + 7 * u, 5 * u, 3 * u))
        pygame.draw.rect(surf, col, (sx + 13 * u, sy + 11 * u, 5 * u, 3 * u))
    elif dx < 0:
        pygame.draw.rect(surf, col, (sx - 2 * u, sy + 3 * u, 5 * u, 3 * u))
        pygame.draw.rect(surf, col, (sx - 5 * u, sy + 7 * u, 5 * u, 3 * u))
        pygame.draw.rect(surf, col, (sx - 2 * u, sy + 11 * u, 5 * u, 3 * u))
    elif dy < 0:
        pygame.draw.rect(surf, col, (sx + 2 * u, sy - 2 * u, 3 * u, 5 * u))
        pygame.draw.rect(surf, col, (sx + 6 * u, sy - 5 * u, 3 * u, 5 * u))
        pygame.draw.rect(surf, col, (sx + 10 * u, sy - 2 * u, 3 * u, 5 * u))
    else:
        pygame.draw.rect(surf, col, (sx + 2 * u, sy + 15 * u, 3 * u, 5 * u))
        pygame.draw.rect(surf, col, (sx + 6 * u, sy + 18 * u, 3 * u, 5 * u))
        pygame.draw.rect(surf, col, (sx + 10 * u, sy + 15 * u, 3 * u, 5 * u))
    surface.blit(surf, (0, 0))

def draw_build_preview(surface):
    dirx, diry = colision.cardinal_from_aim()
    tx = round((estado.player.x + dirx * TILE) / TILE) * TILE
    ty = round((estado.player.y + diry * TILE) / TILE) * TILE
    sx, sy = camara.world_to_screen(tx, ty)
    pulse = 0.35 + math.sin(pygame.time.get_ticks() / 150) * 0.15
    s = pygame.Surface((TILE * PIXEL_SCALE, TILE * PIXEL_SCALE), pygame.SRCALPHA)
    s.fill((244, 224, 74, int(255 * pulse)))
    surface.blit(s, (sx, sy))
    pygame.draw.rect(surface, (244, 224, 74), (sx, sy, TILE * PIXEL_SCALE, TILE * PIXEL_SCALE), 2)
    
_vision_mask = None

_light_masks = {}

def get_light_mask(radius, inner):
    """Alpha 255 en el centro (despeja del todo), cae solo en la orilla.
    RGB en negro para que al restar solo cambie el alpha, no el color del overlay."""
    R = int(radius * PIXEL_SCALE)
    key = (R, inner)
    m = _light_masks.get(key)
    if m is None:
        m = pygame.Surface((R * 2, R * 2), pygame.SRCALPHA)
        for r in range(R, 0, -1):
            frac = r / R
            t = max(0.0, min(1.0, (frac - inner) / (1.0 - inner)))
            smooth = t * t * (3 - 2 * t)
            pygame.draw.circle(m, (0, 0, 0, int(255 * (1.0 - smooth))), (R, R), r)
        _light_masks[key] = m
    return m

def carve_light(overlay, wx, wy, radius, inner, strength):
    """Abre un halo de luz en el overlay de la noche."""
    sx, sy = camara.world_to_screen(wx, wy)
    R = int(radius * PIXEL_SCALE)
    if sx < -R or sy < -R or sx > SCREEN_W + R or sy > SCREEN_H + R:
        return                                   # fuera de pantalla, no gasta nada
    mask = get_light_mask(radius, inner)
    light = mask.copy()
    light.fill((255, 255, 255, int(255 * strength)), special_flags=pygame.BLEND_RGBA_MULT)
    overlay.blit(light, (int(sx) - R, int(sy) - R), special_flags=pygame.BLEND_RGBA_SUB)

_cone_base = {}

def carve_cone(overlay, wx, wy, aim_x, aim_y, strength):
    """Abre un cono de luz hacia donde apunta el jugador."""
    sx, sy = camara.world_to_screen(wx, wy)
    R = int(CONE_RANGE * (baca_pico.LAMP_RANGE_MULT if estado.player.has_lamp else 1.0) * PIXEL_SCALE)    
    base = _cone_base.get(R)
    if base is None:                      # se dibuja una sola vez
        base = pygame.Surface((R * 2, R * 2), pygame.SRCALPHA)
        N = 18
        for i in range(N, 0, -1):
            f = i / N
            t = 1.0 - f
            alpha = int(255 * t * t * (3 - 2 * t))
            half = CONE_HALF_ANGLE * (0.65 + 0.30 * f)
            reach = R * (0.35 + 0.75 * f)
            pts = [(R, R)]
            for k in range(13):
                a = -half + 2 * half * k / 12
                pts.append((R + math.cos(a) * reach, R + math.sin(a) * reach))
            pygame.draw.polygon(base, (0, 0, 0, alpha), pts)
        _cone_base[R] = base
    ang = math.degrees(math.atan2(aim_y, aim_x))
    rot = pygame.transform.rotate(base, -ang)
    rot.fill((255, 255, 255, int(255 * strength)), special_flags=pygame.BLEND_RGBA_MULT)
    overlay.blit(rot, (int(sx - rot.get_width() / 2), int(sy - rot.get_height() / 2)),
                 special_flags=pygame.BLEND_RGBA_SUB)

def draw_night_overlay(surface):
    dark = refineria.MAP_DARK[fundidora.map_kind] if estado.in_mine else ciclo_dia.night_darkness()      
    if dark <= 0.01:
        return
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((6, 10, 25, int(dark * 0.97 * 255)))  # oscuridad base

    # Fogatas encendidas: luz con parpadeo (se atenúa al quedarse sin leña)
    for st in estado.structures:
        if st["type"] == "fire" and st.get("fuel", 1) > 0:
            fade = min(1.0, st.get("fuel", FIRE_DIM_TIME) / FIRE_DIM_TIME)
            flick = 0.85 + math.sin(pygame.time.get_ticks() / 130) * 0.05
            carve_light(overlay, st["x"], st["y"], FIRE_RADIUS, FIRE_INNER, dark * flick * fade)
            
    if estado.in_mine:                                   # brillo de la salida
        carve_light(overlay, MINE_INFO["exit"][0], MINE_INFO["exit"][1], 48, 0.4, dark * 0.9)
    else:                                         # brillo suave de la trampilla en la isla
        carve_light(overlay, CAVE_POS[0] * TILE + 8, CAVE_POS[1] * TILE + 8, 40, 0.4, dark * 0.5)
        
    if estado.in_mine and fundidora.map_kind == "foundry" and fundidora.furnace_burning():      # el horno ilumina la nave
        carve_light(overlay, fundidora.FOUNDRY_INFO["furnace"][0], fundidora.FOUNDRY_INFO["furnace"][1] + 24, 110, 0.4, dark * 0.9)
                    
    # Visión del jugador: solo un cono hacia donde apunta el mouse
    cone_strength = min(1.0, CONE_STRENGTH + (baca_pico.LAMP_STRENGTH_BONUS if estado.player.has_lamp else 0.0))
    carve_cone(overlay, estado.player.x, estado.player.y, estado.player.aim_x, estado.player.aim_y, dark * cone_strength)
    if CONE_NEAR_RADIUS > 0:
        carve_light(overlay, estado.player.x, estado.player.y, CONE_NEAR_RADIUS, 0.3, dark * cone_strength)

    surface.blit(overlay, (0, 0))
        
def draw_aim_cursor(surface):
    mx, my = pygame.mouse.get_pos()
    col = (244, 224, 74)
    pygame.draw.line(surface, col, (mx - 6, my), (mx + 6, my), max(1, UI_S))
    pygame.draw.line(surface, col, (mx, my - 6), (mx, my + 6), max(1, UI_S))

def draw_player_sprite(surface, x, y, sprite_dir, anim_t, moving):
    salto.draw_sombra(surface, x, y)      # sombra en el suelo cuando saltas
    y -= salto.altura()
    half = PLAYER_DISPLAY_SIZE / 2
    sx, sy = camara.world_to_screen(x - half, y - half)
    if PLAYER_SPRITES is not None:
        col = int(anim_t * 12) % 4 if moving else 0
        frame = PLAYER_SPRITES[sprite_dir][col]
        surface.blit(frame, (round(sx), round(sy)))
    else:
        # Respaldo: el dibujo de rectángulos de siempre, por si falta el archivo
        facing = -1 if sprite_dir == "left" else 1
        draw_character(surface, x, y, facing, 0, 0, anim_t,
                        PALETTE["player_body"], PALETTE["player_body_dark"],
                        PALETTE["player_head"], 0)

def draw_zombie_sprite(surface, x, y, sprite_dir, anim_t, moving, hit_flash):
    half = ZOMBIE_DISPLAY_SIZE / 2
    sx, sy = camara.world_to_screen(x - half, y - half)
    if ZOMBIE_SPRITES is not None and hit_flash <= 0:
        col = int(anim_t * 6) % 4 if moving else 0
        frame = ZOMBIE_SPRITES[sprite_dir][col]
        surface.blit(frame, (round(sx), round(sy)))
    else:
        # Respaldo: rectángulos de siempre (también cuando el zombi recibe un golpe,
        # para conservar el parpadeo blanco de hit_flash)
        facing = -1 if sprite_dir == "left" else 1
        draw_character(surface, x, y, facing, 0, 0, anim_t,
                        PALETTE["zombie_body"], PALETTE["zombie_body_dark"],
                        PALETTE["zombie_head"], hit_flash)

def draw_drop(surface, dr):
    sx, sy = camara.world_to_screen(dr["x"] - 8, dr["y"] - 8)
    u = PIXEL_SCALE
    bob = math.sin(pygame.time.get_ticks() / 300) * 1.5
    nm = "drop_" + dr["kind"]
    if dr["kind"] == "debris" and len(dr["items"]) == 1:
        only = next(iter(dr["items"]))
        if only in ("ingot", "dynamite", "diesel", "part"):
            nm = "drop_" + only    
    if draw_sprite(surface, nm, dr["x"], dr["y"] + bob):        
        return
    if dr["kind"] == "watch":        
        c = (int(sx + 8 * u), int(sy + 9 * u + bob))
        pygame.draw.circle(surface, (217, 183, 74), c, 4 * u)
        pygame.draw.circle(surface, (30, 30, 26), c, 3 * u)
    elif dr["kind"] == "debris" and set(dr["items"]) == {"ingot"}:
        px(surface, sx + 2 * u, sy + 9 * u, 12 * u, 4 * u, PALETTE["gun_metal"])
        px(surface, sx + 4 * u, sy + 5 * u, 8 * u, 4 * u, PALETTE["gun_metal"])
        px(surface, sx + 2 * u, sy + 12 * u, 12 * u, 1 * u, PALETTE["gun_dark"])
        px(surface, sx + 4 * u, sy + 8 * u, 8 * u, 1 * u, PALETTE["gun_dark"])
    elif dr["kind"] == "debris" and set(dr["items"]) == {"dynamite"}:
        px(surface, sx + 4 * u, sy + 6 * u, 3 * u, 8 * u, (176, 52, 44))
        px(surface, sx + 8 * u, sy + 6 * u, 3 * u, 8 * u, (176, 52, 44))
        px(surface, sx + 3 * u, sy + 9 * u, 9 * u, 2 * u, (230, 220, 190))
    elif dr["kind"] == "debris" and set(dr["items"]) == {"part"}:
        px(surface, sx + 3 * u, sy + 6 * u, 10 * u, 8 * u, PALETTE["gun_dark"])
        px(surface, sx + 5 * u, sy + 4 * u, 6 * u, 3 * u, PALETTE["gun_metal"])
        px(surface, sx + 6 * u, sy + 8 * u, 4 * u, 4 * u, (176, 150, 80))
        px(surface, sx + 3 * u, sy + 13 * u, 10 * u, 1 * u, (20, 20, 18))
    elif dr["kind"] == "debris" and set(dr["items"]) == {"diesel"}:        
        px(surface, sx + 4 * u, sy + 3 * u, 8 * u, 11 * u, (98, 78, 52))
        px(surface, sx + 4 * u, sy + 6 * u, 8 * u, 1 * u, (60, 46, 30))
        px(surface, sx + 4 * u, sy + 10 * u, 8 * u, 1 * u, (60, 46, 30))
        px(surface, sx + 6 * u, sy + 2 * u, 4 * u, 2 * u, (150, 150, 140))
    elif dr["kind"] == "debris":        
        px(surface, sx + 3 * u, sy + 9 * u, 10 * u, 5 * u, PALETTE["scrap_pile"])
        px(surface, sx + 3 * u, sy + 12 * u, 10 * u, 2 * u, PALETTE["scrap_pile_dark"])
        px(surface, sx + 6 * u, sy + 7 * u, 4 * u, 3 * u, PALETTE["wall"])
    elif dr["kind"] == "bear_trap":
        px(surface, sx + 3 * u, sy + 6 * u + bob, 10 * u, 8 * u, PALETTE["gun_dark"])
        px(surface, sx + 5 * u, sy + 8 * u + bob, 6 * u, 4 * u, PALETTE["door_dark"])
        for i in range(4):
            px(surface, sx + (4 + i * 2) * u, sy + 5 * u + bob, 1 * u, 2 * u, PALETTE["gun_metal"])
        pygame.draw.rect(surface, (244, 224, 74), (sx + 2 * u, sy + 4 * u + bob, 12 * u, 11 * u), 1)
    elif dr["kind"] == "baca_pick":
        pygame.draw.line(surface, (110, 90, 60), (sx + 3 * u, sy + 14 * u + bob), (sx + 12 * u, sy + 4 * u + bob), max(2, 2 * u))
        pygame.draw.line(surface, (170, 170, 160), (sx + 7 * u, sy + 3 * u + bob), (sx + 15 * u, sy + 8 * u + bob), max(2, 3 * u))
        pygame.draw.rect(surface, (244, 224, 74), (sx + 1 * u, sy + 2 * u + bob, 14 * u, 13 * u), 1)
    elif dr["kind"] == "baca_lamp":
        c = (int(sx + 8 * u), int(sy + 9 * u + bob))
        pygame.draw.circle(surface, (255, 220, 120), c, 5 * u)
        pygame.draw.circle(surface, (255, 245, 200), c, 3 * u)
        pygame.draw.rect(surface, (90, 80, 60), (sx + 5 * u, sy + 12 * u + bob, 6 * u, 3 * u))
    elif dr["kind"] == "baca_tonic":
        px(surface, sx + 6 * u, sy + 5 * u + bob, 4 * u, 3 * u, (150, 150, 140))
        px(surface, sx + 4 * u, sy + 8 * u + bob, 8 * u, 7 * u, (86, 150, 140))
        px(surface, sx + 5 * u, sy + 9 * u + bob, 2 * u, 3 * u, (190, 225, 215))
    elif dr["kind"] == "foundry_key":
        px(surface, sx + 3 * u, sy + 6 * u + bob, 5 * u, 5 * u, (176, 150, 80))
        px(surface, sx + 8 * u, sy + 8 * u + bob, 6 * u, 2 * u, (176, 150, 80))
        px(surface, sx + 12 * u, sy + 10 * u + bob, 2 * u, 3 * u, (176, 150, 80))
    elif dr["kind"] == "ammo":        
        px(surface, sx + 2 * u, sy + 7 * u + bob, 12 * u, 8 * u, PALETTE["crate"])
        px(surface, sx + 6 * u, sy + 9 * u + bob, 4 * u, 4 * u, PALETTE["crate_mark"])
    else:
        px(surface, sx + 1 * u, sy + 8 * u + bob, 14 * u, 2 * u, PALETTE["gun_dark"])
        px(surface, sx + 1 * u, sy + 10 * u + bob, 6 * u, 3 * u, PALETTE["gun_grip"])

def draw_boss(surface):
    if not estado.boss:
        return
    b = estado.boss
    sx, sy = camara.world_to_screen(b.x, b.y)
    moving = math.hypot(b.vx, b.vy) > 0.1
    if BOSS_SPRITES is not None and b.hit_flash <= 0:
        frame = BOSS_SPRITES[b.sprite_dir][int(b.anim_t * 5) % 4 if moving else 0]
        fw, fh = frame.get_size()
        surface.blit(frame, (round(sx - fw / 2), round(sy - fh / 2)))
    else:
        u = PIXEL_SCALE * BOSS_SCALE
        col = (255, 255, 255) if b.hit_flash > 0 else (110, 40, 40)
        pygame.draw.rect(surface, col, (sx - 6 * u, sy - 8 * u, 12 * u, 16 * u))
        pygame.draw.rect(surface, col, (sx - 4 * u, sy - 12 * u, 8 * u, 6 * u))
        
def draw_bear(surface, b):
    sx, sy = camara.world_to_screen(b.x, b.y)
    k = PIXEL_SCALE * b.size
    base = BEAR_TYPES[b.kind]["color"]
    warning = b.state == "windup" and (pygame.time.get_ticks() // 80) % 2 == 0
    if b.hit_flash > 0:
        col = (255, 255, 255)
    elif b.state == "stagger":
        col = (120, 130, 175)                       # mareado
    else:
        col = (240, 170, 50) if (warning and b.attack == "roar") else ((200, 60, 40) if warning else base)
    head = (255, 255, 255) if b.hit_flash > 0 else tuple(min(255, c + 30) for c in col)
    horiz = b.sprite_dir in ("left", "right")
    bw, bh = (16, 12) if horiz else (12, 16)
    px(surface, sx - bw * k / 2, sy - bh * k / 2, bw * k, bh * k, col)
    hx, hy = {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1)}[b.sprite_dir]
    cx, cy = sx + hx * 9 * k, sy + hy * 9 * k
    px(surface, cx - 3 * k, cy - 3 * k, 6 * k, 6 * k, head)
    px(surface, cx - 3 * k, cy - 4 * k, 2 * k, 2 * k, col)
    px(surface, cx + 1 * k, cy - 4 * k, 2 * k, 2 * k, col)
    top = sy - bh * k / 2
    if b.state == "windup":
        ex = FONT_MED.render("!", True, (255, 80, 60))
        surface.blit(ex, (sx - ex.get_width() // 2, top - ex.get_height() - 4))
    elif b.state == "stagger":
        ex = FONT_MED.render("* * *", True, (240, 220, 90))
        surface.blit(ex, (sx - ex.get_width() // 2, top - ex.get_height() - 4))
    if b.stagger > 0:                                # barrita de aturdimiento
        w = 14 * k
        frac = min(1.0, b.stagger / BEAR_TYPES[b.kind]["stagger_max"])
        px(surface, sx - w / 2, top - 6, w, 4, (0, 0, 0))
        px(surface, sx - w / 2, top - 6, w * frac, 4, (240, 220, 90))
    if b.kind == "weak" and b.hp < b.max_hp:
        w = 14 * k
        px(surface, sx - w / 2, top - 12, w, 3, (0, 0, 0))
        px(surface, sx - w / 2, top - 12, w * max(0.0, b.hp / b.max_hp), 3, (184, 67, 59))

def draw_bear_telegraph(surface, b):
    swiping = b.state == "windup" and b.attack == "swipe"
    charging = b.state == "windup" and b.attack == "charge"
    if not (swiping or charging or b.strike_t > 0):
        return
    cfg = BEAR_TYPES[b.kind]
    sx, sy = camara.world_to_screen(b.x, b.y)
    layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    if charging:
        ux, uy = b.aim_dx, b.aim_dy
        ox, oy = -uy, ux
        w = cfg["charge_hit_r"] * PIXEL_SCALE
        L = cfg["charge_dist"] * PIXEL_SCALE
        locked = b.state_t <= cfg["charge_lock"]
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 40)

        def lane(length):
            return [(sx + ox * w, sy + oy * w), (sx + ux * length + ox * w, sy + uy * length + oy * w),
                    (sx + ux * length - ox * w, sy + uy * length - oy * w), (sx - ox * w, sy - oy * w)]
        if locked:                                   # bloqueada: se acabó el tiempo de esquivar
            pygame.draw.polygon(layer, (255, 60, 40, 150), lane(L))
            pygame.draw.polygon(layer, (255, 240, 220, 255), lane(L), 3)
        else:
            pygame.draw.polygon(layer, (220, 40, 30, int(40 + 40 * pulse)), lane(L))
            pygame.draw.polygon(layer, (255, 110, 70, 200), lane(L), 2)
    else:
        R = cfg["swipe_range"] * PIXEL_SCALE
        ang = math.atan2(b.aim_dy, b.aim_dx)
        half = cfg["swipe_arc"]
        if swiping:
            prog = 1 - b.state_t / b.state_total
            pygame.draw.polygon(layer, (220, 40, 30, 45), makadewaa.cone_points(sx, sy, ang, half, R))
            pygame.draw.polygon(layer, (235, 70, 40, 130), makadewaa.cone_points(sx, sy, ang, half, R * prog))
            pygame.draw.polygon(layer, (255, 110, 70, 230), makadewaa.cone_points(sx, sy, ang, half, R), 2)
        else:
            a = int(220 * max(0.0, b.strike_t) / 0.15)
            pygame.draw.polygon(layer, (255, 230, 200, a), makadewaa.cone_points(sx, sy, ang, half, R))
    surface.blit(layer, (0, 0))

def update_shockwaves(dt):
    for w in estado.shockwaves:
        w["r"] += w["speed"] * dt
        if not w["hit"] and not estado.god_mode:
            d = mundo.dist(estado.player.x, estado.player.y, w["x"], w["y"])
            if w["r"] - w["thick"] <= d <= w["r"] + w["thick"]:
                w["hit"] = True
                estado.player.hp = max(0, estado.player.hp - w["dmg"])
                estado.log("¡La onda expansiva te golpeó!")
    estado.shockwaves[:] = [w for w in estado.shockwaves if w["r"] < w["max"] + w["thick"]]

def draw_slam_telegraph(surface, b):
    if b.state != "windup" or b.attack != "slam":
        return
    cfg = BEAR_TYPES[b.kind]
    sx, sy = camara.world_to_screen(b.x, b.y)
    R = int(cfg["slam_radius"] * PIXEL_SCALE)
    prog = 1 - b.state_t / b.state_total
    layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    pygame.draw.circle(layer, (220, 40, 30, 40), (int(sx), int(sy)), R)
    pygame.draw.circle(layer, (235, 70, 40, 90), (int(sx), int(sy)), max(1, int(R * prog)))
    pygame.draw.circle(layer, (255, 110, 70, 230), (int(sx), int(sy)), R, 3)
    surface.blit(layer, (0, 0))

def draw_shockwaves(surface):
    if not estado.shockwaves:
        return
    layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    for w in estado.shockwaves:
        sx, sy = camara.world_to_screen(w["x"], w["y"])
        fade = max(0.0, 1 - w["r"] / (w["max"] + w["thick"]))
        width = max(3, int(w["thick"] * 2 * PIXEL_SCALE))
        pygame.draw.circle(layer, (255, 220, 170, int(60 + 170 * fade)),
                           (int(sx), int(sy)), max(width, int(w["r"] * PIXEL_SCALE)), width)
    surface.blit(layer, (0, 0))

def render_bear_bar(surface):
    b = next((x for x in estado.bears if x.kind == "boss" and not x.dead), None)
    if not b:
        return
    if b.roar_t > 0:
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((150, 0, 0, int(110 * min(1, b.roar_t / BOSS_ROAR_TIME))))
        surface.blit(ov, (0, 0))
    y = 14 + (FONT_MED.get_height() + 6 * PIXEL_SCALE + 16 if estado.boss else 0)
    name = FONT_MED.render(f"{BEAR_NAME} — {BEAR_TITLE}", True, (210, 130, 60))
    surface.blit(name, (SCREEN_W // 2 - name.get_width() // 2, y))
    bw, bh = int(SCREEN_W * 0.4), 6 * PIXEL_SCALE
    bx, by = SCREEN_W // 2 - bw // 2, y + name.get_height() + 4
    pygame.draw.rect(surface, (0, 0, 0), (bx - 2, by - 2, bw + 4, bh + 4))
    pygame.draw.rect(surface, (170, 90, 30), (bx, by, int(bw * max(0, b.hp / b.max_hp)), bh))

def render_boss_bar(surface):
    if not estado.boss:
        return
    if estado.boss.roar_t > 0:   # destello rojo durante el gruñido
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((150, 0, 0, int(110 * min(1, estado.boss.roar_t / BOSS_ROAR_TIME))))
        surface.blit(ov, (0, 0))
    name = FONT_MED.render(f"{BOSS_NAME} — {BOSS_TITLE}", True, (200, 80, 80))
    surface.blit(name, (SCREEN_W // 2 - name.get_width() // 2, 14))
    bw, bh = int(SCREEN_W * 0.4), 6 * PIXEL_SCALE
    bx, by = SCREEN_W // 2 - bw // 2, 14 + name.get_height() + 4
    pygame.draw.rect(surface, (0, 0, 0), (bx - 2, by - 2, bw + 4, bh + 4))
    pygame.draw.rect(surface, (160, 30, 30), (bx, by, int(bw * max(0, estado.boss.hp / estado.boss.max_hp)), bh))

def render_world(surface):
    surface.fill((0, 0, 0))
    tiles_x = int(SCREEN_W / (TILE * PIXEL_SCALE)) + 3
    tiles_y = int(SCREEN_H / (TILE * PIXEL_SCALE)) + 3
    start_x = int(estado.camera_x // TILE) - 1
    start_y = int(estado.camera_y // TILE) - 1
    for yy in range(tiles_y):
        for xx in range(tiles_x):
            draw_tile(surface, start_x + xx, start_y + yy)

    for w in estado.wood_pickups:
        if w["active"]:
            draw_resource(surface, w)
    for r in estado.rock_pickups:
        if r["active"]:
            draw_resource(surface, r)
    for s in estado.scrap_pickups:
        if s["active"]:
            draw_resource(surface, s)
    for f in estado.food_pickups:
        if f["active"]:
            draw_resource(surface, f)

    if estado.gun_pickup and not estado.gun_pickup["taken"]:
        draw_gun_pickup(surface)
    for a in estado.ammo_pickups:
        if a["active"]:
            draw_ammo_pickup(surface, a)

    barco.draw_boat(surface)
    barco.draw_boat(surface)
    fundidora.draw_foundry_gate(surface)
    refineria.draw_refinery_gate(surface)
    deshuesadero.draw_junk_gate(surface)
    fundidora.draw_furnace(surface)
    for st in estado.structures:
        draw_structure(surface, st)        
    if estado.build_menu_open:
        draw_build_preview(surface)

    for b in estado.bullets:
        draw_bullet(surface, b)

    for z in estado.zombies:
        draw_zombie_sprite(surface, z.x, z.y, z.sprite_dir, z.anim_t,
                            math.hypot(z.vx, z.vy) > 0.1, z.hit_flash)
        
    mina.draw_mine_extras(surface)
    for dr in estado.drops:              # <- dropeo de boss
        draw_drop(surface, dr)
    draw_boss(surface)           
    
    for b in estado.bears:
        draw_bear_telegraph(surface, b)
        draw_slam_telegraph(surface, b)
        makadewaa.draw_roar_telegraph(surface, b)
    for b in estado.bears:
        draw_bear(surface, b)
    draw_shockwaves(surface)
    baca_jefe.draw_baca_all(surface)    
    exploracion.draw_world(surface)
    tiburones.draw_sharks(surface)

    draw_player_sprite(surface, estado.player.x, estado.player.y, estado.player.sprite_dir,
                        estado.player.anim_t, math.hypot(estado.player.vx, estado.player.vy) > 1)
    draw_swing(surface, estado.player.x, estado.player.y - salto.altura(), estado.player.action_anim)
    tonico.draw_dash_fx(surface)
    
    draw_night_overlay(surface)
    ambiente.draw_rain(surface)
    clima.draw_overlay(surface)
    draw_aim_cursor(surface)
