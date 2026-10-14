"""Cambio entre mapas (isla <-> mina, fundidora, refinería, deshuesadero).

Salió de ebanon.py (original), alrededor de las líneas 7355-7477.
"""

import random
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global baca_jefe, construccion, deshuesadero, estado, fundidora
    global mina, mundo, neri_jefe, refineria
    from jefes import baca_jefe, neri_jefe
    from mapas import deshuesadero, fundidora, mina, refineria
    from nucleo import estado, mundo
    from sistemas import construccion


def enter_map(kind):
    """Entra a un mapa interior: 'mine' o 'foundry'. La isla se guarda y se restaura al salir."""
    
    
    if estado.in_mine:
        return
    lists = mina._entity_lists()
    estado.island_stash = {
        "world": mundo.WORLD, "mask": estado.WORLD_MASK, "w": estado.WORLD_W, "h": estado.WORLD_H,
        "center": estado.WORLD_CENTER, "radius": estado.WORLD_RADIUS,
        "boss": estado.boss, "baca": baca_jefe.baca, "gun": estado.gun_pickup,
        "px": estado.player.x, "py": estado.player.y,
        "lists": {k: list(v) for k, v in lists.items()},
    }
    for v in lists.values():
        v.clear()
    estado.boss = None
    baca_jefe.baca = None
    estado.gun_pickup = None
    fundidora.map_kind = kind
    stash = {"mine": estado.mine_stash, "foundry": fundidora.foundry_stash, "refinery": refineria.refinery_stash}.get(
        kind, deshuesadero.map_stashes.get(kind))    
    first_time = stash is None
    if kind == "mine":
        estado.MINE_ZOMBIE_CAP = max(6, (MINE_W * MINE_H) // MINE_AREA_PER_ZOMBIE)
        if first_time:
            estado.mine_seed = random.randint(1, 10 ** 9)
            mine_broken.clear()
        else:
            estado.mine_seed = stash["seed"]
            mine_broken[:] = stash.get("broken", [])
        loot = mina.gen_mine(estado.mine_seed)
        if first_time:
            mina.spawn_mine_resources(loot)
    elif kind == "foundry":
        estado.MINE_ZOMBIE_CAP = fundidora.FOUNDRY_ZOMBIE_CAP
        loot = fundidora.gen_foundry()
        if first_time:
            fundidora.spawn_foundry_resources(loot)
    elif kind == "refinery":
        estado.MINE_ZOMBIE_CAP = refineria.REFINERY_ZOMBIE_CAP
        loot = refineria.gen_refinery()
        if first_time:
            refineria.spawn_refinery_resources(loot)
    else:
        estado.MINE_ZOMBIE_CAP = deshuesadero.JUNK_ZOMBIE_CAP
        loot = deshuesadero.gen_junkyard()
        if first_time:
            deshuesadero.spawn_fixed_resources(loot)                     
    if not first_time:
        estado.structures[:] = stash.get("structures", [])
        for st in estado.structures:
            construccion.init_structure(st)
        estado.drops[:] = stash.get("drops", [])
        estado.wood_pickups[:] = stash.get("wood", [])
        estado.rock_pickups[:] = stash.get("rock", [])
        estado.scrap_pickups[:] = stash.get("scrap", [])
        estado.food_pickups[:] = stash.get("food", [])
        estado.ammo_pickups[:] = stash.get("ammo", [])
    neri_jefe.lair_reset()
    estado.in_mine = True
    estado.player.x, estado.player.y = MINE_INFO["start"]
    estado.player.vx = estado.player.vy = 0.0
    bats.clear()
    mine_field.clear()
    estado.mine_field_t = 0.0
    estado.bat_spawn_timer = 3.0
    if kind == "mine" and (first_time or not stash.get("dyn")):
        refineria.spawn_mine_dynamite()                      # la dinamita solo se encuentra en la mina
    estado.zombie_spawn_timer = 10.0 if kind == "mine" else 6.0
    construccion.clear_build_selection()
    estado.log({"mine": "Entras a la mina. Huele a humedad y a algo podrido.",
         "foundry": "Entras a la fundidora. El metal frío huele a óxido y a podredumbre.",
         "refinery": "Entras a la refinería. El aire quema por olor a combustible.",
         "junkyard": "Entras al deshuesadero. El óxido cruje bajo tus pies."}[kind])

def leave_map():
    
    
    
    if not estado.in_mine:
        return
    kind = fundidora.map_kind
    data = {"dyn": True, "structures": list(estado.structures), "drops": list(estado.drops),            
            "wood": list(estado.wood_pickups), "rock": list(estado.rock_pickups), "scrap": list(estado.scrap_pickups),
            "food": list(estado.food_pickups), "ammo": list(estado.ammo_pickups)}
    if kind == "mine":
        data["seed"] = estado.mine_seed
        data["broken"] = [list(b) for b in mine_broken]
        estado.mine_stash = data
    elif kind == "foundry":
        fundidora.foundry_stash = data
    elif kind == "refinery":
        refineria.refinery_stash = data
    else:
        deshuesadero.map_stashes[kind] = data   
    s = estado.island_stash
    mundo.WORLD, estado.WORLD_MASK = s["world"], s["mask"]
    estado.WORLD_W, estado.WORLD_H = s["w"], s["h"]
    estado.WORLD_CENTER, estado.WORLD_RADIUS = s["center"], s["radius"]
    estado.boss, baca_jefe.baca, estado.gun_pickup = s["boss"], s["baca"], s["gun"]
    for k, v in mina._entity_lists().items():
        v[:] = s["lists"].get(k, [])
    bats.clear()
    mine_breakable.clear()
    neri_jefe.lair_reset()
    mine_field.clear()
    estado.mine_field_t = 0.0
    estado.in_mine = False
    fundidora.map_kind = "mine"
    estado.MINE_ZOMBIE_CAP = max(6, (MINE_W * MINE_H) // MINE_AREA_PER_ZOMBIE)
    estado.player.x, estado.player.y = s["px"], s["py"]
    estado.player.vx = estado.player.vy = 0.0
    construccion.clear_build_selection()
    estado.log({"mine": "Sales de la mina.", "foundry": "Sales de la fundidora.",
         "refinery": "Sales de la refinería.", "junkyard": "Sales del deshuesadero."}[kind])
    
def enter_mine():                 # estas dos reemplazan a las versiones viejas
    enter_map("mine")


def leave_mine():
    leave_map()
