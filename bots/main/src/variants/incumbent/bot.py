"""Champion decisions. main.py dispatches here after the draft."""
from math import ceil
from operator import itemgetter
from .randomness import below
from . import policy
from .coordination import publish, claimed_jobs, job_claim_counts

import cambc
from cambc import game_map
from .planner.ledger import (LEDGER, COST_ATTACK, COST_BANK, COST_CANDIDATE, COST_DASH,
                            COST_FIELD, COST_MOVE, COST_RETREAT, COST_SCAN, COST_SETUP,
                            COST_WALK, COST_WARD, SOFT_FLOOR)

Team, Item = cambc.Team, cambc.ItemType
_first = itemgetter(0)
WARM_FLOOR = 1_500_000  # warming outside a decision leaves at least this much
# Route searches start bounded to this many steps and widen only when a goal is past it.
NEAR_FIELD = 16
# Turns to break an enemy altar lock (three basic attacks; resets can shorten it).
LOCK_BREAK_TURNS = 3
# Route pricing: a respawn wait beyond the walk counts WAIT_COST turns per turn idle, and
# gold (spent on Strength shards at spawn) is worth GOLD_WORTH gem-units per coin.
WAIT_COST = 1.5
GOLD_WORTH = 0.3

# Board queries are memoized until our next action. Nothing else moves during our
# turn, so only our own actions (move, attack, cast, ward, lock) can change them.
_memo = {}
_static = {}


def acted():
    _memo.clear()


def static_blocked():
    blocked = _static.get('blocked')
    if blocked is None:
        blocked = _static['blocked'] = (game_map.walls() | game_map.holes() | game_map.altars()
                                        | game_map.spawn_region(Team.ENEMY))
    return blocked


def my_abilities():
    """(ability, kind, range, info) per slot; kind and range are fixed per champion."""
    slots = _static.get('abilities')
    if slots is None:
        slots = []
        for ability in cambc.me().abilities():
            info = ability.info()
            kind = None
            if info is not None:
                for name, test in (('reset', ability.is_attack_reset), ('dash', ability.is_dash),
                                   ('damage', ability.is_damage), ('aoe', ability.is_aoe_damage),
                                   ('cc', ability.is_cc), ('shield', ability.is_shield),
                                   ('heal', ability.is_heal)):
                    if test():
                        kind = name
                        break
            slots.append((ability, kind, int(getattr(info, 'range', 0) or 0), info))
        slots = _static['abilities'] = tuple(slots)
    return slots


def home_side(x, y):
    """True when (x, y) is nearer our spawn than the enemy's (Chebyshev to region centres)."""
    centres = _static.get('spawn_centres')
    if centres is None:
        centres = []
        for team in (Team.ALLY, Team.ENEMY):
            tiles = game_map.spawn_region(team).positions()
            centres.append((sum(t.x for t in tiles) / len(tiles), sum(t.y for t in tiles) / len(tiles)))
        centres = _static['spawn_centres'] = tuple(centres)
    (ax, ay), (ex, ey) = centres
    return max(abs(x - ax), abs(y - ay)) < max(abs(x - ex), abs(y - ey))


def ally_spawn_xy():
    """First four ally spawn tiles as (x, y): the walk-to-flee goal for non-carriers."""
    tiles = _static.get('spawn4')
    if tiles is None:
        tiles = _static['spawn4'] = tuple((t.x, t.y) for t in game_map.spawn_region(Team.ALLY).positions()[:4])
    return tiles


def ready(ability, me):
    # Ability.is_ready() for our own non-empty slot, without its per-call Champion rebuild.
    return ability.cooldown() == 0 and me.can_cast()


def route_field(blocked, origin, radius):
    """Walking distances from origin; with a radius, exact up to it and unreached beyond."""
    field, reached = cambc.DistanceField(), cambc.Bitboard()
    if radius is None:
        field.compute(blocked, tiles_around(origin, 0), reached)
    else:
        field.compute(blocked, tiles_around(origin, 0), reached, radius)
    return field, reached


def box_distance(x, y, box):
    """Chebyshev distance from (x, y) to the nearest tile of an inclusive bounding box."""
    min_x, min_y, max_x, max_y = box
    return max(min_x - x, x - max_x, min_y - y, y - max_y, 0)


def distance(a, b):
    if a is None or b is None:
        return 999999
    return max(abs(a.x - b.x), abs(a.y - b.y))


def safe_is_visible(unit):
    if unit is None:
        return False
    try:
        key = ('visible', type(unit), int(unit))
        if key not in _memo:
            _memo[key] = unit.is_visible()
        return _memo[key]
    except Exception:
        return False


def safe_position(unit):
    if unit is None:
        return None
    try:
        key = ('position', type(unit), int(unit))
        if key not in _memo:
            _memo[key] = unit.position() if safe_is_visible(unit) else None
        return _memo[key]
    except Exception:
        pass
    return None


def safe_health(unit):
    if unit is None:
        return 0
    try:
        if safe_is_visible(unit):
            return unit.health()
    except Exception:
        pass
    return 0


def safe_strength(unit):
    if unit is None:
        return 0
    try:
        if safe_is_visible(unit):
            return unit.strength()
    except Exception:
        pass
    return 0


def safe_attack_range(unit):
    if unit is None:
        return 1
    try:
        if safe_is_visible(unit):
            return unit.attack_range()
    except Exception:
        pass
    return 1


def safe_gem_count(unit):
    if unit is None:
        return 0
    try:
        if safe_is_visible(unit):
            return unit.gem_count()
    except Exception:
        pass
    return 0


def safe_is_submitting_gems(unit):
    if unit is None:
        return False
    try:
        if safe_is_visible(unit):
            return unit.is_submitting_gems()
    except Exception:
        pass
    return False


def safe_is_recalling(unit):
    if unit is None:
        return False
    try:
        if safe_is_visible(unit):
            return unit.is_recalling()
    except Exception:
        pass
    return False


def safe_is_alive(unit):
    if unit is None:
        return False
    try:
        return unit.is_alive()
    except Exception:
        return False


def safe_max_health(unit):
    if unit is None:
        return 1
    try:
        if safe_is_visible(unit):
            return unit.max_health()
    except Exception:
        pass
    return 1


def safe_visible_enemies():
    found = _memo.get('enemies')
    if found is None:
        found = _memo['enemies'] = _visible_enemies()
    return found


def _visible_enemies():
    try:
        champs = cambc.vision.champions(Team.ENEMY)
    except Exception:
        try:
            champs = [e for e in cambc.champions(Team.ENEMY) if safe_is_visible(e)]
        except Exception:
            return []
    res = []
    for e in champs:
        try:
            if safe_is_visible(e) and safe_is_alive(e):
                res.append(e)
        except Exception:
            pass
    return res


def safe_visible_allies():
    found = _memo.get('allies')
    if found is None:
        found = _memo['allies'] = _visible_allies()
    return found


def _visible_allies():
    try:
        champs = cambc.vision.champions(Team.ALLY)
    except Exception:
        try:
            champs = [a for a in cambc.champions(Team.ALLY) if safe_is_visible(a)]
        except Exception:
            return []
    res = []
    for a in champs:
        try:
            if safe_is_visible(a) and safe_is_alive(a):
                res.append(a)
        except Exception:
            pass
    return res


def safe_camps():
    c_list = []
    try:
        c_tiles = cambc.vision.camp_tiles()
        for pos in c_tiles.positions():
            try:
                if cambc.vision.has_camp(pos):
                    c = cambc.vision.camp_at(pos)
                    if safe_is_visible(c):
                        c_list.append(c)
            except Exception:
                pass
    except Exception:
        pass
    return c_list


def tiles_around(position, radius):
    tiles = cambc.Bitboard()
    if position is None or radius < 0:
        return tiles
    try:
        w, h = game_map.width(), game_map.height()
        if 0 <= position.x < w and 0 <= position.y < h:
            tiles.draw_chebyshev(position, radius)
    except Exception:
        pass
    return tiles


def blocked_tiles():
    """Shared and memoized: callers must not mutate the returned bitboard."""
    blocked = _memo.get('blocked')
    if blocked is None:
        blocked = _memo['blocked'] = _blocked_tiles()
    return blocked


def _blocked_tiles():
    # Combine terrain and visible occupants using native bitboard operations.
    blocked = (static_blocked() | cambc.vision.champion_tiles()
               | cambc.vision.camp_tiles() | cambc.vision.teleport_tiles()
               | cambc.vision.ward_tiles())
    me = cambc.me()
    try:
        if me.is_alive():
            pos = me.position()
            w, h = game_map.width(), game_map.height()
            if 0 <= pos.x < w and 0 <= pos.y < h:
                blocked.set(pos, False)
    except Exception:
        pass
    return blocked


