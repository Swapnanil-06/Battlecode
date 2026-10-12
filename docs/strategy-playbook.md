# Cambridge Battlecode ’26 Autumn: strategy playbook

**Pre-reveal draft · 12 October 2026 · timezone: Europe/London**

**Purpose:** reach a reliable, measurable bot quickly after the reveal, then spend development time on the changes that win matches. This document contains no bot implementation. All implementation, game-specific experiments, and submissions described below start **after the official reveal**.

## What we know, and what we do not

- **Confirmed:** play is turn-based; the announced objective is to collect gems and offer them at altars. The precise scoring and victory rules are not yet known. [1]
- **Confirmed:** the season runs **12 October–18 November 2026**, with three weekly ladder-seeded sprints, UK and international qualifiers, and a 16-team in-person final. [1]
- **Reveal:** **13 October 2026 at 09:00 UK** — 09:00 BST, 08:00 UTC. The official site's delay banner gives this time, although its schedule/FAQ still contain older 12 October reveal wording. Recheck the official announcement at launch. [1]
- **Unknown:** everything else needed to choose a strategy: exact victory conditions, actions, map representation, number of participants or controlled entities, visibility, resource persistence, randomness, and execution limits. Do not import MIT Battlecode's grids, combat, robots, economy growth, communication, or bytecode model into this game.

**Labels:** “hypothesis” means an assumption to verify, not a mechanic we expect to exist. “Team default” means a proposed workflow or experiment budget, not an organizer rule. Conditional examples below are questions to investigate; mark irrelevant ones **N/A** after the reveal.

“Banking” is shorthand for converting collected gems into whatever benefit offering actually gives. It does **not** imply that gems must be carried, that offering grants permanent points, or that offered gems are safe from reversal.

## 1. Learn the game by tracing how an action becomes a win

### Read in decision order

1. **Victory, termination, and ranking rules.** Write the exact winner calculation in plain language, including every alternative victory route, maximum duration, tiebreak priority, and disqualification condition. Separate winning a game from scoring a tournament match and from ladder rating. Never optimize “most collected gems” merely because it sounds like the objective.
2. **Turn and execution contract.** Read the official API lifecycle, legal-action rules, observation format, update order, compute/memory limits, and consequences of invalid actions or timeouts. Determine whether decisions are sequential or simultaneous and what information is available when each decision is made.
3. **Gem-to-offering economy.** Read the rules for obtaining gems and making offerings, plus any costs, ownership, limits, reversibility, and timing. Identify the actual scarce constraint: opportunities, actions, access, information, or something else supported by the rules.
4. **Official minimal example and match tools.** Follow one observation through one legal decision to the engine's next state and eventual result. Learn how to run a match, identify the submitted version, and inspect a replay or log, **if those tools exist**. An example demonstrates API use; it is not evidence of a strong strategy.
5. **Clarifications, changelog, and adjudication policy.** Record the rules/API version. If documentation, example, and observed engine behavior disagree, preserve the evidence and ask the organizers; do not silently assume which is authoritative or rely on a suspected exploit. Read relevant engine source only if published and permitted.

For every strategically important rule, record **source → interpretation → smallest distinguishing example → observed result**. Prefer examples where competing interpretations produce different legal actions or winners.

### First three hours: proposed checkpoints, not promises

| Time after reveal | Deliverable | Stop condition |
| --- | --- | --- |
| 0–30 minutes | Fill the critical rows in section 5; explain scoring and the execution contract to a teammate. | Each unknown that could invalidate the first bot has an owner. Do not debate advanced strategies yet. |
| 30–90 minutes | Run the official example and then a minimal legal bot; inspect a complete game. Demonstrate gem collection and an offering if feasible under the actual rules. | We can distinguish a strategy loss from an invalid action, crash, or timeout and identify the version that played. |
| 90–180 minutes | Compare the simplest scoring policy with one alternative using controlled matches; replay at least one loss. | We have a frozen baseline, one recorded hypothesis, and a reproducible result rather than an architectural plan. |

If tooling is unavailable or setup consumes the window, finish the execution loop first and record the blocker. Divide ownership into rules/economy, runtime/testing, and baseline decisions if team capacity allows; one person may cover all three. Integrate at each checkpoint.

