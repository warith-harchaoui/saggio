#!/usr/bin/env python3
"""
Turn the script and the measured narration into two compositions.

The timings are not typed. Each scene lasts exactly as long as the voice
takes to say it plus a held tail, which is why ``narrate_film.py`` runs
first and writes ``narration/measured.json``. A composition whose cuts
were guessed drifts against its own track the moment a line is reworded.

Nothing here animates by clock. ``seek(t)`` is a pure function of time:
every element's reveal is computed from ``t`` and written to a custom
property the stylesheet reads. A renderer can therefore ask for frame
1 234 directly and get the same pixels every time, which is the whole
requirement a deterministic render has of a page.

Author
------
`Warith HARCHAOUI, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

import html
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "script.yaml"
MEASURED = HERE / "narration" / "measured.json"
COMPOSITION = HERE / "composition"

#: The model fragment scene four shows. Code, so it is the same in both
#: languages: a reader who meets `derived_from` on screen will meet the
#: same key in their own file.
YAML_LINES = [
    ("key", "costs:"),
    ("key", "  carbon:"),
    ("key", "    value:", "num", " 0.0014"),
    ("key", "    unit:", "str", ' "gCO2e"'),
    ("key", "    status:", "est", ' "estimated"'),
    ("key", "    derived_from:"),
    ("ref", "      - scenarios[0].costs.energy"),
    ("ref", "      - assumptions.grid_carbon_intensity"),
]

STATUS_CLASS = {
    "measured": "measured",
    "mesuré": "measured",
    "estimated": "estimated",
    "estimé": "estimated",
    "placeholder": "placeholder",
    "réservé": "placeholder",
    "TODO": "todo",
}

STYLE = """
@font-face{font-family:Roboto;
  src:url(fonts/Roboto-Variable.woff2)format('woff2-variations');
  font-weight:100 900;font-display:block}
@font-face{font-family:'Roboto Serif';
  src:url(fonts/Roboto-Serif-Variable.woff2)format('woff2-variations');
  font-weight:100 900;font-display:block}
@font-face{font-family:'Roboto Mono';
  src:url(fonts/Roboto-Mono-Variable.woff2)format('woff2-variations');
  font-weight:100 700;font-display:block}

:root{
  --ground:#0B0B0C; --ink:#F5F5F5; --soft:#B4B2A4; --faint:#6E6C66;
  --rule:rgba(255,255,255,.13);
  --accent:#7FD1FF; --navy:#003C5D;
  --measured:#6BC4A8; --estimated:#E0AC4E; --placeholder:#A2A6E0; --todo:#EF8A76;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1920px;height:1080px;overflow:hidden;background:var(--ground)}
body{font-family:Roboto,system-ui,sans-serif;color:var(--ink);-webkit-font-smoothing:antialiased}

#stage{position:relative;width:1920px;height:1080px;background:
  radial-gradient(1200px 700px at 78% -12%, rgba(0,60,93,.55), transparent 70%),
  var(--ground);}
#stage::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(1400px 900px at 50% 50%, transparent 55%, rgba(0,0,0,.45) 100%)}

.scene{position:absolute;inset:0;display:none;flex-direction:column;justify-content:center;
  padding:0 150px;opacity:calc(var(--in,1) * var(--out,1))}

.kicker{font-size:21px;letter-spacing:.22em;text-transform:uppercase;color:var(--accent);
  font-weight:600;margin-bottom:34px}
h1{font-family:'Roboto Serif',serif;font-weight:700;font-size:92px;line-height:1.04;
  letter-spacing:-.022em;max-width:1500px}
h2{font-family:'Roboto Serif',serif;font-weight:700;font-size:66px;line-height:1.08;
  letter-spacing:-.02em;max-width:1420px}
.sub{font-size:34px;color:var(--soft);line-height:1.45;max-width:1280px}
.reveal{opacity:var(--r,1);transform:translateY(calc((1 - var(--r,1)) * 16px))}
.rule{height:1px;background:var(--rule);margin:46px 0}
.mono{font-family:'Roboto Mono',ui-monospace,monospace}

/* 1 — the question */
.chips{display:flex;gap:18px;flex-wrap:wrap;margin-top:44px}
.chip{font-size:28px;color:var(--soft);border:1px solid var(--rule);border-radius:999px;
  padding:12px 26px}

