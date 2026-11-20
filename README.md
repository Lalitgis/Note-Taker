# Daily Sidebar Next

A calm research planner for Windows, built with Python and PySide6 (Qt).
It grows the original Daily Sidebar into a full workspace, and keeps the slim always-on-top sidebar as **compact mode**.

<img src="docs/home-light.png" width="720" alt="Home page in light mode">

<p>
<img src="docs/calendar-dark.png" width="420" alt="Calendar in dark mode">
<img src="docs/focus-dark.png" width="420" alt="Focus timer in dark mode">
<img src="docs/compact.png" width="160" alt="Compact sidebar">
</p>

## Download

Get **DailySidebarNext-windows.zip** from the [latest release](../../releases/latest), unzip it anywhere permanent
(for example `Documents\DailySidebarNext`) and run `DailySidebarNext.exe`. No installer and no Python needed.
Turn on *Start when I sign in to Windows* in Settings if you want it at startup.

> **Windows SmartScreen:** the app isn't code-signed yet, so the first time Windows may say
> "Windows protected your PC". Click **More info → Run anyway**. You can check the source here
> and the build log in the Actions tab.

## Run from source

From this folder in PowerShell:

```powershell
# uses the .venv one folder up (the starter's), or create one here
..\.venv\Scripts\python.exe main.py
```

Or double-click **run.bat** (no console window).

First time on a new machine:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # PySide6-Essentials; full PySide6 works too
python main.py
```

Build a standalone app with **build_exe.bat** (creates `dist\DailySidebarNext\DailySidebarNext.exe`).

## What's inside

| Page | What it does |
|---|---|
| **Home** | Greeting, live clock and week number, today's progress, overdue count, deadlines in the next 7 days, focus time this week, today's plan, coming up, today's note, currently reading |
| **Tasks** | Quick add with shortcuts, views for Today, Upcoming, Overdue, All open and Done, filters by category and project, tasks grouped by Overdue, Today, Tomorrow, This week and Later |
| **Calendar** | Month grid with deadlines and daily-note markers. Click a day to see its tasks and note, double-click to add a task due that day |
| **Projects** | Project cards with colour, status, deadline and progress. Open one to see and add its tasks |
| **Reading** | Papers and books with status (To read, Reading, Read), authors, year, venue, DOI or link, rating, tags and notes. Paste a DOI to add one quickly |
| **Notes** | A daily research log (with a template) and a notebook with pinning, a meeting template and search. Saved as you type |
| **Focus** | Pomodoro timer (focus, short and long breaks) linked to a task, last 7 days chart, today's sessions. Keeps running on other pages |
| **Settings** | Theme (system, light or dark), 6 accent colours, timer lengths, compact sidebar options, start with Windows, close to tray, export and import |

**Also:**
- **Compact sidebar** (Ctrl+M or ⇥ Compact): a slim panel with the clock, today's tasks, quick add and the focus timer. You can drag it, it snaps to screen edges, double-click its top to dock it right, and pin it on top.
- **Ctrl+K** searches tasks, projects, papers and notes, and runs commands.
- **Tray icon:** closing the window keeps the app running in the tray (you can turn this off).
- Repeating tasks (daily, weekdays, weekly, monthly). Unfinished "My Day" tasks roll over to today.
- Undo after you complete or delete a task.
- Right-click a task to set its due date or priority, move it to a project, or start a focus session on it.

### Quick-add syntax

```
Read GWAS paper !high #reading @Thesis fri *weekly
```

| Type | Meaning |
|---|---|
| `!high` `!low` | priority |
| `#reading` | category |
| `@Thesis` | project (matches an existing one, or creates it; use `_` for spaces) |
| `today` `tomorrow` `fri` `+3` `12/03` `2026-12-01` | due date |
| `*daily` `*weekdays` `*weekly` `*monthly` | repeat |

### Keyboard shortcuts

| Keys | Action |
|---|---|
| Ctrl+K | Search and commands |
| Ctrl+N | New task |
| Ctrl+Shift+N | New note |
| Ctrl+1 … Ctrl+8 | Switch page |
| Ctrl+M | Compact sidebar |
| Ctrl+D | Light / dark |
| Ctrl+Shift+F | Start or pause focus |

## Your data

Everything is stored locally in `%APPDATA%\DailySidebarNext\data.db` (SQLite).
A backup copy is made each day in `backups\` next to it, and the last 10 are kept.
Settings → *Export backup* writes everything to a readable JSON file.

**Coming from the first Daily Sidebar?** On first start the app offers to import your tasks and daily notes from
`%APPDATA%\DailySidebar\data.json`. The old file is only read, never changed. You can also do it later
from Settings → *Import from Daily Sidebar*.

To use a different data file: `python main.py D:\path\to\my.db`.

## Code layout

```
main.py                    start-up, single instance
dailysidebar/store.py      SQLite storage, quick-add parser, import/export (no Qt; tested)
dailysidebar/theme.py      palettes and stylesheet
dailysidebar/widgets.py    task rows, lists, quick add, charts, toast
dailysidebar/dialogs.py    task / project / paper dialogs, Ctrl+K palette
dailysidebar/window.py     main window, navigation, tray, shortcuts
dailysidebar/mini.py       compact sidebar
dailysidebar/pages/        one file per page
tests/                     python -m unittest discover -s tests
```

## Releasing a new version

1. Change `__version__` in `dailysidebar/__init__.py` and add notes to `CHANGELOG.md`.
2. Commit, then tag and push: `git tag v2.0.1 && git push origin v2.0.1`.
3. GitHub Actions runs the tests, builds the Windows app and attaches `DailySidebarNext-windows.zip` to a new Release.

## License

[MIT](LICENSE)
