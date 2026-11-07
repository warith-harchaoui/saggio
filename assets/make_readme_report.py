"""Photograph the web report the README and the LISEZMOI open on.

Module summary
--------------
The front pages used to describe the report for five hundred lines before a
reader saw one. This takes the picture instead: the HTML report of
``examples/render.yaml``, rendered by the package itself, then photographed in
a real browser, in English and in French, light and dark.

That example is the one chosen because it holds all three things the report
exists to show at once: numbers measured on a machine, numbers estimated from a
source, and numbers still left open as ``TODO``, with the chain that ties them.
An example where everything is measured would make the tool look like any other.

The picture is never edited by hand. If the report's design changes, run this
again; if the example changes, run this again.

Usage example
-------------
::

    pip install playwright
    python assets/make_readme_report.py

Playwright is not a dependency of the package: it is needed here and nowhere
else, by whoever regenerates these four files. It drives the Chrome already on
the machine rather than downloading one.

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLE = HERE.parent / "examples" / "render.yaml"

#: The browser window the report is photographed in: wide enough for the
#: derivation chain to sit on one row, short enough to stop under it.
VIEWPORT = {"width": 1280, "height": 900}

#: Language code, and the infix the other front-page figures use for it.
LANGUAGES = {"en": "", "fr": "fr."}


def render(lang: str, folder: pathlib.Path) -> pathlib.Path:
    """Render the example's web report in one language, with the package itself."""
    page = folder / f"report.{lang}.html"
    subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "saggio",
            "render",
            str(EXAMPLE),
            "-f",
            "html",
            "--language",
            lang,
            "-o",
            str(page),
        ],
        check=True,
    )
    return page


def main() -> None:
    """Write ``readme-report[.fr][.dark].png`` beside this file."""
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory() as scratch, sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        for lang, infix in LANGUAGES.items():
            page_file = render(lang, pathlib.Path(scratch))
            for scheme, suffix in (("light", ""), ("dark", "dark.")):
                page = browser.new_page(
                    viewport=VIEWPORT, device_scale_factor=2, color_scheme=scheme
                )
                page.goto(page_file.as_uri())
                page.wait_for_timeout(800)
                out = HERE / f"readme-report.{infix}{suffix}png"
                page.screenshot(path=str(out))
                page.close()
                print(out.name)
        browser.close()


if __name__ == "__main__":
    main()
