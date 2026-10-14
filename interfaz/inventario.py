"""Mochila estilo Valheim: casillas con ICONO y CANTIDAD, herramientas con barra de durabilidad.

  - Arriba: tus recursos en casillas (clic = tirar 1, Shift + clic = tirar todo). Pasa el mouse para ver qué es.
  - Botones: Comer, Vendar y Reparar (repara todas tus herramientas; hay que estar junto a un banco de trabajo).
  - Abajo: herramientas y armas. Las que aún no tienes salen apagadas con su costo debajo (clic = craftear).
    Borde dorado = equipada. Barra verde/amarilla/roja = durabilidad. "ROTA" = no sirve hasta repararla.

Los iconos se dibujan con bloques de color (ver ICONOS). Si pones un PNG llamado assets/sprites/ic_<nombre>.png
(por ejemplo ic_wood.png, ic_axe.png), se usa en vez del dibujo.
"""

import math
import os
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global barco, estaciones, estado, hud
    from interfaz import hud
    from mapas import barco
    from nucleo import estado
    from sistemas import estaciones


# ============================================================================
# AJUSTES
# ============================================================================
ESCALA = 1.1         # ← tamaño de toda la mochila (0.9 = un poco más chica, 1.1 = más grande)
COLUMNAS = 7          # ← casillas por fila
SLOT = 52             # ← tamaño de cada casilla (antes de escalar)
GAP = 4               # ← separación entre casillas
# Costos que se muestran bajo cada herramienta. Deben coincidir con los de crafteo.py.
RECETAS = {"axe": {"wood": 3, "scrap": 2}, "pickaxe": {"wood": 4, "scrap": 5},
           "bat": {"wood": 4, "scrap": 4}, "hammer": {"wood": 3, "scrap": 3}}
HERRAMIENTAS = ("axe", "pickaxe", "bat", "hammer")              # siempre se muestran
EXTRAS = ("gun", "shotgun", "baca_pick")                        # solo si las tienes
CON_DURABILIDAD = ("axe", "pickaxe", "bat")

NOMBRES = {"wood": "Madera", "stone": "Piedra", "scrap": "Chatarra", "food": "Comida", "bandages": "Vendas",
           "ammo": "Munición", "ingot": "Lingotes", "part": "Pieza mecánica", "diesel": "Diésel"}
DESCRIPCION = {
    "wood": "Para construir y craftear. Alimenta las fogatas (E).",
    "stone": "Para muros de piedra y mejoras de herramientas.",
    "scrap": "Para craftear, mejorar y construir.",
    "food": "Calma el hambre. Cocinada en una fogata (C) rinde más.",
    "bandages": "Curan 30 PV.",
    "ammo": "Munición para la pistola y la escopeta.",
    "ingot": "Lingotes de la fundidora: mejoras de hierro y el barco.",
    "part": "Pieza mecánica que necesita el barco.",
    "diesel": "Combustible que necesita el barco.",
    "axe": "Tala árboles más rápido y rinde más madera.",
    "pickaxe": "Rompe rocas para sacar piedra.",
    "bat": "Más daño cuerpo a cuerpo.",
    "hammer": "Sirve para reparar y desmontar estructuras.",
    "gun": "Pistola.",
    "shotgun": "Escopeta.",
    "baca_pick": "El zapapico de Baca.",
}

# ============================================================================
# ICONOS (dibujados con bloques en una cuadrícula de 12 x 12)
# ============================================================================
_C = {"bark": (96, 66, 38), "wood": (168, 122, 72), "ring": (214, 176, 118),
      "rock": (128, 130, 134), "rockl": (176, 178, 182), "rockd": (86, 88, 92),
      "metal": (140, 148, 158), "metall": (190, 198, 208), "metald": (92, 98, 108),
      "red": (186, 52, 48), "redd": (122, 30, 30), "leaf": (84, 150, 70), "white": (232, 232, 224), "greyw": (186, 186, 178),
      "brass": (200, 160, 70), "brassd": (140, 104, 40), "gold": (236, 196, 76), "dark": (52, 54, 60), "black": (30, 30, 34)}


