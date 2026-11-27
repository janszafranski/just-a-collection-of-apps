# install.ps1 — just a... PAINTcanvas: a tiny raster image editor. (Windows)
#
# This is the Windows counterpart of install.sh. It mirrors the same logic:
#   * find Python 3, or tell you exactly how to get it;
#   * use your system PySide6 if it imports, otherwise build a private venv under
#     %LOCALAPPDATA%\paint\venv (a one-off ~150 MB download);
#   * install the SAME dependencies install.sh uses — PySide6, Pillow, numpy —
#     plus OpenCV as a strictly OPTIONAL extra for the Smart Mask tool: exactly
#     like install.sh, a failed/offline OpenCV install never aborts the setup;
#   * copy the app + its data beside it, register the bundled fonts for your
#     user, and make a launcher and a Start-Menu shortcut.
#
# Run as your normal user (no admin needed). From PowerShell:
#     powershell -ExecutionPolicy Bypass -File .\install.ps1
#
# NOTE: this installs FROM SOURCE and needs Python. If you'd rather not install
# Python at all, grab the prebuilt PAINTcanvas.exe from the project's Releases
# page — see packaging\windows\README.md.

$ErrorActionPreference = 'Stop'

# ----- this app's profile (the only thing that differs between the four) ------
$AppId       = 'paint'
$ProductName = 'just a... PAINTcanvas'
$MainPy      = 'paint.py'
$ExtraPy     = @()                                  # no extra python modules
$Deps        = @('PySide6', 'Pillow', 'numpy')      # same as install.sh
$OptionalDeps = @('opencv-python-headless')         # optional; never fatal
$OptionalProbe = 'cv2'                              # import name to test for it

# -----------------------------------------------------------------------------
$Self = Split-Path -Parent $MyInvocation.MyCommand.Path
function Log  ($m) { Write-Host ":: $m"  -ForegroundColor Magenta }
function Warn ($m) { Write-Host "!! $m"  -ForegroundColor Yellow }
function Die  ($m) { Write-Host "xx $m"  -ForegroundColor Red; exit 1 }

$AppDir = Join-Path $env:LOCALAPPDATA $AppId
$BinDir = Join-Path $AppDir 'bin'

# ----- find a Python 3 launcher ----------------------------------------------
# On Windows the usual entry points are the 'py' launcher and 'python'.
function Find-Python {
  foreach ($cand in @('py', 'python', 'python3')) {
    $cmd = Get-Command $cand -ErrorAction SilentlyContinue
    if ($cmd) {
      $exe = $cmd.Source
      $pargs = @()
      if ($cand -eq 'py') { $pargs = @('-3') }      # force Python 3 via the launcher
      try {
        $v = & $exe @pargs '-c' 'import sys;print(sys.version_info[0])' 2>$null
        if ($LASTEXITCODE -eq 0 -and "$v".Trim() -eq '3') {
          return [pscustomobject]@{ Exe = $exe; Args = $pargs }
        }
      } catch { }
    }
  }
  return $null
}

$py = Find-Python
if (-not $py) {
  Die @"
Python 3 was not found on your PATH.

Install it (either one works), then re-run this installer:
  * winget:        winget install Python.Python.3
  * or download:   https://www.python.org/downloads/windows/
                   (tick "Add python.exe to PATH" in the installer)
"@
}
function Py { param([Parameter(ValueFromRemainingArguments=$true)]$a) & $py.Exe @($py.Args + $a) }

# ----- make sure PySide6 is available, provisioning a venv if need be --------
$VenvPy = Join-Path $AppDir 'venv\Scripts\python.exe'
$Run = $null

Py '-c' 'import PySide6' 2>$null
if ($LASTEXITCODE -eq 0) {
  Log 'Found PySide6 — using your system Python.'
  $Run = @{ Exe = $py.Exe; Args = $py.Args; PyW = $null }
}
elseif ((Test-Path $VenvPy) -and ((& $VenvPy '-c' 'import PySide6' 2>$null); $LASTEXITCODE -eq 0)) {
  Log 'Using the private environment already set up for this app.'
  $Run = @{ Exe = $VenvPy; Args = @(); PyW = (Join-Path $AppDir 'venv\Scripts\pythonw.exe') }
}
else {
  Log "PySide6 isn't installed on this system — setting up a private environment for the app."
  Log '(a one-off download of ~150 MB; needs an internet connection)'
  $VenvDir = Join-Path $AppDir 'venv'
  if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
  Py '-m' 'venv' $VenvDir
  if ($LASTEXITCODE -ne 0) { Die "Could not create a Python environment at $VenvDir" }
  & $VenvPy '-m' 'pip' 'install' '--upgrade' 'pip' *> $null
  Log 'Downloading PySide6 (this can take a minute)...'
  & $VenvPy '-m' 'pip' 'install' @Deps
  if ($LASTEXITCODE -ne 0) {
    Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue
    Die "Could not download with pip. Check your internet connection and try again."
  }
  & $VenvPy '-c' 'import PySide6' 2>$null
  if ($LASTEXITCODE -ne 0) { Die "PySide6 still won't import after install." }
  $Run = @{ Exe = $VenvPy; Args = @(); PyW = (Join-Path $AppDir 'venv\Scripts\pythonw.exe') }
  Log 'Private environment ready.'
}

