#!/usr/bin/env python3
"""Build PAINTcanvas's illustrated docs: quickstart.html (and, in progress, the
full manual.html) from real screenshots captured by driving the app itself.

    python3 tools/build-pagemanual.py            # both docs
    python3 tools/build-pagemanual.py --quick    # just quickstart.html

Every picture is grabbed from the running app (offscreen), so the guide always
matches what the program actually looks like. Images are embedded as data URIs,
so each HTML file is self-contained and installs with no extra assets.

Modelled on Serif's PhotoPlus Quick Start / User Guide structure, describing
*this* app's real menus and features.
"""
from __future__ import annotations
import argparse, base64, html as H, importlib.util, io, os, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "apps" / "paint" / "paint.py"
OUT = ROOT / "apps" / "paint"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REAL_ARGS = sys.argv[1:]
sys.argv = ["build-pagemanual", "--no-startup"]   # the app reads this to skip its Startup Assistant

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox   # noqa: E402
from PySide6.QtCore import Qt                                      # noqa: E402

app = QApplication.instance() or QApplication([])
QDialog.exec = lambda self, *a, **k: 0
for _n in ("information", "warning", "critical", "question", "about"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: 0))


def _load():
    spec = importlib.util.spec_from_file_location("paint", APP)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


PC = _load()
mk = getattr(PC, "mk", None)

try:
    from PIL import Image
except Exception:
    Image = None


# ---------------------------------------------------------------- screenshots
_TMP = ROOT / "tools" / "_tmp_grab.png"


def grab(widget) -> "Image.Image":
    widget.grab().save(str(_TMP), "PNG")
    im = Image.open(str(_TMP)).convert("RGB")
    return im.copy()


def _win():
    w = PC.Main()
    w.setAttribute(Qt.WA_DontShowOnScreen, True)
    w.resize(1180, 860); w.show()
    for _ in range(12):
        app.processEvents()
    return w


GALLERY_DIR = ROOT / "docs" / "assets" / "paint"


def gallery_items():
    """Reuse the committed effect gallery (one sample photo through every
    adjustment and filter)."""
    import json
    man = GALLERY_DIR / "manifest.json"
    if not man.exists():
        return []
    return json.loads(man.read_text())


SAMPLE = [
    ("shape", 0, 0, None, 118, dict(shape="rect", fill="#2a7d6b", strokeW=0)),
    ("artistic", 40, 26, 500, 60, dict(html="<p>The Quayside Gazette</p>", size=40, color="#ffffff", bold=True)),
    ("text", 44, 86, 600, 28, dict(html="<p>Spring issue · news from the harbour community</p>", size=14, color="#ddeae6", pad=0)),
    ("artistic", 40, 150, 420, 40, dict(html="<p>New boardwalk opens</p>", size=26, color="#243137", bold=True)),
    ("text", 40, 200, 350, 420, dict(pad=0, size=13, color="#243137", html=(
        "<p>After a winter of work, the restored boardwalk along Mill Lane is open "
        "again. The council and dozens of volunteers rebuilt every plank by hand.</p>"
        "<p>“It is the best it has looked in thirty years,” said one resident.</p>"
        "<p>A small ceremony is planned for the May bank holiday, with tea, cake and "
        "a brass band.</p>"))),
    ("picture", 410, 150, 344, 210, dict(fill="#cfe0e6", stroke="#9fb8c0", strokeW=1)),
    ("text", 410, 366, 344, 28, dict(pad=0, size=11, color="#5c6b73", html="<p><i>The new boardwalk at first light.</i></p>")),
    ("artistic", 410, 408, 320, 34, dict(html="<p>Dates for the diary</p>", size=20, color="#243137", bold=True)),
    ("table", 410, 450, 344, 150, dict(head="#dff0eb", cells=[["Event", "When"], ["Boardwalk opening", "3 May"], ["Harbour market", "17 May"], ["Regatta", "31 May"]])),
    ("shape", 40, 648, 714, 3, dict(shape="rect", fill="#2a7d6b", strokeW=0)),
    ("text", 40, 662, 714, 28, dict(pad=0, size=11, color="#5c6b73", html="<p>The Quayside Gazette · delivered free to every home on the harbour · issue 42</p>")),
]


