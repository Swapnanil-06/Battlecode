# Cambridge Battlecode ’26 Autumn: strategy playbook

**Post-reveal rules snapshot · 13 October 2026 · Europe/London**

**Recommendation:** build a reliable **clear → capture → deliver → tribute** bot before a sophisticated fighting bot. Default to **Marcella + Tavi + Varg** on clustered-camp maps; replace Varg with **Vendetta** on sparse, safe farming routes. Protect carriers, use free wards, spend gold, and finish channels correctly. These are rules-derived hypotheses, **not measured tier rankings or win-rate claims**.

**Evidence:** read the complete official [GameRules.md download][agents], all twelve rules chapters, the [glossary], and all eleven published champion-kit pages. The export includes details hidden in interactive diagrams. Its SHA-256 was `1d4259246a45ca7de4c446f18423779efc2a70772521e11bb8c61a70156173b6`. The [public homepage][event] advertises a twelfth entry, **“Restricted — Under containment,” but publishes no kit or handbook link**. The handbook lists eleven selectable entries, with Cassi & Issac supplying two bodies. Do not invent a twelfth selectable champion from either the teaser or the sidebar’s “12 pages” count.

**Labels:** **Rule** means documented in the cited handbook, not independently engine-tested here. **Recommendation / hypothesis** means our strategic judgment. **Uncertain** means missing or conflicting documentation; section 5 gives the required checks. No matches were run for this document.

## 1. Rules digest: optimize delivered gems, not damage dealt

### Winning and the economy

- **1,000 tributed gems wins immediately.** Otherwise the game ends at the 2,000-round limit and compares, in order: **tributed gems → lifetime gold earned → champion kills → Team B** (the team that acted second in round one). Carried gems are not a tiebreak. Spending gold does not reduce lifetime earnings. A local runner can use a shorter horizon, so its configuration matters. [Objective]
- **Carried gems are unsecured; tributed gems are permanent team score.** There is no documented teammate gem-transfer action. Choose who receives a camp reward rather than designing around an assumed courier handoff. A kill grants the killer the victim’s entire bag plus 50 base gold; a camp kill destroys the bag. The export says assists award no gold. [Gems] [Death] [Bundle][agents]
- **Camp ownership comes from capture, not the last hit.** Monsters in cardinally connected groups must all die. Occupy their former tiles uncontested to start a five-round capture timer. The export specifies that one capture phase starts the timer and later phases decrement it: arriving on a tile is not already a capture tick. Wait for the actual reward, not a guessed five iterations. Empty or contested regions reset progress; extra allies do not accelerate it. Allies present split rewards, with integer remainder to the lowest ID. [Camps] [Bundle][agents]
- **Respawn starts after reward capture, not after the kill.** A group uses its longest member cooldown and respawns together only when every spawn tile is free. Leave the region after collecting unless deliberately denying a respawn. Camping on a cleared tile can suppress our next harvest. [Camps] [Bundle][agents]

| Monster | Health | Damage | Listed attack range | Gold | Gems | Respawn after capture |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Gem cluster | 500 | 0 | 0 | 0 | 24 | 50 rounds |
| Gold cluster | 500 | 0 | 0 | 35 | 0 | 50 rounds |
| Wolf | 1,350 | 20 | 3 | 90 | 22 | 40 rounds |
| Elk | 2,400 | 60 | 3 | 160 | 36 | 60 rounds |
| Monolith | 20,000 | 200 | 5 | 300 | 200 | 150 rounds |

Source: [Camps]. **Uncertain:** that same page later says *all* monsters have range 3, contradicting the table’s monolith and cluster entries. Its sleep descriptions also disagree: “no damage for two turns” versus “two rounds without an in-range champion.” Until verified, budget for the larger plausible threat range and do not depend on sleep timing. Monsters do not chase, see through bushes, and wake as a group when damaged.

**Strategic consequence:** a standalone gem cluster provides 24 gems for 500 damage, versus a wolf’s 22 for 1,350 damage: approximately **2.95× the gems per damage**, without retaliation. This is not a 2.95× win-rate or throughput advantage: travel, capture, group membership, gold and respawn dominate some routes. A gem cluster connected to an elk is not a free 500-health objective; clearing the whole group is mandatory. Prioritize reachable safe gem groups, then gold that materially shortens later cycles; do not open on a monolith. [Camps]

### Tribute, recall and teleport have different interruption rules

| Channel | Duration in owner turn ends | Damage | Stun / death | Manual cancel | Practical consequence |
| --- | --- | --- | --- | --- | --- |
| Tribute | Starting bag ÷ 10, rounded up; minimum 1 | Continues | Cancels | Yes | Survive the channel; a nonlethal hit is not itself a reason to abandon it. |
| Recall | 5; Home emblem reduces it to 3 | Cancels | Cancels | Yes | Escape threat range before starting. |
| Teleport crystal | 3 | Continues | Cancels | No | A committed delayed reposition, not an instant escape. |

Sources: [Turn], [Gems], [Combat], [Death], [Items]. A newly placed altar lock also cancels tribute. All timers count the turn on which the channel starts, reach zero at a turn **end**, and resolve at the owner’s next turn **start**. Starting a one-tick tribute on the final actionable turn does not bank gems immediately.

