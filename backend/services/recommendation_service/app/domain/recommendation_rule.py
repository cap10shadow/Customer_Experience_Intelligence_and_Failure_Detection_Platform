from abc import ABC, abstractmethod
from typing import Tuple

from backend.services.recommendation_service.app.domain.intelligence_context import IntelligenceContext
from backend.services.recommendation_service.app.domain.recommendation import Recommendation


class RecommendationRule(ABC):
    """
    Base for a single, independent Recommendation Rule.

    Architectural Boundaries:
    - A rule consumes only the single `IntelligenceContext` snapshot it is
      given -- never persistence, never another service's API, never a
      different snapshot than every other rule in the same engine run.
    - A rule must never call or depend on another `RecommendationRule`
      (rules never call each other), and must never mutate the
      `IntelligenceContext` it receives (immutable by construction, since
      the context and every value object it holds are frozen dataclasses).
    - A rule returns zero or more `Recommendation`s -- most rules will
      return at most one, but the contract permits more, and returning
      none (an empty tuple) when the rule's condition does not hold is a
      normal, expected outcome, not an error.
    - Every rule computes its `Recommendation.score` via the shared
      Recommendation Scoring Policy (`scoring.compute_score`) -- never its
      own arithmetic -- which is what guarantees score consistency across
      the engine (see `scoring.py`).
    - The Recommendation Engine depends on this abstraction, never on
      concrete rule classes, so new rules can be added by registering
      another `RecommendationRule` without modifying the engine.
    """

    @abstractmethod
    def evaluate(self, context: IntelligenceContext) -> Tuple[Recommendation, ...]:
        """Evaluates this rule against `context` and returns zero or more Recommendations."""
        raise NotImplementedError
