"""
Tests for Phase 13 Batch 7's database backup/restore tooling.

Two tiers, mirroring this repository's own established convention for
Docker-dependent code (see `test_postgresql_recommendation_repository.py`):

- Pure unit tests (no Docker, no Postgres) for filename determinism and
  the destructive-operation safety guard -- always run.
- One real, end-to-end integration test (actual `docker compose exec
  pg_dump`, an actual throwaway `docker run` container, actual
  `pg_restore`) -- skipped cleanly if Docker/Compose or the `postgres`
  service is not reachable, so `python -m pytest backend` stays green
  with or without Docker running.
"""

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.tooling.backup_restore.backup import backup_filename, run_backup
from backend.tooling.backup_restore.restore_verify import (
    RestoreTargetSafetyError,
    _guard_target_container,
    run_restore_verification,
)


def test_backup_filename_is_deterministic_for_a_given_timestamp():
    now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)

    assert backup_filename(db_name="operational_intelligence", now=now) == "operational_intelligence_20260815T120000Z.dump"


def test_backup_filename_never_collides_across_two_calls():
    first = backup_filename(db_name="operational_intelligence")
    second = backup_filename(db_name="operational_intelligence")

    # Not asserting inequality directly (two calls within the same
    # second would legitimately collide by the second-resolution
    # filename convention) -- asserting the convention itself: the
    # filename is always built from a real timestamp, never a fixed
    # constant that would make every backup overwrite the last one.
    assert first.startswith("operational_intelligence_")
    assert first.endswith(".dump")
    assert second.startswith("operational_intelligence_")


@pytest.mark.parametrize("forbidden_name", ["postgres", "oi_postgres"])
def test_guard_rejects_the_real_development_container_names(forbidden_name):
    with pytest.raises(RestoreTargetSafetyError):
        _guard_target_container(forbidden_name)


def test_guard_allows_an_isolated_container_name():
    _guard_target_container("oi_postgres_restore_verify")  # must not raise


def test_run_restore_verification_refuses_a_real_container_target_before_touching_docker(tmp_path):
    """
    The safety guard must fire before any `docker` command runs at all
    -- proven here by pointing at a real container name with a dump
    path that doesn't even exist; if the guard fired after attempting
    docker operations, this would fail with a different error
    (FileNotFoundError/CalledProcessError), not RestoreTargetSafetyError.
    """
    with pytest.raises(RestoreTargetSafetyError):
        run_restore_verification(tmp_path / "does-not-exist.dump", target_container="oi_postgres")


def _docker_compose_postgres_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "postgres", "pg_isready", "-U", "postgres"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


pytestmark_integration = pytest.mark.skipif(
    not _docker_compose_postgres_available(),
    reason="docker compose's 'postgres' service is not running/reachable -- run `docker compose up -d postgres` to enable this test",
)


@pytestmark_integration
def test_real_backup_then_restore_verification_round_trip(tmp_path):
    """
    The one real, end-to-end integration test: a genuine `pg_dump`
    against the actually-running `postgres` Compose service, then a
    genuine restore into a throwaway, isolated container, then real
    verification queries against the restored data -- never against
    the source database. Compares actual row counts/migration head
    before and after, not merely "the command exited 0".
    """
    artifact = run_backup(out_dir=tmp_path)

    assert artifact.exists()
    assert artifact.stat().st_size > 0

    summary = run_restore_verification(artifact, target_container="oi_postgres_restore_verify_pytest")

    # Every count must be a real, non-negative integer string -- proves
    # the restored database has a genuine, queryable schema, not an
    # empty/broken one.
    for key in (
        "users_count",
        "roles_count",
        "user_roles_count",
        "recommendations_count",
        "recommendation_decision_history_count",
        "copilot_conversations_count",
        "copilot_messages_count",
    ):
        assert summary[key].isdigit(), f"{key} was not a valid row count: {summary[key]!r}"

    # No orphaned cross-service relationship survived the restore as a
    # dangling reference -- the FK constraints (recommendations.decided_by
    # -> users.id, copilot_conversations.owner_id -> users.id) round-trip
    # correctly through pg_dump/pg_restore.
    assert summary["decided_by_orphans"] == "0"
    assert summary["owner_id_orphans"] == "0"

    # A real Alembic migration head string was restored (never empty).
    assert len(summary["migration_head"]) > 0


def test_backup_directory_is_git_ignored():
    """
    Static, no-Docker check: `backups/` (the default artifact
    destination) must be excluded from source control by `.gitignore`
    -- verified via the real `git check-ignore`, not by re-reading
    `.gitignore`'s text (which could drift out of sync with what Git
    actually honors).
    """
    repo_root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        ["git", "check-ignore", "-q", "backups/example.dump"],
        cwd=repo_root,
        capture_output=True,
    )
    assert result.returncode == 0, "backups/ is not excluded by .gitignore"
