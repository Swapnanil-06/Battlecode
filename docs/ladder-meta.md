# Ladder meta and the v4 directive

**Quantum Altar Keepers · 13 October 2026 · snapshot fetched 19:45 BST (18:45 UTC)**

**Hypothesis — recommendation:** prioritize Vendetta's clear/reset loop, Varg's splash and shield, and a guarded Cassi & Issac implementation. Test **Cassi & Issac / Vendetta / Varg**, then add Ryth and Tavi for four/five selections. Do not promote the playbook's Marcella/Tavi core without an A/B comparison. Keep a **Ryth / Vendetta / Varg** fallback if the linked-death pair fails its gate. The likely opportunity is more productive champion turns and safer conversion into score, not indiscriminate fighting.

**Measured — headline:** Vendetta appears in **21/25 (84%)** top-team lists versus **6/25 (24%)** bottom-team lists; Cassi & Issac appears in **17/25 (68%)** versus **8/25 (32%)**. Marcella, Prism and Willow appear in **zero top-25 lists**, but all eleven champions appear somewhere on the ladder. This is association with rank, not a champion win rate or proof of causation.

## Evidence boundaries: these are top-three lists, not full drafts

- **Measured:** the public [ladder][ladder] now contains **159**, not 158, ranked rows. Seven unauthenticated requests to the page's own [JSON endpoint][api] returned 25/25/25/25/25/25/9 rows, 159 unique team IDs and consecutive ranks 1–159. Each response reported `updatedAt = 2026-10-13T18:41:05.729Z`; the retrieval ended at `18:45:18Z`. This is a single retrieval sweep, not a guaranteed transactional snapshot: some rating-history entries postdate that update marker.
- **Measured:** the browser's champion tooltips say, for example, **“Vendetta: 50 picks in the last 50 completed games.”** The API field is `mostPickedChampions`, with `champion` and `picks`. There are exactly three entries for 158 teams; rank 83, Atlas, has no entries and a 0–0 record. Text-only page extraction omits these icon tooltips; the analysis used the JSON and checked the rendered top-three tooltips.
- **Measured:** **118 teams have a displayed champion count greater than their W+L count**. Mite has 50 Vendetta picks but a 24–5 record; our team has 19 Varg picks but a 2–4 record. These counters therefore cannot be joined as though one pick observation equalled one recorded W–L result. The relationship between game/series counts and their windows is not established here.
- **Measured:** percentages below mean **fraction of teams whose displayed top three include a champion**. They do not mean fraction of games drafting that champion. Three to five selections are possible, so omitted fourth/fifth picks, tie ordering and historical bot changes can hide substantial usage. A missing icon means *unobserved in this top-three list*, not zero picks.
- **Documented:** the handbook permits 3–5 selections, no duplicates within a team, and mirrored enemy selections. Cassi & Issac is one selection with two bodies. [Draft][draft] [Cassi & Issac][cassi]
- **Hypothesis:** use these correlations to choose the next controlled experiment, not to claim that a particular opponent farms, fights, wards or uses a particular programming language. No opponent replays, source code or engine matches were inspected in this run.

**Labels throughout:** **Measured** = this ladder snapshot and arithmetic on it; **Documented** = cited handbook mechanics; **Hypothesis** = causal interpretation, expected impact, proposed implementation or acceptance threshold. Repository references identify the implementation being targeted, not measured opponent behavior. All proposed numerical gates below are untested targets.

## 1. Draft meta: Vendetta and the extra body distinguish the leaders

**Measured:** partition the complete ladder into **top 25 (ranks 1–25)**, **middle 109 (26–134)** and **bottom 25 (135–159)**. The middle includes Atlas's empty list; percentages deliberately retain every ranked row. The final column is the sum of a champion's displayed counts among the top 25, divided by **3,667 total displayed counts**. It is a *share of displayed picks*, not an uncensored game-pick rate.