/* 2 and 3 — a number on its own */
.bignum{font-family:'Roboto Mono',monospace;font-size:170px;font-weight:600;letter-spacing:-.03em;
  line-height:1}
.bignum .unit{font-size:62px;color:var(--soft);margin-left:22px;letter-spacing:0}
.bignum.wrong{color:var(--todo)}
.provenance{margin-top:44px;display:flex;flex-direction:column;gap:20px}
.provenance li{list-style:none;font-size:31px;color:var(--faint);
  padding-left:38px;position:relative}
.provenance li::before{content:"·";position:absolute;left:12px;color:var(--faint)}
.verdict{display:flex;align-items:center;gap:22px;margin-top:40px;font-size:36px;color:var(--todo)}
.verdict .mark{font-size:52px;line-height:1}

/* 4 — the file */
.code{font-family:'Roboto Mono',monospace;font-size:38px;line-height:1.62;
  white-space:pre;
  background:rgba(255,255,255,.035);border:1px solid var(--rule);border-radius:18px;
  padding:44px 52px;max-width:1240px}
.code .key{color:var(--accent)}
.code .num{color:var(--ink)}
.code .str{color:var(--soft)}
.code .est{color:var(--estimated)}
.code .ref{color:var(--faint)}

/* 5 — the four statuses */
.statuses{display:flex;flex-direction:column;gap:30px;margin-top:52px}
.status{display:grid;grid-template-columns:300px 1fr;align-items:baseline;gap:44px}
.status .name{font-family:'Roboto Mono',monospace;font-size:40px;font-weight:600}
.status .what{font-size:31px;color:var(--soft)}
.status.measured .name{color:var(--measured)}
.status.estimated .name{color:var(--estimated)}
.status.placeholder .name{color:var(--placeholder)}
.status.todo .name{color:var(--todo)}

/* 6 — the derivation chain */
.chain{display:flex;flex-direction:column;gap:30px;margin-top:40px}
.row{display:flex;align-items:center;gap:26px}
.node{display:inline-block;border:1px solid var(--rule);border-radius:14px;padding:20px 28px;
  min-width:290px;background:rgba(255,255,255,.03)}
.node .label{display:block;font-size:27px;color:var(--soft);margin-bottom:9px}
.node .tag{display:block;font-family:'Roboto Mono',monospace;font-size:24px;font-weight:600;
  letter-spacing:.04em}
.node.measured{border-color:rgba(107,196,168,.5)} .node.measured .tag{color:var(--measured)}
.node.estimated{border-color:rgba(224,172,78,.5)} .node.estimated .tag{color:var(--estimated)}
.node.todo{border-color:rgba(239,138,118,.5)} .node.todo .tag{color:var(--todo)}
.op{font-family:'Roboto Mono',monospace;font-size:30px;color:var(--faint);white-space:nowrap}

/* 7 — checked rather than declared */
.checks{display:flex;flex-direction:column;gap:34px;margin-top:50px}
.check{display:flex;gap:26px;align-items:baseline;font-size:36px;color:var(--soft)}
.check .mark{color:var(--accent);font-family:'Roboto Mono',monospace;font-size:30px}
.check .mono{color:var(--ink)}

/* 8 — refusals */
.refusals{display:flex;flex-direction:column;gap:0;margin-top:48px;max-width:1500px}
.refusal{display:grid;grid-template-columns:1fr 1fr;gap:60px;align-items:baseline;
  padding:34px 0;border-top:1px solid var(--rule)}
.refusal:last-child{border-bottom:1px solid var(--rule)}
.refusal .when{font-size:34px;color:var(--soft)}
.refusal .then{font-size:34px;color:var(--ink);font-family:'Roboto Mono',monospace}

/* 9 — the close */
.surfaces{display:flex;gap:16px;margin-top:46px;flex-wrap:wrap}
.surface{border:1px solid var(--rule);border-radius:12px;padding:22px 30px;font-size:28px;
  color:var(--soft);background:rgba(255,255,255,.03)}
.facts{display:flex;gap:40px;margin-top:58px}
.fact{min-width:300px}
.fact .n{font-family:'Roboto Mono',monospace;font-size:82px;font-weight:600;color:var(--accent);
  line-height:1}
