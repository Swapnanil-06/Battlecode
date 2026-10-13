"""Sparring hunter: chase visible enemy gem carriers, pursue briefly to last sighting.

Hunters (Tavi, Vendetta, Varg, Ryth) leash up to HUNT_LEASH tiles toward any
visible carrier and pursue its last seen tile for PURSUE_ROUNDS. Marcella, the
stun-immune banker, only takes carriers that are already close. Everyone falls
back to the copied v2 farm/bank economy when no carrier is in reach.
"""
import cambc

import kit
from bot import Bot, distance, tiles_around, move_towards_closest

Team, Champ = cambc.Team, cambc.ChampionType

HUNT_LEASH = 11
PURSUE_ROUNDS = 6
PURSUE_RADIUS = 14


class SparringBot(Bot):
    def __init__(self):
        super().__init__()
        self.marks = {}  # enemy id -> (position, round seen, gems)
        kit.warm_up()

    def turn_start(self):
        kit.begin_turn()

    def leash(self):
        return 4 if cambc.me().champion_name() == Champ.MARCELLA else HUNT_LEASH

    def risk(self, tile):
        return self.danger(tile, 2)

    def aggressive_turn(self):
        if kit.low_fuel():
            return False
        me = cambc.me()
        now = cambc.round_number()
        origin = me.position()
        self.marks = {k: v for k, v in self.marks.items() if now - v[1] <= PURSUE_ROUNDS}
        enemies = cambc.vision.champions(Team.ENEMY)
        for enemy in enemies:
            if enemy.gem_count() > 0:
                self.marks[int(enemy)] = (enemy.position(), now, enemy.gem_count())
            else:
                self.marks.pop(int(enemy), None)

        healthy = me.health() >= me.max_health() * 0.45
        bag = me.gem_count()
        leash = self.leash() if bag < 30 else 3
        carriers = [e for e in enemies if e.gem_count() > 0 and not kit.in_enemy_spawn(e.position())
                    and distance(origin, e.position()) <= leash]
        if carriers and healthy:
            target = max(carriers, key=lambda e: kit.target_value(e) - 6 * distance(origin, e.position()))
            spot = target.position()
            kit.engage(target, self.risk)
            kit.ward_toward(spot)  # after acting: moving the ward can drop sight of target
            return True

        # Opportunistic: punish any enemy we can already hit, or one that is nearly dead.
        if kit.opportunistic(enemies, self.risk, healthy):
            return True

        # Pursue the freshest carrier sighting toward its last seen tile.
        if healthy and bag < 30 and self.marks and me.champion_name() != Champ.MARCELLA:
            key, (spot, seen, gems) = max(self.marks.items(), key=lambda kv: (kv[1][2], kv[1][1]))
            if distance(origin, spot) <= 1:
                self.marks.pop(key, None)
            elif distance(origin, spot) <= PURSUE_RADIUS and not kit.in_enemy_spawn(spot):
                kit.COUNTS["pursue"] += 1
                kit.ward_toward(spot)
                if not kit.chase_move(spot, 1, self.risk):
                    move_towards_closest(tiles_around(spot, 1))
                return True
        return False
