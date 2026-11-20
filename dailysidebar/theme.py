"""Colours and the Qt stylesheet. Calm, paper-like palette inspired by Notion."""

ACCENTS = {
    "Sage":  {"light": ("#527B63", "#E8EFE9"), "dark": ("#8BAF9B", "#29352F")},
    "Ocean": {"light": ("#3F6E9E", "#E5EDF6"), "dark": ("#86ADD6", "#243241")},
    "Plum":  {"light": ("#7A5A9A", "#EFE8F5"), "dark": ("#B79AD6", "#322A3D")},
    "Amber": {"light": ("#A8692A", "#F6EDE1"), "dark": ("#E0A86A", "#3A2F22")},
    "Rose":  {"light": ("#A9506A", "#F6E6EB"), "dark": ("#E295AB", "#3B2730")},
    "Slate": {"light": ("#4A5563", "#E9EBEE"), "dark": ("#AEB7C4", "#2C3139")},
}

BASE = {
    "light": {
        "window": "#F7F7F5", "sidebar": "#F0F0ED", "surface": "#FFFFFF", "surface_alt": "#FAFAF8",
        "hover": "#ECEDE9", "border": "#E3E4DF", "border_strong": "#CFD2CB", "text": "#252923",
        "muted": "#757C73", "faint": "#A2A79F", "input": "#FFFFFF", "accent_text": "#FFFFFF",
        "danger": "#B94D4D", "danger_soft": "#F7E5E3", "warn": "#B07415", "warn_soft": "#FBF0DC",
        "high": "#B94D4D", "medium": "#B07415", "low": "#6F8A9E", "shadow": "#00000014",
    },
    "dark": {
        "window": "#191B20", "sidebar": "#1F2228", "surface": "#24282F", "surface_alt": "#21252B",
        "hover": "#2D323B", "border": "#333842", "border_strong": "#454B57", "text": "#EEF0F2",
        "muted": "#A0A6B2", "faint": "#6E7480", "input": "#1F2329", "accent_text": "#14201A",
        "danger": "#E58D8D", "danger_soft": "#3A2629", "warn": "#E8B060", "warn_soft": "#3A3122",
        "high": "#E58D8D", "medium": "#E8B060", "low": "#93AFC4", "shadow": "#00000040",
    },
}


def palette(mode: str, accent: str) -> dict:
    c = dict(BASE[mode])
    a = ACCENTS.get(accent, ACCENTS["Sage"])[mode]
    c["accent"], c["soft"] = a
    c["mode"] = mode
    if mode == "dark":
        c["accent_text"] = "#14181C"
    return c


