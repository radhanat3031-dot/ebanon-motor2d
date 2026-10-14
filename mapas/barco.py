"""El barco Esperanza.

Salió de ebanon.py (original), alrededor de las líneas 7085-7262.
"""

import pygame
from nucleo.ajustes import *  # noqa: F401,F403
from sistemas import construccion
from nucleo import estado


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global camara, dibujo, hud, mundo
    from interfaz import dibujo, hud
    from nucleo import mundo
    from sistemas import camara


    
# ============================================================================
# ESPERANZA: EL BARCO
# ============================================================================
BOAT_POS = [0, 0]              # centro del barco (lo fija gen_world)
BOAT_W, BOAT_H = 5, 3          # tamaño en tiles
DOCK_RANGE = 12 * TILE          # ← distancia máxima entre el muelle y el barco
BOAT_STAGES = [                # ← etapas y costos: edítalos libremente
    {"name": "Casco", "need": {"wood": 40, "ingot": 20}},
    {"name": "Motor", "need": {"part": 3, "ingot": 10}},
    {"name": "Combustible", "need": {"diesel": 5}},
    {"name": "Suministros", "need": {"food": 20, "med": 10, "wood": 20, "ingot": 10}},
]
BOAT_LABELS = {"wood": "Madera", "ingot": "Lingotes", "part": "Piezas de motor",
               "diesel": "Diésel", "food": "Comida", "med": "Medicina"}
boat = {"stage": 0, "loaded": {}, "open": False}
boat_ui = {"buttons": {}}
estado.player.cargo = {}              # lingotes, piezas y diésel que llevas

BUILD_COSTS["dock"] = {"wood": 10, "scrap": 0, "stone": 0}
BUILD_NAMES["dock"] = "Muelle construido."
BUILD_LABELS["dock"] = "8) Muelle  (Madera 10)"
BUILD_KEYS[pygame.K_8] = "dock"
construccion.BUILD_TITLES["dock"] = "Muelle"


def cargo_get(k):
    if k == "wood":
        return estado.player.inv_wood
    if k == "food":
        return estado.player.inv_food
    if k == "med":
        return estado.player.bandages
    return estado.player.cargo.get(k, 0)


def cargo_add(k, n):
    if k == "wood":
        estado.player.inv_wood += n
    elif k == "food":
        estado.player.inv_food += n
    elif k == "med":
        estado.player.bandages += n
    else:
        estado.player.cargo[k] = estado.player.cargo.get(k, 0) + n


def boat_moored():
    return any(st["type"] == "dock" and mundo.dist(st["x"], st["y"], BOAT_POS[0], BOAT_POS[1]) <= DOCK_RANGE
               for st in estado.structures)


def boat_interact():
    if BOAT_POS == [0, 0] or mundo.dist(estado.player.x, estado.player.y, BOAT_POS[0], BOAT_POS[1]) > 4 * TILE:
        return False
    if not boat_moored():
        estado.log("El casco está varado en la orilla. Necesitas un muelle cerca para amarrarlo.")
        return True
    boat["open"] = True
    return True


def boat_load(k):
    stage = boat["stage"]
    if stage >= len(BOAT_STAGES):
        return
    need = BOAT_STAGES[stage]["need"].get(k, 0)
    loaded = boat["loaded"].get(k, 0)
    if loaded >= need:
        estado.log("Eso ya está completo.")
        return
    n = min(cargo_get(k), need - loaded)
    if n <= 0:
        estado.log("No llevas eso en la mochila.")
        return
    cargo_add(k, -n)
    boat["loaded"][k] = loaded + n
    pygame.mixer.Channel(8).play(bag_sound)
    estado.log(f"Cargas {n} de {BOAT_LABELS[k].lower()} al barco.")
    if all(boat["loaded"].get(kk, 0) >= nn for kk, nn in BOAT_STAGES[stage]["need"].items()):
        boat["stage"] += 1
        boat["loaded"] = {}
        pygame.mixer.Channel(14).play(hammer_sound)
        estado.log(f"¡Etapa completada: {BOAT_STAGES[stage]['name']}!")


def handle_boat_click(pos, buttons):
    for k, r in buttons.items():
        if not r.collidepoint(pos):
            continue
        if k == "close":
            boat["open"] = False
        elif k.startswith("load_"):
            boat_load(k[5:])
        return


