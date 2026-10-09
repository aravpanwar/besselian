# Totality Path & Nearby Locations
# Copyright (C) 2026 Arav Panwar
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. See <https://www.gnu.org/licenses/>.

"""Draw the link-preview card and the site icons.

The card is drawn from the same outlines, path and places as the site, not
screenshotted from the map, so it carries no basemap tiles and needs no tile
credit. Requires Pillow. Fonts and outlines are downloaded into data/cache on
first run.
"""
import json
import math
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
EVENT = '2027-08-02'
DOCS = ROOT / 'docs'
DATA = DOCS / 'data'
CACHE = ROOT / 'data' / 'cache'
UA = {'User-Agent': 'besselian/0.1 (+https://github.com/aravpanwar/besselian)'}

NE_URL = ('https://raw.githubusercontent.com/nvkelso/natural-earth-vector/'
          'v5.1.2/geojson/ne_10m_admin_0_countries_gbr.geojson')
PLEX = 'https://raw.githubusercontent.com/IBM/plex/master/packages'
FONTS = {
    'semibold': f'{PLEX}/plex-sans/fonts/complete/ttf/IBMPlexSans-SemiBold.ttf',
    'regular': f'{PLEX}/plex-sans/fonts/complete/ttf/IBMPlexSans-Regular.ttf',
    'mono': f'{PLEX}/plex-mono/fonts/complete/ttf/IBMPlexMono-Medium.ttf',
}

# The site's palette (docs/style.css).
GROUND = '#f7f6f3'
PAPER = '#fffefb'
INK = '#14110e'
DIM = '#6b655c'
LINE = '#d5d1c8'
ACCENT = '#1a5c7a'
SEA = '#e2e7ea'
DOT = '#3d382f'


def cached(url):
    dest = CACHE / url.rsplit('/', 1)[1]
    if not dest.exists():
        print(f'downloading       {url}')
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=120) as resp:
            dest.write_bytes(resp.read())
    return dest


def font(kind, px):
    return ImageFont.truetype(str(cached(FONTS[kind])), px)


def rgba(hex_colour, alpha):
    h = hex_colour.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (round(alpha * 255),)


def polygons(geom):
    if geom['type'] == 'Polygon':
        return [geom['coordinates']]
    if geom['type'] == 'MultiPolygon':
        return geom['coordinates']
    return []


# ---------- link-preview card ----------

W, H = 1200, 630
S = 3                      # drawn at 3x and scaled down, for smooth edges
LAT_TOP, LAT0 = 42.5, 24.0
LON_LEFT = -19.0
K = H / 39.0               # pixels per degree of latitude


def project(lon, lat):
    x = (lon - LON_LEFT) * math.cos(math.radians(LAT0)) * K
    y = (LAT_TOP - lat) * K
    return x * S, y * S