- Tribute from any of the **eight neighboring tiles** of an altar; the altar itself is not walkable. A bag of 22 needs three countdown ticks, 24 needs three, 48 needs five. The duration uses the **starting** bag, but completion deposits the **whole current** bag, including a capture reward received meanwhile. Captures resolve before channels. [Gems]
- An **altar lock costs 10 gold**, is placed within range 2, and blocks enemy tributes while allowing its owner’s team through. It takes **three basic attacks**, not a damage threshold, to remove. Attempting to tribute against an enemy lock becomes a basic attack against it: do not treat that call as successful channel initiation. Place our lock before our carrier starts; cancellation on lock placement needs an ownership boundary test. [Gems] [Items]
- **Death costs 60 rounds**, potentially longer if no spawn tile is available; the export describes respawn at a turn start after the countdown, at full health with abilities reset. Dead champions still shop. Cassi and Issac die together and surrender both bags for one kill reward. [Death] [Bundle][agents]
- Recall retains gems. Arriving on spawn is not the full heal: **stay until that turn’s end**. Shop before leaving. A five-tick recall plus recovery and travel is usually cheaper than death, but compare that complete downtime with continuing a safe route. [Death]

### Action economy and resolution order

**A turn is not “choose one action.”** Every champion normally gets a walk, a basic attack and one successful ability cast, subject to these restrictions. [Turn] [Combat]

| Action | Rule | Bot implication |
| --- | --- | --- |
| Walk | One tile, eight directions | Use SDK movement legality; target a free attack/capture/tribute position, not an occupied monster or altar tile. |
| Melee basic attack | Range 1, visible target, damage = Strength before modifiers | Can walk and attack in the same turn. |
| Ranged basic attack | Range 3; normal walking and attacking consume each other’s allowance | No ordinary move-and-shoot kiting. An attack reset can restore the attack allowance after walking. |
| Ability | One successful cast across both slots per turn; each slot has an eight-owner-turn-end cooldown | Slots can be used on consecutive turns, not together. A cooldown reset does not remove the one-cast limit. |
| Attack-reset ability | Restores basic attack | Prefer attack → reset → attack when stationary; walking → reset → attack is also valuable for ranged units. Do not infer that reset restores movement. |
| “Excludes walking” ability | Cannot share a turn with an ordinary walk | Choose the spell before greedily moving. It can still accompany an available basic attack. |
| Ward / consumable / shop | Separate charge, inventory and location restrictions | Do not waste a whole turn merely because one of these was used. |
| Channel / stun / death | Channel: cancellation only where allowed; stun: no actions; dead: shop only | Handle these states before running movement or combat logic. |

The [Markdown export][agents] gives the fuller order:

1. **Round start:** camp respawns; existing spell/ward updates; camp captures; camp actions.
2. **Champion turns:** teams alternate execution slots, with the starting team swapping each round. Within each team, higher priority acts first, then draft order. `set_priority` persists and affects the **next** round.
3. **Champion turn start:** resolve zero timers for respawn, ward recharge, buff/shield expiry, then channels.
4. **Champion turn end:** decrement timers; apply spawn recovery. Zero countdowns wait for the next start to resolve.

**Consequences:** an awakened camp can hit before our next action; a shield expiring at turn start cannot protect a later exchange; capture rewards can enter a pending tribute; a stun’s value depends on the target’s execution slot. Never model all allies acting before all enemies, or assume one fixed team always moves first. [Turn]

### Map, movement and private vision

- Maps are grids from 30×30 to 100×100. Ranges use **Chebyshev distance**: diagonals count as one. Walls block sight and walking/dashes; holes block walking but not sight and can be dashed over; bushes are walkable and obscure vision. Dashes reach up to two legal steps; crystals reach three tiles and ignore intervening terrain. The export forbids landing on walls, holes, altars, enemy spawn or occupied tiles. **The map table’s “TP Crystal can reach walls” conflicts with this; do not plan a wall landing.** [Maps] [Bundle][agents]
- Each champion sees radius 8 using symmetric shadowcasting, **plus only its own ward**. Teammate sight and wards are **not** shared. From outside, bushes hide their interior and tiles beyond; from inside, the connected bush cluster is transparent to that champion, but other bushes still block. Holes do not block sight. [Vision]
- Each champion has one free permanent, indestructible ward: placement within range 2, vision 6, charge refreshed after one round. Replacement removes the old ward. Scout an altar approach or bush before committing; do not relocate a useful rear alarm reflexively every turn. [Turn] [Vision]
- SDK movement masks account for **visible** occupants, not hidden enemies. A hidden blocker makes the attempt return `false`, reveals its tile for the rest of the round, and consumes no move, ability cooldown or crystal. Reobserve and try a different destination with a bounded retry count. A destination already known to be occupied raises an error instead. [Maps]

**Consequence:** knowing the terrain from draft is not knowing where enemies currently are. Maintain last-seen information with age, and distinguish “unseen” from “empty.” A shared-memory warning does not make a unit a legal visible target for a unit-targeted spell. [Draft] [Vision] [Combat]

### Gold, items and durable scaling

Shards cost **30 gold** and add that champion’s growth in Strength, Health or Focus. Five identical shards automatically make an emblem for **150 total gold**; stats apply immediately, the family passive only on completion. Buy at spawn or while dead; Tavi alone can buy shards in the field. Buying Health on spawn heals the added amount; Tavi’s field Health does not heal. [Items] [Tavi]