SHAPES_DEMO = [
    ("artistic", 40, 36, 560, 44, dict(html="<p>Shapes, lines &amp; QuickShapes</p>", size=30, color="#243137", bold=True)),
    ("shape", 40, 110, 150, 108, dict(shape="rect", fill="#9fc3d6", stroke="#2b3a42", strokeW=2)),
    ("shape", 212, 110, 150, 108, dict(shape="rect", fill="#cfe0e6", stroke="#2b3a42", strokeW=2, radius=18)),
    ("shape", 384, 110, 150, 108, dict(shape="ellipse", fill="#f4c96b", stroke="#8a6d1f", strokeW=2)),
    ("line", 560, 164, 190, 0, dict(stroke="#2b3a42", strokeW=3)),
    ("shape", 40, 250, 120, 120, dict(shape="star5", fill="#f4c96b", stroke="#c8851b", strokeW=2)),
    ("shape", 180, 250, 120, 120, dict(shape="arrow", fill="#5b8def", stroke="#2f5fb0", strokeW=2)),
    ("shape", 320, 250, 128, 120, dict(shape="heart", fill="#e8556b", stroke="#b2374b", strokeW=2)),
    ("shape", 470, 250, 150, 120, dict(shape="speech", fill="#ffffff", stroke="#2a7df0", strokeW=3)),
    ("shape", 640, 250, 120, 120, dict(shape="hexagon", fill="#49c5b6", stroke="#2a8577", strokeW=2)),
    ("shape", 40, 410, 160, 110, dict(shape="rect", fill="#2a7d6b", strokeW=0, shadow=dict(color="#000000", blur=16, dx=7, dy=9, opacity=40))),
    ("shape", 240, 410, 160, 110, dict(shape="rect", fill="#f4c96b", strokeW=0, glow=dict(color="#ffe08a", blur=22, opacity=85))),
    ("text", 40, 540, 360, 30, dict(pad=0, size=12, color="#5c6b73", html="<p>A filled rectangle (left) carries a drop shadow; the gold one has an outer glow.</p>")),
]

TEXT_DEMO = [
    ("artistic", 40, 36, 560, 44, dict(html="<p>Working with text</p>", size=30, color="#243137", bold=True)),
    ("text", 40, 104, 350, 300, dict(size=13, color="#243137", html=(
        "<p><span style='font-size:230%'>O</span>nce upon a time a paragraph began with a large "
        "dropped capital, set into the first few lines. Frame text wraps neatly inside its frame "
        "and can flow on to a second, linked frame when it overruns.</p>"
        "<p>This is a second paragraph. Notice how the text keeps an even left edge and a comfortable "
        "line height for reading.</p>"))),
    ("text", 410, 104, 344, 300, dict(size=13, color="#243137", html=(
        "<p><b>A short checklist</b></p><ul><li>Type straight into a frame</li>"
        "<li>Link frames to flow long text</li><li>Give a heading its own style</li>"
        "<li>Add a bulleted or numbered list</li><li>Check spelling before you print</li></ul>"))),
    ("artistic", 40, 430, 500, 56, dict(html="<p>Big artistic headlines</p>", size=38, color="#2a7d6b", bold=True)),
    ("text", 40, 500, 714, 30, dict(pad=0, size=12, color="#5c6b73", html="<p>Artistic text is a single line you scale freely — ideal for titles and mastheads.</p>")),
]


def _add(w, objs, upto=None):
    pw = w.site.get("width", 794)
    for i, (t, x, y, ww, hh, p) in enumerate(objs):
        if upto is not None and i >= upto:
            break
        w.add_object(mk(t, x, y, pw if ww is None else ww, hh, **p))
    w.sel = []
    if hasattr(w, "set_tool"):
        w.set_tool("pointer")


def _add_sample(w, upto=None):
    _add(w, SAMPLE, upto)


