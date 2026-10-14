"""Combate: golpes, disparos y daño.

Salió de ebanon.py (original), alrededor de las líneas 1711-1831.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global baca_jefe, baca_pico, colision, construccion, estado
    global hombre_reloj, makadewaa, mundo, neri_jefe
    global tiburones
    global estaciones
    from jefes import baca_jefe, baca_pico, hombre_reloj, makadewaa, neri_jefe
    from nucleo import estado, mundo
    from sistemas import colision, construccion
    from sistemas import tiburones
    from sistemas import estaciones


# ----------------------------------------------------------------------------
# 9. COMBATE
# ----------------------------------------------------------------------------
def melee_attack():
    if estado.player.attack_cooldown > 0:
        return
    estado.player.attack_cooldown = 0.35
    rng = 20
    dirx, diry = colision.cardinal_from_aim()
    ax, ay = estado.player.x + dirx * 10, estado.player.y + diry * 10
    dmg = estaciones.melee_damage(estado.player.equipped, MELEE_DAMAGE.get(estado.player.equipped, MELEE_DAMAGE["fist"]))
    #if player.equipped in ("axe", "pickaxe", "bat"):     # comentar para debugg de armas
        #use_tool_durability(player.equipped) # comentar para debugg de armas
    for z in estado.zombies:
        if z.dead:
            continue
        if mundo.dist(ax, ay, z.x, z.y) < rng:
            z.hp -= dmg
            estaciones.xp("combate")
            z.hit_flash = 0.15
            if z.hp <= 0:
                z.dead = True
                estado.log("Zombi eliminado.")
            if estado.player.equipped in ("axe", "bat"):
                pygame.mixer.Channel(3).play(hit_sound)
    estado.player.action_anim = {"type": "melee", "t": 0.18, "total": 0.18, "dx": dirx, "dy": diry}
    
    for bt in bats:
        if not bt.dead and mundo.dist(ax, ay, bt.x, bt.y) < rng + 4:
            bt.hp -= dmg
            bt.hit_flash = 0.15
    
    # --- daño al boss ---
    if estado.boss and mundo.dist(ax, ay, estado.boss.x, estado.boss.y) < rng:
        hombre_reloj.hit_boss(dmg)
        if estado.player.equipped in ("axe", "bat"):
            pygame.mixer.Channel(3).play(hit_sound)
    for br in estado.bears:
        if not br.dead and mundo.dist(ax, ay, br.x, br.y) < rng + 6 * br.size:
            estaciones.xp("combate")
            makadewaa.hit_bear(br, dmg)            
    baca_jefe.melee_hits_baca(ax, ay, rng, dmg)
    neri_jefe.melee_hits_neri(ax, ay, rng, dmg)
    tiburones.melee_hits_sharks(ax, ay, rng, dmg)
    
    estado.player.action_anim = {"type": "melee", "t": 0.18, "total": 0.18, "dx": dirx, "dy": diry}

def fire_gun():
    if estado.player.attack_cooldown > 0:
        return
    if estado.player.ammo <= 0:
        estado.log("Sin balas.")
        return
    estado.player.attack_cooldown = 0.20
    estado.player.ammo -= 1
    pygame.mixer.Channel(2).play(gunshot_sound)
    estado.bullets.append({
        "x": estado.player.x, "y": estado.player.y,
        "vx": estado.player.aim_x * 180, "vy": estado.player.aim_y * 180,
        "life": 0.5, "dmg": 21, "stagger": 4
    })
    dirx, diry = colision.cardinal_from_aim()
    estado.player.action_anim = {"type": "gun", "t": 0.12, "total": 0.12, "dx": dirx, "dy": diry}

def fire_shotgun():
    if estado.player.attack_cooldown > 0:
        return
    if estado.player.ammo < SHOTGUN_AMMO_COST:
        estado.log("Sin balas suficientes (la escopeta gasta 2).")
        return
    estado.player.attack_cooldown = 0.9
    estado.player.ammo -= SHOTGUN_AMMO_COST
    pygame.mixer.Channel(2).play(gunshot_sound)
    base = math.atan2(estado.player.aim_y, estado.player.aim_x)
    for _ in range(7):
        a = base + random.uniform(-0.22, 0.22)
        estado.bullets.append({"x": estado.player.x, "y": estado.player.y,
                        "vx": math.cos(a) * 200, "vy": math.sin(a) * 200,
                        "life": 0.3, "dmg": 12, "stagger": 9})
        dirx, diry = colision.cardinal_from_aim()
    estado.player.action_anim = {"type": "gun", "t": 0.12, "total": 0.12, "dx": dirx, "dy": diry}

def attempt_attack():
    if estado.player.equipped == "gun":
        fire_gun()
    elif estado.player.equipped == "shotgun":
        fire_shotgun()
    elif estado.player.equipped == "hammer":
        construccion.use_hammer()
    elif estado.player.equipped == "baca_pick":
        baca_pico.baca_pick_swing()
    else:
        melee_attack()
        
# ----------------------------------------------------------------------------
# 9b. EQUIPAMIENTO
# ----------------------------------------------------------------------------
def available_weapons():
    w = ["fist"]
    if estado.player.has_axe: w.append("axe")
    if estado.player.has_pickaxe: w.append("pickaxe")
    if estado.player.has_bat: w.append("bat")
    if estado.player.has_gun: w.append("gun")
    if estado.player.has_shotgun: w.append("shotgun")   
    if estado.player.has_hammer: w.append("hammer")
    if estado.player.has_baca_pick: w.append("baca_pick")
    return w

def cycle_weapon():
    avail = available_weapons()
    if estado.player.equipped not in avail:
        estado.player.equipped = "fist"
        return
    i = avail.index(estado.player.equipped)
    estado.player.equipped = avail[(i + 1) % len(avail)]
    estado.log(f"Equipaste: {WEAPON_LABELS[estado.player.equipped]}")

def toggle_equip(name):
    owned = {"axe": estado.player.has_axe, "pickaxe": estado.player.has_pickaxe, "bat": estado.player.has_bat, "gun": estado.player.has_gun, "hammer": estado.player.has_hammer, "shotgun": estado.player.has_shotgun, "baca_pick": estado.player.has_baca_pick, "fist":  True}
    if not owned.get(name):
        return
    if estado.player.equipped == name:
        estado.player.equipped = "fist"
        estado.log("Guardaste el arma (puños).")
    else:
        estado.player.equipped = name
        estado.log(f"Equipaste: {WEAPON_LABELS[name]}")
