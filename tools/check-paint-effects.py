#!/usr/bin/env python3
"""Headless verification for the PAINTcanvas Effects studio (v1.15).

Runs under QT_QPA_PLATFORM=offscreen. For a synthetic RGBA image with a non-trivial
alpha shape it exercises EACH effect's module-level core function, asserting it returns
an HxWx4 uint8 ndarray of the expected size without raising — once with OpenCV present
(if installed) and once with the cv2 fast path forced to its NumPy/PIL fallback. It also
checks every effect dialog class exists, and that the procedural textures are
seed-deterministic (same seed → identical, different seeds → different).

Usage:
    QT_QPA_PLATFORM=offscreen python3 tools/check-paint-effects.py
"""
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "paint"))

import numpy as np
import paint as P

FAIL = []


def ok(msg):
    print("  PASS", msg)


def check(cond, msg):
    if cond:
        ok(msg)
    else:
        print("  FAIL", msg)
        FAIL.append(msg)


def synth_rgba(h=96, w=120):
    """A non-trivial alpha shape (a rounded star-ish blob) over a coloured fill."""
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2.0, h / 2.0
    r = np.sqrt(((xx - cx) / (w * 0.42)) ** 2 + ((yy - cy) / (h * 0.42)) ** 2)
    ang = np.arctan2(yy - cy, xx - cx)
    edge = 0.7 + 0.25 * np.cos(ang * 5)              # 5-point lobed edge
    alpha = np.where(r < edge, 255, 0).astype(np.uint8)
    rgb = np.dstack([
        (120 + 80 * np.sin(xx / 15.0)).astype(np.uint8),
        (110 + 70 * np.cos(yy / 17.0)).astype(np.uint8),
        np.full((h, w), 90, np.uint8),
    ])
    return np.dstack([rgb, alpha]).astype(np.uint8)


def main():
    print(f"PAINTcanvas Effects headless check — VERSION {P.VERSION}")
    print(f"HAS_CV2 = {P.HAS_CV2}  (fast path {'available' if P.HAS_CV2 else 'absent'})")
    img = synth_rgba()
    h, w = img.shape[:2]

    print("\n[1] Edge/shape + distortion core functions (cv2 path AND forced fallback):")
    # (name, callable, kwargs) — all take an RGBA ndarray and accept force_fallback
    rgba_effects = [
        ("Bevel",         P.bevel,          dict(width=10, smoothness=2, profile='round', intensity=0.7)),
        ("Chrome",        P.chrome,         dict(ramp='sky', width=12, contrast=0.6, shine=0.7)),
        ("Glass",         P.glass,          dict(width=10, refraction=6.0, opacity=0.8)),
        ("Gradient Glow", P.gradient_glow,  dict(width=16, softness=0.6, opacity=0.85)),
        ("Motion Trail",  P.motion_trail,   dict(angle=30, length=24, echoes=8, falloff=0.7)),
        ("Twirl",         P.twirl,          dict(angle=120, radius=40, falloff=1.0)),
    ]
    for name, fn, kw in rgba_effects:
        for label, ff in (("cv2", False), ("fallback", True)):
            try:
                out = fn(img, force_fallback=ff, **kw)
                good = (isinstance(out, np.ndarray) and out.shape == (h, w, 4)
                        and out.dtype == np.uint8)
                check(good, f"{name} [{label}] -> {getattr(out, 'shape', '?')} {getattr(out, 'dtype', '?')}")
            except Exception as e:
                check(False, f"{name} [{label}] raised {e!r}")

    # Bevel profiles (exercise each branch of the height field)
    for prof in ('round', 'flat', 'button'):
        try:
            out = P.bevel(img, width=8, profile=prof)
            check(out.shape == (h, w, 4) and out.dtype == np.uint8, f"Bevel profile '{prof}'")
        except Exception as e:
            check(False, f"Bevel profile '{prof}' raised {e!r}")

    # Also a 3-channel (no-alpha) input must be accepted and promoted
    rgb3 = img[..., :3]
    try:
        out = P.bevel(rgb3, width=8)
        check(out.shape == (h, w, 4) and out.dtype == np.uint8, "Bevel accepts HxWx3 input")
    except Exception as e:
        check(False, f"Bevel on HxWx3 raised {e!r}")

    print("\n[2] Procedural texture core functions (size + dtype + seed determinism):")
    tex_effects = [
        ("Wood",   lambda s: P.wood(h, w, spacing=16, turb=0.5, angle=20, seed=s)),
        ("Marble", lambda s: P.marble(h, w, scale=38, turb=0.6, sharpness=4.0, seed=s)),
        ("Weave",  lambda s: P.weave(h, w, strand=12, gap=3, seed=s)),
    ]
    for name, fn in tex_effects:
        try:
            a = fn(7); b = fn(7); c = fn(42)
            shape_ok = a.shape == (h, w, 4) and a.dtype == np.uint8
            check(shape_ok, f"{name} -> {a.shape} {a.dtype}")
            check(np.array_equal(a, b), f"{name} same seed -> identical output")
            check(not np.array_equal(a, c), f"{name} different seeds -> different output")
        except Exception as e:
            check(False, f"{name} raised {e!r}")

    print("\n[3] Effect dialog classes exist:")
    for cls in ("BevelDialog", "ChromeDialog", "GlassDialog", "GradientGlowDialog",
                "MotionTrailDialog", "TwirlDialog", "WoodDialog", "MarbleDialog",
                "WeaveDialog", "_EffectDialog", "_TextureDialog"):
        check(hasattr(P, cls) and isinstance(getattr(P, cls), type), f"class {cls}")

    print("\n[4] Noise/turbulence helpers are seedable & deterministic:")
    n1 = P._turbulence(h, w, 20, octaves=4, seed=5)
    n2 = P._turbulence(h, w, 20, octaves=4, seed=5)
    n3 = P._turbulence(h, w, 20, octaves=4, seed=6)
    check(np.array_equal(n1, n2), "_turbulence same seed -> identical")
    check(not np.array_equal(n1, n3), "_turbulence different seeds -> differ")

    print("\n" + ("=" * 60))
    if FAIL:
        print(f"RESULT: {len(FAIL)} FAILURE(S)")
        for f in FAIL:
            print("   -", f)
        sys.exit(1)
    print("RESULT: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
