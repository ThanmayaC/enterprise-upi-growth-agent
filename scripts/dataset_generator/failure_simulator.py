"""
failure_simulator.py

Decides transaction outcomes (SUCCESS/FAILURE) and, for failures,
assigns a response code and a compatible error code drawn from the
official masters (constants.RESPONSE_CODES / constants.ERROR_CODES),
honoring the configured SUCCESS_RATE / FAILURE_RATE.
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Optional

import constants
from config import GeneratorConfig


@dataclass(frozen=True)
class OutcomeResult:
    responsecode: str
    responseresult: str
    errorcode: Optional[str]
    currstatusdesc: str


class FailureSimulator:
    """Samples transaction outcomes consistent with the response/error masters."""

    def __init__(self, config: GeneratorConfig, rng: Random) -> None:
        self.config = config
        self.rng = rng
        # Failure codes are not equally likely; weight them so common,
        # retryable network/timeout issues dominate over rarer hard failures.
        self._failure_codes = list(constants.FAILURE_RESPONSE_CODES)
        self._failure_weights = [
            3.0 if constants.RESPONSE_TO_ERROR_MAP[c][0] in ("E002", "E003", "E006") else 1.0
            for c in self._failure_codes
        ]

    def decide_outcome(self, lifecycle_stage_is_terminal_pay: bool) -> OutcomeResult:
        """Decide SUCCESS/FAILURE for one response event.

        Non-financial lifecycle responses (mandate creation/auth/etc.) use
        the same success rate but rarely carry hard financial failure
        semantics; financial RespPay failures use the full failure code set.
        """
        is_success = self.rng.random() < self.config.SUCCESS_RATE
        if is_success:
            return OutcomeResult(
                responsecode=constants.SUCCESS_RESPONSE_CODE,
                responseresult="SUCCESS",
                errorcode=None,
                currstatusdesc=constants.CURR_STATUS_DESCRIPTIONS["COMPLETED"],
            )

        responsecode = self.rng.choices(self._failure_codes, weights=self._failure_weights, k=1)[0]
        errorcode = self.rng.choice(constants.RESPONSE_TO_ERROR_MAP[responsecode])
        return OutcomeResult(
            responsecode=responsecode,
            responseresult="FAILURE",
            errorcode=errorcode,
            currstatusdesc=constants.CURR_STATUS_DESCRIPTIONS["FAILED"],
        )
