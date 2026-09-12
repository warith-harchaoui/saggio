"""
The Green Algorithms chain: from watts and seconds to carbon, water, and money.

Module summary
--------------
This is the arithmetic at the centre of the package, and it is deliberately
small. Power multiplied by time is energy; energy multiplied by a grid intensity
is carbon; energy multiplied by a tariff is money; energy multiplied by a water
usage effectiveness is water. The method and the coefficients follow Lannelongue,
Grealey, and Inouye, *Green Algorithms: Quantifying the Carbon Footprint of
Computation* (Advanced Science, 2021).

Two distinctions are kept that are easy to lose, and expensive to lose.

*IT energy against facility energy.* The machine draws one amount; the building
draws that amount multiplied by its power usage effectiveness. Carbon and money
follow the facility figure, because that is what the grid supplies and the meter
counts. Water follows the IT figure, because water usage effectiveness is defined
per kilowatt-hour of IT load, and multiplying it by facility energy would count
the cooling overhead twice.

*Arithmetic against confidence.* Every function here returns a quantity whose
status is the weakest of its inputs, and a missing input produces a ``TODO``
rather than a zero. A zero is a claim. Silence is not.

Usage example
-------------
>>> from running_code_cost_helper.estimate.energy import it_energy_from_runtime
>>> from running_code_cost_helper.model import Quantity
>>> runtime = Quantity(value=3600.0, unit="s", status="measured")
>>> power = Quantity(value=1000.0, unit="W", status="estimated")
>>> energy = it_energy_from_runtime(runtime, power)
>>> energy.value, energy.status
(1.0, 'estimated')

Author
------
Warith Harchaoui
"""

from __future__ import annotations

from typing import Final

from ..catalog.registry import Catalog
from ..model.quantity import Quantity
from ..model.taxonomy import ESTIMATED, TODO, weakest

#: Power drawn per gigabyte of installed memory, in watts. From the Green
#: Algorithms paper, which derives it from manufacturer figures for DDR4.
MEMORY_POWER_W_PER_GB: Final[float] = 0.3725

#: Seconds in an hour, spelled out so the unit conversions read as physics rather
#: than as magic numbers.
_SECONDS_PER_HOUR: Final[float] = 3600.0

#: Watts in a kilowatt.
_WATTS_PER_KILOWATT: Final[float] = 1000.0

#: The published source for the method, carried on every quantity this module
#: derives so a reader can check the formula rather than take it on trust.
GREEN_ALGORITHMS_SOURCE: Final[str] = "https://doi.org/10.1002/advs.202100707"


def _combine(*inputs: Quantity) -> str | None:
    """Return the strongest status a value derived from these inputs may claim.

    Parameters
    ----------
    *inputs : Quantity
        The quantities a result is computed from.

    Returns
    -------
    str or None
        The weakest input status, or ``None`` when there were no inputs.

    Examples
    --------
    >>> _combine(Quantity(value=1, status="measured"), Quantity(value=2, status="estimated"))
    'estimated'
    """
    return weakest(*(item.status for item in inputs))


def _unresolved(unit: str, missing: str, *, currency: str | None = None) -> Quantity:
    """Return a ``TODO`` quantity naming the input that was not available.

    Parameters
    ----------
    unit : str
        The unit the result would have had.
    missing : str
        What is missing, phrased so a reader knows what to go and find.
    currency : str or None, optional
        Currency to carry when the result would have been money.

    Returns
    -------
    Quantity
        A ``TODO`` with the unit intact, so the shape of the model does not
        change when a number is unavailable.

    Examples
    --------
    >>> _unresolved("kWh", "no runtime").status
    'TODO'
    """
    return Quantity(unit=unit, currency=currency, status=TODO, notes=missing)


