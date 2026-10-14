"""Physical cargo sources and split genealogy, replayed without creating goods."""

from .core import natural, identifier


def cargo_events(w):
    roots = {mid: w.manifest(mid) for mid in w._jobs}
    for split in reversed(w._splits):
        manifest = roots[split["mission_id"]]
        manifest.pop(split["child"], None)
        parent = split["parent"]
        manifest[parent] = manifest.get(parent, 0) + split["quantity"]
    events = []
    for mid, manifest in sorted(roots.items()):
        for key, quantity in sorted(manifest.items()):
            events.append(
                {
                    "schema_version": 1,
                    "simulation_id": w.simulation_id,
                    "mission_id": mid,
                    "kind": "load",
                    "at_s": w._loaded_at[key],
                    "cargo": list(key),
                    "quantity": quantity,
                }
            )
    for split in w._splits:
        events.append(
            {
                "schema_version": 1,
                "simulation_id": w.simulation_id,
                "mission_id": split["mission_id"],
                "kind": "split",
                "at_s": split["at_s"],
                "cargo": list(split["child"]),
                "parent": list(split["parent"]),
                "quantity": split["quantity"],
            }
        )
    return events


def validate_cargo_ledger(events, deliveries, creations, labels):
    timeline = []
    for index, row in enumerate(events):
        expected = {
            "schema_version",
            "simulation_id",
            "mission_id",
            "kind",
            "at_s",
            "cargo",
            "quantity",
        }
        if row.get("kind") == "split":
            expected.add("parent")
        if (
            set(row) != expected
            or row["kind"] not in ("load", "split")
            or type(row["schema_version"]) is not int
            or row["schema_version"] != 1
        ):
            raise ValueError("invalid cargo event contract")
        natural(row["at_s"], "cargo time")
        natural(row["quantity"], "cargo quantity", True)
        mid = (row["simulation_id"], row["mission_id"])
        if mid not in creations:
            raise ValueError("orphan cargo mission")
        if (
            not creations[mid]["observed_s"]
            <= row["at_s"]
            <= labels[mid]["label_cutoff_s"]
        ):
            raise ValueError("cargo event outside mission history")
        items = {line["item_id"] for line in creations[mid]["features"]["lines"]}
        for field in ("cargo", "parent") if row["kind"] == "split" else ("cargo",):
            key = row[field]
            if not isinstance(key, list) or len(key) != 3:
                raise ValueError("cargo key must contain trip, batch, item")
            for value in key:
                identifier(value)
            if key[2] not in items:
                raise ValueError("unknown cargo item")
        timeline.append((row["at_s"], 0 if row["kind"] == "load" else 1, index, row))
    for index, row in enumerate(deliveries):
        timeline.append((row["occurred_s"], 2, index, row))
    remaining, batches = {}, set()
    for _, kind, _, row in sorted(timeline, key=lambda entry: entry[:3]):
        mid = (row["simulation_id"], row["mission_id"])
        if kind == 2:
            key = (*mid, row["trip_id"], row["batch_id"], row["item_id"])
            quantity = row["accepted"] + row["unusable"]
            if key not in remaining or remaining[key] < quantity:
                raise ValueError("delivery exceeds available physical batch")
            remaining[key] -= quantity
            continue
        key = (*mid, *row["cargo"])
        batch = (row["simulation_id"], row["cargo"][1])
        if key in remaining or batch in batches:
            raise ValueError("duplicate physical cargo batch")
        quantity = row["quantity"]
        if kind == 1:
            parent = (*mid, *row["parent"])
            if (
                parent not in remaining
                or remaining[parent] < quantity
                or row["parent"][2] != row["cargo"][2]
            ):
                raise ValueError("split exceeds parent cargo or changes item")
            remaining[parent] -= quantity
        remaining[key] = quantity
        batches.add(batch)
    return remaining
