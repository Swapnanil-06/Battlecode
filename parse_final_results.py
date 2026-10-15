#!/usr/bin/env python3
import os
import re
import zipfile
import glob

maps = ['collision', 'corners', 'elkring', 'expanse', 'interlock', 'lanes', 'monolith', 'packs', 'rows']
opponents = [
    ('starter-python', 'starter_python', 'gate_starter_python.log'),
    ('starter-cpp', 'starter_cpp', 'gate_starter_cpp.log'),
    ('sparring-hunter', 'sparring_hunter', 'gate_sparring_hunter.log'),
    ('sparring-altar', 'sparring_altar', 'gate_sparring_altar.log'),
    ('sparring-denial', 'sparring_denial', 'gate_sparring_denial.log'),
    ('sparring-meta', 'sparring_meta', 'gate_sparring_meta.log'),
]

print("=" * 80)
print("FINAL BENCHMARK RESULTS")
print("=" * 80)

summary_table = {}

for opp_name, opp_key, log_file in opponents:
    results = {}
    with open(log_file) as f:
        content = f.read()
    
    # Matches look like:
    # [+] TEAM A WIN (main)  main vs starter-python  corners  Round 0474/2000
    # [+] TEAM B WIN (main)  starter-python vs main  corners  Round 0440/2000
    pattern = re.compile(r"\[\+\] (TEAM [AB] WIN \([^)]+\))\s+([^\s]+)\s+vs\s+([^\s]+)\s+([^\s]+)\s+Round\s+(\d+)/2000")
    for match in pattern.finditer(content):
        winner_tag, bot_a, bot_b, map_name, rounds = match.groups()
        main_won = "main" in winner_tag
        side = 'A' if bot_a == 'main' else 'B'
        results[(map_name, side)] = {
            'won': main_won,
            'winner': winner_tag,
            'rounds': int(rounds)
        }
    
    summary_table[opp_name] = results

# Print per-opponent table
for opp_name, opp_key, _ in opponents:
    results = summary_table[opp_name]
    wins = sum(1 for r in results.values() if r['won'])
    total = len(results)
    pct = (wins / total * 100) if total else 0
    print(f"\n### Opponent: {opp_name} (Total: {wins}/{total} = {pct:.1f}%)")
    print(f"{'Map':<12} | {'Side A (main)':<20} | {'Side B (main)':<20} | {'Map Result':<10}")
    print("-" * 70)
    for m in maps:
        res_a = results.get((m, 'A'), {'won': False, 'rounds': 0})
        res_b = results.get((m, 'B'), {'won': False, 'rounds': 0})
        a_str = f"{'WIN' if res_a['won'] else 'LOSS'} (r{res_a['rounds']})"
        b_str = f"{'WIN' if res_b['won'] else 'LOSS'} (r{res_b['rounds']})"
        map_wins = (1 if res_a['won'] else 0) + (1 if res_b['won'] else 0)
        map_res = f"{map_wins}/2"
        print(f"{m:<12} | {a_str:<20} | {b_str:<20} | {map_res:<10}")

# Check all replays for errors/faults
print("\n" + "=" * 80)
print("CHECKING REPLAYS FOR ENGINE FAULTS AND BOT EXCEPTIONS")
print("=" * 80)

total_replays = 0
total_bot_errors = 0
replays = glob.glob("replays/gate/*.repl26a")

for rpath in sorted(replays):
    total_replays += 1
    with zipfile.ZipFile(rpath) as z:
        # Check team stdout for bot error
        for fname in ['team-a.stdout', 'team-b.stdout']:
            if fname in z.namelist():
                text = z.open(fname).read().decode('ascii', errors='ignore')
                for line in text.splitlines():
                    if 'bot error:' in line.lower() or 'traceback' in line.lower():
                        if fname == 'team-a.stdout' and 'main' in rpath:
                            print(f"[ERROR in {rpath} {fname}]: {line.strip()}")
                            total_bot_errors += 1
                        elif fname == 'team-b.stdout' and '_B.repl26a' in rpath:
                            print(f"[ERROR in {rpath} {fname}]: {line.strip()}")
                            total_bot_errors += 1

print(f"Total replays checked: {total_replays}")
print(f"Total bot exceptions found in main: {total_bot_errors}")
