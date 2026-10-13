"""Aggressive combat helpers shared verbatim by every sparring bot.

Every action is guarded by the documented preconditions (visibility, range,
readiness, walk exclusivity, landing legality) so engine errors never reach the
turn loop. Counters are printed by main.py as a compact usage summary.
"""
import cambc
from cambc import game_map

from bot import attack_if_in_range, blocked_tiles, distance, tiles_around

Team = cambc.Team

COUNTS = {"cc": 0, "damage": 0, "reset": 0, "dash": 0, "shield": 0, "lock": 0, "ward": 0,
          "engage": 0, "pursue": 0, "contest": 0, "stolen_gems": 0, "min_fuel_left": 10**9}
TURN = {"start": None, "exclusive": False}


def begin_turn():
    me = cambc.me()
    TURN["start"] = me.position() if me.is_alive() else None
    TURN["exclusive"] = False


def end_turn_bookkeeping():
    COUNTS["min_fuel_left"] = min(COUNTS["min_fuel_left"], cambc.fuel_remaining())


def moved():
    return TURN["start"] is not None and cambc.me().position() != TURN["start"]


def summary(tag):
    me = cambc.me()
    parts = " ".join(f"{key}={value}" for key, value in COUNTS.items())
    return f"[{tag}] round={cambc.round_number()} champ={me.champion_name()} {parts}"


def describe_kit():
    me = cambc.me()
    kinds = []
    for ability in me.abilities():
        info = ability.info()
        if info is None:
            kinds.append("none")
            continue
        kinds.append(f"{type(info).__name__}(range={getattr(info, 'range', '-')},"
                     f"excl={info.exclusive_with_movement},"
                     f"enemies={ability.can_target_enemies()},ground={ability.can_target_ground()})")
    return f"kit {me.champion_name()}: " + "; ".join(kinds)


def stun_immune(unit):
    return unit.passive() == cambc.PassiveType.STUN_IMMUNITY


def in_enemy_spawn(position):
    return game_map.spawn_region(Team.ENEMY).is_set(position)


def target_value(enemy):
    return (enemy.gem_count() * 3 + (enemy.max_health() - enemy.health()) / 20
            + (400 if enemy.is_submitting_gems() else 0))


def cast_offensive(target, want_stun=False):
    """Use the best ready damage/CC spell that can legally hit target now."""
    me = cambc.me()
    if not me.can_cast() or not target.is_visible() or not target.is_alive():
        return False
    gap = distance(me.position(), target.position())
    immune = stun_immune(target)
    stunned = target.buffs().has_stun()
    best, best_score = None, 0.0
    for ability in me.abilities():
        if not (ability.is_cc() or ability.is_damage() or ability.is_aoe_damage()):
            continue
        if not ability.is_ready():
            continue
        info = ability.info()
        if gap > int(info.range):
            continue
        if info.exclusive_with_movement and moved():
            continue
        if not (ability.can_target_enemies() or ability.can_target_ground()):
            continue
        score = info.modifier * me.focus()
        if ability.is_cc() and not immune and not stunned:
            score += 150 + (1000 if want_stun else 0)
        if score > best_score:
            best, best_score = ability, score
    if best is None:
        return False
    info = best.info()
    used = best.use(target) if best.can_target_enemies() else best.use(target.position())
    if used:
        COUNTS["cc" if best.is_cc() else "damage"] += 1
        if info.exclusive_with_movement:
            TURN["exclusive"] = True
    return used


def shield_self():
    """Varg-style shield when hurt or outnumbered; otherwise keep the cast for a reset."""
    me = cambc.me()
    if not me.can_cast():
        return False
    origin = me.position()
    close = sum(1 for e in cambc.vision.champions(Team.ENEMY) if distance(origin, e.position()) <= 4)
    if close == 0 or (me.health() >= me.max_health() * 0.75 and close < 2):
        return False
    for ability in me.abilities():
        if ability.is_shield() and ability.is_ready() and ability.can_target_self():
            if ability.info().exclusive_with_movement and moved():
                continue
            if ability.use(me):
                COUNTS["shield"] += 1
                if ability.info().exclusive_with_movement:
                    TURN["exclusive"] = True
                return True
    return False


def strike(target):
    """Basic attack (plus attack reset) if target is already in range."""
    me = cambc.me()
    ready = [a for a in me.abilities() if a.is_attack_reset() and a.is_ready()]
    if not attack_if_in_range(target):
        return False
    if ready and not ready[0].is_ready():
        COUNTS["reset"] += 1
    return True


