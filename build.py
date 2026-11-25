"""script.json -> the channel trailer: narration (Kokoro, open source) + music bed (ffmpeg) + index.html (a
HyperFrames composition). Also the shared pieces both builders use: music(), word_times(), vintage() and the era lint.

  python build.py      # needs models/kokoro-v1.0.onnx, models/voices-v1.0.bin and ffmpeg on PATH
  npx hyperframes render --output out/video.mp4

Every scene lasts as long as its narration (plus breathing room), so the animation always follows the voice.
"""
import html, json, os, re, subprocess
import numpy as np

LEAD, TAIL, MIN_SCENE, END_HOLD = 0.7, 1.4, 5.0, 2.5  # seconds
VOICE, SPEED, LANG = "bm_george", 0.86, "en-gb"  # chosen by audition; a bm_/bf_ voice needs en-gb
VINTAGE = True                                   # early-1990s room-recording texture on the voice (vintage())
W, H = 1920, 1080
END_CARD_SUFFIX = ""  # appended to the tradition on every closing card
DISCLAIMER = ("Independent channel. Not affiliated with or endorsed by OSHO International Foundation. "
              "Narration is original writing, read by a synthetic voice.")

# Words that date a script to today (the scripts must sound like a talk given around 1991). Whole words, any case,
# with plural and -ing forms; checked by both self-tests against every say, title, chapter title and description.
BANNED_ERA_WORDS = [
    "internet", "online", "website", "email", "smartphone", "mobile phone", "cell phone", "screen time", "scrolling",
    "app", "social media", "likes", "followers", "subscribers", "viral", "notification", "wi-fi", "laptop", "ai",
    "algorithm", "streaming", "netflix", "youtube", "podcast", "influencer", "content", "selfie", "zoom", "pandemic",
    "lockdown", "climate change", "gig", "startup",
    "mindset", "self-care", "toxic", "trauma", "triggered", "boundaries", "holding space", "manifest", "vibe", "journey",
    "hack", "productivity", "level up", "burnout", "mental health", "wellness", "empower", "authentic self",
    "gratitude practice", "growth mindset", "unpack", "sit with that", "process"]
_ERA = re.compile(r"\b(?:" + "|".join(re.escape(w) + "(?:s|es|ing)?" for w in BANNED_ERA_WORDS) + r")\b", re.I)
# The style is of the era, never of one real speaker: no names, no fake recording claims, no dates
_IMPERSONATION = re.compile(r"osho|beloved|recorded live|\b(?:19[5-9]\d|20[0-2]\d|2030)\b", re.I)


def era_hits(text):
    """Banned modern words in a text (empty list = it could have been said in 1991)."""
    return [m.group(0) for m in _ERA.finditer(text)]


def impersonation_hits(text):
    return [m.group(0) for m in _IMPERSONATION.finditer(text)]


