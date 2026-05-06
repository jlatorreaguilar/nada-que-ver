#!/usr/bin/env python3
"""Construye el ZIP del plugin plugin.video.nada_que_ver."""
import zipfile, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
addon_id = 'plugin.video.nada_que_ver'

with open(os.path.join(ROOT, 'addon.xml'), encoding='utf-8') as f:
    m = re.search(r'addon id=["\']{}["\'][^>]+version=["\']([0-9.]+)["\']'.format(addon_id), f.read())
    version = m.group(1) if m else '1.5.4'

zip_name = '{}-{}.zip'.format(addon_id, version)
zip_path = os.path.join(ROOT, 'repo', addon_id, zip_name)

# Archivos individuales a incluir
single_files = [
    'addon.py',
    'addon.xml',
    'resources/settings.xml',
    'resources/data/canales.json',
    'resources/lib/horus_player.py',
    'resources/lib/acestream/__init__.py',
    'resources/lib/acestream/engine.py',
    'resources/lib/acestream/object.py',
    'resources/lib/acestream/server.py',
    'resources/lib/acestream/stream.py',
]
for img in ['icon.png', 'fanart.jpg', 'fanart.png']:
    if os.path.exists(os.path.join(ROOT, img)):
        single_files.append(img)

# Directorios de librerías bundleadas (dentro de resources/lib/)
lib_packages = ['bs4', 'certifi', 'charset_normalizer', 'idna',
                'requests', 'soupsieve', 'typing_extensions', 'urllib3']

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for rel in single_files:
        src = os.path.join(ROOT, rel)
        if os.path.exists(src):
            z.write(src, '{}/{}'.format(addon_id, rel))
            print('  +', rel)
        else:
            print('  SKIP:', rel)

    # Bundlear librerías Python puras
    lib_root = os.path.join(ROOT, 'resources', 'lib')
    for pkg in lib_packages:
        pkg_dir = os.path.join(lib_root, pkg)
        if not os.path.isdir(pkg_dir):
            print('  SKIP lib (no existe):', pkg)
            continue
        for dirpath, dirnames, filenames in os.walk(pkg_dir):
            for fname in filenames:
                if fname.endswith('.pyc'):
                    continue
                fullpath = os.path.join(dirpath, fname)
                relpath = os.path.relpath(fullpath, ROOT).replace('\\', '/')
                z.write(fullpath, '{}/{}'.format(addon_id, relpath))
        print('  + lib/{}/'.format(pkg))

size = os.path.getsize(zip_path)
print('ZIP creado: {} ({:.0f} KB)'.format(zip_path, size / 1024))
