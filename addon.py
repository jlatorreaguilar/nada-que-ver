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

# Añadir resources/lib al path para las libs de acestream integradas
_ADDON_PATH_EARLY = xbmcaddon.Addon().getAddonInfo('path')
_LIB_PATH = os.path.join(_ADDON_PATH_EARLY, 'resources', 'lib')
if _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)

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
ACESTREAM_PATH   = _get_setting('acestream_path', '')   # ruta de instalación en PC (opcional)
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
# Fallback: canales hardcodeados (ELCANO) usados si GitHub Pages no responde
# ---------------------------------------------------------------------------
CANALES_FALLBACK = [
    {'categoria': 'DAZN',      'nombre': 'DAZN 1',           'acestream_id': '9afc89481b721ce6c326c85e47148676077b8e62', 'fuente': 'ELCANO'},
    {'categoria': 'DAZN',      'nombre': 'DAZN 2 1080p',     'acestream_id': '13a16a0630ae87bd97d6ba4165963c201c9a2e9c', 'fuente': 'ELCANO'},
    {'categoria': 'DAZN',      'nombre': 'DAZN 3',           'acestream_id': 'e1ccce973c71547a8acda770885cb1c30a9cf3e1', 'fuente': 'ELCANO'},
    {'categoria': 'LA LIGA',   'nombre': 'DAZN LaLiga 1080p','acestream_id': 'cc108ae39f92c48f6c946763047bd1c9b7b7d889', 'fuente': 'ELCANO'},
    {'categoria': 'LA LIGA',   'nombre': 'M+ LaLiga 1080p',  'acestream_id': '0febfb5cac3384f487d55c559bbfc877db2d0357', 'fuente': 'ELCANO'},
    {'categoria': 'HYPERMOTION','nombre': 'LaLiga TV Hypermotion 1080p','acestream_id': '4636ed75106cb00e9c70cc2029edf0a4df7ad73f','fuente':'ELCANO'},
    {'categoria': 'LIGA DE CAMPEONES','nombre': 'M+ Liga de Campeones 1080p','acestream_id': '91b2a1fe85f5bb4a6cf9ef6d01cc65883d986920','fuente':'ELCANO'},
    {'categoria': 'EUROSPORT', 'nombre': 'Eurosport 1 1080p','acestream_id': '48a589dbeab3544662fafd79888aada7d834cfe9', 'fuente': 'ELCANO'},
]


# ---------------------------------------------------------------------------
# Cache en memoria para no descargar canales.json en cada apertura de carpeta
# ---------------------------------------------------------------------------
_canales_cache = None


def _get_categorias():
    """Descarga canales.json y devuelve la lista de categorías. Usa caché."""
    global _canales_cache
    if _canales_cache is not None:
        return _canales_cache

    data_text = fetch_url(DATA_URL_CANALES)
    if data_text:
        try:
            data = json.loads(data_text)
            cats = data.get('categorias', [])
            if cats:
                _canales_cache = cats
                return cats
        except (ValueError, KeyError) as e:
            log('Error parsing canales.json: {}'.format(str(e)), xbmc.LOGERROR)

    # Fallback: convertir la lista plana en [{"nombre": cat, "canales": [...]}]
    log('Usando canales fallback', xbmc.LOGWARNING)
    grupos = {}
    for c in CANALES_FALLBACK:
        cat = c['categoria']
        if cat not in grupos:
            grupos[cat] = []
        grupos[cat].append(c)
    return [{'nombre': k, 'canales': v} for k, v in grupos.items()]


# ---------------------------------------------------------------------------
# Sección CANALES  → muestra las subcategorías
# ---------------------------------------------------------------------------
def show_canales():
    xbmcplugin.setPluginCategory(HANDLE, 'Canales')
    xbmcplugin.setContent(HANDLE, 'files')

    categorias = _get_categorias()
    for cat in categorias:
        nombre = cat['nombre']
        total  = len(cat.get('canales', []))
        label  = '[COLOR FF00FFFF]{}[/COLOR]  ({})'.format(nombre, total)

        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
        li.setInfo('video', {'title': nombre})
        url = build_url({'mode': 'categoria', 'cat': nombre})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, True)

    xbmcplugin.endOfDirectory(HANDLE)


# ---------------------------------------------------------------------------
# Sección de CATEGORÍA  → muestra todos los enlaces de esa categoría
# formato: "NOMBRE short_id --> FUENTE"  (igual que KodispainTV)
# ---------------------------------------------------------------------------
def show_categoria(cat_nombre):
    xbmcplugin.setPluginCategory(HANDLE, cat_nombre)
    xbmcplugin.setContent(HANDLE, 'videos')

    categorias = _get_categorias()
    canales = []
    for cat in categorias:
        if cat['nombre'].upper() == cat_nombre.upper():
            canales = cat.get('canales', [])
            break

    if not canales:
        xbmcgui.Dialog().notification(ADDON_NAME, 'No hay canales en esta categoría', ICON, 3000)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    for canal in canales:
        nombre       = canal.get('nombre', '')
        acestream_id = canal.get('acestream_id', '')
        short_id     = canal.get('short_id', acestream_id[:4] if acestream_id else '')
        fuente       = canal.get('fuente', 'ELCANO')

        # Formato idéntico al de KodispainTV: "NOMBRE short_id --> FUENTE"
        label = '{} {} --> {}'.format(nombre, short_id, fuente)

        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
        li.setInfo('video', {'title': label, 'genre': cat_nombre, 'mediatype': 'video'})
        li.setProperty('IsPlayable', 'true')

        ace_url = build_url({'mode': 'play', 'acestream_id': acestream_id, 'title': label})
        xbmcplugin.addDirectoryItem(HANDLE, ace_url, li, False)

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

            if hora:
                label = '[COLOR FFFFFF00]{}[/COLOR]  {}'.format(hora, titulo)
            elif fecha:
                label = '[COLOR FFFFFF00]{}[/COLOR]  {}'.format(fecha, titulo)
            else:
                label = titulo

            li = xbmcgui.ListItem(label)
            li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
            li.setInfo('video', {
                'title'    : titulo,
                'plot'     : '{} {}'.format(fecha, hora).strip(),
                'mediatype': 'video'
            })
            li.setProperty('IsPlayable', 'true')

            ace_url = build_url({'mode': 'play', 'acestream_id': acestream_id, 'title': titulo})
            xbmcplugin.addDirectoryItem(HANDLE, ace_url, li, False)

    except (ValueError, KeyError) as e:
        log('Error parsing agenda.json: {}'.format(str(e)), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, 'Error al cargar la agenda', ICON, 5000)

    xbmcplugin.endOfDirectory(HANDLE)


# ---------------------------------------------------------------------------
# Reproducción vía Acestream — delegado en horus_player embebido
# ---------------------------------------------------------------------------
def play_acestream(acestream_id, title=''):
    from horus_player import play
    play(acestream_id, title=title, port=int(ACESTREAM_PORT), ace_path=ACESTREAM_PATH)


# ---------------------------------------------------------------------------
# Router principal
# ---------------------------------------------------------------------------
def router():
    mode = PARAMS.get('mode')

    if mode is None:
        main_menu()
    elif mode == 'canales':
        show_canales()
    elif mode == 'categoria':
        show_categoria(PARAMS.get('cat', ''))
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
