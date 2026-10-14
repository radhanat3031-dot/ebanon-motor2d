"""La niña de las bayas y la anciana: caminos y ayudantes.

Salió de ebanon.py (original), alrededor de las líneas 8171-9147.
"""

import heapq
import math
import os
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global ambiente, camara, ciclo_dia, colision, construccion
    global dibujo, estado, mundo
    from interfaz import dibujo
    from nucleo import estado, mundo
    from sistemas import ambiente, camara, ciclo_dia, colision, construccion


    
# ============================================================================
# NPC: LA NIÑA DE LAS BAYAS
# ============================================================================
GIRL_ARRIVES_DAY = 2          # ← desde qué día puede aparecer
GIRL_SPEED = 50               # ← velocidad al caminar
GIRL_CARRY = 3                # ← bayas que lleva por viaje
GIRL_RANGE = 200 * TILE        # ← hasta dónde se aleja del almacén
GIRL_REST = 5.0              # ← descanso entre viajes (segundos)
GIRL_FEAR = 30               # ← a qué distancia le asusta un zombi
GIRL_GARDEN_MAX = 6           # ← arbustos que cultiva cerca del almacén
GIRL_GROW = 43.0              # ← segundos que tarda en crecer un arbusto nuevo
NPC_DISPLAY = 24              # ← tamaño en pantalla (el Navegante mide 28)
GIRL_SPEECH = {
    "arrive": ["¿Puedo quedarme cerca del fuego?", "Mi casa ya no tiene luz. ¿Puedo quedarme aquí?"],
    "deposit": ["Estas las revisé, no están podridas.", "Las dejé en el almacén.", "Hoy hubo bayas.",
                "Mi papá decía que hay que comer aunque no den ganas."],
    "scared": ["¡Shhh! Ahí vienen...", "¡Zombis!", "No me mires, no me mires..."],
    "rain": ["Otra vez la lluvia...", "Mejor espero a que pare."],
    "night": ["Ya oscurece. Vuelvo.", "De noche no se sale."],
    "full": ["Ya no cabe nada."],
    "plant": ["Aquí van a crecer más."],
}
girl = {"npc": None, "state": "idle", "carry": 0, "t": 0.0, "target": None, "say": ("", 0.0),
        "calm": 0.0, "full_warned": False, "spot": None}


from nucleo import hojas


def load_npc_sheet(nombre):
    """Carga la hoja de un NPC según su configuración en nucleo/hojas.py (HOJAS).
    Devuelve None si no existe (entonces se dibuja una figura simple)."""
    return hojas.cargar(nombre, PIXEL_SCALE, NPC_DISPLAY)


GIRL_SPRITES = load_npc_sheet("nina")


class Npc:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.dir = "down"
        self.anim_t = 0.0
        self.stuck = 0.0
        self.detour_t = 0.0
        self.side = random.choice((1, -1))


