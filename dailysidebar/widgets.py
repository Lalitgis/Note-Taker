"""Reusable widgets shared by the pages and the compact sidebar."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QTimer, Signal, QRectF, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QAction
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QCheckBox,
    QLineEdit, QMenu, QSizePolicy, QGraphicsOpacityEffect, QLayout,
)

from .store import due_info, group_label, GROUP_ORDER, PRIORITIES


def label(text="", name=None, wrap=False, parent=None) -> QLabel:
    lb = QLabel(text, parent)
    if name:
        lb.setObjectName(name)
    if wrap:
        lb.setWordWrap(True)
    return lb


def button(text, name=None, on_click=None, tip=None) -> QPushButton:
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if on_click:
        b.clicked.connect(on_click)
    if tip:
        b.setToolTip(tip)
    return b


def hbox(*items, spacing=8, margins=(0, 0, 0, 0)) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(spacing)
    lay.setContentsMargins(*margins)
    for it in items:
        _add(lay, it)
    return lay


def vbox(*items, spacing=8, margins=(0, 0, 0, 0)) -> QVBoxLayout:
    lay = QVBoxLayout()
    lay.setSpacing(spacing)
    lay.setContentsMargins(*margins)
    for it in items:
        _add(lay, it)
    return lay


def _add(lay, it):
    if it is None:
        lay.addStretch()
    elif isinstance(it, int):
        lay.addSpacing(it)
    elif isinstance(it, QLayout):
        lay.addLayout(it)
    else:
        lay.addWidget(it)


def clear_layout(lay):
    while lay.count():
        item = lay.takeAt(0)
        w = item.widget()
        if w is not None:
            w.hide()
            w.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def card(name="card", margins=(16, 14, 16, 14), spacing=8):
    f = QFrame()
    f.setObjectName(name)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return f, lay


def divider() -> QFrame:
    f = QFrame()
    f.setObjectName("divider")
    return f


class Page(QWidget):
    """Base page: title, subtitle and a content layout. Subclasses implement refresh()."""

    def __init__(self, ctx, title, subtitle=""):
        super().__init__()
        self.ctx = ctx
        self.setObjectName("page")
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.outer.setSpacing(16)
        self.header = QHBoxLayout()
        self.header.setSpacing(10)
        titles = vbox(spacing=2)
        self.title_label = label(title, "pageTitle")
        self.subtitle_label = label(subtitle, "pageSubtitle")
        titles.addWidget(self.title_label)
        titles.addWidget(self.subtitle_label)
        self.header.addLayout(titles)
        self.header.addStretch()
        self.outer.addLayout(self.header)

    def refresh(self):
        pass

    def tick(self):
        """Called every second while the page is visible."""


class ElidedLabel(QLabel):
    """A one-line label that ends with … when there isn't room."""

    def __init__(self, text="", name=None):
        super().__init__()
        self.full = text
        if name:
            self.setObjectName(name)
        self.setToolTip(text)
        self.setMinimumWidth(10)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        super().setText(text)

    def resizeEvent(self, e):
        m = self.contentsMargins()
        avail = self.width() - m.left() - m.right() - 8
        super().setText(self.fontMetrics().elidedText(self.full, Qt.TextElideMode.ElideRight, max(10, avail)))
        super().resizeEvent(e)


class Segmented(QFrame):
    """A row of mutually exclusive pill buttons."""
    changed = Signal(str)

    def __init__(self, options, current=None):
        super().__init__()
        self.setObjectName("segmentBar")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self.buttons = {}
        for key in options:
            b = QPushButton(key)
            b.setObjectName("segment")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.set_current(k, emit=True))
            lay.addWidget(b)
            self.buttons[key] = b
        self.current = current or options[0]
        self.set_current(self.current)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def set_current(self, key, emit=False):
        self.current = key
        for k, b in self.buttons.items():
            b.setChecked(k == key)
        if emit:
            self.changed.emit(key)

    def set_label(self, key, text):
        self.buttons[key].setText(text)


