# Totality Path & Nearby Locations
# Copyright (C) 2026 Arav Panwar
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. See <https://www.gnu.org/licenses/>.

"""Path geometry: greatest duration, centerline, and per-place ranking."""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import local_circumstances as L
from .places import Place, haversine_km


def greatest_duration(elements: L.Elements, seed: tuple[float, float],
                      tol_deg: float = 1e-6) -> tuple[float, float, float]:
    """Hill-climb to the point of greatest duration.

    Distinct from greatest eclipse, which is where the shadow axis passes
    closest to Earth's centre. For a total eclipse the two differ by 1-2 s and
    can be 100+ km apart, so the denominator for "seconds sacrificed" has to be
    this point, not the more widely quoted greatest-eclipse coordinates.
    """
    lat, lon = seed
    best = L.compute(lat, lon, 0.0, elements).duration_seconds or 0.0
    step = 0.5
    while step > tol_deg:
        moved = False
        for dla, dlo in ((step, 0.0), (-step, 0.0), (0.0, step), (0.0, -step),
                         (step, step), (step, -step), (-step, step), (-step, -step)):
            c = L.compute(lat + dla, lon + dlo, 0.0, elements)
            if c.duration_seconds and c.duration_seconds > best + 1e-12:
                best, lat, lon, moved = c.duration_seconds, lat + dla, lon + dlo, True
                break
        if not moved:
            step /= 2.0
    return lat, lon, best


_CENTERLINE_CACHE: dict[tuple[int, float], float | None] = {}


def centerline_latitude(lon: float, elements: L.Elements) -> float | None:
    """Latitude where the shadow axis pierces Earth at this longitude.

    Solved by minimising the observer's distance from the shadow axis, using
    the same forward model as everything else. Deriving the piercing point by
    inverting the fundamental-plane equations is faster but introduced errors
    of several km once flattening was accounted for, so this pays a little
    compute to keep one source of truth.
    """
    key = (id(elements), round(lon, 6))
    if key in _CENTERLINE_CACHE:
        return _CENTERLINE_CACHE[key]

    lo, hi = -60.0, 60.0
    # Coarse scan first: the axis-distance function has one minimum in lat but
    # a golden-section search needs a bracketing interval to be safe.
    best_lat, best_m = None, float('inf')
    n = 280
    for i in range(n + 1):
        lat = lo + (hi - lo) * i / n
        m = L.compute(lat, lon, 0.0, elements).distance_from_axis_radii
        if m < best_m:
            best_m, best_lat = m, lat
    if best_lat is None:
        _CENTERLINE_CACHE[key] = None
        return None
    span = (hi - lo) / n
    a, b = best_lat - span, best_lat + span
    for _ in range(90):
        m1 = a + (b - a) * 0.382
        m2 = a + (b - a) * 0.618
        f1 = L.compute(m1, lon, 0.0, elements).distance_from_axis_radii
        f2 = L.compute(m2, lon, 0.0, elements).distance_from_axis_radii
        if f1 < f2:
            b = m2
        else:
            a = m1
    result = (a + b) / 2.0
    _CENTERLINE_CACHE[key] = result
    return result


def build_centerline(elements: L.Elements, lon_lo: float, lon_hi: float,
                     step: float = 0.25) -> list[tuple[float, float]]:
    """Sample the centerline across a longitude range, once per build."""
    track: list[tuple[float, float]] = []
    lon = lon_lo
    while lon <= lon_hi:
        lat = centerline_latitude(lon, elements)
        if lat is not None:
            c = L.compute(lat, lon, 0.0, elements)
            if c.distance_from_axis_radii < 1e-3:
                track.append((lat, lon))
        lon += step
    return track


def distance_from_centerline_km(lat: float, lon: float,
                                track: list[tuple[float, float]],
                                elements: L.Elements) -> float | None:
    """Great-circle distance to the centerline.

    Uses the sampled track to bracket, then refines against the exact solve so
    the answer does not depend on the track's sampling interval. Geodesic
    throughout; never Web Mercator.
    """
    if not track:
        return None
    # Nearest sampled point.
    best_i, best_d = None, float('inf')
    for i, (tlat, tlon) in enumerate(track):
        if abs(tlon - lon) > 15.0:
            continue
        d = haversine_km(lat, lon, tlat, tlon)
        if d < best_d:
            best_d, best_i = d, i
    if best_i is None:
        return None

    # Refine in longitude around that sample, solving the centerline exactly.
    lo = track[max(0, best_i - 1)][1]
    hi = track[min(len(track) - 1, best_i + 1)][1]
    if hi < lo:
        lo, hi = hi, lo

    def dist_at(tlon: float) -> float:
        tlat = centerline_latitude(tlon, elements)
        if tlat is None:
            return float('inf')
        return haversine_km(lat, lon, tlat, tlon)

    for _ in range(40):
        m1 = lo + (hi - lo) * 0.382
        m2 = lo + (hi - lo) * 0.618
        if dist_at(m1) < dist_at(m2):
            hi = m2
        else:
            lo = m1
    return min(best_d, dist_at((lo + hi) / 2.0))


@dataclass
class RankedPlace:
    place: Place
    duration_seconds: float
    seconds_sacrificed: float
    sun_altitude_deg: float
    max_eclipse_ut_hours: float
    distance_from_centerline_km: float | None

    def as_row(self) -> dict:
        p = self.place
        return {
            'geonameid': p.geonameid,
            'name': p.name,
            'country_code': p.country_code,
            'country': p.country,
            'latitude': round(p.latitude, 5),
            'longitude': round(p.longitude, 5),
            'elevation_m': int(p.elevation_m),
            'population': p.population,
            'timezone': p.timezone,
            'duration_seconds': round(self.duration_seconds, 1),
            'seconds_sacrificed': round(self.seconds_sacrificed, 1),
            'sun_altitude_deg': round(self.sun_altitude_deg, 2),
            'max_eclipse_ut_hours': round(self.max_eclipse_ut_hours, 6),
            'distance_from_centerline_km': (
                round(self.distance_from_centerline_km, 1)
                if self.distance_from_centerline_km is not None else None),
        }


def rank(places: list[Place], elements: L.Elements, peak_duration: float,
         track: list[tuple[float, float]] | None = None) -> list[RankedPlace]:
    """Compute circumstances for every place and keep those inside totality."""
    out: list[RankedPlace] = []
    for p in places:
        c = L.compute(p.latitude, p.longitude, p.elevation_m, elements)
        if not c.in_totality or not c.duration_seconds:
            continue
        out.append(RankedPlace(
            place=p,
            duration_seconds=c.duration_seconds,
            seconds_sacrificed=peak_duration - c.duration_seconds,
            sun_altitude_deg=c.sun_altitude_deg,
            max_eclipse_ut_hours=c.max_eclipse_ut_hours,
            distance_from_centerline_km=(
                distance_from_centerline_km(p.latitude, p.longitude, track, elements)
                if track else None),
        ))
    out.sort(key=lambda r: r.seconds_sacrificed)
    return out
