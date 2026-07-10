"""API schema package (Phase 9).

Pydantic v2 request and response models — the HTTP contract of the
platform, kept strictly separate from ORM models and service DTOs. Request
models validate/parse query and body input; response models document and
serialize the plain dictionaries the Service and Analytics layers return.
No ORM object is ever exposed.
"""
