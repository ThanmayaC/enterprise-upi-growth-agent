"""
transaction_generator.py

Produces rows for the fact_upi_transactions table as an ENTERPRISE
BUSINESS-EVENT FACT TABLE: one row = one business transaction (P2P
payment, merchant payment, mandate registration, AutoPay execution,
refund, etc.) — NOT one API call. See constants.BUSINESS_EVENT_TYPES for
the full vocabulary this module emits.

Design highlights:
    - Mandates are long-lived: registration happens once; PDN + AutoPay
      execution cycles are scheduled weeks/months later and spread across
      the date range (never immediately after registration).
    - Mandates carry real state (ACTIVE/PAUSED/REVOKED/EXPIRED/FAILED/
      UPDATED/SUSPENDED) via relationship_generator.MandateContext, with
      legal-transition enforcement.
    - Customers have behavioural personas (persona_simulator.py); merchants
      have behavioural archetypes (merchant_behavior.py). Both bias event
      selection, amounts, and timing without touching customer/merchant
      identity generation.
    - Failures use named reasons (constants.FAILURE_REASONS); retryable
      failures may produce a distinct AUTOPAY_RETRY row for mandate
      executions, or are resolved internally (bounded attempts) for
      one-off financial events so the vocabulary stays business-event
      shaped.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import accumulate
from random import Random
from typing import List, Optional

import business_rules
import constants
from config import GeneratorConfig
from customer_generator import CustomerRecord
from failure_simulator import FailureSimulator, OutcomeResult
from growth_simulator import GrowthSimulator
from master_data_generator import BankRecord, PspRecord
from merchant_behavior import MerchantBehaviorSimulator
from merchant_generator import MerchantRecord
from persona_simulator import PersonaSimulator
from relationship_generator import MandateContext, RelationshipManager
from seasonality_simulator import SeasonalitySimulator
from utils import derive_sub_seed, format_date, format_ts, seeded_random


@dataclass
class _EntityLookup:
    bank_by_name: dict
    psp_by_name: dict


# Merchants in these MCCs (restaurants, food delivery, bars) get the
# bimodal lunch+dinner intraday shape instead of the generic OFFICE/
# EVENING_FOOD curve, matching real Swiggy/Zomato-style traffic.
FOOD_SERVICE_MCCS: frozenset[str] = frozenset({"5812", "5813"})

# Merchants in these MCCs run meaningfully busier on weekends than an
# average merchant (e-commerce shopping, dining out, entertainment,
# apparel, travel) — Task 3 "Amazon: weekend spike", "Swiggy: weekend
# spike".
WEEKEND_SPIKE_MCCS: frozenset[str] = frozenset({"5964", "5812", "5813", "5311", "5691", "7011", "4511"})

# Fuel stations get the bimodal morning+evening commute intraday shape.
COMMUTE_MCCS: frozenset[str] = frozenset({"5541"})


@dataclass
class _RecentPayment:
    """Rolling record of a successful merchant payment, used to sample refunds."""

    txnid: str
    customer: CustomerRecord
    merchant: MerchantRecord
    amount: float
    ts: datetime
    purposecode: str


class TransactionGenerator:
    """Generates a full batch of fact_upi_transactions business-event rows."""

    _MAX_RECENT_PAYMENTS = 5000

    def __init__(
        self,
        config: GeneratorConfig,
        banks: List[BankRecord],
        psps: List[PspRecord],
        customers: List[CustomerRecord],
        merchants: List[MerchantRecord],
    ) -> None:
        self.config = config
        self.banks = banks
        self.psps = psps
        self.customers = customers
        self.merchants = merchants

        self.rng: Random = seeded_random(derive_sub_seed(config.RANDOM_SEED, "transaction_generator"))
        self.relationships = RelationshipManager(self.rng)
        self.seasonality = SeasonalitySimulator(config.START_DATE, config.END_DATE, self.rng)
        self.growth = GrowthSimulator(self.rng)
        self.failure = FailureSimulator(config, self.rng)
        self.personas = PersonaSimulator(customers, self.rng)
        self.merchant_behavior = MerchantBehaviorSimulator()

        self._lookup = _EntityLookup(
            bank_by_name={b.bank_name: b for b in banks},
            psp_by_name={p.psp_name: p for p in psps},
        )
        self._customer_weights = self.growth.entity_market_share_weights(len(customers))
        # Task 5: heavy/dormant/power/business users — fold each customer's
        # activity-tier multiplier into their base selection weight so
        # activity frequency, not just behaviour flavour, varies by
        # customer. This propagates into every _customer_weights_by_category
        # below since they're all derived from this array.
        self._customer_weights = [
            w * self.personas.activity_multiplier_for(c)
            for w, c in zip(self._customer_weights, customers)
        ]
        self._merchant_weights = self.growth.merchant_selection_weights(merchants)

        # Archetype-aware merchant weighting for ONE-OFF events: a merchant
        # whose behaviour archetype is AutoPay/BBPS-heavy (Netflix, an
        # insurer, an electricity board) should rarely surface as a random
        # one-off MERCHANT_PAYMENT/QR/Collect row, since that volume is
        # supposed to flow through its mandate instead. Mandate registration
        # already biases toward these merchants (see generate_autopay_
        # registration); this is the complementary bias in the other
        # direction so the same merchant doesn't show contradictory
        # behaviour across both paths.
        self._oneoff_merchant_weights = [
            w * (self.merchant_behavior.profile_for(m).oneoff_share + 0.05)
            for w, m in zip(self._merchant_weights, merchants)
        ]

        # Persona-aware customer weighting per top-level transaction
        # category. Overall category row-counts are still governed by
        # config.BUSINESS_EVENT_DISTRIBUTION (unchanged); this only shifts
        # *which* customers populate each category, so a college student
        # persona surfaces disproportionately in P2P/QR rows and a retired
        # persona in BBPS rows, etc.
        self._customer_weights_by_category = {
            "p2p": [
                w * self.personas.profile_for(c).p2p_weight
                for w, c in zip(self._customer_weights, customers)
            ],
            "merchant_payment": [
                w * self.personas.profile_for(c).merchant_payment_weight
                for w, c in zip(self._customer_weights, customers)
            ],
            "qr": [
                w * self.personas.profile_for(c).qr_weight
                for w, c in zip(self._customer_weights, customers)
            ],
            "bbps": [
                w * self.personas.profile_for(c).bbps_weight
                for w, c in zip(self._customer_weights, customers)
            ],
        }

        n_mandate_customers = max(1, int(len(customers) * config.MANDATE_CUSTOMER_SHARE))
        self._mandate_customers = self.rng.sample(customers, k=min(n_mandate_customers, len(customers)))

        # PERFORMANCE (critical at real scale): random.choices(weights=...)
        # recomputes the full cumulative-sum array from scratch on EVERY
        # call. At small scale (thousands of customers) that's invisible;
        # at 100k+ customers and 1M+ target rows it turns into billions of
        # redundant operations and the generator appears to hang for hours.
        # Precompute cum_weights ONCE here and use
        # random.choices(cum_weights=...) everywhere a large population
        # (self.customers, self.merchants) is sampled repeatedly.
        self._customer_cum_weights = list(accumulate(self._customer_weights))
        self._merchant_cum_weights = list(accumulate(self._merchant_weights))
        self._oneoff_merchant_cum_weights = list(accumulate(self._oneoff_merchant_weights))
        self._customer_cum_weights_by_category = {
            k: list(accumulate(v)) for k, v in self._customer_weights_by_category.items()
        }
        self._autopay_merchant_cum_weights = list(accumulate([
            self.merchant_behavior.profile_for(m).autopay_share + 0.05 for m in self.merchants
        ]))

        self._recent_payments: List[_RecentPayment] = []

        # Persistent per-customer behaviour: favourite merchants, personal
        # preferred hour, personal spend multiplier — assigned once so
        # customers "develop history" (repeat visits to the same handful
        # of merchants) instead of behaving independently every transaction.
        self.relationships.build_customer_preferences(
            customers, merchants, self._oneoff_merchant_cum_weights, self.rng
        )
        self._merchant_by_id = {m.merchant_id: m for m in merchants}

    def _select_merchant_for_customer(self, customer: CustomerRecord, fallback_cum_weights: List[float]) -> MerchantRecord:
        """70% of the time, return one of this customer's established
        favourite merchants (a repeat visit); 30% of the time, sample a new
        merchant from the given weighted pool. This is what produces
        realistic customer history (Amazon, Swiggy, Amazon, recharge,
        Netflix...) instead of a fresh uniformly-random merchant every time."""
        pref = self.relationships.preference_for(customer)
        if pref and pref.favorite_merchant_ids and self.rng.random() < 0.7:
            fav_id = self.rng.choice(pref.favorite_merchant_ids)
            merchant = self._merchant_by_id.get(fav_id)
            if merchant is not None:
                return merchant
        return self.rng.choices(self.merchants, cum_weights=fallback_cum_weights, k=1)[0]

    # ------------------------------------------------------------------
    # Shared row construction (identity/product/credential fields — these
    # are unaffected by the API -> business-event refactor).
    # ------------------------------------------------------------------
    def _base_row(self) -> dict:
        return {field: None for field in constants.FACT_TABLE_FIELDS}

    def _payer_fields(self, customer: CustomerRecord) -> dict:
        psp = self._lookup.psp_by_name.get(customer.payerpsp)
        payer_psp_bank = psp.sponsor_bank if psp else customer.payerbank
        return {
            "payeraddress": customer.payeraddress,
            "payerbank": customer.payerbank,
            "payerpsp": customer.payerpsp,
            "payerpsporgid": customer.payerpsporgid,
            "payer_psp_bank": payer_psp_bank,
            "remitterorgid": customer.remitterorgid,
            "remitteracctype": customer.remitteracctype,
        }

    def _payee_merchant_fields(self, merchant: MerchantRecord) -> dict:
        psp = self._lookup.psp_by_name.get(merchant.payeepsp)
        payee_psp_bank = psp.sponsor_bank if psp else merchant.payeebank
        return {
            "payeeaddress": merchant.payeeaddress,
            "payeename": merchant.merchant_name,
            "payeebank": merchant.payeebank,
            "payee_psp_bank": payee_psp_bank,
            "payeemcc": merchant.mcc,
            "payeetype": "MERCHANT",
            "payeemerchantgenre": merchant.merchant_genre,
            "payeemerchanttype": merchant.merchant_type,
            "payeeonboardingtype": merchant.onboarding_type,
            "payee_verified_name": merchant.verified_name,
            "payeepsporgid": merchant.payeepsporgid,
        }

    def _payee_p2p_fields(self, payee_customer: CustomerRecord) -> dict:
        psp = self._lookup.psp_by_name.get(payee_customer.payerpsp)
        payee_psp_bank = psp.sponsor_bank if psp else payee_customer.payerbank
        return {
            "payeeaddress": payee_customer.payeraddress,
            "payeename": payee_customer.customer_name,
            "payeebank": payee_customer.payerbank,
            "payee_psp_bank": payee_psp_bank,
            "payeemcc": None,
            "payeetype": "PERSON",
            "payeemerchantgenre": None,
            "payeemerchanttype": None,
            "payeeonboardingtype": None,
            "payee_verified_name": payee_customer.customer_name,
            "payeepsporgid": payee_customer.payerpsporgid,
        }

    def _cred_fields(self) -> dict:
        cred_type = self.rng.choice(constants.CRED_TYPES)
        cred_subtype = self.rng.choice(constants.CRED_SUBTYPES[cred_type])
        secondary = self.rng.random() < 0.1
        cred_type_2 = self.rng.choice(constants.CRED_TYPES) if secondary else None
        cred_subtype_2 = self.rng.choice(constants.CRED_SUBTYPES[cred_type_2]) if secondary else None
        return {
            "cred_type": cred_type,
            "cred_subtype": cred_subtype,
            "cred_type_secondary": cred_type_2,
            "cred_subtype_secondary": cred_subtype_2,
        }

    def _product_fields(self, customer: CustomerRecord) -> dict:
        return {
            "pracctype": customer.remitteracctype,
            "prcode": f"PR{self.rng.randint(1000, 9999)}",
            "prorgid": customer.remitterorgid,
            "prdmobile": customer.mobile,
            "pycode": f"PY{self.rng.randint(1000, 9999)}",
            "pyorgid": customer.payerpsporgid,
            "pyrefaddr": customer.payeraddress,
        }

    def _purpose_description(self, purposecode: str) -> str:
        for p in constants.PURPOSE_CODES:
            if p["purposecode"] == purposecode:
                return p["purpose"]
        return "Default"

    def _pick_purposecode_for_mcc(self, mcc: str) -> str:
        """Deterministic purpose code for a one-off merchant payment,
        via the Business Rule Engine (business_rules.py). No longer a
        random pick among MCC-compatible codes."""
        return business_rules.get_purpose_code(mcc, transaction_type="MERCHANT_PAYMENT")

    def _pick_recurring_purposecode_for_mcc(self, mcc: str) -> str:
        """Deterministic purpose code for a recurring/AutoPay-related
        transaction, via the Business Rule Engine."""
        return business_rules.get_purpose_code(mcc, transaction_type="AUTOPAY_EXECUTION")

    def _pick_initiation_mode(self, mandate_related: bool = False, qr: bool = False,
                               international: bool = False, bbps: bool = False,
                               mcc: Optional[str] = None) -> str:
        """Deterministic initiation mode via the Business Rule Engine. The
        boolean flags map onto a transaction_type so every existing call
        site keeps working unchanged while the underlying resolution is
        now fully rule-driven, not random."""
        if mandate_related:
            transaction_type = "AUTOPAY_EXECUTION"
        elif bbps:
            transaction_type = "BBPS_PAYMENT"
        elif international:
            transaction_type = "INTERNATIONAL_PAYMENT"
        elif qr:
            transaction_type = "QR_PAYMENT"
        else:
            transaction_type = "MERCHANT_PAYMENT"
        return business_rules.get_initiation_mode(transaction_type, mcc)

    def _outcome_fields(self, outcome: OutcomeResult, txnnote: str) -> dict:
        return {
            "responsecode": outcome.responsecode,
            "responseresult": outcome.responseresult,
            "errorcode": outcome.errorcode,
            "currstatusdesc": outcome.currstatusdesc,
            "txnnote": txnnote,
        }

    def _resolve_final_outcome(
        self,
        base_note: str,
        amount: Optional[float] = None,
        ts: Optional[datetime] = None,
        payer_psp: Optional[str] = None,
        payer_bank: Optional[str] = None,
        merchant_high_value: bool = False,
        transaction_type: Optional[str] = None,
        mcc: Optional[str] = None,
    ) -> tuple[OutcomeResult, str]:
        """Resolve a one-off financial event's outcome, honoring bounded
        retries internally (no separate row emitted - the vocabulary has
        no generic "_RETRY" event for one-off payment types). Failure
        probability is contextual (amount, peak hour, PSP/bank, merchant
        archetype, and now the transaction-type category baseline from
        business_rules.get_default_success_rate). Whether a retryable
        failure is actually retried is itself gated by
        business_rules.get_retry_probability — a casual P2P transfer is
        retried far less doggedly than a biller chasing a BBPS/AutoPay
        collection. Returns the terminal outcome and a note describing
        how many attempts it took.
        """
        is_peak_hour = self.seasonality.is_peak_hour(ts.hour) if ts is not None else False
        outcome = self.failure.decide_initial_outcome(
            amount=amount, is_peak_hour=is_peak_hour, payer_psp=payer_psp,
            payer_bank=payer_bank, merchant_high_value=merchant_high_value,
            transaction_type=transaction_type,
        )
        attempts = 1
        retry_probability = business_rules.get_retry_probability(transaction_type or "", mcc)
        while (outcome.retryable and attempts <= self.config.MAX_RETRY_ATTEMPTS
               and self.rng.random() < retry_probability):
            outcome = self.failure.decide_retry_outcome(attempt=attempts)
            attempts += 1
        note = base_note if attempts == 1 else f"{base_note} (resolved after {attempts} attempts)"
        return outcome, note

    def _customer_ticket_multiplier(self, customer: CustomerRecord) -> float:
        persona_multiplier = self.personas.profile_for(customer).avg_ticket_multiplier
        pref = self.relationships.preference_for(customer)
        personal_multiplier = pref.spend_multiplier if pref else 1.0
        return persona_multiplier * personal_multiplier

    def _sample_ts_for_customer(self, customer: CustomerRecord, base_category: str = "DEFAULT",
                                 weekend_boost: float = 1.0) -> datetime:
        """Sample a timestamp shaped by the natural intraday category for
        this kind of transaction, this customer's persona (night-owl
        tendency, salary-day clustering), this customer's own personal
        preferred hour AND preferred weekday(s) (Task 2 customer
        continuity), and optionally a merchant-driven weekend spike
        (Task 3 — e.g. e-commerce/food-delivery/entertainment merchants
        run busier on weekends than an average merchant) — so two
        customers with the same persona still transact at recognizably
        different times, and a merchant's own weekend personality shows
        through regardless of which customer is paying it."""
        persona = self.personas.profile_for(customer)
        pref = self.relationships.preference_for(customer)
        preferred_weekdays = pref.preferred_weekdays if pref else None

        category = base_category
        if base_category != "NIGHT_OTT" and self.rng.random() < min(0.4, 0.12 * persona.night_activity_multiplier):
            category = "NIGHT_OTT"

        if self.rng.random() < min(0.5, 0.18 * persona.salary_day_affinity):
            d = self.seasonality.sample_salary_day(weekend_boost, preferred_weekdays)
        else:
            d = self.seasonality.sample_day(weekend_boost, preferred_weekdays)

        if pref and self.rng.random() < 0.5:
            spread = max(1, pref.preferred_hour_spread)
            hour = int(round(self.rng.gauss(pref.preferred_hour_center, spread))) % 24
        else:
            hour = self.seasonality.sample_hour_for_category(category)

        minute = self.rng.randint(0, 59)
        second = self.rng.randint(0, 59)
        return datetime(d.year, d.month, d.day, hour, minute, second)

    def _collect_not_approved_outcome(self) -> OutcomeResult:
        """Build a FAILURE outcome for a Collect request the payer never
        approved, mapped to the official CUSTOMER_DECLINED response/error
        code pair. Status is strictly "FAILURE" (the only failure value
        the official Response Code Master defines) — the decline detail
        lives in failure_reason, not in an invented status label."""
        meta = constants.FAILURE_REASONS["CUSTOMER_DECLINED"]
        return OutcomeResult(
            status="FAILURE",
            responsecode=meta["responsecode"],
            responseresult="FAILURE",
            errorcode=meta["errorcode"],
            failure_reason="CUSTOMER_DECLINED",
            retryable=False,
            currstatusdesc=constants.CURR_STATUS_DESCRIPTIONS.get("FAILED", "Transaction failed"),
        )

    # ------------------------------------------------------------------
    # One-off business events: each returns exactly one row.
    # ------------------------------------------------------------------
    def _new_financial_shared(self, customer: CustomerRecord, payee_fields: dict, purposecode: str,
                               initiationmode: str, ts: datetime) -> dict:
        row = self._base_row()
        row.update(self._payer_fields(customer))
        row.update(payee_fields)
        row.update(self._cred_fields())
        row.update(self._product_fields(customer))
        row.update({
            "txnid": self.relationships.new_txnid(),
            "custrefno": self.relationships.new_custrefno(),
            "ts": format_ts(ts),
            "txndate": format_date(ts.date()),
            "asdt": format_ts(ts),
            "purpose": self._purpose_description(purposecode),
            "purposecode": purposecode,
            "initiationmode": initiationmode,
            "initiatedby": self.rng.choice(constants.INITIATED_BY_VALUES),
            "initiatorpsp": customer.payerpsp,
            "initiatorpsporgid": customer.payerpsporgid,
        })
        return row

    def generate_p2p(self, ts: Optional[datetime] = None) -> List[dict]:
        """One-off person-to-person payment."""
        customer = self.rng.choices(self.customers, cum_weights=self._customer_cum_weights_by_category["p2p"], k=1)[0]
        payee_customer = self.rng.choice(self.customers)
        while payee_customer.customer_id == customer.customer_id:
            payee_customer = self.rng.choice(self.customers)

        ts = ts or self._sample_ts_for_customer(customer, "DEFAULT")
        initiationmode = self._pick_initiation_mode()
        amount = self.growth.sample_p2p_amount(self._customer_ticket_multiplier(customer))

        row = self._new_financial_shared(customer, self._payee_p2p_fields(payee_customer), "00", initiationmode, ts)
        row["transaction_type"] = "P2P_PAYMENT"
        row["txntype"] = constants.TXN_TYPE_FINANCIAL
        row["txamount"] = amount
        row["payeeamt"] = amount

        outcome, note = self._resolve_final_outcome("P2P payment", amount=amount, ts=ts, payer_psp=customer.payerpsp, payer_bank=customer.payerbank, transaction_type="P2P_PAYMENT")
        row.update(self._outcome_fields(outcome, note))
        self.relationships.record_payment(customer, None, row["txnid"])
        return [row]

    def generate_p2m(self, ts: Optional[datetime] = None, merchant: Optional[MerchantRecord] = None) -> List[dict]:
        """One-off merchant (P2M) payment."""
        customer = self.rng.choices(self.customers, cum_weights=self._customer_cum_weights_by_category["merchant_payment"], k=1)[0]
        merchant = merchant or self._select_merchant_for_customer(customer, self._oneoff_merchant_cum_weights)
        if merchant.mcc in FOOD_SERVICE_MCCS:
            time_category = "LUNCH_DINNER"
        elif merchant.mcc in COMMUTE_MCCS:
            time_category = "COMMUTE"
        else:
            time_category = "OFFICE"
        weekend_boost = 1.8 if merchant.mcc in WEEKEND_SPIKE_MCCS else 1.0
        ts = ts or self._sample_ts_for_customer(customer, time_category, weekend_boost=weekend_boost)

        behavior = self.merchant_behavior.profile_for(merchant)
        purposecode = self._pick_purposecode_for_mcc(merchant.mcc)
        initiationmode = self._pick_initiation_mode()
        multiplier = self._customer_ticket_multiplier(customer) * (1.6 if behavior.high_value else 1.0)
        amount = self.growth.sample_amount(merchant.mcc, multiplier, merchant_id=merchant.merchant_id)

        row = self._new_financial_shared(customer, self._payee_merchant_fields(merchant), purposecode, initiationmode, ts)
        row["transaction_type"] = "MERCHANT_PAYMENT"
        row["txntype"] = constants.TXN_TYPE_FINANCIAL
        row["txamount"] = amount
        row["payeeamt"] = amount

        outcome, note = self._resolve_final_outcome(
            f"Merchant payment to {merchant.merchant_name}", amount=amount, ts=ts,
            payer_psp=customer.payerpsp, payer_bank=customer.payerbank,
            merchant_high_value=behavior.high_value,
            transaction_type="MERCHANT_PAYMENT", mcc=merchant.mcc,
        )
        row.update(self._outcome_fields(outcome, note))
        self.relationships.record_payment(customer, merchant, row["txnid"])

        if outcome.status == "SUCCESS":
            self._recent_payments.append(_RecentPayment(
                txnid=row["txnid"], customer=customer, merchant=merchant,
                amount=amount, ts=ts, purposecode=purposecode,
            ))
            if len(self._recent_payments) > self._MAX_RECENT_PAYMENTS:
                self._recent_payments.pop(0)
        return [row]

    def generate_qr(self, ts: Optional[datetime] = None) -> List[dict]:
        """QR-code initiated payment (merchant-biased, matching real UPI QR usage)."""
        is_merchant = self.rng.random() < 0.85
        if is_merchant:
            customer = self.rng.choices(self.customers, cum_weights=self._customer_cum_weights_by_category["qr"], k=1)[0]
            merchant = self._select_merchant_for_customer(customer, self._oneoff_merchant_cum_weights)
            if merchant.mcc in FOOD_SERVICE_MCCS:
                time_category = "LUNCH_DINNER"
            elif merchant.mcc in COMMUTE_MCCS:
                time_category = "COMMUTE"
            else:
                time_category = "EVENING_FOOD"
            weekend_boost = 1.8 if merchant.mcc in WEEKEND_SPIKE_MCCS else 1.0
            ts = ts or self._sample_ts_for_customer(customer, time_category, weekend_boost=weekend_boost)
            purposecode = self._pick_purposecode_for_mcc(merchant.mcc)
            initiationmode = self._pick_initiation_mode(qr=True)
            amount = self.growth.sample_amount(merchant.mcc, self._customer_ticket_multiplier(customer), merchant_id=merchant.merchant_id)
            row = self._new_financial_shared(customer, self._payee_merchant_fields(merchant), purposecode, initiationmode, ts)
            self.relationships.record_payment(customer, merchant, row["txnid"])
        else:
            customer = self.rng.choices(self.customers, cum_weights=self._customer_cum_weights_by_category["qr"], k=1)[0]
            payee = self.rng.choice(self.customers)
            while payee.customer_id == customer.customer_id:
                payee = self.rng.choice(self.customers)
            merchant = None
            ts = ts or self._sample_ts_for_customer(customer, "EVENING_FOOD")
            initiationmode = self._pick_initiation_mode(qr=True)
            amount = self.growth.sample_p2p_amount(self._customer_ticket_multiplier(customer))
            row = self._new_financial_shared(customer, self._payee_p2p_fields(payee), "00", initiationmode, ts)
            self.relationships.record_payment(customer, None, row["txnid"])

        row["transaction_type"] = "QR_PAYMENT"
        row["txntype"] = constants.TXN_TYPE_FINANCIAL
        row["txamount"] = amount
        row["payeeamt"] = amount
        outcome, note = self._resolve_final_outcome(
            "QR payment", amount=amount, ts=ts, payer_psp=customer.payerpsp, payer_bank=customer.payerbank,
            transaction_type="QR_PAYMENT", mcc=(merchant.mcc if merchant else None),
        )
        row.update(self._outcome_fields(outcome, note))
        return [row]

    def generate_bbps(self, ts: Optional[datetime] = None) -> List[dict]:
        """Bill payment routed via BBPS to a utility/telecom/insurance biller."""
        bbps_merchants = [m for m in self.merchants if m.mcc in ("4900", "4899", "4814", "6300")]
        pool = bbps_merchants or self.merchants
        # Even within the bill-payer pool, favor merchants whose archetype
        # actually leans BBPS (an electricity board over an occasional
        # BBPS-adjacent biller), rather than a uniform pick.
        pool_weights = [self.merchant_behavior.profile_for(m).bbps_share + 0.05 for m in pool]
        merchant = self.rng.choices(pool, weights=pool_weights, k=1)[0]
        customer = self.rng.choices(self.customers, cum_weights=self._customer_cum_weights_by_category["bbps"], k=1)[0]
        ts = ts or self._sample_ts_for_customer(customer, "OFFICE")

        purposecode = self._pick_purposecode_for_mcc(merchant.mcc)
        initiationmode = self._pick_initiation_mode(bbps=True)
        amount = self.growth.sample_amount(merchant.mcc, self._customer_ticket_multiplier(customer), merchant_id=merchant.merchant_id)

        row = self._new_financial_shared(customer, self._payee_merchant_fields(merchant), purposecode, initiationmode, ts)
        row["transaction_type"] = "BBPS_PAYMENT"
        row["txntype"] = constants.TXN_TYPE_FINANCIAL
        row["txamount"] = amount
        row["payeeamt"] = amount
        outcome, note = self._resolve_final_outcome(
            f"BBPS bill payment to {merchant.merchant_name}", amount=amount, ts=ts,
            payer_psp=customer.payerpsp, payer_bank=customer.payerbank,
            transaction_type="BBPS_PAYMENT", mcc=merchant.mcc,
        )
        row.update(self._outcome_fields(outcome, note))
        self.relationships.record_payment(customer, merchant, row["txnid"])
        return [row]

    def generate_international_payment(self, ts: Optional[datetime] = None) -> List[dict]:
        """Cross-border UPI payment (Global UPI / NIPL-style acceptance)."""
        customer = self.rng.choices(self.customers, cum_weights=self._customer_cum_weights, k=1)[0]
        merchant = self.rng.choices(self.merchants, cum_weights=self._merchant_cum_weights, k=1)[0]
        ts = ts or self.seasonality.sample_datetime_for_category("DEFAULT")

        purposecode = business_rules.get_purpose_code(merchant.mcc, "INTERNATIONAL_PAYMENT")
        initiationmode = self._pick_initiation_mode(international=True)
        amount = self.growth.sample_amount(merchant.mcc, self._customer_ticket_multiplier(customer) * 1.3, merchant_id=merchant.merchant_id)

        row = self._new_financial_shared(customer, self._payee_merchant_fields(merchant), purposecode, initiationmode, ts)
        row["transaction_type"] = "INTERNATIONAL_PAYMENT"
        row["txntype"] = constants.TXN_TYPE_FINANCIAL
        row["txamount"] = amount
        row["payeeamt"] = amount
        outcome, note = self._resolve_final_outcome(
            "International payment", amount=amount, ts=ts,
            payer_psp=customer.payerpsp, payer_bank=customer.payerbank,
            transaction_type="INTERNATIONAL_PAYMENT", mcc=merchant.mcc,
        )
        row.update(self._outcome_fields(outcome, note))
        self.relationships.record_payment(customer, merchant, row["txnid"])
        return [row]

    def generate_balance_check(self, ts: Optional[datetime] = None) -> List[dict]:
        """Non-financial balance-check event."""
        customer = self.rng.choices(self.customers, cum_weights=self._customer_cum_weights, k=1)[0]
        ts = ts or self.seasonality.sample_datetime_for_category("DEFAULT")
        initiationmode = self._pick_initiation_mode()

        row = self._base_row()
        row.update(self._payer_fields(customer))
        row.update(self._cred_fields())
        row.update(self._product_fields(customer))
        row.update({
            "transaction_type": "BALANCE_CHECK",
            "txnid": self.relationships.new_txnid(),
            "txntype": constants.TXN_TYPE_NON_FINANCIAL,
            "custrefno": self.relationships.new_custrefno(),
            "ts": format_ts(ts),
            "txndate": format_date(ts.date()),
            "asdt": format_ts(ts),
            "purpose": self._purpose_description("00"),
            "purposecode": "00",
            "initiationmode": initiationmode,
            "initiatedby": "PAYER",
            "initiatorpsp": customer.payerpsp,
            "initiatorpsporgid": customer.payerpsporgid,
        })
        outcome, note = self._resolve_final_outcome("Balance check", transaction_type="BALANCE_CHECK")
        row.update(self._outcome_fields(outcome, note))
        return [row]

    def generate_collect(self, ts: Optional[datetime] = None) -> List[dict]:
        """Collect payment: the payee raises a request and the payer either
        approves (debit happens) or declines it. Modeled as ONE row — a
        single completed business action from the customer's point of
        view — rather than a linked Collect-Request/Collect-Payment
        protocol pair."""
        is_merchant_collect = self.rng.random() < 0.6

        if is_merchant_collect:
            customer = self.rng.choices(
                self.customers, cum_weights=self._customer_cum_weights_by_category["merchant_payment"], k=1
            )[0]
            merchant = self.rng.choices(self.merchants, cum_weights=self._oneoff_merchant_cum_weights, k=1)[0]
            payee_fields = self._payee_merchant_fields(merchant)
            purposecode = self._pick_purposecode_for_mcc(merchant.mcc)
            amount = self.growth.sample_amount(merchant.mcc, self._customer_ticket_multiplier(customer), merchant_id=merchant.merchant_id)
            initiator_psp = merchant.payeepsp
            initiator_orgid = merchant.payeepsporgid
        else:
            merchant = None
            customer = self.rng.choices(self.customers, cum_weights=self._customer_cum_weights_by_category["p2p"], k=1)[0]
            payee = self.rng.choice(self.customers)
            while payee.customer_id == customer.customer_id:
                payee = self.rng.choice(self.customers)
            payee_fields = self._payee_p2p_fields(payee)
            purposecode = "00"
            amount = self.growth.sample_p2p_amount(self._customer_ticket_multiplier(customer))
            initiator_psp = payee.payerpsp
            initiator_orgid = payee.payerpsporgid

        ts = ts or self._sample_ts_for_customer(customer, "OFFICE")
        initiationmode = self._pick_initiation_mode()

        row = self._new_financial_shared(customer, payee_fields, purposecode, initiationmode, ts)
        row["transaction_type"] = "COLLECT_PAYMENT"
        row["txntype"] = constants.TXN_TYPE_FINANCIAL
        row["txamount"] = amount
        row["payeeamt"] = amount
        row["initiatedby"] = "PAYEE"
        row["initiatorpsp"] = initiator_psp
        row["initiatorpsporgid"] = initiator_orgid

        approved = self.rng.random() < business_rules.get_default_success_rate("COLLECT_PAYMENT", fallback=self.config.SUCCESS_RATE)
        if approved:
            outcome, note = self._resolve_final_outcome(
                "Collect request approved by payer", amount=amount, ts=ts,
                payer_psp=customer.payerpsp, payer_bank=customer.payerbank,
                transaction_type="COLLECT_PAYMENT", mcc=(merchant.mcc if merchant else None),
            )
            row.update(self._outcome_fields(outcome, note))
            self.relationships.record_payment(customer, merchant, row["txnid"])
        else:
            outcome = self._collect_not_approved_outcome()
            row.update(self._outcome_fields(outcome, "Collect request declined by payer"))
        return [row]

    def generate_refund(self, ts: Optional[datetime] = None) -> List[dict]:
        """Merchant refund against a previously successful merchant payment.
        Candidates are weighted by business_rules.get_refund_probability so
        e-commerce/retail merchants (Amazon-like) get refunded noticeably
        more often than a restaurant or utility biller, matching real
        return/cancellation patterns rather than a uniform pick."""
        if not self._recent_payments:
            return []
        weights = [business_rules.get_refund_probability(p.merchant.mcc) + 0.001 for p in self._recent_payments]
        original = self.rng.choices(self._recent_payments, weights=weights, k=1)[0]
        ts = ts or (original.ts + timedelta(hours=self.rng.randint(
            self.config.REFUND_LAG_MIN_HOURS, self.config.REFUND_LAG_MAX_HOURS
        )))

        row = self._new_financial_shared(
            original.customer, self._payee_merchant_fields(original.merchant),
            original.purposecode, self._pick_initiation_mode(), ts,
        )
        row["transaction_type"] = "MERCHANT_REFUND"
        row["txntype"] = constants.TXN_TYPE_FINANCIAL
        row["txamount"] = original.amount
        row["payeeamt"] = original.amount
        row["initiatedby"] = "PAYEE"
        row["initiatorpsp"] = original.merchant.payeepsp
        row["initiatorpsporgid"] = original.merchant.payeepsporgid

        outcome = OutcomeResult(
            status="SUCCESS", responsecode=constants.SUCCESS_RESPONSE_CODE,
            responseresult="SUCCESS", errorcode=None, failure_reason=None,
            retryable=False, currstatusdesc="Amount refunded to payer",
        )
        row.update(self._outcome_fields(outcome, f"Refund for original txn {original.txnid}"))
        return [row]

    # ------------------------------------------------------------------
    # Mandate lifecycle business events
    # ------------------------------------------------------------------
    def generate_autopay_registration(self, ts: Optional[datetime] = None) -> tuple[List[dict], Optional[MandateContext]]:
        """Register a new mandate. Prefers a merchant this customer
        already has a history with (their own favourites list, filtered
        to autopay-eligible MCCs per business_rules.is_autopay_eligible)
        so a subscription plausibly follows from habits already visible
        in their one-off payments (Task 2 customer continuity) — e.g. a
        customer who already pays Netflix as MERCHANT_PAYMENT is far more
        likely to be the one who sets up its mandate. Falls back to the
        global AutoPay-archetype-weighted pool (Task 3 merchant
        personality) when the customer has no eligible favourite yet."""
        customer = self.rng.choice(self._mandate_customers)
        pref = self.relationships.preference_for(customer)
        eligible_favorites = []
        if pref:
            eligible_favorites = [
                self._merchant_by_id[mid] for mid in pref.favorite_merchant_ids
                if mid in self._merchant_by_id and business_rules.is_autopay_eligible(self._merchant_by_id[mid].mcc)
            ]
        if eligible_favorites and self.rng.random() < 0.6:
            merchant = self.rng.choice(eligible_favorites)
        else:
            merchant = self.rng.choices(self.merchants, cum_weights=self._autopay_merchant_cum_weights, k=1)[0]
        ts = ts or self.seasonality.sample_datetime_for_category("OFFICE")

        purposecode = self._pick_recurring_purposecode_for_mcc(merchant.mcc)
        initiationmode = self._pick_initiation_mode(mandate_related=True)
        recurrencepattern = self.rng.choice(constants.RECURRENCE_PATTERNS)
        revokable = self.rng.choices(["Y", "N"], weights=[85, 15], k=1)[0]

        validitystart = ts.date()
        validity_days = self.rng.randint(90, 365)
        validityend = validitystart + timedelta(days=validity_days)

        ctx = self.relationships.new_umn(
            customer=customer, merchant=merchant, purposecode=purposecode,
            initiationmode=initiationmode, recurrencepattern=recurrencepattern,
            validitystart=validitystart, validityend=validityend, revokable=revokable,
        )

        row = self._base_row()
        row.update(self._payer_fields(customer))
        row.update(self._payee_merchant_fields(merchant))
        row.update(self._cred_fields())
        row.update(self._product_fields(customer))
        row.update({
            "transaction_type": "MANDATE_REGISTRATION",
            "txnid": self.relationships.new_txnid(),
            "txntype": constants.TXN_TYPE_NON_FINANCIAL,
            "custrefno": self.relationships.new_custrefno(),
            "ts": format_ts(ts),
            "txndate": format_date(ts.date()),
            "asdt": format_ts(ts),
            "umn": ctx.umn,
            "mandateoperation": "CREATE",
            "validitystart": format_date(validitystart),
            "validityend": format_date(validityend),
            "recurrencepattern": recurrencepattern,
            "revokable": revokable,
            "purpose": self._purpose_description(purposecode),
            "purposecode": purposecode,
            "initiationmode": initiationmode,
            "initiatedby": "PAYER",
            "initiatorpsp": customer.payerpsp,
            "initiatorpsporgid": customer.payerpsporgid,
        })

        outcome, note = self._resolve_final_outcome("Mandate registration", transaction_type="MANDATE_REGISTRATION", mcc=merchant.mcc)
        row.update(self._outcome_fields(outcome, note))

        if outcome.status != "SUCCESS":
            self.relationships.apply_mandate_transition(ctx, "FAILED")
            return [row], None

        ctx.next_due_date = validitystart + timedelta(
            days=self.rng.randint(self.config.MANDATE_FIRST_EXECUTION_MIN_DAYS,
                                   self.config.MANDATE_FIRST_EXECUTION_MAX_DAYS)
        )
        return [row], ctx

    def generate_mandate_update(self, ctx: MandateContext, ts: Optional[datetime] = None) -> List[dict]:
        """Update an existing mandate (e.g. amount/validity change)."""
        ts = ts or self.seasonality.sample_datetime_for_category("OFFICE")
        row = self._mandate_admin_row(ctx, "MANDATE_UPDATE", "UPDATE", ts)
        applied = self.relationships.apply_mandate_transition(ctx, "UPDATED")
        outcome, note = (self._resolve_final_outcome("Mandate update", transaction_type="MANDATE_UPDATE", mcc=ctx.merchant.mcc) if applied
                         else (self.failure.decide_mandate_failure("MANDATE_REVOKED"), "Mandate update rejected: invalid state"))
        row.update(self._outcome_fields(outcome, note))
        return [row]

    def generate_pause(self, ctx: MandateContext, ts: Optional[datetime] = None) -> List[dict]:
        ts = ts or self.seasonality.sample_datetime_for_category("OFFICE")
        row = self._mandate_admin_row(ctx, "MANDATE_PAUSE", "PAUSE", ts)
        applied = self.relationships.apply_mandate_transition(ctx, "PAUSED")
        outcome, note = (self._resolve_final_outcome("Mandate paused", transaction_type="MANDATE_PAUSE", mcc=ctx.merchant.mcc) if applied
                         else (self.failure.decide_mandate_failure("MANDATE_REVOKED"), "Pause rejected: invalid state"))
        row.update(self._outcome_fields(outcome, note))
        return [row]

    def generate_resume(self, ctx: MandateContext, ts: Optional[datetime] = None) -> List[dict]:
        ts = ts or self.seasonality.sample_datetime_for_category("OFFICE")
        row = self._mandate_admin_row(ctx, "MANDATE_RESUME", "UNPAUSE", ts)
        applied = self.relationships.apply_mandate_transition(ctx, "ACTIVE")
        outcome, note = (self._resolve_final_outcome("Mandate resumed", transaction_type="MANDATE_RESUME", mcc=ctx.merchant.mcc) if applied
                         else (self.failure.decide_mandate_failure("MANDATE_REVOKED"), "Resume rejected: invalid state"))
        row.update(self._outcome_fields(outcome, note))
        if applied:
            ctx.next_due_date = ts.date() + timedelta(
                days=self.rng.randint(self.config.MANDATE_CYCLE_GAP_MIN_DAYS, self.config.MANDATE_CYCLE_GAP_MAX_DAYS)
            )
        return [row]

    def generate_revoke(self, ctx: MandateContext, ts: Optional[datetime] = None) -> List[dict]:
        ts = ts or self.seasonality.sample_datetime_for_category("OFFICE")
        row = self._mandate_admin_row(ctx, "MANDATE_REVOKE", "REVOKE", ts)
        applied = self.relationships.apply_mandate_transition(ctx, "REVOKED")
        outcome, note = (self._resolve_final_outcome("Mandate revoked", transaction_type="MANDATE_REVOKE", mcc=ctx.merchant.mcc) if applied
                         else (self.failure.decide_mandate_failure("MANDATE_REVOKED"), "Revoke rejected: invalid state"))
        row.update(self._outcome_fields(outcome, note))
        return [row]

    def _mandate_admin_row(self, ctx: MandateContext, transaction_type: str, mandateoperation: str, ts: datetime) -> dict:
        row = self._base_row()
        row.update(self._payer_fields(ctx.customer))
        row.update(self._payee_merchant_fields(ctx.merchant))
        row.update(self._cred_fields())
        row.update(self._product_fields(ctx.customer))
        row.update({
            "transaction_type": transaction_type,
            "txnid": self.relationships.new_txnid(),
            "txntype": constants.TXN_TYPE_NON_FINANCIAL,
            "custrefno": self.relationships.new_custrefno(),
            "ts": format_ts(ts),
            "txndate": format_date(ts.date()),
            "asdt": format_ts(ts),
            "umn": ctx.umn,
            "mandateoperation": mandateoperation,
            "validitystart": format_date(ctx.validitystart),
            "validityend": format_date(ctx.validityend),
            "recurrencepattern": ctx.recurrencepattern,
            "revokable": ctx.revokable,
            "purpose": self._purpose_description(ctx.purposecode),
            "purposecode": ctx.purposecode,
            "initiationmode": ctx.initiationmode,
            "initiatedby": "PAYER",
            "initiatorpsp": ctx.customer.payerpsp,
            "initiatorpsporgid": ctx.customer.payerpsporgid,
        })
        return row

    def generate_autopay_cycle(self, ctx: MandateContext, due_date: date) -> List[dict]:
        """One AutoPay execution cycle for an active mandate (the pre-debit
        notification lead time is modeled internally for timing realism but
        does not emit its own row), with a distinct AUTOPAY_RETRY row
        emitted if the first attempt fails and is retryable (spread across
        real time, not the same instant)."""
        rows: List[dict] = []
        if not ctx.is_executable():
            return rows

        pdn_ts = datetime.combine(due_date, datetime.min.time()) + timedelta(
            hours=self.rng.randint(6, 20), minutes=self.rng.randint(0, 59)
        )
        umnexects = pdn_ts + timedelta(hours=self.rng.randint(
            self.config.PDN_LEAD_HOURS_MIN, self.config.PDN_LEAD_HOURS_MAX
        ))
        seqnum = ctx.take_seqnum()

        def mandate_cycle_row(transaction_type: str, ts: datetime, txntype: str) -> dict:
            row = self._base_row()
            row.update(self._payer_fields(ctx.customer))
            row.update(self._payee_merchant_fields(ctx.merchant))
            row.update(self._cred_fields())
            row.update(self._product_fields(ctx.customer))
            row.update({
                "transaction_type": transaction_type,
                "txnid": self.relationships.new_txnid(),
                "txntype": txntype,
                "custrefno": self.relationships.new_custrefno(),
                "ts": format_ts(ts),
                "txndate": format_date(ts.date()),
                "asdt": format_ts(ts),
                "umn": ctx.umn,
                "payerseqnum": seqnum,
                "validitystart": format_date(ctx.validitystart),
                "validityend": format_date(ctx.validityend),
                "recurrencepattern": ctx.recurrencepattern,
                "umnexects": format_ts(umnexects),
                "revokable": ctx.revokable,
                "purpose": self._purpose_description(ctx.purposecode),
                "purposecode": ctx.purposecode,
                "initiationmode": ctx.initiationmode,
                "initiatedby": "PAYEE",
                "initiatorpsp": ctx.merchant.payeepsp,
                "initiatorpsporgid": ctx.merchant.payeepsporgid,
            })
            return row

        # NOTE: the pre-debit notification lead time (pdn_ts -> umnexects) is
        # still modeled since it drives a realistic gap between a mandate
        # becoming due and the actual debit, but the notification itself is
        # a protocol/messaging step, not something the customer "did" — so
        # no standalone PDN row is emitted. AUTOPAY_EXECUTION is the single
        # customer-facing business transaction for this cycle.

        # --- AutoPay execution (financial), at/after umnexects --------------
        exec_ts = umnexects + timedelta(minutes=self.rng.randint(1, 45))
        behavior = self.merchant_behavior.profile_for(ctx.merchant)
        amount = self.growth.sample_amount(
            ctx.merchant.mcc, self._customer_ticket_multiplier(ctx.customer) * (1.4 if behavior.high_value else 1.0),
            merchant_id=ctx.merchant.merchant_id,
        )

        exec_row = mandate_cycle_row("AUTOPAY_EXECUTION", exec_ts, constants.TXN_TYPE_FINANCIAL)
        exec_row["txamount"] = amount
        exec_row["payeeamt"] = amount
        exec_outcome = self.failure.decide_initial_outcome(
            amount=amount, is_peak_hour=self.seasonality.is_peak_hour(exec_ts.hour),
            payer_psp=ctx.customer.payerpsp, payer_bank=ctx.customer.payerbank,
            merchant_high_value=behavior.high_value, transaction_type="AUTOPAY_EXECUTION",
        )
        exec_row.update(self._outcome_fields(exec_outcome, "AutoPay execution attempt 1"))
        rows.append(exec_row)
        ctx.total_executions += 1

        attempt = 1
        current_outcome = exec_outcome
        retry_ts = exec_ts
        retry_probability = business_rules.get_retry_probability("AUTOPAY_RETRY", ctx.merchant.mcc)
        while (current_outcome.retryable and attempt <= self.config.MAX_RETRY_ATTEMPTS
               and self.rng.random() < retry_probability):
            attempt += 1
            retry_ts = retry_ts + timedelta(minutes=self.rng.randint(
                self.config.RETRY_DELAY_MIN_MINUTES, self.config.RETRY_DELAY_MAX_MINUTES
            ))
            retry_row = mandate_cycle_row("AUTOPAY_RETRY", retry_ts, constants.TXN_TYPE_FINANCIAL)
            retry_row["txamount"] = amount
            retry_row["payeeamt"] = amount
            current_outcome = self.failure.decide_retry_outcome(attempt=attempt)
            retry_row.update(self._outcome_fields(current_outcome, f"AutoPay retry attempt {attempt}"))
            rows.append(retry_row)
            self.relationships.record_retry(exec_row["txnid"], attempt, retry_ts, current_outcome.status)

        if current_outcome.status == "SUCCESS":
            ctx.consecutive_failures = 0
            self.relationships.record_payment(ctx.customer, ctx.merchant, exec_row["txnid"])
        else:
            ctx.total_failures += 1
            ctx.consecutive_failures += 1
        return rows

    # ------------------------------------------------------------------
    # Batch orchestration
    # ------------------------------------------------------------------
    def _allocate_counts(self, target_rows: int) -> dict:
        dist = self.config.BUSINESS_EVENT_DISTRIBUTION
        total_pct = sum(dist.values())
        return {k: max(0, round(target_rows * (v / total_pct))) for k, v in dist.items()}

    def _advance_mandate_cycle(self, ctx: MandateContext) -> tuple[List[dict], bool]:
        """Advance one mandate by exactly one due-date step: apply any
        inline admin-state decision (revoke/update/pause/resume) first,
        then an execution if the mandate is still active. This is the
        resumable, one-step-at-a-time version of what used to be a nested
        loop that ran a mandate's entire future timeline in one go — so
        the main batch loop can interleave mandate steps with everything
        else instead of generating them in a block."""
        rows: List[dict] = []
        due = ctx.next_due_date
        if due is None or due > self.config.END_DATE:
            return rows, False

        remaining = getattr(ctx, "_remaining_cycles", None)
        if remaining is None:
            remaining = self.rng.randint(
                self.config.MIN_EXECUTIONS_PER_MANDATE, self.config.MAX_EXECUTIONS_PER_MANDATE
            )
        if remaining <= 0:
            return rows, False

        cycle_ts = datetime.combine(due, datetime.min.time())

        if ctx.state in ("ACTIVE", "UPDATED") and self._admin_rows_generated < self._admin_rows_budget:
            if self.rng.random() < self.config.MANDATE_REVOKE_PROBABILITY:
                rows.extend(self.generate_revoke(ctx, cycle_ts - timedelta(days=1)))
                self._admin_rows_generated += 1
                return rows, False
            if self.rng.random() < self.config.MANDATE_UPDATE_PROBABILITY:
                rows.extend(self.generate_mandate_update(ctx, cycle_ts - timedelta(hours=6)))
                self._admin_rows_generated += 1
            if self.rng.random() < self.config.MANDATE_PAUSE_PROBABILITY:
                rows.extend(self.generate_pause(ctx, cycle_ts - timedelta(hours=2)))
                self._admin_rows_generated += 1

        if ctx.state == "PAUSED":
            if self.rng.random() < self.config.MANDATE_RESUME_PROBABILITY:
                rows.extend(self.generate_resume(ctx, cycle_ts))
                self._admin_rows_generated += 1
            else:
                # Stays paused this cycle; try again at the next due date.
                # Some mandates therefore remain paused for a long time, or
                # permanently, exactly as real mandates do.
                ctx.next_due_date = due + timedelta(days=self.rng.randint(
                    self.config.MANDATE_CYCLE_GAP_MIN_DAYS, self.config.MANDATE_CYCLE_GAP_MAX_DAYS
                ))
                ctx._remaining_cycles = remaining
                return rows, True

        if not ctx.is_executable():
            ctx._remaining_cycles = 0
            return rows, False

        cycle_rows = self.generate_autopay_cycle(ctx, due)
        rows.extend(cycle_rows)

        next_due = due + timedelta(days=self.rng.randint(
            self.config.MANDATE_CYCLE_GAP_MIN_DAYS, self.config.MANDATE_CYCLE_GAP_MAX_DAYS
        ))
        ctx.next_due_date = next_due
        ctx._remaining_cycles = remaining - 1
        has_more = ctx._remaining_cycles > 0 and next_due <= self.config.END_DATE
        return rows, has_more

    def generate_batch(self, target_rows: int) -> List[dict]:
        """Generate a batch of business-event rows sized close to target_rows.

        Transactions are generated one at a time in randomly interleaved
        order (a recipe of category labels is built to the configured
        distribution, then shuffled) rather than in category blocks, so
        the raw generation order doesn't group "all mandates, then all
        merchant payments, then all P2P...". Each mandate's execution
        cycle advances one due-date step per turn through
        _advance_mandate_cycle, re-queuing itself for a later turn if it
        still has cycles left — some mandates never execute, expire, stay
        paused indefinitely, or get revoked, exactly like real mandates.
        The full batch is sorted by timestamp before being returned, so
        the final CSV reads as natural, chronologically mixed daily
        traffic regardless of internal generation order.
        """
        rows: List[dict] = []
        counts = self._allocate_counts(target_rows)

        self._admin_rows_generated = 0
        self._admin_rows_budget = counts.get("MANDATE_UPDATE", 0) + counts.get("MANDATE_PAUSE_RESUME_REVOKE", 0)

        # Build the interleaving recipe: one entry per business transaction
        # to generate. MANDATE_UPDATE/PAUSE_RESUME_REVOKE aren't separate
        # recipe entries — they're decided inline as part of a mandate's
        # own cycle (see _advance_mandate_cycle), governed by the budget
        # above.
        recipe: List[str] = []
        for category in ("MERCHANT_PAYMENT", "P2P_PAYMENT", "QR_PAYMENT", "BBPS_PAYMENT",
                          "COLLECT_PAYMENT", "MERCHANT_REFUND", "MANDATE_REGISTRATION",
                          "AUTOPAY_EXECUTION"):
            recipe.extend([category] * counts.get(category, 0))
        self.rng.shuffle(recipe)

        pending_mandates: List[MandateContext] = []

        for category in recipe:
            if category == "MANDATE_REGISTRATION":
                reg_rows, ctx = self.generate_autopay_registration()
                rows.extend(reg_rows)
                if ctx is not None and ctx.next_due_date is not None:
                    pending_mandates.append(ctx)
            elif category == "AUTOPAY_EXECUTION":
                if pending_mandates:
                    ctx = pending_mandates.pop(self.rng.randrange(len(pending_mandates)))
                    cycle_rows, still_pending = self._advance_mandate_cycle(ctx)
                    rows.extend(cycle_rows)
                    if still_pending:
                        pending_mandates.append(ctx)
                    if not cycle_rows:
                        # This mandate wasn't actually due yet or has no
                        # more cycles; don't waste the recipe slot.
                        rows.extend(self.generate_p2m())
                else:
                    rows.extend(self.generate_p2m())
            elif category == "MERCHANT_PAYMENT":
                rows.extend(self.generate_p2m())
            elif category == "P2P_PAYMENT":
                rows.extend(self.generate_p2p())
            elif category == "QR_PAYMENT":
                rows.extend(self.generate_qr())
            elif category == "BBPS_PAYMENT":
                rows.extend(self.generate_bbps())
            elif category == "COLLECT_PAYMENT":
                rows.extend(self.generate_collect())
            elif category == "MERCHANT_REFUND":
                refund_rows = self.generate_refund()
                rows.extend(refund_rows if refund_rows else self.generate_p2m())

        # Drain any mandates still awaiting further cycles so a mandate
        # registered late in the recipe still gets a fair chance to
        # execute within the date range (bounded attempts to avoid a
        # runaway loop on a mandate that will never come due in range).
        drain_budget = len(pending_mandates) * 6
        while pending_mandates and drain_budget > 0:
            ctx = pending_mandates.pop(0)
            cycle_rows, still_pending = self._advance_mandate_cycle(ctx)
            rows.extend(cycle_rows)
            if still_pending:
                pending_mandates.append(ctx)
            drain_budget -= 1

        # Top up any shortfall with additional merchant/P2P payments.
        while len(rows) < target_rows:
            rows.extend(self.generate_p2m() if self.rng.random() < 0.6 else self.generate_p2p())

        rows.sort(key=lambda r: r["ts"])
        return rows


if __name__ == "__main__":
    from config import DEFAULT_CONFIG
    from customer_generator import CustomerGenerator
    from master_data_generator import MasterDataGenerator
    from merchant_generator import MerchantGenerator

    cfg = DEFAULT_CONFIG
    mdg = MasterDataGenerator(cfg)
    master_data = mdg.write_all(cfg.master_path())
    customers = CustomerGenerator(cfg, master_data["bank_master"], master_data["psp_master"]).write(cfg.master_path())
    merchants = MerchantGenerator(cfg, master_data["bank_master"], master_data["psp_master"]).write(cfg.master_path())

    tg = TransactionGenerator(cfg, master_data["bank_master"], master_data["psp_master"], customers, merchants)
    batch = tg.generate_batch(1000)
    print(f"Generated {len(batch)} rows")
    from collections import Counter
    print(Counter(r["transaction_type"] for r in batch))
