"""Champion decisions. main.py dispatches here after the draft."""
from math import ceil
from randomness import below

import cambc
from cambc import game_map
from combat import exchange

Team, Item = cambc.Team, cambc.ItemType


def distance(a, b):
    return a.chebyshev_distance(b)


def tiles_around(position, radius):
    tiles = cambc.Bitboard()
    tiles.draw_chebyshev(position, radius)
    return tiles


def blocked_tiles():
    # Combine terrain and visible occupants using native bitboard operations.
    blocked = (game_map.walls() | game_map.holes() | game_map.altars()
               | game_map.spawn_region(Team.ENEMY) | cambc.vision.champion_tiles()
               | cambc.vision.camp_tiles() | cambc.vision.teleport_tiles()
               | cambc.vision.ward_tiles())
    blocked.set(cambc.me().position(), False)
    return blocked


def safe_move(tile):
    me = cambc.me()
    if not me.can_move():
        return False
    try:
        return me.move_absolute(tile)
    except Exception:
        return False


def move_towards_closest(goals, avoid=None):
    me = cambc.me()
    origin = me.position()
    goals = goals.copy()  # Map/group masks are cached; never trim their source tiles.
    if not me.can_move() or goals.is_set(origin):
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
    field.compute_to(blocked & ~goals, goals, tiles_around(origin, 0), cambc.Bitboard())

    # Dash legality differs from walking: holes can be crossed but not landed on.
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

    # Choose a reachable step with a smaller distance to the goal.
    if not me.can_move():
        return False
    blocked = blocked_tiles()
    if avoid is not None:
        blocked |= avoid
        blocked.set(origin, False)
    reachable = blocked.reachable_tiles(origin, me.base_stats().base_move_speed)
    step = min([origin, *reachable.positions()], key=field.get)
    if step == origin or blocked.is_set(step):
        return False
    return safe_move(step)