def chase_move(goal, reach, danger, allow_dash=True):
    """Walk (or safely dash) toward tiles within reach of goal."""
    me = cambc.me()
    if not me.can_move() or TURN["exclusive"]:
        return False
    origin = me.position()
    blocked = blocked_tiles()
    goals = tiles_around(goal, reach) & ~blocked & ~game_map.spawn_region(Team.ENEMY)
    if goals.is_empty() or goals.is_set(origin):
        return False
    field = cambc.DistanceField()
    field.compute_to(blocked & ~goals, goals, tiles_around(origin, 0), cambc.Bitboard())
    here = field.get(origin)
    healthy = me.health() > me.max_health() * 0.5
    if allow_dash and healthy and here > 1:
        for ability in me.abilities():
            if not (ability.is_dash() and ability.is_ready()):
                continue
            transit = blocked & ~game_map.holes()
            landings = transit.reachable_tiles(origin, int(ability.info().range)) & ~blocked
            landings &= ~game_map.spawn_region(Team.ENEMY)
            safe = [tile for tile in landings.positions()
                    if danger(tile) < me.health() * 0.6 and field.get(tile) + 1 < here]
            if safe:
                landing = min(safe, key=field.get)
                if ability.use(landing):
                    COUNTS["dash"] += 1
                    if ability.info().exclusive_with_movement:
                        TURN["exclusive"] = True
                        return True
                    origin = me.position()
                    blocked = blocked_tiles()
            break
    if not me.can_move() or TURN["exclusive"]:
        return True
    reachable = blocked.reachable_tiles(origin, me.base_stats().base_move_speed)
    step = min([origin, *reachable.positions()], key=field.get)
    if step != origin and field.get(step) < field.get(origin):
        return me.move_absolute(step)
    return False


def engage(target, danger, chase=True, allow_dash=True):
    """Spell -> basic attack/reset -> close distance -> follow-up."""
    me = cambc.me()
    if not target.is_visible() or not target.is_alive():
        return False
    COUNTS["engage"] += 1
    want_stun = target.is_submitting_gems() or target.gem_count() >= 20
    acted = cast_offensive(target, want_stun) or shield_self()
    if target.is_visible() and target.is_alive():
        acted = strike(target) or acted
    if chase and target.is_visible() and target.is_alive() and not in_enemy_spawn(target.position()):
        reach = max(1, me.attack_range()) if me.can_attack() else 1
        if distance(me.position(), target.position()) > reach:
            acted = chase_move(target.position(), reach, danger, allow_dash) or acted
            if target.is_visible() and target.is_alive():
                cast_offensive(target, want_stun)
                strike(target)
    return acted


def opportunistic(enemies, danger, healthy):
    """Hit any enemy already in range, or finish a nearly dead one close by."""
    me = cambc.me()
    origin = me.position()
    for enemy in sorted(enemies, key=lambda e: e.health()):
        gap = distance(origin, enemy.position())
        if gap <= me.attack_range() or (healthy and enemy.health() < enemy.max_health() * 0.3
                                        and gap <= 4 and not in_enemy_spawn(enemy.position())):
            engage(enemy, danger, chase=gap > me.attack_range())
            return True
    return False


_FIELDS = {}


def spawn_distance(team):
    """Static walking distance from a team's spawn region (walls/holes only)."""
    field = _FIELDS.get(team)
    if field is None:
        field = cambc.DistanceField()
        field.compute(game_map.walls() | game_map.holes(), game_map.spawn_region(team), cambc.Bitboard())
        _FIELDS[team] = field
    return field


def warm_up():
    """Build lazy caches during the construction turn, never mid-decision.

    A decision turn that runs out of fuel resumes next round with stale unit
    handles; keeping first-use costs out of play turns avoids that.
    """
    spawn_distance(Team.ALLY)
    spawn_distance(Team.ENEMY)
    game_map.camp_groups()
    _ = cambc.constants.MAX_ROUNDS
    print(describe_kit(), flush=True)


FUEL_FLOOR = 900000


def low_fuel():
    return cambc.fuel_remaining() < FUEL_FLOOR


def enemy_side(tile):
    return spawn_distance(Team.ENEMY).get(tile) < spawn_distance(Team.ALLY).get(tile)


def place_lock(altar):
    """Drop an altar lock on a visible, unlocked altar within placement range."""
    me = cambc.me()
    lock = me.consumables()[cambc.ConsumableType.ALTAR_LOCK]
    if (lock.count() and distance(me.position(), altar) <= 2
            and cambc.vision.visible_tiles().is_set(altar)
            and not cambc.vision.has_altar_lock(altar)
            and not me.restrictions() & cambc.BuffRestrictions.CONSUMABLE
            # A fresh lock cancels any tribute at the altar, including our own.
            and not any(ally.is_submitting_gems() and distance(ally.position(), altar) <= 1
                        for ally in cambc.vision.champions(Team.ALLY))):
        if lock.use(altar):
            COUNTS["lock"] += 1
            return True
    return False


def ward_toward(focus, keep_radius=4):
    """Place our single ward on a legal visible tile nearest focus."""
    me = cambc.me()
    if me.ward_cooldown() or me.restrictions() & cambc.BuffRestrictions.WARD:
        return False
    wards = me.ward_positions()
    if wards and distance(wards[0], focus) <= keep_radius:
        return False
    candidates = (me.ward_placement_tiles() & ~blocked_tiles() & cambc.vision.visible_tiles()
                  & ~cambc.vision.ward_tiles(Team.ALLY))
    candidates.set(me.position(), False)
    if candidates.is_empty():
        return False
    tile = min(candidates.positions(), key=lambda t: distance(t, focus))
    if wards and distance(tile, focus) >= distance(wards[0], focus):
        return False
    if me.place_ward(tile):
        COUNTS["ward"] += 1
        return True
    return False
