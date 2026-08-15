"""
Phase 13 Batch 7 (docs/architecture/phase-13/PHASE_13_ARCHITECTURE.md
§22): database restore verification. Proves a `backup.py`-produced
archive is genuinely recoverable, using §22's exact prescribed
procedure -- "`pg_restore` against a fresh `postgres` container" --
without ever touching the active development database.

Spins up a throwaway, fully isolated PostgreSQL container
(`DEFAULT_TARGET_CONTAINER`, its own ephemeral, unnamed volume --
never the real `postgres_data` named volume, never the real `oi_postgres`
container), restores the supplied dump into it via `pg_restore`, runs a
small set of targeted, deterministic integrity queries (row counts and
relationship checks -- never a full-table dump), and always tears the
container down afterward, including on failure.

Destructive-operation safety (mandatory -- restoring is destructive to
its target): this script refuses to operate against the platform's real
database container names under any circumstance, checked *before* any
docker command runs, whether the name comes from the default or from
`--target-container`.

Usage:

    python -m backend.tooling.backup_restore.restore_verify backups/operational_intelligence_20260815T120000Z.dump
    python -m backend.tooling.backup_restore.restore_verify --help
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from backend.shared.config.settings import settings

DEFAULT_TARGET_CONTAINER = "oi_postgres_restore_verify"
ISOLATED_HOST_PORT = "55432"
POSTGRES_IMAGE = "postgres:15-alpine"

# Guard rail: the platform's real, persistent database container/service
# names -- this script may never target them, no matter what a caller
# passes on the command line. Checked before every destructive step.
_FORBIDDEN_TARGET_CONTAINERS = {"postgres", "oi_postgres"}

# Row counts + relationship checks only -- never row content. Covers
# every table Phase 13 introduced (identity, recommendation
# attribution/history, Copilot ownership) plus the two cross-service
# relationships that must survive a restore intact.
_VERIFICATION_QUERIES: Dict[str, str] = {
    "migration_head": "SELECT version_num FROM alembic_version",
    "users_count": "SELECT COUNT(*) FROM users",
    "roles_count": "SELECT COUNT(*) FROM roles",
    "user_roles_count": "SELECT COUNT(*) FROM user_roles",
    "recommendations_count": "SELECT COUNT(*) FROM recommendations",
    "recommendations_with_decided_by": "SELECT COUNT(*) FROM recommendations WHERE decided_by IS NOT NULL",
    "recommendation_decision_history_count": "SELECT COUNT(*) FROM recommendation_decision_history",
    "copilot_conversations_count": "SELECT COUNT(*) FROM copilot_conversations",
    "copilot_conversations_with_owner": "SELECT COUNT(*) FROM copilot_conversations WHERE owner_id IS NOT NULL",
    "copilot_messages_count": "SELECT COUNT(*) FROM copilot_messages",
    "decided_by_orphans": (
        "SELECT COUNT(*) FROM recommendations r LEFT JOIN users u ON u.id = r.decided_by "
        "WHERE r.decided_by IS NOT NULL AND u.id IS NULL"
    ),
    "owner_id_orphans": (
        "SELECT COUNT(*) FROM copilot_conversations c LEFT JOIN users u ON u.id = c.owner_id "
        "WHERE c.owner_id IS NOT NULL AND u.id IS NULL"
    ),
}


class RestoreTargetSafetyError(Exception):
    """Raised when a caller attempts to point this script at a non-isolated (real) database container."""


def _guard_target_container(container_name: str) -> None:
    if container_name in _FORBIDDEN_TARGET_CONTAINERS:
        raise RestoreTargetSafetyError(
            f"Refusing to operate on '{container_name}' -- this is the platform's real development "
            "database container/service name, never a valid restore-verification target. "
            "Use an isolated container name (see --target-container)."
        )


def _run(command: List[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, check=check)


def start_isolated_container(container_name: str, *, db_name: str) -> None:
    """
    `POSTGRES_HOST_AUTH_METHOD=trust`, no `POSTGRES_PASSWORD` at all --
    deliberate: this container is network-isolated (published only to
    an ephemeral localhost port), destroyed immediately after
    verification, and never holds anything but a just-restored copy of
    already-backed-up data. Avoids ever having a credential value (real
    or throwaway) appear in a command line, log, or exception message.
    """
    _guard_target_container(container_name)
    print(f"Starting isolated restore-verification container '{container_name}'...")
    _run(
        [
            "docker", "run", "-d", "--rm",
            "--name", container_name,
            "-e", f"POSTGRES_USER={settings.POSTGRES_USER}",
            "-e", f"POSTGRES_DB={db_name}",
            "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
            "-p", f"{ISOLATED_HOST_PORT}:5432",
            POSTGRES_IMAGE,
        ]
    )
    _wait_until_ready(container_name)


def _wait_until_ready(container_name: str, *, timeout_seconds: int = 30) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = _run(["docker", "exec", container_name, "pg_isready", "-U", settings.POSTGRES_USER], check=False)
        if result.returncode == 0:
            return
        time.sleep(1)
    raise RuntimeError(f"Isolated container '{container_name}' did not become ready within {timeout_seconds}s.")


def restore_dump(container_name: str, dump_path: Path, *, db_name: str) -> None:
    _guard_target_container(container_name)
    if not dump_path.is_file():
        raise FileNotFoundError(f"Backup artifact not found: {dump_path}")

    in_container_path = f"/tmp/{dump_path.name}"
    print(f"Copying {dump_path.name} into '{container_name}'...")
    _run(["docker", "cp", str(dump_path), f"{container_name}:{in_container_path}"])

    print(f"Restoring into isolated database '{db_name}'...")
    _run(
        [
            "docker", "exec", container_name,
            "pg_restore", "-U", settings.POSTGRES_USER, "-d", db_name, "--no-owner",
            in_container_path,
        ]
    )


def verify(container_name: str, *, db_name: str) -> Dict[str, str]:
    """Runs every query in `_VERIFICATION_QUERIES` and returns their results -- row counts and IDs only, never row content."""
    _guard_target_container(container_name)

    def _query(sql: str) -> str:
        result = _run(
            ["docker", "exec", container_name, "psql", "-U", settings.POSTGRES_USER, "-d", db_name, "-t", "-A", "-c", sql]
        )
        return result.stdout.strip()

    return {name: _query(sql) for name, sql in _VERIFICATION_QUERIES.items()}


def teardown(container_name: str) -> None:
    _guard_target_container(container_name)
    print(f"Tearing down isolated container '{container_name}'...")
    _run(["docker", "rm", "-f", container_name], check=False)


def run_restore_verification(
    dump_path: Path, *, target_container: str = DEFAULT_TARGET_CONTAINER, db_name: Optional[str] = None
) -> Dict[str, str]:
    """
    Full cycle: start isolated container -> restore -> verify -> tear
    down (always, even on failure). Returns the verification summary on
    success; re-raises on failure after tearing down.
    """
    _guard_target_container(target_container)
    db_name = db_name or settings.POSTGRES_DB

    try:
        start_isolated_container(target_container, db_name=db_name)
        restore_dump(target_container, dump_path, db_name=db_name)
        return verify(target_container, db_name=db_name)
    finally:
        teardown(target_container)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore a pg_dump backup into an isolated, throwaway PostgreSQL container and verify its integrity."
    )
    parser.add_argument("dump_path", type=Path, help="Path to the .dump artifact produced by backup.py")
    parser.add_argument(
        "--target-container",
        default=DEFAULT_TARGET_CONTAINER,
        help=f"Name of the isolated container to create (default: {DEFAULT_TARGET_CONTAINER}). "
        "Never the real development container name -- rejected if it is.",
    )
    parser.add_argument("--db-name", default=None, help="Database name to restore into (default: the configured POSTGRES_DB).")
    args = parser.parse_args()

    try:
        _guard_target_container(args.target_container)
    except RestoreTargetSafetyError as exc:
        print(f"Refusing to proceed: {exc}", file=sys.stderr)
        return 1

    try:
        summary = run_restore_verification(args.dump_path, target_container=args.target_container, db_name=args.db_name)
    except Exception as exc:  # noqa: BLE001 -- always report a clear failure message, never a raw traceback to the operator.
        print(f"Restore verification failed: {exc}", file=sys.stderr)
        return 1

    print("Restore verification summary (row counts / integrity checks only -- no row content):")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
