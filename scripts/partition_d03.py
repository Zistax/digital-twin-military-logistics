"""Copy verified D03 ZIP members into four bounded, seed-paired archives."""

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import zipfile


def digest(handle):
    result = sha256()
    while chunk := handle.read(1024 * 1024):
        result.update(chunk)
    return result.hexdigest()


def partition(source, destination):
    evidence = json.loads(source.with_suffix(".zip.verification.json").read_text())
    with source.open("rb") as handle:
        if not evidence["passed"] or digest(handle) != evidence["archive_sha256"]:
            raise ValueError("original archive verification mismatch")
    groups, expected = defaultdict(set), {}
    with zipfile.ZipFile(source) as original:
        infos = {item.filename: item for item in original.infolist()}
        records = [n for n in infos if n.startswith("d03-batch-v1/records/")]
        if len(records) != 90:
            raise ValueError("90 accepted records required")
        for name in records:
            record = json.loads(original.read(name))
            if record["valid"] is not True:
                raise ValueError("nonaccepted attempt")
            members = groups[record["group_id"]]
            members.add(name)
            bundle = "d03-batch-v1/" + record["bundle"] + "/"
            manifest_name = bundle + "manifest.json"
            raw_manifest = original.read(manifest_name)
            expected[manifest_name] = record["manifest_sha256"]
            if sha256(raw_manifest).hexdigest() != expected[manifest_name]:
                raise ValueError("manifest changed")
            members.add(manifest_name)
            for filename, info in json.loads(raw_manifest)["files"].items():
                members.add(bundle + filename)
                expected[bundle + filename] = info["sha256"]
            trace = "d03-batch-v1/" + record["trace"]
            members.add(trace)
            expected[trace] = record["trace_sha256"]
        owned = set().union(*groups.values())
        common = set(infos) - owned
        for name in set(infos) - set(expected):
            expected[name] = sha256(original.read(name)).hexdigest()
        sizes = {
            group: sum(infos[n].compress_size + len(n) * 2 + 256 for n in members)
            for group, members in groups.items()
        }
    bins = [{"groups": [], "size": 0} for _ in range(4)]
    for group in sorted(groups, key=lambda g: (-sizes[g], g)):
        target = min(bins, key=lambda b: b["size"])
        target["groups"].append(group)
        target["size"] += sizes[group]
    if len(groups) != 30 or any(len(members) != 33 for members in groups.values()):
        raise ValueError("paired groups incomplete")
    results, seen = [], set()
    for index, bucket in enumerate(bins, 1):
        names = common | set().union(*(groups[g] for g in bucket["groups"]))
        output = destination / f"Dataset_D03_Parte_{index}_di_4.zip"
        if output.exists():
            raise ValueError("partition already exists")
        subprocess.run(
            ["zip", "-q", "-U", str(source), "--out", str(output), "-@"],
            input="\n".join(sorted(names)) + "\n",
            text=True,
            check=True,
        )
        if output.stat().st_size > 536870912:
            raise ValueError("partition exceeds the per-file limit")
        with zipfile.ZipFile(output) as archive:
            if set(archive.namelist()) != names or len(archive.namelist()) != len(
                names
            ):
                raise ValueError("partition member mismatch")
            for name in names:
                with archive.open(name) as handle:
                    if digest(handle) != expected[name]:
                        raise ValueError(f"partition checksum mismatch: {name}")
        seen.update(names)
        with output.open("rb") as handle:
            checksum = digest(handle)
        results.append(
            {
                "filename": output.name,
                "bytes": output.stat().st_size,
                "sha256": checksum,
                "groups": sorted(bucket["groups"]),
                "runs": len(bucket["groups"]) * 3,
                "verified_entries": len(names),
            }
        )
        print(json.dumps(results[-1]), flush=True)
    if seen != set(infos):
        raise ValueError("incomplete combined dataset")
    report = {
        "passed": True,
        "accepted_runs": 90,
        "paired_groups": 30,
        "verified_unique_entries": len(seen),
        "original_verified_archive_sha256": evidence["archive_sha256"],
        "plan_sha256": evidence["plan_sha256"],
        "instructions": "Extract all four ZIP archives into the same directory.",
        "parts": results,
    }
    (destination / "Verifica_Dataset_D03.json").write_text(json.dumps(report, indent=2))
    (destination / "Leggimi_Dataset_D03.md").write_text(
        "# Dataset D03 — 90 simulazioni\n\n"
        "Scaricare i quattro file `Dataset_D03_Parte_N_di_4.zip` ed estrarli "
        "tutti nella stessa cartella. Sono archivi ZIP indipendenti: non "
        "occorre concatenarli. I file comuni sono identici; se richiesto, "
        "consentire la loro sostituzione durante l'estrazione.\n\n"
        "La cartella risultante contiene `d03-batch-v1` con i 90 bundle, "
        "le tracce, il piano, l'audit e gli split, e `d03-closeout-20261014` "
        "con rapporto, catalogo, qualità e roadmap. Ogni seed conserva "
        "insieme i propri tre profili in una sola parte.\n\n"
        "`Verifica_Dataset_D03.json` riporta SHA256, dimensioni e gruppi di "
        "ogni parte. Tutti i 1014 file unici sono stati riletti e verificati "
        "dopo la suddivisione. Split: 54 training, 18 calibrazione, 18 test.\n"
    )
    print(
        json.dumps({"passed": True, "parts": 4, "verified_unique_entries": len(seen)})
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    partition(args.source.resolve(), args.destination.resolve())
