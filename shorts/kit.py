"""Paper-cut silhouette kit for 1080x1920 story Shorts, in two styles: silhouette (warm skies) and inkwash (sumi-e).

Everything is drawn as SVG markup; motion is described as plain dicts that the page's small GSAP interpreter
turns into tweens, so every frame is deterministic and seekable. Coordinates: x across 0-1080, y down 0-1920,
the horizon at HZ, and every character or prop is placed by the point where it touches the ground.
"""
import math

W, H, HZ = 1080, 1920, 1300
INK = "#140f17"          # the silhouette colour
FEET = 1390              # where characters on the near ground stand

SKIES = {  # top, middle, horizon colours, and an optional sun/moon (kind, x, y, radius)
    "dawn": ("#2a3550", "#b88a7a", "#f3d2a6", ("sun", 760, 1170, 70)),        # misty dawn
    "day": ("#4a78a8", "#a9c6d8", "#f5e4bd", ("sun", 930, 430, 58)),
    "dusk": ("#3a1c2e", "#b8502e", "#f6a040", ("sun", 300, 1160, 110)),       # saffron dusk
    "night": ("#070820", "#1a1c4a", "#35306a", ("moon", 800, 400, 52)),       # indigo night
    "storm": ("#0b0e15", "#262e3b", "#465163", None),
}


SILHOUETTE = dict(ink=INK, skies=SKIES, c=dict(wave="#dfe8ff", sea="#3a4a6a", hole="#030206", rain="#c9d6ec",
                 rays="#fff1c8", spark="#fff3c4", star="#fff", sun="#fff4d6", moon="#e9ecf5", rim="#ffe6b8",
                 petal="#f6c9d2", mist="#e6e2f0", fly="#fbe98a"))
# sumi-e: near-black ink on rice paper, grey wash ridges (the ink at low opacity), a red seal sun
INKWASH = dict(ink="#1a1714", c=dict(wave="#4a4540", sea="#c9bfae", hole="#2a2420", rain="#5a544c", rays="#fffaf0",
                                     spark="#a3302a", star="#6b625a", sun="#a3302a", moon="#f6f1e6", rim="#f7f2e8",
                                     petal="#c2534a", mist="#f7f3ea", fly="#a3302a"),
               skies={"day": ("#efe8da", "#e6dccb", "#d9cfbd", ("sun", 930, 430, 58)),
                      "dawn": ("#efe8da", "#e8dccb", "#dccbb4", ("sun", 760, 1170, 70)),
                      "dusk": ("#ece2d2", "#e0cdb4", "#cfb79a", ("sun", 300, 1160, 110)),
                      "night": ("#d6cebf", "#cbc2b2", "#bdb3a2", ("moon", 800, 400, 52)),
                      "storm": ("#cfc8bb", "#bfb7a9", "#aaa294", None)})
STYLES = {"silhouette": SILHOUETTE, "inkwash": INKWASH}
C = SILHOUETTE["c"]


def use(style):
    """Switch every drawing function to a style's palette (module-level, one story is built per process)."""
    global INK, SKIES, C
    st = STYLES[style]
    INK, SKIES, C = st["ink"], st["skies"], st["c"]


def rng(seed):
    """Seeded pseudo-random numbers, so 'random' stars and raindrops are identical on every render."""
    s = seed & 0x7FFFFFFF

    def r():
        nonlocal s
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        return s / 0x7FFFFFFF
    return r


def sky(p, name, orb_shown=True):
    top, mid, low, orb = SKIES[name]
    out = [f'<defs><linearGradient id="{p}-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
           f'<stop offset="0.5" stop-color="{mid}"/><stop offset="0.68" stop-color="{low}"/><stop offset="1" stop-color="{low}"/>'
           f'</linearGradient><radialGradient id="{p}-halo"><stop offset="0" stop-color="#ffe9b0" stop-opacity="0.9"/>'
           f'<stop offset="1" stop-color="#ffe9b0" stop-opacity="0"/></radialGradient></defs>',
           f'<rect width="{W}" height="{H}" fill="url(#{p}-sky)"/>']
    anims = []
    if name in ("night", "storm"):
        r = rng(7 if name == "night" else 11)
        stars = "".join(f'<circle cx="{r() * W:.0f}" cy="{r() * 950:.0f}" r="{1 + r() * 2.2:.1f}" fill="{C["star"]}" '
                        f'opacity="{0.35 + r() * 0.65:.2f}"/>' for _ in range(110 if name == "night" else 0))
        out.append(f'<g id="{p}-stars">{stars}</g>')
        if name == "night":
            anims.append({"t": f"#{p}-stars", "do": "twinkle"})
    if orb and orb_shown:  # off when the cast brings its own moon
        kind, x, y, rad = orb
        col = C["sun"] if kind == "sun" else C["moon"]
        out.append(f'<circle cx="{x}" cy="{y}" r="{rad * 3.2}" fill="url(#{p}-halo)" opacity="0.55"/>'
                   f'<circle cx="{x}" cy="{y}" r="{rad}" fill="{col}"/>')
    return "".join(out), anims


def ridge(base, amp, waves, phase, op=1.0, fill=None):
    fill = fill or INK
    pts = " L".join(f"{x} {base + amp * math.sin(x / W * waves * math.pi + phase):.0f}" for x in range(-40, W + 81, 60))
    return f'<path d="M-40 {H} L{pts} L{W + 40} {H} Z" fill="{fill}" opacity="{op}"/>'


