# -*- coding: utf-8 -*-
# Plugin: Jodete Tebas
# Addon de canales y agenda de fútbol vía Acestream para Kodi

import sys
import os
import json

try:
    from urllib.parse import urlencode, parse_qsl, unquote_plus, quote_plus
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
except ImportError:
    from urllib import urlencode, unquote_plus, quote_plus
    from urllib2 import urlopen, Request, URLError, HTTPError
    from urlparse import parse_qsl

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

# ---------------------------------------------------------------------------
# Constantes del addon
# ---------------------------------------------------------------------------
ADDON         = xbmcaddon.Addon()
ADDON_ID      = ADDON.getAddonInfo('id')
ADDON_NAME    = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH    = ADDON.getAddonInfo('path')
ICON          = os.path.join(ADDON_PATH, 'icon.png')
FANART        = os.path.join(ADDON_PATH, 'fanart.jpg')

HANDLE   = int(sys.argv[1])
BASE_URL = sys.argv[0]
PARAMS   = dict(parse_qsl(sys.argv[2][1:]))


def _get_setting(key, default=''):
    val = ADDON.getSetting(key)
    return val if val else default


SOURCE_URL     = _get_setting('source_url', 'https://eventos-eight-dun.vercel.app/')
ACESTREAM_PORT = _get_setting('acestream_port', '6878')


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log('[{}-{}]: {}'.format(ADDON_ID, ADDON_VERSION, msg), level)


def build_url(params):
    return '{}?{}'.format(BASE_URL, urlencode(params))


def fetch_url(url):
    """Realiza una petición HTTP y devuelve el contenido como texto."""
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
        }
        req      = Request(url, headers=headers)
        response = urlopen(req, timeout=15)
        data     = response.read().decode('utf-8', errors='ignore')
        response.close()
        return data
    except (URLError, HTTPError) as e:
        log('Error fetching {}: {}'.format(url, str(e)), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            ADDON_NAME, 'Error de conexión: {}'.format(str(e)), ICON, 5000
        )
        return None


def add_menu_item(label, mode, is_folder=True, icon=None, description=''):
    """Añade un elemento de directorio al menú."""
    li = xbmcgui.ListItem(label)
    li.setArt({'icon': icon or ICON, 'thumb': icon or ICON, 'fanart': FANART})
    li.setInfo('video', {'title': label, 'plot': description})
    url = build_url({'mode': mode})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, is_folder)


# ---------------------------------------------------------------------------
# Menú principal
# ---------------------------------------------------------------------------
def main_menu():
    xbmcplugin.setPluginCategory(HANDLE, ADDON_NAME)
    xbmcplugin.setContent(HANDLE, 'videos')

    add_menu_item(
        label       = '[COLOR FFFFFF00]Agenda[/COLOR]',
        mode        = 'agenda',
        description = 'Partidos y eventos programados'
    )
    add_menu_item(
        label       = '[COLOR FF00FFFF]Canales[/COLOR]',
        mode        = 'canales',
        description = 'Canales de televisión en directo'
    )

    xbmcplugin.endOfDirectory(HANDLE)


# ---------------------------------------------------------------------------
# Sección CANALES
# ---------------------------------------------------------------------------
def show_canales():
    xbmcplugin.setPluginCategory(HANDLE, 'Canales')
    xbmcplugin.setContent(HANDLE, 'videos')

    data_text = fetch_url(SOURCE_URL)
    if not data_text:
        xbmcplugin.endOfDirectory(HANDLE)
        return

    try:
        data    = json.loads(data_text)
        canales = data.get('canales', data.get('channels', []))

        if not canales:
            xbmcgui.Dialog().notification(ADDON_NAME, 'No se encontraron canales', ICON, 4000)
            xbmcplugin.endOfDirectory(HANDLE)
            return

        for canal in canales:
            nombre       = canal.get('nombre', canal.get('name', 'Canal'))
            acestream_id = canal.get('acestream_id', canal.get('id', ''))
            logo         = canal.get('logo', canal.get('icon', canal.get('thumbnail', ICON)))
            categoria    = canal.get('categoria', canal.get('category', ''))
            descripcion  = canal.get('descripcion', canal.get('description', ''))

            if not acestream_id:
                continue

            li = xbmcgui.ListItem(nombre)
            li.setArt({'icon': logo, 'thumb': logo, 'fanart': FANART})
            li.setInfo('video', {
                'title'     : nombre,
                'genre'     : categoria,
                'plot'      : descripcion,
                'mediatype' : 'video'
            })
            li.setProperty('IsPlayable', 'true')

            ace_url = build_url({'mode': 'play', 'acestream_id': acestream_id, 'title': nombre})
            xbmcplugin.addDirectoryItem(HANDLE, ace_url, li, False)

        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL)

    except (ValueError, KeyError) as e:
        log('Error parsing canales: {}'.format(str(e)), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, 'Error al cargar canales', ICON, 5000)

    xbmcplugin.endOfDirectory(HANDLE)


