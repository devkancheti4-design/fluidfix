#!/usr/bin/env python3
"""One perfect example sets the path — an added scene for the fluidfix trailer.

  python3 path_scene.py preview 2 5 9 13 17
  python3 path_scene.py clip one-example-sets-the-path.mp4      # standalone, ~20 s
  python3 path_scene.py trailer fluidfix-trailer-v2.mp4         # full trailer with the scene after "Teach it once"
"""
import math, os, random, subprocess, sys, time
from PIL import Image, ImageDraw
import trailer as T
from trailer import (text, text_w, rrect, glow_rect, arrow, background, fade_edges, enter, prog, ease_out,
                     eyebrow, headline, caption, BG, INK, TEXT, MUTED, DIM, AMBER, OK, BAD, SURFACE, RAISED, RULE, RULE2)

DUR = 21.0
rng = random.Random(7)
FIELD = (170, 330, 940, 860)
DOTS = [(rng.uniform(FIELD[0], FIELD[2]), rng.uniform(FIELD[1], FIELD[3])) for _ in range(110)]
EXAMPLE = 41                                   # the one perfect example
LABELS = ["invoice.py", "quote.py", "rates.py", "vec3.h · 2016", "affine.h · 2018", "aabb2d.h · 2023", "frustum.h", "mat4.h"]
def _pick():
    """Members and the unknown dot, chosen so no label collides with another or with the example's box."""
    ex = DOTS[EXAMPLE]; box = (ex[0] - 140, ex[1] - 200, ex[0] + 360, ex[1] + 20)
    taken = [ex]; out = []
    def clear(pt):
        x, y = pt
        if box[0] <= x <= box[2] and box[1] <= y <= box[3]: return False
        return all(math.dist(pt, q) >= 110 for q in taken) and x + 200 < 1000
    for i, pt in enumerate(DOTS):
        if i == EXAMPLE or len(out) == len(LABELS) + 1: continue
        if clear(pt): out.append(i); taken.append(pt)
    return out[:len(LABELS)], out[len(LABELS)]
_m, UNKNOWN = _pick()
MEMBERS = list(zip(_m, LABELS))
NODES = [(1290, 330, "signal", r"round\(\w+\)"), (1530, 330, "transform", "→ round(x, 2)"), (1770, 330, "act", "derived each call")]

