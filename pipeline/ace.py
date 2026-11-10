#!/usr/bin/env python3
"""Did MTA bus-lane camera enforcement speed up buses? Difference-in-differences.

Usage: python3 pipeline/ace.py YYYY-MM-DD [--refresh]   (run analysis, write site/data/ace.json;
                                       --refresh downloads the source data again, otherwise a
                                       copy already in data/raw is reused and its age is printed)
       python3 pipeline/ace.py --selfcheck     (toy-number asserts)
Stdlib only. Method notes: docs/ACE-METHOD.md
"""
import glob, json, os, random, re, statistics, sys, time, urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "site", "data", "ace.json")
ENF_URL = "https://data.ny.gov/resource/ki2b-sg5y.json"
SPD_URL = "https://data.ny.gov/resource/cudb-vcni.json"
WEEKDAY = "1"  # dataset metadata: day_type 1 = weekday, 2 = weekend
MIN_AFTER = 6
MIN_CONTROLS = 5
MAX_PAIRS = 11  # see caveats: the 12th matched month would be the skipped activation month
PAND = (2020 * 12 + 2, 2021 * 12 + 5)  # March 2020 .. June 2021 as month index y*12+(m-1)
SEED = 20261109
BOOT = 10000
# Queens Bus Network Redesign: Queens routes were renumbered and re-stopped in phases in mid 2025.
# The feed's own stop ids change in 2025-06 and 2025-09, so we flag Queens routes whose before or
# after months touch June to September 2025.
QR = (2025 * 12 + 5, 2025 * 12 + 8)
# Bronx Local Bus Network Redesign: late June 2022. A route whose before/after months straddle it is flagged.
BR = 2022 * 12 + 5
# enforced name -> data names, when they differ
ALIASES = {"M14+": ["M14A+", "M14D+"]}


# ---------- pure helpers (covered by --selfcheck) ----------
def mi(s):
    """'2024-06-20T..' or '2024-06' -> month index"""
    return int(s[:4]) * 12 + int(s[5:7]) - 1


def base(route):
    """Corridor key: strip SBS '+' and a trailing A-D variant letter after a digit."""
    return re.sub(r"(?<=\d)[A-D]$", "", route.rstrip("+"))


def speed(rows):
    t = sum(r[0] for r in rows)
    return sum(r[1] for r in rows) / t if t else None  # sum(miles)/sum(hours), never mean of means


def in_redesign(borough, months):
    return borough == "Queens" and any(QR[0] <= m <= QR[1] for m in months)


def in_bronx_redesign(borough, months):
    return borough == "Bronx" and min(months) <= BR <= max(months)


def share_map():
    """route base -> bases of routes listed on a shared corridor in corridors/map_*.json (same streets, so
    the same bus lanes). Only the 50 Priority Corridors are covered, so this is a partial list."""
    sm = defaultdict(set)
    for p in glob.glob(os.path.join(ROOT, "corridors", "map_*.json")):
        for c in json.load(open(p))["corridors"]:
            bs = {base(r) for r in c.get("routes", [])}
            for b in bs:
                sm[b] |= bs - {b}
    return sm


def pct(a, b):
    return (b / a - 1) * 100


def did(tb, ta, cb, ca):
    return pct(tb, ta) - pct(cb, ca)


def boot_mean(vals, rng, clusters=None):
    """Percentile 95% interval of the mean. With clusters, resample whole clusters."""
    n = len(vals)
    if clusters:
        groups = defaultdict(list)
        for v, c in zip(vals, clusters):
            groups[c].append(v)
        gl = list(groups.values())
    means = []
    for _ in range(BOOT):
        if clusters:
            s = [v for g in (rng.choice(gl) for _ in gl) for v in g]
        else:
            s = [rng.choice(vals) for _ in range(n)]
        means.append(sum(s) / len(s))
    means.sort()
    return means[int(0.025 * BOOT)], means[int(0.975 * BOOT) - 1]


def stats(rs, rng):
    d = [r["did_pct"] for r in rs]
    if not d:
        return {"n_routes": 0}
    lo, hi = boot_mean(d, rng)
    clo, chi = boot_mean(d, rng, [r["activated"] for r in rs])
    return {
        "n_routes": len(d),
        "median_did_pct": round(statistics.median(d), 2),
        "mean_did_pct": round(sum(d) / len(d), 2),
        "mean_ci95_lo": round(lo, 2), "mean_ci95_hi": round(hi, 2),
        "mean_ci95_clustered_by_activation_date_lo": round(clo, 2),
        "mean_ci95_clustered_by_activation_date_hi": round(chi, 2),
        "share_improved_vs_control": round(sum(x > 0 for x in d) / len(d), 3),
    }