def card():
    land = json.loads(cached(NE_URL).read_text(encoding='utf-8'))
    path = json.loads((DATA / f'{EVENT}-path.geojson').read_text(encoding='utf-8'))
    places = json.loads((DATA / f'{EVENT}-places.json').read_text(encoding='utf-8'))

    img = Image.new('RGBA', (W * S, H * S), SEA)
    d = ImageDraw.Draw(img)
    for f in land['features']:
        for poly in polygons(f['geometry']):
            ring = [project(*c) for c in poly[0]]
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            if max(xs) < 0 or min(xs) > W * S or max(ys) < 0 or min(ys) > H * S:
                continue
            d.polygon(ring, fill=GROUND, outline=LINE, width=S)

    over = Image.new('RGBA', img.size, (0, 0, 0, 0))
    o = ImageDraw.Draw(over)
    for f in path['features']:
        if f['properties']['kind'] == 'umbra':
            ring = [project(*c) for c in f['geometry']['coordinates'][0]]
            o.polygon(ring, fill=rgba(ACCENT, 0.16))
            o.line(ring, fill=rgba('#7fa0b2', 1), width=round(1.4 * S))
    for f in path['features']:
        if f['properties']['kind'] == 'centerline':
            o.line([project(*c) for c in f['geometry']['coordinates']],
                   fill=rgba(ACCENT, 1), width=round(2.2 * S), joint='curve')
    for p in places['places']:
        x, y = project(p['x'], p['y'])
        r = (1.1 + 2.1 * min(1.0, math.log10(max(p['p'], 1000) / 1000) / 3.3)) * S
        o.ellipse((x - r, y - r, x + r, y + r), fill=rgba(DOT, 0.8))
    img = Image.alpha_composite(img, over)

    # Text panel over the empty Sahara, clear of the path.
    d = ImageDraw.Draw(img)
    px, py, pw, ph = 36 * S, 352 * S, 660 * S, 242 * S
    d.rectangle((px, py, px + pw, py + ph), fill=PAPER, outline=LINE, width=S)
    x = px + 30 * S
    d.text((x, py + 26 * S), 'Totality Path & Nearby Locations',
           font=font('semibold', 38 * S), fill=INK)
    d.text((x, py + 84 * S), 'Total solar eclipse, 2 August 2027',
           font=font('regular', 27 * S), fill='#4a453d')
    n = len(places['places'])
    countries = len(places['advisories'])
    d.text((x, py + 136 * S),
           f'{n} places in {countries} countries, ranked by seconds of totality lost',
           font=font('mono', 15 * S), fill=DIM)
    d.text((x, py + 184 * S), 'eclipse.aravpanwar.com',
           font=font('semibold', 21 * S), fill=ACCENT)
    d.text((px + pw - 30 * S, py + ph - 20 * S), 'Places: GeoNames',
           font=font('regular', 12 * S), fill='#787165', anchor='rs')

    out = img.resize((W, H), Image.LANCZOS).convert('RGB')
    dest = DOCS / 'og.png'
    out.save(dest, optimize=True)
    print(f'wrote             {dest.relative_to(ROOT)} '
          f'({dest.stat().st_size // 1024} KB)')


# ---------- icons ----------

# An eclipse: dark disc, pale corona ring, on the accent teal so it reads on
# both light and dark browser tab bars.
ICON_SVG = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect width="32" height="32" rx="7" fill="{ACCENT}"/>
<circle cx="16" cy="16" r="10.6" fill="none" stroke="{GROUND}" stroke-width="2.2"/>
<circle cx="16" cy="16" r="8" fill="{INK}"/>
</svg>
'''


def icon(px):
    """The same drawing as ICON_SVG, rasterised at px by px."""
    s = px * 8 / 32
    img = Image.new('RGBA', (px * 8, px * 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, px * 8 - 1, px * 8 - 1), radius=7 * s, fill=ACCENT)
    r_out, r_in = (10.6 + 1.1) * s, (10.6 - 1.1) * s
    c = 16 * s
    d.ellipse((c - r_out, c - r_out, c + r_out, c + r_out), fill=GROUND)
    d.ellipse((c - r_in, c - r_in, c + r_in, c + r_in), fill=ACCENT)
    d.ellipse((c - 8 * s, c - 8 * s, c + 8 * s, c + 8 * s), fill=INK)
    return img.resize((px, px), Image.LANCZOS)


def icons():
    (DOCS / 'favicon.svg').write_text(ICON_SVG, encoding='utf-8')
    icon(48).save(DOCS / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
    # iOS draws its own rounded corners and ignores transparency.
    touch = Image.new('RGB', (180, 180), ACCENT)
    touch.paste(icon(180), (0, 0), icon(180))
    touch.save(DOCS / 'apple-touch-icon.png', optimize=True)
    for name in ('favicon.svg', 'favicon.ico', 'apple-touch-icon.png'):
        print(f'wrote             docs/{name}')


card()
icons()
