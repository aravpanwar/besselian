'use strict';

const EVENT = '2027-08-02';
const R_EARTH = 6371.0088;

const state = {
  data: null,
  pin: null,          // {lat, lon} or null for the whole path
  radius: 120,
  sort: 's',
  selected: null,     // geonameid
};

/* ---------- geometry ---------- */

// Great-circle distance. Circle membership is by this, never point-in-polygon
// against the drawn circle: a polygon approximation makes edge towns flicker
// in and out depending on how finely it was tessellated.
function haversine(lat1, lon1, lat2, lon2) {
  const p1 = lat1 * Math.PI / 180;
  const p2 = lat2 * Math.PI / 180;
  const dp = p2 - p1;
  const dl = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dp / 2) ** 2 +
            Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * R_EARTH * Math.asin(Math.sqrt(a));
}

// A geodesic circle, drawn as a polygon only for display.
function circlePolygon(lat, lon, km, steps = 180) {
  const coords = [];
  const d = km / R_EARTH;
  const p1 = lat * Math.PI / 180;
  const l1 = lon * Math.PI / 180;
  for (let i = 0; i <= steps; i++) {
    const brg = (i / steps) * 2 * Math.PI;
    const p2 = Math.asin(Math.sin(p1) * Math.cos(d) +
                         Math.cos(p1) * Math.sin(d) * Math.cos(brg));
    const l2 = l1 + Math.atan2(Math.sin(brg) * Math.sin(d) * Math.cos(p1),
                               Math.cos(d) - Math.sin(p1) * Math.sin(p2));
    coords.push([l2 * 180 / Math.PI, p2 * 180 / Math.PI]);
  }
  return { type: 'Feature', geometry: { type: 'Polygon', coordinates: [coords] } };
}

/* ---------- formatting ---------- */

