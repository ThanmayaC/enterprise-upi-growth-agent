"""Decision Intelligence layer — Analytics + ML + Business Rules → decisions.

Dependency direction (inward only, never violated):

    AI Copilot / APIs → [Decision Intelligence] → Rules
                                               → ML Intelligence
                                               → Analytics (via ML provider)

Phase-12 consumers (AI Copilot, Report Generator, Forecasting, Knowledge
Engine) use :class:`DecisionIntelligenceService` and receive fully
explainable :class:`DecisionResult` payloads — never raw ML predictions.
"""

from app.decision.decision_engine import DecisionEngine, DecisionLabels
from app.decision.decision_result import DecisionResult
from app.decision.decision_service import DecisionIntelligenceService

__all__ = [
    "DecisionEngine",
    "DecisionIntelligenceService",
    "DecisionLabels",
    "DecisionResult",
]
