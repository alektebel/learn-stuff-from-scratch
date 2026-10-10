"""
Render the skill tree as a self-contained interactive page.

    python3 skill-tree/render_html.py [out.html]

Reads tree.toml and books.toml and writes `skill-tree/tree.html` (override with a
path): a dependency map of the curriculum. Tracks are columns, dependency depth is
the vertical order (prerequisites first), each node is a station, and every
`requires` edge is drawn between stations. The page is one file, no network, no
dependencies beyond the system fonts.

The design: a quiet daylight dependency map. One typeface, one accent, hairlines instead
of chrome. Colour is identity (which track) and shape is progress: filled = built, ringed
= ready, hollow = todo, hatched = blocked on a resource. Only one thing is loud — the map.
Project nodes (tracks.py: `counts_for_xp=False`) are drawn but do not move the level.
Regenerate after any change to tree.toml.
"""

from __future__ import annotations

import html
import json
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from tracks import (  # noqa: E402
    DOMAIN_LABEL,
    TRACKS,
    badges,
    earned_xp,
    level_for,
    max_xp,
    node_xp,
)

TRACK_LABEL = {t: TRACKS[t].label for t in TRACKS}
COLORS = {t: TRACKS[t].color for t in TRACKS}


def load():
    nodes = tomllib.loads((HERE / "tree.toml").read_text())["node"]
    data = tomllib.loads((HERE / "books.toml").read_text())
    sources = {**data.get("book", {}), **data.get("doc", {})}
    return nodes, sources


def book_name(sources: dict, ref: str) -> str:
    key = ref.split(":", 1)[0]
    s = sources.get(key)
    return f"{s['title']} ({s['authors']}, {s['year']})" if s else ref


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def progress_markup(nodes: list[dict]) -> str:
    total = len(nodes)
    done = sum(1 for n in nodes if n["status"] == "done")
    segs = []
    for t in TRACKS:
        mem = [n for n in nodes if n["track"] == t]
        if not mem:
            continue
        d = sum(1 for n in mem if n["status"] == "done")
        segs.append(
            f'<span class="seg" style="--c:{COLORS[t]}" title="{esc(TRACK_LABEL[t])}: '
            f'{d}/{len(mem)} built"><span class="fill" style="width:{d/len(mem)*100:.1f}%"></span></span>'
        )
    return (
        '<div class="progress">'
        f'<span class="big">{done}<span class="slash">/</span>{total}</span>'
        f'<span class="pwrap"><span class="plabel mono">nodes graded · '
        f'{sum(1 for n in nodes if n["status"] in ("done", "exists"))} settled</span>'
        f'<span class="bar">{"".join(segs)}</span></span>'
        "</div>"
    )


def gamify_markup(nodes: list[dict]) -> str:
    xp, cap = earned_xp(nodes), max_xp(nodes)
    level, rank, nxt = level_for(xp)
    pct = (xp / cap * 100) if cap else 0.0
    bg = badges(nodes)

    def chip(label, ok, color):
        return f'<span class="{"chip on" if ok else "chip"}" style="--c:{color}">{esc(label)}</span>'

    domains = "".join(chip(DOMAIN_LABEL[d], ok, "#8893A8")
                      for d, ok in bg["domains"].items())
    tracks = "".join(chip(TRACKS[t].label, ok, TRACKS[t].color)
                     for t, ok in bg["tracks"].items())
    nxt_txt = f"next level at {nxt:,} XP" if nxt else "top rank reached"
    return (
        '<div class="gamify">'
        f'<div class="rankrow"><span class="lvl mono">Lv {level}</span>'
        f'<span class="rank">{esc(rank)}</span>'
        f'<span class="xps mono">{xp:,} / {cap:,} XP</span></div>'
        f'<div class="xpbar" title="{pct:.0f}% of the tree\'s XP">'
        f'<span style="width:{pct:.1f}%"></span></div>'
        f'<div class="nxtx">{nxt_txt}</div>'
        f'<div class="chips"><span class="chiplab mono">badges</span>{domains}{tracks}</div>'
        "</div>"
    )


