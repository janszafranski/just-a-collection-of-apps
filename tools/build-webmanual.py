#!/usr/bin/env python3
"""Build WEBcreator's illustrated docs — a book-length User Guide and a Quick
Start — entirely from the running app.

    python3 tools/build-webmanual.py            # both docs (HTML + PDF)
    python3 tools/build-webmanual.py --quick    # just the Quick Start
    python3 tools/build-webmanual.py --no-pdf   # HTML only (fast; skip printing)

Every picture is produced by the program itself: workspace and panel screenshots
are grabbed from a live (offscreen) window, every dialog is captured by driving the
real menu command, and the demo pages and template catalogue are rendered with the
app's own page painter (render_page_image). Images embed as data URIs, so each HTML
file is self-contained and installs with no extra assets.

Modelled on the structure and depth of Serif's WebPlus User Guide — step-by-step
procedures, callouts, worked projects and a full reference section — but describing
*this* program's real menus and features throughout (clean-room: original prose).
"""
from __future__ import annotations
import argparse, base64, html as H, importlib.util, io, os, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "apps" / "webcreator" / "webcreator.py"
OUT = ROOT / "apps" / "webcreator"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REAL_ARGS = sys.argv[1:]
sys.argv = ["build-webmanual", "--no-startup"]   # the app reads this to skip its Startup Assistant

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox   # noqa: E402
from PySide6.QtCore import Qt                                      # noqa: E402

app = QApplication.instance() or QApplication([])

# Silence modal message boxes so a driver call never blocks.
for _n in ("information", "warning", "critical", "question", "about"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: 0))

# Capture every dialog the app opens: when a command calls dlg.exec(), show the
# dialog offscreen, grab it, then return "rejected" so nothing is actually changed.
DGRABS: dict = {}
_orig_exec = QDialog.exec


def _cap_exec(self, *a, **k):
    try:
        self.setAttribute(Qt.WA_DontShowOnScreen, True)
        if self.size().width() < 80 or self.size().height() < 60:
            self.adjustSize()
        self.show()
        for _ in range(14):
            app.processEvents()
        key = self.windowTitle() or ("dialog%d" % len(DGRABS))
        DGRABS[key] = _grab(self)
        self.hide()
    except Exception:
        pass
    return 0


QDialog.exec = _cap_exec


