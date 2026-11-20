"""Main window. It also acts as the shared context (`ctx`) every page talks to."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt, QTimer, QByteArray
from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence, QShortcut, QAction, QCursor
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu,
                               QPushButton, QScrollArea, QStackedWidget, QSystemTrayIcon, QVBoxLayout, QWidget,
                               QMessageBox)

from . import __version__
from .dialogs import TaskDialog, PaperDialog, ProjectDialog, CommandPalette
from .mini import CompactSidebar
from .pages.calendar import CalendarPage
from .pages.focus import FocusPage, FocusTimer
from .pages.home import HomePage
from .pages.notes import NotesPage
from .pages.projects import ProjectsPage
from .pages.reading import ReadingPage
from .pages.settings import SettingsPage
from .store import PRIORITIES, v1_data_path
from .theme import palette, stylesheet, check_svg
from .widgets import Toast, label, button, popup_menu

APP_NAME = "Daily Sidebar Next"

NAV = [
    ("Home", "⌂"), ("Tasks", "☑"), ("Calendar", "▦"), ("Projects", "◇"),
    ("Reading", "▤"), ("Notes", "✎"), ("Focus", "◎"), ("Settings", "⚙"),
]
SCROLLING = {"Home", "Tasks", "Projects", "Reading", "Settings"}


def resource(*parts) -> str:
    import sys
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)


class NavButton(QPushButton):
    def __init__(self, name, symbol):
        super().__init__()
        self.name = name
        self.setObjectName("navButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(10)
        self.icon_label = QLabel(symbol)
        self.icon_label.setFixedWidth(16)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label = QLabel(name)
        self.badge = QLabel("")
        self.badge.setObjectName("navBadge")
        for w in (self.icon_label, self.text_label, self.badge):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lay.addWidget(self.icon_label)
        lay.addWidget(self.text_label, 1)
        lay.addWidget(self.badge)
        self.setMinimumHeight(34)

    def set_badge(self, text, alert=False):
        self.badge.setText(text)
        self.badge.setObjectName("navBadgeAlert" if alert else "navBadge")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)

    def set_active(self, on, colors):
        self.setChecked(on)
        col = colors["accent"] if on else colors["muted"]
        weight = 650 if on else 400
        for w in (self.icon_label, self.text_label):
            w.setStyleSheet(f"color:{col}; font-weight:{weight}; font-size:13px; background:transparent;")


class MainWindow(QMainWindow):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.colors = palette("light", "Sage")
        self.focus = FocusTimer(store)
        self.current = "Home"
        self.quitting = False
        self.setWindowTitle(APP_NAME)
        icon_path = resource("assets", "icon.png")
        self.app_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.setWindowIcon(self.app_icon)
        self.setMinimumSize(980, 640)
        self.resize(1240, 800)

        central = QWidget()
        central.setObjectName("root")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- sidebar ----
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(232)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(14, 20, 14, 14)
        side.setSpacing(3)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(label("d", "brandMark"))
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label("Daily Sidebar", "brandName"))
        names.addWidget(label("Research planner", "brandSub"))
        brand.addLayout(names)
        brand.addStretch()
        side.addLayout(brand)
        side.addSpacing(16)

        clock = QFrame()
        clock.setObjectName("sideClock")
        cl = QVBoxLayout(clock)
        cl.setContentsMargins(12, 9, 12, 10)
        cl.setSpacing(0)
        self.side_time = label("", "sideTime")
        self.side_date = label("", "muted")
        cl.addWidget(self.side_time)
        cl.addWidget(self.side_date)
        side.addWidget(clock)
        side.addSpacing(14)

        side.addWidget(label("WORKSPACE", "eyebrow"))
        self.nav = {}
        for name, sym in NAV[:-1]:
            b = NavButton(name, sym)
            b.clicked.connect(lambda _=False, n=name: self.navigate(n))
            side.addWidget(b)
            self.nav[name] = b
        side.addStretch()
        self.focus_pill = button("", "ghostButton", lambda: self.navigate("Focus"))
        self.focus_pill.setStyleSheet("text-align:left; padding:8px 10px;")
        side.addWidget(self.focus_pill)
        side.addWidget(label("PREFERENCES", "eyebrow"))
        b = NavButton(*NAV[-1])
        b.clicked.connect(lambda: self.navigate("Settings"))
        side.addWidget(b)
        self.nav["Settings"] = b
        root.addWidget(self.sidebar)

        # ---- main area ----
        main = QFrame()
        main.setObjectName("mainArea")
        ml = QVBoxLayout(main)
        ml.setContentsMargins(32, 18, 32, 22)
        ml.setSpacing(18)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.crumb = label("", "breadcrumb")
        top.addWidget(self.crumb)
        top.addStretch()
        self.search = QLineEdit()
        self.search.setObjectName("searchBox")
        self.search.setPlaceholderText("Search or jump to…        Ctrl+K")
        self.search.setFixedWidth(260)
        self.search.textEdited.connect(self._search_typed)
        self.search.installEventFilter(self)
        top.addWidget(self.search)
        top.addWidget(button("⇥  Compact", None, self.show_compact, "Switch to the compact sidebar (Ctrl+M)"))
        self.theme_btn = button("", None, self.toggle_theme, "Light / dark (Ctrl+D)")
        top.addWidget(self.theme_btn)
        ml.addLayout(top)

        self.stack = QStackedWidget()
        self.stack.setObjectName("pages")
        ml.addWidget(self.stack, 1)
        root.addWidget(main, 1)

        self.pages = {}
        self.page_containers = {}
        classes = {"Home": HomePage, "Tasks": None, "Calendar": CalendarPage, "Projects": ProjectsPage,
                   "Reading": ReadingPage, "Notes": NotesPage, "Focus": FocusPage, "Settings": SettingsPage}
        from .pages.tasks import TasksPage
        classes["Tasks"] = TasksPage
        for name, cls in classes.items():
            page = cls(self)
            self.pages[name] = page
            if name in SCROLLING:
                sc = QScrollArea()
                sc.setWidgetResizable(True)
                sc.setFrameShape(QFrame.Shape.NoFrame)
                sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                wrap = QWidget()
                wrap.setObjectName("page")
                wl = QVBoxLayout(wrap)
                wl.setContentsMargins(0, 0, 10, 0)
                wl.addWidget(page)
                sc.setWidget(wrap)
                container = sc
            else:
                container = page
            self.page_containers[name] = container
            self.stack.addWidget(container)

        self.toast_widget = Toast(central)
        self.compact = CompactSidebar(self)
        self._setup_tray()
        self._setup_shortcuts()

        self.focus.changed.connect(self._update_focus_pill)
        self.focus.finished.connect(self._focus_finished)

        self.clock = QTimer(self)
        self.clock.timeout.connect(self._tick)
        self.clock.start(1000)
        self._last_day = date.today()

        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(lambda _: self.apply_theme())

        self.apply_theme()
        self.restore_window()
        self.navigate("Home")
        self._tick()
        self._update_focus_pill()

    # ------------------------------------------------------------------ setup
    def _setup_tray(self):
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self.app_icon, self)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        menu.addAction("Open Daily Sidebar", self.show_full)
        menu.addAction("Compact sidebar", self.show_compact)
        menu.addSeparator()
        menu.addAction("New task…", lambda: (self.show_full(), self.new_task()))
        self.tray_focus = menu.addAction("Start focus", self.focus.toggle)
        menu.addSeparator()
        menu.addAction("Quit", self.quit_app)
        self.tray_menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_clicked)
        self.tray.show()

    def _tray_clicked(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.isVisible() and not self.isMinimized():
                self.hide()
            elif self.compact.isVisible():
                self.compact.raise_()
                self.compact.activateWindow()
            else:
                self.show_full()

    def _setup_shortcuts(self):
        def sc(keys, fn):
            s = QShortcut(QKeySequence(keys), self)
            s.setContext(Qt.ShortcutContext.ApplicationShortcut)
            s.activated.connect(fn)

        sc("Ctrl+K", self.open_palette)
        sc("Ctrl+N", self.new_task)
        sc("Ctrl+Shift+N", lambda: (self.navigate("Notes"), self.pages["Notes"].new_note()))
        sc("Ctrl+M", self.toggle_compact)
        sc("Ctrl+D", self.toggle_theme)
        sc("Ctrl+Shift+F", self.focus.toggle)
        for i, (name, _) in enumerate(NAV):
            sc(f"Ctrl+{i + 1}", lambda n=name: (self.show_full(), self.navigate(n)))

    # ------------------------------------------------------------------ theme
    def theme_mode(self) -> str:
        t = self.store.get("theme")
        if t in ("light", "dark"):
            return t
        try:
            return "dark" if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark else "light"
        except AttributeError:
            return "light"

    def apply_theme(self):
        mode = self.theme_mode()
        self.colors = palette(mode, self.store.get("accent"))
        family = "Segoe UI" if os.name == "nt" else QApplication.font().family()
        icon = os.path.join(os.path.dirname(os.path.abspath(self.store.path)), f"check-{mode}.svg")
        try:
            with open(icon, "w", encoding="utf-8") as f:
                f.write(check_svg(self.colors["accent_text"]))
        except OSError:
            icon = ""
        QApplication.instance().setStyleSheet(stylesheet(self.colors, family, icon.replace(os.sep, "/")))
        self.theme_btn.setText("☀  Light" if mode == "dark" else "☾  Dark")
        for n, b in self.nav.items():
            b.set_active(n == self.current, self.colors)
        self.refresh()
        self.compact.refresh()

    def toggle_theme(self):
        self.store.set("theme", "light" if self.theme_mode() == "dark" else "dark")
        self.apply_theme()
        if "Settings" in self.pages:
            s = self.pages["Settings"]
            s.theme.set_current({"light": "Light", "dark": "Dark"}[self.store.get("theme")])

    def apply_compact_settings(self):
        self.compact.apply_settings()

    # ------------------------------------------------------------------ navigation
    def navigate(self, name, view=None, day=None, project=None):
        if self.current == "Notes" and name != "Notes":
            self.pages["Notes"].save()
        self.current = name
        page = self.pages[name]
        if view and hasattr(page, "set_view"):
            page.set_view(view)
        self.stack.setCurrentWidget(self.page_containers[name])
        for n, b in self.nav.items():
            b.set_active(n == name, self.colors)
        self.crumb.setText(f"Workspace  /  {name}")
        page.refresh()
        if day and name == "Notes":
            page.open_day(date.fromisoformat(day))
        if project and name == "Projects":
            page.open_project(project)

    def refresh(self):
        """Re-read data for the visible page, the nav badges and the compact sidebar."""
        if not hasattr(self, "pages"):
            return
        self.pages[self.current].refresh()
        c = self.store.counts()
        open_today = c["today"] - c["today_done"]
        self.nav["Tasks"].set_badge(str(c["overdue"]) if c["overdue"] else (str(open_today) if open_today else ""),
                                    alert=c["overdue"] > 0)
        self.nav["Tasks"].setToolTip(f"{open_today} open today · {c['overdue']} overdue")
        reading = self.store.paper_counts()["Reading"]
        self.nav["Reading"].set_badge(str(reading) if reading else "")
        if self.compact.isVisible():
            self.compact.refresh()

    notify = refresh

    def _tick(self):
        now = datetime.now()
        self.side_time.setText(now.strftime("%H:%M"))
        self.side_date.setText(now.strftime("%a %d %b") + f"  ·  W{now.isocalendar()[1]}")
        if self.isVisible():
            self.pages[self.current].tick()
        if date.today() != self._last_day:       # midnight: today's view changes
            self._last_day = date.today()
            self.refresh()
            self.compact.refresh()
            try:
                self.store.daily_backup()
            except Exception:
                pass

    def _update_focus_pill(self):
        f = self.focus
        if f.running or f.remaining < f.length():
            name = {"focus": "Focus", "short": "Break", "long": "Long break"}[f.mode]
            state = "" if f.running else "  (paused)"
            self.focus_pill.setText(f"◎  {name}  {f.text()}{state}")
            self.focus_pill.show()
        else:
            self.focus_pill.hide()
        if self.tray:
            self.tray_focus.setText("Pause focus" if f.running else "Start focus")
            self.tray.setToolTip(f"{APP_NAME}  ·  {f.text()}" if f.running else APP_NAME)

    def _focus_finished(self, title, message):
        if self.tray:
            self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 6000)
        self.toast(f"{title}. {message}")
        if self.current == "Focus":
            self.pages["Focus"].refresh()

    # ------------------------------------------------------------------ toast
    def toast(self, text, action=None, callback=None):
        target = self if self.isVisible() else None
        if target:
            self.toast_widget.show_message(text, action, callback)
        elif self.tray and not action:
            pass

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.toast_widget.isVisible():
            self.toast_widget.reposition()

    # ------------------------------------------------------------------ tasks
    def _dialog_parent(self):
        return self if self.isVisible() else self.compact

    def new_task(self, defaults=None):
        if defaults is None:
            defaults = {}
            if self.current == "Projects" and self.pages["Projects"].current:
                defaults["project_id"] = self.pages["Projects"].current
        if not defaults.get("due"):
            defaults.setdefault("my_day", date.today().isoformat())
        dlg = TaskDialog(self._dialog_parent(), self.store, None, defaults)
        if dlg.exec():
            v = dlg.values()
            self.store.add_task(**v)
            self.notify()
            self.toast(f"Added “{v['title'].strip()}”")

    def edit_task(self, tid):
        t = self.store.task(tid)
        if not t:
            return
        dlg = TaskDialog(self._dialog_parent(), self.store, t)
        if not dlg.exec():
            return
        if dlg.deleted:
            self.delete_task(tid)
            return
        v = dlg.values()
        if v["my_day"] and t["my_day"] and t["my_day"] >= date.today().isoformat():
            v["my_day"] = t["my_day"]
        self.store.update_task(tid, **v)
        self.notify()

    def delete_task(self, tid):
        row = self.store.delete_task(tid)
        self.notify()
        if row:
            self.toast(f"Deleted “{row['title']}”", "Undo", lambda: (self.store.restore_task(row), self.notify()))

    def set_task_done(self, tid, done):
        t = self.store.task(tid)
        if not t or bool(t["done"]) == bool(done):
            return
        nxt = self.store.set_done(tid, done)
        self.notify()
        if done:
            msg = f"Completed “{t['title']}”"
            if nxt:
                msg += f" · next one {date.fromisoformat(nxt['due']).strftime('%a %d %b')}"
            self.toast(msg, "Undo", lambda: (self.store.set_done(tid, False),
                                             nxt and self.store.delete_task(nxt["id"]), self.notify()))

    def task_menu(self, t, pos):
        s = self.store
        tid = t["id"]
        today = date.today()

        def due(days):
            return lambda: (s.update_task(tid, due=(today + timedelta(days=days)).isoformat()), self.notify())

        next_monday = (7 - today.weekday()) % 7 or 7
        items = [("Edit…", lambda: self.edit_task(tid)),
                 ("Mark as not done" if t["done"] else "Mark as done", lambda: self.set_task_done(tid, not t["done"])),
                 None]
        if t.get("my_day") and t["my_day"] <= today.isoformat():
            items.append(("Remove from My Day", lambda: (s.update_task(tid, my_day=""), self.notify())))
        else:
            items.append(("Add to My Day", lambda: (s.update_task(tid, my_day=today.isoformat()), self.notify())))
        items.append(("Due", [("Today", due(0)), ("Tomorrow", due(1)), ("Next Monday", due(next_monday)),
                              ("In a week", due(7)), None,
                              ("No due date", lambda: (s.update_task(tid, due=""), self.notify()))]))
        items.append(("Priority", [(p, (lambda p=p: (s.update_task(tid, priority=p), self.notify())))
                                   for p in PRIORITIES]))
        projects = s.projects(include_done=False)
        proj_items = [(p["name"], (lambda pid=p["id"]: (s.update_task(tid, project_id=pid), self.notify())))
                      for p in projects]
        proj_items += [None, ("No project", lambda: (s.update_task(tid, project_id=None), self.notify()))]
        items.append(("Move to project", proj_items))
        items.append(("Focus on this", lambda: self.focus_on(tid)))
        items += [None, ("Delete", lambda: self.delete_task(tid))]
        popup_menu(items, pos)

    def focus_on(self, tid):
        self.focus.task_id = tid
        if self.focus.mode != "focus":
            self.focus.set_mode("focus")
        self.show_full()
        self.navigate("Focus")
        self.focus.start()

    # ------------------------------------------------------------------ other dialogs
    def new_paper(self):
        dlg = PaperDialog(self)
        if dlg.exec():
            v = dlg.values()
            self.store.add_paper(v.pop("title"), **v)
            self.notify()

    def edit_paper(self, pid):
        p = self.store.paper(pid)
        if not p:
            return
        dlg = PaperDialog(self, p)
        if not dlg.exec():
            return
        if dlg.deleted:
            self.store.delete_paper(pid)
        else:
            v = dlg.values()
            if not v["title"]:
                v["title"] = v["link"]
            self.store.update_paper(pid, **v)
        self.notify()

    def new_project(self):
        dlg = ProjectDialog(self)
        if dlg.exec():
            v = dlg.values()
            p = self.store.add_project(v["name"], v["color"], v["description"], v["status"], v["deadline"])
            self.notify()
            return p["id"]
        return None

    def edit_project(self, pid):
        p = self.store.project(pid)
        dlg = ProjectDialog(self, p)
        if not dlg.exec():
            return None
        if dlg.deleted:
            self.store.delete_project(pid)
            self.notify()
            return "deleted"
        self.store.update_project(pid, **dlg.values())
        self.notify()
        return "saved"

    # ------------------------------------------------------------------ palette
    def eventFilter(self, obj, ev):
        if obj is self.search and ev.type() == ev.Type.MouseButtonPress:
            QTimer.singleShot(0, self.open_palette)
            return True
        return super().eventFilter(obj, ev)

    def _search_typed(self, text):
        self.search.clear()
        self.open_palette(text)

    def open_palette(self, initial=""):
        self.show_full()
        CommandPalette(self, self, initial if isinstance(initial, str) else "").exec()

    def commands(self):
        cmds = [(f"Go to {n}", ("nav", n)) for n, _ in NAV]
        cmds += [("New task", ("new_task",)), ("New note", ("new_note",)), ("New project", ("new_project",)),
                 ("Add paper", ("new_paper",)), ("Start / pause focus", ("focus",)),
                 ("Switch to compact sidebar", ("compact",)), ("Toggle light / dark", ("theme",)),
                 ("Open today's daily log", ("today_log",))]
        return cmds

    def open_result(self, kind, value):
        if kind == "task":
            t = self.store.task(value)
            if t and t["project_id"]:
                self.navigate("Projects", project=t["project_id"])
            else:
                self.navigate("Tasks", view="All open" if t and not t["done"] else "Done")
            self.edit_task(value)
        elif kind == "project":
            self.navigate("Projects", project=value)
        elif kind == "paper":
            self.navigate("Reading")
            self.edit_paper(value)
        elif kind == "note":
            self.navigate("Notes")
            self.pages["Notes"].open_note(value)
        elif kind == "daily":
            self.navigate("Notes", day=value)
        elif kind == "newtask":
            try:
                t = self.store.quick_add(value, {"my_day": date.today().isoformat()})
                self.notify()
                self.toast(f"Added “{t['title']}”")
            except ValueError as e:
                self.toast(str(e))
        elif kind == "cmd":
            a = value
            if a[0] == "nav":
                self.navigate(a[1])
            elif a[0] == "new_task":
                self.new_task()
            elif a[0] == "new_note":
                self.navigate("Notes")
                self.pages["Notes"].new_note()
            elif a[0] == "new_project":
                self.navigate("Projects")
                self.pages["Projects"].new_project()
            elif a[0] == "new_paper":
                self.navigate("Reading")
                self.new_paper()
            elif a[0] == "focus":
                self.focus.toggle()
            elif a[0] == "compact":
                self.show_compact()
            elif a[0] == "theme":
                self.toggle_theme()
            elif a[0] == "today_log":
                self.navigate("Notes", day=date.today().isoformat())

    # ------------------------------------------------------------------ windows
    def show_full(self):
        self.compact.hide()
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()
        self.refresh()

    def show_compact(self):
        self.save_window()
        self.hide()
        self.compact.show()
        self.compact.raise_()
        self.compact.activateWindow()

    def toggle_compact(self):
        if self.compact.isVisible():
            self.show_full()
        else:
            self.show_compact()

    def restore_window(self):
        geo = self.store.get("window_geometry", None)
        if geo:
            self.restoreGeometry(QByteArray.fromBase64(geo.encode()))

    def save_window(self):
        if self.isVisible():
            self.store.set("window_geometry", bytes(self.saveGeometry().toBase64()).decode())

    def closeEvent(self, e):
        self.save_window()
        self.pages["Notes"].save()
        if not self.quitting and self.store.get("close_to_tray") and self.tray:
            e.ignore()
            self.hide()
            if not self.store.get("tray_hint_shown"):
                self.tray.showMessage(APP_NAME, "Still running here. Right-click the icon for options, "
                                                "or turn this off in Settings.",
                                      QSystemTrayIcon.MessageIcon.Information, 5000)
                self.store.set("tray_hint_shown", True)
            return
        self.quit_app()

    def quit_app(self):
        self.quitting = True
        self.save_window()
        try:
            self.pages["Notes"].save()
            if self.focus.running:
                self.focus.reset()   # keeps the minutes already focused
        except Exception:
            pass
        if self.tray:
            self.tray.hide()
        self.compact.close()
        QApplication.instance().quit()

    def first_run(self):
        """Offer data from the first Daily Sidebar, and make the daily backup."""
        try:
            self.store.daily_backup()
        except Exception:
            pass
        old = v1_data_path()
        if self.store.get("imported_v1") or not os.path.exists(old) or not self.store.is_empty():
            return
        self.store.set("imported_v1", True)
        r = QMessageBox.question(self, "Bring your tasks along?",
                                 "Found data from the first Daily Sidebar on this computer.\n\n"
                                 "Import its tasks and daily notes? The old file is only read, not changed.")
        if r == QMessageBox.StandardButton.Yes:
            try:
                n, m = self.store.import_v1(old)
                self.notify()
                self.toast(f"Imported {n} tasks and {m} daily notes")
            except (OSError, ValueError) as e:
                QMessageBox.warning(self, "Import failed", str(e))
