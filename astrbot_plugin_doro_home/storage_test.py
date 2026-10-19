import tempfile
import unittest
from pathlib import Path

from storage import DoroStore


class DoroStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = DoroStore(Path(self.temp_dir.name) / "doro.db")
        self.endings = [("结局甲", "a.jpg"), ("结局乙", "b.jpg")]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_daily_draw_is_idempotent(self):
        first = self.store.draw_ending("group-1", "user-1", "2026-10-15", self.endings)
        second = self.store.draw_ending("group-1", "user-1", "2026-10-15", self.endings)
        self.assertTrue(first.is_new_today)
        self.assertFalse(second.is_new_today)
        self.assertEqual(first.ending_name, second.ending_name)
        self.assertEqual(1, second.total_times)

    def test_draws_are_separate_per_group(self):
        left = self.store.draw_ending("group-1", "user-1", "2026-10-15", [("甲", "a")])
        right = self.store.draw_ending("group-2", "user-1", "2026-10-15", [("乙", "b")])
        self.assertEqual("甲", left.ending_name)
        self.assertEqual("乙", right.ending_name)

    def test_repeat_ending_increments_collection(self):
        self.store.draw_ending("group-1", "user-1", "2026-10-15", [("甲", "a")])
        result = self.store.draw_ending("group-1", "user-1", "2026-10-16", [("甲", "a")])
        self.assertEqual(2, result.total_times)
        self.assertEqual({"甲": 2}, self.store.get_collection("group-1", "user-1"))

    def test_history_is_saved_and_reused(self):
        self.store.record_history("source-1", "100")
        picked = self.store.pick_history(["source-1"])
        self.assertEqual(("source-1", "100"), picked)
        self.store.mark_history_used(*picked)
        self.assertEqual(1, self.store.history_count(["source-1"]))


if __name__ == "__main__":
    unittest.main()
