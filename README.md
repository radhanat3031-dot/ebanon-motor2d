# Ébanon

Juego de supervivencia hecho en Python con Pygame: zombis, construcción, jefes, mapas subterráneos y una historia por capítulos.

## Cómo correrlo

```bash
pip install -r requirements.txt
py -3.12 main.py        # en Windows
python3 main.py         # en otros sistemas
```

Ejecútalo siempre desde la carpeta que contiene `main.py`.

## Assets

Los audios y sprites **no están en el código**; van en `assets/`:

```
assets/
├── audio/          # todos los .ogg y .mp3 (efectos, música, lluvia)
├── spritesheets/   # hojas de animación: navegante_walk.png, zombie_walk.png, nina_walk.png, anciana_walk.png
└── sprites/        # sprites sueltos (árboles, estructuras, objetos…)
```

Si falta un audio, el juego usa un silencio; si falta un sprite, usa un dibujo de respaldo. Así arranca aunque tengas la carpeta vacía.

Audios que busca el juego en `assets/audio/`:
`boss1_roar`, `footsteps_walk`, `footsteps_run`, `gunshot`, `blood_hit`, `wood_axe_hit`, `down_three`, `scrapping_sound`, `eat`, `open_bag`, `pickaxe`, `pickaxe_rocks`, `clock_alarm`, `fire_loop`, `trap`, `hammer`, `bear_roar`, `bear_charge`, `bear_growl`, `bear_swipe`, `bear_slam`, `neri_howl` (todos `.ogg`), más `soft_rain.ogg`, `menu_theme.mp3` y `gameplay_1.mp3`.

Opcionales para los tiburones: `assets/sprites/shark_fin.png` (aleta, se dibuja de 16x16), `assets/sprites/shark_bite.png` (tiburón mordiendo, 28x14) y `assets/audio/shark_bite.ogg`. Si faltan, se dibujan con bloques y suena el golpe normal.

Las partidas se guardan en `ebano_save.json` y en `saves/` (están en `.gitignore`).

## Cómo está organizado

| Carpeta | Qué contiene |
|---|---|
| `nucleo/` | `ajustes` (constantes, paleta, fuentes, sonidos), `estado` (variables que cambian durante la partida), `entidades` (Player, Zombie, Boss, Bear), `mundo` (generación de la isla), `bucle` (el `main()`) |
| `sistemas/` | `spawn`, `ciclo_dia`, `colision`, `construccion`, `combate`, `interaccion`, `almacen`, `crafteo`, `actualizacion`, `recursos`, `camara`, `ambiente` (lluvia y árboles), `tiburones` (el mar), `guardado`, `partida` |
| `jefes/` | `hombre_reloj`, `baca_jefe`, `baca_pico`, `makadewaa`, `neri_jefe`, `tonico` |
| `mapas/` | `mina`, `barco`, `transicion` (entrar y salir de mapas), `fundidora`, `refineria` (incluye la dinamita), `deshuesadero` |
| `interfaz/` | `dibujo` (mundo, sprites, enemigos), `hud`, `menus` (mochila, inicio, slots, pausa, game over) |
| `npcs/` | `ayudantes` (la niña y la anciana) |

## Convenciones del código

- Lo que viene de otro archivo lleva el nombre del archivo delante: `estado.player.x`, `combate.hit_boss(20)`.
- Las constantes de `nucleo/ajustes.py` se usan sin prefijo (`TILE`, `PALETTE`…).
- Las variables que cambian durante la partida viven en el archivo donde nacieron y se modifican con prefijo (`estado.game_state = STATE_PLAYING`); `global` solo hace falta para las del propio archivo.
- Cada archivo que usa a otros tiene una función `conectar_modulos()` arriba, que `main.py` llama cuando todos ya cargaron. Así no hay imports circulares.
- `main.py` importa **todos** los módulos en orden. Algunos agregan cosas a tablas compartidas (`BUILD_COSTS`, `ITEM_NAMES`, `DROP_KEYS`…) en el momento de cargar, por eso ninguno puede faltar.

## Agregar un archivo nuevo

Ejemplo: `jefes/cazador.py`.

1. Arriba pon lo que necesites: `import pygame`, `import math` y `from nucleo.ajustes import *`.
2. Si usa otros archivos, agrega esta función (cambiando los nombres):
   ```python
   def conectar_modulos():
       global estado, combate
       from nucleo import estado
       from sistemas import combate
   ```
3. En `main.py`, debajo de `from npcs import ayudantes  # noqa: F401`, agrega `from jefes import cazador  # noqa: F401`.
4. En `main.py`, dentro del paréntesis de `for _m in (`, agrega `cazador,` antes de `bucle`.

## Si algo falla

- `NameError: name 'estado' is not defined`: ese archivo usa `estado.` pero no lo tiene en su `conectar_modulos()`. Agrégalo ahí y en su línea `global`.
- `AttributeError: module 'x' has no attribute 'y'`: `y` no está en ese archivo. Búscalo con Ctrl+Shift+F en VS Code.
