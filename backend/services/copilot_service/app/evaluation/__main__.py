"""
Internal, developer-facing evaluation-harness entrypoint (Batch 6
implementation prompt §14: no Gateway route, no frontend surface). Run
from the repository root:

    python -m backend.services.copilot_service.app.evaluation [--out report.json]

Uses the same shared, already-configured database engine every other
`copilot_service` code path uses (`backend/shared/database/database.py`)
-- respects whatever `POSTGRES_HOST` this process's real environment
actually has (e.g. `postgres` when run inside a container via `docker
exec oi_copilot python -m ...`, or `POSTGRES_HOST=localhost` when run
from the host, matching every other host-run script/test in this
repository), rather than hardcoding either one. Exits with a clear
message, not a raw traceback, if the database is unreachable.
"""

import argparse
import asyncio
import json
import sys

import httpx
from sqlalchemy import text

from backend.services.copilot_service.app.evaluation.dataset import DatasetValidationError, load_dataset
from backend.services.copilot_service.app.evaluation.runner import (
    EVALUATION_ACTOR_EMAIL,
    EVALUATION_ACTOR_ID,
    run_evaluation,
)
from backend.shared.database.database import async_session_maker, engine


async def _ensure_evaluation_actor_exists(session) -> None:
    """
    Phase 13 Batch 6 (AD-4): `copilot_conversations.owner_id` now carries
    a real, cross-service FOREIGN KEY to `users.id` -- this harness's
    fixed synthetic actor (`runner.EVALUATION_ACTOR_ID`) must exist as a
    real row before `run_evaluation` can persist any conversation.
    Idempotent (`ON CONFLICT DO NOTHING`): safe to run on every
    invocation, never accumulates duplicate rows. Never a login-capable
    account -- `password_hash` is a value that can never validate, and
    this row is never used by the real authentication flow (AD-1).
    """
    await session.execute(
        text(
            "INSERT INTO users (id, email, password_hash, is_active) "
            "VALUES (:id, :email, :password_hash, TRUE) ON CONFLICT (id) DO NOTHING"
        ),
        {"id": str(EVALUATION_ACTOR_ID), "email": EVALUATION_ACTOR_EMAIL, "password_hash": "not-a-real-account"},
    )
    await session.commit()


async def _main(out_path: str | None) -> int:
    try:
        dataset = load_dataset()
    except DatasetValidationError as exc:
        print(f"Evaluation dataset error: {exc}", file=sys.stderr)
        return 2

    try:
        async with async_session_maker() as session:
            await _ensure_evaluation_actor_exists(session)
            async with httpx.AsyncClient(timeout=10.0) as client:
                report = await run_evaluation(dataset, client=client, session=session)
            await session.commit()
    except Exception as exc:  # noqa: BLE001 -- surface a clear message, not a raw traceback, for a developer running this by hand.
        print(f"Evaluation run failed: {exc}", file=sys.stderr)
        print("Is PostgreSQL reachable? (docker compose up postgres)", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()

    print(f"Copilot evaluation: {report.passed_count}/{report.total} case(s) passed.")
    for case in report.cases:
        status = "PASS" if case.passed else "FAIL"
        print(f"  [{status}] {case.case_id} ({case.category}) -- provider={case.provider_used}")
        if case.error:
            print(f"      error: {case.error}")
        for dim in case.dimension_results:
            print(f"      {dim.dimension.value}: {dim.status.value} -- {dim.detail}")

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(report.to_dict(), handle, indent=2)
        print(f"Report written to {out_path}")

    return 0 if report.failed_count == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Copilot evaluation harness.")
    parser.add_argument("--out", default=None, help="Optional path to write the JSON report to.")
    args = parser.parse_args()
    sys.exit(asyncio.run(_main(args.out)))
