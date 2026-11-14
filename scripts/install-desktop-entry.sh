#!/usr/bin/env bash
set -euo pipefail

# Determine repository root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"
if [ ! -f "${VENV_PYTHON}" ]; then
    VENV_PYTHON="$(command -v python3 || command -v python)"
fi

ICON_PATH="${REPO_ROOT}/free_games_checker/assets/icon.png"
DESKTOP_DIR="${HOME}/.local/share/applications"
DESKTOP_FILE="${DESKTOP_DIR}/free-games-checker.desktop"

mkdir -p "${DESKTOP_DIR}"

cat <<EOF > "${DESKTOP_FILE}"
[Desktop Entry]
Version=1.0
Type=Application
Name=Free Games Checker
Comment=Track, claim, and get notified about 100% free PC game giveaways
Exec=${VENV_PYTHON} -m free_games_checker
Icon=${ICON_PATH}
Terminal=false
Categories=Game;Utility;
Keywords=games;giveaways;epic;steam;gog;
StartupNotify=true
StartupWMClass=free-games-checker
EOF

chmod +x "${DESKTOP_FILE}"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${DESKTOP_DIR}" || true
fi

echo "Desktop entry installed successfully at: ${DESKTOP_FILE}"
