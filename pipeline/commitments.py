#!/usr/bin/env python3
"""Build site/data/commitments.json: every dated or counted promise in the July 2026 Next Stop plan,
with what open data can and cannot say. Baseline tracker, not a scorecard.

Usage: python3 pipeline/commitments.py [YYYY-MM-DD]   (fetch datasets, write commitments.json,
                                                         update commitments_history.json)
       python3 pipeline/commitments.py --selfcheck     (asserts on counting logic, no network)
Stdlib only. Method notes: docs/COMMITMENTS-METHOD.md
"""
import datetime, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site", "data", "commitments.json")
HIST = os.path.join(ROOT, "site", "data", "commitments_history.json")
PLAN = os.path.join(ROOT, "docs", "next-stop-plan.txt")
SINCE = "2026-07-01"
NY, NYC = "data.ny.gov", "data.cityofnewyork.us"
DS = {  # key -> (domain, id, name)
    "ace": (NY, "ki2b-sg5y", "MTA Bus Automated Camera Enforced Routes: Beginning October 2019"),
    "shelters": (NYC, "t4f2-8md7", "Bus Stop Shelters"),
    "seating": (NYC, "esmy-s8q5", "Seating Locations"),
    "rtpi": (NYC, "g9jx-npbk", "Real Time Passenger Information Sign Locations"),
    "lanes": (NYC, "ycrg-ses3", "Bus Lanes - Local Streets"),
}
D = "\u2014"  # the plan's own em dash, kept as an escape so no raw dash sits in this file

