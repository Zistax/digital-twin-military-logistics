"""Seeded synthetic bidirectional graph and deterministic travel-time routing."""

from dataclasses import dataclass
from heapq import heappop, heappush
from math import ceil, hypot, isfinite
from random import Random

from .core import identifier, natural


class NoRoute(ValueError):
    pass


def finite(value, positive=False):
    if (
        type(value) not in (int, float)
        or not isfinite(value)
        or value < 0
        or (positive and value == 0)
    ):
        raise ValueError("finite nonnegative number required")


@dataclass(frozen=True)
class Node:
    node_id: str
    x_km: float
    y_km: float

    def __post_init__(self):
        identifier(self.node_id)
        finite(self.x_km)
        finite(self.y_km)


@dataclass(frozen=True)
class Road:
    first: str
    second: str
    speed_kph: int
    capacity: int = 10

    def __post_init__(self):
        identifier(self.first)
        identifier(self.second)
        if self.first == self.second or self.speed_kph not in (30, 50, 70):
            raise ValueError("invalid road endpoints/speed")
        natural(self.capacity, "capacity", True)


class Network:
    def __init__(self, nodes, roads, congestion_alpha=0.15):
        finite(congestion_alpha)
        self.alpha = congestion_alpha
        self.nodes = {}
        for node in nodes:
            if not isinstance(node, Node) or node.node_id in self.nodes:
                raise ValueError("invalid/duplicate node")
            self.nodes[node.node_id] = node
        if len(self.nodes) < 2:
            raise ValueError("at least two nodes required")
        self.roads = {}
        self.conditions = {}
        self.adjacency = {n: [] for n in self.nodes}
        for road in roads:
            if not isinstance(road, Road):
                raise ValueError("Road required")
            key = self.key(road.first, road.second)
            if (
                key in self.roads
                or any(n not in self.nodes for n in key)
                or self.distance(*key) == 0
            ):
                raise ValueError("duplicate, unknown or zero-length road")
            self.roads[key] = road
            self.conditions[key] = {"traffic": 1.0, "weather": 1.0, "closed": False}
            for a, b in (key, tuple(reversed(key))):
                self.adjacency[a].append(b)
        self.validate()

    @staticmethod
    def key(a, b):
        return tuple(sorted((a, b)))

    def distance(self, a, b):
        a, b = self.nodes[a], self.nodes[b]
        return hypot(a.x_km - b.x_km, a.y_km - b.y_km)

    def validate(self, alternatives=False):
        removals = [None] + (list(self.roads) if alternatives else [])
        for removed in removals:
            found = set()
            todo = [next(iter(self.nodes))]
            while todo:
                a = todo.pop()
                if a in found:
                    continue
                found.add(a)
                todo.extend(
                    b
                    for b in self.adjacency[a]
                    if self.key(a, b) != removed and b not in found
                )
            if len(found) != len(self.nodes):
                raise ValueError(
                    "network disconnected or lacks edge-disjoint alternatives"
                )

    def set_condition(self, a, b, *, traffic=None, weather=None, closed=None):
        key = self.key(a, b)
        if key not in self.roads:
            raise ValueError("unknown road")
        previous = self.conditions[key]
        traffic = previous["traffic"] if traffic is None else traffic
        weather = previous["weather"] if weather is None else weather
        closed = previous["closed"] if closed is None else closed
        if type(closed) is not bool:
            raise ValueError("invalid closure")
        finite(traffic, True)
        finite(weather, True)
        self.conditions[key] = dict(traffic=traffic, weather=weather, closed=closed)

    def seconds(self, a, b, occupancy=None):
        key = self.key(a, b)
        condition = self.conditions[key]
        if condition["closed"]:
            raise NoRoute("road closed")
        road = self.roads[key]
        count = (occupancy or {}).get(key, 0)
        natural(count, "occupancy")
        congestion = 1 + self.alpha * (count / road.capacity) ** 4
        return max(
            1,
            ceil(
                self.distance(a, b)
                / road.speed_kph
                * 3600
                * condition["traffic"]
                * condition["weather"]
                * congestion
            ),
        )

    def route(self, origin, destination, occupancy=None):
        if origin not in self.nodes or destination not in self.nodes:
            raise ValueError("unknown node")
        heap = [(0, (origin,))]
        visited = set()
        while heap:
            cost, path = heappop(heap)
            node = path[-1]
            if node in visited:
                continue
            visited.add(node)
            if node == destination:
                return path, cost
            for neighbor in sorted(self.adjacency[node]):
                if neighbor in visited:
                    continue
                try:
                    duration = self.seconds(node, neighbor, occupancy)
                except NoRoute:
                    continue
                heappush(heap, (cost + duration, path + (neighbor,)))
        raise NoRoute("no accessible route")

    def path_seconds(self, path, occupancy=None):
        return sum(self.seconds(a, b, occupancy) for a, b in zip(path, path[1:]))


def reference_network(seed=0):
    """25 nodes, 40 undirected edges; ring guarantees edge-disjoint alternatives."""
    natural(seed, "seed")
    rng = Random(seed)
    ids = ["central-a", "central-b", "local-a", "local-b", "local-c"]
    ids += [f"junction-{i:02d}" for i in range(20)]
    nodes = [Node(n, rng.uniform(0, 100), rng.uniform(0, 100)) for n in ids]
    pairs = {Network.key(ids[i], ids[(i + 1) % len(ids)]) for i in range(len(ids))}
    remaining = [
        (a, b)
        for i, a in enumerate(ids)
        for b in ids[i + 1 :]
        if Network.key(a, b) not in pairs
    ]
    rng.shuffle(remaining)
    pairs.update(Network.key(a, b) for a, b in remaining[:15])
    network = Network(
        nodes, [Road(a, b, rng.choice((30, 50, 70))) for a, b in sorted(pairs)]
    )
    network.validate(alternatives=True)
    return network
