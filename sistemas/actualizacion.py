"""Actualización por cuadro: jugador, zombis, trampas y balas.

Salió de ebanon.py (original), alrededor de las líneas 2146-2537.
"""

import math
import random
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global baca_jefe, ciclo_dia, colision, combate, construccion
    global estado, hombre_reloj, interaccion, makadewaa, mina
    global mundo, neri_jefe, spawn
    global clima
    global salto
    from jefes import baca_jefe, hombre_reloj, makadewaa, neri_jefe
    from mapas import mina
    from nucleo import estado, mundo
    from sistemas import ciclo_dia, colision, combate, construccion, interaccion, spawn
    from sistemas import clima
    from sistemas import salto


                

# ----------------------------------------------------------------------------
# 13. ACTUALIZACIÓN
# ----------------------------------------------------------------------------
def read_keyboard_move(keys):
    x = y = 0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:  x -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]: x += 1
    if keys[pygame.K_w] or keys[pygame.K_UP]:    y -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:  y += 1
    return x, y

def update_aim_from_mouse():
    mx_screen, my_screen = pygame.mouse.get_pos()
    dx = mx_screen - SCREEN_W / 2
    dy = my_screen - SCREEN_H / 2
    length = math.hypot(dx, dy)
    if length > 2:
        estado.player.aim_x = dx / length
        estado.player.aim_y = dy / length
        estado.player.facing = 1 if dx >= 0 else -1