def line(img, pts, color, width, alpha=1.0, progress=1.0):
    """Polyline drawn up to `progress` of its length, with alpha."""
    if alpha <= 0 or progress <= 0 or len(pts) < 2: return
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(math.dist(a, b) for a, b in segs); left = total * progress
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; pad = width + 4
    ox, oy = int(min(xs)) - pad, int(min(ys)) - pad
    layer = Image.new("RGBA", (int(max(xs)) - ox + pad, int(max(ys)) - oy + pad), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    a = int(255 * alpha); sh = lambda P: (P[0] - ox, P[1] - oy)
    for p, q in segs:
        L = math.dist(p, q)
        if left <= 0: break
        if L <= left: d.line([sh(p), sh(q)], fill=(*color, a), width=width); left -= L
        else:
            f = left / L; d.line([sh(p), sh((p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f))], fill=(*color, a), width=width); left = 0
    img.paste(layer, (ox, oy), layer)

def dot(img, xy, r, color, alpha=1.0, glow=0.0):
    x, y = xy
    if glow > 0: glow_rect(img, (x - r, y - r, x + r, y + r), r, color, glow, 18)
    rrect(img, (x - r, y - r, x + r, y + r), r, color, alpha)

def s_path(img, t):
    eyebrow(img, t, "IMAGINE THE SPACE OF DEFECTS")
    headline(img, t, "One perfect example sets the path.")
    ex = DOTS[EXAMPLE]
    members = {i: (k, lab) for k, (i, lab) in enumerate(MEMBERS)}
    # the field
    for i, (x, y) in enumerate(DOTS):
        a = ease_out(prog(t, 0.5 + 0.006 * i, 0.5))
        if i == EXAMPLE or i in members or i == UNKNOWN: continue
        dot(img, (x, y), 5, RULE2, a * 0.9)
    # nodes of the route, popping in as the path reaches them
    sig_node = (NODES[0][0], NODES[0][1])
    for k, (nx, ny, name, desc) in enumerate(NODES):
        t0 = 3.4 + 0.55 * k
        a, dy = enter(t, t0, 0.5)
        if a <= 0: continue
        hw = 112
        rrect(img, (nx - hw, ny - 44 + dy, nx + hw, ny + 44 + dy), 22, SURFACE, a, AMBER if k < 2 else None)
        if k == 2:
            glow_rect(img, (nx - hw, ny - 44 + dy, nx + hw, ny + 44 + dy), 22, AMBER, 0.35 * a, 20)
            rrect(img, (nx - hw, ny - 44 + dy, nx + hw, ny + 44 + dy), 22, AMBER, a)
        text(img, (nx, ny - 32 + dy), name, "monob", 22, BG if k == 2 else AMBER, a, anchor="c")
        text(img, (nx, ny + 4 + dy), desc, "mono", 18, BG if k == 2 else TEXT, a, anchor="c")
    # the path from the example: example -> signal -> transform -> act
    route = [ex, sig_node, (NODES[1][0], NODES[1][1]), (NODES[2][0], NODES[2][1])]
    p_route = ease_out(prog(t, 3.0, 1.9))
    pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(t * 4.0)) if t > 6 else 1.0
    line(img, route, AMBER, 4, 0.95 * pulse if p_route > 0 else 0, p_route)
    # the example itself
    ae = ease_out(prog(t, 1.8, 0.6))
    if ae > 0:
        dot(img, ex, 11, AMBER, ae, 0.6 * ae)
        bx, by = ex[0] - 120, ex[1] - 150
        rrect(img, (bx, by, bx + 470, by + 96), 14, SURFACE, ae, AMBER)
        text(img, (bx + 16, by + 12), "return round(total)", "mono", 24, BAD, ae)
        text(img, (bx + 16, by + 50), "return round(total, 2)", "mono", 24, OK, ae)
        text(img, (bx, by - 34), "the one perfect example", "light", 24, AMBER, ae)
    # members of the class join the path, one by one — no new example
    for i, (k, lab) in members.items():
        t0 = 6.0 + 0.55 * k
        a = ease_out(prog(t, t0, 0.5))
        if a <= 0: dot(img, DOTS[i], 5, RULE2, 0.9); continue
        pj = ease_out(prog(t, t0 + 0.15, 0.6))
        line(img, [DOTS[i], sig_node], AMBER, 2, 0.55 * a, pj)
        dot(img, DOTS[i], 7, AMBER, a, 0.3 * a)
        text(img, (DOTS[i][0] + 14, DOTS[i][1] - 30), lab, "mono", 18, TEXT, a)
    if t >= 8.0:
        a, dy = enter(t, 8.0)
        text(img, (1180, 420 + dy), "same path, no new example", "light", 30, AMBER, a)
    # the one that is not this class: no path
    tu = 11.2
    au = ease_out(prog(t, tu, 0.5))
    if au > 0:
        pr = 0.5 + 0.5 * math.sin((t - tu) * 6)
        dot(img, DOTS[UNKNOWN], 8, BAD, au, 0.35 * au * pr)
        text(img, (DOTS[UNKNOWN][0] + 16, DOTS[UNKNOWN][1] - 30), "unknown class → no path → refused", "mono", 18, BAD, au)
    else:
        dot(img, DOTS[UNKNOWN], 5, RULE2, 0.9)
    # facts
    a1, d1 = enter(t, 13.0)
    text(img, (1180, 500 + d1), "cglm, real history: one 2016 example produced the correct", "light", 25, TEXT, a1)
    text(img, (1180, 534 + d1), "repair for four real fixes, 2016 to 2023, in four files.", "light", 25, TEXT, a1)
    a2, d2 = enter(t, 15.0)
    text(img, (1180, 620 + d2), "route(F1, A1, Fq): the act is re-derived from the example", "mono", 20, MUTED, a2)
    text(img, (1180, 652 + d2), "on every call, never stored.", "mono", 20, MUTED, a2)
    text(img, (1180, 700 + d2), "4,096 / 4,096 routes verified by  fluidfix selfcheck", "mono", 20, AMBER, a2)
    caption(img, t, "Write the incident down once. The path is the law's; every future member follows it for free.", 16.8, size=34)

def frame_clip(Tm):
    img = background(Tm); s_path(img, Tm); return fade_edges(img, Tm, DUR)

def render(frames_fn, n, out):
    p = subprocess.Popen([T.FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{T.W}x{T.H}", "-r", str(T.FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                          "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(n):
        p.stdin.write(frames_fn(f / T.FPS).tobytes())
    p.stdin.close(); p.wait(); print("done", out, n, "frames", f"{time.time() - t0:.0f}s")

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "preview":
        os.makedirs("preview_path", exist_ok=True)
        for s in sys.argv[2:]: frame_clip(float(s)).save(f"preview_path/p_{float(s):05.2f}.png")
        print("ok")
    elif mode == "clip":
        render(frame_clip, int(DUR * T.FPS), sys.argv[2])
    elif mode == "trailer":
        scenes = list(T.SCENES); i = [k for k, (fn, _) in enumerate(scenes) if fn is T.s_teach][0]
        scenes.insert(i + 1, (s_path, DUR)); T.SCENES[:] = scenes; T.TOTAL = sum(d for _, d in scenes)
        render(T.frame_at, int(T.TOTAL * T.FPS), sys.argv[2])