| Champion | Top 25: teams (%) | Middle 109: teams (%) | Bottom 25: teams (%) | All 159: teams | Top-25 displayed counts (share) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Vendetta | 21 (84%) | 62 (56.9%) | 6 (24%) | 89 | 1,050 (28.6%) |
| Cassi & Issac | 17 (68%) | 47 (43.1%) | 8 (32%) | 72 | 846 (23.1%) |
| Varg | 14 (56%) | 69 (63.3%) | 13 (52%) | 96 | 681 (18.6%) |
| Ryth | 10 (40%) | 52 (47.7%) | 11 (44%) | 73 | 500 (13.6%) |
| Stellar | 5 (20%) | 18 (16.5%) | 2 (8%) | 25 | 244 (6.7%) |
| Tavi | 4 (16%) | 31 (28.4%) | 5 (20%) | 40 | 194 (5.3%) |
| Vesper Vale | 3 (12%) | 19 (17.4%) | 7 (28%) | 29 | 102 (2.8%) |
| Ren | 1 (4%) | 10 (9.2%) | 4 (16%) | 15 | 50 (1.4%) |
| Marcella | 0 | 8 (7.3%) | 4 (16%) | 12 | 0 |
| Prism | 0 | 6 (5.5%) | 12 (48%) | 18 | 0 |
| Willow | 0 | 2 (1.8%) | 3 (12%) | 5 | 0 |

**Measured — sensitivity checks:** the central 25 teams, ranks 68–92, show Vendetta 48%, Cassi & Issac 40%, Varg 52%, Ryth 40%, Tavi 40%, Stellar 16%, Vesper 24%, Ren 16%, Marcella 12%, Prism/Willow 0%. Restricting the bottom cohort to its 20 teams with at least 15 recorded results leaves Vendetta at 20%, Cassi & Issac at 25% and Prism at 50%; the principal contrast is not solely new-team noise. All top-25 teams already have at least 15 results.

**Measured — repeated lists:** seven top teams show Cassi & Issac/Varg/Vendetta; four show Ryth/Varg/Vendetta; four show Cassi & Issac/Ryth/Vendetta; three show Cassi & Issac/Stellar/Vendetta. However, **five bottom-25 teams also show Cassi & Issac/Varg/Vendetta**. The draft is not sufficient. Twenty top-25 teams show 50/50/50 counts for their three displayed champions, versus nine bottom teams; this shows concentration in the reported window, not necessarily an unchanging three-pick lineup.

**Measured — “never picked”:** no published champion is absent ladder-wide. Only **Marcella, Prism and Willow are absent from the top-25 display**. True never-picked champions cannot be identified from censored top-three data.

### Kits explain plausible mechanisms, not the winners' actual tactics

| Champion | Documented mechanic | Hypothesis: why it could matter, and the implementation obligation |
| --- | --- | --- |
| **Vendetta** | 70 base Strength, melee walk+attack, reset, two-step dash; **camp kills refresh both spell cooldowns**. Still only one cast per turn. [Kit][vendetta] [Combat][combat] | High baseline clearing and shorter travel compound across repeated captures. Prefer attack → reset → attack; choose a killable camp when it refreshes a useful next-turn dash/reset. Do not spend the cast on an unnecessary approach dash or assume a kill permits a second cast. This explains both economy and combat value; the ladder does not distinguish them. |
| **Cassi & Issac** | One selection supplies two independently acting bodies, bags and positions. Cassi has 2× Focus damage and a walk-compatible range-4 stun; Issac has reset/dash. Either death kills both and loses both bags. [Kit][cassi] | Extra attacks, capture occupancy and coverage can beat any small stat advantage. A pair can leave one capturer while the other clears nearby. The liability is two bodies/bags lost from one weak link: generic solo health checks are inadequate. Begin with a nearby visible pair, not disconnected cross-map routes. |
| **Varg** | Every basic attack also deals full Strength to other valid targets within radius 1; reset repeats it. Shield = 2.5× Focus for five turns, initially 250. [Kit][varg] | Cluster clearing without spending a damage-spell cast; shield can avoid a recall/death. Select the primary target by useful splash, not iteration order. Do not wake an unsafe second group. Varg's similar top/bottom presence means it is common infrastructure, not a strong rank discriminator alone. |
| **Ryth** | 1,200 Health, reset, range-4 radius-1 damage/stun; +1% of **bonus** Health as Strength. [Kit][ryth] | Durable clearing and a nearby anti-tribute tool make a practical no-pair fallback. Use the AoE before walking when interruption matters. His top/bottom prevalence gives no evidence for a special winning-only Ryth strategy. |
| **Stellar / Tavi** | Stellar: 200 single-target or 140-per-target AoE at base Focus. Tavi: 220 damage plus stun, reset, field shard purchases. Their damage spells exclude walking. [Stellar][stellar] [Tavi][tavi] | An unimplemented damage spell wastes much of these kits. Tavi can turn capture gold into power without recalling, but fragility and stationary casts require support from the action policy. Neither is established as a mandatory top-team pick. |
| **Vesper / Ren** | Vesper: +20% gold, reset/dash. Ren: 0.2× Focus retaliation per damaging event, stun/dash. [Vesper][vesper] [Ren][ren] | Gold only helps primary score after reinvestment; retaliation is not damage reduction. Both remain experiments, not v4 defaults. |
| **Marcella / Prism / Willow** | Marcella is stun-immune with 1,200 Health. Prism gains 0.2 Focus per carried gem. Willow heals **another** ally for 3× Focus, but cannot self-heal. [Marcella][marcella] [Prism][prism] [Willow][willow] | Marcella is still a valid anti-stun carrier, but the measured meta does not support her as an automatic first pick. Hoarding 50 Prism gems buys only 10 Focus (+15/+10 spell damage), delaying score and increasing exposure. Willow must repay the lost independent farmer with saved recovery time. Absence from top lists does not prove any of these kits is weak. |

