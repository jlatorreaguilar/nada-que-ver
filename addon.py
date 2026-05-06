# -*- coding: utf-8 -*-
# Plugin: Nada que ver
# Addon de canales y agenda de fútbol vía Acestream para Kodi

import sys
import os
import json
import re
import datetime

from urllib.parse import urlencode, parse_qsl, unquote_plus, quote
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

# Añadir resources/lib al path para las libs de acestream integradas
_LIB_PATH = os.path.join(ADDON_PATH, 'resources', 'lib')
if _LIB_PATH not in sys.path:
    sys.path.insert(0, _LIB_PATH)


def _get_setting(key, default=''):
    val = ADDON.getSetting(key)
    return val if val else default


ACESTREAM_PORT   = _get_setting('acestream_port', '6878')
ACESTREAM_PATH   = _get_setting('acestream_path', '')
DATA_URL_CANALES = 'https://jlatorreaguilar.github.io/nada-que-ver/data/canales.json'
DATA_URL_AGENDA  = 'https://jlatorreaguilar.github.io/nada-que-ver/data/agenda.json'

AGENDA_URLS = [
    'https://deportes-live.vercel.app/index.html',
    'https://ciriaco.netlify.app/',
    'https://eventos-eight-dun.vercel.app/',
    'https://uk.4everproxy.com/secure/KpUm_WoxDYiMMqOAdEZifdMMb0AJKLdAbBX9Yf65kU_CCoqpUvCnHfFaTVnwEkBz',
]


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
    add_menu_item(
        label       = '[COLOR FFFF7700]Buscar canal[/COLOR]',
        mode        = 'buscar',
        description = 'Busca un canal por sus 4 dígitos (ej: dda5)'
    )

    xbmcplugin.endOfDirectory(HANDLE)


# ---------------------------------------------------------------------------
# Ruta del canales.json local empaquetado en el addon (copia de seguridad)
_CANALES_LOCAL = os.path.join(ADDON_PATH, 'resources', 'data', 'canales.json')


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

    # Fallback: leer el canales.json local empaquetado con el addon
    log('Descarga remota fallida, usando canales.json local', xbmc.LOGWARNING)
    try:
        with open(_CANALES_LOCAL, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cats = data.get('categorias', [])
        if cats:
            _canales_cache = cats
            return cats
    except Exception as e:
        log('Error leyendo canales.json local: {}'.format(str(e)), xbmc.LOGERROR)
    return []


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
# Agenda deportiva — helpers de scraping
# ---------------------------------------------------------------------------

def _strip_html(raw):
    """Elimina tags HTML y normaliza espacios."""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', raw)).strip()


def _fetch_agenda_html(url, index):
    try:
        import requests
    except ImportError:
        xbmcgui.Dialog().ok(ADDON_NAME,
            'Componentes no disponibles.\nVe a la Agenda para instalarlos.')
        return None

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    xbmcgui.Dialog().notification(
        'Agenda', 'Probando servidor {}...'.format(index + 1),
        xbmcgui.NOTIFICATION_INFO, 1000
    )

    # 1 — Directo
    try:
        r = requests.get(url, headers=headers, timeout=10)
        log('Agenda servidor {}: HTTP {} ({} bytes)'.format(index + 1, r.status_code, len(r.text)))
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception as e:
        log('Agenda servidor {} directo fallido: {}'.format(index + 1, e), xbmc.LOGWARNING)

    # 2 — allorigins.win
    try:
        r = requests.get('https://api.allorigins.win/get?url={}'.format(quote(url)), headers=headers, timeout=15)
        log('Agenda allorigins servidor {}: HTTP {}'.format(index + 1, r.status_code))
        if r.status_code == 200:
            data = r.json()
            if data.get('contents') and len(data['contents']) > 500:
                return data['contents']
    except Exception as e:
        log('Agenda allorigins servidor {} fallido: {}'.format(index + 1, e), xbmc.LOGWARNING)

    # 3 — corsproxy.io
    try:
        r = requests.get('https://corsproxy.io/?{}'.format(quote(url)), headers=headers, timeout=15)
        log('Agenda corsproxy servidor {}: HTTP {} ({} bytes)'.format(index + 1, r.status_code, len(r.text)))
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception as e:
        log('Agenda corsproxy servidor {} fallido: {}'.format(index + 1, e), xbmc.LOGWARNING)

    log('Agenda: todos los metodos fallaron para servidor {} ({})'.format(index + 1, url), xbmc.LOGERROR)
    return None


def _parse_agenda_events(html):
    """
    Extrae eventos del HTML del servidor de agenda.
    """
    return _parse_agenda_bs4(html)


def _parse_agenda_bs4(html):
    """Parseo robusto con BeautifulSoup."""
    from bs4 import BeautifulSoup
    today = datetime.datetime.now().strftime('%d/%m/%Y')
    soup  = BeautifulSoup(html, 'html.parser')

    # Buscar tabla del día de hoy
    table = None
    for h2 in soup.find_all('h2', class_='fecha'):
        if today in h2.get_text():
            table = h2.find_next_sibling('table')
            break
    if not table:
        table = soup.find('table')
    if not table:
        log('Agenda BS4: no se encontró tabla', xbmc.LOGWARNING)
        return []

    events = []
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) < 5:
            continue

        if len(cols) == 5:
            time_val    = cols[0].get_text(strip=True)
            sport       = cols[1].get_text(strip=True)
            competition = cols[2].get_text(strip=True)
            event_name  = cols[3].get_text(strip=True)
            links_col   = cols[4]
        else:
            time_val    = cols[1].get_text(strip=True)
            sport       = cols[2].get_text(strip=True)
            competition = cols[3].get_text(strip=True)
            event_name  = cols[4].get_text(strip=True)
            links_col   = cols[5]

        if not time_val and not event_name:
            continue

        links = []
        for a in links_col.find_all('a'):
            href = a.get('href', '')
            m = re.search(r'acestream://([a-f0-9]{40})', href)
            if m:
                name = a.get_text(strip=True).replace('\u25b6', '').strip() or 'Ver'
                links.append({'id': m.group(1), 'name': name})

        if links:
            events.append({
                'time'        : time_val,
                'sport'       : sport,
                'competition' : competition,
                'event_name'  : event_name,
                'links'       : links,
            })

    log('Agenda BS4: {} eventos encontrados'.format(len(events)))
    return events


