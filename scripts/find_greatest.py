"""Locate greatest duration by walking the centerline, not a lat/lon grid.

The duration field is very flat along the path, so a naive box search drifts
kilometres along the ridge. The centerline is where the axis pierces Earth, so
solve for that curve in time and maximise duration along it.
"""
import sys, math
sys.path.insert(0, 'src')
import eclipse.local_circumstances as L

E = L.Elements.from_json('data/elements/2027-08-02.json')
LUXOR = (25.6872, 32.6396)


def centerline_point(t):
    """Geodetic lat/lon where the shadow axis pierces the ellipsoid at time t."""
    el = E.at(t)
    x, y = el['x'], el['y']
    d = math.radians(el['d'])
    mu = el['mu'] - E.delta_t_seconds / 3600.0 * 15.0

    rho = math.hypot(x, y)
    if rho >= 1.0:
        return None
    # Iterate for the piercing point on the flattened Earth.
    f = L.FLATTENING
    zeta = math.sqrt(1.0 - rho * rho)
    for _ in range(60):
        lat_c = math.asin(max(-1.0, min(1.0, y * math.cos(d) + zeta * math.sin(d))))
        # Correct zeta for flattening at this latitude.
        rho_s, rho_c = L.geocentric_observer(math.degrees(
            math.atan(math.tan(lat_c) / (1.0 - f) ** 2)), 0.0, 0.0)
        r = math.hypot(rho_s, rho_c)
        new_zeta = math.sqrt(max(0.0, r * r - rho * rho))
        if abs(new_zeta - zeta) < 1e-12:
            break
        zeta = new_zeta
    lat_c = math.asin(max(-1.0, min(1.0, y * math.cos(d) + zeta * math.sin(d))))
    denom = zeta * math.cos(d) - y * math.sin(d)
    H = math.degrees(math.atan2(x, denom))
    lon = H - mu
    lon = ((lon + 180.0) % 360.0) - 180.0
    lat_gd = math.degrees(math.atan(math.tan(lat_c) / (1.0 - f) ** 2))
    return lat_gd, lon


def haversine_km(a, b):
    R = 6371.0088
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    h = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def bearing_deg(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    return math.degrees(math.atan2(
        math.sin(dl) * math.cos(p2),
        math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl))) % 360


def compass(b):
    pts = ['N','NNE','NE','ENE','E','ESE','SE','SSE','S','SSW','SW','WSW','W','WNW','NW','NNW']
    return pts[int((b + 11.25) % 360 / 22.5)]


# Golden-section on t along the centerline.
lo, hi = -1.0, 1.0
for _ in range(200):
    m1 = lo + (hi - lo) * 0.382
    m2 = lo + (hi - lo) * 0.618
    def dur(t):
        p = centerline_point(t)
        if not p:
            return -1.0
        c = L.compute(p[0], p[1], 0.0, E)
        return c.duration_seconds or -1.0
    if dur(m1) < dur(m2):
        lo = m1
    else:
        hi = m2
t_best = (lo + hi) / 2
pt = centerline_point(t_best)
c = L.compute(pt[0], pt[1], 0.0, E)

print('GREATEST DURATION (centerline search)')
print('  location  : %.4f N, %.4f E' % pt)
print('  NASA says : 25.5 N, 33.2 E')
print('  duration  : %.1f s (%dm%02ds)   NASA: 06m23s' % (
    c.duration_seconds, c.duration_seconds // 60, c.duration_seconds % 60))
print('  sun alt   : %.2f deg            NASA: 81.7' % c.sun_altitude_deg)
print('  offset from NASA point: %.1f km' % haversine_km(pt, (25.5, 33.2)))
print()
d = haversine_km(LUXOR, pt)
b = bearing_deg(LUXOR, pt)
print('  from Luxor: %.1f km, bearing %.0f deg (%s)   brief says ~60 km SE' % (d, b, compass(b)))
print()
lux = L.compute(LUXOR[0], LUXOR[1], 76, E)
print('LUXOR')
print('  duration   : %.1f s (%dm%02ds)' % (
    lux.duration_seconds, lux.duration_seconds // 60, lux.duration_seconds % 60))
print('  sacrificed : %.1f s' % (c.duration_seconds - lux.duration_seconds))
