#!/usr/bin/env python3
"""Build site/data/corridors.json from corridors/map_*.json plus the raw segment CSVs.

Usage: python3 pipeline/build.py [YYYY-MM-DD]     (date defaults to today)
       python3 pipeline/build.py --selfcheck

Speed is average weekday bus speed: sum(mile_trips) / (sum(minute_trips) / 60) over any group
of rows. Per-segment speeds are never averaged.

Consistent basis: segments come and go in the feed (a timepoint is added, a route is rerouted),
so a corridor's pooled speed can shift just because the segment mix changed. Stop-id variants of
the same stop pair (same route, direction and stop locations) are merged into one segment. A
segment is "consistent" if it has rows in every one of the 12 baseline months; that window is
closed, so the basis never changes retroactively. If consistent segments carry at least 70% of the
corridor's trips in the baseline months, baseline, latest and post-plan figures use them ("basis":
"consistent"); otherwise they use all segments ("basis": "all"). Year-over-year and post-plan
changes use only segments present in every month being compared. Segments whose recorded distance
moves more than 3% inside the window are dropped (a source distance change would look like a speed
change); smaller drift is removed by holding each segment's miles per trip fixed at its baseline value.
Stop-id variants whose recorded lengths differ by more than about 0.1 mi are not merged. "series" starts at 2025-07 and is on the basis used. Summary pooled figures count each
segment-month once even when two corridors share it, and skip corridors with no baseline.
Mapped segments that never match a row are listed on stdout.
"""
import csv, datetime, glob, hashlib, json, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE_FROM, BASE_TO, PLAN_MONTH, TARGET = "2025-07", "2026-06", "2026-07", 20
MIN_COVER = 0.70
MAX_DIST_MOVE = 0.03  # a segment whose miles-per-trip moves more than this in the window is left out


def mph(rows):
    mi = sum(r[0] for r in rows)
    mn = sum(r[1] for r in rows)
    return mi / (mn / 60) if mn > 0 else None


def r2(x): return None if x is None else round(x, 2)
def r1(x): return None if x is None else round(x, 1)
def pct(a, b): return None if a is None or not b else (a / b - 1) * 100


def prev_year(ym): return f"{int(ym[:4]) - 1}{ym[4:]}"


def pooled(data, keys, months):
    """mph for the given segment keys over the given months."""
    return mph([data[k][m] for k in keys for m in months if m in data.get(k, {})])


def corridor_numbers(data, keys, all_months, drop=()):
    """All speed figures for one corridor. data: key -> {ym: (mile_trips, minute_trips, trips)}.
    drop: keys left out entirely (unstable source distance)."""
    keys = [k for k in keys if data.get(k) and k not in drop]
    if not keys:
        return None
    win = [m for m in all_months if m >= BASE_FROM]  # comparison window; earlier months are never used
    base_months = [m for m in win if m <= BASE_TO]
    post = [m for m in win if m >= PLAN_MONTH]
    latest_m = all_months[-1]
    # Basis is frozen by the closed baseline window: a segment counts as consistent if it has rows in
    # every baseline month, so later months can never change the baseline or target.
    cons = [k for k in keys if all(m in data[k] for m in base_months)]
    trips = lambda ks: sum(data[k][m][2] for k in ks for m in base_months if m in data[k])
    cover = trips(cons) / trips(keys) if cons and trips(keys) else 0
    basis = "consistent" if cover >= MIN_COVER else "all"
    use = cons if basis == "consistent" else keys
    ser = lambda ks: [{"month": m, "mph": r2(pooled(data, ks, [m])),
                       "trips": sum(data[k][m][2] for k in ks if m in data[k])}
                      for m in win if any(m in data[k] for k in ks)]
    # like for like: yoy and post-plan use only (segment, month) cells whose same month a year earlier also exists
    cells = lambda ms: [(k, m) for k in use for m in ms if m in data[k] and prev_year(m) in data[k]]
    prior_of = lambda cs: [(k, prev_year(m)) for k, m in cs]
    val = lambda cs: mph([data[k][m] for k, m in cs])
    lc, pc = cells([latest_m]), cells(post)
    base = pooled(data, use, base_months)
    lat = pooled(data, use, [latest_m])
    lk = [k for k in use if latest_m in data[k]]  # basis segments still reporting in the latest month
    pk = [k for k in use if any(m in data[k] for m in post)]
    pp, pp_prior = val(pc), val(prior_of(pc))
    return {
        "basis": basis, "consistent_coverage_pct": r1(cover * 100),
        "n_consistent_segments": len(cons), "n_basis_segments": len(use),
        "n_latest_segments": len(lk), "n_post_plan_segments": len(pk),
        "baseline_mph": r2(base), "target_mph": r2(base * (1 + TARGET / 100)) if base else None,
        "latest": {"month": latest_m, "mph": r2(lat),
                   "yoy_pct": r1(pct(val(lc), val(prior_of(lc)))),
                   "vs_baseline_pct": r1(pct(lat, pooled(data, lk, base_months))) if lk else None},
        "post_plan": {"mph": r2(pp), "same_months_prior_year_mph": r2(pp_prior),
                      "change_pct": r1(pct(pp, pp_prior)), "months": len(post)},
        "series": ser(use), "consistent_series": ser(cons), "full_series": ser(keys),
        "_use": use, "_base_months": base_months, "_latest": latest_m, "_post": post,
        "_cells_base": [(k, m) for k in use for m in base_months if m in data[k]],
        "_cells_latest": [(k, latest_m) for k in use if latest_m in data[k]],
        "_cells_post": pc, "_cells_prior": prior_of(pc),
    }