| Emblem family | Stat value | Passive |
| --- | --- | --- |
| Monster | 5 chosen-stat shards | +10% damage to camps |
| Power | 6 chosen-stat shards | No additional passive |
| Durability | 5 chosen-stat shards | −10% incoming damage |
| Treasure | 5 chosen-stat shards | +20% gold gained |
| Jungle | 5 chosen-stat shards | −30% camp damage |
| Home | 5 chosen-stat shards | Recall five ticks → three |
| Bruiser | 5 chosen-stat shards + 1 of each other stat | No additional passive |

Stats stack, including duplicate emblems, but a family’s passive **does not stack with itself**. Vesper’s +20% gold and Treasure’s +20% add to **+40%, not +44%**. Only Tavi sells, at spawn for full purchase price; refunds are not earned gold. Locks and teleport crystals each cost 10 gold, with at most one of each held. [Items]

**Recommendation:** buy useful stats before stockpiling gold, and complete a useful first family before scattering purchases just to chase passives. Strength improves repeated farming attacks; Health/Jungle can enable a camp that otherwise kills us; Focus improves actual scaling spells. **Do not buy Focus for Vesper, Vendetta or Issac merely because they have abilities:** their documented reset/dash kits have no Focus multiplier. Ryth gains only **1 Strength per +100 bonus Health**, not 1% of total health. [Items] [Ryth] [Vesper] [Vendetta] [Cassi]

### Draft, fuel and team memory

- A map specifies **3–5 draft selections per team**. Picks are simultaneous each step and revealed as the draft proceeds. No duplicate within our team; the opponent may select the same champions, so this is **not pick denial**. Cassi & Issac cost one selection and each get a body, bag, bot instance and turn. The entire map and initial camps are visible during draft. Missing a pick through yielding, crashing or fuel exhaustion results in random remaining selections. [Draft] [Cassi]
- **1,024 bytes of draft memory** are writable only in draft, then read-only to every champion. **8 bytes of match memory** are readable/writable throughout the match and private to the team. These are communication budgets, not a statement that each bot has only eight bytes of local state. [Memory]
- Wasmtime fuel is deterministic instruction-like computation, not wall time. Limits below are the handbook defaults; unused fuel does not carry over. **Exhaustion suspends execution and resumes at the same instruction next round**, risking actions based on a now-stale observation. Return/yield deliberately with budget in reserve. [Fuel]

| Language | Normal turn | First draft turn (10×) | First play turn (2×) |
| --- | ---: | ---: | ---: |
| C++ / Rust | 100,000 | 1,000,000 | 200,000 |
| OCaml | 500,000 | 5,000,000 | 1,000,000 |
| Python | 2,500,000 | 25,000,000 | 5,000,000 |

The homepage still says Python gets 20×; **use the current fuel chapter’s 25× as the documented default and verify the actual runner configuration**, not the marketing FAQ. The 10× allowance is for the first draft turn, not every pick. [Fuel] [Event][event]

**Week-one memory plan — proposed, not an SDK contract:** store a versioned shortlist of camp groups, altars, champion roles and route waypoints in draft memory; a 100×100 terrain grid does not fit uncompressed into 1,024 bytes. Use the 64-bit live buffer for one high-value alert: 7-bit x + 7-bit y + 3-bit event kind + 3-bit sender slot + 11-bit observation round + 11-bit expiry round + 22 reserved = 64. Coordinates fit 0–99; round fields fit 0–2,000; sender slots support the extra Cassi/Issac body. Define “none,” freshness, severity and replacement rules. A later writer must preserve a fresher higher-priority carrier/altar warning. Do not try to broadcast everyone’s vision; normal roles come from the draft plan. [Draft] [Memory] [Vision]

## 2. Champion tiers: value per implementation hour

**These tiers rank week-one bot suitability, not proven combat strength.** S means the proposed default implementation set; A means a strong map-dependent alternative; B means coordination or risk management must earn the slot. All champions have vision 8, walk 1, one cast per turn and eight-tick ability cooldowns. Listed Health / Strength / Focus are base values before equipment and passives. [Roster]

