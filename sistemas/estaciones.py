"""Estaciones y herramientas por nivel.

BANCO DE TRABAJO (tecla 0 en el menú de construcción, B):
  - El pico y el bate ya no se craftean en cualquier lado: hay que estar junto a un banco.
    (El hacha y el martillo se siguen haciendo en cualquier parte, para poder arrancar.)
  - El banco tiene nivel según lo que construyas a su alrededor:
        nivel 1  el banco solo
        nivel 2  + una fogata encendida cerca
        nivel 3  + un almacén (cofre) cerca
  - Con el banco cerca, equipa un hacha, pico o bate y pulsa E para MEJORARLO:
        nivel 2 (reforzado)  pide banco nivel 2, y materiales (incluye piedra, o sea: ya necesitas pico)
        nivel 3 (hierro)     pide banco nivel 3 y lingotes (los mismos que necesita el barco)
    Cada nivel gasta menos golpes, rinde más recursos, dura más y pega más fuerte.
  - Si la herramienta se rompe NO se pierde: queda inútil hasta que la repares en el banco (E o botón Reparar de la mochila).

Aquí también viven los ganchos hacia habilidades.py (xp, bonos, guardado) para que el resto del
juego solo tenga que hablar con este archivo.
"""

import pygame
from nucleo.ajustes import *  # noqa: F401,F403
from sistemas import construccion
from sistemas import habilidades


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global dibujo, estado, mundo
    global hogar
    from interfaz import dibujo
    from nucleo import estado, mundo
    from sistemas import hogar


# ============================================================================
# AJUSTES
# ============================================================================
BENCH_RANGE = 3 * TILE          # ← qué tan cerca del banco debes estar para usarlo
BENCH_AURA = 6 * TILE           # ← radio en que la fogata / el almacén suben el nivel del banco
BENCH_NEEDED_FOR = ("pickaxe", "bat")        # ← qué herramientas piden banco para craftearse
REPAIR_COST = {}      # ← materiales por cada herramienta reparada. Vacío = gratis (como en Valheim). Ejemplo: {"scrap": 1}

# Por nivel: name, dur (durabilidad), hits (golpes por árbol/roca), yield (madera/piedra), mult (daño),
#            cost (materiales para llegar a ese nivel), bench (nivel de banco que pide)
TIERS = {
    "axe": [
        {"name": "HACHA", "dur": 120, "hits": 7, "yield": 3, "mult": 1.0},
        {"name": "HACHA REFORZADA", "dur": 170, "hits": 6, "yield": 4, "mult": 1.15,
         "cost": {"wood": 6, "scrap": 6, "stone": 4}, "bench": 2},
        {"name": "HACHA DE HIERRO", "dur": 240, "hits": 5, "yield": 5, "mult": 1.30,
         "cost": {"wood": 4, "scrap": 8, "ingot": 6}, "bench": 3},
    ],
    "pickaxe": [
        {"name": "PICO", "dur": 100, "hits": 9, "yield": 3, "mult": 1.0},
        {"name": "PICO REFORZADO", "dur": 140, "hits": 8, "yield": 4, "mult": 1.15,
         "cost": {"wood": 6, "scrap": 8, "stone": 4}, "bench": 2},
        {"name": "PICO DE HIERRO", "dur": 200, "hits": 6, "yield": 5, "mult": 1.30,
         "cost": {"wood": 4, "scrap": 10, "ingot": 6}, "bench": 3},
    ],
    "bat": [
        {"name": "BATE", "dur": 50, "hits": 0, "yield": 0, "mult": 1.0},
        {"name": "BATE CON CLAVOS", "dur": 75, "hits": 0, "yield": 0, "mult": 1.20,
         "cost": {"wood": 4, "scrap": 8}, "bench": 2},
        {"name": "BATE DE HIERRO", "dur": 110, "hits": 0, "yield": 0, "mult": 1.45,
         "cost": {"scrap": 8, "ingot": 6}, "bench": 3},
    ],
}
MAT_NAMES = {"wood": "madera", "scrap": "chatarra", "stone": "piedra", "ingot": "lingotes"}