def legend_markup() -> str:
    tracks = "".join(
        f'<li><span class="swatch" style="--c:{COLORS[t]}"></span>{esc(TRACK_LABEL[t])}</li>'
        for t in TRACKS
    )
    states = (
        '<li><span class="sdot s-done"></span>built</li>'
        '<li><span class="sdot s-ready"></span>ready</li>'
        '<li><span class="sdot s-todo"></span>todo</li>'
        '<li><span class="sdot s-blocked"></span>blocked</li>'
        '<li><span class="sdot s-exists"></span>exists</li>'
        '<li><span class="sdot s-cap"></span>capstone</li>'
    )
    return (
        f'<ul class="legend tracks">{tracks}</ul>'
        f'<ul class="legend states">{states}</ul>'
    )


def colheaders_markup(nodes: list[dict]) -> str:
    bg = badges(nodes)
    cells = []
    for t in TRACKS:
        mem = [n for n in nodes if n["track"] == t]
        if not mem:
            continue
        settled = sum(1 for n in mem if n["status"] in ("done", "exists"))
        star = (' <span class="tstar" title="track badge earned">★</span>'
                if bg["tracks"].get(t) else '')
        cells.append(
            f'<div class="colhead" style="--c:{COLORS[t]}">'
            f'<span class="swatch"></span><span class="cname">{esc(TRACK_LABEL[t])}{star}</span>'
            f'<span class="ctally mono" title="settled: built or already in the repo">'
            f'{settled}/{len(mem)}</span></div>'
        )
    return "".join(cells)


