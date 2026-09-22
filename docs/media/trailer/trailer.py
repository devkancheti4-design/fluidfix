#!/usr/bin/env python3
"""fluidfix — animated explainer trailer. Deterministic frame renderer (Pillow) piped
into ffmpeg. Every number on screen is a measured one from the repo's research.

  python3 trailer.py preview 0.8 7.2 16 25 35 46 55 65 75 83   # PNGs of those seconds
  python3 trailer.py render out.mp4                             # full 60 fps render
"""
import math, os, subprocess, sys, functools
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 60
FFMPEG = "/opt/homebrew/bin/ffmpeg"
FONTS = "/System/Library/Fonts"

# ---------------------------------------------------------------- palette --
BG = (11, 15, 20); INK = (255, 255, 255); TEXT = (221, 227, 234)
MUTED = (139, 149, 162); DIM = (90, 101, 114); AMBER = (242, 180, 65)
OK = (95, 181, 138); BAD = (217, 119, 107); SURFACE = (18, 24, 33)
RAISED = (23, 31, 42); RULE = (31, 42, 54); RULE2 = (44, 58, 74)

@functools.lru_cache(maxsize=None)
def font(kind, size):
    path, idx = {"bold": ("HelveticaNeue.ttc", 1), "medium": ("HelveticaNeue.ttc", 10),
                 "light": ("HelveticaNeue.ttc", 7), "regular": ("HelveticaNeue.ttc", 0),
                 "mono": ("Menlo.ttc", 0), "monob": ("Menlo.ttc", 1)}[kind]
    return ImageFont.truetype(os.path.join(FONTS, path), size, index=idx)

# ---------------------------------------------------------------- easing ---
def clamp(x, lo=0.0, hi=1.0): return lo if x < lo else hi if x > hi else x
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else (1.0 if t >= t0 else 0.0)
def ease_out(p): return 1 - (1 - p) ** 3
def ease_in_out(p): return 3 * p * p - 2 * p * p * p
def enter(t, t0, d=0.6):
    """(alpha, dy) for a fade-up entrance starting at t0."""
    p = ease_out(prog(t, t0, d)); return p, int((1 - p) * 28)

# ---------------------------------------------------------------- drawing --
@functools.lru_cache(maxsize=4096)
def _text_mask(s, kind, size):
    f = font(kind, size)
    l, tp, r, b = f.getbbox(s)
    pad = 4
    im = Image.new("L", (max(1, r - l + 2 * pad), max(1, b - tp + 2 * pad)), 0)
    ImageDraw.Draw(im).text((pad - l, pad - tp), s, font=f, fill=255)
    return im, (l - pad, tp - pad)

def text(img, xy, s, kind, size, color, alpha=1.0, anchor="l"):
    """Draw s with its top-left (or top-center / top-right) at xy, at the given alpha."""
    if alpha <= 0 or not s: return
    mask, (dx, dy) = _text_mask(s, kind, size)
    w = mask.width
    x, y = xy
    if anchor == "c": x -= w // 2
    elif anchor == "r": x -= w
    if alpha < 1: mask = mask.point(lambda v: int(v * alpha))
    img.paste(color, (int(x + dx), int(y + dy)), mask)

def text_w(s, kind, size):
    return _text_mask(s, kind, size)[0].width - 8

