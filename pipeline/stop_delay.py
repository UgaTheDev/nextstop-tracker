#!/usr/bin/env python3
"""Goal 2 of the Next Stop plan: additional bus stop time (min) on routes that run on tracked corridors.
Usage: python3 pipeline/stop_delay.py [YYYY-MM-DD]   |   --selfcheck
stdlib only. Raw download cached in data/raw/stop_delay_raw.json."""
import json, sys, os, time, urllib.request, urllib.parse, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data/raw/stop_delay_raw.json")
META = os.path.join(ROOT, "data/raw/stop_delay_meta.json")
URL = "https://data.ny.gov/resource/8mkn-d32t.json"
META_URL = "https://data.ny.gov/api/views/8mkn-d32t.json"
THRESH = 2.0
B_FROM, B_TO, RELEASE = "2025-07", "2026-06", "2026-07"

def fetch(refresh=True):
    os.makedirs(os.path.dirname(RAW), exist_ok=True)
    if not refresh and os.path.exists(RAW):
        return json.load(open(RAW))
    rows, off, page = [], 0, 50000
    while True:
        q = urllib.parse.urlencode({"$limit": page, "$offset": off, "$order": "month,route_id,period,trip_type"})
        for attempt in range(4):  # the portal returns occasional transient errors
            try: b = json.load(urllib.request.urlopen(f"{URL}?{q}", timeout=120)); break
            except OSError:
                if attempt == 3: raise
                time.sleep(5 * (attempt + 1))
        rows += b; off += page
        if len(b) < page: break
    json.dump(rows, open(RAW, "w"))
    with open(META, "wb") as f: f.write(urllib.request.urlopen(META_URL, timeout=60).read())
    return rows

def prep(rows):
    """-> {(month 'YYYY-MM', route): [sum(w*x), sum(w)]}, pooling periods and trip types."""
    out = {}
    for r in rows:
        try: w = float(r["number_of_customers"]); x = float(r["additional_bus_stop_time"])
        except (KeyError, TypeError, ValueError): continue
        a = out.setdefault((r["month"][:7], r["route_id"].strip().upper()), [0.0, 0.0])
        a[0] += w * x; a[1] += w
    return out

def pool(data, routes, months):
    s = w = 0.0
    for (m, r), (sx, sw) in data.items():
        if m in months and (routes is None or r in routes): s += sx; w += sw
    return (s / w, w) if w else (None, 0.0)

SERIES_FROM = "2024-07"  # published series starts here: baseline plus the year-earlier months

def r2(v): return None if v is None else round(v, 2)

def stats(data, routes, all_months):
    """Rider-weighted stats for a route set. Never averages averages: sums riders*minutes then divides."""
    base = {m for m in all_months if B_FROM <= m <= B_TO}
    since = sorted(m for m in all_months if m >= RELEASE)
    prior = {f"{int(m[:4]) - 1}{m[4:]}" for m in since}
    series = []
    for m in sorted(all_months):
        v, w = pool(data, routes, {m})
        if v is not None: series.append({"month": m, "min": r2(v), "riders": round(w)})
    have = {s["month"] for s in series}
    since_m = [m for m in since if m in have and f"{int(m[:4]) - 1}{m[4:]}" in have]  # only months with a prior-year pair
    sv = pool(data, routes, set(since_m))[0]
    pv = pool(data, routes, {f"{int(m[:4]) - 1}{m[4:]}" for m in since_m})[0]
    last = series[-1] if series else None
    return {"baseline_min": r2(pool(data, routes, base)[0]),
            "since_release": {"min": r2(sv), "same_months_prior_year_min": r2(pv),
                              "change_min": round(r2(sv) - r2(pv), 2) if sv is not None and pv is not None else None,
                              "months": since_m},
            "latest": {"month": last["month"], "min": last["min"]} if last else {"month": None, "min": None},
            "under_threshold": None if sv is None else sv < THRESH,
            "under_threshold_prior_year": None if pv is None else pv < THRESH,
            "has_since": sv is not None,
            "series": [s for s in series if s["month"] >= SERIES_FROM]}

def match_routes(want, have):
    used, miss = [], []
    for r in want:
        u = r.strip().upper()
        # a local route and its Select Bus sibling ("+") share the street, so take every spelling the MTA lists
        c = [x for x in (u.rstrip("+"), u.rstrip("+") + "+") if x in have]
        (used.extend(c) if c else miss.append(r))
    return sorted(set(used)), miss