def build(nodes: list[dict], sources: dict) -> str:
    data = {
        "nodes": nodes,
        "books": sources,
        "tracks": list(TRACKS),
        "labels": TRACK_LABEL,
        "colors": COLORS,
        "domains": {t: TRACKS[t].domain for t in TRACKS},
        "domainLabels": DOMAIN_LABEL,
        "countsForXp": {t: TRACKS[t].counts_for_xp for t in TRACKS},
        "xp": {n["id"]: node_xp(n) for n in nodes},
        "bookName": {n: book_name(sources, n)
                     for n in sorted({s for x in nodes for s in x["sources"]})},
    }
    done = sum(1 for n in nodes if n["status"] == "done")
    payload = json.dumps(data).replace("</", "<\\/")

    doc = TEMPLATE
    doc = doc.replace("/*__DATA__*/", payload)
    doc = doc.replace("<!--__PROGRESS__-->", progress_markup(nodes))
    doc = doc.replace("<!--__GAMIFY__-->", gamify_markup(nodes))
    doc = doc.replace("<!--__LEGEND__-->", legend_markup())
    doc = doc.replace("<!--__COLHEADERS__-->", colheaders_markup(nodes))
    doc = doc.replace("__NCOLS__", str(len(TRACKS)))
    doc = doc.replace("__DONE__", str(done)).replace("__TOTAL__", str(len(nodes)))
    return doc


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Skill Tree — a dependency map of everything you build from scratch</title>
<style>
  :root{
    --paper:#FAFAF7; --panel:#FFFFFF; --ink:#16181D; --soft:#565A60; --dim:#9A9C9F;
    --line:#E4E3DD; --focus:#16181D; --flag:#B23A2E;
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
    --mono:"Hack","DejaVu Sans Mono","Liberation Mono",monospace;
    --colw:210px; --rowh:108px; --ncols:__NCOLS__;
  }
  *{box-sizing:border-box}
  html{-webkit-text-size-adjust:100%}
  body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
    font-size:16px;line-height:1.5;text-rendering:optimizeLegibility}
  .mono{font-family:var(--mono)}
  a{color:inherit}
  :focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:3px}

  /* ---- masthead: quiet, the map is the hero ---- */
  header.masthead{padding:clamp(22px,3.4vw,44px) clamp(18px,3.4vw,44px) 18px;
    border-bottom:1px solid var(--line)}
  .masthead .cols{display:flex;flex-wrap:wrap;gap:26px 48px;align-items:flex-end;
    justify-content:space-between}
  h1{font-family:var(--sans);font-weight:680;font-size:clamp(2.1rem,4.6vw,3.4rem);
    line-height:.98;letter-spacing:-.03em;margin:0}
  .lede{margin:.7rem 0 0;max-width:60ch;color:var(--soft);font-size:1.02rem}
  .lede b{color:var(--ink);font-weight:600}
  .stat{display:flex;flex-direction:column;gap:10px;min-width:min(360px,100%)}
  .progress{display:flex;align-items:center;gap:16px}
  .big{font-family:var(--mono);font-size:3.5rem;line-height:.9;letter-spacing:-.03em}
  .big .slash{color:var(--dim);font-size:2.2rem;vertical-align:.06em}
  .pwrap{display:flex;flex-direction:column;gap:5px;flex:1;min-width:150px}
  .plabel{color:var(--dim);font-size:.72rem;letter-spacing:.02em}
  .bar{display:flex;gap:3px;height:7px}
  .seg{flex:1;background:var(--line);border-radius:99px;overflow:hidden;position:relative}
  .seg .fill{display:block;height:100%;background:var(--c);border-radius:99px}

  /* ---- gamification: one quiet rank line, then badges ---- */
  .gamify{margin-top:12px;display:flex;flex-direction:column;gap:6px}
  .rankrow{display:flex;align-items:baseline;gap:9px}
  .lvl{font-size:.78rem;color:var(--ink);background:#00000008;border:1px solid var(--line);
    border-radius:5px;padding:1px 7px}
  .rank{font-weight:650;font-size:1.02rem}
  .xps{margin-left:auto;color:var(--soft);font-size:.78rem}
  .xpbar{height:5px;background:var(--line);border-radius:99px;overflow:hidden}
  .xpbar span{display:block;height:100%;background:var(--ink);border-radius:99px}
  .nxtx{color:var(--dim);font-size:.72rem}
  .chips{display:flex;flex-wrap:wrap;gap:5px;align-items:center}
  .chiplab{color:var(--dim);font-size:.66rem;letter-spacing:.03em}
  .chip{font-size:.72rem;color:var(--dim);border:1px solid var(--line);border-radius:99px;
    padding:2px 8px;display:inline-flex;align-items:center;gap:6px}
  .chip.on{color:var(--ink);border-color:var(--c);box-shadow:inset 0 0 0 1px var(--c)}
  .chip.on::before{content:"★";color:var(--c);font-size:.7rem}
  .tstar{color:var(--c);font-size:.82rem}
  .legend{list-style:none;display:flex;flex-wrap:wrap;gap:6px 16px;margin:0;padding:0;
    color:var(--soft);font-size:.86rem}
  .legend.states{margin-top:2px}
  .legend li{display:flex;align-items:center;gap:7px}
  .swatch{width:14px;height:4px;border-radius:99px;background:var(--c);display:inline-block}
  .sdot{width:11px;height:11px;border-radius:50%;display:inline-block;border:1.5px solid var(--dim)}
  .sdot.s-done{background:var(--ink);border-color:var(--ink)}
  .sdot.s-ready{border-color:var(--ink);box-shadow:inset 0 0 0 2.5px var(--paper),inset 0 0 0 5px var(--ink)}
  .sdot.s-todo{border-color:var(--dim)}
  .sdot.s-exists{border-style:dashed}
  .sdot.s-blocked{border-color:var(--flag);
    background:repeating-linear-gradient(45deg,transparent 0 2px,var(--flag) 2px 3px)}
  .sdot.s-cap{box-shadow:0 0 0 2px var(--paper),0 0 0 4px var(--dim)}

  /* ---- atlas ---- */
  .atlas{min-width:0;padding:0 clamp(8px,1.6vw,20px) 8px}
  .scroller{overflow:auto;max-height:calc(100vh - 40px)}
  .colheaders{position:sticky;top:0;z-index:5;display:grid;
    grid-template-columns:repeat(var(--ncols),var(--colw));background:
      linear-gradient(var(--paper) 78%,transparent)}
  .colhead{display:flex;align-items:center;gap:9px;padding:12px 12px 10px;font-size:.98rem}
  .colhead .swatch{width:16px;height:5px}
  .colhead .cname{font-weight:600}
  .colhead .ctally{margin-left:auto;color:var(--dim);font-size:.76rem}

  #map{position:relative;width:calc(var(--ncols) * var(--colw))}
  #edges{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
  .lane{position:absolute;top:0;bottom:0;width:var(--colw);border-left:1px solid var(--line);
    opacity:.5;pointer-events:none}
  .lane.alt{background:#00000003}

  .station{position:absolute;display:flex;gap:9px;align-items:flex-start;width:calc(var(--colw) - 26px);
    padding:9px 10px 9px 0;background:none;border:0;color:inherit;text-align:left;cursor:pointer;
    font-family:var(--sans);border-radius:6px;transition:opacity .18s ease,transform .18s ease}
  .station .dot{flex:0 0 auto;width:13px;height:13px;border-radius:50%;margin-top:3px;
    border:1.6px solid var(--dim);background:transparent;position:relative}
  .station .name{font-size:.92rem;line-height:1.22}
  .station .id{display:block;font-family:var(--mono);font-size:.63rem;color:var(--dim);
    margin-top:3px;letter-spacing:.01em}
  .station[data-status="done"] .dot{background:var(--c);border-color:var(--c)}
  .station[data-status="done"] .name{color:var(--ink)}
  .station[data-status="ready"] .dot{border-color:var(--c);
    box-shadow:inset 0 0 0 2px var(--paper),inset 0 0 0 3.5px var(--c)}
  .station[data-status="ready"] .name{color:var(--ink)}
  .station[data-status="todo"] .name{color:var(--soft)}
  .station[data-status="exists"] .dot{border-style:dashed}
  .station[data-status="exists"] .name{color:var(--dim);font-style:italic}
  .station[data-status="blocked"] .dot{border-color:var(--flag);
    background:repeating-linear-gradient(45deg,transparent 0 2px,var(--flag) 2px 3px)}
  .station[data-status="blocked"] .name{color:var(--soft)}
  .station[data-kind="capstone"] .dot{box-shadow:0 0 0 2.5px var(--paper),0 0 0 5.5px var(--c)}
  .station[data-kind="capstone"] .name{font-weight:700}
  .station:hover,.station:focus-visible{background:#00000007}
  .station[aria-current="true"]{background:#0000000f}
  .station[aria-current="true"] .name{font-weight:700}
  #map.dimming .station{opacity:.22}
  #map.dimming .station.inchain{opacity:1}
  path.edge{fill:none;stroke-width:1.5;transition:opacity .18s ease}
  #map.dimming path.edge{opacity:.12}
  #map.dimming path.edge.inchain{opacity:.95;stroke-width:2.1}

  /* ---- detail rail ---- */
  main.layout{display:grid;grid-template-columns:1fr;gap:0}
  @media(min-width:1180px){main.layout{grid-template-columns:minmax(0,1fr) 340px}}
  aside#detail{border-top:1px solid var(--line);padding:22px clamp(18px,3vw,34px) 60px}
  @media(min-width:1180px){
    aside#detail{border-top:0;border-left:1px solid var(--line);position:sticky;top:0;
      max-height:100vh;overflow:auto;align-self:start}
  }
  .tag{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:.7rem;
    color:var(--soft);border:1px solid var(--line);border-radius:99px;padding:3px 9px}
  .tag .swatch{width:11px;height:3px}
  #detail h2{font-size:1.5rem;line-height:1.12;margin:12px 0 4px;letter-spacing:-.01em}
  #detail .path{font-family:var(--mono);font-size:.72rem;color:var(--dim);word-break:break-all}
  #detail h3{font-family:var(--mono);font-weight:400;font-size:.7rem;color:var(--dim);
    margin:20px 0 6px;letter-spacing:.02em}
  #detail ul{margin:0;padding-left:1.05em}
  #detail li{margin:.28em 0;color:var(--soft)}
  #detail .reqs{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px}
  #detail .reqs button{font-family:var(--mono);font-size:.7rem;background:#00000006;color:var(--soft);
    border:1px solid var(--line);border-radius:99px;padding:3px 9px;cursor:pointer}
  #detail .reqs button:hover{color:var(--ink);border-color:var(--dim)}
  #detail .tag.blocked{color:var(--flag);border-color:var(--flag)}
  .empty{color:var(--dim)}
  #lowbar{display:flex;flex-wrap:wrap;gap:8px;padding:12px clamp(18px,3.4vw,44px);border-top:1px solid var(--line)}
  #lowbar button{font-family:var(--mono);font-size:.72rem;background:#00000006;color:var(--soft);
    border:1px solid var(--line);border-radius:99px;padding:4px 11px;cursor:pointer}
  #lowbar button[aria-pressed="true"]{color:var(--ink);border-color:var(--dim);background:#00000010}
  footer{padding:22px clamp(18px,3.4vw,44px) 46px;color:var(--dim);font-size:.8rem;
    border-top:1px solid var(--line)}
  footer code{font-family:var(--mono);color:var(--soft)}

  @media (prefers-reduced-motion: reduce){
    *{transition:none!important;animation:none!important}
  }
  @media (max-width:640px){
    :root{--colw:196px;--rowh:112px}
  }
