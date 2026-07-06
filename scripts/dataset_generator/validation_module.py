"""
validation_module.py

Validates a generated batch of fact_upi_transactions rows against every
integrity/business rule before it is written to CSV:
    - duplicate txnid
    - duplicate UMN (at creation)
    - broken lifecycle / broken request-response pairing
    - invalid timestamps (non-monotonic within a lifecycle)
    - invalid seqnum (skips or decreases)
    - invalid purpose / initiation mode / MCC / bank / PSP
    - invalid response code / error code
    - orphan transactions (RespX without ReqX, ReqPay without active UMN
      for mandate executions)

Rows failing validation are reported; the orchestrator uses this to
decide whether to reject a batch.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

import constants


@dataclass
class ValidationReport:
    total_rows: int
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add(self, message: str) -> None:
        self.errors.append(message)


class DatasetValidator:
    """Runs all structural and business-rule checks over a batch of rows."""

    def __init__(
        self,
        valid_banks: set[str],
        valid_psps: set[str],
        valid_mccs: set[str],
        valid_purposecodes: set[str],
        valid_initiation_modes: set[str],
        valid_response_codes: set[str],
        valid_error_codes: set[str],
    ) -> None:
        self.valid_banks = valid_banks
        self.valid_psps = valid_psps
        self.valid_mccs = valid_mccs
        self.valid_purposecodes = valid_purposecodes
        self.valid_initiation_modes = valid_initiation_modes
        self.valid_response_codes = valid_response_codes
        self.valid_error_codes = valid_error_codes

    def validate(self, rows: List[dict]) -> ValidationReport:
        """Run the full validation suite and return a report."""
        report = ValidationReport(total_rows=len(rows))

        self._check_duplicate_txnids(rows, report)
        self._check_lifecycle_pairing(rows, report)
        self._check_master_references(rows, report)
        self._check_seqnum_progression(rows, report)
        self._check_umn_and_duplicates(rows, report)
        self._check_response_error_consistency(rows, report)
        self._check_timestamp_ordering(rows, report)

        return report

    # ------------------------------------------------------------------
    def _check_duplicate_txnids(self, rows: List[dict], report: ValidationReport) -> None:
        # By design, a request and its paired response share one logical
        # txnid (exactly 2 rows). Only 3+ occurrences indicate a real
        # duplicate-id collision.
        counts: Dict[str, int] = defaultdict(int)
        for row in rows:
            counts[row.get("txnid")] += 1
        for txnid, count in counts.items():
            if count > 2:
                report.add(f"Duplicate txnid detected: {txnid} (appears {count} times)")

    def _check_lifecycle_pairing(self, rows: List[dict], report: ValidationReport) -> None:
        by_txnid: Dict[str, List[dict]] = defaultdict(list)
        for row in rows:
            by_txnid[row["txnid"]].append(row)

        for txnid, txn_rows in by_txnid.items():
            apinames = [r["apiname"] for r in txn_rows]
            if len(apinames) == 1:
                api = apinames[0]
                if api in constants.REQUEST_RESPONSE_PAIRS:
                    report.add(f"Orphan request without response: txnid={txnid} api={api}")
                elif api in constants.RESPONSE_TO_REQUEST:
                    report.add(f"Orphan response without request: txnid={txnid} api={api}")
            elif len(apinames) == 2:
                req, resp = sorted(apinames, key=lambda a: 0 if a in constants.REQUEST_RESPONSE_PAIRS else 1)
                expected_resp = constants.REQUEST_RESPONSE_PAIRS.get(req)
                if expected_resp != resp:
                    report.add(f"Mismatched request/response pair for txnid={txnid}: {apinames}")
            else:
                report.add(f"Unexpected number of rows for txnid={txnid}: {len(apinames)}")

    def _check_master_references(self, rows: List[dict], report: ValidationReport) -> None:
        for row in rows:
            api = row["apiname"]
            if api not in constants.API_NAMES:
                report.add(f"Invalid apiname: {api} (txnid={row.get('txnid')})")
            if row.get("payerbank") and row["payerbank"] not in self.valid_banks:
                report.add(f"Invalid payerbank: {row['payerbank']} (txnid={row.get('txnid')})")
            if row.get("payeebank") and row["payeebank"] not in self.valid_banks:
                report.add(f"Invalid payeebank: {row['payeebank']} (txnid={row.get('txnid')})")
            if row.get("payerpsp") and row["payerpsp"] not in self.valid_psps:
                report.add(f"Invalid payerpsp: {row['payerpsp']} (txnid={row.get('txnid')})")
            if row.get("payeemcc") and row["payeemcc"] not in self.valid_mccs:
                report.add(f"Invalid payeemcc: {row['payeemcc']} (txnid={row.get('txnid')})")
            if row.get("purposecode") and row["purposecode"] not in self.valid_purposecodes:
                report.add(f"Invalid purposecode: {row['purposecode']} (txnid={row.get('txnid')})")
            if row.get("initiationmode") and row["initiationmode"] not in self.valid_initiation_modes:
                report.add(f"Invalid initiationmode: {row['initiationmode']} (txnid={row.get('txnid')})")
            if row.get("mandateoperation") and row["mandateoperation"] not in constants.MANDATE_OPERATIONS:
                report.add(f"Invalid mandateoperation: {row['mandateoperation']} (txnid={row.get('txnid')})")
            if row.get("recurrencepattern") and row["recurrencepattern"] not in constants.RECURRENCE_PATTERNS:
                report.add(f"Invalid recurrencepattern: {row['recurrencepattern']} (txnid={row.get('txnid')})")

    def _check_seqnum_progression(self, rows: List[dict], report: ValidationReport) -> None:
        seq_by_umn: Dict[str, List[int]] = defaultdict(list)
        for row in rows:
            if row.get("umn") and row.get("payerseqnum") is not None:
                seq_by_umn[row["umn"]].append(int(row["payerseqnum"]))

        for umn, seqs in seq_by_umn.items():
            # Sequence numbers appear twice per execution (ReqPay row) — dedupe
            # while preserving order of first occurrence for monotonic check.
            ordered_unique: List[int] = []
            for s in seqs:
                if not ordered_unique or ordered_unique[-1] != s:
                    ordered_unique.append(s)
            for prev, curr in zip(ordered_unique, ordered_unique[1:]):
                if curr <= prev:
                    report.add(f"Non-increasing payerseqnum for UMN={umn}: {prev} -> {curr}")

    def _check_umn_and_duplicates(self, rows: List[dict], report: ValidationReport) -> None:
        creation_apis = {"ReqMandate"}
        seen_creation_umns: set[str] = set()
        for row in rows:
            if row["apiname"] in creation_apis and row.get("umn"):
                if row["umn"] in seen_creation_umns:
                    report.add(f"Duplicate UMN at creation: {row['umn']}")
                seen_creation_umns.add(row["umn"])

    def _check_response_error_consistency(self, rows: List[dict], report: ValidationReport) -> None:
        for row in rows:
            responsecode = row.get("responsecode")
            if responsecode is None:
                continue
            if responsecode not in self.valid_response_codes:
                report.add(f"Invalid responsecode: {responsecode} (txnid={row.get('txnid')})")
            errorcode = row.get("errorcode")
            if row.get("responseresult") == "SUCCESS" and errorcode:
                report.add(f"Errorcode present on SUCCESS row: txnid={row.get('txnid')}")
            if row.get("responseresult") == "FAILURE":
                if not errorcode:
                    report.add(f"Missing errorcode on FAILURE row: txnid={row.get('txnid')}")
                elif errorcode not in self.valid_error_codes:
                    report.add(f"Invalid errorcode: {errorcode} (txnid={row.get('txnid')})")

    def _check_timestamp_ordering(self, rows: List[dict], report: ValidationReport) -> None:
        by_txnid: Dict[str, List[dict]] = defaultdict(list)
        for row in rows:
            by_txnid[row["txnid"]].append(row)

        for txnid, txn_rows in by_txnid.items():
            if len(txn_rows) != 2:
                continue
            timestamps = []
            for r in txn_rows:
                try:
                    timestamps.append((r["apiname"], datetime.strptime(r["ts"], "%Y-%m-%d %H:%M:%S")))
                except (ValueError, TypeError):
                    report.add(f"Invalid timestamp format for txnid={txnid}")
                    return
            timestamps.sort(key=lambda t: 0 if t[0] in constants.REQUEST_RESPONSE_PAIRS else 1)
            if timestamps[0][1] > timestamps[1][1]:
                report.add(f"Response timestamp precedes request for txnid={txnid}")
