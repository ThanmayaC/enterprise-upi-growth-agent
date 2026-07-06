"""
customer_generator.py

Generates the Customer Master. Every customer has a stable, immutable
identity: one payeraddress (VPA), one payerbank, one payerpsp, one
account type, one mobile number. These attributes never change across
transactions (Rule: Customer Consistency).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import List

import constants
from config import GeneratorConfig
from master_data_generator import BankRecord, PspRecord
from utils import derive_sub_seed, generate_indian_mobile, seeded_random, write_dataclasses_to_csv

FIRST_NAMES: tuple[str, ...] = (
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna",
    "Ishaan", "Rohan", "Ananya", "Diya", "Saanvi", "Aadhya", "Kiara", "Myra",
    "Pari", "Anika", "Riya", "Isha", "Rahul", "Amit", "Sneha", "Pooja",
    "Neha", "Karan", "Priya", "Sanjay", "Deepa", "Vikram",
)
LAST_NAMES: tuple[str, ...] = (
    "Sharma", "Verma", "Gupta", "Iyer", "Nair", "Reddy", "Rao", "Patel",
    "Mehta", "Singh", "Kumar", "Das", "Chatterjee", "Bose", "Pillai",
    "Menon", "Joshi", "Desai", "Kapoor", "Malhotra",
)


@dataclass(frozen=True)
class CustomerRecord:
    customer_id: str
    customer_name: str
    payeraddress: str
    payerbank: str
    payerpsp: str
    payerpsporgid: str
    remitter_bank: str
    remitterorgid: str
    remitteracctype: str
    mobile: str


class CustomerGenerator:
    """Builds a deterministic, internally consistent Customer Master."""

    def __init__(self, config: GeneratorConfig, banks: List[BankRecord], psps: List[PspRecord]) -> None:
        self.config = config
        self.banks = banks
        self.psps = psps
        self.rng: Random = seeded_random(derive_sub_seed(config.RANDOM_SEED, "customer_generator"))
        # Market-share style weighting: earlier (larger, more common) banks/psps
        # get proportionally more customers, giving a realistic concentration.
        self._bank_weights = [max(1.0, len(banks) - i) for i in range(len(banks))]
        self._psp_weights = [max(1.0, len(psps) - i) for i in range(len(psps))]

    def _pick_bank(self) -> BankRecord:
        return self.rng.choices(self.banks, weights=self._bank_weights, k=1)[0]

    def _pick_psp(self) -> PspRecord:
        return self.rng.choices(self.psps, weights=self._psp_weights, k=1)[0]

    def generate(self) -> List[CustomerRecord]:
        """Generate NUMBER_OF_CUSTOMERS distinct, stable customer identities."""
        customers: List[CustomerRecord] = []
        used_vpas: set[str] = set()

        for idx in range(self.config.NUMBER_OF_CUSTOMERS):
            first = self.rng.choice(FIRST_NAMES)
            last = self.rng.choice(LAST_NAMES)
            name = f"{first} {last}"

            bank = self._pick_bank()
            psp = self._pick_psp()

            local_part = f"{first}.{last}{idx}".lower()
            vpa = f"{local_part}@{psp.handle.lower()}"
            suffix = 1
            while vpa in used_vpas:
                suffix += 1
                vpa = f"{local_part}{suffix}@{psp.handle.lower()}"
            used_vpas.add(vpa)

            acctype = self.rng.choices(
                constants.ACCOUNT_TYPES,
                weights=[40, 30, 5, 5, 10, 5, 5],
                k=1,
            )[0]

            customers.append(
                CustomerRecord(
                    customer_id=f"CUST{idx + 1:07d}",
                    customer_name=name,
                    payeraddress=vpa,
                    payerbank=bank.bank_name,
                    payerpsp=psp.psp_name,
                    payerpsporgid=psp.orgid,
                    remitter_bank=bank.bank_name,
                    remitterorgid=f"ORGB{bank.bank_id[-3:]}",
                    remitteracctype=acctype,
                    mobile=generate_indian_mobile(self.rng),
                )
            )
        return customers

    def write(self, master_dir: Path) -> List[CustomerRecord]:
        """Generate the customer master and persist it to CSV."""
        customers = self.generate()
        write_dataclasses_to_csv(master_dir / "customer_master.csv", customers)
        return customers


if __name__ == "__main__":
    from config import DEFAULT_CONFIG
    from master_data_generator import MasterDataGenerator

    mdg = MasterDataGenerator(DEFAULT_CONFIG)
    master_data = mdg.write_all(DEFAULT_CONFIG.master_path())
    gen = CustomerGenerator(DEFAULT_CONFIG, master_data["bank_master"], master_data["psp_master"])
    gen.write(DEFAULT_CONFIG.master_path())
    print("Customer master generated.")