def _roof(x, y, w, lift=26):
    """A tiled roof with upturned eaves over a wall of width w whose top is at y."""
    a = w / 2 + 22
    return (f'<path d="M{x - a:.0f} {y} Q{x - a * 0.6:.0f} {y - lift * 0.7:.0f} {x - a * 0.4:.0f} {y - lift} '
            f'L{x + a * 0.4:.0f} {y - lift} Q{x + a * 0.6:.0f} {y - lift * 0.7:.0f} {x + a:.0f} {y} Z"/>')


def _pagoda(tiers=4, w=150, th=64):
    """A pagoda around (0,0): walls shrinking upwards, each under its own roof, and a spire."""
    out, y = [], 0
    for k in range(tiers):
        ww = w * (1 - 0.15 * k)
        out.append(f'<rect x="{-ww * 0.4:.0f}" y="{y - th}" width="{ww * 0.8:.0f}" height="{th}"/>' + _roof(0, y - th, ww))
        y -= th + 22
    return "".join(out) + f'<rect x="-4" y="{y - 70}" width="8" height="80"/><circle cx="0" cy="{y - 74}" r="9"/>'


def _pine(x, y, h, w):
    return (f'<path d="M{x:.0f} {y - h:.0f} L{x + w / 2:.0f} {y - h * 0.45:.0f} L{x + w / 3:.0f} {y - h * 0.45:.0f} '
            f'L{x + w / 2:.0f} {y} L{x - w / 2:.0f} {y} L{x - w / 3:.0f} {y - h * 0.45:.0f} L{x - w / 2:.0f} {y - h * 0.45:.0f} Z"/>')


def ground(p, name):
    """The landscape layers in front of the sky; returns (markup, anims)."""
    anims = []
    if name == "hills":
        g = ridge(HZ - 70, 55, 3, 0.5, 0.42) + ridge(HZ - 10, 40, 2.2, 2.0, 0.7) + ridge(FEET - 20, 22, 1.6, 4.0)
    elif name == "field":
        r = rng(5)
        tufts = "".join(f'<path d="M{x:.0f} {FEET + 8} l-6 -{18 + r() * 14:.0f} l6 10 l6 -{14 + r() * 12:.0f} l4 14 Z"/>'
                        for x in [r() * W for _ in range(40)])
        g = ridge(HZ - 50, 35, 2.5, 1.2, 0.42) + ridge(FEET - 10, 14, 1.4, 0.3) + f'<g fill="{INK}">{tufts}</g>'
    elif name == "desert":
        g = ridge(HZ - 30, 26, 2, 1.0, 0.38) + ridge(HZ + 20, 30, 1.3, 2.6, 0.62) + ridge(FEET, 12, 1.0, 3.3)
    elif name == "city":  # a village of tiled roofs with a pagoda above them
        houses = "".join(f'<rect x="{x - w / 2:.0f}" y="{HZ - h}" width="{w}" height="{h + 40}"/>' + _roof(x, HZ - h, w)
                         for x, w, h in [(70, 110, 70), (210, 130, 95), (360, 100, 60), (520, 150, 85), (690, 110, 65),
                                         (980, 120, 80)])
        g = (f'<g fill="{INK}" opacity="0.55">{houses}<g transform="translate(840,{HZ}) scale(0.9)">{_pagoda()}</g>'
             f'<rect x="0" y="{HZ - 30}" width="{W}" height="70"/></g>' + ridge(FEET - 10, 10, 1.2, 0.8))
    elif name == "sea":  # a still lake: distant hills, their reflection, and a few slow glints on the water
        r = rng(3)
        mirror = " L".join(f"{x} {HZ + 25 - 18 * math.sin(x / W * 2 * math.pi + 1.5):.0f}" for x in range(-40, W + 81, 60))
        glints = "".join(f'<path d="M{r() * W:.0f} {y:.0f} h{40 + r() * 120:.0f}" stroke-opacity="{0.08 + r() * 0.14:.2f}"/>'
                         for y in range(HZ + 50, H, 46))
        g = (ridge(HZ - 25, 18, 2, 1.5, 0.45)
             + f'<defs><linearGradient id="{p}-sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["sea"]}"/>'
               f'<stop offset="1" stop-color="{INK}"/></linearGradient></defs>'
             + f'<rect x="0" y="{HZ}" width="{W}" height="{H - HZ}" fill="url(#{p}-sea)"/>'
             + f'<path d="M-40 {HZ} L{mirror} L{W + 40} {HZ} Z" fill="{INK}" opacity="0.18"/>'
             + f'<g id="{p}-waves" fill="none" stroke="{C["wave"]}" stroke-width="3" stroke-linecap="round">{glints}</g>')
        anims.append({"t": f"#{p}-waves", "do": "drift", "amp": 14, "period": 6})
    elif name == "garden":
        bushes = "".join(f'<circle cx="{x}" cy="{FEET - 20}" r="{rr}"/>' for x, rr in [(60, 70), (150, 50), (930, 60), (1030, 80)])
        g = ridge(HZ - 60, 40, 2.5, 0.2, 0.42) + ridge(FEET - 10, 14, 1.5, 1.0) + f'<g fill="{INK}">{bushes}</g>'
    elif name == "forest":
        far = "".join(_pine(x, HZ, 230 + (x * 7) % 90, 110) for x in range(-20, W + 60, 75))
        near = "".join(_pine(x, HZ + 50, 330 + (x * 13) % 120, 150) for x in range(20, W + 60, 160))
        g = (f'<g fill="{INK}"><g opacity="0.35">{far}</g><g opacity="0.65">{near}</g></g>' + ridge(FEET - 10, 12, 1.4, 2.0))
    elif name == "river":
        r = rng(19)
        band = (f'<path d="M-40 {FEET + 130} C300 {FEET + 70} 700 {FEET + 230} {W + 40} {FEET + 150} L{W + 40} {FEET + 290} '
                f'C700 {FEET + 370} 300 {FEET + 200} -40 {FEET + 270} Z" fill="{C["sea"]}" opacity="0.85"/>')
        lines = "".join(f'<path d="M{r() * W:.0f} {FEET + 160 + r() * 120:.0f} h{40 + r() * 70:.0f}"/>' for _ in range(16))
        g = (ridge(HZ - 60, 45, 2.4, 0.6, 0.42) + ridge(FEET - 10, 14, 1.4, 2.2) + band
             + f'<g id="{p}-waves" fill="none" stroke="{C["wave"]}" stroke-width="3" stroke-opacity="0.3">{lines}</g>')
        anims.append({"t": f"#{p}-waves", "do": "drift", "amp": 30, "period": 4})
    elif name == "zen":  # a raked-sand garden behind a low wall, three stones with rings raked around them
        rakes = "".join(f'<path d="M0 {y} H{W}"/>' for y in range(FEET + 30, H, 30))
        stones = [(250, FEET + 160, 60), (640, FEET + 260, 85), (900, FEET + 120, 40)]
        rings = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rr + k * 26}" ry="{(rr + k * 26) * 0.4:.0f}" fill="{INK}"/>'
                        for x, y, rr in stones for k in (3, 2, 1))
        g = (f'<rect x="0" y="{HZ - 70}" width="{W}" height="80" fill="{INK}" opacity="0.5"/>'
             f'<rect x="-10" y="{HZ - 84}" width="{W + 20}" height="18" fill="{INK}" opacity="0.6"/>'
             f'<rect x="0" y="{FEET - 10}" width="{W}" height="{H - FEET + 10}" fill="{INK}"/>'
             f'<g fill="none" stroke="{C["wave"]}" stroke-width="2" stroke-opacity="0.16">{rakes}'
             f'<g stroke-opacity="1">{rings}</g></g>'
             + "".join(f'<ellipse cx="{x}" cy="{y - rr * 0.3:.0f}" rx="{rr}" ry="{rr * 0.6:.0f}" fill="{INK}" stroke="{C["rim"]}" '
                       f'stroke-width="2" stroke-opacity="0.5"/>' for x, y, rr in stones))
    elif name == "mountain":
        g = (f'<path d="M-40 {HZ + 20} L240 {HZ - 420} L380 {HZ - 250} L560 {HZ - 620} L760 {HZ - 300} L900 {HZ - 440} '
             f'L1120 {HZ} L1120 {H} L-40 {H} Z" fill="{INK}" opacity="0.45"/>'
             + ridge(HZ - 10, 40, 2.2, 2.0, 0.7) + ridge(FEET - 20, 22, 1.6, 4.0))
    else:
        raise ValueError(f"unknown ground {name!r}")
    return g, anims


