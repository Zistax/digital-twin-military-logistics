"""Weekly depot windows with a UTC epoch and an explicit local timezone."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .core import natural


@dataclass(frozen=True)
class Calendar:
    # Monday=0; opening included, closing excluded; 86400 means midnight next day.
    windows: tuple[tuple[int, int, int], ...]
    timezone_name: str = "Europe/Rome"

    def __post_init__(self):
        ZoneInfo(self.timezone_name)
        if not isinstance(self.windows, tuple) or not self.windows:
            raise ValueError("nonempty immutable weekly windows required")
        for window in self.windows:
            if not isinstance(window, tuple) or len(window) != 3:
                raise ValueError("window must contain weekday, opening, closing")
            for value in window:
                natural(value, "window value")
        previous = {}
        for window in sorted(self.windows):
            if not isinstance(window, tuple) or len(window) != 3:
                raise ValueError("window must contain weekday, opening, closing")
            day, start, end = window
            for value in window:
                natural(value, "window value")
            if day > 6 or not 0 <= start < end <= 86400:
                raise ValueError("invalid weekly window")
            if day in previous and start < previous[day]:
                raise ValueError("overlapping windows")
            previous[day] = end

    @classmethod
    def daily(cls, opening=0, closing=86400, weekdays=range(7)):
        return cls(tuple((day, opening, closing) for day in weekdays))

    def _intervals(self, epoch, at_s, days=9):
        instant = epoch + timedelta(seconds=at_s)
        zone = ZoneInfo(self.timezone_name)
        date = instant.astimezone(zone).date()
        for offset in range(-1, days):
            day = date + timedelta(days=offset)
            for weekday, opening, closing in sorted(self.windows):
                if day.weekday() != weekday:
                    continue
                midnight = datetime.combine(day, time())
                start = (midnight + timedelta(seconds=opening)).replace(tzinfo=zone)
                end = (midnight + timedelta(seconds=closing)).replace(
                    tzinfo=zone, fold=1
                )
                for boundary in (start, end):
                    roundtrip = boundary.astimezone(timezone.utc).astimezone(zone)
                    if roundtrip.replace(tzinfo=None) != boundary.replace(tzinfo=None):
                        raise ValueError("calendar boundary falls in a DST gap")
                yield (
                    int((start.astimezone(timezone.utc) - epoch).total_seconds()),
                    int((end.astimezone(timezone.utc) - epoch).total_seconds()),
                )

    def is_open(self, epoch, at_s):
        return any(start <= at_s < end for start, end in self._intervals(epoch, at_s))

    def next_change(self, epoch, at_s):
        return min(
            t for interval in self._intervals(epoch, at_s) for t in interval if t > at_s
        )

    def closed_seconds(self, epoch, start_s, end_s):
        closed = 0
        cursor = start_s
        while cursor < end_s:
            stop = min(end_s, self.next_change(epoch, cursor))
            if not self.is_open(epoch, cursor):
                closed += stop - cursor
            cursor = stop
        return closed
