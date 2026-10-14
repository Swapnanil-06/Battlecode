#!/usr/bin/env python3
import subprocess
import os
import re
import sys
import time

manifests = [
    ("starter-python", "manifests/gate_starter_python.manifest", "gate_starter_python.log"),
    ("starter-cpp", "manifests/gate_starter_cpp.manifest", "gate_starter_cpp.log"),
    ("sparring-hunter", "manifests/gate_sparring_hunter.manifest", "gate_sparring_hunter.log"),
    ("sparring-altar", "manifests/gate_sparring_altar.manifest", "gate_sparring_altar.log"),
    ("sparring-denial", "manifests/gate_sparring_denial.manifest", "gate_sparring_denial.log"),
]

print("Starting final gates benchmark suite across all 5 opponents and 9 maps (18 matches each)...")
start_time = time.time()

# Pre-build bots so that run-batch does not encounter build races
print("Pre-building bots...")
subprocess.run(["cambc", "build", "bots/main"], check=True)
subprocess.run(["cambc", "build", "bots/starter-cpp"], check=True)

for opp, manifest, logfile in manifests:
    print(f"Running {opp} ({manifest})...")
    m_start = time.time()
    cmd = ["cambc", "run-batch", manifest, "--jobs", "4"]
    with open(logfile, "w") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True)
    print(f"  {opp} finished in {time.time() - m_start:.1f}s")

total_duration = time.time() - start_time
print(f"All gates finished in {total_duration:.1f}s!")
