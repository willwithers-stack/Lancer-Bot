# FormationIQ — Quick Start Guide and Definitions

FormationIQ reads Hudl play-by-play exports and shows an opponent's run/pass and pass-type tendencies by formation and situation. Every number is counted straight from the Hudl tags. A tendency earns **Verified** only after it holds up on games it wasn't built from. Tendencies show what an offense has done, not what it will call.

---

## Quick Start

### 1. Export from Hudl

- **One file per game.** Export each game separately as Excel (.xlsx) or CSV.
- **Name the file after the game.** The file name becomes the game label, for example `Opponent-vs-Poway-10-16-2026.xlsx`.
- **The scouted team is ODK = O.** FormationIQ analyzes only the offensive snaps of the team tagged O.
- **Required columns:** DN, DIST, YARD LN, OFF FORM.
- **Recommended columns:**

| Column | Used for |
|---|---|
| PLAY # | Play order, drives, stacked-game check |
| ODK | Picks the scouted offense |
| QTR | Quarter table |
| HASH | Hash table, strength to field / boundary |
| OFF STR | Strength to field / boundary, run direction |
| OFF PLAY | Play names, pass type, run concepts, trick plays |
| PLAY TYPE | Run or Pass |
| GN/LS | Gain, success, explosives |
| RESULT | Completions, sacks, INTs, rebuilt score |
| MOTION DIR | Motion tables |
| BACKFIELD | QB alignment (Gun / Pistol / Under Center) |
| PLAY DIR | Run direction (post-snap) |
| PASS TYPE | Quick / Dropback / PA / Boot / Screen tags (otherwise read from OFF PLAY) |

### 2. Set up the sidebar

| Setting | Default | What it does |
|---|---|---|
| Opponent formation profile | Default | Picks the rules that group raw formation tags into families |
| High-alert threshold | 70% | Run or pass rate needed for a High Alert |
| Watch-alert threshold | 65% | Run or pass rate needed for a Watch Alert |
| Minimum plays per alert | 6 | Fewest snaps a look needs before it can alert |

Leave these at their defaults unless you have a reason to change them.

### 3. Upload and analyze

1. Drag in every game file at once (or use **+** to add more).
2. Click **Analyze**.
3. Read the green banner. It lists every game the app counted. Make sure each game appears once.
4. If a yellow **Upload check** warning appears, fix the files before you use the numbers (see Common Problems below).

### 4. Check the data before reading tendencies

1. **Score Timeline → Calculated Finals.** Compare each final with the real score. If one is off, a scoring play is mis-tagged in Hudl, and Score State for that game will be off too.
2. **Data Quality.** Look at Run/Pass = Unknown, Missing Formation and Missing Down. Large counts mean tagging gaps.

### 5. Read the results

1. **Executive Summary.** Formation Alerts and Composite Alerts, each with an Accuracy Check.
2. **Formation IQ, Down & Distance, Situation IQ, Motion IQ.** The full tables behind the alerts.
3. **Pass Type IQ.** The pass-type mix by formation and situation, and results by type.
4. **Explosive Plays, Trick Plays, First Drive IQ.** Play lists to cut up on film.
5. **Pivot Lab.** Build your own split: pick the rows and a metric (play count, average gain, success rate or explosive rate).

### 6. Export

Download the Excel workbook. Its Read Me sheet records the games, the settings and the upload check.

---

## Reading an Alert Row

| Formation | Plays | Games | Run | Pass | Tendency | Rate | Lift | Confidence | Held Up | Accuracy Check |
|---|---|---|---|---|---|---|---|---|---|---|
| TRIPS RIGHT | 30 | 7 | 2 | 28 | Pass | 93% | +37 pts | High Confidence | 6 of 6 games | ✓ Verified |

In plain words: the opponent passed on 28 of 30 snaps from TRIPS RIGHT across 7 games. That's 37 points above its normal 56% pass rate. The lean held in every game where TRIPS RIGHT showed up at least twice, and a model that never saw each game still predicted pass.

---

## Tabs

