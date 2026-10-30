"""The deployment context, and the country ladder that refuses to guess."""

from __future__ import annotations

from pathlib import Path

import pytest

from saggio.estimate.context import (
    COUNTRY_ENVIRONMENT_VARIABLE,
    DeploymentContext,
    _names_a_zone,
    country_from_timezone,
    local_timezone_name,
)


def build(**kwargs) -> DeploymentContext:
    kwargs.setdefault("allow_timezone_inference", False)
    return DeploymentContext.build(**kwargs)


# --- The country ladder ------------------------------------------------------


def test_a_stated_country_is_a_human_assertion() -> None:
    context = build(country="FR")
    assert (context.country, context.country_status) == ("FR", "measured")


def test_a_stated_country_is_normalised() -> None:
    assert build(country=" fr ").country == "FR"


def test_the_environment_can_state_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(COUNTRY_ENVIRONMENT_VARIABLE, "se")
    context = build()
    assert (context.country, context.country_status) == ("SE", "measured")


def test_a_timezone_inference_is_only_an_estimate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(COUNTRY_ENVIRONMENT_VARIABLE, raising=False)
    monkeypatch.setenv("TZ", "Europe/Paris")
    context = DeploymentContext.build(allow_timezone_inference=True)
    assert (context.country, context.country_status) == ("FR", "estimated")
    assert "timezone" in str(context.country_note)


def test_nothing_resolved_stays_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(COUNTRY_ENVIRONMENT_VARIABLE, raising=False)
    context = build()
    assert context.country is None
    assert context.country_status == "TODO"


def test_a_country_in_two_countries_timezone_resolves_to_neither() -> None:
    # Half a guess is worse than none: it would put a number in a file nobody chose.
    assert country_from_timezone("Antarctica/Troll") is None


def test_the_timezone_reader_returns_a_zone_or_nothing() -> None:
    name = local_timezone_name()
    assert name is None or _names_a_zone(name)


def test_a_zone_name_without_a_slash_is_still_a_zone_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The assertion this replaces failed on the first machine that was not ours.

    `UTC`, `GMT`, `Japan`, `Singapore`, `Israel` and `EST5EDT` are all real
    entries in the timezone database and none of them has a slash. The reader
    filtered on the slash, so on a machine set to any of them the `TZ` somebody
    had deliberately set was discarded and the machine's own zone used instead:
    a stated input silently replaced by a different one, answering with a
    perfectly ordinary-looking country.

    Found by putting macOS back in the gate. A CI runner is set to UTC, which no
    developer's laptop is, and the suite had never run anywhere that was.
    """
    monkeypatch.setenv("TZ", "UTC")
    assert local_timezone_name() == "UTC"


def test_a_zone_the_user_asked_for_beats_the_machine_it_runs_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The user-visible half of the same defect. `TZ=Japan` used to be dropped,
    # and the country came back as whatever the laptop was in -- which is a
    # different country's grid, in a file somebody will quote.
    #
    # `Japan` is a backward-compatibility link, and a minimal Linux image ships
    # a database without those. Asserting it resolves encodes the developer's
    # machine: this test passed on macOS and failed on the Linux runner, where
    # the answer was the runner's own `Etc/UTC`. What has to hold on every
    # machine is that the answer is the zone that was asked for, or nothing --
    # never a different one.
    monkeypatch.setenv("TZ", "Japan")
    assert local_timezone_name() in {"Japan", None}


def test_a_stated_zone_the_database_cannot_resolve_gives_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never this machine's zone, which is a different country's grid.

    Fixing the detection left the fall-through. On a database without the
    backward links, `TZ=Japan` failed the check and the *next source* answered
    -- with `/etc/localtime`, the machine's own zone. A stated input replaced
    by a plausible wrong one is the defect this whole package exists to refuse,
    and it was in the function whose docstring describes refusing it.
    """
    here = local_timezone_name()
    monkeypatch.setenv("TZ", "Definitely/Not-A-Zone")
    answer = local_timezone_name()
    assert answer is None, (
        f"a zone the database cannot resolve gave {answer!r}. It must give "
        "None so the country falls to the next rung, rather than to wherever "
        "this machine happens to be."
    )
    assert answer != here, "the stated zone was replaced by the machine's own"