.fact .what{font-size:27px;color:var(--soft);margin-top:12px}
.close{display:flex;align-items:baseline;gap:40px;margin-top:62px}
.cmd{font-family:'Roboto Mono',monospace;font-size:46px;color:var(--ink);
  border:1px solid var(--rule);border-radius:14px;padding:22px 34px;
  background:rgba(255,255,255,.04)}
.url{font-size:34px;color:var(--accent)}
.star{font-size:30px;color:var(--soft);font-family:'Roboto Mono',monospace}

/* 6 -- the interval, on a real model */
.intervals{margin-top:54px;border-top:1px solid var(--rule)}
.interval{display:grid;grid-template-columns:1fr 1.1fr 1.2fr;gap:36px;align-items:baseline;
  padding:30px 0;border-bottom:1px solid var(--rule)}
.interval .point{font-family:'Roboto Mono',monospace;font-size:40px;color:var(--ink)}
.interval .span{font-family:'Roboto Mono',monospace;font-size:40px;color:var(--accent)}
.interval .why{font-size:29px;color:var(--soft)}
.note{margin-top:44px;font-size:34px;color:var(--soft)}

/* 8 -- the closing punchline */
.punch{max-width:1500px}
.punch .one{font-size:92px;font-weight:300;line-height:1.1;color:var(--soft);
  letter-spacing:-.02em}
.punch .two{font-size:92px;font-weight:600;line-height:1.1;color:var(--ink);
  letter-spacing:-.02em;margin-top:14px}
"""

SEEK = """
const scenes = Array.from(document.querySelectorAll('.scene'));
const clamp = (x, lo, hi) => x < lo ? lo : (x > hi ? hi : x);

/**
 * Put the page in the state it is in at `t` seconds. A pure function of
 * `t`: no clock is read and nothing accumulates, so frame 1234 looks the
 * same whether it is asked for first or last.
 */
