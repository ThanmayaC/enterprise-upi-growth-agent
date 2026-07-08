"""Streaming importer for the ~1,000,000-row transaction fact CSV.

Differences from the master importer are purely scale-driven:

    - the file is never materialized in memory — rows stream through
      ``csv.DictReader`` straight into transform → batch → INSERT;
    - duplicate ``txnid`` detection happens incrementally against a set of
      seen keys (compact: one short string per row) instead of an up-front
      full-file scan;
    - a larger batch size amortizes commit overhead across the load.

Everything else — validation, transformation, per-batch commit/rollback,
reject capture, progress — is inherited from :class:`BaseImporter`.
"""

from __future__ import annotations

from app.importers.base_importer import BaseImporter


class TransactionImporter(BaseImporter):
    """CSV importer for the ``fact_upi_transactions`` table."""

    batch_size = 10_000
