"""Host-side checks: python runner/test_objective_policy.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bots/main/src'))
from objective_policy import assign_jobs, bank_now, objective_rate


class ObjectivePolicyTests(unittest.TestCase):
    def test_risky_fight_loses_large_bag(self):
        self.assertLess(objective_rate(24, 0, 150, .5, 20, 60), 0)

    def test_delivery_beats_unnecessary_extra_camp(self):
        self.assertTrue(bank_now(48, 8, .99, 24, 35, .85))

    def test_short_safe_detour_can_pay(self):
        self.assertFalse(bank_now(24, 20, .99, 24, 25, .99))

    def test_capturer_keeps_job_and_allies_spread(self):
        offers = [(1, 4, 5), (2, 4, 4), (2, 5, 3), (3, 5, 2), (3, 6, 1)]
        self.assertEqual(assign_jobs(offers, ((1, 4),)), {1: 4, 2: 5, 3: 6})

    def test_unsafe_jobs_and_conflicting_commitments(self):
        self.assertEqual(assign_jobs([(1, 1, -1)]), {})
        with self.assertRaises(ValueError):
            assign_jobs([], ((1, 4), (2, 4)))
        with self.assertRaises(ValueError):
            objective_rate(24, 0, 0, 1.2, 10)


if __name__ == '__main__':
    unittest.main()
