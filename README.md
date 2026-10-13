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

The Python bot lives in [`bots/main/src/`](bots/main/src/):

- `main.py`: persistent draft/gameplay loop, exception logging and turn yielding.
- `draft.py`: picks distinct champions using the SDK's draft IDs.
- `bot.py`: legal movement, basic attacks, camp farming/capture, altar tribute and shopping.
- `randomness.py`: deterministic spawn-seeded PRNG (WASI randomness is zero in matches).

This baseline is derived from CAMBC 2.1.5's Python starter. It buys strength shards,
recalls below 35% health, attacks enemies already in range, banks carried gems at
the nearest reachable unlocked altar, and otherwise farms camps. Native bitboards
and distance fields route around terrain and visible occupants. Standing on a
cleared camp's spawn tile captures its rewards automatically. Existing channels
are left running. It does not yet cast abilities or coordinate champions.

## Match Runner

```sh
python runner/run_matches.py --opponent starter-python --matches 18
```

Runs the nine-map pool once per side and reports per-map and overall win rates.
See [`runner/README.md`](runner/README.md) for options and result files.

## Strategy

The current bot is a working baseline, not a tuned competitive strategy.
See [`docs/strategy-playbook.md`](docs/strategy-playbook.md) for planning notes.

## Development Setup

From the repository root (Python 3.10+ recommended for the local runner):

```sh
python -m pip install cambc==2.1.5
cambc init --yes .
cambc build main
cambc run main starter-python --map maps/collision.map26a --statistics replays/stats.json
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
