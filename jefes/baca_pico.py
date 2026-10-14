"""Objetos únicos de Baca: el zapapico y su golpe en cono.

Salió de ebanon.py (original), alrededor de las líneas 3304-9166.
"""

import math
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global almacen, ayudantes, baca_jefe, camara, colision
    global estado, hombre_reloj, makadewaa, mundo, neri_jefe
    global refineria
    from jefes import baca_jefe, hombre_reloj, makadewaa, neri_jefe
    from mapas import refineria
    from npcs import ayudantes
    from nucleo import estado, mundo
    from sistemas import almacen, camara, colision


# ── OBJETOS ÚNICOS DE BACA ──
LAMP_RANGE_MULT = 1.5        # cuánto más lejos llega el cono con la lámpara
LAMP_STRENGTH_BONUS = 0.25   # cuánta luz extra da la lámpara
WEAPON_LABELS["baca_pick"] = "ZAPAPICO DE BACA"
MELEE_DAMAGE["baca_pick"] = 45
broken_ruins = []            # ruinas rotas (se guardan con la partida)

# ── GOLPE EN CONO DEL ZAPAPICO DE BACA ──
BACA_PICK_RANGE = 44          # ← ALCANCE del golpe (el cono de Baca usa 54; el puño normal 20)
BACA_PICK_ARC = 0.9           # ← mitad de la apertura del cono en radianes (0.9 ≈ 103° en total)
BACA_PICK_COOLDOWN = 0.45      # pausa mínima entre golpes (además de la estamina)
BACA_PICK_ANIM = 0.28         # duración de la animación del golpe
BACA_PICK_BEAR_HITS = 2       # golpes que aguanta un osito débil
BACA_PICK_SPILLS_CHEST = True # True: al destrozar un almacén, su contenido cae al suelo (la estructura no devuelve nada)


def in_pick_cone(x, y, pad=0):
    """True si el punto (x, y) está dentro del cono del zapapico. pad = tamaño del objetivo."""
    dx, dy = x - estado.player.x, y - estado.player.y
    d = math.hypot(dx, dy)
    if d > BACA_PICK_RANGE + pad:
        return False
    if d < 6:
        return True
    diff = abs((math.atan2(dy, dx) - math.atan2(estado.player.aim_y, estado.player.aim_x) + math.pi) % (2 * math.pi) - math.pi)
    return diff <= BACA_PICK_ARC


def baca_pick_swing():
    if estado.player.attack_cooldown > 0:
        return
    # Contra: cada golpe gasta estamina y un poco de hambre
    if not baca_pick_pay():
        estado.player.attack_cooldown = 0.3
        return
    estado.player.attack_cooldown = BACA_PICK_COOLDOWN

    ang = math.atan2(estado.player.aim_y, estado.player.aim_x)
    pygame.mixer.Channel(21).play(bear_swipe_sound)
    estado.player.action_anim = {"type": "pick", "t": BACA_PICK_ANIM, "total": BACA_PICK_ANIM,
                          "dx": 0, "dy": 0, "ang": ang}

    # 1) Zombis: mueren todos los que estén dentro del cono
    kills = 0
    for z in estado.zombies:
        if not z.dead and in_pick_cone(z.x, z.y, 6):
            z.hp = 0
            z.dead = True
            kills += 1
    if kills:
        estado.log(f"Zombis aplastados: {kills}.")

    # 2) Murciélagos
    for bt in bats:
        if not bt.dead and in_pick_cone(bt.x, bt.y, 4):
            bt.hp = 0
            bt.dead = True

    # 3) Árboles: caen de un golpe pero no dan madera
    trees = 0
    for w in estado.wood_pickups:
        if w["active"] and in_pick_cone(w["x"], w["y"], 8):
            w["active"] = False
            w["timer"] = RESPAWN_WOOD
            w["hits"] = 0
            trees += 1
    if trees:
        pygame.mixer.Channel(5).play(down_three)
        estado.log("Solo quedaron astillas. Es demasiado poderoso.")

    # 4) Estructuras tuyas: se rompen sin devolver nada
    smashed = 0
    for st in list(estado.structures):
        if in_pick_cone(st["x"], st["y"], 8):
            if estado.active_chest is st:
                almacen.close_storage()
            if st["type"] == "chest" and BACA_PICK_SPILLS_CHEST:
                items = {k: n for k, n in st.get("store", {}).items() if n > 0}
                if items:
                    estado.drops.append({"x": st["x"], "y": st["y"], "kind": "debris", "items": items})
            estado.structures.remove(st)
            smashed += 1
    if smashed:
        estado.log(f"Estructuras destrozadas: {smashed}. No queda nada que recuperar.")

    # 5) Osos: los débiles aguantan 2 golpes; el jefe recibe el daño normal
    for br in estado.bears:
        if not br.dead and in_pick_cone(br.x, br.y, 6 * br.size):
            if br.kind == "weak":
                makadewaa.hit_bear(br, br.max_hp / BACA_PICK_BEAR_HITS)
            else:
                makadewaa.hit_bear(br, MELEE_DAMAGE["baca_pick"])
                
    if neri_jefe.neri and in_pick_cone(neri_jefe.neri.x, neri_jefe.neri.y, 6 * neri_jefe.neri.size):
        neri_jefe.hit_neri(neri_jefe.NERI_PICK_DAMAGE, neri_jefe.NERI_PICK_STUN)        
    for p in neri_jefe.neri_pups:
        if not p.dead and in_pick_cone(p.x, p.y, 6):
            neri_jefe.hit_pup(p, MELEE_DAMAGE["baca_pick"])

    # 6) Jefes y perros de Baca: daño normal del zapapico
    if estado.boss and in_pick_cone(estado.boss.x, estado.boss.y, 12):
        hombre_reloj.hit_boss(MELEE_DAMAGE["baca_pick"])
    if baca_jefe.baca and in_pick_cone(baca_jefe.baca.x, baca_jefe.baca.y, 6 * baca_jefe.baca.size):
        baca_jefe.hit_baca(MELEE_DAMAGE["baca_pick"])
    for g in list(baca_jefe.baca_dogs):
        if not g.dead and in_pick_cone(g.x, g.y, 6):
            baca_jefe.hit_baca_dog(g, MELEE_DAMAGE["baca_pick"])


