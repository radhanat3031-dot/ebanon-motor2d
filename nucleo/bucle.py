"""Bucle principal del juego (main).

Salió de ebanon.py (original), alrededor de las líneas 9171-9405.
"""

import os
import sys
import pygame
from nucleo.ajustes import *  # noqa: F401,F403


def conectar_modulos():
    """Conecta este archivo con los demás módulos que usa mientras corre el juego.
    main.py la llama cuando todos los módulos ya cargaron (así no hay imports circulares)."""
    global actualizacion, almacen, ambiente, ayudantes, baca_jefe
    global barco, camara, ciclo_dia, colision, combate
    global construccion, deshuesadero, dibujo, estado, fundidora
    global guardado, hombre_reloj, hud, makadewaa, menus
    global mina, neri_jefe, partida, recursos, refineria
    global tonico, transicion
    global tiburones
    global hogar
    global clima
    global exploracion
    global eventos
    global salto
    from interfaz import dibujo, hud, menus
    from jefes import baca_jefe, hombre_reloj, makadewaa, neri_jefe, tonico
    from mapas import barco, deshuesadero, fundidora, mina, refineria, transicion
    from npcs import ayudantes
    from nucleo import estado
    from sistemas import actualizacion, almacen, ambiente, camara, ciclo_dia, colision, combate, construccion, guardado, partida, recursos
    from sistemas import tiburones
    from sistemas import hogar
    from sistemas import clima
    from sistemas import exploracion
    from sistemas import eventos
    from sistemas import salto


