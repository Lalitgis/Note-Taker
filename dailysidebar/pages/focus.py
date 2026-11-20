from datetime import date, datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal, Qt
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QVBoxLayout, QWidget

from ..widgets import Page, label, button, card, BarChart, TimerDial, clear_layout, Segmented


class FocusTimer(QObject):
    """Pomodoro timer that keeps running whichever page is open."""
    changed = Signal()
    finished = Signal(str, str)  # (title, message)

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.mode = "focus"         # focus | short | long
        self.running = False
        self.remaining = self.length()
        self.task_id = None
        self.completed_focus = 0
        self.started_at = None
        self._elapsed_in_segment = 0
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

    def length(self, mode=None) -> int:
        mode = mode or self.mode
        key = {"focus": "focus_minutes", "short": "short_break", "long": "long_break"}[mode]
        return int(self.store.get(key)) * 60

    def set_mode(self, mode):
        if self.running:
            self._log_partial()
        self.mode = mode
        self.running = False
        self.timer.stop()
        self.remaining = self.length()
        self.changed.emit()

    def start(self):
        if not self.running:
            self.running = True
            if self.started_at is None:
                self.started_at = datetime.now().isoformat(timespec="seconds")
            self.timer.start()
            self.changed.emit()

    def pause(self):
        if self.running:
            self.running = False
            self.timer.stop()
            self.changed.emit()

    def toggle(self):
        self.pause() if self.running else self.start()

    def reset(self):
        self._log_partial()
        self.running = False
        self.timer.stop()
        self.remaining = self.length()
        self.changed.emit()

    def skip(self):
        self._log_partial()
        self._advance()

    def _log_partial(self):
        """Keep credit for focus time spent before a reset or skip (at least one minute)."""
        if self.mode == "focus" and self._elapsed_in_segment >= 60:
            self.store.log_focus(self._elapsed_in_segment / 60, self.task_id, self._label(), self.started_at)
        self._elapsed_in_segment = 0
        self.started_at = None

    def _label(self):
        if self.task_id:
            t = self.store.task(self.task_id)
            return t["title"] if t else ""
        return ""

    def _tick(self):
        self.remaining -= 1
        if self.mode == "focus":
            self._elapsed_in_segment += 1
        if self.remaining <= 0:
            self._complete()
        self.changed.emit()

    def _complete(self):
        if self.mode == "focus":
            self.store.log_focus(self._elapsed_in_segment / 60, self.task_id, self._label(), self.started_at)
            self.completed_focus += 1
            self.finished.emit("Focus session complete", "Nice work. Time for a break.")
        else:
            self.finished.emit("Break is over", "Ready for another focus session?")
        self._elapsed_in_segment = 0
        self.started_at = None
        if self.store.get("focus_sound"):
            QApplication.beep()
        self._advance()

    def _advance(self):
        if self.mode == "focus":
            every = max(1, int(self.store.get("sessions_before_long")))
            self.mode = "long" if self.completed_focus and self.completed_focus % every == 0 else "short"
        else:
            self.mode = "focus"
        self.running = False
        self.timer.stop()
        self.remaining = self.length()
        self.changed.emit()

    def text(self) -> str:
        m, s = divmod(max(0, self.remaining), 60)
        return f"{m:02d}:{s:02d}"

    def fraction(self) -> float:
        total = self.length()
        return 1 - self.remaining / total if total else 0


MODE_NAMES = {"focus": "Focus", "short": "Short break", "long": "Long break"}


