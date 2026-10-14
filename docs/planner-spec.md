# Full-fuel expectimax planner specification (v4 “master stroke”)

**Spec · 14 October 2026 · targets `bots/main/src` on cambc 2.1.5 (`cambc.toml` pins `sdk_version = "2.1.5"`)**

**Labels:** **Verified** = read in SDK sources, handbook chapters, or measured in this repository's orb (probe bot, two-point fuel deltas on `maps/collision.map26a`); **Spec** = a decision this document mandates; **Initial value** = a tunable constant with a stated calibration path. Nothing here is engine-tested beyond the cited probe; every stage ships behind a regression gate (§9).

## 0. Why: spend the whole budget, never forfeit a turn

The ladder is full of heuristic bots built from the same handbook. Our differentiator is not a cleverer heuristic — it is **actually consuming the ~2.5M fuel units per Python turn on search** while guaranteeing we never suspend. Two measured facts motivate this:

- **The incumbent already suspends.** A 500-round local run (`main` vs `starter-python`, `collision`) logs per-champion `min_fuel` as low as 16 and **17–48 suspensions per champion per 500 rounds** (one champion showed `min_fuel=1,467,074` with 19 suspensions). Suspension is silent: the turn's remaining actions are forfeited and the bot resumes mid-loop next round on stale observations.
- **The current decision policy is one-ply.** `bot.py` scores routes (`farm_camps`), picks targets by fixed priority keys (`combat_turn`), and banks on thresholds. It never compares a *sequence* of our turns against *predicted* enemy responses; `combat.py`'s `exchange` is the only lookahead (two rounds, no movement tree).

The planner is a model-predictive expectimax over 2–4 rounds that **replaces the heuristic decision chain on actionable turns** (channel turns get a dedicated mini-search), with the heuristic chain preserved verbatim as the guaranteed fallback tier.

## 1. Fuel model (ground truth)

### 1.1 Budgets — Verified

| Turn kind | Budget | Notes |
| --- | ---: | --- |
| Normal Python turn | **2,500,000** | Fuel chapter: 25× the C++/Rust 100k. The homepage FAQ still says 20×; **measurement confirms 2.5M** (first instruction sees ≈2,485,683, so ≈14.3k/turn interpreter overhead). |
| First draft turn | 25,000,000 | 10× allowance, first draft turn only. |
| First play turn | 5,000,000 | 2×; ≈452.8k burns before the first user instruction (imports + `Bot.__init__` cache warming, including `camp_groups()` at 352k) → ≈4.53M usable. |
| Runner / ladder | Same defaults | `runner/run_matches.py` passes no `--fuel` override; ladder assumed to use defaults. |

Fuel is deterministic instruction-like accounting (wasmtime), **not wall time**; unused fuel does not carry over; there is no documented wall-clock turn limit — **running out of fuel is the only way to “time out.”**

### 1.2 Exhaustion penalty — Verified (fuel + draft chapters)

- **Play turns:** execution is suspended immediately; the next bot in turn order runs; **next round our bot resumes at the same instruction**. Practical effect: all remaining actions this turn are forfeited, and resumed code acts on one-round-stale observations. The probe empirically confirmed silent mid-loop suspension/resume.
- **Draft turns:** exhaustion (or crash/yield) results in **random remaining selections**.

### 1.3 Measured per-call costs (Python SDK, cambc 2.1.5, `collision.map26a`) — Verified

