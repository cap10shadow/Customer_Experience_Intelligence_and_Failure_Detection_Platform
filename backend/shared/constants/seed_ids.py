import uuid

"""
Fixed, deterministic UUIDs for the one "Legacy / Demo Data" Dataset every
pre-existing complaint (seed/demo data and anything ingested before the
Dataset/DatasetVersion model existed) was backfilled into by migration
`a1c3d5e7f902_add_datasets_and_dataset_versions`. Referenced identically
-- as a literal constant, never a lookup -- by that migration, by every
downstream service's own "add dataset_id" migration
(anomaly/root_cause/business_impact/recommendation), and by
`backend/tooling/seed_data/load_sample_complaints.py`'s default target,
so no cross-migration or cross-service coordination is ever needed to
agree on the value. See docs/DECISIONS.md AD-12.
"""

LEGACY_DATASET_ID = uuid.UUID("00000000-0000-0000-0000-0000000000d1")
LEGACY_DATASET_VERSION_ID = uuid.UUID("00000000-0000-0000-0000-0000000000d2")
