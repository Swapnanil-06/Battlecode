# Quantum Altar v16

Based on the current repository at `f159455`, not the earlier v15 baseline.

## Supplied top-team matches

The five supplied match groups contain 25 games: 2 wins and 23 losses.
Match-level data and public match IDs are in `top-five-analysis.json`.

| Opponent | Our wins | Games |
| --- | ---: | ---: |
| Alphafish | 1 | 5 |
| Intercontinental Fish | 1 | 5 |
| Mite | 0 | 5 |
| Sneaky Bush Campers | 0 | 5 |
| Univardisty of Shingtonwash | 0 | 5 |

## What the supplied replays establish

- Ambush: our team produced zero gems, moves and attacks. Repeated budget aborts prevented economic actions. This is a scheduling failure, not evidence that a different champion alone fixes the map.
- Rows and Expanse: some losses had zero deaths. Farm routing, purchase timing and clear speed matter even without combat.
- Eight: our team suffered roughly 19–29 deaths in the supplied losses, against 1–2 for the opponents. The farming improvements do not solve this combat deficit; this release preserves the existing policy there.
- Opponent inventories show both damage-reduction builds and health-first Jungle plus Monster farming builds. They support testing these options, not a claim that every leading team uses one recipe.
- Local Stampede traces exposed a separate siege/capture deadlock after monsters died. The farming variant fixes it, but its draft still lost one side; Stampede therefore keeps the incumbent in this release.
- Idle counters also include spell and capture turns. They are not automatically wasted turns.


## Changes

The release selects policies from static public map geometry. The farming policy is enabled only on Ambush, Expanse, Fragment, Monolith and Rows. Packs uses a separately tested pack-clearing variant. Other layouts retain the incumbent policy. The following changes describe the farming policy; they are not enabled globally.

- Reserve fuel for movement and execute chosen farm routes for a bounded period.
- Capture an already cleared objective before rescoring the entire map.
- Move into an unseen cleared camp instead of remaining on its geometric siege ring.
- Exclude optional skipped monoliths from the ordinary farming build classification.
- Compare area and single-target damage with overkill capped; centre Varg splash on packs.
- Compare combat spell damage and interrupts, and local fighting strength before chasing.
- Prioritise deposits from carriers already at the altar, including winning bags.
- Use team-size-aware farming drafts, health/monster emblems, and Ren retaliation scaling.

## Final local validation

23/34 wins against the frozen current repository bot, using cambc 2.2.1, engine 0.0.2, release mode, default fuel and complete matches.

| Map | Our side | Our gems | Baseline gems | Result |
| --- | --- | ---: | ---: | --- |
| ambush | A | 1008 | 0 | Win |
| ambush | B | 1102 | 0 | Win |
| collision | A | 846 | 1144 | Loss |
| collision | B | 1006 | 328 | Win |
| contest | A | 600 | 1000 | Loss |
| contest | B | 1000 | 0 | Win |
| corners | A | 716 | 1016 | Loss |
| corners | B | 1032 | 708 | Win |
| eight | A | 282 | 1008 | Loss |
| eight | B | 1048 | 110 | Win |
| elkring | A | 756 | 1008 | Loss |
| elkring | B | 1008 | 576 | Win |
| expanse | A | 1002 | 950 | Win |
| expanse | B | 1022 | 824 | Win |
| fragment | A | 1056 | 402 | Win |
| fragment | B | 1005 | 767 | Win |
| interlock | A | 738 | 1068 | Loss |
| interlock | B | 1018 | 738 | Win |
| lanes | A | 1016 | 884 | Win |
| lanes | B | 986 | 1016 | Loss |
| monolith | A | 1038 | 550 | Win |
| monolith | B | 906 | 1004 | Loss |
| packs | A | 1040 | 932 | Win |
| packs | B | 1036 | 832 | Win |
| pilgrimage | A | 1120 | 544 | Win |
| pilgrimage | B | 612 | 1044 | Loss |
| rows | A | 1056 | 792 | Win |
| rows | B | 1056 | 924 | Win |
| rushbait-v2 | A | 1030 | 928 | Win |
| rushbait-v2 | B | 928 | 1010 | Loss |
| stampede | A | 0 | 0 | Loss |
| stampede | B | 0 | 0 | Win |
| swirl | A | 1030 | 640 | Win |
| swirl | B | 1094 | 770 | Win |

Logged exceptions: 0. Fixtures reporting fuel suspension: 0.
No fuel suspensions reported by the bot diagnostics.

The 16 main tests and 13 league tests pass. The older exchange-helper tests do not imply that a tactical search is integrated into live play.

## Limits

These results establish performance against the frozen local baseline. Fixtures using the incumbent fallback are near-mirror games, not evidence of strategic improvement. Map selection was informed by these development fixtures and can overfit. A globally enabled candidate won only 15/34 and was rejected. These results do not establish a new top-five win rate or an Elo prediction. The private top-team binaries were not available for responsive local rematches. All development maps informed iteration.

The five match archives were analysed as data. No bot instructions were taken from them. The policy is fixed during ladder games; there is no neural network training online.

## Upload

Use `quantum-altar-v16.zip`. It contains only the exact tested `src/` Python files.
SHA-256: `cd21b9ae7dbdaa3ed21e2467b37b879b2c2e447804f58c6584388d89409ce04b`.

The previous `quantum-altar.zip` is retained as a historical artifact; it is not this release.