| Operation | Fuel | Planner consequence |
| --- | ---: | --- |
| `fuel_remaining()` | 3,165 | Sample per phase / every few nodes, not per iteration |
| `Bitboard()` | 1,677 | |
| bitboard `or` / `and` | 3,515 | Bulk masking is cheap |
| bitboard `invert` | ~1,630 | |
| `copy()` (bitboard) | 2,990 | Data clone only — usable, sparingly |
| `count()` | 2,275 | |
| `is_set(tile)` | 1,744 | **The hot-path tile query** |
| `positions()` on an r8 mask | ~66,000 (~266/tile) | **Avoid in hot paths** |
| `shift_right(1)` | 8,966 | |
| `reachable_tiles` (d2) | 3,866 | Area-scaled |
| `draw_chebyshev` (r8) | 3,848 | |
| `shadow_cast` (r8) | 5,726 | Fails “Invalid metadata…” if the viewer tile is set — clear the center first. Avoid; use `hypothetical_vision` |
| `DistanceField()` | 6,611 | |
| `field.compute` (full map) | 64,481 | Area-scaled; precompute ≤4/turn |
| `field.compute_to` (r8 dest) | 25,175 | Area-scaled |
| `field.get` | 1,657 | **The sim's movement primitive** |
| `field.copy` | 12,010 | |
| `field.export_linear` / bit `export_linear` | 19,683 / 3,935 | |
| `vision.visible_tiles` / `camp_tiles` | 3,935 | |
| `vision.champion_tiles` | 8,945 | |
| `vision.champions(ENEMY)` | 11,344 | Once per turn, snapshot into sim |
| `hypothetical_vision` (r8) | 8,107 | Finalist checks only, not per node |
| `me.position` / `me.health` / `me.state` | 2,894 / 2,786 / 4,805 | Snapshot once; never poll per node |
| `ability.cooldown` | 4,035 | Snapshot once |
| `me.attack_tiles` | 9,298 | Once per turn |
| `game_map.camp_groups` | 352,380 | Already cached in `Bot.__init__` |
| `game_map.walls` | 1,744 | |
| `Vec2` add | 2,753 | Prefer plain int tuples in sim |
| 4-key dict clone | 6,571 | **No per-node dict clones** |
| Plain Python loop iteration | ~553 | **The governing constraint** |

**Caveats.** Area-scaled costs (`compute`, `compute_to`, `reachable_tiles`) were measured on one map; maps range 30×30–100×100. The S0 harness must print `Bitboard.width()`/height and re-measure per map; per-map constants are cached on the champion `Bot` during turn 1 (covered by the 10×/2× first-turn allowance). All constants are re-verified whenever `cambc.toml` bumps the SDK version.

### 1.4 Affordability arithmetic — Verified arithmetic from measured costs

- A pure-Python loop that did nothing else could run ≈ **4,500 iterations** per normal turn (2.485M ÷ 553). A naive per-tile simulator is therefore impossible; the planner must be **bitboard/field-centric with O(few) Python ops per node**.
- Target node costs (design obligations, self-calibrated at runtime):
  - interior node (apply + journal + revert): **≤ 10k fuel**;
  - leaf (position/health/gem arithmetic over journaled state + ≤10 native `is_set`/`field.get` calls): **≤ 20k fuel**.
- With the default search cap of ~1.2M (§2): **≈ 20 fully evaluated leaves at depth 2, ≈ 60 at depth 3, ≈ 75 with PV-deepening to 4** — roughly 100–150 simulated round-transitions and ~2,000–2,700 loop-equivalents per turn. This is the entire compute envelope; every design choice below exists to fit inside it.

## 2. Fuel ledger and the budget guard — Spec

One `Ledger` (new `planner/ledger.py`) owns all fuel decisions for the turn; it subsumes the incumbent's ad-hoc checks (`farm_camps`' 350k cutoff, `combat_turn`'s 700k gate) so there is a single source of truth. No planner or fallback code calls `fuel_remaining()` directly.

### 2.1 Phase budgets (Initial values; calibrated from S0 telemetry)

| Phase | Cap | Contents |
| --- | ---: | --- |
| P0 observe + precompute | 250k | `observe_enemies`, snapshot into `SimState`, `blocked_tiles`, threat-zone bitboards, ≤4 `DistanceField`s (goals/altar/spawn/safety), enemy-intent classification |
| P1 candidates | 50k | Generate ≤5 root action bundles (§4.1) |
| P2 search | **min(remaining − RESERVE − P3_est, 1,200,000)** | Expectimax; self-calibrates depth/branching (§4.3). The 1.2M ceiling matches the v4 directive's “stop optional search below 1.2M remaining.” |
| P3 execute + yield | RESERVE (see guard) | Chosen bundle's SDK calls, `set_priority`, telemetry, `end_turn` |

Default turn total ≈ 14.3k overhead + 250 + 50 + 1,200 + 250 ≈ **1.76M of 2.485M usable** — ≈700k headroom absorbs map-size scaling, tier-D fallback, or opportunistic PV-deepening.

