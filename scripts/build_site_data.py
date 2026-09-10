# Totality Path & Nearby Locations
# Copyright (C) 2026 Arav Panwar
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. See <https://www.gnu.org/licenses/>.

"""Trim the dataset for the browser.

Short keys and rounded numbers: the full CSV stays the download, this is what
the page loads on every visit.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
EVENT = '2027-08-02'

src = json.loads((ROOT / 'data' / 'out' / f'{EVENT}-places.json')
                 .read_text(encoding='utf-8'))
OUT = ROOT / 'docs' / 'data'
OUT.mkdir(parents=True, exist_ok=True)

places = []
for p in src['places']:
    places.append({
        'i': p['geonameid'],
        'n': p['name'],
        'c': p['country_code'],
        'y': round(p['latitude'], 4),
        'x': round(p['longitude'], 4),
        'p': p['population'],
        'd': round(p['duration_seconds'], 1),
        's': round(p['seconds_sacrificed'], 1),
        'a': round(p['sun_altitude_deg'], 1),
        'u': round(p['max_eclipse_ut_hours'], 4),
        'k': p['distance_from_centerline_km'],
        'w': p['mean_cloud_percent'],
        'q': p['clear_sky_probability'],
        'l': p['lodging_within_25km'],
        'L': p['lodging_within_80km'],
        'z': p['timezone'],
    })

adv = {}
for cc, a in src['advisories']['by_country'].items():
    adv[cc] = {
        'country': a['country'],
        'worst': a['worst'],
        'label': a['labels'][0] if a['labels'] else None,
        'regions': a['regions'],
        'reviewed': (a['reviewed_at'] or '')[:10],
        'url': a['url'],
    }

payload = {
    'event': {
        'id': src['event']['id'],
        'label': src['event']['label'],
        'delta_t': src['event']['delta_t_seconds'],
        'peak': src['event']['greatest_duration']['duration_seconds'],
        'peak_lat': src['event']['greatest_duration']['latitude_deg'],
        'peak_lon': src['event']['greatest_duration']['longitude_deg'],
    },
    'caveats': src['event']['caveats'],
    'sources': src['sources'],
    'advisories': adv,
    'issuer': src['advisories']['issuer'],
    'places': places,
}

dest = OUT / f'{EVENT}-places.json'
dest.write_text(json.dumps(payload, separators=(',', ':'), ensure_ascii=False),
                encoding='utf-8')
print(f'places  {len(places)}')
print(f'wrote   {dest.relative_to(ROOT)} ({dest.stat().st_size // 1024} KB)')
