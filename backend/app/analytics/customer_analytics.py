"""Customer Analytics — activity, frequency, behaviour, and trends.

Purpose:
    Transform the per-customer traffic table (Customer Service) into
    analytical insight: how many customers are active, how their activity
    is distributed, how often they transact, how they compare, and how the
    active base moves over time.

Business notes:
    - Every period analysis derives from
      ``CustomerService.get_customer_traffic`` — one authoritative
      per-customer table for the period (only *active* customers appear,
      most-active first). Registered-base figures come from
      ``CustomerService.count_registered``.
    - Lifetime summaries for a single customer delegate to
      ``CustomerService.get_customer_summary`` — the KPI-consistent view
      is owned by the service, not recomputed here.
    - No clustering and no segmentation: this module describes the base;
      grouping arrives with later phases.
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
    contribution_table,
    describe_distribution,
    month_windows,
    percent_change,
    rank_rows,
    share_percentage,
)
from app.services import CustomerService

#: Histogram buckets for per-customer transaction-frequency distribution.
#: Traffic only lists active customers, so the first bucket starts at 1.
_FREQUENCY_EDGES = (1, 2, 6, 21, 51, 101)
_FREQUENCY_LABELS = ("1", "2-5", "6-20", "21-50", "51-100", "100+")


class CustomerAnalytics:
    """Analytical views over customer activity.

    Parameters:
        customer_service: Business-level customer access.
    """

    def __init__(self, customer_service: CustomerService) -> None:
        self._customers = customer_service

    @translate_service_errors
    def get_active_customers(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Any]:
        """Size and activation of the active customer base for a period.

        Purpose:
            The headline "how many customers are active?" answer.

        Business Meaning:
            Active customers against the registered base — the activation
            gap the growth team works to close.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Dict with ``active_customers``, ``registered_customers``,
            ``activation_rate_pct``, ``total_transactions``, and
            ``average_transactions_per_active_customer``.
        """

        traffic = self._customers.get_customer_traffic(
            start_date=start_date, end_date=end_date
        )
        active = len(traffic)
        registered = self._customers.count_registered()
        total_transactions = sum(row["transaction_count"] for row in traffic)
        return {
            "active_customers": active,
            "registered_customers": registered,
            "activation_rate_pct": share_percentage(active, registered),
            "total_transactions": total_transactions,
            "average_transactions_per_active_customer": (
                round(total_transactions / active, 2) if active else 0.0
            ),
        }

    @translate_service_errors
    def get_activity_distribution(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Any]:
        """Distribution of activity across active customers.

        Purpose:
            The shape of the active customer base.

        Business Meaning:
            Whether activity is spread evenly or concentrated in a few
            heavy users — the context for every customer target.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Dict with ``transaction_count_stats`` /
            ``transaction_amount_stats`` (descriptive statistics over
            active customers) and ``frequency_histogram`` (labelled
            transaction-count buckets with counts and shares).
        """

        traffic = self._customers.get_customer_traffic(
            start_date=start_date, end_date=end_date
        )
        counts = [row["transaction_count"] for row in traffic]
        return {
            "transaction_count_stats": describe_distribution(counts),
            "transaction_amount_stats": describe_distribution(
                [row["total_amount"] for row in traffic]
            ),
            "frequency_histogram": bucket_counts(
                counts, _FREQUENCY_EDGES, _FREQUENCY_LABELS
            ),
        }

    @translate_service_errors
    def get_transaction_frequency(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Any]:
        """How often active customers transact in a period.

        Purpose:
            The frequency profile of the active base.

        Business Meaning:
            Distinguishes one-and-done customers from repeat users — the
            factual basis for engagement and retention programs.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Dict with ``active_customers``, ``single_transaction_customers``
            and ``single_transaction_share_pct`` (bought exactly once),
            ``repeat_customers`` and ``repeat_share_pct`` (transacted more
            than once), and ``frequency_histogram``.
        """

        traffic = self._customers.get_customer_traffic(
            start_date=start_date, end_date=end_date
        )
        counts = [row["transaction_count"] for row in traffic]
        active = len(counts)
        single = sum(1 for c in counts if c == 1)
        repeat = active - single
        return {
            "active_customers": active,
            "single_transaction_customers": single,
            "single_transaction_share_pct": share_percentage(single, active),
            "repeat_customers": repeat,
            "repeat_share_pct": share_percentage(repeat, active),
            "frequency_histogram": bucket_counts(
                counts, _FREQUENCY_EDGES, _FREQUENCY_LABELS
            ),
        }

    @translate_service_errors
    def get_top_customers(
        self,
        *,
        n: int = 10,
        by: str = "transaction_count",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """The N most active customers on a metric.

        Purpose:
            The head of the customer leaderboard.

        Business Meaning:
            The platform's most valuable customers by activity or spend.

        Parameters:
            n: How many customers.
            by: Metric key (``transaction_count`` or ``total_amount``).
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Ranked customer traffic rows (each with ``rank``), best first.
        """

        traffic = self._customers.get_customer_traffic(
            start_date=start_date, end_date=end_date
        )
        return rank_rows(traffic, by=by, descending=True, top_n=n)

    @translate_service_errors
    def get_customer_contribution(
        self,
        *,
        top_n: int = 10,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Customer contribution and concentration analysis.

        Purpose:
            How customer activity concentrates across the active base.

        Business Meaning:
            Reliance risk on the customer side: how much of platform
            activity the heaviest users represent.

        Parameters:
            top_n: How many leading customers to detail.
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The standard contribution object (see
            :func:`analytics_utils.contribution_table`): ``total_transactions``,
            ``total_amount``, ``leaders`` (with count/amount/cumulative
            shares), and the combined ``top_n`` shares.
        """

        traffic = self._customers.get_customer_traffic(
            start_date=start_date, end_date=end_date
        )
        return contribution_table(
            traffic,
            count_field="transaction_count",
            amount_field="total_amount",
            label_field="customer_vpa",
            top_n=top_n,
        )

    @translate_service_errors
    def get_customer_lifetime_summary(self, customer_id: str) -> dict[str, Any]:
        """One customer's lifetime activity summary.

        Purpose:
            The complete single-customer view for behaviour analysis.

        Business Meaning:
            Lifetime scale and reliability of one customer — profile,
            counts, spend, and first/last activity.

        Parameters:
            customer_id: Customer master id (e.g. ``CUST0000001``).

        Returns:
            The service summary (``profile``, ``total_transactions``,
            ``successful_transactions``, ``success_rate``, ``total_spent``,
            ``first_transaction_date``, ``last_transaction_date``,
            ``recent_transactions``).

        Raises:
            DataUnavailableError: If the customer id is unknown.
        """

        return self._customers.get_customer_summary(customer_id)

    @translate_service_errors
    def compare_customers(
        self,
        customer_vpas: list[str],
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Compare named customers side by side for a period.

        Purpose:
            Direct multi-customer comparison.

        Business Meaning:
            The factual table behind "how does customer A compare with B?".

        Parameters:
            customer_vpas: Two or more customer VPAs (the fact-side key).
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Traffic rows for the requested customers, ranked by
            transaction count.

        Raises:
            InvalidAnalysisRequestError: For fewer than two distinct VPAs
                or a VPA with no activity in the period.
        """

        if len(set(customer_vpas)) < 2:
            raise InvalidAnalysisRequestError(
                "compare_customers needs at least two distinct customer VPAs"
            )
        traffic = {
            row["customer_vpa"]: row
            for row in self._customers.get_customer_traffic(
                start_date=start_date, end_date=end_date
            )
        }
        unknown = sorted(set(customer_vpas) - set(traffic))
        if unknown:
            raise InvalidAnalysisRequestError(
                f"no activity in period for VPAs: {unknown}"
            )
        selected = [traffic[vpa] for vpa in set(customer_vpas)]
        return rank_rows(selected, by="transaction_count")

    @translate_service_errors
    def get_customer_trend(
        self, start_date: date, end_date: date
    ) -> dict[str, Any]:
        """Monthly trend of the active customer base.

        Purpose:
            The movement view of customer activity.

        Business Meaning:
            Month by month, how many customers are active, how much they
            transact, and how that base grows or shrinks — the retention
            signal on the customer side.

        Parameters:
            start_date: First day of the range (inclusive).
            end_date: Last day of the range (inclusive).

        Returns:
            Trend object: ``grain`` (``monthly``) and ``series`` rows with
            ``period`` (month start), ``active_customers``,
            ``transaction_count``, ``total_amount``, and
            ``active_change_pct`` (``None`` for the first month).

        Raises:
            InvalidAnalysisRequestError: If the range is inverted.
        """

        series: list[dict[str, Any]] = []
        previous: dict[str, Any] | None = None
        for window_start, window_end in month_windows(start_date, end_date):
            traffic = self._customers.get_customer_traffic(
                start_date=window_start, end_date=window_end
            )
            active = len(traffic)
            entry = {
                "period": window_start,
                "active_customers": active,
                "transaction_count": sum(row["transaction_count"] for row in traffic),
                "total_amount": sum(
                    (row["total_amount"] for row in traffic), Decimal("0")
                ),
                "active_change_pct": (
                    percent_change(active, previous["active_customers"])
                    if previous
                    else None
                ),
            }
            series.append(entry)
            previous = entry
        return {"grain": "monthly", "series": series}