def rrect(img, box, r, fill, alpha=1.0, outline=None, width=2):
    if alpha <= 0: return
    x0, y0, x1, y1 = [int(v) for v in box]
    layer = Image.new("RGBA", (x1 - x0 + 2, y1 - y0 + 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    d.rounded_rectangle((1, 1, x1 - x0, y1 - y0), r, fill=(*fill, a) if fill else None,
                        outline=(*outline, a) if outline else None, width=width)
    img.paste(layer, (x0 - 1, y0 - 1), layer)

def arrow(img, x, y, w, h, color, alpha=1.0):
    """A right-pointing arrow (shaft + head) — the → glyph is not in Helvetica Neue."""
    if alpha <= 0: return
    layer = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer); a = int(255 * alpha); th = max(4, h // 7)
    d.rectangle((0, h // 2 - th // 2, w - h // 2, h // 2 + th // 2), fill=(*color, a))
    d.polygon([(w - h // 2 - 4, 2), (w, h // 2), (w - h // 2 - 4, h - 2)], fill=(*color, a))
    img.paste(layer, (int(x), int(y)), layer)

def glow_rect(img, box, r, color, strength=0.5, blur=28):
    x0, y0, x1, y1 = [int(v) for v in box]
    pad = blur * 2
    layer = Image.new("RGBA", (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((pad, pad, pad + x1 - x0, pad + y1 - y0), r,
                                            fill=(*color, int(255 * strength)))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    img.paste(layer, (x0 - pad, y0 - pad), layer)

@functools.lru_cache(maxsize=1)
def glow_bg():
    g = Image.new("RGBA", (1400, 1400), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((300, 300, 1100, 1100), fill=(*AMBER, 40))
    return g.filter(ImageFilter.GaussianBlur(220))

def background(T):
    img = Image.new("RGB", (W, H), BG)
    g = glow_bg()
    x = int(W * 0.62 + 160 * math.sin(T * 0.11)); y = int(H * 0.35 + 90 * math.cos(T * 0.07))
    img.paste(g, (x - 700, y - 700), g)
    return img

def eyebrow(img, t, s, t0=0.0, y=118):
    a, dy = enter(t, t0)
    text(img, (160, y + dy), s, "mono", 26, AMBER, a)

def headline(img, t, s, t0=0.25, y=170, size=76, color=INK):
    a, dy = enter(t, t0)
    text(img, (160, y + dy), s, "bold", size, color, a)

def caption(img, t, s, t0, y=930, color=MUTED, size=38):
    a, dy = enter(t, t0)
    text(img, (160, y + dy), s, "light", size, color, a)

def fade_edges(img, t, dur, fin=0.45, fout=0.45):
    a = 1.0
    if t < fin: a = ease_in_out(t / fin)
    elif t > dur - fout: a = ease_in_out((dur - t) / fout)
    if a < 1:
        return Image.blend(Image.new("RGB", (W, H), BG), img, clamp(a))
    return img

# ---------------------------------------------------------------- scenes ---
def s_title(img, t):
    a, dy = enter(t, 0.2, 0.9)
    # brand mark
    rrect(img, (160, 372 + dy, 250, 462 + dy), 18, AMBER, a)
    rrect(img, (184, 396 + dy, 226, 438 + dy), 6, BG, a)
    text(img, (286, 336 + dy), "fluidfix", "bold", 150, INK, a)
    a2, dy2 = enter(t, 1.2, 0.7); text(img, (164, 560 + dy2), "Repairs the bug.", "bold", 72, INK, a2)
    a3, dy3 = enter(t, 1.9, 0.7); text(img, (164 + text_w("Repairs the bug. ", "bold", 72), 560 + dy3), "Refuses the guess.", "bold", 72, AMBER, a3)
    a4, dy4 = enter(t, 3.0, 0.7); text(img, (164, 700 + dy4), "How it works, in ninety seconds. Every number on screen was measured.", "light", 36, MUTED, a4)

CODE = ["def invoice_total(shipments):",
        "    net = sum(quote(w, z) for w, z in shipments)",
        "    gross = net * (1 + VAT)",
        "    return round(gross, 2)"]

def code_panel(img, t, lines, y0=270, flip_line=None, flip_at=None, t0=0.3, size=40, hl=None):
    a, dy = enter(t, t0)
    rrect(img, (160, y0 + dy, 1760, y0 + dy + 60 + 58 * len(lines)), 22, SURFACE, a, RULE)
    for i, ln in enumerate(lines):
        y = y0 + dy + 32 + 58 * i
        if i == flip_line and flip_at is not None and t >= flip_at:
            p = prog(t, flip_at, 0.5)
            before, after = ln
            s = after
            # red pulse behind the line
            rrect(img, (200, y - 8, 1720, y + 48), 10, BAD, 0.22 * (1 - p) + 0.10, )
            text(img, (200, y), s, "mono", size, TEXT, a)
            k = s.index("-")
            px = 200 + text_w(s[:k], "mono", size)
            text(img, (px, y), "-", "monob", size, BAD, a)
        else:
            s = ln[0] if isinstance(ln, tuple) else ln
            text(img, (200, y), s, "mono", size, TEXT, a)

def s_regression(img, t):
    eyebrow(img, t, "A REGRESSION SHIPS")
    headline(img, t, "Someone tidies a formula.")
    code_panel(img, t, [CODE[0], CODE[1], ("    gross = net * (1 + VAT)", "    gross = net * (1 - VAT)"), CODE[3]],
               flip_line=2, flip_at=2.0)
    tests = [("test_quote_domestic", True), ("test_express_eu", True), ("test_invoice", False)]
    for i, (name, ok) in enumerate(tests):
        a, dy = enter(t, 0.9 + 0.15 * i)
        y = 610 + 56 * i + dy
        red = (not ok) and t >= 3.2
        mark = "✗" if red else "✓"
        text(img, (200, y), mark, "monob", 36, BAD if red else OK, a)
        text(img, (250, y), name, "mono", 36, TEXT if not red else INK, a)
        if red:
            ar = ease_out(prog(t, 3.2, 0.4))
            text(img, (250 + text_w(name + "   ", "mono", 36), y), "AssertionError: assert 23.49 == 34.51", "mono", 30, BAD, ar)
    if t >= 3.9:
        ar, dyr = enter(t, 3.9)
        rrect(img, (196, 790 + dyr, 640, 846 + dyr), 12, BAD, 0.16 * ar)
        text(img, (214, 800 + dyr), "1 failed, 2 passed", "monob", 34, BAD, ar)
    caption(img, t, "The suite goes red. Nobody has to be watching.", 4.8)

def s_localise(img, t):
    eyebrow(img, t, "1 · LOCALISE")
    headline(img, t, "Your failing tests point at the file.")
    rows = [("shipwise/invoice.py", 1.00, "rank 1"), ("shipwise/quote.py", 0.36, "rank 2"), ("shipwise/rates.py", 0.12, "rank 3")]
    for i, (name, wgt, lab) in enumerate(rows):
        a, dy = enter(t, 0.8 + 0.25 * i)
        y = 330 + 120 * i + dy
        text(img, (160, y), name, "mono", 38, INK if i == 0 else TEXT, a)
        p = ease_out(prog(t, 1.2 + 0.25 * i, 1.1))
        full = 1180
        rrect(img, (160, y + 58, 160 + full, y + 84), 8, RAISED, a)
        col = AMBER if i == 0 else RULE2
        rrect(img, (160, y + 58, 160 + max(12, int(full * wgt * p)), y + 84), 8, col, a)
        text(img, (1380, y + 52), lab, "mono", 28, AMBER if i == 0 else DIM, a * p)
    caption(img, t, "Traceback frames first, then the lines the failing tests actually ran. No model reads your code.", 3.4)

BITS = [("BUILT", "a candidate passed"), ("AMB", "one input, two outputs"), ("UNREAD", "a tool read nothing"),
        ("NOTWIN", "built, not what was wanted"), ("HIDDEN", "fine records disagree"), ("CAPPED", "search cut short"),
        ("REFUTED", "every candidate rejected"), ("SELF", "the job is the worker")]

def s_observe(img, t):
    eyebrow(img, t, "2 · OBSERVE")
    headline(img, t, "Eight measured bits describe the situation.")
    cw, gap = 190, 14
    x0 = 160
    lit = {0: 2.6}   # BUILT lights at 2.6 s
    for i, (name, desc) in enumerate(BITS):
        a, dy = enter(t, 0.7 + 0.08 * i)
        x = x0 + i * (cw + gap); y = 330 + dy
        on = i in lit and t >= lit[i]
        pl = ease_out(prog(t, lit.get(i, 99), 0.5)) if on else 0.0
        if on: glow_rect(img, (x, y, x + cw, y + 150), 16, AMBER, 0.55 * pl, 24)
        fill = tuple(int(RAISED[k] + (AMBER[k] * 0.22 + RAISED[k] * 0.78 - RAISED[k]) * pl) for k in range(3))
        rrect(img, (x, y, x + cw, y + 150), 16, fill, a, AMBER if on else RULE)
        text(img, (x + 18, y + 20), name, "monob", 26, INK if on else MUTED, a)
        d = ImageDraw.Draw(img)
        cx, cy = x + cw - 30, y + 34
        d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=AMBER if on else RULE2)
        # wrapped description
        words = desc.split(); line1, line2 = " ".join(words[:2]), " ".join(words[2:])
        text(img, (x + 18, y + 72), line1, "light", 22, MUTED if on else DIM, a)
        text(img, (x + 18, y + 102), line2, "light", 22, MUTED if on else DIM, a)
    a2, dy2 = enter(t, 3.3)
    text(img, (160, 560 + dy2), "byte", "mono", 40, MUTED, a2)
    byte_s = "00000001" if t >= 2.6 else "00000000"
    text(img, (270, 560 + dy2), byte_s, "monob", 40, INK, a2)
    text(img, (560, 560 + dy2), "= 1", "mono", 40, AMBER if t >= 2.6 else MUTED, a2)
    caption(img, t, "Eight bits. 256 situations. Every one of them enumerated before the tool ever ran.", 4.2)

def ship(x): return (x & 0x7E) == 0

def s_law(img, t):
    eyebrow(img, t, "3 · THE LAW RULES")
    headline(img, t, "One integer expression decides.")
    cell, gap = 30, 6
    gx, gy = 160, 292
    n_shown = int(256 * ease_out(prog(t, 0.6, 1.6)))
    sweep = (t * 55) % 300
    for x in range(min(256, n_shown)):
        r, c = divmod(x, 16)
        px, py = gx + c * (cell + gap), gy + r * (cell + gap)
        if ship(x):
            pulse = 0.5 + 0.5 * math.sin(t * 3 + x)
            glow_rect(img, (px, py, px + cell, py + cell), 8, AMBER, 0.35 + 0.25 * pulse, 12)
            rrect(img, (px, py, px + cell, py + cell), 8, AMBER)
        else:
            near = max(0.0, 1 - abs(x - sweep) / 6)
            g = int(46 + 12 * ((x >> 1) & 3) + 60 * near)
            rrect(img, (px, py, px + cell, py + cell), 5, (g, g + 6, g + 12))
    # highlight byte 1 from 3.2 s
    if t >= 3.2:
        p = ease_out(prog(t, 3.2, 0.5))
        px, py = gx + 1 * (cell + gap), gy
        rrect(img, (px - 6, py - 6, px + cell + 6, py + cell + 6), 10, None, p, INK, 3)
    # right panel
    rx = 900
    a1, d1 = enter(t, 1.8); text(img, (rx, 300 + d1), "256 situations · 4 write your code · 252 refuse, and say why", "light", 30, MUTED, a1)
    a2, d2 = enter(t, 3.4); text(img, (rx, 380 + d2), "byte 1 · BUILT", "mono", 34, TEXT, a2)
    a3, d3 = enter(t, 3.9, 0.5); text(img, (rx, 430 + d3), "SHIP", "bold", 110, AMBER, a3)
    text(img, (rx, 560 + d3), "write it, byte-exact", "light", 34, MUTED, a3)
    facts = ["178 integer operations", "2.01 ns per ruling, compiled", "0 floats · 0 branches · 0 weights", "re-proven on all 256 states by  fluidfix selfcheck"]
    for i, f in enumerate(facts):
        a, dy = enter(t, 5.0 + 0.35 * i)
        text(img, (rx, 650 + 48 * i + dy), "▸ " + f, "mono", 28, TEXT if i < 3 else AMBER, a)
    caption(img, t, "Not a model. Not a heuristic. Arithmetic on eight bits, proven exhaustively, at zero tokens.", 6.8)

CANDS = [("    return round(gross, 1)", False, "✗ test_invoice"),
         ("    gross = net * (0 + VAT)", False, "✗ test_invoice"),
         ("    gross = net * (1 + VAT)", True, "✓ 3 passed")]

def s_judge(img, t):
    eyebrow(img, t, "4 · YOUR SUITE IS THE JUDGE")
    headline(img, t, "Every candidate runs your tests.")
    for i, (cand, ok, verdict) in enumerate(CANDS):
        t0 = 0.9 + 2.0 * i
        a, dy = enter(t, t0)
        y = 320 + 110 * i + dy
        judged = t >= t0 + 1.1
        settled = judged and (ok or t >= t0 + 1.9)
        dimmed = settled and not ok
        rrect(img, (160, y, 1760, y + 84), 16, SURFACE, a * (0.55 if dimmed else 1.0), (OK if (judged and ok) else BAD if judged else RULE))
        text(img, (196, y + 22), cand, "mono", 36, DIM if dimmed else INK, a)
        if not judged:
            # running dots
            k = int((t - t0) * 6) % 4
            text(img, (1300, y + 22), "running suite" + "." * k, "mono", 30, MUTED, a * ease_out(prog(t, t0 + 0.3, 0.3)))
        else:
            av = ease_out(prog(t, t0 + 1.1, 0.35))
            text(img, (1300, y + 22), verdict, "monob", 32, OK if ok else BAD, av)
            if dimmed:
                text(img, (1300, y + 22), verdict, "monob", 32, BAD, 0.5)
                text(img, (196 + text_w(cand + "   ", "mono", 36), y + 26), "rolled back, byte-exact", "light", 28, DIM, ease_out(prog(t, t0 + 1.9, 0.4)))
    if t >= 7.6:
        a, dy = enter(t, 7.6)
        glow_rect(img, (160, 680 + dy, 1100, 760 + dy), 16, AMBER, 0.25 * a, 24)
        rrect(img, (160, 680 + dy, 1100, 760 + dy), 16, AMBER, a)
        text(img, (192, 700 + dy), "SHIP  ·  fluidfix: restore invoice.py:8", "monob", 34, BG, a)
        a2, dy2 = enter(t, 8.1)
        text(img, (1130, 700 + dy2), "repaired in 6 suite runs · 2.3 s · 0 tokens", "mono", 30, MUTED, a2)
    caption(img, t, "A wrong candidate cannot land: it is rolled back byte for byte. The one that passes is committed.", 9.0)

def s_refuse(img, t):
    eyebrow(img, t, "WHEN IT CANNOT PROVE")
    headline(img, t, "It refuses. It never guesses.")
    rows = [("    return n * 2 - 1", "✓ green"), ("    return n * 1 + 1", "✓ green")]
    for i, (cand, v) in enumerate(rows):
        a, dy = enter(t, 0.8 + 0.6 * i)
        y = 320 + 100 * i + dy
        rrect(img, (160, y, 1300, y + 80), 16, SURFACE, a, OK)
        text(img, (196, y + 20), cand, "mono", 36, INK, a)
        text(img, (1000, y + 22), v, "monob", 32, OK, a)
    a2, dy2 = enter(t, 2.4)
    text(img, (160, 540 + dy2), "two different programs, both green — your tests cannot tell them apart", "light", 34, MUTED, a2)
    a3, dy3 = enter(t, 3.2, 0.5)
    text(img, (160, 610 + dy3), "AMBIGUOUS", "bold", 84, AMBER, a3)
    ax = 160 + text_w("AMBIGUOUS", "bold", 84) + 34
    arrow(img, ax, 610 + dy3 + 30, 96, 44, AMBER, a3)
    text(img, (ax + 130, 610 + dy3), "REFUSED", "bold", 84, AMBER, a3)
    a4, dy4 = enter(t, 4.2)
    text(img, (160, 730 + dy4), "Not a byte touched. A pinning test written instead:  .fluidfix/pin_me_test.py", "light", 34, TEXT, a4)
    a5, dy5 = enter(t, 5.4)
    text(img, (160, 800 + dy5), "Killed mid-write? The next run restores the original bytes from the journal before it judges anything.", "light", 30, MUTED, a5)
    caption(img, t, "Precision is bounded by your suite, never by a guess.", 6.6)

TEACH = ["# one worked example: line before, line after, a signal, a transform",
         "#   return round(total)        <- money rounded to whole units",
         "#   return round(total, 2)     <- the fix",
         "register(",
         "    4, \"round-lost-precision\",",
         "    'a round() on a money value with no ndigits, dropping the cents',",
         "    re.compile(r\"round\\(\\w+\\)\"),",
         "    lambda line, o: re.sub(r\"round\\((\\w+)\\)\", r\"round(\\1, 2)\", line),",
         ")"]

def s_teach(img, t):
    eyebrow(img, t, "TEACH IT ONCE")
    headline(img, t, "One structured example. A whole class, forever.")
    a, dy = enter(t, 0.5)
    rrect(img, (160, 290 + dy, 1760, 290 + dy + 40 + 46 * len(TEACH)), 22, SURFACE, a, RULE)
    chars = int(max(0, t - 0.9) * 95)          # typewriter speed
    for i, ln in enumerate(TEACH):
        if chars <= 0: break
        s = ln[:chars]; chars -= len(ln) + 1
        col = DIM if ln.startswith("#") else TEXT
        text(img, (200, 310 + dy + 46 * i), s, "mono", 32, col, a)
    if t >= 6.4:
        a2, dy2 = enter(t, 6.4)
        text(img, (160, 780 + dy2), "fluidfix guard . --dictionary rules.py", "monob", 34, AMBER, a2)
        a3, dy3 = enter(t, 7.0)
        text(img, (160, 840 + dy3), "Every future member of the class: decided by the law, judged by your suite, zero tokens.", "light", 32, TEXT, a3)
    caption(img, t, "Structured examples, not prose. That is the whole trade.", 8.0)

STATS = [("0", "tokens, ever"), ("2.01 ns", "per ruling"), ("12 / 12", "repairs byte-exact"),
         ("0", "wrong repairs in 32 runs"), ("225 / 225", "tests green"), ("256 / 256", "law states verified")]

def s_proof(img, t):
    eyebrow(img, t, "MEASURED, NOT CLAIMED")
    headline(img, t, "Every number has a file behind it.")
    for i, (n, lab) in enumerate(STATS):
        r, c = divmod(i, 3)
        a, dy = enter(t, 0.7 + 0.25 * i)
        x = 160 + c * 540; y = 330 + r * 250 + dy
        rrect(img, (x, y, x + 500, y + 210), 20, SURFACE, a, RULE)
        text(img, (x + 32, y + 36), n, "bold", 88, AMBER, a)
        text(img, (x + 34, y + 150), lab, "light", 30, MUTED, a)
    caption(img, t, "github.com/devkancheti4-design/fluidfix/research — scripts, logs and results for every figure above.", 3.0, size=32)

def s_end(img, t):
    a, dy = enter(t, 0.2, 0.9)
    rrect(img, (160, 300 + dy, 250, 390 + dy), 18, AMBER, a)
    rrect(img, (184, 324 + dy, 226, 366 + dy), 6, BG, a)
    text(img, (286, 264 + dy), "fluidfix", "bold", 150, INK, a)
    a2, dy2 = enter(t, 1.0)
    rrect(img, (164, 500 + dy2, 164 + text_w("pip install -U fluidfix", "monob", 48) + 80, 590 + dy2), 45, SURFACE, a2, RULE2)
    text(img, (204, 518 + dy2), "pip install -U fluidfix", "monob", 48, INK, a2)
    a3, dy3 = enter(t, 1.7)
    text(img, (164, 640 + dy3), "github.com/devkancheti4-design/fluidfix", "light", 36, MUTED, a3)
    a4, dy4 = enter(t, 2.4)
    text(img, (164, 740 + dy4), "Repairs the bug.", "bold", 60, INK, a4)
    text(img, (164 + text_w("Repairs the bug. ", "bold", 60), 740 + dy4), "Refuses the guess.", "bold", 60, AMBER, a4)
    a5, dy5 = enter(t, 3.2)
    text(img, (164, 840 + dy5), "Free and open source · AGPL-3.0", "light", 30, DIM, a5)

SCENES = [(s_title, 6.0), (s_regression, 8.0), (s_localise, 7.5), (s_observe, 8.0), (s_law, 10.5),
          (s_judge, 12.0), (s_refuse, 9.5), (s_teach, 10.5), (s_proof, 8.0), (s_end, 6.5)]
TOTAL = sum(d for _, d in SCENES)

def frame_at(T):
    img = background(T)
    acc = 0.0
    for fn, d in SCENES:
        if T < acc + d or (fn is SCENES[-1][0]):
            t = T - acc
            fn(img, t)
            return fade_edges(img, t, d)
        acc += d
    return img

def main():
    mode = sys.argv[1]
    if mode == "preview":
        os.makedirs("preview", exist_ok=True)
        for s in sys.argv[2:]:
            frame_at(float(s)).save(f"preview/f_{float(s):06.2f}.png")
        print("previews written; total length", TOTAL, "s")
    elif mode == "render":
        out = sys.argv[2]
        n = int(TOTAL * FPS)
        p = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                              "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                              "-movflags", "+faststart", out], stdin=subprocess.PIPE)
        import time
        t0 = time.time()
        for f in range(n):
            p.stdin.write(frame_at(f / FPS).tobytes())
            if f % 600 == 0: print(f"{f}/{n} frames, {time.time() - t0:.0f}s", flush=True)
        p.stdin.close(); p.wait()
        print("done", out, f"{n} frames in {time.time() - t0:.0f}s")

if __name__ == "__main__":
    main()
