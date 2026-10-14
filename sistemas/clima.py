"""Clima: la lluvia te moja, el frío te desgasta, y la fogata y los refugios te salvan.

MOJADO (0 a 100)
  Sube con la lluvia si estás al aire libre, y muy rápido si nadas. Se seca solo despacio,
  más rápido bajo un refugio y MUY rápido junto a una fogata encendida.
  REFUGIO = 4 o más muros / puertas a menos de 3 casillas de ti (una choza): ahí no te cae la lluvia.

FRÍO (0 a 100)
  Sube de noche, con la lluvia y sobre todo si estás mojado. Baja solo, y muy rápido junto a una fogata.
  Una comida caliente (tecla C en la fogata) hace que el frío te afecte la mitad.
      40 o más  Frío:        caminas un poco más lento
      70 o más  Mucho frío:  caminas bastante más lento
      90 o más  Hipotermia:  vas perdiendo vida hasta que entres en calor

Las minas y demás mapas interiores no tienen lluvia ni noche fría. Mojado y frío no se guardan en la partida.
"""

import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global ambiente, ciclo_dia, estado, hogar, hud, mundo
    from interfaz import hud
    from nucleo import estado, mundo
    from sistemas import ambiente, ciclo_dia, hogar


# ============================================================================
# AJUSTES (todo lo que quieras tocar está aquí)
# ============================================================================
RAIN_WET_RATE = 5.0        # ← mojado por segundo con lluvia fuerte al aire libre (20 s para empaparte)
SWIM_WET_RATE = 30.0       # ← mojado por segundo al nadar
DRY_RATE = 1.2             # ← se seca solo (por segundo)
DRY_RATE_SHELTER = 3.0     # ← se seca bajo un refugio
DRY_RATE_FIRE = 10.0       # ← se seca junto a una fogata encendida
NIGHT_COLD = 0.30          # ← frío por segundo de noche
RAIN_COLD = 0.35           # ← frío por segundo con lluvia fuerte al aire libre
WET_COLD = 0.70            # ← frío por segundo si estás empapado (proporcional a lo mojado)
SWIM_COLD = 1.00           # ← frío extra por segundo al nadar
FED_COLD_FACTOR = 0.5      # ← con comida caliente el frío sube a esta fracción
COOL_RECOVER = 0.7         # ← entras en calor solo, por segundo, cuando nada te enfría
FIRE_WARM = 7.0            # ← entras en calor junto a una fogata, por segundo
WARM_RANGE = 80            # ← qué tan cerca de la fogata debes estar (px)
SHELTER_RADIUS = 3 * TILE  # ← radio en que se cuentan los muros del refugio
SHELTER_MIN = 4            # ← cuántos muros/puertas hacen falta para que sea refugio
COLD_LEVELS = (40, 70, 90) # ← desde dónde empieza Frío, Mucho frío e Hipotermia
SPEED_BY_LEVEL = (1.0, 0.94, 0.86, 0.80)   # ← velocidad según el nivel de frío
HYPOTHERMIA_DRAIN = 0.8    # ← vida que pierdes por segundo con hipotermia
TINT_MAX_ALPHA = 55        # ← cuánto se oscurece/azulea la pantalla con mucho frío

S = {"wet": 0.0, "cold": 0.0, "level": 0, "sheltered": False, "soaked": False}
_tint = {}


def reset():
    S.update({"wet": 0.0, "cold": 0.0, "level": 0, "sheltered": False, "soaked": False})


# ============================================================================
# AYUDAS
# ============================================================================
def sheltered(x, y):
    n = 0
    for st in estado.structures:
        if st["type"] in ("wall", "wallStone", "door", "doorMetal") and mundo.dist(x, y, st["x"], st["y"]) <= SHELTER_RADIUS:
            n += 1
    return n >= SHELTER_MIN


def level_of(cold):
    return sum(1 for t in COLD_LEVELS if cold >= t)


def speed_mult():
    """Lo usa update_player: el frío te hace caminar más lento."""
    return SPEED_BY_LEVEL[S["level"]]