def _load():
    spec = importlib.util.spec_from_file_location("webcreator", APP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


PC = _load()
mk = PC.mk

try:
    from PIL import Image
except Exception:
    Image = None

_TMP = ROOT / "tools" / "_tmp_grab.png"


def _grab(widget) -> "Image.Image":
    widget.grab().save(str(_TMP), "PNG")
    return Image.open(str(_TMP)).convert("RGB").copy()


def _pil(qt_obj) -> "Image.Image":
    """PIL image from a QPixmap or QImage."""
    qt_obj.save(str(_TMP), "PNG")
    return Image.open(str(_TMP)).convert("RGBA").copy()


def _win():
    w = PC.MainWindow()
    w.setAttribute(Qt.WA_DontShowOnScreen, True)
    w.resize(1200, 940)
    w.show()
    for _ in range(16):
        app.processEvents()
    return w


# ------------------------------------------------------------------- demo pages
# A demo page is a plain list of (type, x, y, w, h, props) tuples. We build a real
# site around it with base_site() and render it with the app's own page painter,
# render_page_image(site, page, px) — the same code that draws template thumbnails.

def _mkobj(t, x, y, w, h, p):
    return mk(t, x, y, w, h, **p)


def render_page(objs, w=960, h=1100, px=900, bg="#ffffff"):
    """Render a demo page (list of object tuples) to a PIL RGB image."""
    site = PC.base_site("Demo", width=w, height=h, bg=bg,
                        palette=["#1f2a30", "#2a7d6b", "#f4f1ea", "#e0a43a", "#ffffff", "#5d6a71"])
    page = site["pages"][0]
    page["bg"] = bg
    page["objects"] = [_mkobj(*o) for o in objs]
    img = PC.render_page_image(site, page, px, crop=h)
    return _pil(img).convert("RGB")


# A complete one-page business home page, built up in stages for the worked project.
HOME = [
    # header bar + logo + inline nav
    ("shape", 0, 0, 960, 72, dict(shape="rect", fill="#ffffff", stroke="#e4e9ec", strokeW=1)),
    ("artistic", 48, 18, 320, 38, dict(html="<p>Harbour &amp; Co.</p>", size=27, color="#2a7d6b", bold=True)),
    ("nav", 520, 20, 400, 36, dict(style="pills", accent="#2a7d6b", accentInk="#ffffff", color="#1f2a30", size=14)),
    # hero band
    ("shape", 0, 72, 960, 380, dict(shape="rect", fill="#2a7d6b", strokeW=0)),
    ("artistic", 60, 160, 840, 76, dict(html="<p>Handmade joinery, built to last</p>", size=44, color="#ffffff", bold=True)),
    ("text", 62, 266, 560, 70, dict(pad=0, size=19, color="#d7ece7", html="<p>Kitchens, staircases and restoration, made by hand in our harbourside workshop.</p>")),
    ("button", 62, 356, 200, 50, dict(html="<p>Get a free quote</p>", size=15, bold=True, fill="#e0a43a", color="#1f2a30")),
    # three services
    ("artistic", 60, 496, 300, 36, dict(html="<p>What we do</p>", size=25, color="#1f2a30", bold=True)),
    ("text", 60, 552, 270, 150, dict(pad=0, size=14, color="#394650", html="<p><b>Kitchens</b></p><p>Fitted kitchens in solid timber, designed around your room and built to measure.</p>")),
    ("text", 348, 552, 270, 150, dict(pad=0, size=14, color="#394650", html="<p><b>Staircases</b></p><p>New stairs and balustrades, and careful repairs to period originals.</p>")),
    ("text", 636, 552, 270, 150, dict(pad=0, size=14, color="#394650", html="<p><b>Restoration</b></p><p>Doors, windows and panelling brought back to life with traditional methods.</p>")),
    # picture + caption
    ("picture", 60, 724, 840, 300, dict(fill="#cfe0e6", stroke="#9fb8c0", strokeW=1)),
    ("text", 60, 1032, 840, 26, dict(pad=0, size=12, color="#5c6b73", html="<p><i>A recent kitchen, photographed on site.</i></p>")),
    # footer
    ("shape", 0, 1086, 960, 90, dict(shape="rect", fill="#1f2a30", strokeW=0)),
    ("text", 60, 1114, 840, 44, dict(pad=0, size=13, color="#c7d2d8", html="<p>Harbour &amp; Co. Joinery &middot; Unit 4, Quay Street &middot; 01234 567890 &middot; &copy; 2026</p>")),
]

# Object-type showcase: the web-specific objects, labelled.
WEBOBJ = [
    ("artistic", 40, 30, 640, 48, dict(html="<p>Web objects</p>", size=32, color="#1f2a30", bold=True)),
    ("nav", 40, 104, 500, 40, dict(style="pills", accent="#2a7d6b", accentInk="#ffffff", color="#1f2a30", size=14)),
    ("text", 560, 110, 360, 28, dict(pad=0, size=13, color="#5c6b73", html="<p>A navigation bar lists your pages automatically.</p>")),
    ("button", 40, 172, 200, 48, dict(html="<p>Get in touch</p>", size=15, bold=True, fill="#2a7d6b", color="#ffffff")),
    ("button", 260, 172, 200, 48, dict(html="<p>Download brochure</p>", size=15, bold=True, fill="#e0a43a", color="#1f2a30", radius=24)),
    ("text", 560, 182, 360, 28, dict(pad=0, size=13, color="#5c6b73", html="<p>Buttons carry a hyperlink and a style.</p>")),
    ("share", 40, 248, 440, 40, dict(nets=["facebook", "x", "linkedin", "whatsapp", "email"], style="colour")),
    ("text", 560, 252, 360, 28, dict(pad=0, size=13, color="#5c6b73", html="<p>Share buttons post the page to social media.</p>")),
    ("search", 40, 316, 400, 46, dict(placeholder="Search this site…", submit="Search", accent="#2a7d6b")),
    ("text", 560, 324, 360, 28, dict(pad=0, size=13, color="#5c6b73", html="<p>A search box finds anything on the site.</p>")),
    ("form", 40, 396, 380, 300, dict(fields=["Name", "Email", "Message"], submit="Send", accent="#2a7d6b")),
    ("table", 460, 396, 460, 150, dict(head="#e9eff2", cells=[["Service", "From"], ["Kitchen", "£2,400"], ["Staircase", "£1,800"], ["Repair", "£120"]])),
    ("text", 460, 566, 460, 28, dict(pad=0, size=13, color="#5c6b73", html="<p>A form collects enquiries; a table lays out data.</p>")),
    ("newsfeed", 460, 610, 460, 240, dict(accent="#2a7d6b", cardbg="#ffffff", ink="#1f2a30")),
]

SHAPES_DEMO = [
    ("artistic", 40, 30, 640, 48, dict(html="<p>Shapes, lines &amp; QuickShapes</p>", size=30, color="#1f2a30", bold=True)),
    ("shape", 40, 104, 150, 108, dict(shape="rect", fill="#9fc3d6", stroke="#2b3a42", strokeW=2)),
    ("shape", 212, 104, 150, 108, dict(shape="rect", fill="#cfe0e6", stroke="#2b3a42", strokeW=2, radius=18)),
    ("shape", 384, 104, 150, 108, dict(shape="ellipse", fill="#f4c96b", stroke="#8a6d1f", strokeW=2)),
    ("line", 560, 158, 200, 2, dict(stroke="#2b3a42", strokeW=3)),
    ("shape", 40, 244, 120, 120, dict(shape="star5", fill="#f4c96b", stroke="#c8851b", strokeW=2)),
    ("shape", 180, 244, 120, 120, dict(shape="arrow", fill="#5b8def", stroke="#2f5fb0", strokeW=2)),
    ("shape", 320, 244, 128, 120, dict(shape="heart", fill="#e8556b", stroke="#b2374b", strokeW=2)),
    ("shape", 470, 244, 150, 120, dict(shape="speech", fill="#ffffff", stroke="#2a7df0", strokeW=3)),
    ("shape", 640, 244, 120, 120, dict(shape="hexagon", fill="#49c5b6", stroke="#2a8577", strokeW=2)),
    ("shape", 40, 404, 170, 110, dict(shape="rect", fill="#2a7d6b", strokeW=0, shadow=dict(color="#000000", blur=16, dx=7, dy=9, opacity=40))),
    ("shape", 250, 404, 170, 110, dict(shape="rect", fill="#f4c96b", strokeW=0, glow=dict(color="#ffe08a", blur=22, opacity=85))),
    ("text", 40, 534, 500, 30, dict(pad=0, size=12, color="#5c6b73", html="<p>A filled rectangle (left) carries a drop shadow; the gold one has an outer glow.</p>")),
]

TEXT_DEMO = [
    ("artistic", 40, 30, 640, 48, dict(html="<p>Working with text</p>", size=30, color="#1f2a30", bold=True)),
    ("text", 40, 100, 400, 320, dict(size=14, color="#243137", html=(
        "<p><span style='font-size:230%'>O</span>nce a page begins with a large dropped capital, the "
        "eye knows where to start. Frame text wraps neatly inside its frame, and a frame that overruns "
        "can flow on to a second, linked frame.</p>"
        "<p>This second paragraph keeps an even left edge and a comfortable line height for reading on "
        "screen.</p>"))),
    ("text", 470, 100, 420, 320, dict(size=14, color="#243137", html=(
        "<p><b>A short checklist</b></p><ul><li>Type straight into a frame</li>"
        "<li>Link frames to flow long text</li><li>Give a heading its own look</li>"
        "<li>Add a bulleted or numbered list</li><li>Check spelling before you publish</li></ul>"))),
    ("artistic", 40, 450, 620, 60, dict(html="<p>Big artistic headlines</p>", size=42, color="#2a7d6b", bold=True)),
    ("text", 40, 526, 850, 30, dict(pad=0, size=12, color="#5c6b73", html="<p>Artistic text is a single line you scale freely &mdash; ideal for titles and mastheads; it stays sharp on the web as real text.</p>")),
]

COLOUR_DEMO = [
    ("artistic", 40, 24, 700, 48, dict(html="<p>Colour, gradients &amp; transparency</p>", size=28, color="#1f2a30", bold=True)),
    ("shape", 40, 96, 240, 150, dict(shape="rect", fill="#2a7d6b", strokeW=0)),
    ("shape", 310, 96, 240, 150, dict(shape="rect", strokeW=0, grad=dict(type="linear", c1="#8ad0c4", c2="#1d5c50", angle=90))),
    ("shape", 580, 96, 240, 150, dict(shape="rect", strokeW=0, grad=dict(type="linear", c1="#f6d98a", c2="#d6893a", angle=45))),
    ("text", 40, 254, 240, 24, dict(pad=0, size=12, color="#5c6b73", html="<p>Flat colour</p>")),
    ("text", 310, 254, 240, 24, dict(pad=0, size=12, color="#5c6b73", html="<p>Linear gradient</p>")),
    ("text", 580, 254, 240, 24, dict(pad=0, size=12, color="#5c6b73", html="<p>Angled gradient</p>")),
    ("picture", 40, 306, 860, 250, dict(fill="#9fb8c0", stroke="#7f98a0", strokeW=1)),
    ("shape", 40, 420, 860, 136, dict(shape="rect", fill="#13303a", strokeW=0, opacity=0.55)),
    ("artistic", 70, 454, 700, 54, dict(html="<p>White text on a half-transparent panel</p>", size=28, color="#ffffff", bold=True)),
    ("text", 40, 568, 860, 28, dict(pad=0, size=12, color="#5c6b73", html="<p>A semi-transparent dark panel over a photo keeps any text readable.</p>")),
]


# ------------------------------------------------------------------- capture
def _log(*a):
    print(*a, flush=True)


def capture(full=True):
    """Return {key: PIL image} for every picture the guide needs."""
    IM = {}

    # --- rendered demo pages (crisp, full-page) --------------------------
    _log("capture: demo pages…")
    IM["home"] = render_page(HOME, w=960, h=1176, px=920)
    IM["build1"] = render_page(HOME[:3], w=960, h=460, px=840)
    IM["build2"] = render_page(HOME[:7], w=960, h=460, px=840)
    IM["build3"] = render_page(HOME[:12], w=960, h=720, px=840)
    IM["webobj"] = render_page(WEBOBJ, w=960, h=880, px=900)
    IM["shapes"] = render_page(SHAPES_DEMO, w=960, h=600, px=880)
    IM["textpage"] = render_page(TEXT_DEMO, w=960, h=580, px=880)
    IM["colourpage"] = render_page(COLOUR_DEMO, w=960, h=620, px=880)

    # --- QuickShape catalogue: every shape in a labelled grid ------------
    _log("capture: quickshapes…")
    qs = PC.QUICKSHAPES
    grid, cols, cw, ch = [], 4, 215, 160
    palette = ["#2a7d6b", "#5b8def", "#e8556b", "#f4c96b", "#49c5b6", "#9b6bd8"]
    for i, (key, label) in enumerate(qs):
        cx, cy = 20 + (i % cols) * cw, 20 + (i // cols) * ch
        col = palette[i % len(palette)]
        grid.append(("shape", cx + 30, cy + 10, cw - 90, ch - 76, dict(shape=key, fill=col, stroke="#1f2a30", strokeW=2)))
        grid.append(("text", cx, cy + ch - 50, cw - 24, 24, dict(pad=0, size=13, color="#1f2a30", align="center", html=f"<p>{H.escape(label)}</p>")))
    rows = (len(qs) + cols - 1) // cols
    IM["qshapes"] = render_page(grid, w=cols * cw + 40, h=rows * ch + 40, px=900)

    # --- template catalogue (our basic + Serif's catalogue) -------------
    _log("capture: template catalogue…")
    tpl_cards = []     # (category, name, meta, PIL image)
    # our three basic templates
    for i, (name, kind, fn) in enumerate(PC.TEMPLATES):
        try:
            site = fn()
            img = _pil(PC.render_page_image(site, site["pages"][0], 520, crop=int(site["width"] * 1.4))).convert("RGB")
            tpl_cards.append(("Basic Templates", name, kind, img))
        except Exception as e:
            print("basic template failed:", name, e)
    # a representative sample from each Serif category (one scheme each)
    try:
        tree = PC.serif_tree(chooser_only=False)
    except Exception as e:
        tree = []
        print("serif tree failed:", e)
    picks_per_cat = {"Theme Layouts": 12, "Pro Templates": 8, "Sample Sites": 6}
    for category, surfaces in tree:
        label = PC.category_label(category)
        taken = 0
        want = picks_per_cat.get(label, 6)
        for surface, rows_ in surfaces:
            for r in rows_:
                if taken >= want:
                    break
                try:
                    schemes = PC.serif_schemes(r)
                    site = PC.serif_site(r, schemes[0] if schemes else None)
                    img = _pil(PC.render_page_image(site, site["pages"][0], 460,
                                                    crop=int(site["width"] * 1.35))).convert("RGB")
                    meta = f"{len(r['pages'])} pages" + (f" · {r['surface']}" if r.get("surface") else "")
                    tpl_cards.append((label, r["name"], meta, img))
                    taken += 1
                except Exception as e:
                    print("serif template failed:", r.get("name"), e)
            if taken >= want:
                break
    IM["_tpl_cards"] = tpl_cards
    # a count of the full catalogue for the prose
    try:
        total = sum(len(rows_) for _c, surfaces in tree for _s, rows_ in surfaces) + len(PC.TEMPLATES)
    except Exception:
        total = len(PC.TEMPLATES)
    IM["_tpl_total"] = total

    # --- workspace & panels (live window) --------------------------------
    _log("capture: workspace…")
    w = _win()
    PC_add(w, HOME)
    try:
        w.view.fit_width()
    except Exception:
        pass
    for _ in range(10):
        app.processEvents()
    full_ws = _grab(w)
    IM["workspace"] = full_ws
    W, Hh = full_ws.size
    IM["toolrail"] = full_ws.crop((0, 70, 56, min(Hh, 760)))
    IM["stdbar"] = full_ws.crop((48, 26, W, 76))

    # a clean (empty) workspace too
    w0 = _win()
    try:
        w0.view.fit_width()
    except Exception:
        pass
    for _ in range(6):
        app.processEvents()
    IM["workspace_empty"] = _grab(w0)

    # Startup Assistant pages
    _log("capture: startup assistant…")
    try:
        dlg = PC.StartupAssistant(w0)
        dlg.setAttribute(Qt.WA_DontShowOnScreen, True)
        dlg.resize(1040, 660)
        dlg.nav.setCurrentRow(0)
        dlg.show()
        for _ in range(16):
            app.processEvents()
        IM["startup_templates"] = _grab(dlg)
        dlg.nav.setCurrentRow(1)
        for _ in range(10):
            app.processEvents()
        IM["startup_new"] = _grab(dlg)
        dlg.nav.setCurrentRow(2)
        for _ in range(10):
            app.processEvents()
        IM["startup_open"] = _grab(dlg)
    except Exception as e:
        print("startup capture failed:", e)

    # Device preview window (website / tablet / phone)
    if os.environ.get("SKIP_DEVICE") != "1":
        _log("capture: device preview…")
        try:
            prev = _capture_device_preview(w)
            if prev is not None:
                IM["device"] = prev
        except Exception as e:
            print("device preview failed:", e, flush=True)

    # --- dialogs: drive the real commands; _cap_exec stores them ---------
    _log("capture: driving dialogs…")

    def drive(fn, *a):
        try:
            fn(*a)
        except Exception as e:
            print("drive failed:", getattr(fn, "__name__", fn), e)
        for _ in range(6):
            app.processEvents()

    w2 = _win()

    def seed(o):
        w2.layer().append(o)
        w2.sel = [o["id"]]
        w2.refresh()
        for _ in range(4):
            app.processEvents()
        return o

    # a selected shape for transform / effects / gradient
    shp = mk("shape", 120, 120, 320, 200, shape="rect", fill="#2a7d6b", strokeW=0)
    seed(shp)
    drive(w2.transform_dialog)
    drive(w2.effects_dialog)
    drive(w2.gradient_dialog, "linear")

    # web-object editors: each takes the object it edits
    drive(w2.nav_dialog, seed(mk("nav", 60, 60, 460, 40)))
    drive(w2.share_dialog, seed(mk("share", 60, 60, 480, 40)))
    # seed the gallery with a placeholder image key: an empty gallery pops a
    # native "Add Photos" file dialog on a 0ms timer, which blocks offscreen.
    drive(w2.gallery_dialog, seed(mk("gallery", 60, 60, 600, 320, images=["_placeholder"])))
    drive(w2.search_dialog, seed(mk("search", 60, 60, 360, 46)))
    drive(w2.form_dialog, seed(mk("form", 60, 60, 360, 300)))
    # Rollover / pop-up editor for a picture (needs a picture selected).
    if hasattr(w2, "rollover_dialog"):
        drive(w2.rollover_dialog, seed(mk("picture", 60, 60, 240, 170, src="_placeholder")))
    drive(w2.youtube_dialog, seed(mk("youtube", 60, 60, 560, 315)))
    drive(w2.map_dialog, seed(mk("map", 60, 60, 480, 320)))
    drive(w2.newsfeed_dialog, seed(mk("newsfeed", 60, 60, 480, 420)))
    drive(w2.html_dialog, seed(mk("html", 60, 60, 300, 120)))
    drive(w2.audio_dialog, seed(mk("audio", 60, 60, 320, 54)))
    drive(w2.table_dialog, seed(mk("table", 60, 60, 480, 160)))
    drive(w2.css_dialog)
    drive(w2.embed_dialog)
    drive(w2.transform_dialog)   # re-run harmless

    # SEO (per-page + site-wide), publish, page properties, master move
    for nm in ("seo_dialog", "site_seo_dialog"):
        if hasattr(w2, nm):
            drive(getattr(w2, nm))
    if hasattr(w2, "page_props"):
        drive(w2.page_props, w2.page())
    if hasattr(w2, "move_common_to_master"):
        drive(w2.move_common_to_master)
    if hasattr(w2, "check_links"):
        drive(w2.check_links)
    if hasattr(w2, "publish_disk"):
        drive(w2.publish_disk)

    IM["_dialogs"] = dict(DGRABS)
    _log("capture: done; dialogs captured:", len(DGRABS))
    return IM


def PC_add(w, objs):
    """Add the demo objects to a live window's current page."""
    for o in objs:
        w.layer().append(_mkobj(*o))
    w.sel = []
    try:
        w.refresh()
    except Exception:
        pass


def _capture_device_preview(win):
    """Open the in-app Device Preview window and grab it in phone mode."""
    try:
        cls = getattr(PC, "DevicePreviewDialog", None)
        if cls is None:
            return None
        # Build a published preview file the dialog can load.
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        files = PC.publish_site(win.site, str(tmp))
        first = win.site["pages"][0]["file"]
        url = (tmp / first).as_uri()
        dlg = cls(win, url, first)
        dlg.setAttribute(Qt.WA_DontShowOnScreen, True)
        dlg.resize(1100, 780)
        dlg.show()
        for _ in range(20):
            app.processEvents()
        try:
            dlg.set_device("phone")
        except Exception:
            pass
        for _ in range(16):
            app.processEvents()
        return _grab(dlg)
    except Exception as e:
        print("device preview grab failed:", e)
        return None


# ------------------------------------------------------------------- image out
def datauri(im, maxw=1100, quality=82):
    if im.mode != "RGB":
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
        im = bg
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ------------------------------------------------------------------- content DSL
def fig(im, cap, cls=""):
    if im is None:
        return ""   # a capture that didn't happen degrades to no figure, not a broken box
    uri = im if isinstance(im, str) else datauri(im)
    c = f" {cls}" if cls else ""
    return f'<figure class="f{c}"><img src="{uri}" alt="{H.escape(cap)}"><figcaption>{cap}</figcaption></figure>'


def proc(title, *steps, intro=""):
    lis = "".join(f"<li>{s}</li>" for s in steps)
    pre = f"<p>{intro}</p>" if intro else ""
    return f'<div class="proc"><p class="proc-h">To {title}</p>{pre}<ol class="steps">{lis}</ol></div>'


def note(body):
    return f'<div class="cal note"><span class="cal-k">Note</span>{body}</div>'


def tip(body):
    return f'<div class="cal tip"><span class="cal-k">Tip</span>{body}</div>'


def caution(body):
    return f'<div class="cal caution"><span class="cal-k">Remember</span>{body}</div>'


def K(x):
    return f"<kbd>{x}</kbd>"


# ------------------------------------------------------------------- the manual
def manual_parts(IM):
    """Returns a list of parts. Each part: (part_title, blurb, [chapters]).
    Each chapter: (title, intro_html, [(heading, body_html), ...])."""
    D = IM.get("_dialogs", {})

    def dlg(*names):
        for n in names:
            if n in D:
                return D[n]
        return None

    parts = []

    # ============================================================ PART I
    ch = []
    ch.append(("Welcome to WEBcreator",
      "<p class='lede'>WEBcreator is a <b>website design</b> program: a tool for arranging text, "
      "pictures, shapes, navigation bars, forms and media on a page exactly where you want them, and then "
      "publishing the result as a real, working website. It belongs to the <i>just a&hellip;</i> family of "
      "apps and works in the tradition of Serif's WebPlus &mdash; the same ideas, the same menus, in the "
      "same places.</p>", [
      ("What a website designer is", f"""
<p>A word processor pours text down a page. A website designer is different: the page is a canvas, and
everything on it &mdash; a logo, a headline, a block of text, a photo, a navigation bar, a button, a
contact form &mdash; is a separate <b>object</b> you position freely. You design the page by eye, and the
program writes the HTML and CSS for you behind the scenes.</p>
{fig(IM.get('home'), 'A one-page business site laid out in WEBcreator — header and navigation, a hero band, three service columns, a photo and a footer, each an independent object.')}
<p>If you have used Wix, Squarespace or Serif's WebPlus, you already know the idea. The one thing to
unlearn, if you have only used a word processor, is this: you no longer type <i>down</i> a page &mdash;
you place things <i>on</i> it, and the finished page is a website, not a printout.</p>"""),
      ("The object model", """
<p>Everything you put on a page is an object. There are the familiar layout objects &mdash; text frames,
artistic text, pictures, shapes and lines, tables &mdash; and then the <b>web objects</b> that make a page
a living site:</p>
<ul>
<li><b>Navigation bars</b> that list your pages automatically;</li>
<li><b>Buttons</b> that link somewhere;</li>
<li><b>Forms</b> for enquiries, and <b>search boxes</b>;</li>
<li><b>Share buttons</b> for social media;</li>
<li><b>Photo galleries</b>, <b>YouTube</b> and <b>Vimeo</b> video, <b>audio</b> players and <b>Google Maps</b>;</li>
<li>a <b>News Feed</b> that builds itself from your pages;</li>
<li><b>HTML fragments</b> and <b>custom CSS</b> for anything bespoke.</li>
</ul>
<p>Because they are all objects, the skills are shared: whatever the kind, you select it, move it, resize
it, colour it, align it and layer it in exactly the same way. Learn those moves once and they apply
everywhere.</p>"""),
      ("The just a… family", """
<p>WEBcreator has three companions, built to work together:</p>
<ul>
<li><b>PAGEdesigner</b> makes printed documents &mdash; flyers, newsletters, booklets &mdash; the same way
WEBcreator makes websites;</li>
<li><b>PAINTcanvas</b> is the image editor &mdash; WEBcreator hands a photo to it for retouching and gets the
result straight back;</li>
<li><b>DRAWmaster</b> is for vector illustration and logos.</li>
</ul>
<p>They share the <b>CREATORsuite</b> launcher and a common <i>Documents/just a&hellip;</i> folder, so your
work is easy to find. Once you know one app, the others feel familiar.</p>"""),
      ("About this guide", f"""
<p>This User Guide is the complete reference. It is organised in parts: the first gets you working, the
middle teaches each skill in depth with step-by-step procedures, then come the web objects and site-wide
features, worked projects you can follow start to finish, publishing, and finally a reference section &mdash;
menus, shortcuts, a catalogue of templates and shapes, a glossary and troubleshooting.</p>
{note('Throughout, a numbered <b>“To &hellip;”</b> box is a procedure you can follow exactly. A <b>Tip</b> suggests a faster or better way. A <b>Remember</b> box flags something easy to forget.')}
<p>For a gentler first read, start with the <b>Quick Start Guide</b> (Help &#9656; Quick Start), which takes
you from a blank page to a published site in about a dozen short steps.</p>"""),
      ("Conventions used here", f"""
<p>A few conventions keep the instructions short:</p>
<ul>
<li><b>Menu &#9656; Command</b> means “open this menu and choose this command”, e.g. <b>File &#9656; Publish&hellip;</b>.</li>
<li>Keys are shown like {K('Ctrl')}+{K('S')}; on a Mac read {K('Ctrl')} as {K('Cmd')}.</li>
<li><b>Click</b> means the left mouse button; <b>right-click</b> opens a context menu; <b>double-click</b>
opens whatever the object is for (its editor dialog, or edit-in-place for text).</li>
<li><b>Drag</b> means press, move, release.</li>
</ul>""")]))

    ch.append(("Starting Out",
      "<p class='lede'>This chapter covers the very first things: launching the program, the Startup "
      "Assistant that greets you, and the three ways to begin a site &mdash; from a ready-made design, from "
      "a blank page, or by opening work you already have.</p>", [
      ("Launching the program", """
<p>Open <b>just a&hellip; WEBcreator</b> from the CREATORsuite launcher, from your system's application
menu, or by running <code>webcreator</code> in a terminal. The first time it opens it may take a moment to
settle; after that it starts quickly.</p>"""),
      ("The Startup Assistant", f"""
<p>Each time it launches, WEBcreator shows the <b>Startup Assistant</b> &mdash; your hub for beginning work.
Down its left side are three sections: <b>Use Design Template</b>, <b>Start New Site</b> and <b>Open Saved
Site</b>.</p>
{fig(IM.get('startup_templates'), 'The Startup Assistant, open on Use Design Template. Pick a design on the left, choose a colour scheme, untick any pages you don’t want, then open it.')}
{proc('begin from the Startup Assistant',
  'Choose <b>Use Design Template</b> to start from a ready-made design (see the next chapter),',
  'or <b>Start New Site</b> to begin with a blank page of a chosen width,',
  'or <b>Open Saved Site</b> to reopen recent work or browse for a saved file.',
  'Make your choice and the Assistant closes, leaving your new site open.')}
{tip('Prefer to start straight on a blank page? Untick <b>Show the Startup Assistant when the app opens</b> at the bottom. You can always begin a new site from <b>File ▸ New Site</b>.')}"""),
      ("Starting a blank site", f"""
<p>Choose <b>Start New Site</b> to begin with an empty page.</p>
{fig(IM.get('startup_new'), 'Start New Site — name the site, set a page width, choose a column layout, and decide whether it should be responsive.')}
{proc('start a blank site',
  'In <b>Start New Site</b>, give the site a <b>name</b>.',
  'Choose a <b>page width</b> in pixels (960 suits most sites; 1000 or 1200 give a wider canvas).',
  'Pick a <b>column layout</b> — full width, two columns or three — to lay guide frames you can drop content into.',
  'Decide on <b>Responsive</b> (see below), then click <b>Create Site</b>.')}
{note('A website page has a fixed width but grows as tall as its content — you drag the page’s bottom edge to make it longer, so there is no fixed “paper size” as there would be in a print program.')}"""),
      ("Fixed-width or responsive", f"""
<p>A website can be laid out two ways, and you choose which at the start (and again when you publish):</p>
<ul>
<li><b>Static (fixed width)</b> &mdash; the classic approach. The page is exactly as wide as you designed it;
on a narrow phone the visitor pinches and scrolls. Simple and predictable, and best when most of your
visitors are on a desktop.</li>
<li><b>Responsive</b> &mdash; the whole design scales down to fit any screen, so a visitor on a phone sees the
full layout shrunk to fit without side-scrolling. This is the modern default for a site that will be read
on phones and tablets.</li>
</ul>
{tip('Not sure? Leave it static while you design, then turn Responsive on at Publish time and preview it on a phone — you can switch back and forth freely.')}"""),
      ("Opening and saving", f"""
<p>WEBcreator sites are saved with a <code>.webc</code> extension.</p>
{proc('save your work',
  'Choose <b>File ▸ Save</b> or press ' + K('Ctrl') + '+' + K('S') + '.',
  'The first time, give the site a name. It is saved into your shared <i>Documents/just a…</i> folder by default, so the launcher can find it.',
  'Use <b>File ▸ Save As…</b> to keep a separate copy under a new name.')}
{proc('open an existing site',
  'Choose <b>File ▸ Open</b> and browse to a <code>.webc</code> file, or',
  'pick a recent file from <b>File ▸ Open Recent</b>, or from the <b>Open Saved Site</b> page of the Startup Assistant.')}
<p>WEBcreator also opens work from the program it stands in for and from the web at large: <b>File &#9656;
Open WebPlus Site&hellip;</b> reads a Serif WebPlus <code>.wpp</code> publication, and from the Startup
Assistant's <b>Import&hellip;</b> menu you can import a whole website folder, or a single web page from its
URL, each as an editable site.</p>""")]))

    ch.append(("The Workspace",
      "<p class='lede'>Everything you do happens in the workspace: your page in the middle, the tools "
      "down the left, the menus and toolbars along the top, and the panels on the right. This chapter "
      "names every part so the rest of the guide can refer to them.</p>", [
      ("A tour of the window", f"""
<p>A new site opens with the page centred and everything you need arranged around it.</p>
{fig(IM.get('workspace'), 'The WEBcreator workspace: the tool palette (left), menus and toolbars (top), the page (centre) and the tabbed panels (right).')}
<p>The parts are:</p>
<ul>
<li>the <b>menu bar</b> and <b>toolbars</b> across the top;</li>
<li>the <b>tool palette</b> down the left edge;</li>
<li>the <b>rulers</b> framing the page;</li>
<li>the <b>page</b> itself in the centre;</li>
<li>the tabbed <b>panels</b> on the right;</li>
<li>the <b>status bar</b> along the bottom, where a hint explains the current tool.</li>
</ul>"""),
      ("The tool palette", f"""
<p>The vertical <b>tool palette</b> on the left holds the tools you draw and edit with. It is longer than a
print program's, because a website has more kinds of object.</p>
{fig(IM.get('toolrail'), 'The tool palette, top to bottom.', 'tall')}
<p>From the top: the <b>Pointer</b> (select and move), the <b>Hand</b> and <b>Zoom</b> tools for getting
around, then the object tools grouped by kind &mdash; <b>Artistic Text</b> and <b>Creative Frame Text</b>;
<b>Table</b>; <b>Picture</b>, <b>Lightbox Image</b> and <b>Photo Gallery</b>; <b>Rectangle</b>,
<b>Ellipse</b> and <b>Line</b>; then the web objects: <b>Navigation Bar</b>, <b>Button</b>, <b>Form</b>,
<b>Search Box</b>, <b>Share Buttons</b>, <b>HTML Code</b>, <b>YouTube</b>, <b>Vimeo</b>, <b>Audio</b>,
<b>Google Map</b> and <b>News Feed</b>. Click a tool, then drag on the page to place it; its name and a hint
appear in the status bar.</p>
{tip('Press ' + K('Esc') + ' or click the Pointer at any time to stop drawing and go back to selecting.')}"""),
      ("Menus and toolbars", f"""
<p>The <b>menu bar</b> gathers every command under <b>File</b>, <b>Edit</b>, <b>View</b>, <b>Insert</b>,
<b>Format</b>, <b>Arrange</b>, then the <b>Preview</b>, <b>Publish</b> and <b>SEO</b> items and <b>Help</b>.
The complete menu reference is Appendix A.</p>
{fig(IM.get('stdbar'), 'The Standard toolbar: new, open and save; undo and redo; cut, copy and paste; and a View HTML toggle.')}
<p>Below the menus, the <b>Standard</b> toolbar carries the everyday buttons and a <b>View HTML</b> toggle
that reveals the page's source. An <b>Insert</b> toolbar sits alongside it with Site Structure and the
alignment buttons, and an <b>Apps</b> toolbar links across to PAINTcanvas and PAGEdesigner.</p>"""),
      ("The panels", f"""
<p>The tabbed <b>panels</b> on the right are where you inspect and fine-tune whatever is selected &mdash;
the <b>Site</b> / Pages structure, <b>Transform</b>, <b>Colour</b>, <b>Swatches</b> and <b>Layers</b>.
The Site panel is the heart of a multi-page site: it shows every page as a tree you can add to, rename and
reorder.</p>
{tip('The <b>Site Structure</b> button on the Insert toolbar brings the Site / Pages panel to the front whenever you need to jump between pages or rearrange them.')}"""),
      ("Moving around and zooming", f"""
<p>You will zoom in to place things precisely and out to judge the whole page.</p>
{proc('change the zoom',
  'Hold ' + K('Ctrl') + ' and scroll the mouse wheel, or',
  'choose <b>View ▸ Zoom In</b> / <b>Zoom Out</b>, or',
  'use <b>View ▸ Actual Size</b> and <b>Fit Page Width</b> to jump to 100% or to frame the full width.')}
<p>The <b>Hand</b> tool &mdash; or holding the space bar and dragging &mdash; slides the page around when you
are zoomed in.</p>"""),
      ("Rulers, grid and snapping", f"""
<p>The <b>rulers</b> along the top and left show position in pixels. From the <b>View</b> menu you can toggle
the rulers, a background <b>grid</b>, <b>snap to grid</b> and a <b>crosshair</b> that follows the cursor.
Snapping, and the gentle pull objects give off as you drag past each other's edges and centres, is how you
keep columns, rows and margins lined up without measuring.</p>
{fig(IM.get('workspace_empty'), 'A fresh, empty site — the page in the centre waiting for its first object.')}""")]))

    parts.append(("Part I", "Getting Started", ch))

    # ============================================================ PART II
    ch = []
    ch.append(("Working with Objects",
      "<p class='lede'>Text frames, pictures, shapes, buttons, forms and galleries are all <b>objects</b>, "
      "and they are handled the same way. Master the moves in this chapter &mdash; select, move, size, "
      "rotate, align, order, group, lock &mdash; and they serve you everywhere in the program.</p>", [
      ("Placing an object", f"""
{proc('place any object',
  'Click its tool in the palette (or choose it from the <b>Insert</b> menu).',
  'Drag a box on the page where you want it. For web objects such as a picture, gallery or map, an editor opens so you can set it up.',
  'Switch to the <b>Pointer</b> to move or resize it.')}
{note('<b>Insert ▸ …</b> drops a default-sized object in the centre of the page if you would rather not drag out its size by hand.')}"""),
      ("Selecting objects", f"""
{proc('select objects',
  'Choose the <b>Pointer</b> tool.',
  'Click an object to select it — a frame of handles appears around it.',
  'Hold ' + K('Shift') + ' and click more objects to add them to the selection.',
  'Or drag a box across empty space to select everything it touches.',
  'Press ' + K('Esc') + ' (or click empty space) to deselect; ' + K('Ctrl') + '+' + K('A') + ' selects everything on the page.')}"""),
      ("Moving and resizing", f"""
<p>With one or more objects selected:</p>
<ul>
<li><b>Move</b> &mdash; drag any selected object; the whole selection moves together.</li>
<li><b>Resize</b> &mdash; drag a corner or edge handle. Dragging a corner keeps a picture's proportions.</li>
<li><b>Nudge</b> &mdash; tap the arrow keys to move a small, exact step at a time.</li>
<li><b>Rotate</b> &mdash; drag the round handle above the object, or use the <b>Rotate</b> tool.</li>
</ul>
{tip('Guides, the grid and other objects give off a gentle snap as you drag past their edges and centres — let it do the aligning for you.')}"""),
      ("The Transform panel", f"""
<p>When “close enough” is not enough, the <b>Transform</b> panel (and <b>Arrange &#9656; Transform&hellip;</b>)
lets you type exact numbers.</p>
{fig(dlg('Transform'), 'The Transform dialog: exact X and Y position, width, height and rotation angle.')}
{proc('place an object precisely',
  'Select the object.',
  'Open <b>Transform</b> and type its <b>X</b> and <b>Y</b> position, its <b>width</b> and <b>height</b>, or a <b>rotation</b> angle.',
  'Press ' + K('Enter') + '. This is the reliable way to make two objects exactly the same size, or to sit something a precise distance from the edge.')}"""),
      ("Aligning and distributing", """
<p>Alignment is what turns a rough arrangement into a crisp one. Select two or more objects, then use
<b>Arrange &#9656; Align</b>:</p>
<ul>
<li><b>Left / Centre / Right edges</b> line up their vertical edges or centres;</li>
<li><b>Top / Middle / Bottom edges</b> line up their horizontal edges or centres;</li>
<li><b>Centre on Page Horizontally</b> centres the selection across the page.</li>
</ul>
<p>A row of buttons, a grid of photos, a stack of headings &mdash; all look intentional once aligned. The
alignment buttons are also on the Insert toolbar for one-click access.</p>"""),
      ("Order, grouping and locking", f"""
<p>Objects stack in the order you create them, newest on top. Use <b>Arrange</b> to change that:</p>
<ul>
<li><b>Bring to Front</b> / <b>Send to Back</b>, and <b>Forward One</b> / <b>Back One</b>, so a caption can sit over a photo;</li>
<li><b>Lock / Unlock</b> ({K('Ctrl')}+{K('L')}) pins something so you cannot nudge it by accident.</li>
</ul>
{caution('A locked object cannot be dragged — that is the point. Unlock it from <b>Arrange ▸ Lock / Unlock</b> when you need to move it again.')}"""),
      ("Cut, copy, paste and duplicate", f"""
<p>The usual editing commands all apply to objects:</p>
<ul>
<li>{K('Ctrl')}+{K('X')} / {K('Ctrl')}+{K('C')} / {K('Ctrl')}+{K('V')} cut, copy and paste;</li>
<li><b>Duplicate</b> ({K('Ctrl')}+{K('D')}) drops a copy a little offset from the original;</li>
<li>{K('Ctrl')}+{K('Z')} undoes and redo steps forward again &mdash; there is a deep undo history, so experiment freely.</li>
</ul>
{tip('Copying an object and pasting it onto another page is the simplest way to reuse something you have built — a styled heading, a logo, a coloured panel.')}""")]))

    ch.append(("Text",
      "<p class='lede'>Text is the heart of most pages. WEBcreator handles it the WebPlus way: body copy "
      "lives in frames you can link and flow, headlines are artistic text you scale freely, and it all "
      "publishes as real, selectable, searchable web text &mdash; never as a picture of words.</p>", [
      ("Frame text", f"""
{proc('add a block of body text',
  'Choose the <b>Creative Frame Text</b> tool.',
  'Drag a rectangle on the page — that is a text frame.',
  'Type, or paste; the text wraps inside the frame’s edges automatically.',
  'Switch to the <b>Pointer</b> to move or resize the frame; the text re-wraps to fit.')}
{fig(IM.get('textpage'), 'Frame text with a dropped capital and a bulleted list (left), beside an artistic headline.')}"""),
      ("Artistic text", """
<p>Where frame text is for paragraphs, <b>artistic text</b> is a single line you can scale to any size
&mdash; the tool for mastheads, titles and pull-quotes. Choose the Artistic Text tool, click, and type; then
drag a corner handle to make it as large as you like. It publishes as ordinary styled web text, so it stays
sharp at any size and a search engine can still read it.</p>"""),
      ("Fonts, size, colour and alignment", f"""
<p>Select some text &mdash; a word, a line or a whole frame &mdash; and set its look from the <b>Format</b>
menu and the text controls:</p>
<ul>
<li><b>Font</b> and <b>size</b>;</li>
<li><b>Bold</b> ({K('Ctrl')}+{K('B')}), <b>Italic</b> ({K('Ctrl')}+{K('I')}) and <b>Underline</b> ({K('Ctrl')}+{K('U')});</li>
<li><b>Colour</b>, from the Colour panel;</li>
<li><b>Alignment</b> &mdash; left, centred, right or justified;</li>
<li><b>Line spacing</b>, to open a dense block up or draw a loose one in.</li>
</ul>
{note('WEBcreator embeds the fonts it needs when it publishes, so a visitor sees the typeface you chose even if they do not have it installed.')}"""),
      ("Lists", f"""
{proc('turn paragraphs into a bulleted or numbered list',
  'Select the paragraphs.',
  'Choose a style from <b>Format ▸ Lists / Bullets</b> — a disc, circle or square bullet, or 1-2-3, a-b-c or i-ii-iii numbering.',
  'The list indents neatly; a numbered list renumbers itself if you add or remove an item. <b>Remove list</b> turns it back into plain paragraphs.')}"""),
      ("Hyperlinks in text", f"""
<p>Any word or phrase can become a link.</p>
{proc('make text into a link',
  'Select the words you want to turn into a link.',
  'Choose <b>Insert ▸ Hyperlink…</b>.',
  'Choose where it goes — another page in your site, a web address, an email, or an anchor further down the page — and click <b>OK</b>.',
  'The linked words take on the site’s link colour; test them in Preview.')}
<p>Links are covered in full in the <i>Navigation, Links &amp; Site Structure</i> chapter.</p>"""),
      ("Importing text, and spell check", f"""
<p><b>Insert &#9656; Import Text&hellip;</b> pours a long text file straight into a frame, so you can draft in
a word processor and lay it out here. Before you publish, check the spelling:</p>
{proc('check spelling across the whole site',
  'Choose <b>Format ▸ Check Spelling…</b> or press ' + K('F7') + '.',
  'WEBcreator scans the text on every page and lists any word it does not recognise.',
  'For each one, choose a suggestion and <b>Change All</b>, <b>Ignore</b> it, or <b>Add to Dictionary</b>.')}
{fig(dlg('Spell Check'), 'The spell checker gathers unknown words from every page, with suggestions.')}
{note('The first time you use it, WEBcreator offers to download a small English dictionary (about 4&nbsp;MB, once).')}""")]))

    ch.append(("Pictures and Galleries",
      "<p class='lede'>Pictures bring a page to life. WEBcreator keeps them in frames you can crop and "
      "style, turns one into a click-to-enlarge lightbox, strings several into a gallery, and hands off to "
      "PAINTcanvas when a photo needs real editing.</p>", [
      ("Picture frames", f"""
{proc('place a photograph',
  'Choose the <b>Picture</b> tool and drag a box — a picture frame.',
  'Choose an image file when prompted (or double-click an empty frame later).',
  'The picture fills the frame. Design the layout first with empty frames and drop the photos in later — a frame can wait.')}
{note('Keeping images in frames (rather than loose on the page) lets you resize the hole and the picture independently, and swap one photo for another without disturbing the layout. WEBcreator copies each picture into the site, so publishing gathers everything it needs.')}"""),
      ("Fitting, cropping and borders", f"""
<p>A picture either <b>fills</b> its frame (cropping to the edges) or sits <b>inside</b> it. To show only
part of a photo, use the <b>Crop</b> tool:</p>
{proc('crop a picture',
  'Select the picture and choose the <b>Crop</b> tool (or double-click to open Crop Picture).',
  'Drag the handles inward to hide the parts you do not want.',
  'Switch back to the Pointer. The hidden area is kept, so you can re-crop later.')}
{fig(dlg('Crop Picture'), 'The Crop Picture tool trims a photo without discarding the hidden part.')}
<p>Round the frame's corners or give it an outline from the panels to finish it off.</p>"""),
      ("Rollovers and pop-ups", f"""
<p>A <b>rollover</b> makes a picture react when a visitor points at it. WEBcreator gives any picture two
kinds of rollover, and both are self-contained &mdash; they work on the published page with no scripts and
no server:</p>
<ul>
<li><b>Rollover image</b> &mdash; a second picture that fades in while the mouse is over the frame (and swaps
back when it leaves). Perfect for &ldquo;on / off&rdquo; buttons, before/after shots or a highlight state.</li>
<li><b>Pop-up rollover</b> &mdash; a small panel (a thumbnail, a caption, or both) that pops up above the
picture on hover &mdash; a tooltip-style label or a preview.</li>
</ul>
{proc('give a picture a rollover',
  'Place a picture and choose its main image.',
  'Select it and click the <b>Rollover</b> tool on the left-hand rail (or right-click the picture &#9656; <b>Rollover and Pop-up&hellip;</b>).',
  'Choose a <b>Rollover image</b> to swap in on hover, and/or a <b>pop-up</b> image and <b>caption</b>.',
  'Click <b>OK</b>. A small <i>rollover</i> badge marks the picture on the canvas; preview the effect in the browser via Device Preview or by publishing.')}
{fig(dlg('Rollover and Pop-up'), 'The Rollover editor: a hover image swap, plus an optional pop-up image and caption.')}
{note('The main image is what shows on the editing canvas; the hover swap and pop-up appear on the live site. The rollover also triggers on keyboard focus, so it stays accessible.')}"""),
      ("Lightbox images", """
<p>A <b>Lightbox Image</b> is a thumbnail that, when a visitor clicks it, opens the full-size picture in a
dark overlay over the page &mdash; the familiar way to show a gallery of photos without sending the visitor
to another page. Place it like any picture, and set its small (thumbnail) and large (full) images.</p>"""),
      ("Photo galleries", f"""
<p>A <b>Photo Gallery</b> shows a series of pictures in turn, fading from one to the next &mdash; perfect for
a hero banner or a portfolio strip.</p>
{proc('build a photo gallery',
  'Choose the <b>Photo Gallery</b> tool and drag out its size.',
  'In the <b>Photo Gallery</b> editor, add the pictures it should show and put them in order.',
  'Set the <b>interval</b> between slides and the <b>fade</b> time, and how each picture should fit its frame.',
  'Click <b>OK</b>. The gallery cycles automatically on the published page.')}
{fig(dlg('Photo Gallery'), 'The Photo Gallery editor — add images, order them, and set the slide interval and fade.')}"""),
      ("Editing a photo in PAINTcanvas", f"""
<p>When a photo needs more than cropping &mdash; brightening, retouching, removing a background &mdash;
WEBcreator sends it to its sister app.</p>
{proc('edit a picture in PAINTcanvas',
  'Select the picture.',
  'Click <b>Edit in PAINTcanvas</b> on the Apps toolbar.',
  'Make your edits in PAINTcanvas and save. The edited version comes straight back into your page, in place.')}
{tip('No photo to hand? <b>Create an image with AI</b> can generate one from a short description, dropped straight into the selected frame.')}""")]))

    ch.append(("Shapes, Lines and QuickShapes",
      "<p class='lede'>Shapes and lines give a page structure and emphasis &mdash; a coloured band behind a "
      "header, a rule between sections, a star on an offer. WEBcreator's QuickShapes give you twenty ready "
      "outlines, each with a fill, an outline and optional effects.</p>", [
      ("Drawing shapes and lines", f"""
{proc('draw a shape or a line',
  'Choose the <b>Rectangle</b>, <b>Ellipse</b> or <b>Line</b> tool (or a QuickShape from <b>Insert ▸ QuickShapes</b>).',
  'Drag on the page to draw it. Hold ' + K('Shift') + ' to constrain a perfect square or circle.',
  'Switch to the Pointer to move, resize or recolour it.')}
{fig(IM.get('shapes'), 'Basic shapes, a line, a row of QuickShapes, and the same rectangle with a drop shadow and with an outer glow.')}
<p>A full-width filled rectangle makes the coloured band behind a header or hero — the teal band on the
sample home page is exactly that.</p>"""),
      ("The QuickShape catalogue", f"""
<p><b>QuickShapes</b> are ready-made outlines. Pick one from the tool palette's Rectangle/Ellipse, or the
rest from <b>Insert &#9656; QuickShapes</b>, drag it out, then resize and recolour it like any other shape.</p>
{fig(IM.get('qshapes'), 'All of WEBcreator’s QuickShapes.')}
<p>They cover geometry (triangles, diamonds, polygons), stars, arrows and a chevron, and the expressive
shapes &mdash; heart, lightning bolt, speech bubble and cloud.</p>"""),
      ("Fills, outlines and dashes", """
<p>Every shape has a <b>fill</b> and an <b>outline</b>, set from the Colour panel. Set the outline <b>width</b>
to zero for a shape with no border at all &mdash; the usual choice for a coloured background band. A line can
be made solid or <b>dashed</b>.</p>"""),
      ("Drop shadow and glow", f"""
<p>Filter effects lift an object off the page, and WEBcreator publishes them as real CSS filters so they
appear on the live site too.</p>
{proc('add a drop shadow or a glow',
  'Select the shape (or picture, or text).',
  'Open the <b>Effects</b> dialog (<b>Effects — Shadow &amp; Glow</b>).',
  'Tick <b>Enable drop shadow</b> and set its colour, blur, offset and strength — or tick <b>Enable outer glow</b> for a soft halo.',
  'Click <b>OK</b>.')}
{fig(dlg('Effects — Shadow & Glow', 'Effects'), 'The Effects dialog controls a drop shadow and an outer glow; both preview live.')}""")]))

    ch.append(("Colour, Gradients and Transparency",
      "<p class='lede'>Colour ties a site together. WEBcreator offers solid colours, swatches you keep to "
      "hand, smooth gradient fills, a coordinated site palette, and adjustable transparency.</p>", [
      ("Applying colour", f"""
{proc('colour an object',
  'Select it.',
  'Open the <b>Colour</b> panel and choose whether you are setting the <b>fill</b>, the <b>outline</b> or the <b>text</b> colour.',
  'Pick a colour with the sliders, or type a <b>hex</b> value like <code>#2a7d6b</code>, or click a saved swatch.')}
{fig(IM.get('colourpage'), 'Flat colour, a linear gradient and an angled gradient; below, a semi-transparent panel keeps white text readable over a photo.')}"""),
      ("Swatches and the site palette", """
<p>The <b>Swatches</b> panel keeps a palette of colours one click away, so a site stays consistent &mdash;
save a colour you use often and reuse it everywhere rather than matching hex values by hand. When you start
from a design template, its <b>colour scheme</b> fills the palette for you, so every heading, band and button
already belongs to the same small, coordinated set.</p>"""),
      ("Gradient fills", f"""
<p>A <b>gradient</b> fades one colour smoothly into another across a shape &mdash; a sky behind a headline, a
soft panel behind text.</p>
{proc('fill a shape with a gradient',
  'Select the shape.',
  'Open the <b>Linear Gradient</b> (or <b>Radial Gradient</b>) dialog.',
  'Choose a <b>start</b> and <b>end</b> colour, and for a linear gradient, an <b>angle</b>.',
  'Click <b>OK</b>. The gradient scales with the object as you resize it, and publishes as a CSS gradient.')}
{fig(dlg('Linear Gradient', 'Radial Gradient'), 'The gradient dialog: a start colour, an end colour and an angle.')}"""),
      ("Transparency", """
<p><b>Transparency</b> lets what is behind an object show through it. A half-transparent coloured rectangle
laid over a photo makes a tint you can read white text on; a faint shape becomes a watermark. Set an object's
transparency from the panel &mdash; from fully solid to barely there.</p>""")]))

    ch.append(("Tables and HTML",
      "<p class='lede'>Beyond free text, WEBcreator builds the structured pieces a real site needs: tables "
      "for data, and — for anything bespoke — a raw HTML fragment and your own site-wide CSS.</p>", [
      ("Tables", f"""
{proc('insert a table',
  'Choose the <b>Table</b> tool (or <b>Insert ▸ Table</b>) and drag out its size.',
  'Double-click the table to open the <b>Edit Table</b> editor.',
  'Set the number of rows and columns, type into the cells, and give the header row its own fill.',
  'Click <b>OK</b>. Drag the table’s edges to resize it.')}
{fig(dlg('Edit Table'), 'The table editor: set rows and columns, type the cell contents, and style the header.')}
<p>A table is ideal for a price list, an opening-hours grid, or a simple comparison.</p>"""),
      ("HTML fragments", f"""
<p>When you need something WEBcreator does not build in &mdash; a booking widget, a third-party map, a snippet
from another service &mdash; drop in an <b>HTML Code</b> object and paste the code.</p>
{proc('add a block of custom HTML',
  'Choose the <b>HTML Code</b> tool and drag out a box.',
  'In <b>Edit HTML Fragment</b>, paste or type the HTML.',
  'Click <b>OK</b>. The fragment is published exactly as written, inside your layout.')}
{fig(dlg('Edit HTML Fragment'), 'The HTML fragment editor accepts any markup and publishes it verbatim.')}"""),
      ("Embeds: comments, sign-ups and forms", f"""
<p><b>Insert &#9656; Embed&hellip;</b> is a shortcut to the most common third-party blocks &mdash; a comments
thread, a newsletter sign-up, an external form &mdash; so you do not have to find the embed code yourself.</p>
{fig(dlg('Insert Embed', 'Embed'), 'The Embed helper offers ready-made blocks for comments, sign-ups and forms.')}"""),
      ("Custom CSS", f"""
<p>For a site-wide tweak &mdash; a web font, a hover effect, a rule that applies to every page &mdash; add your
own <b>Custom CSS</b>.</p>
{proc('add your own CSS',
  'Choose <b>Insert ▸ Custom CSS…</b> (it sits right after Insert ▸ HTML Code).',
  'Type or paste your CSS rules.',
  'Click <b>OK</b>. The rules are written into every published page’s stylesheet.')}
{fig(dlg('Custom CSS'), 'Custom CSS is added to the whole site’s stylesheet.')}
{caution('Custom HTML and CSS are powerful but unchecked — a mistake can break a page’s layout. Preview after any change.')}""")]))

    parts.append(("Part II", "Core Skills", ch))

    # ============================================================ PART III (web)
    ch = []
    ch.append(("The Web Objects",
      "<p class='lede'>These are the objects that make a page a living website rather than a static picture: "
      "navigation bars, buttons, forms, search, share buttons, video, audio, maps and a self-building news "
      "feed. Each is placed like any object, then set up in its own editor.</p>", [
      ("An overview", f"""
<p>All the web objects, shown together on one page:</p>
{fig(IM.get('webobj'), 'The web objects — a navigation bar, buttons, share buttons, a search box, a form, a table and a news feed.')}
<p>You add each from the tool palette or the <b>Insert</b> menu, and most open an editor as soon as you place
them so you can set them up straight away.</p>"""),
      ("Navigation bars", f"""
<p>A <b>Navigation Bar</b> lists the pages of your site as links &mdash; and it does it <i>automatically</i>,
so adding or renaming a page updates every nav bar at once.</p>
{proc('add a navigation bar',
  'Choose the <b>Navigation Bar</b> tool and drag it across the top of the page (usually on a master page, so it appears on every page).',
  'Double-click it to open the <b>Navigation Bar</b> editor.',
  'Choose a <b>style</b> — pills, underline or plain — and whether it runs across (horizontal) or down (vertical).',
  'Set the font, size and accent colour, then click <b>OK</b>.')}
{fig(dlg('Navigation Bar'), 'The Navigation Bar editor: style, orientation, font and accent colour. The links themselves come from your pages.')}
<h3>Multi-level drop-down menus</h3>
<p>When your site has <b>sub-pages</b>, the navigation bar nests them automatically as <b>drop-down menus</b>.
A top-level page that has sub-pages shows a small &#9662; arrow; hovering (or tabbing to) it reveals its
sub-pages beneath.</p>
{proc('build a drop-down menu',
  'Add the parent page as usual (for example <b>Services</b>).',
  'Add each child with <b>Insert &#9656; Page</b> and tick <b>&ldquo;Make it a sub-page&rdquo;</b> — it nests under the page above it.',
  'That is all: the navigation bar builds the drop-down by itself, both in automatic mode and when you hand-pick pages in the editor.')}
{note('The drop-down is pure HTML and CSS — no scripts — so it works on every browser and is keyboard-accessible (it opens on focus as well as hover). On a phone the whole menu, sub-pages included, folds into the slide-in hamburger panel.')}"""),
      ("Buttons", f"""
<p>A <b>Button</b> is a styled call to action that links somewhere &mdash; “Get a quote”, “Buy now”,
“Download”.</p>
{proc('add a button',
  'Choose the <b>Button</b> tool and drag out its size.',
  'Double-click it and type its words.',
  'Set its fill colour and corner radius from the panels, and give it a <b>hyperlink</b> (Insert ▸ Hyperlink) to a page, a URL, an email or a file.')}
{tip('The <b>Buy Me a Coffee</b> button on the Insert toolbar drops a ready-made, palette-matched support button in one click.')}"""),
      ("Forms", f"""
<p>A <b>Form</b> lets visitors send you an enquiry without revealing your email address to spammers.</p>
{proc('add a contact form',
  'Choose the <b>Form</b> tool and drag out its size.',
  'In the <b>Edit Form</b> editor, list the fields you want (one per line) — for example Name, Email, Message.',
  'Set the <b>submit button</b> text.',
  'Choose <b>When submitted</b> — how the form actually sends (see below) — then click <b>OK</b>.')}
{fig(dlg('Edit Form', 'Form'), 'The form editor: list the fields, name the submit button and choose how the form sends.')}
<h3>Making the form actually send</h3>
<p>A published form needs somewhere to deliver its answers. WEBcreator writes the correct code for whichever
of these three you pick in <b>When submitted</b> &mdash; all three work on a plain static host, with no server
to run:</p>
<ul>
<li><b>Netlify Forms</b> <i>(recommended)</i> &mdash; if you publish to Netlify (WEBcreator's built-in
publish target), this is <b>zero setup</b>. WEBcreator adds the <code>data-netlify</code> marker and a hidden
form name; Netlify captures every submission and lists it in your dashboard under <b>Forms</b>. Just give the
form a <b>name</b> so you can tell several forms apart.</li>
<li><b>Formspree</b> &mdash; create a free form at formspree.io, copy its <b>endpoint URL</b>
(<code>https://formspree.io/f/&hellip;</code>) and paste it in. Submissions are emailed to you. Good when you
publish somewhere other than Netlify.</li>
<li><b>Email (mailto)</b> &mdash; opens the <i>visitor's own</i> email program with the answers filled in.
It works anywhere and needs no account, but relies on the visitor having email set up on their device.</li>
</ul>
{note('Each field is published with a proper <code>name</code> so the service knows which answer is which. If you leave the handler unconfigured, the form stays inert (it shows a reminder) rather than silently losing messages.')}"""),
      ("Search box", f"""
<p>A <b>Search Box</b> lets a visitor find anything on your site.</p>
{proc('add a search box',
  'Choose the <b>Search Box</b> tool and drag it out.',
  'In the editor, choose a search <b>provider</b> — Google, Bing or DuckDuckGo — and whether it searches just <b>this site</b> or the whole <b>web</b>.',
  'Set the placeholder and button text, then click <b>OK</b>.')}
{fig(dlg('Search Box'), 'The search-box editor: provider and scope, placeholder and button text.')}
{note('For a site-only search you need to have set your site’s web address in Site-wide SEO, so the search engine knows which site to look within.')}"""),
      ("Share buttons", f"""
<p><b>Share Buttons</b> are a row of one-click links that let a visitor post your page to social media.</p>
{proc('add share buttons',
  'Choose the <b>Share Buttons</b> tool and drag out a row.',
  'In the <b>Share Buttons</b> editor, tick the networks you want — Facebook, X, LinkedIn, WhatsApp, Bluesky, Reddit, Threads or Email.',
  'Choose the button style, then click <b>OK</b>.')}
{fig(dlg('Share Buttons'), 'The share-buttons editor: tick the networks and pick a style.')}"""),
      ("Video and audio", f"""
<p>Embed media that plays right inside the page:</p>
<ul>
<li><b>YouTube</b> and <b>Vimeo</b> — place the object and paste the video's link; the player appears on the page.</li>
<li><b>Audio</b> — place a player and choose a sound file or paste a link; it plays with the browser's own audio controls.</li>
</ul>
{fig(dlg('YouTube Video'), 'The YouTube editor: paste a video link and give it a title.')}"""),
      ("Google Maps", f"""
<p>A <b>Google Map</b> shows an interactive map with a pin on your location &mdash; and it needs no API key.</p>
{proc('add a map',
  'Choose the <b>Google Map</b> tool and drag out its size.',
  'In the <b>Google Map</b> editor, type an address or place name and a label for the pin.',
  'Set the zoom level, then click <b>OK</b>.')}
{fig(dlg('Google Map'), 'The map editor: type an address, label the pin and choose a zoom level.')}"""),
      ("The News Feed", f"""
<p>A <b>News Feed</b> builds itself: it lists the sub-pages of the page it sits on, newest first, each as a
card that links to the full story. Add a news story simply by adding a page under the News page &mdash; the
feed updates automatically.</p>
{proc('add a self-building news feed',
  'Make a <b>News</b> page, and add each story as a page nested under it in the Site panel.',
  'On the News page, choose the <b>News Feed</b> tool and drag out a column.',
  'In the <b>News Feed</b> editor, choose the source page and how many stories to show, and whether to show each story’s date and picture.',
  'Click <b>OK</b>. Every story appears as a card, newest first.')}
{fig(dlg('News Feed'), 'The News Feed editor: source page, maximum stories, and whether to show dates and thumbnails.')}
{tip('<b>Insert ▸ News from a Link…</b> can create a story page straight from a web article’s address — handy for a press or blog section.')}""")]))

    ch.append(("Pages, Masters and Site Structure",
      "<p class='lede'>A website is a set of linked pages that share a look. This chapter covers adding and "
      "arranging pages in the Site panel, the master pages that carry anything meant to repeat, and the "
      "links and navigation that tie the whole site together.</p>", [
      ("The Site panel", f"""
<p>Open the <b>Site</b> panel (the <b>Site Structure</b> button) to see every page as a tree. A page nested
under another is a <b>sub-page</b>; this is how a navigation bar builds its drop-downs and how a News Feed
finds its stories.</p>
{proc('add, remove and arrange pages',
  'Choose <b>Insert ▸ Page…</b> (or the add button on the Site panel) and give the new page a name.',
  'Drag a page in the tree to reorder it, or indent it under another to make it a sub-page.',
  'Double-click a page to open it; delete a selected page from the panel.')}
{fig(dlg('Page Properties'), 'Page Properties: the page’s name and file name, its master page, background, height, and whether it appears in navigation.')}"""),
      ("Page properties", """
<p>Each page has its own <b>Page Properties</b> (double-click it in the Site panel, or <b>Format &#9656; Page
Properties&hellip;</b>): its title, the file name it publishes as, which master page it uses, its background
colour, and whether it should appear in navigation bars. A story page can also carry a <b>date</b>, which the
News Feed shows on its card.</p>"""),
      ("Master pages", f"""
<p>Anything that should appear on <i>every</i> page &mdash; a logo, a navigation bar, a footer &mdash; belongs
on a <b>master page</b>. A master sits <i>behind</i> the ordinary pages that use it, so you build the header
once and it shows on every page.</p>
{proc('put a header on every page',
  'Switch to editing the master page (from the Site panel).',
  'Place the logo, navigation bar and footer on the master.',
  'Return to an ordinary page: those items now show on it, and on every page that uses the master.',
  'To change the header later, edit the master once and every page updates.')}
{tip('Built a page and only then realised several items repeat? <b>Arrange ▸ Move Repeated Objects to Master Page…</b> finds them and lifts them onto the master for you.')}
{fig(dlg('Move Repeated Objects to Master Page'), 'WEBcreator can detect objects that repeat across pages and promote them to the master in one step.')}"""),
      ("Hyperlinks everywhere", f"""
<p>A link can live on text, a button, a shape or a picture, and can point to:</p>
<ul>
<li>another <b>page</b> in your site (so a rename never breaks the link);</li>
<li>a <b>web address</b> on another site;</li>
<li>an <b>anchor</b> further down the same page;</li>
<li>an <b>email</b> address (opens the visitor's mail program);</li>
<li>a <b>file</b> to download.</li>
</ul>
<p>Select the object (or some text), choose <b>Insert &#9656; Hyperlink&hellip;</b>, and pick the target.</p>"""),
      ("An automatic site index", f"""
<p><b>Insert &#9656; Index Page</b> drops in a tidy, grouped list of every page on the site, each a working
link &mdash; a ready-made sitemap for visitors. It keeps itself up to date as you add pages.</p>"""),
      ("Checking your links", f"""
<p>Before you publish, make sure nothing points nowhere.</p>
{proc('check every link on the site',
  'Choose <b>File ▸ Check Links…</b>.',
  'WEBcreator lists every link on every page and flags any that are broken — a deleted page, a mistyped address.',
  'Fix each one at its source, then re-check.')}
{fig(dlg('Check Links'), 'Check Links lists every link on the site and flags the broken ones.')}""")]))

    ch.append(("Search Engines (SEO)",
      "<p class='lede'>A beautiful site is no use if nobody finds it. SEO &mdash; search-engine optimisation "
      "&mdash; is the handful of details that help Google and others understand and list your pages. "
      "WEBcreator makes it a fill-in-the-blanks job, per page and site-wide, and can even do it for you.</p>", [
      ("This page's SEO", f"""
<p>Every page can have its own search-engine details.</p>
{proc('set a page’s SEO',
  'Open the page, then choose <b>SEO ▸ This Page’s SEO…</b>.',
  'Write a concise <b>title</b> (what shows in the search result) and a one-sentence <b>description</b>.',
  'Give it a <b>focus keyword</b> — the phrase you hope people search for.',
  'Optionally set a <b>social preview image</b> (the picture that appears when the page is shared), and click <b>OK</b>.')}
{fig(dlg(*[k for k in D if k.startswith('SEO —')] or ['SEO']), 'The per-page SEO dialog: title, description, focus keyword and social preview, with a live check of each.')}
{note('The dialog scores each field as you type — a title that is the right length, a description that mentions the keyword — so you can see at a glance whether a page is well described.')}"""),
      ("Site-wide SEO", f"""
<p>Some details belong to the whole site, not one page.</p>
{proc('set the site-wide SEO',
  'Choose <b>SEO ▸ Site-wide SEO…</b>.',
  'Set the site’s <b>base web address</b> (needed for sitemaps, social cards and site search).',
  'Set a default <b>social image</b>, a <b>Twitter / X handle</b>, and your <b>organisation</b> details for rich search listings.',
  'Click <b>OK</b>.')}
{fig(dlg('Site-wide SEO'), 'Site-wide SEO: base address, default social image, social handle and organisation details.')}"""),
      ("Auto-generating SEO", f"""
<p>If filling in a title and description for every page sounds like a chore, let the program do it.</p>
{proc('fill in SEO for every page at once',
  'Choose <b>SEO ▸ Auto-generate SEO for all pages…</b>.',
  'WEBcreator reads the text on each page and writes a sensible title, description and keywords from it.',
  'Review the result — it is a starting point you can refine — and publish.')}
{fig(dlg('Auto-generate SEO'), 'Auto-generate SEO fills in titles, descriptions and keywords for every page from its own content.')}"""),
      ("What WEBcreator does automatically", """
<p>Even with no effort from you, WEBcreator writes the technical SEO on publish: a <code>&lt;title&gt;</code>
and meta description for each page, social-sharing (Open Graph and Twitter) tags, a <code>sitemap.xml</code>
that lists your pages for search engines, and a <code>robots.txt</code>. Filling in the SEO dialogs simply
replaces its guesses with your own, better words.</p>""")]))

    parts.append(("Part III", "Building a Website", ch))

    # ============================================================ PART IV (design + templates)
    ch = []
    tpl_cards = IM.get("_tpl_cards", [])
    total = IM.get("_tpl_total", 0)

    tpl_secs = [("Starting from a template", f"""
<p>The fastest way to a finished site is to start from a <b>design template</b> &mdash; a complete, multi-page
site you make your own. In the Startup Assistant's <b>Use Design Template</b> section you pick a design,
choose a colour scheme, untick any pages you do not need, and open it as an ordinary, fully editable site.</p>
{fig(IM.get('startup_templates'), 'Choosing a design template in the Startup Assistant.')}
{proc('build a site from a template',
  'In the Startup Assistant, choose <b>Use Design Template</b>.',
  'Pick a design from the tree — our own Basic Templates, or one of Serif’s catalogue.',
  'Choose a <b>colour scheme</b>, and untick any pages you do not want.',
  'Click <b>Open Template</b>. It opens as a complete site.',
  'Replace the placeholder words and pictures with your own, recolour anything, then publish.')}
{caution('A template is just a normal site once it opens — nothing is locked. Change everything freely.')}""")]

    # group the catalogue cards by category
    bycat = {}
    for (cat, name, meta, img) in tpl_cards:
        bycat.setdefault(cat, []).append((name, meta, img))
    for cat in ("Basic Templates", "Theme Layouts", "Pro Templates", "Sample Sites"):
        if cat not in bycat:
            continue
        cards = []
        for (name, meta, img) in bycat[cat]:
            cap = f"{H.escape(name)}<br><span style='color:#8a97a0'>{H.escape(meta)}</span>"
            cards.append(f'<div class="cat-card">{fig(img, cap)}</div>')
        tpl_secs.append((cat, f'<div class="catgrid">{"".join(cards)}</div>'))

    ch.append(("The Template Library",
      f"<p class='lede'>WEBcreator opens with around {total} ready-made designs: our own Basic Templates, "
      "plus the full Theme Layouts, Pro Templates and Sample Sites catalogue in the tradition of WebPlus. "
      "This chapter is an illustrated sample of each group &mdash; pick the nearest fit and make it "
      "yours.</p>", tpl_secs))

    ch.append(("Designing a Page",
      "<p class='lede'>The tools are only half the job; the other half is using them well. This chapter "
      "distils the handful of principles that separate a page that looks designed from one that looks "
      "thrown together &mdash; the same instincts a Squarespace or a WebPlus user relies on.</p>", [
      ("Start with a grid", """
<p>Before placing anything, decide on your columns and lay guides against them. Lining every object up to the
same few vertical lines is the single biggest thing that makes a layout feel calm and intentional. Two or
three columns suit most pages; a full-width band can break the grid deliberately for a hero or a footer.</p>"""),
      ("Alignment and white space", """
<p>Line things up, and give them room. Nothing should sit a few stray pixels off from its neighbour &mdash;
select and <b>Align</b>. And resist filling every corner: generous space around a headline makes a page look
confident, not empty. Crowding is what reads as amateur.</p>"""),
      ("A limited palette and two fonts", """
<p>Pick two or three colours and stick to them &mdash; the site palette from your template makes this
effortless. Do the same with type: one font for headings, one for body, and vary <i>size</i> and <i>weight</i>
rather than adding more fonts. Restraint looks professional; variety for its own sake looks noisy.</p>"""),
      ("Hierarchy: lead the eye", """
<p>Decide what a visitor should see first, second, third &mdash; and let the sizes say so. A big headline, a
clear subhead, calm body text, one bright button for the thing you want them to do. A landing page has one
loud message; a content page has a heading, then sections. If everything shouts, nothing is heard.</p>"""),
      ("Design for the phone too", """
<p>More than half of most sites' visitors are on a phone. Keep the important things near the top, make tap
targets (buttons, links) big enough for a thumb, and preview on the <b>Phone</b> device before you publish.
A responsive site handles most of this for you, but a quick look on a narrow screen always pays off.</p>""")]))

    parts.append(("Part IV", "Templates &amp; Design", ch))

    # ============================================================ PART V (projects)
    ch = []
    ch.append(("Project: A Small-Business Site",
      "<p class='lede'>This project builds the one-page business site you have seen throughout the guide, "
      "from a blank page to a published layout &mdash; putting the skills of Parts II and III to work in "
      "order.</p>", [
      ("Set up the page and header", f"""
{proc('start the site',
  'In the Startup Assistant choose <b>Start New Site</b>, name it, and create it at 960&nbsp;px wide.',
  'Switch to the master page and draw a white header band across the top; place the logo as artistic text and a <b>navigation bar</b> beside it.')}
{fig(IM.get('build1'), 'Step 1 — the header: a white band, the business name and a navigation bar, all on the master page.')}"""),
      ("Add the hero", f"""
<p>Back on the home page, draw a full-width coloured band below the header, and over it place an
<b>artistic</b> headline, a line of frame text, and a bright <b>button</b> for the main call to action.</p>
{fig(IM.get('build2'), 'Step 2 — a hero band with a headline, a strapline and a call-to-action button.')}"""),
      ("Lay out the content", f"""
{proc('add the content',
  'Add a section heading, then three text frames side by side for the three services.',
  'Draw a wide <b>picture frame</b> below them and drop in a photo.')}
{fig(IM.get('build3'), 'Step 3 — a three-column content section and a picture.')}"""),
      ("Finish and publish", f"""
<p>Add a dark footer band on the master with your contact details. Run a spell check ({K('F7')}) and
<b>File &#9656; Check Links&hellip;</b>, preview on a phone, then <b>Publish</b>.</p>
{fig(IM.get('home'), 'The finished one-page business site, ready to publish.')}
{tip('Save this as your own starting point: next client, open it, change the words, the photo and the palette, and you are most of the way there.')}""")]))

    ch.append(("Project: A Portfolio",
      "<p class='lede'>A portfolio is about the work, not the words. This short project shows the gallery-led "
      "way of thinking, using the kind of layout the Folio template provides.</p>", [
      ("Let the images lead", f"""
<p>Start from the <b>Folio</b> template (or a blank site). The home page is mostly pictures: a grid of
<b>lightbox images</b> or a <b>photo gallery</b>, with just enough text to say who you are.</p>
{proc('build the portfolio home page',
  'Place a short artistic headline and a line or two of intro text.',
  'Lay a grid of <b>lightbox images</b> — each a thumbnail that opens full-size when clicked — or a single <b>photo gallery</b> that cycles through your best work.',
  'Add an <b>About</b> and a <b>Contact</b> page, and a <b>form</b> or an email button so people can reach you.')}
{caution('Resist captions on everything and long explanations. In a portfolio, the work speaks; your words should be few and confident.')}""")]))

    ch.append(("Project: A Community or Club Site",
      "<p class='lede'>A community group's site lives or dies on being kept up to date. This project leans on "
      "the self-building News Feed so that adding news is as easy as adding a page.</p>", [
      ("Structure it for easy updates", f"""
<p>Start from the <b>Meadow</b> template, or build the pages: Home, Our Groups, Events, Get Involved, and a
<b>News</b> page.</p>
{proc('set up a self-updating news section',
  'In the Site panel, add each news item as a page nested under the News page.',
  'On the News page, place a <b>News Feed</b> pointing at itself — every story appears as a card, newest first.',
  'On the home page, place a second, shorter News Feed showing the latest two or three stories.',
  'From now on, posting news means adding a page — the feeds and navigation update themselves.')}
{tip('A <b>Google Map</b> on the Contact page and a <b>form</b> for enquiries are the two things visitors to a club site look for most — add both.')}""")]))

    parts.append(("Part V", "Worked Projects", ch))

    # ============================================================ PART VI (publish)
    ch = []
    ch.append(("Previewing Your Site",
      "<p class='lede'>Before you put a site online, look at it the way a visitor will &mdash; in a real "
      "browser, and at phone, tablet and desktop widths. WEBcreator previews without publishing, so you can "
      "catch a problem before anyone sees it.</p>", [
      ("Preview in a window", f"""
<p>The quickest check is the in-app preview, which shows the real published page and lets you switch screen
sizes.</p>
{proc('preview at different screen sizes',
  'Choose <b>Preview ▸ Preview as Website / Phone / Tablet…</b>.',
  'Click <b>Website</b>, <b>Tablet</b> or <b>Phone</b> to see the page at that width; use <b>Rotate</b> to swap portrait and landscape.',
  'Click any link or button — the preview is live, so navigation works.')}
{fig(IM.get('device'), 'The in-app preview showing the site at phone width — switch between Website, Tablet and Phone, and rotate.')}"""),
      ("Preview in your browser", """
<p>To see a page exactly as the world will, in your own browser: <b>Preview &#9656; Preview Page in
Browser</b> opens the current page, and <b>Preview Site in Browser</b> opens the whole site with working
navigation. This is the final look-over before publishing.</p>""")]))

    ch.append(("Publishing Your Site",
      "<p class='lede'>Publishing turns your design into a folder of real web files, and then puts them "
      "online. WEBcreator writes the files for you and walks you through getting them onto the web &mdash; "
      "including routes that need no technical knowledge at all.</p>", [
      ("What publishing produces", """
<p>When you publish, WEBcreator writes a complete, self-contained website folder: an HTML file for each page,
the images and files it uses, the stylesheet, and the <code>sitemap.xml</code> and <code>robots.txt</code>
search engines expect. These are ordinary web files that any host in the world can serve.</p>"""),
      ("Publishing", f"""
{proc('publish your site',
  'Choose <b>Publish</b> on the menu bar.',
  'Choose whether the site should be <b>Static</b> (fixed width) or <b>Responsive</b> (scales to fit any screen).',
  'Click <b>Publish</b>. WEBcreator writes the whole site to a folder for you — you do not have to pick folders or file names.',
  'It then offers to put the site online (see below).')}
{fig(dlg('Publish your site'), 'Publishing: choose static or responsive, and WEBcreator writes the files automatically.')}"""),
      ("Putting it online", f"""
<p>Once the files are written, WEBcreator helps you get them onto the web. It cannot host the site for you
&mdash; that needs your own account somewhere &mdash; but it explains each option in plain English and opens
the right page for it.</p>
{fig(dlg('Your site is ready — put it online'), 'The “put it online” guide — the no-account drag-and-drop route, and GitHub Pages for those who use it.')}
<ul>
<li><b>Netlify Drop</b> &mdash; the recommended, no-account route. You drag the published folder onto a web
page and your site is live in seconds, with a free address.</li>
<li><b>GitHub Pages</b> &mdash; if you use GitHub, WEBcreator can publish a site straight to a Pages repository
and update it again on each publish.</li>
</ul>
{note('Once a site has been put online by one of these routes, publishing again just updates the live site — WEBcreator remembers where it lives and shows a short “updated” confirmation.')}"""),
      ("Updating a live site", """
<p>A website is never finished. When you change something, choose <b>Publish</b> again: WEBcreator rewrites
the files and, for a site it has already put online, pushes the update straight to the live address and tells
you how many pages changed. For a drag-and-drop host, you drag the refreshed folder across once more.</p>"""),
      ("Importing an existing site", """
<p>If you already have a site elsewhere, you can bring it in and keep working on it here. From the Startup
Assistant's <b>Import&hellip;</b> menu, import a <b>website folder</b>, a single <b>web page from its
URL</b>, or a Serif <b>WebPlus publication</b> (<code>.wpp</code>). WEBcreator turns each into an editable
site; your original is never altered.</p>""")]))

    parts.append(("Part VI", "Preview &amp; Publish", ch))

    # ============================================================ PART VII (reference)
    ch = []
    ch.append(("Appendix A — Menu Reference", "<p class='lede'>Every menu and the commands on it.</p>", [
      ("File", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>New Site</td><td>Start a new site via the Startup Assistant</td></tr>
<tr><td>Open… / Open Recent</td><td>Open a saved <code>.webc</code> site, or a recent one</td></tr>
<tr><td>Open WebPlus Site…</td><td>Import a Serif WebPlus <code>.wpp</code> publication</td></tr>
<tr><td>Import…</td><td>Import a website folder, or a page from its URL</td></tr>
<tr><td>Save / Save As…</td><td>Save the site, or save a copy under a new name</td></tr>
<tr><td>Check Links…</td><td>List every link on the site and flag broken ones</td></tr>
<tr><td>Preview (window / page / site)</td><td>Preview in the app, or in your browser</td></tr>
<tr><td>Publish</td><td>Write the site files and help you put it online</td></tr>
<tr><td>Quit</td><td>Close the program (prompts to save)</td></tr></table>"""),
      ("Edit", f"""<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Undo / Redo</td><td>Step back and forward through your changes</td></tr>
<tr><td>Cut / Copy / Paste</td><td>Move or copy the selection via the clipboard</td></tr>
<tr><td>Duplicate ({K('Ctrl')}+{K('D')})</td><td>Drop a copy of the selection, slightly offset</td></tr>
<tr><td>Delete</td><td>Remove the selection</td></tr>
<tr><td>Select All ({K('Ctrl')}+{K('A')})</td><td>Select every object on the page</td></tr></table>"""),
      ("View", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Rulers / Grid / Snap / Crosshair</td><td>Toggle the on-screen aids</td></tr>
<tr><td>Zoom In / Out</td><td>Change the zoom level</td></tr>
<tr><td>Actual Size / Fit Page Width</td><td>Jump to 100%, or frame the full width</td></tr></table>"""),
      ("Insert", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Page… / Index Page</td><td>Add a page; add an automatic site-index page</td></tr>
<tr><td>News from a Link…</td><td>Make a story page from a web article's address</td></tr>
<tr><td>Artistic Text / Frame Text</td><td>A scalable headline; a wrapping body-text frame</td></tr>
<tr><td>Table / Picture / Lightbox / Gallery</td><td>A data grid; a picture; a click-to-enlarge image; a slideshow</td></tr>
<tr><td>Rectangle / Ellipse / Line / QuickShapes ▸</td><td>Shapes and the preset-shape gallery</td></tr>
<tr><td>Navigation Bar / Button / Form / Search Box</td><td>The core web objects</td></tr>
<tr><td>Share Buttons / HTML Code / Custom CSS…</td><td>Social sharing; a raw HTML block; site-wide CSS</td></tr>
<tr><td>YouTube / Vimeo / Audio / Google Map</td><td>Embedded media and a map</td></tr>
<tr><td>News Feed</td><td>A self-building list of sub-pages as cards</td></tr>
<tr><td>Embed… / Contact details ▸</td><td>Third-party blocks; a field from Site Properties</td></tr>
<tr><td>Import Text… / Hyperlink…</td><td>Pour in a text file; link the selection</td></tr></table>"""),
      ("Format", f"""<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Bold / Italic / Underline</td><td>Character styling for selected text</td></tr>
<tr><td>Align Left / Centre / Right / Justify</td><td>Paragraph alignment</td></tr>
<tr><td>Lists / Bullets ▸</td><td>Bulleted or numbered list styles</td></tr>
<tr><td>Check Spelling… ({K('F7')})</td><td>Spell-check every page</td></tr>
<tr><td>Page Properties…</td><td>Name, file, master, background and navigation for this page</td></tr></table>"""),
      ("Arrange", f"""<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Bring to Front / Forward One</td><td>Move the selection up the stack</td></tr>
<tr><td>Send to Back / Back One</td><td>Move the selection down the stack</td></tr>
<tr><td>Align ▸</td><td>Line up selected objects, or centre on the page</td></tr>
<tr><td>Lock / Unlock ({K('Ctrl')}+{K('L')})</td><td>Pin the selection, or release it</td></tr>
<tr><td>Move Repeated Objects to Master Page…</td><td>Promote shared items onto the master</td></tr></table>"""),
      ("Preview, Publish and SEO", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>Preview ▸ Website / Phone / Tablet…</td><td>In-app preview at each screen size</td></tr>
<tr><td>Preview ▸ Page / Site in Browser</td><td>Open in your own browser</td></tr>
<tr><td>Publish</td><td>Write the site files and put it online</td></tr>
<tr><td>SEO ▸ This Page's SEO…</td><td>Title, description, keyword and social image for this page</td></tr>
<tr><td>SEO ▸ Site-wide SEO…</td><td>Base address, default social image, organisation details</td></tr>
<tr><td>SEO ▸ Auto-generate SEO…</td><td>Fill in SEO for every page from its content</td></tr></table>"""),
      ("Help", """<table class="ref"><tr><th>Command</th><th>What it does</th></tr>
<tr><td>User Guide / Quick Start Guide</td><td>This book, and the short guide</td></tr>
<tr><td>Check for Updates… / Settings…</td><td>Update the app; change preferences</td></tr>
<tr><td>About</td><td>Version and credits</td></tr>
<tr><td>Buy Me a Coffee ☕</td><td>Support the maker</td></tr></table>""")]))

    ch.append(("Appendix B — Keyboard Shortcuts", "<p class='lede'>The keys worth learning.</p>", [
      ("Everyday", f"""<table class="ref">
<tr><th>Action</th><th>Shortcut</th></tr>
<tr><td>Save</td><td>{K('Ctrl')}+{K('S')}</td></tr>
<tr><td>Undo / Redo</td><td>{K('Ctrl')}+{K('Z')} · {K('Ctrl')}+{K('Y')}</td></tr>
<tr><td>Cut / Copy / Paste</td><td>{K('Ctrl')}+{K('X')} · {K('Ctrl')}+{K('C')} · {K('Ctrl')}+{K('V')}</td></tr>
<tr><td>Duplicate</td><td>{K('Ctrl')}+{K('D')}</td></tr>
<tr><td>Select all / Deselect</td><td>{K('Ctrl')}+{K('A')} · {K('Esc')}</td></tr>
<tr><td>Delete</td><td>{K('Delete')}</td></tr></table>"""),
      ("Text, objects and view", f"""<table class="ref">
<tr><th>Action</th><th>Shortcut</th></tr>
<tr><td>Bold / Italic / Underline</td><td>{K('Ctrl')}+{K('B')} · {K('Ctrl')}+{K('I')} · {K('Ctrl')}+{K('U')}</td></tr>
<tr><td>Check spelling</td><td>{K('F7')}</td></tr>
<tr><td>Lock / Unlock</td><td>{K('Ctrl')}+{K('L')}</td></tr>
<tr><td>Nudge selection</td><td>{K('↑')} {K('↓')} {K('←')} {K('→')}</td></tr>
<tr><td>Constrain a shape to square / circle</td><td>hold {K('Shift')} while drawing</td></tr>
<tr><td>Zoom with the wheel</td><td>{K('Ctrl')} + scroll</td></tr></table>""")]))

    ch.append(("Appendix C — Tools and Objects", "<p class='lede'>A reference to the tool palette and the object types.</p>", [
      ("The tool palette", f"""
{fig(IM.get('toolrail'), 'The tool palette.', 'tall')}
<table class="ref"><tr><th>Tool</th><th>Use</th></tr>
<tr><td>Pointer</td><td>Select, move and resize objects</td></tr>
<tr><td>Hand / Zoom</td><td>Scroll the page; change the zoom</td></tr>
<tr><td>Artistic Text</td><td>A single scalable line — titles and mastheads</td></tr>
<tr><td>Creative Frame Text</td><td>A box of body text that wraps</td></tr>
<tr><td>Table</td><td>A grid of cells</td></tr>
<tr><td>Picture / Lightbox / Photo Gallery</td><td>A photo; a click-to-enlarge image; a slideshow</td></tr>
<tr><td>Rectangle / Ellipse / Line</td><td>Basic shapes and rules</td></tr>
<tr><td>Navigation Bar</td><td>An auto-updating menu of your pages</td></tr>
<tr><td>Button</td><td>A styled, linked call to action</td></tr>
<tr><td>Form / Search Box</td><td>An enquiry form; a site search</td></tr>
<tr><td>Share Buttons</td><td>One-click social sharing</td></tr>
<tr><td>HTML Code</td><td>A raw HTML fragment</td></tr>
<tr><td>YouTube / Vimeo / Audio</td><td>Embedded video and sound</td></tr>
<tr><td>Google Map</td><td>An interactive map with a pin</td></tr>
<tr><td>News Feed</td><td>A self-building list of story cards</td></tr></table>"""),
      ("The object types", """
<table class="ref"><tr><th>Object</th><th>What it is</th></tr>
<tr><td>Text frame</td><td>Wrapping body text</td></tr>
<tr><td>Artistic text</td><td>A single scalable headline line</td></tr>
<tr><td>Picture / Lightbox</td><td>An image; an image that enlarges on click</td></tr>
<tr><td>QuickShape / Line</td><td>A preset shape; a straight rule</td></tr>
<tr><td>Navigation bar</td><td>Auto menu of pages (pills / underline / plain)</td></tr>
<tr><td>Button</td><td>Linked call to action</td></tr>
<tr><td>Table</td><td>A grid of data cells</td></tr>
<tr><td>Form / Search box</td><td>An enquiry form; a site search field</td></tr>
<tr><td>Share buttons</td><td>Social-sharing links</td></tr>
<tr><td>Photo gallery</td><td>A fading slideshow of pictures</td></tr>
<tr><td>YouTube / Vimeo / Audio</td><td>Embedded media players</td></tr>
<tr><td>Google Map</td><td>An embedded, pinned map</td></tr>
<tr><td>News feed</td><td>Cards built from sub-pages</td></tr>
<tr><td>HTML fragment</td><td>Verbatim custom markup</td></tr></table>""")]))

    ch.append(("Appendix D — Glossary", "<p class='lede'>The web-design words used in this guide.</p>", [
      ("A–Z", """<dl class="gloss">
<dt>Anchor</dt><dd>A named spot on a page that a link can jump straight to.</dd>
<dt>Artistic text</dt><dd>A single line of display type you scale freely; publishes as real web text.</dd>
<dt>Breadcrumb</dt><dd>A trail of links showing where a page sits in the site.</dd>
<dt>Frame</dt><dd>A box that holds text or a picture; you size the box and its contents independently.</dd>
<dt>Gradient</dt><dd>A smooth fade from one colour to another across a shape.</dd>
<dt>Hyperlink</dt><dd>A clickable link to a page, address, email or file.</dd>
<dt>Lightbox</dt><dd>A thumbnail that opens the full picture in an overlay when clicked.</dd>
<dt>Master page</dt><dd>A page behind the others whose content repeats on every page that uses it.</dd>
<dt>Navigation bar</dt><dd>A menu of your pages that updates itself as pages change.</dd>
<dt>News Feed</dt><dd>A block that builds a list of story cards from a page's sub-pages.</dd>
<dt>Object</dt><dd>Anything you place on a page — text, picture, shape, button, form…</dd>
<dt>Open Graph</dt><dd>The tags that control how a page looks when shared on social media.</dd>
<dt>QuickShape</dt><dd>A ready-made shape outline (star, arrow, speech bubble…).</dd>
<dt>Responsive</dt><dd>A layout that scales to fit any screen, from phone to desktop.</dd>
<dt>SEO</dt><dd>Search-engine optimisation — the details that help a site be found.</dd>
<dt>Sitemap</dt><dd>A list of a site's pages, for search engines (and sometimes visitors).</dd>
<dt>Sub-page</dt><dd>A page nested under another in the Site panel.</dd>
<dt>Swatch</dt><dd>A saved colour kept one click away.</dd>
</dl>""")]))

    ch.append(("Appendix E — Troubleshooting", "<p class='lede'>Quick answers to common snags.</p>", [
      ("Common questions", """<dl class="gloss">
<dt>My navigation bar is empty or missing a page.</dt><dd>A page only appears in navigation if its Page Properties has it ticked to show, so check there; and the nav lists pages at its own level — sub-pages appear as drop-downs under their parent.</dd>
<dt>My contact form does not send anything.</dt><dd>A form needs a server-side handler to deliver its messages. Publish the site, then point the form at a free form service (the published HTML is ready for one); a purely local preview cannot send mail.</dd>
<dt>My site-search finds nothing.</dt><dd>Site-only search needs your site's web address set in SEO ▸ Site-wide SEO, so the search engine knows which site to look within. Set it, then re-publish.</dd>
<dt>A picture looks fuzzy on the live site.</dt><dd>The image is smaller than the frame you stretched it into. Use a larger original, or make the frame smaller.</dd>
<dt>The page looks fine on my screen but cramped on a phone.</dt><dd>Publish as Responsive, and preview on the Phone device. For a fixed-width site, the phone shows the full width and the visitor scrolls.</dd>
<dt>I can't select an object.</dt><dd>It may be locked (Arrange ▸ Lock / Unlock), on a master page (edit the master), or behind another object (bring it forward, or use the Layers panel).</dd>
<dt>My YouTube video shows a blank box in the editor.</dt><dd>The editor fetches the poster image in the background; it appears once fetched, and the real player always shows on the published page.</dd>
<dt>The app won't start on Linux.</dt><dd>Run the installer again from a terminal; it sets up its own private Python environment automatically if the system one is missing.</dd>
</dl>""")]))

    parts.append(("Part VII", "Reference", ch))
    return parts


# ------------------------------------------------------------------- quickstart
def quickstart_sections(IM):
    def f(k, cap):
        return fig(IM.get(k), cap)
    S = []
    S.append(("Welcome to WEBcreator", f"""
<p class="lede">WEBcreator is a <b>website design</b> program: you lay a page out by placing text, pictures,
shapes, navigation and media exactly where you want them, preview it in your browser, and publish it as a
real website. It works the way Serif's <b>WebPlus</b> did &mdash; the same menus, in the same places.</p>
<p>This Quick Start takes you from a blank page to a published site in a dozen short steps. For the complete
reference &mdash; every feature, worked projects and a full menu guide &mdash; open the <b>User Guide</b>
(Help &#9656; User Guide).</p>
{f('home', 'A finished one-page business site, built entirely in WEBcreator.')}"""))
    S.append(("Start a site", f"""
<p>When WEBcreator opens it shows the <b>Startup Assistant</b>. Choose <b>Use Design Template</b> to build on
a ready-made design, or <b>Start New Site</b> for a blank page &mdash; name it, pick a width, and decide
whether it should be <b>responsive</b> (scale to fit phones and tablets).</p>
{f('startup_templates', 'The Startup Assistant: start from a design, a blank page, or recent work.')}"""))
    S.append(("The workspace", f"""
<p>Your page sits in the middle, the <b>tools</b> down the left, the <b>menus and toolbars</b> across the top,
and the <b>panels</b> on the right.</p>
{f('workspace', 'Tools on the left, your page in the middle, panels on the right.')}"""))
    S.append(("Pages and masters", """
<p>Open the <b>Site</b> panel to add, rename and reorder pages; nest one under another to make a
<b>sub-page</b>. Things that belong on every page &mdash; a logo, the navigation, a footer &mdash; go on a
<b>master page</b>, built once and shown everywhere.</p>"""))
    S.append(("Add text", f"""
<p>Drag out a <b>Creative Frame Text</b> box and type; the text wraps inside it. For a headline or masthead,
use <b>Artistic Text</b> &mdash; a single line you scale freely. It all publishes as real, searchable web
text.</p>
{f('textpage', 'Frame text with a drop cap and a list, beside an artistic headline.')}"""))
    S.append(("Add pictures", """
<p>Draw a <b>picture frame</b> with the Picture tool and choose a photo. Make it a <b>lightbox</b> that
enlarges on click, or string several into a <b>photo gallery</b>. For real edits, <b>Edit in PAINTcanvas</b>
sends it across and brings the result back.</p>"""))
    S.append(("Shapes and QuickShapes", f"""
<p>Draw rectangles, ellipses and <b>QuickShapes</b> &mdash; stars, arrows, speech bubbles and more. Each has
a fill and an outline, and can carry a drop shadow or glow. A full-width filled rectangle makes a coloured
header or hero band.</p>
{f('shapes', 'Basic shapes, a line and a row of QuickShapes.')}"""))
    S.append(("Add the web objects", f"""
<p>This is what makes it a website: a <b>Navigation Bar</b> that lists your pages automatically, <b>Buttons</b>
that link somewhere, a <b>Form</b> and <b>Search Box</b>, <b>Share Buttons</b>, video and <b>Google Maps</b>,
and a self-building <b>News Feed</b>.</p>
{f('webobj', 'The web objects — navigation, buttons, share buttons, search, a form, a table and a news feed.')}"""))
    S.append(("Arrange and align", """
<p>With the <b>Pointer</b>, click to select, drag to move, pull the handles to resize. <b>Arrange &#9656;
Align</b> lines objects up; <b>Transform</b> sets exact positions; <b>Lock</b> stops accidental nudges.</p>"""))
    S.append(("Colour and the palette", f"""
<p>The <b>Colour</b> panel sets a fill, outline or text colour; <b>Swatches</b> keeps your palette handy. Add
a <b>gradient</b> fill, or make something <b>transparent</b> so what's behind shows through. A design
template fills the palette with a coordinated scheme for you.</p>
{f('colourpage', 'Flat colour, gradients, and a transparent panel over a photo.')}"""))
    S.append(("Help people find it (SEO)", """
<p>Give each page a clear <b>title</b> and <b>description</b> under <b>SEO &#9656; This Page's SEO…</b>, set
your site's web address in <b>Site-wide SEO</b>, or let <b>Auto-generate SEO</b> fill it all in from your
content. WEBcreator writes the sitemap and sharing tags for you.</p>"""))
    S.append(("Preview, then publish", f"""
<p>Check it on a phone with <b>Preview &#9656; Website / Phone / Tablet</b>, run a <b>spell check</b>
({K('F7')}) and <b>Check Links</b>. Then click <b>Publish</b>: WEBcreator writes the whole site and walks you
through putting it online &mdash; the drag-and-drop route needs no account at all.</p>
{f('device', 'Preview your site at phone, tablet and desktop widths before publishing.')}"""))
    S.append(("Where to go next", """
<p>That is the whole round trip: new site → pages → text, pictures, shapes and web objects → arrange → SEO →
publish. The <b>User Guide</b> covers every feature in depth, with worked projects and a full reference. And
the other <i>just a…</i> apps work the same way &mdash; once you know one, you know them all.</p>"""))
    return S


# ------------------------------------------------------------------- CSS
CSS = """
:root{ --ink:#232b31; --mute:#64737c; --line:#d7dee3; --accent:#2a7d6b; --accent2:#1d5c50;
  --paper:#ffffff; --band:#eef3f2; --warn:#b5651d; }
*{box-sizing:border-box} body{margin:0;background:#e8edf0;color:var(--ink);
  font:16px/1.62 "Noto Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}
.page{max-width:840px;margin:28px auto;background:var(--paper);padding:54px 62px;
  box-shadow:0 2px 20px -8px rgba(20,40,50,.35);border-radius:4px;}
h1{font-size:2.3rem;margin:.1em 0 .1em;letter-spacing:-.01em}
.lede{font-size:1.12rem;color:#374249}
p{max-width:68ch} ul,ol,dl{max-width:68ch} li{margin:.22em 0}
code{background:var(--band);padding:1px 5px;border-radius:4px;font-size:.92em}
kbd{display:inline-block;background:#f6f8f9;border:1px solid #c4ced4;border-bottom-width:2px;
  border-radius:5px;padding:0 6px;font:600 .82em/1.5 "Noto Sans",sans-serif;color:#2b3a42;white-space:nowrap}
figure.f{margin:1.3em auto;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--band);max-width:470px}
figure.f img{width:100%;display:block}
/* the tool rail is a tall, thin strip: cap it by HEIGHT so it can't balloon down the page */
figure.f.tall{max-width:none;width:max-content;margin:1.2em auto}
figure.f.tall img{width:auto;max-height:430px}
figcaption{font-size:.85rem;color:var(--mute);padding:8px 12px;background:var(--band);border-top:1px solid var(--line)}
.fig-missing{color:#b24;font-size:.85rem;border:1px dashed #c99;padding:8px;border-radius:6px;margin:1em 0}
/* procedures */
.proc{background:#f7fbfa;border:1px solid #cfe2dd;border-left:4px solid var(--accent);
  border-radius:8px;padding:12px 18px 14px;margin:1.3em 0}
.proc-h{font-weight:700;color:var(--accent2);margin:.1em 0 .5em;max-width:none}
ol.steps{margin:.3em 0;padding-left:1.3em} ol.steps li{margin:.3em 0}
/* callouts */
.cal{border-radius:8px;padding:10px 14px 10px 14px;margin:1.1em 0;font-size:.97rem;max-width:68ch;position:relative}
.cal-k{display:inline-block;font-weight:700;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;
  margin-right:.6em;padding:1px 7px;border-radius:999px;vertical-align:1px}
.cal.note{background:#eef3f6;border:1px solid #cdd9e0}.cal.note .cal-k{background:#3a5566;color:#fff}
.cal.tip{background:#eef7f1;border:1px solid #c7e3d1}.cal.tip .cal-k{background:#2a7d4f;color:#fff}
.cal.caution{background:#fbf2e8;border:1px solid #e8d2b4}.cal.caution .cal-k{background:var(--warn);color:#fff}
/* reference tables */
table.ref{border-collapse:collapse;width:100%;max-width:68ch;margin:1em 0;font-size:.95rem}
table.ref th,table.ref td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
table.ref th{background:var(--band)}
dl.gloss dt{font-weight:700;margin-top:.7em;color:#17323a} dl.gloss dd{margin:.1em 0 .1em 1.3em;color:#374249}
/* catalogue grids */
.catgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:1em 0}
.cat-card figure.f{margin:0;max-width:none}
.cat-card figure.f img{background:#fff;object-fit:contain;max-height:280px}
/* back-of-book index */
.index{columns:2;gap:30px}
.idx-let{font-weight:800;color:var(--accent);font-size:1.1rem;margin:.7em 0 .15em;break-after:avoid}
ul.idx{list-style:none;padding:0;margin:0 0 .5em}
ul.idx li{margin:.12em 0;font-size:.92rem;break-inside:avoid;padding-left:1.1em;text-indent:-1.1em}
ul.idx a{color:var(--accent);text-decoration:none}
"""

COVER_CSS = """
.cover{min-height:980px;display:flex;align-items:center;justify-content:center;text-align:center;break-after:page;page-break-after:always}
.cv-inner{max-width:640px;padding:0 40px}
.cv-banner{width:100%;max-width:560px;margin:0 auto 12px;display:block;border-radius:8px}
.cv-kind{font-size:2.5rem;font-weight:800;color:var(--accent);letter-spacing:.01em;margin-top:.3em}
.cv-rule{height:3px;width:120px;background:var(--accent);margin:18px auto}
.cv-sub{color:var(--mute);font-size:1.08rem;max-width:48ch;margin:0 auto}
.cv-date{color:var(--mute);margin-top:2.4em;font-size:.95rem}
/* part divider */
.part{min-height:720px;display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;break-before:page;page-break-before:always;break-after:page;page-break-after:always}
.part .pn{color:var(--accent);font-size:1rem;letter-spacing:.3em;text-transform:uppercase;font-weight:700}
.part .pt{font-size:2.6rem;font-weight:800;margin:.25em 0;color:#17323a;max-width:none}
.part .prule{height:3px;width:90px;background:var(--accent);margin:14px auto}
"""

MANUAL_CSS = """
.contents{margin:1.3em 0 0}
.booktoc{list-style:none;padding:0;margin:0}
.booktoc .part-h{font-size:.8rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);
  font-weight:800;margin:1.1em 0 .3em;border-bottom:2px solid var(--line);padding-bottom:3px}
.booktoc .ch{margin:.35em 0;font-weight:600}.booktoc .ch>a{color:var(--ink);text-decoration:none}
.booktoc .n{color:var(--accent);margin-right:.5em;font-variant-numeric:tabular-nums}
.booktoc ul{list-style:none;padding:0 0 0 1.7em;margin:.15em 0 .4em;font-weight:400;font-size:.93rem;columns:2;gap:24px}
.booktoc ul li{margin:.08em 0;break-inside:avoid}.booktoc a:hover{color:var(--accent)}
.chapter{break-before:page;page-break-before:always;margin-top:1em}
.chrule{border-top:4px solid var(--accent);margin-bottom:.4em}
.chrule .cn{display:block;color:var(--accent);font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;margin-top:.5em}
.chrule h2{border:0;margin:.05em 0 .35em;padding:0;font-size:2rem;max-width:none}
h3{font-size:1.2rem;margin:1.7em 0 .4em;color:#17323a;max-width:none}
header.mast{background:var(--accent);color:#fff;border-radius:4px;padding:28px 34px;margin:0 0 .4em}
header.mast h1{margin:0;color:#fff}header.mast p{margin:.3em 0 0;color:#d7ece7;max-width:none}
@media print{ body{background:#fff} .page{box-shadow:none;margin:0;max-width:none;padding:38px 46px}
  h3{break-after:avoid} figure.f{break-inside:avoid} .proc{break-inside:avoid} .cal{break-inside:avoid}
  table.ref{break-inside:auto} .cat-card{break-inside:avoid} }
"""

QS_CSS = """
.toc{columns:2;gap:28px;margin:1em 0 0;padding:0;list-style:none}
.toc li{margin:.25em 0;break-inside:avoid}.toc a{color:var(--ink);text-decoration:none}
.toc a:hover{color:var(--accent)}.toc .n{color:var(--accent);font-weight:700;margin-right:.5em}
h2{font-size:1.5rem;margin:2.2em 0 .5em;padding-top:.5em;border-top:3px solid var(--accent);max-width:none}
h2 .n{color:var(--accent);margin-right:.5em;font-weight:700}
header.mast{background:var(--accent);color:#fff;border-radius:4px;padding:28px 34px}
header.mast h1{margin:0;color:#fff}header.mast p{margin:.3em 0 0;color:#d7ece7;max-width:none}
@media print{ body{background:#fff} .page{box-shadow:none;margin:0;max-width:none} h2{break-after:avoid} figure.f{break-inside:avoid} }
"""


def _banner_uri():
    p = OUT / "banner.png"
    if Image and p.exists():
        return datauri(Image.open(str(p)).convert("RGB"), 900)
    return ""


def cover(kind):
    uri = _banner_uri()
    top = f'<img class="cv-banner" src="{uri}" alt="">' if uri else '<div style="font-size:3rem;font-weight:800;color:var(--accent)">WEBcreator</div>'
    return (f'<section class="cover"><div class="cv-inner">{top}'
            f'<div class="cv-kind">{kind}</div><div class="cv-rule"></div>'
            f'<div class="cv-sub">just a&hellip; WEBcreator &mdash; a website designer in the spirit of Serif WebPlus</div>'
            f'<div class="cv-date">{date.today().strftime("%B %Y")}</div></div></section>')


# ------------------------------------------------------------------- assembly
def build_quickstart(IM):
    S = quickstart_sections(IM)
    toc = "".join(f'<li><span class="n">{i+1}</span><a href="#s{i+1}">{H.escape(t)}</a></li>'
                  for i, (t, _) in enumerate(S))
    body = "".join(f'<h2 id="s{i+1}"><span class="n">{i+1}</span>{H.escape(t)}</h2>\n{b}'
                   for i, (t, b) in enumerate(S))
    doc = f"""<!DOCTYPE html><html lang="en-GB"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>just a… WEBcreator — Quick Start Guide</title>
<style>{CSS}{COVER_CSS}{QS_CSS}</style>
<div class="page">
{cover('Quick Start Guide')}
<header class="mast"><h1>WEBcreator — Quick Start</h1>
<p>From a blank page to a published website — in a dozen steps.</p></header>
<h2 style="border:0">Contents</h2><ol class="toc">{toc}</ol>
{body}
<footer style="color:var(--mute);font-size:.85rem;margin-top:3em;border-top:1px solid var(--line);padding-top:1em">
just a… WEBcreator Quick Start · generated {date.today().isoformat()} · every picture is produced by the app itself.
See <b>Help ▸ User Guide</b> for the full manual.</footer>
</div></html>"""
    (OUT / "quickstart.html").write_text(doc, encoding="utf-8")
    print("wrote quickstart.html:", len(doc) // 1024, "KiB,", len(S), "sections")


def build_index(numbered):
    """A back-of-book index: every section heading plus a curated term list, each
    linked to the chapter/section that covers it, grouped A–Z."""
    import re as _re
    from collections import defaultdict
    entries = {}
    secs = []
    for _pt, _pb, pc in numbered:
        for (n, title, intro, secitems) in pc:
            for si, (h, b) in enumerate(secitems, 1):
                anchor = f"c{n}s{si}"
                plain = _re.sub(r"<[^>]+>", " ", h + " " + b)
                secs.append((n, anchor, plain))
                term = _re.sub(r"\s+", " ", h).strip().rstrip("…").strip()
                if term and len(term) < 46:
                    entries.setdefault(term, set()).add((n, anchor))
    TERMS = ["navigation bar", "button", "form", "search box", "share buttons", "photo gallery",
             "lightbox", "YouTube", "Vimeo", "audio", "Google Map", "news feed", "HTML fragment",
             "custom CSS", "master page", "sub-page", "page properties", "hyperlink", "anchor",
             "site index", "sitemap", "SEO", "responsive", "device preview", "publish", "Netlify",
             "GitHub Pages", "spell check", "check links", "gradient", "transparency", "swatch",
             "colour scheme", "QuickShape", "drop shadow", "outer glow", "crop", "picture frame",
             "artistic text", "text frame", "table", "template", "Startup Assistant", "import"]
    for t in TERMS:
        for (n, anchor, plain) in secs:
            if _re.search(r"\b" + _re.escape(t) + r"\b", plain, _re.I):
                entries.setdefault(t[0].upper() + t[1:], set()).add((n, anchor))
                break
    groups = defaultdict(list)
    for term in sorted(entries, key=lambda s: s.lower()):
        refs = sorted(entries[term])
        links = ", ".join(f'<a href="#{a}">Ch&nbsp;{n}</a>' for (n, a) in refs)
        letter = term[0].upper() if term[:1].isalpha() else "#"
        groups[letter].append(f"<li>{H.escape(term)} &nbsp;{links}</li>")
    out = ['<div class="index">']
    for letter in sorted(groups):
        out.append(f'<div class="idx-let">{letter}</div><ul class="idx">{"".join(groups[letter])}</ul>')
    out.append("</div>")
    return "".join(out)


def build_manual(IM):
    parts = manual_parts(IM)
    chno = 0
    numbered = []
    for ptitle, pblurb, chapters in parts:
        pc = []
        for (title, intro, secs) in chapters:
            chno += 1
            pc.append((chno, title, intro, secs))
        numbered.append((ptitle, pblurb, pc))

    toc = []
    for ptitle, pblurb, pc in numbered:
        toc.append(f'<li class="part-h">{H.escape(ptitle)} · {pblurb}</li>')
        for (n, title, intro, secs) in pc:
            subs = "".join(f'<li><a href="#c{n}s{si}">{H.escape(h)}</a></li>'
                           for si, (h, _b) in enumerate(secs, 1))
            toc.append(f'<li class="ch"><span class="n">{n}</span>'
                       f'<a href="#c{n}">{H.escape(title)}</a><ul>{subs}</ul></li>')

    body = []
    for ptitle, pblurb, pc in numbered:
        body.append(f'<section class="part"><div class="pn">{H.escape(ptitle)}</div>'
                    f'<div class="pt">{pblurb}</div><div class="prule"></div></section>')
        for (n, title, intro, secs) in pc:
            body.append(f'<section class="chapter"><div class="chrule"><span class="cn">Chapter {n}</span>'
                        f'<h2 id="c{n}">{H.escape(title)}</h2></div>\n{intro}')
            for si, (h, b) in enumerate(secs, 1):
                body.append(f'<h3 id="c{n}s{si}">{H.escape(h)}</h3>\n{b}')
            body.append("</section>")

    toc.append('<li class="part-h">Index</li>')
    body.append('<section class="part"><div class="pn">Reference</div><div class="pt">Index</div><div class="prule"></div></section>')
    body.append(f'<section class="chapter"><div class="chrule"><span class="cn">Reference</span>'
                f'<h2 id="bookindex">Index</h2></div>{build_index(numbered)}</section>')

    doc = f"""<!DOCTYPE html><html lang="en-GB"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>just a… WEBcreator — User Guide</title>
<style>{CSS}{COVER_CSS}{MANUAL_CSS}</style>
<div class="page">
{cover('User Guide')}
<header class="mast"><h1>WEBcreator</h1><p>User Guide — the complete reference for designing,
building and publishing a website.</p></header>
<nav class="contents"><h2 style="border:0;font-size:1.6rem">Contents</h2><ol class="booktoc">{''.join(toc)}</ol></nav>
{''.join(body)}
<footer style="color:var(--mute);font-size:.85rem;margin-top:3em;border-top:1px solid var(--line);padding-top:1em">
just a… WEBcreator User Guide · generated {date.today().isoformat()} · every picture is produced by the app itself ·
in the spirit of Serif WebPlus.</footer>
</div></html>"""
    (OUT / "manual.html").write_text(doc, encoding="utf-8")
    nch = sum(len(pc) for _, _, pc in numbered)
    print("wrote manual.html:", len(doc) // 1024, "KiB,", len(numbered), "parts,", nch, "chapters")


def render_pdf(html_path, pdf_path):
    from PySide6.QtCore import QUrl, QEventLoop, QMarginsF, QTimer
    from PySide6.QtGui import QPageLayout, QPageSize
    from PySide6.QtWebEngineCore import QWebEnginePage
    pg = QWebEnginePage(); loop = QEventLoop(); res = {}

    def finished(_ok):
        lay = QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(12, 12, 12, 12))
        pg.printToPdf(str(pdf_path), lay)

    def pdfdone(_path, good):
        res['ok'] = good; loop.quit()

    pg.loadFinished.connect(finished); pg.pdfPrintingFinished.connect(pdfdone)
    pg.load(QUrl.fromLocalFile(os.path.abspath(str(html_path))))
    QTimer.singleShot(120000, loop.quit); loop.exec()
    sz = os.path.getsize(pdf_path) // 1024 if os.path.exists(pdf_path) else 0
    print(f"wrote {os.path.basename(str(pdf_path))}: {sz} KiB", "OK" if res.get('ok') else "FAILED")
    return res.get('ok', False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args(_REAL_ARGS)
    if Image is None:
        sys.exit("Pillow required")
    IM = capture(full=not args.quick)
    build_quickstart(IM)
    if not args.no_pdf:
        render_pdf(OUT / "quickstart.html", OUT / "quickstart.pdf")
    if not args.quick:
        build_manual(IM)
        if not args.no_pdf:
            render_pdf(OUT / "manual.html", OUT / "manual.pdf")
    try:
        _TMP.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    main()
