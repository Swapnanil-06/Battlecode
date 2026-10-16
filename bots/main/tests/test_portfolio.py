import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from portfolio import select_mode, FARMING, PACKS, INCUMBENT


class PortfolioTests(unittest.TestCase):
    def test_verified_farming_layout(self):
        groups = [[None] * 3] * 8 + [[None] * 4]
        self.assertEqual(select_mode(50, 50, groups), FARMING)

    def test_verified_packs_layout(self):
        self.assertEqual(select_mode(31, 31, [[None] * 3, [None] * 3, [None] * 3, [None]] * 2), PACKS)

    def test_dimensions_alone_cannot_select_a_variant(self):
        self.assertEqual(select_mode(50, 50, [[None] * 14]), INCUMBENT)

    def test_unknown_layout_preserves_incumbent(self):
        self.assertEqual(select_mode(90, 90, []), INCUMBENT)


if __name__ == '__main__':
    unittest.main()
