"""Running the package with ``python -m saggio``.

Module summary
--------------
The console script installed as ``saggio`` is the ordinary way in. This is the
other one, and it matters more than it looks: ``python -m saggio`` runs the
command line out of *this* interpreter's environment, whatever is on the PATH.
That is what somebody reaches for when two versions are installed, what a test
suite needs to exercise the working tree rather than whatever was installed
last, and what works in a container where no scripts directory is on the PATH.

Without it the package answers ``'saggio' is a package and cannot be directly
executed``, which reads as though the tool is broken rather than as though one
file is missing.

Usage example
-------------
.. code-block:: console

   $ python -m saggio --version
   saggio 1.4.2

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .cli.app import run

run()