**Documented — fuel distinction:** the fuel chapter gives **per-bot**, language-dependent budgets, not champion-specific multipliers: Python normally receives 2.5 million; C++/Rust 100,000. Unused fuel cannot carry forward; exhaustion resumes the suspended instruction next round. [Fuel][fuel] Combined with the duo's separate turns, four active bodies instead of three provide **33% more aggregate turn opportunities**; six instead of five provide **20% more**. This is not a larger personal budget or permission to move unused fuel between champions. [Cassi & Issac][cassi]

**Hypothesis — compute advantage:** simple melee reset policies may deliver more useful actions per unit of policy code than AoE targeting/support logic. This is a profiling hypothesis, not measured ladder fuel headroom. Extra-body throughput only exists while both linked bodies survive.

## 2. Performance structure: rating is not a farming/combat classifier

**Measured — cohort outcomes:** W–L below sums the displayed records, not the last-50-games draft window. The pooled rate weights teams by number of recorded results; it is not the average team rate or a champion win rate.

| Cohort | Rating range | Mean rating | Pooled W–L | Pooled win rate | Median recorded results |
| --- | ---: | ---: | ---: | ---: | ---: |
| Top 25 | 1,560.56–1,662.08 | 1,587.20 | 593–400 | 59.7% | 40 |
| Middle 109 | 1,446.82–1,558.55 | 1,503.52 | 1,715–1,725 | 49.9% | 35 |
| Bottom 25 | 1,230.78–1,444.99 | 1,404.57 | 340–510 | 40.0% | 33 |

**Measured — steepest displayed gains:** every one of the **158 non-null 7d deltas equals current rating minus 1,500**. Thus the 7d column supplies no independent momentum ranking in this launch-day snapshot. These are largest net gains, not fitted hourly slopes, recent-version effects or seven days of evidence.

| Team (rank) | Rating | 7d change | W–L | Win rate | Displayed top three |
| --- | ---: | ---: | ---: | ---: | --- |
| Mite (1) | 1,662.08 | +162.08 | 24–5 | 82.8% | Cassi & Issac / Varg / Vendetta |
| WHIM (2) | 1,648.95 | +148.95 | 33–12 | 73.3% | Ryth / Varg / Vendetta |
| NOVA (3) | 1,635.34 | +135.34 | 22–5 | 81.5% | Ryth / Tavi / Vendetta |
| KratosMessi (4) | 1,616.40 | +116.40 | 29–20 | 59.2% | Cassi & Issac / Varg / Vendetta |
| Nyx (5) | 1,607.76 | +107.76 | 31–21 | 59.6% | Cassi & Issac / Stellar / Vendetta |
| What da (6) | 1,604.78 | +104.78 | 17–10 | 63.0% | Ryth / Varg / Vendetta |
| Ely2sh (7) | 1,597.65 | +97.65 | 23–12 | 65.7% | Cassi & Issac / Stellar / Vendetta |
| BottleBots (8) | 1,593.69 | +93.69 | 10–5 | 66.7% | Ryth / Varg / Vendetta |
| procless (15) | 1,572.86 | +72.86 | 13–3 | 81.3% | Ryth / Stellar / Vendetta |
| Quantum Altar Keepers (117) | 1,468.17 | −31.83 | 2–4 | 33.3% | Varg 19 / Prism 18 / Vesper 18 |

