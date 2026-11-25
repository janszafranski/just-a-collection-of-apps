#!/usr/bin/env bash
# install.sh — just a... PAINT: a tiny raster image editor. Run as your normal user.
set -euo pipefail
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log(){ printf '\033[1;35m::\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }
[[ ${EUID:-$(id -u)} -eq 0 ]] && die "Run as your normal user, not root."
BIN="$HOME/.local/bin"; DATA="${XDG_DATA_HOME:-$HOME/.local/share}"; APPS="$DATA/applications"
command -v python3 >/dev/null || die "python3 not found."
APPDIR="$DATA/paint"
PYRUN="python3"
VENV="$APPDIR/venv"
if python3 -c 'import PySide6' 2>/dev/null; then
  log "Found PySide6 — using your system Python."
elif [[ -x "$VENV/bin/python" ]] && "$VENV/bin/python" -c 'import PySide6' 2>/dev/null; then
  log "Using the private environment already set up for this app."
  PYRUN="$VENV/bin/python"
else
  log "PySide6 isn't installed on this system — setting up a private environment for the app."
  log "(a one-off download of ~150 MB; needs an internet connection)"
  if ! python3 -m venv --help >/dev/null 2>&1; then
    die "Python's 'venv' module is missing. Install it, then re-run this installer:
     Mint / Ubuntu / Debian:  sudo apt install python3-venv python3-pip
     Fedora:                  sudo dnf install python3-pip"
  fi
  rm -rf "$VENV"
  python3 -m venv "$VENV" || die "Could not create a Python environment at $VENV"
  "$VENV/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || true
  log "Downloading PySide6 (this can take a minute)…"
  if ! "$VENV/bin/python" -m pip install PySide6 Pillow numpy; then
    rm -rf "$VENV"
    die "Could not download with pip. Check your internet and try again, or install from your
distro and re-run:  apt install python3-pyside6.qtwidgets  /  dnf install python3-pyside6  /  pacman -S pyside6"
  fi
  "$VENV/bin/python" -c 'import PySide6' 2>/dev/null || die "PySide6 still won't import after install."
  PYRUN="$VENV/bin/python"
  log "Private environment ready."
fi
log "Installing the app"
install -Dm755 "$SELF/paint.py" "$DATA/paint/paint.py"
install -Dm644 "$SELF/banner.png" "$DATA/paint/banner.png"
[[ -f "$SELF/manual.html" ]] && install -Dm644 "$SELF/manual.html" "$DATA/paint/manual.html"
[[ -f "$SELF/quickstart.html" ]] && install -Dm644 "$SELF/quickstart.html" "$DATA/paint/quickstart.html"
log "Installing the icon"
for sz in 32 48 64 128 256; do
  [[ -f "$SELF/icon-$sz.png" ]] && install -Dm644 "$SELF/icon-$sz.png" "$DATA/icons/hicolor/${sz}x${sz}/apps/paint.png"
done
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t -f "$DATA/icons/hicolor" 2>/dev/null || true
log "Installing the launcher"
install -d "$BIN"
cat > "$BIN/paint" <<LAUNCH
#!/usr/bin/env bash
exec "$PYRUN" "$APPDIR/paint.py" "\$@"
LAUNCH
chmod 755 "$BIN/paint"
log "Installing the menu entry"
install -d "$APPS"
sed "s|^Exec=paint|Exec=$BIN/paint|" "$SELF/paint.desktop" > "$APPS/paint.desktop"
chmod 644 "$APPS/paint.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true
log 'Done. Open "just a... PAINT" from your app menu, or run: paint'