FAST, VALUED, COURTESY, QUALITY = "Fast, Reliable Buses", "Valued Bus Riders", "Culture of Courtesy and Respect", "Quality Transit for All"
LC, SO, ND, MS = "live count", "snapshot only", "no public data", "milestone"
# (id, section, label, quote, target value, unit, deadline, status, dataset key, note)
C = [
 ("priority_corridors", FAST, "Improvements along 50 Priority Corridors",
  "Joint NYC DOT and MTA improvements along 50 Priority Corridors.", 50, "corridors", None, ND, None,
  "No public list of which corridors have received improvements."),
 ("projects_2026", FAST, "Advance 28 ongoing street design projects",
  "In 2026, advance 28 ongoing street design projects and evaluate future service adjustments.", 28, "projects", "2026", ND, None,
  "Year list wording: \"Advance 28 ongoing projects with coordinated schedule adjustments.\" No public project tracker."),
 ("speed_goal", FAST, "Bus speeds up 20% on Priority Corridors",
  "20% increase in bus speeds on Priority Corridors, saving riders up to six minutes during their journey.", 20, "percent", None, ND, None,
  "No official figure: the city has not published the corridor segments or a baseline. Our own estimate from public segment speeds is on the Corridors page."),
 ("delay_goal", FAST, "Stop delay under two minutes on Priority Corridors",
  "Reduce bus rider delay at bus stops to less than two minutes beyond the scheduled wait time on Priority Corridors.", 2, "minutes", None, ND, None,
  "No official corridor figure. The MTA publishes extra wait at stops for whole routes only; our estimate from that is on the Corridors page."),
 ("queue_jumps", FAST, "125 queue jumps by 2030 (25 per year)",
  "Install 25 queue jump signals per year to reach 125 queue jumps by 2030.", 125, "queue jumps", "2030", ND, None,
  "Catalog searches on both portals found no queue jump dataset. Annual pace is 25. The plan says 43 queue jumps were installed before it."),
 ("tsp", FAST, "175 transit signal priority corridors by 2030",
  "Activate or improve transit signal priority along 35 corridors per year, with the goal of 175 corridors by 2030", 175, "corridors", "2030", ND, None,
  "Catalog searches on both portals found no signal priority dataset. Annual pace is 35."),
 ("new_buses", FAST, "Purchase 2,500 new buses",
  "Purchase 2,500 new buses" + D + " replacing over 40% of the existing fleet" + D + " as part of the 2025-2029 MTA Capital Program.", 2500, "buses", None, ND, None,
  "The plan ties this to the 2025-2029 Capital Program, not to a date, and elsewhere says \"approximately 2,500\". Only a fleet inventory from the 20-year needs assessment turned up; it does not record purchases."),
 ("all_door", FAST, "All-door boarding with full tap and ride",
  "Implement all-door boarding by 2027 with the complete transition to tap and ride.", None, None, "2027", MS, None,
  "A yes/no event; not measurable from open data."),
 ("bk_redesign", FAST, "Engage on three Central Brooklyn bus corridors",
  "Release next draft of the Brooklyn Bus Network Redesign and begin engagement for bus priority improvements on three key Central Brooklyn bus corridors.", 3, "corridors", "2026", MS, None,
  "Year list item for 2026; an engagement event, not measurable from data."),
 ("shelters_300", VALUED, "300 new bus shelters by 2028",
  "Install 300 new bus shelters by 2028.", 300, "new shelters", "2028", SO, "shelters",
  "The shelter list has no install date, so new shelters cannot be separated from existing ones. Today's total is saved so change can be shown later."),
 ("shelters_100", VALUED, "100 new bus shelters per year, starting in 2026",
  "Install 100 new bus shelters per year, starting in 2026.", 100, "new shelters per year", None, SO, "shelters",
  "Same dataset and limits as the 300 shelter commitment."),
 ("seating_875", VALUED, "Seating at 875 bus stops in 2026",
  "Install seating at 875 bus stops in 2026 to meet universal seating goal by 2035.", 875, "bus stops", "2026", SO, "seating",
  "The seating list has install dates but mixes bus stop seating with other sidewalk seating (category is empty), so dated rows would overcount. Total is saved for later comparison. Elsewhere the plan gives 875 stops as a yearly pace."),
 ("seating_universal", VALUED, "Universal seating at bus stops by 2035",
  "Achieve universal seating at bus stops.", None, None, "2035", ND, None,
  "Needs a list of all bus stops with and without seating."),
 ("trees_30", VALUED, "Plant 30 trees at bus stops in 2026",
  "Plant 30 trees at bus stops and pilot shelter design improvements for mitigating extreme heat in 2026.", 30, "trees", "2026", ND, None,
  "No dataset links tree plantings to bus stops. The 2015 street tree census is too old and not stop-specific."),
 ("trees_all", VALUED, "Tree planting at all feasible bus stops by 2035",
  "Complete tree planting at all feasible bus stops.", None, None, "2035", ND, None,
  "\"Feasible\" is not defined publicly and no stop-level tree data exists."),
 ("rtpi_2026", VALUED, "90 new real-time passenger information signs in 2026",
  "Install 90 new real-time passenger information displays in 2026", 90, "signs", "2026", SO, "rtpi",
  "The sign list carries completion dates, but none of them are recent, so it does not show new installs. Total is saved for later comparison."),
 ("rtpi_2030", VALUED, "2,900 new and improved RTPI signs by 2030",
  "install 2,900 new and technologically improved RTPI signs by 2030.", 2900, "signs", "2030", SO, "rtpi",
  "Same dataset and caveats as the 2026 sign commitment."),
 ("access_2026", VALUED, "Upgrade 35 inaccessible bus stops in 2026",
  "Upgrade 35 inaccessible bus stops in 2026", 35, "bus stops", "2026", ND, None,
  "No public list of stop accessibility status or upgrades."),
 ("access_2029", VALUED, "At least 50 accessible stop upgrades per year, 2027 to 2029",
  "scaling to at least 50 per year from 2027 to 2029", 50, "bus stops per year", "2029", ND, None,
  "Same gap as the 2026 accessibility commitment."),
 ("access_2030", VALUED, "At least 65 accessible stop upgrades per year after 2029",
  "and at least 65 per year thereafter.", 65, "bus stops per year", "2030", ND, None,
  "Same gap as the 2026 accessibility commitment. Year list places this at 2030."),
 ("capital_six", VALUED, "Capital projects along six priority corridors",
  "Advance capital projects along six priority corridors across the city", 6, "corridors", None, ND, None,
  "No public project list or schedule."),
 ("projects_2027", FAST, "Advance new bus priority projects in 2027",
  "Advance new bus priority projects on Priority Corridors.", None, None, "2027", ND, None,
  "Year list item for 2027. No public project tracker."),
 ("ace_2026", COURTESY, "Launch ACE on 25 routes in 2026",
  "Launch ACE on 25 routes.", 25, "routes", "2026", LC, "ace",
  "Counts routes whose first enforcement date falls in the calendar year."),
 ("ace_2027", COURTESY, "Add ACE to 25 additional routes in 2027",
  "Add ACE to 25 additional routes.", 25, "routes", "2027", LC, "ace",
  "Counts routes whose first enforcement date falls in the calendar year."),
 ("ace_50plus", COURTESY, "ACE on 50+ additional routes by 2027",
  "Expand Automated Camera Enforcement (ACE) to 50+ additional routes by 2027, prioritizing high-ridership and delay-prone corridors.", 50, "routes", "2027", LC, "ace",
  "The plan describes this as 25 additional routes a year in 2026 and 2027, so the count covers both calendar years."),
 ("stationary_cams", COURTESY, "200 new stationary bus lane cameras by 2027",
  "Install 200 new stationary bus lane cameras by 2027.", 200, "cameras", "2027", ND, None,
  "The ACE route list covers routes, not camera counts or locations. No camera dataset found."),
 ("nypd_routes", COURTESY, "NYPD daily enforcement on 20 routes",
  "Expand NYPD enforcement from 14 to 20 routes daily to be deployed where most needed.", 20, "routes", "2026", ND, None,
  "No public data on which routes NYPD patrols. Year list says 2026."),
 ("coverage_90", QUALITY, "90% of New Yorkers near a subway, rail, Select Bus, or rapid bus station",
  "Ensure 90% of New Yorkers live within a half-mile of a subway, rail, Select Bus, or new rapid bus station.", 90, "percent", None, ND, None,
  "No published measure; it would need station locations joined to population by the city."),
 ("flatbush", QUALITY, "Rapid bus route on Flatbush Avenue by 2030",
  "Implement a new, world-class rapid bus route on Flatbush Avenue by 2030.", None, None, "2030", MS, None,
  "A yes/no event; not measurable from open data."),
 ("rapid_four", QUALITY, "Public engagement on four rapid bus corridors in 2026",
  "Launch public engagement for the development of rapid bus service on four additional corridors in 2026.", 4, "corridors", "2026", MS, None,
  "An engagement event, not measurable from data."),
]