# ============================================================================
# ACTUALIZACIÓN (una vez por cuadro)
# ============================================================================
def update(dt):
    p = estado.player
    if p.hp <= 0:
        return
    interior = estado.in_mine
    rain_lv = 0.0 if interior else ambiente.rain["level"]
    swimming = mundo.tile_water(int(p.x // TILE), int(p.y // TILE))
    fire = hogar.fire_near(p.x, p.y, WARM_RANGE)
    roof = sheltered(p.x, p.y)
    S["sheltered"] = roof

    # --- mojado
    gain = SWIM_WET_RATE if swimming else (RAIN_WET_RATE * rain_lv if (rain_lv > 0.05 and not roof) else 0.0)
    if fire:
        loss = DRY_RATE_FIRE
    elif roof:
        loss = DRY_RATE_SHELTER
    elif gain == 0:
        loss = DRY_RATE
    else:
        loss = 0.0
    S["wet"] = min(100.0, max(0.0, S["wet"] + (gain - loss) * dt))

    # --- frío
    cold_gain = WET_COLD * S["wet"] / 100.0
    if not interior:
        if ciclo_dia.is_night():
            cold_gain += NIGHT_COLD
        if rain_lv > 0.05 and not roof:
            cold_gain += RAIN_COLD * rain_lv
    if swimming:
        cold_gain += SWIM_COLD
    if hogar.is_fed():
        cold_gain *= FED_COLD_FACTOR
    if fire:
        delta = -FIRE_WARM
    elif cold_gain > 0.05:
        delta = cold_gain
    else:
        delta = -COOL_RECOVER
    S["cold"] = min(100.0, max(0.0, S["cold"] + delta * dt))

    # --- avisos
    if S["wet"] >= 60 and not S["soaked"]:
        S["soaked"] = True
        estado.log("Estás empapado: el frío te va a calar más rápido. Busca una fogata o un refugio.")
    elif S["wet"] < 15 and S["soaked"]:
        S["soaked"] = False
        estado.log("Ya te secaste.")
    new = level_of(S["cold"])
    if new != S["level"]:
        if new > S["level"]:
            estado.log(("", "Tienes frío.", "Tienes mucho frío: acércate a una fogata.",
                        "HIPOTERMIA: estás perdiendo vida. ¡Una fogata, rápido!")[new])
        elif new == 0:
            estado.log("Entras en calor.")
        S["level"] = new

    # --- hipotermia
    if S["level"] == 3 and not estado.god_mode:
        p.hp = max(0.0, p.hp - HYPOTHERMIA_DRAIN * dt)


# ============================================================================
# PANTALLA
# ============================================================================
def draw_status(surface):
    parts = []
    col = (141, 145, 120)
    if S["wet"] >= 3:
        parts.append(f"Mojado {int(S['wet'])}%")
        col = (120, 170, 220)
    if S["cold"] >= 3:
        parts.append(f"Frío {int(S['cold'])}%")
        col = ((150, 190, 230), (110, 150, 235), (230, 90, 80))[min(2, max(0, S["level"] - 1))] if S["level"] else col
    if S["sheltered"] and ambiente.rain["level"] > 0.05 and not estado.in_mine:
        parts.append("bajo refugio")
    if S["level"] == 3:
        parts.append("¡HIPOTERMIA!")
    if not parts:
        return
    img = FONT_SMALL.render("  ·  ".join(parts), True, col)
    surface.blit(img, (SCREEN_W - img.get_width() - 14, int(88 * UI_S)))


def draw_overlay(surface):
    """Tinte azulado cuando tienes frío (se nota más con hipotermia)."""
    if S["cold"] < COLD_LEVELS[0]:
        return
    alpha = int(TINT_MAX_ALPHA * min(1.0, (S["cold"] - COLD_LEVELS[0]) / (100 - COLD_LEVELS[0])))
    if alpha <= 0:
        return
    key = (SCREEN_W, SCREEN_H)
    if _tint.get("key") != key:
        _tint["key"] = key
        _tint["surf"] = pygame.Surface(key, pygame.SRCALPHA)
    _tint["surf"].fill((40, 80, 140, alpha))
    surface.blit(_tint["surf"], (0, 0))
