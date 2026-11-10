# Commitments tracker: method

This page tracks the dated or counted promises in "Next Stop: Fast Buses, Better Service" (NYC DOT and MTA, July 2026). It is a baseline, not a scorecard. It never says whether the city is ahead or behind.

## What counts as a commitment
Each numbered or dated promise in the plan's Goals and Commitments blocks and in its year-by-year timeline (docs/next-stop-plan.txt). The same promise in both places is merged into one item. Promises with no number or date are left out.
The quote is the plan's own words, checked against the plan text every time the script runs. A few quotes are one clause of a longer sentence, so the clause stands alone.

## Statuses (exactly four)
- live count: open data gives a number we can compare to the target.
- snapshot only: data exists but cannot show change since the plan yet. Today's total is saved to commitments_history.json so change can be shown later.
- no public data: no dataset measures it. data_requests names what the city would need to publish.
- milestone: a yes/no event with a date, not measurable from data.

## Datasets
- MTA Bus Automated Camera Enforced Routes (data.ny.gov ki2b-sg5y): route, program, implementation_date. Used for the three ACE commitments.
- Bus Stop Shelters (t4f2-8md7): current list, no install date.
- Seating Locations (esmy-s8q5): has install dates but does not separate bus stop seating from other sidewalk seating, so its dated rows are not used as a count.
- Real Time Passenger Information Sign Locations (g9jx-npbk): it has completion dates, but none are recent, so it does not show new installs. The page prints the date the dataset was last updated.
- Bus Lanes - Local Streets (ycrg-ses3): checked, unused (no bus lane target in the plan).
Each dataset's last-updated date comes from its Socrata metadata. A dataset last updated before 2026-07-01 is flagged stale.
Queue jumps, signal priority, accessible stops, stationary cameras, trees and fleet purchases were searched in the portal catalogs; nothing fit, so they are "no public data".

## ACE counting
A route counts at its earliest implementation_date in the list. We report calendar-year counts for the "25 routes in 2026" and "25 more in 2027" items, and the count first enforced since 2026-07-01 through 2027 for "50+ additional routes". The plan does not define the baseline for "additional", so that is one reading.

## Limits
Counts are from the lists as published on the run date, and lists can be revised. Targets with "per year" are shown as the yearly pace.

## Rebuild
python3 pipeline/commitments.py YYYY-MM-DD (needs network, stdlib only). python3 pipeline/commitments.py --selfcheck tests the counting logic.