def node_power(
    *,
    cpu_key: str | None,
    physical_cores: int,
    memory_gb: float,
    gpu_key: str | None = None,
    accelerator_count: int = 0,
    overlay_catalog: Catalog | None = None,
) -> Quantity:
    """Estimate what a machine draws under load, from its parts.

    The sum is the Green Algorithms one: cores multiplied by per-core power, plus
    memory multiplied by per-gigabyte power, plus each accelerator's board power.
    It is an upper-ish bound on sustained draw and is always ``estimated``: a
    datasheet is not a wattmeter.

    Parameters
    ----------
    cpu_key : str or None
        Catalogue key of the CPU. ``None`` yields a ``TODO``, because a machine
        whose processor is unknown has no power figure worth stating.
    physical_cores : int
        Physical cores to count.
    memory_gb : float
        Installed memory in gigabytes.
    gpu_key : str or None, optional
        Catalogue key of the accelerator, when there is one.
    accelerator_count : int, optional
        How many of that accelerator are installed.
    overlay_catalog : Catalog or None, optional
        A pre-loaded hardware catalogue; loaded from the default location when
        not given.

    Returns
    -------
    Quantity
        Watts, ``estimated``, with the formula in its notes, or a ``TODO``
        naming the catalogue row that is missing.

    Examples
    --------
    >>> power = node_power(cpu_key="epyc-7742", physical_cores=64, memory_gb=512,
    ...                    gpu_key="A100", accelerator_count=1)
    >>> round(power.value, 1)
    814.7
    >>> node_power(cpu_key=None, physical_cores=8, memory_gb=16).status
    'TODO'
    """
    if not cpu_key:
        return _unresolved("W", "The CPU is not identified, so its power cannot be looked up.")

    catalog = overlay_catalog if overlay_catalog is not None else Catalog.load("hardware")
    cpu_row = catalog.row("cpus", cpu_key)
    if cpu_row is None or cpu_row.get("w_per_core") is None:
        return _unresolved(
            "W",
            f"CPU {cpu_key!r} is not in the hardware catalogue; "
            "add it with its datasheet TDP before a power figure can be given.",
        )

    cpu_power = float(cpu_row["w_per_core"]) * max(physical_cores, 1)
    memory_power = max(memory_gb, 0.0) * MEMORY_POWER_W_PER_GB
    parts = [
        f"{physical_cores} cores x {cpu_row['w_per_core']} W",
        f"{memory_gb:g} GB x {MEMORY_POWER_W_PER_GB} W/GB",
    ]

    gpu_power = 0.0
    if gpu_key and accelerator_count > 0:
        gpu_row = catalog.row("gpus", gpu_key)
        if gpu_row is None or gpu_row.get("tdp_w") is None:
            return _unresolved(
                "W",
                f"GPU {gpu_key!r} is not in the hardware catalogue; "
                "add it with its datasheet TDP before a power figure can be given.",
            )
        gpu_power = float(gpu_row["tdp_w"]) * accelerator_count
        parts.append(f"{accelerator_count} x {gpu_row['tdp_w']} W")

    return Quantity(
        value=cpu_power + memory_power + gpu_power,
        unit="W",
        status=ESTIMATED,
        source_url=GREEN_ALGORITHMS_SOURCE,
        retrieved_date=cpu_row.get("retrieved_date"),
        notes="Nameplate sum, Green Algorithms method: " + " + ".join(parts),
    )


def it_energy_from_runtime(runtime: Quantity, power: Quantity) -> Quantity:
    """Return the energy the machine itself draws over a runtime.

    Parameters
    ----------
    runtime : Quantity
        Wall-clock seconds for one unit of work.
    power : Quantity
        Average watts drawn while it runs.

    Returns
    -------
    Quantity
        Kilowatt-hours, at the weaker of the two input statuses, or a ``TODO``
        when either input has no number.

    Examples
    --------
    >>> it_energy_from_runtime(Quantity(value=7200.0, status="measured"),
    ...                        Quantity(value=500.0, status="measured")).value
    1.0
    >>> it_energy_from_runtime(Quantity(status="TODO"),
    ...                        Quantity(value=1.0, status="measured")).status
    'TODO'
    """
    if not (runtime.is_known() and power.is_known()):
        return _unresolved("kWh", "Needs both a runtime and an average power draw.")
    hours = float(runtime.value) / _SECONDS_PER_HOUR
    return Quantity(
        value=hours * float(power.value) / _WATTS_PER_KILOWATT,
        unit="kWh",
        status=_combine(runtime, power) or ESTIMATED,
        source_url=GREEN_ALGORITHMS_SOURCE,
        notes="runtime in hours x average power in watts / 1000.",
    )


