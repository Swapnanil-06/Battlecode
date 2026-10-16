# Battlecode - CAMBC '26 Autumn

A bot developed for the [Cambridge Battlecode '26 Autumn](https://2026a.battlecode.co.uk) competition.

## Competition Overview

- **Format:** Turn-based strategy bot competition
- **Season:** 12 October – 18 November 2026
- **Prize Pool:** £15,000
- **Finals:** Cambridge Union
- **Game Engine & API Reveal:** 13 October 2026 at 09:00 BST

---

## Bot

Upload **[`quantum-altar-v16.zip`](quantum-altar-v16.zip)**. Release evidence and
limitations are in [`docs/v16-strategy.md`](docs/v16-strategy.md) and
[`docs/v16-results.json`](docs/v16-results.json).

This release analyses 25 supplied matches against five leading teams and compares
against the newer repository baseline `f159455`. It selects a farming policy for
five verified layouts, a pack-clearing variant for Packs, and retains the existing
strategy elsewhere. Improvements include bounded farm routes, fuel headroom,
area-damage targeting, capture completion and revised farming item builds.
Top-five ladder performance still needs fresh server matches.

`bots/main/src/` is the release source; `bots/league/src/` mirrors it. The
`variants/` packages preserve the tested policies used by the map selector.
The previous `quantum-altar.zip` and `docs/league-results.json` are historical;
their 28/34 result uses an older baseline and does not describe this release.

## Match Runner

```sh
python runner/run_matches.py --opponent starter-python --matches 18
```

Runs the nine-map pool once per side and reports per-map and overall win rates.
See [`runner/README.md`](runner/README.md) for options and result files.

## Strategy

Use [`docs/v16-strategy.md`](docs/v16-strategy.md) for the current strategy,
measured results and limitations. Older planning notes remain in
[`docs/strategy-playbook.md`](docs/strategy-playbook.md).

## Development Setup

From the repository root (Python 3.10+ recommended for the local runner):

```sh
python -m pip install cambc==2.2.1
cambc init --yes .
cambc maps pull
cambc build bots/league
cambc run bots/league bots/main --map maps/collision.map26a --statistics replays/stats.json
```

The match runs to completion, headlessly, at the default fuel budget. All replays
and statistics stay in ignored `replays/`. To update the CLI, use
`python -m pip install --upgrade cambc`, then rerun `cambc init --yes .` to refresh
the SDK without replacing our source. Refresh the map pool with `cambc maps pull`.

**Python differences from the C++ guide:** create a *new* bot with
`cambc new other-bot --lang python` (our existing `main` needs no recreation).
The generated entry point is `bots/<name>/src/main.py`; no CMake file is needed in
the Python bot. `cambc build` supplies the Python/WASI runtime and produces
`.cambc/build/bot.wasm`. The `cambc` SDK import runs inside that engine, not with
`python bots/main/src/main.py` on the host. SDK Python sources/type stubs are
downloaded under `sdk/python`; `pyrightconfig.json` points the editor there.

`cambc init --yes .` currently installs all four language starters (rather than
prompting for Python only), including `starter-python`. These generated reference
opponents, `sdk/`, `cmake/`, `maps/`, caches and binaries are ignored and can be
regenerated. Only our source and workspace configuration belong in version control.
No login, ladder submission or display is required for local matches.
