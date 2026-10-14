"""Canonical manifests for the actual configuration used by each run."""

from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import platform


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=lambda v: str(v) if isinstance(v, Decimal) else asdict(v),
    )


def run_manifest(w, config, policy):
    package = Path(__file__).parent
    from .journal import normalize

    manifest = {
        "manifest_version": 1,
        "simulation_id": w.simulation_id,
        "epoch_utc": w._epoch.isoformat(),
        "tick_s": w.tick_s,
        "python": platform.python_version(),
        "scenario": asdict(config),
        "runner": asdict(policy),
        "incident_policy": asdict(w._policy),
        "categories": w._categories,
        "catalog": [asdict(item) for _, item in sorted(w._items.items())],
        "stores": [asdict(store) for _, store in sorted(w._stores.items())],
        "operations": {d: asdict(op) for d, op in sorted(w._operations.items())},
        "vehicles": [asdict(v) for _, v in sorted(w._vehicles.items())],
        "network": {
            "nodes": [asdict(n) for _, n in sorted(w._network.nodes.items())],
            "roads": [asdict(r) for _, r in sorted(w._network.roads.items())],
            "congestion_alpha": w._network.alpha,
            "conditions": [
                {"first": edge[0], "second": edge[1], **condition}
                for edge, condition in sorted(w._network.conditions.items())
            ],
        },
        "initial_commands": normalize(w._audit),
        "metadata_usage": "configuration and replay only; excluded from model features",
        "initial_stock": w._stock,
        "reorder_rules": [
            {"depot": d, "item": i, **asdict(rule)}
            for (d, i), rule in sorted(w._rules.items())
        ],
        "source_sha256": {
            p.name: sha256(p.read_bytes()).hexdigest()
            for p in sorted(package.glob("*.py"))
        },
        "versions": {"creation": "creation-v1", "rolling": "rolling-v1", "bundle": 4},
    }
    normalized = json.loads(canonical(manifest))
    normalized["configuration_sha256"] = sha256(
        canonical(normalized).encode()
    ).hexdigest()
    return normalized


def validate_manifest(manifest, config):
    if manifest["manifest_version"] != 1 or manifest["scenario"] != config:
        raise ValueError("run manifest configuration mismatch")
    unsigned = {k: v for k, v in manifest.items() if k != "configuration_sha256"}
    if (
        sha256(canonical(unsigned).encode()).hexdigest()
        != manifest["configuration_sha256"]
    ):
        raise ValueError("run manifest checksum mismatch")
    if not manifest["catalog"] or not manifest["source_sha256"]:
        raise ValueError("incomplete run manifest")
    for name, digest in manifest["source_sha256"].items():
        if (
            not name.endswith(".py")
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ValueError("invalid source provenance checksum")
    if manifest["versions"] != {
        "creation": "creation-v1",
        "rolling": "rolling-v1",
        "bundle": 4,
    }:
        raise ValueError("unsupported provenance versions")
    from datetime import datetime, timedelta
    from .warehouse import Item, Store, Vehicle
    from .calendars import Calendar
    from .operations import DepotOperations
    from .roads import Node, Road, Network
    from .scenarios import ScenarioConfig
    from .experiments import RunPolicy
    from .incidents import IncidentPolicy
    from .core import natural, identifier

    ScenarioConfig(**manifest["scenario"])
    RunPolicy(**manifest["runner"])
    IncidentPolicy(**manifest["incident_policy"])
    identifier(manifest["simulation_id"])
    natural(manifest["tick_s"], "tick_s", True)
    if datetime.fromisoformat(manifest["epoch_utc"]).utcoffset() != timedelta(0):
        raise ValueError("manifest UTC epoch required")
    items = {}
    for row in manifest["catalog"]:
        item = Item(**{**row, "kg": Decimal(row["kg"]), "m3": Decimal(row["m3"])})
        if item.item_id in items:
            raise ValueError("duplicate catalog item")
        items[item.item_id] = item
    stores = {}
    for row in manifest["stores"]:
        store = Store(
            row["depot_id"], Decimal(row["ordinary_m3"]), Decimal(row["cold_m3"])
        )
        if store.depot_id in stores:
            raise ValueError("duplicate manifest depot")
        stores[store.depot_id] = store
    for row in manifest["vehicles"]:
        vehicle = Vehicle(
            **{
                **row,
                "max_kg": Decimal(row["max_kg"]),
                "max_m3": Decimal(row["max_m3"]),
            }
        )
        if vehicle.depot_id not in stores:
            raise ValueError("orphan manifest vehicle")
    if len({v["vehicle_id"] for v in manifest["vehicles"]}) != len(
        manifest["vehicles"]
    ):
        raise ValueError("duplicate manifest vehicle")
    if set(manifest["operations"]) != set(stores):
        raise ValueError("missing depot operation contract")
    for row in manifest["operations"].values():
        cal = row["calendar"]
        DepotOperations(
            Calendar(tuple(tuple(w) for w in cal["windows"]), cal["timezone_name"]),
            row["berths"],
            Decimal(row["quarantine_m3"]),
            Decimal(row["quarantine_cold_m3"]),
        )
    network = manifest["network"]
    graph = Network(
        [Node(**n) for n in network["nodes"]],
        [Road(**r) for r in network["roads"]],
        network["congestion_alpha"],
    )
    if not set(stores) <= set(graph.nodes):
        raise ValueError("depots absent from network")
    for row in network["conditions"]:
        graph.set_condition(
            row["first"],
            row["second"],
            traffic=row["traffic"],
            weather=row["weather"],
            closed=row["closed"],
        )
    from .supply import ReorderRule

    for rule in manifest["reorder_rules"]:
        if rule["depot"] not in stores or rule["item"] not in items:
            raise ValueError("orphan reorder rule")
        ReorderRule(
            Decimal(rule["daily_demand"]),
            Decimal(rule["trigger_days"]),
            Decimal(rule["target_days"]),
            rule["lead_s"],
        )
    for depot, stock in manifest["initial_stock"].items():
        if depot not in stores or not set(stock) <= set(items):
            raise ValueError("unknown initial depot or item")
        for q in stock.values():
            natural(q, "initial stock")
        for cold in (False, True):
            used = sum(
                items[i].m3 * q for i, q in stock.items() if items[i].cold == cold
            )
            capacity = stores[depot].cold_m3 if cold else stores[depot].ordinary_m3
            if used > capacity:
                raise ValueError("initial stock exceeds capacity")
