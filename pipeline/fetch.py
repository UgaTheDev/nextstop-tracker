#!/usr/bin/env python3
"""Download weekday monthly aggregates of MTA Bus Route Segment Speeds (data.ny.gov kufs-yh3x).

Writes data/raw/segment_monthly.csv (one row per segment per month) and
data/raw/segment_catalog.csv (one row per segment, with stop names and coordinates).
A segment is the stretch between two consecutive timepoint stops on one route and direction.
Stdlib only. Usage: python3 pipeline/fetch.py
"""
import csv, json, pathlib, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://data.ny.gov/resource/kufs-yh3x.json"
RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
KEY = "route_id,direction,timepoint_stop_id,next_timepoint_stop_id"
WEEKDAY = "day_of_week not in('Saturday','Sunday') AND route_type in('Local','Limited','SBS')"  # drops school and express trips
PAGE = 50000


def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise


def pages(params):
    out, offset = [], 0
    while True:
        rows = get({**params, "$limit": PAGE, "$offset": offset})
        out += rows
        if len(rows) < PAGE:
            return out
        offset += PAGE


def month_rows(ym):
    y, m = ym
    return pages({
        "$select": f"year,month,{KEY},sum(road_distance*bus_trip_count) as mile_trips,"
                   "sum(average_travel_time*bus_trip_count) as minute_trips,sum(bus_trip_count) as trips",
        "$where": f"year={y} AND month={m} AND {WEEKDAY}",
        "$group": f"year,month,{KEY}", "$order": KEY,
    })


def write(name, rows):
    cols = list(rows[0].keys())
    with open(RAW / name, "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    print(name, len(rows), "rows")


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    months = sorted((int(r["year"]), int(r["month"])) for r in get({"$select": "year,month", "$group": "year,month"}))
    print("months:", months[0], "to", months[-1])
    with ThreadPoolExecutor(4) as ex:
        monthly = [r for rows in ex.map(month_rows, months) for r in rows]
    write("segment_monthly.csv", monthly)
    catalog = pages({
        "$select": f"{KEY},borough,route_type,max(timepoint_stop_name) as from_stop,max(next_timepoint_stop_name) as to_stop,"
                   "max(timepoint_stop_latitude) as from_lat,max(timepoint_stop_longitude) as from_lon,"
                   "max(next_timepoint_stop_latitude) as to_lat,max(next_timepoint_stop_longitude) as to_lon,"
                   "avg(road_distance) as miles",
        "$group": f"{KEY},borough,route_type", "$order": KEY,
    })
    write("segment_catalog.csv", catalog)
    # provenance: build.py records this under "inputs" so a stale or differently filtered download is visible
    json.dump({"filter": WEEKDAY},
              open(RAW / "fetch_meta.json", "w"))