def gkey(k, cat):
    """Stop-id variants of one physical segment (same route, direction, stop locations) share a key."""
    try:
        c = cat[k]
        # variants of different recorded length (rounded to 0.1 mi) are different stretches, so not merged
        return (k[0], k[1]) + tuple(round(float(c[f]), 3) for f in ("from_lat", "from_lon", "to_lat", "to_lon")) + (round(float(c["miles"]), 1),)
    except (KeyError, TypeError, ValueError):
        return k


def load(raw=ROOT / "data" / "raw"):
    rows, cat = {}, {}
    with open(raw / "segment_monthly.csv") as f:
        for r in csv.DictReader(f):
            k = (r["route_id"], r["direction"], r["timepoint_stop_id"], r["next_timepoint_stop_id"])
            m = f"{int(r['year'])}-{int(r['month']):02d}"
            a = rows.setdefault(k, {}).get(m, (0, 0, 0))
            rows[k][m] = (a[0] + float(r["mile_trips"]), a[1] + float(r["minute_trips"]), a[2] + int(r["trips"]))
    with open(raw / "segment_catalog.csv") as f:
        for r in csv.DictReader(f):
            cat.setdefault((r["route_id"], r["direction"], r["timepoint_stop_id"], r["next_timepoint_stop_id"]), r)
    data = {}  # merged by physical segment
    for k, v in rows.items():
        d = data.setdefault(gkey(k, cat), {})
        for m, a in v.items():
            b = d.get(m, (0, 0, 0))
            d[m] = (a[0] + b[0], a[1] + b[1], a[2] + b[2])
    return data, cat


def unstable(data):
    """Segments whose recorded distance (miles per trip) moves more than 3% inside the comparison
    window. Speed = distance / time, so a changed distance looks like a speed change."""
    bad = set()
    for k, v in data.items():
        d = [x[0] / x[2] for m, x in v.items() if m >= BASE_FROM and x[2] > 0 and x[0] > 0]
        if d and max(d) / min(d) > 1 + MAX_DIST_MOVE:
            bad.add(k)
    return bad


def fix_distance(data):
    """Give each segment one fixed distance (its baseline miles per trip) so only travel time moves a
    speed. Baseline figures are unchanged; later months lose the effect of small recorded-distance drift."""
    out = {}
    for k, v in data.items():
        for ms in ([m for m in v if BASE_FROM <= m <= BASE_TO], [m for m in v if m >= BASE_FROM]):
            t = sum(v[m][2] for m in ms)
            if t > 0 and sum(v[m][0] for m in ms) > 0:
                d = sum(v[m][0] for m in ms) / t
                out[k] = {m: (d * x[2], x[1], x[2]) for m, x in v.items()}
                break
        else:
            out[k] = v
    return out


def seg_key(s): return (s["route_id"], s["direction"], str(s["from_id"]), str(s["to_id"]))