### Build an economy ledger before choosing a policy

For each **verified** scoring route, list prerequisites, actions consumed, elapsed turns, costs, expected reward, failure conditions, and whether the benefit can be lost. Keep collected gems, offered gems, and actual score separate until the rules establish their relationship.

| Question | Comparison to make after the rules are known |
| --- | --- |
| Collection | Which legal choice produces the most eventual scoring value for its action/turn cost, rather than the largest immediately visible haul? |
| Banking/offering | If collecting and offering compete for time or resources, compare offering now with collecting more first. Count the complete sequence through a successful offering, not just acquisition. |
| Denial | If opponents compete for resources or access, compare their expected lost scoring opportunity with our own forgone scoring. Denial is useful only if it changes the actual outcome; physical blocking, theft, and combat are not assumed. |
| Investment | If spending resources can increase future earning capacity, calculate when that investment repays its cost in score, including delay and risk. Do not assume any compounding economy exists. |
| Endgame | If games have a known horizon, determine the last decision point at which each plan can still produce a counted result. Unfinished plans may be worthless — verify this. |

**Hypotheses to test, not starting beliefs:** immediate offering beats accumulation; acquisition is the bottleneck; early investment pays off; denying a shared opportunity beats pursuing a private one. Each needs a competing policy and a case where their outcomes differ.

Use the win condition to value risk. If the objective is winning rather than maximizing total score, a lower-variance policy may be preferable when ahead and a higher-variance policy when behind. That requires a meaningful estimate of who is ahead and confirmation of the tournament objective; neither is assumed.

The transferable lesson from The Kragle is to inspect conversion efficiency and idle time, not to copy its economy-first game plan. Its authors describe improving resource use while also wasting effort on low-impact behavior and unreliable pathfinding. [3]

### Edge cases to resolve before they decide a tournament

Test only the cases that exist in the revealed game, with both sides of each boundary:

- **Last-turn accounting:** an offering just before versus just after the final scoring update; simultaneous threshold crossings; exact ties versus a one-unit advantage.
- **Action order and legality:** whether one action enables another in the same turn; exact cost/range/capacity boundaries; whether a rejected action consumes a turn or resources.
- **Competition for one opportunity:** two actors choosing the same gem, altar, or action target; resolution priority, stale observations, and whether earlier actions invalidate later ones.
- **Unavailable goals:** no reachable/eligible target, exhausted resources, changed eligibility, or interrupted plans. Can the bot safely abandon an impossible goal rather than loop or wait forever?
- **Information changes:** if there is partial visibility or persistent memory, distinguish “not observed” from “does not exist”; invalidate stale beliefs; confirm whether memory survives turns and resets between games.
- **Topology and orientation:** if there is a spatial map, try awkward boundaries, narrow access, disconnected regions, and each starting role. Do not infer symmetry or movement geometry from pictures.
- **Budget and terminal behavior:** large valid observations, expensive turns, initialization, no legal actions, exact budget exhaustion, and termination during a planned sequence. Verify the official fallback/pass behavior rather than inventing one.

Tiebreakers can be a primary strategy, not an afterthought: 5 Musketeers describes exploiting the actual resource tiebreak in MIT Battlecode 2022. That is evidence to read the rules carefully, **not** evidence that Cambridge has the same tiebreak. [4, §4.2.1]

## 2. Advance through the strategy ladder only when evidence earns it

These are capability levels, not a mandatory sequence of increasingly complex algorithms. A well-tested heuristic may remain the final bot. Keep earlier versions as controls and fallback submissions. Effort estimates below are **team defaults** to revise after seeing the API and available hours.