class FocusPage(Page):
    def __init__(self, ctx):
        super().__init__(ctx, "Focus", "Work in calm, timed sessions. Breaks are part of the work.")
        self.timer = ctx.focus
        body = QHBoxLayout()
        body.setSpacing(18)

        main, ml = card(margins=(24, 20, 24, 22), spacing=14)
        ml.addStretch(1)
        self.seg = Segmented(["Focus", "Short break", "Long break"], "Focus")
        self.seg.changed.connect(self._mode_clicked)
        ml.addWidget(self.seg, 0, Qt.AlignmentFlag.AlignHCenter)
        dial_holder = QWidget()
        dh = QVBoxLayout(dial_holder)
        dh.setContentsMargins(0, 0, 0, 0)
        self.dial = TimerDial(ctx, 250)
        dh.addWidget(self.dial, 0, Qt.AlignmentFlag.AlignHCenter)
        ml.addWidget(dial_holder, 0, Qt.AlignmentFlag.AlignHCenter)
        # time label over the dial
        self.time = label("25:00", "timerLabel", parent=self.dial)
        self.time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time.setGeometry(0, 80, 250, 70)
        self.state = label("", "mutedBody", parent=self.dial)
        self.state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state.setGeometry(0, 150, 250, 22)

        task_row = QHBoxLayout()
        task_row.addStretch()
        task_row.addWidget(label("Working on", "mutedBody"))
        self.task_combo = QComboBox()
        self.task_combo.setMinimumWidth(280)
        self.task_combo.currentIndexChanged.connect(self._task_changed)
        task_row.addWidget(self.task_combo)
        task_row.addStretch()
        ml.addLayout(task_row)

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(button("Reset", None, self.timer.reset))
        self.start_btn = button("Start", "primaryButton", self.timer.toggle)
        self.start_btn.setMinimumWidth(120)
        btns.addWidget(self.start_btn)
        btns.addWidget(button("Skip", None, self.timer.skip))
        btns.addStretch()
        ml.addLayout(btns)
        self.cycle = label("", "faint")
        self.cycle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ml.addWidget(self.cycle)
        ml.addStretch(2)
        body.addWidget(main, 3)

        side = QVBoxLayout()
        side.setSpacing(14)
        wk, wl = card()
        wl.addWidget(label("Last 7 days", "cardTitle"))
        self.week_total = label("", "muted")
        wl.addWidget(self.week_total)
        self.chart = BarChart(ctx, 140)
        wl.addWidget(self.chart)
        side.addWidget(wk)
        sess, self.sess_lay = card()
        self.sess_lay.addWidget(label("Today's sessions", "cardTitle"))
        self.sess_items = QVBoxLayout()
        self.sess_items.setSpacing(6)
        self.sess_lay.addLayout(self.sess_items)
        side.addWidget(sess)
        side.addStretch()
        sw = QWidget()
        sw.setLayout(side)
        sw.setMinimumWidth(280)
        body.addWidget(sw, 2)
        self.outer.addLayout(body, 1)

        self.timer.changed.connect(self._update_timer)
        self._filling = False
        self._update_timer()

    def _mode_clicked(self, name):
        mode = {v: k for k, v in MODE_NAMES.items()}[name]
        self.timer.set_mode(mode)

    def _task_changed(self, _):
        if not self._filling:
            self.timer.task_id = self.task_combo.currentData()

    def _fill_tasks(self):
        self._filling = True
        self.task_combo.clear()
        self.task_combo.addItem("No specific task", None)
        seen = set()
        for t in self.ctx.store.tasks("today") + self.ctx.store.tasks("open"):
            if t["done"] or t["id"] in seen:
                continue
            seen.add(t["id"])
            self.task_combo.addItem(t["title"][:70], t["id"])
        idx = self.task_combo.findData(self.timer.task_id)
        self.task_combo.setCurrentIndex(max(0, idx))
        self._filling = False

    def _update_timer(self):
        t = self.timer
        self.time.setText(t.text())
        self.dial.set_fraction(t.fraction(), t.mode != "focus")
        self.seg.set_current(MODE_NAMES[t.mode])
        self.start_btn.setText("Pause" if t.running else ("Resume" if t.remaining < t.length() else "Start"))
        self.state.setText(("Focusing" if t.mode == "focus" else "On a break") if t.running
                           else ("Paused" if t.remaining < t.length() else "Ready"))
        every = int(self.ctx.store.get("sessions_before_long"))
        self.cycle.setText(f"Session {t.completed_focus % every + 1} of {every} before a long break"
                           if t.mode == "focus" else "Stretch, drink some water, look away from the screen.")

    def refresh(self):
        s = self.ctx.store
        self._fill_tasks()
        today = date.today()
        data = [(date.fromisoformat(d).strftime("%a")[:2], m) for d, m in s.focus_by_day(7)]
        self.chart.set_data(data)
        total = sum(m for _, m in data)
        h, m = divmod(int(total), 60)
        self.week_total.setText(f"{h}h {m:02d}m focused" if total else "No focus time logged yet")
        clear_layout(self.sess_items)
        sessions = s.focus_sessions(today.isoformat())
        if not sessions:
            self.sess_items.addWidget(label("No sessions yet today. Pick a task and press Start.", "mutedBody", wrap=True))
        for x in sessions[:8]:
            when = x["started"][11:16]
            what = x["task_title"] or x["label"] or "Focus"
            self.sess_items.addLayout(_row(when, what, f"{int(round(x['minutes']))}m"))
        self._update_timer()


def _row(a, b, c):
    lay = QHBoxLayout()
    lay.addWidget(label(a, "muted"))
    t = label(b, "bodyText")
    t.setWordWrap(True)
    lay.addWidget(t, 1)
    lay.addWidget(label(c, "chipAccent"))
    return lay
