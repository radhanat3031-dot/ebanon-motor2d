"""Consumibles y crafteo.

Salió de ebanon.py (original), alrededor de las líneas 2053-2140.
"""

import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global estado
    from nucleo import estado


# ----------------------------------------------------------------------------
# 12. CONSUMIBLES Y CRAFTEO
# ----------------------------------------------------------------------------
def use_food():
    if estado.player.inv_food <= 0 or estado.player.hunger >= estado.player.max_hunger:
        return
    estado.player.inv_food -= 1
    estado.player.hunger = min(estado.player.max_hunger, estado.player.hunger + 30)
    pygame.mixer.Channel(7).play(eating_sound)
    estado.log("Comiste algo.")

def use_bandage():
    if estado.player.bandages <= 0 or estado.player.hp >= estado.player.max_hp:
        return
    estado.player.bandages -= 1
    estado.player.hp = min(estado.player.max_hp, estado.player.hp + 30)
    estado.log("Te vendaste las heridas.")

def craft_axe():
    if estado.player.has_axe or estado.player.inv_wood < 3 or estado.player.inv_scrap < 2:
        return
    estado.player.inv_wood -= 3
    estado.player.inv_scrap -= 2
    estado.player.has_axe = True
    estado.player.axe_durability = TOOL_DURABILITY_MAX["axe"]
    estado.log("Crafteaste un hacha.")

def craft_pickaxe():
    if estado.player.has_pickaxe or estado.player.inv_wood < 4 or estado.player.inv_scrap < 5:
        return
    estado.player.inv_wood -= 4
    estado.player.inv_scrap -= 5
    estado.player.has_pickaxe = True
    estado.player.pickaxe_durability = TOOL_DURABILITY_MAX["pickaxe"]
    estado.player.pickaxe_low_warned = False
    estado.log("Crafteaste un pico.")

def craft_bat():
    if estado.player.has_bat or estado.player.inv_wood < 4 or estado.player.inv_scrap < 4:
        return
    estado.player.inv_wood -= 4
    estado.player.inv_scrap -= 4
    estado.player.has_bat = True
    estado.player.bat_durability = TOOL_DURABILITY_MAX["bat"]
    estado.log("Crafteaste un bat con tornillos.")
    
def craft_hammer():
    if estado.player.has_hammer or estado.player.inv_wood < 3 or estado.player.inv_scrap < 3:
        return
    estado.player.inv_wood -= 3
    estado.player.inv_scrap -= 3
    estado.player.has_hammer = True
    estado.log("Crafteaste un martillo. Clic repara, X desmonta.")
    
def use_tool_durability(tool_name):
    """Gasta 1 uso de durabilidad. Al llegar a 0 la herramienta NO se pierde: queda rota (no sirve)
    hasta que la repares en un banco de trabajo."""
    if tool_name not in ("axe", "pickaxe", "bat"):
        return
    p = estado.player
    antes = getattr(p, tool_name + "_durability")
    if antes <= 0:
        return
    ahora = antes - 1
    setattr(p, tool_name + "_durability", ahora)
    nombre = WEAPON_LABELS[tool_name].lower()
    if ahora <= 0:
        estado.log(f"¡Tu {nombre} se rompió! No se pierde: repárala en un banco de trabajo.")
    elif ahora <= TOOL_DURABILITY_MAX[tool_name] * 0.25 and not getattr(p, tool_name + "_low_warned"):
        setattr(p, tool_name + "_low_warned", True)
        estado.log(f"Tu {nombre} está a punto de romperse.")