# ---------------------------------------------------------------------------
# Sección AGENDA
# ---------------------------------------------------------------------------
def show_agenda():
    xbmcplugin.setPluginCategory(HANDLE, 'Agenda')
    xbmcplugin.setContent(HANDLE, 'videos')

    data_text = fetch_url(SOURCE_URL)
    if not data_text:
        xbmcplugin.endOfDirectory(HANDLE)
        return

    try:
        data    = json.loads(data_text)
        eventos = data.get('agenda', data.get('eventos', data.get('events', [])))

        if not eventos:
            xbmcgui.Dialog().notification(ADDON_NAME, 'No hay eventos en la agenda', ICON, 4000)
            xbmcplugin.endOfDirectory(HANDLE)
            return

        for evento in eventos:
            titulo       = evento.get('titulo', evento.get('title', 'Evento'))
            acestream_id = evento.get('acestream_id', evento.get('id', ''))
            fecha        = evento.get('fecha', evento.get('date', ''))
            hora         = evento.get('hora', evento.get('time', ''))
            categoria    = evento.get('categoria', evento.get('category', ''))
            descripcion  = evento.get('descripcion', evento.get('description', ''))
            logo         = evento.get('logo', evento.get('icon', evento.get('thumbnail', ICON)))

            if not acestream_id:
                continue

            # Formato de etiqueta: [hora] Título del evento
            if hora:
                label = '[COLOR FFFFFF00]{}[/COLOR]  {}'.format(hora, titulo)
            elif fecha:
                label = '[COLOR FFFFFF00]{}[/COLOR]  {}'.format(fecha, titulo)
            else:
                label = titulo

            li = xbmcgui.ListItem(label)
            li.setArt({'icon': logo, 'thumb': logo, 'fanart': FANART})
            li.setInfo('video', {
                'title'     : titulo,
                'genre'     : categoria,
                'plot'      : descripcion or '{} - {}'.format(fecha, hora).strip(' -'),
                'aired'     : fecha,
                'mediatype' : 'video'
            })
            li.setProperty('IsPlayable', 'true')

            ace_url = build_url({'mode': 'play', 'acestream_id': acestream_id, 'title': titulo})
            xbmcplugin.addDirectoryItem(HANDLE, ace_url, li, False)

    except (ValueError, KeyError) as e:
        log('Error parsing agenda: {}'.format(str(e)), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, 'Error al cargar la agenda', ICON, 5000)

    xbmcplugin.endOfDirectory(HANDLE)


# ---------------------------------------------------------------------------
# Reproducción vía Acestream
# ---------------------------------------------------------------------------
def play_acestream(acestream_id, title=''):
    """Construye la URL de Acestream y la pasa a Kodi para reproducir."""
    port       = ACESTREAM_PORT
    stream_url = 'http://127.0.0.1:{}/ace/getstream?id={}'.format(port, acestream_id)

    log('Reproduciendo acestream: {}'.format(stream_url))

    li = xbmcgui.ListItem(label=title, path=stream_url)
    li.setMimeType('video/mp4')
    li.setContentLookup(False)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


# ---------------------------------------------------------------------------
# Router principal
# ---------------------------------------------------------------------------
def router():
    mode = PARAMS.get('mode')

    if mode is None:
        main_menu()
    elif mode == 'canales':
        show_canales()
    elif mode == 'agenda':
        show_agenda()
    elif mode == 'play':
        acestream_id = PARAMS.get('acestream_id', '')
        title        = unquote_plus(PARAMS.get('title', ''))
        if acestream_id:
            play_acestream(acestream_id, title)
        else:
            xbmcgui.Dialog().notification(ADDON_NAME, 'ID de Acestream no válido', ICON, 4000)
    else:
        main_menu()


if __name__ == '__main__':
    router()