def attack_if_in_range(target):
    # Kit introspection also handles random drafts and champions without a reset.
    me = cambc.me()
    if isinstance(target, cambc.Camp) and not cambc.vision.camp_tiles().is_set(target.spawn_position()):
        return False
    if (not me.can_attack() or not target.is_visible() or target.health() <= 0
            or not me.attack_tiles().is_set(target.position())):
        return False
    me.attack(target)
    alive = (cambc.vision.camp_tiles().is_set(target.spawn_position())
             if isinstance(target, cambc.Camp) else target.is_visible() and target.is_alive())
    if me.can_cast() and alive and target.health() > 0:
        for ability in me.abilities():
            if ability.is_attack_reset() and ability.is_ready():
                if not me.can_attack() and ability.use() and me.can_attack():
                    if target.is_visible() and target.health() > 0:
                        me.attack(target)
                break
    return True


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
        if not camp.is_visible() or not cambc.vision.camp_tiles().is_set(camp.spawn_position()):
            return False
        gap = distance(me.position(), camp.position())
        if me.position() == self.turn_origin and me.can_cast():
            for ability in me.abilities():
                if not ability.is_ready():
                    continue
                if (ability.is_damage() or ability.is_cc() or ability.is_aoe_damage()) and gap <= ability.info().range:
                    # A range-four spell can clear without standing in retaliation.
                    if ability.damage_amount() > me.strength() or gap > me.attack_range():
                        ability.use(camp if ability.can_target_camps() else camp.position())
                        attack_if_in_range(camp)
                        return True
                if ability.is_shield() and gap <= 3 and me.health() < me.max_health() * 0.75:
                    ability.use(me)
        return attack_if_in_range(camp)

    def farm_camps(self):
        me = cambc.me()
        now = cambc.round_number()
        visible = cambc.vision.visible_tiles()
        occupied_camps = cambc.vision.camp_tiles()
        # Finish an in-range member of the chosen group before rescoring routes.
        # This both avoids target thrashing and saves the Python turn's fuel.
        if self.group is not None:
            for camp in self.group:
                if self.farm_attack(camp):
                    return
        allies = [a for a in cambc.vision.champions(Team.ALLY) if a.is_visible()]
        blocked = blocked_tiles()
        field, reached = cambc.DistanceField(), cambc.Bitboard()
        field.compute(blocked, tiles_around(me.position(), 0), reached)
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
            capturers = [ally for ally in allies if region.is_set(ally.position())]
            if capturing and capturers:
                # Extra allies do not accelerate capture and would split the reward.
                if min(int(ally) for ally in capturers) != int(me):
                    continue
                self.group = group
                return  # Stay until the observed reward/respawn transition, not 5 calls.

            camps = []
            for camp in group:
                stats = camp.base_stats()
                if camp.is_visible():
                    health = camp.health()
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

            # Budget with solo DPS: never assume leaving allies will help
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
            # Prioritize high gem value objectives (e.g. standalone gem clusters)
            value = (group.gem_value() * 1.5 + group.gold_value() * 0.1) / max(1, time)
            if group.gem_value() == 0:
                value *= 0.001
            risk = incoming + self.danger(approach, 3)
            if risk > me.health() - me.max_health() * 0.25:
                # Prefer complete safe clears.
                value *= 0.1 * me.health() / max(me.health(), risk)
            # Spread solo farmers; downweight groups closer to an ally
            for ally in allies:
                if ally != me and not ally.gem_count() and not ally.is_recalling():
                    ally_dist = distance(ally.position(), approach)
                    if ally_dist < travel or (ally_dist == travel and int(ally) < int(me)):
                        value *= 0.35
            # Finish the chosen group rather than bouncing between equal alternatives.
            if group == self.group:
                value *= 1.2
            if value > best_value:
                best, best_value = group, value
        self.group = best
        if best is None:
            return
        for camp in best:
            if self.farm_attack(camp):
                return
        goals = cambc.Bitboard()
        # A cleared member is not a capture objective until *every* member dies.
        for camp in best:
            tile = camp.spawn_position()
            if not visible.is_set(tile) or occupied_camps.is_set(tile):
                goals.set(tile)
        if goals.is_empty():
            goals = best.spawn_tiles()
        move_towards_closest(goals)
        for camp in best:
            if attack_if_in_range(camp):
                return

    def fighter(self, unit):
        spells = []
        for ability in unit.abilities():
            info = ability.info()
            kind, damage, stun = 'none', 0, False
            if ability.is_attack_reset():
                kind, stun = 'reset', info.enhanced_attack
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
        return dict(strength=unit.strength(), range=unit.attack_range(),
                    speed=unit.base_stats().base_move_speed, spells=spells,
                    health=unit.health() + shield,
                    immune=unit.passive() == cambc.PassiveType.STUN_IMMUNITY,
                    stunned=buffs.has_stun() and not unit.has_completed_turn())

    def combat_turn(self):
        me = cambc.me()
        enemies = [e for e in cambc.vision.champions(Team.ENEMY) if e.is_visible() and e.is_alive()]
        if not enemies:
            return False
        origin = me.position()
        min_dist = min(distance(origin, e.position()) for e in enemies)
        if min_dist > 6:
            return False

        # Run combat planner to evaluate burst and incoming damage
        if cambc.fuel_remaining() > 700000 and len(enemies) <= 5:
            ours = self.fighter(me)
            foes = [self.fighter(e) for e in enemies]
            gaps = [distance(origin, e.position()) for e in enemies]
            for target_idx in range(len(enemies)):
                for cast_idx in (-1, 0, 1):
                    if cast_idx >= 0:
                        ability = me.abilities()[cast_idx]
                        if not ability.is_ready() or ability.is_dash():
                            continue
                    outgoing, incoming, first = exchange(ours, foes, gaps, target_idx, cast_idx, False)
                    self.plan_count += 1

        # 1. Immediate in-range defense / opportunity: if any enemy is in attack or spell range, fight!
        in_attack_range = [e for e in enemies if me.attack_tiles().is_set(e.position())]
        submitting_enemies = [e for e in enemies if e.is_submitting_gems()]

        # Pre-attack spells: shield if threatened, or CC an enemy
        if me.can_cast() and origin == self.turn_origin:
            for ability in me.abilities():
                if not ability.is_ready():
                    continue
                if ability.is_shield() and min_dist <= 3:
                    ability.use(me)
                    break
                if ability.is_cc():
                    cc_targets = [e for e in enemies if distance(origin, e.position()) <= ability.info().range
                                  and e.passive() != cambc.PassiveType.STUN_IMMUNITY and not e.buffs().has_stun()]
                    if cc_targets:
                        best_cc = max(cc_targets, key=lambda e: (e.is_submitting_gems(), e.gem_count(), e.strength()))
                        ability.use(best_cc if ability.can_target_enemies() else best_cc.position())
                        attack_if_in_range(best_cc)
                        if ability.info().exclusive_with_movement and not me.can_attack():
                            return True
                        break
                elif (ability.is_damage() or ability.is_aoe_damage()):
                    dmg_targets = [e for e in enemies if distance(origin, e.position()) <= ability.info().range]
                    if dmg_targets:
                        best_dmg = min(dmg_targets, key=lambda e: e.health())
                        ability.use(best_dmg if ability.can_target_enemies() else best_dmg.position())
                        attack_if_in_range(best_dmg)
                        if ability.info().exclusive_with_movement and not me.can_attack():
                            return True
                        break

        # If any enemy is in attack range, strike them!
        if in_attack_range:
            target = max(in_attack_range, key=lambda e: (e.is_submitting_gems(), e.gem_count() * 4, -e.health()))
            attack_if_in_range(target)
            near_altar = min(distance(origin, a) for a in self.altars) <= 1
            if me.gem_count() > 0 and not near_altar and me.health() < me.max_health() * 0.4:
                self.retreat()
            return True

        # 2. For non-carriers: if an enemy carrier or submitting enemy or close enemy is nearby, close in and attack!
        if me.gem_count() == 0 and me.health() >= me.max_health() * 0.4:
            priority_targets = [e for e in enemies if e.is_visible() and (e.is_submitting_gems() or e.gem_count() > 0 or distance(me.position(), e.position()) <= 4)]
            if priority_targets:
                target = max(priority_targets, key=lambda e: (e.is_submitting_gems(), e.gem_count() * 4, -e.health(), -distance(me.position(), e.position())))
                reach = max(1, me.attack_range())
                if distance(me.position(), target.position()) > reach:
                    goals = tiles_around(target.position(), reach)
                    move_towards_closest(goals)
                if attack_if_in_range(target):
                    return True
                for e in enemies:
                    if attack_if_in_range(e):
                        return True
                return True

        # If carrier or low health and enemy is close, retreat to safety
        cur_pos = me.position()
        if (me.gem_count() > 0 or me.health() < me.max_health() * 0.4):
            if any(e.is_visible() and distance(cur_pos, e.position()) <= e.attack_range() + 1 for e in enemies):
                self.retreat()
                return True
        return False

    def observe_enemies(self):
        now = cambc.round_number()
        self.enemies = {key: value for key, value in self.enemies.items()
                        if now - value[1] <= 8}
        for enemy in cambc.vision.champions(Team.ENEMY):
            if not enemy.is_visible():
                continue
            self.enemies[int(enemy)] = (enemy.position(), now, enemy.strength(),
                                        enemy.attack_range(), enemy.focus())
        self.camp_threats = [(camp.position(), camp.strength(), camp.attack_range())
                            for camp in cambc.vision.camps()]

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
        for enemy in cambc.vision.champions(Team.ENEMY):
            if not enemy.is_visible():
                continue
            reach = enemy.attack_range() + enemy.base_stats().base_move_speed
            for ability in enemy.abilities():
                if ability.cooldown() <= 1:
                    if ability.is_dash():
                        reach = max(reach, enemy.attack_range() + int(ability.info().range) + 1)
                    elif ability.is_cc() or ability.is_damage() or ability.is_aoe_damage():
                        reach = max(reach, int(ability.info().range) + 1)
            zones |= tiles_around(enemy.position(), reach)
        return zones

    def channel_damage(self, tile, turns):
        return self.danger(tile, turns) + turns * sum(
            strength for position, strength, radius in self.camp_threats
            if distance(tile, position) <= radius)

    def retreat(self):
        me = cambc.me()
        origin = me.position()

        def exposure(tile):
            return self.channel_damage(tile, 2)

        enemies = cambc.vision.champions(Team.ENEMY)
        enemy_info = [(e.position(), e.attack_range(), e) for e in enemies
                      if e.is_visible() and distance(origin, e.position()) <= 8]

        # Never start an interruptible recall if enemies are nearby or under camp attack!
        if not enemy_info and exposure(origin) == 0:
            me.recall()
            return

        # 1. Defensive abilities before moving: shield or CC
        for ability in me.abilities():
            if not ability.is_ready():
                continue
            if ability.is_shield():
                ability.use(me)
                break
            if ability.is_cc() and origin == self.turn_origin:
                targets = [e for p, r, e in enemy_info
                           if e.is_visible() and e.is_alive()
                           and distance(origin, p) <= ability.info().range
                           and e.passive() != cambc.PassiveType.STUN_IMMUNITY
                           and not e.buffs().has_stun()]
                if targets:
                    target = max(targets, key=lambda e: e.strength())
                    ability.use(target if ability.can_target_enemies() else target.position())
                    attack_if_in_range(target)
                    if ability.info().exclusive_with_movement:
                        return
                    break

        # 2. Dash to escape: choose landing that maximizes distance to closest enemy
        for ability in me.abilities():
            if ability.is_dash() and ability.is_ready():
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
                            origin = me.position()
                            break
                else:
                    landing = min(choices, key=exposure)
                    if exposure(landing) < exposure(origin) and ability.use(landing):
                        origin = me.position()
                        break

        # 3. Walk to flee: step away from enemies, avoid standing in enemy attack ranges
        if me.can_move():
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

        # 4. Defend with basic attack / reset if enemy is in range
        for enemy in [e for e in cambc.vision.champions(Team.ENEMY) if e.is_visible()]:
            if attack_if_in_range(enemy):
                break

    def bank(self):
        me = cambc.me()
        duration = max(cambc.constants.SUBMIT_GEM_MINIMUM_DURATION,
                       ceil(me.gem_count() * cambc.constants.SUBMIT_GEM_DURATION_MULTIPLIER
                            + cambc.constants.SUBMIT_GEM_BASE_DURATION))
        origin = me.position()
        altars = sorted(self.altars, key=lambda altar: distance(origin, altar))
        enemy_locks = cambc.vision.altar_lock_tiles(Team.ENEMY)

        blocked = blocked_tiles()
        field, reached = cambc.DistanceField(), cambc.Bitboard()
        field.compute(blocked, tiles_around(origin, 0), reached)
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
            locks = cambc.vision.altar_locks(Team.ENEMY)
            if locks:
                lock = min(locks, key=lambda l: distance(origin, l.position()))
                if me.can_attack() and me.attack_tiles().is_set(lock.position()):
                    me.attack(lock)
                    if me.can_cast():
                        for a in me.abilities():
                            if a.is_attack_reset() and a.is_ready():
                                if a.use() and me.can_attack():
                                    me.attack(lock)
                                break
                    return
                else:
                    move_towards_closest(tiles_around(lock.position(), 1))
            else:
                self.retreat()
            return
        _, tile, altar = min(options, key=lambda option: option[0])
        self.bank_altar = altar

        # Place altar lock if we have one within range 2
        lock = me.consumables()[cambc.ConsumableType.ALTAR_LOCK]
        if (lock.count() > 0 and distance(origin, altar) <= 2
                and not cambc.vision.has_altar_lock(altar)
                and not any(ally.is_submitting_gems() and distance(ally.position(), altar) <= 1
                            for ally in cambc.vision.champions(Team.ALLY) if ally.is_visible())):
            lock.use(altar)

        # Check if we can submit
        if distance(origin, altar) <= cambc.constants.SUBMIT_GEMS_RANGE:
            is_marcella = (me.champion_name() == cambc.ChampionType.MARCELLA or
                           me.passive() == cambc.PassiveType.STUN_IMMUNITY)
            # Only visible enemies close enough to hit/stun us during the channel are actual threats
            visible_threats = [e for e in cambc.vision.champions(Team.ENEMY) if e.is_visible()]
            lethal = False
            stun_threat = False
            for e in visible_threats:
                d = distance(origin, e.position())
                if d <= e.attack_range() + 2:
                    if e.strength() * min(duration, 5) >= me.health():
                        lethal = True
                if not is_marcella and d <= 4:
                    if any(a.is_cc() or (a.is_attack_reset() and a.info().enhanced_attack)
                           for a in e.abilities() if a.is_ready()):
                        stun_threat = True

            safe = not lethal and not stun_threat
            if safe and cambc.round_number() + duration <= cambc.constants.MAX_ROUNDS:
                me.submit_gems(altar)
                return
            close_foes = [e for e in visible_threats if distance(origin, e.position()) <= me.attack_range()]
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
        if me.restrictions() & cambc.BuffRestrictions.WARD:
            return
        wards = me.ward_positions()
        # Keep a useful sentry instead of replacing it every time the charge returns.
        if me.ward_cooldown() or (wards and distance(wards[0], me.position()) <= 6):
            return
        # The SDK's placement mask is range-only, not a complete legality mask.
        candidates = (me.ward_placement_tiles() & ~blocked_tiles()
                      & ~cambc.vision.ward_tiles(Team.ALLY))
        candidates.set(me.position(), False)
        if candidates.is_empty():
            return
        altars = self.altars
        bushes = game_map.bushes()
        origin = me.position()
        def ward_score(t):
            altar_dist = min(distance(t, a) for a in altars)
            bush_bonus = 10 if bushes.is_set(t) else 0
            return bush_bonus - altar_dist + distance(t, origin)
        best = max(candidates.positions(), key=ward_score)
        try:
            me.place_ward(best)
        except Exception:
            pass

    def buy_items(self):
        me = cambc.me()
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

    def play_turn(self):
        me = cambc.me()
        self.turn_origin = me.position() if me.is_alive() else None
        self.observe_enemies()
        self.buy_items()
        if not me.is_alive() or me.is_recalling() or me.is_teleporting():
            return
        if me.is_submitting_gems():
            if self.channel_damage(me.position(), me.remaining_channel_time() + 1) < me.health() * 0.85:
                return
            me.cancel_submit_gems()
            self.retreat()
            return
        if not me.can_move() and not me.can_attack():
            return

        self.place_ward()
        self.observe_enemies()

        at_spawn = game_map.spawn_region(Team.ALLY).is_set(me.position())
        # Recall arrival precedes spawn healing at turn end; do not leave wounded.
        if at_spawn and me.health() < me.max_health():
            return

        if self.combat_turn():
            return

        enemies = [e for e in cambc.vision.champions(Team.ENEMY) if e.is_visible()]
        close_enemies = [e for e in enemies if distance(me.position(), e.position()) <= 8]
        near_altar = min(distance(me.position(), a) for a in self.altars) <= 2
        immediate_threat = any(distance(me.position(), e.position()) <= e.attack_range() + 1 for e in close_enemies)
        threatened_carrier = me.gem_count() > 0 and not near_altar and (me.health() < me.max_health() * 0.45 or immediate_threat)

        if threatened_carrier:
            self.retreat()
            return

        threshold = 0.6 if (me.gem_count() >= 40 and close_enemies) else 0.35
        if not at_spawn and me.health() < me.max_health() * threshold:
            self.retreat()
            return

        # Banking logic:
        team_gems = cambc.global_submitted_gems(Team.ALLY)
        winning_bag = me.gem_count() > 0 and (team_gems + me.gem_count() >= 1000)
        altar_dist = min(distance(me.position(), a) for a in self.altars)
        bank_threshold = 20 if (close_enemies or altar_dist <= 8) else 40
        should_bank = (me.gem_count() >= bank_threshold or
                       (me.gem_count() > 0 and (near_altar or winning_bag or me.health() < me.max_health() * 0.6)))
        if should_bank:
            self.bank()
            return
        self.bank_altar = None

        # Attack the first enemy champion already in range.
        for enemy in enemies:
            if attack_if_in_range(enemy):
                return

        self.farm_camps()

        me.set_priority(1 + below(100))
