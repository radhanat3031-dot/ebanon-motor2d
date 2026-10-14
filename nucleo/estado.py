"""Variables que cambian durante la partida (jugador, listas, menús abiertos, etc.).

Salió de ebanon.py (original), alrededor de las líneas 91-1008.
"""

import math
import random
from nucleo.ajustes import *  # noqa: F401,F403
from nucleo import entidades


WORLD_W, WORLD_H = 300, 300
# Parámetros de forma del mundo
WORLD_CENTER = (WORLD_W // 2, WORLD_H // 2)
WORLD_RADIUS = min(WORLD_W, WORLD_H) * 0.36
WORLD_MASK = [[True for _ in range(WORLD_W)] for __ in range(WORLD_H)]
WORLD_SEED_X = random.uniform(0, 100000)
WORLD_SEED_Y = random.uniform(0, 100000)
MINE_ZOMBIE_CAP = max(6, (MINE_W * MINE_H) // MINE_AREA_PER_ZOMBIE)   # o pon un número fijo

in_mine = False
island_stash = None
mine_stash = None            # la mina guardada (estructuras, recursos...)
mine_seed = 0
mine_field_t = 0.0
bat_spawn_timer = 3.0

# ----------------------------------------------------------------------------
# 4. ESTADO GLOBAL
# ----------------------------------------------------------------------------
player = entidades.Player()
zombies = []
boss = None
boss_night_done = False   # evita que reaparezca en la misma noche
boss_spawned_once = False  # hace que el hombre del reloj solo apaezca una vez en la partida
drops = []                # objetos soltados por el jefe
bears = []
bear_spawn_timer = 45.0
shockwaves = []
bear_night_done = False
bear_spawned_once = False
clock_boss_defeated = False
weak_bears_unlocked = False      # lo usaremos para desbloquear mini osos
prop_tiles = set()    # tiles ocupados por recursos y fogatas
save_slots = []        # partidas encontradas: (nombre, ruta, info, fecha)
current_save = None    # ruta de la partida activa
menu_msg = ""
name_input = ""
delete_confirm = None
dusk_warned = False
structures = []
bullets = []

wood_pickups = []
rock_pickups = []
scrap_pickups = []
food_pickups = []
ammo_pickups = []
gun_pickup = None

day_count = 1
world_time = 0.48
hunger_timer = 0.0
zombie_spawn_timer = 0.0
camera_x = camera_y = 0.0
log_lines = []

build_menu_open = False
# clear_build_selection()
inventory_open = False
active_chest = None
pause_menu_open = False
build_selected = None        # estructura cargada (None = ninguna)
build_ui = {"panel": None}   # rect del panel de construcción (lo llena render_build_menu)

game_state = STATE_START
survived_days = 0
god_mode = False
autosave_acc = 0.0

def chest_capacity_used(chest):
    return (chest["store"]["wood"] + chest["store"]["scrap"] +
            chest["store"]["stone"] + chest["store"]["food"] +
            chest["store"]["bandages"])


# --- Cooldown de interacción ---
interact_cd = 0.0

def current_capacity():
    cajas = math.ceil(player.ammo / AMMO_PER_PICKUP)
    return (player.inv_wood + player.inv_scrap + player.inv_stone +
            player.inv_food + player.bandages + cajas + sum(player.cargo.values()))
    
def log(msg):
    log_lines.append(msg)
    if len(log_lines) > 5:
        log_lines.pop(0)