def facility_energy(it_energy: Quantity, pue: Quantity) -> Quantity:
    """Return the energy the whole facility draws to run the machine.

    Parameters
    ----------
    it_energy : Quantity
        Kilowatt-hours drawn by the machine, from :func:`it_energy_from_runtime`.
    pue : Quantity
        The site's power usage effectiveness.

    Returns
    -------
    Quantity
        Kilowatt-hours including cooling, lighting, and conversion loss, or a
        ``TODO`` when either input has no number.

    Examples
    --------
    >>> facility_energy(Quantity(value=1.0, status="measured"),
    ...                 Quantity(value=1.2, status="estimated")).value
    1.2
    """
    if not (it_energy.is_known() and pue.is_known()):
        return _unresolved(
            "kWh",
            "Needs the machine's own energy and the site's power usage effectiveness.",
        )
    return Quantity(
        value=float(it_energy.value) * float(pue.value),
        unit="kWh",
        status=_combine(it_energy, pue) or ESTIMATED,
        source_url=GREEN_ALGORITHMS_SOURCE,
        notes="Machine energy x power usage effectiveness: what the building draws.",
    )


def energy_from_runtime(runtime: Quantity, power: Quantity, pue: Quantity) -> Quantity:
    """Return facility energy directly from runtime, power, and overhead.

    A convenience over :func:`it_energy_from_runtime` followed by
    :func:`facility_energy`, for the common case where a caller wants the number
    the meter would show and not the intermediate.

    Parameters
    ----------
    runtime : Quantity
        Wall-clock seconds for one unit of work.
    power : Quantity
        Average watts drawn while it runs.
    pue : Quantity
        The site's power usage effectiveness.

    Returns
    -------
    Quantity
        Kilowatt-hours for the whole facility.

    Examples
    --------
    >>> round(energy_from_runtime(Quantity(value=3600.0, status="measured"),
    ...                           Quantity(value=1000.0, status="estimated"),
    ...                           Quantity(value=1.5, status="estimated")).value, 2)
    1.5
    """
    return facility_energy(it_energy_from_runtime(runtime, power), pue)


def carbon_from_energy(energy: Quantity, intensity: Quantity) -> Quantity:
    """Return the grid emissions for an amount of facility energy.

    Parameters
    ----------
    energy : Quantity
        Facility kilowatt-hours.
    intensity : Quantity
        Grams of CO2 equivalent per kilowatt-hour where the code runs.

    Returns
    -------
    Quantity
        Grams of CO2 equivalent, or a ``TODO``. An unresolved country makes this
        a ``TODO`` rather than a zero, because "we do not know where this runs"
        and "this emits nothing" are different statements.

    Examples
    --------
    >>> carbon_from_energy(Quantity(value=2.0, status="measured"),
    ...                    Quantity(value=56, status="estimated")).value
    112.0
    >>> carbon_from_energy(Quantity(value=2.0, status="measured"),
    ...                    Quantity(status="TODO")).status
    'TODO'
    """
    if not (energy.is_known() and intensity.is_known()):
        return _unresolved(
            "gCO2e",
            "Needs the energy drawn and the grid carbon intensity where it runs.",
        )
    return Quantity(
        value=float(energy.value) * float(intensity.value),
        unit="gCO2e",
        status=_combine(energy, intensity) or ESTIMATED,
        source_url=GREEN_ALGORITHMS_SOURCE,
        notes="Facility energy x grid carbon intensity, operating emissions only.",
    )