| Tab | What it shows |
|---|---|
| Executive Summary | Accuracy Promise, Formation Alerts, Composite Alerts (formation + down & distance) |
| First Drive IQ | Tendencies on the opening drive, by play number and formation (needs 3+ games) |
| Formation IQ | Run/pass by formation family, by exact tag, by family + modifier (Stack, Tight, Wing…), and by QB alignment. Also lists tags that matched no family. |
| Motion IQ | Motion vs. no motion, motion by formation, motion direction |
| Down & Distance | Run/pass by down and distance; pick a situation to see its formations, calls and plays |
| Situation IQ | Field zone, hash, score state, score state + down & distance, strength to field/boundary, quarter |
| Explosive Plays | Every snap that gained more than 20 yards |
| Trick Plays | Reverses, double passes, flea flickers, fake punts/FGs and other gadgets found in the play names |
| Score Timeline | Score rebuilt from TD/FG/PAT results, calculated finals, scoring events |
| Pivot Lab | Custom grouping by any pre-snap field |
| Data Quality | Row counts, missing tags, upload check findings, unused columns, clean play table download |
| Pass Type IQ | Pass-type mix, pass-type alerts, results by type, play action after the run, launch point vs. strength |

---

## Definitions

### Counting

| Term | Definition |
|---|---|
| **Snap / Plays** | A run or pass by the scouted offense (ODK = O). Kicks, punts, timeouts and dead-ball penalties with no play are removed. Snaps with Run/Pass = Unknown are left out of run/pass math. |
| **Games** | Number of games in which the look appeared at least once. |
| **Run / Pass** | Taken from PLAY TYPE when it says Run or Pass. Otherwise read from the play name and result (for example, "Sack" means a pass). Some staff calls are always runs (for example, Toss Crack). |
| **Rate** | The larger of the run rate and the pass rate for that look. |
| **Tendency** | Run or Pass, whichever the look leaned toward. |
| **Team Baseline** | The team's overall rate for that same call across all uploaded games. If the team passes 56%, the pass baseline is 56% and the run baseline is 44%. |
| **Lift** | Rate minus Team Baseline, in percentage points. It shows how far the look strays from the team's normal mix. A 58% pass look from a team that passes 56% has only 2 points of Lift. |

### Alerts

| Term | Definition |
|---|---|
| **High Alert** | At least 6 plays, Rate of 70% or higher, and Lift of 10+ points. |
| **Watch Alert** | At least 6 plays, Rate of 65–69%, and Lift of 10+ points. |
| **Composite Alert** | An alert on two or more conditions together, such as formation + down & distance. |
| **Pass Type Alert** | Same rules, applied to the pass-type mix (for example, EMPTY → Quick). |

### Confidence (sample size)

| Label | Rule |
|---|---|
| **High Confidence** | 15+ plays at 70%+ in 2+ games |
| **Usable Tendency** | 10+ plays at 65%+ in 2+ games |
| **Low Volume / Confirm on Film** | 6+ plays, or any lean seen in only one game |
| **No Clear Lean** | 6+ plays, but the rate is under the Watch threshold |
| **Insufficient Sample** | Fewer than 6 plays |

### Accuracy Check (does it hold up?)

| Label | Rule |
|---|---|
| **✓ Verified** | Passes both tests. (1) **Consistency:** the lean held in at least two-thirds of the games where the look showed up 2+ times. (2) **Held-out test:** a model trained without each game still predicted that lean for those snaps, at least 5 points past the team baseline. |
| **Developing** | Passed one of the two tests. |
| **Film Only** | Passed neither. Confirm on film before you plan around it. |
| **Pending** | Fewer than 3 games uploaded, so the held-out test can't run yet. |
| **Held Up** | "X of Y games": how many of the games where the look appeared 2+ times leaned the same way. |

The held-out test leaves out one game at a time. It uses only pre-snap information: formation family, QB alignment, personnel, motion, shift, down, distance, field zone, hash, strength to field/boundary and score state. Gain, result, play direction and pass type are never used to predict.

### Situations

