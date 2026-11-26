"""Self-check for every long-form video, without TTS or rendering: python longform/test_long.py  (must print ok)"""
import glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lineart as art
from build_long import (videos, estimate, timings, render_html, chunks, description, stamp, depth_order, TEMPLATE, END,
                        WPS, MIN_LEN, MAX_LEN)
from build import era_hits, impersonation_hits, DISCLAIMER

ACTIONS = set(re.findall(r"^\s{6}(\w+): a =>", TEMPLATE, re.M))
assert {"walk", "raise", "kneel", "rays", "spin", "rise", "descend"} <= ACTIONS, ACTIONS
NEW_VERBS = {"sit", "bow", "breathe", "whirl", "dance", "open", "petals", "mist", "ripples", "fireflies"}
assert NEW_VERBS <= ACTIONS, NEW_VERBS - ACTIONS
KINDS = set(art.PROPS) | art.PEOPLE | {"crowd"}
LEFTOVER = re.compile(r"\b(jesus|kjv|bible|scripture|gospel|christ|cross|thorns|manger|tomb)\b", re.I)


def lint(where, text):
    assert not era_hits(text), f"{where}: modern word(s) {era_hits(text)} in {text[:50]!r}"
    assert not impersonation_hits(text), f"{where}: {impersonation_hits(text)} in {text[:50]!r}"


# every prop, person, land and effect draws in every template
for t in art.TEMPLATES:
    art.use(t)
    art.background("b0", "night")
    for k in sorted(set(art.PROPS) | art.PEOPLE):
        assert f'id="t-{k}"' in art.place(f"t-{k}", k, 960, art.GF, 1.0, False, "", "b0"), k
    for g in art.LANDS:
        art.land("b0", g)
    for f in art.FX:
        art.fx("b0", f)

vs = videos()
assert len({v["id"] for v in vs}) == len(vs) and all("--" not in v["id"] for v in vs)
assert len({v["template"] for v in vs}) == len(vs), "every long video has its own template"
used = set()
for v in vs:
    vid = v["id"]
    assert v["template"] in art.TEMPLATES, vid
    assert len(v["chapters"]) >= 3, f"{vid}: YouTube chapters need at least 3"
    lint(vid, v["title"])
    assert "Osho" in v["title"] and "Osho" in v["description"], f"{vid}: the title and description name Osho"
    lint(vid, v["thumbnail"])
    assert not era_hits(v["description"]), (vid, era_hits(v["description"]))
    length = sum(estimate(c) for c in v["chapters"])
    # the estimate runs a little long or short of the real voice; keep a margin inside 10-12 minutes
    assert MIN_LEN + 20 <= length <= MAX_LEN - 20, f"{vid}: ~{stamp(length)}, aim for 10:20-11:40"
    last = v["chapters"][-1]
    assert any(a["do"] in ("breathe", "sit") for b in last["beats"] for c in b.get("cast", []) for a in c.get("acts", [])), \
        f"{vid}: the last chapter is the guided meditation (a breathe or sit act)"
    for n, ch in enumerate(v["chapters"]):
        where = f"{vid} ch{n}"
        lint(where, ch["title"])
        assert estimate(ch) >= 12, f"{where}: YouTube chapters must be at least 10 s"
        assert len(ch["beats"]) >= 2 and ch["title"] and ch["ref"], where  # the title card and closing card need room
        says = " ".join(b["say"] for b in ch["beats"])
        assert "Osho" in says or ch is last, f"{where}: every chapter ties back to Osho's teaching"
        # a verbatim quote sits in "quotation marks" and the chapter's card names its book
        assert '"' not in says or "Osho, " in ch["ref"], f"{where}: quote needs 'Osho, <book>' in ref"
        for b in ch["beats"]:
            lint(where, b["say"])
            assert b.get("sky", "night") in art.SKIES and b.get("land", "hills") in art.LANDS, (where, b["say"][:30])
            assert set(b.get("fx", [])) <= art.FX, (where, b.get("fx"))
            used |= set(b.get("fx", []))
            for j, c in enumerate(b.get("cast", [])):
                assert c["k"] in KINDS, (where, c["k"])
                assert "in" not in c or 0 <= c["in"] < j, (where, j)
                for a in c.get("acts", []):
                    assert a["do"] in ACTIONS, (where, a["do"])
                    assert a["do"] not in ("walk", "roll", "fly", "climb") or "to" in a, (where, a)
                    used.add(a["do"])
        voice = [len(b["say"].split()) / WPS for b in ch["beats"]]
        slots = timings(voice)
        total = round(slots[-1][0] + slots[-1][1] + END, 3)
        page = render_html(v, n, ch, voice, slots, total)
        ids = re.findall(r'\sid="([^"]+)"', page)
        assert len(ids) == len(set(ids)), (where, sorted({i for i in ids if ids.count(i) > 1})[:5])
        assert f'data-duration="{total}"' in page and 'window.__timelines["long-chapter"]' in page
        assert "letterSpacing" not in page and 'id="music"' not in page  # music is laid once, under the whole video
        assert page.count('pathLength="1"') > 20, where  # the scene is line art that draws itself in
        assert art.TEMPLATES[v["template"]]["line"] in page, where
        assert page.count("<span class=w>") == sum(len(b["say"].split()) for b in ch["beats"]), where  # word highlight
        assert ('class="d o"' in page) == any(b.get("cast") for b in ch["beats"]), where  # figures are cut-outs
        assert not LEFTOVER.search(page), (where, LEFTOVER.search(page).group(0))
    txt = description(v, [0.0] + [70.0 * i for i in range(1, len(v["chapters"]))])
    assert DISCLAIMER in txt and txt.split("Chapters\n")[1].startswith("0:00 "), vid
    print(f"  {vid}: {len(v['chapters'])} chapters, ~{stamp(length)} ({v['template']})")

assert NEW_VERBS <= used, f"verbs no video uses (use them or delete them): {sorted(NEW_VERBS - used)}"
for path in [os.path.join(HERE, "lineart.py")] + glob.glob(os.path.join(HERE, "videos", "*.json")):
    m = LEFTOVER.search(open(path, encoding="utf-8").read())
    assert not m, (os.path.basename(path), m and m.group(0))
assert chunks("Sit, and watch. Let the mind settle") == ["Sit, and watch.", "Let the mind settle"]
assert depth_order([{"k": "man"}, {"k": "crowd"}, {"k": "man", "y": 700}, {"k": "man", "in": 0}]) == [2, 1, 0]
assert "b.s + b.d -" not in TEMPLATE  # no beat fades out at its end (no dips to black between beats)
assert stamp(0) == "0:00" and stamp(61.9) == "1:01" and stamp(3725) == "1:02:05"
print(f"ok: {len(vs)} long videos")
