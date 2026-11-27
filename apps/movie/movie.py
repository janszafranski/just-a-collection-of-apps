#!/usr/bin/env python3
# just a... MOVIEeditor — a clean-room home-video editor in the spirit of Serif
# MoviePlus X6 (the final version of MoviePlus). A multi-track TIMELINE: drop video
# clips, photos, titles and music onto tracks, trim and split them, cross-fade
# between shots, add picture-in-picture + chroma key, then render to an MP4.
# Rendering is done by ffmpeg (shelled out); preview uses Qt Multimedia.
#
# Project files are plain JSON with a .movp extension. Part of the "just a..."
# CREATORsuite family (shares the ~/Documents|Pictures/just a... folders and the
# ~/.local/share/justapps/recents.json log the launcher reads).
import sys, os, json, time, math, shutil, subprocess, tempfile, uuid

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QToolBar, QFileDialog, QMessageBox,
        QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QScrollArea,
        QDockWidget, QListWidget, QListWidgetItem, QLineEdit, QDialog, QFormLayout,
        QSpinBox, QDoubleSpinBox, QDialogButtonBox, QColorDialog, QMenu, QSlider,
        QStyle, QProgressDialog, QFontComboBox, QCheckBox, QTextEdit, QSizePolicy,
        QAbstractItemView, QToolButton)
    from PySide6.QtGui import (
        QAction, QIcon, QColor, QPainter, QPen, QBrush, QPixmap, QImage, QFont,
        QKeySequence, QActionGroup, QLinearGradient, QFontMetrics, QPolygonF)
    from PySide6.QtCore import (
        Qt, QSize, QRect, QRectF, QPoint, QPointF, QSettings, QTimer, QThread,
        Signal, QUrl, QMarginsF)
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
except ImportError:
    sys.stderr.write("just a... MOVIEeditor needs PySide6 (use your distro package, not pip):\n"
                     "    sudo pacman -S --needed pyside6\n")
    sys.exit(1)

APP = "just a... MOVIEeditor"
ORG = "justamovieeditor"
VERSION = "1.1-00"
EXT = ".movp"
FMT = "justamovie1"
HERE = os.path.dirname(os.path.abspath(__file__))
BANNER_IMG = os.path.join(HERE, 'banner.png')
MANUAL = next((p for p in (os.path.join(HERE, 'manual.pdf'), os.path.join(HERE, 'manual.html')) if os.path.isfile(p)), os.path.join(HERE, 'manual.pdf'))
QUICKSTART = next((p for p in (os.path.join(HERE, 'quickstart.pdf'), os.path.join(HERE, 'quickstart.html')) if os.path.isfile(p)), os.path.join(HERE, 'quickstart.pdf'))

def _bundled_tool(name):
    """A copy of ffmpeg/ffprobe shipped inside a PyInstaller bundle (Windows .exe),
    or beside the app, takes priority over whatever is on PATH."""
    bases = [getattr(sys, '_MEIPASS', None), HERE]
    for base in bases:
        if not base:
            continue
        for cand in (os.path.join(base, name), os.path.join(base, name + '.exe')):
            if os.path.isfile(cand):
                return cand
    return None


FFMPEG = _bundled_tool('ffmpeg') or shutil.which('ffmpeg')
FFPROBE = _bundled_tool('ffprobe') or shutil.which('ffprobe')

VIDEO_EXT = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.m4v', '.mpg', '.mpeg', '.flv', '.3gp'}
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tif', '.tiff'}
AUDIO_EXT = {'.mp3', '.wav', '.aac', '.m4a', '.ogg', '.flac', '.wma'}

# xfade transition name -> friendly label
TRANSITIONS = [
    ('none', 'Cut (none)'), ('fade', 'Dissolve'), ('fadeblack', 'Fade through black'),
    ('fadewhite', 'Fade through white'), ('wipeleft', 'Wipe left'), ('wiperight', 'Wipe right'),
    ('wipeup', 'Wipe up'), ('wipedown', 'Wipe down'), ('slideleft', 'Slide left'),
    ('slideright', 'Slide right'), ('dissolve', 'Grainy dissolve'), ('circleopen', 'Circle open'),
    ('circleclose', 'Circle close'), ('radial', 'Clock wipe'), ('pixelize', 'Pixelate'),
    ('smoothleft', 'Smooth left'),
]

DEFAULT_IMAGE_DUR = 4.0
DEFAULT_TITLE_DUR = 4.0

# video-effect presets -> an ffmpeg filter fragment (MoviePlus "2D/3D filter effects")
EFFECTS = [
    ('none', 'None', ''),
    ('bw', 'Black & white', 'hue=s=0'),
    ('sepia', 'Sepia', 'colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131'),
    ('vignette', 'Vignette', 'vignette=PI/4'),
    ('blur', 'Soft focus', 'gblur=sigma=8'),
    ('sharpen', 'Sharpen', 'unsharp=5:5:1.0'),
    ('oldfilm', 'Old film', 'curves=vintage,noise=alls=12:allf=t'),
    ('warm', 'Warm', 'colorbalance=rm=.15:ym=.1'),
    ('cool', 'Cool', 'colorbalance=bm=.15:gm=.05'),
    ('negative', 'Negative', 'negate'),
    ('mirror', 'Mirror', 'hflip'),
]
EFFECT_LABELS = [(k, lbl) for k, lbl, _ in EFFECTS]
EFFECT_FRAG = {k: frag for k, _, frag in EFFECTS}


def atempo_chain(speed):
    """ffmpeg atempo accepts 0.5–2.0 per stage; chain stages for larger factors."""
    speed = max(0.1, min(100.0, float(speed)))
    stages = []
    s = speed
    while s > 2.0:
        stages.append(2.0); s /= 2.0
    while s < 0.5:
        stages.append(0.5); s /= 0.5
    stages.append(s)
    return ','.join(f'atempo={x:.4f}' for x in stages)


# overlay blend modes (MoviePlus "Blend Modes")
BLEND_MODES = ['normal', 'multiply', 'screen', 'overlay', 'darken', 'lighten',
               'addition', 'difference', 'hardlight', 'softlight']
# title animations
TEXT_ANIMS = [('none', 'None'), ('fade', 'Fade in & out'), ('slideL', 'Slide in from left'),
              ('slideR', 'Slide in from right'), ('slideU', 'Rise up')]


def _ff_path(p):
    """Make a filesystem path safe inside an ffmpeg filtergraph (Windows drive
    colons and backslashes would otherwise be read as option separators)."""
    return p.replace('\\', '/').replace(':', '\\:')


