"""Version 1 contracts and deterministic replay for inspected deliveries.

Time is integer simulated seconds from a UTC run epoch. Events supplied to
replay must be observed, inspected deliveries, never hidden simulator outcomes.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING

SCHEMA_VERSION = 1


def natural(value: int, field: str, positive: bool = False) -> None:
    if type(value) is not int or value < int(positive):
        raise ValueError(f"{field}: expected integer >= {int(positive)}")


def identifier(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("identifier must be a non-empty string")


@dataclass(frozen=True)
class MissionLine:
    item_id: str
    requested: int
    threshold: Decimal

    def __post_init__(self) -> None:
        identifier(self.item_id)
        natural(self.requested, "requested", positive=True)
        if (
            not isinstance(self.threshold, Decimal)
            or not self.threshold.is_finite()
            or not Decimal(0) < self.threshold <= Decimal(1)
        ):
            raise ValueError("threshold: finite Decimal in (0, 1]")

    @property
    def minimum(self) -> int:
        return int(
            (self.requested * self.threshold).to_integral_value(rounding=ROUND_CEILING)
        )


@dataclass(frozen=True)
class Mission:
    simulation_id: str
    mission_id: str
    origin_id: str
    destination_id: str
    start_s: int
    deadline_s: int
    lines: tuple[MissionLine, ...]

    def __post_init__(self) -> None:
        for value in (
            self.simulation_id,
            self.mission_id,
            self.origin_id,
            self.destination_id,
        ):
            identifier(value)
        natural(self.start_s, "start_s")
        natural(self.deadline_s, "deadline_s")
        if self.origin_id == self.destination_id:
            raise ValueError("origin and destination must differ")
        if self.deadline_s <= self.start_s:
            raise ValueError("deadline must follow start")
        if not isinstance(self.lines, tuple) or not self.lines:
            raise ValueError("lines: non-empty immutable tuple required")
        if any(not isinstance(line, MissionLine) for line in self.lines):
            raise ValueError("lines: MissionLine required")
        if len({line.item_id for line in self.lines}) != len(self.lines):
            raise ValueError("duplicate mission item")


@dataclass(frozen=True)
class Delivery:
    event_id: str
    simulation_id: str
    mission_id: str
    trip_id: str
    batch_id: str
    item_id: str
    occurred_s: int
    observed_s: int
    accepted: int
    unusable: int = 0
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for value in (
            self.event_id,
            self.simulation_id,
            self.mission_id,
            self.trip_id,
            self.batch_id,
            self.item_id,
        ):
            identifier(value)
        for field in ("occurred_s", "observed_s", "accepted", "unusable"):
            natural(getattr(self, field), field)
        if self.observed_s < self.occurred_s:
            raise ValueError("observation cannot precede occurrence")
        if self.accepted + self.unusable == 0:
            raise ValueError("empty delivery")
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported schema version")


@dataclass(frozen=True)
class Outcome:
    status: str
    quota_reached_s: int | None
    late: bool | None
    delay_minutes: float | None
    accepted: dict[str, int]
    item_quota_s: dict[str, int | None]
    onboard: dict[str, int]
    unusable: dict[str, int]
    logistics_complete: bool


def replay(
    mission: Mission,
    loads: dict[tuple[str, str, str], int],
    events: list[Delivery],
    cutoff_s: int,
) -> Outcome:
    """Replay a sealed history through cutoff, with quantity conservation.

    loads keys are (trip_id, batch_id, item_id); each batch belongs to one trip
    and item in this first slice. The manifest represents already loaded cargo.
    Cutoff is inclusive, after all deliveries due at that timestamp.
    """
    natural(cutoff_s, "cutoff_s")
    if cutoff_s < mission.start_s:
        raise ValueError("cutoff precedes mission start")
    lines = {line.item_id: line for line in mission.lines}
    remaining = dict(loads)
    batches: set[str] = set()
    for key, quantity in remaining.items():
        if not isinstance(key, tuple) or len(key) != 3:
            raise ValueError("manifest key: (trip, batch, item) required")
        for value in key:
            identifier(value)
        natural(quantity, "loaded", positive=True)
        if key[2] not in lines or key[1] in batches:
            raise ValueError("unknown item or duplicated physical batch")
        batches.add(key[1])
    accepted = dict.fromkeys(lines, 0)
    unusable = dict.fromkeys(lines, 0)
    reached: dict[str, int | None] = dict.fromkeys(lines, None)
    seen: dict[str, Delivery] = {}
    visible = []
    for event in events:
        if event.observed_s > cutoff_s:
            continue
        if (event.simulation_id, event.mission_id) != (
            mission.simulation_id,
            mission.mission_id,
        ):
            raise ValueError("event belongs to another mission/run")
        if event.occurred_s < mission.start_s:
            raise ValueError("delivery precedes mission start")
        if event.event_id in seen:
            if seen[event.event_id] != event:
                raise ValueError("conflicting duplicate event")
            continue  # exact retry is idempotent
        seen[event.event_id] = event
        visible.append(event)
    # Acceptance occurs after inspection, hence at observed_s, not occurred_s.
    for event in sorted(visible, key=lambda e: (e.observed_s, e.event_id)):
        key = (event.trip_id, event.batch_id, event.item_id)
        moved = event.accepted + event.unusable
        if key not in remaining or moved > remaining[key]:
            raise ValueError("unknown cargo or quantity conservation violation")
        remaining[key] -= moved
        accepted[event.item_id] += event.accepted
        unusable[event.item_id] += event.unusable
        if (
            reached[event.item_id] is None
            and accepted[event.item_id] >= lines[event.item_id].minimum
        ):
            reached[event.item_id] = event.observed_s
    quota = (
        max(reached.values()) if all(t is not None for t in reached.values()) else None
    )
    if quota is not None:
        late = quota > mission.deadline_s
        delay = max(0, quota - mission.deadline_s) / 60
        status = "reached"
    else:
        late = True if cutoff_s >= mission.deadline_s else None
        delay = None
        status = "incomplete"
    onboard = dict.fromkeys(lines, 0)
    for (_, _, item), quantity in remaining.items():
        onboard[item] += quantity
    return Outcome(
        status,
        quota,
        late,
        delay,
        accepted,
        reached,
        onboard,
        unusable,
        all(q == 0 for q in remaining.values()),
    )