def update_player(dt, keys, attack_pressed, interact_pressed):
    

    # si ya está en GAMEOVER, no proceses nada
    if estado.game_state == STATE_GAMEOVER:
        return

    # cooldown de interacción
    if estado.interact_cd > 0:
        estado.interact_cd -= dt

    # movimiento teclado
    mx, my = read_keyboard_move(keys)
    if estado.player.dash_t > 0:
        mx = my = 0    
    length = math.hypot(mx, my)
    if length > 1:
        mx /= length
        my /= length

    # dirección visual del sprite
   # aim_dx, aim_dy = cardinal_from_aim()
    #if aim_dx > 0:
    #    player.sprite_dir = "right"
    #elif aim_dx < 0:
     #   player.sprite_dir = "left"
    #elif aim_dy > 0:
     #   player.sprite_dir = "down"
    #elif aim_dy < 0:
     #   player.sprite_dir = "up"
     
    # dirección visual del sprite según el mouse
    if abs(estado.player.aim_x) >= abs(estado.player.aim_y):
        estado.player.sprite_dir = "right" if estado.player.aim_x > 0 else "left"
    else:
        estado.player.sprite_dir = "down" if estado.player.aim_y > 0 else "up"

    # stamina / agotamiento
    if estado.player.stamina <= 0:
        estado.player.exhausted = True
    elif estado.player.stamina >= STAMINA_RECOVER_MIN:
        estado.player.exhausted = False

    sprinting = keys[pygame.K_LSHIFT] and not estado.player.exhausted and length > 0
    spd = estado.player.speed * (estado.player.sprint_mult if sprinting else 1)
    spd *= clima.speed_mult()
    spd *= salto.speed_mult()

    # ralentización en agua
    if mundo.tile_water(int(estado.player.x // TILE), int(estado.player.y // TILE)):
        spd *= 0.43

    # movimiento con anti‑tunneling
    nx = estado.player.x + mx * spd * dt
    ny = estado.player.y + my * spd * dt

    # colisión con zombis: desliza por ejes o se detiene
    if spawn.zombie_blocks_player(nx, ny):
        if not spawn.zombie_blocks_player(nx, estado.player.y):
            ny = estado.player.y
        elif not spawn.zombie_blocks_player(estado.player.x, ny):
            nx = estado.player.x
        else:
            nx, ny = estado.player.x, estado.player.y

    cur_t = (int(estado.player.x // TILE), int(estado.player.y // TILE))
    def free(tx, ty):
        return (tx, ty) == cur_t or not colision.blocked(tx, ty, False) or salto.cruza(tx, ty)

    if free(int(nx // TILE), int(ny // TILE)):
        estado.player.x, estado.player.y = nx, ny
    else:
        if free(int(nx // TILE), int(estado.player.y // TILE)):
            estado.player.x = nx
        elif free(int(estado.player.x // TILE), int(ny // TILE)):
            estado.player.y = ny
            
    # límites del mundo
    cx, cy = estado.WORLD_CENTER
    max_swim = estado.WORLD_RADIUS * 1.4 * TILE
    d = math.hypot(estado.player.x - cx * TILE, estado.player.y - cy * TILE)
    if d > max_swim:
        k = max_swim / d
        estado.player.x = cx * TILE + (estado.player.x - cx * TILE) * k
        estado.player.y = cy * TILE + (estado.player.y - cy * TILE) * k

    estado.player.x = max(TILE, min(estado.WORLD_W * TILE - TILE, estado.player.x))
    estado.player.y = max(TILE, min(estado.WORLD_H * TILE - TILE, estado.player.y))

    estado.player.vx, estado.player.vy = mx * spd, my * spd
    if length > 0:
        estado.player.anim_t += dt
        
    # sonido pasos
    if length > 0:
        if sprinting and not estado.player.exhausted:
            if not pygame.mixer.Channel(1).get_busy() or pygame.mixer.Channel(1).get_sound() != step_sound_run:
                pygame.mixer.Channel(1).stop()
                pygame.mixer.Channel(1).play(step_sound_run, loops=-1)
                pygame.mixer.Channel(1).set_volume(0.4)
        elif estado.player.exhausted:
            if not pygame.mixer.Channel(1).get_busy() or pygame.mixer.Channel(1).get_sound() != step_sound_walk:
                pygame.mixer.Channel(1).stop()
                pygame.mixer.Channel(1).play(step_sound_walk, loops=-1)
                pygame.mixer.Channel(1).set_volume(0.3)
        else:
            if not pygame.mixer.Channel(1).get_busy() or pygame.mixer.Channel(1).get_sound() != step_sound_walk:
                pygame.mixer.Channel(1).stop()
                pygame.mixer.Channel(1).play(step_sound_walk, loops=-1)
                pygame.mixer.Channel(1).set_volume(0.4)
    else:
        pygame.mixer.Channel(1).stop()

    # interacción
    if interact_pressed:
        interaccion.interact()

    # stamina
    if sprinting and not estado.player.exhausted:
        estado.player.stamina = max(0, estado.player.stamina - dt * 20)
    else:
        estado.player.stamina = min(estado.player.max_stamina, estado.player.stamina + dt * 15)

    # ataques
    if estado.player.attack_cooldown > 0:
        estado.player.attack_cooldown -= dt
    if estado.player.action_anim and estado.player.action_anim["t"] > 0:
        estado.player.action_anim["t"] -= dt
    if attack_pressed:
        combate.attempt_attack()

    # hambre
    estado.hunger_timer += dt * (FIRE_HUNGER_FACTOR if colision.near_fire(estado.player.x, estado.player.y) else 1.0)
    if estado.hunger_timer > 9:  # velocidad de hambre
        estado.hunger_timer = 0
        if estado.player.inv_food > 0 and estado.player.hunger < 60:
            estado.player.inv_food -= 1
            estado.player.hunger = min(estado.player.max_hunger, estado.player.hunger + 16)
        else:
            if not estado.god_mode:
                estado.player.hunger = max(0, estado.player.hunger - 2)  # PV perdidos por hambre

        # daño por inanición procesado una vez cada tick
        if estado.player.hunger <= 0 and not estado.god_mode:
            estado.player.hp = max(0, estado.player.hp - 2)
            if not estado.player.hunger_warned:
                estado.player.hunger_warned = True
                estado.log("Te mueres de hambre: busca comida ya.")

        # regeneración periódica: SOLO aquí, una vez por tick de hambre
        if estado.player.hunger > 70 and estado.player.hp < estado.player.max_hp:
            estado.player.hp = min(estado.player.max_hp, estado.player.hp + 1)
    else:
        # avisos y flags que deben evaluarse cada frame (sin curación por frame)
        if estado.player.hunger < 30 and not estado.player.hunger_low_warned:
            estado.player.hunger_low_warned = True
            estado.log("Tienes hambre.")
        if estado.player.hunger >= 30:
            estado.player.hunger_low_warned = False
        if estado.player.hunger > 0:
            estado.player.hunger_warned = False

    # validación de muerte
    if estado.player.hp <= 0 and estado.game_state == STATE_PLAYING:
        estado.game_state = STATE_START
        estado.log("Has muerto. Regresando al menú inicial")
        
        # borrar archivo de guardado si existe
       # if os.path.exists(SAVE_FILE):
        #    try:
        #        os.remove(SAVE_FILE)
        #        log("Archivo de guardado eliminado.")
        #    except Exception as e:
        #        log(f"No se pudo borrar el save: {e}")
                
        return

# ── 6. ANTI-TUNNELING ZOMBIS ─────────────────────────────────────────────
def _zombie_can_move(z, nx, ny):
    tx, ty = int(nx // TILE), int(ny // TILE)
    if (tx, ty) == (int(z.x // TILE), int(z.y // TILE)):
        return True          # si ya está dentro de ese tile (p. ej. un árbol que rebrotó), puede salir
    return not colision.blocked(tx, ty, True)

def update_zombies(dt):
    
    night = ciclo_dia.is_night() or estado.in_mine
    mina.update_mine_field(dt)    
    for z in estado.zombies:
        if z.dead:
            continue

        # Penalización si el zombi está en agua
        base_speed = MINE_ZOMBIE_SPEED if estado.in_mine else (60 if night else 39)        
        if mundo.tile_water(int(z.x // TILE), int(z.y // TILE)):
            base_speed *= 0.3        # se mueve mucho más lento
            z.hp -= dt * 10          # pierde vida por ahogarse
            if z.hp <= 0:
                z.dead = True
                estado.log("Un zombi se ahogó.")
                continue

        if z.alert_cd > 0:
            z.alert_cd -= dt
        if z.alert_t > 0:
            z.alert_t -= dt
        if z.hit_flash > 0:
            z.hit_flash -= dt

        d = mundo.dist(estado.player.x, estado.player.y, z.x, z.y)
        if estado.in_mine and d > 38 * TILE:      # se quedó muy atrás: desaparece
            z.dead = True
            continue
        aggro_range = 200 if night else 90
        z.aggro = estado.in_mine or d < aggro_range or z.alert_t > 0
        
        if z.aggro:
            dx, dy = estado.player.x - z.x, estado.player.y - z.y
            l = math.hypot(dx, dy) or 1
            dx, dy = dx / l, dy / l
            if estado.in_mine and not mina.mine_line_clear(z.x, z.y, estado.player.x, estado.player.y):
                fd = mina.mine_flow_dir(z)
                dx, dy = fd if fd else (0.0, 0.0)
            if d < 14 and not estado.god_mode:
                estado.player.hp = max(0, estado.player.hp - dt * 16)
                if not z.biting:
                    z.biting = True         # agregar sonido de mordida
                    estado.log("¡Un zombi te está mordiendo!")
                    if z.alert_cd <= 0:
                        for other in estado.zombies:
                            if other.dead or other is z:
                                continue
                            if mundo.dist(z.x, z.y, other.x, other.y) < 650:
                                other.alert_t = 8.0
                        z.alert_cd = 7.0
            else:
                z.biting = False
        else:
            z.wander_t -= dt
            if z.wander_t <= 0:
                z.wander_t = 2 + random.random() * 3
                a = random.random() * math.pi * 2
                z.wander_dir = (math.cos(a), math.sin(a))
            dx, dy = z.wander_dir
        for other in estado.zombies:
            if other is z or other.dead:
                continue
            ox, oy = z.x - other.x, z.y - other.y
            od = math.hypot(ox, oy)
            if 0 < od < 8:
                push = (8 - od) * 0.5
                nx2, ny2 = z.x + ox / od * push, z.y + oy / od * push
                if _zombie_can_move(z, nx2, ny2):
                    z.x, z.y = nx2, ny2
        # Movimiento con anti-tunneling: prueba tile destino final
        stunned = z.stun_t > 0
        if stunned:
            z.stun_t -= dt
            nx, ny = z.x, z.y
        elif z.throw_t > 0:
            z.throw_t -= dt
            nx, ny = z.x + z.tvx * dt, z.y + z.tvy * dt
        else:
            nx, ny = z.x + dx * base_speed * dt, z.y + dy * base_speed * dt
                        
        # colisión con el jugador: no entrar en su cuerpo
        d_new = mundo.dist(nx, ny, estado.player.x, estado.player.y)
        if d_new < BODY_DIST and d_new < d:
            nx, ny = z.x, z.y

        if z.aggro and not stunned and z.throw_t <= 0:
            construccion.move_or_breach(z, nx, ny, dx, dy, base_speed, dt, ZOMBIE_STRUCT_DPS)
        elif _zombie_can_move(z, nx, ny):
            z.x, z.y = nx, ny
        else:
            if _zombie_can_move(z, nx, z.y):
                z.x = nx
            elif _zombie_can_move(z, z.x, ny):
                z.y = ny
                                
        if dx != 0:
            z.facing = 1 if dx > 0 else -1

        # Dirección visual del sprite                    
        if abs(dx) >= abs(dy):
            z.sprite_dir = "right" if dx > 0 else "left"
        else:
            z.sprite_dir = "down" if dy > 0 else "up"

        z.vx, z.vy = (0.0, 0.0) if stunned else (dx, dy)
        
        z.anim_t += dt

    estado.zombies[:] = [z for z in estado.zombies if not z.dead]

    estado.zombie_spawn_timer -= dt
    cap = estado.MINE_ZOMBIE_CAP if estado.in_mine else (100 if night else 40)
    if estado.zombie_spawn_timer <= 0 and len(estado.zombies) < cap:  # con zombies
    #if False and zombie_spawn_timer <= 0 and len(zombies) < cap:  # sin zombies
        estado.zombie_spawn_timer = MINE_ZOMBIE_EVERY if estado.in_mine else (2.2 if night else 5)
        if estado.in_mine:
            mina.spawn_mine_zombie()
        else:
            spawn.spawn_zombie(night)
                    
def update_traps(dt):
    used = []
    for st in estado.structures:
        cfg = TRAPS.get(st["type"])
        if not cfg:
            continue
        for z in estado.zombies:
            if z.dead or mundo.dist(z.x, z.y, st["x"], st["y"]) > TRAP_RADIUS:
                continue
            z.hp -= cfg["damage"]
            z.hit_flash = 0.15
            if cfg["stun"] > 0:
                z.stun_t = cfg["stun"]
            pygame.mixer.Channel(13).play(trap_sound)
            estado.log(cfg["msg"])
            if z.hp <= 0:
                z.dead = True
                estado.log("Zombi eliminado por una trampa.")
            used.append(st)          # se destruye al activarse
            break
    for st in used:
        estado.structures.remove(st)

def update_bullets(dt):
    for b in estado.bullets:
        b["x"] += b["vx"] * dt
        b["y"] += b["vy"] * dt
        b["life"] -= dt
        # Punto 5: blocked() ya respeta puertas abiertas (is_zombie=False)
        if colision.blocked(int(b["x"] // TILE), int(b["y"] // TILE), False, ignore_props=True):
            b["life"] = 0
        if estado.boss and b["life"] > 0 and mundo.dist(b["x"], b["y"], estado.boss.x, estado.boss.y) < 20:
            hombre_reloj.hit_boss(b["dmg"])
            b["life"] = 0
            continue
        if b["life"] > 0 and baca_jefe.bullet_hits_baca(b):
            b["life"] = 0
            continue
        if b["life"] > 0 and neri_jefe.bullet_hits_neri(b):
            b["life"] = 0
            continue        
        if b["life"] > 0:
            for br in estado.bears:
                if not br.dead and mundo.dist(b["x"], b["y"], br.x, br.y) < 8 * br.size:
                    makadewaa.hit_bear(br, b["dmg"], b.get("stagger", 0))                    
                    b["life"] = 0
                    break
            if b["life"] <= 0:
                continue
            
        if b["life"] > 0:
            for bt in bats:
                if not bt.dead and mundo.dist(b["x"], b["y"], bt.x, bt.y) < 8:
                    bt.hp -= b["dmg"]
                    bt.hit_flash = 0.15
                    b["life"] = 0
                    break
            if b["life"] <= 0:
                continue
        for z in estado.zombies:
            if z.dead:
                continue
            if mundo.dist(b["x"], b["y"], z.x, z.y) < 10:                
                z.hp -= b["dmg"]
                z.hit_flash = 0.15
                b["life"] = 0
                if z.hp <= 0:
                    z.dead = True
                    estado.log("Zombi abatido.")
                break
    estado.bullets[:] = [b for b in estado.bullets if b["life"] > 0]