def build_corridor(entry, mp, data, cat, all_months, bad, public):
    out = {"id": entry["id"], "name": entry["name"], "borough": entry["borough"],
           "rapid_bus_corridor": entry.get("rapid_bus_corridor", False),
           "status": "unmapped", "definition": None, "notes": "mapping pending", "public_note": public.get(str(entry["id"])),
           "routes": [], "miles": None, "n_segments": None, "basis": None, "baseline_mph": None, "target_mph": None,
           "latest": None, "post_plan": None, "series": [], "consistent_series": [], "segments": []}
    if mp is None:
        return out, [], None
    out.update(status=mp["status"], definition=mp.get("definition") or None, notes=mp.get("notes") or "",
               routes=mp.get("routes", []))
    segs, seen = [], set()
    for s in mp.get("segments", []):
        g = gkey(seg_key(s), cat)
        if g not in seen:
            seen.add(g)
            segs.append((g, s))
    if not segs:
        return out, [], None
    keys = [g for g, _ in segs]
    never = [s for g, s in segs if not data.get(g)]
    out["miles"] = r2(sum(float(s.get("miles") or 0) for _, s in segs))  # replaced below by basis miles when there is a basis
    out["n_segments"] = len(segs)
    dropped = [g for g in keys if g in bad]
    n = corridor_numbers(data, keys, all_months, bad)
    if dropped:
        out["dropped_distance_unstable"] = len(dropped)
    if n is None or n["baseline_mph"] is None:
        # no data in the baseline window (e.g. stop ids changed), so nothing can be compared
        out["no_recent_data"] = True
        return out, never, None
    use = set(n["_use"])
    out["miles"] = r2(sum(float(s.get("miles") or 0) for g, s in segs if g in use))  # route-miles of segments used
    for f in ("basis", "consistent_coverage_pct", "n_consistent_segments", "n_basis_segments", "n_latest_segments", "n_post_plan_segments", "baseline_mph",
              "target_mph", "latest", "post_plan", "series", "consistent_series"):
        out[f] = n[f]
    fl = lambda x: float(x) if x not in (None, "") else None
    for g, s in segs:
        c = cat.get(seg_key(s), {})
        out["segments"].append({
            "route_id": s["route_id"], "direction": s["direction"], "from_stop": s.get("from_stop"),
            "to_stop": s.get("to_stop"), "from_lat": fl(c.get("from_lat")), "from_lon": fl(c.get("from_lon")),
            "to_lat": fl(c.get("to_lat")), "to_lon": fl(c.get("to_lon")), "miles": s.get("miles"),
            "baseline_mph": r2(pooled(data, [g], n["_base_months"])) if g in use else None,
            "latest_mph": r2(pooled(data, [g], [n["_latest"]])) if g in use else None, "in_basis": g in use,
            "excluded_reason": None if g in use else "distance changed" if g in bad else "no data" if not data.get(g) else "not in every baseline month"})
    return out, never, n


def pool_once(data, nums, field):
    """Pooled mph over tracked corridors' (segment, month) cells, counting each cell once even if two corridors share it."""
    cells = {c for n in nums for c in n[field]}
    return mph([data[k][m] for k, m in cells])  # unrounded; callers round for output