def test_an_unresolvable_zone_gives_no_country_rather_than_the_laptop_s(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """And the catalogue not knowing a name is not a licence to use another.

    `Japan` is a compatibility name the database keeps; the catalogue lists
    `Asia/Tokyo`. So the country stays open. That is the right outcome and the
    point of the fix: before it, this resolved to the country the developer
    happened to be sitting in.
    """
    monkeypatch.delenv(COUNTRY_ENVIRONMENT_VARIABLE, raising=False)
    monkeypatch.setenv("TZ", "Japan")
    assert country_from_timezone("Japan") is None
    assert build().country is None


@pytest.mark.parametrize(
    "value",
    [
        "EST5EDT,M3.2.0,M11.1.0",  # a POSIX rule string, not a zone name
        "/etc/passwd",  # an absolute path, which zoneinfo refuses outright
        "../../etc/passwd",  # and one climbing out of the database
        "Europe/Nowhere",  # a plausible shape the database does not have
        "",
    ],
)
def test_what_is_not_a_zone_name_is_not_taken_for_one(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The other direction of the same question. A slash was never evidence: a
    # POSIX rule string can carry one and names no zone at all.
    monkeypatch.setenv("TZ", value)
    assert local_timezone_name() != value


def test_a_country_the_catalogue_does_not_know_is_still_the_users_word() -> None:
    context = build(country="ZZ")
    assert context.country == "ZZ"
    assert context.grid_intensity().status == "TODO"


# --- What the context implies ------------------------------------------------


def test_the_grid_intensity_comes_with_its_source() -> None:
    # The name of this test is the claim: what has to hold is that the figure
    # arrives with provenance attached, and that it is the catalogue's figure
    # rather than one invented on the way. Restating the number here made a
    # routine refresh look like a regression.
    from saggio.catalog import Catalog

    expected = Catalog.bundled("grid").rows("countries")["PL"]["carbon_gco2e_per_kwh"]
    intensity = build(country="PL").grid_intensity()
    assert intensity.value == pytest.approx(float(expected))
    assert intensity.source_url
    assert intensity.retrieved_date


def test_norway_survives_yaml_reading_it_as_a_boolean() -> None:
    # Unquoted, YAML reads NO as false and Norway vanishes from the catalogue
    # with no error anywhere. The keys are quoted; this is the guard for it.
    # What proves it is that Norway resolves at all, not what its grid emits.
    intensity = build(country="NO").grid_intensity()
    assert intensity.status != "TODO"
    assert isinstance(intensity.value, (int, float))
    assert intensity.source_url


def test_an_inferred_country_carries_its_provenance_into_what_it_derives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(COUNTRY_ENVIRONMENT_VARIABLE, raising=False)
    monkeypatch.setenv("TZ", "Europe/Paris")
    context = DeploymentContext.build(allow_timezone_inference=True)
    assert "timezone" in str(context.grid_intensity().notes)


def test_a_stated_country_does_not_clutter_the_notes() -> None:
    assert "timezone" not in str(build(country="FR").grid_intensity().notes)


def test_the_overhead_comes_from_the_provider() -> None:
    assert build(provider="gcp").pue().value == 1.09


def test_an_unknown_provider_leaves_the_overhead_open() -> None:
    assert build(provider="not-a-provider").pue().status == "TODO"


def test_a_provider_with_no_published_water_figure_leaves_water_open() -> None:
    water = build(provider="lambda").water_effectiveness()
    assert water.status == "TODO"
    assert "publishes no water" in str(water.notes)


def test_a_provider_that_publishes_one_gives_a_number() -> None:
    assert build(provider="gcp").water_effectiveness().value == 0.99


def test_a_self_run_room_in_the_union_is_told_where_a_published_figure_is() -> None:
    """The refusal names a way out when the reporting duty creates one.

    `STANDARDS.md` has said since the Commission's first assessment that *"for a
    room inside the Union, that sentence is no longer true"*. For a while the
    code did not know it: the catalogue carried `on-prem-eu` and nothing ever
    pointed a reader at it, so a French self-run room got the same bare `TODO`
    as a room in a country with no reporting duty at all.
    """
    water = build(country="FR").water_effectiveness()
    assert water.status == "TODO"
    assert "on-prem-eu" in str(water.notes)


def test_the_union_hint_is_scoped_to_membership_and_not_to_the_continent() -> None:
    """Britain, Norway and Switzerland are in Europe and not in the Union.

    The figure behind the hint is a Union-wide average published under a duty
    that binds Member States. A continent-shaped test would pass on a guess.
    """
    for country in ("GB", "NO", "CH"):
        assert "on-prem-eu" not in str(build(country=country).water_effectiveness().notes)


def test_the_union_hint_does_not_follow_a_vendor_machine() -> None:
    """A Member State's reported average says nothing about a vendor's hall."""
    water = build(country="FR", provider="lambda").water_effectiveness()
    assert water.status == "TODO"
    assert "on-prem-eu" not in str(water.notes)


def test_the_union_figure_is_named_and_never_taken() -> None:
    """Naming a row is not choosing it: the quantity stays open."""
    water = build(country="FR").water_effectiveness()
    assert water.value is None
    assert water.status == "TODO"


def test_a_cloud_price_falls_back_to_the_local_tariff_and_says_so() -> None:
    price = build(country="DE", provider="aws").electricity_price()
    assert price.currency == "USD"
    assert "machine-hours" in str(price.notes)


def test_no_country_leaves_the_price_open() -> None:
    assert build(provider="aws").electricity_price().status == "TODO"


def test_an_instance_gives_a_nameplate_power() -> None:
    power = build(instance="node-1x-a100").instance_power()
    assert power.value == 550
    assert power.status == "estimated"


def test_no_instance_leaves_the_power_open() -> None:
    assert build().instance_power().status == "TODO"


def test_an_unknown_instance_names_itself() -> None:
    result = build(instance="not-an-instance").instance_power()
    assert "not-an-instance" in str(result.notes)


def test_the_context_serialises_only_prose() -> None:
    mapping = build(country="FR", provider="aws", instance="node-1x-a100").to_mapping()
    assert set(mapping) == {"provider", "country", "country_provenance", "instance_type"}
    assert all(isinstance(value, str) for value in mapping.values())


def test_the_country_name_is_available_for_a_report() -> None:
    assert build(country="JP").country_name() == "Japan"
    assert build().country_name() is None


def test_an_overlay_row_wins(overlay: Path) -> None:
    import yaml

    (overlay / "grid.yaml").write_text(
        yaml.safe_dump(
            {
                "countries": [
                    {
                        "key": "FR",
                        "name": "France",
                        "carbon_gco2e_per_kwh": 1,
                        "price_usd_per_kwh": 0.01,
                        "source_url": "https://example.invalid",
                        "retrieved_date": "2026-09-12",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    context = DeploymentContext.build(country="FR", overlay=overlay, allow_timezone_inference=False)
    assert context.grid_intensity().value == 1
