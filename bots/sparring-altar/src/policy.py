"""Sparring altar camper: hold enemy-used altar approaches; stun/lock tributes, kill carriers.

Ryth and Tavi (their range-4 stuns interrupt tributes) each take one of the
altars the enemy is most likely to bank at: the nearest altar to enemy-side camp
groups, weighted by gem value. A camper keeps its ward on the altar, locks it
when an enemy carrier approaches or is tributing (placement cancels an enemy
channel) and stuns/kills tributing or carrying enemies inside the leash.
Ryth is a strict camper: it waits on a post beside the altar (bushes preferred)
and farms only camp groups next to it. Tavi is a rover: it farms anywhere
(preferring groups near its altar) while the altar ward watches, and rushes back
when the ward shows an enemy carrier. Other picks use the copied v2 economy plus
opportunistic hits.
"""
from math import ceil

import cambc
from cambc import game_map

import kit
from bot import Bot, distance, tiles_around, move_towards_closest

Team, Champ = cambc.Team, cambc.ChampionType

CAMPER_SLOTS = {Champ.RYTH: 0, Champ.TAVI: 1}
CAMP_START = 60      # farm normally until enemies plausibly carry gems
LEASH = 6            # chase radius around the guarded altar
LOCAL_FARM = 7       # camp groups this close to the altar may be farmed between visits
LOCK_ALERT = 7       # enemy carriers within this distance of the altar trigger a lock
ROVER_RETURN = 16    # a roving camper answers its ward's alert from this far away