| Stage | What to build after reveal | When it is worth the effort | Evidence for moving on |
| --- | --- | --- | --- |
| **1. Trivial-legal bot** | The smallest policy that reliably produces legal decisions, completes games, and attempts the simplest verified scoring route. Use an official safe fallback only if one exists. | Immediately; timebox the first attempt to hours. This is the execution and submission baseline. | Representative games finish without bot faults, the recorded result matches our understanding of the rules, and losses are mostly poor decisions rather than broken execution. |
| **2. Scripted opening** | A short, explicit initial plan with checked preconditions, an abort condition, and a handoff to the baseline. A script must not continue blindly after the state diverges. | When initial conditions repeat enough that early choices predictably affect later scoring. Skip or shorten it if starts are highly variable. | The opening improves early progress **and** final outcomes across starting roles. Replays show most remaining losses arise after its handoff or require reacting to state. |
| **3. Heuristic evaluation** | Rank legal choices by a few interpretable estimates tied to actual scoring: completion cost, expected benefit, delay, and applicable risk. Separate hard legality from preferences and avoid repeated goal switching. | When scripts fail in varied states and the relevant tradeoffs can be estimated cheaply. Usually the best first-week default. | Held-out losses repeatedly require looking beyond the next choice, despite sensible features and thresholds. Feature ablations show which terms matter; tuning is no longer yielding comparable gains. |
| **4. Search/planning** | Add bounded lookahead to one demonstrated decision bottleneck, with a tested transition model and enough budget reserved to return a legal decision. Keep the heuristic fallback. | Only when the failure needs multi-step reasoning, transitions can be modeled adequately, and measured compute headroom supports it. Prototype one decision class before a whole-game planner. | Equal-budget tests show gains over the heuristic, including hard states. Then consider modelling opponents only if remaining errors are specifically about their choices, not our transition model or horizon. |
| **5. Opponent modelling** | Adapt among already-tested policies using permitted observable behavior; track uncertainty and retain a general policy when evidence is weak. | When repeated behavior is observable and a counter has positive value without making us broadly exploitable. Do not require opponent identity to be exposed. | Retain it only if it beats the non-adaptive version on unseen opponents and varied behaviors. Otherwise return to the simpler policy; there is no obligation to reach this stage. |

**Search selection is also conditional.** Deterministic planning requires sufficiently known transitions; adversarial search requires a justified model of turn order, participants, and objectives; stochastic or hidden-information planning requires a model of uncertainty. Do not choose minimax or Monte Carlo search from the competition's name alone. Short-horizon planning can also miss delayed offerings; compare against complete scoring sequences.

**Promote a change, not an impressive algorithm.** State the expected benefit before building it, test at the same actual execution limit, and remove it if the gain does not justify runtime, debugging, and maintenance cost. Just Woke Up's retrospective explicitly recommends starting simple, iterating, and avoiding complexity for its own sake. [2, pp. 20–23]

**Sprint pacing — team default:** aim for reliable legal play and a measured scoring heuristic at the first lock; use later sprints to test evidence-backed additions. Reserve the final working session before each lock for integration, representative matches, and submission verification. Confirm exact lock and seeding times independently; a stronger bot uploaded too late may not improve its seed. [4, §4.3.3]

## 3. Evaluate changes without fooling ourselves

### Separate diagnosis from promotion

Use three pools, to the extent official tools and permitted opponent access allow:

1. **Development cases:** deliberately small cases that expose a rule interpretation, bug, or expected improvement. Passing these explains a mechanism; it does not establish general strength.
2. **Fixed regression suite:** the last accepted bot, several older versions with different weaknesses, the official example if provided, and permitted diverse opponents. Cover actual map/scenario families and every meaningful starting role. Do not invent map generation or opponent-download capabilities.
3. **Held-out promotion set:** different scenarios/seeds and, where possible, opponents not used while tuning. Keep results out of routine parameter selection. Once inspected and tuned against, that set is no longer held out; replace or extend it before the next strong claim.

If local opponents, seed control, replay export, or custom scenarios are unavailable, record that limitation. Use available official matches/logs and describe conclusions as observational rather than pretending to have a controlled experiment.

For candidate-versus-baseline tests, hold rules/engine, scenarios, seeds where supported, opponent versions, and execution limits fixed. Run both versions against the **same opponent panel** as well as head-to-head. Swap starting roles when supported; for more than two roles, rotate across all relevant assignments. Evaluate natural variation rather than replaying the same deterministic fixture hundreds of times.

