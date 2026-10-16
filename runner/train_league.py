"""Offline tuple-model policy search against a frozen opponent league.

Each evaluated policy is built and played in the real WASI engine. Historical
bots supply frozen opponents; measured results seed subsequent proposals. The
eight newer maps are deliberately absent from TRAIN_MAPS. Validation never
feeds back into selection. This is black-box policy learning, not a neural
network, and makes no inference about unobserved opponents' source code.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from itertools import combinations, product
import json
from math import log, sqrt
import os
from pathlib import Path
import random
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TRAIN_MAPS = ('collision', 'elkring', 'rows', 'expanse')
VALIDATION_MAPS = ('ambush', 'contest', 'eight', 'fragment', 'pilgrimage',
                   'rushbait-v2', 'stampede', 'swirl')
ROSTERS = (
    (2, 10, 6, 9, 0),   # incumbent
    (9, 4, 3, 0, 8),    # Varg / Stellar / duo
    (9, 0, 3, 8, 4),    # Varg / Ryth / duo
    (3, 4, 9, 10, 8),   # duo / Stellar / Varg
    (8, 3, 4, 9, 0),    # Ren / duo / Stellar
    (0, 4, 8, 10, 9),   # Ryth / Stellar / Ren
    (2, 9, 0, 10, 3),   # Vendetta / Varg / Ryth
    (9, 2, 4, 10, 8),   # Varg / Vendetta / Stellar
)
BASE = dict(DASH_WALK=True, JOB_LEASES=True, TAVI_STRENGTH=True,
            JUNGLE_BUILD=True, CLAIM_FACTOR=0.25,
            ROSTER=ROSTERS[0])


def suggest_ntuple(archive, rng):
    """One/two-tuple UCB surrogate; prefer informative unseen policies.

    This small adaptation of NTBEA models interactions without fitting a large
    neural network to a handful of noisy full-game outcomes.
    """
    keys = ('ROSTER', 'DASH_WALK', 'JOB_LEASES', 'TAVI_STRENGTH', 'JUNGLE_BUILD', 'CLAIM_FACTOR')
    domains = (ROSTERS, (False, True), (False, True), (False, True), (False, True), (0.1, 0.25, 0.5, 0.8))
    subsets = [subset for size in (1, 2) for subset in combinations(range(len(keys)), size)]
    tables = {subset: {} for subset in subsets}
    visited = set()
    prior = sum(record['score'] for record in archive) / max(1, len(archive))
    def point(config):
        return tuple(tuple(config[key]) if key == 'ROSTER' else config[key] for key in keys)
    for record in archive:
        values = point(record['config'])
        visited.add(values)
        for subset, table in tables.items():
            key = tuple(values[index] for index in subset)
            total, count = table.get(key, (0, 0))
            table[key] = total + record['score'], count + 1
    candidates = list(product(*domains))
    rng.shuffle(candidates)  # Stable seeded tie breaking.
    best, best_value = None, -float('inf')
    for values in candidates:
        if values in visited:
            continue
        estimate = 0
        for subset, table in tables.items():
            total, count = table.get(tuple(values[index] for index in subset), (0, 0))
            mean = total / count if count else prior
            estimate += mean + 0.35 * sqrt(log(len(archive) + 2) / (count + 1))
        if estimate > best_value:
            best, best_value = values, estimate
    if best is None:
        return dict(max(archive, key=lambda record: record['score'])['config'])
    config = dict(BASE)
    config.update(zip(keys, best))
    return config


def cli_path():
    found = shutil.which('cambc')
    if found:
        return found
    return str(Path.home() / 'AppData/Roaming/Python/Python313/Scripts/cambc.exe')


def policy_source(config):
    return '"""Selected by real-engine offline policy search."""\n' + ''.join(
        f'{key} = {value!r}\n' for key, value in sorted(config.items()))


def check_inputs(output, maps, opponents, seed):
    """Refuse to reuse scores after a map or frozen opponent has changed."""
    all_maps = sorted(set(maps) | set(VALIDATION_MAPS))
    inputs = dict(seed=seed, sdk=(ROOT / 'cambc.toml').read_text(),
                  maps={name: hashlib.sha256((ROOT / 'maps' / f'{name}.map26a').read_bytes()).hexdigest()
                        for name in all_maps}, opponents={})
    for name in opponents:
        files = sorted(p for p in (ROOT / 'bots' / name / 'src').rglob('*')
                       if p.is_file() and '__pycache__' not in p.parts)
        inputs['opponents'][name] = hashlib.sha256(b''.join(p.read_bytes() for p in files)).hexdigest()
    target = output / 'inputs.json'
    if target.exists() and json.loads(target.read_text()) != inputs:
        raise ValueError('Frozen maps/opponents changed; start a fresh experiment directory')
    target.write_text(json.dumps(inputs, indent=2) + '\n')


def analyse(task):
    replay, side, opponent, map_name = task
    output = subprocess.run(['node', str(ROOT / 'runner/replay_dump.mjs'),
                             str(replay), '--every', '1'], check=True,
                            capture_output=True, text=True).stdout
    data = json.loads(output)
    with zipfile.ZipFile(replay) as archive:
        log = archive.read(f'team-{chr(97 + side)}.stdout')
    import re
    suspensions = max([int(v) for v in re.findall(rb'suspensions=(\d+)', log)] or [0])
    error = b'bot error:' in log
    other = 1 - side
    us, them = data['submitted'][side], data['submitted'][other]
    at250 = [0, 0]
    for point in data['rounds']:
        if point['r'] <= 250:
            at250 = point['sub']
    win = data['outcome'] == side + 1
    # Wins dominate; margin and early delivery break ties. Every failure counts.
    score = int(win) + 0.2 * (us - them) / max(1000, us + them)
    score += 0.05 * (at250[side] - at250[other]) / 1000
    if error or suspensions:
        score -= 2
    return dict(map=map_name, side='AB'[side], opponent=opponent, win=win,
                score=score, gems=us, enemy_gems=them, round=data['finalRound'],
                deaths=data['events']['deaths'][side],
                gems_lost=data['events']['gemsLostOnDeath'][side],
                suspensions=suspensions, logged_error=error,
                replay=str(replay.relative_to(ROOT)))


def evaluate(config, name, output, maps, opponents, cli, jobs, source_bot='league'):
    directory = output / name
    report = directory / 'result.json'
    base = ROOT / 'bots' / source_bot / 'src'
    base_hash = hashlib.sha256(b''.join(p.read_bytes() for p in
        sorted(base.rglob('*.py')))).hexdigest()
    spec = dict(config=config, maps=list(maps), opponents=list(opponents),
                source=base_hash, sdk=(ROOT / 'cambc.toml').read_text())
    if source_bot != 'league':
        spec['source_bot'] = source_bot
    # Round-trip tuples to JSON lists so resumed comparisons are exact.
    spec = json.loads(json.dumps(spec))
    if report.exists():
        previous = json.loads(report.read_text())
        if previous.get('spec') != spec:
            raise ValueError(f'{directory} contains a different experiment; use a new output directory')
        return previous
    source = directory / 'agent/src'
    shutil.copytree(base, source,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'), dirs_exist_ok=True)
    (source / 'policy.py').write_text(policy_source(config))
    lines, tasks = [], []
    for opponent in opponents:
        for side in (0, 1):
            for map_name in maps:
                replay = directory / f'{opponent}-{map_name}-{side}.repl26a'
                a, b = directory / 'agent', ROOT / 'bots' / opponent
                if side:
                    a, b = b, a
                # Relative paths have no workspace spaces; resolve from the manifest.
                paths = (a, b, ROOT / 'maps' / f'{map_name}.map26a', replay)
                lines.append(' '.join(os.path.relpath(p, directory) for p in paths))
                tasks.append((replay, side, opponent, map_name))
    manifest = directory / 'panel.manifest'
    manifest.write_text('\n'.join(lines) + '\n')
    with (directory / 'engine.log').open('w') as log:
        subprocess.run([cli, 'run-batch', str(manifest), '--jobs', str(jobs)],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    with ThreadPoolExecutor(max_workers=min(jobs, 4)) as pool:
        rows = list(pool.map(analyse, tasks))
    summary = dict(name=name, config=config, spec=spec, games=len(rows),
                   wins=sum(r['win'] for r in rows),
                   score=sum(r['score'] for r in rows) / len(rows),
                   code_sha256=hashlib.sha256(b''.join(
                       p.read_bytes() for p in sorted(source.rglob('*.py')))).hexdigest(),
                   rows=rows)
    report.write_text(json.dumps(summary, indent=2) + '\n')
    print(f"{name}: {summary['wins']}/{len(rows)} score={summary['score']:.3f}", flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--trials', type=int, default=7)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--opponents', nargs='+', default=['main', 'sparring-meta'])
    parser.add_argument('--maps', nargs='+', default=list(TRAIN_MAPS))
    parser.add_argument('--seed', type=int, default=20261016)
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    if args.trials < 1 or args.jobs < 1:
        parser.error('--trials and --jobs must be positive')
    if set(args.maps) & set(VALIDATION_MAPS):
        parser.error('validation maps must stay out of training')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    check_inputs(output, args.maps, args.opponents, args.seed)
    rng, archive = random.Random(args.seed), []
    cli = cli_path()
    for index in range(args.trials):
        # Warm start every roster before mutation to avoid a premature collapse.
        config = dict(BASE)
        previous_path = output / f'trial-{index:03d}' / 'result.json'
        if previous_path.exists():
            config = json.loads(previous_path.read_text())['config']
        elif index == 0:
            config.update(DASH_WALK=False, JOB_LEASES=False, TAVI_STRENGTH=False, JUNGLE_BUILD=False)
        elif index <= len(ROSTERS):
            config['ROSTER'] = ROSTERS[index - 1]
        else:
            config = suggest_ntuple(archive, rng)
        print(f'Training {index + 1}/{args.trials}: {config}', flush=True)
        archive.append(evaluate(config, f'trial-{index:03d}', output,
                                args.maps, args.opponents, cli, args.jobs))
        (output / 'archive.json').write_text(json.dumps(archive, indent=2) + '\n')
    clean = [record for record in archive if not any(
        row['suspensions'] or row['logged_error'] for row in record['rows'])]
    if not clean:
        raise RuntimeError('No clean candidate; no policy selected for deployment')
    best = max(clean, key=lambda r: r['score'])
    (output / 'selected-policy.py').write_text(policy_source(best['config']))
    print(f"Selected {best['name']}; training {best['wins']}/{best['games']}", flush=True)
    if args.validate:
        validation = evaluate(best['config'], 'validation', output, VALIDATION_MAPS,
                              args.opponents, cli, args.jobs)
        print(f"Independent validation: {validation['wins']}/{validation['games']}", flush=True)
    print(f'Policy and full evidence: {output}', flush=True)


if __name__ == '__main__':
    main()