### 2.2 The guard (the non-negotiable invariant)

**Invariant: when the planner (or any tier) finishes deciding, `fuel_remaining() ≥ RESERVE_ACTION`, where RESERVE_ACTION covers the most expensive remaining executable bundle plus end-turn overhead.** Running out of fuel mid-turn forfeits the turn's remaining actions (§1.2), so the guard is checked *before* committing to execute, not after.

- `RESERVE_ACTION = 250,000` (Initial value). Basis: measured per-call costs put the worst realistic bundle — `move` + `attack` (+ reset re-checks) + `cast` + channel start + ward + `set_priority` — well under 150k, plus margin; S0 replaces this with the measured p99 of real bundle executions from telemetry.
- **Sampling:** `Ledger.check()` samples `fuel_remaining()` (3,165/call) at every phase boundary and every 4 nodes (~1–2% overhead at leaf costs).
- **Mid-search abort:** before expanding any node, require `fuel ≥ RESERVE + leaf_cost_estimate`. On violation, stop expanding, evaluate the current frontier, and return the best *completed* candidate. If no candidate completed, fall through to the next tier (§7).
- **Pre-execution check:** after choosing a bundle, require `fuel ≥ RESERVE + measured_cost(bundle_kind)` from the S0 per-kind table. If violated (only possible if constants drifted), execute the cheapest safe bundle — a single `move` or nothing — and yield. Never forfeit the turn to a guard bug.
- **First turn** (5M budget, ≈453k pre-instruction burn): run P0 fully, measure per-map node costs, cache per-map constants; search may run but tier defaults to D2.
- **Channel turns** skip P1/P2 tree search entirely (§6.5) — the dedicated continue/cancel mini-search is capped at 150k, leaving the full reserve.

**Regression target (gate for every stage): zero suspensions, `min_fuel ≥ RESERVE_ACTION` on all exercised turns** — replacing the incumbent's measured 17–48 suspensions per 500 rounds. `main.py`'s existing `min_fuel`/`suspended` telemetry already reports this every 100 rounds; S0 extends the line with the chosen tier.

## 3. What the SDK gives us — and what it does not (simulation feasibility) — Verified

Read directly from `sdk/python/cambc/` (v2.1.5) and the native stubs:

**Provided:** observation (`me()`, `vision.*`, `game_map` static terrain/altars/spawn regions, cached `camp_groups()`, engine `constants`); `Bitboard` with `copy/or/and/invert/count/is_set/positions/shift/reachable_tiles/draw_chebyshev/shadow_cast/export_linear_buffer`; `DistanceField` with `compute/compute_to/get/next_move_from/copy`; `hypothetical_vision(kind, x, y)` (what *I* would see from a hypothetical position). `Bitboard.copy` and `DistanceField.copy` are **plain data clones**.

**NOT provided — stated explicitly:** there is **no game-state cloning, no forward simulation, and no opponent-intent API**. The SDK is observe/act: actions mutate the live engine; nothing can advance a hypothetical state by a round, apply an attack/move/capture to a cloned state, or ask what an enemy intends. `Bitboard.copy`/`DistanceField.copy` clone *data structures*, not game state; `hypothetical_vision` answers a visibility query only.

**Therefore — Spec:** the in-bot simulator is **hand-written, deliberately approximate**, built from cloneable plain-Python state plus the SDK's bitboards/fields as immutable shared read-only inputs; opponent behavior is modeled with **deterministic approximations over last-seen intent** (§6.4). Approximation error is contained by four mechanisms: pessimistic enemy ordering, risk-weighted evaluation, a 2–4 round horizon, and **re-planning every turn** (model-predictive control — only the current turn's bundle is executed; next turn re-observes and re-plans, so systematic sim error self-corrects within one round).

## 4. Search design — Spec

### 4.1 Candidate generation (branching limited to meaningful actions)