def render_boat_panel(surface):
    S = lambda n: int(n * UI_S)
    buttons = {}
    panel = pygame.Rect(SCREEN_W // 2 - S(210), SCREEN_H // 2 - S(200), S(420), S(400))
    hud.panel_bg(surface, panel)
    x = panel.x + S(16)
    y = panel.y + S(14)
    hud.draw_text(surface, "ESPERANZA", (x, y), FONT_MED, (217, 183, 74))
    y += S(34)
    stage = boat["stage"]
    for i, stg in enumerate(BOAT_STAGES):
        if i < stage:
            mark, col = "[x]", (143, 174, 76)
        elif i == stage:
            mark, col = "[>]", (217, 183, 74)
        else:
            mark, col = "[ ]", (110, 110, 100)
        hud.draw_text(surface, f"{mark} {i + 1}. {stg['name']}", (x, y), FONT_SMALL, col)
        y += S(20)
    y += S(12)
    if stage >= len(BOAT_STAGES):
        hud.draw_text(surface, "El barco está listo. Zarpar llegará en la próxima entrega.",
                  (x, y), FONT_SMALL, (143, 174, 76))
    else:
        cur = BOAT_STAGES[stage]
        hud.draw_text(surface, f"Etapa {stage + 1}: {cur['name']}  (clic en una fila para cargar)",
                  (x, y), FONT_SMALL, (217, 183, 74))
        y += S(26)
        for k, need in cur["need"].items():
            loaded = boat["loaded"].get(k, 0)
            have = cargo_get(k)
            rect = pygame.Rect(x, y, S(388), S(28))
            can = have > 0 and loaded < need
            pygame.draw.rect(surface, (58, 64, 45) if can else (40, 40, 36), rect)
            pygame.draw.rect(surface, (58, 64, 40), rect, max(1, UI_S))
            pygame.draw.rect(surface, (143, 174, 76),
                             (rect.x + 2, rect.bottom - S(5), int((rect.w - 4) * min(1.0, loaded / need)), S(3)))
            hud.draw_text(surface, f"{BOAT_LABELS[k]}: {loaded}/{need}     (llevas {have})",
                      (rect.x + S(8), rect.y + S(6)))
            buttons["load_" + k] = rect
            y += S(34)
    rc = pygame.Rect(panel.centerx - S(80), panel.bottom - S(50), S(160), S(34))
    pygame.draw.rect(surface, (58, 64, 45), rc)
    pygame.draw.rect(surface, (58, 64, 40), rc, max(1, UI_S))
    ct = FONT_MED.render("Cerrar", True, (217, 214, 194))
    surface.blit(ct, (rc.centerx - ct.get_width() // 2, rc.centery - ct.get_height() // 2))
    buttons["close"] = rc
    return buttons


def draw_boat(surface):
    if estado.in_mine or BOAT_POS == [0, 0]:
        return
    stage = min(boat["stage"], len(BOAT_STAGES))
    size = (BOAT_W * TILE, BOAT_H * TILE)
    if not (dibujo.draw_sprite(surface, "esperanza_%d" % stage, BOAT_POS[0], BOAT_POS[1], "center", False, size)
            or dibujo.draw_sprite(surface, "esperanza", BOAT_POS[0], BOAT_POS[1], "center", False, size)):
        sx, sy = camara.world_to_screen(BOAT_POS[0], BOAT_POS[1])
        u = PIXEL_SCALE
        x0, y0 = sx - 40 * u, sy - 24 * u
        dibujo.px(surface, x0 + 4 * u, y0 + 10 * u, 72 * u, 28 * u, PALETTE["wall_dark"])      # casco
        dibujo.px(surface, x0 + 8 * u, y0 + 14 * u, 64 * u, 20 * u, PALETTE["wall"])           # cubierta
        dibujo.px(surface, x0 + 60 * u, y0 + 16 * u, 16 * u, 16 * u, PALETTE["wall_dark"])     # proa
        if stage == 0:                                                                   # casco roto
            dibujo.px(surface, x0 + 24 * u, y0 + 8 * u, 16 * u, 12 * u, PALETTE["water2"])
            dibujo.px(surface, x0 + 44 * u, y0 + 28 * u, 14 * u, 10 * u, PALETTE["water2"])
        if stage >= 2:
            dibujo.px(surface, x0 + 12 * u, y0 + 18 * u, 12 * u, 12 * u, PALETTE["gun_dark"])  # motor
        if stage >= 3:
            dibujo.px(surface, x0 + 28 * u, y0 + 18 * u, 8 * u, 12 * u, PALETTE["fire2"])      # tanque
        if stage >= 4:
            dibujo.px(surface, x0 + 40 * u, y0 + 2 * u, 2 * u, 14 * u, PALETTE["wall"])        # mástil
    if mundo.dist(estado.player.x, estado.player.y, BOAT_POS[0], BOAT_POS[1]) <= 4 * TILE:
        sx, sy = camara.world_to_screen(BOAT_POS[0], BOAT_POS[1])
        t = FONT_SMALL.render("E: revisar el barco", True, (244, 224, 74))
        surface.blit(t, (sx - t.get_width() // 2, sy - 30 * PIXEL_SCALE - t.get_height()))


def debug_boat():
    """Atajo de prueba (Ctrl+B): materiales del barco en la mochila."""
    estado.player.cargo = {"ingot": 30, "part": 3, "diesel": 5}
    estado.player.inv_wood += 40
    estado.player.inv_food += 20
    estado.player.bandages += 10
    estado.log("PRUEBA: materiales del barco en la mochila.")
