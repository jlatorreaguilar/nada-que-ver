#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_data.py
Descarga las listas del IPFS de shickat.me y genera:
  - data/canales.json  → canales acestream organizados por categoría
  - data/agenda.json   → eventos deportivos del día
"""

import json
import os
import re
import sys
import urllib.request

# ---------------------------------------------------------------------------
# Fuentes (por orden de preferencia)
# ---------------------------------------------------------------------------
_IPNS_SHICKAT = "k2k4r8oqlcjxsritt5mczkcn4mmvcmymbqw7113fz2flkrerfwfps004"
_IPNS_ELCANO  = "k51qzi5uqu5di462t7j4vu4akwfhvtjhy88qbupktvoacqfqe9uforjvhyi4wr"

# Gateways IPFS públicos, en orden de preferencia
_GATEWAYS = [
    "https://dweb.link",
    "https://ipfs.io",
    "https://cloudflare-ipfs.com",
    "https://gateway.pinata.cloud",
]

def _ipns_urls(ipns_key, path):
    """Genera URLs para un mismo recurso IPNS en todos los gateways disponibles."""
    urls = []
    for gw in _GATEWAYS:
        urls.append(f"{gw}/ipns/{ipns_key}{path}")
    return urls

# Lista completa con todas las fuentes (ELCANO, NEW ERA, NEW LOOP, SPORT TV…)
# en formato Kodi: plugin://script.module.horus?action=play&id=<acestream_id>
URLS_CANALES_KODI  = _ipns_urls(_IPNS_SHICKAT, "/data/listas/lista_kodi.m3u")
# Fallback con formato acestream://
URLS_CANALES_FUERA = _ipns_urls(_IPNS_SHICKAT, "/data/listas/lista_fuera_iptv.m3u")

URL_AGENDA = (
    "https://raw.githubusercontent.com/ezdakit/zukzeuk_listas/refs/heads/main"
    "/zz_eventos/zz_eventos_all_ott.m3u"
)
URLS_AGENDA_ALT = _ipns_urls(_IPNS_ELCANO, "/hashes_acestream.m3u")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  WARN: no se pudo descargar {url}: {e}", file=sys.stderr)
        return None


def fetch_any(urls, timeout=20):
    """Intenta descargar de cada URL en orden, devuelve el primer resultado exitoso."""
    for url in urls:
        result = fetch(url, timeout=timeout)
        if result:
            return result
    return None


def inferir_fuente(nombre):
    n = nombre.upper()
    if "NEW ERA" in n:
        return "NEW ERA"
    if "NEW LOOP" in n:
        return "NEW LOOP"
    if "SPORT TV" in n and "-->" in n:
        return "SPORT TV"
    return "ELCANO"


# ---------------------------------------------------------------------------
# Parsear lista_kodi.m3u  (formato: group-title + plugin://...?id=<acestream_id>)
# Parsear lista_fuera_iptv.m3u (formato: group-title + acestream://<acestream_id>)
# Devuelve lista de categorías con todos sus canales
# ---------------------------------------------------------------------------

def build_canales_from_m3u(text):
    categorias = []
    cat_index = {}   # nombre_cat -> lista canales

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            g = re.search(r'group-title="([^"]+)"', line)
            n = re.search(r',(.+)$', line)
            if g and n:
                cat = g.group(1).strip().upper()
                nombre = n.group(1).strip()
                # Línea siguiente: URL del canal
                if i + 1 < len(lines):
                    url_line = lines[i + 1].strip()
                    # Formato Kodi: plugin://script.module.horus?action=play&id=XXXXX
                    ace = re.search(r'[?&]id=([a-f0-9]{40})', url_line)
                    # Formato acestream://XXXXX
                    if not ace:
                        ace = re.search(r'acestream://([a-f0-9]{40})', url_line)
                    if ace:
                        ace_id = ace.group(1)
                        fuente = inferir_fuente(nombre)
                        if cat not in cat_index:
                            cat_index[cat] = []
                            categorias.append({"nombre": cat, "canales": cat_index[cat]})
                        cat_index[cat].append({
                            "nombre": nombre,
                            "acestream_id": ace_id,
                            "short_id": ace_id[:4],
                            "fuente": fuente,
                        })
        i += 1

    total = sum(len(c["canales"]) for c in categorias)
    return categorias, total


# ---------------------------------------------------------------------------
# Parsear m3u de agenda
# ---------------------------------------------------------------------------

def build_agenda(text):
    eventos = []
    # Formato m3u: #EXTINF:-1 tvg-id="..." title="FECHA, HORA",TITULO\nacestream://ID
    patron = re.compile(
        r'#EXTINF[^\n]*?title="([^"]+),\s*([^"]+)"[^\n]*\n([^\n]+)',
        re.IGNORECASE,
    )
    for m in patron.finditer(text):
        fecha  = m.group(1).strip()
        hora   = m.group(2).strip()
        enlace = m.group(3).strip()
        titulo_match = re.search(r',(.+)$', m.group(0).split('\n')[0])
        titulo = titulo_match.group(1).strip() if titulo_match else fecha

        ace_id = None
        if "acestream://" in enlace:
            ace_id = enlace.replace("acestream://", "").strip()
        elif re.search(r"[0-9a-f]{40}", enlace):
            ace_id = re.search(r"[0-9a-f]{40}", enlace).group(0)

        if ace_id:
            eventos.append({
                "titulo": titulo,
                "fecha": fecha,
                "hora": hora,
                "acestream_id": ace_id,
            })

    # Fallback: formato simple  title="HORA",TITULO
    if not eventos:
        patron2 = re.compile(
            r'#EXTINF[^\n]*?,(.+)\n([^\n]+)',
            re.IGNORECASE,
        )
        for m in patron2.finditer(text):
            titulo = m.group(1).strip()
            enlace = m.group(2).strip()
            ace_id = None
            if "acestream://" in enlace:
                ace_id = enlace.replace("acestream://", "").strip()
            if ace_id:
                eventos.append({
                    "titulo": titulo,
                    "fecha": "",
                    "hora": "",
                    "acestream_id": ace_id,
                })

    return eventos


# ---------------------------------------------------------------------------
# Merge: fusiona canales nuevos con los existentes sin perder ninguno
# ---------------------------------------------------------------------------

def merge_canales(existentes, nuevos):
    """
    Combina dos listas de categorías.
    - Conserva todos los canales ya existentes (identificados por acestream_id).
    - Añade canales nuevos que no estuvieran presentes.
    - Nunca elimina canales existentes.
    Devuelve la lista fusionada y el número de canales añadidos.
    """
    # Índice: acestream_id -> True para todos los existentes
    ids_existentes = {
        canal["acestream_id"]
        for cat in existentes
        for canal in cat["canales"]
    }

    # Índice de categorías existentes por nombre para poder añadir canales a ellas
    cat_index = {cat["nombre"]: cat["canales"] for cat in existentes}

    añadidos = 0
    for cat_nueva in nuevos:
        nombre_cat = cat_nueva["nombre"]
        for canal in cat_nueva["canales"]:
            if canal["acestream_id"] not in ids_existentes:
                if nombre_cat not in cat_index:
                    nueva_cat = {"nombre": nombre_cat, "canales": []}
                    existentes.append(nueva_cat)
                    cat_index[nombre_cat] = nueva_cat["canales"]
                cat_index[nombre_cat].append(canal)
                ids_existentes.add(canal["acestream_id"])
                añadidos += 1

    return existentes, añadidos


def _load_canales_existentes():
    """Carga data/canales.json si existe, o devuelve lista vacía."""
    path = "data/canales.json"
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f).get("categorias", [])
        except Exception:
            pass
    return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs("data", exist_ok=True)

    # --- Canales ---
    print("Descargando lista_kodi.m3u desde IPFS...")
    texto_canales = fetch_any(URLS_CANALES_KODI, timeout=60)
    if texto_canales:
        categorias_nuevas, total = build_canales_from_m3u(texto_canales)
        print(f"  lista_kodi.m3u: {total} canales en {len(categorias_nuevas)} categorías")
    else:
        print("  Fallback → lista_fuera_iptv.m3u...")
        texto_canales = fetch_any(URLS_CANALES_FUERA, timeout=60)
        if texto_canales:
            categorias_nuevas, total = build_canales_from_m3u(texto_canales)
            print(f"  lista_fuera_iptv.m3u: {total} canales en {len(categorias_nuevas)} categorías")
        else:
            print("  ✗ No se pudo obtener ninguna lista de canales", file=sys.stderr)
            categorias_nuevas = None

    existentes = _load_canales_existentes()
    if categorias_nuevas is not None:
        categorias_finales, añadidos = merge_canales(existentes, categorias_nuevas)
        print(f"  + {añadidos} canales nuevos añadidos")
    else:
        categorias_finales = existentes
        print("  → Conservando canales existentes sin cambios", file=sys.stderr)

    if not categorias_finales:
        print("  ✗ No hay datos de canales disponibles, abortando", file=sys.stderr)
        sys.exit(1)

    total_final = sum(len(c["canales"]) for c in categorias_finales)
    with open("data/canales.json", "w", encoding="utf-8") as f:
        json.dump({"categorias": categorias_finales}, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {total_final} canales en {len(categorias_finales)} categorías → data/canales.json")

    # --- Agenda ---
    print("Descargando agenda de eventos...")
    texto_agenda = fetch(URL_AGENDA, timeout=20)
    if not texto_agenda:
        print("Intentando agenda alternativa...")
        texto_agenda = fetch_any(URLS_AGENDA_ALT, timeout=20)

    if texto_agenda:
        eventos = build_agenda(texto_agenda)
        with open("data/agenda.json", "w", encoding="utf-8") as f:
            json.dump({"eventos": eventos, "total": len(eventos)}, f,
                      ensure_ascii=False, indent=2)
        print(f"  ✓ {len(eventos)} eventos → data/agenda.json")
    else:
        print("  WARN: No se encontraron eventos de agenda", file=sys.stderr)
        with open("data/agenda.json", "w", encoding="utf-8") as f:
            json.dump({"eventos": [], "total": 0}, f)


if __name__ == "__main__":
    main()
