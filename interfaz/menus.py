"""Mochila, almacén, pantallas de inicio, slots, nombre, pausa y game over.

Salió de ebanon.py (original), alrededor de las líneas 4576-5461.
"""

import os
import time
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global almacen, barco, combate, construccion, crafteo
    global estado, guardado, hud, partida
    global estaciones
    global inventario
    from interfaz import hud
    from mapas import barco
    from nucleo import estado
    from sistemas import almacen, combate, construccion, crafteo, guardado, partida
    from sistemas import estaciones
    from interfaz import inventario


def render_inventory(surface):
    """La mochila se dibuja en interfaz/inventario.py (cuadrícula con iconos, estilo Valheim)."""
    return inventario.render(surface)

def handle_inventory_click(pos, buttons):
    if buttons.get("repair") and buttons["repair"].collidepoint(pos):
        estaciones.repair_all()
        return
    for k, r in buttons.items():
        if k.startswith("drop_") and r.collidepoint(pos):
            cantidad = 999 if (pygame.key.get_mods() & pygame.KMOD_SHIFT) else 1
            construccion.drop_item(k[5:], cantidad)
            return
    if buttons.get("food") and buttons["food"].collidepoint(pos):
        crafteo.use_food()
        return
    if buttons.get("bandage") and buttons["bandage"].collidepoint(pos):
        crafteo.use_bandage()
        return
    for name, craft_fn in (("axe", crafteo.craft_axe), ("pickaxe", crafteo.craft_pickaxe), ("bat", crafteo.craft_bat), ("hammer", crafteo.craft_hammer), ("gun", None), ("shotgun", None), ("baca_pick", None)):
        entry = buttons.get(name)
        if not entry:
            continue
        rect, kind = entry
        if rect.collidepoint(pos):
            if kind == "craft" and craft_fn:
                if estaciones.can_craft(name):
                    craft_fn()
                    estaciones.after_craft(name)
            else:
                combate.toggle_equip(name)
            return

