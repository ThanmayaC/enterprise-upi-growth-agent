"""
master_data_generator.py

Generates all master (dimension) tables except customer_master and
merchant_master, which have dedicated generators (customer_generator.py,
merchant_generator.py) due to their higher complexity and consistency rules.

Tables produced here:
    bank_master
    psp_master
    mcc_master
    purpose_master
    response_master
    error_master
    initiation_mode_master
    mandate_operation_master
    recurrence_pattern_master
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import List

import constants
from config import GeneratorConfig
from utils import derive_sub_seed, seeded_random, write_dicts_to_csv

BANK_NAMES: tuple[tuple[str, str], ...] = (
    ("State Bank of India", "SBIN"),
    ("HDFC Bank", "HDFC"),
    ("ICICI Bank", "ICIC"),
    ("Axis Bank", "UTIB"),
    ("Punjab National Bank", "PUNB"),
    ("Bank of Baroda", "BARB"),
    ("Kotak Mahindra Bank", "KKBK"),
    ("Canara Bank", "CNRB"),
    ("Union Bank of India", "UBIN"),
    ("IndusInd Bank", "INDB"),
    ("Yes Bank", "YESB"),
    ("IDFC First Bank", "IDFB"),
    ("Bank of India", "BKID"),
    ("Central Bank of India", "CBIN"),
    ("Indian Bank", "IDIB"),
    ("Indian Overseas Bank", "IOBA"),
    ("UCO Bank", "UCBA"),
    ("Bank of Maharashtra", "MAHB"),
    ("Punjab & Sind Bank", "PSIB"),
    ("Federal Bank", "FDRL"),
    ("South Indian Bank", "SIBL"),
    ("RBL Bank", "RATN"),
    ("Karur Vysya Bank", "KVBL"),
    ("City Union Bank", "CIUB"),
    ("DCB Bank", "DCBL"),
    ("Karnataka Bank", "KARB"),
    ("Tamilnad Mercantile Bank", "TMBL"),
    ("Jammu & Kashmir Bank", "JAKA"),
    ("Dhanlaxmi Bank", "DLXB"),
    ("Bandhan Bank", "BDBL"),
)

PSP_DEFS: tuple[tuple[str, str, str], ...] = (
    ("PhonePe", "YBL", "Yes Bank"),
    ("Google Pay", "OKAXIS", "Axis Bank"),
    ("Paytm Payments Bank", "PTYES", "Yes Bank"),
    ("Amazon Pay", "APL", "Axis Bank"),
    ("BHIM", "UPI", "NPCI Settlement"),
    ("WhatsApp Pay", "WABANK", "ICICI Bank"),
    ("Cred", "CRED", "Axis Bank"),
    ("Mobikwik", "IBL", "ICICI Bank"),
)


@dataclass(frozen=True)
class BankRecord:
    bank_id: str
    bank_name: str
    bank_short_name: str
    bank_type: str
    ifsc_prefix: str
    active_flag: str


@dataclass(frozen=True)
class PspRecord:
    psp_id: str
    psp_name: str
    orgid: str
    sponsor_bank: str
    handle: str
    active_flag: str


class MasterDataGenerator:
    """Builds all non-entity master tables and writes them to CSV."""

    def __init__(self, config: GeneratorConfig) -> None:
        self.config = config
        self.rng: Random = seeded_random(derive_sub_seed(config.RANDOM_SEED, "master_data"))

    # ------------------------------------------------------------------
    # Bank Master
    # ------------------------------------------------------------------
    def generate_bank_master(self) -> List[BankRecord]:
        """Generate the Bank Master table, sized by config.NUMBER_OF_BANKS."""
        n = min(self.config.NUMBER_OF_BANKS, len(BANK_NAMES))
        banks: List[BankRecord] = []
        for idx in range(n):
            name, prefix = BANK_NAMES[idx]
            bank_type = "PUBLIC" if idx < 16 else "PRIVATE"
            banks.append(
                BankRecord(
                    bank_id=f"BANK{idx + 1:03d}",
                    bank_name=name,
                    bank_short_name=prefix,
                    bank_type=bank_type,
                    ifsc_prefix=prefix,
                    active_flag="Y",
                )
            )
        return banks

    # ------------------------------------------------------------------
    # PSP Master
    # ------------------------------------------------------------------
    def generate_psp_master(self, banks: List[BankRecord]) -> List[PspRecord]:
        """Generate the PSP Master table, sized by config.NUMBER_OF_PSPS."""
        bank_by_name = {b.bank_name: b for b in banks}
        n = min(self.config.NUMBER_OF_PSPS, len(PSP_DEFS))
        psps: List[PspRecord] = []
        for idx in range(n):
            name, handle, sponsor_name = PSP_DEFS[idx]
            sponsor = bank_by_name.get(sponsor_name, banks[idx % len(banks)])
            psps.append(
                PspRecord(
                    psp_id=f"PSP{idx + 1:03d}",
                    psp_name=name,
                    orgid=f"ORG{idx + 1:04d}",
                    sponsor_bank=sponsor.bank_name,
                    handle=handle,
                    active_flag="Y",
                )
            )
        return psps

    # ------------------------------------------------------------------
    # Simple static/reference masters
    # ------------------------------------------------------------------
    def generate_mcc_master(self) -> List[dict]:
        """Return the MCC master rows exactly as sourced from constants."""
        return [dict(row) for row in constants.MCC_LIST]

    def generate_purpose_master(self) -> List[dict]:
        """Return the Purpose master rows exactly as sourced from constants."""
        return [dict(row) for row in constants.PURPOSE_CODES]

    def generate_response_master(self) -> List[dict]:
        """Return the Response Code master rows exactly as sourced from constants."""
        return [dict(row) for row in constants.RESPONSE_CODES]

    def generate_error_master(self) -> List[dict]:
        """Return the Error Code master rows exactly as sourced from constants."""
        return [dict(row) for row in constants.ERROR_CODES]

    def generate_initiation_mode_master(self) -> List[dict]:
        """Return the Initiation Mode master rows exactly as sourced from constants."""
        return [dict(row) for row in constants.INITIATION_MODES]

    def generate_mandate_operation_master(self) -> List[dict]:
        """Return the Mandate Operation master rows."""
        descriptions = {
            "CREATE": "Create a new mandate",
            "UPDATE": "Update an existing mandate",
            "PAUSE": "Temporarily pause a mandate",
            "UNPAUSE": "Resume a paused mandate",
            "REVOKE": "Permanently revoke a mandate",
        }
        return [
            {"mandateoperation": op, "description": descriptions[op]}
            for op in constants.MANDATE_OPERATIONS
        ]

    def generate_recurrence_pattern_master(self) -> List[dict]:
        """Return the Recurrence Pattern master rows."""
        descriptions = {
            "DAILY": "Executes every day",
            "WEEKLY": "Executes every week",
            "FORTNIGHTLY": "Executes every two weeks",
            "MONTHLY": "Executes every month",
            "BIMONTHLY": "Executes every two months",
            "QUARTERLY": "Executes every quarter",
            "YEARLY": "Executes every year",
            "ASPRESENTED": "Executes as and when presented",
        }
        return [
            {"recurrencepattern": pat, "description": descriptions[pat]}
            for pat in constants.RECURRENCE_PATTERNS
        ]

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------
    def generate_all(self) -> dict:
        """Generate every master table this module is responsible for.

        Returns a dict keyed by table name containing the in-memory rows,
        so downstream generators (customer/merchant/transaction) can
        reference them without re-reading from disk.
        """
        banks = self.generate_bank_master()
        psps = self.generate_psp_master(banks)
        return {
            "bank_master": banks,
            "psp_master": psps,
            "mcc_master": self.generate_mcc_master(),
            "purpose_master": self.generate_purpose_master(),
            "response_master": self.generate_response_master(),
            "error_master": self.generate_error_master(),
            "initiation_mode_master": self.generate_initiation_mode_master(),
            "mandate_operation_master": self.generate_mandate_operation_master(),
            "recurrence_pattern_master": self.generate_recurrence_pattern_master(),
        }

    def write_all(self, master_dir: Path) -> dict:
        """Generate all master tables and persist them as CSV files."""
        data = self.generate_all()

        write_dicts_to_csv(
            master_dir / "bank_master.csv",
            [b.__dict__ for b in data["bank_master"]],
            ["bank_id", "bank_name", "bank_short_name", "bank_type", "ifsc_prefix", "active_flag"],
        )
        write_dicts_to_csv(
            master_dir / "psp_master.csv",
            [p.__dict__ for p in data["psp_master"]],
            ["psp_id", "psp_name", "orgid", "sponsor_bank", "handle", "active_flag"],
        )
        write_dicts_to_csv(
            master_dir / "mcc_master.csv",
            data["mcc_master"],
            ["mcc", "category", "autopay_possible", "autopay_priority"],
        )
        write_dicts_to_csv(
            master_dir / "purpose_master.csv",
            data["purpose_master"],
            ["purposecode", "purpose", "category", "autopay_potential", "recurring"],
        )
        write_dicts_to_csv(
            master_dir / "response_master.csv",
            data["response_master"],
            ["responsecode", "responseresult", "description", "owner", "retryable"],
        )
        write_dicts_to_csv(
            master_dir / "error_master.csv",
            data["error_master"],
            ["errorcode", "description", "type", "owner", "retryable", "severity", "category"],
        )
        write_dicts_to_csv(
            master_dir / "initiation_mode_master.csv",
            data["initiation_mode_master"],
            ["initiationmode", "description", "category", "autopay_supported"],
        )
        write_dicts_to_csv(
            master_dir / "mandate_operation_master.csv",
            data["mandate_operation_master"],
            ["mandateoperation", "description"],
        )
        write_dicts_to_csv(
            master_dir / "recurrence_pattern_master.csv",
            data["recurrence_pattern_master"],
            ["recurrencepattern", "description"],
        )
        return data


if __name__ == "__main__":
    from config import DEFAULT_CONFIG

    generator = MasterDataGenerator(DEFAULT_CONFIG)
    generator.write_all(DEFAULT_CONFIG.master_path())
    print("Master data generated at", DEFAULT_CONFIG.master_path())
