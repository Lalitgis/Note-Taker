import os
import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QHBoxLayout, QMessageBox, QPushButton, QSpinBox,
                               QSlider, QGridLayout)

from .. import __version__
from ..store import v1_data_path
from ..theme import ACCENTS
from ..widgets import Page, label, button, card, Segmented, divider

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "DailySidebarNext"


def startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    main = os.path.abspath(sys.argv[0])
    return f'"{exe}" "{main}"'


def get_startup() -> bool:
    if os.name != "nt":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
            return True
    except OSError:
        return False


def set_startup(on: bool):
    if os.name != "nt":
        raise OSError("Start with Windows is only available on Windows")
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except OSError:
                pass


SHORTCUTS = [
    ("Ctrl+K", "Search and commands"), ("Ctrl+N", "New task"), ("Ctrl+Shift+N", "New note"),
    ("Ctrl+1 … 8", "Switch page"), ("Ctrl+M", "Compact sidebar"), ("Ctrl+D", "Light / dark"),
    ("Ctrl+Shift+F", "Start / pause focus"),
]


class SettingsPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx, "Settings", "Make the workspace yours.")
        s = ctx.store
        cols = QHBoxLayout()
        cols.setSpacing(16)
        left = QGridLayout()

        # Appearance
        ap, al = card(spacing=12)
        al.addWidget(label("Appearance", "sectionTitle"))
        row = QHBoxLayout()
        row.addWidget(label("Theme", "bodyText"))
        row.addStretch()
        names = {"system": "System", "light": "Light", "dark": "Dark"}
        self.theme = Segmented(list(names.values()), names.get(s.get("theme"), "System"))
        self.theme.changed.connect(lambda v: self._set("theme", {b: a for a, b in names.items()}[v], theme=True))
        row.addWidget(self.theme)
        al.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(label("Accent colour", "bodyText"))
        row.addStretch()
        self.swatches = {}
        for name, modes in ACCENTS.items():
            b = QPushButton()
            b.setObjectName("swatch")
            b.setToolTip(name)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, n=name: self._set("accent", n, theme=True))
            self.swatches[name] = (b, modes["light"][0])
            row.addWidget(b)
        al.addLayout(row)

        # Compact sidebar
        cp, cl = card(spacing=10)
        cl.addWidget(label("Compact sidebar", "sectionTitle"))
        cl.addWidget(label("A slim always-at-hand panel with the clock, today's tasks and the focus timer. "
                           "Open it with Ctrl+M, the ⇥ button, or from the tray icon.", "mutedBody", wrap=True))
        self.c_top = self._check("Keep on top of other windows", "compact_on_top", cl)
        self.c_start = self._check("Open in compact mode when the app starts", "start_compact", cl)
        row = QHBoxLayout()
        row.addWidget(label("Opacity", "bodyText"))
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(40, 100)
        self.opacity.setValue(int(s.get("compact_opacity")))
        self.opacity.valueChanged.connect(lambda v: (s.set("compact_opacity", v), ctx.apply_compact_settings()))
        row.addWidget(self.opacity, 1)
        cl.addLayout(row)

        # Focus
        fo, fl = card(spacing=10)
        fl.addWidget(label("Focus timer", "sectionTitle"))
        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)
        for i, (text, key, lo, hi) in enumerate([("Focus length", "focus_minutes", 5, 120),
                                                  ("Short break", "short_break", 1, 30),
                                                  ("Long break", "long_break", 5, 60),
                                                  ("Sessions before a long break", "sessions_before_long", 2, 8)]):
            sp = QSpinBox()
            sp.setFixedWidth(110)
            sp.setRange(lo, hi)
            sp.setValue(int(s.get(key)))
            if key != "sessions_before_long":
                sp.setSuffix(" min")
            sp.valueChanged.connect(lambda v, k=key: self._set_focus(k, v))
            g.addWidget(label(text, "bodyText"), i, 0)
            g.addWidget(sp, i, 1)
        g.setColumnStretch(2, 1)
        fl.addLayout(g)
        self._check("Play a sound when a session ends", "focus_sound", fl)

        # Behaviour
        be, bl = card(spacing=10)
        bl.addWidget(label("Behaviour", "sectionTitle"))
        self._check("Closing the window keeps the app running in the tray", "close_to_tray", bl)
        self.startup = QCheckBox("Start Daily Sidebar when I sign in to Windows")
        self.startup.setEnabled(os.name == "nt")
        self.startup.setChecked(get_startup())
        self.startup.toggled.connect(self._startup)
        bl.addWidget(self.startup)

        # Data
        da, dl = card(spacing=10)
        dl.addWidget(label("Your data", "sectionTitle"))
        dl.addWidget(label("Everything stays on this computer, in one file. A backup copy is made each day "
                           "(the last 10 are kept).", "mutedBody", wrap=True))
        self.path_label = label(s.path, "faint", wrap=True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dl.addWidget(self.path_label)
        row = QHBoxLayout()
        row.addWidget(button("Open data folder", None, self._open_folder))
        row.addWidget(button("Export backup (JSON)…", None, self._export))
        row.addWidget(button("Import from Daily Sidebar…", None, self._import))
        row.addStretch()
        dl.addLayout(row)

        # About
        ab, abl = card(spacing=8)
        abl.addWidget(label("Keyboard shortcuts", "sectionTitle"))
        kg = QGridLayout()
        kg.setVerticalSpacing(6)
        for i, (k, what) in enumerate(SHORTCUTS):
            kg.addWidget(label(k, "kbd"), i, 0, Qt.AlignmentFlag.AlignLeft)
            kg.addWidget(label(what, "bodyText"), i, 1)
        kg.setColumnStretch(1, 1)
        kg.setHorizontalSpacing(12)
        abl.addLayout(kg)
        abl.addWidget(divider())
        abl.addWidget(label("Quick-add syntax", "cardTitle"))
        abl.addWidget(label("!high  !low  ·  #category  ·  @project  ·  today, tomorrow, fri, +3, 12/03  ·  "
                            "*daily  *weekly", "mutedBody", wrap=True))
        abl.addWidget(divider())
        abl.addWidget(label(f"Daily Sidebar Next {__version__}", "muted"))

        lcol = QGridLayout()
        lcol.setSpacing(14)
        lcol.addWidget(ap, 0, 0)
        lcol.addWidget(fo, 1, 0)
        lcol.addWidget(be, 2, 0)
        lcol.addWidget(da, 3, 0)
        lcol.setRowStretch(4, 1)
        rcol = QGridLayout()
        rcol.setSpacing(14)
        rcol.addWidget(cp, 0, 0)
        rcol.addWidget(ab, 1, 0)
        rcol.setRowStretch(2, 1)
        cols.addLayout(lcol, 3)
        cols.addLayout(rcol, 2)
        self.outer.addLayout(cols, 1)
        self.refresh()

    def _check(self, text, key, lay):
        cb = QCheckBox(text)
        cb.setChecked(bool(self.ctx.store.get(key)))
        cb.toggled.connect(lambda v: self._set(key, v))
        lay.addWidget(cb)
        return cb

    def _set(self, key, value, theme=False):
        self.ctx.store.set(key, value)
        if theme:
            self.ctx.apply_theme()
            self.refresh()
        if key.startswith("compact"):
            self.ctx.apply_compact_settings()

    def _set_focus(self, key, value):
        self.ctx.store.set(key, value)
        if not self.ctx.focus.running:
            self.ctx.focus.reset()

    def _startup(self, on):
        try:
            set_startup(on)
            self.ctx.toast("Will start when you sign in" if on else "Won't start automatically")
        except OSError as e:
            self.ctx.toast(f"Couldn't change startup: {e}")

    def _open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(self.ctx.store.path)))

    def _export(self):
        from datetime import date
        path, _ = QFileDialog.getSaveFileName(self, "Export backup",
                                              os.path.expanduser(f"~/DailySidebar-backup-{date.today()}.json"),
                                              "JSON (*.json)")
        if path:
            self.ctx.store.export_json(path)
            self.ctx.toast("Backup exported")

    def _import(self):
        start = v1_data_path()
        path, _ = QFileDialog.getOpenFileName(self, "Import from Daily Sidebar",
                                              start if os.path.exists(start) else os.path.expanduser("~"),
                                              "Daily Sidebar data (*.json)")
        if not path:
            return
        try:
            n, m = self.ctx.store.import_v1(path)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Import failed", f"Couldn't read that file.\n\n{e}")
            return
        self.ctx.notify()
        self.ctx.toast(f"Imported {n} tasks and {m} daily notes")

    def refresh(self):
        cur = self.ctx.store.get("accent")
        for name, (b, col) in self.swatches.items():
            ring = f"3px solid {self.ctx.colors['text']}" if name == cur else f"1px solid {self.ctx.colors['border']}"
            b.setStyleSheet(f"background:{col}; border:{ring};")