def stylesheet(c: dict, font_family: str = "Segoe UI", check_icon: str = "") -> str:
    check = f'image: url("{check_icon}");' if check_icon else 'image: none;'
    return f"""
* {{ font-family: "{font_family}"; }}
QMainWindow, QWidget#root, QDialog {{ background: {c['window']}; color: {c['text']}; }}
QWidget {{ color: {c['text']}; }}
QToolTip {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 5px 7px; border-radius: 6px; }}
QFrame#sidebar {{ background: {c['sidebar']}; border-right: 1px solid {c['border']}; }}
QFrame#mainArea, QWidget#page, QStackedWidget#pages, QScrollArea > QWidget > QWidget {{ background: {c['window']}; }}
QLabel {{ background: transparent; }}
QLabel#brandMark {{ background: {c['accent']}; color: {c['accent_text']}; border-radius: 8px; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; font-size: 17px; font-weight: 700; qproperty-alignment: AlignCenter; }}
QLabel#brandName {{ font-size: 14px; font-weight: 650; }}
QLabel#brandSub {{ color: {c['muted']}; font-size: 11px; }}
QLabel#eyebrow {{ color: {c['faint']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; padding: 4px 8px; }}
QPushButton#navButton {{ text-align: left; border: 0; border-radius: 7px; padding: 8px 10px; color: {c['muted']}; background: transparent; font-size: 13px; }}
QPushButton#navButton:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton#navButton:checked {{ background: {c['soft']}; color: {c['accent']}; font-weight: 650; }}
QLabel#navBadge {{ color: {c['muted']}; font-size: 11px; }}
QLabel#navBadgeAlert {{ color: {c['danger']}; font-size: 11px; font-weight: 700; }}
QFrame#sideClock {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 10px; }}
QLabel#sideTime {{ font-size: 22px; font-weight: 650; }}
QLabel#breadcrumb {{ color: {c['muted']}; font-size: 12px; }}

QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox {{
    background: {c['input']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 7px 10px;
    color: {c['text']}; font-size: 12px; selection-background-color: {c['accent']}; selection-color: {c['accent_text']}; }}
QPlainTextEdit, QTextEdit {{ padding: 8px 10px; }}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus {{ border: 1px solid {c['accent']}; }}
QLineEdit#quickAdd {{ font-size: 13px; padding: 10px 12px; border-radius: 9px; }}
QLineEdit#searchBox {{ padding: 7px 10px; }}
QLineEdit#titleEdit {{ background: transparent; border: 0; font-size: 22px; font-weight: 700; padding: 2px 0; }}
QPlainTextEdit#bareEditor {{ background: transparent; border: 0; font-size: 13px; padding: 2px 0; }}
QComboBox::drop-down, QDateEdit::drop-down {{ border: 0; width: 20px; }}
QComboBox QAbstractItemView {{ background: {c['surface']}; border: 1px solid {c['border']}; selection-background-color: {c['soft']}; selection-color: {c['text']}; outline: 0; padding: 4px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 16px; border: 0; }}

QPushButton {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 7px 12px; color: {c['text']}; font-size: 12px; }}
QPushButton:hover {{ background: {c['hover']}; }}
QPushButton:disabled {{ color: {c['faint']}; }}
QPushButton#primaryButton {{ background: {c['accent']}; color: {c['accent_text']}; border: 1px solid {c['accent']}; font-weight: 650; }}
QPushButton#primaryButton:hover {{ background: {c['accent']}; border: 1px solid {c['text']}; }}
QPushButton#dangerButton {{ color: {c['danger']}; }}
QPushButton#dangerButton:hover {{ background: {c['danger_soft']}; }}
QPushButton#ghostButton, QToolButton#ghostButton {{ background: transparent; border: 0; border-radius: 6px; padding: 5px 8px; color: {c['muted']}; }}
QPushButton#ghostButton:hover, QToolButton#ghostButton:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton#iconButton {{ background: transparent; border: 0; border-radius: 6px; padding: 3px; color: {c['muted']}; font-size: 13px; min-width: 22px; min-height: 22px; }}
QPushButton#iconButton:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton#segment {{ background: transparent; border: 0; border-radius: 7px; padding: 6px 11px; color: {c['muted']}; font-size: 12px; }}
QPushButton#segment:hover {{ color: {c['text']}; background: {c['hover']}; }}
QPushButton#segment:checked {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']}; }}
QFrame#segmentBar {{ background: {c['sidebar']}; border-radius: 9px; }}
QPushButton#swatch {{ border-radius: 13px; min-width: 26px; max-width: 26px; min-height: 26px; max-height: 26px; padding: 0; }}
QPushButton#calNav {{ min-width: 30px; padding: 6px; }}

QLabel#pageTitle {{ font-size: 26px; font-weight: 700; }}
QLabel#pageSubtitle {{ color: {c['muted']}; font-size: 13px; }}
QLabel#sectionTitle {{ font-size: 14px; font-weight: 650; }}
QLabel#cardTitle {{ font-size: 13px; font-weight: 650; }}
QLabel#muted {{ color: {c['muted']}; font-size: 11px; }}
QLabel#mutedBody {{ color: {c['muted']}; font-size: 12px; }}
QLabel#faint {{ color: {c['faint']}; font-size: 11px; }}
QLabel#bodyText {{ font-size: 12px; }}
QLabel#bigTime {{ font-size: 34px; font-weight: 300; }}
QLabel#statValue {{ font-size: 24px; font-weight: 700; }}
QLabel#statIcon {{ color: {c['accent']}; font-size: 16px; }}
QLabel#statValueAlert {{ font-size: 24px; font-weight: 700; color: {c['danger']}; }}
QLabel#groupHeader {{ color: {c['muted']}; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; padding: 8px 2px 2px 2px; }}
QLabel#groupHeaderAlert {{ color: {c['danger']}; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; padding: 8px 2px 2px 2px; }}
QLabel#emptyIcon {{ color: {c['accent']}; font-size: 30px; }}
QLabel#timerLabel {{ font-size: 54px; font-weight: 300; }}
QLabel#kbd {{ background: {c['sidebar']}; border: 1px solid {c['border']}; border-radius: 4px; padding: 1px 6px; font-size: 11px; color: {c['muted']}; }}

QFrame#card, QFrame#statCard, QFrame#emptyPanel, QFrame#noteCard {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 11px; }}
QFrame#projectCard {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 11px; }}
QFrame#projectCard:hover {{ border: 1px solid {c['border_strong']}; }}
QFrame#taskRow, QFrame#paperRow {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 9px; }}
QFrame#taskRow:hover, QFrame#paperRow:hover {{ border: 1px solid {c['border_strong']}; }}
QFrame#taskRowDone {{ background: {c['surface_alt']}; border: 1px solid {c['border']}; border-radius: 9px; }}
QFrame#divider {{ background: {c['border']}; max-height: 1px; min-height: 1px; border: 0; }}
QFrame#calCell {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 8px; }}
QFrame#calCell:hover {{ border: 1px solid {c['border_strong']}; }}
QFrame#calCellOther {{ background: {c['surface_alt']}; border: 1px solid {c['border']}; border-radius: 8px; }}
QFrame#calCellToday {{ background: {c['surface']}; border: 1px solid {c['accent']}; border-radius: 8px; }}
QFrame#calCellSelected {{ background: {c['soft']}; border: 1px solid {c['accent']}; border-radius: 8px; }}
QLabel#calDay {{ font-size: 12px; font-weight: 600; }}
QLabel#calDayToday {{ font-size: 12px; font-weight: 700; color: {c['accent_text']}; background: {c['accent']}; border-radius: 9px; min-width: 18px; max-width: 26px; padding: 1px 4px; qproperty-alignment: AlignCenter; }}
QLabel#calDayOther {{ font-size: 12px; color: {c['faint']}; }}
QLabel#calItem {{ font-size: 10px; color: {c['text']}; background: {c['sidebar']}; border-radius: 4px; padding: 1px 4px; }}
QLabel#calItemDone {{ font-size: 10px; color: {c['faint']}; background: transparent; padding: 1px 4px; }}
QLabel#calItemHigh {{ font-size: 10px; color: {c['high']}; background: {c['danger_soft']}; border-radius: 4px; padding: 1px 4px; }}
QLabel#weekday {{ color: {c['muted']}; font-size: 11px; font-weight: 600; qproperty-alignment: AlignCenter; }}

QLabel#chip {{ background: {c['sidebar']}; color: {c['muted']}; border-radius: 5px; padding: 2px 6px; font-size: 10px; }}
QLabel#chipAccent {{ background: {c['soft']}; color: {c['accent']}; border-radius: 5px; padding: 2px 6px; font-size: 10px; font-weight: 600; }}
QLabel#chipDanger {{ background: {c['danger_soft']}; color: {c['danger']}; border-radius: 5px; padding: 2px 6px; font-size: 10px; font-weight: 600; }}
QLabel#chipWarn {{ background: {c['warn_soft']}; color: {c['warn']}; border-radius: 5px; padding: 2px 6px; font-size: 10px; font-weight: 600; }}
QLabel#taskTitle {{ font-size: 13px; }}
QLabel#taskTitleDone {{ font-size: 13px; color: {c['faint']}; text-decoration: line-through; }}
QLabel#paperTitle {{ font-size: 13px; font-weight: 600; }}
QLabel#stars {{ color: {c['warn']}; font-size: 12px; }}

QCheckBox {{ spacing: 7px; font-size: 12px; background: transparent; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1.5px solid {c['border_strong']}; background: {c['input']}; }}
QCheckBox::indicator:hover {{ border: 1.5px solid {c['accent']}; }}
QCheckBox::indicator:checked {{ background: {c['accent']}; border: 1.5px solid {c['accent']}; {check} }}
QCheckBox#taskCheck::indicator {{ width: 17px; height: 17px; border-radius: 9px; }}
QCheckBox#taskCheckHigh::indicator {{ width: 17px; height: 17px; border-radius: 9px; border: 1.5px solid {c['high']}; background: {c['danger_soft']}; }}
QCheckBox#taskCheckHigh::indicator:checked {{ background: {c['accent']}; border: 1.5px solid {c['accent']}; }}

QListWidget {{ background: transparent; border: 0; outline: 0; font-size: 12px; }}
QListWidget::item {{ border-radius: 7px; padding: 7px 8px; margin: 1px 0; color: {c['text']}; }}
QListWidget::item:hover {{ background: {c['hover']}; }}
QListWidget::item:selected {{ background: {c['soft']}; color: {c['text']}; }}
QListWidget#palette::item {{ padding: 8px 10px; }}

QProgressBar {{ background: {c['sidebar']}; border: 0; border-radius: 3px; max-height: 6px; min-height: 6px; text-align: center; }}
QProgressBar::chunk {{ border-radius: 3px; background: {c['accent']}; }}
QSlider::groove:horizontal {{ height: 4px; background: {c['border']}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {c['accent']}; width: 14px; margin: -5px 0; border-radius: 7px; }}

QScrollArea {{ border: 0; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 4px; min-height: 25px; }}
QScrollBar::handle:vertical:hover {{ background: {c['border_strong']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ height: 0; background: transparent; }}
QScrollBar:horizontal {{ height: 0; }}

QMenu {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 8px; padding: 5px; }}
QMenu::item {{ padding: 6px 22px 6px 12px; border-radius: 5px; color: {c['text']}; }}
QMenu::item:selected {{ background: {c['hover']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 6px; }}
QCalendarWidget QWidget {{ alternate-background-color: {c['surface_alt']}; }}
QCalendarWidget QToolButton {{ color: {c['text']}; background: transparent; border: 0; padding: 4px; }}
QCalendarWidget QAbstractItemView {{ background: {c['surface']}; selection-background-color: {c['accent']}; selection-color: {c['accent_text']}; }}

QFrame#toast {{ background: {c['text']}; border-radius: 9px; }}
QLabel#toastText {{ color: {c['window']}; font-size: 12px; }}
QPushButton#toastAction {{ background: transparent; border: 0; color: {c['soft']}; font-weight: 700; font-size: 12px; padding: 4px 8px; }}
QPushButton#toastAction:hover {{ text-decoration: underline; }}

QFrame#miniRoot {{ background: {c['window']}; border: 1px solid {c['border_strong']}; border-radius: 12px; }}
QFrame#miniHeader {{ background: transparent; }}
QLabel#miniTime {{ font-size: 30px; font-weight: 300; }}
QFrame#paletteRoot {{ background: {c['surface']}; border: 1px solid {c['border_strong']}; border-radius: 12px; }}
QLineEdit#paletteInput {{ border: 0; border-bottom: 1px solid {c['border']}; border-radius: 0; font-size: 15px; padding: 12px 14px; background: transparent; }}
QStatusBar {{ color: {c['muted']}; background: {c['window']}; border: 0; }}
"""


def check_svg(color: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            f'<path d="M3.5 8.3l3 3 6-6.3" fill="none" stroke="{color}" stroke-width="2.2" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg>')
