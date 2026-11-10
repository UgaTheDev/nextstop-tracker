# NYC Next Stop Bus Tracker

An independent, open tracker for the bus speed goals in NYC's
"Next Stop: Fast Buses, Better Service" plan (July 2026).

This is an independent project by Kush Zingade. It is not affiliated with
NYC DOT or the MTA, and it does not speak for either agency.

## What it is

The plan promises buses 20% faster on 50 Priority Corridors. This project
measures average weekday bus speed on those corridors from public MTA data,
so anyone can see where things stand. It also includes a before-and-after
look at camera enforcement of bus lanes (ACE).

## Why

The plan says the agencies will
"include a real-time performance dashboard with public-facing reporting that
tracks progress against the goals outlined in this report"
(docs/next-stop-plan.txt). That dashboard has not been published. This
tracker is an independent baseline until it is.

## What it shows

- **Corridors:** for each of the 50 Priority Corridors, the average weekday
  bus speed over the 12 months before the plan, the target (20% higher), the
  latest month, and the change since the plan was released.
- **ACE:** how bus speeds changed on routes with camera enforcement compared
  with similar routes without it.

"mph" figures are average weekday bus speed: miles of bus travel divided by
hours spent on the bus, for the segments we track.

Most street projects are not built yet, so flat speeds are expected. A
corridor that has not changed yet is a starting point, not a failure.

## Run it locally

Needs Python 3 and an internet connection. No third-party packages.

```
python3 pipeline/fetch.py && python3 pipeline/build.py && python3 pipeline/ace.py $(date +%F) --refresh
cd site && python3 -m http.server
```

Then open http://localhost:8000.

`pipeline/ace.py` reuses data already in `data/raw/`; `--refresh` downloads it again.
Rebuild with `pipeline/build.py` after any change to `corridors/`: the output records a hash
of each map file under `inputs`.

## How corridors are defined

- `corridors/list.json` holds the 50 corridor names, boroughs, and whether
  each is a rapid bus corridor, as listed in the plan.
- `corridors/map_*.json` (one per borough group) holds the bus segments that
  make up each corridor. Each segment is a stretch between two consecutive
  timepoint stops on one route and direction.
- Each corridor has a `status`: `mapped`, `partial`, or `unmapped`. Unmapped
  corridors are listed with a reason and no numbers. `corridors/public.json` holds
  the plain-English note shown for each corridor; the map files keep working notes.

To challenge a definition, find the corridor in its `map_*.json` file and
check its segments. If a segment is wrong or a corridor is missing segments,
[open an issue](https://github.com/UgaTheDev/nextstop-tracker/issues/new) with the corridor, the stop IDs
and a short reason.

## Method choices

- **Baseline:** the plan does not define a baseline period. We use the 12
  months from July 2025 to June 2026, the year before the plan.
- **Target:** baseline speed times 1.2.
- **Speed:** total miles divided by total hours, weekdays only. Speeds are
  never averaged segment by segment.

## Limits

- Segments run between timepoint stops, so they may not cover every block of
  a corridor.
- Source data arrives with a lag. The latest month shown is the latest one
  the source has published.
- ACE is observational. Cameras were not assigned at random, and bus-lane
  work often came with them. Read the caveats in `site/data/ace.json`.
- Corridors that are not mapped show no numbers. "Partly mapped" corridors do
  show numbers, but only for the stretch we could match.
- Speeds use the segments that report in every baseline month, and segments
  whose recorded distance changes are left out. See the Methods page.

## Data sources

- MTA Bus Route Segment Speeds, NY Open Data (dataset `kufs-yh3x`), fetched
  by `pipeline/fetch.py`.
- MTA bus-lane camera enforcement and bus speed datasets on NY Open Data,
  used by `pipeline/ace.py`.
- The plan itself: `docs/next-stop-plan.txt`.
- Column definitions: [docs/DATA.md](docs/DATA.md). License: MIT ([LICENSE](LICENSE)).
