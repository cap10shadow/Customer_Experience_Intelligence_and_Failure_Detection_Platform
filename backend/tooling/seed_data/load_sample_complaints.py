import argparse
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

# Add project root to sys.path to allow running this script from anywhere
root_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.services.ingestion_service.app.models.complaint import Complaint
from backend.services.ingestion_service.app.models.dataset import DatasetVersion
from backend.services.ingestion_service.app.repositories.complaint_repository import ComplaintRepository
from backend.services.ingestion_service.app.repositories.dataset_repository import DatasetRepository
from backend.services.ingestion_service.app.schemas.complaint import ComplaintCreateRequest
from backend.services.ingestion_service.app.utils.hash_helper import generate_complaint_hash
from backend.shared.constants.enums.complaint import ComplaintStatus
from backend.shared.constants.enums.dataset import DatasetVersionStatus
from backend.shared.constants.enums.enrichment import ProcessingStage
from backend.shared.constants.seed_ids import LEGACY_DATASET_ID
from backend.shared.database.database import async_session_maker

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

"""
Operational Validation Seed Loader

Dataset Purpose:
This script loads a baseline set of realistic operational complaints. It bypasses
the HTTP API layer for speed and repeatability, inserting directly through the
repository layer.

Dataset targeting (docs/DECISIONS.md AD-12): every complaint now belongs to a
real Dataset. By default this script targets the same fixed "Legacy / Demo
Data" dataset the AD-12 migration backfilled all pre-existing complaints
into (`LEGACY_DATASET_ID`), so repeated runs accumulate into one place
rather than each spawning a new dataset. Pass `--dataset-id` to seed a
different, already-existing dataset instead (e.g. one created via the
`POST /datasets` API for a specific test scenario). This script never
creates a Dataset itself -- only complaints within one -- and it targets
whatever DatasetVersion is currently open (DRAFT) for that dataset,
opening a fresh one first if the current version has already been
finalized (mirroring what `finalize_dataset_version`'s own "open the
next draft" behavior does at the API layer).

Operational Realism Philosophy:
The seed data explicitly avoids "Lorem Ipsum" or synthetic gibberish. It relies
on tangible, real-world customer experience failures (delivery issues, broken
cancellation buttons, support frustration) spread across multiple regions,
channels, and business segments.

Future Analytics Usage:
By inserting these structured records into the primary operational datastore,
subsequent NLP enrichment, temporal aggregation, and anomaly detection workflows
can be executed locally against a stable, reproducible dataset -- now scoped to
this dataset's own version history rather than the platform's entire corpus.
"""


async def load_seed_data(file_path: Path, dataset_id: uuid.UUID):
    if not file_path.exists():
        logger.error(f"Seed file not found: {file_path}")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read seed file: {e}")
        return

    inserted_count = 0
    duplicate_count = 0
    error_count = 0

    logger.info(f"Loaded {len(raw_data)} records from {file_path.name}")
    logger.info("Starting ingestion validation...")

    async with async_session_maker() as session:
        repo = ComplaintRepository(session)
        dataset_repo = DatasetRepository(session)

        dataset = await dataset_repo.get_dataset(dataset_id)
        if dataset is None:
            logger.error(f"Dataset {dataset_id} does not exist -- create it first (POST /datasets).")
            return

        draft = await dataset_repo.get_draft_version(dataset_id)
        if draft is None:
            latest = await dataset_repo.get_latest_version(dataset_id)
            next_version_number = (latest.version_number + 1) if latest else 1
            logger.info(
                f"Dataset {dataset_id} has no open draft version -- opening version {next_version_number}."
            )
            draft = await dataset_repo.create_dataset_version(
                DatasetVersion(
                    dataset_id=dataset_id, version_number=next_version_number, status=DatasetVersionStatus.DRAFT
                )
            )

        for item in raw_data:
            try:
                # 1. Validation via Pydantic
                payload = ComplaintCreateRequest(**item)

                # 2. Hash Deduplication
                record_hash = generate_complaint_hash(
                    payload.external_reference_id,
                    payload.complaint_text
                )

                if await repo.exists_by_source_record_hash(record_hash):
                    duplicate_count += 1
                    logger.debug(f"Skipping duplicate: {payload.external_reference_id}")
                    continue

                # 3. Entity Mapping (Operational defaults applied)
                new_complaint = Complaint(
                    **payload.model_dump(),
                    dataset_id=dataset_id,
                    dataset_version_id=draft.id,
                    complaint_status=ComplaintStatus.INGESTED,
                    processing_stage=ProcessingStage.RAW_INGESTION,
                    source_record_hash=record_hash,
                )

                # 4. Persistence
                await repo.create_complaint(new_complaint)
                inserted_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"Failed to ingest record {item.get('external_reference_id', 'UNKNOWN')}: {e}")

        # Commit all inserted records at once
        await session.commit()

    logger.info("=== Ingestion Summary ===")
    logger.info(f"Dataset: {dataset_id}")
    logger.info(f"Total processed: {len(raw_data)}")
    logger.info(f"Successfully inserted: {inserted_count}")
    logger.info(f"Skipped (duplicates): {duplicate_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("=========================")
    logger.info(
        "Note: this script only ingests records. Run the analysis pipeline "
        "(POST /api/v1/datasets/{id}/versions/finalize via the Gateway) to enrich, "
        "detect anomalies, correlate incidents, and generate recommendations for this data."
    )


def parse_arguments(argv=None) -> argparse.Namespace:
    """
    CLI surface for the seed loader.

    `--file` exists because the repository's `datasets/` directory is
    deliberately excluded from the backend container image
    (see `.dockerignore`) -- the default path only resolves when this
    script runs against a checkout. Inside a container the dataset is
    copied in first (`docker cp`), then pointed at explicitly.
    """
    parser = argparse.ArgumentParser(
        description="Load the operational validation seed complaints into the primary datastore.",
    )
    parser.add_argument(
        "--file",
        dest="file",
        default=None,
        help=(
            "Path to the seed JSON file. Defaults to "
            "datasets/sample_complaints/operational_seed.json relative to the repository root."
        ),
    )
    parser.add_argument(
        "--dataset-id",
        dest="dataset_id",
        default=None,
        help="UUID of an existing Dataset to seed into. Defaults to the fixed Legacy/Demo Data dataset.",
    )
    return parser.parse_args(argv)


async def main(argv=None):
    arguments = parse_arguments(argv)

    if arguments.file:
        seed_file_path = Path(arguments.file).expanduser()
    else:
        seed_file_path = root_dir / "datasets" / "sample_complaints" / "operational_seed.json"

    dataset_id = uuid.UUID(arguments.dataset_id) if arguments.dataset_id else LEGACY_DATASET_ID

    await load_seed_data(seed_file_path, dataset_id)


if __name__ == "__main__":
    # Ensure asyncio event loop handles windows environments correctly if needed
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
