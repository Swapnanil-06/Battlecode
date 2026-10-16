import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from coordination import claimed_jobs, publish


class ClaimsTest(unittest.TestCase):
    def test_six_writers_preserve_each_other(self):
        word = 0
        for slot in range(6):
            word = publish(word, slot, slot + 1, 10)
        self.assertLess(word, 2**64)
        self.assertEqual(claimed_jobs(word, 2, 11), {1, 2, 4, 5, 6})

    def test_stale_claim_never_revives_while_other_writer_advances(self):
        word = publish(0, 0, 63, 2)
        for turn in range(3, 80):
            word = publish(word, 1, 1, turn)
            self.assertEqual(63 in claimed_jobs(word, 1, turn), turn <= 4)

    def test_long_gap_and_modulo_boundary(self):
        word = publish(0, 0, 2, 3)
        self.assertEqual(claimed_jobs(word, 1, 5), {2})
        self.assertEqual(claimed_jobs(word, 1, 6), set())
        self.assertEqual(claimed_jobs(word, 1, 67), set())

    def test_release_and_reassignment(self):
        word = publish(0, 0, 7, 99)
        word = publish(word, 1, 8, 100)
        word = publish(word, 0, 0, 100)
        self.assertEqual(claimed_jobs(word, 0, 100), {8})
        self.assertEqual(claimed_jobs(word, 1, 100), set())


if __name__ == '__main__':
    unittest.main()
