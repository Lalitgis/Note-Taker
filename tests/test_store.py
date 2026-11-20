import json
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dailysidebar import store as st  # noqa: E402

TODAY = date(2026, 11, 20)  # a Friday


class ParseTests(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(st.parse_date("today", TODAY), "2026-11-20")
        self.assertEqual(st.parse_date("tmr", TODAY), "2026-11-21")
        self.assertEqual(st.parse_date("+3", TODAY), "2026-11-23")
        self.assertEqual(st.parse_date("mon", TODAY), "2026-11-23")
        self.assertEqual(st.parse_date("fri", TODAY), "2026-11-27")  # next Friday, not today
        self.assertEqual(st.parse_date("01/12/2026", TODAY), "2026-12-01")
        self.assertEqual(st.parse_date("05/01", TODAY), "2027-01-05")  # day/month, rolls to next year
        with self.assertRaises(ValueError):
            st.parse_date("someday", TODAY)

    def test_quick_add(self):
        p = st.parse_quick_add("Read GWAS paper !high #reading @Thesis fri *weekly", TODAY)
        self.assertEqual(p["title"], "Read GWAS paper")
        self.assertEqual(p["priority"], "High")
        self.assertEqual(p["category"], "Reading")
        self.assertEqual(p["project"], "Thesis")
        self.assertEqual(p["due"], "2026-11-27")
        self.assertEqual(p["repeat"], "weekly")

    def test_quick_add_plain(self):
        p = st.parse_quick_add("Email supervisor about today's results", TODAY)
        self.assertEqual(p["title"], "Email supervisor about today's results")
        self.assertEqual(p["due"], "")

    def test_next_occurrence(self):
        self.assertEqual(st.next_occurrence("2026-11-20", "weekdays", TODAY), "2026-11-23")
        self.assertEqual(st.next_occurrence("2026-01-31", "monthly", date(2026, 1, 31)), "2026-02-28")
        self.assertEqual(st.next_occurrence("2026-11-10", "daily", TODAY), "2026-11-20")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "data.db")
        self.s = st.Store(self.path)

    def tearDown(self):
        self.s.close()
        self.dir.cleanup()

    def test_task_lifecycle_and_persistence(self):
        t = self.s.add_task("Draft methods", "High", "Writing", due="2026-11-20")
        self.s.update_task(t["id"], title="Draft methods section")
        self.s.set_done(t["id"], True)
        self.s.close()
        self.s = st.Store(self.path)
        r = self.s.task(t["id"])
        self.assertEqual(r["title"], "Draft methods section")
        self.assertEqual(r["done"], 1)
        row = self.s.delete_task(t["id"])
        self.assertIsNone(self.s.task(t["id"]))
        self.s.restore_task(row)
        self.assertIsNotNone(self.s.task(t["id"]))

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            self.s.add_task("   ")

    def test_views(self):
        today = date.today()
        iso = lambda n: (today + timedelta(days=n)).isoformat()  # noqa: E731
        late = self.s.add_task("late", due=iso(-2))
        now = self.s.add_task("now", due=iso(0))
        myday = self.s.add_task("my day", my_day=iso(-1))     # rolls over from yesterday
        later = self.s.add_task("later", due=iso(5))
        self.s.add_task("someday")
        ids = lambda rows: {r["id"] for r in rows}  # noqa: E731
        self.assertEqual(ids(self.s.tasks("today")), {late["id"], now["id"], myday["id"]})
        self.assertEqual(ids(self.s.tasks("overdue")), {late["id"]})
        self.assertEqual(ids(self.s.tasks("upcoming")), {later["id"]})
        self.s.set_done(now["id"], True)
        self.assertIn(now["id"], ids(self.s.tasks("today")))  # done today stays visible
        c = self.s.counts()
        self.assertEqual((c["today"], c["today_done"], c["overdue"]), (3, 1, 1))

    def test_repeat_creates_next(self):
        t = self.s.add_task("Weekly lab meeting", due="2026-11-20", repeat="weekly")
        nxt = self.s.set_done(t["id"], True, today=TODAY)
        self.assertEqual(nxt["due"], "2026-11-27")
        self.assertEqual(nxt["repeat"], "weekly")

    def test_quick_add_creates_project(self):
        t = self.s.quick_add("Run PCA !low @Chapter_2")
        self.assertEqual(t["project_name"], "Chapter 2")
        t2 = self.s.quick_add("Plot results @chapter")
        self.assertEqual(t2["project_id"], t["project_id"])  # prefix match on existing project
        p = self.s.projects()[0]
        self.assertEqual((p["total"], p["done_count"]), (2, 0))

    def test_delete_project_keeps_tasks(self):
        p = self.s.add_project("Grant")
        t = self.s.add_task("Budget", project_id=p["id"])
        self.s.delete_project(p["id"])
        self.assertIsNone(self.s.task(t["id"])["project_id"])

    def test_notes_and_papers(self):
        self.s.set_daily_note("2026-11-20", "Ran GWAS")
        self.assertEqual(self.s.daily_note("2026-11-20"), "Ran GWAS")
        self.s.set_daily_note("2026-11-20", "  ")
        self.assertEqual(self.s.note_days("2026-11-01", "2026-11-30"), set())
        n = self.s.add_note("Ideas", "mixed models")
        self.assertEqual(self.s.notes("mixed")[0]["id"], n["id"])
        p = self.s.add_paper("Attention is all you need", authors="Vaswani", year=2017)
        self.s.update_paper(p["id"], status="Reading", rating=5)
        self.assertEqual(self.s.paper_counts()["Reading"], 1)
        self.assertEqual(len(self.s.search_all("vaswani")["papers"]), 1)

    def test_focus_log(self):
        self.s.log_focus(25, label="writing", started="2026-11-20T10:00:00")
        self.s.log_focus(10, started="2026-11-19T10:00:00")
        self.assertEqual(self.s.focus_minutes("2026-11-20", "2026-11-20"), 25)
        self.assertEqual([m for _, m in self.s.focus_by_day(2, TODAY)], [10, 25])

    def test_settings(self):
        self.assertEqual(self.s.get("focus_minutes"), 25)
        self.s.set("focus_minutes", 50)
        self.assertEqual(self.s.get("focus_minutes"), 50)
        self.assertIsNone(self.s.get("missing_key", None))

    def test_import_v1_is_idempotent(self):
        old = os.path.join(self.dir.name, "old.json")
        with open(old, "w", encoding="utf-8") as f:
            json.dump({"days": {"2026-11-19": {
                "tasks": [{"text": "Read paper", "priority": "High", "category": "Reading", "deadline": "",
                           "done": False, "created": "2026-11-19T09:00:00"},
                          {"text": "Done thing", "priority": "Low", "category": "General", "deadline": "2026-11-18",
                           "done": True}],
                "notes": "old note"}}, "settings": {}}, f)
        self.assertEqual(self.s.import_v1(old), (2, 1))
        self.assertEqual(self.s.import_v1(old), (0, 0))
        self.assertEqual(self.s.daily_note("2026-11-19"), "old note")
        read = [t for t in self.s.tasks("all") if t["title"] == "Read paper"][0]
        self.assertEqual((read["my_day"], read["category"]), ("2026-11-19", "Reading"))

    def test_export_and_backup(self):
        self.s.add_task("x")
        out = os.path.join(self.dir.name, "export.json")
        self.s.export_json(out)
        with open(out, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["tasks"][0]["title"], "x")
        self.assertTrue(os.path.exists(self.s.daily_backup()))
        self.assertIsNone(self.s.daily_backup())  # once per day


if __name__ == "__main__":
    unittest.main()