- **Measured:** Mite reaches first with 29 recorded results, while `:3` has 62 and ranks 19; PTN Ares has 61 and ranks 152. Pearson correlation across the 158 nonempty records is **0.634 for rating versus win fraction**, but only **0.114 for rating versus result count**. More recorded games is not a reliable explanation for being stronger.
- **Measured:** orZers is 28–28 at rank 17; `we were fed fish` is 28–25 at rank 135. Conversely, procless is 13–3 at rank 15, below teams with much lower raw win fractions. A pooled W–L summary cannot reconstruct rating order.
- **Hypothesis:** opponent strength, result ordering, rating-update rules and bot revisions can explain these differences. Neither “fast climb = efficient farming” nor “many games = combat bot” is identified by these fields. The useful visible signature is concentrated high-throughput kits, not observed early aggression. Replays with first-tribute time, deaths, stolen bags and camp throughput would distinguish these explanations.
- **Measured:** the steepest negative deltas are gold digger −269.22 (3–29), `:blauerdrache:` −139.10 (19–34), and Signal −130.82 (2–13). Our own six recorded results are too few to characterize a stable win rate; the snapshot gap to rank 25 is **92.40 rating**, not a forecast that any one feature will gain 92 points.

## 3. What to change relative to our baseline

**Hypothesis — scope and implementation context:** target the farming/tribute baseline in [draft.py](../bots/main/src/draft.py) and [bot.py](../bots/main/src/bot.py), not the stale root README description. Source inspection finds random drafting; generic resets/dashes but no general damage/stun/shield/heal casting; first-eligible enemy attacks; immediate banking for any nonempty bag; Strength-only Power purchases; local warding/enemy memory; and no draft/live-memory coordination. The [playbook](strategy-playbook.md) already proposes more than this implementation supplies. Treat these as targets to recheck against the incoming v3 diff, not instructions to overwrite work already completed.

**Hypothesis — handoff boundary:** the [parent thread][parent] reports v3 in flight with map-feature drafting, bounded two-round exchanges, Corners repair and hunter/altar/camp-denial sparring. Extend those components when they arrive; do not implement a parallel combat planner. The priorities below estimate marginal rating impact from frequency, cost and severity. They are **not measured feature-to-rating effects**.

| Priority / expected impact | Hypothesis: concrete missing capability | Documented reason / measured evidence |
| --- | --- | --- |
| **1 · High** | Intentional meta draft **plus complete kit execution**. Promote Vendetta; evaluate Cassi & Issac now rather than deferring to Sprint 3. Choose useful Varg splash targets, shield before lethal exposure, and cast damage/interrupts before spending movement. | **Measured:** strongest top/bottom contrasts are Vendetta and the duo. **Documented:** one cast, melee walk+attack, reset/kill-refresh and splash create distinct action opportunities. [Combat][combat] [Vendetta][vendetta] [Varg][varg] |
| **2 · High, coupled to #1** | Linked-pair survival and team objective allocation. Treat the duo as two bodies with one death liability; allocate other farmers separate openings; one capturer per group; continue nearby work during capture. | **Documented:** either duo death loses both bags; extra allies do not speed capture. [Cassi & Issac][cassi] [Camps][camps] **Measured:** the same popular trio occurs at both ends of the ladder, so execution must earn its slot. |
| **3 · High** | Delivery-aware combat: choose the carrier/interruptor rather than the first enemy; deny enemy channels at a known actionable moment; break a three-hit lock with reset attacks when safer/faster than detouring. Preserve own scoring before chasing. | **Documented:** nonlethal damage does not cancel tribute; stun, death and locks do. Marcella ignores stuns, not locks or death. [Gems][gems] [Marcella][marcella] |
| **4 · Medium–high** | Improve entire clear/capture/bank/recovery cycles. Stop optimistic allied-DPS accounting for allies who are leaving or unable to attack; evaluate batching only when the additional route stays safe. Spend for the chosen kit, not one global build. | **Documented:** gold is not primary score; Tavi can buy shards in-field; capture/tribute have fixed timing costs; death costs 60 rounds. [Gems][gems] [Tavi][tavi] [Camps][camps] [Death][death] |
| **5 · Medium, reliability prerequisite** | Budget compute before adding search; make wards goal-directed and share one fresh danger alert if v3 has an existing memory protocol. Keep safety/tribute/attack decisions ahead of optional rescoring. | **Documented:** private vision/wards, only 8 live shared bytes, suspension on exhaustion. [Vision][vision] [Memory][memory] [Fuel][fuel] **Hypothesis:** a lower search budget that acts every round beats a sophisticated stale plan. No winner fuel or ward-coverage data is available. |