# ---------- data ----------
def fetch(url, name, order):
    path = os.path.join(RAW, name)
    if os.path.exists(path) and "--refresh" not in sys.argv:
        print(f"using cached {name}, {(time.time() - os.path.getmtime(path)) / 86400:.1f} days old (pass --refresh to download again)")
        return json.load(open(path))
    print(f"downloading {name}")
    os.makedirs(RAW, exist_ok=True)
    rows, off, step = [], 0, 50000
    while True:
        u = f"{url}?$limit={step}&$offset={off}&$order={order}"
        with urllib.request.urlopen(u, timeout=120) as f:
            b = json.load(f)
        rows += b
        off += step
        if len(b) < step:
            break
    json.dump(rows, open(path, "w"))
    return rows


def analyse(today):
    enf = fetch(ENF_URL, "ace_enforced_routes.json", "route,program,implementation_date")
    spd = fetch(SPD_URL, "bus_speeds.json",
                "month,route_id,day_type,period,trip_type,borough")

    # weekday panel: route -> month -> (borough, trip_type) -> [hours, miles]
    panel = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0.0, 0.0])))
    for r in spd:
        if r["day_type"] != WEEKDAY:
            continue
        c = panel[r["route_id"]][mi(r["month"])][(r["borough"], r["trip_type"])]
        c[0] += float(r["total_operating_time"])
        c[1] += float(r["total_mileage"])
    last_month = max(m for rt in panel.values() for m in rt)

    # one event per enforced route: earliest camera date (ABLE or ACE); later one truncates window
    ev = defaultdict(list)
    for e in enf:
        ev[e["route"]].append((e["implementation_date"][:10], e["program"]))
    excluded, targets = [], []
    for name, lst in sorted(ev.items()):
        lst.sort()
        names = ALIASES.get(name, [name])
        miss = [n for n in names if n not in panel]
        if miss:
            excluded.append({"route": name, "reason": f"no matching route_id in bus-speed data ({', '.join(miss)})"})
            continue
        targets.append((name, names, lst))

    # corridor key -> month index of first camera activation (any program)
    first_act = {}
    for name, lst in ev.items():
        k = base(name)
        first_act[k] = min(first_act.get(k, 10 ** 9), mi(lst[0][0]))

    def ctl_ok(route, last):
        return first_act.get(base(route), 10 ** 9) > last

    SHARE = share_map()

    def compute(names, act, limit, noshare=False):
        """DiD for one route with activation month `act`; after months must be < `limit` (or None).
        Returns (result dict, None) or (None, reason)."""
        rows_of = lambda m: [v for n in names for k, v in panel[n].get(m, {}).items()]
        pairs = []
        for i in range(1, MAX_PAIRS + 1):
            a = act + i
            if a > last_month or (limit is not None and a >= limit):
                break
            if rows_of(a) and rows_of(a - 12):
                pairs.append((a - 12, a))
        if len(pairs) < MIN_AFTER:
            return None, f"only {len(pairs)} matched before/after month pairs (need {MIN_AFTER})"
        bm, am = [p[0] for p in pairs], [p[1] for p in pairs]
        tot = defaultdict(float)  # dominant (borough, trip_type) of the route in the window
        for m in bm + am:
            for n in names:
                for k, v in panel[n].get(m, {}).items():
                    tot[k] += v[0]
        stratum = max(tot, key=tot.get)
        if tot[stratum] < 0.9 * sum(tot.values()):
            return None, "borough/trip type mixed in window: " + ", ".join(f"{k[0]} {k[1]} {round(v)}h" for k, v in tot.items())
        sel = lambda ms: [v for n in names for m in ms for k, v in panel[n].get(m, {}).items() if k == stratum]
        tb, ta = speed(sel(bm)), speed(sel(am))
        # control: same stratum, never camera-enforced through the window, data in every used month
        last = max(am)
        cb_rows, ca_rows, nc = [], [], 0
        near = set().union(*(SHARE.get(base(n), set()) for n in names)) if noshare else set()
        for r, byc in panel.items():
            if r in names or not ctl_ok(r, last) or base(r) in near:
                continue
            if not all(stratum in byc.get(m, {}) for m in bm + am):
                continue
            nc += 1
            cb_rows += [byc[m][stratum] for m in bm]
            ca_rows += [byc[m][stratum] for m in am]
        if nc < MIN_CONTROLS:
            return None, f"only {nc} eligible control routes in {stratum[0]} {stratum[1]} (need {MIN_CONTROLS})"
        cb, ca = speed(cb_rows), speed(ca_rows)
        return {
            "before_mph": round(tb, 3), "after_mph": round(ta, 3),
            "change_pct": round(pct(tb, ta), 2),
            "control_change_pct": round(pct(cb, ca), 2),
            "did_pct": round(did(tb, ta, cb, ca), 2),
            "months_after": len(pairs),
            "pandemic_overlap": any(PAND[0] <= m <= PAND[1] for m in bm + am),
            "redesign_overlap": in_redesign(stratum[0], bm + am),
            "bronx_redesign_overlap": in_bronx_redesign(stratum[0], bm + am),
            "borough": stratum[0], "trip_type": stratum[1], "n_control_routes": nc,
        }, None

    out, placebo = [], []
    for name, names, lst in targets:
        act = mi(lst[0][0])
        later = mi(lst[1][0]) if len(lst) > 1 else None
        res, why = compute(names, act, later)
        if not res:
            excluded.append({"route": name, "reason": f"activated {lst[0][0]}: {why}"
                             + (f"; second camera program starts {lst[1][0]}" if later else "")
                             + f"; bus-speed data ends {last_month // 12}-{last_month % 12 + 1:02d}"})
            continue
        out.append({"route": name, "program": lst[0][1], "activated": lst[0][0], **res,
                    "second_camera_program": lst[1][0] if later else None})
        # placebo: pretend the camera arrived 12 months earlier; only months before the real activation
        pres, _ = compute(names, act - 12, act)
        if pres:
            placebo.append({"route": name, "activated": lst[0][0], "did_pct": pres["did_pct"],
                            "pandemic_overlap": pres["pandemic_overlap"]})

    # sensitivity: drop controls that share a corridor (so likely bus lanes) with the camera route
    out_ns = []
    for name, names, lst in targets:
        later = mi(lst[1][0]) if len(lst) > 1 else None
        r2_, _ = compute(names, mi(lst[0][0]), later, noshare=True)
        if r2_:
            out_ns.append({"did_pct": r2_["did_pct"], "activated": lst[0][0]})
    rng = random.Random(SEED)
    clean = [r for r in out if not r["pandemic_overlap"]]
    summary = {
        "all_routes": stats(out, rng),
        "excluding_pandemic_overlap": stats(clean, rng),
        "pandemic_overlap_routes": len(out) - len(clean),
        "bootstrap": f"{BOOT} resamples of routes with replacement, seed {SEED}; percentile interval",
        "unit": "did_pct = treated % change minus control % change, percentage points",
    }
    summary["excluding_queens_redesign_overlap"] = stats([r for r in out if not r["redesign_overlap"]], rng)
    summary["excluding_controls_sharing_a_corridor"] = stats(out_ns, rng)
    summary["queens_redesign_overlap_routes"] = sum(r["redesign_overlap"] for r in out)
    for p in ("ACE", "ABLE"):
        sub = [r for r in clean if r["program"] == p]
        summary[f"excluding_pandemic_first_program_{p}"] = stats(sub, rng)
    pl = [r for r in placebo if not r["pandemic_overlap"]]
    summary["placebo_fake_activation_12_months_early"] = {
        "note": "same method with activation moved 12 months before the real date, using only pre-camera months; a mean far from 0 means treated and control routes were already drifting apart",
        **stats(pl, rng)}
    pm = summary["placebo_fake_activation_12_months_early"].get("mean_did_pct")
    mm = summary["all_routes"].get("mean_did_pct")
    qr = ", ".join(r["route"] for r in out if r["redesign_overlap"]) or "none"
    drift = ("That is larger than the main result, so the method's own drift is about as big as the effect it is trying to measure and the result is within noise."
             if pm is not None and mm is not None and abs(pm) >= abs(mm) else "That is smaller than the main result.")
    ns_mean = summary["excluding_controls_sharing_a_corridor"].get("mean_did_pct")
    br = ", ".join(r["route"] for r in out if r["bronx_redesign_overlap"]) or "none"
    caveats = [
        "This is observational. Routes were not picked at random, and cameras often came with new or repainted bus lanes, so any effect is cameras plus whatever came with them.",
        "Each camera route is compared with routes in the same borough and trip type that never had cameras. Those routes can still differ in road work, service changes, and Manhattan congestion pricing, which began 2025-01-05 and falls in the before months of the 2025 Manhattan routes.",
        "Queens bus routes were redesigned in phases in mid 2025 (this tracker flags June to September 2025). Queens routes whose before or after months include that period (this run: " + qr + ") mix the redesign with any camera effect. Read them with care. The summary is also given without those routes.",
        "The Bronx Local Bus Network Redesign took effect in late June 2022. Bronx routes whose before and after months straddle it (this run: " + br + ") mix the redesign with any camera effect. They are flagged in the data but not removed.",
        "Some comparison routes run in the same bus lanes as camera routes (for example the Madison Av routes M1 and M3 beside M2 and M4). Cameras ticket every vehicle in the lane, so these routes may also benefit, which would push the measured difference toward zero. As a check, the summary also gives a version without comparison routes that share a corridor with the camera route, using the corridor maps of the 50 Priority Corridors, so it catches only some overlaps. Mean difference in this run: " + str(ns_mean) + " points without them, " + str(mm) + " with them.",
        "Almost all Select Bus Service (SBS) routes have cameras, so too few SBS routes without cameras remain to compare against. The results are really about local and limited routes.",
        "Many routes started on the same dates and share comparison routes, so their results are not independent. The interval shown on the page is the wider of two intervals we compute, so it does not overstate the certainty.",
        "Speed is measured over the whole route, but cameras cover only part of it, which dilutes any effect.",
        "The start date is the earliest camera date (from either program). If a second program began later, the after months stop before it.",
        "A route has at most 11 matched months after its start date. The matching month for the 12th would be the start month itself, which we skip.",
        "Comparison routes that share a corridor name with a camera route (for example B44 local and B44 SBS) are left out.",
        "Routes whose cameras started in 2019 or earlier lack a full year of earlier data (the series starts 2019-01) and are excluded.",
        "March 2020 to June 2021 (the pandemic) is flagged. Results are given with and without those routes. " + (f"{len(out) - len(clean)} routes overlap it in this run." if len(out) != len(clean) else "None of the routes overlap it in this run."),
        f"Check with fake dates: moving each start date a year earlier, when no camera was present, gave an average of {pm} points against {mm} for the real dates. " + drift,
    ]
    doc = {"generated": today, "summary": summary,
           "routes": sorted(out, key=lambda r: r["route"]),
           "excluded": excluded, "caveats": caveats}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    try:
        old = json.load(open(OUT))
        if {**old, "generated": None} == {**json.loads(json.dumps(doc)), "generated": None}:
            doc["generated"] = old["generated"]  # nothing else changed, so the nightly job commits nothing
    except (OSError, ValueError):
        pass
    json.dump(doc, open(OUT, "w"), indent=1)
    return doc


