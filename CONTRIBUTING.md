# Contributing to Free Games Checker

Thank you for your interest in contributing to **Free Games Checker**! Follow these instructions to set up your development environment, run tests, and contribute new features or store checkers.

---

## 🛠️ Development Setup

### Prerequisites
- **Python 3.11+**
- Git
- Recommended: [uv](https://github.com/astral-sh/uv) or standard Python `venv`

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dazozelm23oz/free-games-checker.git
   cd free-games-checker
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the package in editable mode with development tools:**
   ```bash
   pip install -e ".[dev]"
   ```

---

## 🧪 Running Tests & Quality Checks

Run all verification tools locally before opening a pull request:

```bash
# Linting & Formatting checks
ruff check .
ruff format --check .

# Strict Type Checking
mypy --strict free_games_checker

# Unit and GUI Tests with Coverage (≥70%)
QT_QPA_PLATFORM=offscreen pytest tests/ -v --cov=free_games_checker --cov-fail-under=70
```

---

## ➕ Adding a New Store Checker

Adding a new game store or giveaway platform requires just two simple steps:

1. **Create the Checker Module:**
   Add a new file under `free_games_checker/checkers/<store_name>.py` subclassing `BaseChecker`:

   ```python
   from typing import ClassVar
   from free_games_checker.checkers.base import BaseChecker
   from free_games_checker.models.game import Game
   from free_games_checker.utils.http import fetch_json

   class ItchIoChecker(BaseChecker):
       name: ClassVar[str] = "itch.io"

       async def _fetch_impl(self) -> list[Game]:
           data = await fetch_json("https://itch.io/api/...")
           games: list[Game] = []
           # Parse responses and yield Game instances
           return games
   ```

2. **Register in `free_games_checker/checkers/__init__.py`:**
   Import your checker and append it to `DEFAULT_CHECKERS`.

3. **Add Unit Tests:**
   Add a test fixture and parser test in `tests/test_checkers.py`.

---

## 🚀 Pull Request Workflow

1. Create a feature branch: `git checkout -b feat/your-feature-name`
2. Commit in logical, well-described increments.
3. Ensure CI checks (`ruff`, `mypy`, `pytest`) pass locally.
4. Push and open a pull request on GitHub!