Record version identifiers, rules version, opponent/version, scenario/seed, starting role, result, score if meaningful, termination reason, runtime/budget use, and replay/log reference. Track invalid actions, crashes, and timeouts separately from strategic losses, but **keep them in the overall result**. Secondary metrics such as time to a successful offering diagnose why a change worked; they do not replace the actual win criterion.

### How many games?

There is no universal adequate count. It depends on effect size, diversity, correlation, and the decision's cost. The following are **team-default budgets and statistical approximations**, not rules from Cambridge or claims made by the postmortems.

| Purpose | Suggested starting budget | What it can establish |
| --- | --- | --- |
| Smoke test | 10–20 varied completed games plus focused boundary cases | Detect gross faults and verify the intended behavior occurs; not a win-rate claim. |
| Screen one hypothesis | 50–100 reasonably diverse games | Reject a large regression or identify a promising effect; modest gains remain uncertain. |
| Promote an important change | Start with 200–400 games across a fixed panel and held-out scenarios | Useful evidence for substantial gains, provided uncertainty and subgroup results support them. It is not an automatic pass threshold. |
| Resolve a small gain | Potentially thousands of fresh, diverse games | Often poor use of the first week. Prefer a larger opportunity or retain the simpler bot if uncertainty remains. |

For an independent binary win/loss sample near 50%, an approximate 95% confidence-interval half-width is \(1.96\sqrt{0.25/n}\), where \(n\) is the number of independent games:

| Independent games | Approximate half-width in percentage points |
| --- | --- |
| 25 | ±20 |
| 100 | ±10 |
| 400 | ±5 |
| 1,600 | ±2.5 |

Thus **55 wins from 100 games is inconclusive against 50%**, not a reliable five-point improvement. These are precision estimates for a single win rate, not sample-size guarantees for detecting an improvement between two versions. Report a Wilson interval for binary results rather than relying on the approximation, especially at small counts or extreme rates.

**Important qualifications:**

- Side-swapped games, shared maps, repeated opponents, and reused random seeds can produce correlated results. Report both game count and independent scenario blocks; do not count every repeat as fresh evidence. Many games against one opponent cannot establish broad strength.
- For matched candidate/control results, compare their **per-block performance differences**, keeping related games together. Use uncertainty over independent blocks, such as a block bootstrap, rather than treating both samples as unrelated coin flips.
- Report wins/draws/losses separately. Use the revealed competition's draw scoring for the primary metric; only use wins plus half draws if that convention actually applies. Binary-win intervals do not automatically apply to fractional scores, placements, or multi-player results.
- Predeclare the experiment budget, main metric, opponent/scenario weighting, and minimum worthwhile gain. Do not stop the first time a favorable result appears or try many settings and quote only the winner. Confirm the selected candidate on fresh held-out cases.
- Zero failures is not proof of safety. Under independent comparable trials, zero faults in 100 games still permits a true fault probability of roughly 3% at a one-sided 95% bound. Targeted boundary tests remain necessary.

**Promotion rule:** accept when the targeted failure is fixed, broad results support the intended gain without unacceptable subgroup regressions, and legality/compute remain sound. When evidence is inconclusive, keep the incumbent or explicitly record a risk-based decision; do not relabel uncertainty as a proven improvement.

### Use the ladder as external validation, not a laboratory

- Snapshot our version, observed opponents, and the time window. Opponents change while we test; rating changes also reflect scheduling, population, map mix, and rating uncertainty. A rank jump alone cannot attribute an improvement to our edit.
- Seek varied permitted matchups: strong, similar-strength, and strategically different opponents. Keep a general-purpose benchmark rather than tuning only against the current leader or a single rival. Respect challenge limits and competition rules.
- Self-play measures progress against our own assumptions. It can miss strategies no version of our bot uses and can produce non-transitive results: A beats B, B beats C, C beats A. Maintain a matchup matrix, not just one scalar rating.
- When local and ladder results disagree, inspect the changed opponent/scenario distribution and replays before choosing which evidence applies. Just Woke Up describes all-map A/B tests and improvements whose value against aggressive external opponents was not captured by its older bots. [2, pp. 7–8, 18–19]
- Treat each sprint as another sample, not final proof. If official tournaments use sets or special scoring, evaluate that format too once known. Protect the accepted submission and allow time for ladder seeding to reflect it.

