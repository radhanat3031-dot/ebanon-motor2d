"""Ruido y generación del mapa de la isla.

Salió de ebanon.py (original), alrededor de las líneas 370-800.
"""

import math
import random
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global barco, deshuesadero, estado, fundidora, refineria
    from mapas import barco, deshuesadero, fundidora, refineria
    from nucleo import estado


# ----------------------------------------------------------------------------
# 2. RUIDO / GENERACIÓN DE MUNDO
# ----------------------------------------------------------------------------

# Diccionario de tipos de tile (no confundir con TILE = tamaño en píxeles)
TILE_TYPE = {
    "ground": 0,   # tierra
    "hill":   1,   # colina
    "road":   2,   # camino
    "water":  3,   # agua
    "ruin":   4,   # ruina/roca
    "cave":   5,   # entrada/salida de la mina
}

def hash_noise(x, y):
    n = math.sin(x * 127.1 + y * 311.7) * 43758.5453
    return n - math.floor(n)

def smooth_noise(x, y):
    xi, yi = math.floor(x), math.floor(y)
    xf, yf = x - xi, y - yi
    v00 = hash_noise(xi, yi)
    v10 = hash_noise(xi + 1, yi)
    v01 = hash_noise(xi, yi + 1)
    v11 = hash_noise(xi + 1, yi + 1)
    i1 = v00 + (v10 - v00) * xf
    i2 = v01 + (v11 - v01) * xf
    return i1 + (i2 - i1) * yf

