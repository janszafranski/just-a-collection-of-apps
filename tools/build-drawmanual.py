#!/usr/bin/env python3
"""Build DRAWmaster's illustrated docs: quickstart.html (and, in progress, the
full manual.html) from real screenshots captured by driving the app itself.

    python3 tools/build-pagemanual.py            # both docs
    python3 tools/build-pagemanual.py --quick    # just quickstart.html

Every picture is grabbed from the running app (offscreen), so the guide always
matches what the program actually looks like. Images are embedded as data URIs,
so each HTML file is self-contained and installs with no extra assets.

Modelled on Serif's DrawPlus Quick Start / User Guide structure, describing
*this* app's real menus and features.
"""
from __future__ import annotations
import argparse, base64, html as H, importlib.util, io, os, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "apps" / "draw" / "draw.py"
OUT = ROOT / "apps" / "draw"
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


GALLERY_DIR = ROOT / "docs" / "assets" / "draw"


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


DRAW_SAMPLE = [
    dict(type='quick', shape='star5', x=60, y=60, w=190, h=190, fill='#ffd24a', stroke='#c8851b', sw=4,
         glow=dict(color='#ffe08a', blur=22, opacity=80)),
    dict(type='quick', shape='heart', x=300, y=80, w=170, h=160, fill='#e8556b', stroke='#b2374b', sw=3,
         shadow=dict(color='#000000', blur=14, dx=8, dy=10, opacity=35)),
    dict(type='quick', shape='hexagon', x=520, y=60, w=180, h=180, fill='#49c5b6', stroke='#2a8577', sw=3),
    dict(type='quick', shape='speech', x=740, y=50, w=210, h=180, fill='#ffffff', stroke='#2a7df0', sw=4),
    dict(type='quick', shape='arrow', x=80, y=320, w=220, h=120, fill='#5b8def', stroke='#2f5fb0', sw=3),
    dict(type='quick', shape='cloud', x=360, y=320, w=230, h=150, fill='#bfe0ff', stroke='#6aa6df', sw=3),
    dict(type='quick', shape='lightning', x=670, y=310, w=120, h=200, fill='#ffd24a', stroke='#c8851b', sw=3,
         glow=dict(color='#fff3b0', blur=18, opacity=70)),
    dict(type='rect', x=830, y=320, w=150, h=110, fill='#d7b3ff', stroke='#7a4fb0', sw=3),
    dict(type='poly', pts=[(120,540),(220,500),(320,560),(420,500),(520,560)], stroke='#1f2a30', sw=5, fill=None, closed=False),
    dict(type='quick', shape='diamond', x=600, y=500, w=150, h=120, fill=None, stroke='#2a7df0', sw=6),
]


def capture():
    """Return {key: PIL image} for every picture the guide needs."""
    imgs = {}
    w = _win()
    try:
        w.canvas.objs = [dict(o) for o in DRAW_SAMPLE]
        w.canvas.sel = None
        w.canvas.update()
    except Exception:
        pass
    for _ in range(10):
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
        im = Image.open(ROOT / "docs" / "assets" / G[k]["file"]).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
        uri = datauri(bg.convert("RGB"), 360)
        cells.append(f'<figure><img src="{uri}" alt="{G[k]["label"]}">'
                     f'<figcaption>{G[k]["label"]}</figcaption></figure>')
    return '<div class="effgrid shapes">' + "".join(cells) + "</div>"


