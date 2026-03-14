# -*- coding: utf-8 -*-
# Plugin: Jodete Tebas
# Addon de canales y agenda de fútbol vía Acestream para Kodi

import sys
import os
import json

from urllib.parse import urlencode, parse_qsl, unquote_plus, quote_plus
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

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


ACESTREAM_PORT   = _get_setting('acestream_port', '6878')
DATA_URL_CANALES = 'https://jlatorreaguilar.github.io/jodeteTebas/data/canales.json'
DATA_URL_AGENDA  = 'https://jlatorreaguilar.github.io/jodeteTebas/data/agenda.json'


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
# Canales hardcodeados (ELCANO + NEW ERA + NEW LOOP)
# ---------------------------------------------------------------------------
CANALES_HARDCODED = [
    # --- DAZN ---
    {'nombre': 'DAZN 1 FHD',          'acestream_id': '691739972eb3468cf16b25e84dafdeaa40dead6d', 'categoria': 'DAZN'},
    {'nombre': 'DAZN 2 FHD',          'acestream_id': '8b081c8afbd9beafc8c5fbf0115eb36eadb07a35', 'categoria': 'DAZN'},
    {'nombre': 'DAZN 3 FHD',          'acestream_id': 'd641cd0fca0f467b3130754a091e2f4d22e68eb1', 'categoria': 'DAZN'},
    {'nombre': 'DAZN 4 FHD',          'acestream_id': '7e27e46c25d4308d16098d9dc67fcd8736e8c1f0', 'categoria': 'DAZN'},
    {'nombre': 'DAZN LA LIGA 1 FHD',  'acestream_id': 'd1596a3988b84a4d2711fd380eb8a53256ad74ae', 'categoria': 'DAZN'},
    {'nombre': 'DAZN LA LIGA 2 FHD',  'acestream_id': '635b61c1f240449163260cd914d10d886a54fee3', 'categoria': 'DAZN'},
    {'nombre': 'DAZN F1 FHD',         'acestream_id': '6422e8bc34282871634c81947be093c04ad1bb29', 'categoria': 'DAZN'},
    {'nombre': 'DAZN MOTOGP FHD',     'acestream_id': '18b03739d660f0066364343e226e437bf2555d56', 'categoria': 'DAZN'},
    # --- Movistar / M+ ---
    {'nombre': 'M+ LALIGA FHD',           'acestream_id': 'b0260a1261eb3817c353ef0a6862747dee18cdda', 'categoria': 'Movistar'},
    {'nombre': 'M+ LALIGA 2 FHD',         'acestream_id': 'caa631e8850e3eb5e7c039063dd8a339ccef1176', 'categoria': 'Movistar'},
    {'nombre': 'M+ LALIGA 3 FHD',         'acestream_id': 'c9afaf4965ad627ea6983fec9f63e0c1e857028d', 'categoria': 'Movistar'},
    {'nombre': 'MOVISTAR DEPORTES FHD',   'acestream_id': 'ef9dcc4eaac36a0f608b52a31f8ab237859e071a', 'categoria': 'Movistar'},
    {'nombre': 'MOVISTAR DEPORTES 2 FHD', 'acestream_id': 'edd06f11e1cef292a1d795e15207ef2f580e298c', 'categoria': 'Movistar'},
    {'nombre': 'MOVISTAR DEPORTES 3 FHD', 'acestream_id': '753d4b1f7c4ef43238b5cf23b05572b550a44eee', 'categoria': 'Movistar'},
    {'nombre': 'MOVISTAR DEPORTES 4 FHD', 'acestream_id': '58a4c880ab18486d914751db32a12760e74b75a4', 'categoria': 'Movistar'},
    {'nombre': 'MOVISTAR DEPORTES 5 FHD', 'acestream_id': '5913205fb6d6d162a50222709aab6129eb7cf916', 'categoria': 'Movistar'},
    {'nombre': 'MOVISTAR DEPORTES 6 FHD', 'acestream_id': 'e4124b2143ed75e5ce902bed61be08cc5e5c3c03', 'categoria': 'Movistar'},
    {'nombre': 'MOVISTAR VAMOS FHD',      'acestream_id': '3b2a8b41e7097c16b0468b42d7de0320886fa933', 'categoria': 'Movistar'},
    # --- LaLiga / Hypermotion ---
    {'nombre': 'HYPERMOTION FHD',   'acestream_id': '58b1c4b8cb65d648505b035a04e879672fcd8e3f', 'categoria': 'LaLiga'},
    {'nombre': 'HYPERMOTION 2',     'acestream_id': '3a21e651c0bffe810cfc8537065cb81f5ed68a55', 'categoria': 'LaLiga'},
    {'nombre': 'HYPERMOTION 3',     'acestream_id': '1fdb405a6942da0941266f24cdd1c71b11552f1f', 'categoria': 'LaLiga'},
    {'nombre': 'GOL PLAY FHD',      'acestream_id': '9fb99c40a2c45d5c5342b30626eb56140f980612', 'categoria': 'LaLiga'},
    # --- Champions League ---
    {'nombre': 'LIGA DE CAMPEONES FHD',   'acestream_id': 'c16b4fab1f724c94cad92081cbb7fc7c6fe8a2cc', 'categoria': 'Champions'},
    {'nombre': 'LIGA DE CAMPEONES 2 FHD', 'acestream_id': 'c6a3673f6a37b1bd3cf31fdd6404dd33d48cfccb', 'categoria': 'Champions'},
    {'nombre': 'LIGA DE CAMPEONES 3 FHD', 'acestream_id': '17b8bc4bf8e29547b0071c742e3d7da3bcbc484d', 'categoria': 'Champions'},
    # --- Generales / Otros ---
    {'nombre': 'TELEDEPORTE FHD',      'acestream_id': '2d997da301573c5aba78f969d0d37eb6107941b2', 'categoria': 'General'},
    {'nombre': 'EUROSPORT 1 FHD',      'acestream_id': 'bae98f69fbf867550b4f73b4eb176dae84d7f909', 'categoria': 'General'},
    {'nombre': 'EUROSPORT 2 FHD',      'acestream_id': 'dc4ccb9e72550bc72be9360aa7d77e337ad11ecc', 'categoria': 'General'},
    {'nombre': 'REAL MADRID TV HD',    'acestream_id': '7a955964c91c66311eef9137a96332352dbb891e', 'categoria': 'General'},
    {'nombre': 'BEIN SPORTS 1',        'acestream_id': '58e454d067b9e25e40f3c62b3430b55ef6fead09', 'categoria': 'General'},
    {'nombre': 'BEIN SPORTS 2',        'acestream_id': 'fa0a5dd9ecc3febbda8b6e1805c539a93fe515ac', 'categoria': 'General'},
    {'nombre': 'SKY SPORTS MAIN EVENT','acestream_id': 'e4b259b6dedb674283ab124117ce793360d3a1c0', 'categoria': 'General'},
    {'nombre': 'SKY SPORTS FOOTBALL',  'acestream_id': '54de746f7823812312b4000422618465f7d58f87', 'categoria': 'General'},
    {'nombre': 'LA 1 FHD',             'acestream_id': 'dad5e0e0825cb3e410008f1c4252387b868e740c', 'categoria': 'General'},
    {'nombre': 'CUATRO FHD',           'acestream_id': '8d66979e705a8b532b9243bbc0862c0f1c734ef0', 'categoria': 'General'},
    {'nombre': 'TELECINCO',            'acestream_id': '3840043b15fd7ac7846004d151ea7b51800fffc0', 'categoria': 'General'},
]