def gen_world():
    seed = (int(estado.WORLD_SEED_X * 1000000) ^ int(estado.WORLD_SEED_Y * 1000000)) & 0xFFFFFFFF
    rng = random.Random(seed)

    w = [[0 for _ in range(estado.WORLD_W)] for __ in range(estado.WORLD_H)]
    cx, cy = estado.WORLD_CENTER
    radius = estado.WORLD_RADIUS

    mask = [[False for _ in range(estado.WORLD_W)] for __ in range(estado.WORLD_H)]
    left_bias_strength = 0.10

    # --- máscara base ---
    for ty in range(estado.WORLD_H):
        for tx in range(estado.WORLD_W):
            dx = tx - cx
            dy = ty - cy
            d = math.hypot(dx, dy)
            edge_noise = smooth_noise(tx * 0.08 + estado.WORLD_SEED_X,
                                      ty * 0.08 + estado.WORLD_SEED_Y) * 0.6
            if tx < cx:
                left_factor = 1.0 - (tx / max(1, cx))
                bias = left_bias_strength * left_factor
            else:
                bias = 0.0
            threshold = radius * (0.85 + edge_noise * 0.4) * (1.0 + bias)
            mask[ty][tx] = d <= threshold

    # --- erosión ---
    def erode_mask(m, iterations=2):
        H, W = estado.WORLD_H, estado.WORLD_W
        for _ in range(iterations):
            new = [row[:] for row in m]
            for y in range(H):
                for x in range(W):
                    if m[y][x]:
                        for dy in (-1,0,1):
                            for dx in (-1,0,1):
                                ny, nx = y+dy, x+dx
                                if 0 <= ny < H and 0 <= nx < W and not m[ny][nx]:
                                    new[y][x] = False
                                    break
            m = new
        return m

    mask = erode_mask(mask, iterations=2)

    # --- isla central ---
    from collections import deque
    island = [[False for _ in range(estado.WORLD_W)] for __ in range(estado.WORLD_H)]
    sx, sy = int(cx), int(cy)
    if mask[sy][sx]:
        island[sy][sx] = True
        q = deque([(sx, sy)])
        while q:
            x, y = q.popleft()
            for ddx, ddy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x+ddx, y+ddy
                if 0 <= nx < estado.WORLD_W and 0 <= ny < estado.WORLD_H and mask[ny][nx] and not island[ny][nx]:
                    island[ny][nx] = True
                    q.append((nx, ny))
        mask = island

    # --- tiles base ---
    for ty in range(estado.WORLD_H):
        for tx in range(estado.WORLD_W):
            if not mask[ty][tx]:
                w[ty][tx] = TILE_TYPE["water"]
                continue
            n  = smooth_noise(tx * 0.12 + estado.WORLD_SEED_X, ty * 0.12 + estado.WORLD_SEED_Y)
            n2 = smooth_noise(tx * 0.05 + 50 + estado.WORLD_SEED_X, ty * 0.05 + 50 + estado.WORLD_SEED_Y)
            if n < 0.18:
                t = TILE_TYPE["ground"]
            elif n2 > 0.72 or n > 0.62:
                t = TILE_TYPE["hill"]
            else:
                t = TILE_TYPE["ground"]
            road_noise = smooth_noise(tx * 0.2 + 200 + estado.WORLD_SEED_X, ty * 0.2 + 200 + estado.WORLD_SEED_Y)
            if road_noise > 0.78 and rng.random() < 0.02:
                t = TILE_TYPE["road"]
            w[ty][tx] = t

    # --- ríos ---
    def carve_river(sx, sy, max_len=600, radius=1):
        x, y = sx + 0.5, sy + 0.5
        for i in range(max_len):
            tx, ty = int(x), int(y)
            if tx < 0 or ty < 0 or tx >= estado.WORLD_W or ty >= estado.WORLD_H:
                break
            for dy in range(-radius, radius+1):
                for dx in range(-radius, radius+1):
                    nx, ny = tx+dx, ty+dy
                    if 0 <= nx < estado.WORLD_W and 0 <= ny < estado.WORLD_H:
                        w[ny][nx] = TILE_TYPE["water"]
            gx = smooth_noise((x+1)*0.1+estado.WORLD_SEED_X, y*0.1+estado.WORLD_SEED_Y) - \
                 smooth_noise((x-1)*0.1+estado.WORLD_SEED_X, y*0.1+estado.WORLD_SEED_Y)
            gy = smooth_noise(x*0.1+estado.WORLD_SEED_X, (y+1)*0.1+estado.WORLD_SEED_Y) - \
                 smooth_noise(x*0.1+estado.WORLD_SEED_X, (y-1)*0.1+estado.WORLD_SEED_Y)
            dirx = gx + (tx - cx)*0.01
            diry = gy + (ty - cy)*0.01
            L = math.hypot(dirx, diry) or 1
            x -= dirx/L*0.8
            y -= diry/L*0.8
            if not mask[ty][tx]:
                break

    # --- lagos ---
    def carve_lake(cx, cy, rx=10, ry=6):
        """Genera un lago ovalado/deforme en (cx,cy)."""
        for dy in range(-ry, ry+1):
            for dx in range(-rx, rx+1):
                # fórmula de elipse
                val = (dx*dx)/(rx*rx) + (dy*dy)/(ry*ry)
                # añade ruido para deformar el borde
                jitter = smooth_noise((cx+dx) * 0.15 + estado.WORLD_SEED_X,
                                      (cy+dy) * 0.15 + estado.WORLD_SEED_Y) * 0.4
                if val <= 1.0 + jitter:
                    tx, ty = cx + dx, cy + dy
                    if 0 <= tx < estado.WORLD_W and 0 <= ty < estado.WORLD_H:
                        w[ty][tx] = TILE_TYPE["water"]


    # fuentes de ríos
    sources = []
    for _ in range(rng.randint(1,3)):
        for tries in range(200):
            rx = rng.randint(int(cx - radius*0.6), int(cx + radius*0.6))
            ry = rng.randint(int(cy - radius*0.6), int(cy + radius*0.6))
            if 0 <= rx < estado.WORLD_W and 0 <= ry < estado.WORLD_H and mask[ry][rx] and w[ry][rx] == TILE_TYPE["hill"]:
                sources.append((rx, ry))
                break
    for sx, sy in sources:
        carve_river(sx, sy, max_len=500, radius=1)

    # --- lagos aleatorios ---
    for _ in range(rng.randint(2,4)):
        lx = rng.randint(int(cx - radius*0.7), int(cx + radius*0.7))
        ly = rng.randint(int(cy - radius*0.7), int(cy + radius*0.7))
        if mask[ly][lx] and w[ly][lx] in (TILE_TYPE["ground"], TILE_TYPE["hill"]):
            carve_lake(lx, ly, rx=rng.randint(6,12), ry=rng.randint(4,10))
            
    # --- ciudad en ruinas: barrios con cuadras, calles por tramos y edificios rotos ---
    T_RUIN, T_ROAD, T_GROUND, T_WATER = TILE_TYPE["ruin"], TILE_TYPE["road"], TILE_TYPE["ground"], TILE_TYPE["water"]
    BLOCK, STREET = 9, 2            # lado de cada cuadra / ancho de calle (en tiles)
    N_DISTRICTS = (4, 5)            # ← cuántos barrios (mín, máx)
    N_LONE_HOUSES = (5, 9)          # ← casas sueltas fuera de los barrios

    def land(x, y):
        return 0 <= x < estado.WORLD_W and 0 <= y < estado.WORLD_H and mask[y][x] and w[y][x] != T_WATER

    def building(x0, y0, bw, bh):
        for yy in range(y0, y0 + bh):
            for xx in range(x0, x0 + bw):
                edge = xx in (x0, x0 + bw - 1) or yy in (y0, y0 + bh - 1)
                if land(xx, yy) and w[yy][xx] != T_ROAD:
                    if edge and rng.random() < 0.78:
                        w[yy][xx] = T_RUIN
                    elif not edge and rng.random() < 0.05:
                        w[yy][xx] = T_RUIN
        for _d in range(2):                           # huecos = puertas
            side = rng.randrange(4)
            if side == 0:
                xx, yy = x0 + rng.randint(1, bw - 2), y0
            elif side == 1:
                xx, yy = x0 + rng.randint(1, bw - 2), y0 + bh - 1
            elif side == 2:
                xx, yy = x0, y0 + rng.randint(1, bh - 2)
            else:
                xx, yy = x0 + bw - 1, y0 + rng.randint(1, bh - 2)
            if land(xx, yy) and w[yy][xx] == T_RUIN:
                w[yy][xx] = T_GROUND

    centers_d = []
    want_d = rng.randint(*N_DISTRICTS)
    for _try in range(500):
        if len(centers_d) >= want_d:
            break
        cols, rows = rng.randint(2, 4), rng.randint(2, 4)
        W_ = cols * (BLOCK + STREET) + STREET
        H_ = rows * (BLOCK + STREET) + STREET
        ox_ = rng.randint(int(cx - radius * 0.9), int(cx + radius * 0.9) - W_)
        oy_ = rng.randint(int(cy - radius * 0.9), int(cy + radius * 0.9) - H_)
        if ox_ - 12 <= cx <= ox_ + W_ + 12 and oy_ - 12 <= cy <= oy_ + H_ + 12:
            continue                                  # no tapar el punto de inicio
        mx, my = ox_ + W_ / 2, oy_ + H_ / 2
        if any(abs(mx - a) < 50 and abs(my - b) < 50 for a, b in centers_d):
            continue
        pts = [(ox_ + i, oy_ + j) for i in range(0, W_, 4) for j in range(0, H_, 4)]
        if sum(1 for (a, b) in pts if land(a, b)) < 0.85 * len(pts):
            continue                                  # casi todo debe ser tierra
        centers_d.append((mx, my))
        for ri in range(rows):                        # edificios y lotes vacíos
            for ci in range(cols):
                bx = ox_ + STREET + ci * (BLOCK + STREET)
                by = oy_ + STREET + ri * (BLOCK + STREET)
                if rng.random() < 0.78:
                    bw, bh = rng.randint(5, BLOCK - 1), rng.randint(5, BLOCK - 1)
                    building(bx + rng.randint(0, BLOCK - bw), by + rng.randint(0, BLOCK - bh), bw, bh)
                else:
                    for yy in range(by, by + BLOCK):
                        for xx in range(bx, bx + BLOCK):
                            if land(xx, yy) and rng.random() < 0.06:
                                w[yy][xx] = T_RUIN
        for ri in range(rows + 1):                    # calles horizontales (por tramos)
            for ci in range(cols):
                if rng.random() < (0.5 if ri in (0, rows) else 0.8):
                    xs = ox_ + ci * (BLOCK + STREET)
                    xe = xs + BLOCK + STREET + (STREET if ci == cols - 1 else 0)
                    for xx in range(xs, xe):
                        for k in range(STREET):
                            yy = oy_ + ri * (BLOCK + STREET) + k
                            if land(xx, yy) and w[yy][xx] != T_RUIN:
                                w[yy][xx] = T_ROAD
        for ci in range(cols + 1):                    # calles verticales (por tramos)
            for ri in range(rows):
                if rng.random() < (0.5 if ci in (0, cols) else 0.8):
                    ys = oy_ + ri * (BLOCK + STREET)
                    ye = ys + BLOCK + STREET + (STREET if ri == rows - 1 else 0)
                    for yy in range(ys, ye):
                        for k in range(STREET):
                            xx = ox_ + ci * (BLOCK + STREET) + k
                            if land(xx, yy) and w[yy][xx] != T_RUIN:
                                w[yy][xx] = T_ROAD
        for _s in range(rng.randint(1, 3)):           # calles que salen del barrio, con huecos
            side = rng.randrange(4)
            if side == 0:
                sx0, sy0, ddx, ddy = ox_ - 1, oy_ + rng.randint(0, H_ - STREET), -1, 0
            elif side == 1:
                sx0, sy0, ddx, ddy = ox_ + W_, oy_ + rng.randint(0, H_ - STREET), 1, 0
            elif side == 2:
                sx0, sy0, ddx, ddy = ox_ + rng.randint(0, W_ - STREET), oy_ - 1, 0, -1
            else:
                sx0, sy0, ddx, ddy = ox_ + rng.randint(0, W_ - STREET), oy_ + H_, 0, 1
            for i in range(rng.randint(12, 30)):
                if (i // 4) % 2 == 1 and rng.random() < 0.6:
                    continue
                for k in range(STREET):
                    xx = sx0 + ddx * i + (k if ddx == 0 else 0)
                    yy = sy0 + ddy * i + (k if ddy == 0 else 0)
                    if land(xx, yy) and w[yy][xx] != T_RUIN:
                        w[yy][xx] = T_ROAD

    lone = 0
    want_l = rng.randint(*N_LONE_HOUSES)
    for _try in range(400):
        if lone >= want_l:
            break
        bw, bh = rng.randint(5, 8), rng.randint(5, 8)
        hx = rng.randint(int(cx - radius * 0.9), int(cx + radius * 0.9))
        hy = rng.randint(int(cy - radius * 0.9), int(cy + radius * 0.9))
        if math.hypot(hx - cx, hy - cy) < 20:
            continue
        if not all(land(hx + i, hy + j) and w[hy + j][hx + i] not in (T_RUIN, T_ROAD)
                   for i in (0, bw // 2, bw - 1) for j in (0, bh // 2, bh - 1)):
            continue
        building(hx, hy, bw, bh)
        lone += 1
            
    # --- entrada de la mina ---
    cave_x, cave_y = int(cx) + 30, int(cy)
    for _ in range(3000):
        ctx = rng.randint(int(cx - radius * 0.9), int(cx + radius * 0.9))
        cty = rng.randint(int(cy - radius * 0.9), int(cy + radius * 0.9))
        d = math.hypot(ctx - cx, cty - cy)
        if d < 25 or d > radius * 0.9:
            continue
        ok = True
        for yy in range(cty - 2, cty + 3):
            for xx in range(ctx - 2, ctx + 3):
                if not (0 <= xx < estado.WORLD_W and 0 <= yy < estado.WORLD_H) or not mask[yy][xx] \
                        or w[yy][xx] in (TILE_TYPE["water"], TILE_TYPE["ruin"]):
                    ok = False
        if ok:
            cave_x, cave_y = ctx, cty
            break
    for yy in range(cave_y - 1, cave_y + 2):
        for xx in range(cave_x - 1, cave_x + 2):
            if 0 <= xx < estado.WORLD_W and 0 <= yy < estado.WORLD_H:
                mask[yy][xx] = True
                w[yy][xx] = TILE_TYPE["ground"]
    w[cave_y][cave_x] = TILE_TYPE["cave"]
    CAVE_POS[0], CAVE_POS[1] = cave_x, cave_y
    
    # --- barco varado: Esperanza ---
    boat_spot = None
    for _try in range(6000):
        lx_ = rng.randint(3, estado.WORLD_W - 4)
        ly_ = rng.randint(4, estado.WORLD_H - 5)
        if not mask[ly_][lx_] or w[ly_][lx_] in (T_WATER, T_RUIN, T_ROAD, TILE_TYPE["cave"]):
            continue
        if math.hypot(lx_ - cave_x, ly_ - cave_y) < 25 or math.hypot(lx_ - cx, ly_ - cy) < 30:
            continue
        for sd in (1, -1):
            bx_, by_ = lx_, ly_ + 2 * sd
            wet = sum(1 for yy in range(by_ - 1, by_ + 2) for xx in range(bx_ - 2, bx_ + 3)
                      if not (0 <= xx < estado.WORLD_W and 0 <= yy < estado.WORLD_H) or not mask[yy][xx] or w[yy][xx] == T_WATER)
            shore = sum(1 for xx in range(bx_ - 2, bx_ + 3)
                        if 0 <= xx < estado.WORLD_W and mask[ly_][xx] and w[ly_][xx] not in (T_WATER, T_RUIN))
            if wet >= 11 and shore >= 4:
                boat_spot = (bx_, by_)
                break
        if boat_spot:
            break
    if boat_spot is None:                     # plan B: la primera orilla que se encuentre
        for ty_ in range(5, estado.WORLD_H - 6):
            for tx_ in range(5, estado.WORLD_W - 6):
                if mask[ty_][tx_] and w[ty_][tx_] not in (T_WATER, T_RUIN) and not mask[ty_ + 1][tx_]:
                    boat_spot = (tx_, ty_ + 2)
                    break
            if boat_spot:
                break
    if boat_spot is None:
        boat_spot = (cave_x + 6, cave_y)
    for yy in range(boat_spot[1] - 1, boat_spot[1] + 2):          # el barco flota en agua
        for xx in range(boat_spot[0] - 2, boat_spot[0] + 3):
            if 0 <= xx < estado.WORLD_W and 0 <= yy < estado.WORLD_H:
                mask[yy][xx] = True
                w[yy][xx] = T_WATER
    barco.BOAT_POS[0], barco.BOAT_POS[1] = boat_spot[0] * TILE + 8, boat_spot[1] * TILE + 8
    
    # --- portón de la fundidora ---
    fx_, fy_ = int(cx) - 30, int(cy)
    for _try in range(4000):
        gx = rng.randint(int(cx - radius * 0.85), int(cx + radius * 0.85))
        gy = rng.randint(int(cy - radius * 0.85), int(cy + radius * 0.85))
        if math.hypot(gx - cx, gy - cy) < 28 or math.hypot(gx - cave_x, gy - cave_y) < 30 \
                or math.hypot(gx - boat_spot[0], gy - boat_spot[1]) < 25:
            continue
        if not all(0 <= gx + i < estado.WORLD_W and 0 <= gy + j < estado.WORLD_H and mask[gy + j][gx + i]
                   and w[gy + j][gx + i] not in (T_WATER, T_RUIN, T_ROAD)
                   for i in range(-3, 4) for j in range(-3, 4)):
            continue
        fx_, fy_ = gx, gy
        break
    for j in range(-1, 2):
        for i in range(-1, 2):
            mask[fy_ + j][fx_ + i] = True
            w[fy_ + j][fx_ + i] = T_GROUND
    fundidora.FOUNDRY_POS[0], fundidora.FOUNDRY_POS[1] = fx_, fy_    
    
    # --- complejo de la refinería: anillo de escombros (hace falta dinamita) ---
    rx_, ry_ = int(cx) + 30, int(cy) + 30
    for _try in range(6000):
        gx = rng.randint(8, estado.WORLD_W - 9)
        gy = rng.randint(8, estado.WORLD_H - 9)
        if math.hypot(gx - cx, gy - cy) < 35 or math.hypot(gx - cave_x, gy - cave_y) < 30 \
                or math.hypot(gx - boat_spot[0], gy - boat_spot[1]) < 25 \
                or math.hypot(gx - fx_, gy - fy_) < 30:
            continue
        if not all(mask[gy + j][gx + i] and w[gy + j][gx + i] not in (T_WATER, T_RUIN, T_ROAD)
                   for i in range(-7, 8) for j in range(-7, 8)):
            continue
        rx_, ry_ = gx, gy
        break
    refineria.REFINERY_BARRIER.clear()
    for j in range(-6, 7):
        for i in range(-6, 7):
            xx, yy = rx_ + i, ry_ + j
            if not (0 <= xx < estado.WORLD_W and 0 <= yy < estado.WORLD_H):
                continue
            mask[yy][xx] = True
            if max(abs(i), abs(j)) <= 4:
                w[yy][xx] = T_GROUND
            else:
                w[yy][xx] = T_RUIN
                refineria.REFINERY_BARRIER.add((xx, yy))
    refineria.REFINERY_POS[0], refineria.REFINERY_POS[1] = rx_, ry_    
    
    # --- portón del deshuesadero (a la vista, sin llave) ---
    jx_, jy_ = int(cx) - 30, int(cy) - 30
    for _try in range(6000):
        gx = rng.randint(6, estado.WORLD_W - 7)
        gy = rng.randint(6, estado.WORLD_H - 7)
        if math.hypot(gx - cx, gy - cy) < 30 or math.hypot(gx - cave_x, gy - cave_y) < 30 \
                or math.hypot(gx - boat_spot[0], gy - boat_spot[1]) < 25 \
                or math.hypot(gx - fx_, gy - fy_) < 30 or math.hypot(gx - rx_, gy - ry_) < 30:
            continue
        if not all(mask[gy + j][gx + i] and w[gy + j][gx + i] not in (T_WATER, T_RUIN, T_ROAD)
                   for i in range(-3, 4) for j in range(-3, 4)):
            continue
        jx_, jy_ = gx, gy
        break
    for j in range(-1, 2):
        for i in range(-1, 2):
            mask[jy_ + j][jx_ + i] = True
            w[jy_ + j][jx_ + i] = T_GROUND
    deshuesadero.JUNK_POS[0], deshuesadero.JUNK_POS[1] = jx_, jy_

    # copiar máscara y devolver
    for ty in range(estado.WORLD_H):
        for tx in range(estado.WORLD_W):
            estado.WORLD_MASK[ty][tx] = mask[ty][tx]
    return w
def tile_at(tx, ty):
    if tx < 0 or ty < 0 or tx >= estado.WORLD_W or ty >= estado.WORLD_H:
        return TILE_TYPE["ruin"] if estado.in_mine else TILE_TYPE["water"]    
    if not estado.WORLD_MASK[ty][tx]:
        return TILE_TYPE["water"]
    return WORLD[ty][tx]

def tile_solid(tx, ty):
    return tile_at(tx, ty) == TILE_TYPE["ruin"]

def tile_water(tx, ty):
    return tile_at(tx, ty) == TILE_TYPE["water"]

def dist(x1, y1, x2, y2):
    return math.hypot(x1 - x2, y1 - y2)