DATA_REQUESTS = [
 "Publish a dataset of Priority Corridors with the date each received improvements, so the 50 corridor commitment can be counted.",
 "Publish a project tracker listing the 28 ongoing street design projects and the six priority corridor capital projects with status dates.",
 "Publish Priority Corridor segment speeds against a pre-plan baseline, and rider delay at stops, to show the speed and delay goals.",
 "Publish a queue jump signal dataset with location and activation date.",
 "Publish a transit signal priority dataset listing corridors with activation or improvement dates.",
 "Publish the MTA bus fleet purchase and delivery record under the 2025-2029 Capital Program.",
 "Add an install date and a new-or-replacement flag to the Bus Stop Shelters dataset.",
 "Split bus stop seating from other sidewalk seating in the Seating Locations dataset, and publish a list of all bus stops with a seating flag.",
 "Publish bus stop tree plantings with stop identifiers and dates, and define which stops are feasible for planting.",
 "Keep the Real Time Passenger Information Sign Locations dataset current, with a completion date for each new sign.",
 "Publish a bus stop accessibility dataset with each stop's status and the date of any upgrade.",
 "Publish stationary bus lane camera locations with installation dates.",
 "Publish the routes covered by daily NYPD bus lane enforcement.",
 "Publish the station list and method behind the 90 percent half-mile access figure.",
]

