from backend.shared.constants.enums.base import BaseStringEnum


class RecommendationDecision(BaseStringEnum):
    """
    The human decision recorded against a persisted Recommendation
    (Step 7.X G-01 -- minimal decision persistence).

    Operational Purpose:
    Answers only "what is the current decision state?" -- never who
    decided, why from a governance perspective, or what happened after.
    A `Recommendation`'s `decision` column is nullable and defaults to
    `NULL`, meaning "no decision has ever been recorded" -- a state this
    enum deliberately does not have a member for, so it can never be
    confused with `PENDING`, which is a real, explicitly-recorded human
    decision to leave a recommendation under review.

    Architectural Boundaries:
    - No decision-owner/actor, approval-authority, or workflow concept is
      modeled here or anywhere in this Batch -- see G-01's scope freeze.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
