#!/usr/bin/env bash
# install.sh — just a... COLLECTION of apps: a tiny launcher for the "just a..."
# app family. Lists the installed apps, launches them, and shows an Update button
# when a newer version is published. Run as your normal user; nothing needs root.
set -euo pipefail
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log()  { printf '\033[1;36m::\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }
[[ ${EUID:-$(id -u)} -eq 0 ]] && die "Run as your normal user, not root."

BIN="$HOME/.local/bin"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APPS="$DATA/applications"

command -v python3 >/dev/null 2>&1 || die "python3 not found."
python3 -c 'import PySide6' 2>/dev/null \
  || die "Needs PySide6 — the distro package, not pip, so the app follows your desktop theme:
     Arch/CachyOS:  sudo pacman -S --needed pyside6
     Debian/Ubuntu/Mint:  sudo apt install python3-pyside6.qtwidgets python3-pyside6.qtwebenginewidgets
     Fedora:  sudo dnf install python3-pyside6
     openSUSE:  sudo zypper install python3-PySide6"

log "Installing the launcher app"
install -Dm755 "$SELF/collectionofapps.py" "$DATA/collectionofapps/collectionofapps.py"
install -Dm644 "$SELF/banner.png" "$DATA/collectionofapps/banner.png"

log "Installing the command"
install -d "$BIN"
cat > "$BIN/collectionofapps" <<'LAUNCH'
#!/usr/bin/env bash
exec python3 "${XDG_DATA_HOME:-$HOME/.local/share}/collectionofapps/collectionofapps.py" "$@"
LAUNCH
chmod 755 "$BIN/collectionofapps"

log "Installing the menu entry"
install -d "$APPS"
sed "s|^Exec=collectionofapps|Exec=$BIN/collectionofapps|" "$SELF/collectionofapps.desktop" > "$APPS/collectionofapps.desktop"
chmod 644 "$APPS/collectionofapps.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true

log "Done. Open \"just a... COLLECTION of apps\" from your app menu, or run: collectionofapps"
warn "If ~/.local/bin is not on your PATH, add it to use the command directly."
