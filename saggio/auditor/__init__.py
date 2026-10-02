"""
Turning a repository into a cost model.

Module summary
--------------
The module is called ``auditor`` and the function it exists for is called
``audit``, because ``saggio.audit`` would otherwise mean the
module in one import and the function in another, and monkeypatching the first
would silently patch the second.

This is the orchestrator, and the only place in the package where the three ways
of knowing meet. Reading the code establishes its shape and its size. The
operating system establishes what machine this is. The catalogues establish what
that machine draws and what the local grid emits. Running a bounded slice, when
the user has agreed to it, replaces the weakest of those guesses with a
measurement. The result is a cost model where every number says which of those it
came from.

The audit refuses to improve a number by pretending. A country nobody stated stays
open; a provider that publishes no water figure yields no water figure; a slice
that failed projects to nothing. Each of those is written into the model as a
``TODO`` with a sentence saying what would close it, which is the most useful
thing an incomplete model can do.

What is where
-------------
This was one file of 1,319 lines carrying seven unrelated concerns, which made
the one question a reader arrives with -- where does *this* number come from --
answerable only by reading the whole thing.

=================== ==========================================================
:mod:`~saggio.auditor.paths`        where each number lives in the model, as
                                    dotted paths the validator resolves
:mod:`~saggio.auditor.options`      what an audit was asked for, and produced
:mod:`~saggio.auditor.naming`       naming a command and a repository
:mod:`~saggio.auditor.blocks`       the parts read out of the repository
:mod:`~saggio.auditor.assumptions`  the numbers taken from the catalogues
:mod:`~saggio.auditor.measuring`    running a slice, and what it cost
:mod:`~saggio.auditor.projections`  from a slice to a run, and to other hardware
:mod:`~saggio.auditor.build`        the orchestration, and the clone
=================== ==========================================================

``audit`` itself is still a long function, and deliberately: it is a linear
recipe, and breaking a recipe into steps called once each means a reader has to
jump about to recover the order they were already being told.

Usage example
-------------
>>> from saggio.auditor import audit, AuditOptions
>>> result = audit(".", options=AuditOptions(run=False, use_llm=False, country="FR"))
>>> result.report.ok
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .build import audit, audit_git_url
from .naming import describe_command, repository_name
from .options import AuditOptions, AuditResult
from .paths import SCENARIO_NAME

__all__ = [
    "SCENARIO_NAME",
    "AuditOptions",
    "AuditResult",
    "audit",
    "audit_git_url",
    "describe_command",
    "repository_name",
]
