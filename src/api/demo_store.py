"""SQLite leases and command journals; no untrusted pickle deserialization."""

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
from threading import BoundedSemaphore
import time

from fastapi import HTTPException

from src.api.logistics import ROOT
from src.logistics.model_registry import safe_path


@dataclass(frozen=True)
class DemoPolicy:
    lifetime_s: int = 1800
    capacity: int = 8
    max_leases: int = 64
    max_commands: int = 24
    horizon_s: int = 3600
    step_s: int = 300
    max_manual_missions: int = 5
    worker_timeout_s: int = 20
    requests_per_minute: int = 60
    access_per_minute: int = 5
    global_per_minute: int = 180


def deny(status, reason):
    raise HTTPException(status, detail=reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def fingerprint(root):
    files = list((root / "src/logistics").glob("*.py"))
    files += [
        root / "src/api" / n
        for n in ("logistics.py", "model_compat.py", "demo_worker.py", "demo_store.py")
    ]
    files += list((root / "models").glob("*.joblib"))
    files += [root / "models/registry-v1.json"]
    files += [root / "requirements-local.txt"]
    registry = json.loads((root / "models/registry-v1.json").read_text())
    for entry in registry["versions"].values():
        references = [entry["artifact"], entry["evaluation"]]
        references += list(entry.get("references", {}).values())
        files += [safe_path(root, ref["path"]) for ref in references]
    digest = hashlib.sha256()
    for path in sorted(set(files)):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


class DemoStore:
    def __init__(self, path, secret, policy=None, root=ROOT, clock=time.time):
        if len(secret) < 32:
            raise ValueError("admin secret must contain at least 32 characters")
        self.path, self.secret = Path(path).resolve(), secret
        self.policy, self.root, self.clock = policy or DemoPolicy(), root, clock
        self.busy = BoundedSemaphore(1)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE IF NOT EXISTS leases (
                    token TEXT PRIMARY KEY, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    sid TEXT PRIMARY KEY, owner TEXT UNIQUE NOT NULL
                        REFERENCES leases(token) ON DELETE CASCADE,
                    config TEXT NOT NULL, view TEXT NOT NULL,
                    invalid INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS commands (
                    sid TEXT NOT NULL REFERENCES sessions(sid) ON DELETE CASCADE,
                    command_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                    signature TEXT NOT NULL, response TEXT NOT NULL,
                    PRIMARY KEY(sid, command_id), UNIQUE(sid, sequence));
                CREATE TABLE IF NOT EXISTS rates (
                    key TEXT PRIMARY KEY, minute INTEGER NOT NULL,
                    count INTEGER NOT NULL);
            """)
            revision = fingerprint(root)
            previous = db.execute(
                "SELECT value FROM metadata WHERE key='revision'"
            ).fetchone()
            self.purge(db)
            if previous and previous[0] != revision:
                if db.execute("SELECT count(*) FROM sessions").fetchone()[0]:
                    raise ValueError(
                        "release changed: expire/archive sessions before upgrade"
                    )
            db.execute(
                "INSERT OR REPLACE INTO metadata VALUES ('revision', ?)", (revision,)
            )

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=1)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA secure_delete=ON")
        db.execute("PRAGMA max_page_count=16384")
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except sqlite3.OperationalError:
            db.rollback()
            deny(503, "storage busy or unavailable")
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def digest(self, value):
        return hmac.new(
            self.secret.encode(), value.encode(), hashlib.sha256
        ).hexdigest()

    def purge(self, db):
        db.execute("DELETE FROM leases WHERE expires<=?", (self.clock(),))
        db.execute("DELETE FROM rates WHERE minute<?", (int(self.clock() // 60) - 1,))

    def throttle(self, client, issuing=False):
        exceeded = False
        minute = int(self.clock() // 60)
        with self.transaction() as db:
            self.purge(db)
            buckets = [
                ("global", self.policy.global_per_minute),
                (self.digest("ip:" + client), self.policy.requests_per_minute),
            ]
            if issuing:
                buckets.append(
                    (self.digest("access:" + client), self.policy.access_per_minute)
                )
            for key, limit in buckets:
                db.execute(
                    """INSERT INTO rates VALUES (?, ?, 1)
                    ON CONFLICT(key) DO UPDATE SET minute=excluded.minute,
                    count=CASE WHEN rates.minute=excluded.minute
                        THEN rates.count+1 ELSE 1 END""",
                    (key, minute),
                )
                if (
                    db.execute(
                        "SELECT count FROM rates WHERE key=?", (key,)
                    ).fetchone()[0]
                    > limit
                ):
                    exceeded = True
        if exceeded:
            deny(429, "request limit reached; retry next minute")

    def access(self):
        token = secrets.token_urlsafe(32)
        with self.transaction() as db:
            self.purge(db)
            if (
                db.execute("SELECT count(*) FROM leases").fetchone()[0]
                >= self.policy.max_leases
            ):
                deny(429, "visitor capacity reached")
            db.execute(
                "INSERT INTO leases VALUES (?, ?)",
                (self.digest(token), self.clock() + self.policy.lifetime_s),
            )
        return {"token": token, "expires_in_s": self.policy.lifetime_s}

    def revoke(self, token):
        with self.transaction() as db:
            owner = self.owner(db, token)
            db.execute("DELETE FROM leases WHERE token=?", (owner,))

    def owner(self, db, token):
        owner = self.digest(token)
        row = db.execute(
            "SELECT expires FROM leases WHERE token=?", (owner,)
        ).fetchone()
        if row is None or row[0] <= self.clock():
            deny(401, "visitor access expired or invalid")
        return owner

    def owned(self, db, owner, sid):
        row = db.execute(
            "SELECT * FROM sessions WHERE sid=? AND owner=?", (sid, owner)
        ).fetchone()
        if row is None:
            deny(404, "unknown session")
        return row

    def simulate(self, sid, config, journal):
        if not self.busy.acquire(blocking=False):
            deny(503, "simulation busy; retry later")
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "src.api.demo_worker"],
                cwd=self.root,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            try:
                output, _ = process.communicate(
                    canonical({"sid": sid, "config": config, "journal": journal}),
                    timeout=self.policy.worker_timeout_s,
                )
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                deny(503, "simulation time budget exceeded; state unchanged")
            if process.returncode:
                deny(503, "simulation worker failed; state unchanged")
            result = json.loads(output)
            if "status" in result:
                deny(result["status"], result["detail"])
            return result["view"]
        finally:
            self.busy.release()

    def create(self, token, body):
        with self.transaction() as db:
            self.purge(db)
            owner = self.owner(db, token)
            if db.execute(
                "SELECT sid FROM sessions WHERE owner=?", (owner,)
            ).fetchone():
                deny(409, "close the existing session first")
            if (
                db.execute("SELECT count(*) FROM sessions").fetchone()[0]
                >= self.policy.capacity
            ):
                deny(429, "demo session capacity reached")
            sid, config = secrets.token_hex(16), body.model_dump()
            view = json.loads(canonical(self.simulate(sid, config, [])))
            self.owner(db, token)
            db.execute(
                "INSERT INTO sessions(sid,owner,config,view) VALUES (?,?,?,?)",
                (sid, owner, canonical(config), canonical(view)),
            )
            return view

    def read(self, token, sid):
        with self.transaction() as db:
            row = self.owned(db, self.owner(db, token), sid)
            return json.loads(row["view"])

    def delete(self, token, sid):
        with self.transaction() as db:
            self.owned(db, self.owner(db, token), sid)
            db.execute("DELETE FROM sessions WHERE sid=?", (sid,))

    def command(self, token, sid, operation, body):
        item = {"operation": operation, "body": body.model_dump()}
        signature = canonical(item)
        with self.transaction() as db:
            row = self.owned(db, self.owner(db, token), sid)
            previous = db.execute(
                "SELECT * FROM commands WHERE sid=? AND command_id=?",
                (sid, body.command_id),
            ).fetchone()
            if previous:
                if previous["signature"] != signature:
                    deny(409, "conflicting retry")
                return json.loads(previous["response"])
            journal = [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT signature FROM commands WHERE sid=? ORDER BY sequence",
                    (sid,),
                )
            ]
            if len(journal) >= self.policy.max_commands:
                deny(429, "session command budget exhausted")
            view = json.loads(row["view"])
            if body.expected_revision != view["revision"]:
                deny(409, "stale view; refresh before sending")
            if operation == "advance" and not (
                view["observed_s"]
                < body.target_s
                <= min(view["observed_s"] + self.policy.step_s, self.policy.horizon_s)
            ):
                deny(422, "demo step/horizon exceeded")
            if operation == "mission":
                if (
                    sum(i["operation"] == "mission" for i in journal)
                    >= self.policy.max_manual_missions
                ):
                    deny(429, "manual mission budget exhausted")
                if len(body.quantities) > 3 or sum(body.quantities.values()) > 100:
                    deny(422, "demo maximum: 3 articles and 100 total units")
            journal.append(item)
            result = json.loads(
                canonical(self.simulate(sid, json.loads(row["config"]), journal))
            )
            response = canonical(result)
            self.owner(db, token)
            if len(response.encode()) > 512 * 1024:
                deny(503, "session response budget exceeded; state unchanged")
            db.execute(
                "INSERT INTO commands VALUES (?,?,?,?,?)",
                (sid, body.command_id, len(journal), signature, response),
            )
            db.execute("UPDATE sessions SET view=? WHERE sid=?", (response, sid))
            return result

    def maintenance(self):
        with self.transaction() as db:
            before = db.execute("SELECT count(*) FROM leases").fetchone()[0]
            self.purge(db)
            leases = db.execute("SELECT count(*) FROM leases").fetchone()[0]
            sessions = db.execute("SELECT count(*) FROM sessions").fetchone()[0]
            return {
                "leases": leases,
                "sessions": sessions,
                "expired_removed": before - leases,
            }
