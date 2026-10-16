import cambc
from cambc import game_map
import policy

_order = None


def select_roster(all_groups):
    if not getattr(policy, 'ADAPTIVE_DRAFT', False):
        return tuple(policy.ROSTER)
    gem_groups = [g for g in all_groups if g.gem_value() > 0]
    if gem_groups and all(any(c.is_monolith() for c in g) for g in gem_groups):
        return tuple(getattr(policy, 'ROSTER_MONO', (4, 10, 5, 3, 8)))
    non_mono = [g for g in gem_groups if not any(c.is_monolith() for c in g)]
    has_boss8 = any(len(g) >= 8 for g in non_mono)
    if has_boss8 or len(all_groups) >= 35:
        return (9, 8, 4, 3, 0)
    wolf3_only = bool(non_mono) and all(
        sum(1 for c in g if c.is_wolf()) >= 3 and not any(c.is_elk() for c in g)
        for g in non_mono
    )
    harmless_gem = sum(
        1 for g in non_mono if all(c.base_stats().base_strength == 0 for c in g)
    )
    if wolf3_only or harmless_gem >= 6:
        return tuple(getattr(policy, 'ROSTER_PVE', (3, 4, 9, 10, 8)))
    return tuple(policy.ROSTER)


def play():
    global _order
    chosen = cambc.draft.current_draft(cambc.Team.ALLY)
    if not chosen:
        all_groups = game_map.camp_groups()
        groups = [group for group in all_groups
                  if not any(camp.is_monolith() for camp in group)]
        total = sum(len(group) for group in groups)
        clustered = sum(len(group) for group in groups if len(group) > 1)
        safe = sum(len(group) for group in groups
                   if all(camp.base_stats().base_strength <= 20 for camp in group))
        _order = select_roster(all_groups)
        cambc.draft_memory.submit(bytes((3, *_order,
                                         clustered * 100 // max(1, total),
                                         safe * 100 // max(1, total))))
        cambc.draft.pick(_order[0])
        return
    if _order is None:
        memory = bytes(cambc.draft_memory)
        _order = tuple(memory[1:6]) if memory and memory[0] == 3 else tuple(policy.ROSTER)
    cambc.draft.pick(next(pick for pick in _order if pick not in chosen))