def water_from_energy(it_energy: Quantity, effectiveness: Quantity) -> Quantity:
    """Return the cooling water for an amount of machine energy.

    Water usage effectiveness is defined per kilowatt-hour of IT load, so this
    takes the machine's own energy rather than the facility figure. Passing
    facility energy here would count the cooling overhead in both terms.

    Parameters
    ----------
    it_energy : Quantity
        Kilowatt-hours drawn by the machine itself.
    effectiveness : Quantity
        Litres of on-site water per kilowatt-hour of IT load.

    Returns
    -------
    Quantity
        Litres, or a ``TODO`` when the provider publishes no figure.

    Examples
    --------
    >>> water_from_energy(Quantity(value=10.0, status="measured"),
    ...                   Quantity(value=0.3, status="estimated")).value
    3.0
    """
    if not (it_energy.is_known() and effectiveness.is_known()):
        return _unresolved(
            "L",
            "Needs the machine's energy and a published water usage effectiveness.",
        )
    return Quantity(
        value=float(it_energy.value) * float(effectiveness.value),
        unit="L",
        status=_combine(it_energy, effectiveness) or ESTIMATED,
        notes="Machine energy x on-site water usage effectiveness; "
        "the water used to generate the electricity is not included.",
    )


def money_from_energy(energy: Quantity, price: Quantity) -> Quantity:
    """Return what an amount of facility energy costs.

    Parameters
    ----------
    energy : Quantity
        Facility kilowatt-hours.
    price : Quantity
        Price per kilowatt-hour, carrying its ISO 4217 currency.

    Returns
    -------
    Quantity
        An amount of money in the price's currency, or a ``TODO``.

    Examples
    --------
    >>> cost = money_from_energy(Quantity(value=10.0, status="measured"),
    ...                          Quantity(value=0.24, currency="EUR", status="estimated"))
    >>> round(cost.value, 2), cost.currency
    (2.4, 'EUR')
    """
    if not (energy.is_known() and price.is_known()):
        return _unresolved(
            "currency",
            "Needs the energy drawn and a price per kilowatt-hour.",
            currency=price.currency,
        )
    return Quantity(
        value=float(energy.value) * float(price.value),
        unit=price.currency or "currency",
        currency=price.currency,
        status=_combine(energy, price) or ESTIMATED,
        notes="Facility energy x price per kilowatt-hour; hardware and staff are not included.",
    )


def total_money(*amounts: Quantity) -> Quantity:
    """Add several money quantities, refusing to mix currencies.

    Parameters
    ----------
    *amounts : Quantity
        Money quantities to add. Ones with no number are skipped, and their
        absence weakens the total's status rather than being treated as zero.

    Returns
    -------
    Quantity
        The sum in the shared currency, or a ``TODO`` when the amounts are in
        different currencies or none of them carries a number.

    Examples
    --------
    >>> total = total_money(Quantity(value=1.0, currency="USD", status="measured"),
    ...                     Quantity(value=2.0, currency="USD", status="estimated"))
    >>> total.value, total.status
    (3.0, 'estimated')
    >>> total_money(Quantity(value=1.0, currency="USD", status="measured"),
    ...             Quantity(value=1.0, currency="EUR", status="measured")).status
    'TODO'
    """
    known = [amount for amount in amounts if amount.is_known()]
    if not known:
        return _unresolved("currency", "No money amount carried a number.")
    currencies = {amount.currency for amount in known if amount.currency}
    if len(currencies) > 1:
        listed = ", ".join(sorted(currencies))
        return _unresolved(
            "currency",
            f"The amounts are in different currencies ({listed}); "
            "convert them before adding, and record the rate you used.",
        )
    currency = next(iter(currencies), None)
    # An amount with no number is not zero; it is unknown, and an unknown term
    # drags the total's confidence down to the status that amount carried.
    statuses = [amount.status for amount in amounts]
    return Quantity(
        value=sum(float(amount.value) for amount in known),
        unit=currency or "currency",
        currency=currency,
        status=weakest(*statuses) or ESTIMATED,
        notes="Sum of the money costs of one unit of work.",
    )
