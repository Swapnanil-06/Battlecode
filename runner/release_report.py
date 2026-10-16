"""Write auditable release evidence from frozen evaluation and replay analysis."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evaluation', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args()
    pool = json.loads((args.evaluation / 'results.json').read_text())
    frozen = args.evaluation / 'agent' / 'src'
    expected = {f'src/{p.relative_to(frozen).as_posix()}': p.read_bytes()
                for p in frozen.rglob('*.py')}
    with zipfile.ZipFile(args.bundle) as archive:
        actual = {name: archive.read(name) for name in archive.namelist() if not name.endswith('/')}
    if actual != expected:
        raise ValueError('Bundle does not match the tested source snapshot')
    for name, contents in actual.items():
        ast.parse(contents, filename=name)
        live = Path('bots/main') / name
        mirror = Path('bots/league') / name
        if live.read_bytes() != contents or mirror.read_bytes() != contents:
            raise ValueError('Working bot differs from the release: ' + name)
    historical = json.loads(Path('replays/top-five/analysis.json').read_text())
    analysis = []
    for record in historical:
        item = {k:v for k,v in record.items() if k not in ('diagnostics', 'profile')}
        item['diagnostics'] = {name: {k:v for k,v in data.items() if k != 'text'}
                               for name, data in record['diagnostics'].items()}
        analysis.append(item)
    Path('docs/top-five-analysis.json').write_text(json.dumps(analysis, indent=2) + '\n')
    evidence = dict(baselineCommit='f159455b5dadf35891871fd2e0470d033e4285fb',
                    candidate=pool, bundle=dict(name=args.bundle.name,
                    sha256=hashlib.sha256(args.bundle.read_bytes()).hexdigest(), files=sorted(actual)),
                    limitations=['Local opponents, not private top-team bot implementations.',
                                 'Development maps and fixtures informed candidate selection.',
                                 'Replays show opponent behaviour, not opponent source code.',
                                 'Repeated deterministic fixtures are not independent samples.'])
    Path('docs/v16-results.json').write_text(json.dumps(evidence, indent=2) + '\n')
    lines = ['# Quantum Altar v16', '',
             'Based on the current repository at `f159455`, not the earlier v15 baseline.', '',
             '## Supplied top-team matches', '',
             'The five supplied match groups contain 25 games: 2 wins and 23 losses.',
             'Match-level data and public match IDs are in `top-five-analysis.json`.', '',
             '| Opponent | Our wins | Games |', '| --- | ---: | ---: |']
    names = sorted({r['opponent'] for r in analysis})
    for name in names:
        games = [r for r in analysis if r['opponent'] == name]
        lines.append(f"| {name} | {sum(r['score'][0] > r['score'][1] for r in games)} | {len(games)} |")
    lines += ['', '## What the supplied replays establish', '',
              '- Ambush: our team produced zero gems, moves and attacks. Repeated budget aborts prevented economic actions. This is a scheduling failure, not evidence that a different champion alone fixes the map.',
              '- Rows and Expanse: some losses had zero deaths. Farm routing, purchase timing and clear speed matter even without combat.',
              '- Eight: our team suffered roughly 19–29 deaths in the supplied losses, against 1–2 for the opponents. The farming improvements do not solve this combat deficit; this release preserves the existing policy there.',
              '- Opponent inventories show both damage-reduction builds and health-first Jungle plus Monster farming builds. They support testing these options, not a claim that every leading team uses one recipe.',
              '- Local Stampede traces exposed a separate siege/capture deadlock after monsters died. The farming variant fixes it, but its draft still lost one side; Stampede therefore keeps the incumbent in this release.',
              '- Idle counters also include spell and capture turns. They are not automatically wasted turns.', '']
    lines += ['', '## Changes', '',
              'The release selects policies from static public map geometry. The farming policy is enabled only on Ambush, Expanse, Fragment, Monolith and Rows. Packs uses a separately tested pack-clearing variant. Other layouts retain the incumbent policy. The following changes describe the farming policy; they are not enabled globally.', '',
              '- Reserve fuel for movement and execute chosen farm routes for a bounded period.',
              '- Capture an already cleared objective before rescoring the entire map.',
              '- Move into an unseen cleared camp instead of remaining on its geometric siege ring.',
              '- Exclude optional skipped monoliths from the ordinary farming build classification.',
              '- Compare area and single-target damage with overkill capped; centre Varg splash on packs.',
              '- Compare combat spell damage and interrupts, and local fighting strength before chasing.',
              '- Prioritise deposits from carriers already at the altar, including winning bags.',
              '- Use team-size-aware farming drafts, health/monster emblems, and Ren retaliation scaling.', '',
              '## Final local validation', '',
              f"{pool['wins']}/{pool['games']} wins against the frozen current repository bot, using cambc 2.2.1, engine 0.0.2, release mode, default fuel and complete matches.", '',
              '| Map | Our side | Our gems | Baseline gems | Result |', '| --- | --- | ---: | ---: | --- |']
    for r in pool['results']:
        lines.append(f"| {r['map']} | {'AB'[r['side']]} | {r['score'][0]} | {r['score'][1]} | {'Win' if r['win'] else 'Loss'} |")
    faults = sum(r['errors'] for r in pool['results'])
    suspended = [r['map'] + ' ' + 'AB'[r['side']] for r in pool['results'] if r['suspensions']]
    lines += ['', f'Logged exceptions: {faults}. Fixtures reporting fuel suspension: {len(suspended)}.',
              ', '.join(suspended) if suspended else 'No fuel suspensions reported by the bot diagnostics.', '',
              'The 16 main tests and 13 league tests pass. The older exchange-helper tests do not imply that a tactical search is integrated into live play.', '',
              '## Limits', '',
              'These results establish performance against the frozen local baseline. Fixtures using the incumbent fallback are near-mirror games, not evidence of strategic improvement. Map selection was informed by these development fixtures and can overfit. A globally enabled candidate won only 15/34 and was rejected. These results do not establish a new top-five win rate or an Elo prediction. The private top-team binaries were not available for responsive local rematches. All development maps informed iteration.', '',
              'The five match archives were analysed as data. No bot instructions were taken from them. The policy is fixed during ladder games; there is no neural network training online.', '',
              '## Upload', '', f'Use `{args.bundle.name}`. It contains only the exact tested `src/` Python files.',
              f"SHA-256: `{evidence['bundle']['sha256']}`.", '',
              'The previous `quantum-altar.zip` is retained as a historical artifact; it is not this release.', '']
    Path('docs/v16-strategy.md').write_text('\n'.join(lines))
    print(json.dumps(dict(wins=pool['wins'], games=pool['games'], exceptions=faults,
                         suspensionFixtures=suspended, bundle=evidence['bundle']), indent=2))


if __name__ == '__main__':
    main()