</style>
</head>
<body>
<header class="masthead">
  <div class="cols">
    <div>
      <h1>The Skill Tree</h1>
      <p class="lede">A from-scratch curriculum — mathematics, low-level systems, distributed
        systems, the cloud, ML systems, agents — drawn as one dependency map.
        <b>Columns are tracks, the vertical order is dependency</b> — a node unlocks only when
        everything above it, in its own column or another, is built. Every station is a graded
        module; a thick ring marks a <b>capstone</b>, a dashed dot material already in the repo
        (it counts toward a badge, not toward XP). A <b>hatched dot</b> is a project
        <b>blocked</b> on a resource it does not have — a GPU, production traffic, human labels —
        tracked on the map but not moving the level.</p>
    </div>
    <div class="stat">
      <!--__PROGRESS__-->
      <!--__GAMIFY__-->
      <!--__LEGEND__-->
    </div>
  </div>
</header>

<main class="layout">
  <section class="atlas">
    <div id="lowbar" role="group" aria-label="Filter and reset">
      <button type="button" data-filter="all" aria-pressed="true">all</button>
      <button type="button" data-filter="ready" aria-pressed="false">ready</button>
      <button type="button" data-filter="done" aria-pressed="false">built</button>
      <button type="button" data-filter="todo" aria-pressed="false">todo</button>
      <button type="button" data-filter="blocked" aria-pressed="false">blocked</button>
      <button type="button" id="reset" aria-pressed="false">clear selection</button>
    </div>
    <div class="scroller">
      <div class="colheaders"><!--__COLHEADERS__--></div>
      <div id="map" role="group" aria-label="Skill tree: tracks as columns, dependency order downward">
        <svg id="edges" aria-hidden="true"></svg>
      </div>
    </div>
  </section>
  <aside id="detail" aria-live="polite"></aside>