# Props: drawn in INK unless they carry their own colour; (0,0) is the point that touches the ground.
# Parts named with {pid} can be found by an action (a flame flickers, a cup's tea changes, a cage door opens).
PROPS = {
    "boat": '<path d="M-210 -40 L210 -40 L160 40 L-160 40 Z"/><rect x="-6" y="-330" width="10" height="300"/>'
            '<path d="M6 -320 L6 -70 L170 -70 Z" opacity="0.92"/>',
    "tree": '<path d="M-18 0 C-12 -90 -14 -180 -4 -260 L8 -260 C16 -180 14 -90 22 0 Z"/>'
            '<circle cx="-70" cy="-300" r="95"/><circle cx="60" cy="-320" r="105"/><circle cx="0" cy="-400" r="110"/>'
            '<circle cx="-120" cy="-230" r="60"/><circle cx="125" cy="-240" r="70"/>',
    "house": '<path d="M-150 0 V-210 H150 V0 Z"/><rect x="-170" y="-230" width="340" height="26"/>'
             '<rect x="-40" y="-120" width="60" height="120" fill="#f0b45a" opacity="0.85"/>'
             '<rect x="70" y="-170" width="40" height="40" fill="#f0b45a" opacity="0.85"/>',
    "rock": '<path d="M-230 0 C-240 -90 -150 -170 -20 -160 C110 -170 240 -100 230 0 Z"/>',
    "jar": '<path d="M-38 0 C-60 -40 -60 -120 -30 -150 L-24 -175 L24 -175 L30 -150 C60 -120 60 -40 38 0 Z"/>'
           '<rect id="{pid}-liq" x="-30" y="-150" width="60" height="130" rx="20" fill="#5d86b8" opacity="0.9"/>',
    "basket": '<path d="M-70 -50 L70 -50 L55 0 L-55 0 Z"/><circle cx="-35" cy="-56" r="18" fill="#c99a5b"/>'
              '<circle cx="0" cy="-62" r="20" fill="#d8a866"/><circle cx="35" cy="-56" r="18" fill="#c99a5b"/>',
    "sheep": '<circle cx="-30" cy="-60" r="30" fill="#efe6d4"/><circle cx="5" cy="-70" r="34" fill="#efe6d4"/>'
             '<circle cx="35" cy="-58" r="28" fill="#efe6d4"/><ellipse cx="68" cy="-72" rx="18" ry="14"/>'
             '<rect x="-30" y="-35" width="7" height="35"/><rect x="25" y="-35" width="7" height="35"/>',
    "table": '<rect x="-170" y="-90" width="340" height="18"/><rect x="-150" y="-80" width="14" height="80"/>'
             '<rect x="136" y="-80" width="14" height="80"/><ellipse cx="-30" cy="-102" rx="45" ry="14" fill="#d8a866"/>'
             '<path d="M60 -90 L72 -130 L98 -130 L110 -90 Z" fill="#7a1f35"/>',
    "stone": '<circle cx="0" cy="-95" r="95"/><circle cx="0" cy="-95" r="60" fill="none" stroke="#2a2230" stroke-width="6"/>',
    "coin": '<circle cx="0" cy="-12" r="12" fill="#f2c96b"/><circle cx="0" cy="-12" r="26" fill="#f2c96b" opacity="0.25"/>',
    "seed": '<circle cx="0" cy="-8" r="8" fill="#f6d78b"/><circle cx="0" cy="-8" r="30" fill="#f6d78b" opacity="0.22"/>',
    "plant": '<path d="M-3 0 Q-6 -60 0 -120 Q6 -60 3 0 Z"/><path d="M0 -50 Q-40 -70 -48 -100 Q-14 -90 0 -60 Z"/>'
             '<path d="M0 -80 Q40 -100 46 -130 Q12 -122 0 -90 Z"/><circle cx="0" cy="-128" r="12" fill="#d9b25f"/>',
    "lily": '<path d="M-3 0 Q-4 -70 0 -130 Q4 -70 3 0 Z"/><path d="M0 -130 C-40 -150 -46 -190 -10 -200 C-4 -170 0 -150 0 -130 Z" '
            'fill="#f3e7c9"/><path d="M0 -130 C40 -150 46 -190 10 -200 C4 -170 0 -150 0 -130 Z" fill="#f3e7c9"/>'
            '<path d="M0 -130 C-12 -170 0 -215 0 -215 C0 -215 12 -170 0 -130 Z" fill="#fff6e0"/>',
    "net": '<path d="M-160 0 Q0 -60 160 0 M-160 0 L-120 -80 M-80 -30 L-60 -100 M0 -40 L0 -110 M80 -30 L60 -100 M160 0 L120 -80 '
           'M-130 -50 Q0 -100 130 -50 M-110 -85 Q0 -125 110 -85" fill="none" stroke="#d9d2c4" stroke-width="3" opacity="0.7"/>',
    "fish": '<path d="M-30 -20 Q0 -44 30 -20 Q0 4 -30 -20 Z M30 -20 L48 -34 L48 -6 Z" fill="#cfd8e6"/>',
    "fire": '<path d="M-60 0 L60 0 L40 -14 L-40 -14 Z"/><path id="{pid}-flame" d="M-28 -14 C-34 -60 -6 -70 0 -110 '
            'C10 -70 36 -60 28 -14 Z" fill="#f0a23c"/><path d="M-12 -14 C-14 -40 0 -50 0 -70 C6 -46 14 -40 12 -14 Z" fill="#ffe28a"/>',
    "star": '<circle cx="0" cy="0" r="160" fill="#fff3c4" opacity="0.18"/><path d="M0 -70 L14 -14 L70 0 L14 14 L0 70 L-14 14 '
            'L-70 0 L-14 -14 Z" fill="#fff6d8"/><path d="M0 -150 L4 -4 L0 150 L-4 -4 Z M-150 0 L-4 -4 L150 0 L-4 4 Z" '
            'fill="#fff6d8" opacity="0.5"/>',
    "chest": '<rect x="-80" y="-90" width="160" height="90"/><path d="M-90 -90 Q0 -140 90 -90 Z"/>'
             '<rect x="-14" y="-100" width="28" height="22" fill="#f2c96b"/>',
    "well": '<rect x="-110" y="-120" width="220" height="120"/><rect x="-125" y="-135" width="250" height="22"/>'
            '<rect x="-95" y="-300" width="12" height="170"/><rect x="83" y="-300" width="12" height="170"/>'
            '<rect x="-110" y="-310" width="220" height="16"/>',
    "lamp": '<path d="M-40 -10 Q0 10 40 -10 L30 -30 L-30 -30 Z"/><path d="M40 -22 L70 -34 L60 -18 Z"/>'
            '<path id="{pid}-flame" d="M66 -36 C60 -60 72 -66 74 -84 C80 -66 88 -60 80 -36 Z" fill="#f0a23c"/>',
    "mat": '<rect x="-110" y="-16" width="220" height="16" rx="6"/>',
    "stones": '<ellipse cx="-40" cy="-14" rx="26" ry="16"/><ellipse cx="10" cy="-12" rx="20" ry="13"/>'
              '<ellipse cx="50" cy="-16" rx="28" ry="17"/>',
    "birds": '<g fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"><path d="M0 0 q14 -12 28 0 q14 -12 28 0"/>'
             '<path d="M70 -40 q10 -9 20 0 q10 -9 20 0"/><path d="M-60 -30 q11 -10 22 0 q11 -10 22 0"/></g>',
    "lotus": '<ellipse cx="0" cy="-4" rx="95" ry="14"/>'
             '<g fill="#f6dfe4"><path d="M0 -10 C-34 -18 -64 -46 -66 -74 C-38 -66 -14 -44 0 -10 Z"/>'
             '<path d="M0 -10 C34 -18 64 -46 66 -74 C38 -66 14 -44 0 -10 Z"/></g>'
             '<path d="M0 -10 C-20 -40 -12 -82 0 -104 C12 -82 20 -40 0 -10 Z" fill="#fbeef0"/>'
             '<circle cx="0" cy="-30" r="9" fill="#f2c96b"/>',
    "bodhi": '<path d="M-34 0 C-22 -120 -44 -220 -12 -300 L16 -300 C46 -220 26 -120 38 0 Z"/>'
             '<path d="M-6 -250 C-60 -270 -120 -300 -170 -330 M8 -260 C60 -280 130 -300 180 -340" fill="none" stroke="{INK}" '
             'stroke-width="14"/><ellipse cx="0" cy="-400" rx="300" ry="120"/><ellipse cx="-170" cy="-350" rx="140" ry="90"/>'
             '<ellipse cx="180" cy="-355" rx="150" ry="95"/><ellipse cx="0" cy="-500" rx="200" ry="90"/>',
    "bamboo": "".join(f'<rect x="{x - 7}" y="-{h}" width="14" height="{h}"/>'
                      + "".join(f'<rect x="{x - 10}" y="-{y}" width="20" height="6"/>' for y in range(90, h, 90))
                      + f'<path d="M{x} -{h - 40} q40 -10 70 -40 q-40 6 -70 30 Z M{x} -{h - 120} q-40 -10 -66 -36 q36 4 66 26 Z"/>'
                      for x, h in [(-50, 560), (0, 620), (46, 520)]),
    "bell": '<rect x="-120" y="-330" width="16" height="330"/><rect x="104" y="-330" width="16" height="330"/>'
            '<path d="M-150 -330 Q0 -360 150 -330 L150 -312 L-150 -312 Z"/><rect x="-4" y="-312" width="8" height="30"/>'
            '<path d="M-58 -120 C-58 -220 -46 -282 0 -282 C46 -282 58 -220 58 -120 Z"/><rect x="-70" y="-122" width="140" height="12"/>',
    "cup": '<path d="M-44 -44 H44 C44 -14 26 0 0 0 C-26 0 -44 -14 -44 -44 Z"/>'
           '<ellipse id="{pid}-liq" cx="0" cy="-44" rx="40" ry="8" fill="#9a7a44"/>',
    "teapot": '<ellipse cx="0" cy="-50" rx="62" ry="50"/><path d="M50 -60 Q90 -70 100 -110 L110 -104 Q100 -56 56 -34 Z"/>'
              '<path d="M-56 -80 C-100 -84 -100 -20 -56 -26" fill="none" stroke="{INK}" stroke-width="10"/>'
              '<ellipse cx="0" cy="-100" rx="26" ry="8"/><circle cx="0" cy="-110" r="8"/>',
    "candle": '<rect x="-16" y="-110" width="32" height="110" fill="#efe4cc"/><rect x="-2" y="-122" width="4" height="14"/>'
              '<path id="{pid}-flame" d="M-9 -122 C-12 -140 -2 -146 0 -166 C4 -146 12 -140 9 -122 Z" fill="#f0a23c"/>',
    "cushion": '<path d="M-80 0 C-92 -44 -50 -58 0 -58 C50 -58 92 -44 80 0 Z"/>',
    "pagoda": _pagoda(),
    "hut": '<rect x="-110" y="-130" width="220" height="130"/><path d="M-150 -120 L0 -250 L150 -120 Z"/>'
           '<rect x="-26" y="-80" width="52" height="80" fill="#f0b45a" opacity="0.8"/>',
    "bridge": '<path d="M-280 0 Q0 -170 280 0 L250 0 Q0 -130 -250 0 Z"/>'
              '<path d="M-260 -40 Q0 -210 260 -40" fill="none" stroke="{INK}" stroke-width="8"/>'
              + "".join(f'<rect x="{x - 4}" y="{-40 - 170 * (1 - (x / 260) ** 2) * 0.82:.0f}" width="8" height="46"/>'
                        for x in (-200, -100, 0, 100, 200)),
    "gate": '<rect x="-150" y="-380" width="26" height="380"/><rect x="124" y="-380" width="26" height="380"/>'
            '<path d="M-220 -400 Q0 -380 220 -400 L230 -440 Q0 -410 -230 -440 Z"/><rect x="-180" y="-330" width="360" height="20"/>',
    "flute": '<rect x="-70" y="-10" width="140" height="10" rx="5"/>',
    "drum": '<rect x="-60" y="-90" width="120" height="90"/><ellipse cx="0" cy="-90" rx="60" ry="16" fill="#d8c8a8"/>',
    "donkey": '<ellipse cx="0" cy="-110" rx="90" ry="44"/><path d="M70 -130 L112 -190 L140 -176 L104 -110 Z"/>'
              '<path d="M112 -192 L104 -236 L120 -196 Z M126 -188 L132 -232 L136 -190 Z"/>'
              '<rect x="-66" y="-80" width="12" height="80"/><rect x="-34" y="-80" width="12" height="80"/>'
              '<rect x="30" y="-80" width="12" height="80"/><rect x="58" y="-80" width="12" height="80"/>'
              '<path d="M-88 -118 Q-118 -100 -110 -60" fill="none" stroke="{INK}" stroke-width="6"/>',
    "cage": '<path d="M-60 -200 Q0 -260 60 -200" fill="none" stroke="{INK}" stroke-width="8"/><rect x="-70" y="-12" width="140" height="12"/>'
            + "".join(f'<rect x="{x - 2}" y="-200" width="4" height="190"/>' for x in (-60, -36, -12))
            + '<path id="{pid}-bird" d="M-6 -70 Q8 -96 26 -82 Q34 -92 44 -88 L36 -78 Q30 -56 4 -56 Z" fill="#f2c96b"/>'
              '<g id="{pid}-door">' + "".join(f'<rect x="{x - 2}" y="-200" width="4" height="190"/>' for x in (12, 36, 60)) + '</g>',
    "rope": '<path d="M-130 -8 C-90 -34 -50 18 -10 -8 C30 -34 70 18 110 -8 Q130 -20 140 -10" fill="none" stroke="{INK}" '
            'stroke-width="11" stroke-linecap="round"/>',
    "mirror": '<rect x="-6" y="-170" width="12" height="170"/><path d="M-50 0 H50 L40 -12 H-40 Z"/>'
              '<ellipse cx="0" cy="-250" rx="72" ry="96"/><ellipse id="{pid}-liq" cx="0" cy="-250" rx="60" ry="84" fill="#dfe3ea"/>',
    "ladder": '<rect x="-60" y="-520" width="12" height="520"/><rect x="48" y="-520" width="12" height="520"/>'
              + "".join(f'<rect x="-50" y="-{y}" width="100" height="10"/>' for y in range(60, 520, 70)),
    "cloud": '<g fill="#f1ece3" opacity="0.9"><circle cx="-80" cy="-40" r="50"/><circle cx="-10" cy="-70" r="70"/>'
             '<circle cx="70" cy="-45" r="55"/><rect x="-130" y="-40" width="250" height="40" rx="20"/></g>',
    "butterfly": '<g fill="#f2c96b"><path d="M0 -20 C-30 -60 -70 -50 -60 -20 C-70 6 -30 10 0 -14 Z"/>'
                 '<path d="M0 -20 C30 -60 70 -50 60 -20 C70 6 30 10 0 -14 Z"/></g><rect x="-3" y="-40" width="6" height="34" rx="3"/>',
    "moon": '<circle cx="0" cy="-150" r="420" fill="#fff4d6" opacity="0.08"/><circle cx="0" cy="-150" r="150" fill="#f1ead6"/>',
    "scroll": '<rect x="-90" y="-150" width="180" height="130" fill="#efe4cc"/><rect x="-100" y="-160" width="14" height="150" rx="6"/>'
              '<rect x="86" y="-160" width="14" height="150" rx="6"/><path d="M-60 -115 H60 M-60 -85 H60 M-60 -55 H30" stroke="{INK}" '
              'stroke-width="5"/>',
}