# ---- el banco como construcción ---------------------------------------------
BUILD_COSTS["bench"] = {"wood": 8, "scrap": 3, "stone": 0}          # ← costo del banco
BUILD_NAMES["bench"] = "Banco de trabajo construido."
BUILD_LABELS["bench"] = "0) Banco de trabajo  (Madera 8, Chatarra 3)"
BUILD_KEYS[pygame.K_0] = "bench"
construccion.BUILD_TITLES["bench"] = "Banco de trabajo"

tiers = {"axe": 0, "pickaxe": 0, "bat": 0}            # nivel actual de cada herramienta (0, 1 o 2)


# ============================================================================
# BANCO
# ============================================================================
def _lit_fire(st):
    return st["type"] == "fire" and st.get("fuel", 1) > 0


def bench_near():
    """El banco más cercano al jugador (dentro de BENCH_RANGE) o None."""
    p = estado.player
    best, best_d = None, BENCH_RANGE + 1
    for st in estado.structures:
        if st["type"] == "bench":
            d = mundo.dist(p.x, p.y, st["x"], st["y"])
            if d <= BENCH_RANGE and d < best_d:
                best, best_d = st, d
    return best


def bench_level(bench):
    lvl = 1
    near = [s for s in estado.structures if mundo.dist(bench["x"], bench["y"], s["x"], s["y"]) <= BENCH_AURA]
    if any(_lit_fire(s) for s in near):
        lvl += 1
    if any(s["type"] == "chest" for s in near):
        lvl += 1
    return lvl


def can_craft(name):
    """Llamada desde el menú de la mochila antes de craftear una herramienta."""
    if name in BENCH_NEEDED_FOR and bench_near() is None:
        estado.log("Necesitas un banco de trabajo cerca (B, tecla 0) para craftear eso.")
        return False
    return True


def after_craft(name):
    """Una herramienta recién crafteada empieza en nivel 1."""
    if name in tiers and getattr(estado.player, "has_" + name, False):
        tiers[name] = 0
        setattr(estado.player, name + "_durability", TIERS[name][0]["dur"])
        refresh()


def use_bench(bench):
    """E junto al banco: mejora la herramienta equipada."""
    p = estado.player
    lvl = bench_level(bench)
    tool = p.equipped
    if tool in TIERS and getattr(p, "has_" + tool, False) and getattr(p, tool + "_durability", 1) < TOOL_DURABILITY_MAX[tool]:
        repair_all()                      # primero se repara; con la herramienta como nueva, E otra vez la mejora
        return
    if tool not in TIERS or not getattr(p, "has_" + tool, False):
        estado.log(f"Banco de trabajo nivel {lvl}. Equipa hacha, pico o bate (TAB) y pulsa E para mejorarlo.")
        return
    t = tiers[tool]
    if t >= len(TIERS[tool]) - 1:
        estado.log(f"{TIERS[tool][t]['name']} ya está al máximo.")
        return
    nxt = TIERS[tool][t + 1]
    if lvl < nxt["bench"]:
        estado.log(f"Para mejorar a {nxt['name']} necesitas banco nivel {nxt['bench']} (el tuyo es nivel {lvl}).")
        estado.log(f"Te falta construir: {missing_text(bench, nxt['bench'])}.")
        return
    missing = []
    for k, n in nxt["cost"].items():
        have = p.cargo.get(k, 0) if k == "ingot" else getattr(p, "inv_" + k)
        if have < n:
            missing.append(f"{MAT_NAMES[k]} {n - have}")
    if missing:
        estado.log(f"Para {nxt['name']} faltan: " + ", ".join(missing) + ".")
        return
    for k, n in nxt["cost"].items():
        if k == "ingot":
            p.cargo["ingot"] = p.cargo.get("ingot", 0) - n
        else:
            setattr(p, "inv_" + k, getattr(p, "inv_" + k) - n)
    tiers[tool] = t + 1
    setattr(p, tool + "_durability", nxt["dur"])
    setattr(p, tool + "_low_warned", False)
    refresh()
    pygame.mixer.Channel(14).play(hammer_sound)
    estado.log(f"¡Mejoraste a {nxt['name']}!")


