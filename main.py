"""Ébanon // Motor de Supervivencia — punto de entrada.

Ejecuta:  py -3.12 main.py
(desde la carpeta del juego, junto a los PNG, sonidos y la carpeta sprites/)
"""
# Importar todos los módulos en este orden carga el juego completo.
# Algunos módulos agregan cosas a tablas compartidas (BUILD_COSTS, ITEM_NAMES, etc.),
# por eso hay que importarlos todos aunque aquí no se usen directamente.
from nucleo import ajustes  # noqa: F401
from nucleo import estado  # noqa: F401
from nucleo import mundo  # noqa: F401
from nucleo import entidades  # noqa: F401
from sistemas import spawn  # noqa: F401
from sistemas import ciclo_dia  # noqa: F401
from sistemas import colision  # noqa: F401
from sistemas import construccion  # noqa: F401
from sistemas import combate  # noqa: F401
from sistemas import interaccion  # noqa: F401
from sistemas import almacen  # noqa: F401
from sistemas import crafteo  # noqa: F401
from sistemas import actualizacion  # noqa: F401
from jefes import hombre_reloj  # noqa: F401
from jefes import baca_jefe  # noqa: F401
from jefes import makadewaa  # noqa: F401
from jefes import baca_pico  # noqa: F401
from sistemas import recursos  # noqa: F401
from sistemas import camara  # noqa: F401
from interfaz import dibujo  # noqa: F401
from interfaz import hud  # noqa: F401
from interfaz import menus  # noqa: F401
from sistemas import guardado  # noqa: F401
from sistemas import partida  # noqa: F401
from mapas import mina  # noqa: F401
from sistemas import ambiente  # noqa: F401
from sistemas import tiburones  # noqa: F401
from jefes import neri_jefe  # noqa: F401
from jefes import tonico  # noqa: F401
from mapas import barco  # noqa: F401
from mapas import fundidora  # noqa: F401
from mapas import transicion  # noqa: F401
from mapas import refineria  # noqa: F401
from mapas import deshuesadero  # noqa: F401
from npcs import ayudantes  # noqa: F401
from sistemas import habilidades  # noqa: F401
from sistemas import estaciones  # noqa: F401
from sistemas import hogar  # noqa: F401
from sistemas import clima  # noqa: F401
from sistemas import exploracion  # noqa: F401
from sistemas import eventos  # noqa: F401
from interfaz import inventario  # noqa: F401
from sistemas import salto  # noqa: F401
from nucleo import bucle

# Con todo cargado, cada archivo se conecta con los módulos que usa mientras corre el juego.
for _m in (
    ajustes, estado, mundo, entidades, spawn, ciclo_dia, colision, construccion, combate,
    interaccion, almacen, crafteo, actualizacion, hombre_reloj, baca_jefe, makadewaa,
    baca_pico, recursos, camara, dibujo, hud, menus, guardado, partida, mina, ambiente,
    neri_jefe, tonico, barco, fundidora, transicion, refineria, deshuesadero, ayudantes,
    tiburones, habilidades, estaciones, hogar, clima, exploracion, eventos, inventario, salto, bucle
):
    _f = getattr(_m, "conectar_modulos", None)
    if _f is not None and _f.__module__ == _m.__name__:
        _f()


if __name__ == "__main__":
    bucle.main()