def capture():
    """Return {key: PIL image} for every picture the guide needs."""
    imgs = {}

    from PySide6.QtGui import QImage
    scene = str(GALLERY_DIR / "original.jpg")

    # The editor with a photo open
    w = _win()
    try:
        w.canvas.load(QImage(scene))
    except Exception:
        pass
    for _ in range(8):
        app.processEvents()
    imgs["workspace"] = grab(w)
    return imgs


# ---------------------------------------------------------------- image helpers
def crop(im, box):
    return im.crop(box)


def datauri(im, maxw=1000, quality=84):
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------------- content model
def figure(uri_or_im, cap):
    uri = uri_or_im if isinstance(uri_or_im, str) else datauri(uri_or_im)
    return f'<figure><img src="{uri}" alt="{H.escape(cap)}"><figcaption>{cap}</figcaption></figure>'


def gimg(key, cap):
    """A figure built from the committed effect-gallery image <key>.jpg."""
    p = GALLERY_DIR / f"{key}.jpg"
    if not p.exists():
        return ""
    return figure(Image.open(p).convert("RGB"), cap)


def effgrid(keys, G):
    cells = []
    for k in keys:
        if k not in G:
            continue
        uri = datauri(Image.open(GALLERY_DIR / (k + ".jpg")).convert("RGB"), 560)
        cells.append(f'<figure><img src="{uri}" alt="{G[k]["label"]}">'
                     f'<figcaption><b>{G[k]["label"]}</b> &#8212; {G[k]["meta"]}</figcaption></figure>')
    return '<div class="effgrid">' + "".join(cells) + "</div>"


def quickstart_sections(IM):
    WS = IM["workspace"]
    S = []
    S.append(("Welcome to PAINTcanvas", f"""
<p class="lede">PAINTcanvas is a <b>photo and image editor</b> in the tradition of Serif
<b>PhotoPlus</b>. You paint and draw, retouch photographs, and apply adjustments and filters —
working in layers, just like the program it replaces.</p>
<p>This Quick Start takes you from opening a photo to saving a finished picture. For the full
reference, open <b>Help &#9656; User Guide</b>.</p>
{figure(WS, 'A photograph open in PAINTcanvas, with the toolbox, canvas, Colour and Layers panels.')}"""))
    S.append(("Opening or creating an image", """
<p><b>File &#9656; Open</b> loads a photo (PNG, JPEG and more); <b>File &#9656; New</b> makes a blank
canvas at a size and background you choose. You can also drag a picture straight in. Saved work goes
by default to your <i>Pictures/just a&#8230;</i> folder so the launcher can find it again.</p>"""))
    S.append(("The workspace", f"""
<p>The <b>toolbox</b> runs down the left; your image fills the canvas; the <b>Colour</b> picker and
the <b>Layers</b> panel sit to the right, with the tool&#8217;s options along the top.</p>
{figure(WS, 'Tools on the left, the picture in the middle, Colour and Layers on the right.')}"""))
    S.append(("Zooming and the canvas", """
<p>Zoom with Ctrl+scroll or the zoom control, and pan with the Hand tool. <b>Image</b> menu commands
resize the picture, change the canvas, <b>crop</b>, <b>straighten</b>, rotate and flip.</p>"""))
    S.append(("Painting and drawing", """
<p>Pick the <b>Brush</b> or <b>Pencil</b> and paint; the <b>Eraser</b> rubs out. Draw filled
rectangles and ellipses, pour colour with the <b>Fill</b>, and add words with the <b>Text</b> tool.
The tool options bar sets size, hardness and opacity.</p>"""))
    S.append(("Choosing colours", """
<p>The <b>Colour</b> picker sets the colour you paint with — drag the sliders or type a hex value.
The eyedropper lifts a colour from anywhere in the picture.</p>"""))
    S.append(("Selections", """
<p>The <b>rectangular</b> and <b>elliptical</b> selection tools mark off part of the image so an edit
only affects that area. With nothing selected, an edit applies to the whole layer.</p>"""))
    S.append(("Working in layers", """
<p>Layers stack like sheets of acetate. Add one for new paint, so you never touch the photo beneath.
The <b>Layers</b> panel sets each layer&#8217;s <b>visibility</b>, <b>opacity</b> and <b>blend mode</b>,
and lets you reorder them.</p>"""))
    S.append(("Adjusting colour", f"""
<p>The <b>Adjust</b> menu corrects and transforms colour — brightness and contrast, levels, hue and
saturation, colour balance, temperature, and one-click looks like greyscale, sepia and invert.</p>
{gimg('sepia', 'The sample photo with a Sepia adjustment applied.')}"""))
    S.append(("Filters", f"""
<p>The <b>Filter</b> menu reworks the whole image — blur and sharpen, or creative looks like emboss
and find-edges.</p>
{gimg('edges', 'The Find Edges filter traces the outlines of the photo.')}"""))
    S.append(("Retouching", """
<p>The retouch tools fix real photos: <b>Clone</b> paints over a blemish with another part of the
picture, <b>Red-eye</b> removes flash red, and <b>Dodge</b> and <b>Burn</b> lighten or darken by
hand.</p>"""))
    S.append(("Saving and exporting", """
<p><b>File &#9656; Save</b> writes a PNG (which keeps transparency) or a JPEG. Need vector shapes
instead? <b>Edit in DRAWmaster</b> hands the picture to the drawing app and back.</p>"""))
    S.append(("Where to go next", """
<p>That is the round trip: open a photo &#8594; paint, select and layer &#8594; adjust and filter
&#8594; retouch &#8594; save. The <b>User Guide</b> covers every tool in depth, and the other apps in
the family work the same way.</p>"""))
    return S

