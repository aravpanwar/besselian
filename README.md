# Eclipse Path Map

Computed local circumstances for every populated place inside the path of a
total solar eclipse, so you can see what a location actually costs you in
seconds of totality.

Status: computation core validated. No frontend yet.

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

## Data sources

- Besselian elements: NASA GSFC. *Eclipse Predictions by Fred Espenak, NASA's GSFC.*
- Prior art worth using: [eclipsewhere.com](https://eclipsewhere.com) for
  curated cloud-first guidance, [Xavier Jubier's interactive map](http://xjubier.free.fr/en/site_pages/solar_eclipses/xSE_GoogleMap3.php?Ecl=+20270802)
  for point queries, [Eclipsophile](https://eclipsophile.com/tse2027/) for
  the authoritative cloud climatology.
