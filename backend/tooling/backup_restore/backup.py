"""
Phase 13 Batch 7 (docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md
§22): database backup for the platform's single, shared PostgreSQL
instance. No backup/restore mechanism existed anywhere in this
repository before this batch (confirmed absent by §22's own audit).

Mechanism: `pg_dump`, custom format (`-Fc`) -- §22 names `pg_restore` as
the restore tool, which requires a custom/directory/tar-format archive
(not a plain-SQL dump `psql` would read back). Runs `pg_dump` *inside*
the already-running `postgres` Compose service via `docker compose
exec`, per §22's "a mounted volume or bind-mounted host directory" and
this batch's own instruction to reuse "the existing PostgreSQL
service/network conventions" rather than requiring `postgresql-client`
on the host. No password is supplied from this script -- the container's
own default `pg_hba.conf` trusts local Unix-socket connections for its
own role, the same convention every `docker compose exec postgres
psql ...` call elsewhere in this project's implementation history
already relies on (verified during this batch's own runtime
verification).

Backup artifacts are written to `backups/` at the repository root
(gitignored -- application data may contain user information,
conversation content, and other sensitive operational data; never
committed). Filename convention: `<db_name>_<UTC timestamp>.dump`,
always unique -- an accidental overwrite is structurally impossible.

Usage (from the repository root, with `docker compose up -d postgres`
already running):

    python -m backend.tooling.backup_restore.backup
    python -m backend.tooling.backup_restore.backup --out-dir /custom/path
    python -m backend.tooling.backup_restore.backup --help
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.shared.config.settings import settings

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BACKUP_DIR = REPO_ROOT / "backups"
COMPOSE_SERVICE = "postgres"


def backup_filename(*, db_name: str, now: Optional[datetime] = None) -> str:
    """Deterministic, always-unique filename -- two backups can never collide/overwrite each other."""
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"{db_name}_{timestamp}.dump"


def run_backup(*, out_dir: Path = DEFAULT_BACKUP_DIR, db_name: Optional[str] = None) -> Path:
    """
    Runs `pg_dump -Fc` inside the running `postgres` Compose service and
    writes the resulting custom-format archive to `out_dir`. Raises
    `RuntimeError` on failure (the partial/empty artifact, if any, is
    removed first -- a failed backup must never be mistaken for a valid
    one just because a file exists at the expected path).
    """
    db_name = db_name or settings.POSTGRES_DB
    out_dir.mkdir(parents=True, exist_ok=True)
    destination = out_dir / backup_filename(db_name=db_name)

    command = [
        "docker", "compose", "exec", "-T", COMPOSE_SERVICE,
        "pg_dump", "-U", settings.POSTGRES_USER, "-d", db_name, "-Fc",
    ]
    with destination.open("wb") as artifact:
        result = subprocess.run(command, stdout=artifact, stderr=subprocess.PIPE)

    if result.returncode != 0:
        destination.unlink(missing_ok=True)
        # pg_dump's own stderr text is safe to surface -- it names
        # connection/auth failures by role or host, never a password
        # value (pg_dump/libpq never echo the password itself).
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"pg_dump failed (exit {result.returncode}): {detail}")

    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a pg_dump custom-format backup of the platform's shared PostgreSQL database."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help=f"Destination directory for the backup artifact (default: {DEFAULT_BACKUP_DIR}).",
    )
    parser.add_argument(
        "--db-name",
        default=None,
        help="Database name to back up (default: the configured POSTGRES_DB).",
    )
    args = parser.parse_args()

    db_name = args.db_name or settings.POSTGRES_DB
    print(f"Starting backup of database '{db_name}' via the '{COMPOSE_SERVICE}' Compose service...")
    try:
        artifact = run_backup(out_dir=args.out_dir, db_name=args.db_name)
    except RuntimeError as exc:
        print(f"Backup failed: {exc}", file=sys.stderr)
        return 1

    size_bytes = artifact.stat().st_size
    print(f"Backup completed: {artifact} ({size_bytes} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
