"""Clases Player, Zombie, Boss y Bear.

Salió de ebanon.py (original), alrededor de las líneas 805-921.
"""

import random
from nucleo.ajustes import *  # noqa: F401,F403
from nucleo import estado


# ----------------------------------------------------------------------------
# 3. ENTIDADES
# ----------------------------------------------------------------------------
class Player:
    def __init__(self):
        self.x = estado.WORLD_W * TILE / 2
        self.y = estado.WORLD_H * TILE / 2
        self.hp = self.max_hp = 100
        self.stamina = self.max_stamina = 155
        self.hunger = self.max_hunger = 120
        self.speed = 65
        self.sprint_mult = 1.8
        self.attack_cooldown = 0.0
        self.inv_wood = 4
        self.inv_scrap = 2
        self.inv_food = 0
        self.inv_stone = 0
        self.bandages = 0
        self.has_gun = False
        self.ammo_boxes = 0
        self.ammo = 0
        self.has_axe = False
        self.has_pickaxe = False
        self.has_bat = False
        self.has_hammer = False
        # recetas que otorgan los bosses
        self.recipes = set()
        # durabilidad y advertencias
        self.axe_durability = 0        # Duración del hacha
        self.pickaxe_durability = 0    # Duracion del pico
        self.bat_durability = 0        # Duracion del bat
        self.axe_low_warned = False
        self.pickaxe_low_warned = False
        self.bat_low_warned = False
        self.equipped = "fist"
        self.aim_x, self.aim_y = 1.0, 0.0
        self.facing = 1
        self.sprite_dir = "down"   # <-- NUEVA: hacia dónde mira el sprite (según WASD, no el aim)
        self.action_anim = None
        self.anim_t = 0.0
        self.hunger_warned = False
        self.hunger_low_warned = False
        self.exhausted = False
        self.vx = self.vy = 0.0
        self.has_shotgun = False
        self.has_watch = False
        self.has_baca_pick = False
        self.has_lamp = False
        
class Zombie:
    def __init__(self, x, y, speed):
        self.x = x
        self.y = y
        self.hp = self.max_hp = 75
        self.speed = speed
        self.wander_t = 0.0
        self.wander_dir = (0.0, 0.0)
        self.alert_t = 0.0
        self.aggro = False
        self.alert_cd = 0.0
        self.hit_flash = 0.0
        self.biting = False
        self.facing = 1
        self.sprite_dir = "down"   # <-- NUEVA para añadir spritesheet
        self.block_t = 0.0                        # tiempo acumulado atascado
        self.detour_side = random.choice((2, -2))  # hacia qué lado intenta rodear        
        self.anim_t = 0.0
        self.stun_t = 0.0           # tiempo inmovilizado por un cepo
        self.vx = self.vy = 0.0
        self.dead = False
        self.throw_t = 0.0          # tiempo restante de "lanzamiento"
        self.tvx = self.tvy = 0.0

class Boss:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.hp = self.max_hp = BOSS_MAX_HP
        self.speed_mult = 1.0
        self.summon_cd = 3.0
        self.hit_flash = 0.0
        self.sprite_dir = "down"
        self.block_t = 0.0                        # tiempo acumulado atascado
        self.detour_side = random.choice((4, -4))  # hacia qué lado intenta rodear
        self.anim_t = 0.0
        self.vx = self.vy = 0.0
        self.roar_t = BOSS_ROAR_TIME
        
class Bear:
    def __init__(self, kind, x, y):
        cfg = BEAR_TYPES[kind]
        self.kind = kind
        self.x, self.y = x, y
        self.hp = self.max_hp = cfg["hp"]
        self.size = cfg["size"]
        self.speed_mult = 1.0
        self.hit_flash = 0.0
        self.sprite_dir = "down"
        self.anim_t = 0.0
        self.vx = self.vy = 0.0
        self.roar_t = BOSS_ROAR_TIME if kind == "boss" else 0.0
        self.block_t = 0.0
        self.detour_side = random.choice((1, -1))
        self.dead = False        
        self.state = "chase"       # chase / windup / recover
        self.attack = None
        self.state_t = 0.0
        self.state_total = 1.0
        self.cd = 1.0              # espera antes del primer ataque
        self.aim_dx, self.aim_dy = 1.0, 0.0
        self.strike_t = 0.0        # destello del golpe
        self.stagger = 0.0          # barra de aturdimiento
        self.stagger_immune = 0.0   # evita aturdirlo en cadena
        self.charge_acc = 0.0       # aturdimiento recibido durante la carga
        self.charge_cd = 2.0
        self.charge_left = 0.0
        self.slam_cd = 4.0          # el primer golpe de suelo tarda en llegar
        self.roar_stage = 0                  # cuántos rugidos del jefe ya usó
        self.aggro = (kind == "boss")        # los débiles empiezan sin verte
        self.wander_t = 0.0
        self.wander_dir = (0.0, 0.0)
