import cambc
from cambc import game_map


def play():
    chosen = cambc.draft.current_draft(cambc.Team.ALLY)
    D = cambc.ChampionDraft
    memory = bytes(cambc.DraftMemoryBuffer())
    if not chosen:
        # The first pick is guaranteed before map analysis uses the larger budget.
        cambc.draft.pick(D.MARCELLA)
        groups = [group for group in game_map.camp_groups()
                  if not any(camp.is_monolith() for camp in group)]
        total = sum(len(group) for group in groups)
        clustered = sum(len(group) for group in groups if len(group) > 1)
        safe = sum(len(group) for group in groups
                   if all(camp.base_stats().base_strength <= 20 for camp in group))
        sparse_safe = clustered * 4 < max(1, total) and safe * 2 >= total
        third = D.VENDETTA if sparse_safe else D.VARG
        fourth = D.VARG if sparse_safe else D.VENDETTA
        # Versioned shared draft scratchpad: roster, clustered percentage, safe %.
        cambc.DraftMemoryBuffer().submit(bytes((3, D.MARCELLA, D.TAVI, third,
                                               fourth, D.RYTH,
                                               clustered * 100 // max(1, total),
                                               safe * 100 // max(1, total))))
        return
    order = memory[1:6] if memory and memory[0] == 3 else (D.MARCELLA, D.TAVI, D.VARG, D.VENDETTA, D.RYTH)
    cambc.draft.pick(next(pick for pick in order if pick not in chosen))
