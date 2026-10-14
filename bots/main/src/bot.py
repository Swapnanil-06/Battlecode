"""Champion decisions. main.py dispatches here after the draft."""
from math import ceil
from randomness import below

import cambc
from cambc import game_map
from combat import exchange

Team, Item = cambc.Team, cambc.ItemType


def distance(a, b):
    if a is None or b is None:
        return 999999
    return max(abs(a.x - b.x), abs(a.y - b.y))


def safe_is_visible(unit):
    if unit is None:
        return False
    try:
        return unit.is_visible()
    except Exception:
        return False


def safe_position(unit):
    if unit is None:
        return None
    try:
        if unit.is_visible():
            return unit.position()
    except Exception:
        pass
    return None


def safe_health(unit):
    if unit is None:
        return 0
    try:
        if unit.is_visible():
            return unit.health()
    except Exception:
        pass
    return 0


def safe_strength(unit):
    if unit is None:
        return 0
    try:
        if unit.is_visible():
            return unit.strength()
    except Exception:
        pass
    return 0


def safe_attack_range(unit):
    if unit is None:
        return 1
    try:
        if unit.is_visible():
            return unit.attack_range()
    except Exception:
        pass
    return 1


def safe_gem_count(unit):
    if unit is None:
        return 0
    try:
        if unit.is_visible():
            return unit.gem_count()
    except Exception:
        pass
    return 0


def safe_is_submitting_gems(unit):
    if unit is None:
        return False
    try:
        if unit.is_visible():
            return unit.is_submitting_gems()
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
        if unit.is_visible():
            return unit.max_health()
    except Exception:
        pass
    return 1


