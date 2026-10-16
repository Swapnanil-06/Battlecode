"""Useful damage to a visible camp pack; overkill is not counted as progress."""


def pack_damage(targets, centre, damage, radius):
    x, y = centre
    return sum(min(health, damage) for tx, ty, health in targets
               if max(abs(tx - x), abs(ty - y)) <= radius)
