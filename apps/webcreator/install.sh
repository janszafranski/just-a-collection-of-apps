#!/usr/bin/env bash
# install.sh — just a... WEBcreator: design a website by laying pages out, then
# publish it as plain HTML. One Python file plus a launcher, a menu entry and
# the .webc file type. Run as your normal user; nothing here needs root.
set -euo pipefail
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log()  { printf '\033[1;36m::\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }
[[ ${EUID:-$(id -u)} -eq 0 ]] && die "Run as your normal user, not root."

BIN="$HOME/.local/bin"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APPS="$DATA/applications"
MIME="$DATA/mime"

command -v python3 >/dev/null 2>&1 || die "python3 not found."
APPDIR="$DATA/webcreator"
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
  if ! "$VENV/bin/python" -m pip install PySide6 beautifulsoup4; then
    rm -rf "$VENV"
    die "Could not download with pip. Check your internet and try again, or install from your
distro and re-run:  apt install python3-pyside6.qtwidgets  /  dnf install python3-pyside6  /  pacman -S pyside6"
  fi
  "$VENV/bin/python" -c 'import PySide6' 2>/dev/null || die "PySide6 still won't import after install."
  PYRUN="$VENV/bin/python"
  log "Private environment ready."
fi

log "Installing the app"
install -Dm755 "$SELF/webcreator.py" "$DATA/webcreator/webcreator.py"
install -Dm644 "$SELF/test_webplus_import.py" "$DATA/webcreator/test_webplus_import.py"
# The 89 template page trees and their colour schemes. The app runs without
# it — the Startup Assistant just falls back to the three design templates —
# so this is installed beside the app, not demanded by it.
install -Dm644 "$SELF/serif-templates.json" "$DATA/webcreator/serif-templates.json"
install -Dm644 "$SELF/quickstart.html" "$DATA/webcreator/quickstart.html"
install -Dm644 "$SELF/banner.png" "$DATA/webcreator/banner.png"
[[ -f "$SELF/manual.html" ]] && install -Dm644 "$SELF/manual.html" "$DATA/webcreator/manual.html"
[[ -f "$SELF/quickstart.html" ]] && install -Dm644 "$SELF/quickstart.html" "$DATA/webcreator/quickstart.html"
install -Dm644 "$SELF/guide_example_site.png" "$DATA/webcreator/guide_example_site.png"

log "Installing the icon"
for sz in 32 48 64 128 256; do
  [[ -f "$SELF/icon-$sz.png" ]] && install -Dm644 "$SELF/icon-$sz.png" "$DATA/icons/hicolor/${sz}x${sz}/apps/webcreator.png"
done
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t -f "$DATA/icons/hicolor" 2>/dev/null || true

log "Installing the launcher"
install -d "$BIN"
cat > "$BIN/webcreator" <<LAUNCH
#!/usr/bin/env bash
exec "$PYRUN" "$APPDIR/webcreator.py" "\$@"
LAUNCH
chmod 755 "$BIN/webcreator"

log "Installing the menu entry and the .webc file type"
# The shipped .desktop says Exec=webcreator, which only works if ~/.local/bin is
# on PATH — and a desktop launcher often has a shorter PATH than your shell.
# Write the absolute path in, the way the other profiles here do.
install -d "$APPS"
sed "s|^Exec=webcreator|Exec=$BIN/webcreator|" "$SELF/webcreator.desktop" > "$APPS/webcreator.desktop"
chmod 644 "$APPS/webcreator.desktop"
install -Dm644 "$SELF/webcreator-mime.xml" "$MIME/packages/webcreator.xml"
command -v update-mime-database    >/dev/null && update-mime-database "$MIME" 2>/dev/null || true
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true
command -v xdg-mime >/dev/null && xdg-mime default webcreator.desktop application/x-webcreator-site 2>/dev/null || true

# Opening Serif WebPlus .wpp sites is the one thing that needs something else on
# the machine: the Serif-for-Linux checkout, whose serif.webplus does the
# reading. Everything else works without it, so this is a note, not a failure.
if ! python3 - <<'PY' 2>/dev/null
import os, sys
for p in ('~/src/serif-linux', '~/Documents/Development/serif-linux', '~/serif-linux', '~/.local/opt/serif-linux'):
    if os.path.isfile(os.path.join(os.path.expanduser(p), 'serif', 'webplus.py')):
        sys.exit(0)
sys.exit(1)
PY
then
  warn "No Serif-for-Linux checkout found, so File ▸ Open WebPlus Site… will ask where it is.
     Everything else — new sites, templates, importing a website folder, publishing — works without it."
fi

log "Done. Open \"just a... WEBcreator\" from your app menu, or run: webcreator"
warn "If ~/.local/bin is not on your PATH, add it to use the command directly."
