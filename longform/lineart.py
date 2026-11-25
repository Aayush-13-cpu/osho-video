"""Glowing line art for the long-form videos (1920x1080): every sky, land, figure and prop is a thin line of light
that traces itself in when its beat begins, inside a soft glow.

Markup is plain SVG; motion is described as dicts that the page's GSAP interpreter turns into tweens, so every frame
is deterministic. Coordinates are the frame's own: x across 0-1920, y down 0-1080, horizon at HZ, and every figure or
prop is placed by the point where it touches the ground (GF for the near ground).
"""
import math

W, H, HZ, GF = 1920, 1080, 760, 850
D = 'class="d" pathLength="1"'      # traced in when the beat begins, with a faint fill
N = 'class="d n" pathLength="1"'    # traced in, never filled (open lines)
F = 'class="d f" pathLength="1"'    # traced in, then glowing solid (flames, the star)
O = 'class="d o" pathLength="1"'    # traced in, then solid as the sky (--cut): a cut-out that hides the lines behind it

# One template per video: its palette, its glow, and the moving light behind every scene.
TEMPLATES = {
    "saffron": dict(line="#ffd27a", glow="#ff9d2e", dot="#fff0d0", motif="sunburst",
                    skies={"night": ("#0c0602", "#2e1606"), "dawn": ("#100803", "#4a2a12"), "dusk": ("#120604", "#4a1c0c"),
                           "day": ("#1a0e06", "#5a3414"), "storm": ("#060403", "#221a14")}),
    "maroon": dict(line="#f6c0b0", glow="#d0465a", dot="#ffe4dc", motif="mandala",
                   skies={"night": ("#10030a", "#3a0c1e"), "dawn": ("#14060c", "#5a2430"), "dusk": ("#12040a", "#4e1626"),
                          "day": ("#1c0812", "#5a2a3a"), "storm": ("#0a0408", "#241820")}),
}


def _mix(a, b, t):
    """Blend two #rrggbb colours: t=0 gives a, t=1 gives b."""
    x, y = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in (a, b))
    return "#" + "".join(f"{round(u + (v - u) * t):02x}" for u, v in zip(x, y))


def _template(line, glow, deep, horizon, motif):
    """A template from four colours: the five skies are the night sky warmed, cooled or darkened."""
    return dict(line=line, glow=glow, dot=_mix(line, "#ffffff", 0.6), motif=motif, skies={
        "night": (deep, horizon), "dawn": (deep, _mix(horizon, "#6a4a2a", 0.5)), "dusk": (deep, _mix(horizon, "#5a2030", 0.5)),
        "day": (_mix(deep, horizon, 0.6), _mix(horizon, "#5a6a9a", 0.35)), "storm": (_mix(deep, "#000000", 0.3), _mix(horizon, "#202428", 0.6))})


TEMPLATES.update({  # name: line, glow, deep sky, horizon, motif
    "lotus": _template("#ffd6e4", "#ff8fb8", "#100509", "#3a1426", "ripple"),
    "bodhi": _template("#d8f0b0", "#9ad45a", "#050a04", "#1c3014", "halo"),
    "himalaya": _template("#e6f2ff", "#a8cfff", "#04070d", "#1a2a40", "constellation"),
    "ganga": _template("#ffe0b0", "#ffa94a", "#0c0703", "#3a2410", "ripple"),
    "zendo": _template("#e8e0d0", "#c8b89a", "#080706", "#2a2620", "motes"),
    "moonlake": _template("#d6e4ff", "#8fb0ff", "#03050f", "#141e3e", "ripple"),
    "tao": _template("#c8f0e0", "#5fd8b0", "#020c08", "#0c3024", "mandala"),
    "sufi": _template("#ffd0a8", "#ff7a3a", "#0e0503", "#3e1a0c", "mandala"),
    "satori": _template("#fff6d0", "#ffe07a", "#0a0904", "#34300e", "sunburst"),
    "vipassana": _template("#e0d8ff", "#a090ff", "#06040f", "#1e1840", "halo"),
    "bamboo": _template("#d4f5c0", "#7ad66a", "#040b04", "#163216", "motes"),
    "kyoto": _template("#ffd0d0", "#ff6a6a", "#0d0404", "#3a1212", "constellation"),
    "marigold": _template("#ffe6a0", "#ffb820", "#0d0802", "#3c280a", "sunburst"),
    "indigo": _template("#c8d4ff", "#6a84ff", "#03040f", "#121a44", "constellation"),
    "ember": _template("#ffc8a0", "#ff6a2a", "#0c0402", "#3a140a", "motes"),
    "jade": _template("#c0f5e0", "#3fd8a0", "#020c09", "#0a3226", "halo"),
    "pearl": _template("#f4f2ec", "#d8d0c0", "#08080a", "#26262e", "ripple"),
    "dusk-raga": _template("#ffc8c0", "#e8607a", "#0e0408", "#3c1424", "mandala"),
})
SKIES = ("night", "dawn", "dusk", "day", "storm")
LANDS = ("hills", "field", "desert", "city", "sea", "garden", "mountain", "river", "forest", "zen")
T = TEMPLATES["saffron"]