// Truncate, never round: 382.9 s is 6:22, not 6:23.
function mmss(seconds) {
  const t = Math.floor(seconds);
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`;
}

const fmtKm = (v) => (v == null ? '—' : v.toFixed(1));
const fmtPct = (v) => (v == null ? '—' : v.toFixed(1) + '%');

/* ---------- selection ---------- */

function inCircle() {
  const all = state.data.places;
  if (!state.pin) return all;
  return all.filter((p) =>
    haversine(state.pin.lat, state.pin.lon, p.y, p.x) <= state.radius);
}

function sorted(list) {
  const k = state.sort;
  const copy = list.slice();
  // Seconds lost and cloud sort ascending (less is better); beds and
  // population descending (more is more).
  const asc = (k === 's' || k === 'w');
  copy.sort((a, b) => {
    const av = a[k], bv = b[k];
    if (av == null) return 1;
    if (bv == null) return -1;
    return asc ? av - bv : bv - av;
  });
  return copy;
}

function byCountry(list) {
  const groups = new Map();
  for (const p of list) {
    if (!groups.has(p.c)) groups.set(p.c, []);
    groups.get(p.c).push(p);
  }
  // Country order follows the best row in each, so the ordering the user
  // chose drives the groups too.
  return [...groups.entries()].sort((a, b) => {
    const ia = list.indexOf(a[1][0]);
    const ib = list.indexOf(b[1][0]);
    return ia - ib;
  });
}

/* ---------- rendering ---------- */

const WARN_ICON = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none"
  stroke="#a8621f" stroke-width="2" stroke-linecap="round" aria-hidden="true">
  <path d="M12 9v4"/><path d="M12 17h.01"/><circle cx="12" cy="12" r="9"/></svg>`;

function advisoryHtml(cc) {
  const a = state.data.advisories[cc];
  if (!a || !a.worst) return '';
  const regions = a.regions.length
    ? ` Named areas: ${a.regions.join(', ')}.`
    : '';
  return `<div class="advisory">${WARN_ICON}<span>${state.data.issuer
    .replace('UK Foreign, Commonwealth &amp; Development Office', 'FCDO')}
    ${a.label.toLowerCase()}.${regions}
    <a href="${a.url}" target="_blank" rel="noopener">Checked ${a.reviewed}</a>.</span></div>`;
}

function render() {
  const list = sorted(inCircle());
  const rows = document.getElementById('rows');

  document.getElementById('count').textContent =
    `${list.length} place${list.length === 1 ? '' : 's'}`;
  document.getElementById('where').textContent = state.pin
    ? `within ${state.radius} km of ${state.pin.lat.toFixed(4)}°N ` +
      `${state.pin.lon.toFixed(4)}°E`
    : 'across the whole path';

  if (!list.length) {
    rows.innerHTML = `<p class="empty">No populated places inside this circle.
      Nothing is hidden: this circle simply contains none that GeoNames
      records.</p>`;
    updateFinding(list);
    return;
  }

  let html = '';
  for (const [cc, places] of byCountry(list)) {
    const name = state.data.advisories[cc]
      ? state.data.advisories[cc].country : cc;
    html += `<div class="group"><div class="name"><b>${name}</b>
      <span class="n">${places.length}</span></div>
      ${advisoryHtml(cc)}</div>`;
    html += `<div class="head"><div>Place</div><div class="num">Totality</div>
      <div class="num">Lost</div><div class="num">Cloud</div>
      <div class="num">Beds</div></div>`;
    for (const p of places) {
      const sel = p.i === state.selected ? ' sel' : '';
      html += `<div class="row${sel}" data-id="${p.i}" tabindex="0" role="button"
        aria-label="${p.n}, ${mmss(p.d)} of totality">
        <div class="nm">${p.n}</div>
        <div class="num dur">${mmss(p.d)}</div>
        <div class="num${p.s < 1 ? ' near' : ''}">−${p.s.toFixed(1)}</div>
        <div class="num">${fmtPct(p.w)}</div>
        <div class="num${p.l < 10 ? ' thin' : ''}">${p.l}</div>
      </div>`;
    }
  }
  rows.innerHTML = html;
  updateFinding(list);
  drawPlaces(list);
  drawCircle();
}

function updateFinding(list) {
  const box = document.getElementById('finding');
  const el = document.getElementById('fText');

  // The sleep-and-stand comparison only means something over a distance you
  // would actually drive. Across the whole path it picks the largest city
  // anywhere, which is not an alternative to anything, so the panel only
  // appears once a circle has been drawn.
  if (!state.pin || list.length < 2) {
    box.hidden = true;
    return;
  }

  const best = list.slice().sort((a, b) => a.s - b.s)[0];

  // Compare against the place the pin is on, if it is on one. That is the
  // town the user is actually asking about. Ranking by lodging instead picks
  // whichever of the villages around a city happens to share its hotel count,
  // because a 25 km radius sweeps up the same hotels for all of them; ranking
  // by population is no better, since GeoNames mixes town and district
  // figures and puts Esna's markaz above the city of Luxor.
  let most = list.find((q) =>
    haversine(state.pin.lat, state.pin.lon, q.y, q.x) < 3);
  if (!most) {
    most = list.slice().sort((a, b) => (b.l - a.l) || (b.p - a.p))[0];
  }

  if (best.i === most.i) {
    box.hidden = false;
    document.getElementById('fBestDur').textContent = mmss(best.d);
    document.getElementById('fBestSub').textContent =
      `${best.n} · ${best.l} bed${best.l === 1 ? '' : 's'}`;
    document.getElementById('fRefDur').textContent = '—';
    document.getElementById('fRefSub').textContent = 'nothing to trade';
    document.getElementById('fGap').textContent = '0 km';
    el.textContent = `${best.n} has both the most places to stay in this ` +
      `circle and the longest totality. Nothing to trade.`;
    return;
  }

  box.hidden = false;
  document.getElementById('fBestDur').textContent = mmss(best.d);
  document.getElementById('fBestSub').textContent =
    `${best.n} · ${best.l} bed${best.l === 1 ? '' : 's'}`;
  document.getElementById('fRefDur').textContent = mmss(most.d);
  document.getElementById('fRefSub').textContent =
    `${most.n} · ${most.l} bed${most.l === 1 ? '' : 's'}`;

  const gap = haversine(best.y, best.x, most.y, most.x);
  document.getElementById('fGap').textContent = `${gap.toFixed(0)} km`;

  const better = list.filter((p) => p.s < most.s).length;
  const secs = (most.s - best.s).toFixed(1);
  el.textContent = `${most.n} has ${most.l} place${most.l === 1 ? '' : 's'} ` +
    `to stay within 25 km. ${better} town${better === 1 ? '' : 's'} in this ` +
    `circle beat${better === 1 ? 's' : ''} it on totality. The best, ` +
    `${best.n}, is ${gap.toFixed(0)} km away, has ` +
    `${best.l} bed${best.l === 1 ? '' : 's'}, and buys ${secs} s.`;
}

/* ---------- map ---------- */

let map;

function initMap() {
  map = new maplibregl.Map({
    container: 'map',
    style: 'https://tiles.openfreemap.org/styles/positron',
    center: [32.0, 26.3],
    zoom: 5.4,
    attributionControl: { compact: false },
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }),
                 'bottom-right');
  map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: 'metric' }),
                 'bottom-right');

  map.on('load', async () => {
    const path = await fetch(`data/${EVENT}-path.geojson`).then((r) => r.json());
    map.addSource('path', { type: 'geojson', data: path });

    map.addLayer({
      id: 'umbra', type: 'fill', source: 'path',
      filter: ['==', ['get', 'kind'], 'umbra'],
      paint: { 'fill-color': '#1a5c7a', 'fill-opacity': 0.10 },
    });
    map.addLayer({
      id: 'umbra-edge', type: 'line', source: 'path',
      filter: ['==', ['get', 'kind'], 'umbra'],
      paint: {
        'line-color': '#7fa0b2', 'line-width': 1.2, 'line-dasharray': [4, 3],
      },
    });
    map.addLayer({
      id: 'centreline', type: 'line', source: 'path',
      filter: ['==', ['get', 'kind'], 'centerline'],
      paint: { 'line-color': '#1a5c7a', 'line-width': 2 },
    });

    map.addSource('circle', { type: 'geojson', data: emptyFC() });
    map.addLayer({
      id: 'circle-fill', type: 'fill', source: 'circle',
      paint: { 'fill-color': '#1a5c7a', 'fill-opacity': 0.05 },
    });
    map.addLayer({
      id: 'circle-edge', type: 'line', source: 'circle',
      paint: {
        'line-color': '#1a5c7a', 'line-width': 1.5, 'line-dasharray': [3, 2],
      },
    });

    map.addSource('places', { type: 'geojson', data: emptyFC() });
    map.addLayer({
      id: 'places', type: 'circle', source: 'places',
      paint: {
        // Radius by population, so the map answers "what is near here"
        // without reading the table.
        'circle-radius': [
          'interpolate', ['linear'], ['get', 'pop'],
          0, 2.5, 20000, 3.5, 100000, 5, 500000, 7.5, 2000000, 10,
        ],
        'circle-color': [
          'case', ['==', ['get', 'sel'], true], '#b5540e', '#3d382f',
        ],
        'circle-opacity': 0.85,
        'circle-stroke-width': ['case', ['==', ['get', 'sel'], true], 2, 0.5],
        'circle-stroke-color': '#fffefb',
      },
    });

    map.on('click', 'places', (e) => {
      const id = e.features[0].properties.id;
      selectPlace(id, false);
    });
    map.on('mouseenter', 'places', () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'places', () => {
      map.getCanvas().style.cursor = '';
    });
    // Clicking bare map drops the pin there.
    map.on('click', (e) => {
      const hit = map.queryRenderedFeatures(e.point, { layers: ['places'] });
      if (hit.length) return;
      setPin(e.lngLat.lat, e.lngLat.lng);
    });

    render();
  });
}