function seek(t){
  for (const scene of scenes){
    const start = parseFloat(scene.dataset.start);
    const dur = parseFloat(scene.dataset.dur);
    const local = t - start;
    const showing = local >= 0 && local < dur;
    scene.style.display = showing ? 'flex' : 'none';
    if (!showing) continue;
    scene.style.setProperty('--in', clamp(local / 0.55, 0, 1));
    scene.style.setProperty('--out', clamp((dur - local) / 0.45, 0, 1));
    for (const el of scene.querySelectorAll('[data-at]')){
      const at = parseFloat(el.dataset.at);
      const span = parseFloat(el.dataset.span || '0.55');
      el.style.setProperty('--r', clamp((local - at) / span, 0, 1));
    }
  }
  document.documentElement.dataset.seeked = t.toFixed(3);
}
window.seek = seek;
seek(0);
"""


def esc(text: str) -> str:
    """Escape for HTML, so a quote in the prose cannot end an attribute."""
    return html.escape(str(text), quote=True)


def reveal(at: float, span: float = 0.55) -> str:
    """Give an element the attributes that reveal it `at` seconds into its scene."""
    return f'class="reveal" data-at="{at:.2f}" data-span="{span:.2f}"'


def scene_question(content: dict, dur: float) -> str:
    """Scene one: the question somebody is going to ask."""
    chips = "".join(
        f'<span class="chip" {reveal(dur * 0.42 + i * 0.22)}>{esc(line)}</span>'
        for i, line in enumerate(content["lines"])
    )
    return (
        f'<p class="kicker" {reveal(0.1)}>saggio</p>'
        f"<h1 {reveal(0.45)}>{esc(content['headline'])}</h1>"
        f'<div class="chips">{chips}</div>'
    )


def scene_loose_number(content: dict, dur: float) -> str:
    """Scene two: the number you would have given, and where it came from."""
    items = "".join(
        f"<li {reveal(dur * 0.42 + i * 0.5)}>{esc(line)}</li>"
        for i, line in enumerate(content["lines"])
    )
    return (
        f"<h2 {reveal(0.1)}>{esc(content['headline'])}</h2>"
        f'<div class="rule"></div>'
        f'<p class="bignum" {reveal(dur * 0.22)}>{esc(content["number"])}'
        f'<span class="unit">{esc(content["unit"])}</span></p>'
        f'<ul class="provenance">{items}</ul>'
    )


def scene_confident_number(content: dict, dur: float, strings: dict) -> str:
    """Scene three: the same number, wrong, and sure of itself."""
    items = "".join(
        f"<li {reveal(dur * 0.5 + i * 0.5)}>{esc(line)}</li>"
        for i, line in enumerate(content["lines"])
    )
    return (
        f"<h2 {reveal(0.1)}>{esc(content['headline'])}</h2>"
        f'<div class="rule"></div>'
        f'<p class="bignum wrong" {reveal(dur * 0.26)}>{esc(strings["wrong_number"])}'
        f'<span class="unit">{esc(strings["wrong_unit"])}</span></p>'
        f'<ul class="provenance">{items}</ul>'
        f'<p class="verdict" {reveal(dur * 0.78)}>'
        f'<span class="mark">&#10007;</span>{esc(strings["and_nothing_said"])}</p>'
    )


def scene_yaml(content: dict, dur: float) -> str:
    """Scene four: the model, as it is actually written."""
    rows = []
    step = (dur * 0.5) / max(len(YAML_LINES), 1)
    for i, line in enumerate(YAML_LINES):
        spans = "".join(
            f'<span class="{line[j]}">{esc(line[j + 1])}</span>' for j in range(0, len(line), 2)
        )
        rows.append(f"<div {reveal(dur * 0.26 + i * step, 0.3)}>{spans}</div>")
    subs = "".join(
        f'<p class="sub" {reveal(dur * 0.78 + i * 0.3)}>{esc(line)}</p>'
        for i, line in enumerate(content["lines"])
    )
    return (
        f"<h2 {reveal(0.1)}>{esc(content['headline'])}</h2>"
        f'<div class="rule"></div>'
        f'<div class="code">{"".join(rows)}</div>'
        f'<div style="margin-top:38px;display:flex;flex-direction:column;gap:12px">{subs}</div>'
    )


def scene_statuses(content: dict, dur: float) -> str:
    """Scene five: the four statuses, each in its own colour."""
    rows = []
    step = (dur * 0.62) / max(len(content["statuses"]), 1)
    for i, (name, what) in enumerate(content["statuses"]):
        kind = STATUS_CLASS.get(name, "placeholder")
        rows.append(
            f'<div class="status {kind}" {reveal(dur * 0.2 + i * step)}>'
            f'<span class="name">{esc(name)}</span>'
            f'<span class="what">{esc(what)}</span></div>'
        )
    return (
        f"<h2 {reveal(0.1)}>{esc(content['headline'])}</h2>"
        f'<div class="statuses">{"".join(rows)}</div>'
    )


def scene_chain(content: dict, dur: float, strings: dict) -> str:
    """Draw the derivation, with the status falling to its weakest input.

    Every line under the chain is drawn, not only the first: the headline
    promises two rules, and a frame that shows one of them takes the promise
    back while the voice is still making it.
    """
    chain = strings["chain"]
    rows = []
    step = (dur * 0.5) / max(len(chain), 1)
    for i, row in enumerate(chain):
        cells = []
        for cell in row:
            if cell[0] == "op":
                cells.append(f'<span class="op">{esc(cell[1])}</span>')
            else:
                cells.append(
                    f'<span class="node {cell[0]}"><span class="label">{esc(cell[1])}</span>'
                    f'<span class="tag">{esc(cell[2])}</span></span>'
                )
        rows.append(f'<div class="row" {reveal(dur * 0.16 + i * step)}>{"".join(cells)}</div>')
    return (
        f"<h2 {reveal(0.1)}>{esc(content['headline'])}</h2>"
        f'<div class="chain">{"".join(rows)}</div>'
        + "".join(
            f'<p class="sub" style="margin-top:{46 if i == 0 else 14}px" '
            f"{reveal(dur * (0.70 + i * 0.12))}>{esc(line)}</p>"
            for i, line in enumerate(content["lines"])
        )
    )


def scene_checked(content: dict, dur: float) -> str:
    """Scene seven: the validator recomputing rather than believing."""
    rows = []
    step = (dur * 0.55) / max(len(content["lines"]), 1)
    for i, line in enumerate(content["lines"]):
        rows.append(
            f'<div class="check" {reveal(dur * 0.2 + i * step)}>'
            f'<span class="mark">&#8594;</span><span>{esc(line)}</span></div>'
        )
    return (
        f"<h2 {reveal(0.1)}>{esc(content['headline'])}</h2>"
        f'<div class="checks">{"".join(rows)}</div>'
    )


def scene_refusals(content: dict, dur: float) -> str:
    """Scene eight: what it answers when it does not know."""
    rows = []
    step = (dur * 0.55) / max(len(content["refusals"]), 1)
    for i, (when, then) in enumerate(content["refusals"]):
        rows.append(
            f'<div class="refusal" {reveal(dur * 0.2 + i * step)}>'
            f'<span class="when">{esc(when)}</span>'
            f'<span class="then">{esc(then)}</span></div>'
        )
    return (
        f"<h2 {reveal(0.1)}>{esc(content['headline'])}</h2>"
        f'<div class="refusals">{"".join(rows)}</div>'
    )


def scene_close(content: dict, dur: float) -> str:
    """Scene nine: the five surfaces, three counts, and the install line."""
    surfaces = "".join(
        f'<span class="surface" {reveal(dur * 0.16 + i * 0.16)}>{esc(name)}</span>'
        for i, name in enumerate(content["surfaces"])
    )
    facts = "".join(
        f'<div class="fact" {reveal(dur * 0.42 + i * 0.22)}>'
        f'<div class="n">{esc(n)}</div><div class="what">{esc(what)}</div></div>'
        for i, (n, what) in enumerate(content["facts"])
    )
    return (
        f"<h2 {reveal(0.1)}>{esc(content['headline'])}</h2>"
        f'<div class="surfaces">{surfaces}</div>'
        f'<div class="facts">{facts}</div>'
        f'<div class="close">'
        f'<span class="cmd" {reveal(dur * 0.66)}>{esc(content["command"])}</span>'
        f'<span class="url" {reveal(dur * 0.76)}>{esc(content["url"])}</span>'
        f"</div>"
        f'<div class="close">'
        f'<span class="star" {reveal(dur * 0.86)}>{esc(content["star"])}</span>'
        f"</div>"
    )


def scene_interval(content: dict, dur: float) -> str:
    """Scene six: one sourced figure, and the figure it forces to be a range.

    Two rows and nothing else. The first is an input that is impeccably
    sourced and still only good to a fifth; the second is what the model is
    then obliged to say about the number computed from it. The line under them
    is the whole demonstration: it is a thing that *fails*, which is the only
    kind of guarantee worth filming.
    """
    rows = "".join(
        f'<div class="interval" {reveal(dur * 0.22 + i * 0.30)}>'
        f'<span class="point">{esc(point)}</span>'
        f'<span class="span">{esc(span)}</span>'
        f'<span class="why">{esc(why)}</span>'
        f"</div>"
        for i, (point, span, why) in enumerate(content["rows"])
    )
    return (
        f"<h2 {reveal(0.1)}>{esc(content['headline'])}</h2>"
        f'<div class="intervals">{rows}</div>'
        f'<p class="note" {reveal(dur * 0.74)}>{esc(content["note"])}</p>'
    )


def scene_punchline(content: dict, dur: float) -> str:
    """Scene eight: the line the film is for, in two halves.

    No chips, no counts, no command. Everything before this earned the right
    to say one sentence, and a frame with anything else on it would take the
    sentence back.
    """
    return (
        f'<div class="punch">'
        f'<div class="one" {reveal(0.15)}>{esc(content["headline"])}</div>'
        f'<div class="two" {reveal(dur * 0.42)}>{esc(content["emphasis"])}</div>'
        f"</div>"
    )


BUILDERS = {
    "question": scene_question,
    "loose-number": scene_loose_number,
    "confident-number": scene_confident_number,
    "yaml": scene_yaml,
    "statuses": scene_statuses,
    "chain": scene_chain,
    "checked": scene_checked,
    "refusals": scene_refusals,
    "close": scene_close,
    "interval": scene_interval,
    "punchline": scene_punchline,
}

#: The few strings the frames need that the narration never says, so they
#: live here rather than being back-formed from a spoken line.
STRINGS = {
    "en": {
        "wrong_number": "1.4",
        "wrong_unit": "gCO2e",
        "and_nothing_said": "a thousand times out. Nothing on the page says so.",
        "title": "What it costs to run your code",
        "chain": [
            [
                ("measured", "runtime", "measured"),
                ("op", "×"),
                ("measured", "power draw", "measured"),
                ("op", "="),
                ("measured", "machine energy", "measured"),
            ],
            [
                ("measured", "machine energy", "measured"),
                ("op", "×"),
                ("estimated", "power usage effectiveness", "estimated"),
                ("op", "="),
                ("estimated", "building energy", "estimated"),
            ],
            [
                ("estimated", "building energy", "estimated"),
                ("op", "×"),
                ("estimated", "grid carbon intensity", "estimated"),
                ("op", "="),
                ("estimated", "carbon", "estimated"),
            ],
            [
                ("measured", "machine energy", "measured"),
                ("op", "×"),
                ("todo", "water usage effectiveness", "TODO"),
                ("op", "="),
                ("todo", "water", "TODO"),
            ],
        ],
    },
    "fr": {
        "wrong_number": "1,4",
        "wrong_unit": "gCO2e",
        "and_nothing_said": "faux d'un facteur mille. Rien sur la page ne le dit.",
        "title": "Ce que coûte votre code à l'exécution",
        "chain": [
            [
                ("measured", "durée", "mesuré"),
                ("op", "×"),
                ("measured", "puissance appelée", "mesuré"),
                ("op", "="),
                ("measured", "énergie de la machine", "mesuré"),
            ],
            [
                ("measured", "énergie de la machine", "mesuré"),
                ("op", "×"),
                ("estimated", "efficacité énergétique du site", "estimé"),
                ("op", "="),
                ("estimated", "énergie du bâtiment", "estimé"),
            ],
            [
                ("estimated", "énergie du bâtiment", "estimé"),
                ("op", "×"),
                ("estimated", "intensité carbone du réseau", "estimé"),
                ("op", "="),
                ("estimated", "carbone", "estimé"),
            ],
            [
                ("measured", "énergie de la machine", "mesuré"),
                ("op", "×"),
                ("todo", "efficacité d'usage de l'eau", "TODO"),
                ("op", "="),
                ("todo", "eau", "TODO"),
            ],
        ],
    },
}


def timeline(script: dict, measured: dict, lang: str) -> list[dict]:
    """Each scene with the start and length the voice gave it."""
    tail = float(script["film"]["tail"])
    out, clock = [], 0.0
    for scene in script["scenes"]:
        spoken = float(measured[lang][scene["id"]])
        dur = round(spoken + tail, 3)
        out.append(
            {
                "id": scene["id"],
                "visual": scene["visual"],
                "start": round(clock, 3),
                "dur": dur,
                "spoken": spoken,
                "content": scene[lang],
            }
        )
        clock += dur
    return out


def compose(lang: str) -> dict:
    """Write one language's composition, and return its timeline."""
    script = yaml.safe_load(SCRIPT.read_text(encoding="utf-8"))
    measured = json.loads(MEASURED.read_text(encoding="utf-8"))
    strings = STRINGS[lang]
    scenes = timeline(script, measured, lang)

    blocks = []
    for scene in scenes:
        builder = BUILDERS[scene["visual"]]
        if builder in (scene_confident_number, scene_chain):
            body = builder(scene["content"], scene["dur"], strings)
        else:
            body = builder(scene["content"], scene["dur"])
        blocks.append(
            f'<section class="scene" id="{scene["id"]}" '
            f'data-start="{scene["start"]}" data-dur="{scene["dur"]}">{body}</section>'
        )

    total = round(sum(s["dur"] for s in scenes), 3)
    page = (
        f'<!doctype html>\n<html lang="{lang}" data-film="{esc(script["film"]["name"])}" '
        f'data-duration="{total}" data-fps="{script["film"]["fps"]}">\n<head>\n'
        f'<meta charset="utf-8">\n<title>{esc(strings["title"])}</title>\n'
        f"<style>{STYLE}</style>\n</head>\n<body>\n"
        f'<div id="stage">\n{"".join(blocks)}\n</div>\n'
        f"<script>{SEEK}</script>\n</body>\n</html>\n"
    )
    COMPOSITION.mkdir(parents=True, exist_ok=True)
    (COMPOSITION / f"index.{lang}.html").write_text(page, encoding="utf-8")
    return {"lang": lang, "duration": total, "scenes": scenes}


def main() -> int:
    """Write both compositions from the script and the measured voice."""
    for lang in ("en", "fr"):
        result = compose(lang)
        print(
            f"{lang}: {result['duration']:.2f}s over {len(result['scenes'])} scenes "
            f"-> composition/index.{lang}.html"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
