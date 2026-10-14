"""Jefe: Baca, el Rompe Rocas (y sus perros).

Salió de ebanon.py (original), alrededor de las líneas 2569-2997.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global actualizacion, camara, colision, construccion, dibujo
    global estado, makadewaa, mundo, salto
    from interfaz import dibujo
    from jefes import makadewaa
    from nucleo import estado, mundo
    from sistemas import actualizacion, camara, colision, construccion
    from sistemas import salto


# ── BACA EL ROMPE ROCKAS ──
BACA_NAME = "BACA EL ROMPE ROCAS"
BACA_TITLE = "Señor de la Jauría"
BACA = {
    "hp": 900, "speed": 46, "size": 2.8, "struct_dps": 70, "cd": 1.2,
    "pick_range": 54, "pick_arc": 0.8, "pick_windup": 0.5, "pick_recover": 0.5, "pick_dmg": 51,
    "dogs_windup": 0.6, "dogs_recover": 0.8, "dogs_cd": 7.0, "dogs_range": 220,
    "rocks_windup": 0.9, "rocks_recover": 1.0, "rock_cd": 8.0, "rock_min": 50, "rock_range": 300,
    "rock_speed": 130, "rock_dist": 300, "rock_spread": 0.44, "rock_dmg": 40,
    "rock_hit_r": 12, "rock_struct_dmg": 90,
}
BACA_DOG = {"hp": 60, "slot": 24, "aim": 0.5, "lock": 0.15, "gap": 0.5,
            "lunge_speed": 260, "lunge_dist": 140, "hit_r": 9, "dmg": 18, "return_speed": 200}
BACA_RAGE_SPEED = 1.35     # cuánto más rápido va enfurecido
BACA_RAGE_CD = 0.5         # sus ataques se repiten más rápido (menor = más seguido)

baca = None
baca_dogs = []
boulders = []

class Baca:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.hp = self.max_hp = BACA["hp"]
        self.size = BACA["size"]
        self.hit_flash = 0.0
        self.sprite_dir = "down"
        self.anim_t = 0.0
        self.vx = self.vy = 0.0
        self.block_t = 0.0
        self.detour_side = random.choice((1, -1))
        self.state = "chase"       # chase / windup / dogs / recover
        self.attack = None
        self.state_t = 0.0
        self.state_total = 1.0
        self.cd = 1.5
        self.rock_cd = 4.0
        self.dogs_cd = 2.0
        self.aim_dx, self.aim_dy = 1.0, 0.0
        self.strike_t = 0.0
        self.enraged = False
        self.roar_t = BOSS_ROAR_TIME
        self.dog_queue = []
        self.dog_wait = 0.0

class BacaDog:
    def __init__(self, x, y, side):
        self.x, self.y = x, y
        self.side = side           # -1 = izquierdo, 1 = derecho
        self.hp = self.max_hp = BACA_DOG["hp"]
        self.state = "heel"        # heel / aim / lunge / return
        self.t = 0.0
        self.dx, self.dy = 1.0, 0.0
        self.left = 0.0
        self.hit = False
        self.hit_flash = 0.0
        self.dead = False

def spawn_baca():
    global baca
    for _ in range(200):
        ang = random.random() * math.pi * 2
        r = random.uniform(18, 26) * TILE
        tx = int((estado.player.x + math.cos(ang) * r) // TILE)
        ty = int((estado.player.y + math.sin(ang) * r) // TILE)
        if not (0 <= tx < estado.WORLD_W and 0 <= ty < estado.WORLD_H):
            continue
        if mundo.tile_water(tx, ty) or mundo.tile_solid(tx, ty):
            continue
        baca = Baca(tx * TILE + 8, ty * TILE + 8)
        baca_dogs.clear()
        for side in (-1, 1):
            baca_dogs.append(BacaDog(baca.x + side * 10, baca.y, side))
        pygame.mixer.Channel(16).play(bear_roar_sound)
        estado.log(f"¡{BACA_NAME}! {BACA_TITLE}.")
        return

def hit_baca(dmg):
    global baca
    b = baca
    if b is None:
        return
    b.hp -= dmg
    b.hit_flash = 0.12
    if b.hp <= 0:
        estado.log("¡Baca cayó!")
        # (Parte 2: aquí soltará su pico y la lámpara)
        estado.drops.append({"x": b.x - 12, "y": b.y, "kind": "baca_pick"})
        estado.drops.append({"x": b.x + 12, "y": b.y, "kind": "baca_lamp"})
        estado.log("Soltó su zapapico y una lámpara.")
        baca = None
        baca_dogs.clear()

def hit_baca_dog(dg, dmg):
    dg.hp -= dmg
    dg.hit_flash = 0.12
    if dg.hp <= 0 and not dg.dead:
        dg.dead = True
        estado.log("¡Mataste a un perro de Baca!")
        if baca and not baca.enraged:
            baca.enraged = True
            estado.log("¡Baca se enfurece!")

def bullet_hits_baca(bl):
    if baca and mundo.dist(bl["x"], bl["y"], baca.x, baca.y) < 8 * baca.size:
        hit_baca(bl["dmg"])
        return True
    for g in baca_dogs:
        if not g.dead and mundo.dist(bl["x"], bl["y"], g.x, g.y) < 8:
            hit_baca_dog(g, bl["dmg"])
            return True
    return False

def melee_hits_baca(ax, ay, rng, dmg):
    if baca and mundo.dist(ax, ay, baca.x, baca.y) < rng + 6 * baca.size:
        hit_baca(dmg)
    for g in list(baca_dogs):
        if not g.dead and mundo.dist(ax, ay, g.x, g.y) < rng:
            hit_baca_dog(g, dmg)

def baca_in_cone(b):
    dx, dy = estado.player.x - b.x, estado.player.y - b.y
    d = math.hypot(dx, dy)
    if d > BACA["pick_range"] + 4:
        return False
    if d < 1:
        return True
    diff = abs((math.atan2(dy, dx) - math.atan2(b.aim_dy, b.aim_dx) + math.pi) % (2 * math.pi) - math.pi)
    return diff <= BACA["pick_arc"]

def fire_boulders(b):
    cfg = BACA
    base = math.atan2(b.aim_dy, b.aim_dx)
    pygame.mixer.Channel(20).play(bear_slam_sound)
    for off in (-cfg["rock_spread"], 0.0, cfg["rock_spread"]):
        a = base + off
        boulders.append({"x": b.x + math.cos(a) * 14, "y": b.y + math.sin(a) * 14,
                         "vx": math.cos(a) * cfg["rock_speed"], "vy": math.sin(a) * cfg["rock_speed"],
                         "life": cfg["rock_dist"] / cfg["rock_speed"]})
    b.strike_t = 0.15
    estado.log("¡Baca lanza rocas!")

def update_boulders(dt):
    for r in boulders:
        r["x"] += r["vx"] * dt
        r["y"] += r["vy"] * dt
        r["life"] -= dt
        
        # Check if player is jumping over this rock
        tx, ty = int(r["x"] // TILE), int(r["y"] // TILE)
        if salto.en_el_aire() and salto.cruza(tx, ty):
            # Player is jumping over this rock - no damage!
            continue
            
        if not estado.god_mode and mundo.dist(r["x"], r["y"], estado.player.x, estado.player.y) < BACA["rock_hit_r"]:
            estado.player.hp = max(0, estado.player.hp - BACA["rock_dmg"])
            estado.log("¡Una roca de Baca te golpeó!")
            r["life"] = 0
            continue
            
        if colision.blocked(tx, ty, True, ignore_props=True):
            st = construccion.structure_at_tile(tx, ty)
            if st and st["type"] in ATTACKABLE and "hp" in st:
                construccion.damage_structure(st, BACA["rock_struct_dmg"])
            r["life"] = 0
    boulders[:] = [r for r in boulders if r["life"] > 0]

def baca_begin(b, name, dx, dy):
    cfg = BACA
    mult = BACA_RAGE_CD if b.enraged else 1.0
    b.attack = name
    b.state = "windup"
    b.state_total = b.state_t = cfg[name + "_windup"]
    b.aim_dx, b.aim_dy = dx, dy
    if name == "rocks":
        b.rock_cd = cfg["rock_cd"] * mult
    if name == "dogs":
        b.dogs_cd = cfg["dogs_cd"] * mult
    if abs(dx) >= abs(dy):
        b.sprite_dir = "right" if dx > 0 else "left"
    else:
        b.sprite_dir = "down" if dy > 0 else "up"
    pygame.mixer.Channel(17).play(bear_growl_sound)

def baca_resolve(b):
    cfg = BACA
    if b.attack == "pick":
        pygame.mixer.Channel(18).play(bear_swipe_sound)
        b.strike_t = 0.15
        if not estado.god_mode and baca_in_cone(b):
            estado.player.hp = max(0, estado.player.hp - cfg["pick_dmg"])
            estado.log("¡Baca te alcanzó con el zapapico!")
        b.state = "recover"
        b.state_total = b.state_t = cfg["pick_recover"]
    elif b.attack == "rocks":
        fire_boulders(b)
        b.state = "recover"
        b.state_total = b.state_t = cfg["rocks_recover"]
    elif b.attack == "dogs":
        alive = [g for g in baca_dogs if not g.dead]
        alive.sort(key=lambda g: g.side)          # el izquierdo (-1) primero
        b.dog_queue = alive
        b.dog_wait = 0.0
        b.state = "dogs"

def baca_run_dogs(b, dt):
    cfg = BACA_DOG
    b.dog_wait -= dt
    if b.dog_queue and b.dog_wait <= 0:
        dg = b.dog_queue.pop(0)
        if not dg.dead:
            dg.state = "aim"
            dg.t = cfg["aim"]
            dx, dy = estado.player.x - dg.x, estado.player.y - dg.y
            l = math.hypot(dx, dy) or 1
            dg.dx, dg.dy = dx / l, dy / l
            b.dog_wait = cfg["aim"] + cfg["gap"]
    if not b.dog_queue and all(g.dead or g.state == "heel" for g in baca_dogs):
        b.state = "recover"
        b.state_total = b.state_t = BACA["dogs_recover"]

def update_baca_dogs(b, dt):
    cfg = BACA_DOG
    for dg in baca_dogs:
        if dg.dead:
            continue
        if dg.hit_flash > 0:
            dg.hit_flash -= dt
        ux, uy = b.aim_dx, b.aim_dy
        vx, vy = (uy, -ux) if dg.side < 0 else (-uy, ux)
        slot_x, slot_y = b.x + vx * cfg["slot"], b.y + vy * cfg["slot"]
        if dg.state == "aim":
            dg.t -= dt
            if dg.t > cfg["lock"]:
                dx, dy = estado.player.x - dg.x, estado.player.y - dg.y
                l = math.hypot(dx, dy) or 1
                dg.dx, dg.dy = dx / l, dy / l
            if dg.t <= 0:
                dg.state = "lunge"
                dg.left = cfg["lunge_dist"]
                dg.hit = False
        elif dg.state == "lunge":
            step = min(cfg["lunge_speed"] * dt, dg.left)
            nx, ny = dg.x + dg.dx * step, dg.y + dg.dy * step
            if not estado.god_mode and not dg.hit and mundo.dist(nx, ny, estado.player.x, estado.player.y) < cfg["hit_r"]:
                dg.hit = True
                estado.player.hp = max(0, estado.player.hp - cfg["dmg"])
                estado.log("¡Un perro de Baca te mordió!")
                dg.state = "return"
            elif actualizacion._zombie_can_move(dg, nx, ny):
                dg.x, dg.y = nx, ny
                dg.left -= step
                if dg.left <= 0:
                    dg.state = "return"
            else:
                dg.state = "return"
        else:                                      # heel o return: ir a su sitio junto a Baca
            dxs, dys = slot_x - dg.x, slot_y - dg.y
            d = math.hypot(dxs, dys)
            if d < 4:
                dg.state = "heel"
            if d > 1.5:
                step = min(d, cfg["return_speed"] * dt)
                dg.x += dxs / d * step
                dg.y += dys / d * step

def update_baca(dt):
    update_boulders(dt)
    b = baca
    if b is None:
        return
    cfg = BACA
    for attr in ("hit_flash", "strike_t", "cd", "rock_cd", "dogs_cd"):
        if getattr(b, attr) > 0:
            setattr(b, attr, getattr(b, attr) - dt)
    update_baca_dogs(b, dt)
    if b.roar_t > 0:
        b.roar_t -= dt
        return
    d = mundo.dist(estado.player.x, estado.player.y, b.x, b.y)
    dx, dy = estado.player.x - b.x, estado.player.y - b.y
    l = math.hypot(dx, dy) or 1
    dx, dy = dx / l, dy / l

    if b.state == "chase":
        b.aim_dx, b.aim_dy = dx, dy
        if d > cfg["pick_range"] * 0.7:
            spd = cfg["speed"] * (BACA_RAGE_SPEED if b.enraged else 1.0)
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
        if b.cd <= 0:
            if d <= cfg["pick_range"]:
                baca_begin(b, "pick", dx, dy)
            else:
                options = []
                if b.dogs_cd <= 0 and d <= cfg["dogs_range"] and any(not g.dead for g in baca_dogs):
                    options.append("dogs")
                if b.rock_cd <= 0 and cfg["rock_min"] <= d <= cfg["rock_range"]:
                    options.append("rocks")
                if options:
                    baca_begin(b, random.choice(options), dx, dy)
    elif b.state == "windup":
        b.vx = b.vy = 0.0
        if b.attack == "rocks" and b.state_t > 0.25:
            b.aim_dx, b.aim_dy = dx, dy          # apunta hasta el último momento
        b.state_t -= dt
        if b.state_t <= 0:
            baca_resolve(b)
    elif b.state == "dogs":
        b.vx = b.vy = 0.0
        baca_run_dogs(b, dt)
    else:                                          # recover
        b.vx = b.vy = 0.0
        b.state_t -= dt
        if b.state_t <= 0:
            b.state = "chase"
            b.attack = None
            b.cd = cfg["cd"] * (BACA_RAGE_CD if b.enraged else 1.0)

def draw_baca_body(surface, b):
    sx, sy = camara.world_to_screen(b.x, b.y)
    k = PIXEL_SCALE * b.size
    warning = b.state == "windup" and (pygame.time.get_ticks() // 80) % 2 == 0
    if b.hit_flash > 0:
        col = (255, 255, 255)
    elif warning:
        col = (200, 60, 40)
    elif b.enraged:
        col = (150, 50, 40)
    else:
        col = (92, 72, 60)
    head = (255, 255, 255) if b.hit_flash > 0 else tuple(min(255, c + 30) for c in col)
    horiz = b.sprite_dir in ("left", "right")
    bw, bh = (16, 12) if horiz else (12, 16)
    dibujo.px(surface, sx - bw * k / 2, sy - bh * k / 2, bw * k, bh * k, col)
    hx, hy = {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1)}[b.sprite_dir]
    cx, cy = sx + hx * 9 * k, sy + hy * 9 * k
    dibujo.px(surface, cx - 3 * k, cy - 3 * k, 6 * k, 6 * k, head)
    # el zapapico
    ex, ey = sx + b.aim_dx * 16 * k, sy + b.aim_dy * 16 * k
    pygame.draw.line(surface, (110, 90, 60), (sx, sy), (ex, ey), max(2, 2 * PIXEL_SCALE))
    pw = 5 * PIXEL_SCALE
    pygame.draw.line(surface, (160, 160, 150), (ex - b.aim_dy * pw, ey + b.aim_dx * pw),
                     (ex + b.aim_dy * pw, ey - b.aim_dx * pw), max(2, 3 * PIXEL_SCALE))
    if b.state == "windup":
        ex_ = FONT_MED.render("!", True, (255, 80, 60))
        surface.blit(ex_, (sx - ex_.get_width() // 2, sy - bh * k / 2 - ex_.get_height() - 4))

def draw_baca_dog(surface, g):
    sx, sy = camara.world_to_screen(g.x, g.y)
    u = PIXEL_SCALE
    col = (255, 255, 255) if g.hit_flash > 0 else ((200, 60, 40) if g.state == "aim" else (120, 100, 80))
    dibujo.px(surface, sx - 5 * u, sy - 3 * u, 10 * u, 6 * u, col)
    hx = 3 if g.dx >= 0 else -7
    dibujo.px(surface, sx + hx * u, sy - 4 * u, 4 * u, 4 * u, tuple(min(255, c + 30) for c in col))
    if g.hp < g.max_hp:
        dibujo.px(surface, sx - 6 * u, sy - 8 * u, 12 * u, 2 * u, (0, 0, 0))
        dibujo.px(surface, sx - 6 * u, sy - 8 * u, 12 * u * max(0.0, g.hp / g.max_hp), 2 * u, (184, 67, 59))

def draw_baca_all(surface):
    b = baca
    cfg = BACA
    pick_t = bool(b) and b.attack == "pick" and (b.state == "windup" or b.strike_t > 0)
    rocks_t = bool(b) and b.state == "windup" and b.attack == "rocks"
    dogs_t = any(g.state == "aim" and not g.dead for g in baca_dogs)
    if pick_t or rocks_t or dogs_t:
        layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        if pick_t:
            sx, sy = camara.world_to_screen(b.x, b.y)
            R = cfg["pick_range"] * PIXEL_SCALE
            ang = math.atan2(b.aim_dy, b.aim_dx)
            half = cfg["pick_arc"]
            if b.state == "windup":
                prog = 1 - b.state_t / b.state_total
                pygame.draw.polygon(layer, (220, 40, 30, 45), makadewaa.cone_points(sx, sy, ang, half, R))
                pygame.draw.polygon(layer, (235, 70, 40, 130), makadewaa.cone_points(sx, sy, ang, half, R * prog))
                pygame.draw.polygon(layer, (255, 110, 70, 230), makadewaa.cone_points(sx, sy, ang, half, R), 2)
            else:
                a = int(220 * max(0.0, b.strike_t) / 0.15)
                pygame.draw.polygon(layer, (255, 230, 200, a), makadewaa.cone_points(sx, sy, ang, half, R))
        if rocks_t:
            sx, sy = camara.world_to_screen(b.x, b.y)
            base = math.atan2(b.aim_dy, b.aim_dx)
            L = cfg["rock_dist"] * PIXEL_SCALE
            locked = b.state_t <= 0.25
            col = (255, 60, 40, 200) if locked else (255, 110, 70, 120)
            for off in (-cfg["rock_spread"], 0.0, cfg["rock_spread"]):
                a = base + off
                pygame.draw.line(layer, col, (sx, sy), (sx + math.cos(a) * L, sy + math.sin(a) * L),
                                 max(2, int(cfg["rock_hit_r"] * 2 * PIXEL_SCALE)))
        for g in baca_dogs:
            if g.state == "aim" and not g.dead:
                gx, gy = camara.world_to_screen(g.x, g.y)
                L = BACA_DOG["lunge_dist"] * PIXEL_SCALE
                locked = g.t <= BACA_DOG["lock"]
                col = (255, 60, 40, 190) if locked else (255, 110, 70, 110)
                pygame.draw.line(layer, col, (gx, gy), (gx + g.dx * L, gy + g.dy * L),
                                 max(2, int(BACA_DOG["hit_r"] * 2 * PIXEL_SCALE)))
        surface.blit(layer, (0, 0))
    if b:
        draw_baca_body(surface, b)
    for g in baca_dogs:
        if not g.dead:
            draw_baca_dog(surface, g)
    for r in boulders:
        sx, sy = camara.world_to_screen(r["x"], r["y"])
        rad = int(cfg["rock_hit_r"] * PIXEL_SCALE)
        pygame.draw.circle(surface, PALETTE["rock_dark"], (int(sx), int(sy)), rad)
        pygame.draw.circle(surface, PALETTE["rock"], (int(sx - 2 * PIXEL_SCALE), int(sy - 2 * PIXEL_SCALE)),
                           int(rad * 0.6))

def render_baca_bar(surface):
    b = baca
    if not b:
        return
    step = FONT_MED.get_height() + 6 * PIXEL_SCALE + 16
    y = 14
    if estado.boss:
        y += step
    if any(x.kind == "boss" and not x.dead for x in estado.bears):
        y += step
    name = FONT_MED.render(f"{BACA_NAME} — {BACA_TITLE}", True, (190, 150, 90))
    surface.blit(name, (SCREEN_W // 2 - name.get_width() // 2, y))
    bw, bh = int(SCREEN_W * 0.4), 6 * PIXEL_SCALE
    bx, by = SCREEN_W // 2 - bw // 2, y + name.get_height() + 4
    pygame.draw.rect(surface, (0, 0, 0), (bx - 2, by - 2, bw + 4, bh + 4))
    pygame.draw.rect(surface, (150, 110, 50), (bx, by, int(bw * max(0, b.hp / b.max_hp)), bh))