def crop_uri(im, box):
    return datauri(crop(im, box), maxw=800)


# ---------------------------------------------------------------- html assembly
CSS = """
:root{ --ink:#232b31; --mute:#64737c; --line:#d7dee3; --accent:#2a7d6b; --paper:#ffffff; --band:#eef3f2; }
*{box-sizing:border-box} body{margin:0;background:#e8edf0;color:var(--ink);
  font:16px/1.65 "Noto Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}
.page{max-width:820px;margin:28px auto;background:var(--paper);padding:56px 64px;
  box-shadow:0 2px 20px -8px rgba(20,40,50,.35);border-radius:4px;}
h1{font-size:2.3rem;margin:.1em 0 .1em;letter-spacing:-.01em}
.sub{color:var(--mute);margin:0 0 1.4em;font-size:1.05rem}
h2{font-size:1.5rem;margin:2.3em 0 .5em;padding-top:.5em;border-top:3px solid var(--accent);}
h2 .n{color:var(--accent);font-variant-numeric:tabular-nums;margin-right:.5em;font-weight:700}
.lede{font-size:1.1rem}
p{max-width:66ch} ul{max-width:66ch} li{margin:.2em 0}
figure{margin:1.3em 0;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--band)}
figure img{width:100%;display:block}
figcaption{font-size:.86rem;color:var(--mute);padding:8px 12px;background:var(--band);border-top:1px solid var(--line)}
.tip{background:var(--band);border-left:4px solid var(--accent);border-radius:6px;padding:10px 14px;font-size:.95rem}
.toc{columns:2;gap:28px;margin:1.2em 0 0;padding:0;list-style:none}
.toc li{margin:.25em 0;break-inside:avoid} .toc a{color:var(--ink);text-decoration:none}
.toc a:hover{color:var(--accent);text-decoration:underline} .toc .n{color:var(--accent);font-weight:700;margin-right:.5em}
header.mast{background:var(--accent);color:#fff;border-radius:4px;padding:30px 36px;margin-bottom:0}
header.mast h1{margin:0;color:#fff} header.mast p{margin:.3em 0 0;color:#d7ece7}
footer{color:var(--mute);font-size:.85rem;margin-top:3em;border-top:1px solid var(--line);padding-top:1em}
@media print{ body{background:#fff} .page{box-shadow:none;margin:0;max-width:none} h2{break-after:avoid} figure{break-inside:avoid} }
"""


