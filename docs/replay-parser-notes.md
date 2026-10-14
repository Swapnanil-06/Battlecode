# `.repl26a` replay parsing notes (time-boxed)

**Notes · 14 October 2026 · cambc 2.1.5 (pinned in `cambc.toml`)**

**Labels:** **Verified** = inspected directly in this orb (zip listing, CLI ELF symbols, Node `WebAssembly.Module.exports` on the cached visualizer asset, ladder API requests); **Measured** = empirical read of repository artifacts; **Spec/Open** = proposed approach / unresolved question. Per the brief, this run stopped at a feasibility verdict; no parser was implemented.

## 0. Verdict

- The format is **not heavy reverse-engineering**: the official visualizer already ships the full engine as a WASM module exposing replay-loading, round-stepping and state-query functions (§5). A Node harness can decode any `.repl26a` in **hours, not days**.
- The binding constraint is **corpus, not parsing**: ladder replays are not downloadable (§6). The realistic corpus is our own matches — local runner output plus, possibly, our own platform submissions.
- Parser-free extraction (§3) already covers our reliability telemetry; positions/actions/scores require the binary (§4–5).

## 1. The bundle — Verified

The outer `.repl26a` is a plain **ZIP** (observed on `replays/main-vs-starter-python-1791960044205.repl26a`):

| Entry | Contents |
| --- | --- |
| `replay.repl26a` | the match record: custom binary packet stream (§4) |
| `team-a.stdout`, `team-b.stdout` | each team's bot stdout, verbatim |
| `team-a.debug`, `team-b.debug` | per-team debug-channel output |
| remote-job variants only | `a.wasm` / `b.wasm`, `map.map26a`, cli logs |

Nothing is encrypted or obfuscated; `unzip -p <replay> team-a.stdout` works. `cambc view` also serves the same bundle at its `/replay.zip` endpoint.

## 2. No usable parser ships with the toolchain — Verified

- The cambc CLI binary (ELF, not stripped) contains replay *serialization internals* — symbols `Game_SaveReplay`, `Engine::Game::Parsers::s_FromReplayFile_v0_0_1(Deep::PacketReader…)`, and a versioned parser registry `k_replayParsers` — but **exposes no user-facing command to parse or dump a replay**.
- The Python SDK (`sdk/python/cambc/`, 2.1.5) has **no replay API at all**: it is observe/act only, with no state cloning or replay loading (planner-spec §3).

## 3. What we can extract today, parser-free — Measured

From `team-*.stdout` alone, per team and champion, for every local match:

- **Our instrumentation line:** `main.py` prints `v3 plans={plan_count} min_fuel={min_fuel} suspensions={suspended}` every 100 rounds (the prefix is a version tag). That is exactly the planner-spec regression telemetry — per-100-round fuel floor, suspension counts, planner plan counts — **already persisted in every replay we produce**.
- **Error lines:** `main.py`'s handler prints `bot error: {error} at {frame chain}`, so faults with file/line stacks are countable per match.
- **Anything we choose to print** (fuel tiers chosen, planner/heuristic disagreement logs per planner-spec §8 S4) is automatically archived by the runner — replay analysis without touching the binary.
- `team-*.debug` captures debug-drawing payloads if we ever emit them.

This yields match-level **reliability** statistics (suspensions, faults, fuel floors) but **no positions, actions or scores** — those live in the binary.

## 4. The inner binary: what is already known — Verified

- Custom binary **packet stream**; magic `rep26a` stored byte-reversed; versioned record framing (the `v0_0_1` parser symbol).
- Embeds the **full map** using the same header layout as `.map26a` files (`w62pam` magic + version/settings words), so map recovery is trivial.
- CLI error strings reveal the **record taxonomy**: champion action subtypes (attack, teleport, consumable use, gem submission, movement/ward placement, purchase, sale), end-turn reason, sandbox actions, record counts.

**Open:** exact field layouts/offsets per record; whether rounds are stored as state snapshots or action deltas; any compression. Not pursued — see §5.

## 5. Future parser: the promising path — Spec

Do **not** hand-reverse the packet stream; drive the official engine instead. The visualizer shipped with `cambc view` caches a WASM engine (pattern `~/.cache/cambc/assets/<sha>/visualiser/assets/v0_0_1-*.wasm`; **398 exports verified** via Node `WebAssembly.Module.exports`): `Game_FromReplayFileBytes`, `Game_FromMapFileBytes`, `Game_API_*` (champions, camps, vision, occupancy, gems, gold, round, draft), `Game_Runner_*` (Init/BeginRound/EndTurn/Advance/Step), `Game_Action_*`, `Game_Sandbox_*`, `Game_Statistics_GetSummary`, plus Bitboard/DistanceField helpers.

**Approach:** Node script → instantiate the wasm → `Game_FromReplayFileBytes(inner bytes)` → step rounds with `Game_Runner_*` → dump per-round per-champion position/health/gems/actions and team scores to JSONL. Calling conventions map from the visualizer's JS glue (`index-*.js`, served by `cambc view`). **Risks:** pointer/allocator conventions; asset-hash and format drift on SDK bumps (pin to the `cambc.toml` version); keep the asset local — do not redistribute it.

**Payoff (ties to planner-spec):** fit opponent-intent weights (§6.4), calibrate the death-downtime farming rate (§5, term 3), and run post-match forensics on gate panels.

## 6. Corpus blocker — Verified

- The ladder API (`/api/v1/ladder`) team rows contain **no replay links**; `/api/v1/games` and `/api/v1/replays` return 404; CLI platform endpoints cover auth/distribution/maps-pool/submissions only. **Opponent replays cannot be mined** — the original goal of modeling ladder opponents from their replays is not achievable with current endpoints.
- Available corpus: every `runner/run_matches.py` match (one `.repl26a` per match, in the git-ignored `replays/` dir) and — **Open, unverified** — our own platform submissions (the CLI remote Job struct has a `replay` field; retrieval was not confirmed).

## 7. Open questions

- Whether the platform `Job.replay` field is retrievable for our own submitted matches (a day-one spike if ladder modeling is ever revisited).
- Exact wasm calling conventions / allocator exports (one focused session, per §5).
- Record-level binary layout (§4) — only needed if the WASM path fails; deliberately deferred.
- Replay format versioning across SDK bumps (`k_replayParsers` registry implies versioning; re-verify on any `cambc.toml` change, as in planner-spec §9).
