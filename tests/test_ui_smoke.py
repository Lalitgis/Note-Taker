"""Opens every page and exercises the main flows without showing a window."""
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
except ImportError:  # pragma: no cover
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 not installed")
class UiSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        QDialog.exec = lambda self: 0                     # never block on a dialog
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

    def setUp(self):
        from dailysidebar.store import Store
        from dailysidebar.window import MainWindow
        import dailysidebar.window as win
        win.popup_menu = lambda items, pos: None
        self.dir = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.dir.name, "data.db"))
        self.w = MainWindow(self.store)
        self.w.show()
        self.app.processEvents()

    def tearDown(self):
        self.w.quit_app()
        self.store.close()
        self.dir.cleanup()

    def test_flows(self):
        s, w, app = self.store, self.w, self.app
        home = w.pages["Home"]
        home.quick.edit.setText("Write intro !high #writing @Paper tomorrow")
        home.quick.submit()
        t = s.tasks("all")[0]
        self.assertEqual((t["project_name"], t["priority"]), ("Paper", "High"))
        home.quick.edit.setText("Check email")
        home.quick.submit()
        self.assertEqual(len(s.tasks("today")), 1)
        for name in w.pages:
            w.navigate(name)
            app.processEvents()
        w.navigate("Tasks", view="All open")
        tid = s.tasks("today")[0]["id"]
        w.set_task_done(tid, True)
        self.assertEqual(s.task(tid)["done"], 1)
        w.delete_task(tid)
        self.assertIsNone(s.task(tid))
        w.toast_widget._do_action()                       # Undo
        self.assertIsNotNone(s.task(tid))
        w.task_menu(s.task(tid), None)

        from dailysidebar.dialogs import TaskDialog, PaperDialog, ProjectDialog, CommandPalette
        self.assertEqual(TaskDialog(w, s, s.task(tid)).values()["title"], "Check email")
        PaperDialog(w)
        ProjectDialog(w, s.projects()[0])
        self.assertGreater(CommandPalette(w, w, "intro").list.count(), 2)

        notes = w.pages["Notes"]
        w.navigate("Notes")
        notes.editor.setPlainText("hello log")
        notes.save()
        self.assertEqual(s.daily_note(date.today().isoformat()), "hello log")
        notes.new_note()
        notes.title.setText("Idea")
        notes.editor.setPlainText("body")
        notes.save()
        self.assertEqual(s.notes()[0]["title"], "Idea")

        f = w.focus
        f.reset()
        f.start()
        for _ in range(70):
            f._tick()
        f.reset()
        self.assertGreater(s.focus_minutes(date.today().isoformat(), date.today().isoformat()), 1)

        reading = w.pages["Reading"]
        w.navigate("Reading")
        reading.quick.setText("10.1038/ng.548")
        reading.quick_add()
        self.assertEqual(s.papers()[0]["link"], "10.1038/ng.548")

        w.show_compact()
        app.processEvents()
        self.assertTrue(w.compact.isVisible())
        w.toggle_compact()
        w.toggle_theme()
        w.toggle_theme()


if __name__ == "__main__":
    unittest.main()