def draw_pick_swing(surface, x, y, a):
    """Animación: el cono se ilumina y el zapapico barre de lado a lado."""
    sx, sy = camara.world_to_screen(x, y)
    R = BACA_PICK_RANGE * PIXEL_SCALE
    ang = a["ang"]
    fade = max(0.0, a["t"] / a["total"])
    p = 1 - fade
    layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    pts = makadewaa.cone_points(sx, sy, ang, BACA_PICK_ARC, R)
    pygame.draw.polygon(layer, (255, 230, 200, int(80 * fade)), pts)
    pygame.draw.polygon(layer, (255, 200, 120, int(230 * fade)), pts, 2)
    cur = ang - BACA_PICK_ARC + 2 * BACA_PICK_ARC * p
    ex, ey = sx + math.cos(cur) * R * 0.85, sy + math.sin(cur) * R * 0.85
    pygame.draw.line(layer, (110, 90, 60, 255), (sx, sy), (ex, ey), max(2, 2 * PIXEL_SCALE))
    pw = 5 * PIXEL_SCALE
    pygame.draw.line(layer, (170, 170, 160, 255), (ex - math.sin(cur) * pw, ey + math.cos(cur) * pw),
                     (ex + math.sin(cur) * pw, ey - math.cos(cur) * pw), max(2, 3 * PIXEL_SCALE))
    surface.blit(layer, (0, 0))

def baca_pick_interact():
    """Con el zapapico de Baca, E rompe de un golpe la roca o la ruina que tengas delante.
    Devuelve True si había algo que romper."""
    rock = None
    for r in estado.rock_pickups:
        if r["active"] and mundo.dist(estado.player.x, estado.player.y, r["x"], r["y"]) < INTERACT_RANGE:
            rock = r
            break
    ruin = None
    if rock is None:
        dirx, diry = colision.cardinal_from_aim()
        for reach in (10, 20):
            tx = int((estado.player.x + dirx * reach) // TILE)
            ty = int((estado.player.y + diry * reach) // TILE)
            if mundo.tile_at(tx, ty) == mundo.TILE_TYPE["ruin"]:
                if (estado.in_mine and (tx, ty) not in mine_breakable) or \
                        (not estado.in_mine and (tx, ty) in refineria.REFINERY_BARRIER):
                    estado.log("Esta pared es demasiado dura, ni el zapapico de Baca la rompe." if estado.in_mine
                        else "Escombros compactados. Solo un explosivo los abriría.")
                    return True                
                ruin = (tx, ty)
                break            
    if rock is None and ruin is None:
        return False
    if estado.player.stamina < baca_pick_cost():
        estado.log(f"Aún no recuperas fuerzas para otro golpe ({int(estado.player.stamina / estado.player.max_stamina * 100)}%).")        
        return True
    if rock is not None:
        if estado.current_capacity() >= MAX_CAPACITY:
            estado.log("Tu mochila está llena. No puedes llevar más piedra.")
            return True
        baca_pick_spend()
        pygame.mixer.Channel(10).play(pickaxe_rock_sound)
        rock["active"] = False
        rock["timer"] = 0.0
        rock.pop("hits", None)
        estado.player.inv_stone += 3
        estado.log("¡De un solo golpe! +3 roca.")
        return True
    baca_pick_spend()
    pygame.mixer.Channel(10).play(pickaxe_rock_sound)
    tx, ty = ruin
    if estado.in_mine:
        mundo.WORLD[ty][tx] = mundo.TILE_TYPE["hill"]
        mine_breakable.discard((tx, ty))
        mine_broken.append([tx, ty])
    else:
        mundo.WORLD[ty][tx] = mundo.TILE_TYPE["ground"]
        broken_ruins.append([tx, ty])    
    if estado.current_capacity() < MAX_CAPACITY:
        estado.player.inv_stone += 1
        estado.log("Rompiste la ruina. +1 roca.")
    else:                                      # mochila llena: la roca cae al suelo (E para recogerla)
        estado.drops.append({"x": estado.player.x, "y": estado.player.y, "kind": "debris", "items": {"stone": 1}})
        estado.log("Rompiste la ruina. Tu mochila está llena: la roca quedó en el suelo.")
    return True


def baca_pick_cost():
    return estado.player.max_stamina * ayudantes.BACA_PICK_STAMINA_FRACTION


def baca_pick_spend():
    """Cobra un golpe del zapapico: estamina y un poco de hambre."""
    estado.player.stamina = max(0.0, estado.player.stamina - baca_pick_cost())
    if not estado.god_mode:
        estado.player.hunger = max(0, estado.player.hunger - ayudantes.BACA_PICK_HUNGER_COST)


def baca_pick_pay():
    if estado.player.stamina < baca_pick_cost():
        estado.log(f"Aún no recuperas fuerzas para otro golpe ({int(estado.player.stamina / estado.player.max_stamina * 100)}%).")
        return False
    baca_pick_spend()
    return True