## 4. One-page v4 implementation directive

**Hypothesis — implement in this order; all constants are initial policy choices, not discovered optimal values.** Preserve v3 correctness and its existing state/legality checks. Implement in `draft.py` and the existing `Bot`; do not add whole-game search, learned policies, permanent deathballs or opponent identification.

1. **P0 — draft and promotion switch.** Candidate A's ordered selections are **Cassi & Issac, Vendetta, Varg, Ryth, Tavi**; take the first 3–5 using SDK draft IDs. Candidate B is **Ryth, Vendetta, Varg, Tavi, Marcella**. Default to B until A passes Gate 3; promote A only if it also passes Gates 1–2. Do not change this roster by map ID. Compare with the frozen v3 roster, not random redrafts. [Draft][draft]
2. **P0 — spend the whole legal turn.** Extend v3's short-exchange evaluator with each selected kit. Before movement, prefer a legal stun on a submitting non-Marcella enemy, then a safe kill, then PvE damage. For a stationary reset user, attack → reset → attack; retain the one-cast limit after Vendetta kills. Use Varg's shield instead of reset if the forecast next hostile phase would leave less than 25% maximum Health and the shield restores that reserve. Choose Varg's primary target by summed useful splash damage, rejecting newly awakened groups that fail the survival reserve. Use Cassi's damage or Ryth/Tavi's damage-stun when stationary and worthwhile; do not walk away their cast. [Combat][combat] [Cassi][cassi] [Ryth][ryth] [Tavi][tavi] [Varg][varg]
3. **P1 — pair/route contract.** During draft assign one first group to the duo and distinct reachable first groups to other farmers, greedily by predicted travel+clear+capture+bank time; tie by group ID. Fall back to existing safe selection if there are too few groups. Initially rendezvous at the assigned group's nearest safe approach; the following guard restricts fights, not safe rendezvous travel. Cassi and Issac must be mutually visible within distance 4, both above 50% Health, with predicted remaining Health above 25% on both before initiating. If either fails, stop initiation and retreat/recover; if the partner becomes unseen, reconnect toward its last position only along a safe path, otherwise recall. Cassi captures; Issac vacates the capture region and works only within that visibility/distance leash. Leave after observed reward, not a guessed timer. [Cassi & Issac][cassi] [Camps][camps]
4. **P1 — deliver and interrupt.** Bank at 40+ gems, on a current/last-seen interception threat, or when the next route cannot finish before the horizon. Below 40, add at most one group only if resulting bag is at most 60, forecast Health stays above 50%, and complete delivery is at most 12 rounds later than banking now; otherwise bank now. Before our channel, ward the approach and place any protective lock before allies start. Against an enemy channel, lock/stun at the first safe legal opportunity; against Marcella use lock or lethal damage. Never leave a live safe tribute merely to land nonlethal damage. Recheck state after lock-breaking attacks/reset. [Gems][gems] [Vision][vision]
5. **P2 — upgrades and fuel.** Buy Monster Strength for Vendetta/Issac/Varg; first Jungle Health instead where the assigned damaging group fails the 25% survival reserve. Cassi buys Power Focus; Tavi buys Power Focus in-field; Ryth/Marcella retain Strength unless the survival test requires Health. Do not buy Focus for Issac/Vendetta. Reserve 10 gold for one lock before shards at a legal shop. Stop optional search/ward rescoring below **1.2 million remaining Python fuel**; cap added tactical evaluation at **350,000 fuel** and reuse the incumbent fallback. Check the actual runner budget before applying those thresholds. [Items][items] [Fuel][fuel]

**Hypothesis — deferred v4+ work:** only after these gates, test independently split duo routes, map-conditioned Marcella inclusion, wider team memory and deeper combat search. If Candidate A fails, ship B only if B independently passes the non-duo gates; do not weaken safety thresholds to force the meta trio through.

## 5. Three gates beyond starter wins

**Hypothesis — common protocol:** freeze v3 and all opponent policies before evaluation. Use all nine official maps, both sides, full 2,000-round limit and the actual default fuel. A 9×2 panel gives 18 deterministic cases, not 18 independent random trials; repeated identical runs add no evidence. Keep a per-map result table. Treat faults, logged exceptions and fuel suspensions as gate failures, never drop them from the denominator. Log tributed gems at round 500/final, time to first tribute, deaths, gems lost/stolen, duplicate-capture occupancy, completed/cancelled channels and worst-turn fuel.