# Line icons drawn on a 100x100 grid; every path animates its stroke from 0 to full length.
ICONS = {
    "lotus": ["M50 78 C38 64 38 40 50 22 C62 40 62 64 50 78 Z", "M50 78 C30 74 18 56 16 40 C34 44 44 58 50 78",
              "M50 78 C70 74 82 56 84 40 C66 44 56 58 50 78", "M14 84 Q50 74 86 84"],
    "moon": ["M62 14 A36 36 0 1 0 86 62 A28 28 0 1 1 62 14 Z"],
    "flame": ["M50 90 C28 86 24 62 36 46 C40 58 46 60 48 54 C44 38 52 22 60 10 C62 30 80 44 76 66 C74 82 64 90 50 90 Z",
              "M50 86 C42 84 40 74 46 66 C48 72 54 72 54 66 C60 72 60 84 50 86 Z"],
    "drop": ["M50 10 C62 34 78 50 78 66 A28 28 0 0 1 22 66 C22 50 38 34 50 10 Z", "M36 68 A14 14 0 0 0 48 80"],
    "eye": ["M8 50 Q50 10 92 50 Q50 90 8 50 Z", "M50 36 A14 14 0 1 1 49.9 36"],
    "bell": ["M30 76 C30 44 34 26 50 26 C66 26 70 44 70 76 Z", "M22 76 H78", "M50 26 V14", "M44 82 A6 6 0 0 0 56 82"],
    "leaf": ["M18 82 C18 42 44 18 86 14 C82 56 58 82 18 82 Z", "M18 82 L66 34"],
    "wave": ["M8 62 C24 62 26 30 46 30 C62 30 64 50 54 54 C46 56 44 44 52 42", "M8 76 Q20 68 32 76 T56 76 T80 76 T92 76"],
    "mountain": ["M6 82 L34 34 L50 58 L64 40 L94 82 Z", "M28 44 L34 34 L40 44"],
    "sun": ["M50 30 A20 20 0 1 1 49.9 30", "M50 6 V18", "M50 82 V94", "M6 50 H18", "M82 50 H94",
            "M19 19 L27 27", "M73 73 L81 81", "M81 19 L73 27", "M27 73 L19 81"],
    "cloud": ["M20 70 H78 A14 14 0 0 0 76 42 A20 20 0 0 0 38 40 A15 15 0 0 0 20 70 Z"],
    "spiral": ["M50 50 m0 -4 a4 4 0 1 1 -4 4 a8 8 0 1 1 8 8 a12 12 0 1 1 -12 -12 a18 18 0 1 1 18 18 a24 24 0 1 1 -24 -24"],
    "bodhi": ["M47 90 C48 74 46 64 50 54 C54 64 52 74 53 90", "M50 56 C30 58 14 46 18 32 C22 18 40 12 50 14 C60 12 78 18 82 32 "
              "C86 46 70 58 50 56 Z", "M50 54 L36 34 M50 54 L64 34 M50 54 V24"],
}


def vintage(path):
    """The voice as a good room recording from around 1990, in place: tape/microphone bandwidth, a broadcast
    cassette's evenness, a small hall, makeup gain back to the clean level, and faint seeded hiss (same on every
    rebuild). Run after word_times(): Whisper is more accurate on the clean clips."""
    tmp = path + ".tmp.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-filter_complex",
                    "[0:a]highpass=f=90,lowpass=f=8500,acompressor=threshold=-20dB:ratio=3:attack=15:release=250,"
                    "aecho=0.8:0.5:35|70:0.18|0.10,volume=11dB[v];"  # the echo and compressor cost ~11 dB
                    "anoisesrc=color=pink:amplitude=0.003:seed=7:sample_rate=24000[n];"
                    "[v][n]amix=inputs=2:duration=first:normalize=0", tmp], check=True)
    os.replace(tmp, path)


def narrate(scenes, out="assets/voice.wav"):
    """TTS every scene, lay the clips on one track, return [(start, duration)] per scene and the total length."""
    from kokoro_onnx import Kokoro
    import soundfile as sf
    k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
    clips, sr = [], 24000
    for s in scenes:
        audio, sr = k.create(s["narration"], voice=VOICE, speed=SPEED, lang=LANG)
        clips.append(np.asarray(audio, np.float32))
    slots = timings([len(c) / sr for c in clips])
    total = slots[-1][0] + slots[-1][1] + END_HOLD
    track = np.zeros(int(total * sr) + 1, np.float32)
    for (start, _), c in zip(slots, clips):
        i = int((start + LEAD) * sr)
        track[i:i + len(c)] = c
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sf.write(out, track, sr)
    if VINTAGE:
        vintage(out)
    return slots, total


def timings(voice_secs):
    """[(start, duration)] for each scene: the narration starts LEAD in, the scene ends TAIL after it."""
    slots, t = [], 0.0
    for v in voice_secs:
        d = round(max(LEAD + v + TAIL, MIN_SCENE), 3)
        slots.append((t, d))
        t = round(t + d, 3)  # rounded each step so a scene starts exactly where the last one ends
    return slots


