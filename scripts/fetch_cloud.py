"""Download ERA5 cloud cover for the path and reduce it to a per-place cache.

Run once per event. Needs ~/.cdsapirc and the ERA5 licence accepted on
https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels

One request for the whole path and all years, not one per place: the CDS is a
shared queue, and 772 requests would be slow and inconsiderate.
"""
import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from eclipse.cloud import (DATASET, build_request, path_area, sample,
                           GRID_DEGREES, GRID_KM_APPROX)

EVENT = '2027-08-02'
YEAR_FROM, YEAR_TO = 1985, 2024
MONTH = 8
DAYS = [1, 2, 3]          # the date and a day either side, for sample size
HOURS_UT = [8, 9, 10, 11, 12]

CACHE = ROOT / 'data' / 'cache' / 'cloud'
CACHE.mkdir(parents=True, exist_ok=True)
NC = CACHE / f'{EVENT}-era5-tcc.nc'

places_csv = ROOT / 'data' / 'out' / f'{EVENT}-places.csv'
rows = list(csv.DictReader(places_csv.open(encoding='utf-8')))
print(f'places          {len(rows)}')

area = path_area([{'latitude': float(r['latitude']),
                   'longitude': float(r['longitude'])} for r in rows])
print(f'area (N,W,S,E)  {[round(a, 2) for a in area]}')
print(f'years           {YEAR_FROM}-{YEAR_TO}  days {DAYS}  hours UT {HOURS_UT}')

if NC.exists():
    print(f'netcdf          cached at {NC.relative_to(ROOT)} '
          f'({NC.stat().st_size // 1024 // 1024} MB)')
else:
    import cdsapi
    request = build_request(YEAR_FROM, YEAR_TO, MONTH, DAYS, HOURS_UT, area)
    print('netcdf          requesting from CDS (this queues, be patient) ...')
    cdsapi.Client().retrieve(DATASET, request, str(NC))
    print(f'netcdf          downloaded {NC.stat().st_size // 1024 // 1024} MB')

import xarray as xr

ds = xr.open_dataset(NC)
print(f'variables       {list(ds.data_vars)}')
print(f'dims            {dict(ds.sizes)}')

# ERA5 netcdf names vary by pipeline generation: tcc or total_cloud_cover,
# latitude/longitude or lat/lon, time or valid_time. Resolve rather than assume.
var = next((v for v in ('tcc', 'total_cloud_cover') if v in ds.data_vars),
           list(ds.data_vars)[0])
lat_name = next(n for n in ('latitude', 'lat') if n in ds.coords)
lon_name = next(n for n in ('longitude', 'lon') if n in ds.coords)
time_name = next(n for n in ('valid_time', 'time') if n in ds.coords)
print(f'using           {var} over ({time_name}, {lat_name}, {lon_name})')

out = {}
missing = 0
for r in rows:
    hour = int(round(float(r['max_eclipse_ut_hours'])))
    hour = min(max(hour, min(HOURS_UT)), max(HOURS_UT))
    c = sample(ds, float(r['latitude']), float(r['longitude']), hour,
               lat_name, lon_name, time_name, var)
    if c is None:
        missing += 1
        continue
    out[r['geonameid']] = c.as_dict()

dest = CACHE / f'{EVENT}-cloud.json'
dest.write_text(json.dumps({
    'event': EVENT,
    'source': {
        'dataset': DATASET,
        'attribution': 'Contains modified Copernicus Climate Change Service '
                       'information. Generated using Copernicus Climate Change '
                       'Service information, ERA5 hourly data on single levels.',
        'url': 'https://cds.climate.copernicus.eu/datasets/'
               'reanalysis-era5-single-levels',
        'variable': 'total_cloud_cover',
        'years': f'{YEAR_FROM}-{YEAR_TO}',
        'days_sampled': DAYS,
        'grid_degrees': GRID_DEGREES,
        'grid_km_approx': GRID_KM_APPROX,
    },
    'caveats': [
        f'ERA5 runs on a {GRID_DEGREES} degree grid, about {GRID_KM_APPROX} km. '
        'One cell can span the Nile valley and the desert plateau beside it, '
        'which do not have the same cloud behaviour. Read these as regional.',
        'Reanalysis is a model constrained by observations, not an observation. '
        'Cloud is among its weaker fields.',
        'A mean over years hides the spread: 20 percent can be one year in five '
        'overcast or five years all hazy. The clear and overcast year counts are '
        'included so the spread is visible.',
        'Climatology is not a forecast. A real forecast for 2 August 2027 will '
        'exist about a week beforehand and will be worth more than any of this.',
        'For the authoritative eclipse-specific treatment see Jay Anderson at '
        'eclipsophile.com, which uses the satellite record rather than '
        'reanalysis. Not reproduced here: it states no licence.',
    ],
    'count': len(out),
    'by_geonameid': out,
}, indent=1), encoding='utf-8')

print(f'sampled         {len(out)} places, {missing} without data')
print(f'wrote           {dest.relative_to(ROOT)} '
      f'({dest.stat().st_size // 1024} KB)')

if out:
    vals = sorted((v['mean_cloud_percent'], k) for k, v in out.items())
    by_id = {r['geonameid']: r['name'] for r in rows}
    print()
    print('CLEAREST')
    for pct, gid in vals[:6]:
        print(f'  {by_id.get(gid, gid):<22} {pct:5.1f}%')
    print('CLOUDIEST')
    for pct, gid in vals[-6:]:
        print(f'  {by_id.get(gid, gid):<22} {pct:5.1f}%')
