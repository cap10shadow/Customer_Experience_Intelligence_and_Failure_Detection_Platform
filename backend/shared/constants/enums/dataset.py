from backend.shared.constants.enums.base import BaseStringEnum


class DatasetVersionStatus(BaseStringEnum):
    """
    Represents the processing lifecycle of one DatasetVersion, from the
    moment new records start arriving through analysis completion.

    DRAFT: a version has been opened (or is implicit -- the very first
    ingest into a brand-new dataset) and complaints are being added, but
    finalize() has not been called yet -- nothing has been analyzed.
    INGESTING: finalize() has been called and the orchestrator is
    recording the version's snapshot metadata (record counts).
    PROCESSING: NLP enrichment is running for the version's newly-added
    complaints.
    ANALYZING: anomaly detection, incident correlation, root cause, and
    business impact (which in turn fans out to recommendation/evaluation)
    are running.
    READY: analysis completed successfully -- this version's intelligence
    is safe to present as current.
    FAILED: a pipeline stage raised and the version's intelligence is
    incomplete/untrustworthy -- never presented as if it were READY.
    PARTIALLY_COMPLETED: some pipeline stages succeeded and at least one
    failed (e.g. some complaints failed enrichment) -- distinct from
    FAILED so a partial-but-real result is never conflated with "nothing
    happened," and distinct from READY so it is never presented as a
    clean success either.
    """

    DRAFT = "draft"
    INGESTING = "ingesting"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    READY = "ready"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
