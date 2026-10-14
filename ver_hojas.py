"""Muestra cómo quedan tus hojas de sprites, para comprobar que cada dirección es la correcta.

Uso (desde la carpeta del juego):
    py -3.12 ver_hojas.py            todas las hojas, una por una
    py -3.12 ver_hojas.py nina       solo esa

Teclas:  ←  →  cambiar de hoja   ·   ESC  salir
Cada fila es una dirección con sus pasos de caminata, y a la derecha se ve animada.
Si una fila no coincide con su nombre (por ejemplo "arriba" muestra al personaje de frente),
corrige el "orden" de esa hoja en nucleo/hojas.py y vuelve a abrir esto.
"""
import sys

import pygame
from nucleo import hojas

VISTA = [("up", "arriba"), ("down", "abajo"), ("left", "izquierda"), ("right", "derecha")]


def dibujar(pantalla, fuente, nombre, frames, i, total, t):
    pantalla.fill((30, 34, 38))
    pantalla.blit(fuente.render(f"{nombre}   ({i + 1}/{total})      ←  →  cambiar de hoja   ·   ESC  salir",
                                True, (235, 235, 235)), (16, 12))
    pantalla.blit(fuente.render(hojas.describir(nombre), True, (170, 190, 150)), (16, 40))
    if frames is None:
        pantalla.blit(fuente.render("No se pudo cargar esta hoja: mira el mensaje en la consola.", True, (230, 120, 100)),
                      (16, 90))
        return
    y = 80
    for clave, etiqueta in VISTA:
        pantalla.blit(fuente.render(etiqueta, True, (240, 220, 140)), (16, y + 28))
        for k, fr in enumerate(frames[clave]):
            pantalla.blit(fr, (130 + k * (fr.get_width() + 8), y))
        anim = frames[clave][int(t * 6) % len(frames[clave])]
        pantalla.blit(anim, (130 + 4 * (anim.get_width() + 8) + 40, y))
        y += frames[clave][0].get_height() + 12


def main():
    nombres = [a for a in sys.argv[1:] if a in hojas.HOJAS] or list(hojas.HOJAS)
    pygame.init()
    pantalla = pygame.display.set_mode((900, 640))
    pygame.display.set_caption("Hojas de sprites")
    fuente = pygame.font.SysFont("consolas", 18)
    reloj = pygame.time.Clock()
    cache = {n: hojas.cargar(n, 3) for n in nombres}
    i = 0
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RIGHT:
                i = (i + 1) % len(nombres)
            if e.type == pygame.KEYDOWN and e.key == pygame.K_LEFT:
                i = (i - 1) % len(nombres)
        dibujar(pantalla, fuente, nombres[i], cache[nombres[i]], i, len(nombres), pygame.time.get_ticks() / 1000)
        pygame.display.flip()
        reloj.tick(30)


if __name__ == "__main__":
    main()