| Term | Definition |
|---|---|
| **Down & Distance** | Short = 1–3 yards, Medium = 4–6, Long = 7–10, Extra = 11+. "1st & Long" covers a normal 1st & 10. |
| **Field Zone** (measured from the offense's own goal line) | Backed Up = own 1–10 · Own Territory = own 11–39 · Midfield = own 40 to opponent 40 · Plus Territory = opponent 39–21 · Red Zone = opponent 20–11 · Goal to Go = opponent 10–1 |
| **Yard Line (Hudl)** | Negative = own side (−35 = own 35); positive = opponent's side (25 = opponent's 25). |
| **Score State** | Score before the snap, from the scouted offense's side: Trailing 9+, Trailing 1–8, Tied, Leading 1–8, Leading 9+. In high school, 9+ points is a two-score game. Rebuilt from TD/FG/PAT/safety results unless the file has score columns. |
| **Hash** | L, M or R as tagged. |
| **Strength to Field / Boundary** | Built from hash + OFF STR when not tagged. Strength away from the near hash = to the field; toward it = to the boundary; middle of the field = Middle. |
| **QB Alignment** | Gun, Pistol or Under Center, read from BACKFIELD first, then the formation tag (EMPTY counts as Gun; I and PRO count as Under Center). |
| **Motion / Shift** | Any value in the MOTION or SHIFT column counts as yes (blank, No, None or 0 counts as no). |
| **First Drive** | The drive that contains the scouted offense's first snap of each game. |

### Formations

| Term | Definition |
|---|---|
| **Formation tag (raw / standardized)** | The exact OFF FORM text, cleaned up for case and spacing. |
| **Formation family** | A group of related tags (for example, DUBS, DOUBLES and 2X2 all go into DOUBLES). A tag goes to the first family it matches, so EMPTY TRIPS lands in EMPTY, not TRIPS. Tags that match no rule keep their own name. |
| **Opponent formation profile** | The set of family rules in use. Default works for most staffs. Mission Hills counts RIGHT and LEFT as TRIPS and keeps SPREAD separate from DOUBLES. |
| **Modifier** | Extra words kept next to the family, such as Stack, Tight, Wing, Slot, Nub. |

### Results (post-snap: described, never used to predict)

| Term | Definition |
|---|---|
| **Gain** | GN/LS yards. |
| **Success** | Gained at least 40% of the yards needed on 1st down, 60% on 2nd down, or 100% on 3rd or 4th down. |
| **Explosive** | A gain of **more than 20 yards** (21+). |
| **Penalty snap** | A snap with a penalty in RESULT. It's flagged and kept; review it on film. |

### Pass types

| Type | Tag it when |
|---|---|
| **Quick** | The QB doesn't fully set and the ball comes out on rhythm: 1-step, 3-step, gun catch-and-throw, RPO throws. |
| **Dropback** | The QB sets in the pocket and reads it out: 5/7-step or gun dropback. |
| **Play Action / Movement** | A run fake or a launch point outside the pocket: PA pocket, boot, naked, sprint/rollout. |
| **Screen** | Bubble, tunnel, slip, RB/WR screens. |
| **Trick Play** | Double pass, reverse pass, flea flicker, HB/WR pass. |
| **Pass Type Source** | **Tagged** (from a PASS TYPE column) or **Inferred from play name** (read from OFF PLAY). Passes that can't be classified are Not Tagged and left out. |
| **Play Action After the Run** | The pass-type mix split by whether the previous snap of the same drive was a successful run, an unsuccessful run, or a pass. |

### Upload Check

| Finding | What happens |
|---|---|
| **Duplicate game** | The same snaps were uploaded twice, even under a different file name or with renumbered plays. The first upload is kept and the copy is dropped. One of the file names is probably the wrong export. |
| **Possible duplicate** | Half or more of one game's snaps match another upload. Both are kept; check the files. |
| **Stacked games** | PLAY # restarts at 1 inside one file. The file is split into (game 1), (game 2), and so on. Check which part is the opponent you meant. |
| **Same file name twice** | Both are kept as "name" and "name (2)" so they can be compared. |

---

## Common Problems

| You see | Likely cause | Fix |
|---|---|---|
| A game appears twice in the banner | The same export was uploaded under two names | Read the Upload check warning; re-export the right game from Hudl |
| A "(game 1) / (game 2)" label | Two games exported into one file | Re-export each game on its own, or keep only the correct part |
| A calculated final doesn't match the real score | A TD/PAT/FG result is mis-tagged | Fix the RESULT tag in Hudl and re-export |
| Many Run/Pass = Unknown | PLAY TYPE left blank and play names unclear | Fill PLAY TYPE with Run or Pass |
| A formation shows up as its own family | The tag matches no family rule | Add it to a family in `src/config.py`, or add an opponent profile |
| Pass Type IQ is empty | No PASS TYPE column and no recognizable play names | Add a PASS TYPE column in Hudl |
| Everything says Pending | Fewer than 3 games uploaded | Upload 3 or more games |
