"""Persistent grouped traffic, map-wide weather and observation-only forecasts."""

from copy import deepcopy

from .core import natural
from .recovery import RecoveryWarehouse
from .scenarios import stream


class Conditions:
    def __init__(self, seed, profile, network):
        natural(seed, "seed")
        if profile not in ("regular", "pressure", "perturbed"):
            raise ValueError("unknown profile")
        self.perturbed = profile == "perturbed"
        self.traffic_rng = stream(seed, "traffic")
        self.weather_rng = stream(seed, "weather")
        self.forecast_rng = stream(seed, "forecast")
        self.groups = {}
        for edge in sorted(network.roads):
            a, b = (network.nodes[n] for n in edge)
            self.groups[edge] = int((a.x_km + b.x_km) / 2 >= 50) + 2 * int(
                (a.y_km + b.y_km) / 2 >= 50
            )
        lo, hi = self.traffic_range
        self.traffic = {g: (lo + hi) / 2 for g in sorted(set(self.groups.values()))}
        self.weather = 1.0
        self._weather_end = None
        self.next_s = 0
        self.at_s = -1
        self.history = []
        self.forecasts = []

    @property
    def traffic_range(self):
        return (1.2, 2.0) if self.perturbed else (1.0, 1.4)

    def advance(self, at_s):
        natural(at_s, "at_s")
        if at_s < self.at_s:
            raise ValueError("conditions cannot move backward")
        while self.next_s <= at_s:
            tick = self.next_s
            lo, hi = self.traffic_range
            for group in self.traffic:
                self.traffic[group] = 0.75 * self.traffic[
                    group
                ] + 0.25 * self.traffic_rng.uniform(lo, hi)
            if tick % 3600 == 0:
                if self._weather_end is not None and tick >= self._weather_end:
                    self.weather, self._weather_end = 1.0, None
                if self._weather_end is None and self.weather_rng.random() < (
                    0.15 if self.perturbed else 0.05
                ):
                    hours = (
                        self.weather_rng.randint(2, 6)
                        if self.perturbed
                        else self.weather_rng.randint(1, 3)
                    )
                    self._weather_end = tick + hours * 3600
                    self.weather = (
                        self.weather_rng.uniform(1.2, 1.5)
                        if self.perturbed
                        else self.weather_rng.uniform(1.1, 1.3)
                    )
                self.forecasts.append(self._forecast(tick, self.weather))
            self.history.append(
                {"at_s": tick, "traffic": dict(self.traffic), "weather": self.weather}
            )
            self.next_s += 1800
        self.at_s = at_s

    def _forecast(self, issued_s, observed_weather):
        # Deliberately uses no episode end time, weather RNG or future state.
        maximum = 1.5 if self.perturbed else 1.3
        values = []
        for hour in range(1, 7):
            expected = 1 + (observed_weather - 1) * (0.65**hour)
            error = self.forecast_rng.uniform(-0.08, 0.08) * (1 + hour / 6)
            values.append(
                {
                    "valid_from_s": issued_s + (hour - 1) * 3600,
                    "valid_to_s": issued_s + hour * 3600,
                    "weather": min(maximum, max(1.0, expected + error)),
                }
            )
        return {
            "version": len(self.forecasts) + 1,
            "model": "persistence-noise-v1",
            "issued_s": issued_s,
            "horizon_s": 21600,
            "values": values,
        }

    def observed(self):
        return deepcopy(
            {
                "observed_s": self.at_s,
                "traffic": self.traffic,
                "weather": self.weather,
                "forecast": self.forecasts[-1] if self.forecasts else None,
            }
        )


class EnvironmentWarehouse(RecoveryWarehouse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._environment = Conditions(
            self._policy.seed, self._policy.profile, self._network
        )

    def observed_environment(self):
        return self._environment.observed()

    def _finish(self, at_s):
        self._environment.advance(at_s)
        for edge, group in self._environment.groups.items():
            self._network.set_condition(
                *edge,
                traffic=self._environment.traffic[group],
                weather=self._environment.weather,
            )
        super()._finish(at_s)

    def _extra_event_times(self, cursor):
        times = super()._extra_event_times(cursor)
        if self._environment.next_s > cursor:
            times.append(self._environment.next_s)
        return times