`planner/planner.py` generates ≤5 **action bundles** per our-turn — a bundle is a coherent full-turn sequence (primary decision + secondary fills via existing primitives like `attack_if_in_range`'s reset logic), ordered by priority so overflow drops the tail:

1. **Channel start:** `submit_gems(altar)` when adjacent to an unblocked altar and carrying; `recall` when exposed and fleeing (≤1).
2. **Attack:** best-value in-range target — enemy champion ranked by (submitting, bag size, killability), active camp member, enemy altar lock (≤3 bundles, one per target class, not per target).
3. **Cast:** each ready slot with its single best target (damage/stun on the tactical pick, shield on self when threatened, dash toward/away) (≤2).
4. **Move:** ≤2 — the `DistanceField.next_move` step toward the active goal (camp/altar/spawn per current role), and the safety/retreat step (max distance-to-threat along the precomputed safety field). **Not** all 8 directions: only goal-directed and safety steps, plus implicit hold.

Deduplicate (a cast that ends at the same leaf as an attack is dropped); hard cap 5. This matches the required “move directions toward goals, attack targets in range, ability casts, channel starts.”

### 4.2 Tree structure — 2–4 round expectimax, factorized chance nodes

A “round” lookahead = our turn + enemy turns. The engine alternates teams, each champion acting once per round; we approximate each modeled enemy as getting **one turn between ours**, acting **before us** (pessimistic, matching `combat.py`'s existing convention).

- **Max nodes (ours):** branch over the ≤5 bundles; deeper our-plies (round 3+) cap at **3** (top-3 by shallow score).
- **Chance nodes (enemy):** **factorized per enemy** — enemy 1's ≤2 intents, then enemy 2's ≤2 intents — so branching stays ≤2 per node instead of ≤4 joint; total chance branching per round ≤4. Weighted average (expectimax), weights from the intent model (§6.4).
- **World determinism:** capture timers, channel ticks, respawns are exact world mechanics and are simulated deterministically (§6.3) — no chance nodes needed for them; unseen enemies are *not* simulated (their pressure enters via the aged-threat safety term, as in today's `danger()`).
- **Depth ladder:** D2 = ours→theirs→eval (≤5×4 = 20 leaves); D3 adds our second turn (≤5×4×3 = 60 leaves); D4 = **PV-deepening only** — after the D2/D3 pass, if `fuel ≥ RESERVE + 250k`, re-search only the chosen root bundle one round deeper (≈ +12 leaves). D4 full-width (≈1,900 leaves) is not affordable and is not attempted.
- **No alpha-beta:** expectimax chance nodes defeat plain pruning; at ≤75 leaves it is not worth the complexity. Tie-breaks, in order: eval value → lifetime-gold delta → lower risk (smaller max-branch loss) → stable candidate index (deterministic, avoids plan thrash).
- **Search aborts** per §2.2 return the best completed candidate — the plan is always either a searched result or an explicit tier fallback, never a partial tree.

### 4.3 Self-calibration — Spec

At search start the ledger measures two probe nodes (cheapest bundle apply+eval) via fuel deltas, derives `leaf_cost = max(measured, 8,000)`, then picks the largest depth whose estimated leaves × `leaf_cost` + interior ≈ 1.3 × estimate ≤ P2 budget. If even D2 does not fit, tier B/C/D (§7). Per-map cost constants from turn-1 calibration feed the estimate so the probe is a safety net, not the primary source.

## 5. Evaluation function — Spec

`planner/eval.py`: `eval(SimState) → float` in **gem-equivalent units** (tributed delta is the unit). All terms evaluated at leaves; weights are Initial values with per-term calibration from S4/S5 disagreement logs and replay forensics (deliverable 2's parser).

| # | Term | Formula (gem-equiv) | Weight | Rationale |
| --- | --- | --- | ---: | --- |
| 1 | **Tributed-gem delta** | `submitted[ALLY] − submitted[ENEMY]` | 1.0 | The score. Win at 1,000 gems (`WINNING_GEMS`) → +10⁶ terminal bonus. Includes gems completing within the horizon from in-progress channels at 0.6 (near-banked). |
| 2 | **Carried-gem potential** | `0.35 × carried` per team | 0.35 | In-transit discount: unbanked, unsecured, no tiebreak value (Verified). |
| 3 | **Carried-gem risk / death cost** | at any leaf where our health ≤ 0: `−(0.35×bag + DOWNTIME + 2.5)` and the bag transfers to the enemy's potential (+0.35×bag to them); enemy death symmetric | DOWNTIME = 18 | Death forfeits the whole bag and 60 rounds (`RESPAWN_TIME=60`, longer if spawn blocked). 60 × ~0.3 gems/round farming rate (replay-calibrated); +50 kill gold (`KILL_GOLD`) × 0.05. Enemy kill of our carrier is a double swing. Risk is structural (branch outcomes), not a fudge probability. |
| 4 | **Capture-timer progress** | `±0.5 × progress_fraction × group_gem_value` on the contested/active group | 0.5 | World mechanic: 5-round uncontested occupancy (`CAPTURE_TIME=5`); partial progress abandoned is wasted; enemy contest holds/resets. |
| 5 | **Altar lock control** | `±2.0` per lock on a relevant altar (ours +, theirs −), ×1.5 while we carry ≥20 toward that altar | 2.0 | Locks gate tribute; 3 basic attacks (`ALTAR_LOCK_HITS=3`) ≈ 3 attack-turns of opportunity cost; 10 gold each. |
| 6 | **Position safety** | `−(expected_incoming / max_health) × 30` using enemy threat-range bitboards (attack_range + move + dash, precomputed once per turn — extends existing `enemy_zones`); extra `−5` inside a threat zone while carrying ≥20; health < 25% max adds the death-cost shadow | — | Losing all health ≈ the death cost (term 3) — keeps safety commensurate with gems. |
| 7 | **Camp respawn economics** | `+0.2 × group_gems` if our simulated arrival round is within ±3 of a gem group's respawn (tier timers 40–150); `−5` if we stand on a cleared group's spawn tile | 0.2 / −5 | Respawn starts after reward capture and requires **all** spawn tiles free — camping a cleared tile suppresses our own next harvest (Verified). |
| 8 | **Gold (lifetime)** | `0.05 × (lifetime_gold[ALLY] − lifetime_gold[ENEMY])` | 0.05 | Lifetime gold is the **second tiebreak** at the 2,000-round limit and funds shards; spending does not reduce it, so model it as monotone. 50 kill gold ≈ 2.5 gem-equiv. |

All terms are pure arithmetic over journaled sim fields plus a handful of `is_set`/`field.get` calls against **per-turn precomputed** bitboards/fields — never per-leaf native construction (that is what keeps leaves ≤ 20k).

## 6. Simulation requirements — Spec

### 6.1 State: one mutable `SimState` + undo journal (no per-node copies)

Per-node deep copies are unaffordable (a 4-key dict clone is 6,571; a 20-unit snapshot ≈ 135k). Design:

- **One mutable `SimState` per turn**, built once in P0 from live observation (cost inside the 250k P0 cap: one `vision.champions` sweep, `me.*` snapshot, camp group state, locks, tributed totals).
- **Undo journal:** every mutation appends `(field, old_value)` (or `(bitboard, tile, old_bit)` for occupancy); revert is LIFO. Apply+revert pair is the ≤10k interior-node obligation.
- **Fields:** `round`; our champion `(x, y, health, max_health, strength, attack_range, allowances walk/attack/cast, slot cooldowns, carried, gold, channel state + ticks, stun/dead flags)`; ≤2 modeled enemies with the same fields (from last-seen + visible snapshots); the active camp group `(per-member health/strength, capture ticks, respawn timer)`; nearby altar lock ownership; tributed totals per team.
- **Shared immutable references (never copied):** terrain bitboards (walls/holes/bushes/altars/spawn regions), the ≤4 precomputed `DistanceField`s, threat-zone bitboards, `camp_groups()` cache. Occupancy is one shared bitboard mutated via journal entries.
- The only clones in the whole planner: `SimState` construction (once/turn) and SDK data clones where genuinely needed (none currently planned in hot paths).

### 6.2 Movement model

- **Ours:** step along precomputed fields via `field.get` (1,657) — accurate terrain-aware motion for goal, altar, spawn, safety.
- **Enemies:** Chebyshev step toward their inferred goal, **deliberately ignoring terrain** (reuses `combat.py`'s stated convention: a wall must never make a carrier overconfident — pessimistic for us, ~5 ops, no field needed).
- Legality checks via `is_set` on the shared occupancy/terrain boards (1,744).

### 6.3 Combat / capture / channels / respawn (deterministic approximations)

- **Champion combat:** damage = strength (per `combat.py` math); kills transfer the victim's bag + 50 gold to the killer; camp kills destroy the bag (Verified). The two-round tactical exchange (best burst vs best reply) reuses `combat.burst/exchange` unmodified — it is already pure-Python, SDK-free, and pessimistic.
- **Camps:** awakened in-range members attack in the pre-champion phase; range/sleep handbook conflicts resolved conservatively (treat ambiguous ranges as ≥3, per the playbook's uncertainty rule).
- **Capture:** exact — all members dead → uncontested occupancy starts the 5-tick timer; ticks at turn ends; reward resolves at the owning turn start; contest holds/resets.
- **Channels:** exact — duration = ceil(starting bag × 0.1) min 1 (`SUBMIT_GEM_*` constants); ticks at turn ends; damage does not cancel; stun/death/new enemy lock cancels (conservatively: *any* newly placed lock cancels, pending the playbook's ownership boundary probe).
- **Respawn:** 60 rounds (`RESPAWN_TIME`), extended while spawn tiles are occupied; camp groups respawn per tier timer (50/40/60/150 for cluster/wolf/elk/monolith by reward tables) only when all spawn tiles are free.
- **Vision in sim:** not recomputed (no `shadow_cast` in nodes). Known tiles stay known; enemy positions are last-seen; `hypothetical_vision` (8,107) only for the ≤3 finalist bundles needing a visibility answer.
- **Not modeled (stated fidelity boundary):** hidden enemies, enemy shopping/stat growth (use last-seen strength), enemy ward relocation, monolith specials. Bounded loops only — no unbounded `while` anywhere in the planner.

### 6.4 Opponent model: last-seen intent, no SDK intent API — Spec

Because the SDK exposes no opponent intent (§3), each modeled enemy carries a **last-seen intent distribution** with ≤2 in-tree intents, classified in P0 from `observe_enemies`' memory (extend it to record last observed action kind: attacking us, submitting, movement direction):

| Intent | Trigger | Simulated reply | Initial weight |
| --- | --- | --- | ---: |
| Bank | carrying ≥ ~10 | Chebyshev-step toward nearest altar; submit when adjacent | 0.5 when carrying, else 0 |
| Hunt | we are (or were recently) visible to them | Close on our highest-value/weakest body; attack in range; stun a channeler if ready | 0.3 when visible, else 0 |
| Farm | default | Continue toward inferred active group (from repeated sightings) | remainder |
| Hold/retreat | health < 40% or recently burst | Step away / recall | 0.2 when hurt |

Weights are normalized per enemy and refit offline from our replay corpus (see `docs/replay-parser-notes.md`). Unseen enemies contribute only through term 6's aged threat spread.

### 6.5 Channel turns (dedicated mini-search)

While `is_submitting_gems()`: no tree search. Evaluate **continue vs cancel-and-retreat** over the ≤4 enemy intents with the exact channel tick math (completion round, remaining ticks, term-1 near-banked value vs term-3/6 risk). ≤10 leaf evals ≈ ≤150k. This replaces the incumbent's `channel_damage` heuristic check with the same pessimism but gem-commensurate values. Recall/teleport channels keep the incumbent's rules.

## 7. Decay / fallback ladder — Spec

Never time out = never exhaust fuel: every tier ends above `RESERVE_ACTION`, and `main.py`'s `end_turn()` always runs.

| Tier | Condition (after P0/P1) | Behavior | Est. cost |
| --- | --- | --- | ---: |
| **A — full** | fuel ≥ 700k | Adaptive D2–D4 expectimax (self-calibrated), full candidate set, full eval | ≤1.2M |
| **B — constrained** | 400–700k, or first probe overshoots | D2, ≤3 candidates, ≤1 modeled enemy, eval drops terms 7–8 | ≤350k (matches the v4 directive's tactical cap) |
| **C — greedy** | 250–400k | Depth-1: score each candidate's immediate outcome only (≤5 evals) | ≤150k |
| **D — incumbent** | < 250k+bundle, planner exception, or sim-build failure | Existing `bot.py` chain verbatim (`combat_turn` → carrier/health retreat → `bank` → first-attack → `farm_camps`), trimmed below 600k (cap `farm_camps` candidates at 4 groups, skip rescoring); its own 350k/700k guards remain as the final backstop | bounded by its guards |

Tier D is the incumbent code path preserved unmodified — the A/B freeze protocol (ladder-meta §5) can always diff against it. The planner is invoked only on actionable turns; tier selection is logged in the telemetry line.

## 8. Integration plan — small, independently-testable stages — Spec

New package `bots/main/src/planner/` — `ledger.py`, `sim.py`, `eval.py`, `opponent.py`, `planner.py` (+ `__init__.py`). `bot.py`, `combat.py`, `main.py` change minimally; `draft.py` untouched (draft-time planning is out of scope; the 10× first draft turn is noted as future route-precompute room). `combat.py` is not modified — `burst`/`exchange` are reused inside sim/eval.

| Stage | Change | Tests (all runnable offline unless noted) | Gate |
| --- | --- | --- | --- |
| **S0** ledger + telemetry | `ledger.py`; wire phase guards into `play_turn`; extend `main.py`'s 100-round line with tier + per-phase fuel | 500-round in-engine smoke vs `starter-python` | Decisions identical to incumbent; **zero suspensions** (fixes the measured 17–48); `min_fuel ≥ RESERVE`; per-map cost table recorded |
| **S1** sim | `sim.py`: snapshot builder, apply/revert journal, §6.3 rules | `tests/test_sim.py` (pure data, no `cambc` import — the `combat.py` pattern): journal round-trip property (revert restores exact state), kill bag transfer, capture tick/resolve, channel cancel, respawn blocking | pytest green; in-engine snapshot cost ≤ 250k via ledger |
| **S2** eval | `eval.py` | `tests/test_eval.py`: hand-computed scenarios — tribute delta dominates; carrier under stun threat penalized vs banking now; capture progress valued; lock control; respawn-block penalty; monotone in tributed gems | pytest green |
| **S3** opponent | `opponent.py` intent classifier + weights | `tests/test_opponent.py` on fixture sightings; offline weight fit stub | pytest green; in-engine ≤ 10k/turn |
| **S4** depth-1 live | `planner.py` tier C only, behind a module constant (`PLANNER_MODE`), invoked from `play_turn` after `place_ward`; disagreement log | 9 official maps × 2 sides vs `starter-python` via `runner/run_matches.py` | ≥17/18 retained; zero suspensions; disagreements reviewed for eval bugs |
| **S5** depth-2 live | Chance nodes + factorized enemy model; PV-deepen to 3 | ladder-meta Gate 1 panel (three meta-farmer sparrers) + Gate 2 sparrers | ≥11/18 vs each sparrer; carried-gems-lost ≤ v3; zero suspensions |
| **S6** full adaptive + promote | Depth ladder + tier D fallback complete; planner-first default; replay-driven weight refits | Full ladder-meta §5 protocol (fixed panel, both sides, full 2,000 rounds, default fuel; faults/suspensions counted as failures) | Gate 3-style aggregate gates; zero suspensions/faults; ≥250k remaining at deliberate yields |

Every stage keeps the incumbent path reachable (planner behind a constant; tiers B–D always available), so any regression is a one-line revert. In-engine verification uses `runner/run_matches.py` + `parse_final_results.py`; replays land in the ignored `replays/` dir.

## 9. Uncertainties and calibration obligations

- **Map-size scaling** of area-scaled costs (§1.3 caveat) — turn-1 per-map calibration; re-probe if a map family suspends.
- **shadow_cast metadata failure** (viewer tile must be clear) — avoided by design; documented for anyone touching vision in sim.
- **Lock-placement channel cancellation ownership** and **monolith range/sleep** conflicts — conservative resolutions in §6.3 pending the playbook §5 probes; the sim keeps them conservative until probed.
- **Farming-rate constant** for death downtime (0.3 gems/round) — replay-calibrated in S6.
- **SDK version drift** — cost table and no-clone/no-sim findings verified against 2.1.5 only; re-verify on any `cambc.toml` bump.
- Engine constants referenced (`MAX_ROUNDS=2000`, `WINNING_GEMS=1000`, `CAPTURE_TIME=5`, `RESPAWN_TIME=60`, `ALTAR_LOCK_HITS=3`, `KILL_GOLD=50`, `SUBMIT_GEM_*`) are measured from engine settings in this environment.
