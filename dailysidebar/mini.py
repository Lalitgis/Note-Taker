"""The compact sidebar: a slim, movable panel that keeps today one glance away."""
from datetime import date, datetime

from PySide6.QtCore import Qt, QPoint, QRect, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QScrollArea, QSizeGrip, QVBoxLayout, QWidget)

from .widgets import label, button, TaskList, QuickAdd, ProgressRing


class CompactSidebar(QWidget):
    def __init__(self, ctx):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.ctx = ctx
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Daily Sidebar")
        self.setMinimumSize(270, 360)
        self._drag = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        root = QFrame()
        root.setObjectName("miniRoot")
        outer.addWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(14, 10, 12, 8)
        lay.setSpacing(8)

        bar = QHBoxLayout()
        bar.setSpacing(2)
        mark = label("d", "brandMark")
        mark.setStyleSheet("min-width:22px;max-width:22px;min-height:22px;max-height:22px;font-size:13px;border-radius:6px;")
        bar.addWidget(mark)
        bar.addSpacing(6)
        bar.addWidget(label("Today", "cardTitle"))
        bar.addStretch()
        self.pin = button("📌", "iconButton", self.toggle_pin, "Keep on top")
        bar.addWidget(self.pin)
        bar.addWidget(button("⤢", "iconButton", ctx.show_full, "Open the full app"))
        bar.addWidget(button("—", "iconButton", self.hide, "Hide (reopen from the tray or Ctrl+M)"))
        lay.addLayout(bar)

        head = QHBoxLayout()
        clock = QVBoxLayout()
        clock.setSpacing(0)
        self.time = label("", "miniTime")
        self.date = label("", "muted")
        clock.addWidget(self.time)
        clock.addWidget(self.date)
        head.addLayout(clock)
        head.addStretch()
        self.ring = ProgressRing(ctx, 46, 5)
        head.addWidget(self.ring)
        lay.addLayout(head)

        self.focus_row = QFrame()
        self.focus_row.setObjectName("card")
        fr = QHBoxLayout(self.focus_row)
        fr.setContentsMargins(10, 6, 6, 6)
        self.focus_label = label("", "bodyText")
        fr.addWidget(self.focus_label, 1)
        self.focus_btn = button("▶", "iconButton", ctx.focus.toggle, "Start / pause focus")
        fr.addWidget(self.focus_btn)
        lay.addWidget(self.focus_row)

        self.quick = QuickAdd(ctx, lambda: {"my_day": date.today().isoformat()}, compact=True)
        lay.addWidget(self.quick)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        holder.setObjectName("page")
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 4, 0)
        self.tasks = TaskList(ctx, grouped=True, compact=True)
        hl.addWidget(self.tasks)
        self.scroll.setWidget(holder)
        lay.addWidget(self.scroll, 1)

        foot = QHBoxLayout()
        self.summary = label("", "faint")
        foot.addWidget(self.summary)
        foot.addStretch()
        foot.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        lay.addLayout(foot)

        ctx.focus.changed.connect(self._update_focus)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.tick)
        self.clock_timer.start(1000)
        self.apply_settings()
        self.restore_position()
        self.tick()
        self._update_focus()

    # ---- placement ---------------------------------------------------------
    def restore_position(self):
        geo = self.ctx.store.get("compact_geometry", None)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        if geo:
            x, y, w, h = geo
            # make sure it is still on a connected screen
            if any(s.availableGeometry().intersects(QRect(x, y, w, h)) for s in QGuiApplication.screens()):
                self.setGeometry(x, y, w, h)
                return
        w = 320
        self.setGeometry(screen.right() - w - 8, screen.top() + 8, w, screen.height() - 16)

    def snap_right(self):
        screen = (self.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        self.setGeometry(screen.right() - self.width() - 8, screen.top() + 8, self.width(), screen.height() - 16)
        self.remember()

    def remember(self):
        g = self.geometry()
        self.ctx.store.set("compact_geometry", [g.x(), g.y(), g.width(), g.height()])

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() < 110:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self._drag = None
            self._snap_edges()
            self.remember()

    def mouseDoubleClickEvent(self, e):
        if e.position().y() < 110:
            self.snap_right()

    def _snap_edges(self):
        screen = (self.screen() or QGuiApplication.primaryScreen()).availableGeometry()
        g = self.frameGeometry()
        x, y = g.x(), g.y()
        d = 24
        if abs(g.left() - screen.left()) < d:
            x = screen.left()
        if abs(g.right() - screen.right()) < d:
            x = screen.right() - g.width() + 1
        if abs(g.top() - screen.top()) < d:
            y = screen.top()
        if abs(g.bottom() - screen.bottom()) < d:
            y = screen.bottom() - g.height() + 1
        self.move(QPoint(x, y))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.isVisible():
            QTimer.singleShot(400, self.remember)

    # ---- content -----------------------------------------------------------
    def apply_settings(self):
        on_top = bool(self.ctx.store.get("compact_on_top"))
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on_top)
        self.setWindowOpacity(int(self.ctx.store.get("compact_opacity")) / 100)
        self.pin.setStyleSheet("" if on_top else "color: transparent;")
        self.pin.setText("📌")
        self.pin.setToolTip("Pinned on top (click to unpin)" if on_top else "Not on top (click to pin)")
        self.pin.setStyleSheet("" if on_top else "QPushButton { color: gray; }")
        if visible:
            self.show()

    def toggle_pin(self):
        self.ctx.store.set("compact_on_top", not self.ctx.store.get("compact_on_top"))
        self.apply_settings()

    def tick(self):
        now = datetime.now()
        self.time.setText(now.strftime("%H:%M"))
        self.date.setText(now.strftime("%a %d %b") + f"  ·  Week {now.isocalendar()[1]}")

    def refresh(self):
        s = self.ctx.store
        c = s.counts()
        self.ring.set_value(c["today_done"] / c["today"] if c["today"] else 0,
                            f"{c['today_done']}/{c['today']}" if c["today"] else "")
        self.tasks.set_tasks(s.tasks("today"), ("☀", "A clear day", "Add something above."))
        bits = []
        if c["overdue"]:
            bits.append(f"{c['overdue']} overdue")
        if c["week"]:
            bits.append(f"{c['week']} due this week")
        self.summary.setText("  ·  ".join(bits) or "All caught up")

    def _update_focus(self):
        f = self.ctx.focus
        active = f.running or f.remaining < f.length()
        name = {"focus": "Focus", "short": "Break", "long": "Long break"}[f.mode]
        self.focus_label.setText(f"◎  {name}  {f.text()}" + ("" if active else "  ·  ready"))
        self.focus_btn.setText("❚❚" if f.running else "▶")

    def showEvent(self, e):
        self.refresh()
        super().showEvent(e)
