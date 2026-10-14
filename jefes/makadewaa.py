"""Jefe: Makadewaa, el oso (y los osos débiles).

Salió de ebanon.py (original), alrededor de las líneas 3069-3625.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global actualizacion, baca_pico, camara, ciclo_dia, colision
    global construccion, dibujo, entidades, estado, mundo
    global refineria
    from interfaz import dibujo
    from jefes import baca_pico
    from mapas import refineria
    from nucleo import entidades, estado, mundo
    from sistemas import actualizacion, camara, ciclo_dia, colision, construccion


def spawn_bear(kind, dist_tiles=(25, 35)):
    for _ in range(200):
        ang = random.random() * math.pi * 2
        r = random.uniform(*dist_tiles) * TILE
        tx = int((estado.player.x + math.cos(ang) * r) // TILE)
        ty = int((estado.player.y + math.sin(ang) * r) // TILE)
        if not (0 <= tx < estado.WORLD_W and 0 <= ty < estado.WORLD_H):
            continue
        if mundo.tile_water(tx, ty) or mundo.tile_solid(tx, ty):
            continue
        if colision.near_fire(tx * TILE + 8, ty * TILE + 8):
            continue
        b = entidades.Bear(kind, tx * TILE + 8, ty * TILE + 8)
        estado.bears.append(b)
        if kind == "boss":
            pygame.mixer.Channel(16).play(bear_roar_sound)
            estado.log(f"¡{BEAR_NAME}! {BEAR_TITLE}.")
        return b
    return None

def hit_bear(b, dmg, stagger=0):
    
    b.hp -= dmg
    b.hit_flash = 0.12
    b.aggro = True
    if stagger > 0 and b.hp > 0:
        add_stagger(b, stagger)
    if b.hp <= 0 and not b.dead:
        b.dead = True
        if b.kind == "boss":
            estado.weak_bears_unlocked = True
            estado.log("A lo lejos se oyen osos más pequeños...")
            estado.drops.append({"x": b.x, "y": b.y, "kind": "bear_trap"})
            estado.drops.append({"x": b.x + 14, "y": b.y + 4, "kind": "debris",
                          "items": {"scrap": random.randint(3, 5)}})
            if random.random() < 0.10:
                estado.drops.append({"x": b.x - 14, "y": b.y + 4, "kind": "ammo"})
            estado.log("¡Makadewaa Makwa cayó! Dejó algo para ti.")
        elif b.kind == "weak" and random.random() < 0.35:
            estado.drops.append({"x": b.x, "y": b.y, "kind": "debris",
                          "items": {"scrap": random.randint(1, 2)}})
            
def cone_points(cx, cy, ang, half, radius, steps=10):
    pts = [(cx, cy)]
    for i in range(steps + 1):
        a = ang - half + (2 * half) * i / steps
        pts.append((cx + math.cos(a) * radius, cy + math.sin(a) * radius))
    return pts

def player_in_cone(b, cfg):
    dx, dy = estado.player.x - b.x, estado.player.y - b.y
    d = math.hypot(dx, dy)
    if d > cfg["swipe_range"] + 4:
        return False
    if d < 1:
        return True
    diff = abs((math.atan2(dy, dx) - math.atan2(b.aim_dy, b.aim_dx) + math.pi) % (2 * math.pi) - math.pi)
    return diff <= cfg["swipe_arc"]

def begin_attack(b, name, dx, dy):
    cfg = BEAR_TYPES[b.kind]
    b.attack = name
    b.state = "windup"
    b.state_total = b.state_t = cfg[name + "_windup"]
    b.aim_dx, b.aim_dy = dx, dy                      # dirección fija: se puede esquivar
    if name == "charge":
        b.charge_cd = cfg["charge_cd"]
        b.charge_acc = 0.0
    if name == "slam":
        b.slam_cd = cfg["slam_cd"]
    if abs(dx) >= abs(dy):
        b.sprite_dir = "right" if dx > 0 else "left"
    else:
        b.sprite_dir = "down" if dy > 0 else "up"
    pygame.mixer.Channel(17).play(bear_growl_sound)

def advance_state(b):
    cfg = BEAR_TYPES[b.kind]
    if b.state == "windup":
        if b.attack == "charge":
            b.state = "charge"
            b.charge_left = cfg["charge_dist"]
            pygame.mixer.Channel(19).play(bear_charge_sound)
            return
        resolve_attack(b)
        b.state = "recover"
        b.state_total = b.state_t = cfg[b.attack + "_recover"]
    elif b.state == "recover":
        b.state = "chase"
        b.cd = cfg["swipe_cd"]
        b.attack = None
    else:                                            # fin del aturdimiento
        b.state = "chase"
        b.cd = 0.8
        b.attack = None

def start_stagger(b, msg):
    cfg = BEAR_TYPES[b.kind]
    if b.attack == "roar":
        b.roar_stage = max(0, b.roar_stage - 1)      # un rugido interrumpido se reintenta
    b.state = "stagger"
    b.attack = None
    b.state_total = b.state_t = cfg["stagger_time"]
    b.stagger = 0.0
    b.charge_acc = 0.0
    b.stagger_immune = cfg["stagger_immune"]
    b.vx = b.vy = 0.0
    estado.log(msg)

def add_stagger(b, amount):
    cfg = BEAR_TYPES[b.kind]
    if b.dead or b.state == "stagger" or b.stagger_immune > 0:
        return
    if b.attack == "charge" and b.state in ("windup", "charge"):
        b.charge_acc += amount
        if b.charge_acc >= cfg.get("charge_interrupt", 9999):
            start_stagger(b, "¡Interrumpiste la carga!")
            return
    b.stagger += amount
    if b.stagger >= cfg["stagger_max"]:
        start_stagger(b, "¡El oso quedó aturdido!")

def end_charge(b, recover):
    b.state = "recover"
    b.state_total = b.state_t = recover

BEAR_BREAK_WIDTH = 1.0     # ← ancho de destrucción (1.0 = el ancho de la franja roja)
BEAR_RUIN_HITS = 2         # ← impactos que aguanta una ruina antes de caer
BEAR_BREAKS = ("wall", "wallStone", "door", "fire", "chest", "trapSpikes", "trapBear")
ruin_hits = {}             # ruinas agrietadas: {(tx, ty): impactos}


def bear_charge_sweep(b, nx, ny, hw):
    """Destruye lo que toca la franja de ddddala carga en (nx, ny). Devuelve True si chocó con una ruina."""
    felled = False
    for lst, timer in ((estado.wood_pickups, RESPAWN_WOOD), (estado.rock_pickups, RESPAWN_ROCK)):
        for p in lst:
            if p["active"] and mundo.dist(nx, ny, p["x"], p["y"]) < hw + 7:
                p["active"] = False          # cae sin dejar recursos
                p["timer"] = timer
                p["hits"] = 0
                felled = True
    if felled and not pygame.mixer.Channel(5).get_busy():
        pygame.mixer.Channel(5).play(down_three)
    for st in list(estado.structures):
        if st["type"] in BEAR_BREAKS and mundo.dist(nx, ny, st["x"], st["y"]) < hw + 7:
            construccion.destroy_structure(st)
    if estado.in_mine:
        return False
    RUIN = mundo.TILE_TYPE["ruin"]
    hit = []
    for ty in range(int((ny - hw - 8) // TILE), int((ny + hw + 8) // TILE) + 1):
        for tx in range(int((nx - hw - 8) // TILE), int((nx + hw + 8) // TILE) + 1):
            if mundo.tile_at(tx, ty) != RUIN:
                continue
            tcx, tcy = tx * TILE + 8, ty * TILE + 8
            if (tcx - nx) * b.aim_dx + (tcy - ny) * b.aim_dy <= 0:
                continue                     # las que quedan atrás o al costado no cuentan
            if math.hypot(max(abs(nx - tcx) - 8, 0), max(abs(ny - tcy) - 8, 0)) < hw:
                hit.append((tx, ty))
    for tx, ty in hit:
        if (tx, ty) in refineria.REFINERY_BARRIER:
            continue                       # el anillo lo frena y lo aturde, pero no se rompe
        n = ruin_hits.get((tx, ty), 0) + 1        
        if n >= BEAR_RUIN_HITS:
            ruin_hits.pop((tx, ty), None)
            mundo.WORLD[ty][tx] = mundo.TILE_TYPE["ground"]
            baca_pico.broken_ruins.append([tx, ty])    # queda destruida también al guardar
        else:
            ruin_hits[(tx, ty)] = n
    return bool(hit)


def draw_ruin_damage(surface, tx, ty, sx, sy):
    if estado.in_mine or (tx, ty) not in ruin_hits:
        return
    cs = dibujo.get_sprite("tile_ruin_cracked")
    if cs is not None:
        surface.blit(cs, (round(sx), round(sy)))
        return
    u = PIXEL_SCALE
    pygame.draw.lines(surface, (22, 22, 18), False, [(sx + 3 * u, sy + 2 * u), (sx + 7 * u, sy + 6 * u),
                                                     (sx + 5 * u, sy + 9 * u), (sx + 10 * u, sy + 13 * u)], max(1, u))
    pygame.draw.lines(surface, (22, 22, 18), False, [(sx + 11 * u, sy + 3 * u), (sx + 9 * u, sy + 7 * u),
                                                     (sx + 13 * u, sy + 10 * u)], max(1, u))


def do_charge(b, dt):
    cfg = BEAR_TYPES[b.kind]
    turn = cfg.get("charge_turn", 0.0)
    if turn > 0:
        want = math.atan2(estado.player.y - b.y, estado.player.x - b.x)
        cur = math.atan2(b.aim_dy, b.aim_dx)
        diff = (want - cur + math.pi) % (2 * math.pi) - math.pi
        cur += max(-turn * dt, min(turn * dt, diff))
        b.aim_dx, b.aim_dy = math.cos(cur), math.sin(cur)
    step = min(cfg["charge_speed"] * dt, b.charge_left)
    nx, ny = b.x + b.aim_dx * step, b.y + b.aim_dy * step
    b.vx, b.vy = b.aim_dx, b.aim_dy
    b.anim_t += dt * 2
    if mundo.dist(nx, ny, estado.player.x, estado.player.y) < cfg["charge_hit_r"]:      # embiste al jugador
        if not estado.god_mode:
            estado.player.hp = max(0, estado.player.hp - cfg["charge_dmg"])
            estado.log("¡El oso te embistió!")
        end_charge(b, 0.9)
        return
    if bear_charge_sweep(b, nx, ny, cfg["charge_hit_r"] * BEAR_BREAK_WIDTH):
        start_stagger(b, "¡Makadewaa se estrelló contra las ruinas!")
        return
    b.x, b.y = nx, ny
    b.charge_left -= step
    if b.charge_left <= 0:
        end_charge(b, cfg["charge_recover"])
        
def resolve_attack(b):
    cfg = BEAR_TYPES[b.kind]
    if b.attack == "swipe":
        pygame.mixer.Channel(18).play(bear_swipe_sound)
        b.strike_t = 0.15
        if not estado.god_mode and player_in_cone(b, cfg):
            estado.player.hp = max(0, estado.player.hp - cfg["swipe_dmg"])
            estado.log("¡El oso te alcanzó con un zarpazo!")
    elif b.attack == "slam":
        pygame.mixer.Channel(20).play(bear_slam_sound)
        estado.shockwaves.append({"x": b.x, "y": b.y, "r": 0.0, "max": cfg["slam_radius"],
                           "speed": cfg["slam_speed"], "thick": cfg["slam_thick"],
                           "dmg": cfg["slam_dmg"], "hit": False})
    elif b.attack == "roar":
        pygame.mixer.Channel(16).play(bear_roar_sound)
        for _ in range(cfg["roar_count"]):
            if sum(1 for x in estado.bears if x.kind == "weak" and not x.dead) < WEAK_SUMMON_MAX:
                spawn_weak_near(b)
        estado.log("¡El oso ruge y llama a su crías!")
        
def update_bears(dt):
    
    night = ciclo_dia.is_night()
    if not night:
        estado.bear_night_done = False
    has_boss_bear = any(b.kind == "boss" and not b.dead for b in estado.bears)
    if (night and not estado.bear_night_done and not estado.bear_spawned_once and not has_boss_bear
            and estado.boss is None and estado.clock_boss_defeated and estado.day_count >= BEAR_BOSS_FIRST_DAY):
        estado.bear_night_done = True
        estado.bear_spawned_once = True
        spawn_bear("boss")

    if estado.weak_bears_unlocked:                              # osos débiles: pocos y espaciados
        estado.bear_spawn_timer -= dt
        if estado.bear_spawn_timer <= 0:
            estado.bear_spawn_timer = WEAK_BEAR_SPAWN_NIGHT if night else WEAK_BEAR_SPAWN_DAY
            weak_count = sum(1 for x in estado.bears if x.kind == "weak" and not x.dead)
            if weak_count < WEAK_BEAR_CAP + (1 if night else 0):
                spawn_bear("weak", (25, 45))

    for b in estado.bears:
        if b.dead:
            continue
        cfg = BEAR_TYPES[b.kind]
        for attr in ("hit_flash", "strike_t", "cd", "charge_cd", "slam_cd", "stagger_immune"):
            if getattr(b, attr) > 0:
                setattr(b, attr, getattr(b, attr) - dt)
        if b.stagger > 0:
            b.stagger = max(0.0, b.stagger - cfg["stagger_decay"] * dt)
        if not (b.attack == "charge" and b.state in ("windup", "charge")):
            b.charge_acc = 0.0
        if b.roar_t > 0:
            b.roar_t -= dt
            continue

        d = mundo.dist(estado.player.x, estado.player.y, b.x, b.y)
        if b.kind == "weak" and not b.aggro and d > 80 * TILE:
            b.dead = True                                # se alejó demasiado: desaparece
            continue
        dx, dy = estado.player.x - b.x, estado.player.y - b.y
        l = math.hypot(dx, dy) or 1
        dx, dy = dx / l, dy / l

        if b.state == "chase":
            if b.kind == "weak" and not b.aggro:         # deambula hasta verte
                if d < (170 if night else 100):
                    b.aggro = True
                else:
                    bear_wander(b, dt)
                    continue
            if d > cfg["swipe_range"] * 0.7:
                spd = cfg["speed"] * b.speed_mult
                if mundo.tile_water(int(b.x // TILE), int(b.y // TILE)):
                    spd *= 0.5
                nx, ny = b.x + dx * spd * dt, b.y + dy * spd * dt
                construccion.move_or_breach(b, nx, ny, dx, dy, spd, dt, cfg["struct_dps"])
                b.vx, b.vy = dx, dy
                b.anim_t += dt
            else:
                b.vx = b.vy = 0.0
            if abs(dx) >= abs(dy):
                b.sprite_dir = "right" if dx > 0 else "left"
            else:
                b.sprite_dir = "down" if dy > 0 else "up"

            if ("roar_thresholds" in cfg and b.roar_stage < len(cfg["roar_thresholds"])
                    and b.hp <= b.max_hp * cfg["roar_thresholds"][b.roar_stage]):
                b.roar_stage += 1
                begin_attack(b, "roar", dx, dy)
            elif b.cd <= 0:
                if ("slam_radius" in cfg and b.slam_cd <= 0 and d <= cfg["slam_trigger"]
                        and (d > cfg["swipe_range"] or random.random() < 0.4)):
                    begin_attack(b, "slam", dx, dy)
                elif d <= cfg["swipe_range"]:
                    begin_attack(b, "swipe", dx, dy)
                elif ("charge_range" in cfg and b.charge_cd <= 0
                      and cfg["charge_min"] <= d <= cfg["charge_range"]):
                    begin_attack(b, "charge", dx, dy)
        elif b.state == "charge":
            do_charge(b, dt)
        else:                                            # windup / recover / stagger: quieto
            b.vx = b.vy = 0.0
            if b.state == "windup" and b.attack == "charge" and b.state_t > cfg["charge_lock"]:
                b.aim_dx, b.aim_dy = dx, dy              # la franja de la carga te sigue
                if abs(dx) >= abs(dy):
                    b.sprite_dir = "right" if dx > 0 else "left"
                else:
                    b.sprite_dir = "down" if dy > 0 else "up"
            b.state_t -= dt
            if b.state_t <= 0:
                advance_state(b)

    estado.bears[:] = [b for b in estado.bears if not b.dead]
    dibujo.update_shockwaves(dt)

def bear_wander(b, dt):
    cfg = BEAR_TYPES[b.kind]
    b.wander_t -= dt
    if b.wander_t <= 0:
        b.wander_t = 2 + random.random() * 3
        a = random.random() * math.pi * 2
        b.wander_dir = (math.cos(a), math.sin(a))
    wx, wy = b.wander_dir
    spd = cfg["speed"] * 0.5
    nx, ny = b.x + wx * spd * dt, b.y + wy * spd * dt
    if actualizacion._zombie_can_move(b, nx, ny) and not mundo.tile_water(int(nx // TILE), int(ny // TILE)):
        b.x, b.y = nx, ny
    b.vx, b.vy = wx, wy
    b.anim_t += dt
    if abs(wx) >= abs(wy):
        b.sprite_dir = "right" if wx > 0 else "left"
    else:
        b.sprite_dir = "down" if wy > 0 else "up"

def spawn_weak_near(boss_bear):
    for _ in range(30):
        a = random.random() * math.pi * 2
        r = random.uniform(22, 34)
        x, y = boss_bear.x + math.cos(a) * r, boss_bear.y + math.sin(a) * r
        tx, ty = int(x // TILE), int(y // TILE)
        if colision.blocked(tx, ty, True) or mundo.tile_water(tx, ty):
            continue
        w = entidades.Bear("weak", x, y)
        w.aggro = True
        w.cd = 1.2
        estado.bears.append(w)
        return

def draw_roar_telegraph(surface, b):
    if b.state != "windup" or b.attack != "roar":
        return
    sx, sy = camara.world_to_screen(b.x, b.y)
    prog = 1 - b.state_t / b.state_total
    layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    for i in range(3):                              # tres ondas que salen del oso
        p = (prog * 1.6 + i / 3) % 1.0
        R = max(2, int(p * 60 * PIXEL_SCALE))
        pygame.draw.circle(layer, (240, 170, 50, int(200 * (1 - p))), (int(sx), int(sy)), R, 3)
    surface.blit(layer, (0, 0))