def safe_move(tile):
    me = cambc.me()
    if not me.is_alive() or not me.can_move() or tile is None:
        return False
    w, h = game_map.width(), game_map.height()
    if not (0 <= tile.x < w and 0 <= tile.y < h):
        return False
    try:
        return me.move_absolute(tile)
    except Exception:
        return False
    finally:
        acted()


def move_towards_closest(goals, avoid=None):
    me = cambc.me()
    if not me.is_alive() or not me.can_move():
        return False
    origin = safe_position(me)
    if origin is None:
        return False
    w, h = game_map.width(), game_map.height()
    if not (0 <= origin.x < w and 0 <= origin.y < h):
        return False
    goals = goals.copy()  # Map/group masks are cached; never trim their source tiles.
    if goals.is_set(origin):
        return False
    if not LEDGER.afford(COST_MOVE):
        return False

    # Only free goals or occupied camp tiles can seed the field.
    blocked = blocked_tiles()
    if avoid is not None:
        blocked = blocked | avoid
        blocked.set(origin, False)
    goals &= ~blocked | cambc.vision.camp_tiles()
    if goals.is_empty():
        return False

    # Expand from the goals until our current tile is reached.
    field = cambc.DistanceField()
    try:
        field.compute_to(blocked & ~goals, goals, tiles_around(origin, 0), cambc.Bitboard())
    except Exception:
        return False

    did_dash = False
    # Dash legality differs from walking: holes can be crossed but not landed on.
    try:
        for ability, kind, _, info in my_abilities():
            if kind == 'dash' and ready(ability, me):
                transit = blocked & ~game_map.holes()
                landings = transit.reachable_tiles(origin, int(info.range)) & ~blocked
                choices = [origin, *landings.positions()]
                landing = min(choices, key=field.get)
                if field.get(landing) + 1 < field.get(origin):
                    try:
                        if ability.use(landing):
                            did_dash = True
                            if not policy.DASH_WALK:
                                return True
                            origin = me.position()
                    except Exception:
                        pass
                    finally:
                        acted()
    except Exception:
        pass

    # Choose a reachable step with a smaller distance to the goal.
    if not me.can_move():
        return did_dash
    try:
        reachable = blocked.reachable_tiles(origin, me.base_stats().base_move_speed)
        step = min([origin, *reachable.positions()], key=field.get)
        if step == origin or blocked.is_set(step):
            return did_dash
        return safe_move(step) or did_dash
    except Exception:
        return did_dash


def _reset_and_attack(me, target, still_valid):
    """After a basic attack, spend a ready attack reset on a second hit."""
    for ability, kind, _, _ in my_abilities():
        if kind == 'reset' and ready(ability, me):
            if not me.can_attack():
                used = ability.use()
                acted()
                if used and me.can_attack() and still_valid():
                    me.attack(target)
                    acted()
            break


def attack_if_in_range(target):
    me = cambc.me()
    if not me.is_alive() or not me.can_attack() or target is None:
        return False
    if not LEDGER.afford(COST_ATTACK):
        return False
    my_pos = safe_position(me)
    if my_pos is None:
        return False

    try:
        if isinstance(target, cambc.AltarLock):
            if not target.is_enemy() or target.hits_remaining() <= 0:
                return False
            t_pos = target.position()
            if distance(my_pos, t_pos) > me.attack_range():
                return False
            me.attack(target)
            acted()
            if me.can_cast() and target.hits_remaining() > 0:
                _reset_and_attack(me, target, lambda: target.hits_remaining() > 0)
            return True

        if isinstance(target, cambc.Camp):
            if not cambc.vision.camp_tiles().is_set(target.spawn_position()):
                return False
            t_pos = safe_position(target)
            if t_pos is None or distance(my_pos, t_pos) > me.attack_range():
                return False
            if not safe_is_visible(target) or safe_health(target) <= 0:
                return False
            me.attack(target)
            acted()
            alive = cambc.vision.camp_tiles().is_set(target.spawn_position()) and safe_is_visible(target)
            if me.can_cast() and alive and safe_health(target) > 0:
                _reset_and_attack(me, target, lambda: safe_is_visible(target) and safe_health(target) > 0)
            return True

        # Champion target
        t_pos = safe_position(target)
        if t_pos is None or distance(my_pos, t_pos) > me.attack_range():
            return False
        if not safe_is_alive(target) or safe_health(target) <= 0:
            return False
        me.attack(target)
        acted()
        if me.can_cast() and safe_is_visible(target) and safe_is_alive(target) and safe_health(target) > 0:
            def still_valid():
                if not (safe_is_visible(target) and safe_is_alive(target) and safe_health(target) > 0):
                    return False
                t_pos2 = safe_position(target)
                return bool(t_pos2) and distance(my_pos, t_pos2) <= me.attack_range()
            _reset_and_attack(me, target, still_valid)
        return True
    except Exception:
        return False


