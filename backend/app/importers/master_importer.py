"""Importer for the 11 frozen master (reference data) tables.

Masters are small (5 – 150,000 rows), so beyond the shared streaming
lifecycle this importer adds an *up-front duplicate primary key scan* of
the whole file: for reference data it is better to know about key
collisions before a single row is written.
"""

from __future__ import annotations

import csv

from app.importers.base_importer import BaseImporter
from app.importers.report import ImportResult
from app.importers.validators import find_duplicate_pks


class MasterImporter(BaseImporter):
    """CSV importer for one master table."""

    batch_size = 5_000

    def run(self, session_factory, reset: bool = False) -> ImportResult:
        result = super().run(session_factory, reset=reset)

        # Surface duplicate-PK rejects prominently for reference data: a
        # master with colliding keys is a dataset defect, not noise.
        if result.status == "PASS" and result.rejected:
            with self.csv_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            pk_cols = [c.name for c in self.table.primary_key.columns]
            dupes = find_duplicate_pks(rows, pk_cols)
            if dupes:
                sample = ", ".join(str(d) for d in dupes[:5])
                result.messages.append(
                    f"duplicate keys found in source CSV: {len(dupes)} "
                    f"(e.g. {sample})"
                )
        return result
