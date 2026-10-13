"""Sparring denial: invade enemy-side camps, contest captures, steal rewards.

Invaders (Varg, Tavi) treat camp groups nearer the enemy spawn as
their farm: enemy-side groups are added to the v2 candidate list and scored
up (own-side groups scored down), so they clear and capture the opponent's
camps. Any visible enemy standing on or next to a camp region is attacked and,
when the region has a pending reward, the invader steps onto an empty region
tile to contest (and so reset) the enemy capture. Marcella, Vendetta and Ryth keep the
copied v2 economy with opportunistic hits, so the team still scores.
"""
import cambc
from cambc import game_map

import kit
from bot import Bot, distance, tiles_around, move_towards_closest, blocked_tiles

Team, Champ = cambc.Team, cambc.ChampionType

INVADERS = (Champ.VARG, Champ.TAVI)
CONTEST_RADIUS = 9
ENEMY_BIAS = 3.0
HOME_BIAS = 0.35


class SparringBot(Bot):
    def __init__(self):
        super().__init__()
        self.invader = cambc.me().champion_name() in INVADERS
        self.side = {}
        self.last_gems = 0
        kit.warm_up()
        self.groups = game_map.camp_groups()
        # Static per-group data, computed once: (group, spawn tiles, anchor tile).
        self.regions = [(g, g.spawn_tiles(), g.camps()[0].spawn_position()) for g in self.groups]
        for group in self.groups:
            self.enemy_group(group)

    def turn_start(self):
        kit.begin_turn()
        self.track_steals()

    def track_steals(self):
        """Count capture rewards collected while standing in an enemy-side camp region."""
        me = cambc.me()
        gems = me.gem_count() if me.is_alive() else 0
        if gems > self.last_gems:
            here = me.position()
            for group, region, _ in self.regions:
                if region.is_set(here):
                    if self.enemy_group(group):
                        kit.COUNTS["stolen_gems"] += gems - self.last_gems
                    break
        self.last_gems = gems

    def risk(self, tile):
        return self.danger(tile, 2)

    def enemy_group(self, group):
        key = int(group)
        if key not in self.side:
            self.side[key] = kit.enemy_side(group.camps()[0].spawn_position())
        return self.side[key]

    def group_bias(self, group):
        if not self.invader:
            return 1.0
        return ENEMY_BIAS if self.enemy_group(group) else HOME_BIAS

    def extra_candidates(self, nearby):
        if not self.invader:
            return []
        return [g for g in nearby if self.enemy_group(g)][:4]

    def contest_target(self, enemies):
        """Enemy champion farming or capturing a camp region we can reach."""
        me = cambc.me()
        visible = cambc.vision.visible_tiles()
        best = None
        for enemy in enemies:
            spot = enemy.position()
            if kit.in_enemy_spawn(spot) or distance(me.position(), spot) > CONTEST_RADIUS:
                continue
            around = tiles_around(spot, 1)
            for group, region, anchor in self.regions:
                if distance(anchor, spot) > 6 or (around & region).is_empty():
                    continue
                reward = (not (region & visible).is_empty()
                          and isinstance(group.state(), game_map.CampGroupRewardAvailable))
                score = (2 if reward else 1, kit.target_value(enemy))
                if best is None or score > best[0]:
                    best = (score, enemy, group, reward)
                break
        return best

    def aggressive_turn(self):
        if kit.low_fuel():
            return False
        me = cambc.me()
        enemies = cambc.vision.champions(Team.ENEMY)
        healthy = me.health() >= me.max_health() * 0.45
        if not self.invader:
            return kit.opportunistic(enemies, self.risk, healthy)

        found = self.contest_target(enemies) if healthy else None
        if found is not None:
            _, enemy, group, reward = found
            region = group.spawn_tiles()
            spot = enemy.position()
            if reward and not region.is_set(me.position()) and me.can_move():
                # Standing on any region tile contests the capture; then fight from there.
                free = region & ~blocked_tiles()
                if not free.is_empty():
                    kit.cast_offensive(enemy, True)
                    if not kit.TURN["exclusive"] and move_towards_closest(free):
                        kit.COUNTS["contest"] += 1
                    if enemy.is_visible() and enemy.is_alive():
                        kit.strike(enemy)
                    kit.ward_toward(spot)
                    return True
            kit.engage(enemy, self.risk)
            kit.ward_toward(spot)
            return True

        # Steal carried gems from any enemy carrier close to us.
        carriers = [e for e in enemies if e.gem_count() > 0 and not kit.in_enemy_spawn(e.position())
                    and distance(me.position(), e.position()) <= 6]
        if carriers and healthy and me.gem_count() < 40:
            kit.engage(max(carriers, key=kit.target_value), self.risk)
            return True

        if kit.opportunistic(enemies, self.risk, healthy):
            return True
        if self.group is not None and self.enemy_group(self.group):
            kit.ward_toward(self.group.camps()[0].spawn_position())
        return False
