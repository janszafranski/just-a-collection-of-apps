#!/usr/bin/env bash
# install.sh — just a... PAGEcreator: design print documents by laying pages out,
# then export them as PDF. One Python file plus a launcher, a menu entry and the
# .pagc file type. Run as your normal user; nothing here needs root.
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
python3 -c 'import PySide6' 2>/dev/null \
  || die "Needs PySide6 — the distro package, not pip, so the app follows your desktop theme:
     Arch/CachyOS:  sudo pacman -S --needed pyside6
     Debian/Ubuntu/Mint:  sudo apt install python3-pyside6.qtwidgets python3-pyside6.qtwebenginewidgets
     Fedora:  sudo dnf install python3-pyside6
     openSUSE:  sudo zypper install python3-PySide6"

log "Installing the app"
install -Dm755 "$SELF/pagecreator.py" "$DATA/pagecreator/pagecreator.py"
install -Dm644 "$SELF/banner.png" "$DATA/pagecreator/banner.png"
[[ -f "$SELF/manual.html" ]] && install -Dm644 "$SELF/manual.html" "$DATA/pagecreator/manual.html"
[[ -f "$SELF/quickstart.html" ]] && install -Dm644 "$SELF/quickstart.html" "$DATA/pagecreator/quickstart.html"

log "Installing the icon"
for sz in 32 48 64 128 256; do
  [[ -f "$SELF/icon-$sz.png" ]] && install -Dm644 "$SELF/icon-$sz.png" "$DATA/icons/hicolor/${sz}x${sz}/apps/pagecreator.png"
done
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t -f "$DATA/icons/hicolor" 2>/dev/null || true

log "Installing the launcher"
install -d "$BIN"
cat > "$BIN/pagecreator" <<'LAUNCH'
#!/usr/bin/env bash
exec python3 "${XDG_DATA_HOME:-$HOME/.local/share}/pagecreator/pagecreator.py" "$@"
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

log "Done. Open \"just a... PAGEcreator\" from your app menu, or run: pagecreator"
warn "If ~/.local/bin is not on your PATH, add it to use the command directly."
