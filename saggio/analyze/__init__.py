"""
Finding out what a repository is and what it costs to run.

Module summary
--------------
Three ways of knowing, in descending order of trust, and each one labelled so the
difference survives into the report. :mod:`static` reads the code and owns every
number that comes from reading. :mod:`run` and :mod:`power` execute a bounded
slice, with the user's explicit consent, and own every number that comes from
measurement. :mod:`llm` asks a local model what shape the work is, and owns no
number at all.

Usage example
-------------
>>> from saggio.analyze import read_repository
>>> read_repository(".").archetype is not None
True

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from .apple import SocEnergy, SocMeter
from .capability import Interface, measurable, paths_read, probe, summary
from .llm import (
    WORKLOAD_KINDS,
    Classification,
    classify,
    installed_models,
    is_available,
    pick_model,
)
from .power import (
    RAPL_SCOPE_NOTE,
    GraphicsSampler,
    PowerMeter,
    PowerReading,
    read_graphics_energy_microjoules,
    read_graphics_watts,
    read_memory_energy_microjoules,
    read_package_energy_microjoules,
    unavailable_reason,
)
from .run import (
    CONSENT_PROMPT,
    DEFAULT_TIMEOUT_SECONDS,
    ProfileEntry,
    SliceResult,
    consent_path,
    has_consent,
    record_consent,
    require_consent,
    run_slice,
)
from .static import (
    DEFAULT_CAP_FRACTION,
    RepositoryReading,
    ServiceHit,
    WorkSizeCandidate,
    capped_entrypoint_command,
    detect_archetype,
    detect_frameworks,
    detect_languages,
    detect_services,
    detect_tests,
    find_entrypoint,
    find_work_size,
    read_repository,
)

__all__ = [
    # Static reading.
    "RepositoryReading",
    "ServiceHit",
    "WorkSizeCandidate",
    "read_repository",
    "detect_languages",
    "detect_archetype",
    "detect_frameworks",
    "detect_services",
    "detect_tests",
    "find_entrypoint",
    "find_work_size",
    "capped_entrypoint_command",
    "DEFAULT_CAP_FRACTION",
    # Power.
    "PowerMeter",
    "PowerReading",
    "GraphicsSampler",
    "RAPL_SCOPE_NOTE",
    "read_package_energy_microjoules",
    "read_memory_energy_microjoules",
    "read_graphics_energy_microjoules",
    "read_graphics_watts",
    "unavailable_reason",
    # Apple Silicon, read without privileges.
    "SocMeter",
    "SocEnergy",
    # What this machine will let you read, and what it would take.
    "Interface",
    "probe",
    "measurable",
    "summary",
    "paths_read",
    # Running.
    "SliceResult",
    "ProfileEntry",
    "run_slice",
    "has_consent",
    "record_consent",
    "require_consent",
    "consent_path",
    "CONSENT_PROMPT",
    "DEFAULT_TIMEOUT_SECONDS",
    # Local model.
    "Classification",
    "WORKLOAD_KINDS",
    "classify",
    "is_available",
    "installed_models",
    "pick_model",
]