# ============================================================================
# EFECTOS DE NIVEL (los usan interaccion.py y combate.py)
# ============================================================================
def tier_of(tool):
    return tiers.get(tool, 0)


def hits_needed(tool, default):
    return TIERS[tool][tier_of(tool)]["hits"] or default


def gather_yield(tool, skill):
    return TIERS[tool][tier_of(tool)]["yield"] + habilidades.extra_yield(skill)


def melee_damage(tool, base):
    if is_broken(tool):
        return int(round(MELEE_DAMAGE["fist"] * habilidades.melee_mult()))      # rota: pega como un puño
    mult = TIERS[tool][tier_of(tool)]["mult"] if tool in TIERS else 1.0
    return int(round(base * mult * habilidades.melee_mult()))


def on_built(st):
    """Llamada al colocar una estructura: xp de Constructor y bono de vida."""
    habilidades.gain("constructor", 3)
    if st.get("max_hp"):
        st["max_hp"] = st["hp"] = int(st["max_hp"] * habilidades.struct_hp_mult())


# ---- pasos hacia habilidades.py ----------------------------------------------
def xp(skill, amount=1):
    habilidades.gain(skill, amount + hogar.bonus_xp(amount))     # Descansado da experiencia extra


def saves_wear(skill):
    return habilidades.saves_durability(skill)


def skill_line(surface, x, y):
    return habilidades.draw_summary(surface, x, y)


# ============================================================================
# NOMBRES, GUARDADO, REINICIO Y DIBUJO
# ============================================================================
def _bench_parts(bench):
    """(¿hay fogata encendida cerca del banco?, ¿hay almacén cerca del banco?)"""
    near = [s for s in estado.structures if mundo.dist(bench["x"], bench["y"], s["x"], s["y"]) <= BENCH_AURA]
    return any(_lit_fire(s) for s in near), any(s["type"] == "chest" for s in near)


def missing_text(bench, needed):
    """Qué construir para que el banco llegue al nivel `needed` ('' si ya llega)."""
    fire, chest = _bench_parts(bench)
    lvl = 1 + int(fire) + int(chest)
    if lvl >= needed:
        return ""
    falta = []
    if not fire:
        falta.append("una FOGATA encendida (B, tecla 2)")
    if not chest:
        falta.append("un ALMACÉN (B, tecla 3)")
    unidad = " o " if needed - lvl < len(falta) else " y "      # a veces basta con una de las dos
    return unidad.join(falta) + f", a menos de {BENCH_AURA // TILE} casillas del banco"


def draw_status(surface):
    """Cerca de un banco: muestra su nivel y qué le falta para subir."""
    p = estado.player
    best, best_d = None, 8 * TILE
    for st in estado.structures:
        if st["type"] == "bench":
            d = mundo.dist(p.x, p.y, st["x"], st["y"])
            if d < best_d:
                best, best_d = st, d
    if best is None:
        return
    lvl = bench_level(best)
    lines = [(f"Banco de trabajo: nivel {lvl} de 3", (217, 183, 74))]
    if lvl < 3:
        lines.append((f"Para subirlo: {missing_text(best, lvl + 1)}", (141, 145, 120)))
    for i, (txt, col) in enumerate(lines):
        img = FONT_SMALL.render(txt, True, col)
        surface.blit(img, (SCREEN_W - img.get_width() - 14, int((110 + i * 18) * UI_S)))