def quickstart_sections(IM):
    WS = IM["workspace"]
    S = []
    S.append(("Welcome to DRAWmaster", f"""
<p class="lede">DRAWmaster is a <b>vector drawing</b> program in the tradition of Serif
<b>DrawPlus</b>. You build pictures from shapes, lines and curves that stay razor-sharp at any
size, and save them as <b>SVG</b> you can re-open and keep editing.</p>
<p>This Quick Start takes you from a blank canvas to a finished drawing. For the full reference,
open <b>Help &#9656; User Guide</b>.</p>
{figure(WS, 'A drawing in DRAWmaster, built from QuickShapes, a line and a few effects.')}"""))
    S.append(("Starting a drawing", """
<p>DRAWmaster opens on a fresh canvas, ready to draw. Everything you make is vector, so you can
resize and recolour it endlessly without it ever going fuzzy.</p>"""))
    S.append(("The workspace", f"""
<p>The <b>toolbox</b> runs down the left; the canvas fills the middle; the options bar along the top
sets the current fill, line width and shape.</p>
{figure(WS, 'Tools on the left, the drawing in the middle, options along the top.')}"""))
    S.append(("Drawing shapes and lines", """
<p>Drag out a <b>rectangle</b>, an <b>ellipse</b> or a straight <b>line</b>. Each shape has a
<b>fill</b> and an <b>outline</b> you can set before or after you draw it.</p>"""))
    S.append(("QuickShapes", """
<p>Choose a <b>QuickShape</b> from the Shape list — a star, an arrow, a heart, a speech bubble and
sixteen more — and drag it onto the canvas. Resize and recolour it like any other shape.</p>"""))
    S.append(("The pen and freehand tools", """
<p>The <b>pen</b> clicks out a polyline point by point; the <b>freehand</b> tool draws a smooth path
as you drag. Close a path to make a filled shape of your own.</p>"""))
    S.append(("Fills and outlines", """
<p>Give a shape a solid <b>fill</b> and an <b>outline</b> of any colour and width; a line can be
<b>dashed</b>. An outline-only shape (no fill) makes a frame.</p>"""))
    S.append(("Effects", """
<p>Lift a shape off the page with a <b>drop shadow</b> or an <b>outer glow</b> — both adjustable for
colour, blur, offset and strength.</p>"""))
    S.append(("Selecting and arranging", """
<p>With the <b>pointer</b>, click to select and drag to move; the handles resize. <b>Order</b> sends
shapes in front or behind, and you can group several to move as one.</p>"""))
    S.append(("Colours", """
<p>Set the fill and line colours from the colour controls — the same colour you pick is reused until
you change it, so a drawing stays consistent.</p>"""))
    S.append(("Saving as SVG", """
<p><b>File &#9656; Save</b> writes an <b>SVG</b>. DRAWmaster stores your editable drawing inside the
file, so re-opening it brings every shape back exactly as you left it — and the same SVG opens in any
web browser.</p>"""))
    S.append(("Exporting and PAINTcanvas", """
<p>Export a <b>PNG</b> for a fixed-size picture, or send the drawing to <b>PAINTcanvas</b> with
<b>Edit in PAINTcanvas</b> when you want to paint over it.</p>"""))
    S.append(("Where to go next", """
<p>That is the whole round trip: new canvas &#8594; shapes, QuickShapes, pen and freehand &#8594;
fills, outlines and effects &#8594; arrange &#8594; save as SVG. The <b>User Guide</b> covers every
tool, and the other apps in the family work the same way.</p>"""))
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
<title>just a… DRAWmaster — Quick Start Guide</title>
<style>{CSS}</style>
<div class="page">
<header class="mast"><h1>DRAWmaster — Quick Start</h1>
<p>From a blank page to a finished, printable document — in thirteen steps.</p></header>
<ol class="toc">{toc}</ol>
{''.join(body)}
<footer>just a… DRAWmaster Quick Start · generated {date.today().isoformat()} ·
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
      "<p class='lede'>DRAWmaster is a vector drawing program in the tradition of Serif DrawPlus. "
      "A drawing is made of shapes, lines and curves — not pixels — so it stays perfectly sharp at any "
      "size and can be re-coloured and reshaped at will. This chapter introduces the workspace.</p>", [
      ("A fresh canvas", """
<p>DRAWmaster opens ready to draw on a blank canvas. There is nothing to set up first — pick a tool
and begin.</p>"""),
      ("The workspace", f"""
<p>The <b>toolbox</b> runs down the left; the drawing fills the centre; the options bar along the top
carries the current fill, line width, shape and effect controls.</p>
{figure(WS, 'The DRAWmaster workspace, with a finished drawing.')}"""),
      ("Saving", """
<p><b>File &#9656; Save</b> writes an <b>SVG</b> with your editable drawing stored inside it, so you
can always re-open and keep working. Drawings save by default to your shared
<i>Documents/just a&#8230;</i> folder.</p>""")]))

    C.append(("The Canvas and Navigation",
      "<p class='lede'>Vector work rewards zooming in close and stepping back out. DRAWmaster makes "
      "both easy.</p>", [
      ("Zooming and panning", """
<p>Zoom with the <b>Zoom +</b> / <b>Zoom &#8722;</b> controls or Ctrl+scroll, and pan the canvas when
you are zoomed in. Because the drawing is vector, zooming never softens an edge.</p>"""),
      ("Undo and redo", """
<p>Every action can be undone with <b>Ctrl+Z</b> and redone with <b>Ctrl+Shift+Z</b>, so you can
experiment freely.</p>""")]))

    C.append(("Drawing Tools",
      "<p class='lede'>DRAWmaster builds a picture from a handful of simple tools — geometric shapes, "
      "straight lines, and freehand curves.</p>", [
      ("Rectangles, ellipses and lines", """
<p>Drag out a <b>rectangle</b> (optionally with rounded corners), an <b>ellipse</b> or a straight
<b>line</b>. Hold a modifier to constrain a perfect square, circle or horizontal line.</p>"""),
      ("The pen (polyline)", """
<p>The <b>pen</b> places points one click at a time, joining them with straight segments — ideal for
an angular outline or an arrow. Close the path to make a filled shape.</p>"""),
      ("Freehand paths", """
<p>The <b>freehand</b> tool draws a smooth path that follows your pointer as you drag, for signatures,
doodles and organic curves.</p>""")]))

    C.append(("QuickShapes",
      "<p class='lede'>QuickShapes are twenty ready-made outlines — drag one onto the canvas and it is "
      "yours to resize, recolour and give effects. Every shape below is drawn by the program itself.</p>", [
      ("The gallery", effgrid(["triangle", "rtriangle", "diamond", "pentagon", "hexagon", "octagon",
          "star5", "star6", "arrow", "darrow", "chevron", "plus", "parallelogram", "trapezoid",
          "heart", "lightning", "speech", "cloud", "rect", "ellipse"], G)),
      ("Using a QuickShape", """
<p>Pick a shape from the <b>Shape</b> list in the options bar, then drag on the canvas to place it at
any size. From there it behaves exactly like a rectangle or ellipse.</p>""")]))

    C.append(("Fills, Outlines and Effects",
      "<p class='lede'>Colour and effects turn plain outlines into finished artwork.</p>", [
      ("Fills and outlines", """
<p>Every shape has a <b>fill</b> (solid colour, or none) and an <b>outline</b> of any colour and
width. A line can be <b>dashed</b>. An unfilled shape with a strong outline makes a clean frame.</p>"""),
      ("Drop shadow and glow", f"""
<p><b>Effects</b> add depth: a <b>drop shadow</b> sits a shape above the page, and an <b>outer
glow</b> haloes it. Both are adjustable — colour, blur, offset and strength.</p>
{figure(WS, 'The star carries a glow and the heart a drop shadow.')}""")]))

    C.append(("Arranging Objects",
      "<p class='lede'>A drawing is a stack of shapes. Arranging them — their order, position and "
      "grouping — is how a picture comes together.</p>", [
      ("Selecting, moving and resizing", """
<p>With the <b>pointer</b>, click a shape to select it and drag to move it; the handles around it
resize it. Shift-click to select several at once.</p>"""),
      ("Order and grouping", """
<p><b>Order</b> sends a shape to the front or the back so overlaps read correctly, and <b>grouping</b>
ties several shapes together so they move and scale as one.</p>""")]))

    C.append(("Colour",
      "<p class='lede'>DRAWmaster keeps a current fill colour and a current line colour, reused until "
      "you change them so a drawing stays consistent.</p>", [
      ("Setting fill and line colours", """
<p>Choose the <b>fill</b> and <b>line</b> colours from the colour controls. Select a shape first to
recolour it, or set the colours before you draw the next one.</p>""")]))

    C.append(("Saving and Exporting",
      "<p class='lede'>DRAWmaster’s native format keeps your drawing fully editable, and it exports to "
      "the formats the rest of the world uses.</p>", [
      ("Editable SVG", """
<p><b>Save</b> writes an <b>SVG</b> with the editable drawing embedded, so re-opening restores every
shape. The same file also displays in any web browser, infinitely scalable.</p>"""),
      ("PNG export and PAINTcanvas", """
<p>Export a <b>PNG</b> when you need a fixed-size bitmap, or choose <b>Edit in PAINTcanvas</b> to send
the drawing to the image editor and paint over it.</p>""")]))

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
<title>just a… DRAWmaster — User Guide</title>
<style>{CSS}{MANUAL_CSS}</style>
<div class="page">
<header class="mast"><h1>DRAWmaster</h1><p>User Guide — the complete reference for laying out,
checking and publishing a document.</p></header>
<nav class="contents"><h2 style="border:0">Contents</h2><ol class="booktoc">{''.join(toc)}</ol></nav>
{''.join(body)}
<footer>just a… DRAWmaster User Guide · generated {date.today().isoformat()} ·
every picture is produced by the app itself · in the spirit of Serif DrawPlus.</footer>
</div>
</html>
"""
    (OUT / "manual.html").write_text(doc, encoding="utf-8")
    print("wrote manual.html:", len(doc) // 1024, "KiB,", len(C), "chapters")


MANUAL_CSS = """
.effgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin:1.2em 0}
.effgrid figure{margin:0}
.effgrid.shapes{grid-template-columns:repeat(5,1fr);gap:10px}
.effgrid.shapes img{background:#fff}
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