# Render del almacén
def render_storage(surface):
    buttons = {}
    # Atajo de escala, igual al patrón que ya usas en todo el archivo
    S = lambda n: int(n * UI_S)

    panel_w, panel_h = S(460), S(460)
    panel = pygame.Rect(SCREEN_W // 2 - panel_w // 2, SCREEN_H // 2 - panel_h // 2, panel_w, panel_h)
    hud.panel_bg(surface, panel)

    pad = S(16)
    y = panel.y + S(14)

    # Título centrado
    title_surf = FONT_MED.render("ALMACÉN", True, (217, 183, 74))
    surface.blit(title_surf, (panel.centerx - title_surf.get_width() // 2, y))
    y += S(30)

    # Tres columnas: Mochila | flechas | Cofre
    col_w = S(150)
    mid_w = S(70)
    left_x = panel.x + pad
    mid_x = left_x + col_w + S(8)
    right_x = mid_x + mid_w + S(8)

    hud.draw_text(surface, "MOCHILA", (left_x, y), FONT_SMALL)
    hud.draw_text(surface, "COFRE", (right_x, y), FONT_SMALL)
    y += S(22)

    store = estado.active_chest["store"]
    keys = [("wood", "Madera", "inv_wood"), ("scrap", "Chatarra", "inv_scrap"),
            ("stone", "Piedra", "inv_stone"), ("food", "Comida", "inv_food"),
            ("bandages", "Vendas", "bandages")]

    row_h = S(48)
    btn_size = S(20)
    for key, label, bag_attr in keys:
        bag_val = getattr(estado.player, bag_attr)
        chest_val = store.get(key, 0)

        hud.draw_text(surface, f"{label}: {bag_val}", (left_x, y + S(14)))
        hud.draw_text(surface, f"{label}: {chest_val}", (right_x, y + S(14)))

        # Botones apilados al centro: arriba envía, abajo recupera
        r_to = pygame.Rect(mid_x + (mid_w - btn_size) // 2, y, btn_size, btn_size)
        r_from = pygame.Rect(mid_x + (mid_w - btn_size) // 2, y + btn_size + S(4), btn_size, btn_size)

        to_ok = bag_val > 0
        from_ok = chest_val > 0
        pygame.draw.rect(surface, (58, 64, 45) if to_ok else (40, 40, 36), r_to)
        pygame.draw.rect(surface, (58, 64, 40), r_to, max(1, UI_S))
        pygame.draw.rect(surface, (58, 64, 45) if from_ok else (40, 40, 36), r_from)
        pygame.draw.rect(surface, (58, 64, 40), r_from, max(1, UI_S))

        arrow_to = FONT_MED.render("→", True, (217, 183, 74) if to_ok else (110, 110, 100))
        surface.blit(arrow_to, (r_to.centerx - arrow_to.get_width() // 2, r_to.centery - arrow_to.get_height() // 2))
        arrow_from = FONT_MED.render("←", True, (217, 183, 74) if from_ok else (110, 110, 100))
        surface.blit(arrow_from, (r_from.centerx - arrow_from.get_width() // 2, r_from.centery - arrow_from.get_height() // 2))

        buttons[f"to_{key}"] = r_to
        buttons[f"from_{key}"] = r_from
        y += row_h

    y += S(8)

    # Comer / Vendar, lado a lado
    food_ok = estado.player.inv_food > 0 and estado.player.hunger < estado.player.max_hunger
    band_ok = estado.player.bandages > 0 and estado.player.hp < estado.player.max_hp
    cons_w = (panel_w - S(32) - S(10)) // 2
    r1 = pygame.Rect(panel.x + pad, y, cons_w, S(30))
    r2 = pygame.Rect(r1.right + S(10), y, cons_w, S(30))
    pygame.draw.rect(surface, (58, 64, 45) if food_ok else (40, 30, 30), r1)
    pygame.draw.rect(surface, (74, 30, 30) if band_ok else (40, 30, 30), r2)
    pygame.draw.rect(surface, (58, 64, 40), r1, max(1, UI_S))
    pygame.draw.rect(surface, (184, 67, 59), r2, max(1, UI_S))
    hud.draw_text(surface, "Comer (+hambre)", (r1.x + S(8), r1.y + S(8)))
    hud.draw_text(surface, "Vendar (+30 PV)", (r2.x + S(8), r2.y + S(8)))
    buttons["food"] = r1
    buttons["bandage"] = r2
    y += S(30) + S(14)

    # Capacidad, centrada
    bag_used = estado.current_capacity()
    chest_used = estado.chest_capacity_used(estado.active_chest)
    cap_txt = f"Mochila: {bag_used}/{MAX_CAPACITY}    Cofre: {chest_used}/{CHEST_CAPACITY}"
    cap_surf = FONT_SMALL.render(cap_txt, True, (180, 200, 160))
    surface.blit(cap_surf, (panel.centerx - cap_surf.get_width() // 2, y))
    y += S(24) + S(10)

    # Cerrar, centrado
    rc_w = S(160)
    rc = pygame.Rect(panel.centerx - rc_w // 2, y, rc_w, S(34))
    pygame.draw.rect(surface, (58, 64, 45), rc)
    pygame.draw.rect(surface, (58, 64, 40), rc, max(1, UI_S))
    close_txt = FONT_MED.render("Cerrar", True, (217, 214, 194))
    surface.blit(close_txt, (rc.centerx - close_txt.get_width() // 2, rc.centery - close_txt.get_height() // 2))
    buttons["close"] = rc

    return buttons

def handle_storage_click(pos, buttons):
    for k, r in buttons.items():
        if not r.collidepoint(pos):
            continue
        if k.startswith("to_"):
            almacen.move_to_chest(k[3:])
        elif k.startswith("from_"):
            almacen.move_to_bag(k[5:])
        elif k == "food":
            crafteo.use_food()
        elif k == "bandage":
            crafteo.use_bandage()
        elif k == "close":
            almacen.close_storage()
        return

def render_start_screen(surface):
    surface.fill((11, 13, 10))
    title = FONT_TITLE.render("ÉBANON // PROTOCOLO DE RUINA", True, (143, 174, 76))
    surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, int(130 * UI_S)))

    lines = [
        "Sobrevive de día. Resiste de noche.",
        "Recolecta madera, chatarra y piedra, y construye tu refugio.",
        "WASD moverte · Mouse apuntar · Espacio/Clic atacar",
        "E recolectar · Q mochila y crafteo · B construir · TAB cambiar arma · ESC pausa",
    ]
    for i, l in enumerate(lines):
        t = FONT_SMALL.render(l, True, (141, 145, 120))
        surface.blit(t, (SCREEN_W // 2 - t.get_width() // 2,
                         int(210 * UI_S) + i * int(26 * UI_S)))

    has_save = bool(estado.save_slots)
    btn_w, btn_h = int(220 * UI_S), int(54 * UI_S)
    gap = int(18 * UI_S)
    y0 = int(350 * UI_S)

    buttons = {}

    # Botón CONTINUAR
    r_cont = pygame.Rect(SCREEN_W // 2 - btn_w // 2, y0, btn_w, btn_h)
    pygame.draw.rect(surface, (20, 23, 15), r_cont)
    cont_color = (217, 183, 74) if has_save else (90, 90, 90)
    pygame.draw.rect(surface, cont_color, r_cont, max(1, UI_S))
    txt = FONT_MED.render("CONTINUAR", True, cont_color)
    surface.blit(txt, (r_cont.x + r_cont.w // 2 - txt.get_width() // 2,
                       r_cont.y + r_cont.h // 2 - txt.get_height() // 2))
    buttons["continue"] = r_cont if has_save else None

    # Botón NUEVO
    r_new = pygame.Rect(SCREEN_W // 2 - btn_w // 2, y0 + btn_h + gap, btn_w, btn_h)
    pygame.draw.rect(surface, (20, 23, 15), r_new)
    pygame.draw.rect(surface, (217, 183, 74), r_new, max(1, UI_S))
    txt2 = FONT_MED.render("NUEVO", True, (217, 183, 74))
    surface.blit(txt2, (r_new.x + r_new.w // 2 - txt2.get_width() // 2,
                        r_new.y + r_new.h // 2 - txt2.get_height() // 2))
    buttons["new"] = r_new

    # Botón SALIR
    r_quit = pygame.Rect(SCREEN_W // 2 - btn_w // 2, y0 + 2*(btn_h + gap), btn_w, btn_h)
    pygame.draw.rect(surface, (20, 23, 15), r_quit)
    pygame.draw.rect(surface, (200, 80, 80), r_quit, max(1, UI_S))
    txt3 = FONT_MED.render("SALIR", True, (200, 80, 80))
    surface.blit(txt3, (r_quit.x + r_quit.w // 2 - txt3.get_width() // 2,
                        r_quit.y + r_quit.h // 2 - txt3.get_height() // 2))
    buttons["quit"] = r_quit

    if estado.menu_msg:
        m = FONT_SMALL.render(estado.menu_msg, True, (200, 80, 80))
        surface.blit(m, (SCREEN_W // 2 - m.get_width() // 2, r_quit.bottom + int(14 * UI_S)))
        
    return buttons

def _menu_button(surface, rect, label, color):
    pygame.draw.rect(surface, (20, 23, 15), rect)
    pygame.draw.rect(surface, color, rect, max(1, UI_S))
    t = FONT_MED.render(label, True, color)
    surface.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))

def render_slots_screen(surface):
    surface.fill((11, 13, 10))
    S = lambda n: int(n * UI_S)
    title = FONT_TITLE.render("CONTINUAR PARTIDA", True, (143, 174, 76))
    surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, S(70)))

    buttons = {"rows": [], "dels": [], "back": None}
    row_w, row_h, gap = S(380), S(60), S(10)
    x = SCREEN_W // 2 - row_w // 2
    y0 = S(140)
    for i in range(MAX_SLOTS):
        rect = pygame.Rect(x, y0 + i * (row_h + gap), row_w, row_h)
        pygame.draw.rect(surface, (20, 23, 15), rect)
        if i >= len(estado.save_slots):
            pygame.draw.rect(surface, (58, 64, 40), rect, max(1, UI_S))
            hud.draw_text(surface, f"Slot {i + 1} - vacío", (rect.x + S(12), rect.centery - S(8)),
                      FONT_SMALL, (90, 90, 90))
            continue
        name, path, label, mtime = estado.save_slots[i]
        confirming = (estado.delete_confirm == path)
        pygame.draw.rect(surface, (184, 67, 59) if confirming else (217, 183, 74), rect,
                         max(1, UI_S))
        hud.draw_text(surface, name, (rect.x + S(12), rect.y + S(4)), FONT_MED, (217, 183, 74))
        if confirming:
            hud.draw_text(surface, "¿Borrar? Pulsa la X otra vez", (rect.x + S(12), rect.y + S(34)),
                      FONT_SMALL, (200, 80, 80))
        else:
            when = time.strftime("%d/%m/%Y %H:%M", time.localtime(mtime))
            hud.draw_text(surface, f"{label}  ·  {when}", (rect.x + S(12), rect.y + S(34)))
        dsize = S(36)
        rd = pygame.Rect(rect.right - dsize - S(10), rect.centery - dsize // 2, dsize, dsize)
        pygame.draw.rect(surface, (74, 30, 30), rd)
        pygame.draw.rect(surface, (184, 67, 59), rd, max(1, UI_S))
        xs = FONT_MED.render("X", True, (217, 214, 194))
        surface.blit(xs, (rd.centerx - xs.get_width() // 2, rd.centery - xs.get_height() // 2))
        buttons["rows"].append((rect, path))
        buttons["dels"].append((rd, path))

    rb = pygame.Rect(SCREEN_W // 2 - S(90), y0 + MAX_SLOTS * (row_h + gap) + S(10), S(180), S(44))
    _menu_button(surface, rb, "VOLVER", (217, 183, 74))
    buttons["back"] = rb
    if estado.menu_msg:
        m = FONT_SMALL.render(estado.menu_msg, True, (200, 80, 80))
        surface.blit(m, (SCREEN_W // 2 - m.get_width() // 2, rb.bottom + S(12)))
    return buttons

def render_name_screen(surface):
    surface.fill((11, 13, 10))
    S = lambda n: int(n * UI_S)
    title = FONT_TITLE.render("NUEVA PARTIDA", True, (143, 174, 76))
    surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, S(120)))
    sub = FONT_SMALL.render("Escribe un nombre para tu partida:", True, (141, 145, 120))
    surface.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, S(200)))

    box = pygame.Rect(SCREEN_W // 2 - S(180), S(230), S(360), S(50))
    pygame.draw.rect(surface, (20, 23, 15), box)
    pygame.draw.rect(surface, (217, 183, 74), box, max(1, UI_S))
    cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
    t = FONT_MED.render(estado.name_input + cursor, True, (217, 214, 194))
    surface.blit(t, (box.x + S(12), box.centery - t.get_height() // 2))

    hint = FONT_SMALL.render("Enter aceptar · Esc cancelar · máx. 16 caracteres", True, (141, 145, 120))
    surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, box.bottom + S(10)))

    ok = pygame.Rect(SCREEN_W // 2 - S(190), box.bottom + S(50), S(180), S(44))
    cancel = pygame.Rect(SCREEN_W // 2 + S(10), box.bottom + S(50), S(180), S(44))
    _menu_button(surface, ok, "ACEPTAR", (217, 183, 74))
    _menu_button(surface, cancel, "CANCELAR", (200, 80, 80))
    if estado.menu_msg:
        m = FONT_SMALL.render(estado.menu_msg, True, (200, 80, 80))
        surface.blit(m, (SCREEN_W // 2 - m.get_width() // 2, ok.bottom + S(14)))
    return {"ok": ok, "cancel": cancel}

def open_slots_screen():
    
    guardado.refresh_saves()
    estado.delete_confirm = None
    estado.menu_msg = ""
    estado.game_state = STATE_SLOTS

def open_name_screen():
    
    guardado.refresh_saves()
    if len(estado.save_slots) >= MAX_SLOTS:
        estado.menu_msg = f"Slots llenos ({MAX_SLOTS}). Borra una partida en CONTINUAR."
        return
    estado.name_input = ""
    estado.menu_msg = ""
    estado.game_state = STATE_NAME

def back_to_start():
    
    estado.game_state = STATE_START
    estado.delete_confirm = None
    estado.menu_msg = ""

def confirm_new_name():
    
    name = estado.name_input.strip()
    if not name:
        estado.menu_msg = "Escribe un nombre."
        return
    path = os.path.join(SAVE_DIR, name + ".json")
    if os.path.exists(path):
        estado.menu_msg = "Ya existe una partida con ese nombre."
        return
    partida.start_game(new_game=True, path=path)

def handle_name_key(event):
    
    if event.key == pygame.K_RETURN:
        confirm_new_name()
    elif event.key == pygame.K_ESCAPE:
        back_to_start()
    elif event.key == pygame.K_BACKSPACE:
        estado.name_input = estado.name_input[:-1]
    elif event.unicode and len(estado.name_input) < 16 and (event.unicode.isalnum() or event.unicode in " -_"):
        estado.name_input += event.unicode

def handle_name_click(pos, buttons):
    if buttons.get("ok") and buttons["ok"].collidepoint(pos):
        confirm_new_name()
    elif buttons.get("cancel") and buttons["cancel"].collidepoint(pos):
        back_to_start()

def handle_slots_click(pos, buttons):
    
    for rect, path in buttons.get("dels", []):
        if rect.collidepoint(pos):
            if estado.delete_confirm == path:
                try:
                    os.remove(path)
                except Exception as e:
                    estado.menu_msg = f"No se pudo borrar: {e}"
                estado.delete_confirm = None
                guardado.refresh_saves()
            else:
                estado.delete_confirm = path
            return
    estado.delete_confirm = None
    for rect, path in buttons.get("rows", []):
        if rect.collidepoint(pos):
            partida.start_game(new_game=False, path=path)
            return
    if buttons.get("back") and buttons["back"].collidepoint(pos):
        back_to_start()

def render_gameover_screen(surface):
    surface.fill((11, 13, 10))
    title = FONT_TITLE.render("HAS MUERTO", True, (184, 67, 59))
    surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, int(150 * UI_S)))
    msg = FONT_SMALL.render(f"Sobreviviste {estado.survived_days} días", True, (141, 145, 120))
    surface.blit(msg, (SCREEN_W // 2 - msg.get_width() // 2, int(210 * UI_S)))
    btn_w, btn_h = int(220 * UI_S), int(54 * UI_S)
    r = pygame.Rect(SCREEN_W // 2 - btn_w // 2, int(300 * UI_S), btn_w, btn_h)
    pygame.draw.rect(surface, (20, 23, 15), r)
    pygame.draw.rect(surface, (217, 183, 74), r, max(1, UI_S))
    txt = FONT_MED.render("REINTENTAR", True, (217, 183, 74))
    surface.blit(txt, (r.centerx - txt.get_width() // 2, r.centery - txt.get_height() // 2))
    return r


def render_pause_menu(surface):
    buttons = {}
    panel_w = int(300 * UI_S)
    panel_h = int(160 * UI_S)
    panel = pygame.Rect(SCREEN_W // 2 - panel_w // 2, SCREEN_H // 2 - panel_h // 2, panel_w, panel_h)
    hud.panel_bg(surface, panel)
    hud.draw_text(surface, "PAUSA", (panel.x + int(16 * UI_S), panel.y + int(12 * UI_S)), FONT_MED, (217, 183, 74))

    btn_w = panel_w - int(32 * UI_S)
    btn_h = int(40 * UI_S)
    x = panel.x + int(16 * UI_S)

    y_save = panel.y + int(50 * UI_S)
    r_save = pygame.Rect(x, y_save, btn_w, btn_h)
    pygame.draw.rect(surface, (58, 64, 45), r_save)
    pygame.draw.rect(surface, (58, 64, 40), r_save, max(1, UI_S))
    hud.draw_text(surface, "GUARDAR", (r_save.x + int(10 * UI_S), r_save.y + int(10 * UI_S)), FONT_MED, (217, 214, 194))
    buttons["save"] = r_save

    y_exit = y_save + btn_h + int(14 * UI_S)
    r_exit = pygame.Rect(x, y_exit, btn_w, btn_h)
    pygame.draw.rect(surface, (74, 30, 30), r_exit)
    pygame.draw.rect(surface, (184, 67, 59), r_exit, max(1, UI_S))
    hud.draw_text(surface, "MENÚ", (r_exit.x + int(10 * UI_S), r_exit.y + int(10 * UI_S)), FONT_MED, (217, 214, 194))
    buttons["exit"] = r_exit

    return buttons


def handle_pause_click(pos, buttons):
    
    if buttons.get("save") and buttons["save"].collidepoint(pos):
        guardado.save_game()
        estado.log("Partida guardada.")
        estado.pause_menu_open = False
        return
    if buttons.get("exit") and buttons["exit"].collidepoint(pos):
        guardado.save_game()
        partida.exit_to_menu()
        return
