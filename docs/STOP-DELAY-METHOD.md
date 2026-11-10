# Stop delay (plan goal 2): method

The plan's second goal: cut bus rider delay at stops to under two minutes beyond the scheduled wait on Priority Corridors.

## The metric
MTA Bus Customer Journey-Focused Metrics (data.ny.gov, dataset 8mkn-d32t), column `additional_bus_stop_time`.
The MTA defines it as "the average time that customers spend waiting at a stop beyond their scheduled wait time", in minutes, by route, month and period (Peak, Off-Peak).

## How we compute it
1. Take each corridor's route list from `site/data/corridors.json`. Where the MTA lists both a local route and its Select Bus sibling (the "+" spelling), both are counted, since they share the street. Anything not found is listed as unmatched (currently none).
2. For each month, pool the corridor's routes and both periods: sum of (customers x minutes) divided by sum of customers. We never average averages.
3. Baseline: July 2025 to June 2026 (our choice; the plan sets none).
4. Since release: July 2026 onward, compared with the same months a year earlier, so seasons line up.
5. A corridor is "under threshold" when its since-release figure is below 2.0 minutes.
6. We also pool all tracked corridors (each route once) and the whole city for context.

Run: `python3 pipeline/stop_delay.py 2026-11-09` (downloads to `data/raw/`, writes `site/data/stop_delay.json`). Test: `--selfcheck`.

## Limits
- The MTA publishes whole routes, not corridor stretches. These are routes that run on the corridor, so delay away from the corridor is included.
- A route on two corridors counts toward both.
- Corridors with no mapped routes show nulls.
- The plan does not say how it will measure the two minutes. This average over all riders is the closest public figure, not the plan's own yardstick.
- The metric is an average, so a stop can be far above two minutes while the route average is below.
- A few months of data after release is early and noisy.
