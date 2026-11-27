<#
  build-windows-exe.ps1 — build standalone Windows .exe files for the four
  "just a..." apps with PyInstaller.

  WHERE THIS RUNS: on WINDOWS only (it produces native Windows .exe files, which
  cannot be cross-compiled from Linux/macOS). The GitHub Actions workflow
  .github/workflows/windows-build.yml runs this on a `windows-latest` runner —
  that CI job is what genuinely produces the downloadable Windows versions.

  WHAT IT DOES: for each app it runs PyInstaller as a ONE-FILE, WINDOWED (no
  console) build, bundling the app's .py (and helper modules) plus its data
  (fonts\, banner.png, icon-*.png, manual.pdf, quickstart.pdf, and any app
  extras) via --add-data, with the app icon, producing dist\<ProductName>.exe.

  USAGE (from the repo root, on Windows, with PyInstaller + each app's deps
  already pip-installed — the CI workflow does that for you):
      pwsh -File tools\build-windows-exe.ps1
      pwsh -File tools\build-windows-exe.ps1 -App paint      # just one app
#>
param(
  [ValidateSet('paint', 'draw', 'pagecreator', 'webcreator', 'movie', 'collectionofapps', 'all')]
  [string]$App = 'all'
)
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$AppsRoot = Join-Path $RepoRoot 'apps'
$DistDir  = Join-Path $RepoRoot 'dist'
$WorkDir  = Join-Path $RepoRoot 'build'
# On Windows, --add-data uses ';' between SRC and DEST (':' on *nix).
$Sep = ';'

# ----- per-app build matrix ---------------------------------------------------
# product  = nice Windows product name -> dist\<product>.exe
# main     = entry-point .py
# modules  = extra .py files to --add-data alongside the entry point
# data     = extra data files (banner/manual/etc) copied into the bundle root
$Matrix = @(
  @{ id = 'paint';       product = 'just a... PAINTcanvas';  main = 'paint.py';
     modules = @();
     data = @('banner.png', 'manual.pdf', 'quickstart.pdf', 'manual.html', 'quickstart.html') },
  @{ id = 'draw';        product = 'just a... DRAWmaster';   main = 'draw.py';
     modules = @();
     data = @('banner.png', 'manual.pdf', 'quickstart.pdf', 'manual.html', 'quickstart.html') },
  @{ id = 'pagecreator'; product = 'just a... PAGEdesigner'; main = 'pagecreator.py';
     modules = @('page_templates.py', 'page_assets.py');
     data = @('banner.png', 'manual.pdf', 'quickstart.pdf', 'manual.html', 'quickstart.html') },
  @{ id = 'webcreator';  product = 'just a... WEBcreator';   main = 'webcreator.py';
     modules = @('test_webplus_import.py');
     data = @('banner.png', 'manual.pdf', 'quickstart.pdf', 'manual.html', 'quickstart.html',
              'serif-templates.json', 'guide_example_site.png') },
  # MOVIEeditor renders with ffmpeg, so its .exe bundles ffmpeg.exe + ffprobe.exe
  # (placed in <repo>\ffmpeg\ by the CI workflow before this script runs).
  @{ id = 'movie';       product = 'just a... MOVIEeditor';  main = 'movie.py';
     modules = @();
     data = @('banner.png', 'manual.pdf', 'quickstart.pdf', 'manual.html', 'quickstart.html');
     ffmpeg = $true },
  @{ id = 'collectionofapps'; product = 'just a... CREATORsuite'; main = 'collectionofapps.py';
     modules = @();
     data = @('banner.png', 'manual.html') }
)

function Log  ($m) { Write-Host ":: $m" -ForegroundColor Cyan }
function Warn ($m) { Write-Host "!! $m" -ForegroundColor Yellow }

# Turn the 256px PNG icon into a multi-size .ico (PyInstaller wants .ico on
# Windows). Pillow is installed for paint, and PyInstaller pulls it in anyway;
# if conversion fails for any reason we just build without a custom icon.
function Make-Ico {
  param($AppDir)
  $png = Join-Path $AppDir 'icon-256.png'
  $ico = Join-Path $AppDir 'icon.ico'
  if (-not (Test-Path $png)) { return $null }
  if (Test-Path $ico) { return $ico }
  $py = @"
from PIL import Image
im = Image.open(r'''$png''').convert('RGBA')
im.save(r'''$ico''', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
"@
  try {
    $py | & python -
    if (Test-Path $ico) { return $ico }
  } catch { Warn "Icon conversion failed ($_) — building $AppDir without a custom icon." }
  return $null
}

function Build-One {
  param($entry)
  $AppDir = Join-Path $AppsRoot $entry.id
  $Main   = Join-Path $AppDir $entry.main
  if (-not (Test-Path $Main)) { Warn "Skipping $($entry.id): $Main not found."; return }

  Log "Building $($entry.product)  (dist\$($entry.product).exe)"

  $pyargs = @(
    '--noconfirm', '--clean',
    '--onefile', '--windowed',
    '--name', $entry.product,
    '--distpath', $DistDir,
    '--workpath', $WorkDir,
    '--specpath', $WorkDir
  )

  # custom icon (best effort)
  $ico = Make-Ico $AppDir
  if ($ico) { $pyargs += @('--icon', $ico) }

  # helper python modules travel with the bundle
  foreach ($m in $entry.modules) {
    $src = Join-Path $AppDir $m
    if (Test-Path $src) { $pyargs += @('--add-data', "$src$Sep.") }
  }

  # app icons (so the app can load its own window icon at runtime)
  foreach ($sz in @(32, 48, 64, 128, 256)) {
    $src = Join-Path $AppDir "icon-$sz.png"
    if (Test-Path $src) { $pyargs += @('--add-data', "$src$Sep.") }
  }

  # data files
  foreach ($d in $entry.data) {
    $src = Join-Path $AppDir $d
    if (Test-Path $src) { $pyargs += @('--add-data', "$src$Sep.") }
    else { Warn "  (data file $d not present — skipping)" }
  }

  # MOVIEeditor: bundle ffmpeg.exe + ffprobe.exe (its render engine) from <repo>\ffmpeg\
  if ($entry.ffmpeg) {
    $FfDir = Join-Path $RepoRoot 'ffmpeg'
    $found = $false
    foreach ($tool in @('ffmpeg.exe', 'ffprobe.exe')) {
      $src = Join-Path $FfDir $tool
      if (Test-Path $src) { $pyargs += @('--add-binary', "$src$Sep."); $found = $true }
      else { Warn "  ($tool not found in $FfDir — the MOVIEeditor .exe will need ffmpeg on PATH)" }
    }
    if ($found) { Log "  bundling ffmpeg for $($entry.id)" }
  }

  # bundled fonts (fonts\ may be a symlink into pagecreator\fonts — resolve it)
  $FontDir = Join-Path $AppDir 'fonts'
  if (Test-Path $FontDir) {
    $resolved = (Resolve-Path $FontDir).Path
    $pyargs += @('--add-data', "$resolved$Sep" + 'fonts')
  }

  $pyargs += $Main

  & python -m PyInstaller @pyargs
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed for $($entry.id)" }
  Log "Built $($entry.product).exe"
}

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

$todo = if ($App -eq 'all') { $Matrix } else { $Matrix | Where-Object { $_.id -eq $App } }
foreach ($e in $todo) { Build-One $e }

Log 'All requested builds complete. The .exe files are in dist\'
Get-ChildItem -Path $DistDir -Filter '*.exe' | ForEach-Object { Write-Host "   $($_.Name)" }
