"""API core package — cross-cutting API machinery (Phase 9).

Holds the composition root (dependency injection), the enterprise error
contract (exception handlers + error schema), and shared OpenAPI response
definitions. Nothing here contains business logic: it only wires the
existing Service and Analytics layers to HTTP.
"""

#: Mount prefix for the versioned API surface. Every router is included
#: under this prefix so authentication, throttling, or a future ``/api/v2``
#: can be layered on without touching individual routers.
API_V1_PREFIX = "/api/v1"

#: Semantic version of the REST contract (independent of the app build).
API_VERSION = "1.0.0"