# ----------------------------------------------------------------------------
# 17. BUCLE PRINCIPAL
# ----------------------------------------------------------------------------
def main():
    colision.rebuild_prop_tiles()
    
    attack_pressed = False
    interact_pressed = False
    inv_buttons, storage_buttons, build_buttons, pause_buttons = {}, {}, {}, {}
    start_buttons, retry_button_rect = {}, None
    guardado.migrate_old_save()
    guardado.refresh_saves()
    slot_buttons, name_buttons = {}, {}
    
    while True:
        dt = min(clock.tick(60) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if estado.game_state == STATE_PLAYING:
                    guardado.save_game()
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if estado.game_state == STATE_PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        if estado.inventory_open or estado.build_menu_open or estado.active_chest or barco.boat["open"]:
                            estado.inventory_open = False
                            estado.build_menu_open = False
                            barco.boat["open"] = False
                            almacen.close_storage()
                            construccion.clear_build_selection()                            
                        else:
                            estado.pause_menu_open = not estado.pause_menu_open
                    elif not estado.pause_menu_open:
                        if event.key == pygame.K_e:
                            interact_pressed = True
                        elif event.key == pygame.K_i:
                            pygame.mixer.Channel(8).play(bag_sound)  # sonido al presionar Q
                            if estado.active_chest:
                                almacen.close_storage()
                            else:
                                estado.inventory_open = not estado.inventory_open
                        elif event.key == pygame.K_b:
                            estado.build_menu_open = not estado.build_menu_open
                            if not estado.build_menu_open:
                                construccion.clear_build_selection()
                        elif event.key == pygame.K_TAB:
                            combate.cycle_weapon()
                        elif event.key == pygame.K_x:
                            construccion.dismantle_at_mouse()                            
                        elif event.key == pygame.K_g and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            estado.god_mode = not estado.god_mode
                            estado.log(f"MODO DIOS {'ACTIVADO' if estado.god_mode else 'DESACTIVADO'}.")
                        elif event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            if estado.boss is None:
                                hombre_reloj.spawn_boss()
                            estado.log(f"MODO DIOS {'EL HOMBRE DEL RELOJ ACTIVADO'}.")      
                        elif event.key == pygame.K_j and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            if not any(b.kind == "boss" for b in estado.bears):
                                makadewaa.spawn_bear("boss")       
                        elif event.key == pygame.K_k and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            makadewaa.spawn_bear("weak", (6, 9))       # un oso débil cerca, sin aggro                                                          
                        elif estado.inventory_open and event.key in DROP_KEYS:
                            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                                construccion.drop_item(DROP_KEYS[event.key], 999)
                            else:
                                construccion.drop_item(DROP_KEYS[event.key], 1)
                        elif event.key == pygame.K_c and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            hogar.cook()
                        elif event.key == pygame.K_t and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            exploracion.toggle_diary()
                        elif event.key == salto.TECLA_SALTO:
                            salto.start()
                        elif event.key == pygame.K_l and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            if baca_jefe.baca is None:
                                baca_jefe.spawn_baca()
                        elif event.key == refineria.DYNAMITE_KEY and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            refineria.light_dynamite()
                        elif event.key == pygame.K_w and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            ayudantes.debug_elder()
                        elif event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            ayudantes.elder_collapse()
                        elif event.key == pygame.K_n and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            ayudantes.debug_girl()
                        elif event.key == pygame.K_u and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            deshuesadero.debug_junk()                            
                        elif event.key == pygame.K_r and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            refineria.debug_dynamite()                                
                        elif event.key == pygame.K_y and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            tonico.debug_tonic()
                        elif event.key == pygame.K_b and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            barco.debug_boat()
                        elif event.key == pygame.K_f and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            fundidora.debug_foundry()                            
                        elif event.key == pygame.K_m and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            if estado.in_mine:
                                transicion.leave_mine()
                            else:
                                transicion.enter_mine()                                
                        elif estado.build_menu_open and event.key in BUILD_KEYS:
                            construccion.select_build(BUILD_KEYS[event.key])
                elif estado.game_state == STATE_GAMEOVER:
                    if event.key == pygame.K_RETURN:
                        partida.start_game(new_game=True)
                elif estado.game_state == STATE_START:
                    if event.key == pygame.K_RETURN:
                        partida.start_game(new_game=not os.path.exists(SAVE_FILE))
                    elif estado.game_state == STATE_GAMEOVER:
                        if event.key == pygame.K_RETURN:
                            menus.open_name_screen()   # en vez de start_game()

                elif estado.game_state == STATE_START:
                        if event.key == pygame.K_RETURN:
                            if estado.save_slots:
                                menus.open_slots_screen()   # muestra pantalla de slots
                            else:
                                menus.open_name_screen()    # pantalla para poner nombre

                elif estado.game_state == STATE_SLOTS:
                    if event.key == pygame.K_ESCAPE:
                        menus.back_to_start()           # regresa al menú inicial

                elif estado.game_state == STATE_NAME:
                    menus.handle_name_key(event)        # procesa teclas para escribir nombre
                    
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == tonico.DASH_MOUSE_BUTTON \
                    and estado.game_state == STATE_PLAYING:
                tonico.try_dash()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if estado.game_state == STATE_START:
                    if start_buttons.get("continue") and start_buttons["continue"].collidepoint(pos):
                        menus.open_slots_screen()
                    elif start_buttons.get("new") and start_buttons["new"].collidepoint(pos):
                        menus.open_name_screen()
                    elif start_buttons.get("quit") and start_buttons["quit"].collidepoint(pos):
                        pygame.quit()
                        sys.exit()
                elif estado.game_state == STATE_SLOTS:
                    menus.handle_slots_click(pos, slot_buttons)
                elif estado.game_state == STATE_NAME:
                    menus.handle_name_click(pos, name_buttons)
                elif estado.game_state == STATE_GAMEOVER and retry_button_rect and retry_button_rect.collidepoint(pos):
                    menus.open_name_screen()
                elif estado.game_state == STATE_PLAYING:
                    if estado.pause_menu_open:
                        menus.handle_pause_click(pos, pause_buttons)
                    elif estado.inventory_open:
                        menus.handle_inventory_click(pos, inv_buttons)
                    elif estado.active_chest:
                        menus.handle_storage_click(pos, storage_buttons)
                    elif barco.boat["open"]:
                        fundidora.handle_boat_click(pos, barco.boat_ui["buttons"])
                    elif estado.build_menu_open:
                        panel_rect = estado.build_ui["panel"]
                        if panel_rect is not None and panel_rect.collidepoint(pos):
                            construccion.handle_build_click(pos, build_buttons)
                        elif estado.build_selected:
                            construccion.attempt_place_structure(*construccion.screen_to_world(*pos))
                        else:
                            attack_pressed = True
                    else:
                        attack_pressed = True                        
        if estado.game_state == STATE_PLAYING:
            paused_by_menu = estado.inventory_open or (estado.active_chest is not None) or estado.pause_menu_open or barco.boat["open"]
            if paused_by_menu:
                pygame.mixer.Channel(1).stop()
                pygame.mixer.Channel(15).pause()        
            if not paused_by_menu:
                colision.rebuild_prop_tiles()             
                actualizacion.update_aim_from_mouse()
                ciclo_dia.update_day_night(dt)
                ambiente.update_rain(dt)
                actualizacion.update_player(dt, pygame.key.get_pressed(), attack_pressed, interact_pressed)
                actualizacion.update_zombies(dt)
                actualizacion.update_traps(dt)                  # (justo después de update_zombies)
                construccion.update_fires(dt)
                pygame.mixer.Channel(15).unpause()      
                construccion.update_fire_sound()                                 
                if not estado.in_mine:
                    hombre_reloj.update_boss(dt)
                mina.update_bats(dt)        
                neri_jefe.update_lair(dt)        
                neri_jefe.update_neri(dt)
                tonico.update_dash(dt)
                fundidora.update_furnace(dt)
                refineria.update_dynamite(dt)
                deshuesadero.update_junkyard(dt)
                ayudantes.update_girl(dt)
                ayudantes.update_elder(dt)
                actualizacion.update_bullets(dt)
                salto.update(dt)
                exploracion.update(dt)
                eventos.update(dt)
                clima.update(dt)
                hogar.update(dt)
                tiburones.update_sharks(dt)
                recursos.update_all_pickups(dt)
                camara.update_camera()
            attack_pressed = False
            interact_pressed = False
            
            dibujo.render_world(screen)
            hud.render_hud(screen)
            if estado.build_menu_open:
                build_buttons = hud.render_build_menu(screen)
            if estado.inventory_open:
                inv_buttons = menus.render_inventory(screen)
            if estado.active_chest:
                storage_buttons = menus.render_storage(screen)
            if barco.boat["open"]:
                barco.boat_ui["buttons"] = fundidora.render_boat_panel(screen)
            if estado.pause_menu_open:
                pause_buttons = menus.render_pause_menu(screen)
        elif estado.game_state == STATE_START:
            pygame.mixer.Channel(15).stop()
            if not pygame.mixer.music.get_busy():
                partida.start_menu_audio()
            start_buttons = menus.render_start_screen(screen)
            
        elif estado.game_state == STATE_SLOTS:
            slot_buttons = menus.render_slots_screen(screen)

        elif estado.game_state == STATE_NAME:
            name_buttons = menus.render_name_screen(screen)            
        
        elif estado.game_state == STATE_GAMEOVER:
            # Detiene sonidos de pasos/loop que puedan seguir sonando
            try:
                pygame.mixer.Channel(1).stop()
            except Exception:
                pass

            # Limpia inputs para evitar acciones residuales
            attack_pressed = False
            interact_pressed = False

            # Dibuja la pantalla de Game Over y guarda el rect del botón Retry
            # (implementa render_gameover_screen para devolver el rect del botón)
            retry_button_rect = menus.render_gameover_screen(screen)
            
        pygame.display.flip()
