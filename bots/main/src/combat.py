"""Small, pessimistic two-round exchanges; no SDK calls or hidden-state queries.

Fighters are snapshots. Each spell is (kind, cooldown, range, damage, stun,
excludes_walk). We bound enemy movement by Chebyshev distance, deliberately
ignoring obstacles: a wall must never make a carrier overconfident.
"""


def burst(fighter, gap, turn, used=-1, forced=-2, moved=False):
    """Best legal move/basic/one-cast sequence, or a specified cast (-1 = none).

    Return damage, stun, approach distance and used spell slot. A ranged walk
    consumes its basic unless reset; dash and damage cannot share a cast.
    """
    strength, reach, speed = fighter['strength'], fighter['range'], fighter['speed']
    melee = reach == 1
    walk = 0 if moved or forced != -2 else min(speed, max(0, gap - reach))
    basic = strength if gap <= reach and (not moved or melee) else 0
    advancing = strength if gap - walk <= reach and melee else 0
    best = (max(basic, advancing), False, walk, -1)
    if forced != -2:
        best = (basic, False, 0, -1)
    for slot, (kind, cooldown, radius, damage, stun, exclusive) in enumerate(fighter['spells']):
        if slot == used or cooldown > turn or (forced != -2 and slot != forced):
            continue
        if moved and exclusive:
            continue
        advance = 0
        hit, cc = basic, False
        if kind == 'reset':
            advance = walk
            hit = (max(basic, advancing) + strength) if gap - walk <= reach else 0
            cc = stun and hit > 0
        elif kind == 'dash':
            advance = min(radius + (speed if melee else 0), max(0, gap - reach))
            hit = strength if gap - advance <= reach else 0
        elif kind == 'damage':
            advance = 0 if exclusive or moved else walk
            if gap - advance <= radius:
                hit += damage
                cc = stun
        elif kind == 'shield':
            continue
        if (hit > best[0] or (hit == best[0] and cc and not best[1])
                or (hit == best[0] == 0 and advance > best[2])):
            best = (hit, cc, advance, slot)
    return best


def exchange(ours, enemies, gaps, target, cast=-1, moved=False):
    """Evaluate our committed action and best next turn against two replies.

    Enemies may move+attack or cast once on each reply, never reuse a cooldown.
    Current stuns deny only an uncompleted enemy slot. A newly applied stun gets
    credit for one reply only, and never against Marcella. All other enemies
    attack independently: do not evaluate a duel while ignoring nearby helpers.
    """
    first, stun, _, used = burst(ours, gaps[target], 0, forced=cast, moved=moved)
    shield = 0
    if cast >= 0 and ours['spells'][cast][0] == 'shield':
        shield = ours['spells'][cast][3]
        used = cast
    incoming, replies = 0, []
    interrupted = False
    for index, enemy in enumerate(enemies):
        gap = gaps[index]
        health = enemy['health'] - (first if index == target else 0)
        if health <= 0:
            replies.append(None)
            continue
        denied = enemy['stunned'] or (index == target and stun and not enemy['immune'])
        damage0, cc0, advance0, spell0 = burst(enemy, gap, 0)
        if denied:
            damage0, cc0, advance0, spell0 = 0, False, 0, -1
        gap = max(1, gap - advance0)
        incoming += damage0
        # An enemy may act before our next slot, so assume their stun denies our
        # second action rather than assuming all of our team acts first.
        interrupted |= cc0 and not ours['immune']
        replies.append((gap, spell0))
    second = 0
    if not interrupted and replies[target] is not None:
        second, _, _, _ = burst(ours, replies[target][0], 1, used=used)
    for index, reply in enumerate(replies):
        if reply is None or (index == target and first + second >= enemies[index]['health']):
            continue
        damage1, _, _, _ = burst(enemies[index], reply[0], 1, used=reply[1])
        incoming += damage1
    return first + second, max(0, incoming - shield), first
