"""Exercise the real cache builder with a small fuel-controlled SDK double."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'src'
sys.path.insert(0, str(SOURCE))
sdk = ModuleType('cambc')
sdk.Team = SimpleNamespace(ALLY=0, ENEMY=1)
sdk.ItemType = SimpleNamespace()
sdk.game_map = ModuleType('cambc.game_map')
sdk.game_map.spawn_region = lambda team: SimpleNamespace(
    positions=lambda: [SimpleNamespace(x=0 if team == 0 else 100, y=0 if team == 0 else 100)])
spec = importlib.util.spec_from_file_location('cache_test_bot', SOURCE / 'bot.py')
module = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'cambc': sdk, 'cambc.game_map': sdk.game_map}):
    spec.loader.exec_module(module)


class Camp:
    def __init__(self, x, cluster=False):
        self.tile = SimpleNamespace(x=x, y=3)
        self.cluster = cluster
        self.reads = 0

    def base_stats(self):
        self.reads += 1
        return SimpleNamespace(base_health=500, base_strength=0, base_attack_range=3)

    def spawn_position(self):
        return self.tile

    def is_monolith(self):
        return False

    def is_gem_cluster(self):
        return self.cluster


class Group(list):
    def __int__(self):
        return 17

    def gem_value(self):
        return 48

    def gold_value(self):
        return 70

    def spawn_tiles(self):
        return 'spawn-mask'


class MapCacheTest(unittest.TestCase):
    def test_unit_queries_share_a_cache_until_an_action(self):
        class Unit:
            def __init__(self):
                self.reads = self.visibility_reads = 0
                self.tile = (3, 4)

            def __int__(self):
                return 1

            def is_visible(self):
                self.visibility_reads += 1
                return True

            def position(self):
                self.reads += 1
                return self.tile

        unit = Unit()
        module.acted()
        for _ in range(12):
            self.assertTrue(module.safe_is_visible(unit))
            self.assertEqual(module.safe_position(unit), (3, 4))
        self.assertEqual((unit.visibility_reads, unit.reads), (1, 1))
        unit.tile = (5, 7)
        module.acted()
        self.assertEqual(module.safe_position(unit), (5, 7))
        self.assertEqual((unit.visibility_reads, unit.reads), (2, 2))

    def test_same_numeric_handle_for_different_entity_kinds_does_not_collide(self):
        class Unit:
            def __int__(self):
                return 1

            def is_visible(self):
                return True

            def position(self):
                return (3, 4)

        class OtherKind(Unit):
            def position(self):
                return (7, 8)

        module.acted()
        self.assertEqual(module.safe_position(Unit()), (3, 4))
        self.assertEqual(module.safe_position(OtherKind()), (7, 8))

    def bot(self):
        bot = module.Bot.__new__(module.Bot)
        bot.ginfo, bot.gpartial, bot.camp_ranges = {}, {}, []
        bot.altar_gap = lambda tile: 12
        return bot

    def test_pause_and_resume_without_repeating_sdk_work(self):
        bot = self.bot()
        group = Group([Camp(3, True), Camp(4), Camp(5)])
        with patch.object(sdk, 'fuel_remaining', side_effect=[1000, 100], create=True):
            self.assertIsNone(bot.group_info(group, 500))
        self.assertEqual([c.reads for c in group], [1, 0, 0])
        with patch.object(sdk, 'fuel_remaining', return_value=1000, create=True):
            info = bot.group_info(group, 500)
        self.assertEqual([c.reads for c in group], [1, 1, 1])
        self.assertEqual(info[1], 0)  # Preserve cluster classification across chunks.
        self.assertEqual(len(info[7]), 3)
        self.assertEqual(info[8], (3, 3, 5, 3))
        self.assertEqual(bot.gpartial, {})
        self.assertIs(bot.group_info(group), info)
        self.assertEqual([c.reads for c in group], [1, 1, 1])

    def test_no_budget_does_not_start_another_camp(self):
        bot = self.bot()
        group = Group([Camp(4)])
        with patch.object(sdk, 'fuel_remaining', return_value=100, create=True):
            self.assertIsNone(bot.group_info(group, 500))
        self.assertEqual(group[0].reads, 0)
        self.assertNotIn(id(group), bot.ginfo)


if __name__ == '__main__':
    unittest.main()
