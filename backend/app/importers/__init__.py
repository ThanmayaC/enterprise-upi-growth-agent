"""Enterprise CSV Import Engine.

Modular, reusable importers that load the frozen master CSVs and the
transaction fact CSV into PostgreSQL through the SQLAlchemy ORM layer.

Package layout:
    - ``base_importer``        — template-method base class (validate →
                                 transform → batch-load → result)
    - ``master_importer``      — importer for the 11 master tables
    - ``transaction_importer`` — streaming importer for the ~1M-row fact CSV
    - ``validators``           — file/header/duplicate-PK validation
    - ``transformers``         — type-safe CSV-string → Python conversions
    - ``loader``               — orchestrator (ordered run + verification)
    - ``progress``             — console progress bars
    - ``report``               — import result model + report rendering
"""