| Tier | Champion; base H / S / F | Concrete value and minimum policy | Why not an unconditional pick? |
| --- | --- | --- | --- |
| **S** | **[Marcella]**; 1,200 / 45 / 50; melee | **Stun immune**: unusually reliable tribute carrier. Slot 0 resets attack and makes the next enhanced hit stun; slot 1 deals 2× Focus at range 4, excluding walking. Simple attack → reset → stunning attack; prioritize the enemy interruptor. | Immunity does not stop death or altar locks, and does not protect recall from damage. No dash; poor delivery routes still lose. |
| **S** | **[Tavi]**; 750 / 35 / 100; ranged | Field shard purchases convert capture gold into power without a shopping trip. Reset plus **220 base damage and stun at range 4** gives simple farm/combat value. Buy after reward, then re-evaluate target and survival. | Fragile; cannot move with the damaging stun, self-heal through field Health, or buy field consumables. Sustain still matters. |
| **S on clustered maps; A otherwise** | **[Varg]**; 1,000 / 50 / 100; melee | Basic attacks splash **full Strength** to other valid targets within radius 1 of the primary target; primary is not double-hit. Reset multiplies this value. Slot 1 gives a **250-base shield for five turns**. Choose the target covering the most useful health; shield before expected burst. | Splash can awaken more monsters than we can survive. Shield and reset compete for this turn’s cast; do not model both. |
| **A** | **[Vendetta]**; 800 / 70 / 100; melee | Highest listed base Strength; reset and two-step dash. **Camp kills also refresh both ability cooldowns.** Fast isolated clusters and finishers make resets cheap; kill, then exploit the refreshed dash on a later turn. | Kill reset does not permit a second cast this turn. Low Health relative to damage, no stun; chasing carriers through fog can throw our own bag. |
| **A** | **[Ryth]**; 1,200 / 50 / 100; melee | Durable farmer/escort. Range-4, radius-1 spell deals 100 base damage and stuns, or use attack reset. Good on adjacent groups and clustered enemy channels. Health purchases also add 1% of the bonus as Strength. | AoE stun excludes walking; passive’s damage gain is modest. Unlike Marcella, Ryth can be stunned out of tribute. |
| **A** | **[Stellar]**; 750 / 35 / 100; ranged | Two uncomplicated range-4 damage spells: **200 single-target** and **140 per target in radius 1**, on separate cooldowns. Spell selection can maximize damage without a complex passive. | Cannot cast both in one turn; both exclude walking. No stun, dash or sustain. Fragile at basic-attack range of an active camp. |
| **A, economy specialist** | **[Vesper][vesper]**; 900 / 45 / 100; ranged | Passive +20% gold, attack reset, two-step dash. Give Vesper the capture of gold-rich groups when route costs permit; basic-attack builds are straightforward. | No damaging spell or stun; gold earns no primary score. Range 3 is not a safety advantage over range-3 camps, and ordinary move-and-fire is forbidden. |
| **B solo; A in a tested pair** | **[Willow]**; 700 / 45 / 105; ranged | Heal **another** ally for up to **315 base Health at range 4**, compatible with walking. Reset supplies damage on other turns. Keep a tank visible and heal missing health before the next dangerous exchange. | Cannot self-heal; modest Health/Strength growth (+50/+3). Escorting costs an independent farmer, and heal/reset cannot share a turn. |
| **B; matchup-dependent** | **[Ren]**; 900 / 40 / 100; melee | Retaliates for **20 base damage per damaging event**, even as he dies; range-4 spell deals 125 and stuns; dash gives access/escape. Candidate against many low-damage attackers. | Retaliation is not damage reduction. No attack reset; taking damage deliberately must beat avoiding it. Verify passive interaction chains before modelling duels. |
| **B week one; high-upside research** | **[Cassi & Issac][cassi]**; Cassi 700 / 30 / 70 ranged; Issac 900 / 40 / 100 melee | **Two independent turns and positions for one pick.** Cassi: 140-base range-4 damage or a walk-compatible range-4 stun. Issac: reset or dash. Can cover two safe routes or split fighter/capturer responsibilities. | Either death kills both and loses both bags. Separate vision and bot instances add coordination cost; protecting only the melee body is insufficient. Not a weak kit, but a large reliability burden. |
| **B, defer gem-hoarding policy** | **[Prism]**; 700 / 35 / 80; ranged | Range-4 spells: 1.5× Focus damage + stun, or 1× Focus radius-1 damage. +0.2 Focus per carried gem; a **50-gem bag adds 10 Focus**, only +15/+10 spell damage before modifiers. | Hoarding delays permanent score and magnifies death losses for modest early gains. No mobility/sustain; do not replace banking with an arbitrary “keep 100 gems” rule. |
| **Unranked** | **Under containment** | Public teaser only; no published stats or ability page found. | Reassess if released. Do not assume availability or fabricate a counter. [Event][event] |

### Strongest combo candidates and their actual constraints

1. **Marcella + Tavi: secure delivery and ranged interruption.** Give Marcella a capture when stun-resistant banking matters; keep Tavi in his own line of sight to enemy interruptors, using the 2.2× Focus stun to protect or stop a tribute. Conversely, Tavi can take gold-bearing captures for immediate field upgrades. There is no free transfer of Tavi’s bag to Marcella. Select the capturer **before** reward resolution. This is the most attractive general-purpose week-one pair. [Marcella] [Tavi] [Camps] [Gems]
2. **Varg + Willow, with Marcella as an additional carrier/escort on larger teams: sustained clustered farming.** Varg’s repeated splash clears groups; Willow’s 315 heal every available cooldown and Varg’s 250 shield reduce recall pressure. Have the durable unit be the nearest valid camp target; keep the patient visible to Willow while she stays outside the dangerous footprint. The heal’s sustained rate is at most 315 ÷ 8 = **39.375 Health per round** before movement, overheal and interruptions—insufficient by itself against several attacking wolves or an elk. Test whether this pair beats two independent farmers, rather than assuming “support” is free. [Varg] [Willow] [Camps]
3. **Ryth + Stellar: AoE control into AoE damage.** Against clustered enemies or camps, Ryth can stun and Stellar can hit the same area on her own turn. Schedule the setup champion early for the **next** round, but model intervening enemy slots. At base Focus their AoE casts total **240 damage per common target**, not two casts from one champion; unstunned/immune targets may move before Stellar acts. Stronger candidate on narrow altar approaches than dispersed maps. [Ryth] [Stellar] [Turn] [Marcella]
4. **Vesper + Treasure: gold snowball, not a direct gem multiplier.** +40% gold can fund faster clearing and improves a tied-gem tiebreak. Have Vesper receive gold-rich captures when that does not delay the next bank. Compare an early Treasure emblem with Monster/Jungle: the latter can immediately increase camp access or uptime. [Vesper] [Items] [Objective]
5. **Cassi & Issac: extra-body map control.** Two safe disconnected farming assignments can exploit their extra action stream without constant local coordination; a combat pairing can combine Cassi’s walk-compatible stun with Issac’s melee approach. Both require conservative retreat and gem exposure limits on **both** bodies. This is a Sprint 2–3 experiment, not something to dismiss permanently because implementation is harder. [Cassi] [Death] [Vision]

