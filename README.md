# Lancer-Bot

New here? Start with the **[Quick Start Guide and Definitions](docs/QUICK_START.md)**.

## Pass Type IQ

Every pass is labeled at two levels:

| Pass_Family | Pass_Type | Tag it when |
|---|---|---|
| Quick | Quick, RPO | QB doesn't fully set; ball out on rhythm (1-step, 3-step, gun catch-and-throw, RPO throw) |
| Dropback | Dropback | QB sets in the pocket and reads it out (5/7-step, gun dropback) |
| Play Action / Movement | PA Pocket, Boot, Naked, Sprint / Rollout | Run fake or a launch point outside the pocket |
| Screen | Screen | Bubble, tunnel, slip, RB/WR screens |
| Trick Play | Trick Play | Double pass, reverse pass, flea flicker, HB/WR pass (same list as the Trick Play Inventory) |

**Hudl setup:** add a `PASS TYPE` column (also read as `DROP`, `PASS FAMILY`). Values like
`Quick`, `Dropback`, `PA`, `Boot`, `Naked`, `Sprint`, `Screen`, `RPO` all work. Optional:
`LAUNCH` (L/R) for boot direction vs strength, and `PROTECTION`.

If `PASS TYPE` is blank, the type is inferred from `OFF PLAY` and marked
`Inferred from play name` in `Pass_Type_Source`. Staff protection numbers (e.g. 60s = quick)
go in `PASS_PROTECTION_SERIES` in `src/config.py`. Passes that can't be classified are
`Not Tagged` and left out of the math.

Pass type is post-snap, so it is only grouped by pre-snap looks (formation, down & distance,
hash, field zone, score state). Alerts use the same threshold / min plays / 10-pt lift rules
as run/pass alerts. They are checked game by game and top out at **Developing**; there is no
held-out model behind them yet, so none are stamped Verified.

The tab also shows results by pass type (comp %, yards, success, explosive, sacks, INTs),
the play action / movement rate after a successful vs unsuccessful run, and boot launch side
vs strength.

## Upload Check

Runs on every upload before any tendency math (`src/duplicate_check.py`).

| Problem | What it looks like | What the app does |
|---|---|---|
| Duplicate game | Same snaps uploaded twice, even under a different file name or with renumbered PLAY # | Keeps the first upload, drops the copy, and warns that one of the file names is likely the wrong export |
| Possible duplicate | 50%+ of one game's snaps match another upload | Keeps both and warns so the coach can check the files |
| Stacked games | PLAY # restarts at 1 inside one file (two games exported together) | Splits the file into `(game 1)`, `(game 2)`, ... and warns |
| Same file name twice | Two uploads named `vs LCC.xlsx` | Keeps both as `vs LCC` and `vs LCC (2)` so the duplicate check can compare them |

Snaps are matched on play content (ODK, quarter, down, distance, yard line, hash, formation,
play type, play name, direction, gain, result), not PLAY #. Hudl padding rows that carry only a
PLAY # are ignored. Findings show as a warning under the upload, in the Data Quality tab, and on
the Excel Read Me sheet.
