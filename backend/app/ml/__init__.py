"""Enterprise ML Intelligence Platform (Phase 11).

A reusable backend layer that turns the Analytics engine's deterministic
outputs into predictive intelligence: merchant growth, customer behaviour,
transaction success, autopay opportunity, merchant/customer segmentation, and
anomaly detection.

Dependency direction (inward only) — never violated:

    REST API → ML Intelligence → Analytics → Services → Repositories → DB

The ML layer consumes **only** the Analytics and Service layers through a
single data provider; it never imports repositories, SQLAlchemy, or ORM
models, and it never issues SQL. Every prediction is explainable: it carries a
confidence score, the important features, the model + version used, and a
human-readable reason.
"""

__all__: list[str] = []