def person(pid, kind, p, rim=True):
    """A robed figure 190 units tall: body group -b (for bob/sit/lie), drawing group -s (breathe, idle sway), robe
    group -r (its hem trails the body: overlapping action), arm groups -al / -ar (sleeves with hands, rotating at the
    shoulder). Faces are never drawn; each kind differs only by its outline (robe, hat, turban...). The thin rim
    light keeps overlapping silhouettes apart as layers; faint folds in the rim colour give the cloth some form."""
    robe = {"master": "M-42 0 C-38 -50 -31 -100 -25 -128 C-22 -141 -14 -148 -6 -150 L6 -150 C14 -148 22 -141 25 -128 "
                      "C31 -100 38 -50 42 0 Q0 9 -42 0 Z",
            "dancer": "M-74 0 Q-44 -46 -22 -104 C-20 -126 -14 -146 -6 -149 L6 -149 C14 -146 20 -126 22 -104 Q44 -46 74 0 "
                      "Q0 10 -74 0 Z",
            "samurai": "M-44 0 C-38 -55 -34 -105 -33 -140 Q-30 -150 -8 -151 L8 -151 Q30 -150 33 -140 C34 -105 38 -55 44 0 "
                       "Q0 7 -44 0 Z"}.get(kind, "M-31 0 C-29 -45 -27 -95 -23 -126 C-21 -140 -14 -147 -6 -149 L6 -149 "
                                                 "C14 -147 21 -140 23 -126 C27 -95 29 -45 31 0 Q0 7 -31 0 Z")
    folds = (f'<path d="M-6 -122 C-9 -82 -11 -42 -14 2 M9 -112 C11 -72 13 -36 16 2" fill="none" stroke="{C["rim"]}" '
             f'stroke-opacity="0.13" stroke-width="2.2"/>')
    parts = [f'<g id="{pid}-r" class="robe"><path d="{robe}"/>{folds}</g>',
             '<path d="M-6 -146 L-5 -158 L5 -158 L6 -146 Z"/><ellipse cx="0" cy="-171" rx="13.5" ry="16"/>']
    if kind == "woman":
        parts.append('<path d="M-18 -181 Q0 -203 18 -181 L25 -136 Q0 -128 -25 -136 Z"/>')
    if kind == "nun":
        parts.append('<path d="M-20 -183 Q0 -207 20 -183 L33 -114 Q0 -106 -33 -114 Z"/>')
    if kind == "elder":
        parts.append('<path d="M38 2 L38 -205 Q38 -228 56 -222" fill="none" stroke="currentColor" stroke-width="6" '
                     'stroke-linecap="round"/>')
    if kind == "farmer":
        parts.append('<path d="M-52 -176 Q0 -214 52 -176 Q0 -184 -52 -176 Z"/>')
    if kind == "nasruddin":  # turban and beard
        parts.append('<ellipse cx="0" cy="-189" rx="23" ry="15"/><path d="M-12 -163 Q0 -132 12 -163 Z"/>')
    if kind == "samurai":  # topknot and a sword at the hip
        parts.append('<circle cx="0" cy="-193" r="6"/><path d="M-36 -70 L44 -120" stroke="currentColor" stroke-width="6" '
                     'stroke-linecap="round"/>')
    arm = '<path d="M-6 -2 C-8 22 -11 46 -14 64 Q-1 70 12 64 C9 46 7 22 6 -2 Z"/><ellipse cx="-1" cy="72" rx="5" ry="6.5"/>'
    parts.append(f'<g id="{pid}-al" class="arm-l" transform="translate(-15,-144)">{arm}</g>'
                 f'<g id="{pid}-ar" class="arm-r" transform="translate(15,-144)">{arm}</g>')
    edge = f' stroke="{C["rim"]}" stroke-width="1.8" stroke-opacity="0.55"' if rim else ""
    return f'<g id="{pid}-s" fill="{INK}" color="{INK}"{edge}>{"".join(parts)}</g>'


