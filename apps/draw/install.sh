#!/usr/bin/env bash
# install.sh — just a... DRAW: a tiny vector drawing app. Run as your normal user.
set -euo pipefail
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log(){ printf '\033[1;35m::\033[0m %s\n' "$*"; }
die(){ printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }
[[ ${EUID:-$(id -u)} -eq 0 ]] && die "Run as your normal user, not root."
BIN="$HOME/.local/bin"; DATA="${XDG_DATA_HOME:-$HOME/.local/share}"; APPS="$DATA/applications"
command -v python3 >/dev/null || die "python3 not found."
python3 -c 'import PySide6' 2>/dev/null || die "Needs PySide6 (distro package): sudo pacman -S --needed pyside6"
log "Installing the app"
install -Dm755 "$SELF/draw.py" "$DATA/draw/draw.py"
install -Dm644 "$SELF/banner.png" "$DATA/draw/banner.png"
[[ -f "$SELF/manual.html" ]] && install -Dm644 "$SELF/manual.html" "$DATA/draw/manual.html"
log "Installing the icon"
for sz in 32 48 64 128 256; do
  [[ -f "$SELF/icon-$sz.png" ]] && install -Dm644 "$SELF/icon-$sz.png" "$DATA/icons/hicolor/${sz}x${sz}/apps/draw.png"
done
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t -f "$DATA/icons/hicolor" 2>/dev/null || true
log "Installing the launcher"
install -d "$BIN"
cat > "$BIN/draw" <<'LAUNCH'
#!/usr/bin/env bash
exec python3 "${XDG_DATA_HOME:-$HOME/.local/share}/draw/draw.py" "$@"
LAUNCH
chmod 755 "$BIN/draw"
log "Installing the menu entry"
install -d "$APPS"
sed "s|^Exec=draw|Exec=$BIN/draw|" "$SELF/draw.desktop" > "$APPS/draw.desktop"
chmod 644 "$APPS/draw.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true
log 'Done. Open "just a... DRAW" from your app menu, or run: draw'
