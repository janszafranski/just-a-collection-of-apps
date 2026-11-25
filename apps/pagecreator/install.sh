#!/usr/bin/env bash
# install.sh — just a... PAGEdesigner: design print documents by laying pages out,
# then export them as PDF (or an eBook). Works on ANY Linux: if PySide6 isn't
# already available it sets up a small private Python environment automatically
# (a one-off download — no distro packages to hunt for). Run as your normal user;
# nothing here needs root.
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
APPDIR="$DATA/pagecreator"

command -v python3 >/dev/null 2>&1 || die "python3 is not installed. On Mint/Ubuntu:  sudo apt install python3"

# ---- make sure PySide6 is available, provisioning it if need be -------------
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
     Fedora:                  sudo dnf install python3-pip
     Arch / CachyOS:          (already included with python)"
  fi
  rm -rf "$VENV"
  python3 -m venv "$VENV" || die "Could not create a Python environment at $VENV"
  "$VENV/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || true
  log "Downloading PySide6 (this can take a minute)…"
  if ! "$VENV/bin/python" -m pip install PySide6 beautifulsoup4; then
    rm -rf "$VENV"
    die "Could not download PySide6 with pip. Check your internet connection and try again, or
install it from your distribution instead, then re-run this installer:
     Mint / Ubuntu / Debian:  sudo apt install python3-pyside6.qtwidgets python3-bs4
     Fedora:                  sudo dnf install python3-pyside6 python3-beautifulsoup4
     Arch / CachyOS:          sudo pacman -S --needed pyside6 python-beautifulsoup4"
  fi
  "$VENV/bin/python" -c 'import PySide6' 2>/dev/null || die "PySide6 still won't import after install."
  PYRUN="$VENV/bin/python"
  log "Private environment ready."
fi

log "Installing the app"
install -Dm755 "$SELF/pagecreator.py" "$APPDIR/pagecreator.py"
install -Dm644 "$SELF/page_templates.py" "$APPDIR/page_templates.py"
install -Dm644 "$SELF/banner.png" "$APPDIR/banner.png"
[[ -f "$SELF/manual.html" ]] && install -Dm644 "$SELF/manual.html" "$APPDIR/manual.html"
[[ -f "$SELF/quickstart.html" ]] && install -Dm644 "$SELF/quickstart.html" "$APPDIR/quickstart.html"

log "Installing the icon"
for sz in 32 48 64 128 256; do
  [[ -f "$SELF/icon-$sz.png" ]] && install -Dm644 "$SELF/icon-$sz.png" "$DATA/icons/hicolor/${sz}x${sz}/apps/pagecreator.png"
done
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t -f "$DATA/icons/hicolor" 2>/dev/null || true

log "Installing the launcher command"
install -d "$BIN"
cat > "$BIN/pagecreator" <<LAUNCH
#!/usr/bin/env bash
exec "$PYRUN" "$APPDIR/pagecreator.py" "\$@"
LAUNCH
chmod 755 "$BIN/pagecreator"

log "Installing the menu entry and the .pagc file type"
# The shipped .desktop says Exec=pagecreator, which only works if ~/.local/bin is
# on PATH — and a desktop launcher often has a shorter PATH than your shell.
# Write the absolute path in, the way the other profiles here do.
install -d "$APPS"
sed "s|^Exec=pagecreator|Exec=$BIN/pagecreator|" "$SELF/pagecreator.desktop" > "$APPS/pagecreator.desktop"
chmod 644 "$APPS/pagecreator.desktop"
install -Dm644 "$SELF/pagecreator-mime.xml" "$MIME/packages/pagecreator.xml"
command -v update-mime-database    >/dev/null && update-mime-database "$MIME" 2>/dev/null || true
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true
command -v xdg-mime >/dev/null && xdg-mime default pagecreator.desktop application/x-pagecreator-site 2>/dev/null || true

log "Done. Open \"just a... PAGEdesigner\" from your app menu, or run: pagecreator"
if ! command -v pagecreator >/dev/null 2>&1; then
  warn "~/.local/bin is not on your PATH yet — the menu entry still works, or run it with:"
  warn "  $BIN/pagecreator"
fi
