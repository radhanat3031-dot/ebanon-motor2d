"""HUD y menú de construcción.

Salió de ebanon.py (original), alrededor de las líneas 4446-4574.
"""

import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global baca_jefe, barco, ciclo_dia, construccion, deshuesadero
    global dibujo, estado, fundidora, mina, neri_jefe
    global refineria
    global hogar
    global clima
    global estaciones
    global exploracion
    global eventos
    from interfaz import dibujo
    from jefes import baca_jefe, neri_jefe
    from mapas import barco, deshuesadero, fundidora, mina, refineria
    from nucleo import estado
    from sistemas import ciclo_dia, construccion
    from sistemas import hogar
    from sistemas import clima
    from sistemas import estaciones
    from sistemas import exploracion
    from sistemas import eventos


    
def draw_text(surface, text, pos, font=FONT_SMALL, color=(217, 214, 194)):
    img = font.render(text, True, color)
    surface.blit(img, pos)
    return img.get_rect(topleft=pos)

def render_hud(surface):
    panel_w = 200 * UI_S
    panel_h = 84 * UI_S
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((11, 13, 10, 190))
    surface.blit(panel, (10 * UI_S, 10 * UI_S))
    bars = [("PV", estado.player.hp, estado.player.max_hp, (184, 67, 59)),
            ("ST", estado.player.stamina, estado.player.max_stamina, (143, 174, 76)),
            ("HB", estado.player.hunger, estado.player.max_hunger, (201, 138, 75))]
    for i, (label, val, mx, color) in enumerate(bars):
        y = int((18 + i * 22) * UI_S)
        draw_text(surface, label, (int(18 * UI_S), y))
        pygame.draw.rect(surface, (0, 0, 0), (int(52 * UI_S), y + 2, int(140 * UI_S), int(10 * UI_S)))
        w = int(int(138 * UI_S) * max(0, val / mx))
        pygame.draw.rect(surface, color, (int(53 * UI_S), y + 3, w, int(8 * UI_S)))

    day_txt = ("NOCHE " if ciclo_dia.is_night() else "DÍA ") + str(estado.day_count)
    hours = int(estado.world_time * 24) % 24
    minutes = int((estado.world_time * 24 * 60) % 60)
    if estado.player.has_watch:
        day_txt += f"  {hours:02d}:{minutes:02d}"
    day_color = (92, 122, 134) if ciclo_dia.is_night() else (217, 183, 74)
    dbadge = FONT_MED.render(day_txt, True, day_color)
    surface.blit(dbadge, (SCREEN_W - dbadge.get_width() - 14, 14))

    weapon_txt = f"Arma: [{WEAPON_LABELS[estado.player.equipped]}]  (TAB cambia)"
    if estado.player.equipped in ("gun", "shotgun"):
        weapon_txt += f"   Balas: {estado.player.ammo}"
    elif estado.player.equipped == "axe":
        weapon_txt += f"   Durabilidad: {estado.player.axe_durability}/{TOOL_DURABILITY_MAX['axe']}"
    elif estado.player.equipped == "pickaxe":
            weapon_txt += f"   Durabilidad: {estado.player.pickaxe_durability}/{TOOL_DURABILITY_MAX['pickaxe']}"    
    elif estado.player.equipped == "bat":
        weapon_txt += f"   Durabilidad: {estado.player.bat_durability}/{TOOL_DURABILITY_MAX['bat']}"
    elif estado.player.equipped == "hammer":
        weapon_txt += "   Clic: reparar · X: desmontar"     
    elif estado.player.equipped == "baca_pick":
        weapon_txt += "   E: romper roca o ruina (gasta TODA la estamina)"   
    wtxt = FONT_SMALL.render(weapon_txt, True, (217, 183, 74))
    surface.blit(wtxt, (SCREEN_W - wtxt.get_width() - 14, 44))

    cargo_txt = "".join(f"{barco.BOAT_LABELS[k]}:{v}  " for k, v in estado.player.cargo.items() if v > 0)
    inv_txt = (f"Madera:{estado.player.inv_wood}  Chatarra:{estado.player.inv_scrap}  Piedra:{estado.player.inv_stone}  "
               f"Comida:{estado.player.inv_food}  Vendas:{estado.player.bandages}  {cargo_txt}"
               f"Mochila:{estado.current_capacity()}/{MAX_CAPACITY}")    
    itxt = FONT_SMALL.render(inv_txt, True, (217, 183, 74))
    surface.blit(itxt, (SCREEN_W - itxt.get_width() - 14, 66))

    hint = FONT_SMALL.render(
        "WASD mover · Mouse apuntar · Espacio/Clic atacar · E recoger · Q mochila · B construir · TAB arma",
        True, (141, 145, 120))
    surface.blit(hint, (14, SCREEN_H - 24))

    for i, line in enumerate(estado.log_lines[-5:]):
        t = FONT_SMALL.render(line, True, (141, 145, 120))
        surface.blit(t, (14, SCREEN_H - 155 + i * 20))
        
    dibujo.render_boss_bar(surface)
    
    dibujo.render_bear_bar(surface)
    baca_jefe.render_baca_bar(surface)
    hogar.draw_status(surface)
    clima.draw_status(surface)
    estaciones.draw_status(surface)
    exploracion.draw_hud(surface)
    eventos.draw_banner(surface)
    mina.draw_cave_arrow(surface)
    neri_jefe.render_neri_bar(surface)
    fundidora.draw_foundry_arrow(surface)
    refineria.draw_refinery_arrow(surface)
    deshuesadero.draw_junk_arrow(surface)