class SparringBot(Bot):
    def __init__(self):
        super().__init__()
        self.altar = None
        self.post = None
        self.camper = cambc.me().champion_name() in CAMPER_SLOTS
        self.rover = cambc.me().champion_name() == Champ.TAVI
        kit.warm_up()
        if self.camper:
            self.choose_post()

    def turn_start(self):
        kit.begin_turn()

    def risk(self, tile):
        return self.danger(tile, 2)

    def choose_post(self):
        enemy_field = kit.spawn_distance(Team.ENEMY)
        ally_field = kit.spawn_distance(Team.ALLY)
        static = (game_map.walls() | game_map.holes() | game_map.altars()
                  | game_map.spawn_region(Team.ENEMY) | game_map.spawn_region(Team.ALLY))
        unreachable = 60000

        def approaches(altar):
            ring = tiles_around(altar, 1) & ~static
            return [t for t in ring.positions()
                    if enemy_field.get(t) < unreachable and ally_field.get(t) < unreachable]

        # Only altars both teams can actually walk up to are worth guarding.
        altars = [a for a in game_map.altars().positions() if approaches(a)]
        if not altars:
            self.camper = False
            return
        weight = {altar: 0.0 for altar in altars}
        for group in game_map.camp_groups():
            tile = group.camps()[0].spawn_position()
            if not kit.enemy_side(tile):
                continue
            nearest = min(altars, key=lambda altar: distance(tile, altar))
            weight[nearest] += group.gem_value() + 1

        def enemy_reach(altar):
            return min(enemy_field.get(t) for t in approaches(altar))

        usable = [a for a in altars if enemy_reach(a) >= 6] or altars
        ranked = sorted(usable, key=lambda a: (-weight[a], enemy_reach(a)))
        slot = CAMPER_SLOTS[cambc.me().champion_name()]
        self.altar = ranked[min(slot, len(ranked) - 1)]
        ring = tiles_around(self.altar, 2) & ~static
        tiles = [t for t in ring.positions() if ally_field.get(t) < unreachable] or approaches(self.altar)
        bushes = game_map.bushes()
        self.post = min(tiles, key=lambda t: (not bushes.is_set(t), enemy_field.get(t)))

    def group_bias(self, group):
        if not self.camper or cambc.round_number() < CAMP_START:
            return 1.0
        tile = group.camps()[0].spawn_position()
        if distance(tile, self.altar) <= LOCAL_FARM:
            return 2.0 if self.rover else 1.0
        return 1.0 if self.rover else 0.0

    def camping(self):
        return self.camper and cambc.round_number() >= CAMP_START

    def place_ward(self):
        # Campers keep their single ward on the guarded altar (see hold_post).
        if not self.camping():
            super().place_ward()

    def extra_candidates(self, nearby):
        if not self.camper or cambc.round_number() < CAMP_START:
            return []
        return [g for g in nearby if distance(g.camps()[0].spawn_position(), self.altar) <= LOCAL_FARM][:4]

    def idle_without_group(self):
        if not self.camper or cambc.round_number() < CAMP_START:
            return False
        return self.hold_post()

    def hold_post(self):
        """Walk to the guard post; False if no route exists right now."""
        me = cambc.me()
        kit.ward_toward(self.altar, keep_radius=3)
        if distance(me.position(), self.altar) <= 2:
            return True
        if move_towards_closest(tiles_around(self.post, 0)):
            return True
        return move_towards_closest(tiles_around(self.altar, 2))

    def aggressive_turn(self):
        if kit.low_fuel():
            return False
        me = cambc.me()
        enemies = cambc.vision.champions(Team.ENEMY)
        healthy = me.health() >= me.max_health() * 0.45
        if not self.camper or cambc.round_number() < CAMP_START:
            return kit.opportunistic(enemies, self.risk, healthy)

        altar = self.altar
        origin = me.position()
        near = [e for e in enemies if distance(e.position(), altar) <= LEASH + 2
                and not kit.in_enemy_spawn(e.position())]
        tributing = [e for e in near if e.is_submitting_gems()]
        carriers = [e for e in near if e.gem_count() > 0]

        # Lock first: a fresh lock cancels an enemy tribute at this altar and
        # blocks the approaching carrier's bank; our own team can still tribute.
        if (any(distance(e.position(), altar) <= 1 for e in tributing)
                or any(distance(e.position(), altar) <= LOCK_ALERT for e in carriers)):
            kit.place_lock(altar)

        target = None
        if tributing:
            target = max(tributing, key=kit.target_value)
        elif carriers and healthy:
            target = max(carriers, key=lambda e: kit.target_value(e) - 5 * distance(origin, e.position()))
        if target is not None:
            chase = distance(target.position(), altar) <= LEASH + 2
            if self.rover and distance(origin, altar) > ROVER_RETURN:
                chase = False
            if chase or distance(origin, target.position()) <= max(4, me.attack_range()):
                kit.engage(target, self.risk, chase=chase)
                kit.ward_toward(altar, keep_radius=3)  # after acting: re-warding can drop sight
                if distance(me.position(), altar) <= 2 and (tributing or carriers):
                    kit.place_lock(altar)
                return True

        if kit.opportunistic(near, self.risk, healthy):
            return True

        if me.gem_count() > 0:
            return self.bank_here(enemies)

        # Restock a used lock when nothing is contesting the altar.
        lock = me.consumables()[cambc.ConsumableType.ALTAR_LOCK]
        if (not lock.count() and me.gold_count() >= 40 and not enemies
                and not game_map.spawn_region(Team.ALLY).is_set(origin)):
            self.retreat()
            return True

        if self.rover:
            wards = me.ward_positions()
            if not wards or distance(wards[0], altar) > 3:
                return self.hold_post()  # re-establish the altar watch first
            return False  # v2 farm, biased toward groups near the altar
        if distance(origin, altar) > LOCAL_FARM + 2:
            return self.hold_post()
        return False  # v2 farm restricted to local groups (group_bias), else hold post.

    def bank_here(self, enemies):
        """Tribute at the guarded altar when no enemy is close; else defer to v2 bank."""
        me = cambc.me()
        altar = self.altar
        if (any(distance(e.position(), me.position()) <= 4 for e in enemies)
                or cambc.vision.altar_lock_tiles(Team.ENEMY).is_set(altar)
                or distance(me.position(), altar) > LOCAL_FARM + 2):
            return False
        gems = me.gem_count()
        duration = max(cambc.constants.SUBMIT_GEM_MINIMUM_DURATION,
                       ceil(gems * cambc.constants.SUBMIT_GEM_DURATION_MULTIPLIER
                            + cambc.constants.SUBMIT_GEM_BASE_DURATION))
        if cambc.round_number() + duration > cambc.constants.MAX_ROUNDS:
            return False
        if distance(me.position(), altar) <= cambc.constants.SUBMIT_GEMS_RANGE:
            if enemies:
                kit.place_lock(altar)
            me.submit_gems(altar)
            return True
        return move_towards_closest(tiles_around(altar, cambc.constants.SUBMIT_GEMS_RANGE))