def is_broken(tool):
    """¿La herramienta está rota (durabilidad 0)? Una rota no se pierde, pero no sirve hasta repararla."""
    p = estado.player
    return tool in ("axe", "pickaxe", "bat") and getattr(p, "has_" + tool, False) and getattr(p, tool + "_durability", 1) <= 0


def damaged_tools():
    """Tus herramientas con la durabilidad por debajo del máximo."""
    p = estado.player
    return [t for t in ("axe", "pickaxe", "bat")
            if getattr(p, "has_" + t, False) and getattr(p, t + "_durability") < TOOL_DURABILITY_MAX[t]]


def repair_all():
    """Repara todas tus herramientas. Hay que estar junto a un banco de trabajo."""
    p = estado.player
    if bench_near() is None:
        estado.log("Necesitas estar junto a un banco de trabajo para reparar.")
        return False
    tools = damaged_tools()
    if not tools:
        estado.log("Todas tus herramientas están en perfecto estado.")
        return False
    falta = []
    for k, n in REPAIR_COST.items():
        total = n * len(tools)
        have = p.cargo.get(k, 0) if k == "ingot" else getattr(p, "inv_" + k)
        if have < total:
            falta.append(f"{MAT_NAMES[k]} {total - have}")
    if falta:
        estado.log("Para reparar faltan: " + ", ".join(falta) + ".")
        return False
    for k, n in REPAIR_COST.items():
        total = n * len(tools)
        if k == "ingot":
            p.cargo["ingot"] = p.cargo.get("ingot", 0) - total
        else:
            setattr(p, "inv_" + k, getattr(p, "inv_" + k) - total)
    for t in tools:
        setattr(p, t + "_durability", TOOL_DURABILITY_MAX[t])
        setattr(p, t + "_low_warned", False)
    pygame.mixer.Channel(14).play(hammer_sound)
    estado.log("Reparaste: " + ", ".join(WEAPON_LABELS[t] for t in tools) + ".")
    return True


def refresh():
    """Pone el nombre y la durabilidad máxima de cada herramienta según su nivel."""
    for tool, lst in TIERS.items():
        WEAPON_LABELS[tool] = lst[tiers[tool]]["name"]
        TOOL_DURABILITY_MAX[tool] = lst[tiers[tool]]["dur"]


def save_data():
    return {"tiers": dict(tiers), "skills": habilidades.save_data()}


def load_data(d):
    d = d or {}
    for k in tiers:
        tiers[k] = max(0, min(len(TIERS[k]) - 1, int(d.get("tiers", {}).get(k, 0))))
    habilidades.load_data(d.get("skills"))
    refresh()


def reset():
    for k in tiers:
        tiers[k] = 0
    habilidades.reset()
    refresh()


def draw_bench(surface, sx, sy):
    """Dibujo de respaldo del banco (si no existe assets/sprites/st_bench.png)."""
    u = PIXEL_SCALE
    dibujo.px(surface, sx, sy + 5 * u, 16 * u, 4 * u, PALETTE["door_plank"])          # tablero
    dibujo.px(surface, sx, sy + 5 * u, 16 * u, 1 * u, PALETTE["wall_dark"])
    dibujo.px(surface, sx + 1 * u, sy + 9 * u, 2 * u, 6 * u, PALETTE["wall_dark"])      # patas
    dibujo.px(surface, sx + 13 * u, sy + 9 * u, 2 * u, 6 * u, PALETTE["wall_dark"])
    dibujo.px(surface, sx + 3 * u, sy + 2 * u, 6 * u, 2 * u, PALETTE["wall_dark"])      # martillo encima
    dibujo.px(surface, sx + 8 * u, sy + 1 * u, 2 * u, 4 * u, PALETTE["door_dark"])
    dibujo.px(surface, sx + 11 * u, sy + 3 * u, 3 * u, 2 * u, PALETTE["door_dark"])     # clavos / tablita
