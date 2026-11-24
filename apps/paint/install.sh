#!/usr/bin/env bash
# install.sh — just a... PAINT: a tiny raster image editor. Run as your normal user.
set -euo pipefail
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log(){ printf '\033[1;35m::\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }
[[ ${EUID:-$(id -u)} -eq 0 ]] && die "Run as your normal user, not root."
BIN="$HOME/.local/bin"; DATA="${XDG_DATA_HOME:-$HOME/.local/share}"; APPS="$DATA/applications"
command -v python3 >/dev/null || die "python3 not found."
python3 -c 'import PySide6' 2>/dev/null || die "Needs PySide6 (distro package): sudo pacman -S --needed pyside6"
python3 -c 'import PIL, numpy' 2>/dev/null || printf '\033[1;33m!!\033[0m %s\n' \
  "Optional: install Pillow + NumPy for the Adjust/Filter menus — e.g. sudo pacman -S python-pillow python-numpy"
log "Installing the app"
install -Dm755 "$SELF/paint.py" "$DATA/paint/paint.py"
install -Dm644 "$SELF/banner.png" "$DATA/paint/banner.png"
[[ -f "$SELF/manual.html" ]] && install -Dm644 "$SELF/manual.html" "$DATA/paint/manual.html"
log "Installing the icon"
for sz in 32 48 64 128 256; do
  [[ -f "$SELF/icon-$sz.png" ]] && install -Dm644 "$SELF/icon-$sz.png" "$DATA/icons/hicolor/${sz}x${sz}/apps/paint.png"
done
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t -f "$DATA/icons/hicolor" 2>/dev/null || true
log "Installing the launcher"
install -d "$BIN"
cat > "$BIN/paint" <<'LAUNCH'
#!/usr/bin/env bash
exec python3 "${XDG_DATA_HOME:-$HOME/.local/share}/paint/paint.py" "$@"
LAUNCH
chmod 755 "$BIN/paint"
log "Installing the menu entry"
install -d "$APPS"
sed "s|^Exec=paint|Exec=$BIN/paint|" "$SELF/paint.desktop" > "$APPS/paint.desktop"
chmod 644 "$APPS/paint.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true
log 'Done. Open "just a... PAINT" from your app menu, or run: paint'
