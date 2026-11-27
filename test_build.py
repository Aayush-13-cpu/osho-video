"""Self-check without TTS or rendering: python test_build.py  (must print ok)"""
import json, os, re, subprocess, tempfile
from build import timings, render_html, ICONS, LEAD, TAIL, MIN_SCENE, era_hits, impersonation_hits, music

data = json.load(open("script.json", encoding="utf-8"))
scenes = data["scenes"]
assert all(s["icon"] in ICONS for s in scenes if s["icon"]), "unknown icon"
assert len({s["id"] for s in scenes}) == len(scenes), "scene ids must be unique"

slots = timings([1.0] + [6.0] * (len(scenes) - 1))
assert slots[0] == (0.0, MIN_SCENE)  # short narration still gets the minimum scene length
assert slots[1] == (MIN_SCENE, LEAD + 6.0 + TAIL)
assert all(round(a[0] + a[1], 3) == b[0] for a, b in zip(slots, slots[1:])), "scenes must butt up, no gap or overlap"

total = slots[-1][0] + slots[-1][1] + 2.5
page = render_html(data, scenes, slots, total)
assert f'data-duration="{round(total, 3)}"' in page
assert 'window.__timelines["channel-trailer"]' in page and 'data-composition-id="channel-trailer"' in page
ids = re.findall(r'\sid="([^"]+)"', page)
assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]  # HyperFrames needs unique ids
assert page.count('class="clip scene"') == len(scenes)
assert "letterSpacing" not in page, "HyperFrames lint rejects animating letter-spacing; tween transforms instead"
for s in scenes:
    assert s["quote"].replace("'", "&#x27;") in page
lefts = [float(x) for x in re.findall(r'class="dot"[^>]*left:([\d.]+)px', page)]
assert lefts[0] == 0 and lefts[-1] == 1560, lefts  # dots sit inside #timeline (1560 px wide), not offset again
for s in scenes:  # the trailer too must sound like 1991 and never like one real speaker
    text = " ".join((s["narration"], s["title"], s["quote"]))
    assert not era_hits(text) and not impersonation_hits(text), (s["id"], era_hits(text), impersonation_hits(text))

# the music bed: stereo, exactly as long as asked, and quieter while someone speaks (sidechain duck) than without
with tempfile.TemporaryDirectory() as tmp:
    v = os.path.join(tmp, "v.wav")  # a stand-in voice: speech-loud tone from 1 s to 5 s
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "aevalsrc='0.3*sin(2*PI*220*t)*between(t,1,5)':s=24000:d=6", v], check=True)
    music(6, os.path.join(tmp, "a.wav"))
    music(6, os.path.join(tmp, "b.wav"), voice=v)
    info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=channels:format=duration", "-of", "csv=p=0",
                           os.path.join(tmp, "b.wav")], capture_output=True, text=True).stdout.split()
    assert info[0] == "2" and abs(float(info[1]) - 6) < 0.05, info

    def rms(f):  # dB over 2-4 s, inside the speech
        out = subprocess.run(["ffmpeg", "-v", "info", "-ss", "2", "-t", "2", "-i", f, "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        return float(re.search(r"mean_volume: (-?[\d.]+) dB", out).group(1))
    assert rms(os.path.join(tmp, "b.wav")) < rms(os.path.join(tmp, "a.wav")) - 3, "the bed must duck under the voice"
print("ok")