def _picos(c1, c2):
    return [("d", "bark", 3, 10, 7, 3, 1), ("d", "bark", 4, 10, 8, 3, 1), (c1, 3, 2, 7, 1), (c1, 2, 3, 2, 1), (c1, 9, 3, 2, 1),
            (c1, 1, 4, 1, 2), (c1, 10, 4, 1, 2), (c2, 3, 2, 5, 1)]


ICONOS = {
    "wood": [("bark", 0, 2, 12, 4), ("wood", 1, 3, 10, 2), ("ring", 0, 3, 1, 2),
             ("bark", 0, 7, 12, 4), ("wood", 1, 8, 10, 2), ("ring", 0, 8, 1, 2)],
    "stone": [("rockd", 3, 2, 6, 1), ("rock", 2, 3, 8, 6), ("rockl", 3, 3, 4, 3), ("rockl", 4, 3, 2, 1),
              ("rockd", 2, 9, 8, 1), ("rockd", 9, 4, 1, 5)],
    "scrap": [("metald", 1, 5, 10, 4), ("metal", 1, 4, 10, 4), ("metall", 1, 4, 10, 1), ("rockd", 2, 6, 1, 1),
              ("rockd", 9, 6, 1, 1), ("metald", 4, 6, 4, 1), ("metal", 7, 1, 3, 3), ("metall", 7, 1, 3, 1)],
    "food": [("red", 2, 5, 3, 3), ("redd", 2, 7, 3, 1), ("red", 6, 4, 3, 3), ("redd", 6, 6, 3, 1), ("red", 4, 7, 3, 3),
             ("redd", 4, 9, 3, 1), ("leaf", 5, 2, 2, 2), ("leaf", 7, 3, 2, 1), ("white", 3, 6, 1, 1), ("white", 7, 5, 1, 1)],
    "bandages": [("white", 1, 3, 10, 6), ("greyw", 1, 8, 10, 1), ("red", 5, 4, 2, 4), ("red", 4, 5, 4, 2)],
    "ammo": [op for x in (2, 5, 8) for op in (("brass", x, 5, 2, 5), ("gold", x, 3, 2, 2), ("brassd", x, 10, 2, 1))],
    "ingot": [("metald", 1, 8, 10, 1), ("metal", 1, 5, 10, 3), ("metall", 3, 4, 6, 1), ("metall", 2, 5, 4, 1), ("metald", 2, 7, 8, 1)],
    "part": [("metal", 5, 1, 2, 10), ("metal", 1, 5, 10, 2), ("metal", 3, 3, 6, 6), ("metald", 4, 4, 4, 4),
             ("dark", 5, 5, 2, 2), ("metall", 3, 3, 6, 1)],
    "diesel": [("red", 2, 4, 7, 7), ("redd", 2, 10, 7, 1), ("red", 7, 2, 3, 3), ("redd", 8, 2, 2, 1), ("gold", 3, 1, 3, 2),
               ("white", 4, 6, 3, 3), ("redd", 5, 7, 1, 1)],
    "axe": [("d", "bark", 2, 10, 8, 4, 1), ("d", "bark", 3, 10, 9, 4, 1), ("metal", 7, 1, 4, 3), ("metall", 7, 1, 4, 1),
            ("metald", 9, 4, 2, 1)],
    "pickaxe": _picos("metal", "metall"),
    "baca_pick": _picos("brass", "gold"),
    "bat": [("d", "wood", 2, 10, 9, 2, 2), ("d", "bark", 3, 11, 10, 3, 1), ("ring", 8, 2, 2, 1)],
    "hammer": [("d", "bark", 2, 10, 7, 4, 1), ("d", "bark", 3, 10, 8, 4, 1), ("metald", 6, 1, 5, 4), ("metal", 6, 1, 5, 3),
               ("metall", 6, 1, 5, 1)],
    "gun": [("dark", 1, 4, 9, 3), ("black", 1, 4, 9, 1), ("dark", 2, 7, 3, 4), ("black", 3, 8, 1, 2), ("metal", 9, 5, 2, 1)],
    "shotgun": [("wood", 0, 6, 4, 3), ("bark", 1, 7, 3, 1), ("dark", 4, 5, 8, 1), ("dark", 4, 7, 8, 1), ("metal", 4, 6, 8, 1),
                ("black", 6, 8, 2, 2)],
}
_cache = {}


