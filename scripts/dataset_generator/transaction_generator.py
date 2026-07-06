"""
transaction_generator.py

Produces rows for the fact_upi_transactions table, strictly following:
    - the 12-API lifecycle and request/response pairing
    - UMN generation and payerseqnum increment rules
    - merchant/customer/PSP/bank consistency
    - purpose <-> MCC compatibility
    - timestamp ordering within a lifecycle
    - response/error code rules

Two transaction patterns are produced:
    1. Mandate lifecycle (AutoPay): full Req/RespMandate -> Req/RespAuthMandate
       -> Req/RespMandateConfirmation, followed by one or more recurring
       executions of ReqValCust/RespValCust (PDN) -> ReqPay/RespPay.
    2. One-off payment: ReqPay -> RespPay only (P2P or P2M, non-mandate).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from random import Random
from typing import List, Optional

import constants
from config import GeneratorConfig
from customer_generator import CustomerRecord
from failure_simulator import FailureSimulator
from growth_simulator import GrowthSimulator
from master_data_generator import BankRecord, PspRecord
from merchant_generator import MerchantRecord
from relationship_generator import MandateContext, RelationshipManager
from seasonality_simulator import SeasonalitySimulator
from utils import derive_sub_seed, format_date, format_ts, seeded_random


@dataclass
class _EntityLookup:
    bank_by_name: dict
    psp_by_name: dict


class TransactionGenerator:
    """Generates a full batch of fact_upi_transactions rows."""

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

        self._lookup = _EntityLookup(
            bank_by_name={b.bank_name: b for b in banks},
            psp_by_name={p.psp_name: p for p in psps},
        )
        self._customer_weights = self.growth.entity_market_share_weights(len(customers))
        self._merchant_weights = self.growth.merchant_selection_weights(merchants)

        # Mandate-eligible customers: a fixed subset, chosen deterministically,
        # so "who holds mandates" doesn't churn between batches with same seed.
        n_mandate_customers = max(1, int(len(customers) * config.MANDATE_CUSTOMER_SHARE))
        self._mandate_customers = self.rng.sample(customers, k=min(n_mandate_customers, len(customers)))

    # ------------------------------------------------------------------
    # Shared row construction
    # ------------------------------------------------------------------
    def _base_row(self) -> dict:
        """Return a dict pre-populated with None for every schema column."""
        return {field: None for field in constants.FACT_TABLE_FIELDS}

    def _payer_fields(self, customer: CustomerRecord) -> dict:
        bank = self._lookup.bank_by_name.get(customer.payerbank)
        psp = self._lookup.psp_by_name.get(customer.payerpsp)
        payer_psp_bank = psp.sponsor_bank if psp else customer.payerbank
        return {
            "payeraddress": customer.payeraddress,
            "payerbank": customer.payerbank,
            "payerpsp": customer.payerpsp,
            "payerpsporgid": customer.payerpsporgid,
            "payer_psp_bank": payer_psp_bank,
            "remitter_bank": customer.remitter_bank,
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
            "beneficiary_bank": merchant.payeebank,
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
            "beneficiary_bank": payee_customer.payerbank,
        }

    def _pick_purposecode_for_mcc(self, mcc: str) -> str:
        candidates = constants.MCC_TO_PURPOSE_CODES.get(mcc, ("00",))
        return self.rng.choice(candidates)

    def _pick_recurring_purposecode_for_mcc(self, mcc: str) -> str:
        candidates = [
            p for p in constants.MCC_TO_PURPOSE_CODES.get(mcc, ("00",))
            if p in constants.RECURRING_PURPOSE_CODES
        ]
        if not candidates:
            candidates = list(constants.RECURRING_PURPOSE_CODES)
        return self.rng.choice(candidates)

    def _purpose_description(self, purposecode: str) -> str:
        for p in constants.PURPOSE_CODES:
            if p["purposecode"] == purposecode:
                return p["purpose"]
        return "Default"

    def _pick_initiation_mode(self, mandate_related: bool) -> str:
        if mandate_related:
            return self.rng.choice(constants.MANDATE_CAPABLE_INITIATION_MODES)
        pool = [m["initiationmode"] for m in constants.INITIATION_MODES
                if m["initiationmode"] not in constants.MANDATE_CAPABLE_INITIATION_MODES]
        return self.rng.choice(pool)

    def _cred_fields(self) -> dict:
        cred_type = self.rng.choice(constants.CRED_TYPES)
        cred_subtype = self.rng.choice(constants.CRED_SUBTYPES[cred_type])
        secondary = self.rng.random() < 0.1
        if secondary:
            cred_type_2 = self.rng.choice(constants.CRED_TYPES)
            cred_subtype_2 = self.rng.choice(constants.CRED_SUBTYPES[cred_type_2])
        else:
            cred_type_2 = None
            cred_subtype_2 = None
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

    def _response_fields(self, is_terminal_financial: bool) -> dict:
        outcome = self.failure.decide_outcome(is_terminal_financial)
        return {
            "responsecode": outcome.responsecode,
            "responseresult": outcome.responseresult,
            "errorcode": outcome.errorcode,
            "respcd": outcome.responsecode,
            "result": outcome.responseresult,
            "currstatusdesc": outcome.currstatusdesc,
        }, outcome

    # ------------------------------------------------------------------
    # One-off (non-mandate) payment lifecycle: ReqPay -> RespPay
    # ------------------------------------------------------------------
    def _generate_oneoff_payment(self, ts_start: datetime) -> List[dict]:
        rows: List[dict] = []
        customer = self.rng.choices(self.customers, weights=self._customer_weights, k=1)[0]

        is_p2m = self.rng.random() < 0.75
        if is_p2m:
            merchant = self.rng.choices(self.merchants, weights=self._merchant_weights, k=1)[0]
            payee_fields = self._payee_merchant_fields(merchant)
            purposecode = self._pick_purposecode_for_mcc(merchant.mcc)
            amount = self.growth.sample_amount(merchant.mcc)
        else:
            payee_customer = self.rng.choice(self.customers)
            while payee_customer.customer_id == customer.customer_id:
                payee_customer = self.rng.choice(self.customers)
            payee_fields = self._payee_p2p_fields(payee_customer)
            purposecode = "00"
            amount = self.growth.sample_p2p_amount()

        initiationmode = self._pick_initiation_mode(mandate_related=False)
        txnid = self.relationships.new_txnid()
        custrefno = self.relationships.new_custrefno()

        shared = self._base_row()
        shared.update(self._payer_fields(customer))
        shared.update(payee_fields)
        shared.update(self._cred_fields())
        shared.update(self._product_fields(customer))
        shared.update(
            {
                "txnid": txnid,
                "txntype": constants.TXN_TYPE_FINANCIAL,
                "custrefno": custrefno,
                "umn": None,
                "payerseqnum": None,
                "mandateoperation": None,
                "validitystart": None,
                "validityend": None,
                "recurrencepattern": None,
                "umnexects": None,
                "revokable": None,
                "txamount": amount,
                "payeeamt": amount,
                "purpose": self._purpose_description(purposecode),
                "purposecode": purposecode,
                "initiationmode": initiationmode,
                "initmode": initiationmode,
                "initiatedby": self.rng.choice(constants.INITIATED_BY_VALUES),
                "initiatorpsp": customer.payerpsp,
                "initiatorpsporgid": customer.payerpsporgid,
                "txnnote": None,
                "asdt": format_ts(ts_start),
            }
        )

        req_ts = ts_start
        row_req = dict(shared)
        row_req.update(
            {
                "apiname": "ReqPay",
                "ts": format_ts(req_ts),
                "txndate": format_date(req_ts.date()),
                "responsecode": None,
                "responseresult": None,
                "errorcode": None,
                "respcd": None,
                "result": None,
                "currstatusdesc": constants.CURR_STATUS_DESCRIPTIONS["PENDING"],
            }
        )
        rows.append(row_req)

        resp_ts = req_ts + timedelta(seconds=self.rng.randint(1, 8))
        response_fields, _ = self._response_fields(is_terminal_financial=True)
        row_resp = dict(shared)
        row_resp.update(
            {
                "apiname": "RespPay",
                "ts": format_ts(resp_ts),
                "txndate": format_date(resp_ts.date()),
            }
        )
        row_resp.update(response_fields)
        rows.append(row_resp)
        return rows

    # ------------------------------------------------------------------
    # Mandate lifecycle: creation + N recurring executions
    # ------------------------------------------------------------------
    def _create_mandate(self, ts_start: datetime) -> tuple[List[dict], MandateContext]:
        rows: List[dict] = []
        customer = self.rng.choice(self._mandate_customers)
        merchant = self.rng.choices(self.merchants, weights=self._merchant_weights, k=1)[0]

        purposecode = self._pick_recurring_purposecode_for_mcc(merchant.mcc)
        initiationmode = self._pick_initiation_mode(mandate_related=True)
        recurrencepattern = self.rng.choice(constants.RECURRENCE_PATTERNS)
        mandateoperation = "CREATE"
        revokable = self.rng.choices(["Y", "N"], weights=[85, 15], k=1)[0]

        validitystart = ts_start.date()
        validity_days = self.rng.randint(90, 365)
        validityend = validitystart + timedelta(days=validity_days)
        if validityend > self.config.END_DATE:
            validityend = self.config.END_DATE + timedelta(days=validity_days)

        mandate_ctx = self.relationships.new_umn(
            customer=customer,
            merchant=merchant,
            purposecode=purposecode,
            initiationmode=initiationmode,
            recurrencepattern=recurrencepattern,
            mandateoperation=mandateoperation,
            validitystart=validitystart,
            validityend=validityend,
            revokable=revokable,
        )

        shared = self._base_row()
        shared.update(self._payer_fields(customer))
        shared.update(self._payee_merchant_fields(merchant))
        shared.update(self._cred_fields())
        shared.update(self._product_fields(customer))
        shared.update(
            {
                "txntype": constants.TXN_TYPE_NON_FINANCIAL,
                "umn": mandate_ctx.umn,
                "payerseqnum": None,
                "mandateoperation": mandateoperation,
                "validitystart": format_date(validitystart),
                "validityend": format_date(validityend),
                "recurrencepattern": recurrencepattern,
                "umnexects": None,
                "revokable": revokable,
                "txamount": None,
                "payeeamt": None,
                "purpose": self._purpose_description(purposecode),
                "purposecode": purposecode,
                "initiationmode": initiationmode,
                "initmode": initiationmode,
                "initiatedby": "PAYER",
                "initiatorpsp": customer.payerpsp,
                "initiatorpsporgid": customer.payerpsporgid,
                "txnnote": "Mandate registration",
                "asdt": format_ts(ts_start),
            }
        )

        stage_ts = ts_start
        for req_api, resp_api in (
            ("ReqMandate", "RespMandate"),
            ("ReqAuthMandate", "RespAuthMandate"),
            ("ReqMandateConfirmation", "RespMandateConfirmation"),
        ):
            txnid = self.relationships.new_txnid()
            custrefno = self.relationships.new_custrefno()

            row_req = dict(shared)
            row_req.update(
                {
                    "apiname": req_api,
                    "txnid": txnid,
                    "custrefno": custrefno,
                    "ts": format_ts(stage_ts),
                    "txndate": format_date(stage_ts.date()),
                    "responsecode": None,
                    "responseresult": None,
                    "errorcode": None,
                    "respcd": None,
                    "result": None,
                    "currstatusdesc": constants.CURR_STATUS_DESCRIPTIONS["PENDING"],
                }
            )
            rows.append(row_req)

            stage_ts = stage_ts + timedelta(seconds=self.rng.randint(1, 8))
            response_fields, outcome = self._response_fields(is_terminal_financial=False)
            row_resp = dict(shared)
            row_resp.update(
                {
                    "apiname": resp_api,
                    "txnid": txnid,
                    "custrefno": custrefno,
                    "ts": format_ts(stage_ts),
                    "txndate": format_date(stage_ts.date()),
                }
            )
            row_resp.update(response_fields)
            rows.append(row_resp)

            stage_ts = stage_ts + timedelta(seconds=self.rng.randint(2, 20))

            if outcome.responseresult == "FAILURE":
                # Mandate creation failed: no executions will follow for this UMN.
                return rows, mandate_ctx

        return rows, mandate_ctx

    def _generate_mandate_execution(self, mandate_ctx: MandateContext, ts_start: datetime) -> List[dict]:
        """Generate one PDN + execution cycle (ReqValCust/RespValCust -> ReqPay/RespPay)."""
        rows: List[dict] = []
        customer = mandate_ctx.customer
        merchant = mandate_ctx.merchant

        seqnum = mandate_ctx.take_seqnum()
        amount = self.growth.sample_amount(merchant.mcc)
        umnexects = ts_start + timedelta(minutes=self.rng.randint(5, 120))

        shared = self._base_row()
        shared.update(self._payer_fields(customer))
        shared.update(self._payee_merchant_fields(merchant))
        shared.update(self._cred_fields())
        shared.update(self._product_fields(customer))
        shared.update(
            {
                "umn": mandate_ctx.umn,
                "payerseqnum": seqnum,
                "mandateoperation": None,
                "validitystart": format_date(mandate_ctx.validitystart),
                "validityend": format_date(mandate_ctx.validityend),
                "recurrencepattern": mandate_ctx.recurrencepattern,
                "umnexects": format_ts(umnexects),
                "revokable": mandate_ctx.revokable,
                "purpose": self._purpose_description(mandate_ctx.purposecode),
                "purposecode": mandate_ctx.purposecode,
                "initiationmode": mandate_ctx.initiationmode,
                "initmode": mandate_ctx.initiationmode,
                "initiatedby": "PAYEE",
                "initiatorpsp": merchant.payeepsp,
                "initiatorpsporgid": merchant.payeepsporgid,
                "txnnote": "AutoPay execution",
            }
        )

        # PDN: ReqValCust / RespValCust (NonFinancial), must precede umnexects.
        pdn_ts = ts_start
        txnid_pdn = self.relationships.new_txnid()
        custrefno_pdn = self.relationships.new_custrefno()
        row_req_pdn = dict(shared)
        row_req_pdn.update(
            {
                "apiname": "ReqValCust",
                "txntype": constants.TXN_TYPE_NON_FINANCIAL,
                "txnid": txnid_pdn,
                "custrefno": custrefno_pdn,
                "ts": format_ts(pdn_ts),
                "txndate": format_date(pdn_ts.date()),
                "txamount": None,
                "payeeamt": None,
                "asdt": format_ts(pdn_ts),
                "responsecode": None,
                "responseresult": None,
                "errorcode": None,
                "respcd": None,
                "result": None,
                "currstatusdesc": constants.CURR_STATUS_DESCRIPTIONS["PENDING"],
            }
        )
        rows.append(row_req_pdn)

        pdn_resp_ts = pdn_ts + timedelta(seconds=self.rng.randint(1, 5))
        pdn_response_fields, pdn_outcome = self._response_fields(is_terminal_financial=False)
        row_resp_pdn = dict(shared)
        row_resp_pdn.update(
            {
                "apiname": "RespValCust",
                "txntype": constants.TXN_TYPE_NON_FINANCIAL,
                "txnid": txnid_pdn,
                "custrefno": custrefno_pdn,
                "ts": format_ts(pdn_resp_ts),
                "txndate": format_date(pdn_resp_ts.date()),
                "txamount": None,
                "payeeamt": None,
                "asdt": format_ts(pdn_resp_ts),
            }
        )
        row_resp_pdn.update(pdn_response_fields)
        rows.append(row_resp_pdn)

        if pdn_outcome.responseresult == "FAILURE":
            return rows

        # Execution: ReqPay / RespPay (Financial), at/after umnexects.
        pay_ts = umnexects + timedelta(seconds=self.rng.randint(1, 30))
        txnid_pay = self.relationships.new_txnid()
        custrefno_pay = self.relationships.new_custrefno()
        row_req_pay = dict(shared)
        row_req_pay.update(
            {
                "apiname": "ReqPay",
                "txntype": constants.TXN_TYPE_FINANCIAL,
                "txnid": txnid_pay,
                "custrefno": custrefno_pay,
                "ts": format_ts(pay_ts),
                "txndate": format_date(pay_ts.date()),
                "txamount": amount,
                "payeeamt": amount,
                "asdt": format_ts(pay_ts),
                "responsecode": None,
                "responseresult": None,
                "errorcode": None,
                "respcd": None,
                "result": None,
                "currstatusdesc": constants.CURR_STATUS_DESCRIPTIONS["PENDING"],
            }
        )
        rows.append(row_req_pay)

        pay_resp_ts = pay_ts + timedelta(seconds=self.rng.randint(1, 8))
        pay_response_fields, _ = self._response_fields(is_terminal_financial=True)
        row_resp_pay = dict(shared)
        row_resp_pay.update(
            {
                "apiname": "RespPay",
                "txntype": constants.TXN_TYPE_FINANCIAL,
                "txnid": txnid_pay,
                "custrefno": custrefno_pay,
                "ts": format_ts(pay_resp_ts),
                "txndate": format_date(pay_resp_ts.date()),
                "txamount": amount,
                "payeeamt": amount,
                "asdt": format_ts(pay_resp_ts),
            }
        )
        row_resp_pay.update(pay_response_fields)
        rows.append(row_resp_pay)
        return rows

    # ------------------------------------------------------------------
    # Batch orchestration
    # ------------------------------------------------------------------
    def generate_batch(self, target_rows: int) -> List[dict]:
        """Generate a batch of fact rows, sized as close as possible to target_rows.

        Mandate lifecycles are generated first (per AUTOPAY_TXN_SHARE of
        estimated financial-transaction volume), each producing a variable
        number of executions; remaining row budget is filled with one-off
        payments. The final list length may exceed target_rows slightly
        (a lifecycle is never truncated mid-way) but will not fall short.
        """
        rows: List[dict] = []
        mandate_contexts: List[MandateContext] = []

        approx_mandate_lifecycles = max(1, int(
            (target_rows * self.config.AUTOPAY_TXN_SHARE) / 6
        ))

        for _ in range(approx_mandate_lifecycles):
            ts_start = self.seasonality.sample_datetime()
            mandate_rows, ctx = self._create_mandate(ts_start)
            rows.extend(mandate_rows)
            if mandate_rows[-1]["responseresult"] == "SUCCESS" or (
                len(mandate_rows) >= 6 and mandate_rows[-1]["responseresult"] != "FAILURE"
            ):
                mandate_contexts.append(ctx)
            if len(rows) >= target_rows:
                break

        for ctx in mandate_contexts:
            if len(rows) >= target_rows:
                break
            n_executions = self.rng.randint(
                self.config.MIN_EXECUTIONS_PER_MANDATE,
                self.config.MAX_EXECUTIONS_PER_MANDATE,
            )
            exec_ts = datetime.combine(ctx.validitystart, datetime.min.time()) + timedelta(days=1)
            for _ in range(n_executions):
                if len(rows) >= target_rows:
                    break
                exec_ts = exec_ts + timedelta(days=self.rng.randint(1, 30))
                if exec_ts.date() > self.config.END_DATE:
                    break
                rows.extend(self._generate_mandate_execution(ctx, exec_ts))

        while len(rows) < target_rows:
            ts_start = self.seasonality.sample_datetime()
            rows.extend(self._generate_oneoff_payment(ts_start))

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
