# -*- coding: utf-8 -*-
# Reproductor Acestream embebido — basado en Horus by Caperucitaferoz (GPL v3)
# https://github.com/Caperucitaferoz/Horus
#
# Adaptado para funcionar como módulo interno del addon, sin instalar Horus
# por separado. Soporta Android TV, Windows y Linux de forma transparente.

import sys
import os
import re
import time
import subprocess

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

# ---------------------------------------------------------------------------
# Detección de plataforma
# ---------------------------------------------------------------------------

def _platform():
    if xbmc.getCondVisibility('System.Platform.Android'):
        return 'android'
    if xbmc.getCondVisibility('System.Platform.Windows'):
        return 'windows'
    return 'linux'


# ---------------------------------------------------------------------------
# Punto de entrada público
# ---------------------------------------------------------------------------

def play(acestream_id, title='', port=6878, ace_path='', timeout=30):
    """
    Reproduce un canal acestream de forma nativa y sin depedencias externas.

    - Android TV : lanza la app Acestream instalada mediante Intent.
    - PC (Windows / Linux) : conecta al HTTP Engine local; si se proporciona
      ace_path y el motor no está corriendo, lo arranca automáticamente.
      Muestra diálogo de progreso durante el prebuffering.

    Parámetros
    ----------
    acestream_id : str   ID hexadecimal de 40 caracteres del canal.
    title        : str   Título que se muestra en el reproductor.
    port         : int   Puerto del Acestream Engine (por defecto 6878).
    ace_path     : str   Carpeta de instalación de Acestream en PC (opcional).
    timeout      : int   Segundos máximos de espera al engine / prebuffering.
    """
    platform = _platform()

    if platform == 'android':
        _play_android(acestream_id)
    else:
        _play_desktop(acestream_id, title, int(port), ace_path, int(timeout))


# ---------------------------------------------------------------------------
# Android
# ---------------------------------------------------------------------------

def _play_android(acestream_id):
    """Lanza la app Acestream de Android mediante StartAndroidActivity.

    Usa android.intent.action.VIEW con acestream://HASH y paquete vacío,
    dejando que Android resuelva qué app maneja el esquema acestream://.
    Funciona con cualquier versión y nombre de paquete de la app Acestream.
    """
    builtin = (
        'StartAndroidActivity("","android.intent.action.VIEW","",'
        '"acestream://{}")'.format(acestream_id)
    )
    xbmc.log('[AcestreamPlayer] Android Intent: ' + builtin, xbmc.LOGDEBUG)
    xbmc.executebuiltin(builtin)


# ---------------------------------------------------------------------------
# PC (Windows / Linux)
# ---------------------------------------------------------------------------

def _play_desktop(acestream_id, title, port, ace_path, timeout):
    from acestream.server import Server
    from acestream.stream import Stream
    from acestream.engine import Engine

    server = Server('127.0.0.1', port)

    # --- Arrancar el engine si no está corriendo ---
    engine = None
    if not server.available and ace_path:
        platform = _platform()
        if platform == 'windows':
            executable = os.path.join(ace_path, 'ace_engine.exe')
        else:
            executable = os.path.join(ace_path, 'acestream.start')

        if os.path.isfile(executable):
            engine = Engine(executable)
            engine.start()
            xbmc.log('[AcestreamPlayer] Engine arrancado: ' + executable, xbmc.LOGDEBUG)

    # --- Esperar a que el engine esté disponible ---
    if not server.available:
        dlg = xbmcgui.DialogProgress()
        dlg.create('Acestream', 'Iniciando motor...')
        deadline = time.time() + timeout

        while not dlg.iscanceled() and not server.available and time.time() < deadline:
            remaining = int(deadline - time.time())
            pct = max(0, min(100, int((timeout - remaining) * 100 / timeout)))
            try:
                dlg.update(pct, 'Esperando Acestream Engine...', '{} seg'.format(remaining))
            except Exception:
                dlg.update(pct)
            time.sleep(1)

        dlg.close()

        if dlg.iscanceled():
            return

        if not server.available:
            xbmcgui.Dialog().notification(
                'Acestream',
                'Motor no disponible en localhost:{}'.format(port),
                '', 5000
            )
            return

    # --- Iniciar el stream ---
    try:
        stream = Stream(server, id=acestream_id)
        stream.start()
    except Exception as exc:
        xbmc.log('[AcestreamPlayer] Error iniciando stream: ' + str(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Acestream', 'Error: ' + str(exc), '', 5000)
        return

    if not stream.playback_url:
        xbmcgui.Dialog().notification('Acestream', 'No se recibió URL de reproducción', '', 5000)
        return

    # --- Esperar prebuffering ---
    dlg = xbmcgui.DialogProgress()
    dlg.create('Acestream', 'Conectando...')
    deadline = time.time() + timeout

    while not dlg.iscanceled() and time.time() < deadline:
        status = stream.status                  # actualizado por _on_stats_update
        progress = stream.stats.progress
        speed    = stream.stats.speed_down
        peers    = stream.stats.peers

        if status == 'dl':
            break

        if status == 'prebuf':
            # ampliar timeout mientras prebufferiza
            deadline = time.time() + 100
            try:
                dlg.update(
                    int(progress),
                    'Prebuffering {}%'.format(int(progress)),
                    'Velocidad: {} kb/s'.format(speed),
                    'Peers: {}'.format(peers)
                )
            except Exception:
                dlg.update(int(progress))
        else:
            remaining = int(deadline - time.time())
            pct = max(0, min(100, int((timeout - remaining) * 100 / timeout)))
            try:
                dlg.update(pct, 'Conectando...', '{} seg restantes'.format(remaining))
            except Exception:
                dlg.update(pct)

        time.sleep(0.25)

    dlg.close()

    if dlg.iscanceled():
        try:
            stream.stop()
        except Exception:
            pass
        return

    if stream.status != 'dl':
        xbmcgui.Dialog().notification('Acestream', 'Tiempo de espera agotado', '', 4000)
        try:
            stream.stop()
        except Exception:
            pass
        return

    # --- Reproducir ---
    handle = int(sys.argv[1])
    li = xbmcgui.ListItem(label=title, path=stream.playback_url)
    li.setMimeType('video/mp4')
    li.setContentLookup(False)
    xbmcplugin.setResolvedUrl(handle, True, li)
    xbmc.log('[AcestreamPlayer] Reproduciendo: ' + stream.playback_url, xbmc.LOGDEBUG)