const emptyFC = () => ({ type: 'FeatureCollection', features: [] });

function drawPlaces(visible) {
  if (!map || !map.getSource('places')) return;
  const shown = new Set(visible.map((p) => p.i));
  const features = state.data.places
    .filter((p) => shown.has(p.i))
    .map((p) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [p.x, p.y] },
      properties: { id: p.i, pop: p.p, sel: p.i === state.selected },
    }));
  map.getSource('places').setData({
    type: 'FeatureCollection', features,
  });
}

function drawCircle() {
  if (!map || !map.getSource('circle')) return;
  map.getSource('circle').setData(
    state.pin
      ? { type: 'FeatureCollection',
          features: [circlePolygon(state.pin.lat, state.pin.lon, state.radius)] }
      : emptyFC());
}

function selectPlace(id, fly) {
  state.selected = Number(id) === state.selected ? null : Number(id);
  const p = state.data.places.find((q) => q.i === state.selected);
  if (p) {
    showPopup(p);
    if (fly) map.easeTo({ center: [p.x, p.y], duration: 500 });
  } else if (popup) {
    popup.remove();
  }
  render();
  writeUrl();
}

let popup = null;

function showPopup(p) {
  if (popup) popup.remove();
  const adv = state.data.advisories[p.c];
  popup = new maplibregl.Popup({ closeButton: true, offset: 10 })
    .setLngLat([p.x, p.y])
    .setHTML(`<div class="pop"><b>${p.n}</b><dl>
      <dt>Totality</dt><dd>${mmss(p.d)}</dd>
      <dt>Seconds lost</dt><dd>−${p.s.toFixed(1)}</dd>
      <dt>From centre line</dt><dd>${fmtKm(p.k)} km</dd>
      <dt>Sun altitude</dt><dd>${p.a.toFixed(1)}°</dd>
      <dt>August cloud</dt><dd>${fmtPct(p.w)}</dd>
      <dt>Beds within 25 km</dt><dd>${p.l}</dd>
      <dt>Beds within 80 km</dt><dd>${p.L}</dd>
      </dl></div>`)
    .addTo(map);
}