SIZES = {"child": 0.62, "master": 1.06}
PEOPLE = {"master", "seeker", "monk", "nun", "man", "woman", "child", "elder", "dancer", "samurai", "farmer", "nasruddin"}


def place(pid, k, x, y, s, flip, inner, p):
    """Wrap a drawing so it can be moved (outer, x/y) and bent (inner -b, rotation/scale about its feet)."""
    if k in PEOPLE:
        body = person(pid, k, p)
        s *= SIZES.get(k, 1.0)
    elif k in PROPS:
        body = f'<g fill="{INK}">{PROPS[k].replace("{pid}", pid).replace("{INK}", INK)}</g>'
    else:
        raise ValueError(f"unknown cast kind {k!r}")
    sx = -s if flip else s
    # the master is a figure in soft light, never a face or a portrait; the glow stays outside the body group
    # so that sit/bow/lie pivot around the feet, not around the glow's bounding box
    glow = (f'<circle id="{pid}-glow" cx="0" cy="-120" r="160" fill="url(#{p}-halo)" opacity="0.75"/>'
            if k == "master" else "")
    return f'<g id="{pid}" transform="translate({x},{y}) scale({sx},{s})">{glow}<g id="{pid}-b" class="body">{inner}{body}</g></g>'


def crowd(pid, x, y, s, n, p, seed=9):
    """A row of small figures for crowds; deterministic spacing and height."""
    r = rng(seed)
    figs = []
    for i in range(n):
        fx = x + (i - (n - 1) / 2) * 62 * s + (r() - 0.5) * 20
        fs = s * (0.85 + r() * 0.25)
        kind = "woman" if r() < 0.35 else ("child" if r() < 0.15 else "man")
        figs.append(f'<g transform="translate({fx:.0f},{y + r() * 14:.0f}) scale({fs * (0.62 if kind == "child" else 1):.2f})">'
                    f'{person(f"{pid}-{i}", kind, p, rim=False)}</g>')
    return f'<g id="{pid}"><g id="{pid}-b" class="body" opacity="0.9">{"".join(figs)}</g></g>'