**Anti-combo:** stacking stuns is not automatically a chain. A second stun on an already-disabled target may waste future denial; Marcella ignores stuns entirely. Save a stun for the next relevant execution slot or tribute attempt unless immediate damage/kill value is higher. Exact stun lifetime/refresh behavior needs a boundary test. [Combat] [Marcella] [Turn]

## 3. Sprint 1: the smallest strong bot, in priority order

The [published schedule][event] says Sprint 1 is **18 October**, with submissions locking **17 October at midnight UK time**; later locks are **24 October** and **31 October**. The page does not supply an unambiguous ISO timestamp for “Saturday at midnight.” **Team default: freeze and verify an accepted candidate by Friday 16 October, 20:00 BST (19:00 UTC)**, safely before either interpretation, and confirm the actual tournament lock. Do not rely on a last-minute upload. London is on BST for the first lock and on GMT by the third.

### P0 — Finish the objective loop and obey action state

Implement explicit goals: **travel → clear → capture → deliver → tribute → recover/shop**. On each turn, check death, stun, active channel, actual action allowances, target visibility and fuel before acting. A channel can occupy multiple turns without being a stuck bot. Change goals after observing success or a failed precondition, not simply after a fixed number of calls. Validate a complete first bank with the exact submitted artifact before optimizing anything. [Turn] [Gems] [Fuel]

**Acceptance:** a bot can clear every member of a group, stand on a capture tile until reward arrival, leave it, reach an adjacent altar tile and observe increased **team tributed gems**. The same loop recovers from an enemy lock, a hidden movement blocker, a cancelled channel and death. No accidental infinite retry after `false`; no cast while stunned; no “successful tribute” inferred from an attack on a lock. [Camps] [Maps] [Gems]

### P1 — Draft routes, not just favorite champions

During the full-vision draft, find connected camp groups, their combined rewards/threats, safe approach tiles, reachable altars and spawn return costs. Assign **non-overlapping first objectives** and a designated capturer per group. Store a compact first route plus fallback waypoints; revalidate occupancy and danger during play. Precompute only what fits the actual first-draft fuel allowance, with a valid pick guaranteed before budget exhaustion. [Draft] [Camps] [Memory] [Fuel]

**Proposed roster policy:**

- **3 picks:** Marcella, Tavi, Varg when useful splash groups exist. Swap Varg for Vendetta for isolated low-threat groups. Ryth is the alternative when durability and AoE interruption matter more than raw clear rate.
- **4 picks:** add an unused farmer for another independent route: Vendetta if not already selected, otherwise Ryth or Stellar as the terrain/threats warrant. Use Vesper instead if a separate gold-rich route can fund repeated upgrades.
- **5 picks:** add Willow only if an identified two-body farming/escort route actually needs sustain; otherwise add an unused A-tier farmer suited to the map. Do not force a five-champion deathball through every capture.
- Later enemy reveals may influence the remaining picks: Marcella is attractive against multiple stuns; do not assume that selecting her prevents the enemy from doing the same. These choices are hypotheses to A/B test, not settled draft theory. [Roster] [Draft]

### P2 — Clear safe camps efficiently; never donate a full bag to an elk

Rank complete **clear/capture/delivery routes**, not nearest monsters. First reject routes with no legal exit or unsafe predicted damage; then favor delivered gems per total travel, clear, capture and tribute time. Treat useful gold as an investment in later routes, not interchangeable score. Prefer standalone clusters; take wolves when our current health and damage support the full group. Avoid monoliths in the initial policy. [Camps] [Objective]

**Minimal threat model:** sum attacks from all awakened monsters that can reach the proposed position until our kills reduce that set; include their pre-champion action phase, enemy approach time and an escape reserve. Basic ranged range 3 does **not** outrange wolves/elks. Range-4 spells offer poke without entering their listed range 3, but a poke-only route is slower and sleep/range ambiguities must be checked. A 1,000-health Varg is not automatically safe into three wolves merely because he hits all three. [Camps] [Turn] [Varg]

Use ordinary attacks whenever safe, resets **after** using an available attack, spells on worthwhile targets, and Varg’s shield before a dangerous phase. Preserve an interrupt spell when an enemy carrier is about to finish banking. After a group dies, leave **one** capturer unless a contested region requires protection; others can clear the next objective or guard approaches outside the capture region. Capture is a world mechanic, not a spell channel: useful legal actions need not stop while holding the region. [Turn] [Camps] [Combat]

### P3 — Bank predictably, with a risk-aware bag threshold

**Initial policy hypothesis:** bank after one or two safe gem groups, using **40–60 carried gems as a tuning range**, not a universal cap. Bank earlier if already near a safe altar, facing a plausible interception, or able to reach 1,000 team score. Allow a larger bag only if the next route and altar remain safe and the saved travel justifies it. Compare against “bank after every capture.” [Gems] [Objective]

