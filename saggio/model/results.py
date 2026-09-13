"""
The verdict of a check: errors, warnings, and where they were found.

Module summary
--------------
Validation, drift detection, and the catalog freshness gate all need to say the
same three things: what went wrong, how badly, and at which path in the model.
:class:`Issue` and :class:`Report` are that shared vocabulary. They never print
and never exit, so a library caller, a command line, and a web surface each
present the same verdict their own way.

Usage example
-------------
>>> from saggio.model.results import Report
>>> report = Report()
>>> report.error("scenarios[0].costs.energy", "claims measured but its inputs are estimated")
>>> report.ok
False
>>> print(report.to_text())
ERROR   scenarios[0].costs.energy: claims measured but its inputs are estimated

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final, Literal

#: The two severities. An error means the model must not be trusted as it
#: stands; a warning means it can be used but a reader should know something.
Severity = Literal["error", "warning"]

#: Column width for the severity in rendered text, so paths line up.
_SEVERITY_WIDTH: Final[int] = 7


@dataclass(frozen=True, slots=True)
class Issue:
    """One thing a check found, at one place in the model.

    Parameters
    ----------
    severity : {"error", "warning"}
        How badly it matters.
    path : str
        The dotted path it was found at, empty for a whole-model issue.
    message : str
        A sentence a human can act on, written without a leading capital so it
        reads as a continuation of the path.

    Examples
    --------
    >>> Issue("warning", "assumptions.pue", "has no source_url").to_text()
    'WARNING assumptions.pue: has no source_url'
    """

    severity: Severity
    path: str
    message: str

    def to_text(self) -> str:
        """Render the issue as one aligned line.

        Returns
        -------
        str
            ``SEVERITY path: message``, or ``SEVERITY message`` when there is no
            path to name.

        Examples
        --------
        >>> Issue("error", "", "the model has no scenario").to_text()
        'ERROR   the model has no scenario'
        """
        label = self.severity.upper().ljust(_SEVERITY_WIDTH)
        if not self.path:
            return f"{label} {self.message}"
        return f"{label} {self.path}: {self.message}"

    def to_mapping(self) -> dict[str, str]:
        """Serialise the issue for a JSON surface.

        Returns
        -------
        dict
            A mapping with ``severity``, ``path``, and ``message``.

        Examples
        --------
        >>> Issue("error", "a", "b").to_mapping()["severity"]
        'error'
        """
        return {"severity": self.severity, "path": self.path, "message": self.message}


@dataclass(slots=True)
class Report:
    """An accumulated verdict: every issue a check found, in order.

    Parameters
    ----------
    issues : list of Issue
        The issues found so far.

    Examples
    --------
    >>> report = Report()
    >>> report.warning("deployment.country", "is unknown")
    >>> report.ok
    True
    >>> len(report.warnings)
    1
    """

    issues: list[Issue] = field(default_factory=list)

    def add(self, severity: Severity, path: str, message: str) -> None:
        """Record an issue.

        Parameters
        ----------
        severity : {"error", "warning"}
            How badly it matters.
        path : str
            The dotted path it was found at.
        message : str
            What is wrong and what to do about it.

        Examples
        --------
        >>> report = Report(); report.add("error", "p", "is negative"); len(report.issues)
        1
        """
        self.issues.append(Issue(severity, path, message))

    def error(self, path: str, message: str) -> None:
        """Record an error.

        Parameters
        ----------
        path : str
            The dotted path it was found at.
        message : str
            What is wrong and what to do about it.

        Examples
        --------
        >>> report = Report(); report.error("p", "overclaims"); report.ok
        False
        """
        self.add("error", path, message)

    def warning(self, path: str, message: str) -> None:
        """Record a warning.

        Parameters
        ----------
        path : str
            The dotted path it was found at.
        message : str
            What a reader should know.

        Examples
        --------
        >>> report = Report(); report.warning("p", "is stale"); report.ok
        True
        """
        self.add("warning", path, message)

    def extend(self, other: Report) -> None:
        """Absorb another report's issues.

        Parameters
        ----------
        other : Report
            The report to absorb. It is left unchanged.

        Examples
        --------
        >>> a, b = Report(), Report()
        >>> b.warning("x", "y"); a.extend(b); len(a.issues)
        1
        """
        self.issues.extend(other.issues)

    @property
    def errors(self) -> list[Issue]:
        """Return the errors found.

        Returns
        -------
        list of Issue
            Every issue with severity ``error``.
        """
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        """Return the warnings found.

        Returns
        -------
        list of Issue
            Every issue with severity ``warning``.
        """
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def ok(self) -> bool:
        """Return whether the check passed.

        A model with warnings still passes: an honest model that admits it is
        incomplete must still load, or the taxonomy would punish honesty.

        Returns
        -------
        bool
            ``True`` when no error was recorded.
        """
        return not self.errors

    def to_text(self) -> str:
        """Render every issue as aligned lines.

        Returns
        -------
        str
            One line per issue, errors and warnings interleaved in the order
            they were found, or an empty string when there are none.

        Examples
        --------
        >>> Report().to_text()
        ''
        """
        return "\n".join(issue.to_text() for issue in self.issues)

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the whole verdict for a JSON surface.

        Returns
        -------
        dict
            A mapping with ``ok``, ``errors``, and ``warnings``, each list
            holding serialised issues.

        Examples
        --------
        >>> Report().to_mapping()["ok"]
        True
        """
        return {
            "ok": self.ok,
            "errors": [issue.to_mapping() for issue in self.errors],
            "warnings": [issue.to_mapping() for issue in self.warnings],
        }

    def summary(self) -> str:
        """Return a one-line count of what was found.

        Returns
        -------
        str
            A sentence naming the counts, suitable as the last line of a
            command's output.

        Examples
        --------
        >>> Report().summary()
        'Valid: 0 errors, 0 warnings.'
        """
        verdict = "Valid" if self.ok else "Invalid"
        errors, warnings = len(self.errors), len(self.warnings)
        plural_e = "" if errors == 1 else "s"
        plural_w = "" if warnings == 1 else "s"
        return f"{verdict}: {errors} error{plural_e}, {warnings} warning{plural_w}."
