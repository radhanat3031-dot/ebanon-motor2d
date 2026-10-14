"""Jefe: Neri, Madre Jauría, y su guarida.

Salió de ebanon.py (original), alrededor de las líneas 6256-6936.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403
from nucleo import ajustes
from nucleo import estado


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global actualizacion, camara, construccion, dibujo, makadewaa
    global mina, mundo, tonico
    from interfaz import dibujo
    from jefes import makadewaa, tonico
    from mapas import mina
    from nucleo import mundo
    from sistemas import actualizacion, camara, construccion


        
# ── GUARIDA DE NERI: eventos de entrada ──
LAIR_TRIGGER_TILES = 17        # ← a cuántos tiles del centro de la guarida se activa
LAIR_SEAL_TILES = 22           # ← radio donde se sellan las entradas (fuera de la cueva)
LAIR_TEST_OPEN_AFTER = None   # None = la guarida solo se abre cuando muere Neri
lair = {"state": "idle", "sealed": [], "purge": [], "purge_t": 0.0, "shake": 0.0, "t": 0.0}
lair_rubble = set()            # tiles con escombros del derrumbe
neri_howl_sound = ajustes._load_sound("neri_howl.ogg", 1.0)


def lair_reset():
    lair["state"] = "cleared" if neri_defeated else "idle"
    reset_neri()    
    lair["sealed"] = []
    lair["purge"] = []
    lair["purge_t"] = 0.0
    lair["shake"] = 0.0
    lair["t"] = 0.0
    lair_rubble.clear()


def seal_lair():
    """Derrumba todos los accesos a la guarida y retira a los enemigos."""
    lair["state"] = "sealed"
    lair["t"] = 0.0
    lair["shake"] = 2.0
    pygame.mixer.Channel(22).play(neri_howl_sound)
    estado.log("Un aullido retumba en la guarida...")
    estado.log("¡La cueva se derrumba! Todas las salidas quedaron selladas.")
    cx_t, cy_t = int(MINE_INFO["lair"][0] // TILE), int(MINE_INFO["lair"][1] // TILE)
    R = LAIR_SEAL_TILES
    RUIN, CAVE = mundo.TILE_TYPE["ruin"], mundo.TILE_TYPE["cave"]
    for yy in range(cy_t - R - 2, cy_t + R + 3):
        for xx in range(cx_t - R - 2, cx_t + R + 3):
            if not (0 <= xx < estado.WORLD_W and 0 <= yy < estado.WORLD_H):
                continue
            if abs(math.hypot(xx - cx_t, yy - cy_t) - R) <= 1.5 and mundo.WORLD[yy][xx] not in (RUIN, CAVE):
                lair["sealed"].append((xx, yy, mundo.WORLD[yy][xx]))
                mundo.WORLD[yy][xx] = RUIN
                lair_rubble.add((xx, yy))
    seal_set = {(x, y) for x, y, _ in lair["sealed"]}
    for lst in (estado.wood_pickups, estado.rock_pickups, estado.scrap_pickups, estado.food_pickups, estado.ammo_pickups):
        for p in lst:                              # lo que quedó bajo el derrumbe reaparece en otro lado
            if (int(p["x"] // TILE), int(p["y"] // TILE)) in seal_set:
                p["active"] = False
                p["timer"] = 5.0
    estado.structures[:] = [s for s in estado.structures
                     if (int(s["x"] // TILE), int(s["y"] // TILE)) not in seal_set]
    lair["purge"] = [z for z in estado.zombies if not z.dead] + [b for b in bats if not b.dead]
    random.shuffle(lair["purge"])
    spawn_neri()
    lair["purge_t"] = 0.0


def open_lair(msg="Los escombros ceden. El camino vuelve a estar abierto."):
    for xx, yy, orig in lair["sealed"]:
        mundo.WORLD[yy][xx] = orig
    lair["sealed"] = []
    lair_rubble.clear()
    lair["state"] = "cleared"
    estado.log(msg)


def update_lair(dt):
    if lair["shake"] > 0:
        lair["shake"] = max(0.0, lair["shake"] - dt * 1.2)
    if not estado.in_mine:
        return
    if lair["state"] == "idle":
        lx, ly = MINE_INFO["lair"]
        if mundo.dist(estado.player.x, estado.player.y, lx, ly) < LAIR_TRIGGER_TILES * TILE:
            seal_lair()
    elif lair["state"] == "sealed":
        if lair["purge"]:                          # enemigos se desvanecen de uno en uno
            lair["purge_t"] -= dt
            if lair["purge_t"] <= 0:
                lair["purge_t"] = 0.15
                lair["purge"].pop().dead = True
        lair["t"] += dt
        if LAIR_TEST_OPEN_AFTER and lair["t"] >= LAIR_TEST_OPEN_AFTER:
            open_lair()
            
# ============================================================================
# NERI, MADRE JAURÍA
# ============================================================================
NERI_NAME = "NERI"
NERI_TITLE = "Madre Jauría"
NERI = {
    "hp": 1100, "speed": 47, "size": 3.0, "cd": 4.3,              # cd = pausa entre ataques
    # mordida
    "bite_range": 40, "bite_arc": 0.9, "bite_windup": 0.45, "bite_recover": 0.4, "bite_dmg": 10,
    # dash: embestida (con franja de aviso)
    "dash_windup": 0.7, "dash_speed": 320, "dash_dist": 150, "dash_hit_r": 20, "dash_dmg": 17,
    "dash_recover": 1.0, "dash_cd": 16.0, "dash_min": 60, "dash_range": 240,
    # dash: esquiva lateral cuando le disparas seguido (aviso corto = destello)
    "dodge_windup": 0.25, "dodge_dist": 70, "dodge_speed": 300, "dodge_recover": 1.0,
    "dodge_cd": 12.0, "dodge_shots": 3, "dodge_window": 2.0,
    # llamado de jauría
    "call_windup": 0.9, "call_recover": 1.3, "call_cd": 32.0, "pups_max": 1, "pups_max_p2": 2,
    # aullido con derrumbes
    "howl_windup": 1.1, "howl_recover": 1.7, "howl_cd": 36.0, "rocks": 8, "rocks_p2": 3,
    "rock_delay": 0.9, "rock_r": 22, "rock_dmg": 20,
}
NERI_PUP = {"hp": 40, "speed": 58, "aim": 0.6, "lock": 0.15, "lunge_speed": 250, "lunge_dist": 120,
            "hit_r": 9, "dmg": 6, "cd": (5.0, 9.0), "range": 95}
NERI_RAGE_SPEED = 1.1          # más rápida enfurecida
NERI_RAGE_CD = 0.7             # sus ataques se repiten más seguido (menor = más seguido)
NERI_PHASE2 = 0.5              # a qué fracción de vida empieza la fase 2
NERI_PICK_DAMAGE = 120         # ← daño del zapapico de Baca contra Neri (contra otros enemigos: 45)
NERI_PICK_STUN = 0.3           # ← segundos que la deja expuesta (y cancela lo que preparaba)

neri = None
neri_defeated = False
neri_pups = []
neri_rocks = []
neri_aux = {"ammo": 0, "shots": [], "clock": 0.0}
estado.player.has_tonic = False
estado.player.has_foundry_key = False


class Neri:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.hp = self.max_hp = NERI["hp"]
        self.size = NERI["size"]
        self.state = "chase"        # chase / windup / dash / dodge / recover
        self.attack = None
        self.state_t = 0.0
        self.state_total = 1.0
        self.aim_dx, self.aim_dy = 1.0, 0.0
        self.cd = 6.0
        self.dash_cd = 10.0
        self.dodge_cd = 0.0
        self.call_cd = 16.0
        self.howl_cd = 24.0        
        self.hit_flash = 0.0
        self.strike_t = 0.0
        self.enraged = False
        self.phase2 = False
        self.roar_t = 2.5           # al aparecer queda rugiendo, intocable
        self.combo = None
        self.dash_left = 0.0
        self.hit_done = False
        self.sprite_dir = "down"
        self.anim_t = 0.0
        self.vx = self.vy = 0.0
        self.block_t = 0.0
        self.detour_side = random.choice((1, -1))


class NeriPup:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.hp = self.max_hp = NERI_PUP["hp"]
        self.state = "chase"        # chase / aim / lunge
        self.t = 0.0
        self.dx, self.dy = 1.0, 0.0
        self.left = 0.0
        self.hit = False
        self.cd = random.uniform(0.8, 1.8)
        self.hit_flash = 0.0
        self.dead = False
        self.wild =False
        self.aggro = True
        self.pack = 0
        self.wander_t = 0.0
        self.wander_dir = (0.0, 0.0)


def spawn_neri():
    global neri
    lx, ly = MINE_INFO["lair"]
    neri = Neri(lx, ly)
    neri_pups.clear()
    neri_rocks.clear()
    neri_aux["ammo"] = estado.player.ammo
    neri_aux["shots"] = []
    neri_aux["clock"] = 0.0
    estado.log(f"¡{NERI_NAME}! {NERI_TITLE}.")


def reset_neri():
    global neri
    neri = None
    neri_pups.clear()
    neri_rocks.clear()


def neri_die():
    global neri, neri_defeated
    n = neri
    neri_defeated = True
    estado.drops.append({"x": n.x - 12, "y": n.y, "kind": "baca_tonic"})
    estado.drops.append({"x": n.x + 12, "y": n.y, "kind": "foundry_key"})
    neri = None
    neri_pups.clear()
    neri_rocks.clear()
    open_lair("¡Neri cayó! Los escombros ceden y el camino vuelve a estar abierto.")
    estado.log("Soltó el Tónico de Baca y la llave de la fundidura.")


def hit_neri(dmg, stun=0.0):
    n = neri
    if n is None or n.roar_t > 0 or n.state in ("dash", "dodge"):
        return                                    # durante el dash es intocable
    n.hp -= dmg
    n.hit_flash = 0.12
    if n.hp <= 0:
        neri_die()
        return
    if not n.phase2 and n.hp <= n.max_hp * NERI_PHASE2:
        n.phase2 = True
        n.enraged = True
        n.howl_cd = 4.0
        estado.log("¡Neri entra en furia!")
    if stun > 0:                                  # el zapapico la interrumpe y la deja expuesta
        neri_recover(n, max(stun, n.state_t if n.state == "recover" else 0.0))
        estado.log("¡El zapapico de Baca la interrumpe!")

def hit_pup(p, dmg):
    p.hp -= dmg
    p.hit_flash = 0.12
    if p.wild:
        for q in neri_pups:                          # si golpeas a una, la manada te ataca
            if q.wild and q.pack == p.pack:
                q.aggro = True
    if p.hp <= 0 and not p.dead:
        p.dead = True
        if p.wild:
            if random.random() < tonico.WILD_PUP_MEAT_CHANCE:
                estado.drops.append({"x": p.x, "y": p.y, "kind": "debris", "items": {"food": 1}})
        elif neri and not neri.enraged:
            neri.enraged = True
            estado.log("¡Neri se enfurece al ver caer a su cría!")

def bullet_hits_neri(bl):
    if neri and mundo.dist(bl["x"], bl["y"], neri.x, neri.y) < 8 * neri.size:
        hit_neri(bl["dmg"])                       # si está en dash, la bala se pierde
        return True
    for p in neri_pups:
        if not p.dead and mundo.dist(bl["x"], bl["y"], p.x, p.y) < 8:
            hit_pup(p, bl["dmg"])
            return True
    return False


def melee_hits_neri(ax, ay, rng, dmg):
    if neri and mundo.dist(ax, ay, neri.x, neri.y) < rng + 6 * neri.size:
        hit_neri(dmg)
    for p in neri_pups:
        if not p.dead and mundo.dist(ax, ay, p.x, p.y) < rng:
            hit_pup(p, dmg)


def neri_in_cone(n):
    dx, dy = estado.player.x - n.x, estado.player.y - n.y
    d = math.hypot(dx, dy)
    if d > NERI["bite_range"] + 4:
        return False
    if d < 1:
        return True
    diff = abs((math.atan2(dy, dx) - math.atan2(n.aim_dy, n.aim_dx) + math.pi) % (2 * math.pi) - math.pi)
    return diff <= NERI["bite_arc"]


def neri_face(n, dx, dy):
    if abs(dx) >= abs(dy):
        n.sprite_dir = "right" if dx > 0 else "left"
    else:
        n.sprite_dir = "down" if dy > 0 else "up"


def neri_begin(n, name, dx, dy):
    cfg = NERI
    mult = NERI_RAGE_CD if n.enraged else 1.0
    n.attack = name
    n.state = "windup"
    n.state_total = n.state_t = cfg[name + "_windup"]
    n.aim_dx, n.aim_dy = dx, dy
    if name == "dash":
        n.dash_cd = cfg["dash_cd"] * mult
    elif name == "dodge":
        n.dodge_cd = cfg["dodge_cd"] * mult
        side = random.choice((1, -1))             # esquiva de lado, respecto a tu línea de tiro
        for _ in range(2):
            lx_, ly_ = -dy * side, dx * side
            if actualizacion._zombie_can_move(n, n.x + lx_ * 40, n.y + ly_ * 40):
                break
            side = -side
        n.aim_dx, n.aim_dy = lx_, ly_
    elif name == "call":
        n.call_cd = cfg["call_cd"] * mult
    elif name == "howl":
        n.howl_cd = cfg["howl_cd"] * mult
    neri_face(n, n.aim_dx, n.aim_dy)
    pygame.mixer.Channel(17).play(bear_growl_sound)


def neri_recover(n, secs):
    n.state = "recover"
    n.attack = None
    n.state_total = n.state_t = secs


def neri_howl_rocks(n):
    cfg = NERI
    count = cfg["rocks_p2"] if n.phase2 else cfg["rocks"]
    lx, ly = MINE_INFO["lair"]
    for i in range(count):
        a = random.uniform(0, 2 * math.pi)
        if i < count // 2:                        # la mitad cae cerca de ti
            r = random.uniform(0, 70)
            x, y = estado.player.x + math.cos(a) * r, estado.player.y + math.sin(a) * r
        else:                                     # el resto por toda la guarida
            r = random.uniform(0, 16 * TILE)
            x, y = lx + math.cos(a) * r, ly + math.sin(a) * r
        if mundo.tile_solid(int(x // TILE), int(y // TILE)):
            continue
        delay = cfg["rock_delay"] + random.uniform(0, 0.6)
        neri_rocks.append({"x": x, "y": y, "t": delay, "total": delay})


def neri_resolve(n):
    cfg = NERI
    a = n.attack
    if a == "bite":
        pygame.mixer.Channel(18).play(bear_swipe_sound)
        n.strike_t = 0.15
        if not estado.god_mode and neri_in_cone(n):
            estado.player.hp = max(0, estado.player.hp - cfg["bite_dmg"])
            estado.log("¡Neri te mordió!")
        neri_recover(n, cfg["bite_recover"])
    elif a in ("dash", "dodge"):
        n.state = a
        n.dash_left = cfg["dash_dist"] if a == "dash" else cfg["dodge_dist"]
        n.hit_done = False
        pygame.mixer.Channel(19).play(bear_charge_sound)
    elif a == "call":
        alive = sum(1 for p in neri_pups if not p.dead)
        cap = cfg["pups_max_p2"] if n.phase2 else cfg["pups_max"]
        for _ in range(cap - alive):
            ang = random.uniform(0, 2 * math.pi)
            neri_pups.append(NeriPup(n.x + math.cos(ang) * 26, n.y + math.sin(ang) * 26))
        pygame.mixer.Channel(16).play(bear_roar_sound)
        estado.log("¡Neri llama a su jauría!")
        neri_recover(n, cfg["call_recover"])
    elif a == "howl":
        pygame.mixer.Channel(22).play(neri_howl_sound)
        lair["shake"] = 1.5
        neri_howl_rocks(n)
        estado.log("¡Neri aúlla y el techo se viene abajo!")
        neri_recover(n, cfg["howl_recover"])
        if n.phase2:
            n.combo = "call"                      # fase 2: aullido y enseguida llamado


def neri_move_dash(n, dt):
    cfg = NERI
    dashing = n.state == "dash"
    step = min((cfg["dash_speed"] if dashing else cfg["dodge_speed"]) * dt, n.dash_left)
    nx, ny = n.x + n.aim_dx * step, n.y + n.aim_dy * step
    n.vx, n.vy = n.aim_dx, n.aim_dy
    n.anim_t += dt * 2
    if dashing and not n.hit_done and mundo.dist(nx, ny, estado.player.x, estado.player.y) < cfg["dash_hit_r"]:
        n.hit_done = True
        if not estado.god_mode:
            estado.player.hp = max(0, estado.player.hp - cfg["dash_dmg"])
            estado.log("¡Neri te embistió!")
    secs = cfg["dash_recover"] if dashing else cfg["dodge_recover"]
    if actualizacion._zombie_can_move(n, nx, ny):
        n.x, n.y = nx, ny
        n.dash_left -= step
        if n.dash_left <= 0:
            neri_recover(n, secs)                 # tras el dash queda expuesta
    else:
        neri_recover(n, secs + 0.6)               # se estrelló: más expuesta todavía
        estado.log("¡Neri se estrelló!")


def update_neri_rocks(dt):
    for r in neri_rocks:
        if "boom" in r:
            r["boom"] -= dt
            continue
        r["t"] -= dt
        if r["t"] <= 0:
            r["boom"] = 0.35
            lair["shake"] = max(lair["shake"], 0.7)
            pygame.mixer.Channel(20).play(bear_slam_sound)
            if not estado.god_mode and mundo.dist(r["x"], r["y"], estado.player.x, estado.player.y) < NERI["rock_r"]:
                estado.player.hp = max(0, estado.player.hp - NERI["rock_dmg"])
                estado.log("¡Una roca te golpeó!")
    neri_rocks[:] = [r for r in neri_rocks if r.get("boom", 1) > 0]


def update_neri_pups(dt):
    tonico.wild_spawn_tick(dt)
    cfg = NERI_PUP
    for p in neri_pups:
        if p.dead:
            continue
        if p.hit_flash > 0:
            p.hit_flash -= dt
        dx, dy = estado.player.x - p.x, estado.player.y - p.y
        d = math.hypot(dx, dy) or 1
        ux, uy = dx / d, dy / d
        if p.wild:
            if d > 60 * TILE:                        # muy lejos: desaparece
                p.dead = True
                continue
            fire = tonico.lit_fire_near(p.x, p.y, tonico.WILD_PUP_FIRE_FEAR)
            if fire is not None:                     # le temen al fuego: huyen
                fx, fy = p.x - fire["x"], p.y - fire["y"]
                fl = math.hypot(fx, fy) or 1
                nx, ny = p.x + fx / fl * cfg["speed"] * dt, p.y + fy / fl * cfg["speed"] * dt
                if actualizacion._zombie_can_move(p, nx, ny):
                    p.x, p.y = nx, ny
                p.state = "chase"
                p.dx, p.dy = fx / fl, fy / fl
                continue
            if not p.aggro:
                if d < tonico.WILD_PUP_AGGRO:               # te notan: se activa toda la manada
                    for q in neri_pups:
                        if q.wild and q.pack == p.pack:
                            q.aggro = True
                else:                                # merodean
                    p.wander_t -= dt
                    if p.wander_t <= 0:
                        p.wander_t = random.uniform(2, 4)
                        a = random.uniform(0, 2 * math.pi)
                        p.wander_dir = (math.cos(a), math.sin(a))
                    wx, wy = p.wander_dir
                    nx, ny = p.x + wx * cfg["speed"] * 0.4 * dt, p.y + wy * cfg["speed"] * 0.4 * dt
                    if actualizacion._zombie_can_move(p, nx, ny) and not mundo.tile_water(int(nx // TILE), int(ny // TILE)):
                        p.x, p.y = nx, ny
                    p.dx, p.dy = wx, wy
                    continue
        if p.state == "chase":
            p.cd -= dt
            if estado.in_mine and not mina.mine_line_clear(p.x, p.y, estado.player.x, estado.player.y):
                fd = mina.mine_flow_dir(p)                # en la mina siguen los caminos
                ux, uy = fd if fd else (0.0, 0.0)
            if d > 18:
                nx, ny = p.x + ux * cfg["speed"] * dt, p.y + uy * cfg["speed"] * dt
                if actualizacion._zombie_can_move(p, nx, ny):
                    p.x, p.y = nx, ny
                elif actualizacion._zombie_can_move(p, nx, p.y):
                    p.x = nx
                elif actualizacion._zombie_can_move(p, p.x, ny):
                    p.y = ny
            p.dx, p.dy = ux, uy
            if p.cd <= 0 and d <= cfg["range"]:
                p.state = "aim"
                p.t = cfg["aim"]
        elif p.state == "aim":
            p.t -= dt
            if p.t > cfg["lock"]:
                p.dx, p.dy = ux, uy
            if p.t <= 0:
                p.state = "lunge"
                p.left = cfg["lunge_dist"]
                p.hit = False
        else:
            step = min(cfg["lunge_speed"] * dt, p.left)
            nx, ny = p.x + p.dx * step, p.y + p.dy * step
            if not estado.god_mode and not p.hit and mundo.dist(nx, ny, estado.player.x, estado.player.y) < cfg["hit_r"]:
                p.hit = True
                estado.player.hp = max(0, estado.player.hp - cfg["dmg"])
                estado.log("¡Una cría de Neri te mordió!")
                p.state = "chase"
                p.cd = random.uniform(*cfg["cd"])
            elif actualizacion._zombie_can_move(p, nx, ny):
                p.x, p.y = nx, ny
                p.left -= step
                if p.left <= 0:
                    p.state = "chase"
                    p.cd = random.uniform(*cfg["cd"])
            else:
                p.state = "chase"
                p.cd = random.uniform(*cfg["cd"])
    neri_pups[:] = [p for p in neri_pups if not p.dead]

def update_neri(dt):
    update_neri_rocks(dt)
    update_neri_pups(dt)
    n = neri
    if n is None:
        return
    cfg = NERI
    aux = neri_aux
    aux["clock"] += dt
    if estado.player.ammo < aux["ammo"]:                 # se gastó munición = disparaste
        aux["shots"].append(aux["clock"])
    aux["ammo"] = estado.player.ammo
    aux["shots"] = [t for t in aux["shots"] if aux["clock"] - t <= cfg["dodge_window"]]
    for attr in ("hit_flash", "strike_t", "cd", "dash_cd", "dodge_cd", "call_cd", "howl_cd"):
        if getattr(n, attr) > 0:
            setattr(n, attr, getattr(n, attr) - dt)
    if n.roar_t > 0:
        n.roar_t -= dt
        return
    d = mundo.dist(estado.player.x, estado.player.y, n.x, n.y)
    dx, dy = estado.player.x - n.x, estado.player.y - n.y
    l = math.hypot(dx, dy) or 1
    dx, dy = dx / l, dy / l

    if n.state == "chase":
        n.aim_dx, n.aim_dy = dx, dy
        if d > cfg["bite_range"] * 0.7:
            spd = cfg["speed"] * (NERI_RAGE_SPEED if n.enraged else 1.0)
            if mundo.tile_water(int(n.x // TILE), int(n.y // TILE)):
                spd *= 0.5
            construccion.move_or_breach(n, n.x + dx * spd * dt, n.y + dy * spd * dt, dx, dy, spd, dt, 70)
            n.vx, n.vy = dx, dy
            n.anim_t += dt
        else:
            n.vx = n.vy = 0.0
        neri_face(n, dx, dy)
        if n.combo:
            name, n.combo = n.combo, None
            neri_begin(n, name, dx, dy)
        elif len(aux["shots"]) >= cfg["dodge_shots"] and n.dodge_cd <= 0 and d > cfg["bite_range"]:
            aux["shots"] = []
            neri_begin(n, "dodge", dx, dy)
        elif n.cd <= 0:
            if d <= cfg["bite_range"]:
                neri_begin(n, "bite", dx, dy)
            else:
                options = []
                if n.dash_cd <= 0 and cfg["dash_min"] <= d <= cfg["dash_range"]:
                    options.append("dash")
                cap = cfg["pups_max_p2"] if n.phase2 else cfg["pups_max"]
                if n.call_cd <= 0 and sum(1 for p in neri_pups if not p.dead) < cap:
                    options.append("call")
                if n.howl_cd <= 0:
                    options.append("howl")
                if options:
                    neri_begin(n, random.choice(options), dx, dy)
    elif n.state == "windup":
        n.vx = n.vy = 0.0
        if n.attack == "dash" and n.state_t > 0.25:
            n.aim_dx, n.aim_dy = dx, dy           # la franja te sigue hasta el último momento
            neri_face(n, dx, dy)
        n.state_t -= dt
        if n.state_t <= 0:
            neri_resolve(n)
    elif n.state in ("dash", "dodge"):
        neri_move_dash(n, dt)
    else:                                         # recover: vulnerable
        n.vx = n.vy = 0.0
        n.state_t -= dt
        if n.state_t <= 0:
            n.state = "chase"
            n.attack = None
            n.cd = cfg["cd"] * (NERI_RAGE_CD if n.enraged else 1.0)


def draw_neri_body(surface, n):
    sx, sy = camara.world_to_screen(n.x, n.y)
    k = PIXEL_SCALE * n.size
    blink = (pygame.time.get_ticks() // 80) % 2 == 0
    if n.hit_flash > 0:
        col = (255, 255, 255)
    elif n.state == "windup" and blink:
        col = (235, 240, 255) if n.attack == "dodge" else (200, 60, 40)
    elif n.state in ("dash", "dodge"):
        col = (140, 160, 185)
    elif n.enraged:
        col = (96, 48, 44)
    else:
        col = (66, 60, 64)
    head = (255, 255, 255) if n.hit_flash > 0 else tuple(min(255, c + 25) for c in col)
    horiz = n.sprite_dir in ("left", "right")
    bw, bh = (16, 12) if horiz else (12, 16)
    dibujo.px(surface, sx - bw * k / 2, sy - bh * k / 2, bw * k, bh * k, col)
    hx, hy = {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1)}[n.sprite_dir]
    cx, cy = sx + hx * 9 * k, sy + hy * 9 * k
    dibujo.px(surface, cx - 3 * k, cy - 3 * k, 6 * k, 6 * k, head)
    dibujo.px(surface, cx - 3 * k, cy - 4 * k, 2 * k, 2 * k, col)
    dibujo.px(surface, cx + 1 * k, cy - 4 * k, 2 * k, 2 * k, col)
    dibujo.px(surface, cx - 2 * k, cy - 1 * k, 1 * k, 1 * k, (230, 200, 80))
    dibujo.px(surface, cx + 1 * k, cy - 1 * k, 1 * k, 1 * k, (230, 200, 80))
    dibujo.px(surface, sx - hx * 10 * k - 1.5 * k, sy - hy * 10 * k - 1.5 * k, 3 * k, 3 * k, col)   # cola


def draw_neri_all(surface):
    n = neri
    cfg = NERI
    bite_t = bool(n) and n.attack == "bite" and (n.state == "windup" or n.strike_t > 0)
    dash_t = bool(n) and n.state == "windup" and n.attack == "dash"
    howl_t = bool(n) and n.state == "windup" and n.attack == "howl"
    pup_t = any(p.state == "aim" and not p.dead for p in neri_pups)
    if bite_t or dash_t or howl_t or pup_t or neri_rocks:
        layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        if bite_t:
            sx, sy = camara.world_to_screen(n.x, n.y)
            R = cfg["bite_range"] * PIXEL_SCALE
            ang = math.atan2(n.aim_dy, n.aim_dx)
            if n.state == "windup":
                prog = 1 - n.state_t / n.state_total
                pygame.draw.polygon(layer, (220, 40, 30, 45), makadewaa.cone_points(sx, sy, ang, cfg["bite_arc"], R))
                pygame.draw.polygon(layer, (235, 70, 40, 130), makadewaa.cone_points(sx, sy, ang, cfg["bite_arc"], R * prog))
                pygame.draw.polygon(layer, (255, 110, 70, 230), makadewaa.cone_points(sx, sy, ang, cfg["bite_arc"], R), 2)
            else:
                a = int(220 * max(0.0, n.strike_t) / 0.15)
                pygame.draw.polygon(layer, (255, 230, 200, a), makadewaa.cone_points(sx, sy, ang, cfg["bite_arc"], R))
        if dash_t:
            sx, sy = camara.world_to_screen(n.x, n.y)
            ux, uy = n.aim_dx, n.aim_dy
            ox, oy = -uy, ux
            w = cfg["dash_hit_r"] * PIXEL_SCALE
            L = cfg["dash_dist"] * PIXEL_SCALE
            lane = [(sx + ox * w, sy + oy * w), (sx + ux * L + ox * w, sy + uy * L + oy * w),
                    (sx + ux * L - ox * w, sy + uy * L - oy * w), (sx - ox * w, sy - oy * w)]
            if n.state_t <= 0.25:
                pygame.draw.polygon(layer, (255, 60, 40, 150), lane)
                pygame.draw.polygon(layer, (255, 240, 220, 255), lane, 3)
            else:
                pygame.draw.polygon(layer, (220, 40, 30, 70), lane)
                pygame.draw.polygon(layer, (255, 110, 70, 200), lane, 2)
        if howl_t:
            sx, sy = camara.world_to_screen(n.x, n.y)
            prog = 1 - n.state_t / n.state_total
            for i in range(3):
                p_ = (prog * 1.6 + i / 3) % 1.0
                pygame.draw.circle(layer, (200, 210, 235, int(200 * (1 - p_))), (int(sx), int(sy)),
                                   max(2, int(p_ * 70 * PIXEL_SCALE)), 3)
        for r in neri_rocks:
            sx, sy = camara.world_to_screen(r["x"], r["y"])
            R = int(cfg["rock_r"] * PIXEL_SCALE)
            if "boom" in r:
                f = max(0.0, r["boom"] / 0.35)
                pygame.draw.circle(layer, (200, 190, 170, int(180 * f)), (int(sx), int(sy)), R, max(2, int(6 * f)))
            else:
                prog = 1 - r["t"] / r["total"]
                pygame.draw.circle(layer, (220, 40, 30, 40), (int(sx), int(sy)), R)
                pygame.draw.circle(layer, (235, 70, 40, 110), (int(sx), int(sy)), max(1, int(R * prog)))
                pygame.draw.circle(layer, (255, 110, 70, 230), (int(sx), int(sy)), R, 2)
        for p in neri_pups:
            if p.state == "aim" and not p.dead:
                gx, gy = camara.world_to_screen(p.x, p.y)
                L = NERI_PUP["lunge_dist"] * PIXEL_SCALE
                col = (255, 60, 40, 190) if p.t <= NERI_PUP["lock"] else (255, 110, 70, 110)
                pygame.draw.line(layer, col, (gx, gy), (gx + p.dx * L, gy + p.dy * L),
                                 max(2, int(NERI_PUP["hit_r"] * 2 * PIXEL_SCALE)))
        surface.blit(layer, (0, 0))
    if n:
        size = 16 * n.size
        if not dibujo.draw_sprite(surface, "neri", n.x, n.y, "center", n.sprite_dir == "left", (size, size)):
            draw_neri_body(surface, n)
        if n.state == "windup":
            sx, sy = camara.world_to_screen(n.x, n.y)
            ex = FONT_MED.render("!", True, (255, 80, 60))
            surface.blit(ex, (sx - ex.get_width() // 2, sy - size * PIXEL_SCALE / 2 - ex.get_height() - 4))
    for p in neri_pups:
        if p.dead:
            continue
        if not dibujo.draw_sprite(surface, "neri_pup", p.x, p.y, "center", p.dx < 0):
            sx, sy = camara.world_to_screen(p.x, p.y)
            u = PIXEL_SCALE
            col = (255, 255, 255) if p.hit_flash > 0 else ((200, 60, 40) if p.state == "aim" else (90, 84, 92))
            dibujo.px(surface, sx - 5 * u, sy - 3 * u, 10 * u, 6 * u, col)
            hx = 3 if p.dx >= 0 else -7
            dibujo.px(surface, sx + hx * u, sy - 4 * u, 4 * u, 4 * u, tuple(min(255, c + 30) for c in col))
        if p.hp < p.max_hp:
            sx, sy = camara.world_to_screen(p.x, p.y)
            u = PIXEL_SCALE
            dibujo.px(surface, sx - 6 * u, sy - 10 * u, 12 * u, 2 * u, (0, 0, 0))
            dibujo.px(surface, sx - 6 * u, sy - 10 * u, 12 * u * max(0.0, p.hp / p.max_hp), 2 * u, (184, 67, 59))


def render_neri_bar(surface):
    n = neri
    if not n:
        return
    name = FONT_MED.render(f"{NERI_NAME} — {NERI_TITLE}", True, (150, 170, 190))
    surface.blit(name, (SCREEN_W // 2 - name.get_width() // 2, 14))
    bw, bh = int(SCREEN_W * 0.4), 6 * PIXEL_SCALE
    bx, by = SCREEN_W // 2 - bw // 2, 14 + name.get_height() + 4
    pygame.draw.rect(surface, (0, 0, 0), (bx - 2, by - 2, bw + 4, bh + 4))
    pygame.draw.rect(surface, (110, 130, 150), (bx, by, int(bw * max(0, n.hp / n.max_hp)), bh))
    pygame.draw.line(surface, (230, 230, 230), (bx + int(bw * NERI_PHASE2), by - 3),
                     (bx + int(bw * NERI_PHASE2), by + bh + 3), 2)       # marca de la fase 2