Why not always one camp? Two 24-gem captures bank together in **five** ticks rather than two three-tick channels and can save a return trip. Why not always accumulate? That 48-gem carrier exposes a bigger transfer and sits still longer. If a carrier dies and the opponent later deposits its bag, the potential score swing against our successful deposit is **twice the bag**, plus downtime; that swing is conditional on the opponent completing delivery. [Gems] [Death]

Before starting, ward the approach, check reachable enemy stun/lock threats and choose the safest legal neighboring tile. Continue through nonlethal damage when completion is safe; cancel if death before completion is likely. Marcella can disregard **stun** interruption, not lethal damage or a lock. When behind near the horizon, prefer plans that can finish before termination; unbankable new gems are worthless. When tributed gems are genuinely tied and no further bank can finish, lifetime gold matters before kills. [Vision] [Gems] [Marcella] [Objective]

### P4 — Recall before lethal pressure; upgrade on the way back

Retreat with enough health to leave monster/enemy reach, then recall. Do not start recall under continuing damage and retry forever. If safe, bank before a shopping trip; if not, recall with the gems rather than dying for a speculative bank. After arrival, shop and remain until the full-heal turn end before routing out. Buy while dead instead of wasting the shopping window. [Death] [Turn]

**Initial build hypotheses, chosen by role:**

- Attack-heavy Varg/Vendetta/Vesper: **Monster Strength** on safe PvE routes; test **Jungle Health** first where incoming camp damage otherwise forces retreats. Switch toward durability if champion fights dominate. Only completed emblems grant these passives. [Items]
- Marcella carrier: enough **Health/Durability** to survive the intended channel, then Strength to reduce clear time. Stun immunity is not a license to ignore incoming damage. [Marcella] [Items]
- Tavi: buy useful shards immediately after capture. Favor **Strength for repeated basic attacks**, **Focus for spell-driven routes**. One shard adds 5 basic damage versus 22 damage to his stun spell; at one spell every eight rounds the latter is at most 2.75 extra damage per round before modifiers, while repeated basics can deliver more. Focus is preferable if range-4 poke, burst or denial is the actual job. Field Health supplies no emergency heal. [Tavi] [Items]
- Carry a **10-gold lock** after an affordable shop visit when an enemy-accessible altar is on our route. Treat a crystal as a preplanned terrain shortcut or damage-tolerant channel, not a three-tile dash. Do not buy redundant emblem passives or repeatedly recall just to spend 30 gold when the return trip costs more than it earns. [Items] [Gems]

### P5 — Fight for a bank, a camp or a high-value carrier

Avoid full tactical search for Sprint 1. Score a small set of legal local choices: finish a kill; interrupt an imminent enemy tribute; protect our channel; take a favorable attack; retreat; continue the farming goal. Favor visible killable carriers, channel interruptors and units contesting a nearly completed capture over an arbitrary nearest champion. Do not follow a fleeing empty-handed enemy through fog while our bag waits to score. [Gems] [Camps] [Death] [Vision]

Use single-turn attack/reset sequences and short survival estimates. Against an enemy tribute, ordinary nonlethal damage **does not cancel it**: use a stun, a lock, or a kill. Against Marcella, only the latter two are reliable interruption routes from that list. A timely 10-gold lock can invalidate a long channel, but do not trade a carrier’s life just to place one. [Combat] [Gems] [Marcella]

### P6 — Ward and communicate the one fact teammates need

Place a ward before entering a blind approach and before committing to a bank. Share a fresh **enemy carrier / altar danger / contested route** alert through the small live buffer; keep ordinary route allocation deterministic from the draft plan. Other champions use the message for movement and risk decisions, not as proof that they can target an unseen unit. Bound how long a goal remains blocked before taking its fallback. [Vision] [Memory] [Maps]

### P7 — Promote based on wins, not a beautiful replay

Team default: first run 10–20 diverse full-match smoke tests, then side-swapped candidate/incumbent comparisons on a fixed opponent panel and held-out maps. Include a greedy farmer, an aggressive interceptor and a lock/stun-focused defender if those controls can be built cheaply. Use the **actual round cap and fuel settings**; a short local game can rank routes differently. [Objective] [Fuel]

Record winner, tributed gems, lifetime gold, deaths and gems lost, time to first tribute, clear-to-capture delay, idle/blocked turns, failed actions, and worst-turn fuel. Keep current/previous bot versions and replay at least one loss per map family. Count a fuel suspension or bot fault as a real result, not a filtered-out sample. Large gains need repeated evidence; small win-rate differences need uncertainty estimates over independent map/opponent blocks. No numerical improvement is claimed in this playbook.

**Freeze order:** reliable objective loop → safe routes/capture → banking/survival → action use/upgrades → wards/basic denial. If time runs out, cut adaptive drafts and search, not capture completion or channel correctness.

## 4. Sprints 2–3: research ranked by expected win-rate impact

The order below is an **ex ante estimate of marginal impact after the week-one baseline**, balancing frequency, consequences and implementation cost. “High/medium” is a priority judgment, not an invented percentage-point gain. Promote a task if replays show it causes more losses than the tasks above it; correctness blockers in section 5 override this ranking.