def panel_bg(surface, rect, alpha=235):
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    s.fill((20, 23, 15, alpha))
    surface.blit(s, rect.topleft)
    pygame.draw.rect(surface, (58, 64, 40), rect, max(1, UI_S))

def render_build_menu(surface):
    buttons = {}
    types = ["wall", "fire", "chest", "wallStone", "door", "trapSpikes", "trapBear", "dock", "doorMetal", "bench"]
    panel_w = 320 * UI_S
    panel_h = int((48 + len(types) * 32) * UI_S)
    x0 = SCREEN_W - panel_w - int(16 * UI_S)
    y0 = max(int(90 * UI_S), SCREEN_H // 2 - panel_h // 2)
    y0 = min(y0, SCREEN_H - panel_h - int(10 * UI_S))    
    panel = pygame.Rect(x0, y0, panel_w, panel_h)
    panel_bg(surface, panel)
    estado.build_ui["panel"] = panel
    draw_text(surface, "CONSTRUIR", (panel.x + int(12 * UI_S), panel.y + int(8 * UI_S)), FONT_MED, (217, 183, 74))
    for i, t in enumerate(types):
        rect = pygame.Rect(x0 + int(10 * UI_S), y0 + int(38 * UI_S) + i * int(32 * UI_S), panel_w - int(20 * UI_S), int(28 * UI_S))
        unlocked = construccion.is_buildable(t)
        ok = construccion.can_afford(t) and unlocked        # si está seleccionada, usar color distinto y borde más visible
        if estado.build_selected == t:
            color = (58, 64, 45) if ok else (40, 30, 30)
            border_color = (217, 183, 74)
        else:
            color = (58, 64, 45) if ok else (40, 30, 30)
            border_color = (58, 64, 40) if ok else (60, 40, 40)
        pygame.draw.rect(surface, color, rect)
        border = (244, 224, 74) if t == estado.build_selected else ((58, 64, 40) if ok else (60, 40, 40))
        pygame.draw.rect(surface, border, rect, max(1, UI_S))
        txt_color = (217, 214, 194) if ok else (110, 110, 110)
        label = BUILD_LABELS[t] if unlocked else BUILD_LABELS[t][:2] + " ???  (bloqueado)"
        draw_text(surface, label, (rect.x + int(8 * UI_S), rect.y + int(6 * UI_S)), FONT_SMALL, txt_color)
        buttons[t] = rect
    return buttons

def _weapon_row(surface, panel, y, name, owned, cost_ok, cost_label):
    rect = pygame.Rect(panel.x + int(16 * UI_S), y, int(308 * UI_S), int(32 * UI_S))
    if not owned:
        pygame.draw.rect(surface, (58, 64, 45) if cost_ok else (40, 30, 30), rect)
        pygame.draw.rect(surface, (58, 64, 40), rect, max(1, UI_S))
        draw_text(surface, cost_label, (rect.x + int(8 * UI_S), rect.y + int(8 * UI_S)))
        return rect, "craft"
    equipped = estado.player.equipped == name
    pygame.draw.rect(surface, (74, 90, 45) if equipped else (58, 64, 45), rect)
    pygame.draw.rect(surface, (217, 183, 74) if equipped else (58, 64, 40), rect, max(1, UI_S))
    dur_suffix = ""
    if name == "axe":
        dur_suffix = f"  [{estado.player.axe_durability}/{TOOL_DURABILITY_MAX['axe']}]"
    elif name == "pickaxe":
            dur_suffix = f"  [{estado.player.pickaxe_durability}/{TOOL_DURABILITY_MAX['pickaxe']}]"    
    elif name == "bat":
        dur_suffix = f"  [{estado.player.bat_durability}/{TOOL_DURABILITY_MAX['bat']}]"
    label = f"{WEAPON_LABELS[name]}: {'EQUIPADA (clic para guardar)' if equipped else 'en mochila (clic para equipar)'}{dur_suffix}"
    draw_text(surface, label, (rect.x + int(8 * UI_S), rect.y + int(8 * UI_S)))
    return rect, "equip"
