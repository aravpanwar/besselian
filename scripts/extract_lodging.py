# Totality Path & Nearby Locations
# Copyright (C) 2026 Arav Panwar
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. See <https://www.gnu.org/licenses/>.

"""Extract lodging from OSM country extracts into a compact cache.

Run once per OSM refresh. The PBF files are gigabytes; the cache is small
enough to commit, so the site build never needs the extracts.
"""
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from eclipse.lodging import extract, EXTRACTS

OSM = ROOT / 'data' / 'cache' / 'osm'
OUT = ROOT / 'data' / 'cache' / 'lodging'
OUT.mkdir(parents=True, exist_ok=True)

only = sys.argv[1:] or sorted(set(EXTRACTS.values()))

for basename in only:
    pbf = OSM / f'{basename}.osm.pbf'
    if not pbf.exists():
        print(f'{basename:<12} SKIP (no extract)')
        continue
    dest = OUT / f'{basename}.json'
    t0 = time.time()
    items = extract(pbf)
    payload = [
        {'lat': round(i.latitude, 5), 'lon': round(i.longitude, 5),
         'kind': i.kind, **({'rooms': i.rooms} if i.rooms else {})}
        for i in items
    ]
    dest.write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')
    lodging = sum(1 for i in items if not i.is_camping)
    camping = len(items) - lodging
    print(f'{basename:<12} {len(items):6d} features  '
          f'({lodging} lodging, {camping} camping)  '
          f'{dest.stat().st_size // 1024:5d} KB  {time.time() - t0:5.1f}s')