### Replay losses with a falsifiable question

Review every failure caused by a crash, invalid action, or timeout; then sample losses across opponents/scenarios and inspect surprising wins too. Avoid fixing only the most dramatic replay.

1. Find the **earliest avoidable decision** that plausibly changed the outcome, not merely the final bad position.
2. Classify it: misunderstood rule, execution fault, missed scoring conversion, wasted action, poor information use, bad estimate, insufficient planning horizon, or wrong opponent prediction.
3. Write a counterfactual using only information the bot could have known at that point. Replay omniscience is not a legal policy.
4. Reproduce the failure in the original fixture and, if tools permit, a smaller distinguishing case. Change one explanation at a time and retest neighboring states, other roles, and the wider panel.
5. Keep the failing fixture as a regression case. Record when the explanation was disproved as well as when it worked.

**Experiment record template:** hypothesis; predicted winning/losing cases; baseline and candidate IDs; official rules version; controlled variables; primary metric and worthwhile gain; fixed budget; W/D/L and uncertainty; subgroup results; replay explanation; accept/reject/inconclusive; next test.

## 4. Pre-mortem: five ways to waste the first week

These are recurring risks drawn from the retrospectives, not a measured ranking of all teams' failures.

| Failure mode | Early warning | Our prevention and recovery |
| --- | --- | --- |
| **1. Build infrastructure or advanced search before a scoring bot exists.** | Most effort goes into abstractions, custom tooling, or a simulator; no complete match can be inspected. | Start from the official execution path and reach a legal scoring attempt first. Give each infrastructure task a current bottleneck and a short timebox. Use heuristics until losses demonstrate a planning need. |
| **2. Optimize an imagined or misunderstood game.** | We equate collected gems with victory, assume MIT mechanics, or cannot explain tiebreaks and turn order. | Maintain section 5 with source-backed answers; use boundary examples and teammate teach-backs. Recheck affected conclusions after every rules patch. Delete assumptions when contradicted rather than defending prior effort. |
| **3. Tune to a tiny, friendly sample.** | One favorable replay, one ladder jump, or beating yesterday's bot becomes “proof.” | Use fixed matched tests, multiple opponent styles, role rotation, held-out cases, and uncertainty. Review losses and surprising wins. Keep genuine external weaknesses visible even if self-play improves. |
| **4. Perfect a low-impact subsystem or chase a clever idea too long.** | Repeated rewrites or parameter sweeps do not address the most frequent costly losses. | Estimate frequency × match impact × confidence, then compare with development hours. Timebox experiments; remove unsuccessful complexity. Revisit simple scoring conversion and wasted-action fixes first. The Kragle explicitly reports this opportunity-cost failure. [3, §3.1] |
| **5. Lose the working bot to rushed integration, deadline mistakes, or burnout.** | Unreviewed bundles of changes, uncertain submitted version, no rollback, or all-night sessions replacing analysis. | Keep a known-good version, integrate small changes daily, and assign a submission owner. Reserve a pre-lock verification window, confirm upload acceptance and seeding timing, and keep sustainable shifts/rest. Test the exact final artifact under the official runner; revert if it cannot be verified in time. [2, pp. 22–23; 4, §4.3.3] |

## 5. Reveal-day open-questions worksheet

**Complete the P0 rows first, ideally within the first hour.** Unknown is an acceptable answer only with an owner and a next check. P1 rows should be answered in the first few hours or explicitly deferred. Promote any P1 question to P0 if the baseline depends on it. Mark absent mechanics N/A; do not design around them.

For each row fill: **answer; official source/version; confidence (documented / observed / hypothesis); distinguishing probe/result; owner; checked-at time; strategy consequence**.

