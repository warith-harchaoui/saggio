"""
Where the code runs: country, provider, machine shape, and what they imply.

Module summary
--------------
A kilowatt-hour is not a cost until you say where it was drawn. The same run
emits four times more carbon in Poland than in France and costs three times more
in Germany than in Egypt, so the deployment context is not decoration around a
cost model, it is half of it.

The part of this that used to go wrong is the country. Guessing it from a
developer's locale, or from a timezone, and then writing the guess into a file as
though it were a fact, is exactly the dishonesty this package exists to prevent.
So the country is resolved through an explicit ladder, and each rung produces a
different honesty status:

1. the caller passed one, which is a human assertion, so ``measured``;
2. the environment names one, same thing, so ``measured``;
3. the machine's timezone sits in exactly one country in the catalogue, which is
   an inference, so ``estimated``, with a note saying it was inferred;
4. nothing resolved, so ``TODO``, and the report asks for it by name.

Everything else the context provides comes from the catalogues, so every number
it hands back carries the URL it was read from and the date it was read.

Usage example
-------------
>>> from running_code_cost_helper.estimate.context import DeploymentContext
>>> context = DeploymentContext.build(country="FR", provider="on-prem")
>>> context.grid_intensity().value
56
>>> context.grid_intensity().status
'estimated'

Author
------
Warith Harchaoui
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import os_helper as osh

from ..catalog.registry import Catalog
from ..model.quantity import Quantity
from ..model.taxonomy import ESTIMATED, MEASURED, TODO

#: Environment variable a user or a container sets to state the country outright.
COUNTRY_ENVIRONMENT_VARIABLE: Final[str] = "RUNNING_CODE_COST_COUNTRY"

#: Where a Unix machine's timezone name can be read without a third-party
#: dependency: the symlink the system points at a zoneinfo file.
_LOCALTIME_LINK: Final[Path] = Path("/etc/localtime")

#: The path component that precedes the IANA zone name inside that symlink.
_ZONEINFO_MARKER: Final[str] = "zoneinfo/"

#: Provider assumed when a model names none: the machine in front of you.
DEFAULT_PROVIDER: Final[str] = "on-prem"

#: The currency the bundled tariffs are quoted in. A model may hold any currency;
#: this is only the one the catalogue's own prices carry.
CATALOG_CURRENCY: Final[str] = "USD"


def local_timezone_name() -> str | None:
    """Return the machine's IANA timezone name, or ``None`` when unknowable.

    Three sources are tried, cheapest first: the ``TZ`` environment variable, the
    ``/etc/localtime`` symlink on Unix, and the standard library's own idea of
    the local zone. Windows names its zones differently and is not mapped here,
    so it simply returns ``None`` and the country falls to the next rung of the
    ladder rather than being guessed.

    Returns
    -------
    str or None
        Something like ``Europe/Paris``, or ``None``.

    Examples
    --------
    >>> name = local_timezone_name()
    >>> name is None or "/" in name
    True
    """
    from_env = os.environ.get("TZ", "").strip()
    if "/" in from_env:
        return from_env

    if osh.unix():
        try:
            if _LOCALTIME_LINK.is_symlink():
                target = str(_LOCALTIME_LINK.readlink())
                if _ZONEINFO_MARKER in target:
                    return target.split(_ZONEINFO_MARKER, 1)[1]
        except OSError:
            # An unreadable symlink is not worth an exception: fall through and
            # let the country stay unresolved, which the ladder handles.
            pass

    try:
        from datetime import datetime

        key = getattr(datetime.now().astimezone().tzinfo, "key", None)
        if isinstance(key, str) and "/" in key:
            return key
    except (OSError, ValueError):
        pass
    return None


def country_from_timezone(timezone: str, *, overlay: Path | None = None) -> str | None:
    """Return the one country a timezone sits in, or ``None`` when ambiguous.

    A timezone listed under two countries resolves to neither. Half a guess is
    worse than none: it would put a number in a file that nobody chose.

    Parameters
    ----------
    timezone : str
        An IANA zone name such as ``Europe/Paris``.
    overlay : pathlib.Path or None, optional
        Catalogue overlay directory.

    Returns
    -------
    str or None
        An ISO 3166-1 alpha-2 code, or ``None``.

    Examples
    --------
    >>> country_from_timezone("Europe/Paris")
    'FR'
    >>> country_from_timezone("Antarctica/Troll") is None
    True
    """
    matches = [
        key
        for key, row in Catalog.load("grid", overlay=overlay).rows("countries").items()
        if timezone in (row.get("timezones") or [])
    ]
    return matches[0] if len(matches) == 1 else None


@dataclass(slots=True)
class DeploymentContext:
    """The resolved answer to "where does this run, and what does that cost".

    Parameters
    ----------
    country : str or None
        ISO 3166-1 alpha-2 code, or ``None`` when it could not be resolved.
    country_status : str
        The honesty status of :attr:`country`, per the resolution ladder.
    country_note : str or None
        How the country was arrived at, written into every quantity derived from
        it so a reader can see the inference rather than having to guess at it.
    provider : str
        Catalogue key of the provider, such as ``on-prem`` or ``gcp``.
    instance : str or None
        Catalogue key of the machine shape, when one is named.
    overlay : pathlib.Path or None
        Catalogue overlay directory.

    Examples
    --------
    >>> DeploymentContext.build(country="SE").grid_intensity().value
    13
    """

    country: str | None = None
    country_status: str = TODO
    country_note: str | None = None
    provider: str = DEFAULT_PROVIDER
    instance: str | None = None
    overlay: Path | None = None

    @classmethod
    def build(
        cls,
        *,
        country: str | None = None,
        provider: str | None = None,
        instance: str | None = None,
        overlay: Path | None = None,
        allow_timezone_inference: bool = True,
    ) -> DeploymentContext:
        """Resolve the deployment context, country ladder and all.

        Parameters
        ----------
        country : str or None, optional
            An ISO 3166-1 alpha-2 code the caller is asserting.
        provider : str or None, optional
            A provider key; defaults to :data:`DEFAULT_PROVIDER`.
        instance : str or None, optional
            A machine-shape key from the instances catalogue.
        overlay : pathlib.Path or None, optional
            Catalogue overlay directory.
        allow_timezone_inference : bool, optional
            Whether to try the timezone rung of the ladder. Turn it off in tests,
            and whenever an inferred country would be worse than none at all.

        Returns
        -------
        DeploymentContext
            The resolved context.

        Examples
        --------
        >>> DeploymentContext.build(country="fr").country
        'FR'
        >>> DeploymentContext.build(allow_timezone_inference=False).country_status
        'TODO'
        """
        resolved, status, note = cls._resolve_country(
            country, overlay=overlay, allow_timezone_inference=allow_timezone_inference
        )
        return cls(
            country=resolved,
            country_status=status,
            country_note=note,
            provider=(provider or DEFAULT_PROVIDER),
            instance=instance,
            overlay=overlay,
        )

    @staticmethod
    def _resolve_country(
        explicit: str | None,
        *,
        overlay: Path | None,
        allow_timezone_inference: bool,
    ) -> tuple[str | None, str, str | None]:
        """Walk the country ladder and return what it found and how.

        Parameters
        ----------
        explicit : str or None
            A country the caller asserted.
        overlay : pathlib.Path or None
            Catalogue overlay directory.
        allow_timezone_inference : bool
            Whether the timezone rung may be used.

        Returns
        -------
        tuple
            The country code or ``None``, its honesty status, and a note saying
            how it was arrived at.

        Examples
        --------
        >>> DeploymentContext._resolve_country("DE", overlay=None,
        ...                                    allow_timezone_inference=False)[:2]
        ('DE', 'measured')
        """
        known = Catalog.load("grid", overlay=overlay).rows("countries")

        if explicit:
            code = explicit.strip().upper()
            if code in known:
                return code, MEASURED, "Stated by the caller."
            osh.warning(
                f"Country {code!r} is not in the grid catalogue; "
                "add it before its carbon intensity can be used."
            )
            return code, MEASURED, "Stated by the caller; not in the grid catalogue."

        from_env = os.environ.get(COUNTRY_ENVIRONMENT_VARIABLE, "").strip().upper()
        if from_env and from_env in known:
            return from_env, MEASURED, f"Read from ${COUNTRY_ENVIRONMENT_VARIABLE}."

        if allow_timezone_inference:
            timezone = local_timezone_name()
            if timezone:
                inferred = country_from_timezone(timezone, overlay=overlay)
                if inferred:
                    return (
                        inferred,
                        ESTIMATED,
                        f"Inferred from the machine timezone {timezone}; "
                        "confirm it before quoting the carbon number.",
                    )
        return None, TODO, "Not resolved; state the country the code runs in."

    def _country_row(self) -> dict[str, Any] | None:
        """Return the grid catalogue row for the resolved country.

        Returns
        -------
        dict or None
            The row, or ``None`` when no country resolved or it is unknown.

        Examples
        --------
        >>> DeploymentContext.build(country="NO")._country_row()["name"]
        'Norway'
        """
        if not self.country:
            return None
        return Catalog.load("grid", overlay=self.overlay).row("countries", self.country)

    def _provider_row(self) -> dict[str, Any] | None:
        """Return the providers catalogue row for the resolved provider.

        Returns
        -------
        dict or None
            The row, or ``None`` when the provider is not in the catalogue.

        Examples
        --------
        >>> DeploymentContext.build(provider="gcp")._provider_row()["name"]
        'Google Cloud'
        """
        return Catalog.load("providers", overlay=self.overlay).row("providers", self.provider)

    def country_name(self) -> str | None:
        """Return the resolved country's human name.

        Returns
        -------
        str or None
            The name, or ``None`` when no country resolved.

        Examples
        --------
        >>> DeploymentContext.build(country="JP").country_name()
        'Japan'
        """
        row = self._country_row()
        return str(row["name"]) if row and row.get("name") else None

    def grid_intensity(self) -> Quantity:
        """Return the grid carbon intensity where the code runs.

        Returns
        -------
        Quantity
            Grams of CO2 equivalent per kilowatt-hour, sourced from the grid
            catalogue, or a ``TODO`` naming what is missing. The result is never
            stronger than the country it depends on: an inferred country yields
            an estimated intensity at best.

        Examples
        --------
        >>> DeploymentContext.build(country="PL").grid_intensity().unit
        'gCO2e/kWh'
        >>> DeploymentContext.build(allow_timezone_inference=False).grid_intensity().status
        'TODO'
        """
        row = self._country_row()
        if row is None or row.get("carbon_gco2e_per_kwh") is None:
            return Quantity(
                unit="gCO2e/kWh",
                status=TODO,
                notes=(
                    self.country_note
                    if self.country is None
                    else f"No grid intensity catalogued for {self.country}."
                ),
            )
        return Quantity(
            value=row["carbon_gco2e_per_kwh"],
            unit="gCO2e/kWh",
            status=ESTIMATED,
            source_url=row.get("source_url"),
            retrieved_date=row.get("retrieved_date"),
            notes=self._country_derived_note(f"Annual average for {row.get('name')}."),
        )

    def electricity_price(self) -> Quantity:
        """Return the price of a kilowatt-hour where the code runs.

        A cloud provider that sells machine-hours rather than electricity has no
        per-kilowatt-hour price of its own, so the country tariff is used and the
        note says so. That is an approximation, and saying which approximation is
        the point.

        Returns
        -------
        Quantity
            Price per kilowatt-hour with its currency, or a ``TODO``.

        Examples
        --------
        >>> DeploymentContext.build(country="DE").electricity_price().currency
        'USD'
        """
        provider_row = self._provider_row()
        if provider_row and provider_row.get("price_usd_per_kwh") is not None:
            return Quantity(
                value=provider_row["price_usd_per_kwh"],
                unit=f"{CATALOG_CURRENCY}/kWh",
                currency=CATALOG_CURRENCY,
                status=ESTIMATED,
                source_url=provider_row.get("source_url"),
                retrieved_date=provider_row.get("retrieved_date"),
                notes=f"Published by {provider_row.get('name')}.",
            )
        row = self._country_row()
        if row is None or row.get("price_usd_per_kwh") is None:
            return Quantity(
                unit=f"{CATALOG_CURRENCY}/kWh",
                currency=CATALOG_CURRENCY,
                status=TODO,
                notes=(
                    self.country_note
                    if self.country is None
                    else f"No electricity tariff catalogued for {self.country}."
                ),
            )
        note = f"Indicative tariff for {row.get('name')}."
        if provider_row and self.provider != DEFAULT_PROVIDER:
            note += (
                f" {provider_row.get('name')} sells machine-hours rather than kilowatt-hours, "
                "so the local tariff stands in for the electricity inside that price."
            )
        return Quantity(
            value=row["price_usd_per_kwh"],
            unit=f"{CATALOG_CURRENCY}/kWh",
            currency=CATALOG_CURRENCY,
            status=ESTIMATED,
            source_url=row.get("source_url"),
            retrieved_date=row.get("retrieved_date"),
            notes=self._country_derived_note(note),
        )

    def pue(self) -> Quantity:
        """Return the datacenter overhead multiplier for the provider.

        Returns
        -------
        Quantity
            Power usage effectiveness, dimensionless, or a ``TODO`` when the
            provider is not catalogued.

        Examples
        --------
        >>> DeploymentContext.build(provider="gcp").pue().value
        1.09
        """
        row = self._provider_row()
        if row is None or row.get("pue") is None:
            return Quantity(
                unit="ratio",
                status=TODO,
                notes=f"Provider {self.provider!r} is not in the providers catalogue.",
            )
        return Quantity(
            value=row["pue"],
            unit="ratio",
            status=ESTIMATED,
            source_url=row.get("source_url"),
            retrieved_date=row.get("retrieved_date"),
            notes=f"Power usage effectiveness published by {row.get('name')}.",
        )

    def water_effectiveness(self) -> Quantity:
        """Return litres of cooling water per kilowatt-hour of IT load.

        Returns
        -------
        Quantity
            Water usage effectiveness, or a ``TODO`` when the provider publishes
            none. Most do not, and a water figure invented in its absence would
            be the worst kind of number in a sustainability report.

        Examples
        --------
        >>> DeploymentContext.build(provider="gcp").water_effectiveness().value
        0.99
        >>> DeploymentContext.build(provider="lambda").water_effectiveness().status
        'TODO'
        """
        row = self._provider_row()
        if row is None or row.get("wue_l_per_kwh") is None:
            name = row.get("name") if row else self.provider
            return Quantity(
                unit="L/kWh",
                status=TODO,
                notes=(
                    f"{name} publishes no water usage effectiveness. "
                    "Leave this open rather than inventing a figure."
                ),
            )
        return Quantity(
            value=row["wue_l_per_kwh"],
            unit="L/kWh",
            status=ESTIMATED,
            source_url=row.get("source_url"),
            retrieved_date=row.get("retrieved_date"),
            notes=f"On-site water usage effectiveness published by {row.get('name')}; "
            "it excludes the water used to generate the electricity.",
        )

    def instance_power(self) -> Quantity:
        """Return the sustained power draw of the named machine shape.

        Returns
        -------
        Quantity
            Watts for the whole node, or a ``TODO`` when no instance is named or
            it is not catalogued.

        Examples
        --------
        >>> DeploymentContext.build(instance="node-1x-a100").instance_power().value
        550
        >>> DeploymentContext.build().instance_power().status
        'TODO'
        """
        if not self.instance:
            return Quantity(
                unit="W",
                status=TODO,
                notes="No instance type named; measure the machine or name its shape.",
            )
        row = Catalog.load("instances", overlay=self.overlay).row("instances", self.instance)
        if row is None or row.get("sustained_power_w") is None:
            return Quantity(
                unit="W",
                status=TODO,
                notes=f"Instance {self.instance!r} is not in the instances catalogue.",
            )
        return Quantity(
            value=row["sustained_power_w"],
            unit="W",
            status=ESTIMATED,
            source_url=row.get("source_url"),
            retrieved_date=row.get("retrieved_date"),
            notes=f"Nameplate-derived sustained draw for {row.get('name')}; "
            "measure the machine to replace this with a recorded figure.",
        )

    def _country_derived_note(self, note: str) -> str:
        """Append the country's provenance to a note when it was inferred.

        Parameters
        ----------
        note : str
            The note so far.

        Returns
        -------
        str
            The note, with the country's own provenance appended when the country
            was not asserted by a human.

        Examples
        --------
        >>> context = DeploymentContext(country="FR", country_status="estimated",
        ...                             country_note="Inferred from the timezone.")
        >>> context._country_derived_note("Tariff.")
        'Tariff. Inferred from the timezone.'
        """
        if self.country_status == MEASURED or not self.country_note:
            return note
        return f"{note} {self.country_note}"

    def to_mapping(self) -> dict[str, Any]:
        """Serialise the context for the model's deployment block.

        Returns
        -------
        dict
            Plain strings only. The numbers the context implies go into the
            assumptions block as quantities, not here.

        Examples
        --------
        >>> sorted(DeploymentContext.build(country="FR", provider="aws").to_mapping())
        ['country', 'country_provenance', 'provider']
        """
        mapping: dict[str, Any] = {"provider": self.provider}
        if self.country:
            mapping["country"] = self.country
        if self.country_note:
            mapping["country_provenance"] = self.country_note
        if self.instance:
            mapping["instance_type"] = self.instance
        return mapping