def icono(nombre, lado):
    """Superficie cuadrada con el icono. Usa assets/sprites/ic_<nombre>.png si existe."""
    clave = (nombre, lado)
    if clave in _cache:
        return _cache[clave]
    ruta = os.path.join(ASSETS_DIR, "sprites", f"ic_{nombre}.png")
    surf = None
    if os.path.exists(ruta):
        try:
            surf = pygame.transform.scale(pygame.image.load(ruta).convert_alpha(), (lado, lado))
        except Exception:
            surf = None
    if surf is None:
        surf = pygame.Surface((lado, lado), pygame.SRCALPHA)
        u = lado / 12.0
        for op in ICONOS.get(nombre, []):
            if op[0] == "d":
                _, col, x0, y0, x1, y1, grosor = op
                pasos = max(abs(x1 - x0), abs(y1 - y0), 1)
                for i in range(pasos + 1):
                    x, y = x0 + (x1 - x0) * i / pasos, y0 + (y1 - y0) * i / pasos
                    pygame.draw.rect(surf, _C[col], pygame.Rect(int(x * u), int(y * u), max(1, int(grosor * u)), max(1, int(grosor * u))))
            else:
                col, x, y, w, h = op
                pygame.draw.rect(surf, _C[col], pygame.Rect(int(x * u), int(y * u), max(1, int(w * u)), max(1, int(h * u))))
    _cache[clave] = surf
    return surf


# ============================================================================
# DIBUJO
# ============================================================================
def _ajustar(font, texto, ancho):
    """Recorta el texto con "…" si no cabe en `ancho` píxeles."""
    if font.size(texto)[0] <= ancho:
        return texto
    while texto and font.size(texto + "…")[0] > ancho:
        texto = texto[:-1]
    return texto + "…"


def _envolver(font, texto, ancho, max_lineas):
    """Parte el texto en renglones que quepan en `ancho` píxeles (máximo `max_lineas`; si sobra, termina en "…")."""
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = (actual + " " + palabra).strip()
        if font.size(prueba)[0] <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        lineas[-1] = _ajustar(font, lineas[-1] + " …", ancho)
    return [_ajustar(font, l, ancho) for l in lineas]


