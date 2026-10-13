"""Contract tests for the bounded exchange used to commit or save a carrier."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from combat import exchange


def fighter(strength, reach=1, spells=(), health=1000, immune=False, stunned=False):
    return dict(strength=strength, range=reach, speed=1, spells=spells,
                health=health, immune=immune, stunned=stunned)


class ExchangeTests(unittest.TestCase):
    def test_ranged_walk_needs_reset_and_cannot_cast_exclusive_stun(self):
        us = fighter(35, 3, [('reset', 0, 0, 0, False, False),
                             ('damage', 0, 4, 220, True, True)])
        enemy = fighter(70)
        self.assertEqual(exchange(us, [enemy], [3], 0, -1, True)[2], 0)
        self.assertEqual(exchange(us, [enemy], [3], 0, 0, True)[2], 35)
        self.assertEqual(exchange(us, [enemy], [3], 0, 1, True)[2], 0)

    def test_cooldown_is_not_cast_twice_and_melee_can_close(self):
        us = fighter(45, spells=[('reset', 0, 0, 0, False, False)])
        enemy = fighter(70)
        # 90 now + 45 next; enemy walks from distance two and strikes twice.
        self.assertEqual(exchange(us, [enemy], [1], 0, 0), (135, 140, 90))
        self.assertEqual(exchange(us, [enemy], [2], 0, -1), (90, 140, 0))

    def test_stun_immunity_and_other_enemy_interrupts(self):
        us = fighter(35, 3, [('damage', 0, 4, 220, True, True)])
        enemy = fighter(70)
        self.assertEqual(exchange(us, [enemy], [1], 0, 0)[1], 70)
        immune = fighter(70, immune=True)
        self.assertEqual(exchange(us, [immune], [1], 0, 0)[1], 140)
        interruptor = fighter(20, 3, [('damage', 0, 4, 90, True, True)])
        # A second enemy's stun cancels our follow-up regardless of list order.
        a = exchange(us, [enemy, interruptor], [1, 3], 0, 0)
        b = exchange(us, [interruptor, enemy], [3, 1], 1, 0)
        self.assertEqual(a, b)
        self.assertEqual(a[0], 255)

    def test_dash_and_damage_compete_for_one_cast(self):
        us = fighter(50)
        enemy = fighter(70, spells=[('dash', 0, 2, 0, False, False),
                                    ('damage', 0, 4, 200, False, True)])
        # At gap five: dash+walk to range one, then the other spell next turn.
        self.assertEqual(exchange(us, [enemy], [5], 0)[1], 270)
        ready_later = fighter(70, spells=[('damage', 1, 4, 200, False, True)])
        self.assertEqual(exchange(us, [ready_later], [4], 0)[1], 200)

    def test_lethal_first_hit_prevents_reply_but_shield_changes_boundary(self):
        us = fighter(90)
        self.assertEqual(exchange(us, [fighter(70, health=90)], [1], 0), (90, 0, 90))
        # Health includes a shield snapshot; 91 cannot be treated as a first-hit kill.
        self.assertEqual(exchange(us, [fighter(70, health=91)], [1], 0), (180, 70, 90))


if __name__ == '__main__':
    unittest.main()
