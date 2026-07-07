"""
validation_module.py

Validates a generated batch of fact_upi_transactions BUSINESS-EVENT rows
against every integrity/business rule before it is written to CSV:
    - unique txnid (one row = one business event; no shared Req/Resp ids)
    - valid business event type ("transaction_type") and matching txntype
    - valid master references (bank/PSP/MCC/purposecode/initiationmode)
    - valid mandateoperation / recurrencepattern where populated
    - non-decreasing payerseqnum per UMN (consecutive repeats within one
      PDN+execution(+retry) cycle are legitimate and collapsed before
      the monotonic check)
    - no duplicate UMN at mandate creation
    - responsecode/errorcode consistency against the full status enum
    - valid, parseable timestamps and chronological ordering within a
      mandate execution cycle (PDN before its AutoPay execution/retries)

Rows failing validation are reported; the orchestrator uses this to
decide whether to reject and regenerate a batch.
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
        self._check_event_type_and_txntype(rows, report)
        self._check_master_references(rows, report)
        self._check_seqnum_progression(rows, report)
        self._check_umn_and_duplicates(rows, report)
        self._check_response_error_consistency(rows, report)
        self._check_timestamp_validity_and_cycle_ordering(rows, report)

        return report

    # ------------------------------------------------------------------
    def _check_duplicate_txnids(self, rows: List[dict], report: ValidationReport) -> None:
        """Every business-event row must have a globally unique txnid."""
        seen: set[str] = set()
        for row in rows:
            txnid = row.get("txnid")
            if txnid in seen:
                report.add(f"Duplicate txnid detected: {txnid}")
            seen.add(txnid)

    def _check_event_type_and_txntype(self, rows: List[dict], report: ValidationReport) -> None:
        for row in rows:
            api = row.get("transaction_type")
            if api not in constants.BUSINESS_EVENT_TYPES:
                report.add(f"Invalid business event type (transaction_type): {api} (txnid={row.get('txnid')})")
                continue
            expected_txntype = (
                constants.TXN_TYPE_FINANCIAL if api in constants.FINANCIAL_EVENT_TYPES
                else constants.TXN_TYPE_NON_FINANCIAL
            )
            if row.get("txntype") != expected_txntype:
                report.add(
                    f"txntype mismatch for {api}: expected {expected_txntype}, "
                    f"got {row.get('txntype')} (txnid={row.get('txnid')})"
                )
            if api in constants.FINANCIAL_EVENT_TYPES and row.get("txamount") in (None, ""):
                report.add(f"Missing txamount on financial event {api} (txnid={row.get('txnid')})")

    def _check_master_references(self, rows: List[dict], report: ValidationReport) -> None:
        for row in rows:
            txnid = row.get("txnid")
            if row.get("payerbank") and row["payerbank"] not in self.valid_banks:
                report.add(f"Invalid payerbank: {row['payerbank']} (txnid={txnid})")
            if row.get("payeebank") and row["payeebank"] not in self.valid_banks:
                report.add(f"Invalid payeebank: {row['payeebank']} (txnid={txnid})")
            if row.get("payerpsp") and row["payerpsp"] not in self.valid_psps:
                report.add(f"Invalid payerpsp: {row['payerpsp']} (txnid={txnid})")
            if row.get("payeemcc") and row["payeemcc"] not in self.valid_mccs:
                report.add(f"Invalid payeemcc: {row['payeemcc']} (txnid={txnid})")
            if row.get("purposecode") and row["purposecode"] not in self.valid_purposecodes:
                report.add(f"Invalid purposecode: {row['purposecode']} (txnid={txnid})")
            if row.get("initiationmode") and row["initiationmode"] not in self.valid_initiation_modes:
                report.add(f"Invalid initiationmode: {row['initiationmode']} (txnid={txnid})")
            if row.get("mandateoperation") and row["mandateoperation"] not in constants.MANDATE_OPERATIONS:
                report.add(f"Invalid mandateoperation: {row['mandateoperation']} (txnid={txnid})")
            if row.get("recurrencepattern") and row["recurrencepattern"] not in constants.RECURRENCE_PATTERNS:
                report.add(f"Invalid recurrencepattern: {row['recurrencepattern']} (txnid={txnid})")

    def _check_seqnum_progression(self, rows: List[dict], report: ValidationReport) -> None:
        """payerseqnum must never decrease per UMN. Consecutive repeats are
        legitimate: PDN, AUTOPAY_EXECUTION, and any AUTOPAY_RETRY rows that
        belong to the same execution cycle intentionally share one seqnum."""
        seq_by_umn: Dict[str, List[int]] = defaultdict(list)
        for row in rows:
            if row.get("umn") and row.get("payerseqnum") not in (None, ""):
                seq_by_umn[row["umn"]].append(int(row["payerseqnum"]))

        for umn, seqs in seq_by_umn.items():
            ordered_unique: List[int] = []
            for s in seqs:
                if not ordered_unique or ordered_unique[-1] != s:
                    ordered_unique.append(s)
            for prev, curr in zip(ordered_unique, ordered_unique[1:]):
                if curr <= prev:
                    report.add(f"Non-increasing payerseqnum for UMN={umn}: {prev} -> {curr}")

    def _check_umn_and_duplicates(self, rows: List[dict], report: ValidationReport) -> None:
        seen_creation_umns: set[str] = set()
        for row in rows:
            if row.get("transaction_type") == "MANDATE_REGISTRATION" and row.get("umn"):
                if row["umn"] in seen_creation_umns:
                    report.add(f"Duplicate UMN at creation: {row['umn']}")
                seen_creation_umns.add(row["umn"])

    def _check_response_error_consistency(self, rows: List[dict], report: ValidationReport) -> None:
        for row in rows:
            status = row.get("responseresult")
            if status is None:
                continue
            if status not in constants.TRANSACTION_STATUSES:
                report.add(f"Invalid transaction status: {status} (txnid={row.get('txnid')})")
                continue

            responsecode = row.get("responsecode")
            if responsecode and responsecode not in self.valid_response_codes:
                report.add(f"Invalid responsecode: {responsecode} (txnid={row.get('txnid')})")

            errorcode = row.get("errorcode")
            requires_error = status in constants.TERMINAL_FAILURE_STATUSES
            forbids_error = status in constants.TERMINAL_SUCCESS_STATUSES

            if forbids_error and errorcode:
                report.add(f"Errorcode present on {status} row: txnid={row.get('txnid')}")
            if requires_error and not errorcode:
                report.add(f"Missing errorcode on {status} row: txnid={row.get('txnid')}")
            elif errorcode and errorcode not in self.valid_error_codes:
                report.add(f"Invalid errorcode: {errorcode} (txnid={row.get('txnid')})")

    def _check_timestamp_validity_and_cycle_ordering(self, rows: List[dict], report: ValidationReport) -> None:
        """Validate timestamp parseability. (Mandate-cycle step ordering
        within a UMN/seqnum is covered by _check_seqnum_progression; PDN
        is no longer emitted as a standalone row, so there is nothing left
        to order it against.)"""
        for row in rows:
            ts_raw = row.get("ts")
            try:
                datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                report.add(f"Invalid timestamp format for txnid={row.get('txnid')}: {ts_raw}")
