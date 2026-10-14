"""Colisiones.

Salió de ebanon.py (original), alrededor de las líneas 1208-1258.
"""

from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global estado, mundo
    from nucleo import estado, mundo


# ----------------------------------------------------------------------------
# 7. COLISIÓN
# ----------------------------------------------------------------------------
def wall_at(tx, ty):
    for st in estado.structures:
        if st["type"] in ("wall", "wallStone"):
            if int(st["x"] // TILE) == tx and int(st["y"] // TILE) == ty:
                return True
    return False

def door_at(tx, ty):
    for st in estado.structures:
        if st["type"] == "door" and int(st["x"] // TILE) == tx and int(st["y"] // TILE) == ty:
            return st
    return None

def near_fire(x, y, radius=FIRE_RADIUS):
    for st in estado.structures:
        if st["type"] == "fire" and st.get("fuel", 1) > 0 and mundo.dist(x, y, st["x"], st["y"]) < radius:
            return True
    return False

def rebuild_prop_tiles():
    estado.prop_tiles.clear()
    for name, lst in (("wood", estado.wood_pickups), ("rock", estado.rock_pickups), ("scrap", estado.scrap_pickups),
                      ("food", estado.food_pickups), ("ammo", estado.ammo_pickups)):
        if name not in SOLID_PICKUPS:
            continue
        for p in lst:
            if p["active"]:
                estado.prop_tiles.add((int(p["x"] // TILE), int(p["y"] // TILE)))
    for st in estado.structures:
        if st["type"] in SOLID_STRUCTURES:
            estado.prop_tiles.add((int(st["x"] // TILE), int(st["y"] // TILE)))

def blocked(tx, ty, is_zombie, ignore_props=False):
    # Bloquea roca/ruina, muros y (salvo que se ignore) recursos y fogatas
    if mundo.tile_solid(tx, ty) or wall_at(tx, ty):
        return True
    if not ignore_props and (tx, ty) in estado.prop_tiles:
        return True
    # Agua no bloquea, se maneja con reducción de velocidad
    if mundo.tile_water(tx, ty):
        return False
    d = door_at(tx, ty)
    if d:
        return True if is_zombie else (not d["open"])
    return False

def cardinal_from_aim():
    ax, ay = estado.player.aim_x, estado.player.aim_y
    if abs(ax) >= abs(ay):
        return (1 if ax >= 0 else -1), 0
    return 0, (1 if ay >= 0 else -1)
