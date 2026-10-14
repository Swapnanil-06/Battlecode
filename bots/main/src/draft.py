import cambc
from cambc import game_map


def play():
    chosen = cambc.draft.current_draft(cambc.Team.ALLY)
    D = cambc.ChampionDraft
    if not chosen:
        groups = [group for group in game_map.camp_groups()
                  if not any(camp.is_monolith() for camp in group)]
        total = sum(len(group) for group in groups)
        clustered = sum(len(group) for group in groups if len(group) > 1)
        safe = sum(len(group) for group in groups
                   if all(camp.base_stats().base_strength <= 20 for camp in group))
        # Candidate B meta roster: Vendetta, Tavi, Marcella, Varg, Ryth
        roster = (D.VENDETTA, D.TAVI, D.MARCELLA, D.VARG, D.RYTH)
        # Versioned shared draft scratchpad: roster, clustered percentage, safe %.
        cambc.draft_memory.submit(bytes((3, *roster,
                                         clustered * 100 // max(1, total),
                                         safe * 100 // max(1, total))))
        cambc.draft.pick(roster[0])
        return
    memory = bytes(cambc.draft_memory)
    order = memory[1:6] if memory and memory[0] == 3 else (D.VENDETTA, D.TAVI, D.MARCELLA, D.VARG, D.RYTH)
    cambc.draft.pick(next(pick for pick in order if pick not in chosen))