def music(total, out="assets/music.wav"):
    """A tanpura-style drone (Pa, Sa', Sa', Sa plucked 1.2 s apart over a quiet Sa+Pa pad) and a singing bowl every
    16 s, generated, so no licensed audio is needed."""
    plucks = []
    for i, f in enumerate((196.00, 261.63, 261.63, 130.81)):  # each string rings for its whole 4.8 s cycle
        tau = f"mod(t+{4.8 - 1.2 * i:.1f},4.8)"
        plucks.append(f"exp(-0.9*{tau})*(sin(2*PI*{f}*t)+0.5*sin(2*PI*{2 * f}*t)+0.25*sin(2*PI*{3 * f}*t))")
    pad = "(0.8+0.2*sin(2*PI*t/9))*(sin(2*PI*65.41*t)+0.6*sin(2*PI*130.81*t)+0.4*sin(2*PI*196.00*t))"
    # inharmonic bowl partials f, 2.76f, 5.40f; the fundamental doubled 0.6 Hz apart so it beats slowly
    bowl = ("min(1,mod(t,16)*30)*exp(-0.35*mod(t,16))*(sin(2*PI*220*t)+0.6*sin(2*PI*220.6*t)+0.4*sin(2*PI*607.2*t)"
            "+0.2*sin(2*PI*1188*t))")
    expr = f"0.017*({'+'.join(plucks)})+0.011*{pad}+0.017*{bowl}"  # ~20 LU under the voice (ebur128)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=48000:d={total}", "-af",
                    f"lowpass=f=1800,aecho=0.8:0.6:400|800:0.35|0.2,afade=t=in:d=2,afade=t=out:st={total - 3}:d=3,"
                    "pan=stereo|c0=c0|c1=c0", out], check=True)


def _spread(times, words, dur):
    """Fill the words Whisper did not match, by character position between the matched words around them; strictly
    increasing, so no caption block or highlight is ever zero-length."""
    pos = [sum(len(w) + 1 for w in words[:k]) for k in range(len(words))]
    pts = {0: 0.0, pos[-1] + len(words[-1]) + 1: dur}
    pts.update({p: t for p, t in zip(pos, times) if t is not None})
    xs = sorted(pts)
    out, prev = [], -1.0
    for p, t in zip(pos, times):
        t = float(np.interp(p, xs, [pts[x] for x in xs])) if t is None else t
        prev = max(t, prev + 0.02)
        out.append(round(prev, 3))
    return out


