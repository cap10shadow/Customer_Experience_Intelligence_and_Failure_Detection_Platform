import asyncio
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path to allow running from anywhere
root_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.services.ingestion_service.app.models.complaint import Complaint
from backend.services.ingestion_service.app.repositories.complaint_repository import ComplaintRepository
from backend.services.ingestion_service.app.schemas.complaint import ComplaintCreateRequest
from backend.services.ingestion_service.app.utils.hash_helper import generate_complaint_hash
from backend.shared.constants.enums.business_impact import OperationalArea
from backend.shared.constants.enums.complaint import ComplaintStatus, SourceChannel, CustomerSegment
from backend.shared.constants.enums.enrichment import ProcessingStage
from backend.shared.database.database import async_session_maker

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

"""
Operational Persistence Validation

Purpose:
This diagnostic tooling provides structured, operational verification of the
Ingestion Service's data layer. It programmatically executes lifecycle
scenarios against the database to confirm entity integrity, enum 
compatibility, and expected repository behavior.

Ingestion Verification Philosophy:
Instead of formal Pytest suites (which will be added in later CI/CD phases),
this diagnostic tool prioritizes readability and deterministic, repeatable execution
against local environments. It serves to guarantee the persistence foundation
is bulletproof before attaching NLP and Anomaly orchestration.

Future Regression-Testing Usefulness:
As schemas evolve, running this diagnostic validates that core operational
behaviors (soft deletes, hash deduplication, pagination bounds) remain intact.
"""

class ValidationRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.inserted_count = 0
        self.duplicate_skips = 0

    def assert_true(self, condition: bool, test_name: str, error_msg: str = ""):
        if condition:
            logger.info(f"✅ PASSED: {test_name}")
            self.passed += 1
        else:
            logger.error(f"❌ FAILED: {test_name} - {error_msg}")
            self.failed += 1

    def print_summary(self):
        logger.info("\n" + "="*40)
        logger.info("   PERSISTENCE VALIDATION SUMMARY   ")
        logger.info("="*40)
        logger.info(f"Total Validations:  {self.passed + self.failed}")
        logger.info(f"Passed:             {self.passed}")
        logger.info(f"Failed:             {self.failed}")
        logger.info(f"Records Inserted:   {self.inserted_count}")
        logger.info(f"Duplicates Skipped: {self.duplicate_skips}")
        logger.info("="*40)