# ---------------------------------------------------------------------------
# Sección CANALES
# ---------------------------------------------------------------------------
def show_canales():
    xbmcplugin.setPluginCategory(HANDLE, 'Canales')
    xbmcplugin.setContent(HANDLE, 'videos')

    canales = []
    data_text = fetch_url(DATA_URL_CANALES)
    if data_text:
        try:
            canales = json.loads(data_text).get('canales', [])
        except (ValueError, KeyError) as e:
            log('Error parsing canales.json: {}'.format(str(e)), xbmc.LOGERROR)
    if not canales:
        canales = CANALES_HARDCODED

    for canal in canales:
        nombre       = canal['nombre']
        acestream_id = canal['acestream_id']
        categoria    = canal.get('categoria', '')

        li = xbmcgui.ListItem(nombre)
        li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
        li.setInfo('video', {
            'title'     : nombre,
            'genre'     : categoria,
            'mediatype' : 'video'
        })
        li.setProperty('IsPlayable', 'true')

        ace_url = build_url({'mode': 'play', 'acestream_id': acestream_id, 'title': nombre})
        xbmcplugin.addDirectoryItem(HANDLE, ace_url, li, False)

    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(HANDLE)


# ---------------------------------------------------------------------------
# Sección AGENDA
# ---------------------------------------------------------------------------
def show_agenda():
    xbmcplugin.setPluginCategory(HANDLE, 'Agenda')
    xbmcplugin.setContent(HANDLE, 'videos')

    data_text = fetch_url(DATA_URL_AGENDA)
    if not data_text:
        xbmcplugin.endOfDirectory(HANDLE)
        return

    try:
        data    = json.loads(data_text)
        eventos = data.get('eventos', [])

        if not eventos:
            xbmcgui.Dialog().notification(ADDON_NAME, 'No hay eventos en la agenda', ICON, 4000)
            xbmcplugin.endOfDirectory(HANDLE)
            return

        for evento in eventos:
            titulo       = evento.get('titulo', 'Evento')
            acestream_id = evento.get('acestream_id', '')
            fecha        = evento.get('fecha', '')
            hora         = evento.get('hora', '')

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
            li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
            li.setInfo('video', {
                'title'     : titulo,
                'plot'      : '{} {}'.format(fecha, hora).strip(),
                'mediatype' : 'video'
            })
            li.setProperty('IsPlayable', 'true')

            ace_url = build_url({'mode': 'play', 'acestream_id': acestream_id, 'title': titulo})
            xbmcplugin.addDirectoryItem(HANDLE, ace_url, li, False)

    except (ValueError, KeyError) as e:
        log('Error parsing agenda.json: {}'.format(str(e)), xbmc.LOGERROR)
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