| Priority / area | Questions to settle | Answer / evidence / owner |
| --- | --- | --- |
| **P0 · Win condition** | What exactly ends a game and chooses the winner? What does an offering contribute? Do collected but unoffered gems count? Are there alternate wins, thresholds, losses, or disqualifications? Is score difference relevant to match/ladder ranking? | TBD |
| **P0 · Action economy** | What decisions are available, by whom, and how often? How many participants and controlled entities are there? Are turns sequential or simultaneous? Can actions combine? What consumes time/resources? What happens on invalid actions, no actions, or conflicting choices? | TBD |
| **P0 · Compute limits and lifecycle** | Which languages/runtime versions and interfaces are supported? What are the exact per-turn, initialization, and whole-game budgets and units? Do limits differ by language? What happens on timeout? What are memory, persistence, randomness, I/O, dependency, and submission constraints? | TBD |
| **P0 · Draw rules and horizon** | Is there a turn/time cap, repetition or stalemate rule? What is the complete ordered tiebreak list? Can outcomes genuinely draw, and how are draws scored in ladder, sets, and qualification? When does final scoring occur? | TBD |
| **P1 · Gems and altars** | How are gems obtained and replenished, if at all? How does eligibility to offer work? Are there costs, capacity limits, ownership restrictions, access restrictions, or offering delays? Can collected or offered value be lost, transferred, spent, or reversed? | TBD |
| **P1 · Map and terrain** | Is there a spatial map at all? If so, what representation, dimensions, movement rules, distances, terrain effects, connectivity, starting roles, and symmetry guarantees exist? Are scenarios fixed, generated, public, or withheld? | TBD |
| **P1 · Information asymmetry** | What is visible initially and later, globally versus locally, and with what delay? What opponent information is exposed? Are there hidden actions or stochastic events? Is memory persistent? If multiple entities exist, what communication is legal? | TBD |
| **P1 · Reproducibility and tools** | Is the engine deterministic given a seed? Can we select seeds, exchange roles, run local matches, inspect replays/logs, construct scenarios, or obtain permitted opponent bots? Does the local engine exactly match ranked play? | TBD |
| **P1 · Competition operations** | What are exact submission-lock and ladder-seeding timestamps in Europe/London, rating rules, challenge limits, patch policy, and tournament format? Are submissions immutable at lock? How do we verify which artifact is active? What reuse, collaboration, and opponent-data rules apply? | TBD |

**First-hours sign-off:** we can explain how to win, produce a legal decision within the real budget, follow one collection/offering sequence through the official result, reproduce or identify a match, and name the strongest unresolved assumption. Everything else goes into a prioritized experiment queue.

## Sources and limits of transfer

Sources checked on **12 October 2026**. Retrospectives are first-person experience, not controlled evidence that a technique will work in Cambridge. Numerical testing budgets and workflow gates above are our proposed defaults. No historical game mechanic is a Cambridge fact.

1. **[Cambridge Battlecode ’26 Autumn — official site](https://2026a.battlecode.co.uk/).** Source for the announced objective, season/format, and delayed reveal banner. The conflicting older reveal wording is noted above; the full rules/API remain the authority once released.
2. **[Tim Gubskiy and Andy Nguyen, “Just Woke Up — BattleCode 2025 Postmortem”](https://battlecode.org/assets/files/postmortem-2025-just-woke-up.pdf).** See “Automations / AB Testing” and “Automatic Scrimmaging” (pp. 7–8), finals changes (pp. 18–19), and tips (pp. 20–23). Lessons used: begin simply, compare across maps, watch replays, distinguish self-play from external matchups, and iterate sustainably. Do not transfer its combat or resource mechanics.
3. **[Justin Ottesen, Andrew Bank, and Matt Voynovich, “The Kragle — Battlecode 25 Postmortem”](https://battlecode.org/assets/files/postmortem-2025-the-kragle.pdf).** See §2.2.5 on unreliable/expensive pathfinding and §§3.1–3.3 on development priorities, resource efficiency, and learning from opponents. Lessons used: quantify opportunity cost and avoid polishing behavior that does not change matches. Its economy-first and map assumptions are not adopted here.
4. **[David Lyons, “5 Musketeers — Battlecode 2022 Strategy Guide”](https://battlecode.org/assets/files/postmortem-2022-5-musketeers.pdf).** See §4.1.8 on a turn-order assumption breaking under state changes, §4.2.1 on tiebreak strategy, §4.3.3 on late improvements missing seeding, and §6 on testing against multiple saved versions. Lessons used: test lifecycle edges, read terminal rules, preserve diverse controls, and treat delivery timing as part of performance.
