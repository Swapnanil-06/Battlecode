#!/usr/bin/env python3
import glob
import os
import zipfile
import re

def audit():
    replay_files = sorted(glob.glob("replays/gate/*.repl26a"))
    print(f"Auditing {len(replay_files)} gate replay files in replays/gate/...")
    
    total_errors = 0
    team_a_errors = 0
    error_breakdown = {}
    
    for rpath in replay_files:
        try:
            with zipfile.ZipFile(rpath) as z:
                for member in ["team-a.stdout", "team-b.stdout"]:
                    if member in z.namelist():
                        data = z.read(member).decode("utf-8", errors="replace")
                        for line in data.splitlines():
                            if "bot error" in line.lower():
                                total_errors += 1
                                if member == "team-a.stdout":
                                    team_a_errors += 1
                                m = re.search(r"bot error in round \d+: ([^a-zA-Z0-9]*[a-zA-Z0-9_ -]+)", line)
                                err_cls = m.group(1).strip() if m else line.strip()
                                error_breakdown[err_cls] = error_breakdown.get(err_cls, 0) + 1
                                print(f"[{os.path.basename(rpath)}:{member}] {line.strip()}")
        except Exception as e:
            print(f"Error reading {rpath}: {e}")

    print("=" * 60)
    print(f"TOTAL BOT ERRORS (ALL STDOUT): {total_errors}")
    print(f"TOTAL BOT ERRORS IN TEAM-A.STDOUT: {team_a_errors}")
    print("Per-class breakdown:")
    if not error_breakdown:
        print("  None (0 errors)")
    else:
        for err, count in error_breakdown.items():
            print(f"  {err}: {count}")
    print("=" * 60)
    return total_errors

if __name__ == "__main__":
    audit()
