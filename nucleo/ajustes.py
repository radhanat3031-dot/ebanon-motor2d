"""Constantes, paleta, fuentes, sprites base y sonidos. Nada aquí cambia durante la partida.

Salió de ebanon.py (original), alrededor de las líneas 18-989.
"""

import os
import pygame


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # carpeta raíz del juego (donde está main.py)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")              # .ogg y .mp3
SHEET_DIR = os.path.join(ASSETS_DIR, "spritesheets")       # *_walk.png (hojas de animación)


# ----------------------------------------------------------------------------
# 1. CONFIG / VENTANA / PALETA
# ----------------------------------------------------------------------------
pygame.init()
pygame.mixer.init()
pygame.mixer.set_num_channels(32)  # reserva suficientes canales
pygame.display.set_caption("Ébanon // Motor de Supervivencia")


info = pygame.display.Info()
SCREEN_W, SCREEN_H = info.current_w, info.current_h
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
clock = pygame.time.Clock()

# ── Escala dinámica ──────────────────────────────────────────────────────
BASE_TILE = 16
MIN_SCALE = 2
MAX_SCALE = 4
# Queremos que quepan ~30 tiles en el eje más corto
target_tiles = 30
scale = max(MIN_SCALE, min(MAX_SCALE, min(SCREEN_W, SCREEN_H) // (BASE_TILE * target_tiles)))
PIXEL_SCALE = scale
TILE = BASE_TILE
# ── Escalado UI ──────────────────────────────────────────────────────────
UI_S = max(1, PIXEL_SCALE // 2)

TEXT_SCALE = max(1, min(3, PIXEL_SCALE))   # limita entre 1 y 3

# Fuentes escaladas
FONT_SMALL = pygame.font.SysFont("consolas", 7 * TEXT_SCALE)
FONT_MED   = pygame.font.SysFont("consolas", 11 * TEXT_SCALE, bold=True)
FONT_TITLE = pygame.font.SysFont("consolas", 17 * TEXT_SCALE, bold=True)

# ── Spritesheet del jugador y del zombi ──────────────────────────────────
from nucleo import hojas   # el orden de direcciones de cada hoja se configura en nucleo/hojas.py


PLAYER_SPRITE_FRAME = 64
PLAYER_DISPLAY_SIZE = 16

PLAYER_SPRITES = hojas.cargar("navegante", PIXEL_SCALE, PLAYER_DISPLAY_SIZE)


ZOMBIE_SPRITE_FRAME = 64
ZOMBIE_DISPLAY_SIZE = 22

ZOMBIE_SPRITES = hojas.cargar("zombi", PIXEL_SCALE, ZOMBIE_DISPLAY_SIZE)

STAMINA_RECOVER_MIN = 58
DAY_LENGTH = 340
AMMO_RESPAWN_TIME = 45
AMMO_PER_PICKUP = 8
INTERACT_RANGE = 9 * scale
FIRE_RADIUS = 110            # radio del halo en unidades de mundo
FIRE_SOUND_VOLUME = 0.9     # volumen máximo, pegado a la fogata
VISION_RADIUS = 73     # radio del halo del jugador
VISION_INNER = 0.82     # fracción del radio con luz plena; el oscurecimiento ocupa el 18% final
FIRE_INNER = 0.75       # fracción del halo de la fogata con luz plena
CONE_RANGE = 110         # hasta dónde llega el cono
CONE_HALF_ANGLE = 0.77   # mitad de la apertura (0.65 ≈ 75° en total)
CONE_STRENGTH = 0.45      # 1.0 = muy claro dentro del cono, menos = más tenue
CONE_NEAR_RADIUS = 35    # circulito mínimo alrededor del jugador (0 = ninguno)
BODY_DIST = 15   # distancia mínima entre centros (jugador-zombi); debe ser < 14 (rango de mordida)
FIRE_HUNGER_FACTOR = 0.4     # 0.4 = el hambre corre al 40% de velocidad junto a la fogata
ALARM_PRE_HOUR = 18.0    # ejemplo 19.5=19:30
ALARM_END_HOUR = 5.5     # 5:30 termina la locura
SAVE_FILE = os.path.join(BASE_DIR, "ebano_save.json")
SAVE_DIR = os.path.join(BASE_DIR, "saves")
MAX_SLOTS = 6

RESPAWN_WOOD = 70
RESPAWN_ROCK = 240
RESPAWN_SCRAP = 300
RESPAWN_FOOD = 150
RESPAWN_AMMO = 90

INITIAL_WOOD = 800
INITIAL_ROCK = 12
INITIAL_SCRAP = 24
INITIAL_FOOD = 12
INITIAL_AMMO = 6

PALETTE = {
    "grass1": (58, 74, 36), "grass2": (50, 64, 32),
    "dirt1": (74, 58, 38), "dirt2": (64, 49, 31),
    "road1": (44, 44, 40), "road2": (36, 36, 32),
    "water1": (38, 69, 82), "water2": (29, 56, 68),
    "ruin1": (51, 52, 46), "ruin2": (38, 39, 31),
    "tree_trunk": (58, 42, 28), "tree_leaf": (45, 74, 31), "tree_leaf_dark": (32, 53, 15),
    "rock": (85, 85, 79), "rock_dark": (61, 61, 56),
    "scrap_pile": (122, 106, 58), "scrap_pile_dark": (92, 79, 40),
    "player_body": (201, 161, 90), "player_body_dark": (138, 106, 56), "player_head": (217, 193, 154),
    "zombie_body": (92, 106, 58), "zombie_body_dark": (58, 67, 36), "zombie_head": (122, 138, 82),
    "wall": (107, 90, 61), "wall_dark": (74, 61, 41),
    "fire1": (232, 134, 42), "fire2": (201, 67, 42),
    "chest": (138, 106, 56), "chest_dark": (92, 69, 34),
    "gun_metal": (139, 141, 134), "gun_dark": (79, 80, 73), "gun_grip": (92, 69, 34),
    "bullet": (244, 224, 74),
    "crate": (122, 90, 52), "crate_dark": (74, 56, 32), "crate_mark": (201, 67, 42),
    "herb_leaf": (90, 154, 74), "herb_flower": (232, 224, 200),
    "door_plank": (107, 74, 47), "door_dark": (74, 50, 32), "door_open_frame": (138, 106, 69),
}

BUILD_COSTS = {
    "wall": {"wood": 4, "scrap": 0, "stone": 0},
    "fire": {"wood": 1, "scrap": 0, "stone": 0},
    "chest": {"wood": 6, "scrap": 2, "stone": 0},
    "wallStone": {"wood": 0, "scrap": 0, "stone": 3},
    "door": {"wood": 3, "scrap": 1, "stone": 0},
}
BUILD_NAMES = {
    "wall": "Muro construido.", "fire": "Fogata encendida.", "chest": "Almacén instalado.",
    "wallStone": "Muro de piedra construido.", "door": "Puerta instalada.",
}
BUILD_LABELS = {
    "wall": "1) Muro  (Madera 3)",
    "fire": "2) Fogata  (Madera 1)",
    "chest": "3) Almacén  (Madera 6, Chatarra 2)",
    "wallStone": "4) Muro de piedra  (Piedra 3)",
    "door": "5) Puerta  (Madera 3, Chatarra 1)",
}
BUILD_KEYS = {
    pygame.K_1: "wall", pygame.K_2: "fire", pygame.K_3: "chest",
    pygame.K_4: "wallStone", pygame.K_5: "door",
}
# Trampas (se construyen desde el menú B)
BUILD_COSTS["trapSpikes"] = {"wood": 2, "scrap": 2, "stone": 0}
BUILD_COSTS["trapBear"]   = {"wood": 1, "scrap": 4, "stone": 0}
BUILD_NAMES["trapSpikes"] = "Trampa de clavos colocada."
BUILD_NAMES["trapBear"]   = "Cepo colocado."
BUILD_LABELS["trapSpikes"] = "6) Clavos  (Madera 2, Chatarra 2)"
BUILD_LABELS["trapBear"]   = "7) Cepo  (Madera 1, Chatarra 4)"
BUILD_KEYS[pygame.K_6] = "trapSpikes"
BUILD_KEYS[pygame.K_7] = "trapBear"

TRAPS = {
    "trapSpikes": {"damage": 75, "stun": 0.0, "msg": "¡Trampa de clavos activada!"},
    "trapBear":   {"damage": 25, "stun": 6.0, "msg": "¡Un zombi quedó atrapado en el cepo!"},
}
TRAP_RADIUS = 9    # a qué distancia del centro se activa

# Qué bloquea el paso (quita lo que no quieras)
SOLID_PICKUPS = ("wood", "rock", "scrap")
SOLID_STRUCTURES = ("fire", "chest")      # añade "chest" si quieres que el almacén también bloquee
# ── HP de estructuras ──
STRUCT_HP = {"wall": 100, "wallStone": 310, "door": 81, "chest": 100}
REPAIR_RANGE = 4 * TILE
REPAIR_FRACTION = 1 / 3      # cada unidad de material repara un tercio de la vida máxima
REPAIR_MATERIAL = {"wall": "wood", "door": "wood", "chest": "wood", "wallStone": "stone"}
REFUND_DISMANTLE = 0.75       # al desmontar tú con el martillo
REFUND_DESTROYED = 0.25      # cuando la destruyen los enemigos
ITEM_NAMES = {"wood": "madera", "scrap": "chatarra", "stone": "piedra",
              "food": "comida", "bandages": "vendas"}
ATTACKABLE = tuple(STRUCT_HP.keys())     # las que los enemigos pueden atacar
ZOMBIE_STRUCT_DPS = 10                   # daño por segundo de un zombi a una estructura
BREACH_AFTER = 2.3     # segundos atascado rodeando antes de empezar a destruir la estructura
BOSS_STRUCT_DPS = 60

# ── Fogata: combustible ──
FIRE_START_FUEL = 150.0     # segundos de fuego al construirla (la noche dura ~100 s)
FIRE_MAX_FUEL = 180.0       # tope de combustible
FIRE_FUEL_PER_WOOD = 45.0   # (para después) segundos que da 1 de madera
FIRE_DIM_TIME = 15.0        # en los últimos segundos la luz se atenúa

#----------------------------------
# Sonidos con fallback silencioso
#----------------------------------
def _load_sound(path, vol):
    try:
        s = pygame.mixer.Sound(os.path.join(AUDIO_DIR, path))
        s.set_volume(vol)
        return s
    except Exception as e:
        print(f"Error cargando {path}: {e}")
        silent = pygame.mixer.Sound(buffer=bytearray(44))  # 1 frame silencio
        silent.set_volume(0)
        return silent
    
# ── BOSS: El Hombre del reloj ──
BOSS_NAME = "EL HOMBRE DEL RELOJ"
BOSS_TITLE = "Invocador de hordas"
BOSS_MAX_HP = 300
BOSS_SPEED = 32              # el jugador camina a 52
BOSS_REACH = 42              # su alcance (tu melee llega a ~30)
BOSS_DPS = 35                # daño por segundo dentro de su alcance
BOSS_SUMMON_EVERY = 11.0
BOSS_SUMMON_COUNT = 4
BOSS_SCALE = 2.4
BOSS_FIRST_DAY = 3           # primera noche en que puede aparecer check point
BOSS_ROAR_TIME = 2.5
SHOTGUN_AMMO_COST = 2


boss_roar_sound = _load_sound("boss1_roar.ogg", 1.0)   # poner aqui gruñido

def _scale_sheet(frames, k):
    """Agranda el spritesheet del zombi y le da un tinte rojizo."""
    if frames is None:
        return None
    out = {}
    for name, lst in frames.items():
        out[name] = []
        for f in lst:
            w, h = f.get_size()
            big = pygame.transform.scale(f, (int(w * k), int(h * k)))
            big.fill((70, 0, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
            out[name].append(big)
    return out

BOSS_SPRITES = _scale_sheet(ZOMBIE_SPRITES, BOSS_SCALE)

step_sound_walk = _load_sound("footsteps_walk.ogg", 0.5)
step_sound_run  = _load_sound("footsteps_run.ogg",  0.6)
gunshot_sound   = _load_sound("gunshot.ogg", 0.6)
hit_sound       = _load_sound("blood_hit.ogg", 0.6)
wood_axe_hit    = _load_sound("wood_axe_hit.ogg", 0.6)
down_three      = _load_sound("down_three.ogg", 0.6)
scrapping_sound = _load_sound("scrapping_sound.ogg", 0.9)
eating_sound    = _load_sound("eat.ogg", 0.8)
bag_sound       = _load_sound("open_bag.ogg", 0.6)
pickaxe_sound   = _load_sound("pickaxe.ogg", 0.6)
pickaxe_rock_sound   = _load_sound("pickaxe_rocks.ogg", 0.6)
clock_alarm_sound = _load_sound("clock_alarm.ogg", 0.7)
fire_loop_sound = _load_sound("fire_loop.ogg", 1.0)
trap_sound = _load_sound("trap.ogg", 0.7)
hammer_sound = _load_sound("hammer.ogg", 0.7)

# ── OSOS ──
BEAR_NAME = "MAKADEWAA MAKWAA"
BEAR_TITLE = "La Rompe trampas"
BEAR_BOSS_FIRST_DAY = 6
BEAR_TYPES = {
    "boss": {
        "hp": 700, "speed": 45, "reach": 34, "size": 2.6, "dps": 30,
        "struct_dps": 60, "color": (62, 42, 30),
        # zarpazo
        "swipe_range": 38, "swipe_arc": 0.8, "swipe_windup": 0.45,
        "swipe_recover": 0.3, "swipe_cd": 0.5, "swipe_dmg": 35,
        # carga
        "charge_range": 100, "charge_min": 80, "charge_dist": 120, "charge_speed": 550,
        "charge_windup": 0.1, "charge_recover": 0.5, "charge_cd": 6.0,
        "charge_dmg": 41, "charge_hit_r": 22, "charge_wall_dmg": 140, "charge_interrupt": 36,
        # golpe de suelo
        "slam_trigger": 90, "slam_radius": 135, "slam_speed": 160, "slam_windup": 0.57,
        "slam_recover": 1.2, "slam_cd": 9.0, "slam_dmg": 33, "slam_thick": 9,
        # aturdimiento
        "stagger_max": 80, "stagger_decay": 10, "stagger_time": 1.4, "stagger_immune": 3.0,
        # rugido invocador
        "roar_windup": 1.2, "roar_recover": 0.9, "roar_count": 2, "roar_thresholds": (0.66, 0.33),
    },
    "weak": {
        "hp": 150, "speed": 42, "reach": 24, "size": 1.5, "dps": 14,
        "struct_dps": 20, "color": (96, 72, 52),
        # zarpazo
        "swipe_range": 33, "swipe_arc": 0.8, "swipe_windup": 0.3,
        "swipe_recover": 0.4, "swipe_cd": 1.8, "swipe_dmg": 17,
        # aturdimiento
        "stagger_max": 40, "stagger_decay": 10, "stagger_time": 1.0, "stagger_immune": 2.0,
    },
}

LOCKED_BUILDS = {"trapBear": "bear_trap"}     # construcción -> receta que la desbloquea
bear_roar_sound = _load_sound("bear_roar.ogg", 1.0)
BEAR_TYPES["boss"].update({
    "charge_range": 230, "charge_min": 80, "charge_dist": 230, "charge_speed": 150,
    "charge_windup": 0.6, "charge_recover": 1.0, "charge_cd": 6.0,
    "charge_dist": 230,
    "charge_lock": 0.2,      # segundos finales del aviso en que la franja se bloquea
    "charge_turn": 0.7,       # radianes/s que puede corregir mientras embiste (0 = ninguna)    
    "charge_dmg": 35, "charge_hit_r": 24, "charge_wall_dmg": 140, "charge_interrupt": 36,
    "stagger_max": 80, "stagger_decay": 10, "stagger_time": 1.4, "stagger_immune": 3.0})
BEAR_TYPES["weak"].update({
    "stagger_max": 40, "stagger_decay": 10, "stagger_time": 1.0, "stagger_immune": 2.0})
bear_charge_sound = _load_sound("bear_charge.ogg", 1.0)     # suena cuando arranca la embestida
bear_growl_sound = _load_sound("bear_growl.ogg", 0.9)    # aviso: suena al empezar a telegrafiar
bear_swipe_sound = _load_sound("bear_swipe.ogg", 0.9)    # suena en el instante del golpe
bear_slam_sound = _load_sound("bear_slam.ogg", 1.0)

WEAK_BEAR_SPAWN_DAY = 30.0
WEAK_BEAR_SPAWN_NIGHT = 12.0
WEAK_BEAR_CAP = 9            # máximo vivos de día (+1 de noche)
WEAK_SUMMON_MAX = 5          # máximo de osos débiles con el rugido

STATE_START = "start"
STATE_SLOTS = "slots"
STATE_NAME = "name"
STATE_PLAYING = "playing"
STATE_GAMEOVER = "gameover"
# ── LA MINA ──
MINE_SIZE = 150              # ← CAMBIA AQUÍ EL TAMAÑO DE LA MINA (cuadrada)
MINE_W = MINE_SIZE
MINE_H = MINE_SIZE
MINE_DARKNESS = 0.77         # oscuridad fija dentro de la mina (0 a 1)
MINE_AREA_PER_ZOMBIE = 5000  # 1 zombi máximo por cada 5000 tiles de mina (250x250 → 12)
MINE_ZOMBIE_NEAR_CAP = 4     # máximo de zombis a la vez cerca de ti (20 tiles)
MINE_ZOMBIE_EVERY = 7.0      # segundos entre cada zombi nuevo
CAVE_ARROW = True            # flecha que apunta a la mina cuando no se ve en pantalla
MINE_ZOMBIE_SPEED = 47
MINE_BAT_CAP = 4
MINE_BAT_EVERY = 5.0
MINE_FIELD_DEPTH = 18        # hasta cuántos pasos de camino ven los zombis
mine_breakable = set()       # paredes marcadas que rompe el pico de Baca
mine_broken = []             # las que ya rompiste (se guardan)
mine_field = {}
bats = []
CAVE_POS = [0, 0]            # tile de la cueva en la isla
MINE_INFO = {"exit": (0, 0), "start": (0, 0), "lair": (0, 0)}   # lair = guarida de Neri

# Capacidad de la mochila
MAX_CAPACITY = 27
DROP_KEYS = {pygame.K_1: "wood", pygame.K_2: "scrap", pygame.K_3: "stone",
             pygame.K_4: "food", pygame.K_5: "bandages"}
STORE_BAG_MAP = {"wood": "inv_wood", "scrap": "inv_scrap", "stone": "inv_stone",
                 "food": "inv_food", "bandages": "bandages"}

WEAPON_LABELS = {"fist": "PUÑOS", "axe": "HACHA", "pickaxe": "PICO", "bat": "BATE",
                 "hammer": "MARTILLO", "gun": "PISTOLA", "shotgun": "ESCOPETA"}
MELEE_DAMAGE = {"fist": 18, "axe": 25, "pickaxe": 30, "bat": 36}
TOOL_DURABILITY_MAX = {"axe": 120, "pickaxe": 100, "bat": 50}

# Capacidad del almacén
CHEST_CAPACITY = 50