class Bot:
    def __init__(self):
        self.enemies = {}
        self.respawns = {}
        self.group = None
        self.groups = game_map.camp_groups()
        self.job_ids = {id(group): index + 1 for index, group in enumerate(self.groups)}
        handles = sorted(int(champ) for champ in cambc.champions(Team.ALLY))
        self.team_size = max(1, len(handles))
        self.claim_slot = handles.index(int(cambc.me()))
        self.claims_enabled = policy.JOB_LEASES and len(handles) <= 6 and len(self.groups) <= 63
        self.altars = game_map.altars().positions()
        self.altar_xy = tuple((altar.x, altar.y) for altar in self.altars)
        self.bank_altar = None
        self.locked_altars = {}
        self.turn_origin = None
        self.plan_count = 0
        self.min_fuel = 2500000
        self.suspended = 0
        self.camp_threats = {}
        self._camp_threats_stale = False
        self.camp_tiles = cambc.Bitboard()
        self.max_camp_range = 1000
        _ = cambc.constants.MAX_ROUNDS
        static_blocked()
        me = cambc.me()
        champ = me.champion_name()
        self.champ = champ
        self.is_duo = champ in (cambc.ChampionType.CASSI, cambc.ChampionType.ISSAC)
        shard = (Item.POWER_SHARD_OF_FOCUS if champ in (cambc.ChampionType.TAVI, cambc.ChampionType.CASSI)
                 else Item.POWER_SHARD_OF_STRENGTH)
        self.cheapest_buy = min(cambc.ConsumableType.ALTAR_LOCK.cost(), shard.cost())
        self.spell_reach = max([3] + [reach for _, kind, reach, _ in my_abilities()
                                      if kind in ('damage', 'cc', 'aoe')])
        self.has_reset = any(kind == 'reset' for _, kind, _, _ in my_abilities())
        self.has_cc = any(kind == 'cc' or (kind == 'aoe' and champ == cambc.ChampionType.RYTH)
                          for _, kind, _, _ in my_abilities())
        self.ginfo = {}
        self.gpartial = {}
        self.rings = {}
        self.handle_region = {}
        self.all_camp_spawns = None
        self.camp_ranges = []
        self.altar_field = None
        self.spawn_altar_dist = 15
        self.gstatic = None
        self.route_order = None
        self.cuts = 0
        self.siege_capable = any(kind in ('damage', 'aoe', 'cc') and reach > 3
                                 for _, kind, reach, _ in my_abilities())
        self.ranged_caster = me.attack_range() > 1 and self.siege_capable
        self.resource_mode = None
        self.monolith_only = None
        self.siege_goal_cache = {}

    def camp_damage_taken_mult(self, me):
        try:
            counts = me.item_count()
            mult = 1.0
            if (counts[Item.JUNGLE_EMBLEM_OF_STRENGTH]
                    or counts[Item.JUNGLE_EMBLEM_OF_FOCUS]
                    or counts[Item.JUNGLE_EMBLEM_OF_HEALTH]):
                mult *= 0.7
            if (counts[Item.DURABILITY_EMBLEM_OF_STRENGTH]
                    or counts[Item.DURABILITY_EMBLEM_OF_FOCUS]
                    or counts[Item.DURABILITY_EMBLEM_OF_HEALTH]):
                mult *= 0.9
            return mult
        except Exception:
            return 1.0

    def can_safe_recall(self, origin):
        me = cambc.me()
        if not me.is_alive() or me.is_recalling() or me.is_teleporting() or me.is_submitting_gems():
            return False
        if game_map.spawn_region(Team.ALLY).is_set(origin):
            return False
        for e in safe_visible_enemies():
            epos = safe_position(e)
            if epos and distance(origin, epos) <= safe_attack_range(e) + 4:
                return False
        return self.channel_damage(origin, 5) == 0

    def investment_map(self):
        if self.resource_mode is None:
            gem_groups = [self.group_info(g) for g in self.groups if g.gem_value()]
            total = sum(info[5] for info in gem_groups)
            difficult = sum(info[5] for info in gem_groups
                            if sum(c[2] for c in info[7]) >= 8000)
            self.resource_mode = bool(total and difficult >= total * 0.5)
            self.monolith_only = bool(total and all(any(c[4] for c in info[7]) for info in gem_groups))
        return self.resource_mode

    def raid(self, group):
        entries = self.group_info(group)[7]
        if any(c[4] for c in entries):
            return self.siege_capable and self.monolith_only and cambc.me().focus() >= 250
        return self.siege_capable and len(entries) >= 8

    def siege_farm(self, group):
        """Keep damage casters outside stationary monsters' retaliation range."""
        if not self.raid(group):
            return False
        info = self.group_info(group)
        visible = cambc.vision.visible_tiles()
        if not (info[4] & visible).is_empty():
            state = group.state()
            if not isinstance(state, game_map.CampGroupAlive):
                return False
        if not LEDGER.afford(COST_MOVE + 30_000 * len(info[7])):
            return True
        me = cambc.me()
        origin = me.position()
        camps = []
        danger, reach_tiles = cambc.Bitboard(), cambc.Bitboard()
        for camp, tile, hp, strength, _ in info[7]:
            if safe_is_visible(camp):
                hp = safe_health(camp)
            elif visible.is_set(tile) and not cambc.vision.camp_tiles().is_set(tile):
                hp = 0
            if hp <= 0:
                continue
            camps.append((camp, tile, hp))
            reach_tiles |= tiles_around(tile, 4)
            if strength:
                danger |= tiles_around(tile, camp.base_stats().base_attack_range)
        if not camps:
            return False
        goals = reach_tiles & ~danger & ~blocked_tiles()
        if any(entry[4] for entry in info[7]):
            quiet = self.siege_goal_cache.get(id(group))
            if quiet is None:
                quiet = reach_tiles & ~danger & ~static_blocked()
                for other in self.groups:
                    if other is not group:
                        for _, tile, _, _, _ in self.group_info(other)[7]:
                            quiet &= ~tiles_around(tile, 4)
                self.siege_goal_cache[id(group)] = quiet
            quiet = quiet & ~blocked_tiles()
            if not quiet.is_empty():
                goals = quiet
        if danger.is_set(origin):
            move_towards_closest(goals)
            return True
        if me.can_cast() and origin == self.turn_origin:
            best = None
            for ability, kind, reach, _ in my_abilities():
                if kind not in ('damage', 'aoe', 'cc') or reach <= 3 or not ready(ability, me):
                    continue
                damage = ability.damage_amount()
                if damage <= 0:
                    continue
                for camp, tile, hp in camps:
                    if not safe_is_visible(camp) or distance(origin, tile) > reach:
                        continue
                    value = (sum(min(damage, h) for _, pos, h in camps
                                 if distance(pos, tile) <= 1) if kind == 'aoe' else min(damage, hp))
                    if best is None or value > best[0]:
                        best = value, ability, camp, tile
            if best is not None:
                _, ability, camp, tile = best
                if ability.use(camp if ability.can_target_camps() else tile):
                    acted()
                    return True
        for camp, tile, _ in camps:
            if safe_is_visible(camp) and distance(origin, tile) <= me.attack_range():
                if attack_if_in_range(camp):
                    return True
        move_towards_closest(goals, avoid=danger)
        return True

    def warm(self, floor):
        """Build static per-group caches while fuel stays above floor; True when done."""
        if self.gstatic is not None:
            return True
        if self.altar_field is None:
            if cambc.fuel_remaining() < floor:
                return False
            field = cambc.DistanceField()
            field.compute(cambc.Bitboard(), game_map.altars(), cambc.Bitboard())
            self.altar_field = field
            sfield = self.spawn_field()
            self.spawn_altar_dist = min(
                (sfield.get(t) for ring in self.submit_rings() for t in ring.positions()),
                default=15,
            )
        for group in self.groups:
            if id(group) not in self.rings:
                if cambc.fuel_remaining() < floor:
                    return False
                info = self.group_info(group, floor)
                if info is None:
                    return False
                self.approach_ring(group, info[4])
        all_spawns = cambc.Bitboard()
        gstatic = []
        for index, group in enumerate(self.groups):
            info = self.group_info(group)
            all_spawns |= info[4]
            self.handle_region[info[0]] = info[4]
            gstatic.append((info[0], info[1], info[2], info[3], index, group))
        self.all_camp_spawns = all_spawns
        self.gstatic = gstatic
        self.max_camp_range = max(self.camp_ranges + [0])
        return True

    def unseen_camp_tiles(self, now, visible):
        if self.all_camp_spawns is None:
            return cambc.Bitboard()
        unseen = self.all_camp_spawns & ~visible
        for handle, until in self.respawns.items():
            if until > now:
                region = self.handle_region.get(handle)
                if region is not None:
                    unseen &= ~region
        return unseen

    def group_info(self, group, floor=None):
        """(handle, tier, first spawn x, first spawn y, spawn mask, gems, gold, camps,
        spawn bounding box (min x, min y, max x, max y), bank distance lower bound).

        Each camp entry is (camp, spawn tile, base health, base strength, is monolith).
        """
        info = self.ginfo.get(id(group))
        if info is None:
            partial = self.gpartial.setdefault(id(group), [[], False])
            camps, gem_cluster = partial
            done = len(camps)
            for index, camp in enumerate(group):
                if index < done:
                    continue
                if floor is not None and cambc.fuel_remaining() < floor:
                    return None
                stats = camp.base_stats()
                camps.append((camp, camp.spawn_position(), stats.base_health,
                              stats.base_strength, camp.is_monolith()))
                self.camp_ranges.append(stats.base_attack_range)
                gem_cluster = gem_cluster or camp.is_gem_cluster()
                partial[1] = gem_cluster
            gems = group.gem_value()
            first = camps[0][1]
            tier = 0 if (gem_cluster and home_side(first.x, first.y) and len(camps) <= 3) else (1 if gems > 0 else 2)
            xs = [entry[1].x for entry in camps]
            ys = [entry[1].y for entry in camps]
            box = (min(xs), min(ys), max(xs), max(ys))
            # Order damaging monsters first (Smith's rule: lowest health/strength first), 0-damage clusters last.
            camps.sort(key=lambda c: (0 if c[3] > 0 else 1, c[2] / max(1, c[3])))
            bank_lb = max(0, min(self.altar_gap(entry[1]) for entry in camps) - 1)
            info = self.ginfo[id(group)] = (int(group), tier, first.x, first.y, group.spawn_tiles(),
                                            gems, group.gold_value(), tuple(camps), box, bank_lb)
            del self.gpartial[id(group)]
        return info

    def approach_ring(self, group, region):
        ring = self.rings.get(id(group))
        if ring is None:
            ring = cambc.Bitboard()
            for tile in region.positions():
                ring |= tiles_around(tile, 1)
            self.rings[id(group)] = ring
        return ring

    def spawn_field(self):
        """Walking distance to our spawn region around static terrain; built once."""
        field = _static.get('spawn_field')
        if field is None:
            blocked = static_blocked()
            field = _static['spawn_field'] = cambc.DistanceField()
            field.compute(blocked, game_map.spawn_region(Team.ALLY) & ~blocked, cambc.Bitboard())
        return field

    def altar_gap(self, tile):
        """Chebyshev distance from tile to the nearest altar."""
        if self.altar_field is not None:
            return self.altar_field.get(tile)
        tx, ty = tile.x, tile.y
        return min(max(abs(tx - x), abs(ty - y)) for x, y in self.altar_xy)

    def submit_rings(self):
        """Per altar (in self.altars order), the tiles within submit range."""
        rings = _static.get('submit_rings')
        if rings is None:
            reach = cambc.constants.SUBMIT_GEMS_RANGE
            rings = _static['submit_rings'] = tuple(tiles_around(altar, reach) for altar in self.altars)
        return rings

    def farm_attack(self, camp):
        me = cambc.me()
        if not safe_is_visible(camp) or not cambc.vision.camp_tiles().is_set(camp.spawn_position()):
            return False
        c_pos = safe_position(camp)
        if c_pos is None:
            return False
        my_pos = me.position()
        gap = distance(my_pos, c_pos)
        if gap > self.spell_reach and gap > me.attack_range():
            return False
        if my_pos == self.turn_origin and me.can_cast():
            for ability, kind, reach, _ in my_abilities():
                if kind is None or not ready(ability, me):
                    continue
                if kind in ('damage', 'cc', 'aoe') and gap <= reach:
                    if ability.damage_amount() > me.strength() or gap > me.attack_range():
                        try:
                            ability.use(camp if ability.can_target_camps() else c_pos)
                            acted()
                            attack_if_in_range(camp)
                            return True
                        except Exception:
                            acted()
                if kind == 'shield' and gap <= 3 and safe_health(me) < safe_max_health(me) * 0.75:
                    try:
                        ability.use(me)
                    except Exception:
                        pass
                    acted()
        return attack_if_in_range(camp)

    def farm_group_attack(self, group):
        """Attack camps in `group` in pre-sorted Smith order (damaging monsters first)."""
        occupied = cambc.vision.camp_tiles()
        for camp, tile, _, _, _ in self.group_info(group)[7]:
            if occupied.is_set(tile) and safe_is_visible(camp) and self.farm_attack(camp):
                return True
        return False

    def claim(self, group=None):
        if not self.claims_enabled:
            return
        buffer = bytearray(8)
        cambc.shared_memory.read(0, buffer)
        job = self.job_ids[id(group)] if group is not None else 0
        word = publish(int.from_bytes(buffer, 'little'), self.claim_slot, job, cambc.round_number())
        cambc.shared_memory.write(0, word.to_bytes(8, 'little'))

    def farm_camps(self):
        me = cambc.me()
        now = cambc.round_number()
        visible = cambc.vision.visible_tiles()
        occupied_camps = cambc.vision.camp_tiles()
        self.investment_map()
        if self.monolith_only and self.siege_capable:
            bosses = [g for g in self.groups if g.gem_value()]
            group = min(bosses, key=lambda g: distance(me.position(), self.group_info(g)[7][0][1]))
            if self.siege_farm(group):
                self.group = group
                return
        # Finish an in-range member of the chosen group before rescoring routes.
        if self.group is not None:
            if self.siege_farm(self.group):
                return
            if self.farm_group_attack(self.group):
                self.claim(self.group)
                return
        if not self.warm(SOFT_FLOOR + COST_SETUP + COST_SCAN) or not LEDGER.optional(COST_SETUP + COST_SCAN):
            self.cuts += 1
            return
        allies = safe_visible_allies()
        blocked = blocked_tiles()
        unseen_camps = cambc.Bitboard() if self.monolith_only else self.unseen_camp_tiles(now, visible)
        route_blocked = blocked | unseen_camps
        my_pos = me.position()
        route_Blocked_me = route_blocked.copy()
        route_Blocked_me.set(my_pos, False)
        route_blocked = route_Blocked_me
        try:
            field, reached = route_field(route_blocked, my_pos, NEAR_FIELD)
        except Exception:
            return
        near = True
        free = reached & ~route_blocked
        best, best_value, best_wait = None, -1, 0
        best_travel, best_spawn_travel = 0, 999
        px, py = my_pos.x, my_pos.y
        my_id = int(me)
        claim_counts = {}
        if self.claims_enabled:
            buffer = bytearray(8)
            cambc.shared_memory.read(0, buffer)
            claim_counts = job_claim_counts(int.from_bytes(buffer, 'little'), self.claim_slot, now)
        current = self.group
        current_id = self.group_info(current)[0] if current is not None else None

        respawns = self.respawns
        if respawns:
            live = {handle: until for handle, until in respawns.items() if until > now}
            if len(live) != len(respawns):
                self.respawns = respawns = live
        timers = tuple(sorted(respawns.items()))
        order = self.route_order
        if (order is not None and order[0][2] == timers
                and max(abs(px - order[0][0]), abs(py - order[0][1])) <= 1):
            nearby = order[1]
        else:
            sort_key = (px, py, timers)
            keyed = [(tier,
                      max(abs(px - x), abs(py - y), respawns.get(handle, now) - now)
                      + (0 if home_side(x, y) else 28),
                      index, group)
                     for handle, tier, x, y, index, group in self.gstatic
                     if respawns.get(handle, 0) <= now or home_side(x, y)]
            keyed.sort()
            nearby = [entry[3] for entry in keyed[:16]]
            self.route_order = (sort_key, nearby)
        candidates = ([current] if current is not None else []) + [g for g in nearby if g is not current]

        ally_tiles = None
        idle_allies = []
        for ally in allies:
            if int(ally) != my_id and safe_gem_count(ally) == 0 and not safe_is_recalling(ally):
                apos = safe_position(ally)
                if apos:
                    idle_allies.append((apos.x, apos.y, int(ally)))
        avail_squad = 1 + len(idle_allies)
        free_allies = max(0, len(idle_allies) - sum(claim_counts.values()))

        dps = max(1, me.strength() * me.base_stats().camp_damage_multiplier)
        spell_dps_bonus = sum(a.damage_amount() for a, k, _, _ in my_abilities() if k in ('damage', 'aoe', 'cc')) / 8.0
        mit_mult = self.camp_damage_taken_mult(me)
        my_health, my_max = safe_health(me), safe_max_health(me)
        safe_risk = my_health - my_max * (0.35 if self.is_duo else 0.25)
        capture_time = cambc.constants.CAPTURE_TIME
        can_wait = me.gem_count() == 0 and not safe_visible_enemies()
        invest = self.investment_map() and not (self.siege_capable and now >= 180)
        sightings = [(x, y, attack_range + (now - seen) + 2, strength, focus * 2)
                     for x, y, seen, strength, attack_range, focus in self.enemies.values()]
        altar_field = self.altar_field
        sfield = self.spawn_field()
        is_varg = self.champ == cambc.ChampionType.VARG
        early_rally = now <= 85 and dps <= 60
        for group in candidates:
            handle, _, gx, gy, region, gems, gold, camp_info, box, bank_lb = self.group_info(group)
            if not LEDGER.optional(COST_SCAN + (COST_CANDIDATE * max(1, len(camp_info) / 3)
                                                if best is not None else 0)):
                self.cuts += 1
                if best is None:
                    return
                break
            if sfield.get(camp_info[0][1]) >= 65535:
                continue
            on_home = home_side(gx, gy)
            if self.is_duo and not on_home and now < 250:
                continue  # Never send linked-death duo bodies onto the enemy half early!
            known = not (region & visible).is_empty()
            state = group.state() if known else None
            if isinstance(state, game_map.CampGroupRespawning):
                self.respawns[handle] = now + state.timer
                wait = state.timer
            else:
                wait = 0 if known else max(0, respawns.get(handle, 0) - now)
            if wait and not can_wait:
                continue
            if wait and not on_home:
                continue
            capturing = isinstance(state, game_map.CampGroupRewardAvailable)
            if capturing:
                if ally_tiles is None:
                    ally_tiles = [(int(ally), safe_position(ally),
                                   safe_is_recalling(ally) or safe_is_submitting_gems(ally))
                                  for ally in allies]
                capturers = [ident for ident, apos, _ in ally_tiles if apos and region.is_set(apos)]
                if capturers:
                    if min(capturers) != my_id:
                        continue
                    self.group = group
                    self.claim(group)
                    return
                if (region & ~blocked).is_empty():
                    continue
                if gems <= 108:
                    my_gap = box_distance(px, py, box)
                    if any(ident != my_id and apos and not busy
                           and (box_distance(apos.x, apos.y, box) < my_gap
                                or (box_distance(apos.x, apos.y, box) == my_gap and ident < my_id))
                           for ident, apos, busy in ally_tiles):
                        continue

            worth = gems * 1.5 + gold * GOLD_WORTH
            fixed = capture_time + 1 + bank_lb + ceil(gems / 10)
            raid = self.raid(group)
            tfac = 1.0 if on_home else (0.35 if now < 150 else 0.55)

            camps = []
            if not capturing:
                for camp, spawn, base_health, base_strength, monolith in camp_info:
                    if wait:
                        health = base_health
                    elif safe_is_visible(camp):
                        health = safe_health(camp)
                    elif occupied_camps.is_set(spawn):
                        health = base_health
                    else:
                        health = 0 if visible.is_set(spawn) else base_health
                    if health > 0:
                        if monolith and not raid:
                            break
                        camps.append((health, base_strength))
                else:
                    monolith = False
                if monolith:
                    continue

            job_id = self.job_ids[id(group)]
            claimed = claim_counts.get(job_id, 0)
            avail_for_group = 1 + claimed + free_allies
            incoming, clear_turns = 0, 0
            k_req = 1
            if camps:
                # camp_info is pre-sorted with damaging monsters first and 0-damage clusters last.
                remaining = sum(strength for _, strength in camps)
                total_str = remaining
                eff_dps = dps + (spell_dps_bonus if not raid else 0)
                if not raid and is_varg and len(camps) > 1:
                    eff_dps *= min(len(camps), 1.8)
                for health, strength in camps:
                    turns = ceil(health / eff_dps)
                    incoming += turns * remaining
                    clear_turns += turns
                    remaining -= strength
                if not raid:
                    incoming *= mit_mult
                if raid:
                    spell_dps = sum(a.damage_amount() for a, k, r, _ in my_abilities()
                                    if k in ('damage', 'aoe', 'cc') and r > 3) / 8
                    clear_turns = ceil(sum(h for h, _ in camps) / max(1, spell_dps))
                    incoming = 0
                elif incoming > safe_risk and total_str >= 40:
                    # Minimum viable squad size k_req (2..4) that brings per-hero risk within safe_risk.
                    for k in (2, 3, 4):
                        if k >= self.team_size or incoming / (k * min(k, 2.2)) <= safe_risk:
                            k_req = min(self.team_size, k)
                            break
                    else:
                        k_req = min(self.team_size, 4)
                    if early_rally and total_str <= 80:
                        k_req = max(k_req, min(self.team_size, 3))
                    k_eff = min(k_req, avail_for_group if (early_rally or claimed > 0) else min(avail_for_group, 2))
                    clear_turns = ceil(clear_turns / k_eff)
                    incoming = incoming / (k_eff * min(k_eff, 2.2))
                elif early_rally and total_str >= 40 and total_str <= 80:
                    k_req = min(self.team_size, 3)
                    k_eff = min(k_req, avail_for_group)
                    clear_turns = ceil(clear_turns / k_eff)
                    incoming = incoming / (k_eff * min(k_eff, 2.2))

            if raid:
                claim_scale = 1.0
            elif capturing:
                claim_scale = policy.CLAIM_FACTOR if claimed else 1.0
            elif claimed > 0:
                if claimed < k_req:
                    claim_scale = 1.35 if (early_rally or claimed >= 1) else 0.90
                else:
                    claim_scale = policy.CLAIM_FACTOR
            else:
                claim_scale = 1.0

            scale = (0.001 if gems == 0 and not invest else 1) * (1.2 if handle == current_id else 1) * tfac * claim_scale
            travel_lb = max(0, box_distance(px, py, box) - 1, wait)
            bound = worth / max(1, travel_lb + clear_turns + fixed) * scale
            if incoming > safe_risk:
                bound *= 0.1 * my_health / max(my_health, incoming)
            if bound * 1.000001 <= best_value:
                continue

            ring = self.approach_ring(group, region)
            approaches = ring & free
            if approaches.is_empty():
                if not near or not LEDGER.afford(COST_FIELD):
                    continue
                try:
                    field, reached = route_field(route_blocked, my_pos, None)
                except Exception:
                    return
                near = False
                free = reached & ~route_blocked
                approaches = ring & free
                if approaches.is_empty():
                    continue
            approach = min(approaches.positions(), key=field.get)
            travel = field.get(approach)
            if travel >= 65535:
                continue

            ax, ay = approach.x, approach.y
            bank_travel = altar_field.get(approach)
            time = travel + max(0, wait - travel) * WAIT_COST + clear_turns + capture_time + 1 + bank_travel
            time += ceil(gems / 10)
            value = worth / max(1, time)
            value *= claim_scale * tfac
            if gems == 0 and not invest:
                value *= 0.001
            danger = 0
            for x, y, slack, strength, focus2 in sightings:
                hits = 3 - max(0, max(abs(ax - x), abs(ay - y)) - slack)
                if hits > 0:
                    danger += hits * strength + focus2
            risk = incoming + danger
            if risk > safe_risk:
                value *= 0.1 * my_health / max(my_health, risk)
            closer = 0
            for x, y, ident in (() if raid else idle_allies):
                ally_dist = max(abs(x - ax), abs(y - ay))
                if ally_dist < travel or (ally_dist == travel and ident < my_id):
                    closer += 1
            if closer:
                if closer < k_req:
                    pass
                else:
                    value *= 0.35 ** (closer - k_req + 1)
            if handle == current_id:
                value *= 1.2
            if wait and danger:
                continue
            if value > best_value:
                best, best_value, best_wait = group, value, wait
                best_travel = travel
                best_spawn_travel = sfield.get(approach)
        self.group = best
        self.claim(best)
        if best is None:
            return
        if not best_wait and can_wait and best_travel > 16 and 6 + best_spawn_travel < best_travel - 4:
            if self.can_safe_recall(my_pos):
                try:
                    me.recall()
                    acted()
                    return
                except Exception:
                    acted()
        if best_wait:
            region = self.group_info(best)[4]
            move_towards_closest(self.approach_ring(best, region) & ~region)
            return
        if self.siege_farm(best):
            return
        best_info = self.group_info(best)
        entries = best_info[7]
        if best is not current:
            if self.farm_group_attack(best):
                return
        # Prioritize approaching living damaging monsters first so we never hit a 0-damage
        # cluster while an Elk/Wolf hits us from range 3!
        goals = cambc.Bitboard()
        for camp, tile, _, base_str, _ in entries:
            if base_str > 0 and (not visible.is_set(tile) or occupied_camps.is_set(tile)):
                goals.set(tile)
        if goals.is_empty():
            for camp, tile, _, _, _ in entries:
                if not visible.is_set(tile) or occupied_camps.is_set(tile):
                    goals.set(tile)
        if goals.is_empty():
            goals = best.spawn_tiles()
        move_towards_closest(goals, avoid=unseen_camps & ~best_info[4])
        self.farm_group_attack(best)

    def combat_turn(self):
        me = cambc.me()
        if not me.is_alive():
            return False
        enemy_spawn = game_map.spawn_region(Team.ENEMY)
        enemies = [
            e for e in safe_visible_enemies()
            if safe_position(e) is not None and not enemy_spawn.is_set(safe_position(e))
        ]
        if not enemies:
            return False
        origin = safe_position(me)
        if origin is None:
            return False
        min_dist = min((distance(origin, safe_position(e)) for e in enemies), default=999)
        if min_dist > 6:
            return False

        # 1. Immediate in-range defense / opportunity: if any enemy is in attack or spell range, fight!
        if me.can_cast() and origin == self.turn_origin:
            for ability, kind, reach, info in my_abilities():
                if kind is None or not ready(ability, me):
                    continue
                if kind == 'shield' and min_dist <= 3:
                    try:
                        ability.use(me)
                    except Exception:
                        pass
                    acted()
                    break
                if kind == 'cc':
                    cc_targets = [e for e in enemies if safe_is_visible(e)
                                  and distance(origin, safe_position(e)) <= reach
                                  and e.passive() != cambc.PassiveType.STUN_IMMUNITY
                                  and not e.buffs().has_stun()]
                    if cc_targets:
                        best_cc = max(cc_targets, key=lambda e: (safe_is_submitting_gems(e), safe_gem_count(e), safe_strength(e)))
                        try:
                            best_cc_pos = safe_position(best_cc)
                            ability.use(best_cc if ability.can_target_enemies() else best_cc_pos)
                            acted()
                            attack_if_in_range(best_cc)
                            if info.exclusive_with_movement and not me.can_attack():
                                return True
                        except Exception:
                            acted()
                        break
                elif kind in ('damage', 'aoe'):
                    dmg_targets = [e for e in enemies if safe_is_visible(e)
                                   and distance(origin, safe_position(e)) <= reach]
                    if dmg_targets:
                        best_dmg = min(dmg_targets, key=lambda e: safe_health(e))
                        try:
                            best_dmg_pos = safe_position(best_dmg)
                            ability.use(best_dmg if ability.can_target_enemies() else best_dmg_pos)
                            acted()
                            attack_if_in_range(best_dmg)
                            if info.exclusive_with_movement and not me.can_attack():
                                return True
                        except Exception:
                            acted()
                        break

        enemies = [
            e for e in safe_visible_enemies()
            if safe_position(e) is not None and not enemy_spawn.is_set(safe_position(e))
        ]
        if not enemies:
            return False
        in_attack_range = [e for e in enemies if safe_is_visible(e) and distance(me.position(), safe_position(e)) <= me.attack_range()]

        if in_attack_range:
            if me.champion_name() == cambc.ChampionType.VARG and len(in_attack_range) > 1:
                def splash_score(e):
                    e_pos = safe_position(e)
                    return sum(1 for o in in_attack_range if o != e and distance(e_pos, safe_position(o)) <= 1)
                target = max(in_attack_range, key=lambda e: (splash_score(e), safe_is_submitting_gems(e), safe_gem_count(e) * 4, -safe_health(e)))
            else:
                target = max(in_attack_range, key=lambda e: (safe_is_submitting_gems(e), safe_gem_count(e) * 4, -safe_health(e)))
            near_altar = min(distance(me.position(), a) for a in self.altars) <= 1
            if safe_health(me) < safe_max_health(me) * 0.4 and safe_health(target) > me.strength() * (
                    2 if any(kind == 'reset' and ready(ability, me) for ability, kind, _, _ in my_abilities()) else 1):
                pass
            elif safe_gem_count(target) > 0 or safe_is_submitting_gems(target) or near_altar or me.gem_count() == 0:
                if attack_if_in_range(target):
                    return True

        holding_capture = (
            self.group is not None
            and self.group.spawn_tiles().is_set(origin)
            and isinstance(self.group.state(), game_map.CampGroupRewardAvailable)
            and self.channel_damage(origin, 2) < safe_health(me) * 0.75
        )
        if holding_capture and not in_attack_range:
            return False

        # 2. For non-carriers: if an enemy carrier or submitting enemy or close enemy is nearby, close in and attack!
        if (me.gem_count() == 0 and safe_health(me) >= safe_max_health(me) * (0.50 if self.is_duo else 0.40)
                and (self.monolith_only or not self.threats(origin, 3))):
            cur_pos = safe_position(me) or origin
            no_brawl = self.champ == cambc.ChampionType.CASSI or (self.ranged_caster and self.investment_map())
            enemies_5 = sum(1 for e in enemies if distance(cur_pos, safe_position(e)) <= 5)
            allies_5 = sum(1 for a in safe_visible_allies() if safe_position(a) and distance(cur_pos, safe_position(a)) <= 5 and not safe_is_recalling(a))
            can_brawl = not no_brawl and (self.monolith_only or allies_5 >= enemies_5)
            brawl_reach = 4 if self.monolith_only else 3
            priority_targets = [
                e for e in enemies
                if safe_is_visible(e) and (
                    safe_is_submitting_gems(e)
                    or safe_gem_count(e) > 0
                    or (can_brawl and distance(cur_pos, safe_position(e)) <= brawl_reach
                        and (tiles_around(safe_position(e), 2) & enemy_spawn).is_empty())
                )
            ]
            if priority_targets:
                target = max(priority_targets, key=lambda e: (safe_is_submitting_gems(e), safe_gem_count(e) * 4, -safe_health(e), -distance(cur_pos, safe_position(e))))
                t_pos = safe_position(target)
                moved = False
                if t_pos:
                    reach = max(1, me.attack_range())
                    if distance(cur_pos, t_pos) > reach:
                        goals = tiles_around(t_pos, reach)
                        moved = move_towards_closest(goals)
                if safe_is_visible(target):
                    if attack_if_in_range(target):
                        return True
                for e in enemies:
                    if attack_if_in_range(e):
                        return True
                if moved:
                    return True

        cur_pos = safe_position(me)
        if cur_pos and (me.gem_count() > 0 or safe_health(me) < safe_max_health(me) * (0.48 if self.is_duo else 0.40)):
            if any(safe_is_visible(e) and distance(cur_pos, safe_position(e)) <= safe_attack_range(e) + 1 for e in enemies):
                self.retreat()
                return True
        return False

    def observe_enemies(self):
        now = self.now = cambc.round_number()
        self.enemies = {key: value for key, value in self.enemies.items()
                        if now - value[2] <= 8}
        for enemy in safe_visible_enemies():
            try:
                pos = safe_position(enemy)
                if pos:
                    self.enemies[int(enemy)] = (pos.x, pos.y, now, safe_strength(enemy),
                                                safe_attack_range(enemy), enemy.focus())
            except Exception:
                pass
        self.camp_tiles = cambc.vision.camp_tiles()
        self._camp_threats_stale = True

    def threats(self, center, reach):
        """(x, y, strength, radius) of visible AWAKE damaging camps within `reach` of center."""
        if self._camp_threats_stale:
            self._camp_threats_stale = False
            self.camp_threats = {}
        found = []
        for pos in (self.camp_tiles & tiles_around(center, reach)).positions():
            key = (pos.x, pos.y)
            entry = self.camp_threats.get(key, False)
            if entry is False:
                try:
                    camp = cambc.vision.camp_at(pos)
                    strength = camp.strength()
                    if strength > 0:
                        if hasattr(camp, 'is_awake'):
                            awake = camp.is_awake()
                        else:
                            awake = safe_health(camp) < safe_max_health(camp)
                        entry = (key[0], key[1], strength, camp.attack_range()) if awake else None
                    else:
                        entry = None
                except Exception:
                    entry = None
                self.camp_threats[key] = entry
            if entry is not None:
                found.append(entry)
        return found

    def danger(self, tile, turns=1):
        now = self.now
        tx, ty = tile.x, tile.y
        damage = 0
        for x, y, seen, strength, attack_range, focus in self.enemies.values():
            arrival = max(0, max(abs(tx - x), abs(ty - y)) - attack_range - (now - seen) - 2)
            hits = max(0, turns - arrival)
            if hits:
                damage += hits * strength + focus * 2
        return damage

    def camp_pressure(self, tile):
        tx, ty = tile.x, tile.y
        return sum(strength for x, y, strength, radius in self.threats(tile, self.max_camp_range)
                   if max(abs(tx - x), abs(ty - y)) <= radius)

    def channel_damage(self, tile, turns):
        return self.danger(tile, turns) + turns * self.camp_pressure(tile)

    def retreat(self):
        me = cambc.me()
        if not me.is_alive() or not LEDGER.afford(COST_RETREAT):
            return
        origin = safe_position(me)
        if origin is None:
            return

        seen = {}
        now = self.now
        ox, oy = origin.x, origin.y
        area = me.base_stats().base_move_speed + max(
            [reach for _, kind, reach, _ in my_abilities() if kind == 'dash'] + [0])
        sightings = [entry for entry in self.enemies.values()
                     if max(abs(ox - entry[0]), abs(oy - entry[1])) - area
                     <= entry[4] + (now - entry[2]) + 3]
        camp_threats = [entry for entry in self.threats(origin, area + self.max_camp_range)
                        if max(abs(ox - entry[0]), abs(oy - entry[1])) - area <= entry[3]]

        def threat_zone():
            zone = cambc.Bitboard()
            for x, y, when, strength, attack_range, focus in sightings:
                if strength > 0 or focus > 0:
                    zone |= tiles_around(cambc.Vec2(x, y), attack_range + (now - when) + 3)
            for x, y, strength, radius in camp_threats:
                if strength > 0:
                    zone |= tiles_around(cambc.Vec2(x, y), radius)
            return zone

        sighting_terms = [(x, y, attack_range + (now - when) + 2, strength, focus * 2)
                          for x, y, when, strength, attack_range, focus in sightings]

        terms = [sighting_terms, camp_threats]

        def exposure(tile):
            return exposure_xy(tile.x, tile.y)

        def exposure_xy(tx, ty):
            key = (tx, ty)
            value = seen.get(key)
            if value is None:
                value = 0
                for x, y, slack, strength, focus2 in terms[0]:
                    hits = 2 - max(0, max(abs(tx - x), abs(ty - y)) - slack)
                    if hits > 0:
                        value += hits * strength + focus2
                value += 2 * sum([strength for x, y, strength, radius in terms[1]
                                  if max(abs(tx - x), abs(ty - y)) <= radius])
                seen[key] = value
            return value

        enemies = safe_visible_enemies()
        enemy_info = []
        for e in enemies:
            try:
                pos = safe_position(e)
                if pos and distance(origin, pos) <= 8:
                    enemy_info.append((pos, safe_attack_range(e), e))
            except Exception:
                pass
        enemy_xy = [(p.x, p.y, r) for p, r, e in enemy_info]

        def enemy_gap(tx, ty):
            return min([max(abs(tx - x), abs(ty - y)) for x, y, _ in enemy_xy])

        if not enemy_info and exposure(origin) == 0:
            try:
                me.recall()
            except Exception:
                pass
            acted()
            return

        # 1. Defensive abilities before moving: shield or CC
        for ability, kind, reach, info in my_abilities():
            if kind is None or not ready(ability, me):
                continue
            if kind == 'shield':
                try:
                    ability.use(me)
                except Exception:
                    pass
                acted()
                break
            if kind == 'cc' and origin == self.turn_origin:
                targets = [e for p, r, e in enemy_info
                           if safe_is_visible(e) and safe_is_alive(e)
                           and distance(origin, p) <= reach
                           and e.passive() != cambc.PassiveType.STUN_IMMUNITY
                           and not e.buffs().has_stun()]
                if targets:
                    target = max(targets, key=lambda e: safe_strength(e))
                    try:
                        t_pos = safe_position(target)
                        ability.use(target if ability.can_target_enemies() else t_pos)
                        acted()
                        attack_if_in_range(target)
                        if info.exclusive_with_movement:
                            return
                    except Exception:
                        acted()
                    break

        # 2. Dash to escape
        for ability, kind, reach, info in my_abilities():
            if kind == 'dash' and ready(ability, me) and LEDGER.afford(COST_DASH):
                try:
                    blocked = blocked_tiles()
                    transit = blocked & ~game_map.holes()
                    landings = transit.reachable_tiles(origin, int(info.range)) & ~blocked
                    landings &= ~game_map.spawn_region(Team.ENEMY)
                    choices = [origin, *landings.positions()]
                    if enemy_info:
                        cur_min = enemy_gap(origin.x, origin.y)
                        gaps = [enemy_gap(tile.x, tile.y) for tile in choices]
                        widest = max(gaps)
                        best_landing = next(tile for tile, gap in zip(choices, gaps) if gap == widest)
                        if camp_threats:
                            def pressure(tile):
                                tx, ty = tile.x, tile.y
                                return sum([strength for x, y, strength, radius in camp_threats
                                            if max(abs(tx - x), abs(ty - y)) <= radius])
                            best_landing = max((tile for tile, gap in zip(choices, gaps) if gap == widest),
                                               key=lambda tile: -pressure(tile))
                        if widest > cur_min:
                            used = ability.use(best_landing)
                            acted()
                            if used:
                                origin = safe_position(me) or origin
                                break
                    else:
                        if exposure(origin) == 0:
                            landing = origin
                        else:
                            calm = landings & ~threat_zone()
                            if calm.is_empty():
                                landing = min(choices, key=exposure)
                            else:
                                landing = calm.positions()[0]
                        if exposure(landing) < exposure(origin):
                            used = ability.use(landing)
                            acted()
                            if used:
                                origin = safe_position(me) or origin
                                break
                except Exception:
                    acted()

        # 3. Walk to flee
        if me.can_move() and LEDGER.afford(COST_WALK):
            try:
                blocked = blocked_tiles()
                step_len = me.base_stats().base_move_speed
                reachable = [origin, *blocked.reachable_tiles(origin, step_len).positions()]
                if enemy_info:
                    goals = self.altar_xy if me.gem_count() > 0 else ally_spawn_xy()
                    cx, cy = origin.x, origin.y
                    terms[0] = [t for t in terms[0] if max(abs(cx - t[0]), abs(cy - t[1])) - step_len <= t[2] + 1]
                    terms[1] = [t for t in terms[1] if max(abs(cx - t[0]), abs(cy - t[1])) - step_len <= t[3]]
                    ranked = []
                    for index, tile in enumerate(reachable):
                        tx, ty = tile.x, tile.y
                        penalty, min_dist = 0, 999
                        for x, y, r in enemy_xy:
                            d = max(abs(tx - x), abs(ty - y))
                            if d < min_dist:
                                min_dist = d
                            if d <= r:
                                penalty = 1000
                            elif d == r + 1 and penalty == 0:
                                penalty = 300
                        ranked.append((penalty - min_dist * 25
                                       + min([max(abs(tx - x), abs(ty - y)) for x, y in goals]), index, tx, ty))
                    ranked.sort()
                    best_score, best_index = None, None
                    for base, index, tx, ty in ranked:
                        if best_score is not None and (base > best_score
                                                       or (base == best_score and index > best_index)):
                            break
                        score = base + exposure_xy(tx, ty)
                        if (best_score is None or score < best_score
                                or (score == best_score and index < best_index)):
                            best_score, best_index = score, index
                    step = reachable[best_index]
                    if step != origin and not blocked.is_set(step):
                        safe_move(step)
                else:
                    field = self.spawn_field()
                    wards = me.ward_positions()
                    step = min(reachable, key=lambda tile: (exposure(tile),
                               0 if wards and distance(tile, wards[0]) <= 6 else 1, field.get(tile)))
                    if step != origin and not blocked.is_set(step):
                        safe_move(step)
            except Exception:
                pass

        # 4. Defend with basic attack / reset if enemy is in range
        if me.can_attack():
            for enemy in safe_visible_enemies():
                if attack_if_in_range(enemy):
                    break

    def bank(self):
        me = cambc.me()
        if not me.is_alive() or not LEDGER.afford(COST_BANK):
            return
        origin = safe_position(me)
        if origin is None:
            return
        duration = max(cambc.constants.SUBMIT_GEM_MINIMUM_DURATION,
                       ceil(me.gem_count() * cambc.constants.SUBMIT_GEM_DURATION_MULTIPLIER
                            + cambc.constants.SUBMIT_GEM_BASE_DURATION))
        ox, oy = origin.x, origin.y
        altars = sorted(zip(self.altars, self.submit_rings()),
                        key=lambda entry: max(abs(ox - entry[0].x), abs(oy - entry[0].y)))
        enemy_locks = cambc.vision.altar_lock_tiles(Team.ENEMY)
        visible = cambc.vision.visible_tiles()
        locked = self.locked_altars
        for altar in self.altars:
            if visible.is_set(altar):
                locked[(altar.x, altar.y)] = enemy_locks.is_set(altar)

        blocked = blocked_tiles()
        try:
            field, reached = route_field(blocked, origin, NEAR_FIELD)
        except Exception:
            return
        near = True
        free = reached & ~blocked
        strength = max(1, me.strength())
        submit_range = cambc.constants.SUBMIT_GEMS_RANGE
        options = []
        best_score = None
        for altar, ring in altars:
            if options and not LEDGER.optional(COST_SCAN + COST_CANDIDATE):
                self.cuts += 1
                break
            inertia = -4 if altar == self.bank_altar else 0
            if locked.get((altar.x, altar.y)):
                inertia += LOCK_BREAK_TURNS
            gap = max(abs(ox - altar.x), abs(oy - altar.y))
            if best_score is not None and max(0, gap - submit_range) + inertia >= best_score:
                continue
            approaches = ring & free
            if approaches.is_empty():
                if not near or not LEDGER.afford(COST_FIELD):
                    continue
                try:
                    field, reached = route_field(blocked, origin, None)
                except Exception:
                    return
                near = False
                free = reached & ~blocked
                approaches = ring & free
                if approaches.is_empty():
                    continue
            tile = min(approaches.positions(), key=field.get)
            travel = field.get(tile)
            risk = self.channel_damage(tile, duration + min(travel, 4))
            score = travel + risk / strength + inertia
            options.append((score, tile, altar, travel))
            if best_score is None or score < best_score:
                best_score = score
        if not options:
            self.retreat()
            return
        _, tile, altar, best_travel = min(options, key=lambda option: option[0])
        self.bank_altar = altar

        if best_travel > 12 and self.can_safe_recall(origin):
            shop_bonus = 5 if (me.gold_count() >= 150 and self.champ != cambc.ChampionType.TAVI) else 0
            heal_wait = 1 if safe_health(me) < safe_max_health(me) else 0
            if 5 + heal_wait + self.spawn_altar_dist - shop_bonus < best_travel - 2:
                try:
                    me.recall()
                    acted()
                    return
                except Exception:
                    acted()

        if enemy_locks.is_set(altar):
            for lock in cambc.vision.altar_locks(Team.ENEMY):
                if lock.position() == altar:
                    if attack_if_in_range(lock):
                        return
                    break
            if distance(origin, altar) <= me.attack_range():
                return
            move_towards_closest(tiles_around(tile, 0))
            return

        # Place altar lock if we have one within range 2
        try:
            lock = me.consumables()[cambc.ConsumableType.ALTAR_LOCK]
            if (lock.count() > 0 and distance(origin, altar) <= 2
                    and not cambc.vision.has_altar_lock(altar)
                    and not any(safe_is_submitting_gems(ally) and distance(safe_position(ally), altar) <= 1
                                for ally in safe_visible_allies())):
                lock.use(altar)
                acted()
        except Exception:
            acted()

        # Check if we can submit
        if distance(origin, altar) <= cambc.constants.SUBMIT_GEMS_RANGE:
            is_marcella = (me.champion_name() == cambc.ChampionType.MARCELLA or
                           me.passive() == cambc.PassiveType.STUN_IMMUNITY)
            visible_threats = safe_visible_enemies()
            lethal = False
            stun_threat = False
            for e in visible_threats:
                if not safe_is_visible(e):
                    continue
                e_pos = safe_position(e)
                if e_pos is None:
                    continue
                d = distance(origin, e_pos)
                if d <= safe_attack_range(e) + 2:
                    if safe_strength(e) * min(duration, 5) >= safe_health(me):
                        lethal = True
                if not is_marcella and d <= 4:
                    try:
                        for a in e.abilities():
                            if a.is_ready() and (a.is_cc() or (a.is_attack_reset() and getattr(a.info(), 'enhanced_attack', False))):
                                stun_threat = True
                                break
                    except Exception:
                        pass

            safe = not lethal and not stun_threat
            if safe and cambc.round_number() + duration <= cambc.constants.MAX_ROUNDS:
                try:
                    me.submit_gems(altar)
                    return
                except Exception:
                    pass
            close_foes = [e for e in visible_threats if distance(origin, safe_position(e)) <= me.attack_range()]
            if close_foes and attack_if_in_range(close_foes[0]):
                return

        goals = tiles_around(tile, 0)
        if not move_towards_closest(goals):
            all_approaches = tiles_around(altar, cambc.constants.SUBMIT_GEMS_RANGE)
            if not move_towards_closest(all_approaches):
                self.bank_altar = None
                if cambc.fuel_remaining() > 600000:
                    self.retreat()

    def place_ward(self):
        me = cambc.me()
        if not me.is_alive():
            return
        try:
            if me.restrictions() & cambc.BuffRestrictions.WARD:
                return
            wards = me.ward_positions()
            my_pos = safe_position(me)
            if my_pos is None:
                return
            if me.ward_cooldown() or (wards and distance(wards[0], my_pos) <= 6):
                return
            if self.altar_field is None or not LEDGER.optional(COST_WARD):
                return
            candidates = (me.ward_placement_tiles() & ~blocked_tiles()
                          & ~cambc.vision.ward_tiles(Team.ALLY))
            candidates.set(my_pos, False)
            if candidates.is_empty():
                return
            bush = candidates & game_map.bushes()
            pool = candidates if bush.is_empty() else bush
            reach = ceil(cambc.constants.WARD_PLACEMENT_RADIUS)
            gap = self.altar_gap(my_pos)
            mx, my, limit = my_pos.x, my_pos.y, gap + 2 * reach
            near_altars = [altar for altar, (x, y) in zip(self.altars, self.altar_xy)
                           if max(abs(x - mx), abs(y - my)) <= limit]
            bands = {}

            def band(k):
                tiles = bands.get(k)
                if tiles is None:
                    tiles = bands[k] = cambc.Bitboard()
                    if k >= 0:
                        for altar in near_altars:
                            tiles.draw_chebyshev(altar, k)
                return tiles

            rings, inner = [], tiles_around(my_pos, 0)
            for c in range(1, reach):
                disk = tiles_around(my_pos, c)
                rings.append((c, pool & disk & ~inner))
                inner = disk
            rings.append((reach, pool & ~inner))
            best = None
            for s in range(2 * reach - gap, -gap - reach, -1):
                level = cambc.Bitboard()
                for c, ring in rings:
                    level |= ring & band(c - s)
                if not level.is_empty():
                    best = level.positions()[0]
                    break
            if best is None:
                return False
            placed = me.place_ward(best)
            acted()
            return placed
        except Exception:
            acted()
        return False

    def buy_items(self):
        me = cambc.me()
        try:
            if me.gold_count() < self.cheapest_buy:
                return
            lock_type = cambc.ConsumableType.ALTAR_LOCK
            lock = me.consumables()[lock_type]
            has_lock = lock.count() > 0
            if not has_lock and me.can_buy(lock_type):
                me.buy(lock_type)
                has_lock = True

            champ = self.champ
            focus_build = (champ in (cambc.ChampionType.CASSI, cambc.ChampionType.STELLAR, cambc.ChampionType.PRISM)
                           or (champ == cambc.ChampionType.TAVI and not policy.TAVI_STRENGTH))
            item = Item.POWER_SHARD_OF_FOCUS if focus_build else Item.POWER_SHARD_OF_STRENGTH
            if getattr(policy, 'JUNGLE_BUILD', False):
                self.investment_map()
                if self.resource_mode:
                    jungle = Item.JUNGLE_SHARD_OF_FOCUS if focus_build else Item.JUNGLE_SHARD_OF_STRENGTH
                    emblem = Item.JUNGLE_EMBLEM_OF_FOCUS if focus_build else Item.JUNGLE_EMBLEM_OF_STRENGTH
                    prereqs = ((jungle, emblem),)
                elif champ == cambc.ChampionType.CASSI:
                    prereqs = (
                        (Item.BRUISER_SHARD_OF_HEALTH, Item.BRUISER_EMBLEM_OF_HEALTH),
                        (Item.JUNGLE_SHARD_OF_FOCUS, Item.JUNGLE_EMBLEM_OF_FOCUS),
                    )
                elif champ == cambc.ChampionType.REN:
                    prereqs = (
                        (Item.BRUISER_SHARD_OF_HEALTH, Item.BRUISER_EMBLEM_OF_HEALTH),
                        (Item.JUNGLE_SHARD_OF_FOCUS, Item.JUNGLE_EMBLEM_OF_FOCUS),
                        (Item.DURABILITY_SHARD_OF_HEALTH, Item.DURABILITY_EMBLEM_OF_HEALTH),
                    )
                    item = Item.POWER_SHARD_OF_FOCUS
                elif champ == cambc.ChampionType.RYTH:
                    prereqs = (
                        (Item.JUNGLE_SHARD_OF_STRENGTH, Item.JUNGLE_EMBLEM_OF_STRENGTH),
                        (Item.BRUISER_SHARD_OF_HEALTH, Item.BRUISER_EMBLEM_OF_HEALTH),
                        (Item.DURABILITY_SHARD_OF_HEALTH, Item.DURABILITY_EMBLEM_OF_HEALTH),
                    )
                elif champ == cambc.ChampionType.ISSAC:
                    prereqs = (
                        (Item.JUNGLE_SHARD_OF_STRENGTH, Item.JUNGLE_EMBLEM_OF_STRENGTH),
                        (Item.DURABILITY_SHARD_OF_HEALTH, Item.DURABILITY_EMBLEM_OF_HEALTH),
                    )
                else:
                    jungle = Item.JUNGLE_SHARD_OF_FOCUS if focus_build else Item.JUNGLE_SHARD_OF_STRENGTH
                    emblem = Item.JUNGLE_EMBLEM_OF_FOCUS if focus_build else Item.JUNGLE_EMBLEM_OF_STRENGTH
                    prereqs = ((jungle, emblem),)
                for j_shard, j_emb in prereqs:
                    counts = me.item_count()
                    if not counts[j_emb]:
                        need = 5 - counts[j_shard]
                        amount = min(need, me.gold_count() // j_shard.cost())
                        if amount and me.can_buy(j_shard, amount):
                            me.buy(j_shard, amount)
                        if counts[j_shard] + amount < 5:
                            break
            reserve = 0 if has_lock else 10
            counts = me.item_count()
            if not getattr(policy, 'JUNGLE_BUILD', False) or all(counts[emb] > 0 for _, emb in prereqs):
                available = max(0, me.gold_count() - reserve)
                count = available // item.cost()
                if count and me.can_buy(item, count):
                    me.buy(item, count)

            if not has_lock and me.can_buy(lock_type):
                me.buy(lock_type)
        except Exception:
            pass

    def play_turn(self):
        try:
            self._do_play_turn()
        finally:
            if self.gstatic is None:
                self.warm(WARM_FLOOR)

    def _do_play_turn(self):
        acted()
        self.claim()
        me = cambc.me()
        if not me.is_alive():
            self.buy_items()
            return
        origin = safe_position(me)
        if origin is None:
            return
        acted()
        warming = self.gstatic is None
        if warming:
            self.warm(WARM_FLOOR)
            if self.gstatic is None:
                return
        self.turn_origin = origin
        self.observe_enemies()
        self.buy_items()
        if not me.is_alive() or me.is_recalling() or me.is_teleporting():
            return
        if me.is_submitting_gems():
            try:
                if self.channel_damage(origin, min(me.remaining_channel_time() + 1, 5)) < safe_health(me) * 0.85:
                    return
                me.cancel_submit_gems()
                acted()
                self.retreat()
            except Exception:
                pass
            return
        if not me.can_move() and not me.can_attack() and not me.can_cast():
            return

        at_spawn = game_map.spawn_region(Team.ALLY).is_set(origin)
        if at_spawn and safe_health(me) < safe_max_health(me):
            return

        if self.combat_turn():
            return

        if not warming and self.place_ward():
            self.observe_enemies()

        enemies = safe_visible_enemies()
        close_enemies = [e for e in enemies if distance(origin, safe_position(e)) <= 8]
        altar_dist = self.altar_gap(origin)
        near_altar = altar_dist <= 2
        immediate_threat = any(distance(origin, safe_position(e)) <= safe_attack_range(e) + 1 for e in close_enemies)
        threatened_carrier = me.gem_count() > 0 and not near_altar and (safe_health(me) < safe_max_health(me) * 0.45 or immediate_threat)

        if threatened_carrier:
            self.retreat()
            return

        threshold = 0.6 if (me.gem_count() >= 40 and close_enemies) else (0.42 if self.is_duo else 0.35)
        if not at_spawn and safe_health(me) < safe_max_health(me) * threshold:
            self.retreat()
            return

        # Banking logic:
        team_gems = cambc.global_submitted_gems(Team.ALLY)
        winning_bag = me.gem_count() > 0 and (team_gems + me.gem_count() >= 1000)
        bank_threshold = 20 if (close_enemies or altar_dist <= 8) else 44
        should_bank = (me.gem_count() >= bank_threshold or
                       (me.gem_count() > 0 and (near_altar or winning_bag or safe_health(me) < safe_max_health(me) * 0.6)))
        if should_bank:
            self.bank()
            return
        self.bank_altar = None

        # Cash in the investment on maps whose gems require a boss or a raid.
        if (me.gem_count() == 0 and me.gold_count() >= (150 if self.investment_map() else 240)
                and not at_spawn and not enemies
                and me.champion_name() != cambc.ChampionType.TAVI):
            capturing = (self.group is not None and self.group.spawn_tiles().is_set(origin)
                         and isinstance(self.group.state(), game_map.CampGroupRewardAvailable))
            if not capturing:
                self.retreat()
                return

        for enemy in enemies:
            if attack_if_in_range(enemy):
                return

        self.farm_camps()

        try:
            me.set_priority(1 + below(100))
        except Exception:
            pass