</main>

<footer>
  Generated from <code>tree.toml</code> by <code>python3 skill-tree/render_html.py</code>.
  <b>__DONE__ of __TOTAL__ nodes built.</b> Regenerate after changing the tree; the
  command-line view is <code>python3 skill-tree/tree.py</code>.
</footer>

<script>
const DATA = /*__DATA__*/;
const map = document.getElementById('map');
const svg = document.getElementById('edges');
const detail = document.getElementById('detail');
const byId = Object.fromEntries(DATA.nodes.map(n => [n.id, n]));
const trackIndex = t => DATA.tracks.indexOf(t);
const children = {};
DATA.nodes.forEach(n => n.requires.forEach(r => (children[r] = children[r] || []).push(n.id)));

const depthMemo = {};
function depth(id){
  if (id in depthMemo) return depthMemo[id];
  const r = byId[id].requires;
  return (depthMemo[id] = r.length ? 1 + Math.max(...r.map(depth)) : 0);
}
const status = n => (n.status === 'done' || n.status === 'exists') ? n.status
  : (n.blocked_by && n.blocked_by.length) ? 'blocked'
  : n.status === 'todo' && n.requires.every(r => byId[r].status === 'done') ? 'ready' : n.status;

const CSS = getComputedStyle(document.documentElement);
const COLW = parseInt(CSS.getPropertyValue('--colw')) || 210;
const ROWH = parseInt(CSS.getPropertyValue('--rowh')) || 108;
const PADY = 22;
const cx = t => trackIndex(t) * COLW + COLW / 2;

/* One row per node within a track, ordered by dependency depth: nodes that share a
   depth are independent, so they stack in the same column instead of colliding. */
const rowOf = {};
for (const t of DATA.tracks) {
  DATA.nodes.filter(n => n.track === t)
    .sort((a, b) => depth(a.id) - depth(b.id) || a.id.localeCompare(b.id))
    .forEach((n, i) => (rowOf[n.id] = i));
}
const maxRows = Math.max(...DATA.nodes.map(n => rowOf[n.id])) + 1;
const cy = id => PADY + rowOf[id] * ROWH + ROWH / 2;

