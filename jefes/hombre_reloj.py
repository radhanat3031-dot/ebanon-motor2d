"""Jefe: El Hombre del reloj.

Salió de ebanon.py (original), alrededor de las líneas 2539-8571.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global ayudantes, baca_jefe, ciclo_dia, colision, construccion
    global entidades, estado, makadewaa, mundo
    from jefes import baca_jefe, makadewaa
    from npcs import ayudantes
    from nucleo import entidades, estado, mundo
    from sistemas import ciclo_dia, colision, construccion


    
def spawn_boss():
    
    for _ in range(200):
        ang = random.random() * math.pi * 2
        r = random.uniform(25, 35) * TILE
        tx = int((estado.player.x + math.cos(ang) * r) // TILE)
        ty = int((estado.player.y + math.sin(ang) * r) // TILE)
        if not (0 <= tx < estado.WORLD_W and 0 <= ty < estado.WORLD_H):
            continue
        if mundo.tile_water(tx, ty) or mundo.tile_solid(tx, ty):
            continue
        estado.boss = entidades.Boss(tx * TILE + 8, ty * TILE + 8)
        pygame.mixer.Channel(11).play(boss_roar_sound)
        estado.log(f"¡{BOSS_NAME}! {BOSS_TITLE}.")
        return

def hit_boss(dmg):
    
    b = estado.boss
    b.hp -= dmg
    b.hit_flash = 0.12
    b.speed_mult = max(0.4, b.speed_mult - 0.015)   # cada impacto lo frena un poco
    if b.hp <= 0:
        estado.drops.append({"x": b.x - 10, "y": b.y, "kind": "watch"})
        estado.drops.append({"x": b.x + 10, "y": b.y, "kind": "shotgun"})
        estado.boss = None
        estado.clock_boss_defeated = True
        estado.log("¡El Hombre del reloj cayó! Soltó un reloj y una escopeta.")

def update_boss(dt):
    makadewaa.update_bears(dt)
    baca_jefe.update_baca(dt)
    
    night = ciclo_dia.is_night()
    if not night:
        estado.boss_night_done = False
    if estado.boss is None:
        # solo spawnea si nunca ha aparecido antes
       # if night and not boss_night_done and day_count >= BOSS_FIRST_DAY and not boss_spawned_once:   #comentar para que no aparezca solo de noche
        if night and not estado.boss_night_done and estado.day_count >= BOSS_FIRST_DAY and not estado.boss_spawned_once and not ayudantes.BOSS_ON_GUN_PICKUP:       
            estado.boss_night_done = True
            estado.boss_spawned_once = True
            spawn_boss()
        return

    b = estado.boss
    if b.hit_flash > 0:
        b.hit_flash -= dt
    if b.roar_t > 0:            # se queda rugiendo, sin atacar ni moverse
        b.roar_t -= dt
        return

    d = mundo.dist(estado.player.x, estado.player.y, b.x, b.y)
    dx, dy = estado.player.x - b.x, estado.player.y - b.y
    l = math.hypot(dx, dy) or 1
    dx, dy = dx / l, dy / l

    # movimiento
    if d > BOSS_REACH * 0.6:
        spd = BOSS_SPEED * b.speed_mult
        if mundo.tile_water(int(b.x // TILE), int(b.y // TILE)):
            spd *= 0.5
        nx, ny = b.x + dx * spd * dt, b.y + dy * spd * dt
        construccion.move_or_breach(b, nx, ny, dx, dy, spd, dt, BOSS_STRUCT_DPS)
        b.vx, b.vy = dx, dy
        b.anim_t += dt
    else:
        b.vx = b.vy = 0.0

    if abs(dx) >= abs(dy):
        b.sprite_dir = "right" if dx > 0 else "left"
    else:
        b.sprite_dir = "down" if dy > 0 else "up"

    # golpe de largo alcance
    if d < BOSS_REACH and not estado.god_mode:
        estado.player.hp = max(0, estado.player.hp - dt * BOSS_DPS)

    # invoca y lanza zombis contra el jugador
    b.summon_cd -= dt
    if b.summon_cd <= 0 and len(estado.zombies) < 80:
        b.summon_cd = BOSS_SUMMON_EVERY
        estado.log("¡El Hombre del reloj invoca una horda!")
        for _ in range(BOSS_SUMMON_COUNT):
            a = random.random() * math.pi * 2
            zx, zy = b.x + math.cos(a) * 14, b.y + math.sin(a) * 14
            if colision.blocked(int(zx // TILE), int(zy // TILE), True):
                continue
            z = entidades.Zombie(zx, zy, 55)
            z.alert_t = 10.0
            ang = math.atan2(estado.player.y - zy, estado.player.x - zx) + random.uniform(-0.25, 0.25)
            z.tvx, z.tvy = math.cos(ang) * 220, math.sin(ang) * 220
            z.throw_t = 0.6
            estado.zombies.append(z)

def trigger_clock_boss():
    """Se llama al recoger la pistola. Despierta al Hombre del reloj, una sola vez por partida."""
    
    if not ayudantes.BOSS_ON_GUN_PICKUP or estado.boss_spawned_once or estado.boss is not None or estado.in_mine:
        return
    estado.boss_spawned_once = True
    estado.log("Un tic-tac metálico se acerca entre los árboles...")
    spawn_boss()
