"""The arithmetic the browser does, against the arithmetic the package does.

The standalone report carries a panel that recomputes energy, carbon, money and
water for another country, provider or machine. It does that in the reader's
browser, from a JSON blob the renderer injected, because the alternative is a
page that has to ask a server what a different grid would cost.

So the same chain is written twice: once in :mod:`saggio.estimate.energy` and
once in ``reporting/report.js``. Until this file, nothing held the two
together. The formatting halves were pinned -- a contract test already refuses
a script that invents its own decimal separator -- but the *arithmetic* was
pinned by nothing. A page that printed a carbon figure the model disagreed with
would be the worst number this package can produce: it would carry the model's
provenance and not the model's value.

What is checked is the real shipped file, run under Node against a blob from a
real rendered report, rather than a transcription of its formulas into Python.
A transcription would pass forever while the file it claims to describe drifted
away from it.

Node rather than a browser on purpose. The panel's arithmetic is arithmetic:
it needs an engine, not a layout, and asking continuous integration to install
a browser to multiply three numbers would cost more than the defect it guards.
Where no engine answers, these skip -- the same shape the measuring probes use,
which report what the machine can do rather than asserting the machine is a
particular one.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "reporting" / "report.js"

#: The model rendered for these checks. It is committed, it carries a measured
#: runtime and a measured machine energy, and both are what the panel needs to
#: have anything to recompute from.
MODEL = ROOT / "examples" / "render.yaml"

#: The smallest DOM that lets the shipped script reach its arithmetic. It is
#: written beside the test rather than shipped in ``reporting/`` because it is
#: scaffolding for a check, not part of the report: nothing a reader receives
#: has a stub in it.
HARNESS = """
const fs = require('fs');
const [, , scriptPath, blobPath, choicesPath] = process.argv;

const values = {};
const listeners = {};
function stub(id) {
  return {
    id,
    get value() { return values[id] === undefined ? '' : values[id]; },
    set value(v) { values[id] = v; },
    textContent: '',
    dataset: {},
    setAttribute() {},
    getAttribute() { return null; },
    addEventListener(kind, run) { (listeners[id] = listeners[id] || []).push(run); },
    focus() {},
  };
}

const nodes = { 'report-data': { textContent: fs.readFileSync(blobPath, 'utf8') } };
for (const id of ['theme-toggle', 'language-toggle', 'whatif-country',
                  'whatif-provider', 'whatif-machine', 'whatif-energy',
                  'whatif-carbon', 'whatif-money', 'whatif-water',
                  'whatif-basis']) {
  nodes[id] = stub(id);
}

global.document = {
  getElementById: (id) => nodes[id] || null,
  documentElement: { setAttribute() {}, removeAttribute() {} },
  querySelectorAll: () => [],
  addEventListener() {},
};
global.window = { matchMedia: () => ({ matches: false }) };
global.localStorage = { getItem: () => null, setItem() {} };
global.navigator = { language: 'en' };

// The script wires each picker to recompute on change, so driving the panel is
// setting the values and firing that handler -- the same path a reader takes.
require(scriptPath);