# ----- optional extras (OpenCV) — NEVER abort on failure, like install.sh ----
if ($OptionalDeps.Count -gt 0) {
  & $Run.Exe @($Run.Args + @('-c', "import $OptionalProbe")) 2>$null
  if ($LASTEXITCODE -ne 0) {
    Log 'Adding OpenCV for the sharpest Smart Mask edges (optional — safe to skip)...'
    & $Run.Exe @($Run.Args + @('-m', 'pip', 'install') + $OptionalDeps) *> $null
    if ($LASTEXITCODE -eq 0) { Log 'OpenCV ready.' }
    else { Log 'OpenCV not installed (offline?) — Smart Mask will use its built-in NumPy fallback.' }
  }
}

# ----- install the app + its data beside it ----------------------------------
Log 'Installing the app'
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
Copy-Item -Force (Join-Path $Self $MainPy) (Join-Path $AppDir $MainPy)
foreach ($m in $ExtraPy) {
  if (Test-Path (Join-Path $Self $m)) { Copy-Item -Force (Join-Path $Self $m) (Join-Path $AppDir $m) }
}
foreach ($d in @('banner.png', 'manual.pdf', 'quickstart.pdf', 'manual.html', 'quickstart.html',
                 'icon-32.png', 'icon-48.png', 'icon-64.png', 'icon-128.png', 'icon-256.png')) {
  if (Test-Path (Join-Path $Self $d)) { Copy-Item -Force (Join-Path $Self $d) (Join-Path $AppDir $d) }
}

# ----- bundled fonts: copy beside the app AND register them for this user ----
$FontSrc = Join-Path $Self 'fonts'
if (Test-Path $FontSrc) {
  $ttfs = Get-ChildItem -Path $FontSrc -Filter '*.ttf' -ErrorAction SilentlyContinue
  if ($ttfs) {
    Log 'Installing the bundled fonts'
    $AppFonts = Join-Path $AppDir 'fonts'
    New-Item -ItemType Directory -Force -Path $AppFonts | Out-Null
    Copy-Item -Force (Join-Path $FontSrc '*.ttf') $AppFonts
    if (Test-Path (Join-Path $FontSrc 'README.txt')) { Copy-Item -Force (Join-Path $FontSrc 'README.txt') $AppFonts }
    # Per-user font install: copy into the user Fonts store and register in HKCU
    # so no admin rights are needed. (If a font is already there this is a no-op.)
    $UserFonts = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
    New-Item -ItemType Directory -Force -Path $UserFonts | Out-Null
    $regKey = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
    foreach ($f in $ttfs) {
      try {
        $dest = Join-Path $UserFonts $f.Name
        Copy-Item -Force $f.FullName $dest
        New-ItemProperty -Path $regKey -Name ($f.BaseName + ' (TrueType)') -Value $dest -PropertyType String -Force | Out-Null
      } catch { Warn "Could not register font $($f.Name) — the app still loads it from its own folder." }
    }
  }
}

# ----- launchers: a silent .vbs (runs pythonw, no console) + a .cmd ----------
Log 'Installing the launcher'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$MainPath = Join-Path $AppDir $MainPy
# Prefer pythonw from the venv if we made one, else the console python; the .vbs
# keeps a black console window from flashing up.
$PyExe  = if ($Run.PyW -and (Test-Path $Run.PyW)) { $Run.PyW } else { $Run.Exe }
$PyWExe = $PyExe
# If we're on the system interpreter, swap python.exe -> pythonw.exe for the GUI.
if (-not $Run.PyW) {
  $cand = $Run.Exe -replace 'python\.exe$', 'pythonw.exe'
  if ($cand -ne $Run.Exe -and (Test-Path $cand)) { $PyWExe = $cand }
}
$runArgs = if ($Run.Args.Count) { ($Run.Args -join ' ') + ' ' } else { '' }

$CmdPath = Join-Path $BinDir "$AppId.cmd"
@"
@echo off
"$PyWExe" $runArgs"$MainPath" %*
"@ | Set-Content -Encoding ASCII -Path $CmdPath

$VbsPath = Join-Path $BinDir "$AppId.vbs"
@"
' Silent launcher for $ProductName (no console window)
Set sh = CreateObject("WScript.Shell")
sh.Run """$PyWExe"" $runArgs""$MainPath""", 0, False
"@ | Set-Content -Encoding ASCII -Path $VbsPath

# add our bin to the *user* PATH (so `paint` works from a new terminal)
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (($userPath -split ';') -notcontains $BinDir) {
  $newPath = if ([string]::IsNullOrEmpty($userPath)) { $BinDir } else { "$userPath;$BinDir" }
  [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
  Warn "Added $BinDir to your PATH — open a NEW terminal for the '$AppId' command to work."
}

# ----- Start-Menu shortcut (.lnk) via WScript.Shell --------------------------
Log 'Installing the Start-Menu shortcut'
$Programs = [Environment]::GetFolderPath('Programs')
New-Item -ItemType Directory -Force -Path $Programs | Out-Null
$Lnk = Join-Path $Programs "$ProductName.lnk"
$ico = Join-Path $AppDir 'icon-256.png'   # .png; Windows prefers .ico but will show the exe/pyw icon otherwise
try {
  $ws = New-Object -ComObject WScript.Shell
  $sc = $ws.CreateShortcut($Lnk)
  $sc.TargetPath = $PyWExe
  $sc.Arguments = (($Run.Args + @("`"$MainPath`"")) -join ' ')
  $sc.WorkingDirectory = $AppDir
  $sc.Description = $ProductName
  if (Test-Path (Join-Path $AppDir 'icon.ico')) { $sc.IconLocation = (Join-Path $AppDir 'icon.ico') }
  $sc.Save()
} catch { Warn "Could not create the Start-Menu shortcut: $_" }

Log "Done. Open `"$ProductName`" from the Start Menu, or run: $AppId"