/* lanes */
DATA.tracks.forEach((t, i) => {
  const lane = document.createElement('div');
  lane.className = 'lane' + (i % 2 ? ' alt' : '');
  lane.style.left = trackIndex(t) * COLW + 'px';
  map.appendChild(lane);
});

/* stations */
const stations = document.createElement('div');
for (const n of DATA.nodes) {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'station';
  b.dataset.id = n.id;
  b.dataset.status = status(n);
  b.dataset.kind = n.kind || 'skill';
  b.setAttribute('aria-current', 'false');
  b.style.setProperty('--c', DATA.colors[n.track]);
  b.style.left = trackIndex(n.track) * COLW + 'px';
  b.style.top = PADY + rowOf[n.id] * ROWH + 4 + 'px';
  b.style.height = ROWH - 8 + 'px';
  const d = document.createElement('span'); d.className = 'dot';
  const s = document.createElement('span'); s.className = 'name';
  s.textContent = n.title;
  const id = document.createElement('span'); id.className = 'id';
  id.textContent = n.id.replace(/^([a-z]+)-\d\d-/, '$1 · ');
  b.append(d, s);
  s.appendChild(id);
  b.addEventListener('click', () => select(n.id, true));
  b.addEventListener('mouseenter', () => highlight(n.id));
  b.addEventListener('mouseleave', () => (selected ? highlight(selected) : unhighlight()));
  b.addEventListener('keydown', e => nav(e, n));
  stations.appendChild(b);
}
function nav(e, n){
  const r = rowOf[n.id];
  const inTrack = t => DATA.nodes.filter(x => x.track === t);
  const nearest = (list, r) => list.slice().sort((a, b) => Math.abs(rowOf[a.id] - r) - Math.abs(rowOf[b.id] - r))[0];
  let target = null;
  if (e.key === 'ArrowUp') target = inTrack(n.track).find(x => rowOf[x.id] === r - 1);
  else if (e.key === 'ArrowDown') target = inTrack(n.track).find(x => rowOf[x.id] === r + 1);
  else if (e.key === 'ArrowLeft') target = nearest(inTrack(DATA.tracks[trackIndex(n.track) - 1]), r);
  else if (e.key === 'ArrowRight') target = nearest(inTrack(DATA.tracks[trackIndex(n.track) + 1]), r);
  if (target) { e.preventDefault(); stationEl(target.id).focus(); }
  else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(n.id, true); }
}
map.insertBefore(stations, svg.nextSibling);
const stationEl = id => map.querySelector('.station[data-id="' + id + '"]');

/* edges */
const NS = 'http://www.w3.org/2000/svg';
for (const n of DATA.nodes) {
  for (const r of n.requires) {
    const x1 = cx(byId[r].track), y1 = cy(r), x2 = cx(n.track), y2 = cy(n.id);
    const p = document.createElementNS(NS, 'path');
    const mid = (y1 + y2) / 2;
    p.setAttribute('d', `M ${x1} ${y1} C ${x1} ${mid}, ${x2} ${mid}, ${x2} ${y2}`);
    p.setAttribute('class', 'edge');
    p.setAttribute('stroke', DATA.colors[n.track]);
    p.setAttribute('opacity', '0.5');
    p.dataset.from = r; p.dataset.to = n.id;
    svg.appendChild(p);
  }
}

/* chain highlight */
function chain(id){
  const up = new Set(), down = new Set();
  (function walkUp(x){ for (const r of byId[x].requires) if (!up.has(r)) { up.add(r); walkUp(r); } })(id);
  (function walkDown(x){ for (const c of children[x] || []) if (!down.has(c)) { down.add(c); walkDown(c); } })(id);
  up.add(id); down.add(id);
  return { up, down, all: new Set([...up, ...down]) };
}
function highlight(id){
  const { all } = chain(id);
  map.classList.add('dimming');
  map.querySelectorAll('.station').forEach(el => el.classList.toggle('inchain', all.has(el.dataset.id)));
  svg.querySelectorAll('path.edge').forEach(p => p.classList.toggle('inchain', all.has(p.dataset.from) && all.has(p.dataset.to)));
}
function unhighlight(){
  map.classList.remove('dimming');
  map.querySelectorAll('.station').forEach(el => el.classList.remove('inchain'));
  svg.querySelectorAll('path.edge').forEach(p => p.classList.remove('inchain'));
}