def build_quickstart(IM):
    S = quickstart_sections(IM)
    toc = "".join(f'<li><span class="n">{i+1}</span><a href="#s{i+1}">{H.escape(t)}</a></li>'
                  for i, (t, _) in enumerate(S))
    body = []
    for i, (t, html) in enumerate(S):
        body.append(f'<h2 id="s{i+1}"><span class="n">{i+1}</span>{H.escape(t)}</h2>\n{html}')
    doc = f"""<!DOCTYPE html>
<html lang="en-GB">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>just a… PAINTcanvas — Quick Start Guide</title>
<style>{CSS}</style>
<div class="page">
<header class="mast"><h1>PAINTcanvas — Quick Start</h1>
<p>From a blank page to a finished, printable document — in thirteen steps.</p></header>
<ol class="toc">{toc}</ol>
{''.join(body)}
<footer>just a… PAINTcanvas Quick Start · generated {date.today().isoformat()} ·
every picture is produced by the app itself. See <b>Help ▸ User Guide</b> for the full manual.</footer>
</div>
</html>
"""
    (OUT / "quickstart.html").write_text(doc, encoding="utf-8")
    print("wrote quickstart.html:", len(doc) // 1024, "KiB,", len(S), "sections")


def manual_chapters(IM):
    WS = IM["workspace"]
    G = {it["file"].split("/")[-1][:-4]: it for it in gallery_items()}
    C = []

    C.append(("Getting Started",
      "<p class='lede'>PAINTcanvas is a layer-based image editor in the tradition of Serif PhotoPlus. "
      "You open a photograph (or start a blank canvas), then paint, retouch and apply adjustments and "
      "filters. This chapter introduces the workspace and the basics of opening and saving.</p>", [
      ("Opening and creating images", """
<p><b>File &#9656; Open</b> loads a picture; <b>File &#9656; New</b> starts a blank canvas at a size
and background colour you set. PAINTcanvas reads common formats including PNG and JPEG, and you can
drag an image straight onto the canvas.</p>"""),
      ("The workspace", f"""
<p>The editor puts your picture in the centre, with the <b>toolbox</b> down the left, the tool&#8217;s
own options along the top, and the <b>Colour</b> picker and <b>Layers</b> panel to the right.</p>
{figure(WS, 'The PAINTcanvas workspace, with a photograph open.')}"""),
      ("Saving your work", """
<p><b>File &#9656; Save</b> and <b>Save As</b> write a PNG (keeping any transparency) or a JPEG.
Pictures save by default to your shared <i>Pictures/just a&#8230;</i> folder.</p>""")]))

    C.append(("The Canvas",
      "<p class='lede'>Before editing the pixels, it helps to get the canvas itself right — its size, "
      "its framing and its orientation.</p>", [
      ("Image size and canvas size", """
<p><b>Image &#9656; Resize</b> changes the picture&#8217;s pixel dimensions; <b>Canvas Size</b> adds or
trims space around it without scaling the image &#8212; useful for adding a border.</p>"""),
      ("Cropping and straightening", """
<p><b>Crop</b> keeps only the part you want; <b>Straighten</b> levels a crooked horizon. Both are on
the <b>Image</b> menu.</p>"""),
      ("Rotating and flipping", """
<p><b>Rotate</b> turns the whole image by 90&#176; or any angle; <b>Flip</b> mirrors it horizontally or
vertically.</p>""")]))

    C.append(("Painting and Drawing Tools",
      "<p class='lede'>PAINTcanvas gives you the familiar toolbox for making marks &#8212; brushes for "
      "freehand work, shapes for geometry, and text for words.</p>", [
      ("Brush, pencil and eraser", """
<p>The <b>Brush</b> paints soft strokes and the <b>Pencil</b> hard ones; the <b>Eraser</b> removes
paint. Set size, hardness and opacity in the options bar.</p>"""),
      ("Shapes and fill", """
<p>Draw filled or outlined <b>rectangles</b> and <b>ellipses</b>, and pour colour into an area with the
<b>Fill</b> (paint-bucket) tool. The <b>Gradient</b> tool blends one colour into another.</p>"""),
      ("Text", """
<p>The <b>Text</b> tool adds words to the picture in any installed font, size and colour &#8212; for a
caption, a title or a watermark.</p>""")]))

    C.append(("Colour",
      "<p class='lede'>Everything you paint uses the current colour. PAINTcanvas makes it easy to pick, "
      "sample and reuse colours.</p>", [
      ("The Colour picker", f"""
<p>Choose a colour with the RGB sliders or by typing a hex value. The eyedropper lifts a colour from
anywhere in the image so you can match it exactly.</p>
{figure(WS, 'The Colour picker sits to the right of the canvas.')}"""),
      ("Foreground and background", """
<p>PAINTcanvas keeps a foreground and a background colour; tools use one or the other, and some
&#8212; like the gradient &#8212; blend between them.</p>""")]))

    C.append(("Selections",
      "<p class='lede'>A selection limits where your edits land, so you can change one part of a "
      "picture and leave the rest untouched.</p>", [
      ("Making a selection", """
<p>The <b>rectangular</b> and <b>elliptical</b> selection tools drag out an area; everything you then
paint, fill, adjust or filter affects only inside it. With nothing selected, edits apply to the whole
layer.</p>"""),
      ("Moving and clearing", """
<p>Move a selection to reposition the marked area, and clear it (Esc) when you want to work on the
whole image again.</p>""")]))

    C.append(("Layers",
      "<p class='lede'>Layers are the heart of a non-destructive edit. Each layer is a transparent "
      "sheet you can paint on, reorder, fade or blend without harming the ones beneath.</p>", [
      ("The Layers panel", f"""
<p>The <b>Layers</b> panel lists every layer, top to bottom. Add a new layer for fresh paint, hide a
layer with its visibility toggle, and drag layers to reorder them.</p>
{figure(WS, 'The Layers panel, lower right, lists the picture&#8217;s layers.')}"""),
      ("Opacity and blend modes", """
<p>Each layer has an <b>opacity</b> (how solid it is) and a <b>blend mode</b> (how its colours combine
with the layers below &#8212; multiply, screen, overlay and more). Together they drive most montage and
tinting effects.</p>""")]))

    C.append(("Adjusting Colour and Tone",
      "<p class='lede'>The <b>Adjust</b> menu corrects exposure and colour and applies one-click looks. "
      "Every picture below is the same sample photograph, produced by the program&#8217;s own code.</p>", [
      ("The adjustments", effgrid(["original", "brightness", "contrast", "saturation", "levels", "hue",
          "temperature", "threshold", "posterize", "greyscale", "sepia", "invert", "autocontrast",
          "equalize"], G)),
      ("Using an adjustment", """
<p>Make a selection first to limit an adjustment to one area, or apply it to the whole layer. Work on a
duplicate layer to keep the original safe.</p>""")]))

    C.append(("Filters",
      "<p class='lede'>The <b>Filter</b> menu reworks the whole image &#8212; softening, sharpening and "
      "creative effects.</p>", [
      ("The filters", effgrid(["gaussian", "unsharp", "median", "sharpen", "soften", "emboss", "edges",
          "contour"], G))]))

    C.append(("Retouching and Effects",
      "<p class='lede'>The retouch tools fix the small flaws every real photograph has, and effects add "
      "finish.</p>", [
      ("Clone, red-eye, dodge and burn", """
<p>The <b>Clone</b> tool paints over a blemish using another part of the picture; <b>Red-eye</b> fixes
flash red; <b>Dodge</b> lightens and <b>Burn</b> darkens, exactly as in a darkroom.</p>"""),
      ("Drop shadow and glow", """
<p>On a layer with transparency, add a <b>drop shadow</b> or an <b>outer glow</b> to lift a cut-out
subject off its background.</p>""")]))

    C.append(("Saving and Exporting",
      "<p class='lede'>When the picture is finished, save it in the right format for the job.</p>", [
      ("PNG and JPEG", """
<p><b>Save</b> as <b>PNG</b> to keep sharp edges and transparency, or as <b>JPEG</b> for a small
photographic file. <b>Save As</b> keeps your working copy while exporting another.</p>"""),
      ("Hand off to DRAWmaster", """
<p><b>Edit in DRAWmaster</b> sends the picture to the vector drawing app; when you save there it comes
back, so you can combine painted and drawn artwork.</p>""")]))

    C.append(("Keyboard Shortcuts", "<p class='lede'>The shortcuts you will use most.</p>", [
      ("Common shortcuts", """
<table class="ref">
<tr><th>Action</th><th>Shortcut</th></tr>
<tr><td>Open / Save</td><td>Ctrl+O &#183; Ctrl+S</td></tr>
<tr><td>Undo / Redo</td><td>Ctrl+Z &#183; Ctrl+Shift+Z</td></tr>
<tr><td>Copy / Paste</td><td>Ctrl+C &#183; Ctrl+V</td></tr>
<tr><td>Deselect</td><td>Esc</td></tr>
<tr><td>Zoom in / out</td><td>Ctrl++ &#183; Ctrl+&#8722;</td></tr>
</table>""")]))
    return C

def build_manual(IM):
    C = manual_chapters(IM)
    # table of contents
    toc = []
    for ci, (title, _intro, secs) in enumerate(C, 1):
        subs = "".join(f'<li><a href="#c{ci}s{si}">{H.escape(h)}</a></li>'
                       for si, (h, _b) in enumerate(secs, 1))
        toc.append(f'<li class="ch"><span class="n">{ci}</span>'
                   f'<a href="#c{ci}">{H.escape(title)}</a><ul>{subs}</ul></li>')
    # body
    body = []
    for ci, (title, intro, secs) in enumerate(C, 1):
        body.append(f'<section class="chapter"><div class="chrule"><span class="cn">Chapter {ci}</span>'
                    f'<h2 id="c{ci}">{H.escape(title)}</h2></div>\n{intro}')
        for si, (h, b) in enumerate(secs, 1):
            body.append(f'<h3 id="c{ci}s{si}">{H.escape(h)}</h3>\n{b}')
        body.append("</section>")
    doc = f"""<!DOCTYPE html>
<html lang="en-GB">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>just a… PAINTcanvas — User Guide</title>
<style>{CSS}{MANUAL_CSS}</style>
<div class="page">
<header class="mast"><h1>PAINTcanvas</h1><p>User Guide — the complete reference for laying out,
checking and publishing a document.</p></header>
<nav class="contents"><h2 style="border:0">Contents</h2><ol class="booktoc">{''.join(toc)}</ol></nav>
{''.join(body)}
<footer>just a… PAINTcanvas User Guide · generated {date.today().isoformat()} ·
every picture is produced by the app itself · in the spirit of Serif PhotoPlus.</footer>
</div>
</html>
"""
    (OUT / "manual.html").write_text(doc, encoding="utf-8")
    print("wrote manual.html:", len(doc) // 1024, "KiB,", len(C), "chapters")


MANUAL_CSS = """
.effgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin:1.2em 0}
.effgrid figure{margin:0}
.contents{margin:1.5em 0 2em} .booktoc{list-style:none;padding:0;margin:0}
.booktoc .ch{margin:.6em 0;font-weight:600} .booktoc .ch>a{color:var(--ink);text-decoration:none}
.booktoc .n{color:var(--accent);margin-right:.5em} .booktoc ul{list-style:none;padding:0 0 0 1.6em;margin:.2em 0;font-weight:400;columns:2;gap:24px}
.booktoc ul li{margin:.1em 0} .booktoc a:hover{color:var(--accent)}
.chapter{margin-top:2.6em} .chrule{border-top:4px solid var(--accent);margin-bottom:.4em}
.chrule .cn{display:block;color:var(--accent);font-size:.8rem;letter-spacing:.14em;text-transform:uppercase;margin-top:.4em}
.chrule h2{border:0;margin:.05em 0 .3em;padding:0;font-size:1.9rem}
h3{font-size:1.18rem;margin:1.6em 0 .4em;color:#17323a}
table.ref{border-collapse:collapse;width:100%;max-width:66ch;margin:1em 0}
table.ref th,table.ref td{border:1px solid var(--line);padding:7px 10px;text-align:left;font-size:.95rem}
table.ref th{background:var(--band)}
@media print{ .chapter{break-before:page} .contents{break-after:page} }
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args(_REAL_ARGS)
    if Image is None:
        sys.exit("Pillow required")
    IM = capture()
    build_quickstart(IM)
    if not args.quick:
        build_manual(IM)
    try:
        _TMP.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    main()
