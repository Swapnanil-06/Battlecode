# Competitive direction: coordinated economy, selective objective fights

15 October 2026, live inspection around 20:50 UK. This is a proposed strategy
and an implementation start, not a claim of top-team performance.

**Validation update:** see [platform and competitive review](strategy-validation.md).
The objective-loop architecture fits the current platform, but the proposed
Varg/Ryth/Stellar trio and the starter scoring functions are not established
as top-tier. Treat the roster section below as an experiment, not the final pick.

## What the leaders actually show

The [live ladder](https://2026a.battlecode.co.uk/game/ladder) had 422 teams:
Intercontinental Fish #1 (1,925), Mite #2 (1,872), Univardisty of Shingtonwash
#3 (1,855), Sneaky Bush Campers #4 (1,819), VeryGood #5 (1,808).
Ratings and ranks will move. Do not treat the repo's 13 October snapshot as current.

Inspected [Fish vs VeryGood, ranked, five maps](https://2026a.battlecode.co.uk/game/match-groups/b69e372f-7c2c-4d8a-8ea1-4a3ea2e8a58f):

| Map | Winner | Finish round | VeryGood gems | Fish gems |
|---|---|---:|---:|---:|
| expanse | VeryGood | 327 | 1,026 | 844 |
| packs | Fish | 491 | 720 | 1,080 |
| elkring | Fish | 446 | 288 | 1,008 |
| collision | Fish | 661 | 330 | 1,016 |
| corners | Fish | 580 | 432 | 1,016 |

Read the [elkring replay analytics](https://2026a.battlecode.co.uk/game/visualiser/d10a837d-3c54-4376-8872-8f691cd16dbf)
at three timeline positions. Columns are VeryGood / Fish:

| Round | Banked gems | Gold earned | Champion kills | Camp captures |
|---|---|---|---|---|
| 85 | 0 / 72 | 585 / 635 | 0 / 1 | 3 / 3 |
| 175 | 36 / 216 | 975 / 2,055 | 0 / 6 | 5 / 9 |
| 446 | 288 / 1,008 | 2,780 / 5,275 | 1 / 8 | 14 / 25 |

Fish drafted **Ren, Stellar, Cassi & Issac, Ryth, Varg**. VeryGood drafted
**Stellar, Tavi, Cassi & Issac, Willow, Ren**. These are complete five-pick
drafts for this one map, not each team's universal lineup. Fish's combat
advantage and economy advantage develop together; the public numbers do not
prove which caused the other. Highlight labels report disable follow-ups and
multi-round fights, but are not proof of a specific targeting algorithm.

**Inference:** a pure passive farmer is unlikely to match this particular
winner. Conversely, VeryGood's fast expanse win shows there is no universal
"always group and fight" answer. We need map-dependent allocation and a policy
that makes fights pay in delivered or denied gems. Opponent source, exact build
orders, internal routes and decision logic were not available in this inspection.

## The strategy I would build

**Win the camp-to-altar cycle; fight only when it improves that cycle.**

1. **Allocate territory in draft.** Use terrain distances to assign two or three
   camp circuits, each ending at a reachable altar. Separate home-side safe
   income from contested central groups. Score whole connected groups, including
   retaliation and capture time. Reserve one fallback circuit per role. Store
   compact group IDs and role assignments in draft memory, within its 1,024-byte
   limit; do not run an all-pairs map search on every later draft turn.
2. **Spread for uncontested income; converge for an advantage.** Give each
   farmer a primary circuit. One body stays for capture; others immediately
   leave for the next useful job. A cleared camp never needs three waiting
   champions. For a central objective, send a short-lived two-body squad only
   when its combined clear/contest value beats two independent circuits. Return
   to separate jobs after capture or after the opportunity expires.
3. **Use a damage dealer plus control near contests.** Varg rewards clustered
   camps; Stellar rewards legal stationary spell opportunities; Ryth provides
   durable damage/control. Vendetta remains an excellent candidate for isolated
   farming and movement. Cassi & Issac adds a body, but linked death demands
   pair-aware escape checks. Ren is a current winner's pick, worth testing when
   retaliation can earn value; the single replay does not establish him as best.
4. **Convert crowd control into something.** Prefer interrupts of enemy tribute,
   a kill achievable before retaliation, or safe access to a contested camp.
   Focus the same legal visible target with nearby allies. Do not spend turns
   chasing an empty-handed enemy away from our route. Do not leave a carrier
   exposed to gain a small amount of damage. Price a duo death using both bags
   and both bodies' lost work.
5. **Bank by opportunity cost, not a fixed bag threshold.** Compare banking now
   against one more camp and then banking. Include the current bag at risk,
   travel, capture, channel completion and expected recovery. Bank immediately
   if the completed tribute wins, or time is running out. Reserve enough rounds
   for the channel's next-start resolution. Protect a good channel unless the
   likely death/interrupt cost outweighs completion.
6. **Scale deliberately.** Buy according to actual spell/attack contribution;
   reserve a lock where it protects a real delivery. Evaluate gold-only camps
   when their purchases shorten future cycles. A gold camp is not automatically
   worthless just because it has no immediate gems. Leave spawn after recovery
   and purchases, and leave captured tiles so the next harvest can respawn.

### Draft to test first

For a quick, lower-complexity candidate: **Varg / Ryth / Stellar**, with
**Vendetta and Tavi** as fourth/fifth candidates. Reorder or replace by map:
Vendetta moves up on dispersed safe clusters; Varg moves up on adjacent groups;
Stellar needs casting positions that do not strand it. This is our engineering
starting hypothesis, not the observed #1 roster.

The higher-ceiling candidate replaces a slot with **Cassi & Issac** after linked
death handling works. Test Fish's Ren/Stellar/duo/Ryth/Varg roster as a separate
candidate rather than assuming their picks alone reproduce their results.
Marcella is a situational anti-stun carrier, not a forced second/third pick.

## Where the current bot leaves value behind

Read against the cloned main branch on 15 October:

- `draft.py` computes cluster/safety statistics but always chooses
  Vendetta/Tavi/Marcella/Varg/Ryth. Those statistics do not affect the draft.
- `farm_camps()` estimates clear time from basic Strength, sequentially, even
  though actual abilities and Varg splash can change the best camp substantially.
  Its early in-range attack return can keep a champion committed before comparing
  a more urgent objective.
- Gold-only routes receive a **0.001 multiplier**. That virtually eliminates
  investment routes regardless of the improvement their purchase would unlock.
- Visible-ally distance penalties are soft and local. There are no durable team
  job reservations; allies outside personal vision can duplicate work.
- Banking uses 20/40-gem thresholds, while `combat_turn()` runs before routine
  bank decisions. Audit whether optional fighting delays a valuable delivery.
- The repo already has a fuel ledger, exchange model, movement and replay tools.
  Build on those; a large expectimax rewrite is not the fastest first improvement.

## Implementation start included

`bots/main/src/objective_policy.py` provides three SDK-free functions:

- `objective_rate`: expected delivered/denied gem swing per round, subtracting
  current-bag loss and recovery cost. Survival is an input estimate, not a claim
  that we can accurately predict opponents. Avoid counting stolen gems twice.
- `assign_jobs`: bounded greedy assignment with one body per exclusive job and
  preserved capture commitments. This is not optimal matching; it is a cheap
  starting point that stops obvious duplicate assignments.
- `bank_now`: compare banking with one extra complete delivery cycle.

**Not wired into live gameplay.** No unmeasured strategy replaces your working
bot. Host-side tests cover bag risk, safe detours, and allocation conflicts;
no engine match or fuel measurement has been run for this new module.

Wire in this order:

1. Snapshot up to eight reachable jobs; use actual path distances and a small
   champion-aware clear estimate (attack/reset, spell damage, splash, retaliation).
   Compare only legal action bundles; ranged walking can consume the basic, and
   one cast cannot simultaneously be reset, shield and damage.
2. Assign static primary circuits in draft so independent champion instances
   agree even outside shared vision. Use the eight live bytes for one urgent
   alert or one temporary reservation with expiry; there is not room for an
   uncompressed six-body job table. Do not assume Python globals are shared.
3. Feed those marginal route scores into `assign_jobs` where the same information
   is available. Keep unknown teammate jobs on their static circuits. Reserve
   existing captures before allocating idle bodies; squad jobs need caller-side
   reservation of both bodies. Release on death, retreat, reward or timeout.
4. Compare delivery options through `bank_now` before optional chase logic.
   Keep the existing emergency survival and legality checks. Do not interrupt
   an existing channel merely to run the economic scorer.
5. Only then add short combat lookahead around a contested objective. Preserve
   the fuel ledger's execution reserve and check real WASI fuel, not host speed.

## What would justify calling it competitive

Use the existing `runner/make_panel.py`, `gem_pace.py` and replay parser. Start
with both sides of expanse, elkring and collision against sparring-meta,
sparring-hunter and sparring-altar. Then cover all downloaded maps and seeds.
Track banked gems at rounds 250/500, finish round, carrier losses, deaths,
capture waiting/duplicate travel, faults and fuel suspensions. Promote one change
at a time only when aggregate delivery improves without a major map regression.
These are proposed gates, not completed results.

For external validation, challenge current top teams across the same maps and
compare with their recent finish times. Aim to beat roughly 327-round expanse
and 446-round elkring examples while surviving opposition; these are individual
reference games, not statistical targets. Starter wins alone cannot establish
top-team strength. Save replay IDs and version every candidate so a gain can be
reproduced.
