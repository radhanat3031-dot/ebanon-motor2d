"""La mina: generación, entrada/salida, zombis y murciélagos.

Salió de ebanon.py (original), alrededor de las líneas 5466-6125.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global ayudantes, baca_jefe, camara, colision, deshuesadero
    global dibujo, entidades, estado, fundidora, makadewaa
    global mundo, neri_jefe, refineria
    from interfaz import dibujo
    from jefes import baca_jefe, makadewaa, neri_jefe
    from mapas import deshuesadero, fundidora, refineria
    from npcs import ayudantes
    from nucleo import entidades, estado, mundo
    from sistemas import camara, colision


    
# ============================================================================
# LA MINA
# ============================================================================
class Bat:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.hp = 20
        self.angle = random.uniform(0, math.pi * 2)
        self.t = random.uniform(0, 6)
        self.state = "flutter"     # flutter / dive / retreat
        self.state_t = 0.0
        self.cd = 0.0
        self.hit_flash = 0.0
        self.dead = False


def _entity_lists():
    return {"zombies": estado.zombies, "bullets": estado.bullets, "structures": estado.structures, "drops": estado.drops,
            "wood": estado.wood_pickups, "rock": estado.rock_pickups, "scrap": estado.scrap_pickups,
            "food": estado.food_pickups, "ammo": estado.ammo_pickups, "bears": estado.bears,
            "baca_dogs": baca_jefe.baca_dogs, "boulders": baca_jefe.boulders, "shockwaves": estado.shockwaves}


def _mine_open(tx, ty, r=2):
    """True si alrededor hay espacio libre (solo pasa en las cavernas)."""
    bad = (mundo.TILE_TYPE["ruin"], mundo.TILE_TYPE["water"], mundo.TILE_TYPE["cave"])
    for yy in range(ty - r, ty + r + 1):
        for xx in range(tx - r, tx + r + 1):
            if mundo.tile_at(xx, yy) in bad:
                return False
    return True


def gen_mine(seed):
    """Crea la mina. La misma semilla da siempre la misma mina."""
    
    rng = random.Random(seed)
    W, H = MINE_W, MINE_H
    WALL, FLOOR = mundo.TILE_TYPE["ruin"], mundo.TILE_TYPE["hill"]
    WATER, ROAD, CAVE = mundo.TILE_TYPE["water"], mundo.TILE_TYPE["road"], mundo.TILE_TYPE["cave"]
    g = [[WALL] * W for _ in range(H)]
    nox, noy = rng.uniform(0, 5000), rng.uniform(0, 5000)
    margin = 4
    paths = []        # (nodo_a, nodo_b, puntos)

    def inside(xx, yy, m=margin):
        return m <= xx < W - m and m <= yy < H - m

    def carve(cx_, cy_, r):
        x0 = max(margin, int(cx_ - r) - 1)
        x1 = min(W - margin - 1, int(cx_ + r) + 1)
        y0 = max(margin, int(cy_ - r) - 1)
        y1 = min(H - margin - 1, int(cy_ + r) + 1)
        r2 = r * r
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                if (xx - cx_) ** 2 + (yy - cy_) ** 2 <= r2:
                    g[yy][xx] = FLOOR

    def carve_cave(cx_, cy_, r):
        R = int(r * 1.4) + 2
        for yy in range(max(margin, int(cy_) - R), min(H - margin, int(cy_) + R + 1)):
            for xx in range(max(margin, int(cx_) - R), min(W - margin, int(cx_) + R + 1)):
                n = mundo.smooth_noise(xx * 0.17 + nox, yy * 0.17 + noy)
                if math.hypot(xx - cx_, yy - cy_) <= r * (0.72 + 0.5 * n):
                    g[yy][xx] = FLOOR

    def tunnel(a, b, ia, ib):
        x, y = a[0], a[1]
        tx_, ty_ = b[0], b[1]
        wob = rng.uniform(-0.8, 0.8)
        pts = []
        for _ in range(4000):
            d = math.hypot(tx_ - x, ty_ - y)
            if d < 3:
                break
            wob = max(-1.15, min(1.15, wob + rng.uniform(-0.22, 0.22)))
            ang = math.atan2(ty_ - y, tx_ - x) + wob * min(1.0, d / 18.0)
            x += math.cos(ang)
            y += math.sin(ang)
            x = max(margin + 2, min(W - margin - 3, x))
            y = max(margin + 2, min(H - margin - 3, y))
            carve(x, y, 1.6)          # 1.6 = caminos de unos 3 tiles de ancho
            pts.append((x, y))
        paths.append((ia, ib, pts))

    # --- entrada y guarida (siempre en lados opuestos = lejos) ---
    lair_r = 20
    li = lair_r + 12
    inset = 16
    side = rng.choice(("left", "right", "top", "bottom"))
    if side == "left":
        ex, ey = inset, rng.uniform(H * 0.3, H * 0.7)
        lx, ly = W - li, rng.uniform(H * 0.3, H * 0.7)
    elif side == "right":
        ex, ey = W - inset, rng.uniform(H * 0.3, H * 0.7)
        lx, ly = li, rng.uniform(H * 0.3, H * 0.7)
    elif side == "top":
        ex, ey = rng.uniform(W * 0.3, W * 0.7), inset
        lx, ly = rng.uniform(W * 0.3, W * 0.7), H - li
    else:
        ex, ey = rng.uniform(W * 0.3, W * 0.7), H - inset
        lx, ly = rng.uniform(W * 0.3, W * 0.7), li

    # --- cavernas ---
    nodes = [(ex, ey, 7.0)]
    n_extra = max(6, (W * H) // 7000)
    for _ in range(n_extra * 40):
        if len(nodes) - 1 >= n_extra:
            break
        r = rng.uniform(7, 15)
        x = rng.uniform(margin + 18, W - margin - 18)
        y = rng.uniform(margin + 18, H - margin - 18)
        if all(math.hypot(x - ox_, y - oy_) >= r + orad + 12
               for (ox_, oy_, orad) in nodes + [(lx, ly, lair_r)]):
            nodes.append((x, y, r))
    nodes.append((lx, ly, float(lair_r)))
    n = len(nodes)
    for (x, y, r) in nodes:
        carve_cave(x, y, r)

    # --- conectar con túneles sinuosos (árbol + algunos bucles) ---
    linked = {0}
    edges = []
    while len(linked) < n:
        best = None
        for a in linked:
            for b in range(n):
                if b in linked:
                    continue
                d = math.hypot(nodes[a][0] - nodes[b][0], nodes[a][1] - nodes[b][1])
                if best is None or d < best[0]:
                    best = (d, a, b)
        edges.append((best[1], best[2]))
        linked.add(best[2])
    for _ in range(3 + n // 4):
        a, b = rng.randrange(n), rng.randrange(n)
        if a != b and (a, b) not in edges and (b, a) not in edges \
                and math.hypot(nodes[a][0] - nodes[b][0], nodes[a][1] - nodes[b][1]) < W * 0.4:
            edges.append((a, b))
    for a, b in edges:
        tunnel(nodes[a], nodes[b], a, b)

    # --- callejones sin salida (laberinto) ---
    base_pts = [p for (_, _, p) in paths if len(p) > 10]
    for __ in range(max(10, W // 10)):
        x, y = rng.choice(base_pts)[0]
        pts = rng.choice(base_pts)
        x, y = pts[rng.randrange(len(pts))]
        ang = rng.uniform(0, 2 * math.pi)
        for ___ in range(rng.randint(20, 60)):
            ang += rng.uniform(-0.3, 0.3)
            nx_, ny_ = x + math.cos(ang), y + math.sin(ang)
            if nx_ < margin + 4 or ny_ < margin + 4 or nx_ > W - margin - 5 or ny_ > H - margin - 5:
                ang += math.pi / 2
                continue
            x, y = nx_, ny_
            carve(x, y, 1.6)
        carve_cave(x, y, rng.uniform(2.5, 4.5))

    # --- pilares en la guarida (para cubrirse al pelear) ---
    for _ in range(7):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(6, 12)
        pxx, pyy = int(lx + math.cos(a) * rr), int(ly + math.sin(a) * rr)
        for dy in (0, 1):
            for dx in (0, 1):
                if inside(pxx + dx, pyy + dy) and g[pyy + dy][pxx + dx] == FLOOR:
                    g[pyy + dy][pxx + dx] = WALL

    # --- ríos delgados ---
    long_paths = [p for p in paths if len(p[2]) > 50]
    rng.shuffle(long_paths)
    for (a, b, pts) in long_paths[:3]:
        for (x, y) in pts[int(len(pts) * 0.12):int(len(pts) * 0.88)]:
            tx_, ty_ = int(x), int(y)
            if math.hypot(tx_ - ex, ty_ - ey) < 10 or math.hypot(tx_ - lx, ty_ - ly) < 24:
                continue
            if g[ty_][tx_] == FLOOR:
                g[ty_][tx_] = WATER

    # --- lagos pequeños ---
    for idx, (x, y, r) in enumerate(nodes):
        if idx == 0 or r < 10 or rng.random() < 0.35:
            continue
        off = 0.55 if idx == n - 1 else 0.35
        a = rng.uniform(0, 2 * math.pi)
        lcx, lcy = x + math.cos(a) * r * off, y + math.sin(a) * r * off
        lr = rng.uniform(2.5, 4.2)
        for yy in range(int(lcy - lr - 2), int(lcy + lr + 3)):
            for xx in range(int(lcx - lr - 2), int(lcx + lr + 3)):
                if inside(xx, yy) and g[yy][xx] == FLOOR:
                    nz = mundo.smooth_noise(xx * 0.3 + nox, yy * 0.3 + noy)
                    if math.hypot(xx - lcx, yy - lcy) <= lr * (0.7 + 0.6 * nz):
                        g[yy][xx] = WATER

    # --- rastros de mina (vías) ---
    rails = long_paths[3:6] + [p for p in paths if p[0] == 0][:1]
    for (a, b, pts) in rails:
        for (x, y) in pts[int(len(pts) * 0.05):int(len(pts) * 0.95)]:
            if g[int(y)][int(x)] == FLOOR:
                g[int(y)][int(x)] = ROAD

    # --- cámaras secretas detrás de paredes marcadas ---
    mine_breakable.clear()
    loot = []
    want = max(4, (W * H) // 14000)
    made = 0
    pool = [p[2] for p in paths if len(p[2]) > 30]
    for _ in range(800):
        if made >= want or not pool:
            break
        pts = rng.choice(pool)
        i = rng.randrange(10, len(pts) - 10)
        x, y = pts[i]
        x0, y0 = pts[i - 4]
        x1, y1 = pts[i + 4]
        qx, qy = -(y1 - y0), (x1 - x0)
        if rng.random() < 0.5:
            qx, qy = -qx, -qy
        if abs(qx) >= abs(qy):
            sx_, sy_ = (1 if qx > 0 else -1), 0
        else:
            sx_, sy_ = 0, (1 if qy > 0 else -1)
        bx, by = int(x), int(y)
        k = 1
        while k <= 5 and inside(bx + sx_ * k, by + sy_ * k, 1) and g[by + sy_ * k][bx + sx_ * k] != WALL:
            k += 1
        if k > 5:
            continue
        bkx, bky = bx + sx_ * k, by + sy_ * k       # la pared marcada
        okk = True
        for t in range(0, 11):
            lim = 1 if t < 3 else 4
            for lat in range(-lim, lim + 1):
                xx = bkx + sx_ * t + sy_ * lat
                yy = bky + sy_ * t + sx_ * lat
                if not inside(xx, yy) or g[yy][xx] != WALL:
                    okk = False
        if not okk:
            continue
        g[bky + sy_][bkx + sx_] = FLOOR              # pasillo de 1 tile
        g[bky + 2 * sy_][bkx + 2 * sx_] = FLOOR
        ccx, ccy = bkx + sx_ * 6, bky + sy_ * 6      # cámara
        for yy in range(ccy - 3, ccy + 4):
            for xx in range(ccx - 3, ccx + 4):
                if math.hypot(xx - ccx, yy - ccy) <= 3:
                    g[yy][xx] = FLOOR
        mine_breakable.add((bkx, bky))
        spots = [(ccx + sy_ * 2, ccy + sx_ * 2), (ccx - sy_ * 2, ccy - sx_ * 2), (ccx + sx_ * 2, ccy + sy_ * 2)]
        for sp in spots:
            loot.append((rng.choice(["scrap", "rock", "herb", "wood", "ammo"]), sp[0], sp[1]))
        made += 1

    # --- entrada (salida hacia la isla) ---
    exi, eyi = int(ex), int(ey)
    g[eyi][exi] = CAVE

    # --- paredes que ya rompiste en partidas anteriores ---
    for bx_, by_ in mine_broken:
        if 0 <= bx_ < W and 0 <= by_ < H:
            g[by_][bx_] = FLOOR
            mine_breakable.discard((bx_, by_))

    mundo.WORLD = g
    estado.WORLD_MASK = [[True] * W for _ in range(H)]
    estado.WORLD_W, estado.WORLD_H = W, H
    estado.WORLD_CENTER = (W // 2, H // 2)
    estado.WORLD_RADIUS = max(W, H)
    MINE_INFO["exit"] = (exi * TILE + 8, eyi * TILE + 8)
    MINE_INFO["start"] = (exi * TILE + 8, (eyi + 2) * TILE + 8)
    MINE_INFO["lair"] = (int(lx) * TILE + 8, int(ly) * TILE + 8)   # ← aquí pondremos a Neri
    return loot


def spawn_mine_resources(loot):
    for lst in (estado.wood_pickups, estado.rock_pickups, estado.scrap_pickups, estado.food_pickups, estado.ammo_pickups):
        lst.clear()
    for kind, tx, ty in loot:                       # botín de las cámaras secretas
        pos = {"x": tx * TILE + 8, "y": ty * TILE + 8, "active": True, "timer": 0.0}
        if kind == "wood":
            estado.wood_pickups.append(dict(pos, type="tree"))
        elif kind == "rock":
            estado.rock_pickups.append(dict(pos, type="rock"))
        elif kind == "scrap":
            estado.scrap_pickups.append(dict(pos, type="scrap"))
        elif kind == "herb":
            estado.food_pickups.append(dict(pos, type="herb"))
        else:
            estado.ammo_pickups.append(pos)
    f = (MINE_W * MINE_H) / 90000.0
    ex, ey = MINE_INFO["exit"]
    lx, ly = MINE_INFO["lair"]
    used = set()
    plan = ((estado.wood_pickups, "tree", 70), (estado.rock_pickups, "rock", 45), (estado.scrap_pickups, "scrap", 40),
            (estado.food_pickups, "food", 36), (estado.ammo_pickups, "ammo", 3))
    for lst, kind, amount in plan:
        for _ in range(max(2, int(amount * f))):
            for __ in range(400):
                tx = random.randint(5, MINE_W - 6)
                ty = random.randint(5, MINE_H - 6)
                if (tx, ty) in used or not _mine_open(tx, ty):
                    continue
                if mundo.dist(tx * TILE, ty * TILE, ex, ey) < 6 * TILE or mundo.dist(tx * TILE, ty * TILE, lx, ly) < 9 * TILE:
                    continue
                used.add((tx, ty))
                pos = {"x": tx * TILE + 8, "y": ty * TILE + 8, "active": True, "timer": 0.0}
                if kind == "food":
                    pos["type"] = "herb" if random.random() < 0.5 else "berry"
                elif kind != "ammo":
                    pos["type"] = kind
                lst.append(pos)
                break

def clear_cave_area():
    """Quita árboles/rocas encima de la cueva y del portón de la fundidora."""
    makadewaa.ruin_hits.clear()
    for lst in (estado.wood_pickups, estado.rock_pickups, estado.scrap_pickups, estado.food_pickups, estado.ammo_pickups):
        for p in lst:
            tx_, ty_ = p["x"] // TILE, p["y"] // TILE
            if (abs(tx_ - CAVE_POS[0]) <= 2 and abs(ty_ - CAVE_POS[1]) <= 2) or \
                    (abs(tx_ - fundidora.FOUNDRY_POS[0]) <= 3 and abs(ty_ - fundidora.FOUNDRY_POS[1]) <= 3) or \
                    (abs(tx_ - refineria.REFINERY_POS[0]) <= 7 and abs(ty_ - refineria.REFINERY_POS[1]) <= 7) or \
                    (abs(tx_ - deshuesadero.JUNK_POS[0]) <= 3 and abs(ty_ - deshuesadero.JUNK_POS[1]) <= 3):                                          
                p["active"] = False
                p["timer"] = 1.0

# ── Zombis de la mina: siguen un "mapa de caminos" hacia el jugador ──
def update_mine_field(dt):
    
    if not estado.in_mine:
        return
    estado.mine_field_t -= dt
    if estado.mine_field_t > 0:
        return
    estado.mine_field_t = 0.25
    start = (int(estado.player.x // TILE), int(estado.player.y // TILE))
    RUIN = mundo.TILE_TYPE["ruin"]
    field = {start: 0}
    frontier = [start]
    depth = 0
    while frontier and depth < MINE_FIELD_DEPTH:
        depth += 1
        nxt = []
        for x, y in frontier:
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                x2, y2 = x + ddx, y + ddy
                if (x2, y2) in field:
                    continue
                if not (0 <= x2 < estado.WORLD_W and 0 <= y2 < estado.WORLD_H) or mundo.WORLD[y2][x2] == RUIN:
                    continue
                field[(x2, y2)] = depth
                nxt.append((x2, y2))
        frontier = nxt
    mine_field.clear()
    mine_field.update(field)


def mine_flow_dir(z):
    tx, ty = int(z.x // TILE), int(z.y // TILE)
    here = mine_field.get((tx, ty))
    if here is None or here == 0:
        return None
    best, bx, by = here, tx, ty
    for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        v = mine_field.get((tx + ddx, ty + ddy))
        if v is not None and v < best:
            best, bx, by = v, tx + ddx, ty + ddy
    if (bx, by) == (tx, ty):
        return None
    ox, oy = bx * TILE + 8 - z.x, by * TILE + 8 - z.y
    l = math.hypot(ox, oy) or 1
    return ox / l, oy / l


def mine_line_clear(x1, y1, x2, y2):
    """True si no hay pared entre los dos puntos (el zombi te ve)."""
    d = mundo.dist(x1, y1, x2, y2)
    if d > 22 * TILE:
        return False
    RUIN = mundo.TILE_TYPE["ruin"]
    steps = int(d // 8) + 1
    for i in range(1, steps):
        t = i / steps
        xx = int((x1 + (x2 - x1) * t) // TILE)
        yy = int((y1 + (y2 - y1) * t) // TILE)
        if not (0 <= xx < estado.WORLD_W and 0 <= yy < estado.WORLD_H) or mundo.WORLD[yy][xx] == RUIN:
            return False
    return True


def spawn_mine_zombie():
    if not mine_field or neri_jefe.lair["state"] == "sealed":
        return
    near = sum(1 for z in estado.zombies if not z.dead and mundo.dist(z.x, z.y, estado.player.x, estado.player.y) < 20 * TILE)
    if near >= MINE_ZOMBIE_NEAR_CAP:          # ya hay suficientes cerca de ti
        return
    ex, ey = MINE_INFO["exit"]
    for _ in range(80):
        tx = int(estado.player.x // TILE) + random.randint(-34, 34)
        ty = int(estado.player.y // TILE) + random.randint(-34, 34)
        if (tx, ty) not in mine_field:
            continue
        d = mundo.dist(tx * TILE, ty * TILE, estado.player.x, estado.player.y)
        if d < 14 * TILE or d > 34 * TILE:
            continue
        if mundo.dist(tx * TILE, ty * TILE, ex, ey) < 12 * TILE:    # la entrada es zona segura
            continue
        if mundo.tile_water(tx, ty):
            continue
        estado.zombies.append(entidades.Zombie(tx * TILE + 8, ty * TILE + 8, MINE_ZOMBIE_SPEED))
        return

# ── Murciélagos ──
def spawn_bat():
    if neri_jefe.lair["state"] == "sealed" or fundidora.map_kind != "mine":             
        return    
    for _ in range(60):
        tx = int(estado.player.x // TILE) + random.randint(-30, 30)
        ty = int(estado.player.y // TILE) + random.randint(-30, 30)
        if mundo.tile_solid(tx, ty):
            continue
        d = mundo.dist(tx * TILE, ty * TILE, estado.player.x, estado.player.y)
        if d < 12 * TILE or d > 30 * TILE:
            continue
        bats.append(Bat(tx * TILE + 8, ty * TILE + 8))
        return


def update_bats(dt):
    
    if estado.in_mine:
        estado.bat_spawn_timer -= dt
        if estado.bat_spawn_timer <= 0 and len(bats) < MINE_BAT_CAP:
            estado.bat_spawn_timer = MINE_BAT_EVERY
            spawn_bat()
    for b in bats:
        if b.dead:
            continue
        if b.hp <= 0:
            b.dead = True
            continue
        b.t += dt
        if b.cd > 0:
            b.cd -= dt
        if b.hit_flash > 0:
            b.hit_flash -= dt
        d = mundo.dist(estado.player.x, estado.player.y, b.x, b.y)
        if d > 45 * TILE:
            b.dead = True
            continue
        ax, ay = estado.player.x - b.x, estado.player.y - b.y
        l = math.hypot(ax, ay) or 1
        ax, ay = ax / l, ay / l
        if b.state == "flutter":
            b.angle += random.uniform(-5, 5) * dt
            vx, vy = math.cos(b.angle) * 28, math.sin(b.angle) * 28
            if d < 120 and b.cd <= 0:
                b.state = "dive"
                b.state_t = 2.5
        elif b.state == "dive":
            b.state_t -= dt
            ang = math.atan2(ay, ax) + math.sin(b.t * 9) * 0.6
            vx, vy = math.cos(ang) * 88, math.sin(ang) * 88
            if d < 11:
                if not estado.god_mode:
                    estado.player.hp = max(0, estado.player.hp - 7)
                    estado.log("¡Un murciélago te muerde!")
                b.state = "retreat"
                b.state_t = 1.2
            elif b.state_t <= 0:
                b.state = "flutter"
                b.cd = 2.0
        else:                                           # retreat
            b.state_t -= dt
            ang = math.atan2(-ay, -ax) + math.sin(b.t * 9) * 0.8
            vx, vy = math.cos(ang) * 75, math.sin(ang) * 75
            if b.state_t <= 0:
                b.state = "flutter"
                b.cd = 2.5
        nx, ny = b.x + vx * dt, b.y + vy * dt
        if not mundo.tile_solid(int(nx // TILE), int(ny // TILE)):
            b.x, b.y = nx, ny
        elif not mundo.tile_solid(int(nx // TILE), int(b.y // TILE)):
            b.x = nx
        elif not mundo.tile_solid(int(b.x // TILE), int(ny // TILE)):
            b.y = ny
        else:
            b.angle += math.pi * random.uniform(0.5, 1.5)
    bats[:] = [b for b in bats if not b.dead]


def draw_bat(surface, b):
    sx, sy = camara.world_to_screen(b.x, b.y)
    u = PIXEL_SCALE
    flap = int(b.t * 14) % 2
    col = (255, 255, 255) if b.hit_flash > 0 else (38, 30, 44)
    wing = 5 if flap else 3
    wy = -2 if flap else 0
    dibujo.px(surface, sx - 1 * u, sy - 1 * u, 3 * u, 3 * u, col)
    dibujo.px(surface, sx - (wing + 1) * u, sy + wy * u, wing * u, 2 * u, col)
    dibujo.px(surface, sx + 2 * u, sy + wy * u, wing * u, 2 * u, col)
    dibujo.px(surface, sx - 1 * u, sy - 1 * u, 1 * u, 1 * u, (200, 60, 60))
    
def draw_hatch(surface, wx, wy, lit):
    """Trampilla grande de 3x3 tiles. lit=True: vista desde dentro (entra luz y se ve una escalera)."""
    sx, sy = camara.world_to_screen(wx, wy)
    u = PIXEL_SCALE
    x0, y0 = sx - 24 * u, sy - 24 * u
    dibujo.px(surface, x0, y0, 48 * u, 48 * u, PALETTE["rock_dark"])               # marco de piedra
    dibujo.px(surface, x0 + 3 * u, y0 + 3 * u, 42 * u, 42 * u, PALETTE["wall_dark"])
    if lit:
        dibujo.px(surface, x0 + 6 * u, y0 + 6 * u, 36 * u, 36 * u, (170, 158, 104))   # luz del día
        dibujo.px(surface, x0 + 16 * u, y0 + 6 * u, 3 * u, 36 * u, PALETTE["wall"])
        dibujo.px(surface, x0 + 29 * u, y0 + 6 * u, 3 * u, 36 * u, PALETTE["wall"])
        for i in range(6):
            dibujo.px(surface, x0 + 16 * u, y0 + (9 + i * 6) * u, 16 * u, 2 * u, PALETTE["wall"])
    else:
        dibujo.px(surface, x0 + 6 * u, y0 + 6 * u, 36 * u, 36 * u, PALETTE["door_plank"])   # puertas de madera
        for i in range(1, 6):
            dibujo.px(surface, x0 + (6 + i * 6) * u, y0 + 6 * u, 1 * u, 36 * u, PALETTE["door_dark"])
        dibujo.px(surface, x0 + 23 * u, y0 + 6 * u, 2 * u, 36 * u, (10, 10, 10))
        dibujo.px(surface, x0 + 6 * u, y0 + 14 * u, 36 * u, 3 * u, PALETTE["gun_dark"])
        dibujo.px(surface, x0 + 6 * u, y0 + 31 * u, 36 * u, 3 * u, PALETTE["gun_dark"])
        dibujo.px(surface, x0 + 19 * u, y0 + 22 * u, 3 * u, 4 * u, PALETTE["gun_metal"])
        dibujo.px(surface, x0 + 26 * u, y0 + 22 * u, 3 * u, 4 * u, PALETTE["gun_metal"])
    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 250)
    col = (int(120 + 124 * pulse), int(110 + 114 * pulse), int(30 + 44 * pulse))
    pygame.draw.rect(surface, col, (round(x0 - 2 * u), round(y0 - 2 * u), 52 * u, 52 * u), max(2, u))


def draw_cave_arrow(surface):
    """Flecha en el borde de la pantalla que apunta a la mina (solo en la isla)."""
    if estado.in_mine or not CAVE_ARROW:
        return
    wx, wy = CAVE_POS[0] * TILE + 8, CAVE_POS[1] * TILE + 8
    sx, sy = camara.world_to_screen(wx, wy)
    m = 40
    if m < sx < SCREEN_W - m and m < sy < SCREEN_H - m:
        return                                    # ya se ve en pantalla
    dx, dy = sx - SCREEN_W / 2, sy - SCREEN_H / 2
    l = math.hypot(dx, dy) or 1
    dx, dy = dx / l, dy / l
    kx = (SCREEN_W / 2 - m) / abs(dx) if abs(dx) > 1e-6 else 1e9
    ky = (SCREEN_H / 2 - m) / abs(dy) if abs(dy) > 1e-6 else 1e9
    k = min(kx, ky)
    ax, ay = SCREEN_W / 2 + dx * k, SCREEN_H / 2 + dy * k
    s = max(1, UI_S)
    tip = (ax + dx * 14 * s, ay + dy * 14 * s)
    left = (ax - dx * 8 * s - dy * 10 * s, ay - dy * 8 * s + dx * 10 * s)
    right = (ax - dx * 8 * s + dy * 10 * s, ay - dy * 8 * s - dx * 10 * s)
    pygame.draw.polygon(surface, (244, 224, 74), [tip, left, right])
    tiles = int(mundo.dist(estado.player.x, estado.player.y, wx, wy) // TILE)
    t = FONT_SMALL.render(f"Mina {tiles}", True, (244, 224, 74))
    surface.blit(t, (ax - dx * 26 * s - t.get_width() / 2, ay - dy * 26 * s - t.get_height() / 2))
    
def draw_mine_extras(surface):
    if estado.in_mine:
        lx, ly = MINE_INFO["lair"]                       # guarida de Neri
        sx, sy = camara.world_to_screen(lx, ly)
        u = PIXEL_SCALE
        pygame.draw.circle(surface, (30, 24, 20), (int(sx), int(sy)), int(30 * u))
        pygame.draw.circle(surface, (52, 44, 34), (int(sx), int(sy)), int(30 * u), max(1, u))
        for ox_, oy_ in ((-9, -5), (7, -8), (-4, 8), (10, 6)):
            dibujo.px(surface, sx + ox_ * u, sy + oy_ * u, 5 * u, 2 * u, (200, 192, 170))
        tx_, ty_ = MINE_INFO["exit"]
        msg = "E: salir de " + {"mine": "la mina", "foundry": "la fundidora", "refinery": "la refinería",
                                "junkyard": "el deshuesadero"}.get(fundidora.map_kind, "aquí")        
    else:
        tx_, ty_ = CAVE_POS[0] * TILE + 8, CAVE_POS[1] * TILE + 8
        msg = "E: entrar a la mina"
    draw_hatch(surface, tx_, ty_, estado.in_mine)
    if mundo.dist(estado.player.x, estado.player.y, tx_, ty_) < INTERACT_RANGE * 1.5:
        sx, sy = camara.world_to_screen(tx_, ty_)
        t = FONT_SMALL.render(msg, True, (244, 224, 74))
        surface.blit(t, (sx - t.get_width() // 2, sy - 28 * PIXEL_SCALE - t.get_height()))
    for b in bats:
        draw_bat(surface, b)
    neri_jefe.draw_neri_all(surface)
    refineria.draw_dynamite(surface)
    ayudantes.draw_girl(surface)
    ayudantes.draw_elder(surface)
