# Making Animated Videos with Code

### A field guide to the TapoBhumi video machine, written so you can build your own

This repository makes narrated, animated videos of Zen, Taoist, Sufi and Buddhist stories, reflections and guided
meditations for the **TapoBhumi** channel, with **free, open-source tools**, and renders them on **GitHub's
computers instead of yours**. It contains:

- **The channel trailer**: a 2-minute horizontal video, thirteen scenes with line icons (`script.json`, `build.py`).
- **80 story Shorts**: vertical 40–55 second animations in two visual styles, silhouette and sumi-e ink (`shorts/`).
- **10 long videos**: horizontal 10–12 minute talks in glowing line art, each ending in a guided meditation
  (`longform/`). See [The long videos](#the-long-videos).

The videos explain Osho's teachings in the third person ("Osho taught...", never speaking as him). The narration
is original commentary, the stories are traditional and retold in our own words, and the only verbatim Osho words
are short quotes in "quotation marks" taken from Wikiquote, with the book named on the chapter's closing card (the
tests enforce this). No photos of Osho, no OSHO logo, no cloned voice. The voice is synthetic (Kokoro `bm_george`)
with a light early-90s room-recording texture. Every long video's description carries the disclaimer below.

**Running the channel (one command):**

```bash
./generate.py              # the next 1 long video + 2 Shorts, rendered on GitHub, downloaded to videos/<date>/
./generate.py --status     # what has been made, what is left
./generate.py --dry-run    # see the next picks without starting anything
./generate.py --redo ID    # forget that ID was made, so the next run makes it again
```

It works through the library in order (`longform/videos/`, then `shorts/stories_library.json`, then the two
starter sets), records what is finished in `generated.txt`, and never renders on your computer. It needs `git` and
the GitHub CLI `gh`, logged in with a token allowed to push and run workflows (fine-grained: Contents and Workflows
read/write, Actions read).

**The full book:** `docs/book/build_book.py` builds a PDF field guide from `docs/book/book.md` plus appendices
read straight from the code (`.venv/bin/python docs/book/build_book.py`).

Read this like a short book. Part One explains the ideas, Part Two walks through how this project uses them, Part
Three shows how to change it, and Part Four shows how to start something new of your own. Every code snippet comes
from this repository.

---

## Contents

