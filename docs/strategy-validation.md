# Platform fit and competitive review

15 October 2026. Scope: current Autumn platform rules/API, strategic reasoning,
and public top-team evidence. No engine tournament or submission was run.

**Verdict: the architecture is compatible and worth building; the exact draft
and starter policy are not validated as top-team strength.** The useful edge
is higher team delivery throughput with correct capture/channel behavior and
selective control of contested objectives. The earlier response was too quick
to recommend Varg/Ryth/Stellar as a default competitive trio.

## Current primary sources checked

Downloaded the complete current `GameRules.md` and `BotAPIPython.md` from the
[official handbook exports](https://2026a.battlecode.co.uk/game/docs/agents),
and read the [shared-memory chapter](https://2026a.battlecode.co.uk/game/docs/shared-memory).
Rules SHA-256: `1c7fcf111d95b4734070f8f676cd50a48154feb0673de73a31c79845afa34732`.
Python API SHA-256: `3013fde86080e89ebf109357d4b8ca913babcb4592be542d92df0fadd542772f`.
The rules export differs from the repo's 13 October snapshot. The current
monolith table says range 3; older playbook caveats should not be treated as
the latest table. The current export still describes sleep in two different
ways, so the strategy should not depend on a precise sleep exploit.

| Strategy component | Platform finding | Required implementation boundary |
|---|---|---|
| Map-aware opening routes | Full map and camps visible during draft; 3–5 unique selections | Draft route planning is supported. Enemy picks can mirror ours. |
| Separate farmers / temporary squads | Champions have independent bot instances and personal vision | Use shared draft plans and compact signals, not shared Python globals or a global live observation. |
| Team coordination | 1,024 draft bytes, read-only in play; 8 live bytes | Full observation sharing does not fit. Compressed assignments are possible, but need explicit encoding and freshness. |
| Solo capture while allies move on | Extra allies do not accelerate capture; present allies split rewards | Clear the whole connected group first. Leave a live uncontested capturer until the reward actually arrives. |
| Revisit farming circuit | Respawn starts after capture; occupied spawn tiles delay it | Vacate captured tiles and track observed timers. Old draft information is not proof a camp is still alive. |
| Carrier protection / denial | Gems score only after tribute; kills transfer carried gems | Price carrier exposure and enemy recovery, not damage dealt alone. No teammate gem handoff is documented. |
| Channel interruption | Ordinary damage does not stop tribute; stun, death or lock does | Focus a valid interruptor; stun-immune Marcella needs a different answer. Locks take three basic hits to remove. |
| Fast ranged clearing | Ranged basics conflict with walking; damaging ranged spells may also exclude it | Score complete legal sequences, not hypothetical move + spell + attack combinations. |
| Reset/shield/spell combinations | Only one successful cast per turn, across both slots | Varg cannot shield and reset on the same turn. Vendetta's kill reset does not grant another cast. |
| Safe tribute timing | ceil(bag/10) owner-turn-end ticks, then next owner-turn-start resolution | Include resolution and match horizon. A final-round start is not an instant score. |
| Recovery and buying | Recall retains bag; damage interrupts recall; healing occurs at spawn turn end | Wait for healing before leaving. Only Tavi buys shards in the field; field Health does not heal. |
| Short local planning | Python default 2.5M fuel; first draft 10x, first play 2x | Yield deliberately. Exhaustion resumes stale code next round. Host test speed is not WASI fuel validation. |
| Duo draft | Cassi & Issac is one selection, two bodies, but linked death | Model both bags and both lost farming streams; protect the weaker body. |

Python API support was checked for `draft.current_draft`,
`game_map.camp_groups`, `CampGroup.spawn_tiles/gem_value/gold_value/state`,
`vision.champions`, `Champion.submit_gems`, `set_priority`, `fuel_remaining`,
`DraftMemoryBuffer.submit`, and `shared_memory.read/write`. These support the
proposed adapters. This is documentation compatibility, not an executed SDK
integration test against the repo's pinned 2.1.6.

### A practical coordination scheme

Put stable route identifiers, role-to-champion mapping and fallback circuits
in draft memory. Identify map groups by deterministic spawn coordinates, not
host Python object identity. Every body follows its own primary circuit until
local observations or a fresh signal justify a change.

Use the 64 live bits for one urgent alert: x 7 bits, y 7, type 3, sender 3,
observation round 11, expiry round 11, reserved 22. Define the empty value,
replacement priority and stale-message handling. This fits 100x100 maps,
2,000 rounds and up to six bodies. All writes happen through the SDK; read
the current record before replacing a fresher, more urgent alert.

This is a design proposal, not an implemented protocol. If later replacing it
with compact job reservations, budget the bits explicitly; do not silently
assume both a full job table and this entire alert fit at once. A signal can
guide movement but does not make its reported enemy a legal visible spell target.

## Is it actually strong?

**The principles have a strong mechanical case.** More allies cannot speed a
capture, so removing redundant waiting increases useful team turns. Gems that
never finish tribute do not win. Stun/lock timing can deny a much larger
delivery than raw damage. Draft-aware splash and stationary burst change clear
times enough to alter route choice. Each benefit has a concrete game mechanism.

**The implementation still needs more than these principles.** Static routes
can waste time after enemy captures, naive grouping sacrifices parallel income,
and early banking can lose to a safe efficient farmer. Routes need expiry,
fallbacks, ability-aware clear estimates, and delivery costs. No principle here
alone proves a rank advantage against opponents already doing it well.

Public evidence checked:

- [Fish vs VeryGood, ranked 4–1](https://2026a.battlecode.co.uk/game/match-groups/b69e372f-7c2c-4d8a-8ea1-4a3ea2e8a58f):
  on elkring Fish won 1,008–288, with 25–14 captures and 8–1 kills. The observed
  five picks were Ren/Stellar/Cassi & Issac/Ryth/Varg. This supports a combined
  economy/combat benchmark, not our exact routing algorithm or a universal roster.
- [Mite vs orZers, unranked 5–0](https://2026a.battlecode.co.uk/game/match-groups/c2d873bf-0661-4a7d-92d0-0c4424dcf27e):
  Mite finished rows in 390, elkring in 469, collision in 937, lanes in 338 and
  corners in 417 rounds. Different opponents and maps prevent a fair speed
  ranking against Fish. Even leading bots have materially different finish times.

Further checked [Mite's elkring replay](https://2026a.battlecode.co.uk/game/visualiser/400c83e9-94c5-43fb-b8d6-f5ed93562722)
at its final state: **1,008–432 gems, 5,575–3,315 gold earned, 14–0 kills,
25–17 camp captures**, in Mite's favor. Mite's complete draft was
**Varg / Stellar / Cassi & Issac / Ryth / Ren**. Thus two separate leading
teams use the same five champions on elkring, in different pick orders.
This is stronger evidence for testing that five-pick roster, while still
not establishing a three-pick subset or the underlying control policy.

There is no source-level evidence here that top teams use our assignment or
banking formulas. Nor does one top-five loss establish a champion is bad.

### Draft correction

For five-pick elkring, the best source-supported candidate from this inspection
is **Varg / Stellar / Cassi & Issac / Ryth / Ren**, shared by both #1 and #2.
Implement its roles as cluster clearer, ranged burst, guarded two-body pairing,
durable control, and retaliation/control. Those roles are rules-derived proposals,
not an observed explanation of the opponents' code. The duo needs linked-death
protection before adoption.

Do not force the same roster on every map or assume its first three icons are
the best three-pick draft. Test three-pick subsets using route geometry and
joint survival. Keep **Vendetta / Varg / Ryth** as a simpler alternative where
isolated farming and mobility matter; it is an engineering candidate, not a
measured winner in the current replay sample. Stellar's burst and Ren's control
deserve explicit support rather than being appended to a universal Vendetta draft.

For example, arithmetic for a fresh, unupgraded, stationary champion already
in legal range of a lone 500-HP harmless cluster gives approximately:

| Champion | Attack turns to clear |
|---|---:|
| Stellar, both spell slots available | 5 |
| Vendetta, reset available | 7 |
| Ryth, damage spell and reset available | 7 |
| Varg, reset available | 9 |

This was checked with a small damage/cooldown calculation, not the game engine.
It excludes movement, capture, tribute, retaliation, visibility and upgrades.
Varg's splash can reverse this comparison for adjacent monsters; Vendetta's
mobility and kill resets affect the next target. Thus this table argues for
map-aware choice, not a tier list.

## Starter code audit

The five existing host tests pass. They check arithmetic/allocation behavior,
not competitive performance. The helper module is not connected to gameplay.

Three limits matter before integration:

1. `assign_jobs` is greedy. With offers A→X=10, A→Y=9, B→X=9, it returns A→X
   worth 10, while A→Y plus B→X is worth 18. Reproduced on the host. Use it as
   a cheap duplicate-work filter, not an optimal team planner. Independent
   champions with different observations cannot independently recompute one
   globally consistent assignment without a protocol.
2. `bank_now` needs survival probabilities we do not currently calibrate. It can
   make bad decisions with optimistic inputs. Use conservative visible-threat
   and last-seen envelopes initially, plus winning-bag, survival and horizon
   overrides. Its ratio is a heuristic, not a full long-horizon optimizer.
3. Gold defaults to zero value and current-bag loss only prices our lost gems.
   Gold-only investment routes need future-throughput estimates. An enemy kill
   can also transfer our bag into enemy score; denial estimates must count that
   separately and avoid double-counting gems already included as our reward.
   Temporary delay is not permanent denial.

**Recommended implementation priority:** route ownership and correct capture
completion; ability-aware clearing; safe delivery/interrupts; then coordinated
contests and adaptive drafting. Preserve the working bot while adding these
behind measured comparisons. Platform fit is verified from current primary
documentation. Actual top-team performance remains unproven.
