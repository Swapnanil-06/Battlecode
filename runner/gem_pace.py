#!/usr/bin/env python3
"""Gem pace per match: tributed gems at rounds 250/500 and the round each side reaches 1,000.

Reads replays through runner/replay_dump.mjs (the visualiser's engine), so it works on any
.repl26a bundle, including ladder replays and bots that print nothing.

    python runner/gem_pace.py manifests/gate_sparring_altar.manifest [...] [--bot main]

Each manifest line is `bot-a bot-b map replay`; `--bot` names our bot by its final path
component. Prints one row per match and a summary; `--json` writes the rows.
"""
import argparse
import json
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DUMP = ROOT / "runner" / "replay_dump.mjs"
MARKS = (250, 500)


def pace(replay):
    """{'round', 'winner', 'gems': [a, b], 'at': {mark: [a, b]}, 'to1000': [a, b]} from a replay."""
    out = subprocess.run(["node", str(DUMP), str(replay), "--every", "1"],
                         capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    at = {mark: [0, 0] for mark in MARKS}
    to1000 = [None, None]
    for point in data["rounds"]:
        for mark in MARKS:
            if point["r"] <= mark:
                at[mark] = point["sub"]
        for team in (0, 1):
            if to1000[team] is None and point["sub"][team] >= 1000:
                to1000[team] = point["r"]
    for team in (0, 1):  # the winning tribute lands in the final round
        if to1000[team] is None and data["submitted"][team] >= 1000:
            to1000[team] = data["finalRound"]
    return {"round": data["finalRound"], "winner": {1: 0, 2: 1}.get(data["outcome"]),
            "gems": data["submitted"], "at": at, "to1000": to1000,
            "deaths": data["events"]["deaths"], "carrier_deaths": data["events"]["carrierDeaths"]}


def rows_from_manifest(manifest, bot):
    base = Path(manifest).resolve().parent
    rows = []
    for line in Path(manifest).read_text().splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        a, b, map_path, replay = parts
        names = [Path(a).name, Path(b).name]
        if bot not in names:
            continue
        us = names.index(bot)
        replay = (base / replay).resolve()
        row = {"map": Path(map_path).stem, "side": "AB"[us], "opponent": names[1 - us], "replay": str(replay)}
        if not replay.exists():
            row["error"] = "missing replay"
            rows.append(row)
            continue
        p = pace(replay)
        them = 1 - us
        row.update(result="win" if p["winner"] == us else "loss", round=p["round"],
                   us250=p["at"][250][us], them250=p["at"][250][them],
                   us500=p["at"][500][us], them500=p["at"][500][them],
                   us1000=p["to1000"][us], them1000=p["to1000"][them],
                   gems=p["gems"][us], them_gems=p["gems"][them],
                   deaths=p["deaths"][us], carrier_deaths=p["carrier_deaths"][us])
        rows.append(row)
    return rows


def summarize(rows, label=""):
    done = [r for r in rows if "error" not in r]
    if not done:
        print(f"{label}: no completed replays")
        return
    def med(key):
        return statistics.median(r[key] for r in done)
    reached = [r["us1000"] for r in done if r["us1000"]]
    them_reached = [r["them1000"] for r in done if r["them1000"]]
    # Unreached counts as 2,000 so a slower bot cannot look faster by never finishing.
    to1000 = statistics.median([r["us1000"] or 2000 for r in done])
    them_to1000 = statistics.median([r["them1000"] or 2000 for r in done])
    wins = sum(r["result"] == "win" for r in done)
    print(f"{label}: {wins}/{len(done)} wins | gems@250 med {med('us250')} vs {med('them250')} | "
          f"gems@500 med {med('us500')} vs {med('them500')} (sum {sum(r['us500'] for r in done)} vs "
          f"{sum(r['them500'] for r in done)}) | round to 1000 med {to1000} vs {them_to1000} "
          f"(reached {len(reached)} vs {len(them_reached)}) | deaths {sum(r['deaths'] for r in done)} "
          f"carrier {sum(r['carrier_deaths'] for r in done)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("manifests", nargs="+")
    parser.add_argument("--bot", default="main")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--quiet", action="store_true", help="summary lines only")
    args = parser.parse_args()
    everything = []
    for manifest in args.manifests:
        rows = rows_from_manifest(manifest, args.bot)
        everything += rows
        if not args.quiet:
            for r in rows:
                if "error" in r:
                    print(f"  {r['map']:<10} {r['side']} vs {r['opponent']}: {r['error']}")
                    continue
                print(f"  {r['map']:<10} {r['side']} vs {r['opponent']:<16} {r['result']:<4} r{r['round']:<4} "
                      f"@250 {r['us250']:>4}/{r['them250']:<4} @500 {r['us500']:>4}/{r['them500']:<4} "
                      f"to1000 {r['us1000'] or '-':>4}/{r['them1000'] or '-':<4} deaths {r['deaths']} ({r['carrier_deaths']} carrying)")
        summarize(rows, Path(manifest).stem)
    if len(args.manifests) > 1:
        summarize(everything, "all")
    if args.json:
        args.json.write_text(json.dumps(everything, indent=1) + "\n")


if __name__ == "__main__":
    main()
