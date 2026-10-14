"""Construcción de estructuras, fogatas y trampas.

Salió de ebanon.py (original), alrededor de las líneas 1263-3067.
"""

import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global actualizacion, almacen, barco, colision, estado
    global fundidora, mundo, neri_jefe
    global estaciones
    from jefes import neri_jefe
    from mapas import barco, fundidora
    from nucleo import estado, mundo
    from sistemas import actualizacion, almacen, colision
    from sistemas import estaciones


# ----------------------------------------------------------------------------
# 8. CONSTRUCCIÓN
# ----------------------------------------------------------------------------
def can_afford(t):
    c = BUILD_COSTS[t]
    return (estado.player.inv_wood >= c["wood"] and estado.player.inv_scrap >= c["scrap"] and estado.player.inv_stone >= c["stone"]
            and estado.player.cargo.get("ingot", 0) >= c.get("ingot", 0))

# Helper function para crear estructuras seguras
def create_structure(t, tx, ty):
    """Crea una estructura con la inicialización correcta."""
    c = BUILD_COSTS[t]
    
    # Verifica recursos
    if not can_afford(t):
        estado.log("No tienes suficientes materiales.")
        return False
    
    # Resta recursos
    estado.player.inv_wood -= c["wood"]
    estado.player.inv_scrap -= c["scrap"]
    estado.player.inv_stone -= c["stone"]
    
    # Crea estructura
    st = {"x": tx * TILE + TILE / 2, "y": ty * TILE + TILE / 2, "type": t}
    if t == "chest":
        st["store"] = {"wood": 0, "scrap": 0, "stone": 0, "food": 0, "bandages": 0}
    if t == "door":
        st["open"] = False
    
    # ¡CRUCIAL! Inicializa siempre la estructura
    init_structure(st)
    
    estado.structures.append(st)
    estado.log(BUILD_NAMES[t])
    return True
    
BUILD_RANGE = 6 * TILE   # alcance máximo de construcción desde el jugador
BUILD_TITLES = {"wall": "Muro", "fire": "Fogata", "chest": "Almacén",
                "wallStone": "Muro de piedra", "door": "Puerta"}
BUILD_TITLES["trapSpikes"] = "Trampa de clavos"
BUILD_TITLES["trapBear"] = "Cepo"

def screen_to_world(sx, sy):
    """Inversa de world_to_screen."""
    return sx / PIXEL_SCALE + estado.camera_x, sy / PIXEL_SCALE + estado.camera_y

def select_build(t):
    if not is_buildable(t):
        estado.log("Aún no sabes construir eso.")
        return
    
    estado.build_selected = t
    estado.log(f"{BUILD_TITLES[t]} seleccionado. Clic izquierdo construye, clic derecho cancela.")

def clear_build_selection():
    
    estado.build_selected = None

