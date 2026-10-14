"""Almacén / cofres.

Salió de ebanon.py (original), alrededor de las líneas 2023-2048.
"""

from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global estado
    from nucleo import estado


# ----------------------------------------------------------------------------
# 11. ALMACÉN
# ----------------------------------------------------------------------------
def open_storage(st):
    
    if "store" not in st:
        st["store"] = {"wood": 0, "scrap": 0, "stone": 0, "food": 0, "bandages": 0}
    estado.active_chest = st
    estado.inventory_open = False

def close_storage():
    
    estado.active_chest = None

def move_to_chest(key):
    bag_attr = STORE_BAG_MAP[key]
    if getattr(estado.player, bag_attr) > 0:
        if estado.chest_capacity_used(estado.active_chest) >= CHEST_CAPACITY:
            estado.log("El almacén está lleno. Construye otro cofre.")
            return
        setattr(estado.player, bag_attr, getattr(estado.player, bag_attr) - 1)
        estado.active_chest["store"][key] += 1
        estado.log(f"Guardaste {key} en el cofre ({estado.chest_capacity_used(estado.active_chest)}/{CHEST_CAPACITY}).")

def move_to_bag(key):
    bag_attr = STORE_BAG_MAP[key]
    if estado.active_chest["store"][key] > 0:
        estado.active_chest["store"][key] -= 1
        setattr(estado.player, bag_attr, getattr(estado.player, bag_attr) + 1)
