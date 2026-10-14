"""Build the D03 descriptive closeout from the verified split manifest."""

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path


def read_json(path):
    return json.loads(path.read_text())


def verified_rows(path, expected):
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected["sha256"]:
        raise ValueError(f"changed table: {path}")
    rows = [json.loads(line) for line in raw.decode().splitlines()]
    if len(rows) != expected["rows"]:
        raise ValueError("table count mismatch")
    return rows


def build_report(root, destination):
    acceptance = read_json(root / "acceptance.json")
    if acceptance.get("passed") is not True or acceptance["verified_runs"] != 90:
        raise ValueError("D03 has not passed its final audit")
    plan = read_json(root / "plan.json")
    splits = read_json(root / "split_manifest.json")
    if splits["plan_sha256"] != plan["plan_sha256"]:
        raise ValueError("split plan mismatch")
    segments = {}
    catalogue = []
    simulation_ids, memberships = set(), {}
    for split, records in splits["sets"].items():
        for record in records:
            identity = record["simulation_id"]
            if identity in simulation_ids:
                raise ValueError("simulation repeated across sets")
            simulation_ids.add(identity)
            group = record["group_id"]
            if memberships.setdefault(group, split) != split:
                raise ValueError("paired seed leakage")
            path = root / record["bundle"]
            raw_manifest = (path / "manifest.json").read_bytes()
            if sha256(raw_manifest).hexdigest() != record["manifest_sha256"]:
                raise ValueError("bundle manifest changed")
            manifest = json.loads(raw_manifest)
            creations = verified_rows(
                path / "observations.jsonl", manifest["files"]["observations.jsonl"]
            )
            labels = {
                row["mission_id"]: row
                for row in verified_rows(
                    path / "labels.jsonl", manifest["files"]["labels.jsonl"]
                )
            }
            for observation in creations:
                features = observation["features"]
                cold = any(line["cold"] for line in features["lines"])
                key = (record["profile"], features["urgent"], cold)
                counter = segments.setdefault(key, Counter())
                label = labels[observation["mission_id"]]
                counter["missions"] += 1
                counter["quota_reached"] += label["status"] == "reached"
                counter["quota_censored"] += label["quota_censored"]
                counter["cancelled"] += label["status"] == "cancelled"
                counter["known_late"] += label["late"] is True
                counter["timing_unknown"] += label["late"] is None
            catalogue.append(
                {
                    **{
                        k: record[k]
                        for k in (
                            "simulation_id",
                            "group_id",
                            "seed",
                            "profile",
                            "split",
                            "bundle",
                            "manifest_sha256",
                            "wall_seconds",
                        )
                    },
                    **{
                        k: record["kpi"][k]
                        for k in (
                            "missions",
                            "quota_reached",
                            "quota_censored",
                            "cancelled",
                            "known_late",
                            "timing_unknown",
                        )
                    },
                    "rolling_samples": record["rows"]["rolling_observations.jsonl"],
                }
            )
    total = acceptance["distributions"]["all"]
    if (
        len(simulation_ids) != 90
        or len(memberships) != 30
        or sum(c["missions"] for c in segments.values()) != total["missions"]
    ):
        raise ValueError("descriptive report accounting mismatch")
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "Catalogo_Run_D03.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(catalogue[0]))
        writer.writeheader()
        writer.writerows(sorted(catalogue, key=lambda r: r["simulation_id"]))
    lines = [
        "# Chiusura D03 — lotto iniziale e split",
        "",
        "**D03 completato: 90 simulazioni verificate, 30 gruppi indivisibili.**",
        f"Il lotto contiene **{total['missions']} missioni** e "
        f"**{total['rolling_samples']} snapshot rolling**.",
        "Siamo alla dodicesima voce su 18; la prossima è M01. "
        "Nessun modello addestrato o selezionato in D03.",
        "",
        "| Insieme | Gruppi | Simulazioni | Per profilo | Missioni |",
        "|---|---:|---:|---:|---:|",
    ]
    for split, count in (("training", 18), ("calibration", 6), ("test", 6)):
        lines.append(
            f"| {split} | {count} | {count * 3} | {count} | "
            f"{acceptance['distributions'][split]['missions']} |"
        )
    lines += [
        "",
        "## Distribuzioni descrittive",
        "",
        "| Profilo | Missioni | Quote raggiunte | Censurate | Annullate | "
        "Puntuali | Ritardo noto | Classe ignota | Rolling |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for profile in ("regular", "pressure", "perturbed", "all"):
        values = acceptance["distributions"][profile]
        numbers = " | ".join(
            str(values[k])
            for k in (
                "missions",
                "quota_reached",
                "quota_censored",
                "cancelled",
                "on_time_reached",
                "known_late",
                "timing_unknown",
                "rolling_samples",
            )
        )
        lines.append(f"| {profile} | {numbers} |")
    lines += [
        "",
        "Le categorie censura e ritardo noto possono sovrapporsi: oltre la "
        "scadenza il ritardo è noto anche quando la durata finale rimane ignota.",
        "",
        "| Profilo | Urgente | Refrigerato | Missioni | Raggiunte | Censurate | "
        "Ritardo noto | Classe ignota |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for (profile, urgent, cold), values in sorted(segments.items()):
        numbers = " | ".join(
            str(values[k])
            for k in (
                "missions",
                "quota_reached",
                "quota_censored",
                "known_late",
                "timing_unknown",
            )
        )
        lines.append(
            f"| {profile} | {'Sì' if urgent else 'No'} | "
            f"{'Sì' if cold else 'No'} | {numbers} |"
        )
    lines += [
        "",
        "## Evidenza e limiti",
        "",
        "Ogni bundle nativo v4 è stato esportato e riletto semanticamente; "
        "tutti e 90 sono stati riletti anche nell'audit finale. Verificati "
        "checksum, relazioni, conservazione, cutoff, contesti e maschere "
        "training. Nessun gruppo o identificativo attraversa gli insiemi.",
        "",
        "Seed 1000–1029; esclusi i seed di sviluppo 0/1/2/3. Assegnazione "
        "congelata mediante hash prima del primo run. Generazione 7 giorni, "
        "estensione massima 7 giorni; nessuna sostituzione dei seed in "
        "funzione degli esiti.",
        "",
        "Volumi ed esiti sono emergenti, senza riequilibrio artificiale. "
        "Snapshot e missioni dello stesso gruppo non sono osservazioni "
        "indipendenti. Le durate censurate rimangono nulle; i soli completati "
        "non rappresentano l'intera popolazione.",
        "",
        "Il test è stato consultato soltanto per integrità e conteggi "
        "descrittivi. Non è stato usato per tuning, selezione di modelli, "
        "soglie o calibrazione. Nessuna misura di qualità predittiva è disponibile.",
        "",
        "[Piano congelato](../d03-batch-v1/plan.json) · "
        "[Manifest degli insiemi](../d03-batch-v1/split_manifest.json) · "
        "[Audit finale](../d03-batch-v1/acceptance.json) · "
        "[Catalogo dei run](Catalogo_Run_D03.csv) · "
        "[Qualità](Qualita_D03.json)",
        "",
        "[Protocollo](Protocollo_D03_v1.md) · "
        "[Esecuzione](Esecuzione_D03.md) · "
        "[Stato della roadmap](Stato_Roadmap.md)",
        "",
        "La verifica di qualità dell'esecutore ha superato 268 test e 16 "
        "sotto-test, con copertura del nucleo del 91,78%; Ruff e Black superati. "
        "La prova è in `reports/d03-quality-executor/quality.json` nel repository.",
        "",
        "Il limite di memoria ha richiesto una ripresa con rilascio dei "
        "risultati prima della rilettura; il simulatore congelato non è stato "
        "modificato. Un file troncato è stato ripristinato soltanto dopo aver "
        "riprodotto gli hash originali di tutte le otto tabelle e della traccia. "
        "I tentativi non accettati non entrano negli insiemi.",
        "",
        "Modifiche locali, senza pubblicazione o invio a GitHub.",
    ]
    (destination / "Chiusura_D03.md").write_text("\n".join(lines) + "\n")
    (destination / "segment_counts.json").write_text(
        json.dumps(
            [
                {"profile": p, "urgent": u, "cold": c, **dict(count)}
                for (p, u, c), count in sorted(segments.items())
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    build_report(args.batch, args.destination)
