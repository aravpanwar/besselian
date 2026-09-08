# besselian

Solar eclipse local circumstances computed from Besselian elements, then
intersected with populated places, so you can see what a location actually
costs you in seconds of totality.

Eclipse is a data row, not a constant: one record per event under
`data/elements/`, same computation for any of them.

Status: computation core validated, place intersection working. No frontend yet.
Licensing not yet settled, so treat this as all rights reserved for the moment.

## The finding, for the 2 August 2027 eclipse

Luxor is the destination everyone names. It ranks **18th of 60 Egyptian places**
by seconds of totality sacrificed.

| Place | Totality | Sacrificed | From centerline | Population |
|---|---|---|---|---|
| Girga | 6m23s | 0.1 s | 1.0 km | 151,256 |
| Al Balyana | 6m22s | 0.2 s | 3.7 km | 68,413 |
| Nag Hammadi | 6m22s | 0.6 s | 6.9 km | 59,601 |
| Sohag | 6m22s | 0.9 s | 7.7 km | 266,944 |
| **Luxor** | **6m20s** | **2.7 s** | **15.1 km** | 422,407 |

Fourteen towns sit within 1.7 s of the theoretical maximum. Sohag has 267,000
people and beats Luxor by 1.8 s.

All 18 places within 3 s of the maximum are in Egypt. The best Spanish location
sacrifices 94.5 s.

### Supply does not follow the path

The obvious hypothesis, that lodging thins toward the centreline and that is
where the markup comes from, is not supported. Binned by distance from the
centreline, the median count of lodging within 25 km of an Egyptian place runs
12, 21, 1, 13, 6, 0. There is no gradient. Supply tracks the tourism cluster,
not the geometry.

What the counts do show is sharper:

| | Totality | Sacrificed | Lodging within 25 km | Within 80 km |
|---|---|---|---|---|
| Girga | 6m23s | 0.1 s | 4 | 22 |
| Luxor | 6m20s | 2.7 s | 115 | 127 |

Luxor has 29 times the lodging within 25 km and gives up 2.6 more seconds.
Widen to 80 km and the two are comparable, because at that radius both reach
the same Nile-valley cluster. Girga and Luxor are 103 km apart.

That is the sleep-and-stand case in two rows: the rooms and the maximum are not
in the same place, and the gap between them is a drive, not a compromise.

## Usage

```
python scripts/build.py          # writes data/out/<event>-places.{csv,json}
python -m pytest tests/ -q       # validation gate
```

The full build takes about 7 minutes, dominated by the exact centerline solve.

## Validation

`python -m pytest tests/ -q`

The computation is checked against independently published values before any
downstream work is trusted:

| Check | Expected | Computed |
|---|---|---|
| Greatest eclipse on shadow axis | ~0 | 1.0e-5 Earth radii |
| Sun altitude at greatest eclipse | 81.7 deg | 81.69 deg |
| Duration at greatest eclipse | 06m23s | 382.5 s |
| Luxor duration | 6m19-6m23s | 380.0 s |
| Seconds Luxor sacrifices | a few | 3.1 s |
| Countries crossed | 9, not incl. Sudan | confirmed |
| Aden / Berbera | partial only | confirmed |

## Notes on correctness

**Delta T is load-bearing.** `mu` is tabulated against TDT but expresses a
Greenwich hour angle, a UT quantity. The frames differ by delta T, so it must
be subtracted in the hour angle. Omitting it leaves latitude correct and shifts
longitude by delta_T * 15 / 3600 degrees, about 32 km for this eclipse. This
eclipse assumes delta T = 76.0 s; NASA's older 2027 map used 71.7 s.

**Greatest eclipse is not greatest duration.** For total eclipses these are
different points, differing by 1-2 seconds and 100+ km. Greatest eclipse is
where the shadow axis passes closest to Earth's centre; greatest duration is
where totality lasts longest. Here they are 0.6 s and ~215 km apart. See
[Espenak on the distinction](https://eclipsewise.com/solar/SEhelp/SEgreatest.html).

**Two lunar radius constants.** k1 = 0.272488 for penumbral contacts,
k2 = 0.272281 for umbral. Duration and path limits use the umbral value.

**Lunar limb profile** shifts path limits by 1-2 km and duration by 1-3 s.
Limb-corrected predictions only appear 12-18 months before an event.

## Coverage

772 of 9,191 places in the nine path countries are inside totality.

| Country | Places | Best |
|---|---|---|
| Algeria | 186 | Arris, 5m30s |
| Tunisia | 136 | Mahires, 5m42s |
| Spain | 118 | Principe, 4m48s |
| Yemen | 114 | Baqim as Suq, 6m00s |
| Morocco | 89 | Mdiq, 4m52s |
| Egypt | 60 | Girga, 6m23s |
| Saudi Arabia | 43 | Al Lith, 6m10s |
| Libya | 18 | Benghazi, 6m09s |
| Somalia | 8 | Qandala, 5m27s |

Those counts are GeoNames density, not reality. Spain having 118 entries and
Somalia 8 says more about who edits the gazetteer than about where towns are.
A place missing here is missing from GeoNames.

## Data sources

- Besselian elements: NASA GSFC. *Eclipse Predictions by Fred Espenak, NASA's GSFC.*
- Prior art worth using: [eclipsewhere.com](https://eclipsewhere.com) for
  curated cloud-first guidance, [Xavier Jubier's interactive map](http://xjubier.free.fr/en/site_pages/solar_eclipses/xSE_GoogleMap3.php?Ecl=+20270802)
  for point queries, [Eclipsophile](https://eclipsophile.com/tse2027/) for
  the authoritative cloud climatology.