def fx(p, name):
    """Full-frame effects; returns (markup, anims)."""
    if name == "rain":
        r = rng(13)
        drops = "".join(f'<path d="M{x:.0f} {y:.0f} l-14 46" />' for x, y in ((r() * (W + 200), r() * 2 * H) for _ in range(170)))
        return (f'<g id="{p}-rain" stroke="{C["rain"]}" stroke-width="2.5" stroke-opacity="0.45" stroke-linecap="round">{drops}</g>',
                [{"t": f"#{p}-rain", "do": "rain"}])
    if name == "lightning":
        return (f'<path id="{p}-bolt" d="M640 0 L560 360 L640 360 L520 760 L700 300 L615 300 L700 0 Z" fill="#f4f7ff" opacity="0"/>'
                f'<rect id="{p}-flash" width="{W}" height="{H}" fill="#e8eeff" opacity="0"/>',
                [{"t": f"#{p}-flash", "do": "flash", "bolt": f"#{p}-bolt"}])
    if name == "rays":
        rays = "".join(f'<path d="M540 -60 L{540 + 700 * math.sin(a):.0f} {1300 * math.cos(a):.0f} '
                       f'L{540 + 700 * math.sin(a + 0.09):.0f} {1300 * math.cos(a + 0.09):.0f} Z"/>'
                       for a in [i * 0.2 - 0.9 for i in range(10)])
        return (f'<g id="{p}-rays" fill="{C["rays"]}" opacity="0">{rays}</g>', [{"t": f"#{p}-rays", "do": "rays"}])
    if name == "sparkle":
        r = rng(17)
        sp = "".join(f'<path d="M{x:.0f} {y - 14:.0f} l4 10 l10 4 l-10 4 l-4 10 l-4 -10 l-10 -4 l10 -4 Z"/>'
                     for x, y in ((140 + r() * 800, 700 + r() * 600) for _ in range(26)))
        return f'<g id="{p}-sparkle" fill="{C["spark"]}" opacity="0">{sp}</g>', [{"t": f"#{p}-sparkle", "do": "sparkle"}]
    if name == "petals":  # blossom drifting down; placed above the frame too, so the whole beat has petals
        r = rng(31)
        ps = "".join(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="10" ry="5" transform="rotate({r() * 180:.0f} {x:.0f} {y:.0f})" '
                     f'opacity="{0.5 + r() * 0.5:.2f}"/>' for x, y in ((r() * W, -800 + r() * (H + 600)) for _ in range(46)))
        return f'<g id="{p}-petals" fill="{C["petal"]}">{ps}</g>', [{"t": f"#{p}-petals", "do": "petals"}]
    if name == "mist":  # two soft bands of fog drifting slowly in opposite directions
        return (f'<defs><linearGradient id="{p}-mistg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["mist"]}" '
                f'stop-opacity="0"/><stop offset="0.5" stop-color="{C["mist"]}" stop-opacity="0.5"/><stop offset="1" '
                f'stop-color="{C["mist"]}" stop-opacity="0"/></linearGradient></defs>'
                f'<g id="{p}-mist"><rect id="{p}-mist-a" x="-300" y="{HZ - 230}" width="{W + 600}" height="240" fill="url(#{p}-mistg)"/>'
                f'<rect id="{p}-mist-c" x="-300" y="{HZ + 40}" width="{W + 600}" height="300" fill="url(#{p}-mistg)" opacity="0.7"/></g>',
                [{"t": f"#{p}-mist", "do": "mist"}])
    if name == "ripples":  # rings spreading on still water
        rings = "".join('<ellipse cx="540" cy="1500" rx="150" ry="38"/>' for _ in range(3))
        return (f'<g id="{p}-ripples" fill="none" stroke="{C["wave"]}" stroke-width="3" stroke-opacity="0.7">{rings}</g>',
                [{"t": f"#{p}-ripples", "do": "ripples"}])
    if name == "fireflies":
        r = rng(37)
        dots = "".join(f'<circle cx="{r() * W:.0f}" cy="{900 + r() * 900:.0f}" r="{3 + r() * 3:.1f}"/>' for _ in range(40))
        return f'<g id="{p}-fireflies" fill="{C["fly"]}">{dots}</g>', [{"t": f"#{p}-fireflies", "do": "fireflies"}]
    raise ValueError(f"unknown fx {name!r}")


