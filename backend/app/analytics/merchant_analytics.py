"""Merchant Analytics — rankings, contribution, distribution, and growth.

Purpose:
    Transform the merchant traffic table (Merchant Service) into
    analytical insight: leaderboards, concentration, distribution shape,
    period-over-period growth, and side-by-side comparisons.

Business notes:
    - Every analysis derives from ``MerchantService.get_merchant_traffic``
      — one authoritative per-merchant table (person payees already
      excluded, zero-traffic merchants included).
    - No recommendations: this module describes; Phase 10 prescribes.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.analytics.analytics_exceptions import (
    InvalidAnalysisRequestError,
    translate_service_errors,
)
from app.analytics.analytics_utils import (
    bucket_counts,
    describe_distribution,
    percent_change,
    rank_rows,
    share_percentage,
)
from app.services import MerchantService

#: Histogram buckets for merchant transaction-count distribution.
_DISTRIBUTION_EDGES = (0, 1, 100, 1_000, 5_000, 20_000)
_DISTRIBUTION_LABELS = (
    "0",
    "1-99",
    "100-999",
    "1,000-4,999",
    "5,000-19,999",
    "20,000+",
)


class MerchantAnalytics:
    """Analytical views over merchant activity.

    Parameters:
        merchant_service: Business-level merchant access.
    """

    def __init__(self, merchant_service: MerchantService) -> None:
        self._merchants = merchant_service

    @translate_service_errors
    def get_merchant_rankings(
        self,
        *,
        by: str = "total_transactions",
        descending: bool = True,
        top_n: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Rank merchants by a traffic metric.

        Purpose:
            The general merchant leaderboard.

        Business Meaning:
            Which merchants carry the platform on any metric — counts,
            volume, or reliability.

        Parameters:
            by: Metric key (``total_transactions``, ``total_amount``,
                ``successful_transactions``, ``success_rate``).
            descending: ``True`` ranks highest-first.
            top_n: Keep only the first N (``None`` = all 500).
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.

        Returns:
            Ranked merchant traffic rows (each with ``rank``).
        """

        traffic = self._merchants.get_merchant_traffic(
            start_date=start_date, end_date=end_date
        )
        return rank_rows(traffic, by=by, descending=descending, top_n=top_n)

    @translate_service_errors
    def get_top_merchants(
        self,
        *,
        n: int = 10,
        by: str = "total_transactions",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """The N leading merchants on a metric.

        Purpose:
            The head of the merchant leaderboard.

        Business Meaning:
            The platform's anchor merchants.

        Parameters:
            n: How many merchants.
            by: Metric key (see :meth:`get_merchant_rankings`).
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.

        Returns:
            Ranked rows, best first.
        """

        return self.get_merchant_rankings(
            by=by, descending=True, top_n=n,
            start_date=start_date, end_date=end_date,
        )

    @translate_service_errors
    def get_bottom_merchants(
        self,
        *,
        n: int = 10,
        by: str = "total_transactions",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """The N weakest merchants on a metric.

        Purpose:
            The tail of the merchant leaderboard.

        Business Meaning:
            Where merchant activity is weakest — the growth team's
            outreach list (zero-traffic merchants included).

        Parameters:
            n: How many merchants.
            by: Metric key (see :meth:`get_merchant_rankings`).
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.

        Returns:
            Ranked rows, weakest first.
        """

        return self.get_merchant_rankings(
            by=by, descending=False, top_n=n,
            start_date=start_date, end_date=end_date,
        )

    @translate_service_errors
    def get_merchant_contribution(
        self,
        *,
        top_n: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Merchant contribution and concentration analysis.

        Purpose:
            How merchant traffic concentrates across the base.

        Business Meaning:
            Reliance risk: how much of merchant volume the leading
            merchants represent.

        Parameters:
            top_n: How many leading merchants to detail.
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.

        Returns:
            Dict with ``total_transactions`` / ``total_amount`` (merchant
            traffic only), ``top_merchants`` (rows extended with
            ``count_share_pct``, ``amount_share_pct``,
            ``cumulative_count_share_pct``), and
            ``top_{top_n}_count_share_pct`` / ``top_{top_n}_amount_share_pct``.
        """

        traffic = self._merchants.get_merchant_traffic(
            start_date=start_date, end_date=end_date
        )
        total_count = sum(row["total_transactions"] for row in traffic)
        total_amount = sum(
            (row["total_amount"] for row in traffic), Decimal("0")
        )
        leaders = rank_rows(traffic, by="total_transactions", top_n=top_n)

        cumulative = 0
        detailed = []
        for row in leaders:
            cumulative += row["total_transactions"]
            detailed.append(
                {
                    **row,
                    "count_share_pct": share_percentage(
                        row["total_transactions"], total_count
                    ),
                    "amount_share_pct": share_percentage(
                        row["total_amount"], total_amount
                    ),
                    "cumulative_count_share_pct": share_percentage(
                        cumulative, total_count
                    ),
                }
            )
        return {
            "total_transactions": total_count,
            "total_amount": total_amount,
            "top_merchants": detailed,
            f"top_{top_n}_count_share_pct": share_percentage(
                sum(r["total_transactions"] for r in leaders), total_count
            ),
            f"top_{top_n}_amount_share_pct": share_percentage(
                sum((r["total_amount"] for r in leaders), Decimal("0")),
                total_amount,
            ),
        }

    @translate_service_errors
    def get_merchant_distribution(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Any]:
        """Distribution of transaction activity across merchants.

        Purpose:
            The shape of the merchant base.

        Business Meaning:
            Whether the base is broad and even or a few giants and a long
            tail — the context for every merchant target.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.

        Returns:
            Dict with ``transaction_count_stats`` /
            ``transaction_amount_stats`` (descriptive statistics) and
            ``count_histogram`` (labelled buckets with counts and shares).
        """

        traffic = self._merchants.get_merchant_traffic(
            start_date=start_date, end_date=end_date
        )
        counts = [row["total_transactions"] for row in traffic]
        return {
            "transaction_count_stats": describe_distribution(counts),
            "transaction_amount_stats": describe_distribution(
                [row["total_amount"] for row in traffic]
            ),
            "count_histogram": bucket_counts(
                counts, _DISTRIBUTION_EDGES, _DISTRIBUTION_LABELS
            ),
        }

    @translate_service_errors
    def get_merchant_growth(
        self,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date,
        *,
        top_n: int | None = 10,
    ) -> dict[str, Any]:
        """Per-merchant growth between two periods.

        Purpose:
            Who is growing and who is fading.

        Business Meaning:
            Period-over-period movement per merchant — the factual input
            for retention and growth programs.

        Parameters:
            current_start: Current period first day (inclusive).
            current_end: Current period last day (inclusive).
            previous_start: Comparison period first day (inclusive).
            previous_end: Comparison period last day (inclusive).
            top_n: How many rows in each direction (``None`` = all).

        Returns:
            Dict with ``fastest_growing`` and ``fastest_declining`` (rows
            with per-period counts/amounts, ``count_change``,
            ``count_change_pct``, ``amount_change``) and ``periods``.
        """

        current = {
            row["merchant_id"]: row
            for row in self._merchants.get_merchant_traffic(
                start_date=current_start, end_date=current_end
            )
        }
        previous = {
            row["merchant_id"]: row
            for row in self._merchants.get_merchant_traffic(
                start_date=previous_start, end_date=previous_end
            )
        }
        movements = []
        for merchant_id, now in current.items():
            before = previous[merchant_id]
            movements.append(
                {
                    "merchant_id": merchant_id,
                    "merchant_name": now["merchant_name"],
                    "current_transactions": now["total_transactions"],
                    "previous_transactions": before["total_transactions"],
                    "count_change": now["total_transactions"]
                    - before["total_transactions"],
                    "count_change_pct": percent_change(
                        now["total_transactions"], before["total_transactions"]
                    ),
                    "current_amount": now["total_amount"],
                    "previous_amount": before["total_amount"],
                    "amount_change": now["total_amount"] - before["total_amount"],
                }
            )
        movements.sort(key=lambda row: row["count_change"], reverse=True)
        slice_n = top_n if top_n is not None else len(movements)
        return {
            "periods": {
                "current": {"start_date": current_start, "end_date": current_end},
                "previous": {"start_date": previous_start, "end_date": previous_end},
            },
            "fastest_growing": movements[:slice_n],
            "fastest_declining": list(reversed(movements[-slice_n:])),
        }

    @translate_service_errors
    def get_success_rate_analysis(
        self,
        *,
        minimum_transactions: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Merchant success-rate analysis.

        Purpose:
            Reliability seen merchant by merchant.

        Business Meaning:
            Which merchants experience the worst payment success — the
            factual input for failure remediation.

        Parameters:
            minimum_transactions: Ignore merchants below this activity
                (tiny samples make ratios meaningless).
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.

        Returns:
            Dict with ``success_rate_stats`` (descriptive statistics over
            qualifying merchants), ``worst`` and ``best`` (10 each,
            ranked), and ``qualifying_merchants``.

        Raises:
            InvalidAnalysisRequestError: For a negative threshold.
        """

        if minimum_transactions < 0:
            raise InvalidAnalysisRequestError(
                f"minimum_transactions must be >= 0, got {minimum_transactions}"
            )
        traffic = [
            row
            for row in self._merchants.get_merchant_traffic(
                start_date=start_date, end_date=end_date
            )
            if row["total_transactions"] >= minimum_transactions
        ]
        return {
            "qualifying_merchants": len(traffic),
            "minimum_transactions": minimum_transactions,
            "success_rate_stats": describe_distribution(
                [row["success_rate"] for row in traffic]
            ),
            "worst": rank_rows(traffic, by="success_rate", descending=False, top_n=10),
            "best": rank_rows(traffic, by="success_rate", descending=True, top_n=10),
        }

    @translate_service_errors
    def compare_merchants(
        self,
        merchant_ids: list[str],
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Compare named merchants side by side.

        Purpose:
            Direct multi-merchant comparison.

        Business Meaning:
            The factual table behind "how does A compare with B?".

        Parameters:
            merchant_ids: Two or more merchant master ids.
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.

        Returns:
            Traffic rows for the requested merchants, ranked by
            transaction count.

        Raises:
            InvalidAnalysisRequestError: For fewer than two ids or an
                unknown id.
        """

        if len(set(merchant_ids)) < 2:
            raise InvalidAnalysisRequestError(
                "compare_merchants needs at least two distinct merchant ids"
            )
        traffic = {
            row["merchant_id"]: row
            for row in self._merchants.get_merchant_traffic(
                start_date=start_date, end_date=end_date
            )
        }
        unknown = sorted(set(merchant_ids) - set(traffic))
        if unknown:
            raise InvalidAnalysisRequestError(f"unknown merchant ids: {unknown}")
        selected = [traffic[mid] for mid in set(merchant_ids)]
        return rank_rows(selected, by="total_transactions")
