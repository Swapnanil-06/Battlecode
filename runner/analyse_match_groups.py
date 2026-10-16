"""Inspect user-provided match group ZIPs using the official replay engine."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import re
import subprocess
import urllib.request
import zipfile


def unpack(source, out):
    group = source.stem.removeprefix('match-group-')
    dest = out / group
    dest.mkdir(parents=True, exist_ok=True)
    tasks = []
    with zipfile.ZipFile(source) as archive:
        for name in archive.namelist():
            if not name.endswith('.zip'):
                continue
            data = archive.read(name)
            target = dest / Path(name).name
            target.write_bytes(data)
            with zipfile.ZipFile(io.BytesIO(data)) as inner:
                logs = {}
                for member in inner.namelist():
                    if member.endswith('.stdout'):
                        log = inner.read(member)
                        logs[member] = dict(
                            errors=len(re.findall(rb'bot error:', log)),
                            suspensions=max([int(v) for v in re.findall(rb'suspensions=(\d+)', log)] or [0]),
                            text=re.findall(rb'[ -~]{6,}', log),
                        )
                        logs[member]['text'] = [v.decode(errors='replace') for v in logs[member]['text']]
                (target.with_suffix('.logs.json')).write_text(json.dumps(logs, indent=2))
            tasks.append(target)
    return tasks


def decode(path):
    output = path.with_suffix('.json')
    if not output.exists():
        result = subprocess.run(['node', 'runner/replay_dump.mjs', str(path), '--every', '1', '--profile', '--champs', '--camps'],
                                capture_output=True, text=True, check=True)
        output.write_text(result.stdout)
    return str(path)


def summarise(out):
    records = []
    for groupfile in sorted(out.glob('*/group.json')):
        group = json.loads(groupfile.read_text())
        for match in group['matches']:
            path = next(groupfile.parent.glob('*' + match['id'] + '.json'))
            data = json.loads(path.read_text())
            logs = json.loads(path.with_suffix('.logs.json').read_text())
            ours = 0 if match['sides'][0]['teamName'] == 'Quantum Altar Keepers' else 1
            theirs = 1 - ours
            profiles = []
            for side in (ours, theirs):
                total = {}
                for item in data['prof'].values():
                    if item['team'] == side:
                        for key, value in item.items():
                            if key != 'team':
                                total[key] = total.get(key, 0) + value
                profiles.append({k: round(100 * v / max(1, total['turns']), 1) for k, v in total.items()})
            pace = []
            for r in (100, 200, 300, 400, 500):
                state = next((v for v in data['rounds'] if v['r'] == r), None)
                if state:
                    pace.append([r, state['sub'][ours], state['sub'][theirs], state['carried'][ours], state['carried'][theirs]])
            record = dict(opponent=match['sides'][theirs]['teamName'], map=match['map'], match=match['id'],
                          rounds=data['finalRound'], score=[data['submitted'][ours], data['submitted'][theirs]],
                          drafts=[data['drafts'][ours], data['drafts'][theirs]],
                          deaths=[data['events']['deaths'][ours], data['events']['deaths'][theirs]],
                          lost=[data['events']['gemsLostOnDeath'][ours], data['events']['gemsLostOnDeath'][theirs]],
                          profile=profiles, pace=pace, diagnostics=logs)
            records.append(record)
            print(record['opponent'], record['map'], record['score'], 'deaths', record['deaths'], 'lost', record['lost'],
                  'idle', [p.get('idle',0) for p in profiles], 'attack', [p.get('attack',0) for p in profiles], 'pace', pace)
    (out / 'analysis.json').write_text(json.dumps(records, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archives', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, default=Path('replays/top-five'))
    parser.add_argument('--metadata', action='store_true')
    args = parser.parse_args()
    paths = []
    for source in args.archives:
        paths.extend(unpack(source, args.output))
        if args.metadata:
            group = source.stem.removeprefix('match-group-')
            with urllib.request.urlopen('https://2026a.battlecode.co.uk/api/v1/match-groups/' + group) as response:
                (args.output / group / 'group.json').write_bytes(response.read())
    with ThreadPoolExecutor(max_workers=4) as pool:
        for value in pool.map(decode, paths):
            print(value, flush=True)
    summarise(args.output)


if __name__ == '__main__':
    main()