def use(name):
    """Switch every drawing function to a template (module-level: one chapter is built per process)."""
    global T
    T = TEMPLATES[name]


def rng(seed):
    """Seeded pseudo-random numbers, so 'random' stars and motes are identical on every render."""
    s = seed & 0x7FFFFFFF

    def r():
        nonlocal s
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        return s / 0x7FFFFFFF
    return r


def ridge(base, amp, waves, phase, op=1.0):
    pts = " L".join(f"{x} {base + amp * math.sin(x / W * waves * math.pi + phase):.0f}" for x in range(-40, W + 81, 60))
    return f'<path {N} d="M{pts}" opacity="{op}"/>'


def background(p, sky, moon=True):
    """Sky gradient, the soft halo of light, the template's moving light, stars and the sun or moon."""
    top, low = T["skies"][sky]
    out = [f'<defs><linearGradient id="{p}-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
           f'<stop offset="1" stop-color="{low}"/></linearGradient>'
           f'<radialGradient id="{p}-halo"><stop offset="0" stop-color="{T["glow"]}" stop-opacity="0.75"/>'
           f'<stop offset="1" stop-color="{T["glow"]}" stop-opacity="0"/></radialGradient>'
           f'<filter id="{p}-glow" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="5" result="b"/>'
           f'<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
           f'<rect width="{W}" height="{H}" fill="url(#{p}-sky)"/>',
           f'<circle cx="{W // 2}" cy="{HZ - 220}" r="720" fill="url(#{p}-halo)" opacity="{0.22 if sky == "storm" else 0.4}"/>']
    anims = []
    c = T["line"]
    cx, cy = W // 2, HZ - 220
    if T["motif"] == "sunburst":  # slow-turning rays of light around the centre of the frame
        r = rng(21)
        rays = "".join(f'<path d="M{cx + 380 * math.cos(a):.0f} {cy + 380 * math.sin(a):.0f} '
                       f'L{cx + 1300 * math.cos(a):.0f} {cy + 1300 * math.sin(a):.0f}" opacity="{0.05 + r() * 0.1:.2f}"/>'
                       for a in (i * math.pi / 24 for i in range(48)))
        out.append(f'<g id="{p}-burst" stroke="{c}" stroke-width="2" fill="none">{rays}</g>'
                   f'<circle {N} cx="{cx}" cy="{cy}" r="330" opacity="0.18"/>'
                   f'<circle {N} cx="{cx}" cy="{cy}" r="450" opacity="0.1"/>')
        anims.append({"t": f"#{p}-burst", "do": "spin", "deg": 6, "ox": cx, "oy": cy})
    elif T["motif"] == "constellation":  # bright stars joined by lines of light, traced in like the scene
        r = rng(29)
        pts = [(160 + r() * 1600, 70 + r() * 420) for _ in range(14)]
        links = "".join(f'<path {N} d="M{a[0]:.0f} {a[1]:.0f} L{b[0]:.0f} {b[1]:.0f}" opacity="0.22"/>'
                        for a, b in zip(pts, pts[1:]) if abs(a[0] - b[0]) < 520)
        out.append(f'<g id="{p}-const" fill="{T["dot"]}">' + "".join(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{2.5 + r() * 2.5:.1f}"/>' for x, y in pts) + f'</g>{links}')
        anims.append({"t": f"#{p}-const", "do": "twinkle"})
    elif T["motif"] == "halo":  # rings of light around the centre, breathing slowly
        rings = "".join(f'<circle cx="{cx}" cy="{cy}" r="{rr}" opacity="{0.3 - k * 0.04:.2f}"/>'
                        for k, rr in enumerate(range(220, 900, 110)))
        out.append(f'<g id="{p}-rings" fill="none" stroke="{c}" stroke-width="2">{rings}</g>')
        anims.append({"t": f"#{p}-rings", "do": "pulse", "ox": cx, "oy": cy})
    elif T["motif"] == "mandala":  # two rings of petals turning slowly against each other
        def ring(n, rad, rx, ry):
            return "".join(f'<ellipse cx="{cx + rad * math.cos(a):.0f}" cy="{cy + rad * math.sin(a):.0f}" rx="{rx}" ry="{ry}" '
                           f'transform="rotate({math.degrees(a):.0f} {cx + rad * math.cos(a):.0f} {cy + rad * math.sin(a):.0f})"/>'
                           for a in (i * 2 * math.pi / n for i in range(n)))
        out.append(f'<g id="{p}-mand-a" fill="none" stroke="{c}" stroke-width="2" opacity="0.3">{ring(16, 300, 46, 14)}</g>'
                   f'<g id="{p}-mand-b" fill="none" stroke="{c}" stroke-width="2" opacity="0.18">{ring(12, 440, 62, 18)}</g>')
        anims += [{"t": f"#{p}-mand-a", "do": "spin", "deg": 10, "ox": cx, "oy": cy},
                  {"t": f"#{p}-mand-b", "do": "spin", "deg": -8, "ox": cx, "oy": cy}]
    elif T["motif"] == "ripple":  # rings spreading on still water at the horizon, breathing slowly
        rings = "".join(f'<ellipse cx="{cx}" cy="{HZ + 10}" rx="{rr}" ry="{rr * 0.2:.0f}" opacity="{0.34 - k * 0.04:.2f}"/>'
                        for k, rr in enumerate(range(180, 1000, 120)))
        out.append(f'<g id="{p}-ripple" fill="none" stroke="{c}" stroke-width="2">{rings}</g>')
        anims.append({"t": f"#{p}-ripple", "do": "pulse", "ox": cx, "oy": HZ + 10})
    else:  # "motes": embers of light rising through the frame, and rings of sunrise on the horizon
        r = rng(23)
        motes = "".join(f'<circle cx="{r() * W:.0f}" cy="{r() * (H + 200):.0f}" r="{1.5 + r() * 3:.1f}" opacity="{0.15 + r() * 0.5:.2f}"/>'
                        for _ in range(80))
        out.append(f'<g id="{p}-motes" fill="{T["dot"]}">{motes}</g>'
                   + "".join(f'<path {N} d="M{cx - rr} {HZ} A{rr} {rr} 0 0 1 {cx + rr} {HZ}" opacity="{0.28 - k * 0.05:.2f}"/>'
                             for k, rr in enumerate((260, 380, 500, 620))))
        anims.append({"t": f"#{p}-motes", "do": "rise", "by": 160})
    if sky in ("night", "dusk"):
        r = rng(7)
        stars = "".join(f'<circle cx="{r() * W:.0f}" cy="{r() * (HZ - 120):.0f}" r="{0.8 + r() * 1.8:.1f}" opacity="{0.3 + r() * 0.7:.2f}"/>'
                        for _ in range(170 if sky == "night" else 60))
        out.append(f'<g id="{p}-stars" fill="{T["dot"]}">{stars}</g>')
        anims.append({"t": f"#{p}-stars", "do": "twinkle"})
    if sky in ("night", "dusk") and moon:  # off when the cast brings its own moon
        out.append(f'<path {D} d="M1500 120 A64 64 0 1 0 1500 248 A48 64 0 1 1 1500 120 Z" opacity="0.9"/>')  # crescent moon
    elif sky in ("day", "dawn"):
        x, y, rad = (1460, 230, 54) if sky == "day" else (1600, HZ - 40, 80)  # dawn sun clear of the centre stage
        rays = "".join(f'<path d="M{x + (rad + 14) * math.cos(a):.0f} {y + (rad + 14) * math.sin(a):.0f} '
                       f'L{x + (rad + 40) * math.cos(a):.0f} {y + (rad + 40) * math.sin(a):.0f}"/>' for a in (i * math.pi / 6 for i in range(12)))
        out.append(f'<circle {D} cx="{x}" cy="{y}" r="{rad}"/><g stroke="{c}" stroke-width="3" opacity="0.7">{rays}</g>')
    return "".join(out), anims


def _roof(x, y, w, lift=26):
    """The line of a tiled roof with upturned eaves over a wall of width w whose top is at y."""
    a = w / 2 + 22
    return (f'<path {N} d="M{x - a:.0f} {y} Q{x - a * 0.6:.0f} {y - lift * 0.7:.0f} {x - a * 0.4:.0f} {y - lift} '
            f'L{x + a * 0.4:.0f} {y - lift} Q{x + a * 0.6:.0f} {y - lift * 0.7:.0f} {x + a:.0f} {y}"/>')


def _pagoda(tiers=4, w=150, th=64):
    """A pagoda around (0,0) in lines: walls shrinking upwards, each under its own roof, and a spire."""
    out, y = [], 0
    for k in range(tiers):
        ww = w * (1 - 0.15 * k)
        out.append(f'<path {D} d="M{-ww * 0.4:.0f} {y} V{y - th} H{ww * 0.4:.0f} V{y} Z"/>' + _roof(0, y - th, ww))
        y -= th + 22
    return "".join(out) + f'<path {N} d="M0 {y + 22} V{y - 70}"/><circle {D} cx="0" cy="{y - 74}" r="9"/>'


def _pine(x, y, h, w):
    return (f'<path {N} d="M{x - w / 2:.0f} {y} L{x - w / 3:.0f} {y - h * 0.45:.0f} L{x - w / 2:.0f} {y - h * 0.45:.0f} '
            f'L{x:.0f} {y - h:.0f} L{x + w / 2:.0f} {y - h * 0.45:.0f} L{x + w / 3:.0f} {y - h * 0.45:.0f} L{x + w / 2:.0f} {y}"/>')


def land(p, name):
    """The ground, drawn as lines of light; returns (markup, anims)."""
    anims = []
    if name == "hills":
        g = ridge(HZ - 70, 55, 3, 0.5, 0.35) + ridge(HZ - 10, 40, 2.2, 2.0, 0.6) + ridge(GF - 20, 22, 1.6, 4.0)
    elif name == "field":
        r = rng(5)
        tufts = "".join(f'<path {N} d="M{x:.0f} {GF + 30 + r() * 120:.0f} l-6 -{18 + r() * 14:.0f} m6 18 l8 -{14 + r() * 12:.0f}" opacity="0.6"/>'
                        for x in [r() * W for _ in range(60)])
        g = ridge(HZ - 50, 35, 2.5, 1.2, 0.35) + ridge(GF - 10, 14, 1.4, 0.3) + tufts
    elif name == "desert":
        g = ridge(HZ - 30, 26, 2, 1.0, 0.3) + ridge(HZ + 20, 30, 1.3, 2.6, 0.55) + ridge(GF, 12, 1.0, 3.3)
    elif name == "city":  # a village of tiled roofs with a pagoda above them
        houses = [(120, 150, 80), (330, 170, 110), (540, 120, 70), (760, 190, 100), (1180, 150, 90), (980, 200, 120),
                  (1640, 140, 75), (1820, 160, 95)]
        walls = "".join(f'<path {N} d="M{x - w // 2} {HZ + 40} V{HZ - h} H{x + w // 2} V{HZ + 40}"/>' + _roof(x, HZ - h, w)
                        for x, w, h in houses)
        g = (f'<g opacity="0.5">{walls}<g transform="translate(1530,{HZ + 30}) scale(1.1)">{_pagoda()}</g></g>'
             + ridge(GF - 10, 10, 1.2, 0.8))
    elif name in ("sea", "river"):
        r = rng(3)
        if name == "sea":  # a still lake: distant hills, their reflection, and short slow glints
            rows = "".join(f'<path {N} d="M{r() * W:.0f} {y} h{60 + r() * 180:.0f}" opacity="{0.2 + r() * 0.3:.2f}"/>'
                           for y in range(HZ + 40, H, 34))
            mirror = " L".join(f"{x} {HZ + 25 - 18 * math.sin(x / W * 2 * math.pi + 1.5):.0f}" for x in range(-40, W + 81, 60))
            g = ridge(HZ - 25, 18, 2, 1.5, 0.4) + f'<path {N} d="M{mirror}" opacity="0.18"/>' + f'<g id="{p}-waves">{rows}</g>'
            anims.append({"t": f"#{p}-waves", "do": "drift", "amp": 16, "period": 6})
        else:
            waves = "".join(f'<path {N} d="M-120 {y} q30 -12 60 0 {"t60 0 " * ((W + 200) // 60)}" opacity="{0.25 + r() * 0.35:.2f}"/>'
                            for y in range(GF - 40, GF + 140, 45))
            g = ridge(HZ - 60, 40, 2.4, 0.6, 0.35) + ridge(GF - 60, 14, 1.4, 2.2, 0.7) + f'<g id="{p}-waves">{waves}</g>'
            anims.append({"t": f"#{p}-waves", "do": "drift", "amp": 40, "period": 3.4})
    elif name == "garden":  # a grove of trees on the slope
        trees = "".join(f'<g transform="translate({x},{HZ + 10}) scale({s})" opacity="0.45">{PROPS["tree"]}</g>'
                        for x, s in [(180, 0.55), (420, 0.45), (1500, 0.5), (1760, 0.6)])
        g = ridge(HZ - 60, 40, 2.5, 0.2, 0.35) + trees + ridge(GF - 10, 14, 1.5, 1.0)
    elif name == "mountain":
        g = (f'<path {N} d="M-40 {HZ + 20} L380 {HZ - 260} L560 {HZ - 120} L860 {HZ - 420} L1180 {HZ - 140} L1420 {HZ - 300} '
             f'L1960 {HZ + 10}" opacity="0.55"/>' + ridge(GF - 20, 24, 1.6, 4.0))
    elif name == "forest":
        far = "".join(_pine(x, HZ + 10, 200 + (x * 7) % 80, 100) for x in range(-20, W + 60, 90))
        near = "".join(_pine(x, HZ + 60, 300 + (x * 13) % 110, 140) for x in range(40, W + 60, 260))
        g = f'<g opacity="0.3">{far}</g><g opacity="0.55">{near}</g>' + ridge(GF - 10, 12, 1.4, 2.0)
    elif name == "zen":  # a raked-sand garden behind a low wall, with three stones and rings raked around them
        stones = [(420, GF + 110, 60), (1180, GF + 150, 90), (1560, GF + 80, 44)]
        rakes = "".join(f'<path {N} d="M0 {y} H{W}" opacity="0.18"/>' for y in range(GF + 20, H, 26))
        rings = "".join(f'<ellipse {N} cx="{x}" cy="{y}" rx="{rr + k * 30}" ry="{(rr + k * 30) * 0.3:.0f}" opacity="0.4"/>'
                        for x, y, rr in stones for k in (1, 2, 3))
        g = (f'<path {N} d="M0 {HZ - 60} H{W} M0 {HZ - 48} H{W} M0 {GF - 10} H{W}" opacity="0.45"/>' + rakes + rings
             + "".join(f'<ellipse {D} cx="{x}" cy="{y - rr * 0.3:.0f}" rx="{rr}" ry="{rr * 0.55:.0f}"/>' for x, y, rr in stones))
    else:
        raise ValueError(f"unknown land {name!r}")
    return g, anims


# Props: (0,0) is the point that touches the ground. Ids with {pid} let actions find a part (flames, a cage door).
PROPS = {
    "boat": f'<path {D} d="M-210 -40 L210 -40 L160 40 L-160 40 Z"/><path {N} d="M0 -40 V-330"/><path {D} d="M8 -320 L8 -70 L170 -70 Z"/>',
    "lamp": f'<path {D} d="M-40 -10 Q0 10 40 -10 L30 -30 L-30 -30 Z"/><path {N} d="M40 -22 L70 -34 L60 -18"/>'
            f'<path id="{{pid}}-flame" {F} d="M66 -36 C60 -60 72 -66 74 -84 C80 -66 88 -60 80 -36 Z"/>',
    "tree": f'<path {N} d="M-14 0 C-8 -90 -12 -170 0 -240 C10 -170 8 -90 14 0"/>'
            f'<circle {D} cx="-70" cy="-280" r="85"/><circle {D} cx="60" cy="-300" r="95"/><circle {D} cx="0" cy="-380" r="100"/>',
    "stone": f'<circle {D} cx="0" cy="-95" r="95"/><circle {N} cx="0" cy="-95" r="60"/>',
    "rock": f'<path {D} d="M-230 0 C-240 -90 -150 -170 -20 -160 C110 -170 240 -100 230 0 Z"/>',
    "star": f'<path {F} d="M0 -70 L14 -14 L70 0 L14 14 L0 70 L-14 14 L-70 0 L-14 -14 Z"/><path {N} d="M0 -170 V170 M-170 0 H170" opacity="0.5"/>',
    "dove": f'<path {D} d="M-40 0 Q-10 -20 20 -6 Q40 -30 70 -40 Q52 -12 30 2 Q50 4 64 14 Q30 14 10 8 Q-20 14 -40 0 Z"/>',
    "bread": f'<ellipse {D} cx="-46" cy="-22" rx="44" ry="22"/><ellipse {D} cx="40" cy="-22" rx="44" ry="22"/><ellipse {D} cx="-4" cy="-52" rx="44" ry="22"/>',
    "fish": f'<path {D} d="M-30 -20 Q0 -44 30 -20 Q0 4 -30 -20 Z M30 -20 L48 -34 L48 -6 Z"/>',
    "cup": f'<path {D} d="M-44 -44 H44 C44 -14 26 0 0 0 C-26 0 -44 -14 -44 -44 Z"/><ellipse {N} cx="0" cy="-44" rx="40" ry="8"/>',
    "scroll": f'<path {D} d="M-90 -150 H90 V-20 H-90 Z"/><path {N} d="M-100 -160 V-10 M100 -160 V-10 M-60 -115 H60 M-60 -85 H60 M-60 -55 H30"/>',
    "sheep": f'<circle {D} cx="-30" cy="-60" r="30"/><circle {D} cx="5" cy="-70" r="34"/><circle {D} cx="35" cy="-58" r="28"/>'
             f'<ellipse {D} cx="68" cy="-72" rx="18" ry="14"/><path {N} d="M-26 -32 V0 M28 -32 V0"/>',
    "well": f'<path {D} d="M-110 0 V-120 H110 V0 Z"/><path {N} d="M-125 -124 H125 M-90 -124 V-300 M90 -124 V-300 M-110 -300 H110"/>',
    "house": f'<path {N} d="M-150 0 V-210 H150 V0 M-170 -216 H170"/><path {D} d="M-40 0 V-120 H20 V0"/><path {D} d="M70 -170 H110 V-130 H70 Z"/>',
    "table": f'<path {N} d="M-200 -90 H200 M-180 -90 V0 M180 -90 V0"/><ellipse {D} cx="-60" cy="-104" rx="44" ry="14"/>'
             f'<ellipse {D} cx="60" cy="-100" rx="34" ry="10"/>',
    "net": f'<path {N} d="M-160 0 Q0 -60 160 0 M-160 0 L-120 -80 M-80 -30 L-60 -100 M0 -40 L0 -110 M80 -30 L60 -100 M160 0 L120 -80 '
           f'M-130 -50 Q0 -100 130 -50 M-110 -85 Q0 -125 110 -85"/>',
    "basket": f'<path {D} d="M-70 -50 L70 -50 L55 0 L-55 0 Z"/><path {N} d="M-60 -50 Q0 -120 60 -50"/>',
    "fire": f'<path {N} d="M-60 0 L60 -14 M-60 -14 L60 0"/><path id="{{pid}}-flame" {F} d="M-28 -14 C-34 -60 -6 -70 0 -110 C10 -70 36 -60 28 -14 Z"/>',
    "stones": f'<ellipse {D} cx="-40" cy="-14" rx="26" ry="16"/><ellipse {D} cx="10" cy="-12" rx="20" ry="13"/><ellipse {D} cx="50" cy="-16" rx="28" ry="17"/>',
    "mat": f'<path {D} d="M-110 0 V-14 H110 V0 Z"/>',
    "birds": f'<path {N} d="M0 0 q14 -12 28 0 q14 -12 28 0 M70 -40 q10 -9 20 0 q10 -9 20 0 M-60 -30 q11 -10 22 0 q11 -10 22 0"/>',
    "jar": f'<path {D} d="M-38 0 C-60 -40 -60 -120 -30 -150 L-24 -175 L24 -175 L30 -150 C60 -120 60 -40 38 0 Z"/>',
    "plant": f'<path {N} d="M0 0 Q-4 -60 0 -120 M0 -50 Q-40 -70 -48 -100 M0 -80 Q40 -100 46 -130"/><circle {F} cx="0" cy="-128" r="10"/>',
    "seed": f'<circle {F} cx="0" cy="-8" r="8"/><circle {N} cx="0" cy="-8" r="26" opacity="0.5"/>',
    "coin": f'<circle {F} cx="0" cy="-12" r="12"/>',
    "chest": f'<path {D} d="M-80 0 V-90 H80 V0 Z"/><path {N} d="M-90 -90 Q0 -140 90 -90"/>',
    "lotus": f'<ellipse {N} cx="0" cy="-4" rx="95" ry="14"/><path {D} d="M0 -10 C-34 -18 -64 -46 -66 -74 C-38 -66 -14 -44 0 -10 Z"/>'
             f'<path {D} d="M0 -10 C34 -18 64 -46 66 -74 C38 -66 14 -44 0 -10 Z"/><path {F} d="M0 -10 C-20 -40 -12 -82 0 -104 C12 -82 20 -40 0 -10 Z"/>',
    "bodhi": f'<path {N} d="M-30 0 C-20 -120 -40 -220 -10 -300 M30 0 C22 -120 40 -220 12 -300 M-6 -250 C-60 -270 -120 -300 -170 -330 '
             f'M8 -260 C60 -280 130 -300 180 -340"/><ellipse {D} cx="0" cy="-400" rx="300" ry="120"/>'
             f'<ellipse {D} cx="-170" cy="-350" rx="140" ry="90"/><ellipse {D} cx="180" cy="-355" rx="150" ry="95"/>',
    "bamboo": "".join(f'<path {N} d="M{x} 0 V-{h}' + "".join(f" M{x - 10} -{y} H{x + 10}" for y in range(90, h, 90)) + '"/>'
                      f'<path {D} d="M{x} -{h - 40} q40 -10 70 -40 q-40 6 -70 30 Z"/>' for x, h in [(-50, 560), (0, 620), (46, 520)]),
    "bell": f'<path {N} d="M-112 0 V-330 M112 0 V-330 M-150 -330 Q0 -360 150 -330 M0 -330 V-282"/>'
            f'<path {D} d="M-58 -120 C-58 -220 -46 -282 0 -282 C46 -282 58 -220 58 -120 Z"/><path {N} d="M-70 -116 H70"/>',
    "teapot": f'<ellipse {D} cx="0" cy="-50" rx="62" ry="50"/><path {N} d="M52 -58 Q90 -70 104 -108 M-56 -80 C-100 -84 -100 -20 -56 -26"/>'
              f'<ellipse {D} cx="0" cy="-100" rx="26" ry="8"/>',
    "candle": f'<path {D} d="M-16 0 V-110 H16 V0 Z"/><path id="{{pid}}-flame" {F} d="M-9 -122 C-12 -140 -2 -146 0 -166 C4 -146 12 -140 9 -122 Z"/>',
    "cushion": f'<path {D} d="M-80 0 C-92 -44 -50 -58 0 -58 C50 -58 92 -44 80 0 Z"/>',
    "pagoda": _pagoda(),
    "hut": f'<path {D} d="M-110 0 V-130 H110 V0 Z"/><path {D} d="M-150 -120 L0 -250 L150 -120 Z"/><path {N} d="M-26 0 V-80 H26 V0"/>',
    "bridge": f'<path {N} d="M-280 0 Q0 -170 280 0 M-260 -40 Q0 -210 260 -40'
              + "".join(f" M{x} {-40 - 170 * (1 - (x / 260) ** 2) * 0.82:.0f} V{-170 * (1 - (x / 260) ** 2) * 0.82 + 6:.0f}"
                        for x in (-200, -100, 0, 100, 200)) + '"/>',
    "gate": f'<path {N} d="M-137 0 V-390 M137 0 V-390 M-180 -320 H180"/><path {D} d="M-220 -400 Q0 -380 220 -400 L230 -440 Q0 -410 -230 -440 Z"/>',
    "flute": f'<path {D} d="M-70 0 V-10 H70 V0 Z"/>',
    "drum": f'<path {D} d="M-60 0 V-90 H60 V0 Z"/><ellipse {D} cx="0" cy="-90" rx="60" ry="16"/>',
    "donkey": f'<ellipse {D} cx="0" cy="-110" rx="90" ry="44"/><path {D} d="M70 -130 L112 -190 L140 -176 L104 -110 Z"/>'
              f'<path {N} d="M112 -192 L104 -236 M128 -190 L132 -232 M-60 -76 V0 M-28 -72 V0 M36 -72 V0 M64 -76 V0 M-88 -118 Q-118 -100 -110 -60"/>',
    "cage": f'<path {N} d="M-60 -200 Q0 -260 60 -200 M-70 0 H70 M-60 -200 V0 M-36 -200 V0 M-12 -200 V0"/>'
            f'<path id="{{pid}}-bird" {F} d="M-6 -70 Q8 -96 26 -82 Q34 -92 44 -88 L36 -78 Q30 -56 4 -56 Z"/>'
            f'<g id="{{pid}}-door"><path {N} d="M12 -200 V0 M36 -200 V0 M60 -200 V0"/></g>',
    "rope": f'<path {N} d="M-130 -8 C-90 -34 -50 18 -10 -8 C30 -34 70 18 110 -8 Q130 -20 140 -10"/>',
    "mirror": f'<path {N} d="M0 0 V-160 M-50 0 H50"/><ellipse {D} cx="0" cy="-250" rx="72" ry="96"/><ellipse {N} cx="0" cy="-250" rx="58" ry="82"/>',
    "ladder": f'<path {N} d="M-54 0 V-520 M54 0 V-520' + "".join(f" M-54 -{y} H54" for y in range(60, 520, 70)) + '"/>',
    "cloud": f'<path {D} d="M-130 0 H120 A55 55 0 0 0 70 -90 A70 70 0 0 0 -60 -100 A50 50 0 0 0 -130 0 Z"/>',
    "butterfly": f'<path {F} d="M0 -20 C-30 -60 -70 -50 -60 -20 C-70 6 -30 10 0 -14 Z"/><path {F} d="M0 -20 C30 -60 70 -50 60 -20 C70 6 30 10 0 -14 Z"/>',
    "moon": f'<circle cx="0" cy="-150" r="300" fill="url(#{{p}}-halo)"/><circle {D} cx="0" cy="-150" r="150"/>',
}
PEOPLE = {"master", "seeker", "monk", "nun", "man", "woman", "child", "elder", "dancer", "samurai", "farmer", "nasruddin"}
SIZES = {"child": 0.62, "master": 1.06}


def person(pid, kind):
    """A robed figure 190 units tall, in lines; never a face. Arms are groups -al / -ar that rotate at the shoulder;
    the whole drawing is -s (breathe scales it without undoing a sit on the body group)."""
    robe = {"master": "M-40 0 C-36 -60 -28 -118 -18 -150 Q0 -160 18 -150 C28 -118 36 -60 40 0 Z",
            "dancer": "M-74 0 Q-40 -50 -20 -110 C-20 -130 -17 -145 -17 -150 Q0 -160 17 -150 C17 -145 20 -130 20 -110 Q40 -50 74 0 Z",
            "samurai": "M-42 0 C-34 -60 -30 -110 -30 -150 Q0 -160 30 -150 C30 -110 34 -60 42 0 Z"}.get(
        kind, "M-30 0 C-28 -60 -24 -118 -17 -150 Q0 -160 17 -150 C24 -118 28 -60 30 0 Z")
    parts = [f'<path {O} d="{robe}"/><circle {O} cx="0" cy="-172" r="15"/>']
    if kind == "woman":
        parts.append(f'<path {N} d="M-26 -136 L-18 -180 Q0 -204 18 -180 L26 -136"/>')
    if kind == "nun":
        parts.append(f'<path {N} d="M-32 -116 L-20 -182 Q0 -206 20 -182 L32 -116"/>')
    if kind == "elder":
        parts.append(f'<path {N} d="M38 2 L38 -205 Q38 -228 56 -222"/>')
    if kind == "farmer":
        parts.append(f'<path {O} d="M-50 -176 L0 -204 L50 -176 Z"/>')
    if kind == "nasruddin":
        parts.append(f'<ellipse {O} cx="0" cy="-188" rx="22" ry="15"/><path {N} d="M-12 -164 Q0 -134 12 -164"/>')
    if kind == "samurai":
        parts.append(f'<circle {O} cx="0" cy="-192" r="6"/><path {N} d="M-36 -70 L44 -120"/>')
    arm = f'<path {N} d="M0 0 L2 72"/>'
    parts.append(f'<g id="{pid}-al" class="arm-l" transform="translate(-15,-146)">{arm}</g>'
                 f'<g id="{pid}-ar" class="arm-r" transform="translate(15,-146)">{arm}</g>')
    return f'<g id="{pid}-s">{"".join(parts)}</g>'


def place(pid, k, x, y, s, flip, inner, p):
    """Outer group moves (walk, climb); inner -b bends about the feet (sit, bow, lie, rock, grow)."""
    if k in PEOPLE:
        body = person(pid, k)
        s *= SIZES.get(k, 1.0)
    elif k in PROPS:
        body = PROPS[k].replace("{pid}", pid).replace("{p}", p).replace(D, O)  # props stand as cut-outs too
    else:
        raise ValueError(f"unknown cast kind {k!r}")
    # The master carries a soft light; it stays outside the body group so sit/bow/lie pivot at the feet.
    glow = (f'<circle id="{pid}-glow" cx="0" cy="-120" r="170" fill="url(#{p}-halo)" opacity="0.8"/>' if k == "master" else "")
    return (f'<g id="{pid}" transform="translate({x},{y}) scale({-s if flip else s},{s})">{glow}'
            f'<g id="{pid}-b" class="body">{inner}{body}</g></g>')


def crowd(pid, x, y, s, n, seed=9):
    r = rng(seed)
    figs = []
    for i in range(n):
        fx_ = x + (i - (n - 1) / 2) * 62 * s + (r() - 0.5) * 20
        fs = s * (0.85 + r() * 0.25)
        kind = "woman" if r() < 0.35 else ("child" if r() < 0.15 else "man")
        figs.append(f'<g transform="translate({fx_:.0f},{y + r() * 14:.0f}) scale({fs * (0.62 if kind == "child" else 1):.2f})">'
                    f'{person(f"{pid}-{i}", kind)}</g>')
    return f'<g id="{pid}"><g id="{pid}-b" class="body" opacity="0.75">{"".join(figs)}</g></g>'


def fx(p, name):
    """Full-frame effects; returns (markup, anims)."""
    c = T["line"]
    if name == "rain":
        r = rng(13)
        drops = "".join(f'<path d="M{r() * (W + 200):.0f} {r() * 2 * H:.0f} l-14 46"/>' for _ in range(200))
        return (f'<g id="{p}-rain" stroke="{c}" stroke-width="2" stroke-opacity="0.35" stroke-linecap="round">{drops}</g>',
                [{"t": f"#{p}-rain", "do": "rain"}])
    if name == "lightning":
        return (f'<path id="{p}-bolt" d="M1140 0 L1060 210 L1140 210 L1020 450 L1200 180 L1115 180 L1200 0 Z" fill="none" '
                f'stroke="#f4f7ff" stroke-width="4" opacity="0"/><rect id="{p}-flash" width="{W}" height="{H}" fill="#e8eeff" opacity="0"/>',
                [{"t": f"#{p}-flash", "do": "flash", "bolt": f"#{p}-bolt"}])
    if name == "rays":
        rays = "".join(f'<path {N} d="M{W // 2} -60 L{W // 2 + 1100 * math.sin(a):.0f} {HZ * math.cos(a):.0f}"/>'
                       for a in [i * 0.16 - 0.88 for i in range(12)])
        return f'<g id="{p}-rays" opacity="0">{rays}</g>', [{"t": f"#{p}-rays", "do": "rays"}]
    if name == "sparkle":
        r = rng(17)
        sp = "".join(f'<path d="M{x:.0f} {y - 14:.0f} l4 10 l10 4 l-10 4 l-4 10 l-4 -10 l-10 -4 l10 -4 Z"/>'
                     for x, y in ((200 + r() * 1520, 140 + r() * 620) for _ in range(34)))
        return f'<g id="{p}-sparkle" fill="{T["dot"]}" opacity="0">{sp}</g>', [{"t": f"#{p}-sparkle", "do": "sparkle"}]
    if name == "dove":  # a white bird coming down out of an opened sky
        return (f'<g id="{p}-dove" transform="translate({W // 2},40) scale(1.2)" opacity="0">{PROPS["dove"]}</g>'
                f'<path {N} d="M{W // 2 - 220} 0 Q{W // 2} 120 {W // 2 + 220} 0" opacity="0.8"/>',
                [{"t": f"#{p}-dove", "do": "descend", "by": 380}])
    if name == "petals":  # blossom drifting down; placed above the frame too, so the whole beat has petals
        r = rng(31)
        ps = "".join(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="8" ry="4" transform="rotate({r() * 180:.0f} {x:.0f} {y:.0f})" '
                     f'opacity="{0.4 + r() * 0.5:.2f}"/>' for x, y in ((r() * W, -500 + r() * (H + 400)) for _ in range(60)))
        return f'<g id="{p}-petals" fill="{T["glow"]}">{ps}</g>', [{"t": f"#{p}-petals", "do": "petals", "by": 420}]
    if name == "mist":  # two soft bands of light fog drifting slowly in opposite directions
        return (f'<defs><linearGradient id="{p}-mistg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c}" stop-opacity="0"/>'
                f'<stop offset="0.5" stop-color="{c}" stop-opacity="0.16"/><stop offset="1" stop-color="{c}" stop-opacity="0"/>'
                f'</linearGradient></defs><g id="{p}-mist"><rect id="{p}-mist-a" x="-300" y="{HZ - 160}" width="{W + 600}" height="180" '
                f'fill="url(#{p}-mistg)"/><rect id="{p}-mist-c" x="-300" y="{HZ + 30}" width="{W + 600}" height="220" '
                f'fill="url(#{p}-mistg)" opacity="0.8"/></g>', [{"t": f"#{p}-mist", "do": "mist"}])
    if name == "ripples":  # rings spreading on still water
        rings = "".join(f'<ellipse cx="{W // 2}" cy="{GF + 120}" rx="220" ry="40"/>' for _ in range(3))
        return (f'<g id="{p}-ripples" fill="none" stroke="{c}" stroke-width="2.5" stroke-opacity="0.7">{rings}</g>',
                [{"t": f"#{p}-ripples", "do": "ripples"}])
    if name == "fireflies":
        r = rng(37)
        dots = "".join(f'<circle cx="{r() * W:.0f}" cy="{300 + r() * 700:.0f}" r="{2.5 + r() * 2.5:.1f}"/>' for _ in range(50))
        return f'<g id="{p}-fireflies" fill="{T["dot"]}">{dots}</g>', [{"t": f"#{p}-fireflies", "do": "fireflies"}]
    raise ValueError(f"unknown fx {name!r}")


FX = {"rain", "lightning", "rays", "sparkle", "dove", "petals", "mist", "ripples", "fireflies"}
