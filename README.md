# Lancer-Bot
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
