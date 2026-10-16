"""Regressions tied to the top-team replay failures."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'src'
sys.path.insert(0, str(SOURCE))
from camp_tactics import pack_damage

sdk = ModuleType('cambc')
sdk.Team = SimpleNamespace(ALLY=0, ENEMY=1)
sdk.ItemType = SimpleNamespace()
sdk.game_map = ModuleType('cambc.game_map')
spec = importlib.util.spec_from_file_location('strategy_regression_bot', SOURCE / 'bot.py')
module = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'cambc': sdk, 'cambc.game_map': sdk.game_map}):
    spec.loader.exec_module(module)


def camp_group(gems, health, monolith=False):
    return (None, None, None, None, None, gems, None,
            [(None, None, health, 20, monolith)])


class StrategyRegressions(unittest.TestCase):
    def investment(self, groups):
        bot = module.Bot.__new__(module.Bot)
        bot.resource_mode = None
        bot.groups = [SimpleNamespace(gem_value=lambda v=g[5]: v) for g in groups]
        infos = {id(group): info for group, info in zip(bot.groups, groups)}
        bot.group_info = lambda group: infos[id(group)]
        return bot.investment_map(), bot.monolith_only

    def test_optional_boss_cannot_override_a_wolf_map(self):
        self.assertEqual(self.investment([camp_group(66, 4050), camp_group(1000, 20000, True)]), (False, False))

    def test_boss_only_map_keeps_investment(self):
        self.assertEqual(self.investment([camp_group(200, 20000, True)]), (True, True))

    def test_large_non_boss_pack_keeps_investment(self):
        self.assertEqual(self.investment([camp_group(360, 17400), camp_group(22, 1850)]), (True, False))

    def test_empty_map_has_no_boss_policy(self):
        self.assertEqual(self.investment([]), (False, False))

    def test_stellar_pack_cast_beats_single_target(self):
        targets = [(5, 3, 1350), (5, 4, 1350), (5, 5, 1350)]
        self.assertEqual(pack_damage(targets, (5, 4), 140, 1), 420)
        self.assertEqual(pack_damage(targets, (5, 4), 200, 0), 200)

    def test_overkill_does_not_make_area_spell_look_better(self):
        targets = [(5, 3, 10), (5, 4, 400), (5, 5, 10)]
        self.assertEqual(pack_damage(targets, (5, 4), 140, 1), 160)
        self.assertEqual(pack_damage(targets, (5, 4), 200, 0), 200)

    def test_varg_prefers_middle_of_vertical_pack(self):
        targets = [(5, 3, 1350), (5, 4, 1350), (5, 5, 1350)]
        scores = [pack_damage(targets, (x, y), 150, 1) for x, y, _ in targets]
        self.assertEqual(scores, [300, 450, 300])


if __name__ == '__main__':
    unittest.main()