def _casilla(surface, rect, borde, fondo=(34, 36, 31)):
    pygame.draw.rect(surface, fondo, rect)
    pygame.draw.rect(surface, (20, 21, 18), pygame.Rect(rect.x, rect.y, rect.w, max(2, rect.h // 12)))
    pygame.draw.rect(surface, borde, rect, max(1, UI_S))


def _cantidad(surface, rect, n, color=(240, 236, 220)):
    img = FONT_SMALL.render(str(n), True, color)
    sombra = FONT_SMALL.render(str(n), True, (0, 0, 0))
    x, y = rect.right - img.get_width() - 4, rect.bottom - img.get_height() - 2
    surface.blit(sombra, (x + 1, y + 1))
    surface.blit(img, (x, y))


def _barra_durabilidad(surface, rect, actual, maximo):
    h = max(4, int(5 * UI_S))
    fondo = pygame.Rect(rect.x + 4, rect.bottom - h - 3, rect.w - 8, h)
    pygame.draw.rect(surface, (14, 14, 12), fondo)
    frac = 0.0 if maximo <= 0 else max(0.0, min(1.0, actual / maximo))
    col = (90, 170, 80) if frac > 0.5 else ((214, 176, 70) if frac > 0.25 else (200, 60, 50))
    pygame.draw.rect(surface, col, pygame.Rect(fondo.x, fondo.y, int(fondo.w * frac), fondo.h))


def _durabilidad(herramienta):
    """(actual, máximo) o None si la herramienta no tiene durabilidad."""
    if herramienta not in CON_DURABILIDAD:
        return None
    return getattr(estado.player, herramienta + "_durability"), TOOL_DURABILITY_MAX[herramienta]


def _tiene(herramienta):
    return getattr(estado.player, "has_" + herramienta)


def _alcanza(receta):
    p = estado.player
    return p.inv_wood >= receta.get("wood", 0) and p.inv_scrap >= receta.get("scrap", 0)


def _texto_costo(receta):
    return ", ".join(f"{NOMBRES[k]} {n}" for k, n in receta.items())


ETIQUETAS_HABILIDAD = {"lenador": "Leñador", "minero": "Minero", "combate": "Combate", "constructor": "Constructor"}


def _habilidades(surface, x, y, ancho, S):
    """Las 4 habilidades en dos columnas, cada una con su nivel y una barrita hacia el siguiente. Devuelve la nueva y."""
    hab = estaciones.habilidades
    mitad = (ancho - S(10)) // 2
    for i, clave in enumerate(ETIQUETAS_HABILIDAD):
        cx, cy = x + (i % 2) * (mitad + S(10)), y + (i // 2) * S(32)
        datos = hab.skills[clave]
        tope = datos["lvl"] >= hab.MAX_LEVEL
        txt = f"{ETIQUETAS_HABILIDAD[clave]}  {datos['lvl']}" + ("  (máx.)" if tope else "")
        hud.draw_text(surface, _ajustar(FONT_SMALL, txt, mitad), (cx, cy), FONT_SMALL, (180, 200, 160))
        barra = pygame.Rect(cx, cy + S(18), mitad, S(5))
        pygame.draw.rect(surface, (14, 14, 12), barra)
        frac = 1.0 if tope else datos["xp"] / float(hab.xp_for_next(datos["lvl"]))
        pygame.draw.rect(surface, (143, 174, 76), pygame.Rect(barra.x, barra.y, int(barra.w * max(0.0, min(1.0, frac))), barra.h))
    return y + S(70)


def render(surface):
    """Dibuja la mochila. Devuelve los botones (misma forma que antes) para handle_inventory_click."""
    S = lambda n: int(n * UI_S * ESCALA)
    p = estado.player
    botones = {}
    mouse = pygame.mouse.get_pos()
    slot, gap, pad = S(SLOT), S(GAP), S(16)
    ancho = pad * 2 + COLUMNAS * slot + (COLUMNAS - 1) * gap

    # ---- contenido de la mochila
    recursos = [("wood", p.inv_wood, True), ("stone", p.inv_stone, True), ("scrap", p.inv_scrap, True),
                ("food", p.inv_food, True), ("bandages", p.bandages, True), ("ammo", p.ammo, False)]
    recursos += [(k, v, True) for k, v in p.cargo.items() if v > 0]
    recursos = [r for r in recursos if r[1] > 0]
    filas = max(2, math.ceil(len(recursos) / COLUMNAS))
    herr = list(HERRAMIENTAS) + [t for t in EXTRAS if _tiene(t)]
    alto = pad + S(24) + S(14) + filas * (slot + gap) + S(66) + S(36) + S(28) + (slot + S(22)) + S(70) + S(22) + pad
    panel = pygame.Rect(SCREEN_W // 2 - ancho // 2, max(S(10), SCREEN_H // 2 - alto // 2), ancho, alto)
    hud.panel_bg(surface, panel)
    x0, y = panel.x + pad, panel.y + pad
    info = None          # (título, descripción) de lo que está bajo el mouse

    # ---- título y espacio
    hud.draw_text(surface, "MOCHILA", (x0, y), FONT_MED, (217, 183, 74))
    usado = estado.current_capacity()
    txt = f"Espacio {usado}/{MAX_CAPACITY}"
    img = FONT_SMALL.render(txt, True, (180, 200, 160))
    surface.blit(img, (panel.right - pad - img.get_width(), y + S(4)))
    y += S(24)
    barra = pygame.Rect(x0, y, ancho - 2 * pad, S(6))
    pygame.draw.rect(surface, (14, 14, 12), barra)
    frac = max(0.0, min(1.0, usado / float(MAX_CAPACITY)))
    pygame.draw.rect(surface, (90, 170, 80) if frac < 0.7 else ((214, 176, 70) if frac < 0.95 else (200, 60, 50)),
                     pygame.Rect(barra.x, barra.y, int(barra.w * frac), barra.h))
    y += S(14)

    # ---- recursos
    for i in range(filas * COLUMNAS):
        c, f = i % COLUMNAS, i // COLUMNAS
        r = pygame.Rect(x0 + c * (slot + gap), y + f * (slot + gap), slot, slot)
        if i >= len(recursos):
            _casilla(surface, r, (46, 48, 42), (26, 27, 24))
            continue
        clave, n, tirable = recursos[i]
        sobre = r.collidepoint(mouse)
        _casilla(surface, r, (217, 183, 74) if sobre else (74, 78, 66))
        ic = icono(clave, slot - S(16))
        surface.blit(ic, (r.x + S(8), r.y + S(6)))
        _cantidad(surface, r, n)
        if tirable:
            botones["drop_" + clave] = r
        if sobre:
            nombre = NOMBRES.get(clave) or barco.BOAT_LABELS.get(clave, clave)
            info = (f"{nombre}  x{n}", DESCRIPCION.get(clave, "") + ("  Clic: tirar 1 · Shift+clic: tirar todo." if tirable else ""))
    y += filas * (slot + gap)

    # ---- zona de ayuda (tooltip)
    zona = pygame.Rect(x0, y, ancho - 2 * pad, S(58))
    pygame.draw.rect(surface, (26, 27, 24), zona)
    pygame.draw.rect(surface, (58, 64, 40), zona, max(1, UI_S))
    ay = zona
    y += S(66)

    # ---- botones: comer, vendar, reparar
    ancho_b = (ancho - 2 * pad - 2 * gap) // 3
    comer_ok = p.inv_food > 0 and p.hunger < p.max_hunger
    vendar_ok = p.bandages > 0 and p.hp < p.max_hp
    reparar_ok = estaciones.bench_near() is not None and bool(estaciones.damaged_tools())
    for k, (clave, etiqueta, ok, col_borde, ic) in enumerate((
            ("food", "Comer", comer_ok, (90, 100, 60), "food"),
            ("bandage", "Vendar (+30)", vendar_ok, (184, 67, 59), "bandages"),
            ("repair", "Reparar todo", reparar_ok, (217, 183, 74), "hammer"))):
        r = pygame.Rect(x0 + k * (ancho_b + gap), y, ancho_b, S(32))
        pygame.draw.rect(surface, (58, 64, 45) if ok else (36, 34, 32), r)
        pygame.draw.rect(surface, col_borde if ok else (60, 58, 54), r, max(1, UI_S))
        surface.blit(icono(ic, S(22)), (r.x + S(5), r.y + S(5)))
        hud.draw_text(surface, _ajustar(FONT_SMALL, etiqueta, r.w - S(34)), (r.x + S(30), r.y + S(8)), FONT_SMALL,
                      (235, 230, 215) if ok else (120, 118, 110))
        botones[clave] = r
        if r.collidepoint(mouse):
            if clave == "repair":
                if estaciones.bench_near() is None:
                    info = ("Reparar todo", "Necesitas estar junto a un banco de trabajo.")
                elif not estaciones.damaged_tools():
                    info = ("Reparar todo", "Todas tus herramientas están en perfecto estado.")
                else:
                    info = ("Reparar todo", "Deja tus herramientas como nuevas." + (" Cuesta: " + _texto_costo(estaciones.REPAIR_COST) + "." if estaciones.REPAIR_COST else " Es gratis."))
            elif clave == "food":
                info = ("Comer", "Come 1 de comida cruda (+30 de hambre). Cocinada en una fogata rinde más.")
            else:
                info = ("Vendar", "Usa 1 venda para curarte 30 PV.")
    y += S(36)

    # ---- herramientas y armas
    hud.draw_text(surface, "HERRAMIENTAS Y ARMAS", (x0, y), FONT_MED, (217, 183, 74))
    y += S(28)
    for i, t in enumerate(herr):
        r = pygame.Rect(x0 + i * (slot + gap), y, slot, slot)
        tiene = _tiene(t)
        sobre = r.collidepoint(mouse)
        equipada = p.equipped == t
        dur = _durabilidad(t) if tiene else None
        rota = bool(dur) and dur[0] <= 0
        if not tiene:
            receta = RECETAS.get(t, {})
            ok = _alcanza(receta)
            _casilla(surface, r, (217, 183, 74) if sobre else (74, 78, 66), (28, 29, 26))
            ic = icono(t, slot - S(16))
            ic.set_alpha(110)
            surface.blit(ic, (r.x + S(8), r.y + S(6)))
            ic.set_alpha(255)
            botones[t] = (r, "craft")
            cx = r.x
            for k, n in receta.items():                                 # costo debajo: icono + número
                surface.blit(icono(k, S(14)), (cx, r.bottom + S(4)))
                hud.draw_text(surface, str(n), (cx + S(16), r.bottom + S(4)), FONT_SMALL,
                              (200, 200, 190) if getattr(p, "inv_" + k) >= n else (214, 90, 80))
                cx += S(26)
            if sobre:
                extra = "  Necesita un banco de trabajo cerca." if t in estaciones.BENCH_NEEDED_FOR else ""
                info = (WEAPON_LABELS[t], f"Cuesta: {_texto_costo(receta)}. Clic: craftear.{extra}" + ("" if ok else "  (te faltan materiales)"))
        else:
            borde = (217, 183, 74) if equipada else ((200, 60, 50) if rota else ((236, 220, 150) if sobre else (74, 78, 66)))
            _casilla(surface, r, borde, (60, 30, 28) if rota else (34, 36, 31))
            ic = icono(t, slot - S(16))
            if rota:
                ic.set_alpha(120)
            surface.blit(ic, (r.x + S(8), r.y + S(4)))
            ic.set_alpha(255)
            if dur:
                _barra_durabilidad(surface, r, dur[0], dur[1])
            if rota:
                hud.draw_text(surface, "ROTA", (r.x + S(10), r.y + S(18)), FONT_SMALL, (255, 110, 100))
            botones[t] = (r, "equip")
            if sobre:
                estado_txt = "ROTA: repárala en un banco de trabajo (no se pierde)." if rota else ("Equipada. Clic: guardarla." if equipada else "Clic: equipar.")
                num = f"  Durabilidad {dur[0]}/{dur[1]}." if dur else ""
                info = (WEAPON_LABELS[t], DESCRIPCION.get(t, "") + num + " " + estado_txt)
    y += slot + S(22)

    # ---- tooltip (se dibuja al final de la zona de ayuda)
    util = ay.w - S(16)
    if info:
        hud.draw_text(surface, _ajustar(FONT_SMALL, info[0], util), (ay.x + S(8), ay.y + S(4)), FONT_SMALL, (240, 225, 160))
        for i, linea in enumerate(_envolver(FONT_SMALL, info[1], util, 2)):
            hud.draw_text(surface, linea, (ay.x + S(8), ay.y + S(22) + i * S(17)), FONT_SMALL, (200, 200, 190))
    else:
        hud.draw_text(surface, _ajustar(FONT_SMALL, "Pasa el mouse sobre algo para ver qué es.", util), (ay.x + S(8), ay.y + S(20)),
                      FONT_SMALL, (120, 122, 110))

    # ---- habilidades y ayuda
    y = _habilidades(surface, x0, y, ancho - 2 * pad, S)
    hud.draw_text(surface, "TAB: cambiar de arma", (x0, y), FONT_SMALL, (141, 145, 120))
    return botones