def _parse_agenda_regex(html):
    """Parseo de fallback con regex."""
    today = datetime.datetime.now().strftime('%d/%m/%Y')

    table_html = None
    for m in re.finditer(
        r'<h2[^>]*class=["\'][^"\']*fecha[^"\']*["\'][^>]*>(.*?)</h2>',
        html, re.IGNORECASE | re.DOTALL
    ):
        if today in m.group(1):
            rest = html[m.end():]
            t = re.search(r'<table[\s\S]*?</table>', rest, re.IGNORECASE)
            if t:
                table_html = t.group(0)
            break

    if not table_html:
        t = re.search(r'<table[\s\S]*?</table>', html, re.IGNORECASE)
        table_html = t.group(0) if t else None

    if not table_html:
        log('Agenda regex: no se encontró tabla', xbmc.LOGWARNING)
        return []

    href_re = re.compile(r'href=["\']?acestream://([a-f0-9]{40})["\']?', re.IGNORECASE)
    events  = []

    for row_m in re.finditer(r'<tr[^>]*>([\s\S]*?)</tr>', table_html, re.IGNORECASE):
        cells = re.findall(r'<td[^>]*>([\s\S]*?)</td>', row_m.group(1), re.IGNORECASE)
        if len(cells) < 5:
            continue

        if len(cells) == 5:
            time_val, sport, competition, event_name, links_html = (
                _strip_html(cells[0]), _strip_html(cells[1]),
                _strip_html(cells[2]), _strip_html(cells[3]), cells[4]
            )
        else:
            time_val, sport, competition, event_name, links_html = (
                _strip_html(cells[1]), _strip_html(cells[2]),
                _strip_html(cells[3]), _strip_html(cells[4]), cells[5]
            )

        if not time_val and not event_name:
            continue

        links = []
        for a_m in re.finditer(r'<a[^>]*>([\s\S]*?)</a>', links_html, re.IGNORECASE):
            id_m = href_re.search(a_m.group(0))
            if id_m:
                name = _strip_html(a_m.group(1)).replace('\u25b6', '').strip() or 'Ver'
                links.append({'id': id_m.group(1), 'name': name})

        if links:
            events.append({
                'time'        : time_val,
                'sport'       : sport,
                'competition' : competition,
                'event_name'  : event_name,
                'links'       : links,
            })

    log('Agenda regex: {} eventos encontrados'.format(len(events)))
    return events


