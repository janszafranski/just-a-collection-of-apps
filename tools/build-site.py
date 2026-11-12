#!/usr/bin/env python3
"""Build docs/ — the site at janszafranski.github.io/just-a-collection-of-apps.

Everything on the site is generated from the apps themselves. The template
pictures are not screenshots and not anybody else's artwork: each one is the
home page *just a... WEBcreator* actually builds when you pick that template,
rendered by the app's own painting code through PySide6.

    python3 tools/build-site.py            # docs/
    python3 tools/build-site.py --fast     # skip the 92 renders

Needs pyside6. Runs headless.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import os
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "apps" / "webcreator" / "webcreator.py"
DOCS = ROOT / "docs"
SITE = "just a... COLLECTION of apps"

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def load_app():
    spec = importlib.util.spec_from_file_location("webcreator", APP)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["webcreator"] = mod
    spec.loader.exec_module(mod)
    return mod


CSS = """
:root {
  color-scheme: light dark;
  --bg: #ffffff; --fg: #1b1d1f; --mute: #5c6368;
  --line: #e2e5e8; --card: #f7f8f9; --accent: #1d6f63;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #15181a; --fg: #e8eaec; --mute: #9aa3a9;
          --line: #2a2f33; --card: #1c2023; --accent: #6fc3b4; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.6
       system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", sans-serif; }
.wrap { max-width: 1120px; margin: 0 auto; padding: 0 24px 72px; }
header.top { border-bottom: 1px solid var(--line); margin-bottom: 40px; }
header.top .wrap { padding-top: 28px; padding-bottom: 28px; }
h1 { font-size: 2.1rem; margin: 0 0 .2em; letter-spacing: -.01em; }
h2 { font-size: 1.4rem; margin: 2.4em 0 .6em; }
h3 { font-size: 1.05rem; margin: 0 0 .3em; }
a { color: var(--accent); }
p { max-width: 70ch; }
.lede { font-size: 1.12rem; color: var(--fg); }
.mute { color: var(--mute); }
.small { font-size: .88rem; }
nav.crumbs { font-size: .9rem; margin-bottom: 1rem; }
img.shot { width: 100%; border: 1px solid var(--line); border-radius: 8px;
           display: block; margin: 1.5rem 0; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { text-align: left; padding: .55rem .7rem; border-bottom: 1px solid var(--line);
         vertical-align: top; }
th { font-size: .82rem; text-transform: uppercase; letter-spacing: .05em; color: var(--mute); }
pre { background: var(--card); border: 1px solid var(--line); border-radius: 8px;
      padding: 14px 16px; overflow-x: auto; font-size: .9rem; }
code { font-family: ui-monospace, "JetBrains Mono", Menlo, monospace; font-size: .92em; }
.apps { display: grid; gap: 20px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
.app { border: 1px solid var(--line); border-radius: 10px; padding: 20px; background: var(--card); }
.filter { position: sticky; top: 0; background: var(--bg); padding: 14px 0 12px;
          border-bottom: 1px solid var(--line); z-index: 2; margin-bottom: 18px; }
.filter input { width: 100%; max-width: 420px; padding: 9px 12px; font: inherit;
                border: 1px solid var(--line); border-radius: 7px;
                background: var(--card); color: var(--fg); }
.grid { display: grid; gap: 18px; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); }
.tile { border: 1px solid var(--line); border-radius: 9px; overflow: hidden;
        background: var(--card); display: flex; flex-direction: column; }
.tile img { width: 100%; display: block; border-bottom: 1px solid var(--line);
            background: #fff; }
.tile .body { padding: 11px 13px 13px; }
.tile .name { font-weight: 600; }
.tile .meta { color: var(--mute); font-size: .83rem; margin-top: .15em; }
.tile details { margin-top: .5em; font-size: .85rem; }
.tile summary { cursor: pointer; color: var(--accent); }
.tile ol { margin: .5em 0 0; padding-left: 1.3em; color: var(--mute); }
.swatches { display: flex; gap: 3px; margin-top: .55em; }
.swatches i { width: 14px; height: 14px; border-radius: 3px; display: block;
              border: 1px solid rgba(128,128,128,.35); }
footer { border-top: 1px solid var(--line); margin-top: 56px; padding-top: 20px;
         color: var(--mute); font-size: .88rem; }
.none { color: var(--mute); padding: 2rem 0; display: none; }
"""

FILTER_JS = """
(function () {
  var box = document.getElementById('q'), none = document.getElementById('none');
  if (!box) return;
  var tiles = [].slice.call(document.querySelectorAll('.tile'));
  var heads = [].slice.call(document.querySelectorAll('[data-section]'));
  function run() {
    var q = box.value.trim().toLowerCase(), hits = 0;
    tiles.forEach(function (t) {
      var on = !q || t.dataset.find.indexOf(q) !== -1;
      t.style.display = on ? '' : 'none';
      if (on) hits++;
    });
    heads.forEach(function (h) {
      var live = [].slice.call(document.querySelectorAll(
        '.tile[data-section="' + h.dataset.section + '"]'))
        .some(function (t) { return t.style.display !== 'none'; });
      h.style.display = live ? '' : 'none';
      var g = document.getElementById('g-' + h.dataset.section);
      if (g) g.style.display = live ? '' : 'none';
    });
    none.style.display = hits ? 'none' : 'block';
  }
  box.addEventListener('input', run);
  run();
})();
"""


def page(title, body, crumbs="", depth=0):
    up = "" if depth == 0 else "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{up}style.css">
<header class="top"><div class="wrap">
<h1><a href="{up}index.html" style="color:inherit;text-decoration:none">{html.escape(SITE)}</a></h1>
<p class="mute" style="margin:0">Simple applications for Linux, each one a ground-up recreation.</p>
</div></header>
<div class="wrap">
{crumbs}
{body}
<footer>Built from the source in
<a href="https://github.com/janszafranski/just-a-collection-of-apps">janszafranski/just-a-collection-of-apps</a>
on {date.today().isoformat()}. Every template picture on this site is rendered
by the app itself.</footer>
</div>
</html>
"""


# Jan's own wording, as he left it in README.md. Kept verbatim on purpose: the
# git page and the front page are meant to say the same thing, and the README is
# the one he edits. If you change it there, change it here.
INTRO = """
<p class="lede">Simple applications for people who want to work using old
familiar workflows but don't want learn a new workflow from a more powerful, but
complex app like the <strong>ARTcraft</strong> ones. Use familiar menus,
toolbars, a page in front of you: open it and get on with the job. No
subscription, no account, no cloud, no tutorial, just save ordinary files to
ordinary folders on your own disk.</p>

<p>Each one is a <strong>ground-up recreation</strong> of an easy-to-use app,
written for Linux. Not a port, nor wrapper, nor fork: new code that borrows the
shape of a retired old app, rather than the thing itself. If you already know
how to do something in one of these popular british apps, you should be able to
do it here without learning anything new &mdash; the same menus in the same
places, the same words for the same jobs, the same order of operations.</p>

<p>The excellent ARTcraft suites do a great deal,and are perfect for familiar
users but for those of us are used to yet no longer with us, This isn't a
replacement for tools like those of ARTcraft... they are a re-creation of
british alternatives many of us used and brings them back and makes them
quick.</p>

<p class="mute">These are not a replacement for the big suites and not trying to
be. If you need what ARTcraft can do, use ARTcraft.</p>
"""


def build_index(counts):
    body = INTRO + f"""
<h2>The apps</h2>
<div class="apps">
  <div class="app">
    <h3><a href="webcreator.html">just a&hellip; WEBcreator</a></h3>
    <p class="small">Design a website by laying pages out &mdash; drag text,
    pictures, buttons and menus where you want them, share the header on a
    master page, preview in your browser, and publish plain HTML to a folder
    you can upload anywhere. Starts from any of
    <a href="webcreator.html#templates">{counts['total']} templates</a>.
    Saves <code>.webc</code>. Also opens a Serif <strong>WebPlus</strong>
    <code>.wpp</code> site, read-only on your original.</p>
    <p class="mute small">Python + Qt 6 (PySide6). Follows your desktop theme.</p>
  </div>
</div>
<p class="mute small">More will join it. It is a collection, not a suite: each
app stands on its own, installs on its own, and updates itself from the
repository.</p>

<h2>Install</h2>
<p>Clone, then run the app's own installer. Nothing needs root.</p>
<pre><code>git clone https://github.com/janszafranski/just-a-collection-of-apps.git
cd just-a-collection-of-apps
apps/webcreator/install.sh</code></pre>
<p>Each app also checks the repository for a newer version of itself
&mdash; <strong>Help &rsaquo; Check for Updates&hellip;</strong> &mdash; and each
has an <code>uninstall.sh</code> beside its installer.</p>
"""
    (DOCS / "index.html").write_text(page(SITE, body), encoding="utf-8")


SECTIONS = (
    ("ours", "Basic Templates", "Three originals that ship with the app &mdash; "
     "a small business, a community group and a portfolio."),
    ("theme-desktop", "Theme Layouts &mdash; Desktop", "Thirty-two starting points: "
     "a full page tree, three colour schemes of their own, and room to work."),
    ("theme-mobile", "Theme Layouts &mdash; Mobile", "The same thirty-two as "
     "narrow, single-column sites."),
    ("pro-desktop", "Pro Templates &mdash; Desktop", "Seven complete sites rather "
     "than starting points &mdash; longer page trees, deeper structure."),
    ("pro-mobile", "Pro Templates &mdash; Mobile", "The same seven, narrow."),
    ("samples", "Sample Sites", "Eleven more page trees from the same catalogue. "
     "They were sample documents rather than things to start a site from, and "
     "they are here because a page tree is a page tree."),
)

SECTION_OF = {
    ("Theme Layouts", "Desktop Websites"): "theme-desktop",
    ("Theme Layouts", "Mobile Websites"): "theme-mobile",
    ("WebPlus X8 Pro Templates", "Desktop Websites"): "pro-desktop",
    ("WebPlus X8 Pro Templates", "Mobile Websites"): "pro-mobile",
}


def render_previews(wc, fast):
    """One JPEG per template: the home page the app actually builds."""
    out = DOCS / "previews"
    out.mkdir(parents=True, exist_ok=True)
    tiles = []

    def shot(site, key):
        name = f"{key}.jpg"
        if not fast:
            img = wc.render_page_image(site, site['pages'][0], 460,
                                       crop=int(site['width'] * 1.5))
            img.save(str(out / name), "JPG", 84)
        return name

    for i, (nm, kind, fn) in enumerate(wc.TEMPLATES):
        site = fn()
        key = "ours-" + nm.lower()
        tiles.append(dict(section="ours", name=nm, sub=kind, key=key,
                          picture=shot(site, key), scheme="", colours=site['palette'],
                          pages=[p['title'] for p in site['pages']]))

    for row in wc.serif_catalogue().get("templates", []):
        section = SECTION_OF.get((row["category"], row["surface"]), "samples")
        site = wc.serif_site(row)
        scheme = site["serif"]["scheme"]
        cols = wc.serif_catalogue()["schemes"].get(scheme, [])
        tiles.append(dict(
            section=section, name=row["name"],
            sub=f"{len(row['pages'])} pages · {row['surface'] or row['category']}",
            key=row["key"], picture=shot(site, row["key"]), scheme=scheme,
            colours=list(dict.fromkeys(cols))[:8],
            pages=[p["name"] for p in wc.serif_pages(row)]))
        print(f"   {row['key']}", flush=True)
    return tiles


def build_webcreator(tiles):
    by_section = {}
    for t in tiles:
        by_section.setdefault(t["section"], []).append(t)

    chunks = []
    for key, title, blurb in SECTIONS:
        rows = by_section.get(key) or []
        if not rows:
            continue
        chunks.append(f'<h2 data-section="{key}">{title} '
                      f'<span class="mute small">({len(rows)})</span></h2>'
                      f'<p class="mute small" data-section="{key}">{blurb}</p>'
                      f'<div class="grid" id="g-{key}">')
        for t in rows:
            find = " ".join([t["name"], t["sub"], t["scheme"]] + t["pages"]).lower()
            sw = "".join(f'<i style="background:{html.escape(c)}"></i>'
                         for c in (t["colours"] or [])[:8])
            pages = "".join(f"<li>{html.escape(p)}</li>" for p in t["pages"])
            scheme = (f'<div class="meta">{html.escape(t["scheme"])}</div>'
                      if t["scheme"] else "")
            chunks.append(f"""<div class="tile" data-section="{key}" data-find="{html.escape(find)}">
<img src="previews/{html.escape(t['picture'])}" alt="{html.escape(t['name'])} home page" loading="lazy">
<div class="body"><div class="name">{html.escape(t['name'])}</div>
<div class="meta">{html.escape(t['sub'])}</div>{scheme}
<div class="swatches">{sw}</div>
<details><summary>{len(t['pages'])} pages</summary><ol>{pages}</ol></details>
</div></div>""")
        chunks.append("</div>")

    total = len(tiles)
    body = f"""<nav class="crumbs mute"><a href="index.html">{html.escape(SITE)}</a> &rsaquo; just a&hellip; WEBcreator</nav>
<h2 style="margin-top:0">just a&hellip; WEBcreator</h2>
<p class="lede">A desktop website designer for Linux. Lay pages out freely, put
the header and the menu on a master page so every page shares them, preview in
your browser, and publish plain HTML to a folder you can upload anywhere.</p>
<p>It is a <strong>ground-up recreation</strong> of the easy end of a desktop web
designer: menus where you expect them, a toolbar, a page in front of you, and a
Site tree down the side. If you have used one of the <strong>ARTcraft</strong>
apps to lay out a page, nothing here should need learning. The powerful,
complicated half &mdash; the parts most people never open &mdash; is not here on
purpose.</p>
<img class="shot" src="assets/screenshot.png" alt="just a... WEBcreator: menu bar, toolbar, tool palette, canvas and the Site tree">

<h2>What it does</h2>
<table>
<tr><th>New site</th><td>From any of {total} templates, or empty, through the Startup Assistant</td></tr>
<tr><th>Pages</th><td>Add, delete, reorder, nest &mdash; the Site tab draws the tree to whatever depth it has</td></tr>
<tr><th>Master pages</th><td>Create, edit and assign per page, so headers and menus are written once</td></tr>
<tr><th>Objects</th><td>Text, pictures, shapes, buttons, navigation bars, tables, forms, embedded HTML &mdash; drag, resize, rotate, align</td></tr>
<tr><th>Publish</th><td>Plain HTML and CSS into a folder, with your own filenames. No build step, nothing to host but files</td></tr>
<tr><th>Opens</th><td>Its own <code>.webc</code> sites, a website folder, and a Serif <strong>WebPlus</strong> <code>.wpp</code> publication &mdash; read-only on your original</td></tr>
</table>

<h2>Install</h2>
<pre><code>sudo pacman -S --needed pyside6 python-beautifulsoup4 qt6-webengine
git clone https://github.com/janszafranski/just-a-collection-of-apps.git
just-a-collection-of-apps/apps/webcreator/install.sh</code></pre>
<p class="small mute">Only <code>pyside6</code> is required, and use the distro
package rather than pip or the app will not pick up your desktop theme.
<code>python-beautifulsoup4</code> is for importing a website folder;
<code>qt6-webengine</code> makes an import match the original layout.</p>

<h2 id="templates">{total} templates</h2>
<img class="shot" src="assets/chooser.png" alt="The Startup Assistant: the template tree, a preview, the colour scheme picker and the page tick boxes">
<p>Pick one on the left, pick a colour scheme, untick any pages you don't want,
and open it. Eighty-nine of these follow the page trees of the templates
<strong>Serif WebPlus X8</strong> shipped &mdash; the page names, the filenames
each page publishes as, which page hangs off which, and the colour schemes that
template was drawn in, read off the install disc.</p>
<p><strong>The pictures below are not Serif's.</strong> No artwork, copy or code
of theirs is used or redistributed here. Every picture on this page is the home
page WEBcreator itself builds from that template, drawn by the app in its own
procedural artwork, in that template's first colour scheme. The structure is the
part that was worth recreating; the drawing is ours.</p>

<div class="filter"><input id="q" type="search" placeholder="Filter {total} templates by name, page or colour scheme&hellip;" autocomplete="off"></div>
<p class="none" id="none">Nothing matches that.</p>
{''.join(chunks)}
<script>{FILTER_JS}</script>
"""
    (DOCS / "webcreator.html").write_text(
        page("just a... WEBcreator", body), encoding="utf-8")


def grab_chooser(wc):
    """A real screenshot of the Startup Assistant, taken off-screen."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTreeWidgetItemIterator
    win = wc.MainWindow()
    dlg = wc.StartupAssistant(win)
    dlg.setAttribute(Qt.WA_DontShowOnScreen, True)
    dlg.resize(1040, 660)
    dlg.show()
    it = QTreeWidgetItemIterator(dlg.ttree)
    while it.value():
        data = it.value().data(0, Qt.UserRole)
        if data and data[0] == "serif" and data[1].endswith("stack-stone"):
            dlg.ttree.setCurrentItem(it.value())
            break
        it += 1
    dlg.show_template()
    (DOCS / "assets").mkdir(parents=True, exist_ok=True)
    dlg.grab().save(str(DOCS / "assets" / "chooser.png"))
    # The app's own README shows the same picture.
    shutil.copy2(DOCS / "assets" / "chooser.png",
                 ROOT / "apps" / "webcreator" / "assets" / "chooser.png")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fast", action="store_true",
                    help="rewrite the HTML without re-rendering the previews")
    args = ap.parse_args(argv)

    from PySide6.QtWidgets import QApplication
    wc = load_app()
    app = QApplication.instance() or QApplication([])

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "style.css").write_text(CSS, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "apps" / "webcreator" / "assets" / "screenshot.png",
                 DOCS / "assets" / "screenshot.png")
    grab_chooser(wc)

    tiles = render_previews(wc, args.fast)
    counts = {"total": len(tiles)}
    build_index(counts)
    build_webcreator(tiles)
    print(f":: {len(tiles)} templates -> {DOCS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
