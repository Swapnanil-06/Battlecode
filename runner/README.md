# Local match runner

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