| Rank / sprint | Hypothesis and expected impact | Rules-based mechanism | Distinguishing experiment and promotion evidence |
| --- | --- | --- | --- |
| **1 · Sprint 2 · High** | **Joint route/capture/bank scheduling** beats independent nearest-camp farming. | Fixed capture delay, no multi-ally acceleration, group respawn only after claim, delivery travel and occupancy-blocked respawns create wasted team turns. [Camps] [Gems] | Compare fixed roles with a small assignment planner on clustered/sparse maps. Vary solo capturer, concurrent clearers, respawn revisit timing and bag thresholds. Require more actual tributes/wins, not merely more harvested gems. |
| **2 · Sprint 2 · High** | **Altar control and protected channels** beat passive banking once opponents contest. | Nonlethal damage cannot interrupt; stun, death and cheap three-hit locks can. Marcella changes that matchup. [Gems] [Marcella] | Test locks before/late in channels, lock breaking with reset champions, escort positions and alternate altars against a dedicated disruptor. Include Marcella carriers as the counterexample. Measure prevented/completed banks and our farming opportunity cost. |
| **3 · Sprint 2 · High** | **Bounded two-round combat planning** prevents avoidable deaths and secures carrier kills. | Move/attack restrictions, one cast, per-slot cooldowns, reset sequences, stun slots and alternating team order reward accurate short lookahead. [Turn] [Combat] | Compare heuristic versus enumerated legal sequences under identical fuel. Use asymmetric health/cooldowns, both starting teams and priority orders. Measure gem-weighted deaths and final wins; reject planners that suspend mid-decision. |
| **4 · Sprint 2 · Medium–high** | **Role-specific item and recovery breakpoints** buy more active farming time than a fixed build. | Shards scale differently; family passives do not stack; Tavi shops remotely; Jungle/Durability/Health can enable routes; Home saves only two recall ticks. [Items] [Death] [Tavi] | Sweep a few discrete first-emblem choices, recall health thresholds and spending intervals. Compare total clear + capture + heal + return cycles, not training-dummy DPS. Evaluate Treasure/Vesper payback before the real horizon. |
| **5 · Sprint 2–3 · Medium–high** | **Ward placement plus compact danger sharing** reduces expensive fog interceptions. | Vision is per champion and bushes hide units; wards are free but replacement loses old coverage; live communication is 64 bits. [Vision] [Memory] | Hold farming policy fixed; compare reactive warding, altar/return-path sentries and age-bounded alerts. Count surprise deaths and false-positive detours. Explicitly test last-writer conflicts and stale warnings. |
| **6 · Sprint 3 · Medium** | **Map/opponent-conditioned drafts and paired roles** outperform one roster. | Full map is visible in draft; previous simultaneous picks reveal information; splash, support and anti-stun value depend on geometry/opponents. [Draft] [Roster] | Compare Varg vs Vendetta on equal-reward grouped/isolated layouts; Willow pair vs two farmers; Ryth/Stellar versus dispersed and stun-immune opponents. Choose using held-out maps, not a memorized map ID. |
| **7 · Sprint 3 · Medium, high upside** | **Cassi & Issac’s extra body** can outweigh linked-death exposure. | One selection grants two positions/turns, but either death removes both and both bags. [Cassi] [Death] | Compare safe split farming with an escort pair and a normal single-slot replacement. Stress simultaneous threats to both bodies. Track joint lost uptime/bags, not just their combined damage. |
| **8 · Sprint 3 · Medium, map-specific** | **Capture/tribute overlap and channel-aware pathing** shorten delivery cycles. | A camp tile adjacent to an altar can support capture; a channel uses the initial bag but deposits later gains; crystals cross intervening terrain; dashes cross holes in up to two steps. [Camps] [Gems] [Maps] | Test starting with 1 carried gem and a capture completing before tribute resolution, versus empty-bag rejection and reversed timing. Only use documented combinations; test against disruption. Compare geometric shortcuts including three-tick crystal commitment. |
| **9 · Sprint 3 · Low until supported by losses** | **Selective monoliths and Prism bag retention** may create decisive late swings. | Monolith: 20,000 health, 200 gems, dangerous listed range; Prism: +0.2 Focus per unbanked gem. [Camps] [Prism] | Require verified monolith range/sleep behavior and a complete kill/capture/delivery forecast. Compare with parallel ordinary camps. For Prism, price the incremental spell damage against delayed score and bag loss at several threat levels; reject blanket hoarding. |

**Defer whole-game minimax, large learned policies and elaborate opponent identification** until a logged loss class cannot be fixed with routes, channels, upgrades or short combat planning. Hidden independent observations, a 2,000-round horizon and limited per-turn fuel make a broad search expensive; they do not preclude a small local planner with a legal-action fallback. [Objective] [Vision] [Fuel]

## 5. Uncertainties and probes before relying on a mechanic

These are **unresolved here**, not permission to choose the most convenient interpretation. Use the current SDK/runner, save the smallest replay, and request organizer clarification where the written rules contradict themselves.