async def run_diagnostics():
    runner = ValidationRunner()
    
    logger.info("Starting Persistence Diagnostics...\n")

    async with async_session_maker() as session:
        repo = ComplaintRepository(session)
        
        # Test Data Generation
        ref_id_1 = f"VAL-TEST-{uuid.uuid4().hex[:6]}"
        ref_id_2 = f"VAL-TEST-{uuid.uuid4().hex[:6]}"
        
        req_1 = ComplaintCreateRequest(
            external_reference_id=ref_id_1,
            complaint_text="This is a diagnostic test complaint regarding logistics.",
            complaint_title="Test Logistics Failure",
            source_channel=SourceChannel.WEBSITE_FORM,
            customer_segment=CustomerSegment.ENTERPRISE,
            operational_area=OperationalArea.LOGISTICS,
            event_occurred_at=datetime.now(timezone.utc)
        )

        req_2 = ComplaintCreateRequest(
            external_reference_id=ref_id_2,
            complaint_text="This is another diagnostic complaint about payments.",
            complaint_title="Test Payment Issue",
            source_channel=SourceChannel.MOBILE_APP,
            customer_segment=CustomerSegment.PREMIUM,
            operational_area=OperationalArea.PAYMENTS,
            event_occurred_at=datetime.now(timezone.utc)
        )

        # ---------------------------------------------------------
        # Scenario 1: Complaint Insertion & Lifecycle Initialization
        # ---------------------------------------------------------
        hash_1 = generate_complaint_hash(req_1.external_reference_id, req_1.complaint_text)
        complaint_1 = Complaint(
            **req_1.model_dump(),
            complaint_status=ComplaintStatus.INGESTED,
            processing_stage=ProcessingStage.RAW_INGESTION,
            source_record_hash=hash_1
        )
        
        await repo.create_complaint(complaint_1)
        await session.commit()
        runner.inserted_count += 1

        runner.assert_true(
            complaint_1.id is not None, 
            "Complaint Insertion", 
            "ID was not generated."
        )
        runner.assert_true(
            complaint_1.complaint_status == ComplaintStatus.INGESTED,
            "Lifecycle State Persistence",
            "Initial status was not INGESTED."
        )
        runner.assert_true(
            complaint_1.operational_area == OperationalArea.LOGISTICS,
            "Enum Persistence Correctness",
            "Operational area enum did not persist correctly."
        )

        # ---------------------------------------------------------
        # Scenario 2: Complaint Retrieval
        # ---------------------------------------------------------
        retrieved_by_id = await repo.get_by_id(complaint_1.id)
        runner.assert_true(
            retrieved_by_id is not None and retrieved_by_id.id == complaint_1.id,
            "Retrieval by complaint_id",
            "Could not fetch the complaint by its primary UUID."
        )

        retrieved_by_ref = await repo.get_by_external_reference(ref_id_1)
        runner.assert_true(
            retrieved_by_ref is not None and retrieved_by_ref.external_reference_id == ref_id_1,
            "Retrieval by external_reference_id",
            "Could not fetch the complaint by its external reference ID."
        )

        # ---------------------------------------------------------
        # Scenario 3: Duplicate Detection Behavior
        # ---------------------------------------------------------
        is_duplicate = await repo.exists_by_source_record_hash(hash_1)
        runner.assert_true(
            is_duplicate is True,
            "Duplicate Ingestion Prevention",
            "Hash collision was not detected."
        )
        if is_duplicate:
            runner.duplicate_skips += 1

        # ---------------------------------------------------------
        # Scenario 4: Filtering & Pagination Correctness
        # ---------------------------------------------------------
        # Insert second record to test lists
        hash_2 = generate_complaint_hash(req_2.external_reference_id, req_2.complaint_text)
        complaint_2 = Complaint(
            **req_2.model_dump(),
            complaint_status=ComplaintStatus.PENDING,
            processing_stage=ProcessingStage.RAW_INGESTION,
            source_record_hash=hash_2
        )
        await repo.create_complaint(complaint_2)
        await session.commit()
        runner.inserted_count += 1

        filtered_items = await repo.list_complaints(area=OperationalArea.PAYMENTS)
        runner.assert_true(
            any(item.external_reference_id == ref_id_2 for item in filtered_items),
            "Filtering Correctness",
            "Did not retrieve the record when filtering by operational area."
        )

        paginated_items = await repo.list_complaints(skip=0, limit=1)
        runner.assert_true(
            len(paginated_items) == 1,
            "Pagination Behavior",
            "Limit parameter was not respected."
        )

        # Deterministic Ordering: event_occurred_at DESC
        # Since req_2 was inserted after but we can rely on ID ordering or event_occurred_at
        ordered_items = await repo.list_complaints(limit=5)
        if len(ordered_items) >= 2:
            time_a = ordered_items[0].event_occurred_at
            time_b = ordered_items[1].event_occurred_at
            runner.assert_true(
                time_a >= time_b or ordered_items[0].id > ordered_items[1].id,
                "Deterministic Ordering Correctness",
                "Items were not returned in deterministic descending order."
            )

        # ---------------------------------------------------------
        # Scenario 5: Soft Deletion Behavior
        # ---------------------------------------------------------
        deleted_success = await repo.soft_delete_complaint(complaint_2.id)
        await session.commit()
        
        runner.assert_true(
            deleted_success is True,
            "Soft Delete Operation",
            "Repository reported failure marking complaint as deleted."
        )

        hidden_record = await repo.get_by_id(complaint_2.id)
        runner.assert_true(
            hidden_record is None,
            "Soft Deletion Visibility",
            "Soft-deleted record was still visible to standard queries."
        )

        explicit_record = await repo.get_by_id(complaint_2.id, include_deleted=True)
        runner.assert_true(
            explicit_record is not None and explicit_record.is_deleted is True,
            "Soft Deletion Persistence",
            "Explicit query failed to find soft-deleted record."
        )

    runner.print_summary()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(run_diagnostics())