def safe_visible_enemies():
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
    # Combine terrain and visible occupants using native bitboard operations.
    blocked = (game_map.walls() | game_map.holes() | game_map.altars()
               | game_map.spawn_region(Team.ENEMY) | cambc.vision.champion_tiles()
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

    # Only free goals or occupied camp tiles can seed the field.
    blocked = blocked_tiles()
    if avoid is not None:
        blocked |= avoid
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

    # Dash legality differs from walking: holes can be crossed but not landed on.
    try:
        for ability in me.abilities():
            if ability.is_dash() and ability.is_ready():
                transit = blocked & ~game_map.holes()
                landings = transit.reachable_tiles(origin, int(ability.info().range)) & ~blocked
                choices = [origin, *landings.positions()]
                landing = min(choices, key=field.get)
                if field.get(landing) + 1 < field.get(origin):
                    try:
                        if ability.use(landing):
                            return True
                    except Exception:
                        pass
    except Exception:
        pass

    # Choose a reachable step with a smaller distance to the goal.
    if not me.can_move():
        return False
    try:
        blocked = blocked_tiles()
        if avoid is not None:
            blocked |= avoid
            blocked.set(origin, False)
        reachable = blocked.reachable_tiles(origin, me.base_stats().base_move_speed)
        step = min([origin, *reachable.positions()], key=field.get)
        if step == origin or blocked.is_set(step):
            return False
        return safe_move(step)
    except Exception:
        return False


def attack_if_in_range(target):
    me = cambc.me()
    if not me.is_alive() or not me.can_attack() or target is None:
        return False
    my_pos = safe_position(me)
    if my_pos is None:
        return False

    try:
        if isinstance(target, cambc.AltarLock):
            if not target.is_enemy() or target.hits_remaining() <= 0:
                return False
            t_pos = safe_position(target)
            if t_pos is None or distance(my_pos, t_pos) > me.attack_range():
                return False
            me.attack(target)
            if me.can_cast() and target.hits_remaining() > 0:
                for ability in me.abilities():
                    if ability.is_attack_reset() and ability.is_ready():
                        if not me.can_attack() and ability.use() and me.can_attack():
                            if target.hits_remaining() > 0:
                                me.attack(target)
                        break
            return True

        if isinstance(target, cambc.Camp):
            if not cambc.vision.camp_tiles().is_set(target.spawn_position()):
                return False
            t_pos = safe_position(target)
            if t_pos is None or not safe_is_visible(target) or safe_health(target) <= 0:
                return False
            if distance(my_pos, t_pos) > me.attack_range():
                return False
            me.attack(target)
            alive = cambc.vision.camp_tiles().is_set(target.spawn_position()) and safe_is_visible(target)
            if me.can_cast() and alive and safe_health(target) > 0:
                for ability in me.abilities():
                    if ability.is_attack_reset() and ability.is_ready():
                        if not me.can_attack() and ability.use() and me.can_attack():
                            if safe_is_visible(target) and safe_health(target) > 0:
                                me.attack(target)
                        break
            return True

        # Champion target
        if not safe_is_visible(target) or not safe_is_alive(target) or safe_health(target) <= 0:
            return False
        t_pos = safe_position(target)
        if t_pos is None or distance(my_pos, t_pos) > me.attack_range():
            return False
        me.attack(target)
        if me.can_cast() and safe_is_visible(target) and safe_is_alive(target) and safe_health(target) > 0:
            for ability in me.abilities():
                if ability.is_attack_reset() and ability.is_ready():
                    if not me.can_attack() and ability.use() and me.can_attack():
                        if safe_is_visible(target) and safe_is_alive(target) and safe_health(target) > 0:
                            t_pos2 = safe_position(target)
                            if t_pos2 and distance(my_pos, t_pos2) <= me.attack_range():
                                me.attack(target)
                    break
        return True
    except Exception:
        return False


class Bot:
    def __init__(self):
        self.enemies = {}
        self.respawns = {}
        self.group = None
        # Warm static SDK caches in the construction turn, not during decisions.
        self.groups = game_map.camp_groups()
        self.altars = game_map.altars().positions()
        self.bank_altar = None
        self.turn_origin = None
        self.plan_count = 0
        self.min_fuel = 2500000
        self.suspended = 0
        _ = cambc.constants.MAX_ROUNDS

    def farm_attack(self, camp):
        me = cambc.me()
        if not safe_is_visible(camp) or not cambc.vision.camp_tiles().is_set(camp.spawn_position()):
            return False
        c_pos = safe_position(camp)
        if c_pos is None:
            return False
        gap = distance(me.position(), c_pos)
        if me.position() == self.turn_origin and me.can_cast():
            for ability in me.abilities():
                if not ability.is_ready():
                    continue
                if (ability.is_damage() or ability.is_cc() or ability.is_aoe_damage()) and gap <= getattr(ability.info(), 'range', 0):
                    # A range-four spell can clear without standing in retaliation.
                    if ability.damage_amount() > me.strength() or gap > me.attack_range():
                        try:
                            ability.use(camp if ability.can_target_camps() else c_pos)
                            attack_if_in_range(camp)
                            return True
                        except Exception:
                            pass
                if ability.is_shield() and gap <= 3 and safe_health(me) < safe_max_health(me) * 0.75:
                    try:
                        ability.use(me)
                    except Exception:
                        pass
        return attack_if_in_range(camp)

    def farm_camps(self):
        me = cambc.me()
        now = cambc.round_number()
        visible = cambc.vision.visible_tiles()
        occupied_camps = cambc.vision.camp_tiles()
        # Finish an in-range member of the chosen group before rescoring routes.
        if self.group is not None:
            for camp in self.group:
                if safe_is_visible(camp) and self.farm_attack(camp):
                    return
        allies = safe_visible_allies()
        blocked = blocked_tiles()
        field, reached = cambc.DistanceField(), cambc.Bitboard()
        try:
            field.compute(blocked, tiles_around(me.position(), 0), reached)
        except Exception:
            return
        best, best_value = None, -1

        def camp_group_priority(group):
            camp0 = group.camps()[0]
            dist = distance(me.position(), camp0.spawn_position())
            has_gems = group.gem_value() > 0
            is_gem_cluster = any(camp.is_gem_cluster() for camp in group)
            tier = 0 if is_gem_cluster else (1 if has_gems else 2)
            return (tier, dist)

        nearby = sorted((group for group in self.groups
                         if self.respawns.get(int(group), 0) <= now), key=camp_group_priority)
        candidates = ([self.group] if self.group is not None else []) + nearby[:16]
        for group in candidates:
            # Keep enough fuel for pathing and actions; never resume a stale plan.
            if cambc.fuel_remaining() < 350000:
                if best is None:
                    return  # A cut scan is not evidence that there are no camps.
                break
            region = group.spawn_tiles()
            known = not (region & visible).is_empty()
            state = group.state() if known else None
            if isinstance(state, game_map.CampGroupRespawning):
                # Timer starts after capture, and occupancy can postpone the respawn.
                self.respawns[int(group)] = now + state.timer
                continue
            if not known and self.respawns.get(int(group), 0) > now:
                continue
            capturing = isinstance(state, game_map.CampGroupRewardAvailable)
            capturers = []
            for ally in allies:
                apos = safe_position(ally)
                if apos and region.is_set(apos):
                    capturers.append(ally)
            if capturing and capturers:
                if min(int(ally) for ally in capturers) != int(me):
                    continue
                self.group = group
                return

            camps = []
            for camp in group:
                stats = camp.base_stats()
                if safe_is_visible(camp):
                    health = safe_health(camp)
                elif occupied_camps.is_set(camp.spawn_position()):
                    health = stats.base_health
                else:
                    health = 0 if visible.is_set(camp.spawn_position()) else stats.base_health
                if not capturing and health > 0:
                    camps.append((camp, health, stats.base_strength))
            if any(camp.is_monolith() for camp, _, _ in camps):
                continue
            approaches = cambc.Bitboard()
            for tile in region.positions():
                approaches |= tiles_around(tile, 1)
            approaches &= reached & ~blocked
            if approaches.is_empty():
                continue
            approach = min(approaches.positions(), key=field.get)
            travel = field.get(approach)

            dps = me.strength() * me.base_stats().camp_damage_multiplier
            incoming, clear_turns = 0, 0
            remaining = sum(strength for _, _, strength in camps)
            for camp, health, strength in sorted(camps, key=lambda entry: entry[1]):
                turns = ceil(health / max(1, dps))
                incoming += turns * remaining
                clear_turns += turns
                remaining -= strength
            bank_travel = min(distance(approach, altar) for altar in self.altars)
            time = travel + clear_turns + cambc.constants.CAPTURE_TIME + 1 + bank_travel
            time += ceil(group.gem_value() / 10)
            value = (group.gem_value() * 1.5 + group.gold_value() * 0.1) / max(1, time)
            if group.gem_value() == 0:
                value *= 0.001
            risk = incoming + self.danger(approach, 3)
            if risk > safe_health(me) - safe_max_health(me) * 0.25:
                value *= 0.1 * safe_health(me) / max(safe_health(me), risk)
            for ally in allies:
                if ally != me and safe_gem_count(ally) == 0 and not ally.is_recalling():
                    apos = safe_position(ally)
                    if apos:
                        ally_dist = distance(apos, approach)
                        if ally_dist < travel or (ally_dist == travel and int(ally) < int(me)):
                            value *= 0.35
            if group == self.group:
                value *= 1.2
            if value > best_value:
                best, best_value = group, value
        self.group = best
        if best is None:
            return
        for camp in best:
            if safe_is_visible(camp) and self.farm_attack(camp):
                return
        goals = cambc.Bitboard()
        for camp in best:
            tile = camp.spawn_position()
            if not visible.is_set(tile) or occupied_camps.is_set(tile):
                goals.set(tile)
        if goals.is_empty():
            goals = best.spawn_tiles()
        move_towards_closest(goals)
        for camp in best:
            if safe_is_visible(camp) and attack_if_in_range(camp):
                return

    def fighter(self, unit):
        try:
            if not safe_is_visible(unit):
                return dict(strength=0, range=1, speed=1, spells=[], health=0, immune=False, stunned=False)
            spells = []
            for ability in unit.abilities():
                info = ability.info()
                kind, damage, stun = 'none', 0, False
                if ability.is_attack_reset():
                    kind, stun = 'reset', getattr(info, 'enhanced_attack', False)
                elif ability.is_dash():
                    kind = 'dash'
                elif ability.is_damage() or ability.is_cc() or ability.is_aoe_damage():
                    kind, damage, stun = 'damage', ability.damage_amount(), ability.is_cc()
                elif ability.is_shield():
                    kind, damage = 'shield', ability.shield_amount()
                spells.append((kind, ability.cooldown(), getattr(info, 'range', 0), damage,
                               stun, getattr(info, 'exclusive_with_movement', False)))
            buffs = unit.buffs()
            shield = sum(buff.value for buff in buffs if buff.kind == cambc.BuffTypes.SHIELD)
            return dict(strength=safe_strength(unit), range=safe_attack_range(unit),
                        speed=unit.base_stats().base_move_speed, spells=spells,
                        health=safe_health(unit) + shield,
                        immune=unit.passive() == cambc.PassiveType.STUN_IMMUNITY,
                        stunned=buffs.has_stun() and not unit.has_completed_turn())
        except Exception:
            return dict(strength=0, range=1, speed=1, spells=[], health=0, immune=False, stunned=False)

    def combat_turn(self):
        me = cambc.me()
        if not me.is_alive():
            return False
        enemies = safe_visible_enemies()
        if not enemies:
            return False
        origin = safe_position(me)
        if origin is None:
            return False
        min_dist = min((distance(origin, safe_position(e)) for e in enemies), default=999)
        if min_dist > 6:
            return False

        # Run combat planner to evaluate burst and incoming damage
        if cambc.fuel_remaining() > 700000 and len(enemies) <= 5:
            try:
                ours = self.fighter(me)
                foes = [self.fighter(e) for e in enemies if safe_is_visible(e)]
                gaps = [distance(origin, safe_position(e)) for e in enemies if safe_is_visible(e)]
                if len(foes) == len(enemies):
                    for target_idx in range(len(enemies)):
                        for cast_idx in (-1, 0, 1):
                            if cast_idx >= 0:
                                ability = me.abilities()[cast_idx]
                                if not ability.is_ready() or ability.is_dash():
                                    continue
                            outgoing, incoming, first = exchange(ours, foes, gaps, target_idx, cast_idx, False)
                            self.plan_count += 1
            except Exception:
                pass

        # 1. Immediate in-range defense / opportunity: if any enemy is in attack or spell range, fight!
        # Pre-attack spells: shield or CC
        if me.can_cast() and origin == self.turn_origin:
            for ability in me.abilities():
                if not ability.is_ready():
                    continue
                if ability.is_shield() and min_dist <= 3:
                    try:
                        ability.use(me)
                    except Exception:
                        pass
                    break
                if ability.is_cc():
                    cc_targets = [e for e in enemies if safe_is_visible(e)
                                  and distance(origin, safe_position(e)) <= getattr(ability.info(), 'range', 0)
                                  and e.passive() != cambc.PassiveType.STUN_IMMUNITY
                                  and not e.buffs().has_stun()]
                    if cc_targets:
                        best_cc = max(cc_targets, key=lambda e: (safe_is_submitting_gems(e), safe_gem_count(e), safe_strength(e)))
                        try:
                            best_cc_pos = safe_position(best_cc)
                            ability.use(best_cc if ability.can_target_enemies() else best_cc_pos)
                            attack_if_in_range(best_cc)
                            if ability.info().exclusive_with_movement and not me.can_attack():
                                return True
                        except Exception:
                            pass
                        break
                elif ability.is_damage() or ability.is_aoe_damage():
                    dmg_targets = [e for e in enemies if safe_is_visible(e)
                                   and distance(origin, safe_position(e)) <= getattr(ability.info(), 'range', 0)]
                    if dmg_targets:
                        best_dmg = min(dmg_targets, key=lambda e: safe_health(e))
                        try:
                            best_dmg_pos = safe_position(best_dmg)
                            ability.use(best_dmg if ability.can_target_enemies() else best_dmg_pos)
                            attack_if_in_range(best_dmg)
                            if ability.info().exclusive_with_movement and not me.can_attack():
                                return True
                        except Exception:
                            pass
                        break

        # Re-query visible enemies after any casts
        enemies = safe_visible_enemies()
        if not enemies:
            return False
        in_attack_range = [e for e in enemies if safe_is_visible(e) and distance(me.position(), safe_position(e)) <= me.attack_range()]

        # If any enemy is in attack range, strike them!
        if in_attack_range:
            # Kit-aware Varg splash usage: pick target that maximizes splash on other in-range enemies
            if me.champion_name() == cambc.ChampionType.VARG and len(in_attack_range) > 1:
                def splash_score(e):
                    e_pos = safe_position(e)
                    return sum(1 for o in in_attack_range if o != e and distance(e_pos, safe_position(o)) <= 1)
                target = max(in_attack_range, key=lambda e: (splash_score(e), safe_is_submitting_gems(e), safe_gem_count(e) * 4, -safe_health(e)))
            else:
                target = max(in_attack_range, key=lambda e: (safe_is_submitting_gems(e), safe_gem_count(e) * 4, -safe_health(e)))
            near_altar = min(distance(me.position(), a) for a in self.altars) <= 1
            if safe_gem_count(target) > 0 or safe_is_submitting_gems(target) or near_altar or me.gem_count() == 0:
                if attack_if_in_range(target):
                    return True

        # 2. For non-carriers: if an enemy carrier or submitting enemy or close enemy is nearby, close in and attack!
        if me.gem_count() == 0 and safe_health(me) >= safe_max_health(me) * 0.4:
            priority_targets = [e for e in enemies if safe_is_visible(e) and (safe_is_submitting_gems(e) or safe_gem_count(e) > 0 or distance(me.position(), safe_position(e)) <= 4)]
            if priority_targets:
                target = max(priority_targets, key=lambda e: (safe_is_submitting_gems(e), safe_gem_count(e) * 4, -safe_health(e), -distance(me.position(), safe_position(e))))
                t_pos = safe_position(target)
                if t_pos:
                    reach = max(1, me.attack_range())
                    if distance(me.position(), t_pos) > reach:
                        goals = tiles_around(t_pos, reach)
                        move_towards_closest(goals)
                if safe_is_visible(target):
                    if attack_if_in_range(target):
                        return True
                for e in safe_visible_enemies():
                    if attack_if_in_range(e):
                        return True
                return True

        # If carrier or low health and enemy is close, retreat to safety
        cur_pos = safe_position(me)
        if cur_pos and (me.gem_count() > 0 or safe_health(me) < safe_max_health(me) * 0.4):
            if any(safe_is_visible(e) and distance(cur_pos, safe_position(e)) <= safe_attack_range(e) + 1 for e in safe_visible_enemies()):
                self.retreat()
                return True
        return False

    def observe_enemies(self):
        now = cambc.round_number()
        self.enemies = {key: value for key, value in self.enemies.items()
                        if now - value[1] <= 8}
        for enemy in safe_visible_enemies():
            try:
                pos = safe_position(enemy)
                if pos:
                    self.enemies[int(enemy)] = (pos, now, safe_strength(enemy),
                                                safe_attack_range(enemy), enemy.focus())
            except Exception:
                pass
        self.camp_threats = []
        for camp in safe_camps():
            try:
                pos = safe_position(camp)
                if pos:
                    self.camp_threats.append((pos, safe_strength(camp), safe_attack_range(camp)))
            except Exception:
                pass

    def danger(self, tile, turns=1):
        # Allow one step per round plus a two-step dash/burst reserve. Old sightings
        # spread out, then expire; they never make a unit legal to target.
        now = cambc.round_number()
        damage = 0
        for position, seen, strength, attack_range, focus in self.enemies.values():
            arrival = max(0, distance(tile, position) - attack_range - (now - seen) - 2)
            hits = max(0, turns - arrival)
            if hits:
                damage += hits * strength + focus * 2
        return damage

    def enemy_zones(self):
        zones = cambc.Bitboard()
        for enemy in safe_visible_enemies():
            try:
                reach = safe_attack_range(enemy) + enemy.base_stats().base_move_speed
                for ability in enemy.abilities():
                    if ability.cooldown() <= 1:
                        if ability.is_dash():
                            reach = max(reach, safe_attack_range(enemy) + int(getattr(ability.info(), 'range', 0)) + 1)
                        elif ability.is_cc() or ability.is_damage() or ability.is_aoe_damage():
                            reach = max(reach, int(getattr(ability.info(), 'range', 0)) + 1)
                pos = safe_position(enemy)
                if pos:
                    zones |= tiles_around(pos, reach)
            except Exception:
                pass
        return zones

    def channel_damage(self, tile, turns):
        return self.danger(tile, turns) + turns * sum(
            strength for position, strength, radius in self.camp_threats
            if distance(tile, position) <= radius)

    def retreat(self):
        me = cambc.me()
        if not me.is_alive():
            return
        origin = safe_position(me)
        if origin is None:
            return

        def exposure(tile):
            return self.channel_damage(tile, 2)

        enemies = safe_visible_enemies()
        enemy_info = []
        for e in enemies:
            try:
                pos = safe_position(e)
                if pos and distance(origin, pos) <= 8:
                    enemy_info.append((pos, safe_attack_range(e), e))
            except Exception:
                pass

        # Never start an interruptible recall if enemies are nearby or under camp attack!
        if not enemy_info and exposure(origin) == 0:
            try:
                me.recall()
            except Exception:
                pass
            return

        # 1. Defensive abilities before moving: shield or CC
        for ability in me.abilities():
            if not ability.is_ready():
                continue
            if ability.is_shield():
                try:
                    ability.use(me)
                except Exception:
                    pass
                break
            if ability.is_cc() and origin == self.turn_origin:
                targets = [e for p, r, e in enemy_info
                           if safe_is_visible(e) and safe_is_alive(e)
                           and distance(origin, p) <= getattr(ability.info(), 'range', 0)
                           and e.passive() != cambc.PassiveType.STUN_IMMUNITY
                           and not e.buffs().has_stun()]
                if targets:
                    target = max(targets, key=lambda e: safe_strength(e))
                    try:
                        t_pos = safe_position(target)
                        ability.use(target if ability.can_target_enemies() else t_pos)
                        attack_if_in_range(target)
                        if ability.info().exclusive_with_movement:
                            return
                    except Exception:
                        pass
                    break

        # 2. Dash to escape: choose landing that maximizes distance to closest enemy
        for ability in me.abilities():
            if ability.is_dash() and ability.is_ready():
                try:
                    blocked = blocked_tiles()
                    transit = blocked & ~game_map.holes()
                    landings = transit.reachable_tiles(origin, int(ability.info().range)) & ~blocked
                    landings &= ~game_map.spawn_region(Team.ENEMY)
                    choices = [origin, *landings.positions()]
                    if enemy_info:
                        cur_min = min(distance(origin, p) for p, r, e in enemy_info)
                        def dash_score(tile):
                            e_dist = min(distance(tile, p) for p, r, e in enemy_info)
                            c_threat = sum(s for p, s, r in self.camp_threats if distance(tile, p) <= r)
                            return (e_dist, -c_threat)
                        best_landing = max(choices, key=dash_score)
                        if min(distance(best_landing, p) for p, r, e in enemy_info) > cur_min:
                            if ability.use(best_landing):
                                origin = safe_position(me) or origin
                                break
                    else:
                        landing = min(choices, key=exposure)
                        if exposure(landing) < exposure(origin) and ability.use(landing):
                            origin = safe_position(me) or origin
                            break
                except Exception:
                    pass

        # 3. Walk to flee: step away from enemies, avoid standing in enemy attack ranges
        if me.can_move():
            try:
                blocked = blocked_tiles()
                reachable = [origin, *blocked.reachable_tiles(origin, me.base_stats().base_move_speed).positions()]
                if enemy_info:
                    def flee_step_score(tile):
                        in_range = any(distance(tile, p) <= r for p, r, e in enemy_info)
                        in_walk_range = any(distance(tile, p) <= r + 1 for p, r, e in enemy_info)
                        min_dist = min(distance(tile, p) for p, r, e in enemy_info)
                        danger_pen = (1000 if in_range else (300 if in_walk_range else 0)) - min_dist * 25
                        goal_dist = (min(distance(tile, a) for a in self.altars) if me.gem_count() > 0
                                     else min(distance(tile, s) for s in game_map.spawn_region(Team.ALLY).positions()[:4]))
                        return danger_pen + goal_dist + exposure(tile)
                    step = min(reachable, key=flee_step_score)
                    if step != origin and not blocked.is_set(step):
                        safe_move(step)
                else:
                    field = cambc.DistanceField()
                    field.compute(blocked, game_map.spawn_region(Team.ALLY) & ~blocked, cambc.Bitboard())
                    wards = me.ward_positions()
                    step = min(reachable, key=lambda tile: (exposure(tile),
                               0 if wards and distance(tile, wards[0]) <= 6 else 1, field.get(tile)))
                    if step != origin and not blocked.is_set(step):
                        safe_move(step)
            except Exception:
                pass

        # 4. Defend with basic attack / reset if enemy is in range
        for enemy in safe_visible_enemies():
            if attack_if_in_range(enemy):
                break

    def bank(self):
        me = cambc.me()
        if not me.is_alive():
            return
        origin = safe_position(me)
        if origin is None:
            return
        duration = max(cambc.constants.SUBMIT_GEM_MINIMUM_DURATION,
                       ceil(me.gem_count() * cambc.constants.SUBMIT_GEM_DURATION_MULTIPLIER
                            + cambc.constants.SUBMIT_GEM_BASE_DURATION))
        altars = sorted(self.altars, key=lambda altar: distance(origin, altar))
        enemy_locks = cambc.vision.altar_lock_tiles(Team.ENEMY)

        blocked = blocked_tiles()
        field, reached = cambc.DistanceField(), cambc.Bitboard()
        try:
            field.compute(blocked, tiles_around(origin, 0), reached)
        except Exception:
            return
        options = []
        for altar in altars:
            if enemy_locks.is_set(altar):
                continue
            approaches = tiles_around(altar, cambc.constants.SUBMIT_GEMS_RANGE) & reached & ~blocked
            if approaches.is_empty():
                continue
            tile = min(approaches.positions(), key=field.get)
            travel = field.get(tile)
            risk = self.channel_damage(tile, duration + min(travel, 4))
            inertia = -4 if altar == self.bank_altar else 0
            options.append((travel + risk / max(1, me.strength()) + inertia, tile, altar))
        if not options:
            lock_tiles = cambc.vision.altar_lock_tiles(Team.ENEMY)
            if not lock_tiles.is_empty():
                target_altar = min(lock_tiles.positions(), key=lambda a: distance(origin, a))
                if cambc.vision.has_altar_lock(target_altar):
                    try:
                        lock = cambc.vision.altar_lock_at(target_altar)
                        if me.can_attack() and distance(origin, target_altar) <= me.attack_range():
                            attack_if_in_range(lock)
                            return
                    except Exception:
                        pass
                move_towards_closest(tiles_around(target_altar, 1))
                return
            self.retreat()
            return
        _, tile, altar = min(options, key=lambda option: option[0])
        self.bank_altar = altar

        # Place altar lock if we have one within range 2
        try:
            lock = me.consumables()[cambc.ConsumableType.ALTAR_LOCK]
            if (lock.count() > 0 and distance(origin, altar) <= 2
                    and not cambc.vision.has_altar_lock(altar)
                    and not any(safe_is_submitting_gems(ally) and distance(safe_position(ally), altar) <= 1
                                for ally in safe_visible_allies())):
                lock.use(altar)
        except Exception:
            pass

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
            # Keep a useful sentry instead of replacing it every time the charge returns.
            if me.ward_cooldown() or (wards and distance(wards[0], my_pos) <= 6):
                return
            candidates = (me.ward_placement_tiles() & ~blocked_tiles()
                          & ~cambc.vision.ward_tiles(Team.ALLY))
            candidates.set(my_pos, False)
            if candidates.is_empty():
                return
            altars = self.altars
            bushes = game_map.bushes()
            def ward_score(t):
                altar_dist = min(distance(t, a) for a in altars)
                bush_bonus = 10 if bushes.is_set(t) else 0
                return bush_bonus - altar_dist + distance(t, my_pos)
            best = max(candidates.positions(), key=ward_score)
            me.place_ward(best)
        except Exception:
            pass

    def buy_items(self):
        me = cambc.me()
        if not me.is_alive():
            return
        try:
            lock_type = cambc.ConsumableType.ALTAR_LOCK
            lock = me.consumables()[lock_type]
            has_lock = lock.count() > 0
            if not has_lock and me.can_buy(lock_type):
                me.buy(lock_type)
                has_lock = True

            champ = me.champion_name()
            item = Item.POWER_SHARD_OF_FOCUS if champ in (cambc.ChampionType.TAVI, cambc.ChampionType.CASSI) else Item.POWER_SHARD_OF_STRENGTH
            reserve = 0 if has_lock else 10
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
        except Exception:
            pass

    def _do_play_turn(self):
        me = cambc.me()
        if not me.is_alive():
            return
        origin = safe_position(me)
        if origin is None:
            return
        self.turn_origin = origin
        self.observe_enemies()
        self.buy_items()
        if not me.is_alive() or me.is_recalling() or me.is_teleporting():
            return
        if me.is_submitting_gems():
            try:
                if self.channel_damage(origin, me.remaining_channel_time() + 1) < safe_health(me) * 0.85:
                    return
                me.cancel_submit_gems()
                self.retreat()
            except Exception:
                pass
            return
        if not me.can_move() and not me.can_attack() and not me.can_cast():
            return

        self.place_ward()
        self.observe_enemies()

        at_spawn = game_map.spawn_region(Team.ALLY).is_set(origin)
        # Recall arrival precedes spawn healing at turn end; do not leave wounded.
        if at_spawn and safe_health(me) < safe_max_health(me):
            return

        if self.combat_turn():
            return

        enemies = safe_visible_enemies()
        close_enemies = [e for e in enemies if distance(origin, safe_position(e)) <= 8]
        near_altar = min(distance(origin, a) for a in self.altars) <= 2
        immediate_threat = any(distance(origin, safe_position(e)) <= safe_attack_range(e) + 1 for e in close_enemies)
        threatened_carrier = me.gem_count() > 0 and not near_altar and (safe_health(me) < safe_max_health(me) * 0.45 or immediate_threat)

        if threatened_carrier:
            self.retreat()
            return

        threshold = 0.6 if (me.gem_count() >= 40 and close_enemies) else 0.35
        if not at_spawn and safe_health(me) < safe_max_health(me) * threshold:
            self.retreat()
            return

        # Banking logic:
        team_gems = cambc.global_submitted_gems(Team.ALLY)
        winning_bag = me.gem_count() > 0 and (team_gems + me.gem_count() >= 1000)
        altar_dist = min(distance(origin, a) for a in self.altars)
        bank_threshold = 20 if (close_enemies or altar_dist <= 8) else 40
        should_bank = (me.gem_count() >= bank_threshold or
                       (me.gem_count() > 0 and (near_altar or winning_bag or safe_health(me) < safe_max_health(me) * 0.6)))
        if should_bank:
            self.bank()
            return
        self.bank_altar = None

        # Attack the first enemy champion already in range.
        for enemy in enemies:
            if attack_if_in_range(enemy):
                return

        self.farm_camps()

        try:
            me.set_priority(1 + below(100))
        except Exception:
            pass
