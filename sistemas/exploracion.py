"""Exploración: alijos escondidos por la isla, naufragios en el mar y páginas del diario del Navegante.

ALIJOS      Cajas abandonadas repartidas por la isla (lejos de donde empiezas). Cerca de una, E la abre
            y sacas provisiones y, con suerte, lingotes, piezas o una página del diario. Cada una se abre una vez.
NAUFRAGIOS  Los crea eventos.py: restos flotando en mar abierto, al norte/sur/este/oeste de la isla.
            Hay que nadar hasta ellos (mojado, frío y tiburones) y pulsar E: el botín es mejor.
DIARIO      Las páginas se van encontrando en orden. La tecla T las lee (T otra vez pasa a la siguiente).
            Los textos están en la lista DIARIO: reescríbelos a tu gusto.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global camara, dibujo, estado, hud, mundo
    from interfaz import dibujo, hud
    from nucleo import estado, mundo
    from sistemas import camara


# ============================================================================
# AJUSTES (todo lo que quieras tocar está aquí)
# ============================================================================
CACHE_COUNT = 10                   # ← alijos repartidos por la isla
CACHE_MIN_START = 20 * TILE        # ← no aparecen más cerca que esto de donde empiezas
CACHE_MIN_SEP = 12 * TILE          # ← separación mínima entre alijos
CACHE_ROLLS = 2                    # ← cuántas "tiradas" de botín da un alijo
CACHE_PAGE_CHANCE = 0.40           # ← probabilidad de que un alijo traiga una página del diario
WRECK_ROLLS = 3                    # ← tiradas de botín de un naufragio (y siempre trae una página)
WRECK_LIFETIME = 600.0             # ← segundos que duran los restos antes de hundirse
WRECK_EXTRA_TILES = (5, 9)         # ← a cuántas casillas de la orilla aparece el naufragio
REACH = 1.4 * INTERACT_RANGE       # ← qué tan cerca debes estar para abrir (alijos)
REACH_WRECK = 2.2 * INTERACT_RANGE # ← y para registrar un naufragio (flota, es más fácil alcanzarlo)

# (peso, objeto, mínimo, máximo)
LOOT_CACHE = [(30, "food", 1, 3), (22, "bandages", 1, 2), (25, "scrap", 3, 6), (15, "ammo", 4, 10),
              (10, "stone", 3, 6), (7, "ingot", 1, 2), (3, "part", 1, 1)]
LOOT_WRECK = [(20, "ingot", 2, 4), (14, "part", 1, 1), (16, "food", 2, 4), (14, "bandages", 1, 3), (26, "scrap", 4, 8)]

DIARIO = [
    "Día de sal. Pesqué toda mi vida y nunca supe cuánto pesa el silencio. Hoy pesa más que la red.",
    "Las esporas viajan como el polen: sin prisa y sin rencor. Es biología, no castigo. Por eso cuesta tanto odiarlas.",
    "Se me escapó otra palabra. Hace un rato sabía hacer un nudo y ahora lo miro como a un idioma ajeno. Escribo para que la mano recuerde lo que la cabeza suelta.",
    "Los muertos caminan hacia donde hubo ruido, luz, gente. Miran vitrinas que ya no existen. Cuesta no reconocerse en ellos.",
    "La fogata no es calor: es un acuerdo. Mientras arda, la noche respeta un pedazo de tierra del tamaño de mi sombra.",
    "Aprendí a clavar tablas con piedras. Mi padre decía que una casa se termina el día que alguien duerme tranquilo en ella.",
    "Algunos animales también cargan el virus. Los perros ya no ladran: avisan. Hay una ternura rara en que sigan montando guardia.",
    "Hoy no encontré mi nombre en ninguno de mis bolsillos. Lo encontré en la voz de alguien que me llamó a comer. Debe bastar.",
    "Si el mar me trae otra cosa, que no sea esperanza. Prefiero una soga, una lata, una página mojada. Cosas que se puedan usar.",
    "No sé si el mundo agoniza o si solo se calló. Sigo remando de todos modos.",
]

NOMBRES = {"food": "comida", "bandages": "vendas", "scrap": "chatarra", "ammo": "munición",
           "stone": "piedra", "ingot": "lingotes", "part": "piezas", "wood": "madera"}
_ATRIBUTO = {"food": "inv_food", "bandages": "bandages", "scrap": "inv_scrap", "stone": "inv_stone",
             "wood": "inv_wood", "ammo": "ammo"}

caches = []        # alijos: {"x", "y", "looted"}
wrecks = []        # naufragios: {"x", "y", "t", "dir", "phase"}
pages = set()      # páginas del diario encontradas (posición en DIARIO)
read = set()       # páginas ya leídas
S = {"generated": False, "open": False, "pos": 0}


def reset():
    caches.clear()
    wrecks.clear()
    pages.clear()
    read.clear()
    S.update({"generated": False, "open": False, "pos": 0})


# ============================================================================
# BOTÍN
# ============================================================================
def give(item, n):
    p = estado.player
    if item in _ATRIBUTO:
        setattr(p, _ATRIBUTO[item], getattr(p, _ATRIBUTO[item]) + n)
    else:                                   # lingotes y piezas van a la carga del barco
        p.cargo[item] = p.cargo.get(item, 0) + n


def roll_loot(table, rolls):
    got = {}
    for _ in range(rolls):
        _, item, lo, hi = random.choices(table, weights=[t[0] for t in table])[0]
        got[item] = got.get(item, 0) + random.randint(lo, hi)
    for item, n in got.items():
        give(item, n)
    return got


def _texto_botin(got):
    return ", ".join(f"{NOMBRES[k]} {n}" for k, n in got.items())


def give_page():
    """Entrega la siguiente página del diario (en orden). Devuelve True si había alguna por encontrar."""
    left = [i for i in range(len(DIARIO)) if i not in pages]
    if not left:
        return False
    pages.add(left[0])
    estado.log(f"Página del diario encontrada ({len(pages)}/{len(DIARIO)}). Pulsa T para leerla.")
    return True


# ============================================================================
# ALIJOS Y NAUFRAGIOS
# ============================================================================
def generate():
    """Reparte los alijos por la isla. Se llama sola al empezar una partida nueva."""
    S["generated"] = True
    caches.clear()
    p = estado.player
    tries = 0
    while len(caches) < CACHE_COUNT and tries < 1000:
        tries += 1
        tx, ty = random.randint(2, estado.WORLD_W - 3), random.randint(2, estado.WORLD_H - 3)
        if not estado.WORLD_MASK[ty][tx] or mundo.tile_water(tx, ty) or mundo.tile_solid(tx, ty):
            continue
        x, y = tx * TILE + 8, ty * TILE + 8
        if mundo.dist(x, y, p.x, p.y) < CACHE_MIN_START:
            continue
        if any(mundo.dist(x, y, c["x"], c["y"]) < CACHE_MIN_SEP for c in caches):
            continue
        caches.append({"x": x, "y": y, "looted": False})


def _agua_abierta(x, y):
    tx, ty = int(x // TILE), int(y // TILE)
    return all(mundo.tile_water(tx + a, ty + b) for a in range(-2, 3) for b in range(-2, 3))


def _rumbo(a):
    nombres = ("este", "sureste", "sur", "suroeste", "oeste", "noroeste", "norte", "noreste")
    return nombres[int(((a + math.pi / 8) % math.tau) / (math.pi / 4))]


def spawn_wreck():
    """Crea un naufragio en mar abierto. Devuelve el rumbo ("norte", "sureste"...) o None si no encontró lugar."""
    cx, cy = estado.WORLD_CENTER
    for _ in range(40):
        a = random.uniform(0, math.tau)
        orilla, r = 0, 0.0
        while r < max(estado.WORLD_W, estado.WORLD_H):
            if not mundo.tile_water(int(cx + math.cos(a) * r), int(cy + math.sin(a) * r)):
                orilla = r
            r += 1.0
        d = orilla + 1 + random.randint(*WRECK_EXTRA_TILES)
        x, y = (cx + math.cos(a) * d) * TILE + 8, (cy + math.sin(a) * d) * TILE + 8
        if _agua_abierta(x, y):
            wrecks.append({"x": x, "y": y, "t": WRECK_LIFETIME, "dir": _rumbo(a), "phase": random.uniform(0, 6.28)})
            return _rumbo(a)
    return None


def update(dt):
    _leer_teclas_de_pagina()
    if estado.in_mine:
        return
    if not S["generated"]:
        generate()
    for w in wrecks:
        w["t"] -= dt
    hundidos = [w for w in wrecks if w["t"] <= 0]
    for w in hundidos:
        wrecks.remove(w)
        estado.log("El mar se llevó los restos del naufragio.")


def interact():
    """Llamada al inicio de interact(): True si abrió un alijo o registró un naufragio."""
    if estado.in_mine:
        return False
    p = estado.player
    for c in caches:
        if not c["looted"] and mundo.dist(p.x, p.y, c["x"], c["y"]) <= REACH:
            c["looted"] = True
            got = roll_loot(LOOT_CACHE, CACHE_ROLLS)
            estado.log("Abres el alijo: " + _texto_botin(got) + ".")
            if random.random() < CACHE_PAGE_CHANCE:
                give_page()
            return True
    for w in wrecks:
        if mundo.dist(p.x, p.y, w["x"], w["y"]) <= REACH_WRECK:
            wrecks.remove(w)
            got = roll_loot(LOOT_WRECK, WRECK_ROLLS)
            estado.log("Registras los restos del naufragio: " + _texto_botin(got) + ".")
            give_page()
            return True
    return False


# ============================================================================
# DIARIO
# ============================================================================
def toggle_diary():
    """Tecla T: abre el diario en la primera página sin leer, o lo cierra si ya estaba abierto."""
    found = sorted(pages)
    if S["open"]:
        S["open"] = False
        return
    if not found:
        estado.log("Aún no tienes páginas del diario. Los alijos, los naufragios y las hordas vencidas las dejan.")
        return
    sin_leer = [k for k, i in enumerate(found) if i not in read]
    S["pos"] = sin_leer[0] if sin_leer else len(found) - 1
    S["open"] = True
    read.add(found[S["pos"]])


def turn_page(delta):
    """Teclas O (anterior) y P (siguiente) con el diario abierto."""
    found = sorted(pages)
    if not S["open"] or not found:
        return
    S["pos"] = max(0, min(len(found) - 1, S["pos"] + delta))
    read.add(found[S["pos"]])


_teclas = {"o": False, "p": False}


def _leer_teclas_de_pagina():
    k = pygame.key.get_pressed()
    k_o, k_p = k[pygame.K_o], k[pygame.K_p]
    if S["open"]:
        if k_o and not _teclas["o"]:
            turn_page(-1)
        if k_p and not _teclas["p"]:
            turn_page(1)
    _teclas["o"], _teclas["p"] = k_o, k_p
    

def _envolver(font, texto, ancho):
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
    return lineas


def draw_diary(surface):
    if not S["open"]:
        return
    found = sorted(pages)
    if S["pos"] >= len(found):
        S["open"] = False
        return
    w, h = min(SCREEN_W - 60, int(560 * UI_S)), int(260 * UI_S)
    x, y = (SCREEN_W - w) // 2, (SCREEN_H - h) // 2
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    panel.fill((22, 20, 18, 235))
    surface.blit(panel, (x, y))
    pygame.draw.rect(surface, (150, 130, 90), pygame.Rect(x, y, w, h), 2)
    hud.draw_text(surface, f"Diario del Navegante  —  página {found[S['pos']] + 1} de {len(DIARIO)}",
                  (x + 18, y + 14), FONT_MED, (225, 200, 140))
    cy = y + int(52 * UI_S)
    for linea in _envolver(FONT_SMALL, DIARIO[found[S["pos"]]], w - 36):
        hud.draw_text(surface, linea, (x + 18, cy), FONT_SMALL, (225, 220, 205))
        cy += int(22 * UI_S)
    abiertos = sum(1 for c in caches if c["looted"])
    pie = f"O / P: cambiar de página ({S['pos'] + 1} de {len(found)})   ·   T: cerrar   ·   alijos {abiertos}/{len(caches)}"    
    hud.draw_text(surface, pie, (x + 18, y + h - int(30 * UI_S)), FONT_SMALL, (141, 145, 120))


def draw_hud(surface):
    draw_diary(surface)


# ============================================================================
# DIBUJO EN EL MUNDO
# ============================================================================
def _cerca(x, y, rango):
    return mundo.dist(estado.player.x, estado.player.y, x, y) <= rango


def draw_world(surface):
    if estado.in_mine:
        return
    u = PIXEL_SCALE
    for c in caches:
        sx, sy = camara.world_to_screen(c["x"], c["y"])
        if sx < -40 or sy < -40 or sx > SCREEN_W + 40 or sy > SCREEN_H + 40:
            continue
        if c["looted"]:
            dibujo.px(surface, sx - 6 * u, sy - 2 * u, 12 * u, 6 * u, (70, 52, 34))          # caja vacía
            dibujo.px(surface, sx - 7 * u, sy - 5 * u, 12 * u, 2 * u, (100, 74, 46))         # tapa abierta
        else:
            dibujo.px(surface, sx - 6 * u, sy - 4 * u, 12 * u, 8 * u, (122, 86, 52))         # caja
            dibujo.px(surface, sx - 6 * u, sy - 4 * u, 12 * u, 2 * u, (150, 108, 66))        # tapa
            dibujo.px(surface, sx - 1 * u, sy - 4 * u, 2 * u, 8 * u, (150, 150, 150))        # cinta metálica
            if _cerca(c["x"], c["y"], REACH):
                img = FONT_SMALL.render("E: abrir alijo", True, (240, 225, 160))
                surface.blit(img, (sx - img.get_width() // 2, sy - 8 * u - img.get_height()))
    for w in wrecks:
        sx, sy = camara.world_to_screen(w["x"], w["y"])
        if sx < -40 or sy < -40 or sx > SCREEN_W + 40 or sy > SCREEN_H + 40:
            continue
        bob = math.sin(pygame.time.get_ticks() / 500 + w["phase"]) * 1.2 * u
        dibujo.px(surface, sx - 9 * u, sy + 3 * u + bob, 18 * u, 1 * u, (84, 120, 134))       # espuma
        dibujo.px(surface, sx - 8 * u, sy - 1 * u + bob, 14 * u, 3 * u, (110, 78, 48))        # tabla larga
        dibujo.px(surface, sx - 3 * u, sy - 4 * u + bob, 9 * u, 3 * u, (90, 64, 40))          # tabla cruzada
        dibujo.px(surface, sx + 4 * u, sy - 6 * u + bob, 5 * u, 6 * u, (70, 56, 46))          # barril
        if _cerca(w["x"], w["y"], REACH_WRECK * 3):
            img = FONT_SMALL.render("E: registrar restos", True, (240, 225, 160))
            surface.blit(img, (sx - img.get_width() // 2, sy - 12 * u - img.get_height()))


# ============================================================================
# GUARDADO
# ============================================================================
def save_data():
    return {"caches": [[c["x"], c["y"], 1 if c["looted"] else 0] for c in caches],
            "pages": sorted(pages), "read": sorted(read)}


def load_data(d):
    reset()
    if not d:
        return
    for x, y, l in d.get("caches", []):
        caches.append({"x": x, "y": y, "looted": bool(l)})
    pages.update(i for i in d.get("pages", []) if 0 <= i < len(DIARIO))
    read.update(i for i in d.get("read", []) if 0 <= i < len(DIARIO))
    S["generated"] = bool(caches)
