#!/usr/bin/env python3
"""Run complete local matches and report wins from CAMBC's statistics JSON."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bot", default="main", help="our bot name or project path")
    parser.add_argument("--opponent", default="starter-python")
    parser.add_argument("-n", "--matches", type=int, default=18, help="total matches (default: 18)")
    parser.add_argument("--maps-dir", type=Path, default=ROOT / "maps")
    parser.add_argument("--timeout", type=float, default=300, help="seconds per match (default: 300)")
    args = parser.parse_args()
    if args.matches < 1 or args.timeout <= 0:
        parser.error("matches and timeout must be positive")
    maps = sorted(args.maps_dir.resolve().glob("*.map26a"))
    if not maps:
        parser.error("no .map26a maps found; run 'cambc maps pull' first")

    output_root = ROOT / "replays" / "batches"
    output_root.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="run-", dir=output_root))
    print(f"Results: {output}", flush=True)
    results = []
    counts = defaultdict(Counter)
    for index in range(args.matches):
        # Visit every map before repeating, then reverse sides for the next pass.
        map_path = maps[index % len(maps)]
        our_team = (index // len(maps)) % 2
        bots = [args.bot, args.opponent] if our_team == 0 else [args.opponent, args.bot]
        match_dir = output / f"{index + 1:03d}-{map_path.stem}"
        match_dir.mkdir()
        stats_path = match_dir / "statistics.json"
        log_path = match_dir / "run.log"
        command = ["cambc", "run", *bots, "--map", str(map_path),
                   "--out-dir", str(match_dir), "--statistics", str(stats_path)]
        print(f"[{index + 1}/{args.matches}] {map_path.stem}: "
              f"{args.bot} as team {'AB'[our_team]}", flush=True)
        result = {"map": map_path.name, "team": our_team, "command": command}
        try:
            with log_path.open("w") as log:
                subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                               timeout=args.timeout, check=True)
            stats = json.loads(stats_path.read_text())
            # Never infer a winner from score alone: the engine has tiebreakers.
            if stats["outcome"] not in ("teamA", "teamB"):
                raise ValueError(f"not a completed result: {stats['outcome']!r}")
            winner = 0 if stats["outcome"] == "teamA" else 1
            result.update(result="win" if winner == our_team else "loss",
                          round=stats["round"], faults=stats["botFaults"][our_team])
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError) as error:
            result.update(result="error", error=str(error))
            print(f"  ERROR: {error}; see {log_path}", flush=True)
        else:
            print(f"  {result['result']} in round {result['round']}; "
                  f"our bot faults: {result['faults']}", flush=True)
        results.append(result)
        counts[map_path.name][result["result"]] += 1

    total = Counter()
    for name, count in counts.items():
        total.update(count)
        completed = count["win"] + count["loss"]
        rate = f"{count['win'] / completed:.1%}" if completed else "n/a"
        print(f"{name}: {count['win']}W {count['loss']}L {count['error']} errors; win rate {rate}")
    completed = total["win"] + total["loss"]
    rate = f"{total['win'] / completed:.1%}" if completed else "n/a"
    faults = sum(result.get("faults", 0) for result in results)
    print(f"Overall: {total['win']}W {total['loss']}L {total['error']} errors; "
          f"win rate {rate} ({completed}/{args.matches} completed); our bot faults: {faults}")
    (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    return 1 if total["error"] or faults else 0


if __name__ == "__main__":
    raise SystemExit(main())
