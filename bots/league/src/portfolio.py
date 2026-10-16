"""Offline validated policies, selected from public static map geometry."""

INCUMBENT = 4
FARMING = 3
PACKS = 5

# width, height, camp groups, camps. Unknown layouts use the existing bot.
FARM_LAYOUTS = frozenset((
    (100, 100, 12, 38),  # Ambush
    (80, 80, 24, 52),    # Expanse
    (30, 30, 6, 12),     # Fragment
    (50, 50, 22, 44),    # Monolith
    (50, 50, 9, 28),     # Rows: the central group is shared.
))


def select_mode(width, height, groups):
    layout = (width, height, len(groups), sum(len(g) for g in groups))
    if layout in FARM_LAYOUTS:
        return FARMING
    if layout == (31, 31, 8, 20):
        return PACKS
    return INCUMBENT


def strategy_modules(mode):
    if mode == INCUMBENT:
        from variants.incumbent.bot import Bot
        from variants.incumbent.planner.ledger import LEDGER
    elif mode == PACKS:
        from variants.packs.bot import Bot
        from variants.packs.planner.ledger import LEDGER
    else:
        from bot import Bot
        from planner.ledger import LEDGER
    return Bot, LEDGER