CAVEATS = [
 "This is a baseline tracker. Statuses describe what open data can show, not how the city is doing.",
 "The plan was released in July 2026; counts since 2026-07-01 start from that baseline. Earlier 2026 activity is shown where a target is a calendar year.",
 "ACE route counts use each route's first date in the enforcement list; routes already under the earlier ABLE program also count at their first date.",
 "Quotes come from a text extraction of the plan PDF. The wording was checked against that text.",
 "The Bus Lanes - Local Streets dataset (ycrg-ses3) was checked; no commitment in the plan sets a bus lane target, so it is not used.",
 "Quote fragments for the accessibility and RTPI commitments are clauses of longer plan sentences; the full sentences are in the plan section.",
]


# ---------- pure helpers (covered by --selfcheck) ----------
def first_dates(rows):
    """[{route, implementation_date}] -> {route: earliest 'YYYY-MM-DD'}"""
    f = {}
    for r in rows:
        d = (r.get("implementation_date") or "")[:10]
        if r.get("route") and d and (r["route"] not in f or d < f[r["route"]]):
            f[r["route"]] = d
    return f


def count_first(first, start, end):
    """routes whose first date d satisfies start <= d <= end (ISO strings)"""
    return sum(1 for d in first.values() if start <= d <= end)


def is_stale(updated, since=SINCE):
    return updated < since


def merge_snapshot(hist, date, values):
    """replace the entry for date, never duplicate; keep sorted"""
    snaps = [s for s in hist.get("snapshots", []) if s["date"] != date]
    snaps.append({"date": date, "values": values})
    return {"snapshots": sorted(snaps, key=lambda s: s["date"])}


def selfcheck():
    check_quotes()
    rows = [{"route": "A", "implementation_date": "2026-02-16T00:00:00.000"},
            {"route": "A", "implementation_date": "2026-08-01T00:00:00.000"},  # later row, not first
            {"route": "B", "implementation_date": "2026-07-01T00:00:00.000"},
            {"route": "C", "implementation_date": "2025-12-31T00:00:00.000"},
            {"route": "D", "implementation_date": "2027-01-04T00:00:00.000"},
            {"route": None, "implementation_date": "2026-09-01T00:00:00.000"},
            {"route": "E", "implementation_date": None}]
    f = first_dates(rows)
    assert f == {"A": "2026-02-16", "B": "2026-07-01", "C": "2025-12-31", "D": "2027-01-04"}, f
    assert count_first(f, "2026-01-01", "2026-12-31") == 2  # A, B
    assert count_first(f, SINCE, "2027-12-31") == 2  # B, D (A first date is before the plan)
    assert count_first(f, "2028-01-01", "2028-12-31") == 0
    assert is_stale("2026-03-05") and not is_stale("2026-07-01")
    h = merge_snapshot({"snapshots": [{"date": "2026-11-09", "values": {"x": 1}}]}, "2026-11-09", {"x": 2})
    assert h == {"snapshots": [{"date": "2026-11-09", "values": {"x": 2}}]}
    h = merge_snapshot(h, "2026-11-01", {"x": 0})
    assert [s["date"] for s in h["snapshots"]] == ["2026-11-01", "2026-11-09"]
    assert len({c[0] for c in C}) == len(C)
    for c in C:
        assert c[7] in (LC, SO, ND, MS) and (c[7] not in (LC, SO)) == (c[8] is None), c[0]
    print("selfcheck ok")


# ---------- network ----------
def get(url):
    for attempt in range(4):  # the portals return occasional transient 5xx
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "nextstop-tracker"}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def meta(key):
    dom, i, _ = DS[key]
    v = get("https://%s/api/views/%s.json" % (dom, i))
    upd = datetime.datetime.fromtimestamp(v["rowsUpdatedAt"], datetime.timezone.utc).date().isoformat()
    return {"dataset_name": v["name"], "dataset_url": "https://%s/d/%s" % (dom, i), "dataset_updated": upd, "stale": is_stale(upd)}