const shown = [];
for (const choice of JSON.parse(fs.readFileSync(choicesPath, 'utf8'))) {
  values['whatif-country'] = choice.country || '';
  values['whatif-provider'] = choice.provider || '';
  values['whatif-machine'] = choice.machine || '';
  for (const run of listeners['whatif-country'] || []) { run(); }
  shown.push({
    energy: nodes['whatif-energy'].textContent,
    carbon: nodes['whatif-carbon'].textContent,
    money: nodes['whatif-money'].textContent,
    water: nodes['whatif-water'].textContent,
  });
}
console.log(JSON.stringify(shown));
"""

#: The panel prints three significant figures, so a comparison against the full
#: precision Python carries has to allow for the rounding the reader sees.
#:
#: Measured rather than argued: multiplying the carbon term by 1.02 fails this
#: check and by 1.005 does not, so it catches an error of two per cent and
#: tolerates one of a half. Every defect it is for -- an overhead applied
#: twice, water taking the building's energy, a term dropped -- is tens of per
#: cent, and the display rounding is tenths.
TOLERANCE = 1e-2


def _node() -> str:
    """Return the Node executable, or skip when the machine has none."""
    found = shutil.which("node")
    if found is None:
        pytest.skip("no JavaScript engine on this machine; the panel is unchecked here")
    return found


@pytest.fixture(scope="module")
def blob(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """Render a committed model and return the data the page would carry."""
    page = tmp_path_factory.mktemp("report") / "report.html"
    subprocess.run(  # noqa: S603 - a fixed argument list, never a shell.
        [sys.executable, "-m", "saggio", "render", str(MODEL), "-f", "html", "-o", str(page)],
        check=True,
        capture_output=True,
    )
    found = re.search(
        r'<script type="application/json" id="report-data">(.*?)</script>',
        page.read_text(encoding="utf-8"),
        re.S,
    )
    assert found is not None, "the rendered page carries no data blob for the panel"
    return json.loads(found.group(1))


@pytest.fixture(scope="module")
def harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("harness") / "harness.js"
    path.write_text(HARNESS, encoding="utf-8")
    return path


def panel(
    harness: Path, blob: dict, tmp_path: Path, choices: list[dict[str, str]]
) -> list[dict[str, float | None]]:
    """Return what the panel shows for each set of selections, as numbers.

    Every selection goes through one engine, because starting one per country
    turned a check into half a minute: thirty-eight processes to multiply three
    numbers each. A test that costs that much gets skipped, which is a worse
    outcome than the defect it guards against.
    """
    written = tmp_path / "blob.json"
    written.write_text(json.dumps(blob), encoding="utf-8")
    asked = tmp_path / "choices.json"
    asked.write_text(json.dumps(choices), encoding="utf-8")
    done = subprocess.run(  # noqa: S603 - a fixed argument list, never a shell.
        [_node(), str(harness), str(SCRIPT), str(written), str(asked)],
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        {key: _as_number(text) for key, text in shown.items()} for shown in json.loads(done.stdout)
    ]


def _as_number(text: str) -> float | None:
    """Read the figure out of what the panel printed, or None for a refusal."""
    found = re.match(r"^(-?[\d.]+(?:e[-+]?\d+)?)", text.strip())
    return float(found.group(1)) if found else None


def test_the_panel_and_the_package_agree_on_every_country(
    harness: Path, blob: dict, tmp_path: Path
) -> None:
    """Carbon and money, for each grid the page offers, both ways.

    The chain is energy times overhead, then that against the grid's intensity
    and its tariff. Getting the overhead in the wrong place is the defect this
    is for: applied twice it inflates every figure on the page by the cooling
    of the building, and nothing on the page would look wrong.
    """
    from saggio.estimate.energy import carbon_from_energy, facility_energy, money_from_energy
    from saggio.model.quantity import Quantity

    machine_energy = blob["machine_energy_kwh"]
    provider = "on-prem"
    overhead = blob["providers"][provider]["pue"]

    grids = sorted(blob["countries"].items())
    panels = panel(
        harness,
        blob,
        tmp_path,
        [{"country": code, "provider": provider} for code, _ in grids],
    )

    def known(value: float) -> Quantity:
        return Quantity(value=value, status="estimated")

    disagreed: list[str] = []
    for (code, grid), shown in zip(grids, panels, strict=True):
        facility = facility_energy(known(machine_energy), known(overhead))
        expected = {
            "energy": float(facility.value),
            "carbon": float(carbon_from_energy(facility, known(grid["carbon"])).value),
            "money": float(money_from_energy(facility, known(grid["price"])).value),
        }
        for name, want in expected.items():
            got = shown[name]
            if got is None or abs(got - want) > TOLERANCE * abs(want):
                disagreed.append(f"{code} {name}: panel {got}, package {want}")

    assert not disagreed, (
        "the browser and the package compute different figures from the same "
        f"inputs: {disagreed[:6]}. Both chains are in this repository -- "
        "saggio/estimate/energy.py and reporting/report.js -- and a page that "
        "states a number its own model disagrees with is the worst output here."
    )


def test_water_follows_the_machine_rather_than_the_building(
    harness: Path, blob: dict, tmp_path: Path
) -> None:
    """Water is per kilowatt-hour of computing load, not of facility energy.

    This is the one term in the chain that does *not* take the overhead, and
    the reason is in the package's own docstring: water usage effectiveness is
    defined against the information-technology load, so multiplying it by
    facility energy counts the cooling twice. A panel that applied the overhead
    uniformly would be wrong only here, and only by the overhead -- which is
    exactly the size of mistake that survives a glance.
    """
    from saggio.estimate.energy import water_from_energy
    from saggio.model.quantity import Quantity

    wet = sorted(
        code for code, provider in blob["providers"].items() if provider.get("wue") is not None
    )
    if not wet:
        pytest.skip("no provider in this model publishes a water figure")

    machine_energy = blob["machine_energy_kwh"]
    country = sorted(blob["countries"])[0]
    panels = panel(
        harness, blob, tmp_path, [{"country": country, "provider": code} for code in wet]
    )
    disagreed: list[str] = []
    for code, shown in zip(wet, panels, strict=True):
        want = float(
            water_from_energy(
                Quantity(value=machine_energy, status="estimated"),
                Quantity(value=blob["providers"][code]["wue"], status="estimated"),
            ).value
        )
        got = shown["water"]
        if got is None or abs(got - want) > TOLERANCE * abs(want):
            disagreed.append(f"{code}: panel {got}, package {want}")

    assert not disagreed, (
        f"the panel's water figure is not the package's: {disagreed}. "
        "Water takes the machine's own energy; the overhead belongs to the "
        "carbon and the money and to nothing else."
    )


def test_swapping_the_machine_recomputes_rather_than_rescales(
    harness: Path, blob: dict, tmp_path: Path
) -> None:
    """Choosing another part makes the energy from its rating and the runtime.

    Not a ratio against the measured figure: the runtime is the measurement
    that survives the swap, and the power is the thing that changed. The
    package reaches the same figure through ``it_energy_from_runtime``, which
    is the function this is pinned against.
    """
    from saggio.estimate.energy import facility_energy, it_energy_from_runtime
    from saggio.model.quantity import Quantity

    runtime = blob.get("runtime_s")
    if not runtime:
        pytest.skip("this model has no measured runtime, so no swap is offered")

    parts = [
        (f"gpu:{name}", part) for name, part in sorted(blob.get("accelerators", {}).items())
    ] + [(f"cpu:{name}", part) for name, part in sorted(blob.get("processors", {}).items())]
    if not parts:
        pytest.skip("this model's page offers no machine to swap to")

    provider = "on-prem"
    overhead = blob["providers"][provider]["pue"]
    country = sorted(blob["countries"])[0]

    panels = panel(
        harness,
        blob,
        tmp_path,
        [{"country": country, "provider": provider, "machine": choice} for choice, _ in parts],
    )

    def known(value: float) -> Quantity:
        return Quantity(value=value, status="estimated")

    disagreed: list[str] = []
    for (choice, part), shown in zip(parts, panels, strict=True):
        want = float(
            facility_energy(
                it_energy_from_runtime(known(runtime), known(part["watts"])), known(overhead)
            ).value
        )
        got = shown["energy"]
        if got is None or abs(got - want) > TOLERANCE * abs(want):
            disagreed.append(f"{choice}: panel {got}, package {want}")

    assert not disagreed, (
        f"the panel's swapped-machine energy is not the package's: {disagreed[:5]}. "
        "Energy is runtime times the part's rating; a panel that rescaled the "
        "measured figure instead would be right only where the ratings happen "
        "to divide evenly."
    )


def test_a_model_with_no_energy_gets_no_invented_one(
    harness: Path, blob: dict, tmp_path: Path
) -> None:
    """Nothing to rescale means nothing is shown, not a zero and not a guess.

    This is the package's whole proposition reaching the browser: a figure the
    model never established does not acquire a value by being asked for in a
    different country.
    """
    hollow = dict(blob)
    hollow["machine_energy_kwh"] = None
    shown = panel(
        harness,
        hollow,
        tmp_path,
        [{"country": sorted(blob["countries"])[0], "provider": "on-prem"}],
    )[0]
    invented = {name: value for name, value in shown.items() if value is not None}
    assert not invented, (
        f"the panel invented {invented} from a model that states no energy. "
        "A what-if built on an unestablished baseline is the one number this "
        "package must never print."
    )
