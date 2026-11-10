# Data dictionary

This file describes the files the tracker publishes (`site/data/`) and the raw
inputs they are built from (`data/raw/`). The raw files are not committed
(see `.gitignore`); they are rebuilt by `pipeline/fetch.py`.

All speeds are average weekday bus speed in miles per hour, computed as:

    mph = sum(mile_trips) / (sum(minute_trips) / 60)

Speeds are never an average of per-segment speeds.

## site/data/corridors.json

Produced by `pipeline/build.py`.

| Field | Type | Meaning |
|---|---|---|
| `generated` | date `YYYY-MM-DD` | Day the file was built. |
| `inputs` | object | `corridor_files_sha256_12`: first 12 hex characters of the SHA-256 of each `corridors/map_*.json` used. If a map file changes, rebuild and compare. |
| `data_through` | `YYYY-MM` | Latest month in the source data. |
| `plan_released` | `YYYY-MM` | `2026-07`, the month of the plan ("Next Stop: Fast Buses, Better Service"; the plan's date line reads July 2026). |
| `baseline` | object | `from` and `to` (both `YYYY-MM`, `2025-07` and `2026-06`) and a `note`. The plan does not define a baseline period; this is our choice. |
| `target_pct` | number | `20`. The plan's goal: buses 20% faster on Priority Corridors. |
| `summary` | object | Totals across corridors (below). |
| `corridors` | array | One entry per corridor (below). |

### summary

| Field | Meaning |
|---|---|
| `corridors_total` | Number of corridors in the plan: `50`. |
| `corridors_tracked` | Corridors with status `mapped` or `partial` that have data. |
| `post_plan_months` | Months from `2026-07` onward that have data. |
| `tracked_baseline_mph` | Baseline speed pooled over all tracked corridors. |
| `tracked_latest_mph` | Latest-month speed pooled over all tracked corridors. One month, not seasonally comparable with the baseline. |
| `tracked_post_plan_mph` | Speed over the months since release, pooled over tracked corridors, on like-for-like segment-months. |
| `tracked_same_months_prior_year_mph` | The same calendar months one year earlier, same segment-months. |
| `tracked_post_plan_change_pct` | Percent change between the two. The site's headline figure. |
| `shared_segment_pairs` | Pairs of corridor ids that use some of the same segments. |

Pooled figures count each segment-month once even when two corridors share it, and skip corridors with no baseline.

### corridors[]

| Field | Type | Meaning |
|---|---|---|
| `id` | integer | Corridor number from `corridors/list.json` (1 to 50). |
| `name` | string | Corridor name as listed in the plan. |
| `borough` | string | `BX`, `MN`, `QN`, `BK`, `SI`, or `BK-QN` (the plan lists one corridor as Brooklyn and Queens). |
| `rapid_bus_corridor` | boolean | Whether `list.json` marks it as a rapid bus corridor. |
| `status` | string | `mapped`, `partial`, or `unmapped`. |
| `definition` | string | How the corridor's segments were chosen. |
| `notes` | string | Mapping notes. Present for every corridor. |
| `routes` | array of strings | Bus routes that run on the corridor. Empty for unmapped corridors. |
| `public_note` | string or null | Plain-English description of what was measured and what is missing, from `corridors/public.json`. This is what the site shows. `notes` and `definition` are working notes for reviewers. |
| `miles` | number or null | Segment miles measured: the miles of every mapped segment added together, so each route and direction counts separately. Not the corridor length. Null when unmapped. |
| `n_segments` | integer | Number of mapped segments (stop-id variants merged). |
| `basis` | string or null | `consistent` (segments with rows in every baseline month, carrying at least 70% of trips since 2025-07) or `all`. See Methods, "Which segments count". |
| `consistent_coverage_pct` | number or null | Share of trips on the consistent segments. |
| `n_consistent_segments`, `n_basis_segments` | integer | Segments that are consistent, and segments actually used (the basis). |
| `consistent_series` | array | Same shape as `series`, on the consistent segments only. |
| `shares_segments_with` | array | Ids of corridors that use some of the same segments. |
| `dropped_distance_unstable` | integer, optional | Segments left out because their recorded distance moved more than 3% inside the comparison window. |
| `no_recent_data` | boolean, optional | Mapped, but no weekday data in the baseline window. |
| `baseline_mph` | number or null | Average speed, `2025-07` to `2026-06`. Null when unmapped. |
| `target_mph` | number or null | `baseline_mph * 1.2`. |
| `latest` | object or null | Most recent month: `month`, `mph`, `yoy_pct` (change from the same month a year earlier, like for like), `vs_baseline_pct` (change from `baseline_mph`; one month against a 12 month average, so not seasonally comparable). Percent values are rounded numbers, not fractions. |
| `post_plan` | object or null | Months from `2026-07` onward: `mph` (pooled), `same_months_prior_year_mph` (the same calendar months one year earlier), `change_pct`, `months` (count of months). |
| `series` | array | Monthly points from `2025-07`, on the basis used: `month` (`YYYY-MM`), `mph`, `trips` (sum of `trips` for the month). |
| `segments` | array | Mapped segments (below). |

Unmapped corridors appear with `status` `unmapped`, their `notes`, and null
numeric fields.

### corridors[].segments[]

| Field | Meaning |
|---|---|
| `route_id` | Bus route, e.g. `B1`. |
| `direction` | Direction code from the source (`N`, `S`, `E`, `W`, and similar). |
| `from_stop`, `to_stop` | Timepoint stop names. |
| `from_lat`, `from_lon`, `to_lat`, `to_lon` | Stop coordinates. |
| `miles` | Average road distance of the segment. |
| `baseline_mph` | Segment speed, baseline period. |
| `latest_mph` | Segment speed, latest month. |
| `in_basis` | Whether the segment is used for the corridor figures. When false, the two speeds are null. |

## site/data/ace.json

Produced by `pipeline/ace.py`. Camera enforcement (ACE) before and after
comparison, using difference-in-differences: change on enforced routes minus
change on control routes in the same borough and trip type. Method notes are in
[ACE-METHOD.md](ACE-METHOD.md).

| Field | Meaning |
|---|---|
| `generated` | Day the file was built. |
| `summary` | Totals and intervals (below). |
| `routes` | One entry per analyzed route (below). |
| `excluded` | Routes not analyzed, each with a `reason` (for example, too few matched months). |
| `caveats` | Plain-language limits of the method. Read these before quoting results. |

### summary

Each block (`all_routes`, `excluding_pandemic_overlap`,
`excluding_pandemic_first_program_ACE`, `excluding_pandemic_first_program_ABLE`)
has:

| Field | Meaning |
|---|---|
| `n_routes` | Routes in the block. |
| `median_did_pct`, `mean_did_pct` | Median and mean difference-in-differences, in percentage points. |
| `mean_ci95_lo`, `mean_ci95_hi` | 95% percentile bootstrap interval for the mean, resampling routes. |
| `mean_ci95_clustered_by_activation_date_lo`, `..._hi` | Interval that resamples whole activation dates, because routes started together are not independent. It can be narrower or wider than the plain interval; the site shows whichever is wider. |
| `share_improved_vs_control` | Share of routes with a positive difference. |

Another block, `excluding_queens_redesign_overlap`, leaves out Queens routes whose
months touch June to September 2025 (count in `queens_redesign_overlap_routes`).
`placebo_fake_activation_12_months_early` has the same fields, computed with the
start date moved a year earlier and only pre-camera months. A mean far from 0
means the method drifts on its own; in this run it is larger than the real mean.

Top-level summary fields: `pandemic_overlap_routes` (count of routes flagged
for the March 2020 to June 2021 window), `bootstrap` (10,000 resamples, seed
20261109, percentile interval), and `unit` (`did_pct` is percentage points).

### routes[]

| Field | Meaning |
|---|---|
| `route` | Route name (for example `B11`). |
| `program` | Camera program at activation: `ACE` or `ABLE`. |
| `activated` | First camera date, `YYYY-MM-DD`. |
| `before_mph`, `after_mph` | Pooled speed in matched months before and after activation. |
| `change_pct` | Percent change for the treated route. |
| `control_change_pct` | Percent change for its control routes. |
| `did_pct` | `change_pct` minus `control_change_pct`, percentage points. |
| `months_after` | Matched months after activation. |
| `pandemic_overlap` | Whether the route's window overlaps March 2020 to June 2021. |
| `redesign_overlap` | Queens route whose before or after months include June to September 2025 (Queens Bus Network Redesign). |
| `borough`, `trip_type` | Matching keys for the control pool. |
| `n_control_routes` | Number of control routes used. |
| `second_camera_program` | Start date (`YYYY-MM-DD`) of a second camera program on the route, else null. The after window stops before it. |

## data/raw/segment_monthly.csv

Written by `pipeline/fetch.py` from NY Open Data dataset `kufs-yh3x` (MTA Bus
Route Segment Speeds). One row per segment per month, weekdays only (Saturday
and Sunday excluded in the query).

| Column | Meaning |
|---|---|
| `year`, `month` | Calendar month. |
| `route_id` | Bus route. |
| `direction` | Direction code. |
| `timepoint_stop_id` | Stop at the start of the segment. |
| `next_timepoint_stop_id` | Stop at the end of the segment. |
| `mile_trips` | Sum of road distance times trip count. |
| `minute_trips` | Sum of average travel time (minutes) times trip count. |
| `trips` | Sum of trip counts. |

## data/raw/segment_catalog.csv

Written by `pipeline/fetch.py`. One row per segment, with names and
coordinates.

| Column | Meaning |
|---|---|
| `route_id`, `direction`, `timepoint_stop_id`, `next_timepoint_stop_id` | Segment key, as above. |
| `borough` | Borough from the source. |
| `route_type` | Service type from the source (for example `Local`, `School`). The monthly file keeps only `Local`, `Limited` and `SBS`. |
| `from_stop`, `to_stop` | Stop names. Taken as the maximum name in the group, so one name is kept per segment. |
| `from_lat`, `from_lon`, `to_lat`, `to_lon` | Stop coordinates (maximum value in the group). |
| `miles` | Average road distance of the segment. |

## Known gaps

- `corridors/map_*.json` carry working notes (`notes`, `definition`, `extent`) that are
  not written for the public. The site shows `public_note` from `corridors/public.json`.
- The exact formulas for `yoy_pct`, `vs_baseline_pct`, and `change_pct` live
  in `pipeline/build.py`. The definitions above follow the contract wording.