| Gate | Hypothesis: opponent/scenario and exact pass condition | What a failure distinguishes |
| --- | --- | --- |
| **1. Beat meta-shaped farmers, not just starters** | Three fixed scripted farmers with **Cassi & Issac/Varg/Vendetta**, **Ryth/Varg/Vendetta**, and **Ryth/Tavi/Vendetta** cores; append the first unused Ryth, Tavi, Varg, Cassi & Issac as maps require. All split available routes, finish captures, bank at 40, and use their actual resets, damage spells and escape rules. They do not hunt. Run 18 cases each: candidate must win **at least 11/18 against each**, and **at least min(54, frozen-v3 total wins + 6)** on the same panel. Calibrate every opponent to clear, capture and tribute without faults before counting results. | Draft/action throughput versus a competent scoring race. This is a surrogate for the observed draft meta, **not a clone of Mite or WHIM**. |
| **2. Survive and punish targeted disruption** | Extend the v3 sparrers: **Vendetta carrier hunter** targets the largest visible bag, abandons fog chases after three turns; **Ryth lock/stun defender** waits at the nearest contested altar and interrupts channels; **duo hunter** attacks the more vulnerable visible Cassi/Issac body to trigger linked death. Other bodies keep farming. Require **at least 11/18 wins against each** and aggregate carried gems lost to death **no greater than v3's** on the identical panel. Include timing probes for first/last actionable channel interruption, Marcella immunity and nonlethal-damage continuation under both team orders; score completion/cancellation, not merely an ability call. | Whether safety survives the specific mobility, stun and linked-death pressures the kits enable. These behaviors are hypotheses, not ladder-observed tactics. |
| **3. Earn the extra body; reject fuel regressions** | Reuse Gate 1's first opponent to compare A and B on the same 18 map/side cases; no duplicate reruns. A must win **at least 2 more cases than B**, produce **at least 10% more total tributed gems by round 500**, and lose **no more total carried gems to deaths**. If a match ends before 500, use its final score. Require zero fuel suspensions/faults for both and at least **250,000 fuel remaining at deliberate normal-turn yield** on the exercised Python turns. Also probe isolated lethal threats to each duo body and an occluded partner; both must stop initiating new fights when the pair contract fails. | Extra-body productivity versus double-death exposure; genuine aggregate gain versus a new bot instance that only consumes resources. A failure selects B, not an undocumented exception. |

**Hypothesis — regression floor:** retain at least 17/18 versus `starter-python`, 18/18 versus `starter-cpp`, zero logged exceptions/faults, and any stricter Corners/sparring gate already passed by v3. Those incumbent results were reported by the [parent thread][parent], **not rerun or measured from this ladder**. Gates 1–3 are proposals, not completed verification or promised ladder gains.

## Snapshot audit and sources

**Measured — aggregation checks:** cohort sizes 25+109+25 = 159; displayed entries 75+324+75 = 474; displayed-count sums 3,667+14,169+2,848 = **20,684**. The all-ladder presence counts sum to 474. W–L totals are **2,648–2,635**, with zero displayed draws; each row's `matches` equals wins+losses. These are team-side observations, not 5,283 unique games. The totals need not balance across this ranked subset/window.

**Measured — acquisition recipe:** the browser loaded `/api/v1/ladder?page=1&pageSize=25&category=all`; the same endpoint was read for pages 1–7 without credentials. Use `teamId` for uniqueness, not names: two rows are named Midnight Wardens. For each cohort, count each `mostPickedChampions[].champion` once per team; separately sum `.picks`. Compute pooled win rate as sum(wins)/sum(wins+losses), excluding the 0–0 row only from correlations that require a win fraction. Re-fetching later gives a new snapshot, not this one. The seven captured responses, serialized with sorted keys and UTF-8 JSON, had SHA-256 `78d288f6a0b735db9ef9ce856746d852fbc8fcb985f98af084969c88da60c624`; raw responses were temporary analysis input, not another repository deliverable.

**Measured — top-25 source counts for audit:** all listed champions have count 50 unless a count follows the name. These are the displayed lists, not full lineups.

