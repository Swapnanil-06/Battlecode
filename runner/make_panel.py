#!/usr/bin/env python3
"""Write a run-batch manifest: our bot vs an opponent on chosen maps, both sides.

    python runner/make_panel.py main sparring-meta --maps expanse elkring -o replays/panels/x.manifest --run

--run replaces the panel's earlier replays (run-batch refuses to overwrite them), builds both
bots, plays the panel and prints its gem pace (runner/gem_pace.py).
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("bot")
parser.add_argument("opponent")
parser.add_argument("--maps", nargs="*", help="map stems (default: every map in maps/)")
parser.add_argument("--sides", default="AB", help="our sides to play: A, B or AB")
parser.add_argument("-o", "--output", type=Path, required=True)
parser.add_argument("--run", action="store_true")
parser.add_argument("--jobs", type=int, default=4)
args = parser.parse_args()
maps = args.maps or sorted(p.stem for p in (ROOT / "maps").glob("*.map26a"))
out = args.output.resolve()
out.parent.mkdir(parents=True, exist_ok=True)
replays = out.parent / out.stem
lines = []
for side in args.sides:
    for name in maps:
        a, b = (args.bot, args.opponent) if side == "A" else (args.opponent, args.bot)
        lines.append(f"{ROOT / 'bots' / a} {ROOT / 'bots' / b} {ROOT / 'maps' / (name + '.map26a')} "
                     f"{replays / f'{args.bot}_vs_{args.opponent}_{name}_{side}.repl26a'}")
out.write_text("\n".join(lines) + "\n")
print(f"{out}: {len(lines)} matches")

if args.run:
    shutil.rmtree(replays, ignore_errors=True)
    replays.mkdir(parents=True)
    for bot in {args.bot, args.opponent}:
        subprocess.run(["cambc", "build", str(ROOT / "bots" / bot)], check=True, stdout=subprocess.DEVNULL)
    with open(out.with_suffix(".log"), "w") as log:
        subprocess.run(["cambc", "run-batch", str(out), "--jobs", str(args.jobs)], stdout=log, stderr=subprocess.STDOUT, check=True)
    sys.exit(subprocess.run([sys.executable, str(ROOT / "runner" / "gem_pace.py"), str(out), "--bot", args.bot]).returncode)