def soql(key, q):
    dom, i, _ = DS[key]
    return get("https://%s/resource/%s.json?%s" % (dom, i, urllib.parse.urlencode({"$query": q})))


def normalize(s):
    return re.sub(r"\s+", " ", s)


def check_quotes():
    """every quote must appear word for word in the plan text; needs no network"""
    plan = normalize(open(PLAN, encoding="utf-8").read())
    plan = re.sub(r"\s*•\s*", " ", plan)
    for c in C:
        assert normalize(c[3]) in plan, "quote not found in plan: " + c[0]
    assert len({c[0] for c in C}) == len(C), "duplicate commitment id"


def main(today):
    check_quotes()
    metas = {k: meta(k) for k in DS}
    first = first_dates(soql("ace", "select route, implementation_date limit 50000"))
    totals = {k: int(soql(k, "select count(*)")[0]["count"]) for k in ("shelters", "seating", "rtpi")}
    ace = {"ace_2026": (count_first(first, "2026-01-01", "2026-12-31"), None),
           "ace_2027": (count_first(first, "2027-01-01", "2027-12-31"), None),
           "ace_50plus": (count_first(first, "2026-01-01", "2027-12-31"), "2026-01-01")}
    since_jul_2026 = count_first(first, SINCE, "2026-12-31")
    assert len(first) >= 50 and all(v > 0 for v in totals.values()), "a portal returned an empty or short response"
    out, snap = [], {}
    for cid, sec, label, quote, tv, tu, dl, status, key, note in C:
        m = None
        if key:
            m = dict(metas[key])
            m["as_of"] = m["dataset_updated"]
            if key == "ace":
                m["value"], m["since"] = ace[cid]
                m["unit"] = "routes first enforced"
                m["method"] = {"ace_2026": "Routes whose first enforcement date in the list falls in calendar 2026. %d of them started on or after %s, when the plan was released." % (since_jul_2026, SINCE),
                               "ace_2027": "Routes whose first enforcement date falls in calendar 2027. That year has not started.",
                               "ace_50plus": "Routes whose first enforcement date falls in calendar 2026 or 2027. %d of them started on or after %s, when the plan was released." % (since_jul_2026, SINCE)}[cid]
            else:
                m["value"], m["since"] = totals[key], None
                m["unit"] = "rows in current list"
                m["method"] = "Total rows in today's list; no usable install date, so no count since %s. Saved to history." % SINCE
                snap[cid] = m["value"]
            m = {k: m[k] for k in ("value", "unit", "as_of", "since", "method", "dataset_name", "dataset_url", "dataset_updated", "stale")}
        out.append({"id": cid, "section": sec, "label": label, "quote": quote,
                    "target": {"value": tv, "unit": tu} if tv is not None else None,
                    "deadline": dl, "status": status, "measured": m, "note": note})
    json.dump({"generated": today, "plan_released": "2026-07", "commitments": out,
               "data_requests": DATA_REQUESTS, "caveats": CAVEATS}, open(OUT, "w"), indent=1)
    try:
        hist = json.load(open(HIST))
    except FileNotFoundError:
        hist = {"snapshots": []}
    last = hist["snapshots"][-1] if hist.get("snapshots") else None
    if not last or last["values"] != snap or last["date"] == today:  # a new snapshot only when a count changes
        json.dump(merge_snapshot(hist, today, snap), open(HIST, "w"), indent=1)
    for k, m in metas.items():
        print(k, m["dataset_updated"], "STALE" if m["stale"] else "")
    print("ace first-date counts:", {k: v[0] for k, v in ace.items()}, "since-plan 2026:", since_jul_2026)
    print("snapshots:", snap)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--selfcheck" in sys.argv:
        selfcheck()
    else:
        main(args[0] if args else datetime.date.today().isoformat())
