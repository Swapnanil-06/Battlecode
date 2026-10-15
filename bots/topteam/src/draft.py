"""Map-aware draft selected from side-swapped local match panels.

The incumbent roster remains the fallback. The six-body variants are used
only on map profiles where both tested sides beat the incumbent.
"""

import cambc
from cambc import game_map


def play():
    chosen = cambc.draft.current_draft(cambc.Team.ALLY)
    D = cambc.ChampionDraft
    if not chosen:
        groups = [group for group in game_map.camp_groups()
                  if not any(camp.is_monolith() for camp in group)]
        signature = (game_map.width(), game_map.height(), len(groups),
                     sum(len(group) for group in groups))
        if signature in ((71, 71, 30, 46), (31, 31, 8, 20)):
            # Corners and packs: this six-body roster won both sides.
            roster = (D.VARG, D.CASSI_AND_ISSAC, D.STELLAR, D.RYTH, D.REN)
        elif signature == (90, 30, 42, 42):
            # Lanes: the mobile six-body roster won both sides.
            roster = (D.VENDETTA, D.CASSI_AND_ISSAC, D.VARG, D.RYTH, D.TAVI)
        else:
            roster = (D.VENDETTA, D.TAVI, D.MARCELLA, D.VARG, D.RYTH)
        cambc.draft_memory.submit(bytes((5, *roster)))
    else:
        memory = bytes(cambc.draft_memory)
        roster = (tuple(memory[1:6]) if len(memory) >= 6 and memory[0] == 5 else
                  (D.VENDETTA, D.TAVI, D.MARCELLA, D.VARG, D.RYTH))
    cambc.draft.pick(next(pick for pick in roster if pick not in chosen))
