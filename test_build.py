"""Self-check without TTS or rendering: python test_build.py  (must print ok)"""
import json, re
from build import timings, render_html, ICONS, LEAD, TAIL, MIN_SCENE, era_hits, impersonation_hits

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
print("ok")
