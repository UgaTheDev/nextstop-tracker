'use strict';
// Static tracker front end. All data-derived text goes through esc() before innerHTML.
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const isN = v => typeof v === 'number' && isFinite(v);
const f1 = v => isN(v) ? v.toFixed(1) : 'n/a';
const f2 = v => isN(v) ? v.toFixed(2) : 'n/a';
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const mlabel = m => { const p = (m || '').match(/^(\d{4})-(\d{2})$/); return p ? MON[+p[2] - 1] + ' ' + p[1] : 'n/a'; };
const mshort = m => mlabel(m).replace(' 20', " '");
const pct = v => isN(v) ? (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(1) + '%' : 'n/a';
// color and arrows only for moves of 1% or more: smaller moves are flat, not good or bad
const pctCls = v => isN(v) && Math.abs(v) >= 1 ? (v > 0 ? 'up' : 'down') : '';
const arrow = v => isN(v) && Math.abs(v) >= 1 ? (v > 0 ? '▲ ' : '▼ ') : '';
const sg = (v, d) => isN(v) ? (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d) : 'n/a';
const BOROUGH = { BX: 'Bronx', MN: 'Manhattan', QN: 'Queens', BK: 'Brooklyn', SI: 'Staten Island', 'BK-QN': 'Brooklyn and Queens' };
const BCODE = { BX: 'Bx', MN: 'M', QN: 'Q', BK: 'Bk', SI: 'SI', 'BK-QN': 'Bk/Q' };
const bname = b => BOROUGH[b] || b;
const bcode = b => BCODE[b] || String(b || '').slice(0, 2);
// scrolling table wrappers must be reachable by keyboard
const a11yScroll = () => document.querySelectorAll('.tw').forEach(e => { e.tabIndex = 0; e.setAttribute('role', 'region'); e.setAttribute('aria-label', 'Scrollable table'); });
const $ = (s, r = document) => r.querySelector(s);
const app = $('#app');

// ---------- theme ----------
const THEME_KEY = 'nst-theme';
const curTheme = () => document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
function applyTheme(t, save) {
  document.documentElement.dataset.theme = t;
  if (save) { try { localStorage.setItem(THEME_KEY, t); } catch (e) {} }
  const b = $('#theme'); if (b) b.textContent = t === 'dark' ? 'Light theme' : 'Dark theme';
}

// ---------- chrome ----------
const LOGO = '<svg width="36" height="36" viewBox="0 0 48 48" aria-hidden="true" focusable="false"><rect x="6" y="3" width="36" height="28" rx="5" style="fill:var(--logo-sign)"/><rect x="21.5" y="31" width="5" height="15" style="fill:var(--logo-sign)"/><path d="M14 17h18M25 10l7 7-7 7" fill="none" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" style="stroke:var(--logo-arrow)"/></svg>';
function chrome() {
  const page = document.body.dataset.page === 'corridor' ? 'home' : document.body.dataset.page;
  const links = [['home', 'index.html', 'Corridors'], ['commitments', 'commitments.html', 'Commitments'], ['ace', 'ace.html', 'Camera enforcement'], ['methods', 'methods.html', 'Methods']];
  $('#chrome-top').innerHTML = '<div class="strip"><div class="wrap">An independent project by <a href="https://www.linkedin.com/in/kush-zingade">Kush Zingade</a>. Not affiliated with NYC DOT or the MTA.</div></div>' +
    '<header class="site"><div class="wrap bar"><a class="brand" href="index.html">' + LOGO + '<span>Next Stop Tracker</span></a>' +
    '<button type="button" class="btn menu" id="menu" aria-expanded="false" aria-controls="nav">Menu</button>' +
    '<nav id="nav" aria-label="Main">' + links.map(l => `<a href="${l[1]}"${l[0] === page ? ' aria-current="page"' : ''}>${l[2]}</a>`).join('') +
    '<button type="button" class="btn" id="theme"></button></nav></div></header>';
  $('#chrome-bottom').innerHTML = '<footer class="site"><div class="wrap foot"><p>An independent project by <a href="https://www.linkedin.com/in/kush-zingade">Kush Zingade</a>. Not affiliated with NYC DOT or the MTA. Corridor definitions are our own: the plan does not publish stop-level definitions. Data: MTA bus segment speeds on data.ny.gov.</p>' +
    '<nav aria-label="Footer"><a href="methods.html">Methods</a><a href="methods.html#report">Report a wrong corridor</a><a href="data/corridors.json">Data</a><a href="https://github.com/UgaTheDev/nextstop-tracker">Code</a></nav></div></footer>';
  applyTheme(curTheme(), false);
  $('#theme').addEventListener('click', () => applyTheme(curTheme() === 'dark' ? 'light' : 'dark', true));
  const menu = $('#menu'), hd = $('header.site');
  menu.addEventListener('click', () => { const o = hd.classList.toggle('open'); menu.setAttribute('aria-expanded', o); });
}

// ---------- data loading: sample fixture ONLY on 404 and ONLY on localhost ----------
const LOCAL = ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
async function load(real, sample) {
  let r;
  try { r = await fetch(real); } catch (e) { return { err: 'Could not load ' + real }; }
  if (r.ok) { try { return { data: await r.json() }; } catch (e) { return { err: real + ' is not valid JSON' }; } }
  if (r.status !== 404 || !LOCAL) return { err: r.status === 404 ? 'The data file is not available right now.' : `Could not load ${real} (HTTP ${r.status})` };
  try { const s = await fetch(sample); if (!s.ok) return { err: 'No data file yet' }; return { data: await s.json(), sample: true }; }
  catch (e) { return { err: 'No data file yet' }; }
}
const banner = (inner, role) => `<div class="warn"><div class="wrap"><span class="bang" aria-hidden="true">!</span><div${role ? ` role="${role}"` : ''}>${inner}</div></div></div>`;
const sampleBanner = () => banner('<strong>Sample data.</strong> The real data file was not found, so these are made-up fixture numbers for layout testing. Do not cite them.', 'status');
const errBox = m => banner(esc(m), 'alert');
const hero = (inner, cls = '') => `<section class="hero ${cls}"><div class="wrap">${inner}</div></section>`;
const stat = (fig, unit, lab, cls = '') => `<div class="stat"><div class="fig ${cls}">${fig}${unit ? ` <span class="unit">${unit}</span>` : ''}</div><div class="lab">${lab}</div></div>`;

// ---------- sortable tables ----------
// Unmapped rows (data-t="n") always sort last; rows with no value for the column come after rows with one.
function sortable(table, onSort) {
  const ths = [...table.tHead.rows[0].cells];
  const rank = r => r.dataset.t === 'n' ? 2 : r.dataset.t === 'm' ? 1 : 0;
  ths.forEach((th, i) => {
    if (th.dataset.nosort !== undefined) return;
    const label = th.textContent;
    th.innerHTML = `<button type="button" aria-label="Sort by ${esc(label)}">${esc(label)}</button>`;
    th.setAttribute('aria-sort', 'none');
    const run = dir => {
      ths.forEach(t => t.setAttribute('aria-sort', 'none')); th.setAttribute('aria-sort', dir);
      const rows = [...table.tBodies[0].rows];
      const key = r => { const c = r.cells[i]; const v = c.dataset.v ?? c.textContent; return v === '' ? null : v; };
      rows.sort((a, b) => {
        if (rank(a) !== rank(b)) return rank(a) - rank(b);
        let x = key(a), y = key(b);
        if (x === null && y === null) return 0; if (x === null) return 1; if (y === null) return -1; // nulls last
        const nx = +x, ny = +y;
        const c = isFinite(nx) && isFinite(ny) && x !== '' && y !== '' ? nx - ny : String(x).localeCompare(String(y));
        return dir === 'ascending' ? c : -c;
      });
      table.tBodies[0].append(...rows);
      if (onSort) onSort(th, dir);
    };
    $('button', th).addEventListener('click', () => run(th.getAttribute('aria-sort') === 'ascending' ? 'descending' : 'ascending'));
    th._run = run;
  });
  return ths;
}

// ---------- svg bits ----------
function sparkline(c) {
  const pts = (c.series || []).filter(s => isN(s.mph));
  if (pts.length < 2) return '<span class="tag no">no series</span>';
  const vals = pts.map(p => p.mph).concat(isN(c.baseline_mph) ? [c.baseline_mph] : []);
  const mn = Math.min(...vals), mx = Math.max(...vals), w = 112, h = 28, sp = mx - mn || 1;
  const X = i => 4 + i / (pts.length - 1) * (w - 8), Y = v => h - 4 - (v - mn) / sp * (h - 8);
  const d = pts.map((p, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(p.mph).toFixed(1)).join('');
  const base = isN(c.baseline_mph) ? `<line x1="0" x2="${w}" y1="${Y(c.baseline_mph).toFixed(1)}" y2="${Y(c.baseline_mph).toFixed(1)}" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 3"/>` : '';
  const last = pts[pts.length - 1];
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="Monthly speed trend, ${f1(Math.min(...pts.map(p => p.mph)))} to ${f1(Math.max(...pts.map(p => p.mph)))} mph, dashed line is the baseline">${base}<path d="${d}" fill="none" stroke="var(--ink)" stroke-width="2" stroke-linejoin="round"/><circle cx="${X(pts.length - 1).toFixed(1)}" cy="${Y(last.mph).toFixed(1)}" r="3.5" fill="var(--ink)"/></svg>`;
}

// Corridor line chart. v = 'd' (desktop viewBox) or 'p' (phone viewBox); CSS shows one of the two.
function lineChart(c, d, v) {
  const P = v === 'p';
  const W = P ? 358 : 840, H = P ? 232 : 340, L = P ? 34 : 56, R = P ? 68 : 110, T = 20, B = P ? 32 : 40, fs = P ? 12 : 13, lh = P ? 14 : 16;
  const ser = c.series.filter(s => isN(s.mph));
  const all = ser.map(s => s.mph).concat([c.baseline_mph, c.target_mph].filter(isN));
  // y range chosen per corridor so it always includes the baseline, the target and every month
  let lo = Math.floor(Math.min(...all) - 0.05), hi = Math.ceil(Math.max(...all) + 0.05);
  if (hi - lo < 2) hi = lo + 2;
  const step = Math.max(1, Math.ceil((hi - lo) / 4)); hi = lo + step * Math.ceil((hi - lo) / step);
  const n = c.series.length, pr = W - R, X = i => L + i / Math.max(n - 1, 1) * (pr - L), Y = x => T + (1 - (x - lo) / (hi - lo)) * (H - T - B), ay = H - B;
  let g = '';
  const idx = m => c.series.findIndex(s => s.month === m);
  const bf = idx(d.baseline?.from), bt = idx(d.baseline?.to);
  if (bf >= 0 && bt > bf) g += `<rect x="${X(bf).toFixed(1)}" y="${T}" width="${(X(bt) - X(bf)).toFixed(1)}" height="${ay - T}" style="fill:var(--surface)"/><text x="${(X(bf) + 6).toFixed(1)}" y="${ay - 8}" font-size="${P ? 11 : 12}" style="fill:var(--muted)">${P ? 'Baseline period' : 'Baseline period, 12 months before the plan'}</text>`;
  for (let t = lo; t <= hi; t += step) { const y = Y(t).toFixed(1); g += (t === lo ? `<line x1="${L}" x2="${pr}" y1="${y}" y2="${y}" stroke-width="1.5" style="stroke:var(--ink)"/>` : `<line x1="${L}" x2="${pr}" y1="${y}" y2="${y}" stroke-width="1" style="stroke:var(--rule)"/>`) + `<text x="${L - 8}" y="${(+y + 4).toFixed(1)}" font-size="${fs}" text-anchor="end" style="fill:var(--muted)">${t}</text>`; }
  const k = Math.max(1, Math.ceil((P ? 72 : 76) / ((pr - L) / Math.max(n - 1, 1))));
  c.series.forEach((s, i) => { if (i % k === 0) g += `<text x="${X(i).toFixed(1)}" y="${H - 10}" font-size="${fs}" text-anchor="middle" style="fill:var(--muted)">${esc(P ? mshort(s.month) : mlabel(s.month))}</text>`; });
  const pi = idx(d.plan_released);
  if (pi >= 0) { const bw = P ? 90 : 98, px = X(pi), bx = px - bw - 4 >= L ? px - bw - 4 : px + 4;
    g += `<line x1="${px.toFixed(1)}" x2="${px.toFixed(1)}" y1="${T}" y2="${ay}" stroke-width="2" style="stroke:var(--ink)"/><rect x="${bx.toFixed(1)}" y="${T + 4}" width="${bw}" height="${P ? 18 : 22}" style="fill:var(--ink)"/><text x="${(bx + bw / 2).toFixed(1)}" y="${T + (P ? 17 : 19.5)}" font-size="${fs}" font-weight="700" text-anchor="middle" style="fill:var(--bg)">Plan released</text>`; }
  if (isN(c.target_mph)) g += `<line x1="${L}" x2="${pr}" y1="${Y(c.target_mph).toFixed(1)}" y2="${Y(c.target_mph).toFixed(1)}" stroke-width="2.5" stroke-dasharray="${P ? '12 6' : '16 7'}" style="stroke:var(--target)"/>`;
  if (isN(c.baseline_mph)) g += `<line x1="${L}" x2="${pr}" y1="${Y(c.baseline_mph).toFixed(1)}" y2="${Y(c.baseline_mph).toFixed(1)}" stroke-width="2" stroke-dasharray="4 4" style="stroke:var(--muted)"/>`;
  let path = '', pen = false;
  c.series.forEach((s, i) => { if (!isN(s.mph)) { pen = false; return; } path += (pen ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(s.mph).toFixed(1); pen = true; });
  g += `<path d="${path}" fill="none" stroke-width="${P ? 2.5 : 3}" stroke-linejoin="round" style="stroke:var(--ink)"/>`;
  c.series.forEach((s, i) => { if (isN(s.mph)) g += `<circle cx="${X(i).toFixed(1)}" cy="${Y(s.mph).toFixed(1)}" r="6" fill="transparent"><title>${esc(mlabel(s.month))}: ${f2(s.mph)} mph (${esc(s.trips ?? 'n/a')} trips)</title></circle>`; });
  let li = -1; c.series.forEach((s, i) => { if (isN(s.mph)) li = i; });
  if (li >= 0) g += `<circle cx="${X(li).toFixed(1)}" cy="${Y(c.series[li].mph).toFixed(1)}" r="${P ? 5 : 5.5}" stroke-width="2.5" style="fill:var(--amber);stroke:var(--ink)"/>`;
  // direct labels at the right edge, pushed apart so they never overlap
  const labs = [];
  if (isN(c.target_mph)) labs.push({ y: Y(c.target_mph), lines: P ? ['Target', f2(c.target_mph)] : ['Target', f2(c.target_mph) + ' mph'], col: 'var(--target)' });
  if (isN(c.baseline_mph)) labs.push({ y: Y(c.baseline_mph), lines: P ? ['Baseline', f2(c.baseline_mph)] : ['Baseline ' + f2(c.baseline_mph)], col: 'var(--muted)' });
  if (li >= 0) labs.push({ y: Y(c.series[li].mph), lines: P ? ['Latest', f2(c.series[li].mph)] : [mlabel(c.series[li].month), f2(c.series[li].mph) + ' mph'], col: 'var(--ink)' });
  labs.sort((a, b) => a.y - b.y); let prev = -1e9;
  labs.forEach(l => { const h = l.lines.length * lh; const top = Math.max(l.y - h / 2, prev + 3); l.top = top; prev = top + h; });
  g += labs.map(l => l.lines.map((t, j) => `<text x="${pr + 8}" y="${(l.top + (j + 1) * lh - 3).toFixed(1)}" font-size="${fs}" font-weight="700" style="fill:${l.col}">${esc(t)}</text>`).join('')).join('');
  return `<svg class="cv-${v}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Monthly average weekday bus speed in mph for ${esc(c.name)}, with baseline and target lines">${g}</svg>`;
}

const binOf = x => !isN(x) ? -1 : x < 6 ? 0 : x < 7 ? 1 : x < 8 ? 2 : 3;
const binCol = x => binOf(x) < 0 ? 'var(--muted)' : `var(--s${binOf(x) + 1})`;

function segMap(c) {
  const segs = c.segments.filter(s => s.in_basis !== false && [s.from_lat, s.from_lon, s.to_lat, s.to_lon].every(isN));
  if (!segs.length) return '<p>No stop coordinates available for this corridor.</p>';
  const lats = segs.flatMap(s => [s.from_lat, s.to_lat]), lons = segs.flatMap(s => [s.from_lon, s.to_lon]);
  const k = Math.cos(Math.min(...lats) * Math.PI / 180);
  const x0 = Math.min(...lons), y1 = Math.max(...lats), dx = (Math.max(...lons) - x0) * k || 1e-4, dy = (y1 - Math.min(...lats)) || 1e-4;
  const W = 500, m = 40, sc = Math.min((W - 2 * m) / dx, 380 / dy), H = dy * sc + 2 * m;
  const P = (lat, lon) => [+(m + (lon - x0) * k * sc).toFixed(1), +(m + (y1 - lat) * sc).toFixed(1)];
  const lines = segs.map(s => { const a = P(s.from_lat, s.from_lon), b = P(s.to_lat, s.to_lon);
    return `<line class="seg" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${binCol(s.latest_mph)}"${isN(s.latest_mph) ? '' : ' stroke-dasharray="3 7"'}><title>${esc(s.route_id)} ${esc(s.direction)}: ${esc(s.from_stop)} to ${esc(s.to_stop)}, ${f1(s.latest_mph)} mph</title></line>`; }).join('');
  const seen = new Set(), dots = segs.flatMap(s => [P(s.from_lat, s.from_lon), P(s.to_lat, s.to_lon)]).filter(p => { const key = p.join(','); if (seen.has(key)) return false; seen.add(key); return true; })
    .map(p => `<circle class="stop" cx="${p[0]}" cy="${p[1]}" r="7"/>`).join('');
  // mph label for every segment, nudged down when two labels would sit on top of each other
  const placed = [];
  const labs = segs.filter(s => isN(s.latest_mph)).map(s => { const a = P(s.from_lat, s.from_lon), b = P(s.to_lat, s.to_lon); const x = (a[0] + b[0]) / 2; let y = (a[1] + b[1]) / 2 - 11;
    for (let t = 0; t < 4 && placed.some(q => Math.abs(q[0] - x) < 30 && Math.abs(q[1] - y) < 15); t++) y += 15;
    placed.push([x, y]); return `<text class="mph" x="${x.toFixed(1)}" y="${y.toFixed(1)}" text-anchor="middle">${f1(s.latest_mph)}</text>`; }).join('');
  const bins = ['Under 6 mph', '6 to 7', '7 to 8', '8 and over'];
  return `<div class="mapbox"><svg class="map" viewBox="0 0 ${W} ${H.toFixed(0)}" role="img" aria-label="Schematic map of ${esc(c.name)} segments colored by latest speed">${lines}${dots}${labs}</svg>
  <ul class="legend" aria-label="Map key, slowest first">${bins.map((t, i) => `<li><span class="bin" style="background:var(--s${i + 1})"></span>${t}</li>`).join('')}<li><span class="bin none"></span>no speed</li></ul></div>
  <p class="note"><strong>Lines are schematic.</strong> Each is a straight line between two timepoint stops, not the street shape. Only segments used for the corridor figures are drawn. The segment table gives the exact numbers.</p>`;
}

// ---------- home ----------
// one place decides how a corridor is described, so the table, filter and corridor page agree
const hasNums = c => isN(c.baseline_mph);
const stateOf = c => hasNums(c) ? (c.status === 'partial' ? 'Partly mapped' : 'Tracked') : c.status !== 'unmapped' ? 'Mapped, no recent data' : 'Not yet mapped';
const tcode = c => hasNums(c) ? 't' : c.status !== 'unmapped' ? 'm' : 'n';
const GLYPH = { 'Tracked': '●', 'Partly mapped': '◐', 'Mapped, no recent data': '◌', 'Not yet mapped': '○' };
const statusTag = (c, cls = '') => { const t = stateOf(c); return `<span class="tag ${tcode(c) === 'n' ? 'no' : ''} ${cls}"><span aria-hidden="true">${GLYPH[t]}</span> ${esc(t)}</span>`; };
const firstSentence = t => { t = (t || '').replace(/^Not mapped\.\s*/, ''); const m = t.match(/^.*?[.!?](\s|$)/); return (m ? m[0] : t || 'No reason given.').trim(); };

async function home() {
  const { data: d, sample, err } = await load('data/corridors.json', 'data/corridors.sample.json');
  if (err) { app.innerHTML = hero('<h1 class="display">Next Stop Tracker</h1>') + errBox(err); return; }
  const s = d.summary || {}, cs = d.corridors || [], pm = s.post_plan_months || [];
  let dash = {}; try { const r = await fetch('data/dashboard.json'); if (r.ok) dash = await r.json(); } catch (e) {}
  let sd = null; try { const r = await fetch('data/stop_delay.json'); if (r.ok) sd = await r.json(); } catch (e) {}
  const T = sd?.summary?.tracked, TS = T?.since_release || {}, CS = sd?.summary?.citywide?.since_release || {}, hasSD = !!(T && isN(T.baseline_min));
  const thr = sd && isN(sd.threshold_min) ? sd.threshold_min.toFixed(1) : '2.0';
  const same = isN(TS.change_min) && isN(CS.change_min) && Math.abs(TS.change_min - CS.change_min) < 0.1;
  const sm = TS.months || [], smSpan = sm.length ? (sm.length > 1 ? mlabel(sm[0]) + ' to ' + mlabel(sm[sm.length - 1]) : mlabel(sm[0])) : '';
  const nPartial = cs.filter(c => stateOf(c) === 'Partly mapped').length;
  const span = pm.length ? (pm.length > 1 ? mlabel(pm[0]) + ' to ' + mlabel(pm[pm.length - 1]) : mlabel(pm[0])) : '';
  const nameOf = id => (cs.find(c => c.id === id) || {}).name || id;
  const shared = (s.shared_segment_pairs || []).map(p => `${esc(nameOf(p[0]))} and ${esc(nameOf(p[1]))}`).join('; ');
  const tgt = d.target_pct ?? 20;
  const order = ['BX', 'BK', 'MN', 'QN', 'SI'], present = [...new Set(cs.map(c => c.borough))];
  const boros = order.filter(b => present.includes(b)).concat(present.filter(b => !order.includes(b)));
  app.innerHTML = `${sample ? sampleBanner() : ''}
  ${hero(`<h1 class="display">Are NYC's buses getting faster?</h1>
  <p class="lead">A baseline tracker for the Next Stop plan, from public bus speed data. An independent project by Kush Zingade, not affiliated with NYC DOT or the MTA.</p>
  <div class="stats s5">
   ${stat(`${esc(s.corridors_tracked ?? 'n/a')} <span class="unit">of ${esc(s.corridors_total ?? 50)}</span>`, '', `corridors with numbers so far (${esc(nPartial)} of them only partly mapped)`)}
   ${stat(f2(s.tracked_baseline_mph), 'mph', 'baseline: average weekday bus speed on these corridors')}
   ${stat(f2(s.tracked_post_plan_mph), 'mph', `since plan release (${esc(span) || 'no months yet'}), against ${f2(s.tracked_same_months_prior_year_mph)} mph in the same months a year earlier`)}
   ${stat(arrow(s.tracked_post_plan_change_pct) + pct(s.tracked_post_plan_change_pct), '', 'change since release, same months a year earlier', 'amber')}
   ${stat('+' + esc(tgt) + '%', '', 'target: over the baseline')}
  </div>`)}
  <div class="notice"><div class="wrap"><strong>Flat speeds are expected for now.</strong> Most street projects are not built yet, so flat speeds now are expected and are not a verdict on the plan.</div></div>
  <div class="wrap">
  <div class="prose2">
   <section><h2>What the plan promised</h2>
   <p>In July 2026 NYC DOT and the MTA released <em>Next Stop: Fast Buses, Better Service</em>. It promises buses 20% faster on 50 Priority Corridors, saving riders up to six minutes on a trip, and a public performance dashboard. ${dash.last_checked ? (dash.found ? `On ${esc(dash.last_checked)} we found a dashboard (${esc(dash.where)}).` : `When we last checked, on ${esc(dash.last_checked)}, we could not find it.`) : 'We have not checked whether it exists.'} The plan gives no date for the dashboard or for the 20% goal. The MTA publishes general bus metrics at <a href="https://metrics.mta.info/">metrics.mta.info</a>, which are not tied to these corridors.</p></section>
   <section><h2>What this tracker is and is not</h2>
   <p>This tracker measures average weekday bus speed (mph) on each corridor from public data, against a baseline of the 12 months before the plan (${esc(mlabel(d.baseline?.from))} to ${esc(mlabel(d.baseline?.to))}). The plan does not set a baseline, so that period is our choice. ${hasSD ? "The plan's second goal, cutting rider delay at bus stops to under two minutes beyond the scheduled wait, is covered below with a rougher measure." : "The plan's second goal, cutting rider delay at bus stops to under two minutes beyond the scheduled wait, is not measured here."} Most street projects are not built yet, so flat speeds now are expected and are not a verdict on the plan. This is not an official dashboard and it cannot say why speeds change. <a href="methods.html">Read the methods</a>.</p></section>
  </div>
  ${hasSD ? `<section class="tblsec"><h2>The second goal: extra wait at stops</h2>
  <p class="sub">The plan aims for under ${esc(thr)} minutes of wait beyond the schedule on Priority Corridors. The MTA publishes this for whole routes only, so these figures cover the ${esc(T.routes_with_data_since_release ?? (T.routes || []).length)} routes that run on tracked corridors, over their full length.</p>
  <dl class="kv"><dt>Baseline</dt><dd>${f2(T.baseline_min)} minutes (${esc(mlabel(sd.baseline?.from))} to ${esc(mlabel(sd.baseline?.to))})</dd>
  <dt>Since plan release</dt><dd>${isN(TS.min) ? `${f2(TS.min)} minutes, versus ${f2(TS.same_months_prior_year_min)} in the same months a year earlier (${sg(TS.change_min, 2)} minutes)` : 'no months since release yet'}</dd>
  ${isN(CS.change_min) ? `<dt>All city bus routes</dt><dd>${f2(CS.min)} minutes, versus ${f2(CS.same_months_prior_year_min)} a year earlier (${sg(CS.change_min, 2)} minutes).${same ? ' The change on corridor routes is about the same as the change citywide, so it is not evidence of a corridor effect.' : ''}</dd>` : ''}
  <dt>Corridors under ${esc(thr)} minutes</dt><dd>${esc(sd.summary.corridors_under_threshold)} of ${esc(sd.summary.corridors_with_data)} with data in ${esc(smSpan)}, and ${esc(sd.summary.corridors_under_threshold_prior_year ?? 'n/a')} in the same months a year earlier. This is a short window, and several corridors sit close to the line. Each corridor page has its own figure.</dd></dl>
  <p class="note">The plan does not say how it will measure the two minutes. This is the MTA's average over all riders, used as a stand-in. <a href="methods.html#delay">How this is measured</a></p></section>` : ''}
  <p class="note">Data runs through ${esc(mlabel(d.data_through))}. The latest single month was ${f2(s.tracked_latest_mph)} mph. A single month is not compared with the 12 month baseline here, because speeds change with the season. Compare the same months of different years instead.${shared ? ` Some corridors use the same segments, so their numbers are not independent: ${shared}.` : ''}</p>
  <section class="tblsec"><h2>All 50 corridors</h2>
  <p class="sub" id="count" role="status"></p><p class="sub" id="sortnote" aria-live="polite"></p>
  <div class="filters" role="group" aria-label="Filter by borough"><button type="button" class="chip" data-b="" aria-pressed="true">All</button>${boros.map(b => `<button type="button" class="chip" data-b="${esc(b)}" aria-pressed="false">${esc(bname(b))}</button>`).join('')}</div>
  <div class="filters2" role="search">
   <label>Search name<input id="q" type="search"></label>
   <label>Status<select id="fs"><option value="">All</option>${[['t', 'Has numbers'], ['m', 'Mapped, no recent data'], ['n', 'Not yet mapped']].filter(o => cs.some(c => tcode(c) === o[0])).map(o => `<option value="${o[0]}">${o[1]}</option>`).join('')}</select></label>
  </div>
  <p class="cap">Speeds are average weekday bus speed in mph. "Partly mapped" corridors show numbers for the stretch we could match, not the whole corridor. Corridors measured on fewer than 3 segments are marked "Small sample" and are not colored or ranked by change. Click a column heading to sort.</p>
  <div class="tw"><table id="tbl" class="dt home cut"><thead><tr><th data-alpha>Corridor</th><th class="b" data-alpha>Borough</th><th class="num bl">Baseline mph</th><th class="num lat">Latest mph</th><th class="num chg">Since release vs same months last year</th><th class="num c5">Latest month vs same month last year</th><th class="num c5">Latest month vs baseline (not seasonally adjusted)</th><th class="tr" data-nosort>Trend</th><th class="st" data-alpha>Status</th></tr></thead><tbody></tbody></table></div>
  <button type="button" class="btn wide more" id="more" hidden></button>
  <ul class="legend key"><li><strong class="up">▲</strong> faster than the same months a year earlier</li><li><strong class="down">▼</strong> slower</li><li>Dashed line in each small chart is that corridor's baseline</li><li>● Tracked, ◐ Partly mapped (numbers cover only the stretch we could match), ○ Not yet mapped</li></ul>
  </section></div>`;
  const tb = $('#tbl tbody');
  const rowsHtml = c => {
    const t = hasNums(c), L = c.latest || {}, P = c.post_plan || {}, tag = stateOf(c), sm = t && isN(c.n_basis_segments) && c.n_basis_segments < 3;
    const cell = (v, txt, cls = '', extra = '') => t ? `<td class="num ${cls} ${extra}" data-v="${isN(v) ? v : ''}">${txt}</td>` : `<td class="num na ${cls} ${extra}" data-v=""></td>`;
    const pc = v => sm ? cell(null, pct(v), 'chg') : cell(v, arrow(v) + pct(v), 'chg ' + pctCls(v)); // small samples: no color, arrow or rank
    const partial = tag === 'Partly mapped' ? ' title="Numbers cover only the stretch we could match"' : '';
    return `<tr${t ? '' : ' class="un"'} data-b="${esc(c.borough)}" data-t="${tcode(c)}" data-name="${esc((c.name || '').toLowerCase())}">
     <td class="nm" data-v="${esc(c.name)}"><a href="corridor.html?id=${encodeURIComponent(c.id)}">${esc(c.name)}</a>${c.rapid_bus_corridor ? ' <span class="tag rapid">Rapid bus</span>' : ''}${sm ? ' <span class="tag no">Small sample</span>' : ''}${t ? '' : `<span class="why">No speed yet. ${esc(firstSentence(c.public_note))}</span>`}</td>
     <td class="b" data-v="${esc(bname(c.borough))}"><span class="bb${t ? '' : ' hollow'}" aria-hidden="true">${esc(bcode(c.borough))}</span><span class="bn">${esc(bname(c.borough))}</span></td>${cell(c.baseline_mph, f2(c.baseline_mph), 'bl')}${cell(L.mph, f2(L.mph), 'lat')}
     ${pc(P.change_pct)}
     ${sm ? cell(null, pct(L.yoy_pct), '', 'c5') : cell(L.yoy_pct, arrow(L.yoy_pct) + pct(L.yoy_pct), pctCls(L.yoy_pct), 'c5')}
     ${cell(L.vs_baseline_pct, pct(L.vs_baseline_pct), '', 'c5')}
     <td class="tr">${t ? sparkline(c) : ''}</td><td class="st" data-v="${tag}"${partial}>${statusTag(c)}</td></tr>`;
  };
  tb.innerHTML = cs.map(rowsHtml).join('');
  const CUT = 10, more = $('#more');
  const tidy = () => { // phones show the first rows only, until "Show all"
    let i = 0; [...tb.rows].forEach(r => { r.classList.toggle('over', !r.hidden && ++i > CUT); });
    const n = [...tb.rows].filter(r => !r.hidden).length, cut = $('#tbl').classList.contains('cut');
    more.hidden = !(cut && n > CUT); more.textContent = `Show all ${n} corridors`;
  };
  const ths = sortable($('#tbl'), (th, dir) => {
    const lab = th.textContent.toLowerCase().replace(/^corridor$/, 'corridor name');
    $('#sortnote').textContent = 'Sorted by ' + lab + (th.hasAttribute('data-alpha') ? (dir === 'ascending' ? ', A to Z' : ', Z to A') : (dir === 'ascending' ? ', lowest first' : ', highest first')) + '. Corridors not yet mapped are always last.';
    tidy();
  });
  more.addEventListener('click', () => { $('#tbl').classList.remove('cut'); tidy(); });
  let boro = '';
  const filt = () => {
    const q = $('#q').value.trim().toLowerCase(), st = $('#fs').value; let n = 0;
    [...tb.rows].forEach(r => { const show = (!q || r.dataset.name.includes(q)) && (!boro || r.dataset.b === boro) && (!st || r.dataset.t === st); r.hidden = !show; if (show) n++; });
    $('#count').textContent = `Showing ${n} of ${cs.length} corridors${boro ? ' in ' + bname(boro) : ''}.`;
    tidy();
  };
  document.querySelectorAll('.chip').forEach(b => b.addEventListener('click', () => { boro = b.dataset.b; document.querySelectorAll('.chip').forEach(x => x.setAttribute('aria-pressed', x === b)); filt(); }));
  ['q', 'fs'].forEach(i => $('#' + i).addEventListener('input', filt));
  filt();
  ths[4]._run('ascending'); // default: since release vs same months last year, lowest first
  a11yScroll();
}

// ---------- corridor ----------
async function corridor() {
  const { data: d, sample, err } = await load('data/corridors.json', 'data/corridors.sample.json');
  if (err) { app.innerHTML = errBox(err); return; }
  const id = new URLSearchParams(location.search).get('id');
  let sd = null; try { const r = await fetch('data/stop_delay.json'); if (r.ok) sd = await r.json(); } catch (e) {}
  const c = (d.corridors || []).find(x => String(x.id) === id);
  if (!c) { app.innerHTML = hero('<a class="back" href="index.html">← All corridors</a><h1 class="display inner">Corridor not found</h1>', 'inner'); return; }
  document.title = c.name + ' | Next Stop Tracker';
  const L = c.latest || {}, P = c.post_plan, tracked = hasNums(c), tag = stateOf(c);
  const nUsed = c.n_basis_segments, small = isN(nUsed) && nUsed < 3;
  const tgt = d.target_pct ?? 20;
  const tags = `${c.rapid_bus_corridor ? '<span class="tag rapid">Rapid Bus corridor</span>' : ''}${statusTag(c, 'ondark')}${small ? `<span class="tag no ondark">Small sample: ${esc(nUsed)} segment${nUsed === 1 ? '' : 's'}</span>` : ''}`;
  const head = stats => hero(`<a class="back" href="index.html">← All corridors</a>
    <div class="titlerow"><h1 class="display inner">${esc(c.name)}</h1><div class="tags">${tags}</div></div>
    <p class="meta">${esc(bname(c.borough))}</p>${stats || ''}`, 'inner');
  const callout = `<aside class="callout"><div class="chd">Our definition, not the city's</div><div class="cbd"><h2>What we measured</h2>
    ${c.public_note ? `<p>${esc(c.public_note)}</p>` : ''}
    ${(c.routes || []).length ? `<div class="clab">Bus routes on it</div><div class="chips">${c.routes.map(r => `<span class="route">${esc(r)}</span>`).join('')}</div>` : ''}
    <div class="clab">Status</div><p class="stl">${statusTag(c)}</p>
    <a class="clink" href="methods.html#report">Report a wrong definition</a></div></aside>`;
  const known = [];
  if (tracked && tag === 'Partly mapped') known.push('Partly mapped: the numbers below cover only the stretch we could match, not the whole corridor.');
  if (small) known.push('With so few segments, month to month swings can be larger than the change shown. Treat the change with caution.');
  const warn = known.length ? banner(`<strong>Known limit.</strong> ${known.map(esc).join(' ')}`) : '';
  if (!tracked) {
    app.innerHTML = (sample ? sampleBanner() : '') + head('') + `<div class="wrap"><div class="row1 single"><div class="col">${c.status === 'unmapped'
      ? '<p>We have not matched this corridor to bus timepoint segments yet, so there are no speed numbers.</p>'
      : '<p>We matched this corridor to bus segments, but the source has no weekday data for them in the comparison period, so there are no speed numbers yet.</p>'}
      <p>Wrong corridor definition? See <a href="methods.html#report">how to report it</a>.</p></div>${callout}</div></div>`;
    return;
  }
  const basisTxt = c.basis === 'consistent' ? 'segments that report in every baseline month' : 'all segments with data; the set changes over time, so treat changes with caution';
  const sh = (c.shares_segments_with || []).map(i => (d.corridors.find(x => x.id === i) || {}).name || i);
  const havePP = P && isN(P.mph) && isN(P.change_pct);
  const stats = `<div class="stats s4">
   ${stat(f2(c.baseline_mph), 'mph', `baseline, ${esc(mlabel(d.baseline?.from))} to ${esc(mlabel(d.baseline?.to))}`)}
   ${stat(f2(L.mph), 'mph', `latest, ${esc(mlabel(L.month))}`, 'amber')}
   ${stat(havePP ? (small ? pct(P.change_pct) : arrow(P.change_pct) + pct(P.change_pct)) : 'n/a', '', havePP ? 'since release vs same months a year earlier' : 'no months since release yet')}
   ${stat(f2(c.target_mph), 'mph', `target, baseline plus ${esc(tgt)}%`)}</div>`;
  const SD = sd && (sd.corridors || []).find(x => String(x.id) === id), SR = SD && SD.since_release || {}, CW = sd && sd.summary?.citywide?.since_release || {};
  const thr = sd && isN(sd.threshold_min) ? sd.threshold_min.toFixed(1) : '2.0';
  const delay = SD && isN(SD.baseline_min) ? `<h2 class="gap" id="delay">Extra wait at stops</h2>
  <p class="sub">The plan's second goal is under ${esc(thr)} minutes of wait beyond the schedule. The MTA publishes this for whole routes only, so these figures cover the full length of the routes that run here, not just this corridor.</p>
  <dl class="kv"><dt>Routes counted</dt><dd>${esc((SD.routes_used || []).join(', ') || 'n/a')}</dd>
  <dt>Baseline</dt><dd>${f2(SD.baseline_min)} minutes (${esc(mlabel(sd.baseline?.from))} to ${esc(mlabel(sd.baseline?.to))})</dd>
  <dt>Since plan release</dt><dd>${isN(SR.min) ? `${f2(SR.min)} minutes over ${esc((SR.months || []).length)} month(s), versus ${f2(SR.same_months_prior_year_min)} in the same months a year earlier (${sg(SR.change_min, 2)} minutes)` : 'no months since release yet'}</dd>
  ${isN(CW.change_min) ? `<dt>Citywide, same months</dt><dd>${f2(CW.min)} minutes, versus ${f2(CW.same_months_prior_year_min)} a year earlier (${sg(CW.change_min, 2)} minutes). A change on this corridor that is about the same size as the citywide change is not specific to it.</dd>` : ''}
  <dt>Latest (${esc(mlabel(SD.latest?.month))})</dt><dd>${f2(SD.latest?.min)} minutes</dd>
  <dt>The plan's goal</dt><dd>Under ${esc(thr)} minutes. The plan does not say how it will measure this, so the MTA's average over all riders is a stand-in, not the plan's own yardstick. <a href="methods.html#delay">How this is measured</a></dd></dl>
  <details><summary>Extra wait by month as a table</summary><div class="tw"><table class="dt plain"><thead><tr><th>Month</th><th class="num">Extra wait (minutes)</th><th class="num">Riders</th></tr></thead><tbody>${(SD.series || []).map(s => `<tr><td>${esc(mlabel(s.month))}</td><td class="num">${f2(s.min)}</td><td class="num">${esc(isN(s.riders) ? s.riders.toLocaleString('en-US') : 'n/a')}</td></tr>`).join('')}</tbody></table></div></details>` : '';
  const first = c.series[0]?.month, lastM = c.series[c.series.length - 1]?.month;
  const segRows = [...c.segments].sort((a, b) => (isN(a.latest_mph) ? a.latest_mph : 1e9) - (isN(b.latest_mph) ? b.latest_mph : 1e9));
  app.innerHTML = (sample ? sampleBanner() : '') + head(stats) + warn + `<div class="wrap">
  <div class="row1"><div class="col">
  <h2>Average weekday speed by month</h2><p class="sub">${esc(mlabel(first))} to ${esc(mlabel(lastM))}, miles per hour</p>
  <div class="chart">${lineChart(c, d, 'd')}${lineChart(c, d, 'p')}</div>
  <ul class="legend lg2"><li><svg width="34" height="6" aria-hidden="true"><line x1="0" y1="3" x2="34" y2="3" stroke-width="3" style="stroke:var(--ink)"/></svg>Monthly speed, solid</li><li><svg width="34" height="6" aria-hidden="true"><line x1="0" y1="3" x2="34" y2="3" stroke-width="2" stroke-dasharray="4 4" style="stroke:var(--muted)"/></svg>Baseline, short dashes</li><li><svg width="40" height="6" aria-hidden="true"><line x1="0" y1="3" x2="40" y2="3" stroke-width="2.5" stroke-dasharray="16 7" style="stroke:var(--target)"/></svg>Target (+${esc(tgt)}%), long dashes</li><li><svg width="12" height="14" aria-hidden="true"><line x1="6" y1="0" x2="6" y2="14" stroke-width="2" style="stroke:var(--ink)"/></svg>Plan released (${esc(mlabel(d.plan_released))})</li></ul>
  <p class="note">The chart starts in ${esc(mlabel(c.series[0]?.month))}, the start of the baseline window. Earlier months are not used.</p>
  <details><summary>Chart data as a table</summary><div class="tw"><table class="dt plain"><thead><tr><th>Month</th><th class="num">Speed (mph)</th><th class="num">Trips</th></tr></thead><tbody>${c.series.map(s => `<tr><td>${esc(mlabel(s.month))}</td><td class="num">${f2(s.mph)}</td><td class="num">${esc(s.trips ?? 'n/a')}</td></tr>`).join('')}</tbody></table></div></details>
  <h2 class="gap">The numbers</h2>
  <dl class="kv"><dt>Routes</dt><dd>${esc((c.routes || []).join(', ') || 'n/a')}</dd>
  <dt>Segments used</dt><dd>${esc(nUsed ?? 'n/a')} of ${esc(c.n_segments ?? 'n/a')} listed: ${esc(basisTxt)}. <a href="methods.html#basis">Which segments count</a></dd>
  ${isN(c.n_latest_segments) && c.n_latest_segments < nUsed ? `<dt>Still reporting</dt><dd>${esc(c.n_latest_segments)} of ${esc(nUsed)} segments used for the baseline have data in ${esc(mlabel(L.month))}. The latest figure and the change versus baseline use only those, so the line on the chart can change mix at the plan release.</dd>` : ''}
  <dt>Segment miles measured</dt><dd>${f1(c.miles)} miles on the segments used, with every route and direction counted separately. This is not the corridor length.</dd>
  <dt>Since plan release</dt><dd>${P && isN(P.mph) ? `${f2(P.mph)} mph over ${esc(P.months)} month(s), versus ${f2(P.same_months_prior_year_mph)} mph in the same months a year earlier (${arrow(P.change_pct)}${pct(P.change_pct)})` : 'no months since release yet'}</dd>
  <dt>Baseline</dt><dd>${f2(c.baseline_mph)} mph (${esc(mlabel(d.baseline?.from))} to ${esc(mlabel(d.baseline?.to))})</dd>
  <dt>Target</dt><dd>${f2(c.target_mph)} mph (baseline plus ${esc(tgt)}%)</dd>
  <dt>Latest (${esc(mlabel(L.month))})</dt><dd>${f2(L.mph)} mph, ${arrow(L.yoy_pct)}${pct(L.yoy_pct)} vs same month last year. Versus the 12 month baseline: ${pct(L.vs_baseline_pct)} (not seasonally adjusted).</dd></dl>
  ${sh.length ? `<p class="note">This corridor uses some of the same segments as ${esc(sh.join(', '))}, so the two are not independent.</p>` : ''}
  <p class="note">Speeds are average weekday bus speed in mph. Flat speeds are expected while street projects are still being built.</p>
  ${delay}
  </div>${callout}</div>
  <div class="row2"><div class="col">
  <h2>Segments, slowest first</h2><p class="sub">Click a heading to sort. Speeds are average weekday bus speed in mph. Segments marked "No" are listed but not used for the corridor figures.</p>
  <div class="tw"><table id="seg" class="dt seg"><thead><tr><th>Segment</th><th class="num mi">Miles</th><th class="num">Baseline mph</th><th class="num">Latest mph</th><th>Used</th></tr></thead><tbody>
  ${segRows.map(s => `<tr${s.in_basis === false ? ' class="off"' : ''}><td data-v="${esc(s.route_id)} ${esc(s.direction)}"><span class="bin" style="background:${binCol(s.latest_mph)}"></span><span class="sn"><strong>${esc(s.route_id)} ${esc(s.direction)}</strong><span class="why">${esc(s.from_stop)} to ${esc(s.to_stop)}${s.in_basis === false && s.excluded_reason ? '. Not used: ' + esc(s.excluded_reason) : ''}</span></span></td><td class="num mi" data-v="${isN(s.miles) ? s.miles : ''}">${f2(s.miles)}</td><td class="num" data-v="${isN(s.baseline_mph) ? s.baseline_mph : ''}">${f1(s.baseline_mph)}</td><td class="num lat" data-v="${isN(s.latest_mph) ? s.latest_mph : ''}">${f1(s.latest_mph)}</td><td>${s.in_basis === false ? 'No' : 'Yes'}</td></tr>`).join('')}</tbody></table></div>
  </div><div class="col"><h2>Schematic map</h2><p class="sub">Latest speed on each segment, mph</p>${segMap(c)}</div></div></div>`;
  sortable($('#seg')); a11yScroll();
}

// ---------- ace ----------
// the wider of the two 95% intervals, so the page never overstates certainty
const wide = S => [Math.min(S.mean_ci95_lo, S.mean_ci95_clustered_by_activation_date_lo), Math.max(S.mean_ci95_hi, S.mean_ci95_clustered_by_activation_date_hi)];
async function ace() {
  const { data: a, sample, err } = await load('data/ace.json', 'data/ace.sample.json');
  const top = `<h1 class="display inner">Camera enforcement: before and after</h1><p class="lead">Do buses speed up after bus-lane cameras start? This compares each camera route with similar routes without cameras. It is an independent analysis by Kush Zingade, not affiliated with NYC DOT or the MTA.</p>`;
  const about = `<div class="prose2"><section><p>The MTA runs two camera programs: ABLE (Automated Bus Lane Enforcement) and ACE (Automated Camera Enforcement). They ticket vehicles blocking bus lanes, and ACE also covers double-parked vehicles and vehicles blocking bus stops. The Program column shows which one started first on each route.</p></section>
  <section><p>The plan reports that bus speeds on ACE routes have increased by 5% on average, with some corridors up to 30%. This page measures something different: whole route speed, local and limited routes only (Select Bus Service routes are left out), relative to routes without cameras. The two figures are not directly comparable.</p></section></div>`;
  if (err) { app.innerHTML = hero(top, 'inner') + `<div class="wrap">${about}</div>` + errBox('Camera enforcement results are not available yet. ' + err); return; }
  const SM = a.summary || {}, S = SM.all_routes || {}, PL = SM.placebo_fake_activation_12_months_early || {}, Q = SM.excluding_queens_redesign_overlap || {}, rs = a.routes || [];
  const ci = isN(S.mean_ci95_lo) ? wide(S) : [NaN, NaN], pci = isN(PL.mean_ci95_lo) ? wide(PL) : [NaN, NaN];
  const incl0 = isN(ci[0]) && ci[0] <= 0 && ci[1] >= 0;
  // The three limits a reader most needs sit beside the number; the rest stay one click away.
  const cvAll = a.caveats || [];
  const cvKey = c => /observational/i.test(c) || /whole route/i.test(c) || /fake dates/i.test(c);
  const cvTop = cvAll.filter(cvKey).length === 3 ? cvAll.filter(cvKey) : cvAll.slice(0, 3);
  const cvRest = cvAll.filter(c => !cvTop.includes(c));
  const cav = cvTop.map(c => `<li>${esc(c)}</li>`).join('') || '<li>No caveats supplied.</li>';
  const cavMore = cvRest.length ? `<details class="cvmore"><summary>Show ${cvRest.length} more limits</summary><ol start="${cvTop.length + 1}">${cvRest.map(c => `<li>${esc(c)}</li>`).join('')}</ol></details>` : '';
  const nEx = (a.excluded || []).length;
  const heroHtml = hero(`${top}<div class="acehero">
   <div class="bignum"><div class="lab">Mean difference versus routes without cameras</div><div class="huge">${sg(S.mean_did_pct, 2)}</div><div class="pp">percentage points</div>
    <p class="range">95% range: ${sg(ci[0], 2)} to ${sg(ci[1], 2)} (the wider of two methods).${incl0 ? ' The range includes zero.' : ''}</p>${interval(S.mean_did_pct, ci)}</div>
   <aside class="caveats" aria-labelledby="cv"><div class="chd" id="cv">Read this with the number</div><ol>${cav}</ol>${cavMore}</aside>
   <div class="stats s2 acestats">
    ${stat(esc(S.n_routes ?? rs.length), '', 'routes with enough data')}
    ${stat(sg(S.median_did_pct, 2), 'pts', 'median difference vs routes without cameras, in percentage points')}
    ${stat(isN(S.share_improved_vs_control) ? Math.round(S.share_improved_vs_control * 100) + '%' : 'n/a', '', `of routes did better than routes without cameras${isN(PL.share_improved_vs_control) ? `. With fake start dates a year early, ${Math.round(PL.share_improved_vs_control * 100)}% did` : ''}`)}
    ${nEx ? stat(esc(nEx), '', 'routes left out; the list is below the table') : ''}
   </div></div>`, 'inner');
  const plain = `<p class="note">Plain reading: if the interval includes zero, these data cannot tell a camera effect from noise.${isN(PL.mean_did_pct) ? ` A check with fake start dates a year early, when no camera was present, gave an average of ${sg(PL.mean_did_pct, 2)} points (interval ${sg(pci[0], 2)} to ${sg(pci[1], 2)}). ${isN(S.mean_did_pct) && Math.abs(PL.mean_did_pct) >= Math.abs(S.mean_did_pct) ? ' That is larger than the real result, so the result is within the noise of the method.' : ' That is smaller than the real result.'}` : ''}${isN(Q.mean_did_pct) ? ` Leaving out the ${esc(SM.queens_redesign_overlap_routes)} Queens routes whose months overlap the mid 2025 Queens bus redesign, the mean is ${sg(Q.mean_did_pct, 2)} points.` : ''} ${isN((SM.excluding_controls_sharing_a_corridor || {}).mean_did_pct) ? ` Leaving out comparison routes that share a corridor with a camera route, the mean is ${sg(SM.excluding_controls_sharing_a_corridor.mean_did_pct, 2)} points.` : ''} Differences are in percentage points of speed change relative to routes without cameras.</p>`;
  const tr = rs.map(r => { const flags = [r.pandemic_overlap ? 'Pandemic overlap' : '', r.redesign_overlap ? 'Queens redesign overlap' : ''].filter(Boolean).join('. ');
    return `<tr><td data-v="${esc(r.route)}"><strong>${esc(r.route)}</strong><span class="why mo">${esc(r.program)}, from ${esc(r.activated)}, ${esc(r.months_after ?? 'n/a')} months after${flags ? '. ' + esc(flags) : ''}</span></td><td class="ho">${esc(r.program)}</td><td class="ho">${esc(r.activated)}</td><td class="num ho" data-v="${isN(r.before_mph) ? r.before_mph : ''}">${f2(r.before_mph)}</td><td class="num ho" data-v="${isN(r.after_mph) ? r.after_mph : ''}">${f2(r.after_mph)}</td><td class="num" data-v="${isN(r.change_pct) ? r.change_pct : ''}" data-l="Route">${pct(r.change_pct)}</td><td class="num" data-v="${isN(r.control_change_pct) ? r.control_change_pct : ''}" data-l="Control">${pct(r.control_change_pct)}</td><td class="num dif ${pctCls(r.did_pct)}" data-v="${isN(r.did_pct) ? r.did_pct : ''}">${arrow(r.did_pct)}${sg(r.did_pct, 2)}</td><td class="num ho">${esc(r.months_after ?? 'n/a')}</td><td class="ho">${r.pandemic_overlap ? 'Yes' : 'No'}</td><td class="ho">${r.redesign_overlap ? 'Yes' : 'No'}</td></tr>`; }).join('');
  app.innerHTML = (sample ? sampleBanner() : '') + heroHtml + `<div class="wrap">${about}${plain}
  <section class="tblsec"><h2>Difference versus routes without cameras, by route</h2>${aceChart(rs)}</section>
  <section class="tblsec"><h2>Routes in the study</h2><p class="cap">Speeds are average weekday bus speed in mph. "Control" means similar routes without cameras. Click a heading to sort.</p><div class="tw"><table id="ace" class="dt ace cut"><thead><tr><th>Route</th><th class="ho">Program</th><th class="ho">Activated</th><th class="num ho">Before mph</th><th class="num ho">After mph</th><th class="num">Change</th><th class="num">Control change</th><th class="num">Difference (pts)</th><th class="num ho">Months after</th><th class="ho">Pandemic overlap</th><th class="ho">Queens redesign overlap</th></tr></thead><tbody>${tr}</tbody></table></div>
  <button type="button" class="btn wide more" id="more"></button></section>
  ${nEx ? `<details><summary>${nEx} routes excluded</summary><ul class="plainlist">${a.excluded.map(e => `<li><strong>${esc(e.route)}</strong>: ${esc(e.reason)}</li>`).join('')}</ul></details>` : ''}</div>`;
  const tb = $('#ace tbody'), CUT = 10, more = $('#more');
  function tidy() { [...tb.rows].forEach((r, i) => r.classList.toggle('over', i >= CUT)); const cut = $('#ace').classList.contains('cut'); more.hidden = !(cut && tb.rows.length > CUT); more.textContent = `Show all ${tb.rows.length} routes`; }
  sortable($('#ace'), tidy); a11yScroll();
  more.addEventListener('click', () => { $('#ace').classList.remove('cut'); tidy(); });
  tidy();
}

// interval graphic in the hero: zero line, 95% range bar, estimate dot
function interval(mean, ci) {
  if (!isN(mean) || !isN(ci[0])) return '';
  const ext = Math.max(1, Math.ceil(Math.max(Math.abs(ci[0]), Math.abs(ci[1]), Math.abs(mean)))), X = v => 10 + (v + ext) / (2 * ext) * 460;
  return `<svg class="ival" viewBox="0 0 480 60" role="img" aria-label="95% range from ${sg(ci[0], 2)} to ${sg(ci[1], 2)} percentage points, estimate ${sg(mean, 2)}, on an axis from ${sg(-ext, 1)} to ${sg(ext, 1)}">
   <line x1="10" x2="470" y1="16" y2="16" stroke="var(--panel-rule)" stroke-width="2"/><line x1="${X(0)}" x2="${X(0)}" y1="0" y2="32" stroke="#fff" stroke-width="2"/>
   <rect x="${X(ci[0]).toFixed(1)}" y="11" width="${(X(ci[1]) - X(ci[0])).toFixed(1)}" height="10" rx="2" fill="#fff"/><circle cx="${X(mean).toFixed(1)}" cy="16" r="10" fill="var(--amber)" stroke="var(--panel)" stroke-width="3"/>
   <g font-size="13" fill="var(--panel-muted)"><text x="10" y="52">${sg(-ext, 1)}</text><text x="${X(0)}" y="52" text-anchor="middle">0</text><text x="470" y="52" text-anchor="end">${sg(ext, 1)}</text></g></svg>`;
}

// zero-centered dot chart: filled circle = faster than comparison routes, hollow square = slower
function aceChart(rs) {
  const r = rs.filter(x => isN(x.did_pct)).sort((a, b) => a.did_pct - b.did_pct);
  if (!r.length) return '<p>No route results.</p>';
  const ext = Math.max(1, Math.ceil(Math.max(...r.map(x => Math.abs(x.did_pct))))), tstep = Math.max(1, Math.ceil(ext / 3));
  const mk = P => {
    const W = P ? 358 : 1160, H = P ? 260 : 320, L = P ? 34 : 44, Rm = P ? 8 : 12, T = 16, B = 16, rad = P ? 3.5 : 6;
    const Y = v => T + (1 - (v + ext) / (2 * ext)) * (H - T - B), X = i => L + (i + 0.5) / r.length * (W - L - Rm), z = Y(0);
    const ticks = []; for (let t = -Math.floor(ext / tstep) * tstep; t <= ext; t += tstep) ticks.push(t);
    let g = ticks.filter(t => t).map(t => `<line x1="${L}" x2="${W - Rm}" y1="${Y(t).toFixed(1)}" y2="${Y(t).toFixed(1)}" stroke-width="1" style="stroke:var(--rule)"/>`).join('');
    g += ticks.map(t => `<text x="${L - 8}" y="${(Y(t) + 4).toFixed(1)}" font-size="${P ? 12 : 13}" text-anchor="end" style="fill:var(--muted)">${t ? sg(t, 0) : '0'}</text>`).join('');
    g += `<line x1="${L}" x2="${W - Rm}" y1="${z.toFixed(1)}" y2="${z.toFixed(1)}" stroke-width="3" style="stroke:var(--ink)"/>`;
    r.forEach((x, i) => { const up = x.did_pct >= 0, cx = X(i).toFixed(1), cy = Y(x.did_pct).toFixed(1);
      g += `<line x1="${cx}" x2="${cx}" y1="${z.toFixed(1)}" y2="${cy}" stroke-width="${P ? 1 : 2}" style="stroke:var(--muted)"/>` + (up ? `<circle cx="${cx}" cy="${cy}" r="${rad}" style="fill:var(--faster)">` : `<rect x="${(X(i) - rad).toFixed(1)}" y="${(Y(x.did_pct) - rad).toFixed(1)}" width="${rad * 2}" height="${rad * 2}" stroke-width="${P ? 1.5 : 2.5}" style="fill:var(--bg);stroke:var(--slower)">`) + `<title>${esc(x.route)}: ${sg(x.did_pct, 2)} points vs routes without cameras</title>` + (up ? '</circle>' : '</rect>'); });
    const f = r[0], l = r[r.length - 1], fs = P ? 11 : 13;
    g += `<text x="${(X(0) + 10).toFixed(1)}" y="${(Y(f.did_pct) + 4).toFixed(1)}" font-size="${fs}" font-weight="700" style="fill:var(--ink)">${esc(f.route)}</text><text x="${(X(r.length - 1) - 10).toFixed(1)}" y="${(Y(l.did_pct) + 4).toFixed(1)}" font-size="${fs}" font-weight="700" text-anchor="end" style="fill:var(--ink)">${esc(l.route)}</text>`;
    return `<svg class="cv-${P ? 'p' : 'd'}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Dot chart of each route's speed change minus control change, in percentage points, sorted from most slowed to most sped up. Values are listed in the table below.">${g}</svg>`;
  };
  return `<p class="sub">${r.length} routes, sorted from most slowed to most sped up. Percentage points.</p><div class="chart">${mk(false)}${mk(true)}</div>
  <ul class="legend lg2"><li><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="6" style="fill:var(--faster)"/></svg>Filled circle: better than comparison routes (above zero, positive number)</li><li><svg width="14" height="14" aria-hidden="true"><rect x="1.5" y="1.5" width="11" height="11" stroke-width="2.5" style="fill:var(--bg);stroke:var(--slower)"/></svg>Hollow square: worse (below zero, negative number)</li><li>Thick line is zero, same as comparison routes</li></ul>`;
}

// ---------- commitments ----------
async function commitments() {
  const { data: d, err } = await load('data/commitments.json', '');
  const top = `<h1 class="display inner">What the plan committed to</h1><p class="lead">Each numbered or dated commitment we found in the plan, quoted exactly, with what open data can and cannot show about it today. An independent project by Kush Zingade, not affiliated with NYC DOT or the MTA.</p>`;
  if (err) { app.innerHTML = hero(top, 'inner') + errBox(err); return; }
  const cs = d.commitments || [], n = s => cs.filter(c => c.status === s).length;
  const ST = { 'live count': ['Live count', ''], 'snapshot only': ['Snapshot only', ''], 'no public data': ['No public data', 'no'], 'milestone': ['Milestone', 'no'] };
  const tagOf = c => { const t = ST[c.status] || [c.status, 'no']; return `<span class="tag ${t[1]}">${esc(t[0])}</span>`; };
  const num = v => isN(v) ? v.toLocaleString('en-US') : esc(v ?? '');
  const shows = c => { const m = c.measured; if (!m) return `<span class="why">${esc(c.note || '')}</span>`;
    return `<strong>${num(m.value)}</strong> ${esc(m.unit)}<span class="why">${esc(m.method)} Source: <a href="${esc(m.dataset_url)}">${esc(m.dataset_name)}</a>, updated ${esc(m.dataset_updated)}${m.stale ? ', which is before the plan was released' : ''}.${c.note ? ' ' + esc(c.note) : ''}</span>`; };
  const secs = [...new Set(cs.map(c => c.section))];
  app.innerHTML = hero(top + `<div class="stats s4">
   ${stat(esc(cs.length), '', 'commitments found in the plan')}
   ${stat(esc(n('live count')), '', 'can be counted from open data today', 'amber')}
   ${stat(esc(n('snapshot only')), '', 'have a dataset, but one that cannot show change since the plan')}
   ${stat(esc(n('no public data') + n('milestone')), '', `have no public data (${esc(n('milestone'))} of them are yes or no milestones)`)}</div>`, 'inner') +
  `<div class="notice"><div class="wrap"><strong>This page does not grade the city.</strong> A status says what open data can show, not whether the work is being done. Most of these commitments have deadlines that are still ahead.</div></div>
  <div class="wrap">
  <div class="prose2"><section><h2>How to read the statuses</h2><p><strong>Live count</strong>: a public dataset has dates, so progress can be counted. <strong>Snapshot only</strong>: a public list exists but has no usable dates, so we save its size and watch it change. <strong>No public data</strong>: we found no public dataset. <strong>Milestone</strong>: a yes or no event that data cannot measure.</p></section>
  <section><h2>Where the wording comes from</h2><p>Each quote is copied from the text of <em>Next Stop: Fast Buses, Better Service</em> (July 2026), and the script that builds this page fails if a quote is not found word for word in that text. Some quotes are one clause of a longer sentence. <a href="methods.html#commitments">How this page is built</a>.</p></section></div>
  ${secs.map(s => `<section class="tblsec"><h2>${esc(s)}</h2>
  <div class="tw"><table class="dt cm"><thead><tr><th>Commitment, in the plan's words</th><th>By</th><th>What open data shows</th><th>Status</th></tr></thead><tbody>
  ${cs.filter(c => c.section === s).map(c => `<tr><td><span class="sn"><strong>${esc(c.label)}</strong><span class="why">"${esc(c.quote)}"</span></span></td><td class="st">${esc(c.deadline || 'No date')}</td><td>${shows(c)}</td><td class="st">${tagOf(c)}</td></tr>`).join('')}</tbody></table></div></section>`).join('')}
  <section class="tblsec"><h2>Data that would make these countable</h2><p class="sub">Each item is a dataset the city or the MTA could publish. With it, the matching commitments above could move to a live count.</p>
  <ul class="plainlist">${(d.data_requests || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul></section>
  <section class="tblsec"><h2>Limits</h2><ul class="plainlist">${(d.caveats || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>
  <p class="note">Last built ${esc(d.generated)}. <a href="data/commitments.json">Download the data</a>.</p></section></div>`;
  a11yScroll();
}

chrome();
({ home, corridor, ace, commitments }[document.body.dataset.page] || (() => {}))();
