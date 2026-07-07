"""
failure_simulator.py

Decides business-event outcomes using STRICTLY the two status values
that exist in the official Response Code Master (SUCCESS / FAILURE —
see constants.RESPONSE_CODES). No invented status labels (TIMEOUT,
DECLINED, RETRY, PENDING, etc.) are produced; finer-grained detail
(why something failed, whether it's retryable) lives in failure_reason
and the retryable flag carried on the official response code, not in
extra status values.

Failure probability is contextual: it can shift based on transaction
amount, PSP/bank (a stable per-entity reliability factor, not just
noise), whether the transaction falls in a peak-traffic hour, and
whether the merchant is a high-value archetype — while every actual
failure still maps strictly to an official response/error code pair.
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Optional

import business_rules
import constants
from config import GeneratorConfig
from utils import clamp, derive_sub_seed


@dataclass(frozen=True)
class OutcomeResult:
    status: str
    responsecode: Optional[str]
    responseresult: str
    errorcode: Optional[str]
    failure_reason: Optional[str]
    retryable: bool
    currstatusdesc: str


class FailureSimulator:
    """Samples business-event outcomes consistent with the failure-reason model."""

    def __init__(self, config: GeneratorConfig, rng: Random) -> None:
        self.config = config
        self.rng = rng
        self._failure_reasons = list(constants.FAILURE_REASONS.keys())
        self._failure_weights = [
            3.0 if constants.FAILURE_REASONS[r]["retryable"] else 1.0
            for r in self._failure_reasons
        ]
        self._reliability_cache: dict[str, float] = {}

    def _entity_reliability_factor(self, entity_name: str) -> float:
        """Stable (not per-call-random) multiplier in ~[0.97, 1.03] for a
        given PSP/bank name, so some PSPs/banks are consistently a little
        more or less reliable than others across the whole run."""
        if entity_name not in self._reliability_cache:
            h = derive_sub_seed(0, entity_name)
            factor = 0.97 + (h % 1000) / 1000.0 * 0.06
            self._reliability_cache[entity_name] = factor
        return self._reliability_cache[entity_name]

    def _contextual_success_rate(
        self,
        amount: Optional[float] = None,
        is_peak_hour: bool = False,
        payer_psp: Optional[str] = None,
        payer_bank: Optional[str] = None,
        merchant_high_value: bool = False,
        transaction_type: Optional[str] = None,
    ) -> float:
        # Task 1/5: the category baseline (e.g. AutoPay retries fail far
        # more than a plain P2P transfer) comes from the centralized
        # Business Rule Engine rather than one flat config.SUCCESS_RATE
        # for every transaction type.
        rate = (
            business_rules.get_default_success_rate(transaction_type, fallback=self.config.SUCCESS_RATE)
            if transaction_type else self.config.SUCCESS_RATE
        )
        if amount is not None:
            if amount > 20_000:
                rate -= 0.03
            elif amount > 5_000:
                rate -= 0.01
        if is_peak_hour:
            rate -= 0.015
        if merchant_high_value:
            rate -= 0.01
        if payer_psp:
            rate *= self._entity_reliability_factor(payer_psp)
        if payer_bank:
            rate *= self._entity_reliability_factor(payer_bank)
        return clamp(rate, 0.75, 0.995)

    def decide_initial_outcome(
        self,
        amount: Optional[float] = None,
        is_peak_hour: bool = False,
        payer_psp: Optional[str] = None,
        payer_bank: Optional[str] = None,
        merchant_high_value: bool = False,
        transaction_type: Optional[str] = None,
    ) -> OutcomeResult:
        """Decide the outcome of a first attempt for one business event.
        All context parameters are optional so existing call sites without
        this information still work, falling back to the flat SUCCESS_RATE."""
        success_rate = self._contextual_success_rate(
            amount=amount, is_peak_hour=is_peak_hour, payer_psp=payer_psp,
            payer_bank=payer_bank, merchant_high_value=merchant_high_value,
            transaction_type=transaction_type,
        )
        if self.rng.random() < success_rate:
            return OutcomeResult(
                status="SUCCESS",
                responsecode=constants.SUCCESS_RESPONSE_CODE,
                responseresult="SUCCESS",
                errorcode=None,
                failure_reason=None,
                retryable=False,
                currstatusdesc=constants.CURR_STATUS_DESCRIPTIONS["COMPLETED"],
            )
        return self._sample_failure()

    def decide_retry_outcome(self, attempt: int = 1) -> OutcomeResult:
        """Decide the outcome of a retry attempt (higher success bias than
        a first attempt, decaying slightly with each further attempt so
        retry probability genuinely depends on retry count)."""
        decay = 0.9 ** max(0, attempt - 1)
        success_rate = clamp(self.config.RETRY_SUCCESS_PROBABILITY * decay, 0.05, 0.95)
        if self.rng.random() < success_rate:
            return OutcomeResult(
                status="SUCCESS",
                responsecode=constants.SUCCESS_RESPONSE_CODE,
                responseresult="SUCCESS",
                errorcode=None,
                failure_reason=None,
                retryable=False,
                currstatusdesc=constants.CURR_STATUS_DESCRIPTIONS["COMPLETED"],
            )
        return self._sample_failure()

    def _sample_failure(self) -> OutcomeResult:
        reason = self.rng.choices(self._failure_reasons, weights=self._failure_weights, k=1)[0]
        meta = constants.FAILURE_REASONS[reason]
        retryable = bool(meta["retryable"])
        # Status is strictly "FAILURE" — the only failure value the
        # official Response Code Master defines. Retryability and the
        # specific reason are carried separately, not folded into extra
        # invented status labels.
        return OutcomeResult(
            status="FAILURE",
            responsecode=meta["responsecode"],
            responseresult="FAILURE",
            errorcode=meta["errorcode"],
            failure_reason=reason,
            retryable=retryable,
            currstatusdesc=constants.CURR_STATUS_DESCRIPTIONS.get("FAILED", "Transaction failed"),
        )

    def decide_mandate_failure(self, reason: str) -> OutcomeResult:
        """Build a FAILURE outcome for a specific mandate-state reason
        (MANDATE_EXPIRED / MANDATE_PAUSED / MANDATE_REVOKED)."""
        meta = constants.FAILURE_REASONS[reason]
        return OutcomeResult(
            status="FAILURE",
            responsecode=meta["responsecode"],
            responseresult="FAILURE",
            errorcode=meta["errorcode"],
            failure_reason=reason,
            retryable=False,
            currstatusdesc=constants.CURR_STATUS_DESCRIPTIONS.get("FAILED", "Transaction failed"),
        )