# ---------------------------------------------------------------------------
# Sección BUSCAR
# ---------------------------------------------------------------------------
def show_buscar():
    query = xbmcgui.Dialog().input('Buscar canal (4 dígitos)', type=xbmcgui.INPUT_ALPHANUM)
    if not query:
        xbmcplugin.endOfDirectory(HANDLE)
        return

    query = query.strip().lower()
    xbmcplugin.setPluginCategory(HANDLE, 'Buscar: {}'.format(query))
    xbmcplugin.setContent(HANDLE, 'videos')

    categorias = _get_categorias()
    resultados = []
    for cat in categorias:
        for canal in cat.get('canales', []):
            short_id = canal.get('short_id', canal.get('acestream_id', '')[:4]).lower()
            if query in short_id:
                resultados.append((cat['nombre'], canal))

    if not resultados:
        xbmcgui.Dialog().notification(
            ADDON_NAME, 'No se encontró ningún canal con "{}"'.format(query), ICON, 3000
        )
        xbmcplugin.endOfDirectory(HANDLE)
        return

    for cat_nombre, canal in resultados:
        nombre       = canal.get('nombre', '')
        acestream_id = canal.get('acestream_id', '')
        short_id     = canal.get('short_id', acestream_id[:4] if acestream_id else '')
        fuente       = canal.get('fuente', 'ELCANO')

        label = '{} {} --> {}  [COLOR FF888888][{}][/COLOR]'.format(
            nombre, short_id, fuente, cat_nombre
        )

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

    events = []
    failed_urls = []
    for i, url in enumerate(AGENDA_URLS):
        log('Agenda: probando servidor {} ({})'.format(i + 1, url))
        html = _fetch_agenda_html(url, i)
        if not html:
            failed_urls.append(str(i + 1))
            continue
        events = _parse_agenda_events(html)
        if events:
            log('Agenda: {} eventos cargados desde servidor {}'.format(len(events), i + 1))
            break
        else:
            log('Agenda: HTML recibido pero 0 eventos parseados en servidor {}'.format(i + 1), xbmc.LOGWARNING)

    if not events:
        detail = 'Servidores fallidos: {}'.format(', '.join(failed_urls)) if failed_urls else 'Parse fallido'
        log('Agenda: FALLO TOTAL - {}'.format(detail), xbmc.LOGERROR)
        xbmcgui.Dialog().ok(
            ADDON_NAME,
            'No se ha podido cargar la agenda deportiva.\n\n{}\n\nRevisa el log de Kodi para más detalles.'.format(detail)
        )
        xbmcplugin.endOfDirectory(HANDLE)
        return

    for ev in events:
        time_val    = ev['time']
        sport       = ev['sport']
        competition = ev['competition']
        event_name  = ev['event_name']
        links       = ev['links']

        label = '[COLOR FFFFFF00][{}][/COLOR] [COLOR FF32CD32][{}][/COLOR] {} [I]({})[/I]'.format(
            time_val, sport, event_name, competition
        )

        if len(links) == 1:
            li = xbmcgui.ListItem(label)
            li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
            li.setInfo('video', {'title': event_name, 'plot': competition, 'mediatype': 'video'})
            li.setProperty('IsPlayable', 'true')
            url_item = build_url({'mode': 'play', 'acestream_id': links[0]['id'], 'title': label})
            xbmcplugin.addDirectoryItem(HANDLE, url_item, li, False)
        else:
            label_multi = label + ' [COLOR FFFFFF00]({} canales)[/COLOR]'.format(len(links))
            li = xbmcgui.ListItem(label_multi)
            li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
            li.setInfo('video', {'title': event_name, 'plot': competition})
            url_item = build_url({
                'mode'  : 'event_links',
                'links' : json.dumps(links),
                'title' : event_name,
            })
            xbmcplugin.addDirectoryItem(HANDLE, url_item, li, True)

    xbmcplugin.endOfDirectory(HANDLE)


def show_event_links(links_json, title):
    """Muestra los canales disponibles para un evento con múltiples enlaces."""
    xbmcplugin.setPluginCategory(HANDLE, title)
    xbmcplugin.setContent(HANDLE, 'videos')

    try:
        links = json.loads(links_json)
    except (ValueError, TypeError):
        xbmcplugin.endOfDirectory(HANDLE)
        return

    for link in links:
        name   = link.get('name', 'Ver')
        ace_id = link.get('id', '')
        label  = '[COLOR FF00FF00]Ver en:[/COLOR] {}'.format(name)
        li = xbmcgui.ListItem(label)
        li.setArt({'icon': ICON, 'thumb': ICON, 'fanart': FANART})
        li.setInfo('video', {'title': title, 'mediatype': 'video'})
        li.setProperty('IsPlayable', 'true')
        url_item = build_url({'mode': 'play', 'acestream_id': ace_id, 'title': title})
        xbmcplugin.addDirectoryItem(HANDLE, url_item, li, False)

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
    elif mode == 'buscar':
        show_buscar()
    elif mode == 'event_links':
        show_event_links(PARAMS.get('links', '[]'), PARAMS.get('title', ''))
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