def check_source():
    """Refuse to build from a download made with a different filter than fetch.py uses now."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import fetch
    try:
        got = json.load(open(ROOT / "data" / "raw" / "fetch_meta.json")).get("filter")
    except OSError:
        got = None
    if got != fetch.WEEKDAY:
        sys.exit(f"data/raw was not downloaded with the current filter ({got!r} vs {fetch.WEEKDAY!r}). Run pipeline/fetch.py first.")


def main(date):
    data, cat = load()
    all_months = sorted({m for v in data.values() for m in v})
    listing = json.load(open(ROOT / "corridors" / "list.json"))
    public = json.load(open(ROOT / "corridors" / "public.json"))
    maps, missing, hashes = {}, [], {}
    for p in sorted(glob.glob(str(ROOT / "corridors" / "map_*.json"))):
        hashes[os.path.basename(p)] = hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
        try:
            for c in json.load(open(p))["corridors"]:
                maps[c["id"]] = c
        except Exception as e:
            missing.append(f"{p}: {e}")
    expected = ["map_bx", "map_mn", "map_qn", "map_bk_si"]
    missing += [f"corridors/{e}.json not found" for e in expected if not (ROOT / "corridors" / f"{e}.json").exists()]
    bad = unstable(data)  # judged on recorded distances, before they are held fixed
    data = fix_distance(data)
    check_source()
    corridors, report, nums = [], {}, {}
    for e in listing:
        c, never, n = build_corridor(e, maps.get(e["id"]), data, cat, all_months, bad, public)
        corridors.append(c)
        if never: report[e["id"]] = never
        if n: nums[e["id"]] = n
    # corridors that use some of the same segments are not independent
    for c in corridors:
        if c["id"] in nums:
            c["shares_segments_with"] = [o for o in nums if o != c["id"] and set(nums[o]["_use"]) & set(nums[c["id"]]["_use"])]
    tracked = [c for c in corridors if c["baseline_mph"] is not None]
    post = [m for m in all_months if m >= PLAN_MONTH]
    ns = list(nums.values())
    pp = pool_once(data, ns, "_cells_post")
    pp_prior = pool_once(data, ns, "_cells_prior")
    summary = {"corridors_total": len(listing), "corridors_tracked": len(tracked),
               "post_plan_months": post,
               "tracked_baseline_mph": r2(pool_once(data, ns, "_cells_base")),
               "tracked_latest_mph": r2(pool_once(data, ns, "_cells_latest")),
               "tracked_post_plan_mph": r2(pp), "tracked_same_months_prior_year_mph": r2(pp_prior),
               "tracked_post_plan_change_pct": r1(pct(pp, pp_prior)),
               "shared_segment_pairs": sorted({tuple(sorted((c["id"], o))) for c in tracked for o in c.get("shares_segments_with", [])})}
    summary["shared_segment_pairs"] = [list(p) for p in summary["shared_segment_pairs"]]
    out = {"generated": date, "data_through": all_months[-1], "plan_released": "2026-07",
           "inputs": {"corridor_files_sha256_12": hashes, "source_filter": __import__("fetch").WEEKDAY},
           "baseline": {"from": BASE_FROM, "to": BASE_TO,
                        "note": "The plan does not define a baseline period. We chose the 12 months before the plan (July 2025 to June 2026). Speeds are average weekday bus speed."},
           "target_pct": TARGET, "summary": summary, "corridors": corridors}
    (ROOT / "site" / "data").mkdir(parents=True, exist_ok=True)
    path = ROOT / "site" / "data" / "corridors.json"
    try:
        old = json.load(open(path))
        if {**old, "generated": None} == {**json.loads(json.dumps(out)), "generated": None}:
            out["generated"] = old["generated"]  # nothing else changed, so the nightly job commits nothing
    except (OSError, ValueError):
        pass
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote site/data/corridors.json: {len(tracked)}/{len(listing)} corridors with data, data through {all_months[-1]}, post-plan months {post}")
    print("summary:", json.dumps(summary))
    from collections import Counter
    print("status:", dict(Counter(c["status"] for c in corridors)), "basis:", dict(Counter(c["basis"] for c in corridors)))
    print("map hashes:", hashes)
    for c in corridors:
        if c.get("n_latest_segments") is not None and c["n_latest_segments"] < c["n_basis_segments"]:
            print(f"corridor {c['id']} {c['name']}: {c['n_basis_segments'] - c['n_latest_segments']} basis segment(s) have no data in {all_months[-1]}")
    print("segments with unstable distance:", len(bad), [c["id"] for c in corridors if c.get("dropped_distance_unstable")])
    for m in missing: print("MISSING:", m)
    print("mapping pending:", [c["id"] for c in corridors if c["notes"] == "mapping pending"])
    print("no public note:", [c["id"] for c in corridors if not c["public_note"]])
    for cid, ss in report.items():
        print(f"corridor {cid}: {len(ss)} mapped segments never matched:", [f"{s['route_id']} {s['direction']} {s['from_id']}->{s['to_id']}" for s in ss][:5])


def selfcheck():
    # segment A present all 4 months, segment B only in the last two.
    mo = ["2025-07", "2025-08", "2026-07", "2026-08"]
    data = {"A": {"2025-07": (10, 60, 5), "2025-08": (10, 60, 5), "2026-07": (12, 60, 5), "2026-08": (12, 60, 5)},
            "B": {"2026-07": (1, 30, 1), "2026-08": (1, 30, 1)}}
    assert abs(mph([(10, 60, 1), (1, 30, 1)]) - 11 / 1.5) < 1e-9  # weighted, not mean of 10 and 2
    n = corridor_numbers(data, ["A", "B"], mo)
    assert n["basis"] == "consistent" and n["n_consistent_segments"] == 1  # A carries 20/22 trips
    assert n["baseline_mph"] == 10.0 and n["target_mph"] == 12.0
    assert n["latest"]["month"] == "2026-08" and n["latest"]["mph"] == 12.0
    assert n["latest"]["yoy_pct"] == 20.0 and n["latest"]["vs_baseline_pct"] == 20.0
    assert n["post_plan"]["mph"] == 12.0 and n["post_plan"]["same_months_prior_year_mph"] == 10.0
    assert n["post_plan"]["change_pct"] == 20.0 and n["post_plan"]["months"] == 2
    data["A"] = {m: v for m, v in data["A"].items() if m != "2025-08"}  # A now misses a month
    n = corridor_numbers(data, ["A", "B"], mo)
    assert n["basis"] == "all" and n["consistent_series"] == []
    assert corridor_numbers(data, ["nope"], mo) is None
    # basis is judged on the baseline window only: B (rows only after the plan) never makes A inconsistent
    data["A"] = {"2025-07": (10, 60, 5), "2025-08": (10, 60, 5), "2026-07": (12, 60, 5)}  # A misses 2026-08
    n = corridor_numbers(data, ["A", "B"], mo)
    assert n["basis"] == "consistent" and n["baseline_mph"] == 10.0
    assert n["post_plan"]["mph"] == 12.0 and n["post_plan"]["months"] == 2  # only 2026-07 cells, like for like
    assert n["post_plan"]["same_months_prior_year_mph"] == 10.0
    assert corridor_numbers(data, ["A", "B"], mo, drop={"A"})["n_consistent_segments"] == 0  # dropped keys are ignored
    # shared segments count once and a corridor with no baseline adds nothing to the pooled figures
    d2 = {"S": {"2025-07": (10, 60, 5), "2025-08": (10, 60, 5), "2026-07": (10, 60, 5), "2026-08": (10, 60, 5)},
          "T": {"2025-01": (1, 60, 1), "2026-08": (1, 60, 1)}}
    ns = [corridor_numbers(d2, ["S"], mo), corridor_numbers(d2, ["S"], mo), corridor_numbers(d2, ["T"], mo)]
    assert ns[2]["baseline_mph"] is None
    ns = [n for n in ns if n["baseline_mph"] is not None]
    assert abs(pool_once(d2, ns, "_cells_latest") - 10.0) < 1e-9
    assert len(unstable({"U": {"2025-07": (10, 60, 10), "2025-08": (6, 60, 10)}, "V": {"2025-07": (10, 60, 10), "2025-08": (10.1, 60, 10)}})) == 1
    cat = {("R", "N", "1", "2"): {"from_lat": "40.1234", "from_lon": "-73.1", "to_lat": "40.2", "to_lon": "-73.2", "miles": "0.184"},
           ("R", "N", "9", "2"): {"from_lat": "40.12341", "from_lon": "-73.1", "to_lat": "40.2", "to_lon": "-73.2", "miles": "0.185"},
           ("R", "N", "8", "2"): {"from_lat": "40.12341", "from_lon": "-73.1", "to_lat": "40.2", "to_lon": "-73.2", "miles": "0.255"}}
    assert gkey(("R", "N", "8", "2"), cat) != gkey(("R", "N", "1", "2"), cat)  # different recorded length: not merged
    assert gkey(("R", "N", "1", "2"), cat) == gkey(("R", "N", "9", "2"), cat) != gkey(("R", "S", "1", "2"), cat)
    fx = fix_distance({"F": {"2025-07": (10, 60, 10), "2026-07": (9.7, 60, 10)}})["F"]
    assert fx["2025-07"] == (10, 60, 10) and abs(fx["2026-07"][0] - 10) < 1e-9 and fx["2026-07"][1] == 60
    print("selfcheck ok")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv: selfcheck()
    else: main(sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat())
