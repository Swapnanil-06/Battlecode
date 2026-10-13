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

# Run in two waves: 2 concurrent in wave 1, 2 concurrent in wave 2, 1 in wave 3
# Each process uses --jobs 2 (so 4 cores total)
def run_manifest(opp, manifest, logfile):
    cmd = ["cambc", "run-batch", manifest, "--jobs", "2"]
    with open(logfile, "w") as f:
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
    return p

# Wave 1: starter-python and starter-cpp
print("Wave 1: starter-python & starter-cpp...")
p1 = run_manifest(*manifests[0])
p2 = run_manifest(*manifests[1])
p1.wait()
p2.wait()
print(f"Wave 1 finished in {time.time() - start_time:.1f}s")

# Wave 2: sparring-hunter and sparring-altar
print("Wave 2: sparring-hunter & sparring-altar...")
w2_start = time.time()
p3 = run_manifest(*manifests[2])
p4 = run_manifest(*manifests[3])
p3.wait()
p4.wait()
print(f"Wave 2 finished in {time.time() - w2_start:.1f}s")

# Wave 3: sparring-denial
print("Wave 3: sparring-denial...")
w3_start = time.time()
p5 = run_manifest(*manifests[4])
p5.wait()
print(f"Wave 3 finished in {time.time() - w3_start:.1f}s")

total_duration = time.time() - start_time
print(f"All gates finished in {total_duration:.1f}s!")
