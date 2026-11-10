# Did bus-lane cameras make buses faster?

Script: `pipeline/ace.py` (Python standard library only). Output: `site/data/ace.json`.
Run: `python3 pipeline/ace.py 2026-11-09` (the argument is the generated date).
Check: `python3 pipeline/ace.py --selfcheck`.

## Data
- Enforced routes and start dates: data.ny.gov `ki2b-sg5y` (programs ABLE and ACE).
- Monthly bus speeds since 2019-01: data.ny.gov `cudb-vcni`. We use weekdays only (`day_type` 1) and
  add up both peak and off-peak rows.
- Speed is always total miles divided by total operating hours. We never average averages.

## Method
1. Match route names between the two datasets. M14+ maps to M14A+ and M14D+. Any route we cannot
   match or measure is excluded and listed with its reason in the output.
2. For each enforced route, take the matched month pairs: every month after activation (up to 11,
   the activation month is skipped) against the same calendar month one year earlier. This keeps
   seasons lined up. A route needs at least 6 pairs.
3. Control: routes in the same borough and trip type that were never camera enforced up to the end
   of the window (routes sharing a corridor name with an enforced route are also left out). Their
   miles and hours are pooled over the same months. We need at least 5 control routes.
4. Difference-in-differences = the route's percent speed change minus the control's percent change.
5. Routes whose months touch March 2020 to June 2021 are flagged, and results are given with and
   without them. In this run none qualified, so the two sets are the same.
   Queens routes get the same treatment for the Queens Bus Network Redesign (below).
6. Summary: median, mean, share of routes beating control, and a bootstrap 95% interval for the
   mean (10,000 resamples, fixed seed). A second interval resamples whole activation dates,
   because routes switched on together are not independent. This is not automatically the wider
   one (in the current run it is slightly narrower), so the page shows whichever of the two is wider.
   The summary is also given without the Queens routes that overlap the redesign.
7. Placebo: the same method with the start date moved a year earlier, using only months before
   the real start. It should be near zero. In the current run it is about +0.36 points, larger
   than the headline mean (about +0.09), so the method's own drift is bigger than the estimate
   and the result cannot be told from noise. The page reports this next to the headline.

## Limits (read these before quoting a number)
- Observational. Routes were not picked at random, and the MTA chose where to start.
- Cameras often arrive with new or repainted bus lanes. We cannot separate the two.
- Speed is measured over the whole route, but cameras cover only part of it, which dilutes effects.
- Control routes can drift for other reasons: road work, service changes, and congestion
  pricing (from 2025-01-05), which sits in the before months for the 2025 Manhattan routes.
- Almost all Select Bus Service routes are enforced, so SBS routes have no usable control and are
  excluded. Results speak for local and limited routes, not SBS.
- Routes with an earlier program (ABLE) and a later one (ACE) use the first start date, and the
  window stops before the second.
- The most recent activations have too few months of data yet. Routes starting in 2026-10 have none.
- Queens Bus Network Redesign. Queens local routes were renumbered and re-stopped in phases in
  mid 2025 (the feed's stop ids change in 2025-06 and 2025-09). Queens routes whose before or after
  months touch June to September 2025 are flagged `redesign_overlap` (this run: Q17, Q27, Q5, Q6,
  Q60, Q69). Q27's speed step up (9.1 to 9.8 mph) came in 2025-07, seven months before its cameras
  started in 2026-02. The plan itself credits the redesign with faster trips. The summary is given
  with and without these routes.
- Bronx Local Bus Network Redesign (late June 2022). Bronx routes whose before or after months straddle it
  are flagged `bronx_redesign_overlap` (this run: BX19, BX35) and named in the caveats. They are not removed.
- Shared lanes. Comparison routes can run in the same bus lanes as camera routes (for example Madison Av:
  M2 and M4 have cameras, M1 and M3 do not). Cameras ticket every vehicle in the lane, so those controls may
  also benefit, which would push the difference toward zero. The summary key
  `excluding_controls_sharing_a_corridor` reruns the analysis without controls that share a corridor with
  the camera route, using `corridors/map_*.json`. That list covers only the 50 Priority Corridors, so it
  catches some overlaps, not all.
- Many routes in one batch means the effective sample is smaller than the route count.
- A result near zero with a wide interval means "no detectable effect", not "no effect".
