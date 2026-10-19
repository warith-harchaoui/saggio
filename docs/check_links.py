"""Follow every link this repository asks a reader to follow.

Module summary
--------------
The argument of this package is that a figure says where it came from, and a
source a reader cannot reach is a figure that no longer does. Nothing checked
the links. There are more than two hundred of them — in the pages, and in the
catalogue rows beside the numbers they vouch for — and link rot is the one kind
of decay that happens without anybody touching the repository.

This is a maintenance script rather than a test, for the same reason
``docs/sync_api.py`` is: it reaches the network, and a suite that fails because
somebody's server is slow teaches people to ignore the suite. Run it before a
release, and read what it says rather than only its exit code.

**It reports categories, not pass or fail.** A previous iteration established
that Legifrance answers 403 to any client that is not a browser and that EUR-Lex
answers 202 with an empty body: on those hosts the probe cannot tell a good URL
from a bad one, and saying "dead" would be a worse lie than saying nothing. Only
404 and 410 — a server stating that it has no such document — are reported as
broken.

Usage example
-------------
.. code-block:: bash

    python3 docs/check_links.py            # report, exit 1 if anything is gone
    python3 docs/check_links.py --list     # just print what would be checked

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Any absolute link in prose, stopping before the punctuation a sentence puts
#: after it. Markdown link targets and bare URLs are both caught.
URL = re.compile(r"https?://[^\s)>\]\"'`]+")

#: Trailing characters a sentence leaves on a URL that are not part of it.
TRAILING = ".,;:"

#: What to send. A default Python user agent is refused by several of the hosts
#: cited here, and being refused is not the same as being gone.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

#: Seconds before a host is called unreachable rather than slow.
TIMEOUT = 20.0

#: A server saying it holds no such document. Everything else is a reason to
#: look, not a reason to fail.
GONE = {404, 410}

#: Hosts reserved for documentation by RFC 2606, plus the loopback a page names
#: when it is telling you to run something locally. A link that illustrates a
#: command rather than vouching for a number belongs on one of these, and the
#: rule is the point: an invented source on a real vendor's domain is
#: indistinguishable from a stale one, which is the worst a citation can be.
#: `nvidia.com/en-us/data-center/h300/` was exactly that, in four pages.
ILLUSTRATIVE = ("example.com", "example.net", "example.org", "example.edu",
                "localhost", "127.0.0.1", "::1")


def sources() -> dict[str, list[str]]:
    """Return every cited URL and where it is cited.

    Returns
    -------
    dict
        URL to the list of places citing it: page filenames, and
        ``catalogue:<name>`` for a row's own source.

    Examples
    --------
    >>> isinstance(sources(), dict)
    True
    """
    found: dict[str, list[str]] = collections.defaultdict(list)

    def illustrative(url: str) -> bool:
        """Return whether a link is an illustration rather than a citation."""
        host = url.split("://", 1)[-1].split("/", 1)[0].split(":")[0].lower()
        return host.endswith(".invalid") or host in ILLUSTRATIVE

    pages = [*ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md"), *(ROOT / "skills").rglob("*.md")]
    for page in sorted(pages):
        where = page.relative_to(ROOT).as_posix()
        for url in URL.findall(page.read_text(encoding="utf-8")):
            if not illustrative(url):
                found[url.rstrip(TRAILING)].append(where)
    # The catalogue rows matter more than the pages: a row's URL is what a
    # reader follows to check the number sitting beside it.
    from saggio.catalog.registry import SECTION_OF_KIND, Catalog

    for kind, (name, section) in SECTION_OF_KIND.items():
        for key, row in Catalog.load(name, overlay=Path("/nonexistent")).rows(section).items():
            for value in row.values():
                if isinstance(value, str) and value.startswith("http"):
                    if illustrative(value):
                        continue
                    found[value.rstrip(TRAILING)].append(f"catalogue:{kind}:{key}")
    return dict(found)


def probe(url: str) -> tuple[int | str, str]:
    """Return what a server says about one URL.

    Parameters
    ----------
    url : str
        The link to follow.

    Returns
    -------
    tuple
        ``(status, detail)``. ``status`` is an HTTP code, or a word when there
        was no reply at all. ``detail`` is the final URL after redirects, or
        the reason there was none.

    Examples
    --------
    >>> isinstance(probe("https://example.invalid/nothing"), tuple)
    True
    """
    if not url.startswith(("http://", "https://")):
        # The scheme is checked here rather than trusted, so that the opener
        # below can never be handed a `file:` URL by a page that acquired one.
        return "unreachable", "not an http link"
    request = urllib.request.Request(url, headers=HEADERS, method="GET")  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:  # noqa: S310
            return answer.status, answer.url
    except urllib.error.HTTPError as error:
        return error.code, url
    except urllib.error.URLError as error:
        return "unreachable", str(error.reason)
    except (TimeoutError, OSError, ValueError) as error:
        return "unreachable", str(error)


def main() -> int:
    """Probe every cited link and report what came back.

    Returns
    -------
    int
        ``0`` when no server said a document is gone, ``1`` when one did.

    Examples
    --------
    >>> callable(main)
    True
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", action="store_true", help="Print the links and stop.")
    options = parser.parse_args()

    cited = sources()
    print(f"{len(cited)} distinct links cited")
    if options.list:
        for url in sorted(cited):
            print(f"  {url}")
        return 0

    with ThreadPoolExecutor(max_workers=8) as pool:
        answers = dict(zip(cited, pool.map(probe, cited), strict=True))

    buckets: dict[str, list[str]] = collections.defaultdict(list)
    for url, (status, detail) in sorted(answers.items()):
        if status in GONE:
            buckets["gone"].append(f"{status}  {url}\n      cited in {', '.join(cited[url])}")
        elif isinstance(status, int) and 200 <= status < 300:
            buckets["ok"].append(url)
        elif status == "unreachable":
            buckets["unreachable"].append(f"{url}\n      {detail}")
        elif isinstance(status, int) and 300 <= status < 400:
            # Reported apart from a refusal, because it means something else:
            # the document is still there and the citation no longer points at
            # it. This is how the Gemini pricing row in the service catalogue
            # was found pointing at a page Google had moved.
            buckets["moved"].append(f"{status}  {url}\n      now at {detail}")
        else:
            buckets["refused"].append(f"{status}  {url}")

    print(f"  {len(buckets['ok'])} followable")
    for name, heading in (
        ("moved", "redirected: the citation no longer points where the document is"),
        ("refused", "answered, but not with the document (a robot filter, usually)"),
        ("unreachable", "no reply at all"),
        ("gone", "the server says it has no such document"),
    ):
        if not buckets[name]:
            continue
        print(f"\n{len(buckets[name])} {heading}:")
        for line in buckets[name]:
            print(f"  - {line}")
    return 1 if buckets["gone"] else 0


if __name__ == "__main__":
    sys.exit(main())