function setPin(lat, lon) {
  state.pin = { lat, lon };
  document.getElementById('clearPin').hidden = false;
  drawCircle();
  render();
  writeUrl();
}

function clearPin() {
  state.pin = null;
  document.getElementById('clearPin').hidden = true;
  drawCircle();
  render();
  writeUrl();
}

/* ---------- url state ---------- */

function writeUrl() {
  const q = new URLSearchParams();
  if (state.pin) {
    q.set('at', `${state.pin.lat.toFixed(4)},${state.pin.lon.toFixed(4)}`);
    q.set('r', String(state.radius));
  }
  if (state.sort !== 's') q.set('sort', state.sort);
  if (state.selected) q.set('place', String(state.selected));
  const url = q.toString() ? `?${q}` : location.pathname;
  history.replaceState(null, '', url);
}

function readUrl() {
  const q = new URLSearchParams(location.search);
  const at = q.get('at');
  if (at && /^-?\d+(\.\d+)?,-?\d+(\.\d+)?$/.test(at)) {
    const [lat, lon] = at.split(',').map(Number);
    if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
      state.pin = { lat, lon };
    }
  }
  const r = Number(q.get('r'));
  if (r >= 10 && r <= 400) state.radius = r;
  const s = q.get('sort');
  if (['s', 'w', 'l', 'p'].includes(s)) state.sort = s;
  const place = Number(q.get('place'));
  if (place) state.selected = place;
}

/* ---------- wiring ---------- */

function bind() {
  const radius = document.getElementById('radius');
  const out = document.getElementById('radiusOut');
  radius.value = state.radius;
  out.value = `${state.radius} km`;
  radius.addEventListener('input', () => {
    state.radius = Number(radius.value);
    out.value = `${state.radius} km`;
    drawCircle();
    render();
  });
  radius.addEventListener('change', writeUrl);

  document.getElementById('clearPin').addEventListener('click', clearPin);

  document.getElementById('sortbar').addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    state.sort = b.dataset.sort;
    for (const x of document.querySelectorAll('#sortbar button')) {
      const on = x === b;
      x.classList.toggle('active', on);
      x.setAttribute('aria-pressed', String(on));
    }
    render();
    writeUrl();
  });

  const rows = document.getElementById('rows');
  rows.addEventListener('click', (e) => {
    const row = e.target.closest('.row');
    if (row) selectPlace(row.dataset.id, true);
  });
  rows.addEventListener('keydown', (e) => {
    const row = e.target.closest('.row');
    if (!row) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      selectPlace(row.dataset.id, true);
    }
  });
}

async function main() {
  readUrl();
  state.data = await fetch(`data/${EVENT}-places.json`).then((r) => r.json());

  document.getElementById('dt').textContent = state.data.event.delta_t;
  document.getElementById('stats').innerHTML =
    `<span>ΔT ${state.data.event.delta_t} s</span>
     <span>${state.data.places.length} places</span>
     <span>${Object.keys(state.data.advisories).length} countries</span>`;
  document.querySelector('nav a[download]').href =
    `data/${EVENT}-places.csv`;

  bind();
  if (state.pin) document.getElementById('clearPin').hidden = false;
  initMap();
}

main();
