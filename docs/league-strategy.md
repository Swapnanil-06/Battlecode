# Coordinated economy with offline policy learning

16 October 2026. This supersedes the recommendation to adopt `topteam.zip`.
The implementation is `bots/league`; results are recorded separately below.

## What the actual losses show

The public ladder snapshot put Quantum Altar Keepers at 1,495.67, rank 248,
177 wins and 180 losses in 357 recorded matches. Recent displayed picks were
Vendetta, Tavi and Marcella. That matches the incumbent draft, rather than
showing adoption of the experimental roster.

In the [ranked 1–4 loss to GPT dot](https://2026a.battlecode.co.uk/game/match-groups/aa80945e-c9a3-47ac-b969-4cd1ea49cc75),
our scores were 652 on fragment, 1,028 on pilgrimage (a win), 834 on
rushbait_v2, 720 on elkring and 726 on rows. In the rows loss our team had
zero deaths. Its recorded idle turns were about 22%, versus 7% for GPT dot.
Some idle turns are necessary capture waits; this metric alone does not
identify every idle turn as a bug. The loss nevertheless establishes an
economic throughput deficit independent of deaths in that game.

The official pool now contains 17 maps; yesterday's local pool had nine.
Refreshing the pool downloaded ambush, contest, eight, fragment, pilgrimage,
rushbait-v2, stampede and swirl. The previous map-specific draft did not
establish performance on those maps.

The current live combat chain does not invoke the existing two-round
`combat.exchange` evaluator. A combat helper's host tests therefore do not
validate live tactical search. Nor does merely playing more ladder games
update any policy: the existing bot has no persistent training process.

## What current leaders demonstrate

Downloaded and decoded all five public replays in
[Sneaky Bush Campers versus Mite](https://2026a.battlecode.co.uk/game/match-groups/7045bb52-e8fc-4b54-8322-b6ab1d07bc58).
Sneaky Bush Campers led the retrieved ladder at roughly 1,973 Elo.

| Map | Sneaky Bush Campers / Mite score | Leader's draft |
| --- | --- | --- |
| interlock | 1,000 / 942 | Ryth, Stellar, Ren, Tavi |
| eight | 396 / 1,030 | Ren, Stellar, duo, Tavi, Varg |
| fragment | 336 / 1,009 | Ren, duo, Stellar |
| stampede | 1,080 / 0 | duo, Stellar, Varg, Tavi, Ren |
| rows | 1,023 / 891 | duo, Stellar, Varg, Tavi |

Mite's fragment trio was Varg/Ryth/duo. The leader's rows roster had five
bodies from four selections. These are observed complete drafts, not a
claim to know the opponents' private routing, training or targeting code.
The contrasting outcomes argue for training complete policies against
multiple opponents. They do not prove any one lineup is universally best.

## The implemented strategy

Keep the incumbent routing, retreat, lock-breaking and channel safeguards as
the base. Learn a compact policy over roster order and three executable
economy changes; avoid hard-coded map fingerprints.

1. **Reserve work outside personal vision.** Six champions publish short-lived
   camp jobs in eight shared bytes. Each job has a six-bit group index and a
   two-bit timestamp, plus one full 16-bit shared round. Writers evict stale
   records before advancing the full timestamp, preventing modulo-wrap ghosts.
   Reservations expire after two rounds without renewal. Banking, death and
   recovery release a job. Another claim discounts a route rather than
   prohibiting it, so a failed or contested job does not strand the team.
2. **Use the legal dash-plus-walk sequence.** The incumbent returns immediately
   after a successful dash. The candidate can continue with its ordinary walk
   using the still-valid distance field. Casts remain subject to the engine's
   one-cast limit; this does not assume a second spell is legal.
3. **Match purchases to actual repeated actions.** Test Strength on Tavi rather
   than automatically buying Focus. Tavi's base Strength growth is five per
   shard and he has a reset; Focus adds burst every cooldown. Stellar receives
   Focus support when drafted. These choices are tested in complete matches,
   rather than selected from damage arithmetic alone.
4. **Select complete draft orders.** The search includes the incumbent,
   several observed leader cores, and a simpler Vendetta/Varg/Ryth core.
   Three-, four- and five-selection maps take the corresponding prefix. The
   draft memory stores the chosen order for later picks.
5. **Separate ordinary farming from raids.** Eight-or-more-monster groups use
   range-four damage casts outside the monsters' range-three retaliation.
   AoE targeting counts damage across neighbouring monsters. Casters hold their
   safe firing position between cooldowns. Smaller groups retain ordinary
   clearing. Monoliths are ignored when other gem sources exist; on boss-only
   maps, a caster first reaches 250 Focus through gold farming and purchases.
   Boss firing positions avoid the nearby farm corridors where possible.
6. **Invest and return to spend.** First complete one Jungle emblem (30% less
   camp damage), then buy Power shards. Recall with an empty bag and 300 unspent
   gold, or 150 on maps dominated by exceptionally large camps. Tavi buys in the
   field. On investment maps, gold-only groups receive normal economic value.
7. **Make planning finish inside the budget.** Warm camp metadata incrementally,
   including pauses within a single large group. Finish warm-up before calling
   consumers that assume a complete cache. Scale route budgets for map area;
   when exact distant-route pricing is unaffordable, use an estimate for ranking
   and retain exact pathfinding for execution. Skip disconnected walking goals.
   Combat runs before optional ward siting. Exceptions propagate to the main
   diagnostic logger instead of silently disappearing.
8. **Avoid paying repeatedly for the same observation.** Visibility and position
   queries share a cache during a decision. Keys include the entity kind and
   handle, so a camp and champion cannot collide. Every action clears it, and
   the next turn clears it before reading the champion's position. This reduces
   SDK overhead without assuming that observations survive an action or a turn.

These changes followed failed engine experiments. The initial learned policy
won 13/16 training games, but only 17/32 across the newer maps and two opponents.
That was insufficient evidence to release it. Unconditional early boss sieges
also failed: enemy farmers could acquire upgrades and steal the eventual reward.
The later release candidates therefore require investment and explicitly avoid
bosses on ordinary farming maps.

## Why this learning approach

[Lucas et al., 2019](https://arxiv.org/abs/1901.00723) study noisy game-agent
parameter optimisation and find strong performance from model-based methods
such as NTBEA and SMAC. Their small surrogate models exploit parameter
interactions while keeping optimiser overhead low. This motivates the
runner's one/two-tuple UCB proposal model; it is an adaptation, not a claim
to reproduce that paper's experiments or its performance.

[TStarBot-X](https://arxiv.org/abs/2011.13729) shows why a diverse opponent
league, exploiter roles and rule-guided search matter under limited compute.
Even that reduced-scale neural system used substantial GPU resources. The
transfer here is to preserve historical opponents and test distinct policies;
we are not claiming an AlphaStar implementation.

[Ontanon, 2017](https://arxiv.org/abs/1710.04805) studies combinatorial bandit
sampling for large RTS action spaces. Its discussion of portfolio approaches
supports considering a bounded set of useful actions or scripts rather than
blindly expanding every low-level move. A full simulator-backed tactical
search remains separate work; the current economy candidate does not pretend
that the unused combat evaluator has become one.

A neural network could later rank macro actions or approximate a searched
value function. It first needs legal observation features, a fast environment
interface, meaningful action labels/rewards, and enough varied games. Training
against one incumbent and calling the result self-improving would risk learning
one counterstrategy. The included runner instead optimises a small explicit
policy using actual WASI matches and keeps its evaluation evidence.

## Reproducible selection and independent evaluation

`python runner/train_league.py --output replays/new-search --trials 20 --validate`

Training uses collision, elkring, rows and expanse, both sides, against the
frozen `main` and `sparring-meta` opponents. Eight newer maps are excluded
from the automated parameter search. Every evaluated policy has a source snapshot,
source hash, engine log, replay panel and machine-readable result. The
optimiser rewards wins, using score margin and early delivery only as smaller
terms; logged errors and fuel suspensions receive a large penalty. Existing
results are checked against the requested configuration before reuse.

Training starts with a control and roster warm starts, then uses past results
to propose new policy combinations. The initial run's first ten proposals used
an elite-mutation search; the shipped runner adds the tuple-model proposal
method for subsequent searches. Neither learns during a ladder game or stores
training state inside the uploaded ZIP. Run the trainer locally, then deploy
the selected frozen policy. Validation results never enter its automated optimiser.
However, those maps subsequently informed manual debugging and release selection;
the final all-map comparison is a development benchmark, not an untouched map
holdout. Separate opponents are used for a final robustness check.

The public replays are downloadable now. Older notes saying no public replay
corpus can be collected are superseded by these observed bundle links.

## Release result

Recommended upload: `quantum-altar.zip`. Selected draft order: Varg, Vendetta,
Stellar, Tavi, Ren; maps take their permitted prefix. The final roster was
introduced during manual development and measured in full-engine panels.

- **28/34 wins (82.4%)** against the actual original `bots/main`,
  all 17 current maps, both sides, at the default engine budget.
- **12/12 wins** against the hunter, altar and denial local opponents,
  collision and rows, both sides. These opponents were outside the automated search.
- Two incumbent-panel games reported fuel suspensions (Eight B and Stampede B,
  both wins). No bot exceptions were logged. The robustness panel reported no
  suspensions. Every fixture remains in all denominators.
- 13 host tests passed, including shared-memory expiry and interrupted map-cache
  warm-up; syntax checks passed. The existing combat-helper tests do not establish
  that live search is enabled.
- The official CLI produced the ZIP. Every packaged file matches the source
  snapshot evaluated here. SHA-256: `d50e39888de519e65c8e734f64b29470c2b5e5e6fee685a4aa43cf393e8181cf`.

Machine-readable scores, configuration, per-file hashes, map hashes and earlier
candidate comparisons are in [`league-results.json`](league-results.json).
The original bot remains available for comparison. Engine replays and complete
logs remain locally under `replays/release-v15/`.

| Map | New / original gems as A | New / original gems as B |
| --- | --- | --- |
| ambush | 996 / 1060 (L) | 1010 / 954 (W) |
| collision | 1024 / 572 (W) | 66 / 1004 (L) |
| contest | 1000 / 0 (W) | 800 / 200 (W) |
| corners | 1028 / 116 (W) | 1026 / 0 (W) |
| eight | 1008 / 682 (W) | 1046 / 688 (W) |
| elkring | 1080 / 720 (W) | 1008 / 720 (W) |
| expanse | 1008 / 912 (W) | 1008 / 860 (W) |
| fragment | 1046 / 476 (W) | 1010 / 512 (W) |
| interlock | 1012 / 414 (W) | 1000 / 934 (W) |
| lanes | 1008 / 908 (W) | 958 / 1004 (L) |
| monolith | 1032 / 880 (W) | 1004 / 946 (W) |
| packs | 1008 / 272 (W) | 1012 / 680 (W) |
| pilgrimage | 1048 / 816 (W) | 1048 / 136 (W) |
| rows | 1056 / 924 (W) | 1056 / 924 (W) |
| rushbait-v2 | 0 / 0 (L) | 0 / 0 (W) |
| stampede | 1080 / 360 (W) | 1080 / 360 (W) |
| swirl | 828 / 1030 (L) | 978 / 1022 (L) |

This is evidence of improvement against these frozen opponents, with all losses
reported. It is not a measured live-ladder rank: the top teams' private agents
have not been run locally against this release. There is no valid conversion
from this development-panel win rate to a promised leaderboard Elo.