def build(rows, corridors, generated):
    data = prep(rows)
    months = {m for m, _ in data}
    have = {r for _, r in data}
    out_c, all_used = [], set()
    for c in corridors:
        used, miss = match_routes(c.get("routes") or [], have)
        all_used |= set(used)
        base = stats(data, set(used), months) if used else {
            "baseline_min": None, "since_release": {"min": None, "same_months_prior_year_min": None, "change_min": None, "months": []},
            "latest": {"month": None, "min": None}, "under_threshold": None, "under_threshold_prior_year": None, "has_since": False, "series": []}
        out_c.append({"id": c["id"], "name": c["name"], "routes_used": used, "routes_unmatched": miss, **base})
    tracked = stats(data, all_used, months)
    city = stats(data, None, months)
    under = sum(1 for c in out_c if c["under_threshold"] is True)
    under_prior = sum(1 for c in out_c if c["under_threshold_prior_year"] is True)
    since_m = set(tracked["since_release"]["months"])
    n_current = sum(1 for r in all_used if pool(data, {r}, since_m)[1] > 0)  # routes with data since release
    n_with = sum(1 for c in out_c if c["under_threshold"] is not None)
    unm = sorted({r for c in out_c for r in c["routes_unmatched"]})
    summary = {"tracked": {"routes": sorted(all_used), "routes_with_data_since_release": n_current, **{k: tracked[k] for k in ("baseline_min", "since_release", "latest")}},
               "citywide": {k: city[k] for k in ("baseline_min", "since_release", "latest")},
               "corridors_with_data": n_with, "corridors_under_threshold": under, "corridors_under_threshold_prior_year": under_prior, "corridors_over_threshold": n_with - under,
               "routes_unmatched": unm}
    return {"generated": generated, "data_through": max(months),
            "threshold_min": THRESH,
            "metric": {"name": "Additional Bus Stop Time (minutes)",
                       "definition": "Additional Bus Stop Time is the average time that customers spend waiting at a stop beyond their scheduled wait time. (MTA dataset description; column: \"The average additional bus stop time (in minutes) for each bus route, monthly, during peak and off-peak hours.\")",
                       "source_url": "https://data.ny.gov/Transportation/MTA-Bus-Customer-Journey-Focused-Metrics-Beginning-/8mkn-d32t"},
            "baseline": {"from": B_FROM, "to": B_TO},
            "summary": summary, "corridors": out_c,
            "caveats": [
                "The MTA publishes this metric for whole routes, not for the corridor stretch. Each figure is for routes that run on the corridor, including their parts off the corridor.",
                "A route that runs on two corridors counts toward both. The tracked-corridor total counts each route once.",
                "Corridor figures are rider-weighted (monthly customers) across routes and across peak and off-peak; no averages of averages.",
                "Baseline is our choice (2025-07 to 2026-06); the plan sets none. Since-release means 2026-07 onward, compared with the same months a year earlier.",
                "The plan says 'less than two minutes beyond the scheduled wait'. The MTA metric is an average over all riders; the plan does not define its measure, so this is a proxy.",
                "Unmapped corridors have no route list and show nulls. Routes not found in the MTA data are listed per corridor.",
                "Where the MTA lists both a local route and its Select Bus sibling, both are counted, since they share the street.",
                "Queens bus routes were redesigned in mid 2025, so on Queens corridors the year-earlier months are not like for like.",
            ]}

def selfcheck():
    def row(m, r, p, c, x): return {"month": m + "-01T00:00:00.000", "route_id": r, "period": p, "number_of_customers": str(c), "additional_bus_stop_time": str(x)}
    rows = [row("2025-07", "A", "Peak", 100, 1.0), row("2025-07", "A", "Off-Peak", 300, 3.0),   # pooled: (100+900)/400 = 2.5
            row("2025-07", "B+", "Peak", 100, 5.0),                                           # B spelled B on corridor, SBS "+" in MTA
            row("2026-07", "A", "Peak", 100, 1.0), row("2026-07", "A", "Off-Peak", 100, 2.0),   # 1.5
            row("2026-08", "A", "Peak", 300, 1.0),
            row("2026-07", "Z", "Peak", 1, 9.0)]
    cor = [{"id": 1, "name": "x", "routes": ["A", "B", "Q"]}, {"id": 2, "name": "none", "routes": []}]
    o = build(rows, cor, "t")
    c = o["corridors"][0]
    assert c["routes_used"] == ["A", "B+"] and c["routes_unmatched"] == ["Q"], c
    assert c["baseline_min"] == round((100 + 900 + 500) / 500, 2) == 3.0                      # rider-weighted, not (2.5+5)/2
    sr = c["since_release"]
    assert sr["months"] == ["2026-07"] and sr["min"] == 1.5     # 2026-08 dropped: no 2025-08 to pair with
    assert sr["same_months_prior_year_min"] == 3.0 and sr["change_min"] == -1.5
    assert c["under_threshold"] is True and c["latest"] == {"month": "2026-08", "min": 1.0}
    assert o["corridors"][1]["under_threshold"] is None and o["corridors"][1]["baseline_min"] is None
    assert o["summary"]["citywide"]["since_release"]["min"] == round((100 + 200 + 9) / 201, 2)
    print("selfcheck ok")

if __name__ == "__main__":
    if "--selfcheck" in sys.argv: selfcheck(); sys.exit()
    gen = next((a for a in sys.argv[1:] if not a.startswith("-")), datetime.date.today().isoformat())
    rows = fetch(refresh="--cached" not in sys.argv)
    cor = json.load(open(os.path.join(ROOT, "site/data/corridors.json")))["corridors"]
    out = build(rows, cor, gen)
    json.dump(out, open(os.path.join(ROOT, "site/data/stop_delay.json"), "w"), indent=1)
    s = out["summary"]
    print("through", out["data_through"], "| tracked", s["tracked"]["baseline_min"], s["tracked"]["since_release"], "| city", s["citywide"]["baseline_min"], s["citywide"]["since_release"])
    print("under", s["corridors_under_threshold"], "of", s["corridors_with_data"], "| unmatched", s["routes_unmatched"])
