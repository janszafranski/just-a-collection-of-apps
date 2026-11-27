# Windows packaging

The four "just a..." apps are built with PySide6 (Qt) and run on Windows. There
are **two ways** to get them on Windows — pick whichever suits you.

## 1. Download a prebuilt `.exe` (no Python needed) — recommended

Each app is packaged as a single self-contained executable:

| App | File |
| --- | --- |
| just a... PAINTcanvas  | `just a... PAINTcanvas.exe` |
| just a... DRAWmaster   | `just a... DRAWmaster.exe` |
| just a... PAGEdesigner | `just a... PAGEdesigner.exe` |
| just a... WEBcreator   | `just a... WEBcreator.exe` |

Get them from the project's **Releases** page:

> https://github.com/janszafranski/just-a-collection-of-apps/releases

Download the one you want and double-click it — there is nothing to install and
you do **not** need Python. (The first launch can take a few seconds while the
one-file bundle unpacks itself.)

If a release hasn't been cut yet, the same `.exe` files are also available as
build artifacts on the latest **Actions ▸ Build Windows executables** run.

### Where do these `.exe` come from?

They are built by GitHub Actions on a **Windows runner** — see
[`.github/workflows/windows-build.yml`](../../.github/workflows/windows-build.yml),
which runs [`tools/build-windows-exe.ps1`](../../tools/build-windows-exe.ps1)
(PyInstaller, one-file windowed build). Native Windows executables cannot be
cross-compiled from Linux, so this is the honest way to produce real Windows
binaries. The workflow runs on demand (**workflow_dispatch**) and on any `v*`
tag push, where it also attaches the `.exe` files to a GitHub Release.

## 2. Install from source with PowerShell (needs Python)

Each app has an `install.ps1` next to its `install.sh`. It mirrors the Linux
installer: it finds Python 3 (or tells you how to get it), uses your system
PySide6 if present or else builds a private venv under
`%LOCALAPPDATA%\<app>\venv`, installs that app's dependencies, copies the app
and its data, registers the bundled fonts for your user, and creates a launcher
plus a Start-Menu shortcut.

First install Python 3 if you don't have it:

```powershell
winget install Python.Python.3
```

(or download it from <https://www.python.org/downloads/windows/> and tick
"Add python.exe to PATH").

Then, from the app's folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Dependencies match each app's `install.sh`:

| App | Dependencies | Optional |
| --- | --- | --- |
| paint       | PySide6, Pillow, numpy | opencv-python-headless (sharper Smart Mask; safe to skip) |
| draw        | PySide6 | — |
| pagecreator | PySide6, beautifulsoup4 | — |
| webcreator  | PySide6, beautifulsoup4 | — |

## Building the `.exe` yourself (on Windows)

If you want to build the executables locally on a Windows machine:

```powershell
python -m pip install pyinstaller Pillow PySide6 numpy beautifulsoup4
pwsh -File tools\build-windows-exe.ps1          # all four apps
pwsh -File tools\build-windows-exe.ps1 -App paint   # just one
```

The results land in `dist\`.