/* selection + detail */
let selected = null;
function select(id, focus){
  selected = id;
  map.querySelectorAll('.station').forEach(el => el.setAttribute('aria-current', el.dataset.id === id ? 'true' : 'false'));
  highlight(id);
  renderDetail(byId[id]);
  if (focus) stationEl(id).focus({ preventScroll: true });
}
function srcText(s){ return (DATA.bookName[s] || s) + ' · ' + s; }
function section(title, items){
  if (!items || !items.length) return '';
  return '<h3>' + title + '</h3><ul>' + items.map(x => '<li>' + escapeHtml(x) + '</li>').join('') + '</ul>';
}
function escapeHtml(s){ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function renderDetail(n){
  const st = status(n);
  const reqs = n.requires.length
    ? n.requires.map(r => '<button type="button" data-goto="' + r + '">' + r + ' · ' + status(byId[r]) + '</button>').join('')
    : '<span class="empty">nothing — a root</span>';
  const metric = DATA.countsForXp[n.track]
    ? (n.difficulty || 2) + '/5 · ' + (DATA.xp[n.id] || 0) + ' XP'
    : 'project · not graded';
  detail.innerHTML =
    '<span class="tag"><span class="swatch" style="--c:' + DATA.colors[n.track] + '"></span>' +
      DATA.labels[n.track] + '</span> <span class="tag">' + st + '</span>' +
    (n.blocked_by && n.blocked_by.length
      ? '<span class="tag blocked">blocked · ' + escapeHtml(n.blocked_by.join(', ')) + '</span>' : '') +
    '<span class="tag">' + metric + '</span>' +
    (n.kind === 'capstone' ? '<span class="tag">capstone</span>' : '') +
    '<h2>' + escapeHtml(n.title) + '</h2>' +
    '<div class="path">' + escapeHtml(n.deliverable) + '/</div>' +
    '<h3>requires</h3><div class="reqs">' + reqs + '</div>' +
    section('build', n.build) +
    section('accept', n.accept) +
    section('limit cases', n.limit_cases) +
    section('sources', n.sources.map(srcText));
  detail.querySelectorAll('[data-goto]').forEach(b => b.addEventListener('click', () => select(b.dataset.goto, true)));
}

/* filters */
let filter = 'all';
function applyFilter(){
  map.querySelectorAll('.station').forEach(el => {
    const hidden = filter !== 'all' && el.dataset.status !== filter;
    el.style.display = hidden ? 'none' : '';
  });
}
document.getElementById('lowbar').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  if (b.id === 'reset') { selected = null; unhighlight(); map.querySelectorAll('.station').forEach(el => el.setAttribute('aria-current','false')); renderDetailDefault(); return; }
  filter = b.dataset.filter;
  document.querySelectorAll('#lowbar button[data-filter]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  applyFilter();
});

function renderDetailDefault(){
  const ready = DATA.nodes.filter(n => status(n) === 'ready');
  detail.innerHTML = '<h2>Next up</h2><p class="empty">Pick a station to see what it asks of you, ' +
    'or start with one that is ready. Hovering traces the dependency chain.</p>' +
    '<div class="reqs">' + (ready.length
      ? ready.map(n => '<button type="button" data-goto="' + n.id + '">' + n.id + '</button>').join('')
      : '<span class="empty">every ready node is built</span>') + '</div>';
  detail.querySelectorAll('[data-goto]').forEach(b => b.addEventListener('click', () => select(b.dataset.goto, true)));
}

/* size the map */
map.style.height = maxRows * ROWH + 2 * PADY + 'px';
svg.setAttribute('viewBox', '0 0 ' + (DATA.tracks.length * COLW) + ' ' + (maxRows * ROWH + 2 * PADY));
svg.setAttribute('preserveAspectRatio', 'none');
map.style.setProperty('--colw', COLW + 'px');

renderDetailDefault();
</script>
</body>
</html>
"""


def main(argv: list[str]) -> int:
    nodes, books = load()
    out = Path(argv[0]) if argv else HERE / "tree.html"
    out.write_text(build(nodes, books))
    print(f"{out} written ({len(nodes)} nodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
