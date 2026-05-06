#!/usr/bin/env python3
"""Construye el ZIP del plugin plugin.video.nada_que_ver."""
import zipfile, os, re, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
addon_id = 'plugin.video.nada_que_ver'

with open(os.path.join(ROOT, 'addon.xml'), encoding='utf-8') as f:
    m = re.search(r'addon id=["\']{}["\'][^>]+version=["\']([0-9.]+)["\']'.format(addon_id), f.read())
    version = m.group(1) if m else '1.5.4'

zip_name = '{}-{}.zip'.format(addon_id, version)
zip_path = os.path.join(ROOT, 'repo', addon_id, zip_name)

files = [
    ('addon.py',),
    ('addon.xml',),
    ('resources/settings.xml',),
    ('resources/data/canales.json',),
    ('resources/lib/horus_player.py',),
    ('resources/lib/acestream/__init__.py',),
    ('resources/lib/acestream/engine.py',),
    ('resources/lib/acestream/object.py',),
    ('resources/lib/acestream/server.py',),
    ('resources/lib/acestream/stream.py',),
]
for img in ['icon.png', 'fanart.jpg', 'fanart.png']:
    if os.path.exists(os.path.join(ROOT, img)):
        files.append((img,))

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for (rel,) in files:
        src = os.path.join(ROOT, rel)
        if os.path.exists(src):
            arcname = '{}/{}'.format(addon_id, rel)
            z.write(src, arcname)
            print('  +', arcname)
        else:
            print('  SKIP:', rel)

size = os.path.getsize(zip_path)
print('ZIP creado: {} ({:.0f} KB)'.format(zip_path, size / 1024))
