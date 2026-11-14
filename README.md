# Free Games Checker

A PySide6 desktop application that tracks 100% free-to-keep PC games across multiple platforms (Epic Games Store, Steam, GOG, and GamerPower), alerts you across customizable notification channels, and tracks your claimed games.

---

## Features

- **Store Coverage:** Checks Epic Games Store, Steam, GOG, and GamerPower for full games.
- **Noise Filtering:** Discards DLCs, playtests, and external key raffles.
- **Desktop GUI:** Built with PySide6, featuring cards, live search, and store filter tabs.
- **System Tray:** Runs in the background and minimizes to tray.
- **Notifications:** Desktop alerts, Discord webhooks, Telegram, and SMTP email.
- **Claimed Tracker:** Persistent claim history and money saved statistics.
- **Resilience:** Circuit breakers, tenacity retries, and async non-blocking queries.
- **Headless Mode:** CLI flag `--headless` for running via automated sidecars or cron.

---

## Installation & Usage

```bash
# Setup environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Launch Desktop GUI
free-games-checker

# Or run headless check
free-games-checker --headless
```

---

## Configuration

Settings are saved to `config.toml` in your user config folder:
- Schedule: check interval and timezone.
- Stores: toggle individual store checkers.
- Notifications: toggle and credentials for Desktop, Discord, Telegram, and Email.

---

## Desktop Integration

To register Free Games Checker with your Linux desktop environment's application launcher and system menus, run the idempotent installation script:

```bash
./scripts/install-desktop-entry.sh
```

This generates and registers `~/.local/share/applications/free-games-checker.desktop` pointing directly to your environment's virtualenv Python executable and bundled application icon.

---

## Testing

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ -v --cov=free_games_checker --cov-fail-under=70
ruff check .
mypy --strict free_games_checker
```