def selfcheck():
    assert mi("2024-06-20T00:00:00.000") == 2024 * 12 + 5 and mi("2019-01") == 2019 * 12
    assert base("B44+") == "B44" and base("M14A+") == "M14" and base("M34A+") == "M34" and base("BX4A") == "BX4"
    assert base("SIM1C") == "SIM1" and base("Q15A") == "Q15" and base("S79+") == "S79"
    # pooled, not averaged: (hours, miles) rows 1h@10mi and 9h@45mi -> 55/10 = 5.5, mean of speeds would be 7.5
    assert abs(speed([(1, 10), (9, 45)]) - 5.5) < 1e-12 and speed([]) is None
    assert abs(pct(8, 8.8) - 10) < 1e-9
    # treated 8 -> 8.8 (+10%), control 10 -> 10.5 (+5%): DiD +5 points
    assert abs(did(8, 8.8, 10, 10.5) - 5) < 1e-9
    assert abs(did(8, 8, 10, 10.5) + 5) < 1e-9  # no treated change, control up 5% -> -5
    # bootstrap of a constant is that constant, with and without clusters
    r = random.Random(1)
    assert boot_mean([3.0] * 5, r) == (3.0, 3.0) and boot_mean([3.0] * 4, r, [1, 1, 2, 2]) == (3.0, 3.0)
    lo, hi = boot_mean([-1, 0, 1, 2, 3, 4], random.Random(SEED))
    assert lo < 1.5 < hi
    s = stats([{"did_pct": d, "activated": "x"} for d in (1, 2, 3, -1)], random.Random(2))
    assert s["n_routes"] == 4 and s["median_did_pct"] == 1.5 and s["mean_did_pct"] == 1.25
    assert s["share_improved_vs_control"] == 0.75
    assert in_redesign("Queens", [2024 * 12 + 9, 2025 * 12 + 6]) and not in_redesign("Queens", [2025 * 12 + 9, 2025 * 12 + 10])
    assert not in_redesign("Bronx", [2025 * 12 + 6])
    assert in_bronx_redesign("Bronx", [2021 * 12 + 11, 2022 * 12 + 9]) and not in_bronx_redesign("Bronx", [2022 * 12 + 8, 2022 * 12 + 9])
    assert not in_bronx_redesign("Queens", [2022 * 12 + 5])
    assert PAND[0] <= 2020 * 12 + 2 <= PAND[1] and not PAND[0] <= 2021 * 12 + 6 <= PAND[1]
    print("selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selfcheck":
        selfcheck()
    elif len(sys.argv) > 1 and sys.argv[1] != "--refresh":
        d = analyse(sys.argv[1])
        print(json.dumps(d["summary"], indent=1))
        print(len(d["routes"]), "routes;", len(d["excluded"]), "excluded")
    else:
        sys.exit("usage: ace.py YYYY-MM-DD | --selfcheck")
