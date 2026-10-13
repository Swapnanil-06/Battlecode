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
               | cambc.vision.camp_tiles() | cambc.vision.teleport_tiles())
    blocked.set(cambc.me().position(), False)
    return blocked


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
    dashed = False
    for ability in me.abilities():
        if ability.is_dash() and ability.is_ready():
            transit = blocked & ~game_map.holes()
            landings = transit.reachable_tiles(origin, int(ability.info().range)) & ~blocked
            choices = [origin, *landings.positions()]
            landing = min(choices, key=field.get)
            if field.get(landing) + 1 < field.get(origin) and ability.use(landing):
                dashed = True
                origin = me.position()
                blocked = blocked_tiles()
                if avoid is not None:
                    blocked |= avoid
                    blocked.set(origin, False)
                break

    # Choose a reachable step with a smaller distance to the goal.
    reachable = blocked.reachable_tiles(origin, me.base_stats().base_move_speed)
    step = min([origin, *reachable.positions()], key=field.get)
    walked = step != origin and me.can_move() and me.move_absolute(step)
    return walked or dashed


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
                if ability.use() and me.can_attack():
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
        allies = cambc.vision.champions(Team.ALLY)
        blocked = blocked_tiles()
        field, reached = cambc.DistanceField(), cambc.Bitboard()
        field.compute(blocked, tiles_around(me.position(), 0), reached)
        best, best_value = None, -1
        nearby = sorted((group for group in self.groups
                         if self.respawns.get(int(group), 0) <= now), key=lambda group:
                        distance(me.position(), group.camps()[0].spawn_position()))
        candidates = ([self.group] if self.group is not None else []) + nearby[:8]
        for group in candidates:
            # Keep enough fuel for pathing and actions; never resume a stale plan.
            if cambc.fuel_remaining() < 1200000:
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
                if occupied_camps.is_set(camp.spawn_position()):
                    health = camp.health()
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

            # Budget the whole connected group, reducing retaliation as members die.
            # The SDK exposes the champion's PvE multiplier; raw Strength is not DPS.
            dps = me.strength() * me.base_stats().camp_damage_multiplier
            for ally in allies:
                if ally != me and distance(ally.position(), me.position()) <= 4:
                    dps += ally.strength() * ally.base_stats().camp_damage_multiplier
            incoming, clear_turns = 0, 0
            remaining = sum(strength for _, _, strength in camps)
            for camp, health, strength in sorted(camps, key=lambda entry: entry[1]):
                turns = ceil(health / max(1, dps))
                incoming += turns * remaining
                clear_turns += turns
                remaining -= strength
            bank_travel = min(distance(approach, altar) for altar in game_map.altars().positions())
            time = travel + clear_turns + cambc.constants.CAPTURE_TIME + 1 + bank_travel
            time += ceil(group.gem_value() / 10)
            value = (group.gem_value() + group.gold_value() * 0.12) / max(1, time)
            risk = incoming + self.danger(approach, 3)
            if risk > me.health() - me.max_health() * 0.25:
                # Prefer complete safe clears. On all-elk maps there may be none;
                # retain a slow fallback instead of waiting forever at spawn.
                value *= 0.1 * me.health() / max(me.health(), risk)
            solo_damage = incoming * dps / max(1, me.strength() * me.base_stats().camp_damage_multiplier)
            if solo_damage < me.health() * 0.75:
                our_claim = (distance(me.position(), approach), int(me))
                if any(ally != me and not ally.gem_count() and not ally.is_recalling()
                       and (distance(ally.position(), approach), int(ally)) < our_claim
                       for ally in allies):
                    # Spread solo farmers; keep co-operation for groups that need it.
                    value *= 0.35
            # Finish the chosen group rather than bouncing between equal alternatives.
            if group == self.group:
                value *= 1.2
            if value > best_value:
                best, best_value = group, value
        self.group = best
        if best is None:
            # Vacate claimed regions so they can respawn; recover if no safe clear exists.
            if not game_map.spawn_region(Team.ALLY).is_set(me.position()):
                self.retreat()
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
        enemies = cambc.vision.champions(Team.ENEMY)
        if not enemies or min(distance(me.position(), e.position()) for e in enemies) > 6:
            return False
        # Snapshot once, then evaluate at most two targets, two positions and three
        # casts. No full-map search, no SDK queries inside the exchange rollout.
        if cambc.fuel_remaining() < 1600000:
            self.retreat()
            return True
        ours = self.fighter(me)
        foes = [self.fighter(enemy) for enemy in enemies]
        positions = [enemy.position() for enemy in enemies]
        origin = me.position()
        blocked = blocked_tiles()
        steps = [origin, *blocked.reachable_tiles(origin, me.base_stats().base_move_speed).positions()]
        targets = sorted(range(len(enemies)), key=lambda i:
                         (not enemies[i].is_submitting_gems(), foes[i]['health'] - enemies[i].gem_count() * 3))[:2]
        best, best_value = None, float('-inf')
        for target in targets:
            tiles = [origin]
            if not me.gem_count() and me.can_move():
                step = min(steps, key=lambda p: distance(p, positions[target]))
                if step != origin:
                    tiles.append(step)
            for tile in tiles:
                gaps = [distance(tile, p) for p in positions]
                for cast in (-1, 0, 1):
                    if cambc.fuel_remaining() < 950000:
                        break
                    if cast >= 0:
                        ability = me.abilities()[cast]
                        if not ability.is_ready() or ability.is_dash():
                            continue
                        if tile != origin and ability.info().exclusive_with_movement:
                            continue
                    outgoing, incoming, first = exchange(ours, foes, gaps, target, cast, tile != origin)
                    self.plan_count += 1
                    incoming += 2 * sum(s for p, s, r in self.camp_threats if distance(tile, p) <= r)
                    # Carrier life costs more than a favorable damage trade. Require
                    # a finish, not a speculative chase, before committing its bag.
                    kill = outgoing >= foes[target]['health']
                    safe = incoming < me.health() - me.max_health() * (0.3 if me.gem_count() else 0.2)
                    if not safe or not first or (me.gem_count() and not kill):
                        continue
                    value = outgoing - incoming * (2 if me.gem_count() else 1.1)
                    value += (500 + enemies[target].gem_count() * 4) if kill else 0
                    if value > best_value:
                        best_value = value
                        best = tile, cast, enemies[target]
        if best is not None and best_value > 0:
            tile, cast, target = best
            if tile != origin and not me.move_absolute(tile):
                return True  # Hidden blocker revealed; reobserve next turn.
            if not target.is_visible() or not target.is_alive():
                return True
            ability = me.abilities()[cast] if cast >= 0 else None
            if ability is not None and not ability.is_attack_reset():
                if ability.is_shield():
                    ability.use(me)
                elif distance(me.position(), target.position()) <= ability.info().range:
                    ability.use(target if ability.can_target_enemies() else target.position())
            attack_if_in_range(target)
            # Ranged walk -> reset -> attack, including when the ordinary attack
            # helper could not fire at all after movement.
            if (ability is not None and ability.is_attack_reset() and ability.is_ready()
                    and target.is_visible() and target.is_alive()
                    and distance(me.position(), target.position()) <= me.attack_range()):
                ability.use()
                if me.can_attack():
                    me.attack(target)
            return True
        if me.gem_count() or self.danger(origin, 2) > me.health() * 0.3:
            self.retreat()
            return True
        return False

    def observe_enemies(self):
        now = cambc.round_number()
        self.enemies = {key: value for key, value in self.enemies.items()
                        if now - value[1] <= 8}
        for enemy in cambc.vision.champions(Team.ENEMY):
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
        # Never repeatedly start an interruptible recall under ongoing camp damage.
        def exposure(tile):
            return self.channel_damage(tile, 2)

        if exposure(origin) == 0:
            me.recall()
            return
        # Defensive stun/shield before walking; these spells cannot be appended
        # to a normal move. A ranged stun buys an escape turn, not a chase.
        for ability in me.abilities():
            if not ability.is_ready():
                continue
            if ability.is_shield():
                ability.use(me)
                break
            if ability.is_cc() and origin == self.turn_origin:
                targets = [e for e in cambc.vision.champions(Team.ENEMY)
                           if distance(origin, e.position()) <= ability.info().range
                           and e.passive() != cambc.PassiveType.STUN_IMMUNITY
                           and not e.buffs().has_stun()]
                if targets:
                    target = max(targets, key=lambda e: e.strength())
                    ability.use(target if ability.can_target_enemies() else target.position())
                    attack_if_in_range(target)
                    if ability.info().exclusive_with_movement:
                        return
                    break
        for ability in me.abilities():
            if ability.is_dash() and ability.is_ready():
                blocked = blocked_tiles()
                landings = (blocked & ~game_map.holes()).reachable_tiles(
                    origin, int(ability.info().range)) & ~blocked
                landing = min([origin, *landings.positions()], key=exposure)
                if exposure(landing) < exposure(origin) and ability.use(landing):
                    origin = me.position()
                    break
        if me.can_move():
            field = cambc.DistanceField()
            blocked = blocked_tiles()
            field.compute(blocked, game_map.spawn_region(Team.ALLY) & ~blocked,
                          cambc.Bitboard())
            choices = [origin, *blocked.reachable_tiles(origin, 1).positions()]
            wards = me.ward_positions()
            step = min(choices, key=lambda tile: (exposure(tile),
                       0 if wards and distance(tile, wards[0]) <= 6 else 1, field.get(tile)))
            if step != origin:
                me.move_absolute(step)
        # Melee units can still defend after walking; ranged ones cannot.
        for enemy in cambc.vision.champions(Team.ENEMY):
            if attack_if_in_range(enemy):
                break

    def bank(self):
        me = cambc.me()
        duration = max(cambc.constants.SUBMIT_GEM_MINIMUM_DURATION,
                       ceil(me.gem_count() * cambc.constants.SUBMIT_GEM_DURATION_MULTIPLIER
                            + cambc.constants.SUBMIT_GEM_BASE_DURATION))
        avoid = self.enemy_zones()
        blocked = blocked_tiles() | avoid
        blocked.set(me.position(), False)
        field, reached = cambc.DistanceField(), cambc.Bitboard()
        field.compute(blocked, tiles_around(me.position(), 0), reached)
        options = []
        enemy_locks = cambc.vision.altar_lock_tiles(Team.ENEMY)
        altars = sorted(self.altars, key=lambda altar: distance(me.position(), altar))
        for altar in altars:
            if enemy_locks.is_set(altar):
                continue
            approaches = tiles_around(altar, cambc.constants.SUBMIT_GEMS_RANGE) & reached & ~blocked
            if approaches.is_empty():
                continue
            # Evaluate every altar, not a fuel-dependent prefix of neighbor tiles.
            tile = min(approaches.positions(), key=field.get)
            travel = field.get(tile)
            risk = self.channel_damage(tile, duration + min(travel, 4))
            inertia = -4 if altar == self.bank_altar else 0
            options.append((travel + risk / max(1, me.strength()) + inertia, tile, altar))
        if not options:
            # A visible enemy lock is removable in three hits, not an unavailable altar.
            locks = cambc.vision.altar_locks(Team.ENEMY)
            if locks:
                lock = min(locks, key=lambda lock: distance(me.position(), lock.position()))
                if me.can_attack() and me.attack_tiles().is_set(lock.position()):
                    me.attack(lock)
                else:
                    move_towards_closest(tiles_around(lock.position(), 1), avoid)
            else:
                self.retreat()
            return
        _, tile, altar = min(options, key=lambda option: option[0])
        self.bank_altar = altar
        lock = me.consumables()[cambc.ConsumableType.ALTAR_LOCK]
        if (lock.count() and distance(me.position(), altar) <= 2
                and not cambc.vision.has_altar_lock(altar)
                and any(distance(enemy.position(), altar) <= 8
                        for enemy in cambc.vision.champions(Team.ENEMY))
                and not any(ally.is_submitting_gems() and distance(ally.position(), altar) <= 1
                            for ally in cambc.vision.champions(Team.ALLY))):
            # Place before our tribute; do not risk cancelling an ally's live channel.
            lock.use(altar)
        if distance(me.position(), altar) <= cambc.constants.SUBMIT_GEMS_RANGE:
            # Starting turn counts, but completion is at a later turn start: budget
            # enemy actions through the entire countdown, including a one-tick bank.
            safe = self.channel_damage(me.position(), duration) < me.health() - me.max_health() * 0.15
            if me.champion_name() != cambc.ChampionType.MARCELLA and duration > 1:
                for enemy in cambc.vision.champions(Team.ENEMY):
                    if distance(me.position(), enemy.position()) <= duration + 4:
                        if any(ability.is_cc() or (ability.is_attack_reset()
                               and ability.info().enhanced_attack) for ability in enemy.abilities()):
                            safe = False
            if safe and cambc.round_number() + duration <= cambc.constants.MAX_ROUNDS:
                me.submit_gems(altar)
                return
        goals = tiles_around(tile, 0)
        if not move_towards_closest(goals, avoid):
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
        altars = game_map.altars().positions()
        visible = cambc.vision.visible_tiles()
        bushes = game_map.bushes()

        def score(tile):
            sight = cambc.Ward.visible_tiles_from(tile)
            # Unseen jungle, bush entrances and altar approaches are worth watching.
            altar_distance = min(distance(tile, altar) for altar in altars)
            return ((sight & ~visible).count() + 3 * (sight & bushes).count()
                    + max(0, 6 - altar_distance) * 8)

        best, best_score = None, -1
        for tile in candidates.positions():
            if cambc.fuel_remaining() < 2100000:
                break
            value = score(tile)
            if value > best_score:
                best, best_score = tile, value
        if best is not None:
            me.place_ward(best)

    def buy_items(self):
        # Basic attacks and resets scale with Strength. Tavi can also shop in-field.
        me = cambc.me()
        item = Item.POWER_SHARD_OF_STRENGTH
        count = me.gold_count() // item.cost()
        if count and me.can_buy(item, count):
            me.buy(item, count)
        lock = cambc.ConsumableType.ALTAR_LOCK
        if me.can_buy(lock):
            me.buy(lock)

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

        threshold = 0.6 if me.gem_count() >= 40 and self.danger(me.position(), 3) else 0.35
        if not at_spawn and me.health() < me.max_health() * threshold:
            self.retreat()
            return

        # Carriers route away from fights instead of stopping to attack every passerby.
        if me.gem_count() > 0:
            self.bank()
            return
        self.bank_altar = None

        # Safe cluster farmers may never die or need healing. Convert their saved
        # capture gold into damage instead of waiting indefinitely for a spawn visit.
        if not at_spawn and me.gold_count() >= 150:
            self.retreat()
            return

        # Attack the first enemy champion already in range.
        for enemy in cambc.vision.champions(Team.ENEMY):
            if attack_if_in_range(enemy):
                return

        self.farm_camps()

        me.set_priority(1 + below(100))