class EmptyState(QFrame):
    def __init__(self, icon, title, detail=""):
        super().__init__()
        self.setObjectName("emptyPanel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 26, 20, 26)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for text, name in ((icon, "emptyIcon"), (title, "cardTitle"), (detail, "mutedBody")):
            if text:
                lb = label(text, name, wrap=True)
                lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lay.addWidget(lb)


# --------------------------------------------------------------------------
# Tasks
# --------------------------------------------------------------------------

def due_chip(task) -> QLabel | None:
    text, tone = due_info(task.get("due") or "", bool(task.get("done")))
    if not text:
        return None
    name = {"danger": "chipDanger", "warn": "chipWarn"}.get(tone, "chip")
    return label("◷ " + text, name)


class TaskRow(QFrame):
    def __init__(self, ctx, task, compact=False, show_project=True):
        super().__init__()
        self.ctx = ctx
        self.task = task
        done = bool(task["done"])
        self.setObjectName("taskRowDone" if done else "taskRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        m = (10, 7, 8, 7) if compact else (12, 9, 10, 9)
        lay.setContentsMargins(*m)
        lay.setSpacing(10)

        self.check = QCheckBox()
        self.check.setObjectName("taskCheckHigh" if task["priority"] == "High" and not done else "taskCheck")
        self.check.setChecked(done)
        self.check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check.setToolTip("Mark as done" if not done else "Mark as not done")
        self.check.toggled.connect(self._toggled)
        lay.addWidget(self.check, 0, Qt.AlignmentFlag.AlignTop if not compact else Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(4)
        title = label(task["title"], "taskTitleDone" if done else "taskTitle", wrap=True)
        if done:
            f = title.font()
            f.setStrikeOut(True)
            title.setFont(f)
        col.addWidget(title)

        chips = []
        dc = due_chip(task)
        if dc:
            chips.append(dc)
        if task.get("my_day") and not task.get("due") and not done:
            chips.append(label("☀ My Day", "chipAccent"))
        if show_project and task.get("project_name"):
            pl = label(f"<span style='color:{task['project_color']}'>●</span> {task['project_name']}", "chip")
            pl.setTextFormat(Qt.TextFormat.RichText)
            chips.append(pl)
        if task.get("category"):
            chips.append(label("#" + task["category"], "chip"))
        if task.get("repeat"):
            chips.append(label("↻ " + task["repeat"], "chip"))
        if task.get("notes"):
            chips.append(label("≡", "chip"))
        if chips and not (compact and done):
            row = QHBoxLayout()
            row.setSpacing(5)
            for c in chips[: (2 if compact else 6)]:
                row.addWidget(c)
            row.addStretch()
            col.addLayout(row)
        lay.addLayout(col, 1)

        if not done and task["priority"] != "Medium" and not compact:
            p = label(task["priority"].upper(), "chipDanger" if task["priority"] == "High" else "chip")
            lay.addWidget(p, 0, Qt.AlignmentFlag.AlignTop)

        self.menu_btn = button("⋯", "iconButton", self._show_menu, "More")
        self.menu_btn.setVisible(False)
        lay.addWidget(self.menu_btn, 0, Qt.AlignmentFlag.AlignTop)

    def enterEvent(self, e):
        self.menu_btn.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.menu_btn.setVisible(False)
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            # single click opens the editor too: rows are the main way into a task
            QTimer.singleShot(0, lambda: self.ctx.edit_task(self.task["id"]))
        super().mouseReleaseEvent(e)

    def contextMenuEvent(self, e):
        self._show_menu(e.globalPos())

    def _toggled(self, checked):
        QTimer.singleShot(120, lambda: self.ctx.set_task_done(self.task["id"], checked))

    def _show_menu(self, pos=None):
        if not isinstance(pos, QPoint):
            pos = self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft())
        self.ctx.task_menu(self.task, pos)


class TaskList(QWidget):
    """Shows tasks, optionally grouped under Overdue / Today / Tomorrow / ..."""

    def __init__(self, ctx, grouped=True, compact=False, show_project=True):
        super().__init__()
        self.ctx = ctx
        self.grouped = grouped
        self.compact = compact
        self.show_project = show_project
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(6 if not compact else 4)
        self.collapsed_done = True

    def set_tasks(self, tasks, empty=("✓", "Nothing here", ""), group_fn=None, done_collapsible=True):
        clear_layout(self.lay)
        if not tasks:
            self.lay.addWidget(EmptyState(*empty))
            self.lay.addStretch()
            return
        if not self.grouped:
            for t in tasks:
                self.lay.addWidget(TaskRow(self.ctx, t, self.compact, self.show_project))
            self.lay.addStretch()
            return
        group_fn = group_fn or group_label
        groups: dict[str, list] = {}
        for t in tasks:
            groups.setdefault(group_fn(t), []).append(t)
        order = [g for g in GROUP_ORDER if g in groups] + [g for g in groups if g not in GROUP_ORDER]
        for g in order:
            items = groups[g]
            head = QHBoxLayout()
            name = "groupHeaderAlert" if g == "Overdue" else "groupHeader"
            hl = label(f"{g.upper()}   {len(items)}", name)
            head.addWidget(hl)
            head.addStretch()
            if g == "Completed" and done_collapsible:
                tog = button("Show" if self.collapsed_done else "Hide", "ghostButton", self._toggle_done)
                head.addWidget(tog)
            self.lay.addLayout(head)
            if g == "Completed" and done_collapsible and self.collapsed_done:
                continue
            for t in items:
                self.lay.addWidget(TaskRow(self.ctx, t, self.compact, self.show_project))
        self.lay.addStretch()

    def _toggle_done(self):
        self.collapsed_done = not self.collapsed_done
        self.ctx.refresh()


class QuickAdd(QWidget):
    """Single-line task entry that understands !high #category @project and dates."""
    added = Signal(dict)

    HINT = "Add a task…   try: Read GWAS paper !high #reading @Thesis fri"

    def __init__(self, ctx, defaults_fn=None, placeholder=None, compact=False):
        super().__init__()
        self.ctx = ctx
        self.defaults_fn = defaults_fn or (lambda: {})
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.edit = QLineEdit()
        self.edit.setObjectName("quickAdd")
        self.edit.setPlaceholderText(placeholder or ("Add a task…" if compact else self.HINT))
        self.edit.setClearButtonEnabled(True)
        self.edit.returnPressed.connect(self.submit)
        self.edit.setToolTip("Shortcuts while typing:\n"
                             "  !high  !low          priority\n"
                             "  #reading             category\n"
                             "  @Thesis              project (created if new)\n"
                             "  today, tomorrow, fri, +3, 12/03, 2026-12-01   due date\n"
                             "  *daily  *weekly  *weekdays  *monthly   repeat")
        lay.addWidget(self.edit, 1)
        self.add_btn = button("+ Add" if not compact else "+", "primaryButton", self.submit, "Add task (Enter)")
        lay.addWidget(self.add_btn)

    def submit(self):
        text = self.edit.text().strip()
        if not text:
            self.edit.setFocus()
            return
        try:
            task = self.ctx.store.quick_add(text, self.defaults_fn())
        except ValueError as e:
            self.ctx.toast(str(e))
            return
        self.edit.clear()
        self.ctx.notify()
        self.ctx.toast(f"Added “{task['title']}”")
        self.added.emit(task)

    def focus(self):
        self.edit.setFocus()
        self.edit.selectAll()


# --------------------------------------------------------------------------
# Painted widgets
# --------------------------------------------------------------------------

class ProgressRing(QWidget):
    def __init__(self, ctx, size=54, width=6):
        super().__init__()
        self.ctx = ctx
        self.value = 0.0
        self.text = ""
        self.ring_width = width
        self.setFixedSize(size, size)

    def set_value(self, value, text=""):
        self.value = max(0.0, min(1.0, value))
        self.text = text
        self.update()

    def paintEvent(self, _):
        c = self.ctx.colors
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.ring_width
        r = QRectF(w / 2, w / 2, self.width() - w, self.height() - w)
        pen = QPen(QColor(c["sidebar"] if c["mode"] == "light" else c["border"]), w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawEllipse(r)
        if self.value > 0:
            pen.setColor(QColor(c["accent"]))
            p.setPen(pen)
            p.drawArc(r, 90 * 16, int(-self.value * 360 * 16))
        if self.text:
            p.setPen(QColor(c["text"]))
            f = QFont(self.font())
            f.setPixelSize(max(10, int(self.height() * (0.22 if len(self.text) <= 4 else 0.15))))
            f.setBold(True)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text)


class BarChart(QWidget):
    """Tiny bar chart: [(label, value)], value in minutes."""

    def __init__(self, ctx, height=120):
        super().__init__()
        self.ctx = ctx
        self.data = []
        self.highlight_last = True
        self.setMinimumHeight(height)

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, _):
        if not self.data:
            return
        c = self.ctx.colors
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        n = len(self.data)
        top, bottom = 16, 20
        h = self.height() - top - bottom
        slot = self.width() / n
        bw = min(28, slot * 0.55)
        mx = max([v for _, v in self.data] + [30])
        f = QFont(self.font())
        f.setPixelSize(10)
        p.setFont(f)
        for i, (lab, v) in enumerate(self.data):
            x = i * slot + (slot - bw) / 2
            bh = max(3, h * v / mx) if v > 0 else 3
            color = QColor(c["accent"]) if (i == n - 1 and self.highlight_last) else QColor(c["accent"])
            if not (i == n - 1 and self.highlight_last):
                color.setAlpha(110)
            if v <= 0:
                color = QColor(c["border"])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(x, top + h - bh, bw, bh), 4, 4)
            p.setPen(QColor(c["muted"]))
            p.drawText(QRectF(i * slot, self.height() - bottom + 4, slot, bottom - 4),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, lab)
            if v > 0:
                txt = f"{int(v)}m" if v < 60 else f"{v / 60:.1f}h"
                p.drawText(QRectF(i * slot, top + h - bh - 15, slot, 14),
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, txt)