def word_times(clips, sr, texts):
    """When each word of each text is spoken, in seconds into its clip: Whisper's word timestamps (faster-whisper,
    base.en, on the CPU) matched in order to the known script. None when faster-whisper is not installed, so callers
    fall back to timing words by estimate."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("::warning::faster-whisper is not installed (pip install faster-whisper); caption words are timed by estimate")
        return None
    import difflib
    norm = lambda w: "".join(ch for ch in w.lower() if ch.isalnum())  # noqa: E731
    out = []
    try:  # a failed model download must not fail the render: the estimate is a working fallback
        model = WhisperModel("base.en", device="cpu", compute_type="int8",
                             download_root=os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "whisper"))
        for clip, text in zip(clips, texts):
            audio = np.interp(np.arange(0, len(clip), sr / 16000), np.arange(len(clip)), clip).astype(np.float32)  # 16 kHz
            segs, _ = model.transcribe(audio, language="en", word_timestamps=True, initial_prompt=text)
            heard = [(norm(w.word), w.start) for s in segs for w in s.words]
            said = text.split()
            times = [None] * len(said)
            m = difflib.SequenceMatcher(None, [norm(w) for w in said], [h for h, _ in heard], autojunk=False)
            for a, b, n in m.get_matching_blocks():
                times[a:a + n] = [t for _, t in heard[b:b + n]]
            out.append(_spread(times, said, len(clip) / sr))
    except Exception as e:  # noqa: BLE001
        print(f"::warning::Whisper word timing failed ({e}); caption words are timed by estimate")
        return None
    return out


def icon_svg(name, sid):
    paths = "".join(f'<path pathLength="1" d="{d}"/>' for d in ICONS[name])
    return f'<svg id="{sid}-icon" class="icon" viewBox="0 0 100 100">{paths}</svg>'


def render_html(meta, scenes, slots, total):
    """The HyperFrames composition: one root, one timed <section class="clip"> per scene, one paused GSAP timeline."""
    e = html.escape
    events = [s for s in scenes if s["icon"]]  # every scene but the intro gets a dot on the timeline
    dots = "".join(f'<div class="dot" id="dot-{s["id"]}" style="left:{i * 1560 / (len(events) - 1):.1f}px"></div>'
                   for i, s in enumerate(events))
    sections = []
    for s, (start, dur) in zip(scenes, slots):
        sid = s["id"]
        words = "".join(f'<span class="w">{e(w)}</span> ' for w in s["title"].split())
        if s["icon"]:
            body = (f'{icon_svg(s["icon"], sid)}<div class="year" id="{sid}-year">{e(s["year"])}</div>'
                    f'<h1 class="title" id="{sid}-title">{words}</h1>'
                    f'<div class="quote" id="{sid}-quote">“{e(s["quote"])}”<span class="ref">{e(s["ref"] + END_CARD_SUFFIX)}</span></div>')
        else:
            body = (f'<h1 class="title big" id="{sid}-title">{words}</h1>'
                    f'<div class="sub" id="{sid}-sub">{e(meta["subtitle"])}</div>')
        sections.append(f'<section id="{sid}" class="clip scene" data-start="{start}" data-duration="{dur}" '
                        f'data-track-index="1"><div class="inner" id="{sid}-inner">{body}</div></section>')
    plan = json.dumps([{"id": s["id"], "start": st, "dur": d, "icon": bool(s["icon"])}
                       for s, (st, d) in zip(scenes, slots)])
    return TEMPLATE.format(total=round(total, 3), sections="\n".join(sections), dots=dots, plan=plan,
                           title=e(meta["title"]), W=W, H=H)


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  @font-face {{ font-family: "Cormorant"; src: url("fonts/CormorantGaramond.ttf"); }}
  @font-face {{ font-family: "Cormorant"; font-style: italic; src: url("fonts/CormorantGaramond-Italic.ttf"); }}
  @font-face {{ font-family: "Cinzel"; src: url("fonts/Cinzel.ttf"); }}
  body {{ margin: 0; background: #070b18; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; isolation: isolate;
          background: radial-gradient(ellipse at 50% 120%, #3a2a1a 0%, #141a33 45%, #070b18 100%);
          color: #f4ead8; font-family: "Cormorant", serif; }}
  #glow {{ position: absolute; width: 1400px; height: 1400px; left: 260px; top: -700px; border-radius: 50%;
          background: radial-gradient(circle, rgba(227,199,138,0.16) 0%, rgba(227,199,138,0) 60%); z-index: 0; }}
  .clip {{ position: absolute; inset: 0; z-index: 2; }}
  .inner {{ position: absolute; left: 0; right: 0; top: 120px; display: flex; flex-direction: column; align-items: center; }}
  .icon {{ width: 200px; height: 200px; fill: none; stroke: #e3c78a; stroke-width: 2.2; stroke-linecap: round;
          stroke-linejoin: round; filter: drop-shadow(0 0 12px rgba(227,199,138,0.45)); }}
  .icon path {{ stroke-dasharray: 1; stroke-dashoffset: 1; }}
  .year {{ margin-top: 26px; font: 30px "Cinzel", serif; letter-spacing: 10px; color: #e3c78a; text-transform: uppercase; }}
  .title {{ margin: 14px 0 0; font-weight: 600; font-size: 104px; line-height: 1.05; text-align: center; }}
  .title.big {{ margin-top: 210px; font-size: 140px; }}
  .w {{ display: inline-block; }}
  .quote {{ margin-top: 34px; max-width: 1240px; text-align: center; font-style: italic; font-size: 50px; line-height: 1.25;
           color: #efe3cc; }}
  .ref {{ display: block; margin-top: 16px; font: 24px "Cinzel", serif; font-style: normal; letter-spacing: 6px; color: #b9a27a; }}
  .sub {{ margin-top: 28px; font: 32px "Cinzel", serif; letter-spacing: 8px; color: #e3c78a; text-transform: uppercase; }}
  #timeline {{ position: absolute; left: 180px; width: 1560px; top: 960px; height: 3px; z-index: 3; }}
  #track {{ position: absolute; inset: 0; background: rgba(244,234,216,0.18); transform-origin: left center; }}
  #progress {{ position: absolute; inset: 0; background: #e3c78a; transform-origin: left center; transform: scaleX(0);
              box-shadow: 0 0 14px rgba(227,199,138,0.7); }}
  .dot {{ position: absolute; top: -9px; width: 20px; height: 20px; margin-left: -10px; border-radius: 50%;
         background: #070b18; border: 2px solid rgba(244,234,216,0.45); }}
</style>
</head>
<body>
<div id="root" data-composition-id="channel-trailer" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
  <div id="glow"></div>
{sections}
  <div id="timeline"><div id="track"></div><div id="progress"></div>{dots}</div>
  <audio id="voice" src="assets/voice.wav" data-start="0" data-duration="{total}" data-volume="1"></audio>
  <audio id="music" src="assets/music.wav" data-start="0" data-duration="{total}" data-volume="1"></audio>
</div>
<script>
  const PLAN = {plan};
  const TOTAL = {total};
  Promise.all([
    document.fonts.load('600 100px "Cormorant"'), document.fonts.load('italic 50px "Cormorant"'),
    document.fonts.load('30px "Cinzel"'),
  ]).then(() => {{
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#glow", {{ x: -160, scale: 0.9 }}, {{ x: 160, scale: 1.1, duration: TOTAL, ease: "none" }}, 0);
    tl.fromTo("#track", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 1.6, ease: "power2.inOut" }}, 0.4);
    tl.fromTo(".dot", {{ scale: 0, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.4, stagger: 0.06, ease: "back.out(2)" }}, 1.2);
    const events = PLAN.filter(p => p.icon);
    PLAN.forEach(p => {{
      const s = p.start, id = p.id;
      tl.fromTo("#" + id + "-inner", {{ opacity: 1 }}, {{ opacity: 0, duration: 0.5, ease: "power1.in" }}, s + p.dur - 0.5);
      tl.fromTo("#" + id + " .w", {{ opacity: 0, y: 46, rotateX: -60 }},
                {{ opacity: 1, y: 0, rotateX: 0, duration: 0.8, stagger: 0.12, ease: "power3.out" }}, s + 0.45);
      if (!p.icon) {{
        tl.fromTo("#" + id + "-sub", {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 1.4, ease: "power2.out" }}, s + 1.1);
        return;
      }}
      const k = events.indexOf(p);
      tl.fromTo("#" + id + "-icon path", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: 1.4, stagger: 0.12, ease: "power2.inOut" }}, s + 0.1);
      tl.fromTo("#" + id + "-icon", {{ scale: 0.85, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.9, ease: "power2.out" }}, s + 0.1);
      // transforms only: letter-spacing snaps to whole pixels and stutters in frame-by-frame capture (lint error)
      tl.fromTo("#" + id + "-year", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 1.0, ease: "power2.out" }}, s + 0.3);
      tl.fromTo("#" + id + "-quote", {{ opacity: 0, y: 24 }}, {{ opacity: 1, y: 0, duration: 1.0, ease: "power2.out" }}, s + 1.3);
      tl.to("#progress", {{ scaleX: k / (events.length - 1), duration: 0.9, ease: "power2.inOut" }}, s + 0.2);
      tl.to("#dot-" + id, {{ backgroundColor: "#e3c78a", borderColor: "#e3c78a", scale: 1.35, duration: 0.5, ease: "back.out(3)" }}, s + 0.6);
      tl.to("#dot-" + id, {{ scale: 1, duration: 0.6, ease: "power2.out" }}, s + 1.1);
    }});
    tl.to("#timeline", {{ opacity: 0, duration: 1.2 }}, TOTAL - 1.4);
    window.__timelines = window.__timelines || {{}};
    window.__timelines["channel-trailer"] = tl;
  }});
</script>
</body>
</html>
"""


def main():
    data = json.load(open("script.json", encoding="utf-8"))
    slots, total = narrate(data["scenes"])
    music(total)
    open("index.html", "w", encoding="utf-8").write(render_html(data, data["scenes"], slots, total))
    print(f"index.html: {len(slots)} scenes, {total:.1f} s")


if __name__ == "__main__":
    main()
