"""Bank Analytics — issuer/acquirer rankings, contribution, and trends.

Purpose:
    Transform the bank traffic tables (Bank Service) into analytical
    insight on both sides of the network: who issues and who acquires the
    most, how bank traffic concentrates, how reliable each bank is, and
    how a bank moves over time.

Business notes:
    - Two sides, one vocabulary: *issuer* is the debit (payer) side,
      *acquirer* is the credit (payee) side. Every method takes a
      ``side`` and dispatches to the matching Bank Service summary; the
      analytics never re-derive per-bank figures.
    - Bank traffic rows carry ``bank``, ``total_transactions``,
      ``successful_transactions``, ``success_rate``, and ``total_amount``
      — success rate is owned by the service (KPI-consistent).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Callable

from app.analytics.analytics_exceptions import (
    InvalidAnalysisRequestError,
    translate_service_errors,
)
from app.analytics.analytics_utils import (
    contribution_table,
    describe_distribution,
    month_windows,
    percent_change,
    rank_rows,
)
from app.services import BankService

#: Supported transaction sides (business terminology).
SIDE_ISSUER = "issuer"
SIDE_ACQUIRER = "acquirer"
_SIDES = (SIDE_ISSUER, SIDE_ACQUIRER)


class BankAnalytics:
    """Analytical views over bank traffic, both issuer and acquirer.

    Parameters:
        bank_service: Business-level bank access.
    """

    def __init__(self, bank_service: BankService) -> None:
        self._banks = bank_service

    def _summary_for(
        self, side: str
    ) -> Callable[..., list[dict[str, Any]]]:
        """Resolve a side to its Bank Service summary method (pure)."""

        if side == SIDE_ISSUER:
            return self._banks.get_issuer_summary
        if side == SIDE_ACQUIRER:
            return self._banks.get_acquirer_summary
        raise InvalidAnalysisRequestError(
            f"unknown side '{side}'; expected one of {list(_SIDES)}"
        )

    @translate_service_errors
    def get_bank_rankings(
        self,
        *,
        side: str = SIDE_ISSUER,
        by: str = "total_transactions",
        descending: bool = True,
        top_n: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Rank banks on one side by a traffic metric.

        Purpose:
            The general bank leaderboard.

        Business Meaning:
            Which banks carry the platform on the chosen side — by count,
            volume, or reliability.

        Parameters:
            side: ``"issuer"`` (debit side) or ``"acquirer"`` (credit side).
            by: Metric key (``total_transactions``, ``total_amount``,
                ``successful_transactions``, ``success_rate``).
            descending: ``True`` ranks highest-first.
            top_n: Keep only the first N (``None`` = all banks).
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Ranked bank traffic rows (each with ``rank``).

        Raises:
            InvalidAnalysisRequestError: For an unknown side.
        """

        rows = self._summary_for(side)(start_date=start_date, end_date=end_date)
        return rank_rows(rows, by=by, descending=descending, top_n=top_n)

    @translate_service_errors
    def get_issuer_analysis(
        self,
        *,
        top_n: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Issuer-side (debit) analysis of the bank base.

        Purpose:
            The standard issuer report block.

        Business Meaning:
            Where debits originate — the leading issuing banks and how
            issuer traffic concentrates.

        Parameters:
            top_n: How many leading issuers to detail.
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The contribution object (see :meth:`get_bank_contribution`)
            for the issuer side.
        """

        return self.get_bank_contribution(
            side=SIDE_ISSUER, top_n=top_n, start_date=start_date, end_date=end_date
        )

    @translate_service_errors
    def get_acquirer_analysis(
        self,
        *,
        top_n: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Acquirer-side (credit) analysis of the bank base.

        Purpose:
            The standard acquirer report block.

        Business Meaning:
            Where credits land — the leading acquiring banks and how
            acquirer traffic concentrates.

        Parameters:
            top_n: How many leading acquirers to detail.
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The contribution object (see :meth:`get_bank_contribution`)
            for the acquirer side.
        """

        return self.get_bank_contribution(
            side=SIDE_ACQUIRER, top_n=top_n, start_date=start_date, end_date=end_date
        )

    @translate_service_errors
    def get_bank_contribution(
        self,
        *,
        side: str = SIDE_ISSUER,
        top_n: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Bank contribution and concentration on one side.

        Purpose:
            How bank traffic concentrates across the base.

        Business Meaning:
            Reliance risk: how much of the side's volume the leading banks
            represent.

        Parameters:
            side: ``"issuer"`` or ``"acquirer"``.
            top_n: How many leading banks to detail.
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The standard contribution object (see
            :func:`analytics_utils.contribution_table`): ``total_transactions``,
            ``total_amount``, ``leaders`` (with count/amount/cumulative
            shares), and the combined ``top_n`` shares. The reported
            ``side`` is echoed alongside.
        """

        rows = self._summary_for(side)(start_date=start_date, end_date=end_date)
        contribution = contribution_table(
            rows,
            count_field="total_transactions",
            amount_field="total_amount",
            label_field="bank",
            top_n=top_n,
        )
        return {"side": side, **contribution}

    @translate_service_errors
    def get_volume_comparison(
        self,
        *,
        side: str = SIDE_ISSUER,
        top_n: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Compare banks by transaction volume on one side.

        Purpose:
            The volume view of the bank base.

        Business Meaning:
            Which banks move the most money — the volume leaderboard with
            the total it is measured against.

        Parameters:
            side: ``"issuer"`` or ``"acquirer"``.
            top_n: Keep only the first N banks (``None`` = all).
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Dict with ``side``, ``total_amount`` (over all banks), and
            ``banks`` ranked by ``total_amount``.
        """

        rows = self._summary_for(side)(start_date=start_date, end_date=end_date)
        total_amount = sum((row["total_amount"] for row in rows), Decimal("0"))
        return {
            "side": side,
            "total_amount": total_amount,
            "banks": rank_rows(rows, by="total_amount", top_n=top_n),
        }

    @translate_service_errors
    def get_success_comparison(
        self,
        *,
        side: str = SIDE_ISSUER,
        minimum_transactions: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Compare banks by payment success on one side.

        Purpose:
            Reliability seen bank by bank.

        Business Meaning:
            Which banks experience the worst payment success — the factual
            input for issuer/acquirer remediation.

        Parameters:
            side: ``"issuer"`` or ``"acquirer"``.
            minimum_transactions: Ignore banks below this activity (tiny
                samples make ratios meaningless).
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Dict with ``side``, ``qualifying_banks``,
            ``minimum_transactions``, ``success_rate_stats`` (descriptive
            statistics over qualifying banks), and ``worst`` / ``best``
            (ranked by success rate).

        Raises:
            InvalidAnalysisRequestError: For a negative threshold or an
                unknown side.
        """

        if minimum_transactions < 0:
            raise InvalidAnalysisRequestError(
                f"minimum_transactions must be >= 0, got {minimum_transactions}"
            )
        rows = [
            row
            for row in self._summary_for(side)(
                start_date=start_date, end_date=end_date
            )
            if row["total_transactions"] >= minimum_transactions
        ]
        return {
            "side": side,
            "qualifying_banks": len(rows),
            "minimum_transactions": minimum_transactions,
            "success_rate_stats": describe_distribution(
                [row["success_rate"] for row in rows]
            ),
            "worst": rank_rows(rows, by="success_rate", descending=False),
            "best": rank_rows(rows, by="success_rate", descending=True),
        }

    @translate_service_errors
    def get_bank_trend(
        self,
        bank_name: str,
        start_date: date,
        end_date: date,
        *,
        side: str = SIDE_ISSUER,
    ) -> dict[str, Any]:
        """Monthly traffic trend for one bank on one side.

        Purpose:
            The movement view of a single bank.

        Business Meaning:
            Month by month, how one bank's activity, volume, and
            reliability move — the factual basis for a bank review.

        Parameters:
            bank_name: Full bank display name (as carried on the fact).
            start_date: First day of the range (inclusive).
            end_date: Last day of the range (inclusive).
            side: ``"issuer"`` or ``"acquirer"``.

        Returns:
            Trend object: ``bank``, ``side``, ``grain`` (``monthly``), and
            ``series`` rows with ``period`` (month start),
            ``transaction_count``, ``successful_transactions``,
            ``success_rate``, ``total_amount``, and ``count_change_pct``
            (``None`` for the first month). Months with no traffic for the
            bank carry zeros.

        Raises:
            InvalidAnalysisRequestError: For an inverted range or unknown
                side.
        """

        summary = self._summary_for(side)  # validates side eagerly
        series: list[dict[str, Any]] = []
        previous: dict[str, Any] | None = None
        for window_start, window_end in month_windows(start_date, end_date):
            row = next(
                (
                    entry
                    for entry in summary(
                        start_date=window_start, end_date=window_end
                    )
                    if entry["bank"] == bank_name
                ),
                None,
            )
            count = row["total_transactions"] if row else 0
            entry = {
                "period": window_start,
                "transaction_count": count,
                "successful_transactions": (
                    row["successful_transactions"] if row else 0
                ),
                "success_rate": row["success_rate"] if row else 0.0,
                "total_amount": row["total_amount"] if row else Decimal("0.00"),
                "count_change_pct": (
                    percent_change(count, previous["transaction_count"])
                    if previous
                    else None
                ),
            }
            series.append(entry)
            previous = entry
        return {
            "bank": bank_name,
            "side": side,
            "grain": "monthly",
            "series": series,
        }