def _font_variant(bold, italic):
    want = 'sans'
    style = (('bold ' if bold else '') + ('italic' if italic else '')).strip() or 'regular'
    try:
        r = subprocess.run(['fc-match', '-f', '%{file}', f'{want}:style={style}'],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and os.path.isfile(r.stdout.strip()):
            return r.stdout.strip()
    except Exception:
        pass
    return FONT_FILE


def crop_vf(clip):
    cr = clip.get('crop')
    if not cr:
        return None
    x, y = float(cr.get('x', 0)), float(cr.get('y', 0))
    w, h = float(cr.get('w', 1)), float(cr.get('h', 1))
    w = max(0.05, min(1.0, w)); h = max(0.05, min(1.0, h))
    return f"crop=iw*{w:.4f}:ih*{h:.4f}:iw*{x:.4f}:ih*{y:.4f}"


def transform_vf(clip, W, H):
    """Shrink + position a full-frame clip on black (2D transform scale/position)."""
    tr = clip.get('transform')
    if not tr:
        return None
    s = max(0.05, min(1.0, float(tr.get('scale', 1.0))))
    if s >= 0.999 and float(tr.get('x', 0.5)) == 0.5 and float(tr.get('y', 0.5)) == 0.5:
        return None
    sw, sh = max(2, int(W * s) // 2 * 2), max(2, int(H * s) // 2 * 2)
    px, py = float(tr.get('x', 0.5)), float(tr.get('y', 0.5))
    return f"scale={sw}:{sh},pad={W}:{H}:(ow-iw)*{px:.4f}:(oh-ih)*{py:.4f}:color=black"


def clip_extra_vf(clip):
    """Per-clip colour adjustments, effect preset and rotation — shared by base + overlay."""
    parts = []
    adj = clip.get('adjust')
    if adj:
        b = float(adj.get('brightness', 0)); c = float(adj.get('contrast', 1.0))
        s = float(adj.get('saturation', 1.0)); g = float(adj.get('gamma', 1.0))
        if b or c != 1.0 or s != 1.0 or g != 1.0:
            parts.append(f"eq=brightness={b:.3f}:contrast={c:.3f}:saturation={s:.3f}:gamma={g:.3f}")
    frag = EFFECT_FRAG.get(clip.get('effect', 'none'), '')
    if frag:
        parts.append(frag)
    rot = float(clip.get('rotate', 0) or 0)
    if rot:
        parts.append(f"rotate={rot}*PI/180:fillcolor=black@0")
    return parts


# ----------------------------------------------------------------- shared-folder plumbing
def _just_dir(kind):
    base = os.path.expanduser('~/Documents' if kind == 'docs' else '~/Pictures')
    d = os.path.join(base, 'just a...')
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def _justapps_recent(appkey, path):
    try:
        d = os.path.expanduser('~/.local/share/justapps'); os.makedirs(d, exist_ok=True)
        f = os.path.join(d, 'recents.json')
        try:
            with open(f) as fh:
                data = json.load(fh)
        except Exception:
            data = []
        data = [e for e in data if isinstance(e, dict) and e.get('path') != path]
        data.insert(0, {'app': appkey, 'path': path, 't': int(time.time())})
        with open(f, 'w') as fh:
            json.dump(data[:50], fh)
    except Exception:
        pass


# ----------------------------------------------------------------- ffmpeg helpers
def ffprobe_info(path):
    """Return {duration, width, height, has_video, has_audio} for a media file."""
    info = {'duration': 0.0, 'width': 0, 'height': 0, 'has_video': False, 'has_audio': False}
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXT:
        info['has_video'] = True
        info['duration'] = DEFAULT_IMAGE_DUR
        img = QImage(path)
        if not img.isNull():
            info['width'], info['height'] = img.width(), img.height()
        return info
    if not FFPROBE:
        return info
    try:
        out = subprocess.run(
            [FFPROBE, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', path],
            capture_output=True, text=True, timeout=30)
        d = json.loads(out.stdout or '{}')
        fmt = d.get('format', {})
        try:
            info['duration'] = float(fmt.get('duration', 0) or 0)
        except (TypeError, ValueError):
            info['duration'] = 0.0
        for s in d.get('streams', []):
            if s.get('codec_type') == 'video' and s.get('disposition', {}).get('attached_pic', 0) == 0:
                info['has_video'] = True
                info['width'] = s.get('width', 0) or info['width']
                info['height'] = s.get('height', 0) or info['height']
            elif s.get('codec_type') == 'audio':
                info['has_audio'] = True
    except Exception:
        pass
    return info


def make_thumbnail(path, kind, dst, size=160):
    """Write a small thumbnail of a clip source to dst (png). Return True on success."""
    try:
        if kind == 'image':
            img = QImage(path)
            if img.isNull():
                return False
            img.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(dst, 'PNG')
            return True
        if kind == 'audio' or not FFMPEG:
            return False
        info = ffprobe_info(path)
        ts = max(0.0, info['duration'] / 3.0)
        r = subprocess.run([FFMPEG, '-y', '-ss', f'{ts:.2f}', '-i', path, '-frames:v', '1',
                            '-vf', f'scale={size}:-1', dst],
                           capture_output=True, timeout=30)
        return r.returncode == 0 and os.path.isfile(dst)
    except Exception:
        return False


def _dt_escape(text):
    """Escape a string for ffmpeg drawtext's text= option."""
    text = text.replace('\\', '\\\\').replace(':', '\\:').replace("'", "’")
    text = text.replace('%', '\\%')
    return text


def _font_file():
    try:
        r = subprocess.run(['fc-match', '-f', '%{file}', 'sans'], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and os.path.isfile(r.stdout.strip()):
            return r.stdout.strip()
    except Exception:
        pass
    cands = ['/usr/share/fonts/noto/NotoSans-Regular.ttf',
             '/usr/share/fonts/TTF/DejaVuSans.ttf',
             '/usr/share/fonts/dejavu/DejaVuSans.ttf',
             r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\segoeui.ttf',
             '/System/Library/Fonts/Supplemental/Arial.ttf']
    # a font bundled with the app (Windows .exe has no fontconfig)
    for base in (getattr(sys, '_MEIPASS', None), HERE):
        if base:
            fdir = os.path.join(base, 'fonts')
            if os.path.isdir(fdir):
                pref = [f for f in sorted(os.listdir(fdir)) if f.lower().endswith('.ttf')
                        and any(k in f.lower() for k in ('dejavu', 'noto', 'roboto', 'opensans', 'arial'))]
                any_ttf = [f for f in sorted(os.listdir(fdir)) if f.lower().endswith('.ttf')]
                for f in (pref + any_ttf):
                    cands.insert(0, os.path.join(fdir, f))
    for p in cands:
        if os.path.isfile(p):
            return p
    return ''


FONT_FILE = _font_file()


# ===================================================================== project model
def new_clip(src, kind, info=None):
    info = info or {}
    cid = uuid.uuid4().hex[:8]
    dur = info.get('duration', DEFAULT_IMAGE_DUR) or DEFAULT_IMAGE_DUR
    c = {
        'id': cid, 'src': src, 'kind': kind, 'name': os.path.basename(src) if src else 'Title',
        'start': 0.0, 'dur': float(dur), 'in': 0.0, 'src_dur': float(dur),
        'volume': 1.0, 'pan': 0.0, 'fade_in': 0.0, 'fade_out': 0.0,
        'transition': {'type': 'none', 'dur': 1.0},
        'kenburns': None, 'chroma': None, 'opacity': 1.0, 'opacity_to': None, 'speed': 1.0,
        'adjust': None,   # {'brightness':0,'contrast':1,'saturation':1,'gamma':1}
        'effect': 'none', 'rotate': 0.0,
        'crop': None,       # {'x','y','w','h'} as fractions 0..1 (w/h = kept size)
        'transform': None,  # {'scale','x','y'} shrink+position a clip on black
        'blend': 'normal',  # overlay blend mode
        'pip': None,  # {'x':.., 'y':.., 'scale':.., optional 'to':{x,y,scale}} picture-in-picture
        'color': '#3366cc',  # used when kind == 'color'
        'text': None,
    }
    if kind == 'text':
        c['dur'] = DEFAULT_TITLE_DUR; c['src_dur'] = DEFAULT_TITLE_DUR
        c['text'] = {'content': 'Your title here', 'size': 64, 'color': '#ffffff',
                     'bg': '#000000', 'x': 'center', 'y': 'center', 'box': False,
                     'bold': False, 'italic': False, 'outline': 0, 'anim': 'none'}
    return c


def default_project():
    return {
        'format': FMT, 'version': VERSION, 'width': 1280, 'height': 720, 'fps': 30,
        'tracks': [
            {'id': 'V2', 'kind': 'video', 'name': 'Overlay', 'clips': []},
            {'id': 'V1', 'kind': 'video', 'name': 'Video', 'clips': []},
            {'id': 'A1', 'kind': 'audio', 'name': 'Audio', 'clips': []},
        ],
    }


def project_duration(proj):
    end = 0.0
    for t in proj['tracks']:
        for c in t['clips']:
            end = max(end, c['start'] + c['dur'])
    return end


def kind_for_path(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXT:
        return 'video'
    if ext in IMAGE_EXT:
        return 'image'
    if ext in AUDIO_EXT:
        return 'audio'
    return None


# ===================================================================== render engine
class RenderWorker(QThread):
    progress = Signal(int, str)   # percent, message
    done = Signal(bool, str)      # ok, message/path

    def __init__(self, proj, outpath, preview=False, out_h=None, crf=20, parent=None):
        super().__init__(parent)
        self.proj = proj
        self.outpath = outpath
        self.preview = preview
        self.out_h = out_h      # export resolution override (height); width scales to keep AR
        self.crf = crf          # x264 quality for the final encode (lower = better)
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _run_ff(self, args):
        if self._cancel:
            raise RuntimeError('cancelled')
        r = subprocess.run([FFMPEG, '-y', '-hide_banner', '-loglevel', 'error'] + args,
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or 'ffmpeg failed')[-800:])

    def run(self):
        try:
            if not FFMPEG:
                raise RuntimeError('ffmpeg is not installed.')
            path = self._render()
            self.done.emit(True, path)
        except Exception as e:
            self.done.emit(False, str(e))

    # -- helpers for dimensions ------------------------------------------------
    def _dims(self):
        p = self.proj
        W, H, FPS = int(p['width']), int(p['height']), int(p['fps'])
        if self.preview:
            # half-ish resolution, keep even numbers
            W = max(160, (W // 2) // 2 * 2)
            H = max(90, (H // 2) // 2 * 2)
        elif self.out_h and self.out_h != H:
            W = max(160, int(round(W * self.out_h / H)) // 2 * 2)
            H = int(self.out_h) // 2 * 2
        return W, H, FPS

    def _vf_fit(self, W, H):
        return (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1")

    def _video_track(self):
        for t in self.proj['tracks']:
            if t['id'] == 'V1':
                return t
        for t in self.proj['tracks']:
            if t['kind'] == 'video':
                return t
        return {'clips': []}

    # -- normalise one base-track clip to a WxH@fps segment --------------------
    def _norm_segment(self, clip, idx, tmp, W, H, FPS):
        out = os.path.join(tmp, f'seg{idx}.mp4')
        dur = max(0.05, float(clip['dur']))
        speed = float(clip.get('speed', 1.0) or 1.0)
        extra = clip_extra_vf(clip)
        crop = crop_vf(clip) if clip['kind'] in ('video', 'image') else None
        tf = transform_vf(clip, W, H) if clip['kind'] != 'text' else None
        vf = ((crop + ',') if crop else '') + self._vf_fit(W, H)
        if tf:
            vf += ',' + tf
        if extra:
            vf += ',' + ','.join(extra)
        if speed != 1.0 and clip['kind'] in ('video',):
            vf += f",setpts=PTS/{speed:.4f}"
        vf += f",fps={FPS},format=yuv420p"
        fi, fo = float(clip.get('fade_in', 0)), float(clip.get('fade_out', 0))
        if fi > 0:
            vf += f",fade=t=in:st=0:d={fi:.3f}"
        if fo > 0:
            vf += f",fade=t=out:st={max(0,dur-fo):.3f}:d={fo:.3f}"
        kind = clip['kind']
        if kind == 'color':
            args = ['-f', 'lavfi', '-t', f'{dur:.3f}',
                    '-i', f"color=c={clip.get('color','#3366cc')}:s={W}x{H}:r={FPS}", '-vf', vf]
        elif kind == 'image':
            kb = clip.get('kenburns')
            if kb:
                # Ken Burns: zoompan over the clip duration, with an optional pan direction
                z = float(kb.get('zoom', 1.3))
                frames = max(1, int(dur * FPS))
                zexpr = f"min(zoom+{(z-1)/frames:.6f},{z})"
                pan = kb.get('pan', 'in')
                # x/y expressions pan across the over-scanned frame as it zooms
                xmid, ymid = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
                xexpr, yexpr = xmid, ymid
                if pan == 'left':
                    xexpr = f"(iw-iw/zoom)*(1-on/{frames})"
                elif pan == 'right':
                    xexpr = f"(iw-iw/zoom)*(on/{frames})"
                elif pan == 'up':
                    yexpr = f"(ih-ih/zoom)*(1-on/{frames})"
                elif pan == 'down':
                    yexpr = f"(ih-ih/zoom)*(on/{frames})"
                cpre = (crop + ',') if crop else ''
                vf = (f"{cpre}scale={W*4}:{H*4}:force_original_aspect_ratio=increase,"
                      f"crop={W*4}:{H*4},"
                      f"zoompan=z='{zexpr}':d={frames}:x='{xexpr}':y='{yexpr}':"
                      f"s={W}x{H}:fps={FPS}")
                if extra:
                    vf += ',' + ','.join(extra)
                vf += ",format=yuv420p"
                if fi > 0:
                    vf += f",fade=t=in:st=0:d={fi:.3f}"
                if fo > 0:
                    vf += f",fade=t=out:st={max(0,dur-fo):.3f}:d={fo:.3f}"
            args = ['-loop', '1', '-t', f'{dur:.3f}', '-i', clip['src'], '-vf', vf]
        elif kind == 'text':
            txt = clip['text']
            bg = txt.get('bg') or '#000000'
            args = ['-f', 'lavfi', '-t', f'{dur:.3f}', '-i', f"color=c={bg}:s={W}x{H}:r={FPS}",
                    '-vf', self._drawtext_vf(txt, W, H, t0=0.0, dur=dur)]
        else:  # video
            ss = float(clip.get('in', 0))
            src_t = dur * speed  # at 2× speed we consume twice the source for the same output
            args = ['-ss', f'{ss:.3f}', '-t', f'{src_t:.3f}', '-i', clip['src'], '-vf', vf]
        preset = 'ultrafast'
        self._run_ff(args + ['-an', '-c:v', 'libx264', '-preset', preset, '-pix_fmt', 'yuv420p',
                             '-r', str(FPS), out])
        return out, dur

    def _drawtext_vf(self, txt, W, H, t0=0.0, dur=4.0):
        content = _dt_escape(txt.get('content', ''))
        size = int(txt.get('size', 64))
        col = txt.get('color', '#ffffff').lstrip('#')
        font = _font_variant(txt.get('bold'), txt.get('italic'))
        xbase = {'left': 'w*0.06', 'center': '(w-text_w)/2', 'right': 'w*0.94-text_w'}.get(txt.get('x'), '(w-text_w)/2')
        ybase = {'top': 'h*0.08', 'center': '(h-text_h)/2', 'bottom': 'h*0.88-text_h'}.get(txt.get('y'), '(h-text_h)/2')
        anim = txt.get('anim', 'none')
        d = max(0.4, float(dur)); AD = min(0.6, d / 2)
        T = f"(t-{t0:.3f})"
        x_expr, y_expr, alpha_expr = xbase, ybase, None
        if anim == 'fade':
            alpha_expr = (f"if(lt({T},{AD}),{T}/{AD},"
                          f"if(gt({T},{d-AD:.3f}),max(0,({d:.3f}-{T})/{AD}),1))")
        elif anim == 'slideL':
            x_expr = f"if(lt({T},{AD}),(0-text_w)+(({xbase})+text_w)*({T}/{AD}),{xbase})"
        elif anim == 'slideR':
            x_expr = f"if(lt({T},{AD}),w+(({xbase})-w)*({T}/{AD}),{xbase})"
        elif anim == 'slideU':
            y_expr = f"if(lt({T},{AD}),h+(({ybase})-h)*({T}/{AD}),{ybase})"
        parts = [f"drawtext=fontfile='{_ff_path(font)}'", f"text='{content}'", f"fontsize={size}",
                 f"fontcolor=#{col}", f"x='{x_expr}'", f"y='{y_expr}'"]
        if alpha_expr:
            parts.append(f"alpha='{alpha_expr}'")
        ow = int(txt.get('outline', 0) or 0)
        if ow > 0:
            parts.append(f"borderw={ow}:bordercolor=black")
        if txt.get('box'):
            parts.append("box=1:boxcolor=black@0.5:boxborderw=18")
        elif not ow:
            parts.append("shadowcolor=black@0.6:shadowx=2:shadowy=2")
        return ":".join(parts)

    # -- stitch base-track segments into one video ----------------------------
    def _render(self):
        W, H, FPS = self._dims()
        total = max(0.1, project_duration(self.proj))
        tmp = tempfile.mkdtemp(prefix='justmovie_')
        try:
            vt = self._video_track()
            clips = sorted([c for c in vt['clips']], key=lambda c: c['start'])
            self.progress.emit(2, 'Preparing the main video track…')
            if not clips:
                base = os.path.join(tmp, 'base.mp4')
                self._run_ff(['-f', 'lavfi', '-t', f'{total:.3f}', '-i',
                              f'color=c=black:s={W}x{H}:r={FPS}', '-c:v', 'libx264',
                              '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', base])
            else:
                base = self._stitch(clips, tmp, W, H, FPS, total)
            self.progress.emit(55, 'Adding titles and overlays…')
            composited = self._overlays(base, tmp, W, H, FPS)
            self.progress.emit(78, 'Mixing audio…')
            audio = self._audio(tmp, total)
            self.progress.emit(90, 'Finishing the movie…')
            final = self.outpath
            os.makedirs(os.path.dirname(final) or '.', exist_ok=True)
            # preview copies (fast); export re-encodes at the chosen quality (CRF)
            venc = (['-c:v', 'copy'] if self.preview else
                    ['-c:v', 'libx264', '-preset', 'medium', '-crf', str(self.crf), '-pix_fmt', 'yuv420p'])
            if audio:
                self._run_ff(['-i', composited, '-i', audio, '-map', '0:v:0', '-map', '1:a:0',
                              *venc, '-c:a', 'aac', '-b:a', '192k',
                              '-t', f'{total:.3f}', '-movflags', '+faststart', final])
            else:
                self._run_ff(['-i', composited, '-an', *venc,
                              '-t', f'{total:.3f}', '-movflags', '+faststart', final])
            self.progress.emit(100, 'Done')
            return final
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _stitch(self, clips, tmp, W, H, FPS, total):
        """Normalise each clip, honour gaps with black, then concat/xfade together."""
        segs = []          # list of (path, dur)
        cursor = 0.0
        for i, c in enumerate(clips):
            gap = c['start'] - cursor
            if gap > 0.05:
                g = os.path.join(tmp, f'gap{i}.mp4')
                self._run_ff(['-f', 'lavfi', '-t', f'{gap:.3f}', '-i',
                              f'color=c=black:s={W}x{H}:r={FPS}', '-an', '-c:v', 'libx264',
                              '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-r', str(FPS), g])
                segs.append((g, gap, 'none', 0.0))
            seg, dur = self._norm_segment(c, i, tmp, W, H, FPS)
            tr = c.get('transition') or {'type': 'none', 'dur': 0}
            # a transition only applies when this clip butts directly against the previous one
            applies = tr.get('type', 'none') != 'none' and gap <= 0.05 and segs
            segs.append((seg, dur, tr.get('type') if applies else 'none',
                         float(tr.get('dur', 1.0)) if applies else 0.0))
            self.progress.emit(5 + int(45 * (i + 1) / len(clips)), f'Rendering clip {i+1} of {len(clips)}…')
            cursor = c['start'] + dur

        if len(segs) == 1 and segs[0][2] == 'none':
            return segs[0][0]
        if all(s[2] == 'none' for s in segs):
            listf = os.path.join(tmp, 'concat.txt')
            with open(listf, 'w') as fh:
                for p, *_ in segs:
                    fh.write(f"file '{p}'\n")
            out = os.path.join(tmp, 'base.mp4')
            self._run_ff(['-f', 'concat', '-safe', '0', '-i', listf, '-c', 'copy', out])
            return out
        # build an xfade/concat chain in one filter_complex. xfade/concat require all
        # inputs to share a timebase + fps, so normalise each with settb/fps first.
        inputs = []
        for p, *_ in segs:
            inputs += ['-i', p]
        fc = []
        for i in range(len(segs)):
            fc.append(f"[{i}:v]fps={FPS},format=yuv420p,setsar=1,settb=AVTB[v{i}]")
        cur = '[v0]'
        cur_dur = segs[0][1]
        for i in range(1, len(segs)):
            _, dur, ttype, tdur = segs[i]
            lbl = f'[x{i}]'
            if ttype != 'none' and tdur > 0:
                tdur = min(tdur, cur_dur - 0.05, dur - 0.05)
                tdur = max(0.1, tdur)
                offset = max(0.0, cur_dur - tdur)
                fc.append(f"{cur}[v{i}]xfade=transition={ttype}:duration={tdur:.3f}:offset={offset:.3f}{lbl}")
                cur_dur = cur_dur + dur - tdur
            else:
                fc.append(f"{cur}[v{i}]concat=n=2:v=1:a=0{lbl}")
                cur_dur = cur_dur + dur
            cur = lbl
        out = os.path.join(tmp, 'base.mp4')
        self._run_ff(inputs + ['-filter_complex', ';'.join(fc), '-map', cur,
                              '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                              '-r', str(FPS), out])
        return out

    def _overlays(self, base, tmp, W, H, FPS):
        """Burn title/overlay-track clips (text drawtext + image/video PiP) onto base."""
        over = []
        for t in self.proj['tracks']:
            if t['kind'] != 'video' or t['id'] == 'V1':
                continue
            for c in t['clips']:
                over.append(c)
        over.sort(key=lambda c: c['start'])
        if not over:
            return base
        inputs = ['-i', base]
        fc = []
        cur = '[0:v]'
        idx = 1
        for c in over:
            s, e = c['start'], c['start'] + c['dur']
            enable = f"enable='between(t,{s:.3f},{e:.3f})'"
            if c['kind'] == 'text':
                lbl = f'[o{idx}]'
                fc.append(f"{cur}{self._drawtext_vf(c['text'], W, H, t0=s, dur=c['dur'])}:{enable}{lbl}")
                cur = lbl
                continue
            # image / video / colour PiP overlay
            pip = c.get('pip') or {'x': 0.0, 'y': 0.0, 'scale': 1.0}
            scale = float(pip.get('scale', 1.0))
            ow, oh = max(2, int(W * scale) // 2 * 2), max(2, int(H * scale) // 2 * 2)
            speed = float(c.get('speed', 1.0) or 1.0)
            if c['kind'] == 'image':
                inputs += ['-loop', '1', '-t', f'{c["dur"]:.3f}', '-itsoffset', f'{s:.3f}', '-i', c['src']]
            elif c['kind'] == 'color':
                inputs += ['-f', 'lavfi', '-t', f'{c["dur"]:.3f}', '-itsoffset', f'{s:.3f}',
                           '-i', f"color=c={c.get('color','#3366cc')}:s={ow}x{oh}:r={FPS}"]
            else:
                inputs += ['-ss', f'{c.get("in",0):.3f}', '-t', f'{c["dur"]*speed:.3f}',
                           '-itsoffset', f'{s:.3f}', '-i', c['src']]
            blend = c.get('blend', 'normal')
            full = blend != 'normal'   # blend modes composite full-frame
            sw, sh = (W, H) if full else (ow, oh)
            cpre = (crop_vf(c) + ',') if (c['kind'] in ('video', 'image') and c.get('crop')) else ''
            pre = f"[{idx}:v]{cpre}scale={sw}:{sh}:force_original_aspect_ratio={'disable' if full else 'decrease'},setsar=1"
            if speed != 1.0 and c['kind'] == 'video':
                pre += f",setpts=PTS/{speed:.4f}"
            for frag in clip_extra_vf(c):
                pre += ',' + frag
            if c.get('chroma'):
                ck = c['chroma']
                col = ck.get('color', '#00ff00').lstrip('#')
                sim = float(ck.get('similarity', 0.25))
                pre += f",chromakey=0x{col}:{sim}:0.1"
            # alpha: constant opacity and/or fade in/out (real overlay opacity animation)
            op = float(c.get('opacity', 1.0) or 1.0)
            fi, fo = float(c.get('fade_in', 0)), float(c.get('fade_out', 0))
            if op < 1.0 or fi > 0 or fo > 0:
                pre += ",format=yuva420p"
                if op < 1.0:
                    pre += f",colorchannelmixer=aa={op:.3f}"
                if fi > 0:
                    pre += f",fade=t=in:alpha=1:st={s:.3f}:d={fi:.3f}"
                if fo > 0:
                    pre += f",fade=t=out:alpha=1:st={max(s,e-fo):.3f}:d={fo:.3f}"
            plbl = f'[p{idx}]'
            fc.append(pre + plbl)
            lbl = f'[o{idx}]'
            if full:
                fc.append(f"{cur}{plbl}blend=all_mode={blend}:{enable}{lbl}")
            else:
                # position, optionally animated start -> end across the clip ('to')
                to = pip.get('to')
                px0, py0 = float(pip.get('x', 0.5)), float(pip.get('y', 0.5))
                if to:
                    px1, py1 = float(to.get('x', px0)), float(to.get('y', py0))
                    frac = f"clip((t-{s:.3f})/{max(0.05,c['dur']):.3f},0,1)"
                    x = f"(W-w)*({px0:.4f}+({px1-px0:.4f})*{frac})"
                    y = f"(H-h)*({py0:.4f}+({py1-py0:.4f})*{frac})"
                else:
                    x = f"(W-w)*{px0:.4f}"
                    y = f"(H-h)*{py0:.4f}"
                fc.append(f"{cur}{plbl}overlay=x='{x}':y='{y}':{enable}{lbl}")
            cur = lbl
            idx += 1
        out = os.path.join(tmp, 'comp.mp4')
        self._run_ff(inputs + ['-filter_complex', ';'.join(fc), '-map', cur,
                              '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                              '-r', str(FPS), out])
        return out

    def _audio(self, tmp, total):
        """Collect audio from every audio-bearing clip, place at its start, mix."""
        srcs = []  # clip dicts that carry audio
        for t in self.proj['tracks']:
            for c in t['clips']:
                k = c['kind']
                if k in ('image', 'text', 'color'):
                    continue
                if k == 'video' and not ffprobe_info(c['src'])['has_audio']:
                    continue
                if float(c.get('volume', 1.0)) <= 0:
                    continue
                srcs.append(c)
        if not srcs:
            return None
        inputs = []
        fc = []
        labels = []
        for i, c in enumerate(srcs):
            ss, dur, start = float(c.get('in', 0)), float(c['dur']), float(c['start'])
            vol, fi, fo = float(c.get('volume', 1.0)), float(c.get('fade_in', 0)), float(c.get('fade_out', 0))
            speed = float(c.get('speed', 1.0) or 1.0)
            pan = float(c.get('pan', 0.0) or 0.0)
            inputs += ['-ss', f'{ss:.3f}', '-t', f'{dur*speed:.3f}', '-i', c['src']]
            chain = f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
            if speed != 1.0:
                chain += ',' + atempo_chain(speed)
            if vol != 1.0:
                chain += f",volume={vol:.3f}"
            if pan:  # -1 full left .. +1 full right
                l = max(0.0, 1 - max(0, pan)); r = max(0.0, 1 + min(0, pan))
                chain += f",pan=stereo|c0={l:.3f}*c0|c1={r:.3f}*c1"
            if fi > 0:
                chain += f",afade=t=in:st=0:d={fi:.3f}"
            if fo > 0:
                chain += f",afade=t=out:st={max(0,dur-fo):.3f}:d={fo:.3f}"
            delay = int(start * 1000)
            if delay > 0:
                chain += f",adelay={delay}|{delay}"
            lbl = f'[a{i}]'
            fc.append(chain + lbl)
            labels.append(lbl)
        mix = ''.join(labels) + f"amix=inputs={len(labels)}:dropout_transition=0:normalize=0[aout]"
        fc.append(mix)
        out = os.path.join(tmp, 'audio.m4a')
        self._run_ff(inputs + ['-filter_complex', ';'.join(fc), '-map', '[aout]',
                              '-t', f'{total:.3f}', '-c:a', 'aac', '-b:a', '192k', out])
        return out


# ===================================================================== timeline widget
TRACK_H = 62
HEADER_W = 92
RULER_H = 22
CLIP_COLORS = {'video': '#3a6ea5', 'image': '#8a5a9e', 'audio': '#2e8b6b',
               'text': '#b5792b', 'color': '#55606e'}


class Timeline(QWidget):
    selectionChanged = Signal()
    playheadMoved = Signal(float)
    clipsChanged = Signal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.pps = 60.0              # pixels per second (zoom)
        self.playhead = 0.0          # seconds
        self.sel = None              # (track_index, clip_id)
        self.setMinimumHeight(RULER_H + TRACK_H * 3 + 10)
        self.setMouseTracking(True)
        self._drag = None            # dict describing an in-progress drag
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # -- geometry helpers ------------------------------------------------------
    def proj(self):
        return self.main.proj

    def x_for(self, t):
        return HEADER_W + int(t * self.pps)

    def t_for(self, x):
        return max(0.0, (x - HEADER_W) / self.pps)

    def track_rect(self, i):
        return QRect(HEADER_W, RULER_H + i * TRACK_H, self.width() - HEADER_W, TRACK_H)

    def clip_rect(self, ti, clip):
        r = self.track_rect(ti)
        x = self.x_for(clip['start'])
        w = max(6, int(clip['dur'] * self.pps))
        return QRect(x, r.y() + 4, w, TRACK_H - 8)

    def sizeHint(self):
        total = max(project_duration(self.proj()), 20)
        return QSize(int(HEADER_W + total * self.pps + 300), RULER_H + TRACK_H * len(self.proj()['tracks']) + 10)

    def minimumSizeHint(self):
        return self.sizeHint()

    def clip_at(self, pos):
        for ti, tr in enumerate(self.proj()['tracks']):
            for c in tr['clips']:
                if self.clip_rect(ti, c).contains(pos):
                    return ti, c
        return None, None

    # -- painting --------------------------------------------------------------
    def paintEvent(self, ev):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#1c1f24'))
        W = self.width()
        tracks = self.proj()['tracks']
        # ruler
        p.fillRect(QRect(0, 0, W, RULER_H), QColor('#2a2e35'))
        p.setPen(QColor('#8891a0'))
        f = QFont(); f.setPixelSize(10); p.setFont(f)
        step = 1 if self.pps >= 40 else (5 if self.pps >= 12 else 10)
        t = 0
        while self.x_for(t) < W:
            x = self.x_for(t)
            p.setPen(QColor('#454b55')); p.drawLine(x, 0, x, RULER_H)
            p.setPen(QColor('#9aa4b2'))
            p.drawText(x + 3, RULER_H - 7, f"{int(t)//60}:{int(t)%60:02d}")
            t += step
        # tracks
        for ti, tr in enumerate(tracks):
            r = self.track_rect(ti)
            p.fillRect(r, QColor('#23272e' if ti % 2 == 0 else '#20242b'))
            hdr = QRect(0, r.y(), HEADER_W, TRACK_H)
            p.fillRect(hdr, QColor('#2b3038'))
            p.setPen(QColor('#dfe4ea')); fb = QFont(); fb.setBold(True); fb.setPixelSize(12); p.setFont(fb)
            p.drawText(hdr.adjusted(8, 0, -4, -TRACK_H // 2), Qt.AlignVCenter | Qt.AlignLeft, tr['id'])
            p.setPen(QColor('#8891a0')); fn = QFont(); fn.setPixelSize(10); p.setFont(fn)
            p.drawText(hdr.adjusted(8, TRACK_H // 2 - 2, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, tr['name'])
            p.setPen(QColor('#14161a')); p.drawLine(0, r.bottom(), W, r.bottom())
            for c in tr['clips']:
                self._paint_clip(p, ti, c)
        # markers
        for mt in self.proj().get('markers', []):
            mx = self.x_for(mt)
            p.setPen(QPen(QColor('#4fc3f7'), 1, Qt.DashLine)); p.drawLine(mx, RULER_H, mx, self.height())
            p.setBrush(QColor('#4fc3f7')); p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF([QPointF(mx - 4, RULER_H), QPointF(mx + 4, RULER_H), QPointF(mx, RULER_H + 7)]))
        # playhead
        px = self.x_for(self.playhead)
        p.setPen(QPen(QColor('#ff5252'), 2)); p.drawLine(px, 0, px, self.height())
        p.setBrush(QColor('#ff5252')); p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygonF([QPointF(px - 5, 0), QPointF(px + 5, 0), QPointF(px, 8)]))

    def _paint_clip(self, p, ti, c):
        r = self.clip_rect(ti, c)
        col = QColor(CLIP_COLORS.get(c['kind'], '#555'))
        grad = QLinearGradient(r.topLeft(), r.bottomLeft())
        grad.setColorAt(0, col.lighter(120)); grad.setColorAt(1, col.darker(115))
        sel = self.sel and self.sel[0] == ti and self.sel[1] == c['id']
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor('#ffd166' if sel else '#11141a'), 2 if sel else 1))
        p.drawRoundedRect(r, 5, 5)
        # audio waveform (the portion of the source this clip plays)
        if c['kind'] == 'audio':
            img = self.main.waves.get(c['src'])
            if img:
                sd = max(0.01, float(c.get('src_dur') or c['dur']))
                sx0 = int(img.width() * min(1, c.get('in', 0) / sd))
                sx1 = int(img.width() * min(1, (c.get('in', 0) + c['dur']) / sd))
                if sx1 > sx0:
                    src = QRect(sx0, 0, sx1 - sx0, img.height())
                    p.setOpacity(0.55)
                    p.drawImage(r.adjusted(2, 2, -2, -2), img, src)
                    p.setOpacity(1.0)
        # transition marker (left edge)
        tr = c.get('transition') or {}
        if tr.get('type', 'none') != 'none':
            p.setBrush(QColor('#ffd166')); p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF([QPointF(r.left(), r.top()), QPointF(r.left() + 12, r.top()),
                                     QPointF(r.left(), r.bottom())]))
        # fades
        p.setPen(QPen(QColor('#ffffff'), 1))
        if c.get('fade_in', 0) > 0:
            fw = int(c['fade_in'] * self.pps)
            p.drawLine(r.left(), r.bottom(), r.left() + fw, r.top())
        if c.get('fade_out', 0) > 0:
            fw = int(c['fade_out'] * self.pps)
            p.drawLine(r.right() - fw, r.top(), r.right(), r.bottom())
        p.setPen(QColor('#ffffff')); f = QFont(); f.setPixelSize(11); p.setFont(f)
        label = c['text']['content'] if c['kind'] == 'text' and c.get('text') else c['name']
        p.setClipRect(r.adjusted(6, 0, -6, 0))
        p.drawText(r.adjusted(8, 0, -6, 0), Qt.AlignVCenter | Qt.AlignLeft,
                   QFontMetrics(f).elidedText(label, Qt.ElideRight, r.width() - 14))
        p.setClipping(False)
        # effect badges
        badges = []
        if c.get('kenburns'):
            badges.append('⤢')
        if c.get('chroma'):
            badges.append('◧')
        if c.get('pip'):
            badges.append('▣')
        if badges:
            p.setPen(QColor('#ffe9b0'))
            p.drawText(r.adjusted(0, 0, -6, -2), Qt.AlignRight | Qt.AlignBottom, ' '.join(badges))

    # -- interaction -----------------------------------------------------------
    EDGE = 7

    def mousePressEvent(self, ev):
        pos = ev.position().toPoint()
        if ev.button() == Qt.LeftButton and pos.y() < RULER_H:
            self.playhead = self.t_for(pos.x()); self.playheadMoved.emit(self.playhead); self.update(); return
        ti, c = self.clip_at(pos)
        if c is not None:
            self.sel = (ti, c['id']); self.selectionChanged.emit()
            r = self.clip_rect(ti, c)
            mode = 'move'
            if abs(pos.x() - r.left()) <= self.EDGE:
                mode = 'trim_l'
            elif abs(pos.x() - r.right()) <= self.EDGE:
                mode = 'trim_r'
            self._drag = {'ti': ti, 'cid': c['id'], 'mode': mode, 'x0': pos.x(),
                          'start0': c['start'], 'dur0': c['dur'], 'in0': c.get('in', 0)}
            if ev.button() == Qt.RightButton:
                self._drag = None
                self._context_menu(ti, c, ev.globalPosition().toPoint())
            self.update()
        else:
            if ev.button() == Qt.LeftButton:
                self.playhead = self.t_for(pos.x()); self.playheadMoved.emit(self.playhead)
            self.sel = None; self.selectionChanged.emit(); self.update()

    def mouseMoveEvent(self, ev):
        pos = ev.position().toPoint()
        if not self._drag:
            ti, c = self.clip_at(pos)
            cur = Qt.ArrowCursor
            if c is not None:
                r = self.clip_rect(ti, c)
                if abs(pos.x() - r.left()) <= self.EDGE or abs(pos.x() - r.right()) <= self.EDGE:
                    cur = Qt.SizeHorCursor
                else:
                    cur = Qt.OpenHandCursor
            self.setCursor(cur)
            return
        d = self._drag
        c = self.main.find_clip(d['ti'], d['cid'])
        if not c:
            return
        dt = (pos.x() - d['x0']) / self.pps
        snap = self._snap_times(d['cid'])
        if d['mode'] == 'move':
            ns = max(0.0, d['start0'] + dt)
            ns = self._apply_snap(ns, snap)
            c['start'] = ns
        elif d['mode'] == 'trim_l':
            maxd = d['dur0'] + d['start0']
            ns = max(0.0, min(d['start0'] + dt, d['start0'] + d['dur0'] - 0.1))
            delta = ns - d['start0']
            c['start'] = ns
            c['dur'] = max(0.1, d['dur0'] - delta)
            if c['kind'] in ('video', 'audio'):
                c['in'] = max(0.0, d['in0'] + delta)
        elif d['mode'] == 'trim_r':
            nd = max(0.1, d['dur0'] + dt)
            if c['kind'] in ('video', 'audio') and c.get('src_dur'):
                nd = min(nd, max(0.1, c['src_dur'] - c.get('in', 0)))
            nd = self._apply_snap(d['start0'] + nd, snap) - d['start0']
            c['dur'] = max(0.1, nd)
        self.updateGeometry(); self.update()

    def _snap_times(self, exclude_cid):
        pts = [0.0, self.playhead]
        for tr in self.proj()['tracks']:
            for c in tr['clips']:
                if c['id'] == exclude_cid:
                    continue
                pts.append(c['start']); pts.append(c['start'] + c['dur'])
        return pts

    def _apply_snap(self, t, pts, tol_px=8):
        tol = tol_px / self.pps
        best, bd = t, tol
        for p in pts:
            if abs(p - t) < bd:
                best, bd = p, abs(p - t)
        return best

    def mouseReleaseEvent(self, ev):
        if self._drag:
            self._drag = None
            self.clipsChanged.emit()
            self.main.push_undo()

    def _context_menu(self, ti, c, gpos):
        m = QMenu(self)
        m.addAction('Split at playhead', lambda: self.main.split_clip(ti, c['id']))
        m.addAction('Delete clip', lambda: self.main.delete_clip(ti, c['id']))
        m.addSeparator()
        if c['kind'] != 'text':
            tmenu = m.addMenu('Transition (into clip)')
            for name, label in TRANSITIONS:
                act = tmenu.addAction(label, lambda n=name: self.main.set_transition(ti, c['id'], n))
                act.setCheckable(True)
                act.setChecked((c.get('transition') or {}).get('type', 'none') == name)
        m.addAction('Properties…', lambda: self.main.edit_clip(ti, c['id']))
        if c['kind'] == 'text':
            m.addAction('Edit title…', lambda: self.main.edit_clip(ti, c['id']))
        if c['kind'] == 'image':
            kb = m.addAction('Ken Burns (pan & zoom)')
            kb.setCheckable(True); kb.setChecked(bool(c.get('kenburns')))
            kb.toggled.connect(lambda on: self.main.toggle_kenburns(ti, c['id'], on))
        m.exec(gpos)

    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self.sel:
            self.main.delete_clip(self.sel[0], self.sel[1])
        elif ev.key() == Qt.Key_S and self.sel:
            self.main.split_clip(self.sel[0], self.sel[1])
        else:
            super().keyPressEvent(ev)


# ===================================================================== clip properties dialog
class ClipDialog(QDialog):
    def __init__(self, clip, main, parent=None):
        super().__init__(parent)
        self.clip = clip
        self.main = main
        self.setWindowTitle(f"Clip — {clip['name']}")
        self.setMinimumWidth(400)
        outer = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
        inner = QWidget(); form = QFormLayout(inner); scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        if clip['kind'] == 'text':
            t = clip['text']
            self.content = QTextEdit(); self.content.setPlainText(t.get('content', '')); self.content.setFixedHeight(70)
            form.addRow('Text', self.content)
            self.size = QSpinBox(); self.size.setRange(8, 400); self.size.setValue(int(t.get('size', 64)))
            form.addRow('Font size', self.size)
            self.color = self._color_btn(t.get('color', '#ffffff'))
            form.addRow('Text colour', self.color)
            self.bg = self._color_btn(t.get('bg', '#000000'))
            form.addRow('Background', self.bg)
            self.halign = QComboBox(); self.halign.addItems(['left', 'center', 'right'])
            self.halign.setCurrentText(t.get('x', 'center'))
            form.addRow('Horizontal', self.halign)
            self.valign = QComboBox(); self.valign.addItems(['top', 'center', 'bottom'])
            self.valign.setCurrentText(t.get('y', 'center'))
            form.addRow('Vertical', self.valign)
            srow = QHBoxLayout()
            self.bold = QCheckBox('Bold'); self.bold.setChecked(bool(t.get('bold')))
            self.italic = QCheckBox('Italic'); self.italic.setChecked(bool(t.get('italic')))
            srow.addWidget(self.bold); srow.addWidget(self.italic); srow.addStretch(1)
            sw = QWidget(); sw.setLayout(srow); form.addRow('Style', sw)
            self.outline = QSpinBox(); self.outline.setRange(0, 12); self.outline.setValue(int(t.get('outline', 0)))
            self.outline.setSuffix(' px'); form.addRow('Outline', self.outline)
            self.box = QCheckBox('Draw a box behind the text'); self.box.setChecked(bool(t.get('box')))
            form.addRow('', self.box)
            self.tanim = QComboBox()
            for k, lbl in TEXT_ANIMS:
                self.tanim.addItem(lbl, k)
            ta = t.get('anim', 'none')
            self.tanim.setCurrentIndex(max(0, [k for k, _ in TEXT_ANIMS].index(ta) if ta in dict(TEXT_ANIMS) else 0))
            form.addRow('Animation', self.tanim)

        self.dur = QDoubleSpinBox(); self.dur.setRange(0.1, 3600); self.dur.setDecimals(2)
        self.dur.setValue(clip['dur']); self.dur.setSuffix(' s')
        form.addRow('Duration', self.dur)
        self.start = QDoubleSpinBox(); self.start.setRange(0, 36000); self.start.setDecimals(2)
        self.start.setValue(clip['start']); self.start.setSuffix(' s')
        form.addRow('Start time', self.start)

        if clip['kind'] == 'color':
            self.ccol = self._color_btn(clip.get('color', '#3366cc'))
            form.addRow('Colour', self.ccol)

        if clip['kind'] in ('video', 'audio'):
            self.vol = QDoubleSpinBox(); self.vol.setRange(0, 4); self.vol.setSingleStep(0.1)
            self.vol.setValue(clip.get('volume', 1.0))
            form.addRow('Volume ×', self.vol)
            self.pan = QDoubleSpinBox(); self.pan.setRange(-1, 1); self.pan.setSingleStep(0.1)
            self.pan.setValue(clip.get('pan', 0.0))
            form.addRow('Pan (L −1 … +1 R)', self.pan)
        if clip['kind'] in ('video', 'audio'):
            self.speed = QDoubleSpinBox(); self.speed.setRange(0.1, 10.0); self.speed.setSingleStep(0.25)
            self.speed.setValue(clip.get('speed', 1.0)); self.speed.setSuffix(' ×  (0.5 = slow-mo)')
            form.addRow('Speed', self.speed)

        if clip['kind'] in ('video', 'image', 'color'):
            self.effect = QComboBox()
            for k, lbl in EFFECT_LABELS:
                self.effect.addItem(lbl, k)
            cur = clip.get('effect', 'none')
            self.effect.setCurrentIndex(max(0, [k for k, _ in EFFECT_LABELS].index(cur) if cur in dict(EFFECT_LABELS) else 0))
            form.addRow('Effect', self.effect)
            adj = clip.get('adjust') or {}
            self.bright = QDoubleSpinBox(); self.bright.setRange(-1, 1); self.bright.setSingleStep(0.05); self.bright.setValue(adj.get('brightness', 0.0))
            self.contrast = QDoubleSpinBox(); self.contrast.setRange(0, 3); self.contrast.setSingleStep(0.1); self.contrast.setValue(adj.get('contrast', 1.0))
            self.satur = QDoubleSpinBox(); self.satur.setRange(0, 3); self.satur.setSingleStep(0.1); self.satur.setValue(adj.get('saturation', 1.0))
            form.addRow('Brightness', self.bright)
            form.addRow('Contrast', self.contrast)
            form.addRow('Saturation', self.satur)
            self.rotate = QDoubleSpinBox(); self.rotate.setRange(-180, 180); self.rotate.setValue(clip.get('rotate', 0.0)); self.rotate.setSuffix('°')
            form.addRow('Rotate', self.rotate)

        if clip['kind'] in ('video', 'image'):
            self.crop_on = QCheckBox('Crop this clip'); self.crop_on.setChecked(bool(clip.get('crop')))
            form.addRow('', self.crop_on)
            cr = clip.get('crop') or {'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0}
            self.crop_x = QDoubleSpinBox(); self.crop_x.setRange(0, 0.95); self.crop_x.setSingleStep(0.05); self.crop_x.setValue(cr.get('x', 0))
            self.crop_y = QDoubleSpinBox(); self.crop_y.setRange(0, 0.95); self.crop_y.setSingleStep(0.05); self.crop_y.setValue(cr.get('y', 0))
            self.crop_w = QDoubleSpinBox(); self.crop_w.setRange(0.05, 1.0); self.crop_w.setSingleStep(0.05); self.crop_w.setValue(cr.get('w', 1))
            self.crop_h = QDoubleSpinBox(); self.crop_h.setRange(0.05, 1.0); self.crop_h.setSingleStep(0.05); self.crop_h.setValue(cr.get('h', 1))
            form.addRow('Crop left / top', self._pair(self.crop_x, self.crop_y))
            form.addRow('Crop width / height', self._pair(self.crop_w, self.crop_h))
            tf = clip.get('transform') or {'scale': 1.0, 'x': 0.5, 'y': 0.5}
            self.tf_scale = QDoubleSpinBox(); self.tf_scale.setRange(0.1, 1.0); self.tf_scale.setSingleStep(0.05); self.tf_scale.setValue(tf.get('scale', 1.0))
            self.tf_x = QDoubleSpinBox(); self.tf_x.setRange(0, 1); self.tf_x.setSingleStep(0.1); self.tf_x.setValue(tf.get('x', 0.5))
            self.tf_y = QDoubleSpinBox(); self.tf_y.setRange(0, 1); self.tf_y.setSingleStep(0.1); self.tf_y.setValue(tf.get('y', 0.5))
            form.addRow('Shrink & place (size)', self.tf_scale)
            form.addRow('…position x / y', self._pair(self.tf_x, self.tf_y))

        if clip['kind'] == 'image':
            self.kb_on = QCheckBox('Pan & zoom (Ken Burns)'); self.kb_on.setChecked(bool(clip.get('kenburns')))
            form.addRow('', self.kb_on)
            self.kb_pan = QComboBox()
            for v in ('in', 'left', 'right', 'up', 'down'):
                self.kb_pan.addItem(v.capitalize(), v)
            self.kb_pan.setCurrentText((clip.get('kenburns') or {}).get('pan', 'in').capitalize())
            form.addRow('Pan direction', self.kb_pan)

        self.fi = QDoubleSpinBox(); self.fi.setRange(0, 30); self.fi.setSingleStep(0.25); self.fi.setValue(clip.get('fade_in', 0)); self.fi.setSuffix(' s')
        self.fo = QDoubleSpinBox(); self.fo.setRange(0, 30); self.fo.setSingleStep(0.25); self.fo.setValue(clip.get('fade_out', 0)); self.fo.setSuffix(' s')
        form.addRow('Fade in', self.fi)
        form.addRow('Fade out', self.fo)

        if clip['kind'] in ('video', 'image'):
            self.pip_on = QCheckBox('Picture-in-picture overlay (smaller, positioned)')
            self.pip_on.setChecked(bool(clip.get('pip')))
            form.addRow('', self.pip_on)
            pip = clip.get('pip') or {'scale': 0.4, 'x': 0.5, 'y': 0.5}
            self.pip_scale = QDoubleSpinBox(); self.pip_scale.setRange(0.1, 1.0); self.pip_scale.setSingleStep(0.05); self.pip_scale.setValue(pip.get('scale', 0.4))
            self.pip_x = QDoubleSpinBox(); self.pip_x.setRange(0, 1); self.pip_x.setSingleStep(0.1); self.pip_x.setValue(pip.get('x', 0.5))
            self.pip_y = QDoubleSpinBox(); self.pip_y.setRange(0, 1); self.pip_y.setSingleStep(0.1); self.pip_y.setValue(pip.get('y', 0.5))
            form.addRow('PiP size', self.pip_scale)
            form.addRow('PiP x (0–1)', self.pip_x)
            form.addRow('PiP y (0–1)', self.pip_y)
            self.chroma_on = QCheckBox('Chroma key (green/blue screen)')
            self.chroma_on.setChecked(bool(clip.get('chroma')))
            form.addRow('', self.chroma_on)
            self.chroma_col = self._color_btn((clip.get('chroma') or {}).get('color', '#00ff00'))
            form.addRow('Key colour', self.chroma_col)
            self.opacity = QDoubleSpinBox(); self.opacity.setRange(0.0, 1.0); self.opacity.setSingleStep(0.05)
            self.opacity.setValue(clip.get('opacity', 1.0))
            form.addRow('Opacity (overlay)', self.opacity)
            self.pipmove_on = QCheckBox('Animate PiP across the screen (move to…)')
            self.pipmove_on.setChecked(bool((clip.get('pip') or {}).get('to')))
            form.addRow('', self.pipmove_on)
            to = (clip.get('pip') or {}).get('to') or {'x': 0.5, 'y': 0.5}
            self.pip_tx = QDoubleSpinBox(); self.pip_tx.setRange(0, 1); self.pip_tx.setSingleStep(0.1); self.pip_tx.setValue(to.get('x', 0.5))
            self.pip_ty = QDoubleSpinBox(); self.pip_ty.setRange(0, 1); self.pip_ty.setSingleStep(0.1); self.pip_ty.setValue(to.get('y', 0.5))
            form.addRow('…end x / y', self._pair(self.pip_tx, self.pip_ty))
            self.blend = QComboBox()
            for m in BLEND_MODES:
                self.blend.addItem(m.capitalize(), m)
            self.blend.setCurrentText(clip.get('blend', 'normal').capitalize())
            form.addRow('Blend mode (overlay)', self.blend)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        outer.addWidget(bb)
        self.resize(430, min(680, 120 + form.rowCount() * 34))

    def _pair(self, a, b):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(a); h.addWidget(b); return w

    def _color_btn(self, initial):
        b = QPushButton(initial)
        b._color = initial
        b.setStyleSheet(f'background:{initial};')

        def pick():
            col = QColorDialog.getColor(QColor(b._color), self, 'Pick a colour')
            if col.isValid():
                b._color = col.name(); b.setText(col.name()); b.setStyleSheet(f'background:{col.name()}; color:{"#000" if col.lightness()>128 else "#fff"};')
        b.clicked.connect(pick)
        return b

    def apply(self):
        c = self.clip
        c['dur'] = self.dur.value(); c['start'] = self.start.value()
        c['fade_in'] = self.fi.value(); c['fade_out'] = self.fo.value()
        if c['kind'] in ('video', 'audio'):
            c['volume'] = self.vol.value(); c['pan'] = self.pan.value(); c['speed'] = self.speed.value()
        if c['kind'] == 'color':
            c['color'] = self.ccol._color; c['name'] = 'Colour'
        if c['kind'] in ('video', 'image', 'color'):
            c['effect'] = self.effect.currentData()
            c['adjust'] = {'brightness': self.bright.value(), 'contrast': self.contrast.value(),
                           'saturation': self.satur.value(), 'gamma': 1.0}
            c['rotate'] = self.rotate.value()
        if c['kind'] in ('video', 'image'):
            c['crop'] = ({'x': self.crop_x.value(), 'y': self.crop_y.value(),
                          'w': self.crop_w.value(), 'h': self.crop_h.value()}
                         if self.crop_on.isChecked() else None)
            c['transform'] = ({'scale': self.tf_scale.value(), 'x': self.tf_x.value(), 'y': self.tf_y.value()}
                              if (self.tf_scale.value() < 0.999 or self.tf_x.value() != 0.5 or self.tf_y.value() != 0.5)
                              else None)
        if c['kind'] == 'image':
            c['kenburns'] = {'zoom': 1.3, 'pan': self.kb_pan.currentData()} if self.kb_on.isChecked() else None
        if c['kind'] == 'text':
            t = c['text']
            t['content'] = self.content.toPlainText()
            t['size'] = self.size.value(); t['color'] = self.color._color; t['bg'] = self.bg._color
            t['x'] = self.halign.currentText(); t['y'] = self.valign.currentText(); t['box'] = self.box.isChecked()
            t['bold'] = self.bold.isChecked(); t['italic'] = self.italic.isChecked()
            t['outline'] = self.outline.value(); t['anim'] = self.tanim.currentData()
            c['name'] = t['content'][:24] or 'Title'
        if c['kind'] in ('video', 'image'):
            if self.pip_on.isChecked():
                c['pip'] = {'scale': self.pip_scale.value(), 'x': self.pip_x.value(), 'y': self.pip_y.value()}
                if self.pipmove_on.isChecked():
                    c['pip']['to'] = {'x': self.pip_tx.value(), 'y': self.pip_ty.value()}
            else:
                c['pip'] = None
            if self.chroma_on.isChecked():
                c['chroma'] = {'color': self.chroma_col._color, 'similarity': 0.25}
            else:
                c['chroma'] = None
            c['opacity'] = self.opacity.value()
            c['blend'] = self.blend.currentData()


# ===================================================================== main window
class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORG, 'MOVIEeditor')
        self.proj = default_project()
        self.path = None
        self._undo = []
        self._redo = []
        self.render_worker = None
        self.waves = {}   # src path -> QImage waveform (or False if none)
        self.setWindowTitle(APP)
        self.resize(1200, 760)

        self._build_media_dock()
        self._build_preview()
        self._build_timeline()
        self._build_actions()
        self.statusBar().showMessage('Ready — import clips from the Media bin, then drop them on the timeline.')
        self._refresh_title()
        QTimer.singleShot(0, self._check_ffmpeg)

    # -- UI construction -------------------------------------------------------
    def _build_preview(self):
        central = QWidget(); v = QVBoxLayout(central); v.setContentsMargins(6, 6, 6, 6)
        self.video = QVideoWidget(); self.video.setMinimumHeight(260)
        self.video.setStyleSheet('background:black;')
        self.player = QMediaPlayer(); self.audio_out = QAudioOutput()
        self.player.setAudioOutput(self.audio_out); self.player.setVideoOutput(self.video)
        self.still = QLabel('Preview'); self.still.setAlignment(Qt.AlignCenter)
        self.still.setStyleSheet('background:black; color:#667;'); self.still.setMinimumHeight(260)
        v.addWidget(self.video, 1); v.addWidget(self.still, 1)
        self.video.hide()
        # transport
        row = QHBoxLayout()
        self.play_btn = QPushButton(' Build & Play preview')
        self.play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_btn.clicked.connect(self.play_preview)
        self.stop_btn = QPushButton(); self.stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_btn.clicked.connect(self.stop_preview)
        self.time_lbl = QLabel('0:00 / 0:00')
        row.addWidget(self.play_btn); row.addWidget(self.stop_btn); row.addStretch(1); row.addWidget(self.time_lbl)
        v.addLayout(row)
        self.setCentralWidget(central)
        self.player.positionChanged.connect(self._on_pos)
        self.player.durationChanged.connect(lambda d: self._on_pos(self.player.position()))
        QTimer.singleShot(50, self.refresh_still)

    def _build_media_dock(self):
        dock = QDockWidget('Media bin', self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(6, 6, 6, 6)
        if os.path.isfile(BANNER_IMG):
            b = QLabel(); pm = QPixmap(BANNER_IMG)
            if not pm.isNull():
                b.setPixmap(pm.scaledToWidth(236, Qt.SmoothTransformation))
            v.addWidget(b)
        imp = QPushButton('Import media…'); imp.clicked.connect(self.import_media)
        v.addWidget(imp)
        self.media = QListWidget()
        self.media.setViewMode(QListWidget.IconMode)
        self.media.setIconSize(QSize(120, 72)); self.media.setResizeMode(QListWidget.Adjust)
        self.media.setSpacing(6); self.media.setMovement(QListWidget.Static)
        self.media.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.media.itemDoubleClicked.connect(lambda it: self.add_to_timeline(it))
        v.addWidget(self.media, 1)
        hint = QLabel('Double-click an item to add it to the timeline.\nVideo/photos → Video track, sound → Audio track.')
        hint.setWordWrap(True); hint.setStyleSheet('color:#889;'); v.addWidget(hint)
        addrow = QHBoxLayout()
        at = QPushButton('+ Add to timeline'); at.clicked.connect(lambda: self.add_to_timeline())
        tt = QPushButton('+ Title'); tt.clicked.connect(self.add_title)
        addrow.addWidget(at); addrow.addWidget(tt); v.addLayout(addrow)
        dock.setWidget(w)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self._media_items = {}  # row -> clip template dict

    def _build_timeline(self):
        dock = QDockWidget('Timeline', self)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        wrap = QWidget(); v = QVBoxLayout(wrap); v.setContentsMargins(4, 2, 4, 4); v.setSpacing(3)
        bar = QHBoxLayout()
        zin = QToolButton(); zin.setText('🔍+'); zin.clicked.connect(lambda: self.zoom(1.3))
        zout = QToolButton(); zout.setText('🔍−'); zout.clicked.connect(lambda: self.zoom(1/1.3))
        split = QPushButton('Split at playhead'); split.clicked.connect(self.split_at_playhead)
        dele = QPushButton('Delete clip'); dele.clicked.connect(self.delete_selected)
        props = QPushButton('Properties…'); props.clicked.connect(self.edit_selected)
        bar.addWidget(zin); bar.addWidget(zout); bar.addSpacing(10)
        bar.addWidget(split); bar.addWidget(dele); bar.addWidget(props); bar.addStretch(1)
        self.dur_lbl = QLabel('Movie length 0:00'); bar.addWidget(self.dur_lbl)
        v.addLayout(bar)
        self.timeline = Timeline(self)
        self.scroll = QScrollArea(); self.scroll.setWidget(self.timeline); self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        v.addWidget(self.scroll, 1)
        dock.setWidget(wrap)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        self.timeline.playheadMoved.connect(lambda t: self.refresh_still())
        self.timeline.clipsChanged.connect(self._clips_changed)
        self.timeline.selectionChanged.connect(lambda: None)

    def _build_actions(self):
        mb = self.menuBar()
        fm = mb.addMenu('&File')
        self._act(fm, 'New', self.new_project, QKeySequence.New)
        self._act(fm, 'Open…', self.open_project, QKeySequence.Open)
        self._act(fm, 'Save', self.save_project, QKeySequence.Save)
        self._act(fm, 'Save As…', self.save_project_as, QKeySequence('Ctrl+Shift+S'))
        fm.addSeparator()
        self._act(fm, 'Import media…', self.import_media, QKeySequence('Ctrl+I'))
        self._act(fm, 'Export movie (MP4)…', self.export_movie, QKeySequence('Ctrl+E'))
        fm.addSeparator()
        self._act(fm, 'Quit', self.close, QKeySequence.Quit)

        em = mb.addMenu('&Edit')
        self._act(em, 'Undo', self.undo, QKeySequence.Undo)
        self._act(em, 'Redo', self.redo, QKeySequence.Redo)
        em.addSeparator()
        self._act(em, 'Split at playhead', self.split_at_playhead, QKeySequence('Ctrl+K'))
        self._act(em, 'Delete clip', self.delete_selected, QKeySequence('Del'))
        self._act(em, 'Clip properties…', self.edit_selected)

        tm = mb.addMenu('&Timeline')
        self._act(tm, 'Add title…', self.add_title)
        self._act(tm, 'Add colour clip…', self.add_color_clip)
        self._act(tm, 'Record narration…', self.record_narration)
        self._act(tm, 'Add video/audio track', self.add_track)
        tm.addSeparator()
        self._act(tm, 'Add marker at playhead', self.add_marker, QKeySequence('M'))
        self._act(tm, 'Clear markers', self.clear_markers)
        tm.addSeparator()
        self._act(tm, 'Project settings…', self.project_settings)

        hm = mb.addMenu('&Help')
        self._act(hm, 'Quick Start', lambda: self._open_doc(QUICKSTART))
        self._act(hm, 'User Guide', lambda: self._open_doc(MANUAL))
        self._act(hm, f'About {APP}', self.about)

        tb = QToolBar('Main'); tb.setMovable(False); self.addToolBar(tb)
        tb.addAction(self._icon(QStyle.SP_FileIcon), 'New', self.new_project)
        tb.addAction(self._icon(QStyle.SP_DirOpenIcon), 'Open', self.open_project)
        tb.addAction(self._icon(QStyle.SP_DialogSaveButton), 'Save', self.save_project)
        tb.addSeparator()
        tb.addAction(self._icon(QStyle.SP_ArrowDown), 'Import media', self.import_media)
        tb.addAction(self._icon(QStyle.SP_DialogYesButton), 'Export MP4', self.export_movie)

    def _act(self, menu, text, slot, shortcut=None):
        a = QAction(text, self); a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(shortcut)
        menu.addAction(a); return a

    def _icon(self, sp):
        return self.style().standardIcon(sp)

    def _check_ffmpeg(self):
        if not FFMPEG or not FFPROBE:
            QMessageBox.warning(self, 'ffmpeg needed',
                                'just a... MOVIEeditor renders video with <b>ffmpeg</b>, which was not '
                                'found on your system.<br><br>Install it and reopen the app:<br>'
                                '• Arch/CachyOS: <code>sudo pacman -S ffmpeg</code><br>'
                                '• Debian/Mint/Ubuntu: <code>sudo apt install ffmpeg</code><br>'
                                '• Fedora: <code>sudo dnf install ffmpeg</code>')

    # -- media bin -------------------------------------------------------------
    def import_media(self):
        pats = ('Media (*.mp4 *.mov *.avi *.mkv *.webm *.wmv *.m4v *.mpg *.mpeg *.png *.jpg *.jpeg '
                '*.bmp *.gif *.webp *.mp3 *.wav *.aac *.m4a *.ogg *.flac);;All files (*)')
        start = self.settings.value('last_import', os.path.expanduser('~'))
        paths, _ = QFileDialog.getOpenFileNames(self, 'Import media', start, pats)
        if not paths:
            return
        self.settings.setValue('last_import', os.path.dirname(paths[0]))
        self._add_media_paths(paths)

    def _add_media_paths(self, paths):
        self.statusBar().showMessage('Reading media…'); QApplication.processEvents()
        thumbdir = os.path.join(tempfile.gettempdir(), 'justmovie_thumbs')
        os.makedirs(thumbdir, exist_ok=True)
        for p in paths:
            kind = kind_for_path(p)
            if not kind:
                continue
            info = ffprobe_info(p)
            it = QListWidgetItem(os.path.basename(p))
            dur = info['duration']
            it.setToolTip(f"{p}\n{kind}, {dur:.1f}s")
            th = os.path.join(thumbdir, uuid.uuid4().hex[:10] + '.png')
            if kind == 'audio' or not make_thumbnail(p, kind, th):
                icons = {'audio': QStyle.SP_MediaVolume, 'video': QStyle.SP_MediaPlay, 'image': QStyle.SP_FileIcon}
                it.setIcon(self._icon(icons.get(kind, QStyle.SP_FileIcon)))
            else:
                it.setIcon(QIcon(th))
            it.setData(Qt.UserRole, {'src': p, 'kind': kind, 'info': info})
            self.media.addItem(it)
        self.statusBar().showMessage('Media imported.', 3000)

    def add_title(self):
        c = new_clip(None, 'text')
        c['start'] = round(self.timeline.playhead, 2)
        # titles go on the overlay track if present, else the video track
        ti = self._track_index('V2')
        if ti is None:
            ti = self._first_video_track()
        self.proj['tracks'][ti]['clips'].append(c)
        self.timeline.sel = (ti, c['id'])
        self._clips_changed(); self.push_undo()
        self.edit_clip(ti, c['id'])

    def add_color_clip(self):
        col = QColorDialog.getColor(QColor('#3366cc'), self, 'Colour clip')
        if not col.isValid():
            return
        c = new_clip(None, 'color'); c['color'] = col.name(); c['name'] = 'Colour'
        c['dur'] = DEFAULT_TITLE_DUR; c['src_dur'] = DEFAULT_TITLE_DUR
        ti = self._track_index('V1')
        if ti is None:
            ti = self._first_video_track()
        track = self.proj['tracks'][ti]
        c['start'] = round(max([cc['start'] + cc['dur'] for cc in track['clips']], default=0.0), 2)
        track['clips'].append(c)
        self.timeline.sel = (ti, c['id'])
        self._clips_changed(); self.push_undo()

    def record_narration(self):
        """Record a voice-over from the microphone (ffmpeg → PulseAudio/PipeWire) and
        drop it on the audio track at the playhead."""
        if not FFMPEG:
            QMessageBox.warning(self, 'Narration', 'Recording needs ffmpeg, which was not found.')
            return
        import time as _t
        outdir = os.path.join(_just_dir('pics'), 'narration'); os.makedirs(outdir, exist_ok=True)
        out = os.path.join(outdir, 'narration-' + _t.strftime('%Y%m%d-%H%M%S') + '.wav')
        try:
            proc = subprocess.Popen([FFMPEG, '-y', '-hide_banner', '-loglevel', 'error',
                                     '-f', 'pulse', '-i', 'default', '-ac', '2', '-ar', '48000', out],
                                    stdin=subprocess.PIPE)
        except Exception as e:
            QMessageBox.warning(self, 'Microphone', f'Could not start recording:\n{e}')
            return
        dlg = QDialog(self); dlg.setWindowTitle('Record narration'); dlg.setMinimumWidth(300)
        v = QVBoxLayout(dlg)
        lbl = QLabel('●  Recording — speak now.'); lbl.setStyleSheet('color:#e04b4b;font-weight:bold')
        elapsed = QLabel('0.0 s')
        btn = QPushButton('Stop && add to timeline')
        v.addWidget(lbl); v.addWidget(elapsed); v.addWidget(btn)
        self._rec_secs = 0.0
        timer = QTimer(dlg)
        timer.timeout.connect(lambda: (setattr(self, '_rec_secs', self._rec_secs + 0.1),
                                       elapsed.setText(f'{self._rec_secs:.1f} s')))
        timer.start(100)

        def stop():
            timer.stop()
            try:
                proc.stdin.write(b'q'); proc.stdin.flush()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.terminate()
            dlg.accept()
        btn.clicked.connect(stop)
        dlg.finished.connect(lambda _: stop() if proc.poll() is None else None)
        dlg.exec()
        if os.path.isfile(out) and os.path.getsize(out) > 2000:
            info = ffprobe_info(out)
            c = new_clip(out, 'audio', info); c['start'] = round(self.timeline.playhead, 2)
            ti = self._track_index('A1')
            ti = self._first_audio_track() if ti is None else ti
            self.proj['tracks'][ti]['clips'].append(c)
            self._add_media_paths([out])
            _justapps_recent('movie', out)
            self._clips_changed(); self.push_undo()
            self.statusBar().showMessage(f'Narration recorded ({info["duration"]:.1f}s) and added.', 5000)
        else:
            QMessageBox.warning(self, 'Narration',
                                'No audio was captured. Check that a microphone is connected and '
                                'that PulseAudio/PipeWire is running.')

    def add_marker(self):
        self.proj.setdefault('markers', [])
        t = round(self.timeline.playhead, 2)
        if t not in self.proj['markers']:
            self.proj['markers'].append(t); self.proj['markers'].sort()
            self._clips_changed(); self.push_undo()

    def clear_markers(self):
        self.proj['markers'] = []
        self._clips_changed(); self.push_undo()

    def add_to_timeline(self, item=None):
        items = [item] if item else self.media.selectedItems()
        if not items:
            QMessageBox.information(self, 'Add to timeline', 'Select one or more items in the Media bin first.')
            return
        for it in items:
            data = it.data(Qt.UserRole)
            if not data:
                continue
            kind = data['kind']
            c = new_clip(data['src'], kind, data['info'])
            if kind == 'audio':
                ti = self._track_index('A1') or self._first_audio_track()
            else:
                ti = self._track_index('V1')
                if ti is None:
                    ti = self._first_video_track()
            track = self.proj['tracks'][ti]
            # place after the last clip on that track
            end = max([cc['start'] + cc['dur'] for cc in track['clips']], default=0.0)
            c['start'] = round(end, 2)
            track['clips'].append(c)
            self.timeline.sel = (ti, c['id'])
        self._clips_changed(); self.push_undo()

    # -- track/clip lookup -----------------------------------------------------
    def _track_index(self, tid):
        for i, t in enumerate(self.proj['tracks']):
            if t['id'] == tid:
                return i
        return None

    def _first_video_track(self):
        for i, t in enumerate(self.proj['tracks']):
            if t['kind'] == 'video':
                return i
        return 0

    def _first_audio_track(self):
        for i, t in enumerate(self.proj['tracks']):
            if t['kind'] == 'audio':
                return i
        # none: make one
        self.proj['tracks'].append({'id': 'A1', 'kind': 'audio', 'name': 'Audio', 'clips': []})
        return len(self.proj['tracks']) - 1

    def find_clip(self, ti, cid):
        if ti < 0 or ti >= len(self.proj['tracks']):
            return None
        for c in self.proj['tracks'][ti]['clips']:
            if c['id'] == cid:
                return c
        return None

    # -- clip operations -------------------------------------------------------
    def split_at_playhead(self):
        if not self.timeline.sel:
            QMessageBox.information(self, 'Split', 'Select a clip first, then split it at the playhead.')
            return
        self.split_clip(*self.timeline.sel)

    def split_clip(self, ti, cid):
        c = self.find_clip(ti, cid)
        if not c:
            return
        t = self.timeline.playhead
        if not (c['start'] + 0.1 < t < c['start'] + c['dur'] - 0.1):
            self.statusBar().showMessage('Move the playhead inside the clip to split it.', 3000)
            return
        off = t - c['start']
        import copy as _copy
        c2 = _copy.deepcopy(c); c2['id'] = uuid.uuid4().hex[:8]
        right_dur = c['dur'] - off
        c['dur'] = off
        c['fade_out'] = 0.0
        c2['start'] = t
        c2['dur'] = right_dur
        c2['fade_in'] = 0.0
        c2['transition'] = {'type': 'none', 'dur': 1.0}
        if c2['kind'] in ('video', 'audio'):
            c2['in'] = c.get('in', 0) + off
        self.proj['tracks'][ti]['clips'].append(c2)
        self._clips_changed(); self.push_undo()

    def delete_selected(self):
        if self.timeline.sel:
            self.delete_clip(*self.timeline.sel)

    def delete_clip(self, ti, cid):
        t = self.proj['tracks'][ti]
        t['clips'] = [c for c in t['clips'] if c['id'] != cid]
        self.timeline.sel = None
        self._clips_changed(); self.push_undo()

    def set_transition(self, ti, cid, ttype):
        c = self.find_clip(ti, cid)
        if c:
            c.setdefault('transition', {'dur': 1.0})['type'] = ttype
            self._clips_changed(); self.push_undo()

    def toggle_kenburns(self, ti, cid, on):
        c = self.find_clip(ti, cid)
        if c:
            c['kenburns'] = {'zoom': 1.3} if on else None
            self._clips_changed(); self.push_undo()

    def edit_selected(self):
        if self.timeline.sel:
            self.edit_clip(*self.timeline.sel)

    def edit_clip(self, ti, cid):
        c = self.find_clip(ti, cid)
        if not c:
            return
        dlg = ClipDialog(c, self, self)
        if dlg.exec() == QDialog.Accepted:
            dlg.apply()
            self._clips_changed(); self.push_undo()

    def add_track(self):
        kinds = ['Video track', 'Audio track']
        from PySide6.QtWidgets import QInputDialog
        choice, ok = QInputDialog.getItem(self, 'Add track', 'Type:', kinds, 0, False)
        if not ok:
            return
        kind = 'video' if choice.startswith('Video') else 'audio'
        prefix = 'V' if kind == 'video' else 'A'
        n = sum(1 for t in self.proj['tracks'] if t['kind'] == kind) + 1
        tid = f'{prefix}{n}'
        tr = {'id': tid, 'kind': kind, 'name': 'Video' if kind == 'video' else 'Audio', 'clips': []}
        # video tracks on top, audio at the bottom
        if kind == 'video':
            self.proj['tracks'].insert(0, tr)
        else:
            self.proj['tracks'].append(tr)
        self._clips_changed(); self.push_undo()

    def project_settings(self):
        dlg = QDialog(self); dlg.setWindowTitle('Project settings')
        form = QFormLayout(dlg)
        res = QComboBox(); presets = [('1920×1080 (Full HD)', 1920, 1080), ('1280×720 (HD)', 1280, 720),
                                      ('854×480 (SD)', 854, 480), ('640×480 (4:3)', 640, 480)]
        for lbl, w, h in presets:
            res.addItem(lbl, (w, h))
        cur = (self.proj['width'], self.proj['height'])
        for i, (_, w, h) in enumerate(presets):
            if (w, h) == cur:
                res.setCurrentIndex(i)
        form.addRow('Resolution', res)
        fps = QComboBox(); [fps.addItem(str(f), f) for f in (24, 25, 30, 60)]
        fps.setCurrentText(str(self.proj['fps']))
        form.addRow('Frame rate', fps)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); form.addRow(bb)
        if dlg.exec() == QDialog.Accepted:
            w, h = res.currentData(); self.proj['width'] = w; self.proj['height'] = h
            self.proj['fps'] = fps.currentData()
            self.refresh_still(); self.push_undo()

    # -- undo/redo (whole-project snapshots) -----------------------------------
    def push_undo(self):
        import copy as _copy
        self._undo.append(_copy.deepcopy(self.proj))
        self._undo = self._undo[-40:]
        self._redo.clear()
        self._refresh_title()

    def undo(self):
        import copy as _copy
        if len(self._undo) < 1:
            return
        self._redo.append(_copy.deepcopy(self.proj))
        self.proj = self._undo.pop()
        self.timeline.sel = None
        self._clips_changed(refresh_only=True)

    def redo(self):
        import copy as _copy
        if not self._redo:
            return
        self._undo.append(_copy.deepcopy(self.proj))
        self.proj = self._redo.pop()
        self._clips_changed(refresh_only=True)

    # -- view refresh ----------------------------------------------------------
    def _clips_changed(self, refresh_only=False):
        self.timeline.updateGeometry(); self.timeline.update()
        d = project_duration(self.proj)
        self.dur_lbl.setText(f'Movie length {int(d)//60}:{int(d)%60:02d}')
        self.refresh_still()
        QTimer.singleShot(0, self._gen_waves)

    def _gen_waves(self):
        """Lazily render a waveform image per audio source for the timeline to paint."""
        if not FFMPEG:
            return
        made = False
        cache = os.path.join(tempfile.gettempdir(), 'justmovie_waves'); os.makedirs(cache, exist_ok=True)
        for tr in self.proj['tracks']:
            for c in tr['clips']:
                if c['kind'] != 'audio' or c['src'] in self.waves:
                    continue
                dst = os.path.join(cache, f"{abs(hash(c['src']))%999999}.png")
                try:
                    if not os.path.isfile(dst):
                        subprocess.run([FFMPEG, '-y', '-hide_banner', '-loglevel', 'error', '-i', c['src'],
                                        '-filter_complex',
                                        'showwavespic=s=1400x120:colors=0x8fe3c8|0x8fe3c8',
                                        '-frames:v', '1', dst], capture_output=True, timeout=30)
                    img = QImage(dst)
                    self.waves[c['src']] = img if not img.isNull() else False
                    made = made or not img.isNull()
                except Exception:
                    self.waves[c['src']] = False
        if made:
            self.timeline.update()

    def zoom(self, factor):
        self.timeline.pps = max(8, min(400, self.timeline.pps * factor))
        self.timeline.updateGeometry(); self.timeline.update()

    def _clips_at_time(self, t):
        hits = []
        for ti, tr in enumerate(self.proj['tracks']):
            if tr['kind'] != 'video':
                continue
            for c in tr['clips']:
                if c['start'] <= t < c['start'] + c['dur']:
                    hits.append((ti, c))
        return hits

    def refresh_still(self):
        """Render a representative still frame for the current playhead into the preview."""
        if self.video.isVisible():
            return
        W, H = 480, 270
        img = QImage(W, H, QImage.Format_RGB32); img.fill(QColor('#000'))
        p = QPainter(img)
        t = self.timeline.playhead
        hits = self._clips_at_time(t)
        base = next((c for ti, c in hits if c['kind'] in ('video', 'image', 'color')), None)
        if base is not None and base['kind'] == 'color':
            p.fillRect(0, 0, W, H, QColor(base.get('color', '#3366cc')))
        elif base is not None:
            frame = self._frame_pixmap(base, t - base['start'], W, H)
            if frame is not None:
                p.drawPixmap(0, 0, frame)
        # draw title text clips
        for ti, c in hits:
            if c['kind'] == 'text':
                self._paint_title(p, c['text'], W, H)
        p.setPen(QColor('#445')); p.drawRect(0, 0, W - 1, H - 1)
        p.end()
        self.still.setPixmap(QPixmap.fromImage(img))

    def _frame_pixmap(self, clip, offset, W, H):
        if clip['kind'] == 'image':
            pm = QPixmap(clip['src'])
            if pm.isNull():
                return None
            return pm.scaled(W, H, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if clip['kind'] == 'video' and FFMPEG:
            cache = os.path.join(tempfile.gettempdir(), 'justmovie_frames')
            os.makedirs(cache, exist_ok=True)
            ts = clip.get('in', 0) + max(0, offset)
            key = f"{abs(hash(clip['src']))%99999}_{int(ts*4)}.jpg"
            dst = os.path.join(cache, key)
            if not os.path.isfile(dst):
                try:
                    subprocess.run([FFMPEG, '-y', '-hide_banner', '-loglevel', 'error', '-ss', f'{ts:.2f}',
                                    '-i', clip['src'], '-frames:v', '1', '-vf', f'scale={W}:-1', dst],
                                   capture_output=True, timeout=15)
                except Exception:
                    return None
            pm = QPixmap(dst)
            return None if pm.isNull() else pm.scaled(W, H, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return None

    def _paint_title(self, p, txt, W, H):
        f = QFont(); f.setPixelSize(max(8, int(txt.get('size', 64) * H / self.proj['height'])))
        f.setBold(True); p.setFont(f)
        p.setPen(QColor(txt.get('color', '#ffffff')))
        flags = {'left': Qt.AlignLeft, 'center': Qt.AlignHCenter, 'right': Qt.AlignRight}.get(txt.get('x'), Qt.AlignHCenter)
        flags |= {'top': Qt.AlignTop, 'center': Qt.AlignVCenter, 'bottom': Qt.AlignBottom}.get(txt.get('y'), Qt.AlignVCenter)
        p.drawText(QRect(10, 10, W - 20, H - 20), flags | Qt.TextWordWrap, txt.get('content', ''))

    # -- preview playback ------------------------------------------------------
    def play_preview(self):
        if project_duration(self.proj) < 0.1:
            QMessageBox.information(self, 'Preview', 'Add some clips to the timeline first.')
            return
        out = os.path.join(tempfile.gettempdir(), 'justmovie_preview.mp4')
        self._render_to(out, preview=True, then=self._start_player)

    def _start_player(self, ok, path):
        if not ok:
            QMessageBox.warning(self, 'Preview failed', path)
            return
        self.still.hide(); self.video.show()
        self.player.setSource(QUrl.fromLocalFile(path)); self.player.play()

    def stop_preview(self):
        self.player.stop(); self.video.hide(); self.still.show(); self.refresh_still()

    def _on_pos(self, pos):
        dur = self.player.duration()
        self.time_lbl.setText(f'{pos//60000}:{(pos//1000)%60:02d} / {dur//60000}:{(dur//1000)%60:02d}')

    # -- export ----------------------------------------------------------------
    def export_movie(self):
        if project_duration(self.proj) < 0.1:
            QMessageBox.information(self, 'Export', 'Add some clips to the timeline first.')
            return
        # export options: resolution + quality preset (YouTube/disc-style sizes)
        dlg = QDialog(self); dlg.setWindowTitle('Export movie'); form = QFormLayout(dlg)
        res = QComboBox()
        res.addItem('Full HD — 1080p', 1080); res.addItem('HD — 720p (YouTube/web)', 720)
        res.addItem('SD — 480p (small file)', 480); res.addItem('Match project', self.proj['height'])
        res.setCurrentIndex(1)
        form.addRow('Size', res)
        qual = QComboBox()
        qual.addItem('Best quality (larger file)', 18); qual.addItem('Good (recommended)', 20)
        qual.addItem('Smaller file', 24); qual.setCurrentIndex(1)
        form.addRow('Quality', qual)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept); bb.rejected.connect(dlg.reject); form.addRow(bb)
        if dlg.exec() != QDialog.Accepted:
            return
        out_h, crf = res.currentData(), qual.currentData()
        base = os.path.splitext(os.path.basename(self.path))[0] if self.path else 'movie'
        start = os.path.join(_just_dir('pics'), base + '.mp4')
        path, _ = QFileDialog.getSaveFileName(self, 'Export movie', start, 'MP4 video (*.mp4)')
        if not path:
            return
        if not path.lower().endswith('.mp4'):
            path += '.mp4'
        self._render_to(path, preview=False, then=self._export_done, out_h=out_h, crf=crf)

    def _export_done(self, ok, path):
        if ok:
            _justapps_recent('movie', path)
            self.statusBar().showMessage(f'Exported {path}', 6000)
            QMessageBox.information(self, 'Export complete', f'Your movie was saved to:\n{path}')
        else:
            QMessageBox.warning(self, 'Export failed', path)

    def _render_to(self, out, preview, then, out_h=None, crf=20):
        if self.render_worker and self.render_worker.isRunning():
            QMessageBox.information(self, 'Busy', 'A render is already in progress.')
            return
        self.player.stop()
        dlg = QProgressDialog('Rendering…', 'Cancel', 0, 100, self)
        dlg.setWindowTitle('Rendering' if not preview else 'Building preview')
        dlg.setWindowModality(Qt.WindowModal); dlg.setMinimumDuration(0); dlg.setValue(0)
        w = RenderWorker(self.proj, out, preview=preview, out_h=out_h, crf=crf)
        self.render_worker = w
        w.progress.connect(lambda pct, msg: (dlg.setValue(pct), dlg.setLabelText(msg)))
        dlg.canceled.connect(w.cancel)

        def finish(ok, res):
            dlg.reset()
            then(ok, res)
        w.done.connect(finish)
        w.start()

    # -- project IO ------------------------------------------------------------
    def new_project(self):
        self.proj = default_project(); self.path = None; self.timeline.sel = None
        self._undo.clear(); self._redo.clear()
        self._clips_changed(); self._refresh_title()

    def open_project(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, 'Open project', _just_dir('docs'),
                                                  f'MOVIEeditor projects (*{EXT});;All files (*)')
        if not path:
            return
        self._open_path(path)

    def _open_path(self, path):
        try:
            with open(path) as fh:
                data = json.load(fh)
            if data.get('format') != FMT:
                raise ValueError('Not a MOVIEeditor project file.')
            self.proj = data; self.path = path; self.timeline.sel = None
            self._undo.clear(); self._redo.clear()
            self._clips_changed(); self._refresh_title()
            _justapps_recent('movie', path)
            self.statusBar().showMessage(f'Opened {path}', 4000)
        except Exception as e:
            QMessageBox.warning(self, 'Open failed', str(e))

    def save_project(self):
        if not self.path:
            return self.save_project_as()
        self._write(self.path)

    def save_project_as(self):
        start = self.path or os.path.join(_just_dir('docs'), 'movie' + EXT)
        path, _ = QFileDialog.getSaveFileName(self, 'Save project', start,
                                              f'MOVIEeditor projects (*{EXT})')
        if not path:
            return
        if not path.endswith(EXT):
            path += EXT
        self.path = path; self._write(path)

    def _write(self, path):
        self.proj['version'] = VERSION
        try:
            with open(path, 'w') as fh:
                json.dump(self.proj, fh, indent=1)
            _justapps_recent('movie', path)
            self._refresh_title()
            self.statusBar().showMessage(f'Saved {path}', 4000)
        except Exception as e:
            QMessageBox.warning(self, 'Save failed', str(e))

    def _refresh_title(self):
        name = os.path.basename(self.path) if self.path else 'Untitled'
        self.setWindowTitle(f'{name} — {APP}')

    def _open_doc(self, path):
        if os.path.isfile(path):
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.information(self, 'Not installed', 'The documentation was not installed with the app.')

    def startup_wizard(self):
        dlg = QDialog(self); dlg.setWindowTitle('Welcome to MOVIEeditor')
        dlg.setMinimumWidth(420)
        v = QVBoxLayout(dlg)
        if os.path.isfile(BANNER_IMG):
            lb = QLabel(); pm = QPixmap(BANNER_IMG)
            if not pm.isNull():
                lb.setPixmap(pm.scaledToWidth(360, Qt.SmoothTransformation))
            v.addWidget(lb, 0, Qt.AlignCenter)
        v.addWidget(QLabel('<b>Start a new movie</b> — pick a size, or open a project you saved earlier.'))
        form = QFormLayout(); v.addLayout(form)
        res = QComboBox()
        for lbl, w, h in [('1920×1080 (Full HD)', 1920, 1080), ('1280×720 (HD)', 1280, 720),
                          ('854×480 (SD)', 854, 480), ('640×480 (4:3)', 640, 480)]:
            res.addItem(lbl, (w, h))
        res.setCurrentIndex(1)
        form.addRow('Project size', res)
        fps = QComboBox(); [fps.addItem(str(f), f) for f in (24, 25, 30, 60)]; fps.setCurrentText('30')
        form.addRow('Frame rate', fps)
        row = QHBoxLayout()
        newb = QPushButton('Start new movie'); openb = QPushButton('Open a project…')
        row.addWidget(openb); row.addStretch(1); row.addWidget(newb); v.addLayout(row)
        result = {'action': None}
        newb.clicked.connect(lambda: (result.update(action='new'), dlg.accept()))
        openb.clicked.connect(lambda: (result.update(action='open'), dlg.accept()))
        dlg.exec()
        if result['action'] == 'open':
            self.open_project()
        elif result['action'] == 'new':
            w, h = res.currentData()
            self.proj['width'], self.proj['height'], self.proj['fps'] = w, h, fps.currentData()
            self._clips_changed()

    def about(self):
        QMessageBox.about(self, f'About {APP}',
                          f'<b>{APP}</b><br>Version {VERSION}<br><br>'
                          'A clean-room home-video editor inspired by Serif MoviePlus X6.<br>'
                          'Timeline editing, transitions, titles, picture-in-picture, chroma key '
                          'and MP4 export — rendered with ffmpeg.<br><br>'
                          'Part of the just a... CREATORsuite.')


def main():
    QApplication.setDesktopFileName('movie')
    app = QApplication(sys.argv)
    app.setApplicationName('MOVIEeditor'); app.setApplicationDisplayName(APP)
    app.setOrganizationName(ORG); app.setApplicationVersion(VERSION)
    app.setWindowIcon(QIcon.fromTheme('movie'))
    w = Main(); w.show()
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if args and os.path.isfile(args[0]):
        p = args[0]
        if p.lower().endswith(EXT):
            QTimer.singleShot(0, lambda: w._open_path(p))
        elif kind_for_path(p):
            QTimer.singleShot(0, lambda: w._add_media_paths([p]))
    else:
        QTimer.singleShot(0, w.startup_wizard)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
