#!/usr/bin/env python3
"""make_pdfs.py — turn an app's bundled manual.html / quickstart.html into
paginated A4 PDFs with a title cover page. Reuses the HTML the per-app manual
generators already produce; injects a cover + print CSS and prints via QtWebEngine.

    python3 tools/make_pdfs.py            # all creative apps
    python3 tools/make_pdfs.py paint      # one app
"""
import base64, os, sys, tempfile
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl, QEventLoop, QMarginsF, QTimer
from PySide6.QtGui import QPageLayout, QPageSize
from PySide6.QtWebEngineCore import QWebEnginePage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = QApplication.instance() or QApplication([])

# appdir, display name, accent colour (matches each app's manual CSS accent)
APPS = {
    "webcreator": ("WEBcreator", "#2a7d6b"),
    "paint":      ("PAINTcanvas", "#2a7d6b"),
    "draw":       ("DRAWmaster", "#2a7d6b"),
    "pagecreator": ("PAGEdesigner", "#2a7d6b"),
    "movie":      ("MOVIEeditor", "#2a7d6b"),
}

COVER_CSS = """
.cover{min-height:960px;display:flex;align-items:center;justify-content:center;text-align:center;break-after:page;page-break-after:always}
.cv-inner{max-width:640px;padding:0 40px;margin:0 auto}
.cv-banner{width:100%;max-width:560px;margin:0 auto 10px;display:block;border-radius:8px}
.cv-kind{font-size:2.4rem;font-weight:700;color:ACCENT;letter-spacing:.02em;margin-top:.3em}
.cv-rule{height:3px;width:120px;background:ACCENT;margin:18px auto}
.cv-sub{color:#64737c;font-size:1.08rem;max-width:48ch;margin:0 auto}
.cv-date{color:#64737c;margin-top:2.4em;font-size:.95rem}
@media print{ .cover{min-height:0;height:96vh} }
"""


def banner_uri(appdir):
    p = os.path.join(appdir, "banner.png")
    if not os.path.isfile(p):
        return ""
    with open(p, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


def inject_cover(html, name, kind, accent, appdir):
    uri = banner_uri(appdir)
    top = (f'<img class="cv-banner" src="{uri}" alt="">' if uri
           else f'<div class="cv-kind" style="font-size:3rem">{name}</div>')
    cover = (f'<section class="cover"><div class="cv-inner">{top}'
             f'<div class="cv-kind">{kind}</div><div class="cv-rule"></div>'
             f'<div class="cv-sub">just a&hellip; {name}</div>'
             f'<div class="cv-date">{date.today().strftime("%B %Y")}</div></div></section>')
    css = COVER_CSS.replace("ACCENT", accent)
    if "</style>" in html:
        html = html.replace("</style>", css + "</style>", 1)
    else:
        html = f"<style>{css}</style>" + html
    # put the cover right after the main page container opens
    if '<div class="page">' in html:
        html = html.replace('<div class="page">', '<div class="page">\n' + cover, 1)
    elif "<body>" in html:
        html = html.replace("<body>", "<body>\n" + cover, 1)
    else:
        html = cover + html
    return html


def html_to_pdf(html, pdf_path):
    # Load from a temp file alongside the PDF rather than via setHtml(): setHtml
    # silently fails (loadFinished=False → an empty PDF) once the inlined, data-URI
    # HTML grows past roughly 2 MB, which the big illustrated manuals now exceed.
    pg = QWebEnginePage(); loop = QEventLoop(); res = {}
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".html",
        dir=os.path.dirname(os.path.abspath(pdf_path)), delete=False)
    tmp.write(html); tmp.close()
    def finished(ok):
        res["loaded"] = ok
        lay = QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(14, 14, 14, 14))
        pg.printToPdf(pdf_path, lay)
    def done(_p, good):
        res["ok"] = good; loop.quit()
    pg.loadFinished.connect(finished); pg.pdfPrintingFinished.connect(done)
    pg.load(QUrl.fromLocalFile(tmp.name))
    QTimer.singleShot(120000, loop.quit); loop.exec()
    try:
        os.unlink(tmp.name)
    except OSError:
        pass
    return res.get("ok", False) and res.get("loaded", False)


def main():
    which = sys.argv[1:] or ["webcreator", "paint", "draw"]
    for key in which:
        name, accent = APPS[key]
        appdir = os.path.join(ROOT, "apps", key)
        for base, kind in (("quickstart", "Quick Start Guide"), ("manual", "User Guide")):
            src = os.path.join(appdir, base + ".html")
            if not os.path.isfile(src):
                continue
            html = inject_cover(open(src, encoding="utf-8").read(), name, kind, accent, appdir)
            out = os.path.join(appdir, base + ".pdf")
            ok = html_to_pdf(html, out)
            sz = os.path.getsize(out) // 1024 if os.path.exists(out) else 0
            print(f"{key}/{base}.pdf: {sz} KiB", "OK" if ok else "FAILED")


if __name__ == "__main__":
    main()
