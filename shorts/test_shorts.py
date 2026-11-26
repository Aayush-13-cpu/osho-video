"""Self-check for every story, without TTS or rendering: python shorts/test_shorts.py  (must print ok)"""
import glob, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit
from build_short import (all_stories, estimate, render_html, timings, chunks, captions, depth_order, TEMPLATE, MAX_TOTAL,
                         WPS, LEAD)
from build import era_hits, impersonation_hits

ACTIONS = set(re.findall(r"^\s{6}(\w+): a =>", TEMPLATE, re.M))
assert {"walk", "raise", "rock", "flash", "rain"} <= ACTIONS, ACTIONS
NEW_VERBS = {"sit", "bow", "breathe", "whirl", "dance", "open", "petals", "mist", "ripples", "fireflies"}
assert NEW_VERBS <= ACTIONS, NEW_VERBS - ACTIONS
KINDS = set(kit.PROPS) | kit.PEOPLE | {"crowd"}
LEFTOVER = re.compile(r"\b(jesus|kjv|bible|scripture|gospel|christ|cross|thorns|manger|tomb)\b", re.I)

# every prop and person draws in both styles
for style in kit.STYLES:
    kit.use(style)
    for k in sorted(set(kit.PROPS) | kit.PEOPLE):
        assert f'id="t-{k}"' in kit.place(f"t-{k}", k, 540, kit.FEET, 1.0, False, "", "b0"), k
    for g in kit.GROUNDS:
        kit.ground("b0", g)
    for f in kit.FX:
        kit.fx("b0", f)

stories = all_stories()
assert len(stories) >= 40 and len({s["id"] for s in stories}) == len(stories), "story ids must be unique"
assert all(s.get("style", "silhouette") in kit.STYLES for s in stories)
used = set()
for st in stories:
    sid = st["id"]
    assert "--" not in sid and re.fullmatch(r"[a-z0-9-]+", sid), sid
    assert estimate(st) <= MAX_TOTAL - 2, f"{sid}: ~{estimate(st):.0f} s is too close to the 60 s Shorts limit"
    for text in [st["title"]] + [b["say"] for b in st["beats"]]:
        assert not era_hits(text), f"{sid}: modern word(s) {era_hits(text)} in {text[:50]!r}"
        assert not impersonation_hits(text), f"{sid}: {impersonation_hits(text)} in {text[:50]!r}"
    assert "Osho" in st["beats"][-1]["say"], f"{sid}: the closing line ties the story to Osho's teaching"
    # a verbatim quote sits in "quotation marks" and the closing card names its book
    assert not any('"' in b["say"] for b in st["beats"]) or "Osho, " in st["ref"], f"{sid}: quote needs 'Osho, <book>' in ref"
    for b in st["beats"]:
        assert b.get("sky", "day") in kit.SKIES and b.get("ground", "hills") in kit.GROUNDS, sid
        assert set(b.get("fx", [])) <= kit.FX, (sid, b.get("fx"))
        used |= set(b.get("fx", []))
        for j, c in enumerate(b.get("cast", [])):
            assert c["k"] in KINDS, (sid, c["k"])
            assert "in" not in c or (0 <= c["in"] < j and b["cast"][c["in"]]["k"] in set(kit.PROPS) | kit.PEOPLE), (sid, j)
            for a in c.get("acts", []):
                assert a["do"] in ACTIONS, (sid, a["do"])
                assert a["do"] not in ("walk", "run", "roll", "fly", "climb") or "to" in a, (sid, a)
                used.add(a["do"])
    voice = [len(b["say"].split()) / WPS for b in st["beats"]]
    slots = timings(voice)
    total = round(slots[-1][0] + slots[-1][1] + 1.2, 3)
    page = render_html(st, voice, slots, total)
    ids = re.findall(r'\sid="([^"]+)"', page)
    assert len(ids) == len(set(ids)), (sid, sorted({i for i in ids if ids.count(i) > 1})[:5])
    assert f'data-duration="{total}"' in page and 'window.__timelines["story-short"]' in page
    assert "letterSpacing" not in page
    assert ("#1a1714" in page) == (st.get("style") == "inkwash"), sid  # the right palette is in use
    assert page.count("<span class=w>") == sum(len(b["say"].split()) for b in st["beats"]), sid  # every word can light up
    assert not LEFTOVER.search(page), (sid, LEFTOVER.search(page).group(0))
assert NEW_VERBS <= used, f"verbs no story uses (use them or delete them): {sorted(NEW_VERBS - used)}"
for path in [os.path.join(HERE, "kit.py")] + glob.glob(os.path.join(HERE, "stories*.json")):
    m = LEFTOVER.search(open(path, encoding="utf-8").read())
    assert not m, (os.path.basename(path), m and m.group(0))
assert chunks("Sit, and watch. Let the mind settle") == ["Sit, and watch.", "Let the mind settle"]
# back to front: farther up the ground first, a crowd behind the near ground by default, children stay in their parent
assert depth_order([{"k": "man"}, {"k": "crowd"}, {"k": "man", "y": 1300}, {"k": "man", "in": 0}], kit.FEET) == [2, 1, 0]
assert "b.s + b.d -" not in TEMPLATE  # no beat fades out at its end (no dips to black between beats)
# Whisper's word times drive the blocks: block 2 starts on its first spoken word, the last block holds to the beat's end,
# and the speech-end marker never comes before the last word
cap = captions({"beats": [{"say": "Sit, and watch. Let the mind settle"}]}, [2.5], [(0.0, 5.0)],
               [[0.1, 0.5, 0.9, 1.6, 2.0, 2.3, 2.6]])
assert [c[0] for c in cap] == [round(LEAD + 0.1, 3), round(LEAD + 1.6, 3)] and cap[1][0] + cap[1][1] == 5.0, cap
assert cap[1][3][-1] > cap[1][3][-2], cap
assert era_hits("check your email, scrolling apps") == ["email", "scrolling", "apps"] and not era_hits("walking across")
print(f"ok: {len(stories)} stories, {min(estimate(s) for s in stories):.0f}-{max(estimate(s) for s in stories):.0f} s each")