def _npc_free(n, x, y):
    tx, ty = int(x // TILE), int(y // TILE)
    if (tx, ty) == (int(n.x // TILE), int(n.y // TILE)):
        return True
    return not colision.blocked(tx, ty, False) and not mundo.tile_water(tx, ty)


def nearest_zombie(x, y, r):
    best, bd = None, r
    for z in estado.zombies:
        if not z.dead:
            d = mundo.dist(x, y, z.x, z.y)
            if d < bd:
                best, bd = z, d
    return best


def depot_chest(n):
    best, bd = None, 1e9
    for st in estado.structures:
        if st["type"] == "chest":
            d = mundo.dist(n.x, n.y, st["x"], st["y"])
            if d < bd:
                best, bd = st, d
    return best
            
BOSS_ON_GUN_PICKUP = True    # ← True: el Hombre del reloj aparece al recoger la pistola (ya no de noche)

ELDER_ARRIVES_DAY = 3          # ← desde qué día puede aparecer la anciana
ELDER_SPEED = 42               # ← velocidad al caminar (DEBE IR MAS LENTO QUE NINA)
ELDER_CARRY = 4                # ← hierbas por viaje
ELDER_GARDEN_MAX = 4           # ← hierbas que cultiva cerca del almacén
ELDER_COLLAPSE_TEXT = "La anciana se desploma. Ya no se levanta."
ELDER_SPEECH = {
    "arrive": ["Conozco estas hierbas desde antes de todo esto. Déjame ayudar.",
               "Aún sé cuáles curan y cuáles no."],
    "deposit": ["Para las heridas. Primero hay que lavarlas.", "Guarda esto. Lo vas a necesitar.",
                "Una venda limpia vale más que mil promesas."],
    "scared": ["Ay... ahí vienen.", "Más despacio, más despacio..."],
    "rain": ["La lluvia me pesa en los huesos.", "Voy a esperar a que pare."],
    "night": ["Ya es tarde. Me recojo.", "De noche no se sale."],
    "full": ["El almacén ya no admite más."],
    "plant": ["Las hierbas buenas crecen donde alguien las cuida."],
    "cough": ["*tos, tos*", "*tos seca*", "*respira con dificultad*"],
}
ELDER_SPRITES = load_npc_sheet("anciana")

# valores por defecto de los nuevos campos del NPC
Npc.path = None
Npc.goal = None
Npc.repath_t = 0.0
Npc.stuck_events = 0
Npc.chk_x = None
Npc.chk_y = 0.0
Npc.chk_t = 0.0
Npc.last_call = 0


# ── Búsqueda de caminos ──
def npc_blocked_structs():
    return {(int(st["x"] // TILE), int(st["y"] // TILE)) for st in estado.structures
            if st["type"] in ("wall", "wallStone") or (st["type"] == "door" and not st.get("open"))}


def npc_tile_ok(x, y, bs):
    return (0 <= x < estado.WORLD_W and 0 <= y < estado.WORLD_H and not mundo.tile_solid(x, y) and not mundo.tile_water(x, y)
            and (x, y) not in estado.prop_tiles and (x, y) not in bs)


def npc_goal_tile(n, gx, gy, bs):
    """El tile de destino, o el vecino libre más cercano si el destino es sólido (como el almacén)."""
    if npc_tile_ok(gx, gy, bs):
        return (gx, gy)
    best, bd = None, 1e9
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
        x, y = gx + dx, gy + dy
        if npc_tile_ok(x, y, bs):
            d = abs(x * TILE + 8 - n.x) + abs(y * TILE + 8 - n.y)
            if d < bd:
                best, bd = (x, y), d
    return best


def npc_find_path(n, goal, bs, limit=9000):
    sx, sy = int(n.x // TILE), int(n.y // TILE)
    gx, gy = goal
    if (sx, sy) == (gx, gy):
        return []
    prev = {(sx, sy): None}
    cost = {(sx, sy): 0}
    open_ = [(abs(sx - gx) + abs(sy - gy), 0, sx, sy)]
    found = False
    while open_ and len(prev) < limit:
        f, g_, x, y = heapq.heappop(open_)
        if (x, y) == (gx, gy):
            found = True
            break
        if g_ > cost[(x, y)]:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = (x + dx, y + dy)
            ng = g_ + 1
            if cost.get(nb, 1e9) <= ng or not npc_tile_ok(nb[0], nb[1], bs):
                continue
            cost[nb] = ng
            prev[nb] = (x, y)
            heapq.heappush(open_, (ng + abs(nb[0] - gx) + abs(nb[1] - gy), ng, nb[0], nb[1]))
    if not found:
        return None
    path = []
    cur = (gx, gy)
    while cur != (sx, sy):
        path.append((cur[0] * TILE + 8, cur[1] * TILE + 8))
        cur = prev[cur]
    path.reverse()
    return path


def npc_unstick(n):
    """Último recurso: la pone en el tile libre más cercano."""
    bs = npc_blocked_structs()
    cx_, cy_ = int(n.x // TILE), int(n.y // TILE)
    for r in range(1, 5):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) == r and npc_tile_ok(cx_ + dx, cy_ + dy, bs):
                    n.x, n.y = (cx_ + dx) * TILE + 8, (cy_ + dy) * TILE + 8
                    n.path = None
                    return


def npc_move_dir(n, ux, uy, speed, dt):
    step = speed * dt
    nx, ny = n.x + ux * step, n.y + uy * step
    if _npc_free(n, nx, ny):
        n.x, n.y = nx, ny
    elif _npc_free(n, nx, n.y):
        n.x = nx
    elif _npc_free(n, n.x, ny):
        n.y = ny
    n.vx, n.vy = ux, uy
    if abs(ux) >= abs(uy):
        n.dir = "right" if ux > 0 else "left"
    else:
        n.dir = "down" if uy > 0 else "up"
    n.anim_t += dt


def npc_goto(n, wx, wy, speed, dt, stop=6):
    """Camina hasta (wx, wy) siguiendo una ruta. Devuelve 'done', 'moving' o 'fail'."""
    if mundo.dist(n.x, n.y, wx, wy) <= stop:
        n.vx = n.vy = 0.0
        n.path = None
        return "done"
    now = pygame.time.get_ticks()
    if now - n.last_call > 400 or n.chk_x is None:         # empieza un recorrido nuevo
        n.chk_x, n.chk_y, n.chk_t, n.stuck_events = n.x, n.y, 0.0, 0
        n.path = None
    n.last_call = now
    gx, gy = int(wx // TILE), int(wy // TILE)
    n.repath_t -= dt
    if n.path is None or n.goal != (gx, gy) or n.repath_t <= 0:
        bs = npc_blocked_structs()
        goal = npc_goal_tile(n, gx, gy, bs)
        n.goal = (gx, gy)
        n.repath_t = 1.5
        n.path = npc_find_path(n, goal, bs) if goal else None
        if n.path is None:
            n.vx = n.vy = 0.0
            return "fail"
    while n.path and mundo.dist(n.x, n.y, n.path[0][0], n.path[0][1]) < 5:
        n.path.pop(0)
    if not n.path:
        n.vx = n.vy = 0.0
        return "done"
    tx_, ty_ = n.path[0]
    d = mundo.dist(n.x, n.y, tx_, ty_) or 1.0
    npc_move_dir(n, (tx_ - n.x) / d, (ty_ - n.y) / d, speed, dt)
    n.chk_t += dt
    if n.chk_t >= 1.0:                                      # ¿avanzó algo en el último segundo?
        moved = mundo.dist(n.x, n.y, n.chk_x, n.chk_y)
        n.chk_x, n.chk_y, n.chk_t = n.x, n.y, 0.0
        if moved < 4:
            n.stuck_events += 1
            n.repath_t = 0.0
            if n.stuck_events >= 3:
                npc_unstick(n)
                n.stuck_events = 0
        else:
            n.stuck_events = 0
    return "moving"


# ── Lógica común de la niña y la anciana ──
def make_gatherer():
    return {"npc": None, "state": "idle", "carry": 0, "t": 0.0, "target": None, "say": ("", 0.0),
            "calm": 0.0, "full_warned": False, "spot": None, "skip": {}, "cough_t": 40.0,
            "collapsed": False}


girl.update(make_gatherer())
elder = make_gatherer()
GIRL_CFG = {"g": girl, "pickup": "berry", "store": "food", "speed": GIRL_SPEED, "carry": GIRL_CARRY,
            "garden": GIRL_GARDEN_MAX, "arrive_day": GIRL_ARRIVES_DAY, "speech": GIRL_SPEECH,
            "sprites": GIRL_SPRITES, "colors": ((150, 96, 110), (96, 62, 74), (206, 186, 160)),
            "carry_col": (150, 40, 60),
            "arrive_log": "Una niña se asoma entre los árboles. Lleva una cesta vacía y te observa.",
            "full_log": "La niña no puede dejar las bayas: el almacén está lleno."}
ELDER_CFG = {"g": elder, "pickup": "herb", "store": "bandages", "speed": ELDER_SPEED, "carry": ELDER_CARRY,
             "garden": ELDER_GARDEN_MAX, "arrive_day": ELDER_ARRIVES_DAY, "speech": ELDER_SPEECH,
             "sprites": ELDER_SPRITES, "colors": ((120, 110, 130), (80, 72, 90), (196, 178, 160)),
             "carry_col": (90, 150, 90), "cough": True, "slows": True,
             "arrive_log": "Una anciana se acerca despacio, apoyada en un bastón. Lleva hierbas en el delantal.",
             "full_log": "La anciana no puede dejar las hierbas: el almacén está lleno."}


def gath_say(cfg, kind):
    cfg["g"]["say"] = (random.choice(cfg["speech"][kind]), 3.5)


def gath_reset(cfg):
    cfg["g"].update(make_gatherer())


def gath_save(cfg):
    g = cfg["g"]
    n = g["npc"]
    if n is None:
        return None
    return {"x": n.x, "y": n.y, "carry": g["carry"], "collapsed": g["collapsed"]}


def gath_load(cfg, data):
    gath_reset(cfg)
    if data:
        g = cfg["g"]
        g["npc"] = Npc(data["x"], data["y"])
        g["carry"] = data.get("carry", 0)
        g["collapsed"] = data.get("collapsed", False)
        g["t"] = 3.0


def gath_try_arrive(cfg, dt):
    g = cfg["g"]
    g["t"] -= dt
    if g["t"] > 0:
        return
    g["t"] = 5.0
    if estado.day_count < cfg["arrive_day"] or ciclo_dia.is_night() or ambiente.rain["level"] > 0.3:
        return
    chests = [st for st in estado.structures if st["type"] == "chest"]
    if not chests:
        return
    ch = min(chests, key=lambda s: mundo.dist(s["x"], s["y"], estado.player.x, estado.player.y))
    for _ in range(80):
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(24, 34) * TILE
        x, y = ch["x"] + math.cos(a) * r, ch["y"] + math.sin(a) * r
        tx, ty = int(x // TILE), int(y // TILE)
        if not (0 <= tx < estado.WORLD_W and 0 <= ty < estado.WORLD_H) or not estado.WORLD_MASK[ty][tx]:
            continue
        if mundo.tile_solid(tx, ty) or mundo.tile_water(tx, ty) or mundo.dist(x, y, estado.player.x, estado.player.y) < 14 * TILE:
            continue
        g["npc"] = Npc(x, y)
        g["state"] = "arriving"
        g["carry"] = 0
        g["t"] = 0.0
        estado.log(cfg["arrive_log"])
        gath_say(cfg, "arrive")
        return


def gath_pick_target(cfg, n, chest):
    g = cfg["g"]
    if g["carry"] >= cfg["carry"] or chest is None:
        return None
    best, bd = None, 1e9
    for p in estado.food_pickups:
        if not p["active"] or p["type"] != cfg["pickup"] or id(p) in g["skip"]:
            continue
        if mundo.dist(p["x"], p["y"], chest["x"], chest["y"]) > GIRL_RANGE:
            continue
        if nearest_zombie(p["x"], p["y"], 90) is not None:
            continue
        d = mundo.dist(n.x, n.y, p["x"], p["y"])
        if d < bd:
            best, bd = p, d
    return best


def gath_plant_spot(cfg, chest):
    garden = sum(1 for p in estado.food_pickups if p.get("keep") and p["type"] == cfg["pickup"]
                 and mundo.dist(p["x"], p["y"], chest["x"], chest["y"]) < GIRL_RANGE)
    if garden >= cfg["garden"]:
        return None
    for _ in range(40):
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(5, 12) * TILE
        x, y = chest["x"] + math.cos(a) * r, chest["y"] + math.sin(a) * r
        tx, ty = int(x // TILE), int(y // TILE)
        if not (0 <= tx < estado.WORLD_W and 0 <= ty < estado.WORLD_H) or not estado.WORLD_MASK[ty][tx]:
            continue
        if mundo.tile_solid(tx, ty) or mundo.tile_water(tx, ty) or mundo.tile_at(tx, ty) == mundo.TILE_TYPE["cave"]:
            continue
        if (tx, ty) in estado.prop_tiles or construccion.structure_at_tile(tx, ty):
            continue
        return (tx * TILE + 8, ty * TILE + 8)
    return None


def gath_deposit(cfg, chest):
    g = cfg["g"]
    if g["carry"] <= 0 or chest is None:
        return
    k = min(g["carry"], CHEST_CAPACITY - estado.chest_capacity_used(chest))
    if k > 0:
        chest["store"][cfg["store"]] += k
        g["carry"] -= k
        g["full_warned"] = False
        gath_say(cfg, "deposit")
    if g["carry"] > 0 and not g["full_warned"]:
        g["full_warned"] = True
        gath_say(cfg, "full")
        estado.log(cfg["full_log"])


def gath_update(cfg, dt):
    if estado.in_mine:
        return
    g = cfg["g"]
    if g["say"][1] > 0:
        g["say"] = (g["say"][0], g["say"][1] - dt)
    for k in list(g["skip"]):
        g["skip"][k] -= dt
        if g["skip"][k] <= 0:
            del g["skip"][k]
    n = g["npc"]
    if n is None:
        gath_try_arrive(cfg, dt)
        return
    if g["collapsed"]:
        n.vx = n.vy = 0.0
        return
    days = max(0, estado.day_count - cfg["arrive_day"])
    spd = cfg["speed"] * (max(0.6, 1.0 - 0.05 * days) if cfg.get("slows") else 1.0)
    if cfg.get("cough"):                                  # la tos aumenta con los días
        g["cough_t"] -= dt
        if g["cough_t"] <= 0:
            g["cough_t"] = random.uniform(35, 75) / (1.0 + 0.15 * days)
            gath_say(cfg, "cough")
    chest = depot_chest(n)

    z = nearest_zombie(n.x, n.y, GIRL_FEAR)               # peligro: huye
    if z is not None:
        if g["state"] != "scared":
            g["state"] = "scared"
            gath_say(cfg, "scared")
        g["calm"] = 2.5
        ax, ay = n.x - z.x, n.y - z.y
        l = math.hypot(ax, ay) or 1
        ux, uy = ax / l, ay / l
        sx_ = sy_ = None
        best = 30 * TILE
        for st in estado.structures:
            if st["type"] == "fire" and st.get("fuel", 1) > 0:
                d = mundo.dist(n.x, n.y, st["x"], st["y"])
                if d < best:
                    best, sx_, sy_ = d, st["x"], st["y"]
        if sx_ is None and chest is not None:
            sx_, sy_ = chest["x"], chest["y"]
        if sx_ is not None:
            tx_, ty_ = sx_ - n.x, sy_ - n.y
            tl = math.hypot(tx_, ty_) or 1
            ux, uy = ux * 0.6 + tx_ / tl * 0.4, uy * 0.6 + ty_ / tl * 0.4
            l2 = math.hypot(ux, uy) or 1
            ux, uy = ux / l2, uy / l2
        npc_move_dir(n, ux, uy, spd * 1.5, dt)
        n.path = None
        return
    if g["state"] == "scared":
        n.vx = n.vy = 0.0
        g["calm"] -= dt
        if g["calm"] <= 0:
            g["state"] = "to_chest"
        return

    shelter = ciclo_dia.is_night() or ambiente.rain["level"] > 0.3           # noche o lluvia: se queda en casa
    if shelter and (g["state"] in ("to_berry", "picking", "to_plant") or (g["state"] == "idle" and g["carry"] > 0)):
        gath_say(cfg, "night" if ciclo_dia.is_night() else "rain")
        g["state"] = "to_chest"
        g["target"] = None

    st_ = g["state"]
    if st_ == "arriving":
        if chest is None:
            g["state"] = "idle"
        else:
            r = npc_goto(n, chest["x"], chest["y"], spd, dt, 22)
            if r == "done":
                g["state"] = "idle"
                g["t"] = 3.0
            elif r == "fail":                             # no pudo llegar: lo intenta más tarde
                g["npc"] = None
                g["t"] = 30.0
    elif st_ == "idle":
        n.vx = n.vy = 0.0
        g["t"] -= dt
        if not shelter and g["t"] <= 0 and chest is not None:
            if g["carry"] > 0:
                g["state"] = "to_chest"
            else:
                tgt = gath_pick_target(cfg, n, chest)
                if tgt:
                    g["target"] = tgt
                    g["state"] = "to_berry"
                else:
                    spot = gath_plant_spot(cfg, chest)
                    if spot:
                        g["spot"] = spot
                        g["state"] = "to_plant"
                    else:
                        g["t"] = GIRL_REST
    elif st_ == "to_berry":
        p = g["target"]
        if p is None or not p["active"]:
            g["state"] = "idle"
            g["t"] = 1.0
        else:
            r = npc_goto(n, p["x"], p["y"], spd, dt, 8)
            if r == "done":
                g["state"] = "picking"
                g["t"] = 1.4
            elif r == "fail":                             # sin camino: lo descarta un rato
                g["skip"][id(p)] = 40.0
                g["target"] = None
                g["state"] = "idle"
                g["t"] = 1.0
    elif st_ == "picking":
        n.vx = n.vy = 0.0
        g["t"] -= dt
        if g["t"] <= 0:
            p = g["target"]
            if p is not None and p["active"]:
                p["active"] = False
                p["timer"] = RESPAWN_FOOD
                p["keep"] = True                          # la planta rebrota en el mismo lugar
                g["carry"] += 1
            g["target"] = None
            tgt = gath_pick_target(cfg, n, chest)
            if tgt:
                g["target"] = tgt
                g["state"] = "to_berry"
            else:
                g["state"] = "to_chest"
    elif st_ == "to_plant":
        spot = g["spot"]
        if spot is None:
            g["state"] = "idle"
        else:
            r = npc_goto(n, spot[0], spot[1], spd, dt, 6)
            if r == "done":
                estado.food_pickups.append({"x": spot[0], "y": spot[1], "active": False,
                                     "timer": GIRL_GROW, "type": cfg["pickup"], "keep": True})
                gath_say(cfg, "plant")
                g["spot"] = None
                g["state"] = "idle"
                g["t"] = 3.0
            elif r == "fail":
                g["spot"] = None
                g["state"] = "idle"
                g["t"] = GIRL_REST
    elif st_ == "to_chest":
        if chest is None:
            g["state"] = "idle"
            g["t"] = GIRL_REST
        else:
            r = npc_goto(n, chest["x"], chest["y"], spd, dt, 22)
            if r == "done":
                gath_deposit(cfg, chest)
                g["state"] = "idle"
                g["t"] = GIRL_REST
            elif r == "fail":
                g["state"] = "idle"
                g["t"] = GIRL_REST


def gath_draw(cfg, surface):
    g = cfg["g"]
    n = g["npc"]
    if n is None or estado.in_mine:
        return
    u = PIXEL_SCALE
    sx, sy = camara.world_to_screen(n.x, n.y)
    body, dark, head = cfg["colors"]
    sprites = cfg["sprites"]
    moving = math.hypot(n.vx, n.vy) > 0.1 and not g["collapsed"]
    if sprites is not None:
        frames = sprites[n.dir]
        img = frames[int(n.anim_t * 8) % len(frames) if moving else 0]
        if g["collapsed"]:
            img = pygame.transform.rotate(img, 90)
        surface.blit(img, (round(sx - img.get_width() / 2), round(sy - img.get_height() / 2)))
    elif g["collapsed"]:
        dibujo.px(surface, sx - 8 * u, sy - 2 * u, 12 * u, 6 * u, body)
        dibujo.px(surface, sx + 4 * u, sy - 3 * u, 5 * u, 5 * u, head)
        dibujo.px(surface, sx - 8 * u, sy + 3 * u, 4 * u, 2 * u, dark)
    else:
        dibujo.draw_character(surface, n.x, n.y, -1 if n.dir == "left" else 1, n.vx, n.vy, n.anim_t,
                       body, dark, head, 0)
    if not g["collapsed"]:
        for i in range(g["carry"]):
            dibujo.px(surface, sx - 6 * u + i * 3 * u, sy + 4 * u, 2 * u, 2 * u, cfg["carry_col"])
    text, t = g["say"]
    if t > 0 and text:
        img = FONT_SMALL.render(text, True, (230, 226, 210))
        bw, bh = img.get_width() + 10, img.get_height() + 6
        bx, by = int(sx - bw / 2), int(sy - 22 * u - bh)
        pygame.draw.rect(surface, (20, 23, 15), (bx, by, bw, bh))
        pygame.draw.rect(surface, (90, 96, 70), (bx, by, bw, bh), 1)
        surface.blit(img, (bx + 5, by + 3))


def gath_debug(cfg):
    if estado.in_mine:
        return
    if not any(st["type"] == "chest" for st in estado.structures):
        estado.log("PRUEBA: construye primero un almacén (B).")
        return
    gath_reset(cfg)
    cfg["g"]["npc"] = Npc(estado.player.x + 8 * TILE, estado.player.y)
    cfg["g"]["state"] = "arriving"
    gath_say(cfg, "arrive")


# nombres que ya usa el resto del código (reemplazan a los anteriores de la niña)
def update_girl(dt):
    gath_update(GIRL_CFG, dt)


def draw_girl(surface):
    gath_draw(GIRL_CFG, surface)


def girl_reset():
    gath_reset(GIRL_CFG)


def girl_save_data():
    return gath_save(GIRL_CFG)


def girl_load_data(data):
    gath_load(GIRL_CFG, data)


def debug_girl():
    gath_debug(GIRL_CFG)


# la anciana
def update_elder(dt):
    gath_update(ELDER_CFG, dt)


def draw_elder(surface):
    gath_draw(ELDER_CFG, surface)


def elder_reset():
    gath_reset(ELDER_CFG)


def elder_save_data():
    return gath_save(ELDER_CFG)


def elder_load_data(data):
    gath_load(ELDER_CFG, data)


def debug_elder():
    """Atajo de prueba (Ctrl+W): la anciana aparece al lado (necesitas un almacén construido)."""
    gath_debug(ELDER_CFG)


def elder_collapse():
    """El colapso de la anciana. Aquí enlazaremos el ataque de abejas. Prueba: Ctrl+Z."""
    g = elder
    if g["npc"] is None or g["collapsed"]:
        return
    g["collapsed"] = True
    g["state"] = "idle"
    g["target"] = None
    g["say"] = ("", 0.0)
    estado.log(ELDER_COLLAPSE_TEXT)
DASH_HUNGER_COST = 2               # ← hambre que cuesta cada dash (el hambre máxima es 120)
BACA_PICK_STAMINA_FRACTION = 0.5   # ← parte de la estamina máxima que gasta cada golpe (1.0 = toda)
BACA_PICK_HUNGER_COST = 3          # ← hambre que cuesta cada golpe del zapapico
