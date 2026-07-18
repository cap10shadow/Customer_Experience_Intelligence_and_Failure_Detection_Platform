import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path to allow running this script from anywhere
root_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.services.ingestion_service.app.models.complaint import Complaint
from backend.services.ingestion_service.app.repositories.complaint_repository import ComplaintRepository
from backend.services.ingestion_service.app.schemas.complaint import ComplaintCreateRequest
from backend.services.ingestion_service.app.utils.hash_helper import generate_complaint_hash
from backend.shared.constants.enums.complaint import ComplaintStatus
from backend.shared.constants.enums.enrichment import ProcessingStage
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

Operational Realism Philosophy:
The seed data explicitly avoids "Lorem Ipsum" or synthetic gibberish. It relies
on tangible, real-world customer experience failures (delivery issues, broken
cancellation buttons, support frustration) spread across multiple regions, 
channels, and business segments.

Future Analytics Usage:
By inserting these structured records into the primary operational datastore, 
subsequent NLP enrichment, temporal aggregation, and anomaly detection workflows
can be executed locally against a stable, reproducible dataset.
"""


async def load_seed_data(file_path: Path):
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
    logger.info(f"Total processed: {len(raw_data)}")
    logger.info(f"Successfully inserted: {inserted_count}")
    logger.info(f"Skipped (duplicates): {duplicate_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("=========================")


async def main():
    seed_file_path = root_dir / "datasets" / "sample_complaints" / "operational_seed.json"
    await load_seed_data(seed_file_path)


if __name__ == "__main__":
    # Ensure asyncio event loop handles windows environments correctly if needed
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