| Priority | Uncertain or easy-to-misread rule | Smallest useful check; safe policy meanwhile |
| --- | --- | --- |
| **P0** | **Camp range and sleep conflict inside the handbook.** Table: monolith range 5, clusters 0; prose: all range 3. Sleep: no damage vs no in-range champion. [Camps] | Probe a monolith at distances 3/4/5/6; probe two no-damage rounds while remaining in range versus moving out. Check whether sleep preserves damage. Avoid monolith/poke strategies dependent on the answer. |
| **P0** | **Capture start versus countdown, respawn occupancy and horizon accounting.** Five-round timer is not five turns from stepping in. [Camps] [Turn] [Objective] | Enter immediately after capture phase, log initiation and every decrement/reward; leave for one phase; contest for one phase; occupy one respawn tile. Try a tribute completing just before/at the configured final round. Observe rewards and score rather than counting local loop iterations. |
| **P0** | **Reset/action order and one-round stun timing.** The broad action rules do not settle every ordering boundary. [Turn] [Combat] | Test ranged walk → reset → attack; attack → dash; forbidden walk → no-walk spell; Vendetta kill after casting; stun before/after target’s slot under both team orders. Confirm actual allowances after each success/failure. No second cast after a cooldown refresh. |
| **P0** | **Official lock timestamp and runner defaults.** “17 Oct midnight UK” is not an ISO timestamp; website Python FAQ differs from fuel docs; local round limits may differ. [Event][event] [Fuel] [Objective] | Confirm tournament timestamp, submitted artifact, language multiplier and 2,000-round tournament cap. Freeze by 16 Oct 20:00 BST; do not tune from a silently shortened local run. |
| **P1** | **Crystal terrain wording and landing revalidation.** “Can reach walls” conflicts with explicit forbidden landing tiles; the handbook does not fully describe a destination becoming occupied during its three-tick channel. [Maps] [Bundle][agents] | Test crossing a wall versus landing on one, and a destination occupied after initiation. Use a known legal free landing; keep a fallback after resolution. |
| **P1** | **Lock placement cancellation ownership, stacking/replacement and removal sequence.** Owner can tribute through its own lock, but the export broadly says placement cancels existing channels. [Gems] | Place friendly/enemy locks during each side’s tribute; attempt a second lock; test three basic hits with mixed champions and a reset. Place friendly protection before the channel until settled. |
| **P1** | **Champion interaction boundaries.** Ground-effect friendly fire/target validity, retaliation chains, shield refresh and exact stun refresh are not fully specified in prose. [Combat] [Ren] [Varg] [Ryth] | Probe an ally inside an AoE, two Rens, a fresh shield near expiry, and a repeated stun. Keep planner assumptions conservative until checked against the engine. |
| **P1** | **Unavailable twelfth champion and evolving published rules.** “Under containment” has no kit. [Event][event] [Roster] | Re-read published roster and [patch notes][patches] before each sprint. Only draft supported published choices; update the source snapshot if rules change. |

## Sources and reading coverage

All links below are official Cambridge Battlecode sources, checked **13 October 2026**. The [download page][agents] provides `GameRules.md` via a browser download button; it was read in full, including every published champion specification. The [glossary] was read separately. The document is a source-backed strategy proposal, not a report of engine experiments or ladder results.

- **Handbook and download:** [Handbook home][handbook], [Agents.md / Markdown downloads][agents], [Champion roster][roster], [Glossary][glossary].
- **All twelve rule chapters:** [The game][objective], [Drafting][draft], [A champion turn][turn], [Maps & movement][maps], [Camps & capture][camps], [Gems & altars][gems], [Combat & abilities][combat], [Items & gold][items], [Vision & wards][vision], [Death, recall & recovery][death], [Fuel][fuel], [Shared memory][memory].
- **All eleven published kit pages:** [Cassi & Issac][cassi], [Ryth][ryth], [Vesper Vale][vesper], [Prism][prism], [Stellar][stellar], [Vendetta][vendetta], [Marcella][marcella], [Tavi][tavi], [Willow][willow], [Ren][ren], [Varg][varg]. Marcella and Varg were also read in the rendered browser when the page extractor did not return their content.
- **Schedule and unpublished slot:** [Official event homepage][event]. The twelfth teaser has no linked rules page in the current roster/export. [Patch notes][patches] should be checked for changes; no versioned patch contents were obtained in this read, so none are asserted here.

[handbook]: https://2026a.battlecode.co.uk/game/docs
[agents]: https://2026a.battlecode.co.uk/game/docs/agents
[objective]: https://2026a.battlecode.co.uk/game/docs/objective
[draft]: https://2026a.battlecode.co.uk/game/docs/draft
[turn]: https://2026a.battlecode.co.uk/game/docs/your-first-turn
[maps]: https://2026a.battlecode.co.uk/game/docs/maps-and-movement
[camps]: https://2026a.battlecode.co.uk/game/docs/camps
[gems]: https://2026a.battlecode.co.uk/game/docs/gems-and-scoring
[combat]: https://2026a.battlecode.co.uk/game/docs/combat
[items]: https://2026a.battlecode.co.uk/game/docs/items
[vision]: https://2026a.battlecode.co.uk/game/docs/vision
[death]: https://2026a.battlecode.co.uk/game/docs/death-and-recall
[fuel]: https://2026a.battlecode.co.uk/game/docs/fuel
[memory]: https://2026a.battlecode.co.uk/game/docs/shared-memory
[glossary]: https://2026a.battlecode.co.uk/game/docs/glossary
[roster]: https://2026a.battlecode.co.uk/game/docs/champions
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
[event]: https://2026a.battlecode.co.uk/
[patches]: https://2026a.battlecode.co.uk/game/patch-notes
