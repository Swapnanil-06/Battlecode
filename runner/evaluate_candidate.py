"""Freeze a candidate and compare it to an explicitly frozen local baseline."""
import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
import re


def fingerprint(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*.py')) if '__pycache__' not in p.parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, default=Path('replays/evaluation/incumbent'))
    parser.add_argument('--bot', type=Path, default=Path('bots/main'))
    parser.add_argument('--maps', nargs='*')
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--set', action='append', default=[])
    args = parser.parse_args()
    root = Path.cwd()
    args.output.mkdir(parents=True, exist_ok=False)
    frozen = args.output / 'agent' / 'src'
    shutil.copytree(args.bot / 'src', frozen, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    if args.set:
        with (frozen / 'policy.py').open('a') as stream:
            for assignment in args.set:
                key, value = assignment.split('=', 1)
                if not key.isidentifier():
                    raise ValueError('invalid policy key')
                stream.write('\n' + key + ' = ' + repr(ast.literal_eval(value)) + '\n')
    maps = [root / 'maps' / (m + '.map26a') for m in args.maps] if args.maps else sorted((root / 'maps').glob('*.map26a'))
    manifest = args.output / 'fixtures.manifest'
    tasks = []
    rows = []
    for mapfile in maps:
        for side in (0, 1):
            name = mapfile.stem + '_' + 'AB'[side]
            replay = args.output / (name + '.repl26a')
            agents = [args.output / 'agent', args.baseline]
            if side:
                agents.reverse()
            paths = [os.path.relpath(p, args.output).replace('\\', '/') for p in [*agents, mapfile, replay]]
            rows.append(' '.join(paths))
            tasks.append((replay, side, mapfile.stem))
    manifest.write_text('\n'.join(rows) + '\n')
    inputs = dict(candidate=fingerprint(frozen), baseline=fingerprint(args.baseline / 'src'),
                  sdk=(root / 'cambc.toml').read_text(), maps={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in maps})
    (args.output / 'inputs.json').write_text(json.dumps(inputs, indent=2))
    subprocess.run(['cambc', 'build', str(args.output / 'agent')], check=True)
    subprocess.run(['cambc', 'run-batch', str(manifest), '--jobs', str(args.jobs), '--release'], check=True)
    def analyse(task):
        replay, side, mapname = task
        result = subprocess.run(['node', 'runner/replay_dump.mjs', str(replay), '--every', '50'], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        with zipfile.ZipFile(replay) as archive:
            log = archive.read('team-' + 'ab'[side] + '.stdout')
        record = dict(map=mapname, side=side, win=data['outcome'] == side + 1,
                      score=[data['submitted'][side], data['submitted'][1-side]], rounds=data['finalRound'],
                      deaths=[data['events']['deaths'][side], data['events']['deaths'][1-side]],
                      errors=len(re.findall(rb'bot error:', log)),
                      suspensions=max([int(v) for v in re.findall(rb'suspensions=(\d+)', log)] or [0]),
                      pace=data['rounds'])
        print(json.dumps({k:v for k,v in record.items() if k != 'pace'}), flush=True)
        return record
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(analyse, tasks))
    report = dict(inputs=inputs, results=results, wins=sum(r['win'] for r in results), games=len(results))
    (args.output / 'results.json').write_text(json.dumps(report, indent=2))
    print('WINS', report['wins'], '/', report['games'], flush=True)


if __name__ == '__main__':
    main()
