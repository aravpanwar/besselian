"""Build the dataset: intersect populated places with the eclipse path.

Everything here runs at build time. No runtime third-party calls.
"""
import csv
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from eclipse.local_circumstances import Elements
from eclipse.places import load, PATH_COUNTRIES_2027, haversine_km
from eclipse.path import greatest_duration, rank, build_centerline

def fmt_duration(seconds: float) -> str:
    """m'ss" from seconds. Truncate, never round: 330.2 s is 5m30s, not 6m30s."""
    total = int(seconds)
    return f'{total // 60}m{total % 60:02d}s'


EVENT = '2027-08-02'
OUT = ROOT / 'data' / 'out'
OUT.mkdir(parents=True, exist_ok=True)

elements_path = ROOT / 'data' / 'elements' / f'{EVENT}.json'
meta = json.loads(elements_path.read_text(encoding='utf-8'))
E = Elements.from_json(elements_path)

print(f'event            {meta["label"]}')
print(f'delta T          {E.delta_t_seconds} s')

places = load(ROOT / 'data' / 'cache' / 'cities1000.zip', PATH_COUNTRIES_2027)
print(f'places loaded    {len(places)}')

ge = meta['greatest_eclipse']
glat, glon, peak = greatest_duration(E, (ge['latitude_deg'], ge['longitude_deg']))
print(f'greatest duration {peak:.2f} s at {glat:.4f} N {glon:.4f} E')
print(f'greatest eclipse  {ge["central_duration"]} at '
      f'{ge["latitude_deg"]} N {ge["longitude_deg"]} E  (NASA)')

t0 = time.time()
track = build_centerline(E, -12.0, 50.0, 0.5)
print(f'centerline pts   {len(track)}')
ranked = rank(places, E, peak, track=track)
print(f'inside the path   {len(ranked)}  ({time.time() - t0:.1f}s)')

rows = [r.as_row() for r in ranked]

# CSV: the full dataset, openly licensed.
csv_path = OUT / f'{EVENT}-places.csv'
with csv_path.open('w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

# JSON: same data plus provenance, for the site to consume.
json_path = OUT / f'{EVENT}-places.json'
json_path.write_text(json.dumps({
    'event': {
        'id': meta['id'],
        'label': meta['label'],
        'delta_t_seconds': E.delta_t_seconds,
        'greatest_eclipse': ge,
        'greatest_duration': {
            'latitude_deg': round(glat, 4),
            'longitude_deg': round(glon, 4),
            'duration_seconds': round(peak, 2),
            'note': ('Distinct from greatest eclipse. For total eclipses the two '
                     'differ by 1-2 s and can be 100+ km apart. Seconds '
                     'sacrificed is measured against this point.'),
        },
        'caveats': {
            'delta_t': (f'Computed with delta T = {E.delta_t_seconds} s '
                        f'({meta["provenance"]["delta_t_basis"]}). delta T is not '
                        'perfectly predictable and shifts the path east or west; '
                        "NASA's older 2027 map used 71.7 s, about 2 km of "
                        'longitudinal difference.'),
            'lunar_limb': ('Path limits carry 1-2 km of uncertainty and duration '
                           '1-3 s from the lunar limb profile. Limb-corrected '
                           'predictions appear 12-18 months before an event.'),
            'geonames_coverage': ('Coverage is uneven by country. Absence of a '
                                  'town here means absence from GeoNames, not '
                                  'absence of a town.'),
        },
    },
    'sources': [
        {'name': 'Besselian elements',
         'attribution': meta['provenance']['attribution'],
         'url': meta['provenance']['url'],
         'retrieved': meta['provenance']['retrieved']},
        {'name': 'Populated places', 'attribution': 'GeoNames, CC BY 4.0',
         'url': 'https://download.geonames.org/export/dump/'},
    ],
    'count': len(rows),
    'places': rows,
}, ensure_ascii=False, indent=1), encoding='utf-8')

print(f'wrote            {csv_path.relative_to(ROOT)}')
print(f'wrote            {json_path.relative_to(ROOT)}  '
      f'({json_path.stat().st_size // 1024} KB)')

# Coverage summary, since it is a caveat the reader needs.
print()
print('BY COUNTRY')
by_country: dict[str, list] = {}
for r in ranked:
    by_country.setdefault(r.place.country, []).append(r)
for country, rs in sorted(by_country.items(), key=lambda kv: -len(kv[1])):
    best = min(rs, key=lambda r: r.seconds_sacrificed)
    print(f'  {country:<14} {len(rs):4d} places   best: {best.place.name} '
          f'({fmt_duration(best.duration_seconds)}, '
          f'-{best.seconds_sacrificed:.1f}s)')