def placement_error(t, tx, ty):
    """None si se puede construir en ese tile; si no, el motivo."""
    if not (0 <= tx < estado.WORLD_W and 0 <= ty < estado.WORLD_H):
        return "No puedes construir fuera del mapa."
    if estado.in_mine and neri_jefe.lair["state"] == "sealed":
        return "No puedes construir mientras la guarida esté sellada."    
    cx, cy = tx * TILE + TILE / 2, ty * TILE + TILE / 2
    if mundo.dist(estado.player.x, estado.player.y, cx, cy) > BUILD_RANGE:
        return "Está demasiado lejos."
    if mundo.tile_solid(tx, ty):
        return "No puedes construir sobre roca/ruina."
    if mundo.tile_water(tx, ty):
        return "No puedes construir sobre agua."
    if mundo.tile_at(tx, ty) == mundo.TILE_TYPE["cave"]:
        return "No puedes construir en la entrada de la mina."
    if t == "dock":
        if estado.in_mine:
            return "El muelle solo se construye en la isla."
        if not any(mundo.tile_water(tx + a, ty + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            return "El muelle va en la orilla, pegado al agua."
        if mundo.dist(tx * TILE + 8, ty * TILE + 8, barco.BOAT_POS[0], barco.BOAT_POS[1]) > barco.DOCK_RANGE:
            return "Está demasiado lejos del barco."
    if (tx, ty) in estado.prop_tiles:
        return "Hay un recurso en ese lugar."
    for lst in (estado.food_pickups, estado.ammo_pickups):
        for p in lst:
            if p["active"] and int(p["x"] // TILE) == tx and int(p["y"] // TILE) == ty:
                return "Hay un recurso en ese lugar."    
    if tx == int(estado.player.x // TILE) and ty == int(estado.player.y // TILE):
        return "No puedes construir debajo de ti mismo."
    for s in estado.structures:
        if int(s["x"] // TILE) == tx and int(s["y"] // TILE) == ty:
            return "Ya hay algo construido ahí."
    if not can_afford(t):
        return "No tienes suficientes materiales."
    return None

def attempt_place_structure(world_x, world_y):
    """Construye la estructura seleccionada en el tile bajo (world_x, world_y).
    Mantiene la selección para poder construir varias seguidas."""
    if not estado.build_selected:
        return False
    tx, ty = int(world_x // TILE), int(world_y // TILE)
    err = placement_error(estado.build_selected, tx, ty)
    if err:
        estado.log(err)
        return False
    t = estado.build_selected
    c = BUILD_COSTS[t]
    estado.player.cargo["ingot"] = estado.player.cargo.get("ingot", 0) - c.get("ingot", 0)    
    estado.player.inv_wood -= c["wood"]
    estado.player.inv_scrap -= c["scrap"]
    estado.player.inv_stone -= c["stone"]
    st = {"x": tx * TILE + TILE / 2, "y": ty * TILE + TILE / 2, "type": t}
    if t == "chest":
        st["store"] = {"wood": 0, "scrap": 0, "stone": 0, "food": 0, "bandages": 0}
    if t == "door":
        st["open"] = False
    init_structure(st)        
    #      ↑ Esta línea añade el depósito de combustible 'fuel' etc.
    
    if t == "doorMetal":
        st["type"] = "door"
        st["open"] = False
        st["metal"] = True
        st["max_hp"] = st["hp"] = fundidora.DOOR_METAL_HP    
    
    estaciones.on_built(st)
    estado.structures.append(st)
    pygame.mixer.Channel(14).play(hammer_sound)     
    estado.log(BUILD_NAMES[t])
    return True

def init_structure(st):
    """Da HP (y combustible a las fogatas). También arregla partidas viejas al cargarlas."""
    t = st["type"]
    if t in STRUCT_HP:
        st.setdefault("max_hp", STRUCT_HP[t])
        st.setdefault("hp", st["max_hp"])
    if t == "fire":
        st.setdefault("fuel", FIRE_START_FUEL)
    return st

def structure_at_tile(tx, ty):
    for st in estado.structures:
        if int(st["x"] // TILE) == tx and int(st["y"] // TILE) == ty:
            return st
    return None

#---------------------------------------------------- PUNTO DE SEGURIDAD 1. HASTA AQUI FUNCIONA-----------------
#---------------------------------------------------------------------------------------------------------------

def damage_structure(st, amount):
    st["hp"] -= amount
    if not st.get("warned"):
        st["warned"] = True
        estado.log(f"¡Atacan: {BUILD_TITLES.get(st['type'], 'estructura')}!")
    if st["hp"] <= 0:
        destroy_structure(st)

def repair_structure(st, amount):
    """Lista para el futuro martillo: suma vida sin pasarse del máximo."""
    st["hp"] = min(st["max_hp"], st["hp"] + amount)
    if st["hp"] >= st["max_hp"]:
        st["warned"] = False

def destroy_structure(st, by_player=False):
    if st in estado.structures:
        estado.structures.remove(st)
    if estado.active_chest is st:
        almacen.close_storage()
    t = st["type"]
    title = BUILD_TITLES.get(t, "estructura")
    rate = REFUND_DISMANTLE if by_player else REFUND_DESTROYED
    items = {}
    for key in ("wood", "scrap", "stone"):
        n = int(BUILD_COSTS.get(t, {}).get(key, 0) * rate)
        if n > 0:
            items[key] = n
    msg = f"Desmontaste: {title}." if by_player else f"Estructura destruida: {title}."
    if t == "chest":
        store = st.get("store", {})
        if by_player:                        # desmontado: el contenido cae completo
            for key, n in store.items():
                if n > 0:
                    items[key] = items.get(key, 0) + n
        else:                                # destruido: solo se salva un objeto al azar
            pool = [key for key, n in store.items() for _ in range(n)]
            if pool:
                keep = random.choice(pool)
                items[keep] = items.get(keep, 0) + 1
                msg += " Solo se salvó un objeto."
    if items:
        estado.drops.append({"x": st["x"], "y": st["y"], "kind": "debris", "items": items})
    estado.log(msg)
    
def attack_structure_in_way(x, y, nx, ny, dt, dps):
    """Ataca la estructura que cierra el paso. Devuelve True si había algo que atacar."""
    for tx, ty in ((int(nx // TILE), int(ny // TILE)),
                   (int(nx // TILE), int(y // TILE)),
                   (int(x // TILE), int(ny // TILE))):
        st = structure_at_tile(tx, ty)
        if st and st["type"] in ATTACKABLE and "hp" in st:
            damage_structure(st, dps * dt)
            return True
    return False

def move_or_breach(e, nx, ny, dx, dy, speed, dt, dps):
    """Mueve a un zombi o al jefe hacia (nx, ny). Si algo le cierra el paso, intenta rodearlo
    caminando de lado; si lleva BREACH_AFTER segundos atascado, destruye la estructura."""
    if actualizacion._zombie_can_move(e, nx, ny):
        e.x, e.y = nx, ny
        e.block_t = max(0.0, e.block_t - dt * 2)
        return
    e.block_t += dt
    if e.block_t >= BREACH_AFTER:
        if attack_structure_in_way(e.x, e.y, nx, ny, dt, dps):
            return                      # está rompiendo la estructura: se queda ahí
    look = TILE * 0.75
    for _ in range(2):                  # prueba un lado y, si está cerrado, el otro
        sx, sy = -dy * e.detour_side, dx * e.detour_side
        if actualizacion._zombie_can_move(e, e.x + sx * look, e.y + sy * look):
            mx, my = e.x + sx * speed * dt, e.y + sy * speed * dt
            if actualizacion._zombie_can_move(e, mx, my):
                e.x, e.y = mx, my
            return
        e.detour_side = -e.detour_side
        
# ── Fogata ──
def add_fuel(st, amount):
    """Lista para el futuro: alimentar la fogata con madera. Devuelve True si estaba apagada."""
    was_out = st["fuel"] <= 0
    st["fuel"] = min(FIRE_MAX_FUEL, st["fuel"] + amount)
    return was_out

def update_fires(dt):
    for st in estado.structures:
        if st["type"] != "fire":
            continue
        init_structure(st)
        if st["fuel"] > 0:
            st["fuel"] = max(0.0, st["fuel"] - dt)
            if st["fuel"] == 0:
                estado.log("Una fogata se apagó.")
                
def update_fire_sound():
    ch = pygame.mixer.Channel(15)
    best, best_d = None, FIRE_RADIUS
    for st in estado.structures:
        if st["type"] == "fire" and st.get("fuel", 1) > 0:
            d = mundo.dist(estado.player.x, estado.player.y, st["x"], st["y"])
            if d < best_d:
                best, best_d = st, d
    if best is None:                       # fuera de rango o fogatas apagadas
        if ch.get_busy():
            ch.fadeout(400)
        return
    if not ch.get_busy() or ch.get_sound() is not fire_loop_sound:
        ch.play(fire_loop_sound, loops=-1, fade_ms=400)
    vol = FIRE_SOUND_VOLUME * max(0.15, 1 - best_d / FIRE_RADIUS)
    vol *= min(1.0, best.get("fuel", FIRE_DIM_TIME) / FIRE_DIM_TIME)
    ch.set_volume(vol)
                
def structure_at_mouse():
    mx, my = pygame.mouse.get_pos()
    wx, wy = screen_to_world(mx, my)
    st = structure_at_tile(int(wx // TILE), int(wy // TILE))
    if st and mundo.dist(estado.player.x, estado.player.y, st["x"], st["y"]) <= REPAIR_RANGE:
        return st
    return None

def use_hammer():
    if estado.player.attack_cooldown > 0:
        return
    estado.player.attack_cooldown = 0.5
    st = structure_at_mouse()
    if not st:
        estado.log("Apunta con el mouse a una estructura cercana.")
        return
    mat = REPAIR_MATERIAL.get(st["type"])
    if not mat or "hp" not in st:
        estado.log("Eso no se puede reparar.")
        return
    if st["hp"] >= st["max_hp"]:
        estado.log("Está en perfecto estado.")
        return
    attr = STORE_BAG_MAP[mat]
    if getattr(estado.player, attr) <= 0:
        estado.log(f"Necesitas {ITEM_NAMES[mat]} para reparar.")
        return
    setattr(estado.player, attr, getattr(estado.player, attr) - 1)
    repair_structure(st, st["max_hp"] * REPAIR_FRACTION)
    pygame.mixer.Channel(14).play(hammer_sound)
    estado.log(f"Reparas: {int(st['hp'])}/{st['max_hp']}")

def dismantle_at_mouse():
    if estado.player.equipped != "hammer":
        estado.log("Equipa el martillo para desmontar (X).")
        return
    st = structure_at_mouse()
    if st:
        destroy_structure(st, by_player=True)
    else:
        estado.log("Apunta con el mouse a una estructura cercana.")

def feed_fire(st):
    init_structure(st)
    if st["fuel"] >= FIRE_MAX_FUEL - 1:
        estado.log("La fogata ya tiene suficiente leña.")
        return
    if estado.player.inv_wood <= 0:
        estado.log("Necesitas madera para alimentar la fogata.")
        return
    estado.player.inv_wood -= 1
    if add_fuel(st, FIRE_FUEL_PER_WOOD):
        estado.log("Reavivas la fogata.")
    else:
        estado.log("Añades leña a la fogata.")

ITEM_NAMES.update({"ingot": "lingotes", "part": "piezas de motor", "diesel": "diésel"})
DROP_KEYS[pygame.K_6] = "ingot"              # con la mochila abierta: tecla 6 tira lingotes


def _bag_get(key):
    if key in STORE_BAG_MAP:
        return getattr(estado.player, STORE_BAG_MAP[key])
    return estado.player.cargo.get(key, 0)


def _bag_add(key, n):
    if key in STORE_BAG_MAP:
        setattr(estado.player, STORE_BAG_MAP[key], getattr(estado.player, STORE_BAG_MAP[key]) + n)
    else:
        estado.player.cargo[key] = estado.player.cargo.get(key, 0) + n


def pick_up_debris(dr):
    got = {}
    for key in list(dr["items"]):
        while dr["items"][key] > 0 and estado.current_capacity() < MAX_CAPACITY:
            _bag_add(key, 1)
            dr["items"][key] -= 1
            got[key] = got.get(key, 0) + 1
        if dr["items"][key] <= 0:
            del dr["items"][key]
    if got:
        estado.log("Recogiste: " + ", ".join(f"{n} {ITEM_NAMES.get(k, k)}" for k, n in got.items()))
    if dr["items"]:
        estado.log("Tu mochila está llena; queda algo en el suelo.")


def drop_item(key, amount=1):
    n = min(amount, _bag_get(key))
    if n <= 0:
        return
    _bag_add(key, -n)
    dirx, diry = colision.cardinal_from_aim()
    x, y = estado.player.x + dirx * 28, estado.player.y + diry * 28      # fuera del alcance de E, para no recogerlo al instante
    if colision.blocked(int(x // TILE), int(y // TILE), False):
        x, y = estado.player.x - dirx * 28, estado.player.y - diry * 28
        if colision.blocked(int(x // TILE), int(y // TILE), False):
            x, y = estado.player.x, estado.player.y
    for dr in estado.drops:                                        # si ya hay un montón cerca, lo suma
        if dr["kind"] == "debris" and mundo.dist(x, y, dr["x"], dr["y"]) < 12:
            dr["items"][key] = dr["items"].get(key, 0) + n
            break
    else:
        estado.drops.append({"x": x, "y": y, "kind": "debris", "items": {key: n}})
    pygame.mixer.Channel(8).play(bag_sound)
    estado.log(f"Tiraste {n} {ITEM_NAMES.get(key, key)}.")
    
def handle_build_click(pos, buttons):
    for t, rect in buttons.items():
        if rect.collidepoint(pos):
            select_build(t)
            return
            
            # Funciones para el oso
def is_buildable(t):
    return t not in LOCKED_BUILDS or LOCKED_BUILDS[t] in estado.player.recipes