FX = {"rain", "lightning", "rays", "sparkle", "petals", "mist", "ripples", "fireflies"}
GROUNDS = ("hills", "field", "desert", "city", "sea", "garden", "forest", "river", "zen", "mountain")


def _seed(text):
    return sum((i + 1) * ord(ch) for i, ch in enumerate(text))


def foreground(p, ground_name, sky_name):
    """A branch hanging into the top corner, nearest to the camera (the multiplane foreground: it moves fastest), in
    front of the sky and away from the sun or moon; seeded by the setting, so beats that dissolve within one setting
    keep the same branch. Leafy over hills, fields, gardens, forest and water, a pine bough over mountains and
    the zen garden; none in the desert or the village. Returns (markup, anims)."""
    kind = {"hills": "leaf", "field": "leaf", "garden": "leaf", "forest": "leaf", "mountain": "pine", "zen": "pine",
            "river": "leaf", "sea": "leaf"}.get(ground_name)
    r = rng(_seed(ground_name + sky_name))
    if not kind or r() > 0.75:
        return "", []
    orb = SKIES[sky_name][3]
    left = orb[1] > W / 2 if orb else r() < 0.5
    # down the side of the frame: under the title band, outside the captions (the zoom maps x 230 to ~150 px)
    limb = f'<path d="M-60 170 C40 250 125 390 205 610 L193 616 C105 400 25 275 -60 232 Z" fill="{INK}"/>'
    twigs = "".join(f'<path d="M{x:.0f} {y:.0f} q{14 + r() * 14:.0f} {6 + r() * 12:.0f} {30 + r() * 20:.0f} '
                    f'{24 + r() * 20:.0f}" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'
                    for x, y in [(10, 226), (85, 330), (150, 470)])
    pts = [(min(235, -30 + 240 * t + (r() - 0.5) * 70), 210 + 390 * t + (r() - 0.5) * 50) for t in [r() for _ in range(34)]]
    if kind == "leaf":
        tips = "".join(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{13 + r() * 9:.0f}" ry="{6 + r() * 3:.0f}" '
                       f'transform="rotate({r() * 180:.0f} {x:.0f} {y:.0f})"/>' for x, y in pts)
    else:  # pine: fans of needles
        tips = "".join(f'<path d="{" ".join(f"M{x:.0f} {y:.0f} l{26 * math.cos(a):.0f} {26 * math.sin(a):.0f}" for a in [math.pi * (0.95 + 0.11 * k) for k in range(10)])}" '
                       f'stroke="{INK}" stroke-width="3" stroke-linecap="round"/>' for x, y in pts[:16])
    art = f'{limb}{twigs}<g fill="{INK}">{tips}</g>'
    flip = "" if left else f' transform="translate({W},0) scale(-1,1)"'
    return (f'<g{flip}><g id="{p}-fg" class="fgb">{art}</g></g>', [{"t": f"#{p}-fg", "do": "sway"}])


def motes(p, sky_name):
    """Dust in the light: a few soft specks drifting up and glinting (seeded). Warm light on silhouette skies, faint
    ink specks on rice paper. Returns (markup, anims)."""
    r = rng(_seed(p + sky_name))
    col, op = (INK, 0.35) if INK == INKWASH["ink"] else ((C["star"] if sky_name in ("night", "storm") else C["spark"]), 0.6)
    dots = "".join(f'<circle cx="{r() * W:.0f}" cy="{380 + r() * 980:.0f}" r="{1.6 + r() * 2.6:.1f}" '
                   f'opacity="{0.15 + r() * 0.5:.2f}"/>' for _ in range(18))
    return f'<g id="{p}-motes" fill="{col}" opacity="{op}">{dots}</g>', [{"t": f"#{p}-motes", "do": "motes"}]