**Part One: The ideas**
1. [A video is a web page that plays itself](#1-a-video-is-a-web-page-that-plays-itself)
2. [Drawing with SVG](#2-drawing-with-svg)
3. [Moving things with GSAP](#3-moving-things-with-gsap)
4. [HyperFrames: turning the page into an MP4](#4-hyperframes-turning-the-page-into-an-mp4)
5. [A voice from text: Kokoro](#5-a-voice-from-text-kokoro)
6. [Sound with FFmpeg](#6-sound-with-ffmpeg)
7. [Someone else's computer: GitHub Actions](#7-someone-elses-computer-github-actions)

**Part Two: How this project works**

8. [The map of files](#8-the-map-of-files)
9. [The channel trailer, step by step](#9-the-channel-trailer-step-by-step)
10. [The story Shorts, step by step](#10-the-story-shorts-step-by-step)
11. [The silhouette and ink kit](#11-the-silhouette-and-ink-kit)
12. [The animation interpreter](#12-the-animation-interpreter)
13. [The cloud pipeline](#13-the-cloud-pipeline)

**Part Three: Changing it**

14. [Write a new story](#14-write-a-new-story)
15. [Add a prop, an action or a style](#15-add-a-prop-an-action-or-a-style)
16. [Checking your work](#16-checking-your-work)
17. [Mistakes we made, and what they teach](#17-mistakes-we-made-and-what-they-teach)

**Part Four: On your own**

18. [Start a new project from nothing](#18-start-a-new-project-from-nothing)
19. [Continue on another computer](#19-continue-on-another-computer)
20. [Glossary and licences](#20-glossary-and-licences)

---

# Part One: The ideas

## 1. A video is a web page that plays itself

A web browser is a very good drawing machine. It draws text, shapes, colours and images, and it can move them. If
you could photograph a web page 30 times a second while its animations play, you would have a video.

That is the whole trick of this project:

```
 words you write ─► a web page with animations ─► a browser photographs every frame ─► MP4
```

Why do it this way instead of in a video editor?

- **Text is precise and repeatable.** Change one word in a story file and the video that uses it updates.
- **Code can make 80 videos as easily as 1.** You describe a pattern once and reuse it.
- **Everything is free.** Browsers, the animation library, the voice, the encoder: all open source.

## 2. Drawing with SVG

SVG ("Scalable Vector Graphics") describes pictures as shapes, written as text. This draws the dusk sun:

```html
<svg viewBox="0 0 1080 1920">
  <circle cx="300" cy="1160" r="110" fill="#fff4d6"/>
</svg>
```

- **The coordinate system.** `viewBox="0 0 1080 1920"` is a vertical Short, 1080 wide and 1920 tall. `x` grows
  to the right and **`y` grows downward**, so `y=0` is the top of the screen.
- **Paths.** `<path d="M-40 0 C-36 -60 ... Z"/>` draws any outline. `M` moves the pen, `L` draws a line, `C` and
  `Q` draw curves, `Z` closes the shape. The master's long robe is one path.
- **Groups and transforms.** `<g transform="translate(540,1390) scale(1.6)">…</g>` draws everything inside
  shifted to (540, 1390) and 1.6 times bigger. Draw a figure once around (0, 0), then place it anywhere.

## 3. Moving things with GSAP

[GSAP](https://gsap.com) is a JavaScript animation library. You give it an element, the values to change, and how
long to take:

```js
const tl = gsap.timeline({ paused: true });
tl.to("#b0-c0-b", { scaleY: 0.58, duration: 0.9, ease: "power2.out" }, 0.4);   // the master sits down
```

- **A timeline** is a list of animations placed at exact times. The last number is the start time.
- **`to`** animates from the current value; **`fromTo`** sets both ends (safer when the playhead can jump);
  **`set`** changes a value instantly.
- **Ease** is the feel of the motion: `"none"` is mechanical, `"power2.out"` starts fast and settles,
  `"sine.inOut"` is gentle at both ends.
- **`repeat` and `yoyo`** make a back-and-forth (breathing, a whirling dervish). Every repeat is *finite*, for a
  reason Chapter 4 explains.
- **`paused: true`** matters: HyperFrames moves the timeline to each frame itself.

## 4. HyperFrames: turning the page into an MP4

[HyperFrames](https://github.com/heygen-com/hyperframes) (open source, Apache 2.0) opens your page in a hidden
Chrome, moves the timeline to frame 0, takes a picture, moves to frame 1, takes a picture, and so on. FFmpeg then
joins the pictures and the sound into an MP4. A page has to follow a small contract:

```html
<div id="root" data-composition-id="story-short" data-start="0" data-duration="38.1"
     data-width="1080" data-height="1920">
  <section id="beat-0" class="clip" data-start="0" data-duration="8.9"> … scene 1 … </section>
  <audio id="voice" src="assets/voice.wav" data-start="0" data-duration="38.1"></audio>
</div>
<script>
  window.__timelines = window.__timelines || {};
  window.__timelines["story-short"] = tl;   // the key must equal data-composition-id
</script>
```

- **`data-start` / `data-duration`** say when each piece is visible or audible.
- **The timeline is registered** under the composition's id, *after* the fonts load and every tween is added.
- **Determinism.** Frames may be photographed in any order, so frame 412 must look the same every time: no clock,
  no unseeded `Math.random()`, no infinite repeats, nothing loading late. Stars, petals and fireflies come from a
  seeded generator (`kit.rng`).
- **Commands:** `npx hyperframes lint` (rules, instant), `npx hyperframes snapshot --at 2,12` (still frames for a
  quick look) and `npx hyperframes render` (the video; in this project only the cloud runs it).

## 5. A voice from text: Kokoro

[Kokoro](https://github.com/thewh1teagle/kokoro-onnx) is a small open-source text-to-speech model (Apache 2.0, so
monetized videos are fine). It runs on an ordinary CPU:

```python
from kokoro_onnx import Kokoro
k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
audio, sample_rate = k.create("Just watch. Nothing else.", voice="bm_george", speed=0.86, lang="en-gb")
```

`bm_george` was chosen by audition from eight English voices; a British (`bm_`/`bf_`) voice needs `lang="en-gb"`.
`VOICE, SPEED, LANG` are set in `build.py`, `build_short.py` and `build_long.py`, the same in all three.
**The voice decides the timing:** each beat is narrated first, measured, and only then given its length.

Then `vintage()` in `build.py` gives the voice the sound of a good room recording from around 1990: tape and
microphone bandwidth (`highpass 90 Hz, lowpass 8.5 kHz`), the evenness of a broadcast cassette (a gentle
compressor), a small hall (a short echo), makeup gain back to the clean level, and faint *seeded* pink hiss so every
rebuild is identical. It runs after Whisper has timed the words on the clean clips. `VINTAGE = False` in a builder
switches it off.

## 6. Sound with FFmpeg

[FFmpeg](https://ffmpeg.org) does three jobs here:

- **Music from maths.** `music()` in `build.py` generates a healing bed with `aevalsrc`: a slow chorused pad
  breathing between C add9 and A minor 7 (20 s each, cross-faded, left and right detuned apart for width), a faint
  shimmer two octaves up, a soft singing bowl every 24 s (partials f, 2.76f, 5.40f with a slow beat), and brown
  noise swelling like distant surf, all in a long hall. Given the narration, it ducks under the speech
  (`sidechaincompress`) and swells back in the pauses: about 17 dB under the voice between sentences, 21 dB under
  while speaking. No licensed track needed. `test_build.py` checks the duck.
- **The vintage texture** on the voice (Chapter 5).
- **Loudness.** YouTube plays everything at about **−14 LUFS**. Every finished video is normalized with
  `loudnorm=I=-14:TP=-1.5:LRA=11`; the hiss in pauses stays near −57 dBFS after that.

## 7. Someone else's computer: GitHub Actions

GitHub Actions runs scripts on GitHub's computers when you push. A *workflow* in `.github/workflows/` lists the
steps: install tools, build, render, upload. For **public repositories it is free with no minute limit**.

Finished videos are attached to a **GitHub Release**, a downloads page you can open from any device:
`https://github.com/Aayush-13-cpu/osho-video/releases`.

---

# Part Two: How this project works

## 8. The map of files

```
generate.py                 one command for the channel: picks, queues, waits, downloads, records
generated.txt               what has been made: "<long|short> <id> <date>" per line
script.json                 the channel trailer's 13 scenes (label, title, quote, tradition, icon, narration)
build.py                    the trailer builder + shared music(), word_times(), vintage(), era lint
test_build.py               checks for the trailer
shorts/
  stories_library.json      60 stories, the queue generate.py works through first (both styles)
  stories.json              10 starter stories, silhouette style
  stories_inkwash.json      10 starter stories, sumi-e ink style
  kit.py                    the drawing kit: skies, grounds, props, people, effects, styles
  build_short.py            narrates one story and writes its HyperFrames page (+ the animation interpreter)
  test_shorts.py            checks every story before any rendering
  render.txt                which story ids the next cloud run renders
  fetch.py                  downloads a finished batch to shorts/output/ (optional)
longform/
  videos/NN-<id>.json       one file per long video: chapters of beats, one template per video
  lineart.py                the glowing line-art kit: templates, skies, lands, figures, props, effects
  build_long.py             plan | chapter <id> <n> | finish <id> <dir> <out>
  test_long.py              checks every video (10-12 minutes, own template, meditation close, disclaimer)
  render.txt                which video ids the next cloud run renders
fonts/                      Cinzel and Cormorant Garamond (SIL Open Font License)
.github/workflows/          render.yml (trailer), shorts.yml, long.yml
```

## 9. The channel trailer, step by step

`build.py` does four things, in order:

1. **Narrate.** `narrate()` speaks every scene's `narration` and measures each clip, then applies `vintage()`.
2. **Time.** `timings()` gives each scene `0.7 s + narration + 1.4 s` (never less than 5 s), rounded at every step
   so one scene ends exactly where the next begins.
3. **Music.** `music()` generates the drone to the exact total length.
4. **Write the page.** `render_html()` fills `TEMPLATE` (composition id `channel-trailer`) with one section per
   scene, the timeline bar with a dot per scene, and the two audio tracks.

Each scene's line icon (`lotus moon flame drop eye bell leaf wave mountain sun cloud spiral bodhi`) draws itself
in: every path has `pathLength="1"` and its dash offset goes from 1 to 0.

## 10. The story Shorts, step by step

A story is four **beats**. Each beat is one or two sentences of narration plus the scene that acts it out:

```json
{"say": "How can I show you anything, unless you first empty your cup? Tonight, put down everything you know. One breath. Empty. Only this.",
 "sky": "dusk", "ground": "zen", "fx": ["mist"],
 "cast": [{"k": "master", "x": 540, "acts": [{"do": "sit", "at": 0.4}, {"do": "breathe", "at": 1.4}]}]}
```

`build_short.py <story-id>` turns that into a page:

1. **Narrate** every beat and time the beats to the voice: `LEAD + narration + TAIL` (0.35 s and 0.6 s).
2. **Captions.** `chunks()` cuts each sentence into blocks of up to 5 words, breaking after punctuation;
   `captions()` times every word with Whisper (`word_times()`: faster-whisper `base.en`, matched to the script),
   falling back to timing by length with a warning. The spoken word lights up in the accent colour.
3. **Scenes.** `compose_beat()` asks the kit for the sky, the ground, each cast member and the effects, and
   collects their *acts* with absolute times. The master always carries a soft glow.
4. **The page.** The title card shows from the first frame, the tradition (`"A Zen story"`) closes the last beat.
5. **Camera and cuts.** A multiplane camera: each beat's scene is four layers (sky `-L0`, far land `-L1`, figures
   `-L2`, a foreground branch `-L3`) and every slow eased move shifts them at different rates (the sky lags, the
   branch leads), so the picture has depth. Shots vary: wide push-ins and pull-outs, pans, and medium shots framed
   on the beat's main figure (`focus()`). A new setting is a hard cut, the same setting dissolves over 0.3 s; never
   a dip to black. The long videos do the same with sky and land layers and gentler moves.
5b. **Life.** Every figure sways a little on its own breath (`idle`), and the robe's hem follows a beat later
   (overlapping action); walking swings the arms and they settle with a small overshoot; dust drifts in the light
   (`motes`); the branch sways. Figures have a neck, shoulders, bell sleeves with hands and faint robe folds.
6. **Depth.** Cast drawn back to front (`depth_order()`), a thin rim light between overlapping silhouettes, and a
   faint static grain so gradients don't band.

## 11. The silhouette and ink kit

`shorts/kit.py` draws everything:

- **Everything stands on the ground line**, drawn around `(0, 0)`. Near figures stand at `y = 1390` (`FEET`),
  the horizon is at `1300` (`HZ`).
- **Three groups per figure.** `place()` wraps each drawing:

  ```
  <g id="b2-c3" transform="translate(x,y) scale(s)">   ← outer: moves (walk, run, fly)
     <g id="b2-c3-b" class="body">                     ← body: bends about the feet (sit, bow, whirl, lie)
        <g id="b2-c3-s"> … </g>                        ← drawing: breathes, without undoing a sit
  ```

- **Arms** (`-al`, `-ar`) rotate at the shoulder: raise, reach, bless, dance.
- **Nesting.** `"in": 0` draws a figure inside cast member 0, so Nasruddin rides his donkey.
- **No faces, ever.** The master is a robed figure in soft light (`-glow`, kept outside the body group so a sit
  pivots at the feet), never a portrait of anyone.
- **People:** `master seeker monk nun man woman child elder dancer samurai farmer nasruddin`.
- **Styles.** `kit.use("inkwash")` swaps the whole palette to sumi-e: near-black ink `#1a1714` on rice-paper skies,
  grey wash ridges, a red seal sun, and seal-red for the spoken word (`CSS["inkwash"]` in `build_short.py`).

## 12. The animation interpreter

Stories don't contain JavaScript. They contain *verbs*. The page holds a small dictionary `F` that turns each verb
into GSAP calls:

```js
      sit: a => tl.to(a.t + "-b", { scaleY: 0.58, duration: 0.9, ease: "power2.out" }, a.s),
      whirl: a => tl.fromTo(a.t + "-b", { scaleX: 1 }, { scaleX: -1, duration: 0.5, repeat: n(a.d, 0.5), yoyo: true, ... }, a.s),
```

`a.t` is the element, `a.s` the start time, `a.d` the duration, and `n(d, p)` turns a duration into a finite repeat
count. The tests discover verbs by their six-space indentation, so keep it.

## 13. The cloud pipeline

`.github/workflows/shorts.yml` runs on every push that changes `shorts/`:

1. **plan**: reads `shorts/render.txt` and creates a Release named `shorts-<run number>`.
2. **render**, once per story, in parallel: install Node, Python and FFmpeg; Kokoro and Whisper (cached); run
   `test_shorts.py`; build; `hyperframes lint`; `hyperframes render --quality high`; normalize to −14 LUFS; four
   preview stills; upload to the Release. Errors are re-printed as `::error::` annotations.

`./generate.py` does all of this for you: it writes the render lists with a fresh `# queued <time>` line (so the
push always starts a run), pushes, waits with `gh run watch`, downloads the Releases into `videos/<date>/`, and only
then records the items in `generated.txt`. A failed render marks nothing done.

---

## The long videos

`longform/` is its own format, separate from the Shorts, with the same voice and captions set at the bottom of a
16:9 frame.

- **Look.** Glowing line art: every line traces itself in when a beat begins, inside a soft glow. Figures and props
  are cut-outs filled with the sky, so lines behind them never show through. The same setting dissolves and keeps
  what is already drawn; a new setting draws itself in.
- **One template per video**, from `_template(line, glow, deep, horizon, motif)` in `lineart.py`: `saffron`,
  `maroon`, `lotus`, `bodhi`, `himalaya`, `ganga`, `zendo`, `moonlake`, `tao`, `sufi`, `satori`, … Motifs:
  `sunburst motes constellation halo mandala ripple`.
- **Chapters.** Chapter 0 is a cold open; story chapters alternate with reflections; **the last chapter is always a
  guided meditation** (sit and breathe, mist, fireflies, ripples). Lands: `hills field desert city sea garden
  mountain river forest zen`; effects: `rain lightning rays sparkle dove petals mist ripples fireflies`.
- **Length.** 10–12 minutes, estimated before any TTS at the measured 2.61 words per second (304 words in 116.3 s
  of `bm_george` at 0.86); the cloud run warns if the real video falls outside.
- **Cloud.** `long.yml` renders every chapter in parallel, joins them, lays one unbroken drone under the whole
  video, normalizes, and publishes `<id>.mp4`, `<id>.txt` (description with chapter timestamps, sources and the
  disclaimer) and `<id>.jpg` (thumbnail) to a Release named `long-N`.

---

# Part Three: Changing it

## 14. Write a new story

1. **Pick a traditional story** (Zen, Tao, Sufi, Buddhist, Upanishadic, an Indian fable, Mulla Nasruddin) and
   **retell it in your own words**. Never paste from a modern translation or from any teacher's books or talks.
2. **Write it as a talk from 1991.** Four beats, 80–100 words (the check stops at about 108). Beat 1 is a hook for
   adults; beats 2–3 tell the story; beat 4 lands one line for the listener's life and a tiny invitation ("One
   breath. Only this."). Spoken, plain, unhurried. The world of the railway station and the transistor radio,
   never of screens. `BANNED_ERA_WORDS` in `build.py` lists the modern words the check refuses.
3. **Add it** to `shorts/stories_library.json` (add `"style": "inkwash"` for the ink style). Unique kebab-case `id`,
   a `title`, a `ref` that names the tradition (`"A Zen story"`, `"Chuang Tzu"`, `"A Sufi tale"`).
4. **Stage each beat.** `sky`: `dawn day dusk night storm`. `ground`: `hills field desert city sea garden forest
   river zen mountain`. Then the `cast`:

   | Field | Meaning |
   |---|---|
   | `k` | a person (`master seeker monk nun man woman child elder dancer samurai farmer nasruddin`), `crowd`, or a prop (`boat tree house rock jar basket sheep table stone coin seed plant lily net fish fire star chest well lamp mat stones birds lotus bodhi bamboo bell cup teapot candle cushion pagoda hut bridge gate flute drum donkey cage rope mirror ladder cloud butterfly moon scroll`) |
   | `x`, `y` | where it touches the ground (`y` defaults to 1390) |
   | `s` | size (people look right around 1.5–1.6) |
   | `flip` | face left instead of right |
   | `in` | the index of an earlier cast member to ride inside |
   | `acts` | what it does: `{"do": "walk", "to": 760, "at": 0.5, "dur": 3}` (`at` = seconds into the beat) |

   Verbs: `walk run climb` (need `to`), `raise bless reach lower`, `kneel sit stand lie bow`, `breathe`,
   `whirl dance`, `appear vanish`, `rock drift` (`amp`, `period`), `fly` (`to`, `toy`), `grow`, `collapse`,
   `roll` (`to`, `deg`), `sink` (`by`), `tint` (`color`, for a jar or cup), `flicker` (fire, lamp, candle),
   `open` (a cage: the door opens and the bird flies out).
5. **Effects:** `"fx": ["rain", "lightning", "rays", "sparkle", "petals", "mist", "ripples", "fireflies"]`.
6. **Check it:** `python shorts/test_shorts.py`. `./generate.py` will pick it up in library order.

## 15. Add a prop, an action or a style

- **A prop:** add an entry to `PROPS` in `kit.py` (and a line version in `lineart.py` for the long videos), drawn
  around `(0, 0)`. Use `{pid}` in an id if an action needs a part (`cup` has `-liq`, `cage` has `-door` and `-bird`).
- **An action:** add one line to `F` in `build_short.py` (and `build_long.py`), at the same indentation. A new verb
  must be used by at least one story or video, or the test fails: dead verbs are deleted.
- **A style:** a palette in `STYLES` in `kit.py`, a matching entry in `CSS` in `build_short.py`, then
  `"style": "<name>"` on a story.

## 16. Checking your work

| Check | Command | What it catches |
|---|---|---|
| Story check | `python shorts/test_shorts.py` | unknown props or verbs, bad `in` links, duplicate ids, length, wrong palette, modern words, a speaker's name or a date, Bible-era leftovers, unused verbs |
| Video check | `python longform/test_long.py` | the same, plus 10–12 minutes, own template, chapter rules, the meditation close, the disclaimer, `0:00` first chapter |
| Trailer check | `python test_build.py` | timing gaps, duplicate ids, forbidden animations, modern words |
| HyperFrames rules | `npx hyperframes lint` (in a built folder) | anything the renderer would refuse |
| A look | `npx hyperframes snapshot --at 2,12,22` | stills of a built page, without rendering a video |
| The real thing | a cloud run, then watch the MP4 | everything else: always watch with sound before publishing |

## 17. Mistakes we made, and what they teach

- **Letter-spacing animation was rejected** by lint: it snaps to whole pixels. *Animate transforms and opacity.*
- **Dots ran off the timeline bar.** *Inside a positioned container, measure from the container.*
- **A figure pivoted around its glow** instead of its feet. *Keep decorations out of the group you rotate.*
- **Scenes overlapped by a hair.** *Round at every step.*
- **The music was inaudible.** *Measure loudness; don't trust your speakers.* The drone here was measured at 19.5 LU
  under the voice with `ebur128`.
- **A downloaded zip got committed.** *Check `git status` before every commit; ignore `*.zip`, `models/`, `out/`.*
- **The vintage chain made the voice 11 dB quieter**, which would have lifted the hiss with loudnorm. *Add makeup
  gain before mixing in the noise, then measure the floor in the pauses.*
- **`breathe` undid `sit`** when both scaled the same group. *Give each kind of motion its own group (`-s`).*
- **Two moons** appeared when a beat used the moon prop under a night sky. *The sky now leaves its moon out when
  the cast brings one.*
- **"Cross" is a fine verb** but trips the leftover check, so the stories say "go over the river". *A blunt rule
  is still cheaper than a missed leftover.*

---

# Part Four: On your own

## 18. Start a new project from nothing

The smallest working video:

```html
<!doctype html>
<html><head>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style> body{margin:0} #root{position:relative;width:1080px;height:1920px;background:#141a33;color:#fff}
  #t{position:absolute;top:800px;width:100%;text-align:center;font:96px serif} </style>
</head><body>
<div id="root" data-composition-id="hello" data-start="0" data-duration="4" data-width="1080" data-height="1920">
  <div id="t" class="clip" data-start="0" data-duration="4">Only this.</div>
</div>
<script>
  const tl = gsap.timeline({ paused: true });
  tl.fromTo("#t", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 1.2, ease: "power2.out" }, 0.3);
  window.__timelines = { hello: tl };
</script>
</body></html>
```

Then `npx hyperframes lint` and `npx hyperframes render --output hello.mp4` (Node 22+ and FFmpeg). Grow it the way
this project grew: a voice, then the voice setting the timing, then SVG scenes, then motion, then a GitHub repo
with a workflow so a free cloud computer renders it.

## 19. Continue on another computer

1. Install Git, then `git clone https://github.com/Aayush-13-cpu/osho-video.git`.
2. Edit, then `git add`, `git commit`, `git push`; or just run `./generate.py`. The cloud renders.
3. Download results from the Releases page (or let `./generate.py` do it).
4. For the checks you need Python 3.11 with `numpy`; for local TTS, `kokoro-onnx soundfile faster-whisper` and the
   models in `models/`; for `lint`, Node 22+.

## 20. Glossary and licences

| Word | Meaning |
|---|---|
| Composition | One HyperFrames page that becomes one video |
| Clip | An element with `data-start` / `data-duration` |
| Beat | One or two sentences of narration and the scene that acts them out |
| Timeline | GSAP's list of timed animations |
| Tween | A single animation on the timeline |
| Deterministic | The same frame always looks the same |
| Matrix job | One workflow step repeated in parallel for each item |
| Release | A GitHub page of downloadable files |
| LUFS / LU | Loudness units; YouTube targets −14 LUFS |
| WPS | Words per second of the voice, used to estimate length before any TTS |

| Part | Licence |
|---|---|
| HyperFrames | Apache 2.0 |
| GSAP | free standard licence (core library) |
| Kokoro voice | Apache 2.0 |
| faster-whisper | MIT |
| Fonts (Cinzel, Cormorant Garamond) | SIL Open Font License |
| Stories | traditional, retold in original words; scripture quotes only from public-domain translations (Legge 1891, Müller 1881) |
| Osho quotes | one-sentence quotes from Wikiquote's sourced list, each credited to its book; everything else is paraphrase |
| Music | generated in this repository |

*Independent channel about the teachings of Osho. Not affiliated with or endorsed by OSHO International Foundation.
OSHO is a registered trademark of OSHO International Foundation. Narration is original commentary, read by a
synthetic voice; short quotations are credited to their books.*
