"""La Fundidora: mapa, horno y lingotes.

Salió de ebanon.py (original), alrededor de las líneas 7267-7692.
"""

import math
import pygame
from nucleo.ajustes import *  # noqa: F401,F403
from mapas import barco
from sistemas import construccion


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global camara, dibujo, estado, hud, mundo
    global transicion
    from interfaz import dibujo, hud
    from mapas import transicion
    from nucleo import estado, mundo
    from sistemas import camara


    
# ============================================================================
# MAPAS FIJOS: LA FUNDIDORA
# ============================================================================
FOUNDRY_DARKNESS = 0.55          # ← oscuridad dentro de la fundidora (0 a 1)
FOUNDRY_ZOMBIE_CAP = 5           # ← máximo de zombis vivos allí
FOUNDRY_RECIPE_SCRAP = 2         # ← chatarra por lingote
FOUNDRY_RECIPE_WOOD = 1          # ← madera por lingote
FOUNDRY_SMELT_TIME = 8.0         # ← segundos por lingote
FOUNDRY_FURNACE_CAP = 40         # ← máximo de cada material dentro del horno
DOOR_METAL_HP = 390              # ← vida de la puerta de metal (la de madera tiene 80)
map_kind = "mine"                # "mine" o "foundry": qué mapa interior está activo
foundry_stash = None
FOUNDRY_POS = [0, 0]             # tile del portón en la isla (lo fija gen_world)
FOUNDRY_INFO = {"furnace": (0, 0)}
furnace = {"scrap": 0, "wood": 0, "ingots": 0, "t": 0.0}

BUILD_COSTS["doorMetal"] = {"wood": 0, "scrap": 0, "stone": 0, "ingot": 3}
BUILD_NAMES["doorMetal"] = "Puerta de metal instalada."
BUILD_LABELS["doorMetal"] = "9) Puerta de metal  (Lingotes 3)"
BUILD_KEYS[pygame.K_9] = "doorMetal"
construccion.BUILD_TITLES["doorMetal"] = "Puerta de metal"
LOCKED_BUILDS["doorMetal"] = "metal_door"