class TimerDial(QWidget):
    def __init__(self, ctx, size=240):
        super().__init__()
        self.ctx = ctx
        self.fraction = 0.0
        self.on_break = False
        self.setFixedSize(size, size)

    def set_fraction(self, f, on_break=False):
        self.fraction = max(0.0, min(1.0, f))
        self.on_break = on_break
        self.update()

    def paintEvent(self, _):
        c = self.ctx.colors
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = 10
        r = QRectF(w, w, self.width() - 2 * w, self.height() - 2 * w)
        pen = QPen(QColor(c["border"]), w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawEllipse(r)
        if self.fraction > 0:
            pen.setColor(QColor(c["low"] if self.on_break else c["accent"]))
            p.setPen(pen)
            p.drawArc(r, 90 * 16, int(-self.fraction * 360 * 16))


# --------------------------------------------------------------------------
# Toast
# --------------------------------------------------------------------------

class Toast(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("toast")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 8, 8, 8)
        lay.setSpacing(10)
        self.text = label("", "toastText")
        lay.addWidget(self.text)
        self.action = button("", "toastAction")
        self.action.clicked.connect(self._do_action)
        lay.addWidget(self.action)
        self._callback = None
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.anim = QPropertyAnimation(self.effect, b"opacity", self)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)
        self.hide()

    def show_message(self, text, action_text=None, callback=None, ms=3200):
        self.text.setText(text)
        self._callback = callback
        self.action.setVisible(bool(action_text))
        self.action.setText(action_text or "")
        self.adjustSize()
        self.reposition()
        self.anim.stop()
        self.effect.setOpacity(1.0)
        self.show()
        self.raise_()
        self.timer.start(ms + (2500 if action_text else 0))

    def reposition(self):
        par = self.parentWidget()
        if par:
            self.move((par.width() - self.width()) // 2, par.height() - self.height() - 28)

    def fade_out(self):
        self.anim.stop()
        self.anim.setDuration(260)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self._hide_after)
        self.anim.start()

    def _hide_after(self):
        try:
            self.anim.finished.disconnect(self._hide_after)
        except (RuntimeError, TypeError):
            pass
        if self.effect.opacity() < 0.05:
            self.hide()

    def _do_action(self):
        cb, self._callback = self._callback, None
        self.hide()
        if cb:
            cb()


def make_action(parent, text, slot, shortcut=None) -> QAction:
    a = QAction(text, parent)
    a.triggered.connect(slot)
    if shortcut:
        a.setShortcut(shortcut)
    return a


def popup_menu(items, pos):
    """items: list of (text, callback) or None for separator or (text, [submenu items])."""
    menu = QMenu()
    _fill_menu(menu, items)
    menu.exec(pos)


def _fill_menu(menu, items):
    for it in items:
        if it is None:
            menu.addSeparator()
            continue
        text, target = it
        if isinstance(target, list):
            sub = menu.addMenu(text)
            _fill_menu(sub, target)
        else:
            act = menu.addAction(text)
            act.triggered.connect(target)


def today_iso() -> str:
    return date.today().isoformat()


__all__ = [
    "label", "button", "hbox", "vbox", "clear_layout", "card", "divider", "Page", "Segmented",
    "EmptyState", "TaskRow", "TaskList", "QuickAdd", "ProgressRing", "BarChart", "TimerDial",
    "Toast", "popup_menu", "today_iso", "PRIORITIES",
]