| Rank | Team | Displayed top picks |
| ---: | --- | --- |
| 1 | Mite | Cassi & Issac, Varg, Vendetta |
| 2 | WHIM | Ryth, Varg, Vendetta |
| 3 | NOVA | Ryth, Tavi, Vendetta |
| 4 | KratosMessi | Cassi & Issac, Varg, Vendetta |
| 5 | Nyx | Cassi & Issac, Stellar, Vendetta |
| 6 | What da | Ryth, Varg, Vendetta |
| 7 | Ely2sh | Cassi & Issac, Stellar, Vendetta |
| 8 | BottleBots | Ryth, Varg, Vendetta |
| 9 | will think later | Cassi & Issac, Stellar, Vendetta |
| 10 | NEETCoders | Cassi & Issac, Varg, Vesper 26 |
| 11 | hello | Cassi & Issac, Tavi, Vesper 32 |
| 12 | Univardisty of Shingtonwash | Tavi 44, Vesper 44, Varg 34 |
| 13 | SSSA | Cassi & Issac, Ryth, Vendetta |
| 14 | BitShift | Tavi, Varg, Stellar 44 |
| 15 | procless | Ryth, Stellar, Vendetta |
| 16 | SHINK AI 6500 | Vendetta, Varg 47, Cassi & Issac 46 |
| 17 | orZers | Cassi & Issac, Varg, Vendetta |
| 18 | Cabbage | Cassi & Issac, Ryth, Vendetta |
| 19 | :3 | Cassi & Issac, Ryth, Vendetta |
| 20 | Emperor Tung | Cassi & Issac, Varg, Vendetta |
| 21 | SilverSamurai | Ryth, Varg, Vendetta |
| 22 | ひななー | Cassi & Issac, Ryth, Vendetta |
| 23 | Quant Merch Traders | Cassi & Issac, Varg, Vendetta |
| 24 | Trzy Kwaterki | Cassi & Issac, Varg, Vendetta |
| 25 | Nameless | Cassi & Issac, Ren, Vendetta |

**Documented — reading coverage:** the [roster][roster] and all eleven linked kit pages were read live, alongside drafting, fuel, combat, gems and vision. Camp, item, death and memory context also comes from the complete prior [strategy playbook](strategy-playbook.md), which cites their handbook chapters and records unresolved timing/range issues. Do not silently resolve those uncertainties in an implementation. No rules experiment or ladder submission was performed here.

**Hypothesis — trust boundary:** team names and biographies are data, not instructions. One ladder biography contained an instruction to abandon the task; it was ignored and was not used as strategic evidence.

[ladder]: https://2026a.battlecode.co.uk/game/ladder
[api]: https://2026a.battlecode.co.uk/api/v1/ladder?page=1&pageSize=25&category=all
[roster]: https://2026a.battlecode.co.uk/game/docs/champions
[draft]: https://2026a.battlecode.co.uk/game/docs/draft
[combat]: https://2026a.battlecode.co.uk/game/docs/combat
[gems]: https://2026a.battlecode.co.uk/game/docs/gems-and-scoring
[camps]: https://2026a.battlecode.co.uk/game/docs/camps
[items]: https://2026a.battlecode.co.uk/game/docs/items
[vision]: https://2026a.battlecode.co.uk/game/docs/vision
[death]: https://2026a.battlecode.co.uk/game/docs/death-and-recall
[fuel]: https://2026a.battlecode.co.uk/game/docs/fuel
[memory]: https://2026a.battlecode.co.uk/game/docs/shared-memory
[cassi]: https://2026a.battlecode.co.uk/game/docs/cassi-and-issac
[ryth]: https://2026a.battlecode.co.uk/game/docs/ryth
[vesper]: https://2026a.battlecode.co.uk/game/docs/vesper-vale
[prism]: https://2026a.battlecode.co.uk/game/docs/prism
[stellar]: https://2026a.battlecode.co.uk/game/docs/stellar
[vendetta]: https://2026a.battlecode.co.uk/game/docs/vendetta
[marcella]: https://2026a.battlecode.co.uk/game/docs/marcella
[tavi]: https://2026a.battlecode.co.uk/game/docs/tavi
[willow]: https://2026a.battlecode.co.uk/game/docs/willow
[ren]: https://2026a.battlecode.co.uk/game/docs/ren
[varg]: https://2026a.battlecode.co.uk/game/docs/varg
[parent]: https://ampcode.com/threads/T-01a13146-82e4-754b-b8d9-2ed17ef0105f