def gen_foundry():
    """Mapa fijo de la fundidora (siempre igual). Edita los rectángulos para cambiar su forma."""
    
    W, H = 60, 36
    WALL, FLOOR = mundo.TILE_TYPE["ruin"], mundo.TILE_TYPE["hill"]
    WATER, ROAD, CAVE = mundo.TILE_TYPE["water"], mundo.TILE_TYPE["road"], mundo.TILE_TYPE["cave"]
    g = [[WALL] * W for _ in range(H)]

    def rect(x0, y0, x1, y1, t=FLOOR):
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                g[yy][xx] = t

    rect(10, 2, 49, 17)                        # nave principal
    rect(2, 5, 8, 16)                          # bodega oeste
    rect(9, 10, 9, 11)                         # puerta a la bodega oeste
    rect(51, 5, 57, 16)                        # bodega este
    rect(50, 10, 50, 11)                       # puerta a la bodega este
    rect(28, 18, 31, 21)                       # pasillo hacia el patio
    rect(2, 22, 57, 33)                        # patio de entrada
    for (a, b, c, d) in ((8, 24, 13, 25), (46, 24, 51, 25), (18, 28, 23, 29), (36, 28, 41, 29)):
        rect(a, b, c, d, WALL)                 # contenedores
    for (a, b) in ((16, 7), (23, 13), (36, 7), (36, 13), (16, 14), (43, 7)):
        rect(a, b, a + 1, b + 1, WALL)         # pilares de la nave
    rect(10, 11, 49, 11, ROAD)                 # vías
    rect(2, 27, 57, 27, ROAD)
    rect(4, 30, 9, 32, WATER)                  # estanques de enfriamiento
    rect(40, 14, 46, 16, WATER)
    rect(27, 3, 31, 4, WALL)                   # el horno (su dibujo se pone encima)
    g[34][30] = CAVE                           # salida
    loot = []
    for (x, y) in ((12, 4), (13, 15), (46, 4), (47, 8), (4, 6), (6, 14), (53, 6), (55, 14),
                   (5, 24), (53, 24), (14, 31), (48, 31), (28, 25), (33, 25)):
        loot.append(("scrap", x, y))
    for (x, y) in ((3, 8), (7, 12), (54, 9), (56, 15), (20, 24), (40, 24), (24, 31), (34, 31)):
        loot.append(("wood", x, y))
    for (x, y) in ((20, 3), (55, 7)):
        loot.append(("ammo", x, y))
    for (x, y) in ((3, 15), (56, 6)):
        loot.append(("herb", x, y))
    mundo.WORLD = g
    estado.WORLD_MASK = [[True] * W for _ in range(H)]
    estado.WORLD_W, estado.WORLD_H = W, H
    estado.WORLD_CENTER = (W // 2, H // 2)
    estado.WORLD_RADIUS = max(W, H)
    MINE_INFO["exit"] = (30 * TILE + 8, 34 * TILE + 8)
    MINE_INFO["start"] = (30 * TILE + 8, 32 * TILE + 8)
    MINE_INFO["lair"] = (-99999, -99999)       # aquí no hay guarida
    FOUNDRY_INFO["furnace"] = (29 * TILE + 8, 3.5 * TILE + 8)
    return loot


def spawn_foundry_resources(loot):
    for lst in (estado.wood_pickups, estado.rock_pickups, estado.scrap_pickups, estado.food_pickups, estado.ammo_pickups):
        lst.clear()
    for kind, tx, ty in loot:
        pos = {"x": tx * TILE + 8, "y": ty * TILE + 8, "active": True, "timer": 0.0}
        if kind == "wood":
            estado.wood_pickups.append(dict(pos, type="tree"))
        elif kind == "scrap":
            estado.scrap_pickups.append(dict(pos, type="scrap"))
        elif kind == "herb":
            estado.food_pickups.append(dict(pos, type="herb"))
        else:
            estado.ammo_pickups.append(pos)


# ── Portón de la isla ──
def foundry_gate_interact():
    if FOUNDRY_POS == [0, 0]:
        return False
    if mundo.dist(estado.player.x, estado.player.y, FOUNDRY_POS[0] * TILE + 8, FOUNDRY_POS[1] * TILE + 8) > 3 * TILE:
        return False
    if not estado.player.has_foundry_key:
        estado.log("Un portón de acero con un candado oxidado. Necesitas la llave de la fundidura.")
        return True
    transicion.enter_map("foundry")
    return True


def draw_foundry_gate(surface):
    if estado.in_mine or FOUNDRY_POS == [0, 0]:
        return
    wx, wy = FOUNDRY_POS[0] * TILE + 8, FOUNDRY_POS[1] * TILE + 8
    sx, sy = camara.world_to_screen(wx, wy)
    u = PIXEL_SCALE
    if not dibujo.draw_sprite(surface, "foundry_gate", wx, wy, "center", False, (48, 48)):
        x0, y0 = sx - 24 * u, sy - 24 * u
        dibujo.px(surface, x0, y0, 48 * u, 48 * u, PALETTE["rock_dark"])
        dibujo.px(surface, x0 + 4 * u, y0 + 4 * u, 40 * u, 40 * u, PALETTE["gun_dark"])
        dibujo.px(surface, x0 + 23 * u, y0 + 4 * u, 2 * u, 40 * u, (10, 10, 10))
        for i in range(3):
            dibujo.px(surface, x0 + 4 * u, y0 + (10 + i * 12) * u, 40 * u, 2 * u, PALETTE["gun_metal"])
        if not estado.player.has_foundry_key:
            dibujo.px(surface, x0 + 21 * u, y0 + 22 * u, 6 * u, 6 * u, (176, 150, 80))    # candado
    if mundo.dist(estado.player.x, estado.player.y, wx, wy) <= 3 * TILE:
        msg = "E: abrir el portón" if estado.player.has_foundry_key else "Portón cerrado con candado"
        t = FONT_SMALL.render(msg, True, (244, 224, 74))
        surface.blit(t, (sx - t.get_width() // 2, sy - 28 * u - t.get_height()))


def draw_foundry_arrow(surface):
    """Flecha hacia la fundidora: solo si ya tienes la llave."""
    if estado.in_mine or not estado.player.has_foundry_key or FOUNDRY_POS == [0, 0]:
        return
    wx, wy = FOUNDRY_POS[0] * TILE + 8, FOUNDRY_POS[1] * TILE + 8
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
    col = (170, 190, 205)
    pygame.draw.polygon(surface, col, [(ax + dx * 14 * s, ay + dy * 14 * s),
                                       (ax - dx * 8 * s - dy * 10 * s, ay - dy * 8 * s + dx * 10 * s),
                                       (ax - dx * 8 * s + dy * 10 * s, ay - dy * 8 * s - dx * 10 * s)])
    t = FONT_SMALL.render(f"Fundidora {int(mundo.dist(estado.player.x, estado.player.y, wx, wy) // TILE)}", True, col)
    surface.blit(t, (ax - dx * 26 * s - t.get_width() / 2, ay - dy * 26 * s - t.get_height() / 2))


# ── El horno ──
def furnace_burning():
    return furnace["scrap"] >= FOUNDRY_RECIPE_SCRAP and furnace["wood"] >= FOUNDRY_RECIPE_WOOD


def update_furnace(dt):
    if not barco.boat["open"]:
        barco.boat["panel"] = None
    f = furnace
    if furnace_burning():
        f["t"] += dt
        if f["t"] >= FOUNDRY_SMELT_TIME:
            f["t"] = 0.0
            f["scrap"] -= FOUNDRY_RECIPE_SCRAP
            f["wood"] -= FOUNDRY_RECIPE_WOOD
            f["ingots"] += 1
    else:
        f["t"] = 0.0


def furnace_interact():
    fx, fy = FOUNDRY_INFO["furnace"]
    if mundo.dist(estado.player.x, estado.player.y, fx, fy) > 4 * TILE:
        return False
    barco.boat["open"] = True
    barco.boat["panel"] = "furnace"
    return True


def _furnace_load(key, attr):
    n = min(getattr(estado.player, attr), FOUNDRY_FURNACE_CAP - furnace[key])
    if n <= 0:
        estado.log("No tienes eso o el horno ya está lleno.")
        return
    setattr(estado.player, attr, getattr(estado.player, attr) - n)
    furnace[key] += n
    pygame.mixer.Channel(8).play(bag_sound)
    estado.log(f"Cargas {n} de {'chatarra' if key == 'scrap' else 'madera'} al horno.")


def _furnace_take():
    n = min(furnace["ingots"], MAX_CAPACITY - estado.current_capacity())
    if n <= 0:
        estado.log("No hay lingotes o tu mochila está llena.")
        return
    furnace["ingots"] -= n
    estado.player.cargo["ingot"] = estado.player.cargo.get("ingot", 0) + n
    pygame.mixer.Channel(14).play(hammer_sound)
    estado.log(f"Recoges {n} lingote(s).")
    if "metal_door" not in estado.player.recipes:
        estado.player.recipes.add("metal_door")
        estado.log("Aprendiste a fabricar puertas de metal (menú B, tecla 9).")


def render_furnace_panel(surface):
    S = lambda n: int(n * UI_S)
    buttons = {}
    panel = pygame.Rect(SCREEN_W // 2 - S(200), SCREEN_H // 2 - S(170), S(400), S(340))
    hud.panel_bg(surface, panel)
    x = panel.x + S(16)
    y = panel.y + S(14)
    hud.draw_text(surface, "HORNO DE LA FUNDIDORA", (x, y), FONT_MED, (217, 183, 74))
    y += S(30)
    hud.draw_text(surface, f"Receta: {FOUNDRY_RECIPE_SCRAP} chatarra + {FOUNDRY_RECIPE_WOOD} madera = "
                       f"1 lingote ({int(FOUNDRY_SMELT_TIME)} s)", (x, y), FONT_SMALL, (141, 145, 120))
    y += S(28)
    rows = (("load_scrap", f"Chatarra en el horno: {furnace['scrap']}/{FOUNDRY_FURNACE_CAP}"
                          f"     (llevas {estado.player.inv_scrap})",
             estado.player.inv_scrap > 0 and furnace["scrap"] < FOUNDRY_FURNACE_CAP),
            ("load_wood", f"Madera en el horno: {furnace['wood']}/{FOUNDRY_FURNACE_CAP}"
                          f"     (llevas {estado.player.inv_wood})",
             estado.player.inv_wood > 0 and furnace["wood"] < FOUNDRY_FURNACE_CAP),
            ("take", f"Lingotes listos: {furnace['ingots']}     (clic para recoger)", furnace["ingots"] > 0))
    for key, text, can in rows:
        rect = pygame.Rect(x, y, S(368), S(32))
        pygame.draw.rect(surface, (58, 64, 45) if can else (40, 40, 36), rect)
        pygame.draw.rect(surface, (58, 64, 40), rect, max(1, UI_S))
        hud.draw_text(surface, text, (rect.x + S(8), rect.y + S(8)))
        buttons[key] = rect
        y += S(40)
    pw = S(368)
    pygame.draw.rect(surface, (0, 0, 0), (x, y, pw, S(10)))
    pygame.draw.rect(surface, (214, 128, 56),
                     (x + 1, y + 1, int((pw - 2) * min(1.0, furnace["t"] / FOUNDRY_SMELT_TIME)), S(8)))
    hud.draw_text(surface, "Fundiendo..." if furnace_burning() else "Apagado: faltan materiales",
              (x, y + S(16)), FONT_SMALL, (217, 183, 74))
    rc = pygame.Rect(panel.centerx - S(80), panel.bottom - S(50), S(160), S(34))
    pygame.draw.rect(surface, (58, 64, 45), rc)
    pygame.draw.rect(surface, (58, 64, 40), rc, max(1, UI_S))
    ct = FONT_MED.render("Cerrar", True, (217, 214, 194))
    surface.blit(ct, (rc.centerx - ct.get_width() // 2, rc.centery - ct.get_height() // 2))
    buttons["close"] = rc
    return buttons


def handle_furnace_click(pos, buttons):
    for k, r in buttons.items():
        if not r.collidepoint(pos):
            continue
        if k == "close":
            barco.boat["open"] = False
        elif k == "load_scrap":
            _furnace_load("scrap", "inv_scrap")
        elif k == "load_wood":
            _furnace_load("wood", "inv_wood")
        elif k == "take":
            _furnace_take()
        return


# El horno reutiliza el panel del barco (mismas teclas y pausa): estos dos "desvían" según cuál esté abierto
_render_boat_panel_orig = barco.render_boat_panel
_handle_boat_click_orig = barco.handle_boat_click


def render_boat_panel(surface):
    if barco.boat.get("panel") == "furnace":
        return render_furnace_panel(surface)
    return _render_boat_panel_orig(surface)


def handle_boat_click(pos, buttons):
    if barco.boat.get("panel") == "furnace":
        return handle_furnace_click(pos, buttons)
    return _handle_boat_click_orig(pos, buttons)


def draw_furnace(surface):
    if not estado.in_mine or map_kind != "foundry":
        return
    fx, fy = FOUNDRY_INFO["furnace"]
    sx, sy = camara.world_to_screen(fx, fy)
    u = PIXEL_SCALE
    if not dibujo.draw_sprite(surface, "furnace", fx, fy, "center", False, (80, 48)):
        x0, y0 = sx - 40 * u, sy - 24 * u
        dibujo.px(surface, x0, y0, 80 * u, 48 * u, PALETTE["rock_dark"])
        dibujo.px(surface, x0 + 4 * u, y0 + 4 * u, 72 * u, 40 * u, PALETTE["gun_dark"])
        dibujo.px(surface, x0 + 28 * u, y0 + 16 * u, 24 * u, 26 * u, (12, 10, 10))        # boca
        dibujo.px(surface, x0 + 34 * u, y0 - 2 * u, 12 * u, 6 * u, PALETTE["gun_dark"])    # chimenea
        if furnace_burning():
            flick = math.sin(pygame.time.get_ticks() / 90) * 2
            dibujo.px(surface, x0 + 31 * u, y0 + 24 * u + flick, 18 * u, 16 * u, PALETTE["fire2"])
            dibujo.px(surface, x0 + 35 * u, y0 + 20 * u + flick, 10 * u, 14 * u, PALETTE["fire1"])
    if mundo.dist(estado.player.x, estado.player.y, fx, fy) <= 4 * TILE:
        t = FONT_SMALL.render("E: usar el horno", True, (244, 224, 74))
        surface.blit(t, (sx - t.get_width() // 2, sy + 28 * u))


def debug_foundry():
    """Atajo de prueba (Ctrl+F): llave de la fundidura y materiales para fundir."""
    estado.player.has_foundry_key = True
    estado.player.inv_scrap += 10
    estado.player.inv_wood += 8
    estado.log("PRUEBA: tienes la llave de la fundidura, chatarra y madera.")
