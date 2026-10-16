# Local match runner

## Offline policy learning

`python runner/train_league.py --output replays/new-search --trials 20 --validate`

The tuple-model optimiser evaluates complete frozen policies in the official
engine against `main` and `sparring-meta`, with both sides on each training map.
It writes source snapshots, manifests, replays, logs, scores and a selected
`policy.py`. Failed policies cannot be selected. Existing results are reused only
when the policy, bot source, SDK, map files and opponent source match. Use a fresh
output directory after source changes. The eight newer maps stay outside the
automated search; they have been used for manual development and are not an
untouched release holdout. See `docs/league-strategy.md` for the final evidence.

The uploaded bot is a fixed policy. Training occurs locally; ladder games do not
update it automatically. Repeating the same deterministic matchup is not another
independent sample.

## Sequential match runner

Set up the workspace first with the commands in the [root README](../README.md).
The runner needs only Python's standard library and `cambc` on PATH.

```sh
# 18 complete matches: all nine downloaded maps, as both A and B.
python runner/run_matches.py --opponent starter-python -n 18

# Another local opponent; N is the total count, not a count per map.
python runner/run_matches.py --bot main --opponent starter-cpp -n 9

# A custom directory containing .map26a files and a longer wall-clock limit.
python runner/run_matches.py --maps-dir maps --timeout 600 -n 2
```

Maps are sorted alphabetically and cycled; each pass through the pool reverses
our side. Use N = 2 × number of maps for balanced sides on every map. Partial
passes are allowed but are not side-balanced. There is no seed option; repeating
the same deterministic bots, map and side is not an independent random trial.

Each match uses `cambc run` without `--rounds`, `--fuel` or `--view`. Changed bots
are built automatically. The script reads the engine's final `outcome` from
`--statistics` JSON, not the score or console text, so tiebreakers are respected.
It prints per-map and overall wins/losses and win percentages over **completed**
matches. Failures/timeouts are reported separately, excluded from that denominator,
and produce a nonzero exit code. Reported faults in our bot also produce a nonzero
exit code; a completed game containing faults still counts in the win rate.

Every invocation creates a unique ignored `replays/batches/run-*/` directory:

- `summary.json`: commands, maps, our side, results, rounds and fault counts.
- `<index>-<map>/statistics.json`: full final engine statistics.
- `<index>-<map>/run.log`: CLI stdout/stderr, including failures.
- `<index>-<map>/*.repl26a`: replay bundle including bot stdout/debug logs.

The starter-style bot catches turn exceptions and logs `bot error:`; these need
inspection in replay stdout and may not increment the engine's fault counter.
No matches are submitted or uploaded. Refresh the official pool with
`cambc maps pull`; use `cambc view <replay>` on a machine with a display to inspect it.

## Gem pace and replay forensics

`replay_dump.mjs` replays any `.repl26a` (bundle or inner record, including ladder
replays) through the visualiser's own engine WASM, which `cambc view`/`cambc init` cache
under `~/.cache/cambc/assets/`. It prints JSON: drafts, outcome, per-round tributed and
carried gems, deaths, carrier deaths and every tribute. Options: `--every N` (sample
rate), `--champs` (positions, health, gems), `--camps` (layout at round 1), `--locks`
(altar locks), `--profile` (per-champion share of turns attacking, moving, idle,
channelling, tributing or dead). The decoding offsets come from the visualiser's JS for
engine v0.0.1 and v0.0.2, selected from replay metadata. `--items` includes final inventories; `--metadata-only` prints map dimensions and unmirrored template camp counts. These template counts differ from the live SDK layout after mirroring.

```sh
node runner/replay_dump.mjs replays/gate/sparring_meta_expanse_A.repl26a --every 50
# Tributed gems at rounds 250/500 and the round each side reaches 1,000, per match:
python runner/gem_pace.py manifests/gate_sparring_meta.manifest --bot main
# A targeted panel (fresh replays, built bots, gem-pace table):
python runner/make_panel.py main sparring-meta --maps expanse elkring -o replays/panels/x.manifest --run
```

`run_final_gates.py` now also runs `sparring-meta` (the ladder-meta fast farmer: v5b's
code with the Cassi & Issac / Vendetta / Varg / Ryth / Tavi draft) and prints the gem
pace of every suite.


## Top-team analysis and frozen comparison

`analyse_match_groups.py` accepts the supplied ZIP paths, unpacks their replays
under ignored `replays/top-five/`, and decodes through the official engine.
Use `--metadata` to fetch public match-group metadata. Run `--help` for options.

Freeze the desired baseline source under `replays/evaluation/incumbent/src/` first.
Then evaluate a snapshot on all installed maps and both sides:

```sh
python runner/evaluate_candidate.py --output replays/evaluation/new-check
```

The output includes exact source/map hashes, full replays, diagnostics and
`results.json`. It uses release mode, default fuel, complete matches and engine
outcomes. Development fixtures informed policy selection; they are not an
untouched holdout. Baseline fallback fixtures are near-mirrors.

```sh
cambc bundle replays/evaluation/new-check/agent --output quantum-altar-v16.zip
python runner/release_report.py --evaluation replays/evaluation/new-check --bundle quantum-altar-v16.zip
```

The report checks every bundled source byte against the evaluated snapshot and
both live source trees before recording the bundle hash.
