#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_data.py
Descarga las listas de ELCANO y genera:
  - data/canales.json  → canales acestream organizados por categoría
  - data/agenda.json   → eventos deportivos del día
"""

import json
import os
import re
import sys
import urllib.request

# ---------------------------------------------------------------------------
# Fuentes ELCANO (por orden de preferencia)
# ---------------------------------------------------------------------------
BASE_IPNS = (
    "https://k51qzi5uqu5di462t7j4vu4akwfhvtjhy88qbupktvoacqfqe9uforjvhyi4wr"
    ".ipns.dweb.link"
)
URL_CANALES      = f"{BASE_IPNS}/hashes.txt"
URL_CANALES_M3U  = f"{BASE_IPNS}/hashes_acestream.m3u"
URL_CANALES_ALT  = f"{BASE_IPNS}/hashes_kodi.m3u"
URL_AGENDA = (
    "https://raw.githubusercontent.com/ezdakit/zukzeuk_listas/refs/heads/main"
    "/zz_eventos/zz_eventos_all_ott.m3u"
)
URL_AGENDA_ALT = f"{BASE_IPNS}/hashes_acestream.m3u"

# Canales relevantes con su categoría (nombre_base → categoría)
CANAL_CATEGORIAS = {
    "DAZN": "DAZN",
    "M+ LALIGA": "Movistar",
    "MOVISTAR": "Movistar",
    "HYPERMOTION": "LaLiga",
    "GOL PLAY": "LaLiga",
    "LIGA DE CAMPEONES": "Champions",
    "EUROSPORT": "General",
    "TELEDEPORTE": "General",
    "REAL MADRID TV": "General",
    "BEIN SPORTS": "General",
    "SKY SPORTS": "General",
    "LA 1": "General",
    "CUATRO": "General",
    "TELECINCO": "General",
    "PRIMERA FEDERACION": "LaLiga",
    "PRIMERA FEDERACIÓN": "LaLiga",
}

# Patrones de canales que nos interesan (sobre el nombre base)
FILTRO_CANALES = re.compile(
    r"DAZN|M\+ LALIGA|MOVISTAR DEPORTES|MOVISTAR VAMOS|HYPERMOTION|"
    r"GOL PLAY|LIGA DE CAMPEONES|EUROSPORT|TELEDEPORTE|REAL MADRID TV|"
    r"BEIN SPORTS|SKY SPORTS|LA 1 FHD|CUATRO FHD|TELECINCO|"
    r"PRIMERA FEDERACI",
    re.IGNORECASE,
)

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


def get_categoria(nombre_base):
    for key, cat in CANAL_CATEGORIAS.items():
        if key.upper() in nombre_base.upper():
            return cat
    return "General"


def prioridad(nombre):
    """Menor número = mayor prioridad (1080p > FHD > 720p > HD > resto)."""
    n = nombre.upper()
    if "1080P" in n:
        return 0
    if "FHD" in n:
        return 1
    if "720P" in n:
        return 2
    if "HD" in n:
        return 3
    return 4


# ---------------------------------------------------------------------------
# Parsear hashes.txt  (formato: cabecera + secciones === CAT === + NOMBRE\nacestream://ID)
# ---------------------------------------------------------------------------

def build_canales(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    grupos = {}
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        # Saltar cabeceras y separadores
        if (line.startswith("===") or line.startswith("AceStream")
                or line.startswith("Generated") or line.startswith("Total:")):
            i += 1
            continue
        # Par: NOMBRE_CANAL + acestream://ID en la siguiente línea
        if lines[i + 1].startswith("acestream://"):
            nombre = line
            ace_id = lines[i + 1].replace("acestream://", "").strip()
            if len(ace_id) == 40 and re.fullmatch(r"[0-9a-f]+", ace_id):
                # Eliminar calidad y estrellas para obtener nombre base
                nombre_base = re.sub(r"\s+\d+p\s*\**\s*$", "", nombre).strip()
                nombre_base = re.sub(r"\s+\*+\s*$", "", nombre_base).strip()
                if FILTRO_CANALES.search(nombre_base):
                    if nombre_base not in grupos:
                        grupos[nombre_base] = []
                    grupos[nombre_base].append({"nombre": nombre, "id": ace_id})
            i += 2
        else:
            i += 1

    canales = []
    for nombre_base, variantes in sorted(grupos.items()):
        mejor = sorted(variantes, key=lambda x: prioridad(x["nombre"]))[0]
        canales.append({
            "nombre": nombre_base,
            "acestream_id": mejor["id"],
            "categoria": get_categoria(nombre_base),
        })

    # Ordenar: por categoría y luego por nombre
    orden_cat = {"DAZN": 0, "Movistar": 1, "LaLiga": 2, "Champions": 3, "General": 4}
    canales.sort(key=lambda c: (orden_cat.get(c["categoria"], 9), c["nombre"]))
    return canales


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
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs("data", exist_ok=True)

    # --- Canales ---
    print("Descargando hashes.txt desde ELCANO...")
    texto_canales = fetch(URL_CANALES, timeout=30)
    if not texto_canales:
        print("Intentando hashes_acestream.m3u...")
        texto_canales = fetch(URL_CANALES_M3U, timeout=20)
    if not texto_canales:
        print("Intentando hashes_kodi.m3u...")
        texto_canales = fetch(URL_CANALES_ALT, timeout=20)

    if texto_canales:
        canales = build_canales(texto_canales)
        with open("data/canales.json", "w", encoding="utf-8") as f:
            json.dump({"canales": canales, "total": len(canales)}, f,
                      ensure_ascii=False, indent=2)
        print(f"  ✓ {len(canales)} canales guardados en data/canales.json")
    else:
        print("  ✗ No se pudo obtener la lista de canales", file=sys.stderr)
        sys.exit(1)

    # --- Agenda ---
    print("Descargando agenda de eventos ELCANO...")
    texto_agenda = fetch(URL_AGENDA, timeout=20)
    if not texto_agenda:
        print("Intentando agenda alternativa...")
        texto_agenda = fetch(URL_AGENDA_ALT, timeout=20)

    if texto_agenda:
        eventos = build_agenda(texto_agenda)
        with open("data/agenda.json", "w", encoding="utf-8") as f:
            json.dump({"eventos": eventos, "total": len(eventos)}, f,
                      ensure_ascii=False, indent=2)
        print(f"  ✓ {len(eventos)} eventos guardados en data/agenda.json")
    else:
        print("  WARN: No se encontraron eventos de agenda", file=sys.stderr)
        with open("data/agenda.json", "w", encoding="utf-8") as f:
            json.dump({"eventos": [], "total": 0}, f)


if __name__ == "__main__":
    main()
