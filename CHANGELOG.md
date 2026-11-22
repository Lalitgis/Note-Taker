## Daily Sidebar Next 2.0.2

- The installer now installs into C:\Program Files by default, with an "Install for me only" option that needs no admin rights.
- GitHub releases take their version from the tag (for example v2.0.2), so publishing a release no longer fails on a version mismatch.
- build_installer.bat installs Inno Setup and the app's requirements by itself if they are missing.

## Daily Sidebar Next 2.0.1

- Windows installer (DailySidebarNext-Setup.exe): Start menu entry, optional desktop icon and start at sign-in, uninstall from Settings > Apps. No admin rights needed. Your data stays in %APPDATA%\DailySidebarNext.
- Minimizing now keeps the app in the taskbar; the compact sidebar has its own taskbar button.
- Closing the window quits the app unless "Keep running in the tray" is turned on in Settings.

## Daily Sidebar Next 2.0.0

A full rebuild of Daily Sidebar with PySide6 (Qt).

- Workspace with Home, Tasks, Calendar, Projects, Reading, Notes, Focus and Settings pages
- Quick add with `!priority #category @project`, natural due dates and `*repeat`
- Today, Upcoming, Overdue, All open and Done views; tasks grouped by when they're due
- Repeating tasks; unfinished "My Day" tasks roll over; undo for complete and delete
- Month calendar with deadlines and daily-note markers
- Projects with colour, status, deadline and progress
- Reading list for papers: status, DOI/link, rating, tags and notes
- Daily research log with a template, plus a notebook with pinning and search
- Pomodoro focus timer linked to tasks, with a 7-day chart
- Compact always-on-top sidebar (the original Daily Sidebar experience), tray icon, Ctrl+K search
- Light, dark and system themes with six accent colours
- Local SQLite storage, daily backups, JSON export, one-click import from Daily Sidebar 1.x
